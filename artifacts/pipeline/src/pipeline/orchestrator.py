import asyncio
import json
import os
from datetime import datetime
from typing import Optional

from db.connection import get_pool
from job_queue import enqueue_job, WORKLOAD_AUDIO
from pipeline.audio_gen import build_narration_script
from pipeline.character_gen import generate_character_references, get_character_embedding
from pipeline.history import (
    record_checkpoint_history,
    record_scene_history,
    record_story_history,
)
from pipeline.job_runtime import update_job
from pipeline.generation_coordinator import GenerationCoordinatorError, generate_with_coordinator
from pipeline.pipeline_runtime import (
    finish_pipeline_run,
    finish_pipeline_step,
    pipeline_context_binding,
    record_pipeline_artifact,
    start_pipeline_run,
    start_pipeline_step,
)
from pipeline.steps.scene_steps import complete_scene_render_step
from pipeline.versioning import (
    GENERATION_VERSION,
    IMAGE_MODEL_NAME,
    IMAGE_MODEL_VERSION,
    WORKFLOW_VERSION,
    build_state_snapshot,
)
from pipeline.assembler import assemble_episode
from pipeline.narrated_image_story import assemble_narrated_episode


def _json_loads(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _workflow_refs(story: dict, key: str) -> list[str]:
    workflow_state = story.get("workflow_state") or {}
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except Exception:
            workflow_state = {}
    refs = workflow_state.get(key) or []
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except Exception:
            refs = []
    return [u for u in refs if u]


def _merge_workflow_state(story: dict, patch: dict) -> dict:
    workflow_state = story.get("workflow_state") or {}
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except Exception:
            workflow_state = {}
    if not isinstance(workflow_state, dict):
        workflow_state = {}
    merged = {**workflow_state}
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


async def _sync_scene_characters(pool, scene_id: str, story_id: str, character_names: list[str]) -> None:
    names = [name for name in character_names if name]
    if not names:
        await pool.execute("DELETE FROM scene_characters WHERE scene_id=$1", scene_id)
        return

    rows = await pool.fetch(
        """SELECT id, name
           FROM characters
           WHERE story_id=$1 AND name = ANY($2::text[])""",
        story_id,
        names,
    )
    name_to_id = {row["name"]: str(row["id"]) for row in rows}
    character_ids = [name_to_id[name] for name in names if name in name_to_id]

    await pool.execute("DELETE FROM scene_characters WHERE scene_id=$1", scene_id)
    for index, character_id in enumerate(character_ids):
        await pool.execute(
            """INSERT INTO scene_characters (scene_id, character_id, is_primary)
               VALUES ($1, $2, $3)""",
            scene_id,
            character_id,
            index == 0,
        )


def _flatten_scene_sequence(plan: dict) -> list[tuple[dict, dict]]:
    sequence: list[tuple[dict, dict]] = []
    for ep_plan in plan.get("episodes", []):
        for scene_plan in ep_plan.get("scenes", []):
            sequence.append((ep_plan, scene_plan))
    return sequence


def _group_scenes_by_episode(plan: dict) -> dict[int, list[tuple[dict, dict]]]:
    """Group scenes by episode number for parallel processing within episodes."""
    episodes: dict[int, list[tuple[dict, dict]]] = {}
    for ep_plan in plan.get("episodes", []):
        ep_num = ep_plan["episode_number"]
        episodes[ep_num] = []
        for scene_plan in ep_plan.get("scenes", []):
            episodes[ep_num].append((ep_plan, scene_plan))
    return episodes


async def _process_episode_scenes_parallel(
    pool,
    *,
    story: dict,
    story_id: str,
    episode_number: int,
    ep_plan: dict,
    scene_plans: list[dict],
    char_map: dict,
    story_scene_refs: list[str],
    previous_exit_frame: str | None,
    previous_summary: str,
    missing_ref_characters: set[str],
    is_narrated_image_story: bool,
    narration_model: str,
    narration_voice: str,
    workflow_version: str,
    generation_version: str,
    run_id: str | None,
    job_id: str,
) -> tuple[list[dict], str | None, str, list[tuple[int, int, str]]]:
    """
    Process all scenes in an episode in parallel for maximum speedup.
    Uses staged parallelization: first scene goes first, then remaining scenes in parallel.
    Returns: (checkpoint_scenes, last_exit_frame, last_summary, failed_scenes)
    """
    ep_id = await _ensure_episode_row(pool, story_id, ep_plan)
    checkpoint_scenes: list[dict] = []
    failed_scene_numbers: list[tuple[int, int, str]] = []
    current_exit_frame = previous_exit_frame
    current_summary = previous_summary

    # Each scene depends on the actual exit frame and summary from its predecessor.
    # This is deliberately sequential to preserve continuity and avoid parallel spend.
    for scene_plan in scene_plans:
        scene_num = scene_plan["scene_number"]
        try:
            cp_scene, exit_frame, summary, failure = await _generate_single_scene_internal(
                pool=pool,
                story=story,
                story_id=story_id,
                ep_id=ep_id,
                ep_plan=ep_plan,
                scene_plan=scene_plan,
                scene_num=scene_num,
                episode_number=episode_number,
                char_map=char_map,
                story_scene_refs=story_scene_refs,
                previous_exit_frame=current_exit_frame,
                previous_summary=current_summary,
                missing_ref_characters=missing_ref_characters,
                is_narrated_image_story=is_narrated_image_story,
                narration_model=narration_model,
                narration_voice=narration_voice,
                workflow_version=workflow_version,
                generation_version=generation_version,
                run_id=run_id,
                job_id=job_id,
            )
            if failure:
                failed_scene_numbers.append(failure)
                break
            if cp_scene:
                checkpoint_scenes.append(cp_scene)
            if exit_frame:
                current_exit_frame = exit_frame
            if summary:
                current_summary = summary
        except Exception as exc:
            failed_scene_numbers.append((episode_number, scene_num, str(exc)[:300]))
            break
    return checkpoint_scenes, current_exit_frame, current_summary, failed_scene_numbers
    # For strict continuity, process scenes sequentially
    # For performance, process first scene then remaining in parallel
    if len(scene_plans) == 1:
        # Single scene - just process it directly
        try:
            result = await _generate_single_scene_internal(
                pool=pool,
                story=story,
                story_id=story_id,
                ep_id=ep_id,
                ep_plan=ep_plan,
                scene_plan=scene_plans[0],
                scene_num=scene_plans[0]["scene_number"],
                episode_number=episode_number,
                char_map=char_map,
                story_scene_refs=story_scene_refs,
                previous_exit_frame=current_exit_frame,
                previous_summary=current_summary,
                missing_ref_characters=missing_ref_characters,
                is_narrated_image_story=is_narrated_image_story,
                narration_model=narration_model,
                narration_voice=narration_voice,
                workflow_version=workflow_version,
                generation_version=generation_version,
                run_id=run_id,
                job_id=job_id,
            )
            cp_scene, exit_frame, summary, failure = result
            if failure:
                failed_scene_numbers.append(failure)
            else:
                if cp_scene:
                    checkpoint_scenes.append(cp_scene)
                if exit_frame:
                    current_exit_frame = exit_frame
                if summary:
                    current_summary = summary
        except Exception as e:
            failed_scene_numbers.append((episode_number, scene_plans[0]["scene_number"], str(e)[:300]))
    else:
        # Multiple scenes - use staged parallelization:
        # 1. First process the first scene with episode's previous exit frame
        # 2. Then process remaining scenes in parallel with the first scene's exit frame
        
        first_scene_plan = scene_plans[0]
        
        # Stage 1: Generate first scene with continuity from previous episode
        try:
            first_result = await _generate_single_scene_internal(
                pool=pool,
                story=story,
                story_id=story_id,
                ep_id=ep_id,
                ep_plan=ep_plan,
                scene_plan=first_scene_plan,
                scene_num=first_scene_plan["scene_number"],
                episode_number=episode_number,
                char_map=char_map,
                story_scene_refs=story_scene_refs,
                previous_exit_frame=current_exit_frame,
                previous_summary=current_summary,
                missing_ref_characters=missing_ref_characters,
                is_narrated_image_story=is_narrated_image_story,
                narration_model=narration_model,
                narration_voice=narration_voice,
                workflow_version=workflow_version,
                generation_version=generation_version,
                run_id=run_id,
                job_id=job_id,
            )
            first_cp, first_exit, first_summary, first_failure = first_result
            if first_failure:
                failed_scene_numbers.append(first_failure)
            else:
                if first_cp:
                    checkpoint_scenes.append(first_cp)
                if first_exit:
                    current_exit_frame = first_exit
                if first_summary:
                    current_summary = first_summary
        except Exception as e:
            failed_scene_numbers.append((episode_number, first_scene_plan["scene_number"], str(e)[:300]))
            # If first scene fails, remaining scenes can't have proper continuity
            current_exit_frame = None
        
        # Stage 2: Generate remaining scenes in parallel with first scene's exit frame
        if len(scene_plans) > 1 and current_exit_frame:
            remaining_tasks = []
            for scene_plan in scene_plans[1:]:
                scene_num = scene_plan["scene_number"]
                try:
                    task = _generate_single_scene_internal(
                        pool=pool,
                        story=story,
                        story_id=story_id,
                        ep_id=ep_id,
                        ep_plan=ep_plan,
                        scene_plan=scene_plan,
                        scene_num=scene_num,
                        episode_number=episode_number,
                        char_map=char_map,
                        story_scene_refs=story_scene_refs,
                        # Use first scene's exit frame for all remaining scenes
                        previous_exit_frame=current_exit_frame,
                        previous_summary=scene_plan.get("description", ""),
                        missing_ref_characters=missing_ref_characters,
                        is_narrated_image_story=is_narrated_image_story,
                        narration_model=narration_model,
                        narration_voice=narration_voice,
                        workflow_version=workflow_version,
                        generation_version=generation_version,
                        run_id=run_id,
                        job_id=job_id,
                    )
                    remaining_tasks.append(task)
                except Exception as e:
                    failed_scene_numbers.append((episode_number, scene_num, str(e)[:300]))
            
            if remaining_tasks:
                results = await asyncio.gather(*remaining_tasks, return_exceptions=True)
                
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        scene_num = scene_plans[idx + 1]["scene_number"]
                        failed_scene_numbers.append((episode_number, scene_num, str(result)[:300]))
                        continue
                    
                    cp_scene, exit_frame, summary, failure = result
                    
                    if failure:
                        failed_scene_numbers.append(failure)
                        continue
                    
                    if cp_scene:
                        checkpoint_scenes.append(cp_scene)
                    if exit_frame:
                        current_exit_frame = exit_frame
                    if summary:
                        current_summary = summary
    
    return checkpoint_scenes, current_exit_frame, current_summary, failed_scene_numbers


async def _generate_single_scene_internal(
    pool,
    *,
    story: dict,
    story_id: str,
    ep_id: str,
    ep_plan: dict,
    scene_plan: dict,
    scene_num: int,
    episode_number: int,
    char_map: dict,
    story_scene_refs: list[str],
    previous_exit_frame: str | None,
    previous_summary: str,
    missing_ref_characters: set[str],
    is_narrated_image_story: bool,
    narration_model: str,
    narration_voice: str,
    workflow_version: str,
    generation_version: str,
    run_id: str | None,
    job_id: str,
) -> tuple[dict | None, str | None, str | None, tuple[int, int, str] | None]:
    """Internal function to generate a single scene. Returns (checkpoint_scene, exit_frame, summary, failure)."""
    plan_metadata = json.dumps({
        "title": scene_plan.get("title", f"Scene {scene_num}"),
        "description": scene_plan.get("description", ""),
        "visual_prompt": scene_plan.get("visual_prompt", ""),
        "mood": scene_plan.get("mood", ""),
        "location": scene_plan.get("location", ""),
        "action": scene_plan.get("action", ""),
        "characters_present": scene_plan.get("characters_present", []),
        "narration": scene_plan.get("narration", ""),
        "duration_seconds": scene_plan.get("duration_seconds"),
        "media_kind": "image" if is_narrated_image_story else "video",
        "narration_model": narration_model if is_narrated_image_story else None,
        "workflow_version": workflow_version,
        "generation_version": generation_version,
        "image_model": IMAGE_MODEL_NAME if is_narrated_image_story else None,
        "image_model_version": IMAGE_MODEL_VERSION if is_narrated_image_story else None,
    })

    scene_row = await pool.fetchrow(
        "SELECT id FROM scenes WHERE episode_id = $1 AND scene_number = $2",
        ep_id, scene_num,
    )

    if not scene_row:
        scene_id = await pool.fetchval(
            """INSERT INTO scenes (episode_id, scene_number, prompt, status, generation_metadata,
               generation_version, image_model, image_model_version, state_snapshot)
               VALUES ($1, $2, $3, 'running', $4::jsonb, $5, $6, $7, $8::jsonb) RETURNING id""",
            ep_id, scene_num,
            scene_plan.get("visual_prompt", scene_plan.get("description", "")),
            plan_metadata,
            generation_version,
            IMAGE_MODEL_NAME if is_narrated_image_story else None,
            IMAGE_MODEL_VERSION if is_narrated_image_story else None,
            json.dumps(build_state_snapshot(
                story=story,
                scene=scene_plan,
                extra={
                    "episode_number": episode_number,
                    "scene_number": scene_num,
                },
            )),
        )
        scene_row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if scene_row:
            await record_scene_history(
                pool,
                story=story,
                scene=scene_row,
                event_type="scene_created",
                payload={
                    "status": scene_row["status"],
                    "scene_number": scene_num,
                },
            )
    else:
        scene_id = str(scene_row["id"])
        await pool.execute(
            """UPDATE scenes SET generation_metadata=$1::jsonb, generation_version=$2,
               image_model=$3, image_model_version=$4, state_snapshot=$5::jsonb WHERE id=$6""",
            plan_metadata,
            generation_version,
            IMAGE_MODEL_NAME if is_narrated_image_story else None,
            IMAGE_MODEL_VERSION if is_narrated_image_story else None,
            json.dumps(build_state_snapshot(
                story=story,
                scene=scene_plan,
                extra={
                    "episode_number": episode_number,
                    "scene_number": scene_num,
                },
            )),
            scene_id,
        )
        scene_row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if scene_row:
            await record_scene_history(
                pool,
                story=story,
                scene=scene_row,
                event_type="scene_prepared",
                payload={
                    "status": scene_row["status"],
                    "scene_number": scene_num,
                },
            )

    await _sync_scene_characters(
        pool,
        scene_id,
        story_id,
        [name for name in scene_plan.get("characters_present", []) if name],
    )

    chars_in_scene = scene_plan.get("characters_present", [])
    char_refs = []
    for char_name in chars_in_scene:
        char = char_map.get(char_name)
        if char:
            refs = char.get("ref_image_urls")
            if isinstance(refs, str):
                refs = json.loads(refs)
            char_refs.extend(refs or [])
            if not refs:
                missing_ref_characters.add(char_name)
    char_refs = char_refs[:4]
    if story_scene_refs:
        char_refs = (char_refs + story_scene_refs)[:8]
    if chars_in_scene and not char_refs:
        print(
            f"[orchestrator] Warning: Scene {scene_num} has characters "
            "but no usable reference images"
        )

    render_step_id = await start_pipeline_step(
        run_id=run_id,
        story_id=story_id,
        episode_id=str(ep_id),
        scene_id=str(scene_id),
        job_id=job_id,
        step_key=f"render_scene:{episode_number}:{scene_num}",
        step_type="scene_render",
        input={
            "episode_number": episode_number,
            "scene_number": scene_num,
            "media_kind": "image" if is_narrated_image_story else "video",
            "character_ref_count": len(char_refs),
            "previous_exit_frame": previous_exit_frame,
        },
    )
    
    try:
        async with pipeline_context_binding(run_id=run_id, step_id=render_step_id):
            result, generation_plan = await generate_with_coordinator(
                story=story,
                episode_id=str(ep_id),
                scene=scene_plan,
                story_context=story.get("episode_plan", {}),
                character_refs=char_refs,
                previous_exit_frame_url=previous_exit_frame,
                previous_scene_image_url=previous_exit_frame,
                previous_scene_summary=previous_summary,
                style=story["style"],
            )

        merged_meta = json.dumps({
            "title": scene_plan.get("title", f"Scene {scene_num}"),
            "description": scene_plan.get("description", ""),
            "visual_prompt": result["prompt"],
            "mood": scene_plan.get("mood", ""),
            "location": scene_plan.get("location", ""),
            "action": scene_plan.get("action", ""),
            "characters_present": scene_plan.get("characters_present", []),
            "refs_used": result.get("refs_used", 0),
            "narration": result.get("narration", scene_plan.get("narration", "")),
            "duration_seconds": result.get("duration", scene_plan.get("duration_seconds")),
            "media_kind": result.get("media_kind", "video"),
            "image_url": result.get("image_url"),
            "media_url": result.get("image_url") or result.get("clip_url"),
            "exit_frame_url": result.get("exit_frame_url"),
            "video_provider": result.get("video_provider"),
            "narration_model": narration_model if is_narrated_image_story else None,
            "generation_coordinator": generation_plan.model_dump(),
        })

        if is_narrated_image_story:
            await pool.execute(
                """UPDATE scenes SET image_url=$1, clip_url=NULL, exit_frame_url=$2, duration=$3,
                   status='completed', generation_metadata=$4::jsonb, generation_version=$5,
                   image_model=$6, image_model_version=$7, state_snapshot=$8::jsonb
                   WHERE id=$9""",
                result["image_url"],
                result.get("exit_frame_url"),
                result.get("duration", 6.0),
                merged_meta,
                generation_version,
                IMAGE_MODEL_NAME,
                IMAGE_MODEL_VERSION,
                json.dumps(build_state_snapshot(
                    story=story,
                    scene=scene_plan,
                    extra={
                        "episode_number": episode_number,
                        "scene_number": scene_num,
                        "refs_used": result.get("refs_used", 0),
                        "image_url": result.get("image_url"),
                        "media_url": result.get("image_url") or result.get("clip_url"),
                        "video_provider": result.get("video_provider"),
                        "generation_coordinator": generation_plan.model_dump(),
                    },
                )),
                scene_id,
            )
        else:
            await pool.execute(
                """UPDATE scenes SET clip_url=$1, exit_frame_url=$2, duration=$3,
                   status='completed', generation_metadata=$4::jsonb, generation_version=$5,
                   state_snapshot=$6::jsonb
                   WHERE id=$7""",
                result["clip_url"],
                result.get("exit_frame_url"),
                result.get("duration", 5.0),
                merged_meta,
                generation_version,
                json.dumps(build_state_snapshot(
                    story=story,
                    scene=scene_plan,
                    extra={
                        "episode_number": episode_number,
                        "scene_number": scene_num,
                        "clip_url": result.get("clip_url"),
                        "media_url": result.get("clip_url"),
                        "video_provider": result.get("video_provider"),
                        "generation_coordinator": generation_plan.model_dump(),
                    },
                )),
                scene_id,
            )

        completed_scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if completed_scene:
            await record_scene_history(
                pool,
                story=story,
                scene=completed_scene,
                event_type="scene_completed",
                payload={
                    "status": completed_scene["status"],
                    "refs_used": result.get("refs_used", 0),
                    "scene_number": scene_num,
                },
            )
        
        await complete_scene_render_step(
            run_id=run_id,
            step_id=render_step_id,
            story_id=story_id,
            episode_id=str(ep_id),
            scene_id=str(scene_id),
            result=result,
            generation_plan=generation_plan,
            episode_number=episode_number,
            scene_number=scene_num,
            default_media_kind="image" if is_narrated_image_story else "video",
        )

        exit_frame = result.get("exit_frame_url")
        summary = scene_plan.get("description", "")
        checkpoint_scene = None
        if is_narrated_image_story:
            checkpoint_scene = {
                "scene_number": scene_plan.get("scene_number", scene_num),
                "title": scene_plan.get("title", f"Scene {scene_num}"),
                "description": scene_plan.get("description", ""),
                "narration": result.get("narration", scene_plan.get("narration", "")),
            }

        return checkpoint_scene, exit_frame, summary, None

    except GenerationCoordinatorError as e:
        print(f"[orchestrator] Coordinator handoff for scene {scene_num}: {e}")
        await finish_pipeline_step(
            render_step_id,
            status="failed",
            error=str(e),
            output={
                "episode_number": episode_number,
                "scene_number": scene_num,
                "generation_coordinator": e.plan.model_dump() if e.plan else None,
            },
        )
        await pool.execute("UPDATE scenes SET status='failed' WHERE id=$1", scene_id)
        return None, None, None, (episode_number, scene_num, str(e)[:300])
    except Exception as e:
        print(f"[orchestrator] Scene {scene_num} generation failed: {e}")
        await finish_pipeline_step(
            render_step_id,
            status="failed",
            error=str(e),
        )
        await pool.execute("UPDATE scenes SET status='failed' WHERE id=$1", scene_id)
        return None, None, None, (episode_number, scene_num, str(e)[:300])


async def _ensure_episode_row(pool, story_id: str, ep_plan: dict) -> str:
    ep_num = ep_plan["episode_number"]
    ep_row = await pool.fetchrow(
        "SELECT * FROM episodes WHERE story_id = $1 AND episode_number = $2",
        story_id, ep_num,
    )
    if not ep_row:
        return str(
            await pool.fetchval(
                """INSERT INTO episodes (story_id, episode_number, title, status)
                   VALUES ($1, $2, $3, 'running') RETURNING id""",
                story_id, ep_num, ep_plan["title"],
            )
        )

    ep_id = str(ep_row["id"])
    await pool.execute("UPDATE episodes SET status = 'running' WHERE id = $1", ep_id)
    return ep_id


async def _fetch_episode_scenes(pool, episode_id: str, narrated: bool) -> list[dict]:
    rows = await pool.fetch(
        "SELECT * FROM scenes WHERE episode_id = $1 ORDER BY scene_number ASC",
        episode_id,
    )
    scenes: list[dict] = []
    for r in rows:
        meta = _json_loads(r["generation_metadata"]) or {}
        scenes.append({
            "scene_number": r["scene_number"],
            "clip_url": r["clip_url"],
            "image_url": r.get("image_url"),
            "media_url": r.get("image_url") or r.get("clip_url"),
            "exit_frame_url": r["exit_frame_url"],
            "duration": r["duration"],
            "prompt": r["prompt"],
            "narration": meta.get("narration", ""),
        })
    return scenes


async def _assemble_episode(pool, story_id: str, episode_id: str, episode_number: int, narrated: bool) -> None:
    scenes = await _fetch_episode_scenes(pool, episode_id, narrated)
    has_media = any(s.get("image_url") or s.get("clip_url") for s in scenes)
    if not has_media:
        await pool.execute("UPDATE episodes SET status='failed' WHERE id=$1", episode_id)
        return

    try:
        if narrated:
            asm = await assemble_narrated_episode(
                story_id=story_id,
                episode_id=episode_id,
                episode_number=episode_number,
                scenes=scenes,
            )
        else:
            asm = await assemble_episode(
                story_id=story_id,
                episode_id=episode_id,
                episode_number=episode_number,
                scenes=scenes,
            )
        await pool.execute(
            """UPDATE episodes SET assembled_video_url=$1, manifest_url=$2, status='completed'
               WHERE id=$3""",
            asm["assembled_video_url"], asm["manifest_url"], episode_id,
        )
    except Exception as e:
        print(f"[orchestrator] Assembly failed for ep {episode_number}: {e}")
        await pool.execute("UPDATE episodes SET status='failed' WHERE id=$1", episode_id)


async def _create_resume_job(pool, story_id: str, resume_state: dict) -> str:
    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type, result)
           VALUES ('story', $1, 'pending', 0, 'Awaiting checkpoint approval', 'full_episode_resume', $2::jsonb)
           RETURNING *""",
        story_id,
        json.dumps(resume_state),
    )
    return str(job_row["id"])


async def _create_audio_job(pool, story_id: str, checkpoint_id: str, narration_model: str, narration_voice: str) -> str:
    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type, result)
           VALUES ('story', $1, 'pending', 1, 'Awaiting narration audio', 'checkpoint_audio', $2::jsonb)
           RETURNING *""",
        story_id,
        json.dumps({
            "story_id": story_id,
            "checkpoint_id": checkpoint_id,
            "narration_model": narration_model,
            "narration_voice": narration_voice,
        }),
    )
    return str(job_row["id"])


