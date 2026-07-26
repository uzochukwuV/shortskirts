"""
Scene routes — granular regeneration and approval gates.

Key endpoints:
  POST /pipeline/scenes/{id}/regenerate    — regenerate this scene's video clip in background
  PUT  /pipeline/scenes/{id}/approve       — approve this scene (human gate)
  PUT  /pipeline/scenes/{id}/reject        — reject / request redo (resets approval)
  PUT  /pipeline/scenes/{id}/lock          — lock scene so it cannot be regenerated
  GET  /pipeline/scenes/{id}               — get scene detail
"""
import json
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import (
    SceneResponse,
    GenerationJobResponse,
    HistoryEntryResponse,
    SceneCreate,
    SceneUpdate,
    SceneCharactersUpdate,
    SceneReorderRequest,
)
from job_queue import enqueue_job, WORKLOAD_MEDIA
from pipeline.history import record_scene_history
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/scenes", tags=["scenes"])


class SceneReferencesUpdate(BaseModel):
    reference_image_urls: list[str] = Field(default_factory=list)


async def _scene_belongs_to_owner(pool, scene_id: str, owner_id: str) -> bool:
    return bool(await pool.fetchval(
        """SELECT 1 FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1 AND s.owner_id=$2""",
        scene_id,
        owner_id,
    ))


# ─── Helper ───────────────────────────────────────────────────────────────────

