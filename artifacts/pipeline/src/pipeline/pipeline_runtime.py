from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, AsyncIterator, Optional

from db.connection import get_pool

_current_run_id: ContextVar[Optional[str]] = ContextVar("pipeline_run_id", default=None)
_current_step_id: ContextVar[Optional[str]] = ContextVar("pipeline_step_id", default=None)


def _json(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {})


def current_pipeline_run_id() -> Optional[str]:
    return _current_run_id.get()


def current_pipeline_step_id() -> Optional[str]:
    return _current_step_id.get()


@asynccontextmanager
async def pipeline_context_binding(
    *,
    run_id: str | None = None,
    step_id: str | None = None,
) -> AsyncIterator[None]:
    run_token = _current_run_id.set(run_id) if run_id is not None else None
    step_token = _current_step_id.set(step_id) if step_id is not None else None
    try:
        yield
    finally:
        if step_token is not None:
            _current_step_id.reset(step_token)
        if run_token is not None:
            _current_run_id.reset(run_token)


async def start_pipeline_run(
    *,
    owner_id: str | None = None,
    story_id: str | None = None,
    job_id: str | None = None,
    run_type: str = "story_generation",
    config: dict[str, Any] | None = None,
) -> str:
    pool = await get_pool()
    run_id = await pool.fetchval(
        """INSERT INTO pipeline_runs
           (owner_id, story_id, job_id, run_type, status, config, started_at)
           VALUES ($1,$2,$3,$4,'running',$5::jsonb,now())
           RETURNING id""",
        owner_id,
        story_id,
        job_id,
        run_type,
        _json(config),
    )
    return str(run_id)


async def finish_pipeline_run(
    run_id: str,
    *,
    status: str = "completed",
    summary: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """UPDATE pipeline_runs
           SET status=$2, summary=$3::jsonb, error=$4, completed_at=now(), updated_at=now()
           WHERE id=$1""",
        run_id,
        status,
        _json(summary),
        error[:2000] if error else None,
    )


async def start_pipeline_step(
    *,
    run_id: str | None = None,
    parent_step_id: str | None = None,
    story_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    job_id: str | None = None,
    step_key: str,
    step_type: str = "operation",
    input: dict[str, Any] | None = None,
    provider: str | None = None,
    provider_model: str | None = None,
    attempt: int = 1,
) -> str:
    pool = await get_pool()
    resolved_run_id = run_id or current_pipeline_run_id()
    resolved_parent_step_id = parent_step_id if parent_step_id is not None else current_pipeline_step_id()
    if not resolved_run_id:
        raise RuntimeError("pipeline run id is required to start a pipeline step")
    step_id = await pool.fetchval(
        """INSERT INTO pipeline_steps
           (run_id, parent_step_id, story_id, episode_id, scene_id, job_id,
            step_key, step_type, status, attempt, provider, provider_model, input, started_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'running',$9,$10,$11,$12::jsonb,now())
           RETURNING id""",
        resolved_run_id,
        resolved_parent_step_id,
        story_id,
        episode_id,
        scene_id,
        job_id,
        step_key,
        step_type,
        attempt,
        provider,
        provider_model,
        _json(input),
    )
    return str(step_id)


async def finish_pipeline_step(
    step_id: str,
    *,
    status: str = "completed",
    output: dict[str, Any] | None = None,
    error: str | None = None,
    provider: str | None = None,
    provider_model: str | None = None,
    provider_task_id: str | None = None,
    provider_request_id: str | None = None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """UPDATE pipeline_steps
           SET status=$2, output=$3::jsonb, error=$4,
               provider=COALESCE($5, provider),
               provider_model=COALESCE($6, provider_model),
               provider_task_id=COALESCE($7, provider_task_id),
               provider_request_id=COALESCE($8, provider_request_id),
               completed_at=now(), updated_at=now()
           WHERE id=$1""",
        step_id,
        status,
        _json(output),
        error[:2000] if error else None,
        provider,
        provider_model,
        provider_task_id,
        provider_request_id,
    )


async def record_pipeline_artifact(
    *,
    run_id: str | None = None,
    step_id: str | None = None,
    story_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    artifact_type: str,
    media_kind: str | None = None,
    url: str | None = None,
    content: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    pool = await get_pool()
    resolved_run_id = run_id or current_pipeline_run_id()
    resolved_step_id = step_id if step_id is not None else current_pipeline_step_id()
    if not resolved_run_id:
        raise RuntimeError("pipeline run id is required to record an artifact")
    artifact_id = await pool.fetchval(
        """INSERT INTO pipeline_artifacts
           (run_id, step_id, story_id, episode_id, scene_id, artifact_type,
            media_kind, url, content, metadata)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb)
           RETURNING id""",
        resolved_run_id,
        resolved_step_id,
        story_id,
        episode_id,
        scene_id,
        artifact_type,
        media_kind,
        url,
        json.dumps(content) if content is not None else None,
        _json(metadata),
    )
    return str(artifact_id)


@asynccontextmanager
async def pipeline_run_context(
    *,
    owner_id: str | None = None,
    story_id: str | None = None,
    job_id: str | None = None,
    run_type: str,
    config: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    run_id = await start_pipeline_run(
        owner_id=owner_id,
        story_id=story_id,
        job_id=job_id,
        run_type=run_type,
        config=config,
    )
    token = _current_run_id.set(run_id)
    try:
        yield run_id
    except Exception as exc:
        await finish_pipeline_run(run_id, status="failed", error=str(exc))
        raise
    finally:
        _current_run_id.reset(token)


@asynccontextmanager
async def pipeline_step_context(
    *,
    step_key: str,
    step_type: str = "operation",
    input: dict[str, Any] | None = None,
    story_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    job_id: str | None = None,
    provider: str | None = None,
    provider_model: str | None = None,
    attempt: int = 1,
) -> AsyncIterator[str]:
    started = time.perf_counter()
    step_id = await start_pipeline_step(
        story_id=story_id,
        episode_id=episode_id,
        scene_id=scene_id,
        job_id=job_id,
        step_key=step_key,
        step_type=step_type,
        input=input,
        provider=provider,
        provider_model=provider_model,
        attempt=attempt,
    )
    token = _current_step_id.set(step_id)
    try:
        yield step_id
    except Exception as exc:
        await finish_pipeline_step(
            step_id,
            status="failed",
            error=str(exc),
            output={"duration_ms": int((time.perf_counter() - started) * 1000)},
        )
        raise
    finally:
        _current_step_id.reset(token)
