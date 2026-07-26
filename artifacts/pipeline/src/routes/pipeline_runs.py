import json

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, user_id
from db.connection import get_pool
from job_queue import WORKLOAD_MEDIA, enqueue_job
from models.pipeline import (
    PipelineArtifactResponse,
    PipelineRunDetailResponse,
    PipelineRunResponse,
    PipelineStepResponse,
)
from models.story import GenerationJobResponse

router = APIRouter(prefix="/pipeline/runs", tags=["pipeline-runs"])


def _json_object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _run_response(row) -> PipelineRunResponse:
    return PipelineRunResponse(
        id=str(row["id"]),
        owner_id=str(row["owner_id"]) if row.get("owner_id") else None,
        story_id=str(row["story_id"]) if row.get("story_id") else None,
        job_id=str(row["job_id"]) if row.get("job_id") else None,
        run_type=row["run_type"],
        status=row["status"],
        config=_json_object(row["config"]),
        summary=_json_object(row["summary"]),
        error=row.get("error"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        created_at=row["created_at"],
        updated_at=row.get("updated_at"),
    )


def _step_response(row) -> PipelineStepResponse:
    return PipelineStepResponse(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        parent_step_id=str(row["parent_step_id"]) if row.get("parent_step_id") else None,
        story_id=str(row["story_id"]) if row.get("story_id") else None,
        episode_id=str(row["episode_id"]) if row.get("episode_id") else None,
        scene_id=str(row["scene_id"]) if row.get("scene_id") else None,
        job_id=str(row["job_id"]) if row.get("job_id") else None,
        step_key=row["step_key"],
        step_type=row["step_type"],
        status=row["status"],
        attempt=row.get("attempt") or 1,
        provider=row.get("provider"),
        provider_model=row.get("provider_model"),
        provider_task_id=row.get("provider_task_id"),
        provider_request_id=row.get("provider_request_id"),
        input=_json_object(row["input"]),
        output=_json_object(row["output"]),
        error=row.get("error"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        created_at=row["created_at"],
        updated_at=row.get("updated_at"),
    )


def _artifact_response(row) -> PipelineArtifactResponse:
    content = row.get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except Exception:
            content = None
    return PipelineArtifactResponse(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        step_id=str(row["step_id"]) if row.get("step_id") else None,
        story_id=str(row["story_id"]) if row.get("story_id") else None,
        episode_id=str(row["episode_id"]) if row.get("episode_id") else None,
        scene_id=str(row["scene_id"]) if row.get("scene_id") else None,
        artifact_type=row["artifact_type"],
        media_kind=row.get("media_kind"),
        url=row.get("url"),
        content=content if isinstance(content, dict) else None,
        metadata=_json_object(row["metadata"]),
        created_at=row["created_at"],
    )


async def _run_for_owner(pool, run_id: str, owner_id: str):
    return await pool.fetchrow(
        """SELECT pr.*
           FROM pipeline_runs pr
           LEFT JOIN stories s ON s.id = pr.story_id
           WHERE pr.id=$1
             AND (pr.owner_id=$2 OR s.owner_id=$2)""",
        run_id,
        owner_id,
    )


@router.get("/story/{story_id}", response_model=list[PipelineRunResponse])
async def list_story_runs(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    owner = user_id(user)
    story = await pool.fetchrow("SELECT id FROM stories WHERE id=$1 AND owner_id=$2", story_id, owner)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    rows = await pool.fetch(
        """SELECT *
           FROM pipeline_runs
           WHERE story_id=$1
           ORDER BY created_at DESC
           LIMIT 25""",
        story_id,
    )
    return [_run_response(row) for row in rows]


@router.get("/{run_id}", response_model=PipelineRunDetailResponse)
async def get_pipeline_run(run_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await _run_for_owner(pool, run_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    steps = await pool.fetch(
        "SELECT * FROM pipeline_steps WHERE run_id=$1 ORDER BY created_at ASC",
        run_id,
    )
    artifacts = await pool.fetch(
        "SELECT * FROM pipeline_artifacts WHERE run_id=$1 ORDER BY created_at ASC",
        run_id,
    )
    return PipelineRunDetailResponse(
        run=_run_response(row),
        steps=[_step_response(step) for step in steps],
        artifacts=[_artifact_response(artifact) for artifact in artifacts],
    )


@router.get("/{run_id}/steps", response_model=list[PipelineStepResponse])
async def list_pipeline_steps(run_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await _run_for_owner(pool, run_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    steps = await pool.fetch(
        "SELECT * FROM pipeline_steps WHERE run_id=$1 ORDER BY created_at ASC",
        run_id,
    )
    return [_step_response(step) for step in steps]


@router.get("/{run_id}/artifacts", response_model=list[PipelineArtifactResponse])
async def list_pipeline_artifacts(run_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await _run_for_owner(pool, run_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    artifacts = await pool.fetch(
        "SELECT * FROM pipeline_artifacts WHERE run_id=$1 ORDER BY created_at ASC",
        run_id,
    )
    return [_artifact_response(artifact) for artifact in artifacts]


@router.get("/steps/{step_id}", response_model=PipelineStepResponse)
async def get_pipeline_step(step_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT ps.*
           FROM pipeline_steps ps
           JOIN pipeline_runs pr ON pr.id = ps.run_id
           LEFT JOIN stories s ON s.id = pr.story_id
           WHERE ps.id=$1
             AND (pr.owner_id=$2 OR s.owner_id=$2)""",
        step_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline step not found")
    return _step_response(row)


@router.post("/steps/{step_id}/retry", response_model=GenerationJobResponse)
async def retry_pipeline_step(step_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    owner = user_id(user)
    row = await pool.fetchrow(
        """SELECT
             ps.*,
             COALESCE(ps.scene_id, parent.scene_id) AS retry_scene_id
           FROM pipeline_steps ps
           LEFT JOIN pipeline_steps parent ON parent.id = ps.parent_step_id
           JOIN pipeline_runs pr ON pr.id = ps.run_id
           LEFT JOIN stories s ON s.id = pr.story_id
           WHERE ps.id=$1
             AND (pr.owner_id=$2 OR s.owner_id=$2)""",
        step_id,
        owner,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline step not found")
    scene_id = row.get("retry_scene_id")
    if not scene_id:
        raise HTTPException(status_code=400, detail="Only scene render/provider steps can be retried right now")
    if row["status"] not in {"failed", "retryable"}:
        raise HTTPException(status_code=409, detail="Only failed or retryable steps can be retried")

    scene = await pool.fetchrow(
        """SELECT sc.*
           FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1 AND s.owner_id=$2""",
        str(scene_id),
        owner,
    )
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    if scene.get("locked"):
        raise HTTPException(status_code=409, detail="Scene is locked and cannot be regenerated")

    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type, result)
           VALUES ('scene', $1, 'pending', 1, 'Queued from pipeline retry', 'scene_regen', $2::jsonb)
           RETURNING *""",
        str(scene_id),
        json.dumps({"retry_step_id": step_id}),
    )
    job_id = str(job_row["id"])
    await enqueue_job(job_id, workload=WORKLOAD_MEDIA)
    return GenerationJobResponse(
        id=job_id,
        entity_type="scene",
        entity_id=str(scene_id),
        status="pending",
        progress=0,
        total_steps=1,
        current_step="Queued from pipeline retry",
        job_type="scene_regen",
        created_at=job_row["created_at"],
    )


@router.post("/{run_id}/cancel", response_model=PipelineRunDetailResponse)
async def cancel_pipeline_run(run_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    owner = user_id(user)
    row = await _run_for_owner(pool, run_id, owner)
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if row["status"] in {"completed", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail=f"Pipeline run is already {row['status']}")
    await pool.execute(
        """UPDATE pipeline_runs
           SET status='canceled', error='Canceled by user', completed_at=now(), updated_at=now()
           WHERE id=$1""",
        run_id,
    )
    if row.get("job_id"):
        await pool.execute(
            """UPDATE generation_jobs
               SET status='canceled', error='Canceled by user', completed_at=now(),
                   lease_expires_at=NULL, updated_at=now()
               WHERE id=$1 AND status IN ('pending','running','retrying')""",
            str(row["job_id"]),
        )
    return await get_pipeline_run(run_id, user)
