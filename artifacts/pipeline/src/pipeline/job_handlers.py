import json
from datetime import datetime, timedelta, timezone

from db.connection import get_pool
from job_queue import WORKLOAD_PUBLISH, WORKLOAD_STORY, enqueue_job
from pipeline.history import record_checkpoint_history, record_scene_history, record_story_history
from pipeline.character_gen import generate_character_references, get_character_embedding
from pipeline.audio_gen import synthesize_narration_audio
from pipeline.job_runtime import update_job
from pipeline.generation_coordinator import GenerationCoordinatorError, generate_with_coordinator
from pipeline.pipeline_runtime import (
    finish_pipeline_run,
    finish_pipeline_step,
    pipeline_context_binding,
    start_pipeline_run,
    start_pipeline_step,
)
from pipeline.publishers.base import PublishRequest
from pipeline.publishers.media import resolve_publish_media
from pipeline.publishers.mock import MockPublisher
from pipeline.publishers.tiktok import TikTokPublisher
from pipeline.publishers.youtube import YouTubePublisher
from pipeline.social.token_manager import get_social_token
from pipeline.social.token_store import decrypt_token
from pipeline.steps.scene_steps import complete_scene_render_step
from pipeline.versioning import (
    GENERATION_VERSION,
    IMAGE_EDIT_MODEL_NAME,
    IMAGE_EDIT_MODEL_VERSION,
    IMAGE_MODEL_NAME,
    IMAGE_MODEL_VERSION,
)