def _json_object(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value or {}


def _scene_media_url(r, metadata: dict | None = None, snapshot: dict | None = None) -> str | None:
    metadata = _json_object(metadata if metadata is not None else r.get("generation_metadata"))
    snapshot = _json_object(snapshot if snapshot is not None else r.get("state_snapshot"))
    return (
        r.get("image_url")
        or metadata.get("image_url")
        or snapshot.get("image_url")
        or snapshot.get("media_url")
        or r.get("clip_url")
    )


def _frame_ratio_from_meta(metadata: dict | None, snapshot: dict | None, fallback: str | None = None) -> str | None:
    metadata = _json_object(metadata)
    snapshot = _json_object(snapshot)
    return (
        metadata.get("frame_ratio")
        or snapshot.get("frame_ratio")
        or snapshot.get("aspect_ratio")
        or fallback
    )


async def _load_scene_character_ids(pool, scene_id: str) -> tuple[list[str], list[str]]:
    rows = await pool.fetch(
        """SELECT character_id, is_primary
           FROM scene_characters
           WHERE scene_id=$1
           ORDER BY is_primary DESC, character_id ASC""",
        scene_id,
    )
    character_ids: list[str] = []
    primary_character_ids: list[str] = []
    for row in rows:
        character_id = str(row["character_id"])
        character_ids.append(character_id)
        if row["is_primary"]:
            primary_character_ids.append(character_id)
    return character_ids, primary_character_ids


async def _sync_scene_characters(
    pool,
    scene_id: str,
    character_ids: list[str],
    primary_character_ids: list[str] | None = None,
):
    character_ids = [str(cid) for cid in character_ids if cid]
    primary_character_ids = [str(cid) for cid in (primary_character_ids or []) if cid]
    if not character_ids:
        await pool.execute("DELETE FROM scene_characters WHERE scene_id=$1", scene_id)
        return

    scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    story = await pool.fetchrow(
        """SELECT s.*
           FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1""",
        scene_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    valid_rows = await pool.fetch(
        """SELECT c.id
           FROM characters c
           JOIN stories s ON s.id = c.story_id
           WHERE s.id=$1 AND c.id = ANY($2::uuid[])""",
        str(story["id"]),
        character_ids,
    )
    valid_ids = {str(row["id"]) for row in valid_rows}
    missing = [cid for cid in character_ids if cid not in valid_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Character not found: {missing[0]}")

    primary_ids = {cid for cid in primary_character_ids if cid in valid_ids}
    if not primary_ids and character_ids:
        primary_ids = {character_ids[0]}

    await pool.execute("DELETE FROM scene_characters WHERE scene_id=$1", scene_id)
    for cid in character_ids:
        await pool.execute(
            """INSERT INTO scene_characters (scene_id, character_id, is_primary)
               VALUES ($1, $2, $3)""",
            scene_id,
            cid,
            cid in primary_ids,
        )


def _row_to_scene(r, metadata: dict | None = None) -> SceneResponse:
    metadata = _json_object(metadata if metadata is not None else r.get("generation_metadata"))
    snapshot = _json_object(r.get("state_snapshot"))
    image_url = _scene_media_url(r, metadata=metadata, snapshot=snapshot)
    frame_ratio = _frame_ratio_from_meta(metadata, snapshot)

    return SceneResponse(
        id=str(r["id"]),
        episode_id=str(r["episode_id"]),
        scene_number=r["scene_number"],
        prompt=r["prompt"],
        clip_url=r["clip_url"],
        image_url=image_url,
        exit_frame_url=r["exit_frame_url"],
        duration=r["duration"],
        status=r["status"],
        approval_status=r.get("approval_status", "pending"),
        locked=r.get("locked", False),
        regeneration_count=r.get("regeneration_count", 0),
        generation_version=r.get("generation_version", "v1"),
        image_model=r.get("image_model"),
        image_model_version=r.get("image_model_version"),
        edit_model=r.get("edit_model"),
        edit_model_version=r.get("edit_model_version"),
        source_scene_id=str(r["source_scene_id"]) if r.get("source_scene_id") else None,
        state_snapshot=snapshot,
        character_ids=[],
        primary_character_ids=[],
        created_at=r["created_at"],
        title=metadata.get("title") or f"Scene {r['scene_number']}",
        description=metadata.get("description", ""),
        visual_prompt=metadata.get("visual_prompt") or r["prompt"],
        mood=metadata.get("mood", ""),
        location=metadata.get("location", ""),
        narration=metadata.get("narration", ""),
        media_kind=metadata.get("media_kind") or ("image" if image_url else "video"),
        frame_ratio=frame_ratio,
    )


def _history_row_to_response(row) -> HistoryEntryResponse:
    state_snapshot = row.get("state_snapshot")
    payload = row.get("payload")
    if isinstance(state_snapshot, str):
        try:
            state_snapshot = json.loads(state_snapshot)
        except Exception:
            state_snapshot = None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = None
    return HistoryEntryResponse(
        id=str(row["id"]),
        entity_type="scene",
        entity_id=str(row["scene_id"]),
        revision=row["revision"],
        event_type=row["event_type"],
        generation_version=row.get("generation_version", "v1"),
        source_job_id=str(row["source_job_id"]) if row.get("source_job_id") else None,
        state_snapshot=state_snapshot,
        payload=payload,
        created_at=row["created_at"],
    )


# ─── Get scene ────────────────────────────────────────────────────────────────

@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    scene = _row_to_scene(row)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


@router.post("", response_model=SceneResponse)
async def create_scene(body: SceneCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    episode = await pool.fetchrow(
        """SELECT e.*, s.owner_id, s.workflow_state, s.workflow_type, s.style
           FROM episodes e
           JOIN stories s ON s.id = e.story_id
           WHERE e.id=$1 AND s.owner_id=$2""",
        body.episode_id,
        user_id(user),
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    metadata = {
        "title": body.title or f"Scene {body.scene_number}",
        "description": body.description or "",
        "visual_prompt": body.visual_prompt or body.prompt,
        "mood": body.mood or "",
        "location": body.location or "",
        "action": body.action or "",
        "narration": body.narration or "",
        "duration_seconds": body.duration,
        "media_kind": body.media_kind,
        "frame_ratio": body.frame_ratio or _json_object(episode.get("workflow_state")).get("frame_ratio", "16:9"),
        "characters_present": body.character_ids,
    }
    snapshot = {
        "story_id": str(episode["story_id"]),
        "episode_id": str(episode["id"]),
        "scene_number": body.scene_number,
        "frame_ratio": metadata["frame_ratio"],
        "media_kind": body.media_kind,
    }
    row = await pool.fetchrow(
        """INSERT INTO scenes
           (episode_id, scene_number, prompt, status, approval_status, duration,
            generation_metadata, state_snapshot)
           VALUES ($1, $2, $3, 'pending', 'pending', $4, $5::jsonb, $6::jsonb)
           RETURNING *""",
        body.episode_id,
        body.scene_number,
        body.prompt,
        body.duration,
        json.dumps(metadata),
        json.dumps(snapshot),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create scene")

    await _sync_scene_characters(pool, str(row["id"]), body.character_ids, body.character_ids[:1])
    if body.reference_image_urls:
        await pool.execute(
            """UPDATE scenes
               SET state_snapshot = jsonb_set(state_snapshot, '{reference_image_urls}', $2::jsonb, true),
                   updated_at = now()
               WHERE id=$1""",
            str(row["id"]),
            json.dumps([u for u in body.reference_image_urls if u]),
        )

    if body.generate:
        job_row = await pool.fetchrow(
            """INSERT INTO generation_jobs
               (entity_type, entity_id, status, total_steps, current_step, job_type)
               VALUES ('scene', $1, 'pending', 1, 'Queued', 'scene_regen')
               RETURNING *""",
            str(row["id"]),
        )
        await enqueue_job(str(job_row["id"]), workload=WORKLOAD_MEDIA)
        await pool.execute(
            "UPDATE scenes SET status='running', updated_at=now() WHERE id=$1",
            str(row["id"]),
        )
        row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", str(row["id"]))

    scene = _row_to_scene(row)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, str(row["id"]))
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


# ─── Approve scene ────────────────────────────────────────────────────────────

@router.put("/{scene_id}/approve", response_model=SceneResponse)
async def approve_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow(
        """UPDATE scenes
           SET approval_status='approved', approved_at=now(), updated_at=now()
           WHERE id=$1 RETURNING *""",
        scene_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    await record_scene_history(
        pool,
        story=await pool.fetchrow(
            """SELECT s.* FROM scenes sc
               JOIN episodes e ON e.id = sc.episode_id
               JOIN stories s ON s.id = e.story_id
               WHERE sc.id=$1""",
            scene_id,
        ),
        scene=row,
        event_type="scene_approved",
        payload={
            "status": row["status"],
            "approval_status": row.get("approval_status"),
        },
    )
    scene = _row_to_scene(row)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


# ─── Reject scene ─────────────────────────────────────────────────────────────

@router.put("/{scene_id}/reject", response_model=SceneResponse)
async def reject_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow(
        """UPDATE scenes
           SET approval_status='rejected', approved_at=NULL, updated_at=now()
           WHERE id=$1 RETURNING *""",
        scene_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    await record_scene_history(
        pool,
        story=await pool.fetchrow(
            """SELECT s.* FROM scenes sc
               JOIN episodes e ON e.id = sc.episode_id
               JOIN stories s ON s.id = e.story_id
               WHERE sc.id=$1""",
            scene_id,
        ),
        scene=row,
        event_type="scene_rejected",
        payload={
            "status": row["status"],
            "approval_status": row.get("approval_status"),
        },
    )
    scene = _row_to_scene(row)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


# ─── Lock scene ───────────────────────────────────────────────────────────────

@router.put("/{scene_id}/lock", response_model=SceneResponse)
async def lock_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow(
        "UPDATE scenes SET locked=true, updated_at=now() WHERE id=$1 RETURNING *",
        scene_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    await record_scene_history(
        pool,
        story=await pool.fetchrow(
            """SELECT s.* FROM scenes sc
               JOIN episodes e ON e.id = sc.episode_id
               JOIN stories s ON s.id = e.story_id
               WHERE sc.id=$1""",
            scene_id,
        ),
        scene=row,
        event_type="scene_locked",
        payload={"locked": True},
    )
    scene = _row_to_scene(row)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


@router.put("/{scene_id}/unlock", response_model=SceneResponse)
async def unlock_scene(scene_id: str, user=Depends(get_current_user)):
    """Unlock a scene so it can be regenerated."""
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow(
        "UPDATE scenes SET locked=false, updated_at=now() WHERE id=$1 RETURNING *",
        scene_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    await record_scene_history(
        pool,
        story=await pool.fetchrow(
            """SELECT s.* FROM scenes sc
               JOIN episodes e ON e.id = sc.episode_id
               JOIN stories s ON s.id = e.story_id
               WHERE sc.id=$1""",
            scene_id,
        ),
        scene=row,
        event_type="scene_unlocked",
        payload={"locked": False},
    )
    scene = _row_to_scene(row)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


@router.put("/{scene_id}", response_model=SceneResponse)
async def update_scene(scene_id: str, body: SceneUpdate, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")

    row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    metadata = _json_object(row.get("generation_metadata"))
    snapshot = _json_object(row.get("state_snapshot"))

    if body.title is not None:
        metadata["title"] = body.title
    if body.description is not None:
        metadata["description"] = body.description
    if body.visual_prompt is not None:
        metadata["visual_prompt"] = body.visual_prompt
    if body.mood is not None:
        metadata["mood"] = body.mood
    if body.location is not None:
        metadata["location"] = body.location
    if body.action is not None:
        metadata["action"] = body.action
    if body.narration is not None:
        metadata["narration"] = body.narration
    if body.duration is not None:
        metadata["duration_seconds"] = body.duration
    if body.media_kind is not None:
        metadata["media_kind"] = body.media_kind
    if body.frame_ratio is not None:
        metadata["frame_ratio"] = body.frame_ratio
        snapshot["frame_ratio"] = body.frame_ratio
    if body.reference_image_urls is not None:
        snapshot["reference_image_urls"] = [u for u in body.reference_image_urls if u]

    updated = await pool.fetchrow(
        """UPDATE scenes
           SET scene_number=COALESCE($2, scene_number),
               prompt=COALESCE($3, prompt),
               duration=COALESCE($4, duration),
               approval_status=COALESCE($5, approval_status),
               locked=COALESCE($6, locked),
               generation_metadata=$7::jsonb,
               state_snapshot=$8::jsonb,
               updated_at=now()
           WHERE id=$1
           RETURNING *""",
        scene_id,
        body.scene_number,
        body.prompt,
        body.duration,
        body.approval_status,
        body.locked,
        json.dumps(metadata),
        json.dumps(snapshot),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Scene not found")

    if body.character_ids is not None or body.primary_character_ids is not None:
        current_character_ids, current_primary_character_ids = await _load_scene_character_ids(pool, scene_id)
        next_character_ids = body.character_ids if body.character_ids is not None else current_character_ids
        next_primary_character_ids = (
            body.primary_character_ids
            if body.primary_character_ids is not None
            else current_primary_character_ids
        )
        await _sync_scene_characters(pool, scene_id, next_character_ids, next_primary_character_ids)

    story = await pool.fetchrow(
        """SELECT s.* FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1""",
        scene_id,
    )
    if story:
        await record_scene_history(
            pool,
            story=story,
            scene=updated,
            event_type="scene_updated",
            payload={
                "scene_number": updated["scene_number"],
                "approval_status": updated.get("approval_status"),
            },
        )
    scene = _row_to_scene(updated)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


@router.put("/{scene_id}/characters", response_model=SceneResponse)
async def update_scene_characters(scene_id: str, body: SceneCharactersUpdate, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    await _sync_scene_characters(pool, scene_id, body.character_ids, body.primary_character_ids)
    row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    scene = _row_to_scene(row)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


@router.post("/{scene_id}/reorder", response_model=SceneResponse)
async def reorder_scene(scene_id: str, body: SceneReorderRequest, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")

    scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    current_number = int(scene["scene_number"])
    target_number = int(body.new_scene_number)
    if current_number == target_number:
        loaded = _row_to_scene(scene)
        character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
        loaded.character_ids = character_ids
        loaded.primary_character_ids = primary_character_ids
        return loaded

    episode_id = str(scene["episode_id"])
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE scenes SET scene_number=0, updated_at=now() WHERE id=$1",
                scene_id,
            )
            if target_number < current_number:
                await conn.execute(
                    """UPDATE scenes
                       SET scene_number = scene_number + 1, updated_at=now()
                       WHERE episode_id=$1 AND scene_number >= $2 AND scene_number < $3""",
                    episode_id,
                    target_number,
                    current_number,
                )
            else:
                await conn.execute(
                    """UPDATE scenes
                       SET scene_number = scene_number - 1, updated_at=now()
                       WHERE episode_id=$1 AND scene_number > $2 AND scene_number <= $3""",
                    episode_id,
                    current_number,
                    target_number,
                )
            updated = await conn.fetchrow(
                "UPDATE scenes SET scene_number=$2, updated_at=now() WHERE id=$1 RETURNING *",
                scene_id,
                target_number,
            )
    if not updated:
        raise HTTPException(status_code=404, detail="Scene not found")

    loaded = _row_to_scene(updated)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    loaded.character_ids = character_ids
    loaded.primary_character_ids = primary_character_ids
    return loaded


@router.delete("/{scene_id}", status_code=204)
async def delete_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    if scene.get("locked"):
        raise HTTPException(status_code=409, detail="Scene is locked and cannot be deleted")
    await pool.execute("DELETE FROM scenes WHERE id=$1", scene_id)
    return None


@router.put("/{scene_id}/references", response_model=SceneResponse)
async def update_scene_references(
    scene_id: str,
    body: SceneReferencesUpdate,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")

    row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")

    snapshot = row.get("state_snapshot") or {}
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except Exception:
            snapshot = {}
    snapshot = dict(snapshot or {})
    snapshot["reference_image_urls"] = [u for u in body.reference_image_urls if u]

    updated = await pool.fetchrow(
        """UPDATE scenes
           SET state_snapshot=$2::jsonb, updated_at=now()
           WHERE id=$1
           RETURNING *""",
        scene_id,
        json.dumps(snapshot),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Scene not found")

    story = await pool.fetchrow(
        """SELECT s.* FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1""",
        scene_id,
    )
    if story:
        await record_scene_history(
            pool,
            story=story,
            scene=updated,
            event_type="scene_references_updated",
            payload={
                "reference_image_count": len(snapshot["reference_image_urls"]),
            },
        )
    scene = _row_to_scene(updated)
    character_ids, primary_character_ids = await _load_scene_character_ids(pool, scene_id)
    scene.character_ids = character_ids
    scene.primary_character_ids = primary_character_ids
    return scene


# ─── Regenerate scene ────────────────────────────────────────────────────────

@router.post("/{scene_id}/regenerate", response_model=GenerationJobResponse)
async def regenerate_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")

    scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    if scene.get("locked"):
        raise HTTPException(status_code=409, detail="Scene is locked and cannot be regenerated")

    # Use atomic conditional UPDATE to prevent race condition
    # Only update if status is not 'running' and scene is not locked
    updated = await pool.fetchrow(
        """UPDATE scenes 
           SET status='running', approval_status='pending', updated_at=now() 
           WHERE id=$1 AND status != 'running' AND (locked IS NULL OR locked = false)
           RETURNING *""",
        scene_id,
    )
    
    if not updated:
        # Check why it wasn't updated to give proper error message
        current_scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        if current_scene and current_scene.get("status") == "running":
            raise HTTPException(status_code=409, detail="Scene generation already in progress")
        raise HTTPException(status_code=409, detail="Scene cannot be regenerated")

    # Create a tracking job
    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('scene', $1, 'pending', 1, 'Queued for regeneration', 'scene_regen')
           RETURNING *""",
        scene_id,
    )
    job_id = str(job_row["id"])
    story = await pool.fetchrow(
        """SELECT s.* FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1""",
        scene_id,
    )
    if story and updated:
        await record_scene_history(
            pool,
            story=story,
            scene=updated,
            event_type="scene_regen_queued",
            source_job_id=job_id,
            payload={"status": updated["status"], "approval_status": updated.get("approval_status")},
        )
    await enqueue_job(job_id, workload=WORKLOAD_MEDIA)

    return GenerationJobResponse(
        id=job_id,
        entity_type="scene",
        entity_id=scene_id,
        status="pending",
        progress=0,
        total_steps=1,
        current_step="Queued for regeneration",
        job_type="scene_regen",
        created_at=job_row["created_at"],
    )


@router.get("/{scene_id}/history", response_model=list[HistoryEntryResponse])
async def get_scene_history(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    rows = await pool.fetch(
        """SELECT * FROM scene_history
           WHERE scene_id=$1
           ORDER BY revision ASC, created_at ASC""",
        scene_id,
    )
    return [_history_row_to_response(row) for row in rows]
