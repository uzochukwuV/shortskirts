from __future__ import annotations

import json
from datetime import datetime, timezone

from db.connection import get_pool
from job_queue import WORKLOAD_SCHEDULER, enqueue_job


async def enqueue_due_schedules(owner_id: str | None = None, limit: int = 25) -> list[dict]:
    pool = await get_pool()
    owner_clause = "AND owner_id=$2" if owner_id else ""
    args = [limit]
    if owner_id:
        args.append(owner_id)
    rows = await pool.fetch(
        f"""SELECT *
            FROM automation_schedules
            WHERE enabled = true
              AND status = 'active'
              AND next_run_at IS NOT NULL
              AND next_run_at <= now()
              {owner_clause}
            ORDER BY next_run_at ASC
            LIMIT $1""",
        *args,
    )
    queued = []
    for row in rows:
        job_type = {
            "generate_only": "scheduled_generate_only",
            "publish_existing": "scheduled_publish_existing",
            "generate_and_publish": "scheduled_generate_and_publish",
            "series_continuation": "scheduled_series_continuation",
        }.get(row["schedule_type"], "scheduled_generate_only")
        job_id = await pool.fetchval(
            """INSERT INTO generation_jobs
               (entity_type, entity_id, status, total_steps, current_step, job_type, result)
               VALUES ('schedule',$1,'pending',1,'Queued scheduled run',$2,$3::jsonb)
               RETURNING id""",
            str(row["id"]),
            job_type,
            json.dumps({"queued_at": datetime.now(timezone.utc).isoformat()}),
        )
        await enqueue_job(str(job_id), workload=WORKLOAD_SCHEDULER)
        queued.append({"schedule_id": str(row["id"]), "job_id": str(job_id), "job_type": job_type})
    return queued

