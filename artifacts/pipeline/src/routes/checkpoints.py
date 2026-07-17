import json
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, user_id
from db.connection import get_pool
from models.story import GenerationCheckpointResponse, HistoryEntryResponse
from job_queue import enqueue_job, WORKLOAD_STORY
from pipeline.history import record_checkpoint_history, record_story_history

router = APIRouter(prefix="/pipeline/stories", tags=["checkpoints"])


def _row_to_checkpoint(row) -> GenerationCheckpointResponse:
    resume_state = row.get("resume_state")
    if isinstance(resume_state, str):
        try:
            resume_state = json.loads(resume_state)
        except Exception:
            resume_state = None
    return GenerationCheckpointResponse(
        id=str(row["id"]),
        story_id=str(row["story_id"]),
        job_id=str(row["job_id"]) if row.get("job_id") else None,
        resume_job_id=str(row["resume_job_id"]) if row.get("resume_job_id") else None,
        batch_number=row.get("batch_number", 1),
        batch_size=row.get("batch_size", 3),
        start_episode_number=row.get("start_episode_number", 1),
        start_scene_number=row.get("start_scene_number", 1),
        end_episode_number=row.get("end_episode_number", 1),
        end_scene_number=row.get("end_scene_number", 1),
        status=row.get("status", "pending_review"),
        generation_version=row.get("generation_version", "v1"),
        narration_model=row.get("narration_model"),
        narration_voice=row.get("narration_voice"),
        narration_text=row.get("narration_text"),
        audio_job_id=str(row["audio_job_id"]) if row.get("audio_job_id") else None,
        audio_status=row.get("audio_status"),
        narration_audio_url=row.get("narration_audio_url"),
        narration_audio_manifest_url=row.get("narration_audio_manifest_url"),
        state_snapshot=row.get("state_snapshot"),
        resume_state=resume_state,
        reviewer_notes=row.get("reviewer_notes"),
        approved_at=row.get("approved_at"),
        reviewed_at=row.get("reviewed_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
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
        entity_type="checkpoint",
        entity_id=str(row["checkpoint_id"]),
        revision=row["revision"],
        event_type=row["event_type"],
        generation_version=row.get("generation_version", "v1"),
        source_job_id=str(row["source_job_id"]) if row.get("source_job_id") else None,
        state_snapshot=state_snapshot,
        payload=payload,
        created_at=row["created_at"],
    )


async def _checkpoint_belongs_to_owner(pool, checkpoint_id: str, owner_id: str) -> bool:
    return bool(await pool.fetchval(
        """SELECT 1 FROM story_generation_checkpoints c
           JOIN stories s ON s.id = c.story_id
           WHERE c.id=$1 AND s.owner_id=$2""",
        checkpoint_id,
        owner_id,
    ))


@router.get("/{story_id}/checkpoints", response_model=list[GenerationCheckpointResponse])
async def list_story_checkpoints(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT c.*
           FROM story_generation_checkpoints c
           JOIN stories s ON s.id = c.story_id
           WHERE c.story_id=$1 AND s.owner_id=$2
           ORDER BY c.created_at DESC""",
        story_id,
        user_id(user),
    )
    return [_row_to_checkpoint(row) for row in rows]


@router.put("/{story_id}/checkpoints/{checkpoint_id}/approve", response_model=GenerationCheckpointResponse)
async def approve_story_checkpoint(story_id: str, checkpoint_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    checkpoint = await pool.fetchrow(
        """SELECT c.*
           FROM story_generation_checkpoints c
           JOIN stories s ON s.id = c.story_id
           WHERE c.id=$1 AND c.story_id=$2 AND s.owner_id=$3""",
        checkpoint_id,
        story_id,
        user_id(user),
    )
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    if checkpoint.get("status") == "approved":
        return _row_to_checkpoint(checkpoint)
    if not checkpoint.get("resume_job_id"):
        raise HTTPException(status_code=409, detail="Checkpoint does not have a pending resume job")
    if checkpoint.get("audio_status") in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="Checkpoint narration audio is still processing")

    await pool.execute(
        """UPDATE story_generation_checkpoints
           SET status='approved', approved_at=now(), reviewed_at=now(), updated_at=now()
           WHERE id=$1""",
        checkpoint_id,
    )
    await pool.execute(
        "UPDATE stories SET status='generating', updated_at=now() WHERE id=$1",
        story_id,
    )
    story_row = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
    if story_row:
        await record_story_history(
            pool,
            story=story_row,
            event_type="checkpoint_approved_story_resumed",
            payload={"status": story_row["status"], "checkpoint_id": checkpoint_id},
        )
    story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
    checkpoint_row = await pool.fetchrow("SELECT * FROM story_generation_checkpoints WHERE id=$1", checkpoint_id)
    if story and checkpoint_row:
        await record_checkpoint_history(
            pool,
            story=story,
            checkpoint=checkpoint_row,
            event_type="checkpoint_approved",
            source_job_id=str(checkpoint_row["resume_job_id"]) if checkpoint_row.get("resume_job_id") else None,
            payload={
                "status": checkpoint_row["status"],
                "audio_status": checkpoint_row.get("audio_status"),
                "approved_at": checkpoint_row.get("approved_at"),
            },
        )
    await enqueue_job(str(checkpoint["resume_job_id"]), workload=WORKLOAD_STORY)
    updated = await pool.fetchrow("SELECT * FROM story_generation_checkpoints WHERE id=$1", checkpoint_id)
    return _row_to_checkpoint(updated)


@router.get("/{story_id}/checkpoints/{checkpoint_id}/history", response_model=list[HistoryEntryResponse])
async def get_checkpoint_history(story_id: str, checkpoint_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    checkpoint = await pool.fetchrow(
        """SELECT c.*
           FROM story_generation_checkpoints c
           JOIN stories s ON s.id = c.story_id
           WHERE c.id=$1 AND c.story_id=$2 AND s.owner_id=$3""",
        checkpoint_id,
        story_id,
        user_id(user),
    )
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    rows = await pool.fetch(
        """SELECT * FROM checkpoint_history
           WHERE checkpoint_id=$1
           ORDER BY revision ASC, created_at ASC""",
        checkpoint_id,
    )
    return [_history_row_to_response(row) for row in rows]
