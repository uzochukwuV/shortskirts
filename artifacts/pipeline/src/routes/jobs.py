import json
from fastapi import APIRouter, HTTPException
from db.connection import get_pool
from models.story import GenerationJobResponse

router = APIRouter(prefix="/pipeline/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=GenerationJobResponse)
async def get_job(job_id: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM generation_jobs WHERE id=$1", job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

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
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[GenerationJobResponse])
async def list_entity_jobs(entity_type: str, entity_id: str):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM generation_jobs
           WHERE entity_type=$1 AND entity_id=$2
           ORDER BY created_at DESC LIMIT 10""",
        entity_type, entity_id,
    )
    result = []
    for row in rows:
        res = row["result"]
        if isinstance(res, str):
            res = json.loads(res)
        result.append(GenerationJobResponse(
            id=str(row["id"]),
            entity_type=row["entity_type"],
            entity_id=str(row["entity_id"]),
            status=row["status"],
            progress=row["progress"],
            total_steps=row["total_steps"],
            current_step=row["current_step"],
            error=row["error"],
            result=res,
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
        ))
    return result
