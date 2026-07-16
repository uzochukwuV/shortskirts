import json
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import GenerationJobResponse
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/jobs", tags=["jobs"])


def _job_response(row) -> GenerationJobResponse:
    result = row["result"]
    if isinstance(result, str):
        result = json.loads(result)
    return GenerationJobResponse(
        id=str(row["id"]),
        entity_type=row["entity_type"],
        entity_id=str(row["entity_id"]),
        status=row["status"],
        progress=row["progress"],
        total_steps=row["total_steps"],
        current_step=row["current_step"],
        error=row["error"],
        result=result,
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
        job_type=row.get("job_type", "full_episode"),
        attempts=row.get("attempts", 0),
        max_attempts=row.get("max_attempts", 3),
        worker_id=row.get("worker_id"),
        leased_at=row.get("leased_at"),
        lease_expires_at=row.get("lease_expires_at"),
        last_heartbeat_at=row.get("last_heartbeat_at"),
        updated_at=row.get("updated_at"),
    )


async def _job_belongs_to_owner(pool, row, owner_id: str) -> bool:
    entity_type = row["entity_type"]
    entity_id = str(row["entity_id"])
    if entity_type == "story":
        found = await pool.fetchval(
            "SELECT 1 FROM stories WHERE id=$1 AND owner_id=$2",
            entity_id,
            owner_id,
        )
    elif entity_type == "character":
        found = await pool.fetchval(
            """SELECT 1 FROM characters c
               JOIN stories s ON s.id = c.story_id
               WHERE c.id=$1 AND s.owner_id=$2""",
            entity_id,
            owner_id,
        )
    elif entity_type == "scene":
        found = await pool.fetchval(
            """SELECT 1 FROM scenes sc
               JOIN episodes e ON e.id = sc.episode_id
               JOIN stories s ON s.id = e.story_id
               WHERE sc.id=$1 AND s.owner_id=$2""",
            entity_id,
            owner_id,
        )
    else:
        found = None
    return bool(found)


@router.get("/{job_id}", response_model=GenerationJobResponse)
async def get_job(job_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM generation_jobs WHERE id=$1", job_id)
    if not row or not await _job_belongs_to_owner(pool, row, user_id(user)):
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(row)


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[GenerationJobResponse])
async def list_entity_jobs(entity_type: str, entity_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM generation_jobs
           WHERE entity_type=$1 AND entity_id=$2
           ORDER BY created_at DESC LIMIT 10""",
        entity_type,
        entity_id,
    )
    result = []
    owner_id = user_id(user)
    for row in rows:
        if await _job_belongs_to_owner(pool, row, owner_id):
            result.append(_job_response(row))
    return result