def _json_object(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value or {}


def _json_array(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = []
    return value if isinstance(value, list) else []


def _publisher_for(platform: str):
    if platform == "mock":
        return MockPublisher()
    if platform == "youtube":
        return YouTubePublisher()
    if platform == "tiktok":
        return TikTokPublisher()
    raise ValueError(f"Unsupported publish platform: {platform}")


def _next_run_at(schedule: dict) -> datetime | None:
    cadence = schedule.get("cadence") or "once"
    config = _json_object(schedule.get("cadence_config"))
    now = datetime.now(timezone.utc)
    if cadence == "once":
        return None
    if cadence == "interval_hours":
        hours = float(config.get("hours") or 24)
        return now + timedelta(hours=max(1, hours))
    if cadence == "daily":
        return now + timedelta(days=1)
    if cadence == "weekly":
        return now + timedelta(days=7)
    return None


async def run_publish_target_job(publish_target_id: str, job_id: str, worker_id: str):
    pool = await get_pool()
    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading publish target")
    run_id = None
    step_id = None
    try:
        target = await pool.fetchrow("SELECT * FROM publish_targets WHERE id=$1", publish_target_id)
        if not target:
            raise ValueError(f"Publish target {publish_target_id} not found")
        target = dict(target)
        if target["requires_approval"] and not target.get("approved_at"):
            raise ValueError("Publish target requires approval before publishing")

        account = None
        access_token = None
        if target.get("social_account_id"):
            account = await pool.fetchrow(
                "SELECT * FROM social_accounts WHERE id=$1 AND owner_id=$2 AND status='connected'",
                str(target["social_account_id"]),
                str(target["owner_id"]),
            )
            if not account:
                raise ValueError("Connected social account not found")
            # Get token (auto-refreshes if expired)
            access_token = await get_social_token(str(target["social_account_id"]))
        elif target["platform"] != "mock":
            raise ValueError(f"{target['platform']} publishing requires a connected social account")

        await update_job(pool, job_id, current_step="Resolving media asset")
        media_url = await resolve_publish_media(pool, target)
        run_id = await start_pipeline_run(
            owner_id=str(target["owner_id"]),
            story_id=str(target["story_id"]) if target.get("story_id") else None,
            job_id=job_id,
            run_type="social_publish",
            config={
                "publish_target_id": publish_target_id,
                "platform": target["platform"],
                "asset_kind": target["asset_kind"],
            },
        )
        step_id = await start_pipeline_step(
            run_id=run_id,
            story_id=str(target["story_id"]) if target.get("story_id") else None,
            episode_id=str(target["episode_id"]) if target.get("episode_id") else None,
            scene_id=str(target["scene_id"]) if target.get("scene_id") else None,
            job_id=job_id,
            step_key=f"publish:{target['platform']}",
            step_type="social_publish",
            provider=target["platform"],
            input={
                "media_url": media_url,
                "title": target["title"],
                "privacy_status": target["privacy_status"],
            },
        )

        await update_job(pool, job_id, current_step=f"Publishing to {target['platform']}")
        publisher = _publisher_for(target["platform"])
        result = await publisher.publish(PublishRequest(
            target_id=publish_target_id,
            platform=target["platform"],
            media_url=media_url,
            title=target["title"],
            description=target["description"],
            tags=_json_array(target.get("tags")),
            privacy_status=target["privacy_status"],
            metadata=_json_object(target.get("metadata")),
            access_token=access_token,
        ))
        post = await pool.fetchrow(
            """INSERT INTO publish_posts
               (publish_target_id, platform, platform_post_id, public_url, upload_session_id, status, response)
               VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)
               RETURNING *""",
            publish_target_id,
            target["platform"],
            result.platform_post_id,
            result.public_url,
            result.upload_session_id,
            result.status,
            json.dumps(result.response),
        )
        await pool.execute(
            """UPDATE publish_targets
               SET status=$2, media_url=$3, error=NULL, updated_at=now()
               WHERE id=$1""",
            publish_target_id,
            result.status,
            media_url,
        )
        await finish_pipeline_step(
            step_id,
            status="completed" if result.status in {"published", "processing"} else result.status,
            output={
                "post_id": str(post["id"]),
                "platform_post_id": result.platform_post_id,
                "public_url": result.public_url,
                "status": result.status,
            },
            provider=target["platform"],
            provider_request_id=result.platform_post_id,
        )
        await finish_pipeline_run(
            run_id,
            status="completed",
            summary={
                "publish_target_id": publish_target_id,
                "post_id": str(post["id"]),
                "platform": target["platform"],
                "status": result.status,
                "public_url": result.public_url,
            },
        )
        await update_job(
            pool,
            job_id,
            status="completed",
            progress=1,
            total_steps=1,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result={
                "publish_target_id": publish_target_id,
                "post_id": str(post["id"]),
                "public_url": result.public_url,
                "platform_status": result.status,
            },
        )
        return {"publish_target_id": publish_target_id, "post_id": str(post["id"])}
    except Exception as e:
        await pool.execute(
            "UPDATE publish_targets SET status='failed', error=$2, updated_at=now() WHERE id=$1",
            publish_target_id,
            str(e)[:1000],
        )
        if step_id:
            await finish_pipeline_step(step_id, status="failed", error=str(e))
        if run_id:
            await finish_pipeline_run(run_id, status="failed", error=str(e))
        await update_job(
            pool,
            job_id,
            status="failed",
            current_step=f"Failed: {str(e)[:200]}",
            error=str(e)[:1000],
            completed_at=datetime.utcnow(),
        )
        raise


async def run_scheduled_job(schedule_id: str, job_id: str, worker_id: str):
    pool = await get_pool()
    await update_job(pool, job_id, status="running", started_at=datetime.utcnow(), current_step="Loading schedule")
    scheduled_run = None
    try:
        schedule = await pool.fetchrow("SELECT * FROM automation_schedules WHERE id=$1", schedule_id)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")
        schedule = dict(schedule)
        if not schedule.get("enabled"):
            raise ValueError("Schedule is disabled")

        scheduled_run = await pool.fetchrow("SELECT * FROM scheduled_runs WHERE job_id=$1", job_id)
        if scheduled_run:
            scheduled_run = await pool.fetchrow(
                """UPDATE scheduled_runs
                   SET status='running', started_at=COALESCE(started_at, now()), updated_at=now()
                   WHERE id=$1
                   RETURNING *""",
                str(scheduled_run["id"]),
            )
        else:
            scheduled_run = await pool.fetchrow(
                """INSERT INTO scheduled_runs
                   (schedule_id, owner_id, story_id, job_id, run_type, due_at, status, started_at)
                   VALUES ($1,$2,$3,$4,$5,$6,'running',now())
                   RETURNING *""",
                schedule_id,
                str(schedule["owner_id"]),
                str(schedule["story_id"]) if schedule.get("story_id") else None,
                job_id,
                schedule["schedule_type"],
                schedule.get("next_run_at"),
            )
        publish_config = _json_object(schedule.get("publish_config"))
        result = {"schedule_id": schedule_id, "schedule_type": schedule["schedule_type"]}

        if schedule["schedule_type"] == "publish_existing":
            publish_target_id = publish_config.get("publish_target_id")
            if not publish_target_id:
                raise ValueError("publish_existing schedules require publish_config.publish_target_id")
            await pool.execute(
                """UPDATE publish_targets
                   SET status=CASE WHEN requires_approval AND approved_at IS NULL THEN 'pending_approval' ELSE 'queued' END,
                       publish_mode='scheduled',
                       scheduled_for=COALESCE(scheduled_for, now()),
                       updated_at=now()
                   WHERE id=$1 AND owner_id=$2""",
                publish_target_id,
                str(schedule["owner_id"]),
            )
            target = await pool.fetchrow("SELECT * FROM publish_targets WHERE id=$1", publish_target_id)
            if not target:
                raise ValueError("Publish target not found")
            if not target["requires_approval"] or target.get("approved_at"):
                publish_job_id = await pool.fetchval(
                    """INSERT INTO generation_jobs
                       (entity_type, entity_id, status, total_steps, current_step, job_type, result)
                       VALUES ('publish',$1,'pending',1,'Queued by scheduler','publish_target',$2::jsonb)
                       RETURNING id""",
                    publish_target_id,
                    json.dumps({"schedule_id": schedule_id, "scheduled_run_id": str(scheduled_run["id"])}),
                )
                await enqueue_job(str(publish_job_id), workload=WORKLOAD_PUBLISH)
                result["publish_job_id"] = str(publish_job_id)
            result["publish_target_id"] = publish_target_id

        elif schedule["schedule_type"] in {"generate_only", "generate_and_publish", "series_continuation"}:
            story_id = str(schedule["story_id"]) if schedule.get("story_id") else None
            if not story_id:
                raise ValueError(f"{schedule['schedule_type']} schedules require story_id")
            story_job_id = await pool.fetchval(
                """INSERT INTO generation_jobs
                   (entity_type, entity_id, status, total_steps, current_step, job_type, result)
                   VALUES ('story',$1,'pending',0,'Queued by scheduler','full_episode',$2::jsonb)
                   RETURNING id""",
                story_id,
                json.dumps({
                    "schedule_id": schedule_id,
                    "scheduled_run_id": str(scheduled_run["id"]),
                    "pipeline_config": _json_object(schedule.get("pipeline_config")),
                    "publish_config": publish_config if schedule["schedule_type"] == "generate_and_publish" else {},
                }),
            )
            await enqueue_job(str(story_job_id), workload=WORKLOAD_STORY)
            result["generation_job_id"] = str(story_job_id)
        else:
            raise ValueError(f"Unsupported schedule type: {schedule['schedule_type']}")

        next_run_at = _next_run_at(schedule)
        await pool.execute(
            """UPDATE automation_schedules
               SET last_run_at=now(), next_run_at=$2, enabled=CASE WHEN $2::timestamptz IS NULL THEN false ELSE enabled END,
                   last_error=NULL, updated_at=now()
               WHERE id=$1""",
            schedule_id,
            next_run_at,
        )
        await pool.execute(
            """UPDATE scheduled_runs
               SET status='completed', result=$2::jsonb, completed_at=now(), updated_at=now()
               WHERE id=$1""",
            str(scheduled_run["id"]),
            json.dumps(result),
        )
        await update_job(
            pool,
            job_id,
            status="completed",
            progress=1,
            total_steps=1,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result=result,
        )
        return result
    except Exception as e:
        await pool.execute(
            "UPDATE automation_schedules SET last_error=$2, updated_at=now() WHERE id=$1",
            schedule_id,
            str(e)[:1000],
        )
        if scheduled_run:
            await pool.execute(
                """UPDATE scheduled_runs
                   SET status='failed', error=$2, completed_at=now(), updated_at=now()
                   WHERE id=$1""",
                str(scheduled_run["id"]),
                str(e)[:1000],
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
    run_id: str | None = None
    render_step_id: str | None = None

    try:
        scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found")

        episode = await pool.fetchrow("SELECT * FROM episodes WHERE id=$1", scene["episode_id"])
        if not episode:
            raise ValueError(f"Episode {scene['episode_id']} not found")

        story_row = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", episode["story_id"])
        if not story_row:
            raise ValueError(f"Story {episode['story_id']} not found")
        story = dict(story_row)
        story_dict = story
        workflow_state = story_dict.get("workflow_state")
        if isinstance(workflow_state, str):
            try:
                workflow_state = json.loads(workflow_state)
            except Exception:
                workflow_state = {}
        run_id = await start_pipeline_run(
            owner_id=str(story_dict["owner_id"]) if story_dict.get("owner_id") else None,
            story_id=str(story["id"]),
            job_id=job_id,
            run_type="scene_regeneration",
            config={
                "scene_id": scene_id,
                "episode_id": str(episode["id"]),
                "workflow_type": story_dict.get("workflow_type"),
                "generation_version": story_dict.get("generation_version"),
                "workflow_state": workflow_state if isinstance(workflow_state, dict) else {},
            },
        )
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

        await _sync_scene_characters(
            pool,
            str(scene_id),
            str(story["id"]),
            [name for name in scene_plan.get("characters_present", []) if name],
        )

        await update_job(
            pool,
            job_id,
            current_step="Generating new image scene" if is_narrated_image_story else "Generating new video clip",
        )
        render_step_id = await start_pipeline_step(
            run_id=run_id,
            story_id=str(story["id"]),
            episode_id=str(episode["id"]),
            scene_id=scene_id,
            job_id=job_id,
            step_key=f"regenerate_scene:{ep_num}:{scene_num}",
            step_type="scene_render",
            input={
                "episode_number": ep_num,
                "scene_number": scene_num,
                "media_kind": "image" if is_narrated_image_story else "video",
                "character_ref_count": len(char_refs),
            },
        )
        async with pipeline_context_binding(run_id=run_id, step_id=render_step_id):
            result, generation_plan = await generate_with_coordinator(
                story=story,
                episode_id=str(episode["id"]),
                scene=scene_plan,
                story_context=plan,
                character_refs=char_refs,
                previous_exit_frame_url=None,
                previous_scene_image_url=None,
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
            "video_provider": result.get("video_provider"),
            "generation_coordinator": generation_plan.model_dump(),
        }
        regen_count = (scene.get("regeneration_count") or 0) + 1
        if is_narrated_image_story:
            scene_state = {
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
                "video_provider": result.get("video_provider"),
                "generation_coordinator": generation_plan.model_dump(),
            }
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
                json.dumps(scene_state),
                scene_id,
            )
        else:
            scene_state = {
                "story_id": str(story["id"]),
                "episode_id": str(episode["id"]),
                "scene_id": scene_id,
                "generation_version": story.get("generation_version", GENERATION_VERSION),
                "clip_url": result.get("clip_url"),
                "media_url": result.get("clip_url"),
                "video_provider": result.get("video_provider"),
                "generation_coordinator": generation_plan.model_dump(),
            }
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
                json.dumps(scene_state),
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
        if generation_plan.state_patch:
            merged_workflow_state = _merge_workflow_state(story, generation_plan.state_patch)
            await pool.execute(
                "UPDATE stories SET workflow_state=$1::jsonb, updated_at=now() WHERE id=$2",
                json.dumps(merged_workflow_state),
                str(story["id"]),
            )
        media_url = await complete_scene_render_step(
            run_id=run_id,
            step_id=render_step_id,
            story_id=str(story["id"]),
            episode_id=str(episode["id"]),
            scene_id=scene_id,
            result=result,
            generation_plan=generation_plan,
            episode_number=ep_num,
            scene_number=scene_num,
            default_media_kind="image" if is_narrated_image_story else "video",
            extra_metadata={"regeneration_count": regen_count},
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
        if run_id:
            await finish_pipeline_run(
                run_id,
                status="completed",
                summary={
                    "scene_id": scene_id,
                    "media_url": media_url,
                    "regeneration_count": regen_count,
                },
            )
    except GenerationCoordinatorError as e:
        print(f"[scenes] Coordinator handoff for {scene_id}: {e}")
        if render_step_id:
            await finish_pipeline_step(
                render_step_id,
                status="failed",
                error=str(e),
                output={"generation_coordinator": e.plan.model_dump() if e.plan else None},
            )
        if run_id:
            await finish_pipeline_run(run_id, status="failed", error=str(e))
        await pool.execute("UPDATE scenes SET status='failed', updated_at=now() WHERE id=$1", scene_id)
        failed_scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if failed_scene:
            await record_scene_history(
                pool,
                story=story,
                scene=failed_scene,
                event_type="scene_regen_handoff",
                source_job_id=job_id,
                payload={
                    "status": failed_scene["status"],
                    "error": str(e)[:500],
                    "generation_coordinator": e.plan.model_dump() if e.plan else None,
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
    except Exception as e:
        print(f"[scenes] Regen failed for {scene_id}: {e}")
        if render_step_id:
            await finish_pipeline_step(render_step_id, status="failed", error=str(e))
        if run_id:
            await finish_pipeline_run(run_id, status="failed", error=str(e))
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
