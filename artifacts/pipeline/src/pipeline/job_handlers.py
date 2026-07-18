import json
from datetime import datetime

from db.connection import get_pool
from pipeline.history import record_checkpoint_history, record_scene_history
from pipeline.character_gen import generate_character_references, get_character_embedding
from pipeline.audio_gen import synthesize_narration_audio
from pipeline.job_runtime import update_job
from pipeline.scene_gen import generate_scene_clip
from pipeline.narrated_image_story import generate_narrated_scene_image
from pipeline.versioning import (
    GENERATION_VERSION,
    IMAGE_EDIT_MODEL_NAME,
    IMAGE_EDIT_MODEL_VERSION,
    IMAGE_MODEL_NAME,
    IMAGE_MODEL_VERSION,
)


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


async def run_character_ref_job(character_id: str, job_id: str, worker_id: str):
    pool = await get_pool()
    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Generating new ref images")

    try:
        char = await pool.fetchrow("SELECT * FROM characters WHERE id=$1", character_id)
        if not char:
            raise ValueError(f"Character {character_id} not found")

        story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", str(char["story_id"]))
        if not story:
            raise ValueError(f"Parent story {char['story_id']} not found")

        char_dict = {
            "name": char["name"],
            "description": char["description"],
            "role": char["role"],
            "personality": char["personality"],
            "appearance": char["appearance"],
        }

        urls = await generate_character_references(str(story["id"]), character_id, char_dict, story["style"])
        embedding = get_character_embedding(char_dict)
        await pool.execute(
            """UPDATE characters
               SET ref_image_urls=$1::jsonb, embedding=$2::jsonb,
                   approval_status='pending', updated_at=now()
               WHERE id=$3""",
            json.dumps(urls),
            json.dumps(embedding),
            character_id,
        )
        await update_job(
            pool,
            job_id,
            status="completed",
            progress=1,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result={"character_id": character_id, "ref_count": len(urls)},
        )
    except Exception as e:
        print(f"[characters] Ref generation failed for {character_id}: {e}")
        await update_job(
            pool,
            job_id,
            status="failed",
            current_step=f"Failed: {str(e)[:200]}",
            error=str(e)[:1000],
            completed_at=datetime.utcnow(),
        )
        raise


