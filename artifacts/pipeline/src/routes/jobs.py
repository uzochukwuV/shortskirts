import json
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import GenerationJobResponse
from auth import get_current_user, user_id
from job_queue import enqueue_job, job_workload

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


def _metric_row(row):
    extra = row.get("extra")
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except Exception:
            extra = {}
    extra = extra or {}
    return {
        "id": str(row["id"]),
        "metric_kind": row["metric_kind"],
        "status": row["status"],
        "duration_ms": row["duration_ms"],
        "provider_latency_ms": row["provider_latency_ms"],
        "estimated_cost_usd": float(row["estimated_cost_usd"]) if row.get("estimated_cost_usd") is not None else None,
        "retries": row["retries"],
        "step_name": row["step_name"],
        "provider": row["provider"],
        "provider_task_id": row.get("provider_task_id") or extra.get("task_id") or extra.get("provider_task_id"),
        "provider_request_id": row.get("provider_request_id") or extra.get("request_id") or extra.get("provider_request_id"),
        "error": row["error"],
        "job_id": str(row["job_id"]) if row.get("job_id") else None,
        "entity_type": row["entity_type"],
        "entity_id": str(row["entity_id"]) if row.get("entity_id") else None,
        "workload": row["workload"],
        "extra": extra,
        "created_at": row["created_at"],
    }


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


@router.get("/{job_id}/metrics")
async def list_job_metrics(job_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    job = await pool.fetchrow("SELECT * FROM generation_jobs WHERE id=$1", job_id)
    if not job or not await _job_belongs_to_owner(pool, job, user_id(user)):
        raise HTTPException(status_code=404, detail="Job not found")

    rows = await pool.fetch(
        """SELECT *
           FROM pipeline_metrics
           WHERE job_id=$1
           ORDER BY created_at ASC""",
        job_id,
    )
    return [_metric_row(row) for row in rows]


@router.post("/{job_id}/cancel", response_model=GenerationJobResponse)
async def cancel_job(job_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM generation_jobs WHERE id=$1", job_id)
    if not row or not await _job_belongs_to_owner(pool, row, user_id(user)):
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] in {"completed", "failed", "canceled"}:
        return _job_response(row)

    updated = await pool.fetchrow(
        """UPDATE generation_jobs
           SET status='canceled',
               error='Canceled by user',
               completed_at=COALESCE(completed_at, now()),
               worker_id=NULL,
               lease_expires_at=NULL,
               updated_at=now()
           WHERE id=$1
           RETURNING *""",
        job_id,
    )
    return _job_response(updated)


@router.post("/{job_id}/retry", response_model=GenerationJobResponse)
async def retry_job(job_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM generation_jobs WHERE id=$1", job_id)
    if not row or not await _job_belongs_to_owner(pool, row, user_id(user)):
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] == "running":
        raise HTTPException(status_code=409, detail="Job is still running")

    updated = await pool.fetchrow(
        """UPDATE generation_jobs
           SET status='pending',
               error=NULL,
               completed_at=NULL,
               worker_id=NULL,
               leased_at=NULL,
               lease_expires_at=NULL,
               last_heartbeat_at=now(),
               current_step='Retry queued',
               updated_at=now()
           WHERE id=$1
           RETURNING *""",
        job_id,
    )
    await enqueue_job(job_id, workload=job_workload(updated["entity_type"], updated.get("job_type")))
    return _job_response(updated)
