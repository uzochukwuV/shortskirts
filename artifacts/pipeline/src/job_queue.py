import os
import time
from typing import Iterable, Optional

import redis.asyncio as redis
import asyncpg

READY_QUEUE_KEY = "storyforge:jobs:ready"
DELAYED_QUEUE_KEY = "storyforge:jobs:delayed"

WORKLOAD_STORY = "story"
WORKLOAD_MEDIA = "media"
WORKLOAD_AUDIO = "audio"
WORKLOAD_ALL = "all"

READY_QUEUE_KEYS = {
    WORKLOAD_STORY: "storyforge:jobs:ready:story",
    WORKLOAD_MEDIA: "storyforge:jobs:ready:media",
    WORKLOAD_AUDIO: "storyforge:jobs:ready:audio",
}
DELAYED_QUEUE_KEYS = {
    WORKLOAD_STORY: "storyforge:jobs:delayed:story",
    WORKLOAD_MEDIA: "storyforge:jobs:delayed:media",
    WORKLOAD_AUDIO: "storyforge:jobs:delayed:audio",
}

_redis_client: Optional[redis.Redis] = None


def normalize_redis_url(raw: str) -> str:
    value = raw.strip()
    if value.startswith("redis-cli -u "):
        value = value.split("redis-cli -u ", 1)[1].strip()
    return value


def get_redis_url() -> str:
    raw = os.environ.get("REDIS_URL")
    if not raw:
        raise RuntimeError("REDIS_URL is required for the worker queue")
    return normalize_redis_url(raw)


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(get_redis_url(), decode_responses=True)
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def job_workload(entity_type: str, job_type: str | None = None) -> str:
    if entity_type == "story":
        if job_type == "checkpoint_audio":
            return WORKLOAD_AUDIO
        return WORKLOAD_STORY
    if entity_type in {"character", "scene"}:
        return WORKLOAD_MEDIA
    if job_type in {"char_refs", "scene_regen"}:
        return WORKLOAD_MEDIA
    return WORKLOAD_STORY


def ready_queue_key(workload: str) -> str:
    return READY_QUEUE_KEYS.get(workload, READY_QUEUE_KEYS[WORKLOAD_STORY])


def delayed_queue_key(workload: str) -> str:
    return DELAYED_QUEUE_KEYS.get(workload, DELAYED_QUEUE_KEYS[WORKLOAD_STORY])


async def enqueue_job(job_id: str, delay_seconds: int = 0, workload: str = WORKLOAD_STORY) -> None:
    client = await get_redis()
    ready_key = ready_queue_key(workload)
    delayed_key = delayed_queue_key(workload)
    if delay_seconds > 0:
        await client.zadd(delayed_key, {job_id: time.time() + delay_seconds})
        return
    await client.rpush(ready_key, job_id)


async def promote_due_delayed_jobs(workload: str, limit: int = 100) -> int:
    client = await get_redis()
    ready_key = ready_queue_key(workload)
    delayed_key = delayed_queue_key(workload)
    now = time.time()
    due = await client.zrangebyscore(delayed_key, min="-inf", max=now, start=0, num=limit)
    if not due:
        return 0

    moved = 0
    for job_id in due:
        removed = await client.zrem(delayed_key, job_id)
        if removed:
            await client.rpush(ready_key, job_id)
            moved += 1
    return moved


async def blpop_job(workload: str, timeout: int = 5) -> Optional[str]:
    client = await get_redis()
    item = await client.blpop(ready_queue_key(workload), timeout=timeout)
    if not item:
        return None
    _, job_id = item
    return job_id


async def claim_job(
    pool: asyncpg.Pool,
    job_id: str,
    worker_id: str,
    lease_seconds: int = 600,
):
    return await pool.fetchrow(
        """UPDATE generation_jobs
           SET status='running',
               worker_id=$2,
               attempts=attempts + 1,
               leased_at=now(),
               lease_expires_at=now() + (($3::text || ' seconds')::interval),
               last_heartbeat_at=now(),
               started_at=COALESCE(started_at, now()),
               updated_at=now()
           WHERE id=$1
             AND (status='pending' OR lease_expires_at IS NULL OR lease_expires_at < now())
           RETURNING *""",
        job_id,
        worker_id,
        str(lease_seconds),
    )


async def touch_lease(
    pool: asyncpg.Pool,
    job_id: str,
    worker_id: str,
    lease_seconds: int = 600,
):
    await pool.execute(
        """UPDATE generation_jobs
           SET last_heartbeat_at=now(),
               lease_expires_at=now() + (($3::text || ' seconds')::interval),
               updated_at=now()
           WHERE id=$1 AND worker_id=$2 AND status='running'""",
        job_id,
        worker_id,
        str(lease_seconds),
    )


async def mark_job_failed(
    pool: asyncpg.Pool,
    job_id: str,
    error: str,
    worker_id: str,
):
    await pool.execute(
        """UPDATE generation_jobs
           SET status='failed',
               error=$2,
               completed_at=now(),
               worker_id=$3,
               lease_expires_at=NULL,
               updated_at=now()
           WHERE id=$1""",
        job_id,
        error,
        worker_id,
    )


async def mark_job_retrying(
    pool: asyncpg.Pool,
    job_id: str,
    error: str,
    worker_id: str,
):
    await pool.execute(
        """UPDATE generation_jobs
           SET status='pending',
               error=$2,
               current_step='Retry scheduled',
               worker_id=NULL,
               leased_at=NULL,
               lease_expires_at=NULL,
               last_heartbeat_at=now(),
               updated_at=now()
           WHERE id=$1""",
        job_id,
        error,
        worker_id,
    )


async def recover_expired_jobs(pool: asyncpg.Pool, workload: str, limit: int = 100) -> list[str]:
    if workload == WORKLOAD_MEDIA:
        workload_clause = "(entity_type IN ('character','scene') OR job_type IN ('char_refs','scene_regen'))"
    elif workload == WORKLOAD_AUDIO:
        workload_clause = "(job_type = 'checkpoint_audio')"
    else:
        workload_clause = "(entity_type = 'story' OR job_type IN ('full_episode','full_episode_resume'))"
    rows = await pool.fetch(
        """SELECT id
           FROM generation_jobs
           WHERE status='running'
             AND """
        + workload_clause
        + """
             AND (lease_expires_at IS NULL OR lease_expires_at < now())
           ORDER BY created_at ASC
           LIMIT $1""",
        limit,
    )
    return [str(row["id"]) for row in rows]


async def requeue_jobs(job_ids: Iterable[str], workload: str) -> int:
    count = 0
    for job_id in job_ids:
        await enqueue_job(job_id, workload=workload)
        count += 1
    return count
