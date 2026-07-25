from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, user_id
from db.connection import get_pool
from job_queue import WORKLOAD_SCHEDULER, enqueue_job
from models.schedule import ScheduleCreate, ScheduleResponse, ScheduleRunNowResponse, ScheduleUpdate, ScheduledRunResponse
from pipeline.scheduler import enqueue_due_schedules

router = APIRouter(prefix="/pipeline/schedules", tags=["schedules"])


def _json_object(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value or {}


def _schedule_response(row) -> ScheduleResponse:
    return ScheduleResponse(
        id=str(row["id"]),
        story_id=str(row["story_id"]) if row.get("story_id") else None,
        name=row["name"],
        schedule_type=row["schedule_type"],
        cadence=row["cadence"],
        cadence_config=_json_object(row.get("cadence_config")),
        timezone=row["timezone"],
        next_run_at=row.get("next_run_at"),
        enabled=row["enabled"],
        pipeline_config=_json_object(row.get("pipeline_config")),
        publish_config=_json_object(row.get("publish_config")),
        approval_policy=row["approval_policy"],
        status=row["status"],
        last_run_at=row.get("last_run_at"),
        last_error=row.get("last_error"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _scheduled_run_response(row) -> ScheduledRunResponse:
    return ScheduledRunResponse(
        id=str(row["id"]),
        schedule_id=str(row["schedule_id"]) if row.get("schedule_id") else None,
        story_id=str(row["story_id"]) if row.get("story_id") else None,
        episode_id=str(row["episode_id"]) if row.get("episode_id") else None,
        publish_target_id=str(row["publish_target_id"]) if row.get("publish_target_id") else None,
        job_id=str(row["job_id"]) if row.get("job_id") else None,
        run_type=row["run_type"],
        due_at=row.get("due_at"),
        status=row["status"],
        result=_json_object(row.get("result")),
        error=row.get("error"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def _assert_story_owner(pool, owner_id: str, story_id: str | None) -> None:
    if not story_id:
        return
    ok = await pool.fetchval("SELECT 1 FROM stories WHERE id=$1 AND owner_id=$2", story_id, owner_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Story not found")


@router.post("", response_model=ScheduleResponse)
async def create_schedule(body: ScheduleCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    owner_id = user_id(user)
    await _assert_story_owner(pool, owner_id, body.story_id)
    row = await pool.fetchrow(
        """INSERT INTO automation_schedules
           (owner_id, story_id, name, schedule_type, cadence, cadence_config, timezone,
            next_run_at, enabled, pipeline_config, publish_config, approval_policy, status)
           VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10::jsonb,$11::jsonb,$12,'active')
           RETURNING *""",
        owner_id,
        body.story_id,
        body.name,
        body.schedule_type,
        body.cadence,
        json.dumps(body.cadence_config),
        body.timezone,
        body.next_run_at,
        body.enabled,
        json.dumps(body.pipeline_config),
        json.dumps(body.publish_config),
        body.approval_policy,
    )
    return _schedule_response(row)


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM automation_schedules WHERE owner_id=$1 ORDER BY created_at DESC LIMIT 100",
        user_id(user),
    )
    return [_schedule_response(row) for row in rows]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM automation_schedules WHERE id=$1 AND owner_id=$2", schedule_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _schedule_response(row)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: str, body: ScheduleUpdate, user=Depends(get_current_user)):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT * FROM automation_schedules WHERE id=$1 AND owner_id=$2", schedule_id, user_id(user))
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    values = body.model_dump(exclude_unset=True)
    if "story_id" in values:
        await _assert_story_owner(pool, user_id(user), values.get("story_id"))
    if not values:
        return _schedule_response(existing)
    fields = []
    params = []
    for index, (key, value) in enumerate(values.items(), start=1):
        if key in {"cadence_config", "pipeline_config", "publish_config"}:
            fields.append(f"{key}=${index}::jsonb")
            params.append(json.dumps(value or {}))
        else:
            fields.append(f"{key}=${index}")
            params.append(value)
    params.extend([schedule_id, user_id(user)])
    row = await pool.fetchrow(
        f"""UPDATE automation_schedules
            SET {', '.join(fields)}, updated_at=now()
            WHERE id=${len(params) - 1} AND owner_id=${len(params)}
            RETURNING *""",
        *params,
    )
    return _schedule_response(row)


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    result = await pool.execute(
        "DELETE FROM automation_schedules WHERE id=$1 AND owner_id=$2",
        schedule_id,
        user_id(user),
    )
    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"ok": True}


@router.post("/{schedule_id}/run-now", response_model=ScheduleRunNowResponse)
async def run_schedule_now(schedule_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM automation_schedules WHERE id=$1 AND owner_id=$2", schedule_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Schedule not found")
    job_type = {
        "generate_only": "scheduled_generate_only",
        "publish_existing": "scheduled_publish_existing",
        "generate_and_publish": "scheduled_generate_and_publish",
        "series_continuation": "scheduled_series_continuation",
    }.get(row["schedule_type"], "scheduled_generate_only")
    job_id = await pool.fetchval(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('schedule',$1,'pending',1,'Queued manually',$2)
           RETURNING id""",
        schedule_id,
        job_type,
    )
    await enqueue_job(str(job_id), workload=WORKLOAD_SCHEDULER)
    scheduled_run = await pool.fetchrow(
        """INSERT INTO scheduled_runs
           (schedule_id, owner_id, story_id, job_id, run_type, due_at, status)
           VALUES ($1,$2,$3,$4,$5,now(),'queued')
           RETURNING *""",
        schedule_id,
        user_id(user),
        str(row["story_id"]) if row.get("story_id") else None,
        str(job_id),
        row["schedule_type"],
    )
    return ScheduleRunNowResponse(scheduled_run=_scheduled_run_response(scheduled_run))


@router.post("/dispatch-due")
async def dispatch_due_schedules(user=Depends(get_current_user)):
    queued = await enqueue_due_schedules(owner_id=user_id(user))
    return {"queued": queued}


@router.get("/{schedule_id}/runs", response_model=list[ScheduledRunResponse])
async def list_schedule_runs(schedule_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    schedule = await pool.fetchval("SELECT 1 FROM automation_schedules WHERE id=$1 AND owner_id=$2", schedule_id, user_id(user))
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    rows = await pool.fetch(
        "SELECT * FROM scheduled_runs WHERE schedule_id=$1 ORDER BY created_at DESC LIMIT 50",
        schedule_id,
    )
    return [_scheduled_run_response(row) for row in rows]

