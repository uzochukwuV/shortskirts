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
from pipeline.scene_gen import generate_scene_clip
from pipeline.versioning import (
    GENERATION_VERSION,
    IMAGE_MODEL_NAME,
    IMAGE_MODEL_VERSION,
    WORKFLOW_VERSION,
    build_state_snapshot,
)
from pipeline.assembler import assemble_episode
from pipeline.narrated_image_story import generate_narrated_scene_image, assemble_narrated_episode


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


def _flatten_scene_sequence(plan: dict) -> list[tuple[dict, dict]]:
    sequence: list[tuple[dict, dict]] = []
    for ep_plan in plan.get("episodes", []):
        for scene_plan in ep_plan.get("scenes", []):
            sequence.append((ep_plan, scene_plan))
    return sequence


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

    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading story")

    try:
        story = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

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

        async def get_episode_id(ep_plan: dict) -> str:
            ep_num = ep_plan["episode_number"]
            if ep_num in episode_cache:
                return episode_cache[ep_num]
            ep_id = await _ensure_episode_row(pool, story_id, ep_plan)
            episode_cache[ep_num] = ep_id
            return ep_id

        for idx in range(resume_index, len(scene_sequence)):
            ep_plan, scene_plan = scene_sequence[idx]
            ep_num = ep_plan["episode_number"]
            scene_num = scene_plan["scene_number"]

            if batch_start_episode_number is None:
                batch_start_episode_number = ep_num
                batch_start_scene_number = scene_num

            await update_job(
                pool,
                job_id,
                progress=step,
                current_step=(
                    f"Ep {ep_num} Scene {scene_num}: Generating image"
                    if is_narrated_image_story
                    else f"Ep {ep_num} Scene {scene_num}: Generating clip"
                ),
            )

            ep_id = await get_episode_id(ep_plan)

            scene_row = await pool.fetchrow(
                "SELECT id FROM scenes WHERE episode_id = $1 AND scene_number = $2",
                ep_id, scene_num,
            )

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
                            "episode_number": ep_num,
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
                            "episode_number": ep_num,
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

            try:
                if is_narrated_image_story:
                    result = await generate_narrated_scene_image(
                        story_id=story_id,
                        episode_id=str(ep_id),
                        scene=scene_plan,
                        story_context=plan,
                        character_refs=char_refs,
                        previous_scene_image_url=previous_exit_frame,
                        previous_scene_summary=previous_summary,
                        style=story["style"],
                    )
                else:
                    result = await generate_scene_clip(
                        story_id=story_id,
                        episode_id=str(ep_id),
                        scene=scene_plan,
                        story_context=plan,
                        character_refs=char_refs,
                        previous_exit_frame_url=previous_exit_frame,
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
                    "narration_model": narration_model if is_narrated_image_story else None,
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
                                "episode_number": ep_num,
                                "scene_number": scene_num,
                                "refs_used": result.get("refs_used", 0),
                                "image_url": result.get("image_url"),
                                "media_url": result.get("image_url") or result.get("clip_url"),
                            },
                        )),
                        scene_id,
                    )
                    previous_exit_frame = result.get("exit_frame_url")
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
                                "episode_number": ep_num,
                                "scene_number": scene_num,
                                "clip_url": result.get("clip_url"),
                                "media_url": result.get("clip_url"),
                            },
                        )),
                        scene_id,
                    )
                    previous_exit_frame = result.get("exit_frame_url")

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

                previous_summary = scene_plan.get("description", "")
                generated_since_checkpoint += 1
                if is_narrated_image_story:
                    checkpoint_scenes.append({
                        "scene_number": scene_plan.get("scene_number", scene_num),
                        "title": scene_plan.get("title", f"Scene {scene_num}"),
                        "description": scene_plan.get("description", ""),
                        "narration": result.get("narration", scene_plan.get("narration", "")),
                    })
                step += 1

            except Exception as e:
                print(f"[orchestrator] Scene {scene_num} failed: {e}")
                await pool.execute("UPDATE scenes SET status='failed' WHERE id=$1", scene_id)
                failed_scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
                if failed_scene:
                    await record_scene_history(
                        pool,
                        story=story,
                        scene=failed_scene,
                        event_type="scene_failed",
                        payload={
                            "status": failed_scene["status"],
                            "scene_number": scene_num,
                            "error": str(e)[:500],
                        },
                    )
                step += 1

            next_item = scene_sequence[idx + 1] if idx + 1 < len(scene_sequence) else None
            episode_finished = next_item is None or next_item[0]["episode_number"] != ep_num
            if episode_finished:
                await update_job(pool, job_id, progress=step, current_step=f"Assembling Episode {ep_num}")
                await _assemble_episode(pool, story_id, ep_id, ep_num, is_narrated_image_story)

            if (
                is_narrated_image_story
                and checkpoint_batch_size > 0
                and generated_since_checkpoint >= checkpoint_batch_size
                and next_item is not None
            ):
                narration_text = build_narration_script(checkpoint_scenes)
                resume_payload = {
                    "next_scene_index": idx + 1,
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
                        "start_episode_number": batch_start_episode_number or ep_num,
                        "start_scene_number": batch_start_scene_number or scene_num,
                        "end_episode_number": ep_num,
                        "end_scene_number": scene_num,
                    },
                    extra={
                        "batch_number": batch_number,
                        "batch_size": checkpoint_batch_size,
                        "narration_model": narration_model,
                        "narration_voice": narration_voice,
                        "next_scene_index": idx + 1,
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
                    start_episode_number=batch_start_episode_number or ep_num,
                    start_scene_number=batch_start_scene_number or scene_num,
                    end_episode_number=ep_num,
                    end_scene_number=scene_num,
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
                        "start_episode_number": batch_start_episode_number or ep_num,
                        "start_scene_number": batch_start_scene_number or scene_num,
                        "end_episode_number": ep_num,
                        "end_scene_number": scene_num,
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
                    "next_scene_index": idx + 1,
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
        return result
    except Exception as e:
        print(f"[orchestrator] Story generation failed: {e}")
        failed_story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
        if failed_story:
            await record_story_history(
                pool,
                story=failed_story,
                event_type="generation_failed",
                payload={"status": failed_story["status"], "error": str(e)[:500]},
            )
        raise
