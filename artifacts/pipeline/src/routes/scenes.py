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
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import SceneResponse, GenerationJobResponse, HistoryEntryResponse
from job_queue import enqueue_job, WORKLOAD_MEDIA
from pipeline.history import record_scene_history
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/scenes", tags=["scenes"])
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

def _row_to_scene(r, metadata: dict | None = None) -> SceneResponse:
    if metadata is None:
        metadata = r.get("generation_metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

    return SceneResponse(
        id=str(r["id"]),
        episode_id=str(r["episode_id"]),
        scene_number=r["scene_number"],
        prompt=r["prompt"],
        clip_url=r["clip_url"],
        image_url=r.get("image_url"),
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
        state_snapshot=r.get("state_snapshot"),
        created_at=r["created_at"],
        title=metadata.get("title") or f"Scene {r['scene_number']}",
        description=metadata.get("description", ""),
        visual_prompt=metadata.get("visual_prompt") or r["prompt"],
        mood=metadata.get("mood", ""),
        location=metadata.get("location", ""),
        narration=metadata.get("narration", ""),
        media_kind=metadata.get("media_kind") or ("image" if r.get("image_url") else "video"),
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
    return _row_to_scene(row)


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
    return _row_to_scene(row)


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
    return _row_to_scene(row)


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
    return _row_to_scene(row)


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

    if scene.get("status") == "running":
        raise HTTPException(status_code=409, detail="Scene generation already in progress")

    # Create a tracking job
    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('scene', $1, 'pending', 1, 'Queued for regeneration', 'scene_regen')
           RETURNING *""",
        scene_id,
    )
    job_id = str(job_row["id"])

    await pool.execute(
        "UPDATE scenes SET status='running', approval_status='pending', updated_at=now() WHERE id=$1",
        scene_id,
    )
    updated = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
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
