import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from contextlib import suppress

from db.connection import close_pool, get_pool, init_db
from job_queue import (
    WORKLOAD_ALL,
    WORKLOAD_MEDIA,
    WORKLOAD_STORY,
    blpop_job,
    claim_job,
    close_redis,
    enqueue_job,
    job_workload,
    mark_job_failed,
    mark_job_retrying,
    promote_due_delayed_jobs,
    recover_expired_jobs,
    touch_lease,
)
from pipeline.metrics import record_pipeline_metric
from pipeline.job_handlers import run_character_ref_job, run_scene_regen_job
from pipeline.runtime_context import job_context
from pipeline.orchestrator import run_story_generation

LEASE_SECONDS = int(os.getenv("JOB_LEASE_SECONDS", "600"))
HEARTBEAT_SECONDS = int(os.getenv("JOB_HEARTBEAT_SECONDS", "30"))
RETRY_BASE_SECONDS = int(os.getenv("JOB_RETRY_BASE_SECONDS", "15"))
DEFAULT_MAX_ATTEMPTS = int(os.getenv("JOB_MAX_ATTEMPTS", "3"))
WORKER_WORKLOAD = os.getenv("WORKER_WORKLOAD", WORKLOAD_STORY)


async def heartbeat_loop(pool, job_id: str, worker_id: str, stop: asyncio.Event):
    try:
        while not stop.is_set():
            await asyncio.sleep(HEARTBEAT_SECONDS)
            if stop.is_set():
                break
            await touch_lease(pool, job_id, worker_id, LEASE_SECONDS)
    except asyncio.CancelledError:
        pass


async def _run_handler(pool, row: dict, worker_id: str):
    entity_type = row["entity_type"]
    job_type = row.get("job_type")
    if entity_type == "story" and job_type == "full_episode":
        return await run_story_generation(str(row["entity_id"]), str(row["id"]))
    if entity_type == "character" or job_type == "char_refs":
        return await run_character_ref_job(str(row["entity_id"]), str(row["id"]), worker_id)
    if entity_type == "scene" or job_type == "scene_regen":
        return await run_scene_regen_job(str(row["entity_id"]), str(row["id"]), worker_id)
    raise RuntimeError(f"Unsupported job type: {entity_type}/{job_type}")


async def process_job(pool, row, worker_id: str):
    row = dict(row)
    job_id = str(row["id"])
    job_started = time.monotonic()
    started_at = row.get("started_at")
    attempts = int(row.get("attempts") or 0)
    max_attempts = int(row.get("max_attempts") or DEFAULT_MAX_ATTEMPTS)
    workload = job_workload(row["entity_type"], row.get("job_type"))

    stop = asyncio.Event()
    hb = asyncio.create_task(heartbeat_loop(pool, job_id, worker_id, stop))
    try:
        async with job_context(
            job_id=job_id,
            entity_type=row["entity_type"],
            entity_id=str(row["entity_id"]),
            workload=workload,
            worker_id=worker_id,
        ):
            result = await _run_handler(pool, row, worker_id)
            finished_at = datetime.now(timezone.utc)
            duration_ms = int((finished_at - started_at).total_seconds() * 1000) if started_at else int((time.monotonic() - job_started) * 1000)
            await record_pipeline_metric(
                metric_kind="job",
                status="completed",
                duration_ms=duration_ms or None,
                step_name="job",
                job_id=job_id,
                entity_type=row["entity_type"],
                entity_id=str(row["entity_id"]),
                workload=workload,
                extra={"attempts": attempts + 1, "job_type": row.get("job_type")},
            )
            return result
    except Exception as e:
        error = str(e)
        if attempts < max_attempts:
            delay = RETRY_BASE_SECONDS * (2 ** max(0, attempts - 1))
            await mark_job_retrying(pool, job_id, error[:1000], worker_id)
            await enqueue_job(job_id, delay_seconds=delay, workload=workload)
            print(f"[worker:{WORKER_WORKLOAD}] retrying job {job_id} in {delay}s: {error[:120]}")
            return {"retry_scheduled": True, "delay_seconds": delay}

        await mark_job_failed(pool, job_id, error[:1000], worker_id)
        if row["entity_type"] == "story":
            await pool.execute("UPDATE stories SET status='failed', updated_at=now() WHERE id=$1", str(row["entity_id"]))
        elif row["entity_type"] == "scene":
            await pool.execute("UPDATE scenes SET status='failed', updated_at=now() WHERE id=$1", str(row["entity_id"]))
        elif row["entity_type"] == "character":
            await pool.execute("UPDATE characters SET updated_at=now() WHERE id=$1", str(row["entity_id"]))
        await record_pipeline_metric(
            metric_kind="job",
            status="failed",
            step_name="job",
            error=error[:1000],
            job_id=job_id,
            entity_type=row["entity_type"],
            entity_id=str(row["entity_id"]),
            workload=workload,
            extra={"attempts": attempts + 1, "job_type": row.get("job_type")},
        )
        print(f"[worker:{WORKER_WORKLOAD}] job {job_id} failed permanently: {error[:200]}")
        return {"failed": True}
    finally:
        stop.set()
        hb.cancel()
        with suppress(asyncio.CancelledError):
            await hb


async def main():
    await init_db()
    pool = await get_pool()
    worker_id = os.getenv("WORKER_ID") or f"worker-{uuid.uuid4().hex[:8]}"
    print(
        f"[worker:{WORKER_WORKLOAD}] started worker_id={worker_id} lease={LEASE_SECONDS}s heartbeat={HEARTBEAT_SECONDS}s"
    )

    if WORKER_WORKLOAD not in {WORKLOAD_STORY, WORKLOAD_MEDIA, WORKLOAD_ALL}:
        raise RuntimeError(f"Unsupported WORKER_WORKLOAD={WORKER_WORKLOAD}")

    workloads = [WORKLOAD_STORY, WORKLOAD_MEDIA] if WORKER_WORKLOAD == WORKLOAD_ALL else [WORKER_WORKLOAD]

    for workload in workloads:
        for job_id in await recover_expired_jobs(pool, workload):
            await enqueue_job(job_id, workload=workload)
            print(f"[worker:{WORKER_WORKLOAD}] recovered expired job {job_id} -> {workload}")

    try:
        while True:
            for workload in workloads:
                await promote_due_delayed_jobs(workload)
                job_id = await blpop_job(workload, timeout=1)
                if not job_id:
                    continue

                row = await claim_job(pool, job_id, worker_id, LEASE_SECONDS)
                if not row:
                    continue
                row_dict = dict(row)
                expected = job_workload(row_dict["entity_type"], row_dict.get("job_type"))
                if expected != workload and WORKER_WORKLOAD != WORKLOAD_ALL:
                    print(
                        f"[worker:{WORKER_WORKLOAD}] skipping job {job_id} type={row_dict['entity_type']}/{row_dict.get('job_type')} expected={workload}"
                    )
                    continue

                print(
                    f"[worker:{WORKER_WORKLOAD}] claimed job {job_id} type={row_dict['entity_type']}/{row_dict.get('job_type')}"
                )
                await process_job(pool, row_dict, worker_id)
    finally:
        await close_redis()
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