async def _create_checkpoint(
    pool,
    *,
    story_id: str,
    job_id: str,
    resume_job_id: str,
    batch_number: int,
    batch_size: int,
    start_episode_number: int,
    start_scene_number: int,
    end_episode_number: int,
    end_scene_number: int,
    narration_model: str,
    narration_voice: str,
    narration_text: str,
    state_snapshot: dict,
    resume_state: dict,
) -> dict:
    row = await pool.fetchrow(
        """INSERT INTO story_generation_checkpoints
           (story_id, job_id, resume_job_id, batch_number, batch_size,
            start_episode_number, start_scene_number, end_episode_number, end_scene_number,
            status, generation_version, narration_model, narration_voice, narration_text,
            audio_status, state_snapshot, resume_state)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'pending_review',$10,$11,$12,$13,'pending',$14::jsonb,$15::jsonb)
           RETURNING *""",
        story_id,
        job_id,
        resume_job_id,
        batch_number,
        batch_size,
        start_episode_number,
        start_scene_number,
        end_episode_number,
        end_scene_number,
        GENERATION_VERSION,
        narration_model,
        narration_voice,
        narration_text,
        json.dumps(state_snapshot),
        json.dumps(resume_state),
    )
    return dict(row)


async def run_story_generation(story_id: str, job_id: str, resume_state: Optional[dict] = None):
    pool = await get_pool()
    run_id: str | None = None

    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading story")

    try:
        story_row = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
        if not story_row:
            raise ValueError(f"Story {story_id} not found")
        story = dict(story_row)
        story_dict = story
        workflow_state = _json_loads(story_dict.get("workflow_state")) or {}
        run_id = await start_pipeline_run(
            owner_id=str(story_dict["owner_id"]) if story_dict.get("owner_id") else None,
            story_id=story_id,
            job_id=job_id,
            run_type="story_generation" if resume_state is None else "story_generation_resume",
            config={
                "workflow_type": story_dict.get("workflow_type"),
                "workflow_version": story_dict.get("workflow_version"),
                "generation_version": story_dict.get("generation_version"),
                "workflow_state": workflow_state,
                "resume_state": resume_state,
            },
        )

        await record_story_history(
            pool,
            story=story,
            event_type="generation_started" if resume_state is None else "generation_resumed",
            payload={
                "status": story["status"],
                "resume_state": resume_state,
            },
        )

        plan = _json_loads(story["episode_plan"])
        if not plan:
            raise ValueError(f"Story {story_id} has no episode plan")

        scene_sequence = _flatten_scene_sequence(plan)
        total_episodes = len(plan.get("episodes", []))
        total_steps = len(scene_sequence) + 2
        step = int((resume_state or {}).get("step", 0))

        # ── Generate character reference images ───────────────────────────────
        await update_job(pool, job_id, total_steps=total_steps, current_step="Generating character references")
        character_step_id = await start_pipeline_step(
            run_id=run_id,
            story_id=story_id,
            job_id=job_id,
            step_key="ensure_character_refs",
            step_type="media",
            input={"expected_character_count": len(plan.get("characters", []))},
        )
        characters = await pool.fetch("SELECT * FROM characters WHERE story_id = $1", story_id)
        char_map: dict = {}
        missing_ref_characters: set[str] = set()
        expected_character_names = {
            c.get("name", "").strip()
            for c in plan.get("characters", [])
            if c.get("name", "").strip()
        }
        if expected_character_names and not characters:
            raise RuntimeError("Story plan includes characters, but none were materialized")
        for char_row in characters:
            char_dict = dict(char_row)
            char_name = char_dict["name"]

            refs = char_dict.get("ref_image_urls")
            if isinstance(refs, str):
                refs = json.loads(refs)

            if not refs:
                await update_job(pool, job_id, current_step=f"Generating refs for {char_name}")
                try:
                    char_id = str(char_dict["id"])
                    ref_urls = await generate_character_references(
                        story_id=story_id,
                        character_id=char_id,
                        character=char_dict,
                        style=story["style"],
                        num_refs=3,
                    )
                    embedding = get_character_embedding(char_dict)
                    await pool.execute(
                        """UPDATE characters SET ref_image_urls=$1::jsonb, embedding=$2::jsonb
                           WHERE id=$3""",
                        json.dumps(ref_urls),
                        json.dumps(embedding),
                        char_id,
                    )
                    char_dict["ref_image_urls"] = ref_urls
                except Exception as e:
                    print(f"[orchestrator] Character ref gen failed for {char_name}: {e}")
                    missing_ref_characters.add(char_name)

            refs = char_dict.get("ref_image_urls")
            if isinstance(refs, str):
                refs = json.loads(refs)
            if not refs:
                missing_ref_characters.add(char_name)

            char_map[char_name] = char_dict
        await finish_pipeline_step(
            character_step_id,
            output={
                "character_count": len(char_map),
                "missing_character_refs": sorted(missing_ref_characters),
            },
        )
        step += 1

        is_narrated_image_story = story.get("workflow_type") == "narrated_image_story"
        checkpoint_batch_size = int(os.getenv("STORY_CHECKPOINT_BATCH_SIZE", "3")) if is_narrated_image_story else 0
        narration_model = os.getenv("NARRATION_AUDIO_MODEL", "qwen-audio-3.0-tts-plus")
        narration_voice = os.getenv("NARRATION_AUDIO_VOICE", "longanfengyue")
        workflow_version = story.get("workflow_version") or WORKFLOW_VERSION
        generation_version = story.get("generation_version") or GENERATION_VERSION

        resume_index = int((resume_state or {}).get("next_scene_index", 0))
        previous_exit_frame = (resume_state or {}).get("previous_exit_frame")
        previous_summary = (resume_state or {}).get("previous_summary", "")
        batch_number = int((resume_state or {}).get("batch_number", 1))
        generated_since_checkpoint = 0
        batch_start_episode_number: Optional[int] = None
        batch_start_scene_number: Optional[int] = None
        checkpoint_scenes: list[dict] = []
        story_scene_refs = _workflow_refs(story, "scene_reference_urls")

        episode_cache: dict[int, str] = {}
        failed_scene_numbers: list[tuple[int, int, str]] = []

        # Use parallel episode processing for maximum speedup (20x improvement)
        # Group scenes by episode and process all scenes in each episode in parallel
        episodes_grouped = _group_scenes_by_episode(plan)
        episode_numbers = sorted(episodes_grouped.keys())
        
        # Determine start index for resume support
        start_ep_idx = 0
        if resume_index > 0:
            # Find which episode contains the resume_index
            scene_count = 0
            for ep_num in episode_numbers:
                ep_scenes = episodes_grouped[ep_num]
                if scene_count + len(ep_scenes) > resume_index:
                    start_ep_idx = episode_numbers.index(ep_num)
                    break
                scene_count += len(ep_scenes)

        for ep_idx in range(start_ep_idx, len(episode_numbers)):
            ep_num = episode_numbers[ep_idx]
            ep_scenes = episodes_grouped[ep_num]
            ep_plan = ep_scenes[0][0]  # Get ep_plan from first scene tuple
            
            if batch_start_episode_number is None:
                batch_start_episode_number = ep_num
                batch_start_scene_number = ep_scenes[0][1]["scene_number"]

            await update_job(
                pool,
                job_id,
                progress=step,
                current_step=(
                    f"Ep {ep_num}: Generating {len(ep_scenes)} scenes in parallel"
                    if len(ep_scenes) > 1
                    else f"Ep {ep_num} Scene {ep_scenes[0][1]['scene_number']}: Generating"
                ),
            )

            # Process all scenes in this episode in parallel using asyncio.gather
            scene_plans = [scene_plan for (ep_plan_item, scene_plan) in ep_scenes]
            ep_checkpoint_scenes, last_exit_frame, last_summary, ep_failed = \
                await _process_episode_scenes_parallel(
                    pool=pool,
                    story=story,
                    story_id=story_id,
                    episode_number=ep_num,
                    ep_plan=ep_plan,
                    scene_plans=scene_plans,
                    char_map=char_map,
                    story_scene_refs=story_scene_refs,
                    previous_exit_frame=previous_exit_frame,
                    previous_summary=previous_summary,
                    missing_ref_characters=missing_ref_characters,
                    is_narrated_image_story=is_narrated_image_story,
                    narration_model=narration_model,
                    narration_voice=narration_voice,
                    workflow_version=workflow_version,
                    generation_version=generation_version,
                    run_id=run_id,
                    job_id=job_id,
                )
            
            # Update state from parallel processing results
            failed_scene_numbers.extend(ep_failed)
            checkpoint_scenes.extend(ep_checkpoint_scenes)
            if last_exit_frame:
                previous_exit_frame = last_exit_frame
            if last_summary:
                previous_summary = last_summary
            generated_since_checkpoint += len(ep_checkpoint_scenes)
            step += len(ep_scenes)

            # Get episode ID for assembly
            ep_id = episode_cache.get(ep_num)
            if not ep_id:
                ep_row = await pool.fetchrow(
                    "SELECT id FROM episodes WHERE story_id=$1 AND episode_number=$2",
                    story_id, ep_num,
                )
                ep_id = str(ep_row["id"]) if ep_row else None

            # Handle failures
            if failed_scene_numbers:
                await pool.execute("UPDATE stories SET status='failed', updated_at=now() WHERE id=$1", story_id)
                failed_story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
                if failed_story:
                    await record_story_history(
                        pool,
                        story=failed_story,
                        event_type="generation_failed",
                        payload={
                            "status": failed_story["status"],
                            "failed_scenes": [
                                {"episode_number": ep, "scene_number": sc, "error": err[:300]}
                                for ep, sc, err in failed_scene_numbers
                            ],
                        },
                    )
                result = {
                    "story_id": story_id,
                    "failed_scenes": [
                        {"episode_number": ep, "scene_number": sc, "error": err[:300]}
                        for ep, sc, err in failed_scene_numbers
                    ],
                }
                if missing_ref_characters:
                    result["warnings"] = {
                        "missing_character_refs": sorted(missing_ref_characters),
                    }
                await update_job(
                    pool,
                    job_id,
                    status="failed",
                    progress=step,
                    current_step="Generation failed",
                    completed_at=datetime.utcnow(),
                    result=result,
                )
                if run_id:
                    await finish_pipeline_run(
                        run_id,
                        status="failed",
                        summary=result,
                        error="One or more scenes failed",
                    )
                return result

            # Assemble episode after all scenes complete
            await update_job(pool, job_id, progress=step, current_step=f"Assembling Episode {ep_num}")
            assembly_step_id = await start_pipeline_step(
                run_id=run_id,
                story_id=story_id,
                episode_id=str(ep_id),
                job_id=job_id,
                step_key=f"assemble_episode:{ep_num}",
                step_type="assembly",
                input={"episode_number": ep_num, "narrated": is_narrated_image_story},
            )
            try:
                await _assemble_episode(pool, story_id, ep_id, ep_num, is_narrated_image_story)
            except Exception as e:
                await finish_pipeline_step(
                    assembly_step_id,
                    status="failed",
                    error=str(e),
                    output={"episode_number": ep_num},
                )
                raise
            episode_row = await pool.fetchrow("SELECT * FROM episodes WHERE id=$1", ep_id)
            await finish_pipeline_step(
                assembly_step_id,
                output={
                    "episode_number": ep_num,
                    "status": episode_row["status"] if episode_row else None,
                    "assembled_video_url": episode_row["assembled_video_url"] if episode_row else None,
                    "manifest_url": episode_row["manifest_url"] if episode_row else None,
                },
            )
            if episode_row and episode_row["assembled_video_url"]:
                await record_pipeline_artifact(
                    run_id=run_id,
                    step_id=assembly_step_id,
                    story_id=story_id,
                    episode_id=str(ep_id),
                    artifact_type="assembled_episode",
                    media_kind="video",
                    url=episode_row["assembled_video_url"],
                    metadata={
                        "episode_number": ep_num,
                        "manifest_url": episode_row["manifest_url"],
                    },
                )

            # Checkpoint logic for narrated image stories
            next_ep_idx = ep_idx + 1
            has_next_episode = next_ep_idx < len(episode_numbers)
            if (
                is_narrated_image_story
                and checkpoint_batch_size > 0
                and generated_since_checkpoint >= checkpoint_batch_size
                and has_next_episode
            ):
                narration_text = build_narration_script(checkpoint_scenes)
                resume_payload = {
                    "next_scene_index": sum(len(episodes_grouped[ep]) for ep in episode_numbers[:next_ep_idx]),
                    "previous_exit_frame": previous_exit_frame,
                    "previous_summary": previous_summary,
                    "batch_number": batch_number + 1,
                    "step": step,
                    "narration_model": narration_model,
                    "workflow_version": workflow_version,
                    "generation_version": generation_version,
                }
                resume_job_id = await _create_resume_job(pool, story_id, resume_payload)
                state_snapshot = build_state_snapshot(
                    story=story,
                    checkpoint={
                        "batch_number": batch_number,
                        "batch_size": checkpoint_batch_size,
                        "start_episode_number": batch_start_episode_number,
                        "start_scene_number": batch_start_scene_number,
                        "end_episode_number": ep_num,
                        "end_scene_number": ep_scenes[-1][1]["scene_number"],
                    },
                    extra={
                        "batch_number": batch_number,
                        "batch_size": checkpoint_batch_size,
                        "narration_model": narration_model,
                        "narration_voice": narration_voice,
                        "next_scene_index": sum(len(episodes_grouped[ep]) for ep in episode_numbers[:next_ep_idx]),
                        "previous_exit_frame": previous_exit_frame,
                        "previous_summary": previous_summary,
                    },
                )
                checkpoint = await _create_checkpoint(
                    pool,
                    story_id=story_id,
                    job_id=job_id,
                    resume_job_id=resume_job_id,
                    batch_number=batch_number,
                    batch_size=checkpoint_batch_size,
                    start_episode_number=batch_start_episode_number,
                    start_scene_number=batch_start_scene_number,
                    end_episode_number=ep_num,
                    end_scene_number=ep_scenes[-1][1]["scene_number"],
                    narration_model=narration_model,
                    narration_voice=narration_voice,
                    narration_text=narration_text,
                    state_snapshot=state_snapshot,
                    resume_state=resume_payload,
                )
                await record_checkpoint_history(
                    pool,
                    story=story,
                    checkpoint=checkpoint,
                    event_type="checkpoint_created",
                    payload={
                        "batch_number": batch_number,
                        "batch_size": checkpoint_batch_size,
                        "start_episode_number": batch_start_episode_number,
                        "start_scene_number": batch_start_scene_number,
                        "end_episode_number": ep_num,
                        "end_scene_number": ep_scenes[-1][1]["scene_number"],
                        "audio_status": checkpoint.get("audio_status"),
                    },
                    state_snapshot=state_snapshot,
                )
                audio_job_id = await _create_audio_job(
                    pool,
                    story_id=story_id,
                    checkpoint_id=str(checkpoint["id"]),
                    narration_model=narration_model,
                    narration_voice=narration_voice,
                )
                await pool.execute(
                    """UPDATE story_generation_checkpoints
                       SET audio_job_id=$2, audio_status='pending', narration_text=$3,
                           narration_model=$4, narration_voice=$5, updated_at=now()
                       WHERE id=$1""",
                    str(checkpoint["id"]),
                    audio_job_id,
                    narration_text,
                    narration_model,
                    narration_voice,
                )
                await enqueue_job(audio_job_id, workload=WORKLOAD_AUDIO)
                await pool.execute(
                    "UPDATE stories SET status='checkpoint_review', updated_at=now() WHERE id=$1",
                    story_id,
                )
                refreshed_story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
                if refreshed_story:
                    await record_story_history(
                        pool,
                        story=refreshed_story,
                        event_type="checkpoint_review_requested",
                        payload={
                            "status": refreshed_story["status"],
                            "checkpoint_id": str(checkpoint["id"]),
                            "audio_job_id": audio_job_id,
                        },
                    )
                result = {
                    "story_id": story_id,
                    "checkpoint_id": str(checkpoint["id"]),
                    "resume_job_id": resume_job_id,
                    "audio_job_id": audio_job_id,
                    "batch_number": batch_number,
                    "batch_size": checkpoint_batch_size,
                    "next_scene_index": sum(len(episodes_grouped[ep]) for ep in episode_numbers[:next_ep_idx]),
                    "narration_model": narration_model,
                    "narration_voice": narration_voice,
                    "workflow_version": workflow_version,
                    "generation_version": generation_version,
                }
                if missing_ref_characters:
                    result["warnings"] = {
                        "missing_character_refs": sorted(missing_ref_characters),
                    }
                await update_job(
                    pool,
                    job_id,
                    status="completed",
                    progress=step,
                    current_step="Checkpoint review required",
                    completed_at=datetime.utcnow(),
                    result=result,
                )
                if run_id:
                    await finish_pipeline_run(
                        run_id,
                        status="waiting_for_approval",
                        summary=result,
                    )
                return result

        await pool.execute("UPDATE stories SET status='completed' WHERE id=$1", story_id)
        completed_story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
        if completed_story:
            await record_story_history(
                pool,
                story=completed_story,
                event_type="generation_completed",
                payload={"status": completed_story["status"]},
            )
        result = {"story_id": story_id}
        if missing_ref_characters:
            result["warnings"] = {
                "missing_character_refs": sorted(missing_ref_characters),
            }
        await update_job(
            pool, job_id,
            status="completed",
            progress=total_steps,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result=result,
        )
        if run_id:
            await finish_pipeline_run(run_id, status="completed", summary=result)
        return result
    except Exception as e:
        print(f"[orchestrator] Story generation failed: {e}")
        if run_id:
            await finish_pipeline_run(run_id, status="failed", error=str(e))
        failed_story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
        if failed_story:
            await record_story_history(
                pool,
                story=failed_story,
                event_type="generation_failed",
                payload={"status": failed_story["status"], "error": str(e)[:500]},
            )
        raise
