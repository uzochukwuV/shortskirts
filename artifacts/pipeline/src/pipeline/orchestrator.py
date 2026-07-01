import asyncio
import json
from datetime import datetime
from typing import Optional

from db.connection import get_pool
from pipeline.character_gen import generate_character_references, get_character_embedding
from pipeline.scene_gen import generate_scene_clip
from pipeline.assembler import assemble_episode


async def update_job(pool, job_id: str, **kwargs):
    fields = []
    values = []
    i = 1
    for k, v in kwargs.items():
        if k == "result" and isinstance(v, dict):
            fields.append(f"{k} = ${i}::jsonb")
            values.append(json.dumps(v))
        else:
            fields.append(f"{k} = ${i}")
            values.append(v)
        i += 1
    values.append(job_id)
    await pool.execute(
        f"UPDATE generation_jobs SET {', '.join(fields)} WHERE id = ${i}",
        *values,
    )


async def run_story_generation(story_id: str, job_id: str):
    pool = await get_pool()

    try:
        await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading story")

        story = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        plan = story["episode_plan"]
        if isinstance(plan, str):
            plan = json.loads(plan)

        total_episodes = len(plan.get("episodes", []))
        total_steps = total_episodes * story["num_scenes"] + 2
        step = 0

        await update_job(pool, job_id, total_steps=total_steps, current_step="Loading characters")

        characters = await pool.fetch(
            "SELECT * FROM characters WHERE story_id = $1", story_id
        )
        char_map = {r["name"]: dict(r) for r in characters}

        step += 1

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
                await pool.execute(
                    "UPDATE episodes SET status = 'running' WHERE id = $1", ep_id
                )

            previous_exit_frame = None
            previous_summary = ""
            completed_scenes = []

            for scene_plan in ep_plan.get("scenes", []):
                scene_num = scene_plan["scene_number"]
                await update_job(
                    pool, job_id,
                    progress=step,
                    current_step=f"Ep {ep_num} Scene {scene_num}: Generating clip",
                )

                scene_row = await pool.fetchrow(
                    "SELECT id FROM scenes WHERE episode_id = $1 AND scene_number = $2",
                    ep_id, scene_num,
                )
                if not scene_row:
                    scene_id = await pool.fetchval(
                        """INSERT INTO scenes (episode_id, scene_number, prompt, status)
                           VALUES ($1, $2, $3, 'running') RETURNING id""",
                        ep_id, scene_num, scene_plan.get("visual_prompt", scene_plan.get("description", "")),
                    )
                else:
                    scene_id = str(scene_row["id"])

                chars_in_scene = scene_plan.get("characters_present", [])
                char_refs = []
                for char_name in chars_in_scene:
                    char = char_map.get(char_name)
                    if char:
                        refs = char.get("ref_image_urls")
                        if isinstance(refs, str):
                            refs = json.loads(refs)
                        char_refs.extend(refs or [])

                char_refs = char_refs[:4]

                try:
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

                    await pool.execute(
                        """UPDATE scenes SET clip_url=$1, exit_frame_url=$2, duration=$3,
                           status='completed', generation_metadata=$4::jsonb
                           WHERE id=$5""",
                        result["clip_url"],
                        result.get("exit_frame_url"),
                        result.get("duration", 5.0),
                        json.dumps({"prompt": result["prompt"], "refs_used": result.get("refs_used", 0)}),
                        scene_id,
                    )

                    previous_exit_frame = result.get("exit_frame_url")
                    previous_summary = scene_plan.get("description", "")
                    completed_scenes.append({
                        "scene_number": scene_num,
                        "clip_url": result["clip_url"],
                        "exit_frame_url": result.get("exit_frame_url"),
                        "duration": result.get("duration", 5.0),
                        "prompt": result["prompt"],
                    })

                except Exception as e:
                    print(f"[orchestrator] Scene {scene_num} failed: {e}")
                    await pool.execute(
                        "UPDATE scenes SET status='failed' WHERE id=$1", scene_id
                    )

                step += 1

            await update_job(pool, job_id, progress=step, current_step=f"Assembling Episode {ep_num}")

            if completed_scenes:
                try:
                    asm = await assemble_episode(
                        story_id=story_id,
                        episode_id=str(ep_id),
                        episode_number=ep_num,
                        scenes=completed_scenes,
                    )
                    await pool.execute(
                        """UPDATE episodes SET assembled_video_url=$1, manifest_url=$2, status='completed'
                           WHERE id=$3""",
                        asm["assembled_video_url"],
                        asm["manifest_url"],
                        ep_id,
                    )
                except Exception as e:
                    print(f"[orchestrator] Assembly failed for ep {ep_num}: {e}")
                    await pool.execute("UPDATE episodes SET status='failed' WHERE id=$1", ep_id)
            else:
                await pool.execute("UPDATE episodes SET status='failed' WHERE id=$1", ep_id)

        await pool.execute("UPDATE stories SET status='ready' WHERE id=$1", story_id)
        await update_job(
            pool, job_id,
            status="completed",
            progress=total_steps,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result={"story_id": story_id},
        )

    except Exception as e:
        print(f"[orchestrator] Story generation failed: {e}")
        await update_job(
            pool, job_id,
            status="failed",
            error=str(e),
            completed_at=datetime.utcnow(),
        )
        await pool.execute("UPDATE stories SET status='failed' WHERE id=$1", story_id)
