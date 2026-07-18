from __future__ import annotations

from decimal import Decimal
import json
from typing import Any

from db.connection import get_pool
from pipeline.runtime_context import get_job_context


async def record_pipeline_metric(
    *,
    metric_kind: str,
    status: str,
    duration_ms: int | None = None,
    provider_latency_ms: int | None = None,
    estimated_cost_usd: float | None = None,
    retries: int = 0,
    step_name: str | None = None,
    provider: str | None = None,
    provider_task_id: str | None = None,
    provider_request_id: str | None = None,
    error: str | None = None,
    job_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    workload: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    ctx = get_job_context() or {}
    pool = await get_pool()
    extra_data = dict(extra or {})
    provider_task_id = provider_task_id or extra_data.get("task_id") or extra_data.get("provider_task_id")
    provider_request_id = provider_request_id or extra_data.get("request_id") or extra_data.get("provider_request_id")
    await pool.execute(
        """INSERT INTO pipeline_metrics
           (metric_kind, status, duration_ms, provider_latency_ms, estimated_cost_usd,
            retries, step_name, provider, provider_task_id, provider_request_id, error,
            job_id, entity_type, entity_id, workload, extra)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16::jsonb)""",
        metric_kind,
        status,
        duration_ms,
        provider_latency_ms,
        Decimal(str(estimated_cost_usd)) if estimated_cost_usd is not None else None,
        retries,
        step_name,
        provider,
        provider_task_id,
        provider_request_id,
        error,
        job_id or ctx.get("job_id"),
        entity_type or ctx.get("entity_type"),
        entity_id or ctx.get("entity_id"),
        workload or ctx.get("workload"),
        json.dumps(extra_data),
    )
