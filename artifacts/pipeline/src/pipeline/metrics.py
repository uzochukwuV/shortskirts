from __future__ import annotations

from decimal import Decimal
import json
import time
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


# Baseline metrics for Agent SDK integration

async def record_scene_metric(
    *,
    story_id: str,
    scene_id: str | None = None,
    episode_number: int | None = None,
    scene_number: int | None = None,
    requested_duration_seconds: float | None = None,
    actual_duration_seconds: float | None = None,
    provider: str | None = None,
    provider_model: str | None = None,
    estimated_cost_usd: float | None = None,
    generation_time_ms: int | None = None,
    success: bool = True,
    error: str | None = None,
    regeneration_count: int = 0,
    job_id: str | None = None,
) -> None:
    """Record detailed scene generation metrics for performance analysis."""
    await record_pipeline_metric(
        metric_kind="scene_generation",
        status="success" if success else "failed",
        duration_ms=generation_time_ms,
        estimated_cost_usd=estimated_cost_usd,
        provider=provider,
        error=error,
        job_id=job_id,
        entity_type="scene",
        entity_id=scene_id,
        extra={
            "story_id": story_id,
            "episode_number": episode_number,
            "scene_number": scene_number,
            "requested_duration_seconds": requested_duration_seconds,
            "actual_duration_seconds": actual_duration_seconds,
            "provider_model": provider_model,
            "regeneration_count": regeneration_count,
            "duration_accuracy": (
                abs(actual_duration_seconds - requested_duration_seconds) / requested_duration_seconds
                if requested_duration_seconds and actual_duration_seconds
                else None
            ),
        },
    )


async def record_regeneration_metric(
    *,
    story_id: str,
    scene_id: str,
    regeneration_count: int,
    reason: str | None = None,
    provider: str | None = None,
    estimated_cost_usd: float | None = None,
    job_id: str | None = None,
) -> None:
    """Record scene regeneration event for tracking regeneration rate."""
    await record_pipeline_metric(
        metric_kind="scene_regeneration",
        status="triggered",
        estimated_cost_usd=estimated_cost_usd,
        provider=provider,
        job_id=job_id,
        entity_type="scene",
        entity_id=scene_id,
        extra={
            "story_id": story_id,
            "regeneration_count": regeneration_count,
            "reason": reason,
        },
    )


async def record_provider_cost_metric(
    *,
    story_id: str,
    scene_id: str | None = None,
    provider: str,
    operation: str,
    estimated_cost_usd: float,
    duration_ms: int | None = None,
    job_id: str | None = None,
) -> None:
    """Record provider cost for individual operations."""
    await record_pipeline_metric(
        metric_kind=f"provider_cost_{operation}",
        status="completed",
        duration_ms=duration_ms,
        estimated_cost_usd=estimated_cost_usd,
        provider=provider,
        job_id=job_id,
        entity_type="scene",
        entity_id=scene_id,
        extra={
            "story_id": story_id,
            "operation": operation,
        },
    )


async def record_story_completion_metric(
    *,
    story_id: str,
    total_scenes: int,
    total_episodes: int,
    total_duration_seconds: float,
    total_generation_time_ms: int,
    total_estimated_cost_usd: float,
    regeneration_count: int,
    success: bool = True,
    job_id: str | None = None,
) -> None:
    """Record overall story completion metrics."""
    await record_pipeline_metric(
        metric_kind="story_completion",
        status="success" if success else "failed",
        duration_ms=total_generation_time_ms,
        estimated_cost_usd=total_estimated_cost_usd,
        job_id=job_id,
        entity_type="story",
        entity_id=story_id,
        extra={
            "total_scenes": total_scenes,
            "total_episodes": total_episodes,
            "total_duration_seconds": total_duration_seconds,
            "regeneration_count": regeneration_count,
            "regeneration_rate": regeneration_count / total_scenes if total_scenes > 0 else 0,
            "avg_scene_duration_ms": total_generation_time_ms / total_scenes if total_scenes > 0 else 0,
        },
    )


class SceneMetricsTimer:
    """Context manager for timing scene generation operations."""
    
    def __init__(
        self,
        story_id: str,
        scene_id: str | None = None,
        episode_number: int | None = None,
        scene_number: int | None = None,
        requested_duration_seconds: float | None = None,
        provider: str | None = None,
        provider_model: str | None = None,
        job_id: str | None = None,
    ):
        self.story_id = story_id
        self.scene_id = scene_id
        self.episode_number = episode_number
        self.scene_number = scene_number
        self.requested_duration_seconds = requested_duration_seconds
        self.provider = provider
        self.provider_model = provider_model
        self.job_id = job_id
        self.start_time = None
        self.estimated_cost = None
        self.success = True
        self.error = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000)
        
        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)[:500] if exc_val else "Unknown error"
        
        await record_scene_metric(
            story_id=self.story_id,
            scene_id=self.scene_id,
            episode_number=self.episode_number,
            scene_number=self.scene_number,
            requested_duration_seconds=self.requested_duration_seconds,
            provider=self.provider,
            provider_model=self.provider_model,
            estimated_cost_usd=self.estimated_cost,
            generation_time_ms=duration_ms,
            success=self.success,
            error=self.error,
            job_id=self.job_id,
        )
        return False