async def run_scene_regen_job(scene_id: str, job_id: str, worker_id: str):
    pool = await get_pool()
    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading context")
    story = None

    try:
        scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        episode = await pool.fetchrow("SELECT * FROM episodes WHERE id=$1", scene["episode_id"])
        if not episode:
            raise ValueError(f"Episode {scene['episode_id']} not found")

        story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", episode["story_id"])
        if not story:
            raise ValueError(f"Story {episode['story_id']} not found")
        is_narrated_image_story = story.get("workflow_type") == "narrated_image_story"

        plan = story["episode_plan"]
        if isinstance(plan, str):
            plan = json.loads(plan)
        story_scene_refs = _workflow_refs(story, "scene_reference_urls")

        ep_num = episode["episode_number"]
        scene_num = scene["scene_number"]
        scene_plan = {}
        for ep in plan.get("episodes", []):
            if ep["episode_number"] == ep_num:
                for sc in ep.get("scenes", []):
                    if sc["scene_number"] == scene_num:
                        scene_plan = sc
                        break
                break

        if not scene_plan:
            meta = scene["generation_metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta) if meta else {}
            scene_plan = {
                "scene_number": scene_num,
                "title": (meta or {}).get("title", f"Scene {scene_num}"),
                "description": (meta or {}).get("description", ""),
                "visual_prompt": scene["prompt"],
                "mood": (meta or {}).get("mood", ""),
                "location": (meta or {}).get("location", ""),
                "action": (meta or {}).get("action", ""),
                "characters_present": (meta or {}).get("characters_present", []),
                "narration": (meta or {}).get("narration", ""),
                "duration_seconds": (meta or {}).get("duration_seconds", scene.get("duration")),
                "media_kind": (meta or {}).get("media_kind", "image" if story.get("workflow_type") == "narrated_image_story" else "video"),
            }

        characters = await pool.fetch(
            "SELECT * FROM characters WHERE story_id=$1", str(story["id"])
        )
        char_map = {r["name"]: dict(r) for r in characters}
        char_refs = []
        for cname in scene_plan.get("characters_present", []):
            char = char_map.get(cname)
            if char:
                refs = char.get("ref_image_urls") or []
                if isinstance(refs, str):
                    refs = json.loads(refs)
                char_refs.extend(refs)
        char_refs = char_refs[:4]
        if story_scene_refs:
            char_refs = (char_refs + story_scene_refs)[:8]

        if is_narrated_image_story:
            await update_job(pool, job_id, current_step="Generating new image scene")
            result = await generate_narrated_scene_image(
                story_id=str(story["id"]),
                episode_id=str(episode["id"]),
                scene=scene_plan,
                story_context=plan,
                character_refs=char_refs,
                previous_scene_image_url=None,
                previous_scene_summary="",
                style=story["style"],
            )
        else:
            await update_job(pool, job_id, current_step="Generating new video clip")
            result = await generate_scene_clip(
                story_id=str(story["id"]),
                episode_id=str(episode["id"]),
                scene=scene_plan,
                story_context=plan,
                character_refs=char_refs,
                previous_exit_frame_url=None,
                previous_scene_summary="",
                style=story["style"],
            )

        existing_meta = scene["generation_metadata"]
        if isinstance(existing_meta, str):
            existing_meta = json.loads(existing_meta) if existing_meta else {}
        merged = {
            **(existing_meta or {}),
            "visual_prompt": result["prompt"],
            "refs_used": result.get("refs_used", 0),
            "media_kind": result.get("media_kind", "image" if is_narrated_image_story else "video"),
            "narration": result.get("narration", ""),
            "generation_version": story.get("generation_version", GENERATION_VERSION),
            "image_model": IMAGE_MODEL_NAME if is_narrated_image_story else None,
            "image_model_version": IMAGE_MODEL_VERSION if is_narrated_image_story else None,
            "edit_model": IMAGE_EDIT_MODEL_NAME if is_narrated_image_story else None,
            "edit_model_version": IMAGE_EDIT_MODEL_VERSION if is_narrated_image_story else None,
            "image_url": result.get("image_url"),
            "media_url": result.get("image_url") or result.get("clip_url"),
            "exit_frame_url": result.get("exit_frame_url"),
        }
        regen_count = (scene.get("regeneration_count") or 0) + 1
        if is_narrated_image_story:
            await pool.execute(
                """UPDATE scenes SET image_url=$1, clip_url=NULL, exit_frame_url=$2, duration=$3,
                   status='completed', approval_status='pending',
                   generation_metadata=$4::jsonb, regeneration_count=$5, generation_version=$6,
                   image_model=$7, image_model_version=$8, edit_model=$9, edit_model_version=$10,
                   state_snapshot=$11::jsonb, updated_at=now()
                   WHERE id=$12""",
                result["image_url"],
                result.get("exit_frame_url"),
                result.get("duration", 6.0),
                json.dumps(merged),
                regen_count,
                story.get("generation_version", GENERATION_VERSION),
                IMAGE_MODEL_NAME,
                IMAGE_MODEL_VERSION,
                IMAGE_EDIT_MODEL_NAME,
                IMAGE_EDIT_MODEL_VERSION,
                    json.dumps({
                        "story_id": str(story["id"]),
                        "episode_id": str(episode["id"]),
                        "scene_id": scene_id,
                        "generation_version": story.get("generation_version", GENERATION_VERSION),
                        "image_model": IMAGE_MODEL_NAME,
                        "image_model_version": IMAGE_MODEL_VERSION,
                        "edit_model": IMAGE_EDIT_MODEL_NAME,
                        "edit_model_version": IMAGE_EDIT_MODEL_VERSION,
                        "image_url": result.get("image_url"),
                        "media_url": result.get("image_url") or result.get("clip_url"),
                    }),
                    scene_id,
                )
        else:
            await pool.execute(
                """UPDATE scenes SET clip_url=$1, exit_frame_url=$2, duration=$3,
                   status='completed', approval_status='pending',
                   generation_metadata=$4::jsonb, regeneration_count=$5, generation_version=$6,
                   state_snapshot=$7::jsonb, updated_at=now()
                   WHERE id=$8""",
                result["clip_url"],
                result.get("exit_frame_url"),
                result.get("duration", 5.0),
                json.dumps(merged),
                regen_count,
                story.get("generation_version", GENERATION_VERSION),
                    json.dumps({
                        "story_id": str(story["id"]),
                        "episode_id": str(episode["id"]),
                        "scene_id": scene_id,
                        "generation_version": story.get("generation_version", GENERATION_VERSION),
                        "clip_url": result.get("clip_url"),
                        "media_url": result.get("clip_url"),
                    }),
                    scene_id,
                )
        completed_scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if completed_scene:
            await record_scene_history(
                pool,
                story=story,
                scene=completed_scene,
                event_type="scene_regenerated",
                source_job_id=job_id,
                payload={
                    "status": completed_scene["status"],
                    "approval_status": completed_scene.get("approval_status"),
                    "regen_count": regen_count,
                },
            )
        await update_job(
            pool,
            job_id,
            status="completed",
            progress=1,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result={
                "scene_id": scene_id,
                "clip_url": result.get("clip_url"),
                "image_url": result.get("image_url"),
            },
        )
    except Exception as e:
        print(f"[scenes] Regen failed for {scene_id}: {e}")
        await pool.execute("UPDATE scenes SET status='failed', updated_at=now() WHERE id=$1", scene_id)
        failed_scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if failed_scene:
            await record_scene_history(
                pool,
                story=story,
                scene=failed_scene,
                event_type="scene_regen_failed",
                source_job_id=job_id,
                payload={
                    "status": failed_scene["status"],
                    "error": str(e)[:500],
                },
            )
        await update_job(
            pool,
            job_id,
            status="failed",
            current_step=f"Failed: {str(e)[:200]}",
            error=str(e)[:1000],
            completed_at=datetime.utcnow(),
        )
        raise


async def run_checkpoint_audio_job(checkpoint_id: str, job_id: str, worker_id: str):
    pool = await get_pool()
    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading checkpoint")
    story = None

    try:
        checkpoint = await pool.fetchrow("SELECT * FROM story_generation_checkpoints WHERE id=$1", checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", str(checkpoint["story_id"]))
        if not story:
            raise ValueError(f"Story {checkpoint['story_id']} not found")

        rows = await pool.fetch(
            """SELECT sc.*, e.episode_number
               FROM scenes sc
               JOIN episodes e ON e.id = sc.episode_id
               WHERE e.story_id=$1
                 AND (e.episode_number > $2 OR (e.episode_number = $2 AND sc.scene_number >= $3))
                 AND (e.episode_number < $4 OR (e.episode_number = $4 AND sc.scene_number <= $5))
               ORDER BY e.episode_number ASC, sc.scene_number ASC""",
            str(checkpoint["story_id"]),
            checkpoint["start_episode_number"],
            checkpoint["start_scene_number"],
            checkpoint["end_episode_number"],
            checkpoint["end_scene_number"],
        )

        scenes = []
        for row in rows:
            meta = row["generation_metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta) if meta else {}
            meta = meta or {}
            scenes.append({
                "scene_number": row["scene_number"],
                "title": meta.get("title") or f"Scene {row['scene_number']}",
                "description": meta.get("description", row.get("prompt", "")),
                "narration": meta.get("narration") or meta.get("description") or row.get("prompt", ""),
            })

        if not scenes:
            raise ValueError(f"No scenes found for checkpoint {checkpoint_id}")

        await pool.execute(
            "UPDATE story_generation_checkpoints SET audio_status='running', updated_at=now() WHERE id=$1",
            checkpoint_id,
        )
        running_checkpoint = await pool.fetchrow("SELECT * FROM story_generation_checkpoints WHERE id=$1", checkpoint_id)
        if running_checkpoint:
            await record_checkpoint_history(
                pool,
                story=story,
                checkpoint=running_checkpoint,
                event_type="checkpoint_audio_running",
                source_job_id=job_id,
                payload={"audio_status": "running"},
            )
        await update_job(pool, job_id, current_step="Synthesizing narration audio")
        result = await synthesize_narration_audio(
            story_id=str(story["id"]),
            checkpoint_id=checkpoint_id,
            scenes=scenes,
            narration_model=checkpoint.get("narration_model"),
            narration_voice=checkpoint.get("narration_voice"),
        )

        await pool.execute(
            """UPDATE story_generation_checkpoints
               SET audio_status='completed', narration_audio_url=$2, narration_audio_manifest_url=$3,
                   narration_text=$4, narration_model=$5, narration_voice=$6, updated_at=now()
               WHERE id=$1""",
            checkpoint_id,
            result["narration_audio_url"],
            result["narration_audio_manifest_url"],
            result["narration_text"],
            result["narration_model"],
            result["narration_voice"],
        )
        completed_checkpoint = await pool.fetchrow("SELECT * FROM story_generation_checkpoints WHERE id=$1", checkpoint_id)
        if completed_checkpoint:
            await record_checkpoint_history(
                pool,
                story=story,
                checkpoint=completed_checkpoint,
                event_type="checkpoint_audio_completed",
                source_job_id=job_id,
                payload={
                    "audio_status": completed_checkpoint["audio_status"],
                    "narration_audio_url": completed_checkpoint.get("narration_audio_url"),
                    "narration_audio_manifest_url": completed_checkpoint.get("narration_audio_manifest_url"),
                },
            )

        await update_job(
            pool,
            job_id,
            status="completed",
            progress=1,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result={
                "checkpoint_id": checkpoint_id,
                "narration_audio_url": result["narration_audio_url"],
                "narration_audio_manifest_url": result["narration_audio_manifest_url"],
            },
        )
    except Exception as e:
        print(f"[audio] Narration generation failed for checkpoint {checkpoint_id}: {e}")
        await pool.execute(
            "UPDATE story_generation_checkpoints SET audio_status='failed', updated_at=now() WHERE id=$1",
            checkpoint_id,
        )
        failed_checkpoint = await pool.fetchrow("SELECT * FROM story_generation_checkpoints WHERE id=$1", checkpoint_id)
        if failed_checkpoint:
            await record_checkpoint_history(
                pool,
                story=story,
                checkpoint=failed_checkpoint,
                event_type="checkpoint_audio_failed",
                source_job_id=job_id,
                payload={
                    "audio_status": failed_checkpoint["audio_status"],
                    "error": str(e)[:500],
                },
            )
        await update_job(
            pool,
            job_id,
            status="failed",
            current_step=f"Failed: {str(e)[:200]}",
            error=str(e)[:1000],
            completed_at=datetime.utcnow(),
        )
        raise
