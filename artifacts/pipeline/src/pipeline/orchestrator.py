import json
from datetime import datetime
from typing import Optional

from db.connection import get_pool
from pipeline.character_gen import generate_character_references, get_character_embedding
from pipeline.job_runtime import update_job
from pipeline.scene_gen import generate_scene_clip
from pipeline.assembler import assemble_episode
from pipeline.narrated_image_story import generate_narrated_scene_image, assemble_narrated_episode


async def run_story_generation(story_id: str, job_id: str):
    pool = await get_pool()

    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading story")

    try:
        story = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        plan = story["episode_plan"]
        if isinstance(plan, str):
            plan = json.loads(plan)

        total_episodes = len(plan.get("episodes", []))
        total_steps = total_episodes * story["num_scenes"] + 2
        step = 0

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

            # Generate ref images if not already done
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

        # ── Generate scenes per episode ───────────────────────────────────────
        for ep_plan in plan.get("episodes", []):
            ep_num = ep_plan["episode_number"]
            await update_job(
                pool, job_id,
                progress=step,
                current_step=f"Starting Episode {ep_num}: {ep_plan['title']}"
            )

            ep_row = await pool.fetchrow(
                "SELECT * FROM episodes WHERE story_id = $1 AND episode_number = $2",
                story_id, ep_num,
            )
            if not ep_row:
                ep_id = await pool.fetchval(
                    """INSERT INTO episodes (story_id, episode_number, title, status)
                       VALUES ($1, $2, $3, 'running') RETURNING id""",
                    story_id, ep_num, ep_plan["title"],
                )
            else:
                ep_id = str(ep_row["id"])
                await pool.execute("UPDATE episodes SET status = 'running' WHERE id = $1", ep_id)

            previous_exit_frame = None
            previous_summary = ""
            completed_scenes = []

            for scene_plan in ep_plan.get("scenes", []):
                scene_num = scene_plan["scene_number"]
                await update_job(
                    pool, job_id,
                    progress=step,
                    current_step=(
                        f"Ep {ep_num} Scene {scene_num}: Generating image"
                        if is_narrated_image_story
                        else f"Ep {ep_num} Scene {scene_num}: Generating clip"
                    ),
                )

                scene_row = await pool.fetchrow(
                    "SELECT id FROM scenes WHERE episode_id = $1 AND scene_number = $2",
                    ep_id, scene_num,
                )

                # Store full scene plan data in generation_metadata at insert time
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
                })

                if not scene_row:
                    scene_id = await pool.fetchval(
                        """INSERT INTO scenes (episode_id, scene_number, prompt, status, generation_metadata)
                           VALUES ($1, $2, $3, 'running', $4::jsonb) RETURNING id""",
                        ep_id, scene_num,
                        scene_plan.get("visual_prompt", scene_plan.get("description", "")),
                        plan_metadata,
                    )
                else:
                    scene_id = str(scene_row["id"])
                    # Update metadata for existing scene (re-generation case)
                    await pool.execute(
                        "UPDATE scenes SET generation_metadata=$1::jsonb WHERE id=$2",
                        plan_metadata, scene_id,
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

                    # Merge generation result into metadata
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
                    })

                    if is_narrated_image_story:
                        await pool.execute(
                            """UPDATE scenes SET image_url=$1, clip_url=NULL, exit_frame_url=$2, duration=$3,
                               status='completed', generation_metadata=$4::jsonb
                               WHERE id=$5""",
                            result["image_url"],
                            result.get("exit_frame_url"),
                            result.get("duration", 6.0),
                            merged_meta,
                            scene_id,
                        )
                        previous_exit_frame = result.get("exit_frame_url")
                    else:
                        await pool.execute(
                            """UPDATE scenes SET clip_url=$1, exit_frame_url=$2, duration=$3,
                               status='completed', generation_metadata=$4::jsonb
                               WHERE id=$5""",
                            result["clip_url"],
                            result.get("exit_frame_url"),
                            result.get("duration", 5.0),
                            merged_meta,
                            scene_id,
                        )
                        previous_exit_frame = result.get("exit_frame_url")
                    previous_summary = scene_plan.get("description", "")
                    completed_scenes.append({
                        "scene_number": scene_num,
                        "clip_url": result.get("clip_url"),
                        "image_url": result.get("image_url"),
                        "media_url": result.get("image_url") or result.get("clip_url"),
                        "exit_frame_url": result.get("exit_frame_url"),
                        "duration": result.get("duration", 5.0),
                        "prompt": result["prompt"],
                        "narration": result.get("narration"),
                    })

                except Exception as e:
                    print(f"[orchestrator] Scene {scene_num} failed: {e}")
                    await pool.execute("UPDATE scenes SET status='failed' WHERE id=$1", scene_id)

                step += 1

            await update_job(pool, job_id, progress=step, current_step=f"Assembling Episode {ep_num}")

            if completed_scenes:
                try:
                    if is_narrated_image_story:
                        asm = await assemble_narrated_episode(
                            story_id=story_id,
                            episode_id=str(ep_id),
                            episode_number=ep_num,
                            scenes=completed_scenes,
                        )
                    else:
                        asm = await assemble_episode(
                            story_id=story_id,
                            episode_id=str(ep_id),
                            episode_number=ep_num,
                            scenes=completed_scenes,
                        )
                    await pool.execute(
                        """UPDATE episodes SET assembled_video_url=$1, manifest_url=$2, status='completed'
                           WHERE id=$3""",
                        asm["assembled_video_url"], asm["manifest_url"], ep_id,
                    )
                except Exception as e:
                    print(f"[orchestrator] Assembly failed for ep {ep_num}: {e}")
                    await pool.execute("UPDATE episodes SET status='failed' WHERE id=$1", ep_id)
            else:
                await pool.execute("UPDATE episodes SET status='failed' WHERE id=$1", ep_id)

        # ── Fix: use 'completed' not 'ready' ──────────────────────────────────
        await pool.execute("UPDATE stories SET status='completed' WHERE id=$1", story_id)
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
        raise
