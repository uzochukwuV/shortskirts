from __future__ import annotations

import asyncio
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

import httpx

from job_queue import get_redis
from pipeline.metrics import record_pipeline_metric
from pipeline.pipeline_runtime import (
    current_pipeline_run_id,
    current_pipeline_step_id,
    finish_pipeline_step,
    start_pipeline_step,
)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class StepPolicy:
    name: str
    provider: str
    rate_limit: int
    rate_window_seconds: int
    max_attempts: int
    base_delay_seconds: float
    max_delay_seconds: float
    estimated_cost_usd: float = 0.0
    prompt_cost_per_1k: float = 0.0
    completion_cost_per_1k: float = 0.0


STEP_POLICIES = {
    "qwen_llm": StepPolicy(
        name="qwen_llm",
        provider="qwen",
        rate_limit=int(os.getenv("QWEN_LLM_RATE_LIMIT", "20")),
        rate_window_seconds=int(os.getenv("QWEN_LLM_RATE_WINDOW", "60")),
        max_attempts=int(os.getenv("QWEN_LLM_MAX_ATTEMPTS", "5")),
        base_delay_seconds=_env_float("QWEN_LLM_BACKOFF_BASE", 2.0),
        max_delay_seconds=_env_float("QWEN_LLM_BACKOFF_MAX", 20.0),
        prompt_cost_per_1k=_env_float("QWEN_LLM_PROMPT_COST_PER_1K", 0.002),
        completion_cost_per_1k=_env_float("QWEN_LLM_COMPLETION_COST_PER_1K", 0.004),
    ),
    "aiml_llm": StepPolicy(
        name="aiml_llm",
        provider="aiml",
        rate_limit=int(os.getenv("AIML_LLM_RATE_LIMIT", "12")),
        rate_window_seconds=int(os.getenv("AIML_LLM_RATE_WINDOW", "60")),
        max_attempts=int(os.getenv("AIML_LLM_MAX_ATTEMPTS", "4")),
        base_delay_seconds=_env_float("AIML_LLM_BACKOFF_BASE", 2.0),
        max_delay_seconds=_env_float("AIML_LLM_BACKOFF_MAX", 20.0),
        prompt_cost_per_1k=_env_float("AIML_LLM_PROMPT_COST_PER_1K", 0.002),
        completion_cost_per_1k=_env_float("AIML_LLM_COMPLETION_COST_PER_1K", 0.004),
    ),
    "dashscope_image": StepPolicy(
        name="dashscope_image",
        provider="dashscope",
        rate_limit=int(os.getenv("DASHSCOPE_IMAGE_RATE_LIMIT", "6")),
        rate_window_seconds=int(os.getenv("DASHSCOPE_IMAGE_RATE_WINDOW", "60")),
        max_attempts=int(os.getenv("DASHSCOPE_IMAGE_MAX_ATTEMPTS", "4")),
        base_delay_seconds=_env_float("DASHSCOPE_IMAGE_BACKOFF_BASE", 5.0),
        max_delay_seconds=_env_float("DASHSCOPE_IMAGE_BACKOFF_MAX", 60.0),
        estimated_cost_usd=_env_float("DASHSCOPE_IMAGE_COST", 0.03),
    ),
    "aiml_image": StepPolicy(
        name="aiml_image",
        provider="aiml",
        rate_limit=int(os.getenv("AIML_IMAGE_RATE_LIMIT", "4")),
        rate_window_seconds=int(os.getenv("AIML_IMAGE_RATE_WINDOW", "60")),
        max_attempts=int(os.getenv("AIML_IMAGE_MAX_ATTEMPTS", "4")),
        base_delay_seconds=_env_float("AIML_IMAGE_BACKOFF_BASE", 5.0),
        max_delay_seconds=_env_float("AIML_IMAGE_BACKOFF_MAX", 60.0),
        estimated_cost_usd=_env_float("AIML_IMAGE_COST", 0.04),
    ),
    "dashscope_audio": StepPolicy(
        name="dashscope_audio",
        provider="dashscope",
        rate_limit=int(os.getenv("DASHSCOPE_AUDIO_RATE_LIMIT", "6")),
        rate_window_seconds=int(os.getenv("DASHSCOPE_AUDIO_RATE_WINDOW", "60")),
        max_attempts=int(os.getenv("DASHSCOPE_AUDIO_MAX_ATTEMPTS", "4")),
        base_delay_seconds=_env_float("DASHSCOPE_AUDIO_BACKOFF_BASE", 5.0),
        max_delay_seconds=_env_float("DASHSCOPE_AUDIO_BACKOFF_MAX", 60.0),
        estimated_cost_usd=_env_float("DASHSCOPE_AUDIO_COST", 0.02),
    ),
    "dashscope_video_submit": StepPolicy(
        name="dashscope_video_submit",
        provider="dashscope",
        rate_limit=int(os.getenv("DASHSCOPE_VIDEO_SUBMIT_RATE_LIMIT", "2")),
        rate_window_seconds=int(os.getenv("DASHSCOPE_VIDEO_RATE_WINDOW", "60")),
        max_attempts=int(os.getenv("DASHSCOPE_VIDEO_SUBMIT_MAX_ATTEMPTS", "3")),
        base_delay_seconds=_env_float("DASHSCOPE_VIDEO_BACKOFF_BASE", 10.0),
        max_delay_seconds=_env_float("DASHSCOPE_VIDEO_BACKOFF_MAX", 120.0),
        estimated_cost_usd=_env_float("DASHSCOPE_VIDEO_COST", 0.2),
    ),
    "dashscope_video_poll": StepPolicy(
        name="dashscope_video_poll",
        provider="dashscope",
        rate_limit=int(os.getenv("DASHSCOPE_VIDEO_POLL_RATE_LIMIT", "24")),
        rate_window_seconds=int(os.getenv("DASHSCOPE_VIDEO_RATE_WINDOW", "60")),
        max_attempts=int(os.getenv("DASHSCOPE_VIDEO_POLL_MAX_ATTEMPTS", "3")),
        base_delay_seconds=_env_float("DASHSCOPE_VIDEO_POLL_BACKOFF_BASE", 5.0),
        max_delay_seconds=_env_float("DASHSCOPE_VIDEO_POLL_BACKOFF_MAX", 30.0),
    ),
}


def _retryable_http_status(status_code: int) -> bool:
    return status_code in {408, 409, 425, 429, 500, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError, asyncio.TimeoutError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        return bool(response and _retryable_http_status(response.status_code))
    if isinstance(exc, (json.JSONDecodeError, ValueError)):
        return True
    message = str(exc).lower()
    return any(token in message for token in ("rate limit", "timeout", "timed out", "temporarily", "503", "502", "gateway"))


def _backoff_seconds(policy: StepPolicy, attempt: int) -> float:
    delay = min(policy.max_delay_seconds, policy.base_delay_seconds * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0, max(0.2, delay * 0.15))
    return delay + jitter


async def _acquire_rate_limit(policy: StepPolicy) -> None:
    client = await get_redis()
    window = int(time.time() // policy.rate_window_seconds)
    key = f"storyforge:rate:{policy.name}:{window}"
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, policy.rate_window_seconds + 1)
    if count > policy.rate_limit:
        ttl = await client.ttl(key)
        wait = ttl if isinstance(ttl, int) and ttl > 0 else policy.rate_window_seconds
        await client.decr(key)
        await asyncio.sleep(wait + random.uniform(0.2, 1.0))


async def run_provider_step(
    policy_name: str,
    step_name: str,
    operation: Callable[[], Awaitable[Any]],
    *,
    cost_fn: Optional[Callable[[Any], float]] = None,
    extra: Optional[dict[str, Any]] = None,
    extra_builder: Optional[Callable[[Any], dict[str, Any]]] = None,
) -> Any:
    policy = STEP_POLICIES[policy_name]
    attempt = 0
    last_exc: Exception | None = None
    while True:
        attempt += 1
        start = time.perf_counter()
        attempt_step_id: str | None = None
        parent_step_id = current_pipeline_step_id()
        run_id = current_pipeline_run_id()
        if run_id:
            try:
                attempt_step_id = await start_pipeline_step(
                    run_id=run_id,
                    parent_step_id=parent_step_id,
                    step_key=step_name,
                    step_type="provider_attempt",
                    attempt=attempt,
                    provider=policy.provider,
                    input={
                        "policy": policy_name,
                        "step_name": step_name,
                        "extra": extra or {},
                    },
                )
            except Exception as trace_exc:
                print(f"[provider_policy] Failed to start provider attempt trace: {trace_exc}")
        await _acquire_rate_limit(policy)
        try:
            result = await operation()
            latency_ms = int((time.perf_counter() - start) * 1000)
            cost = policy.estimated_cost_usd
            if cost_fn is not None:
                try:
                    cost = float(cost_fn(result))
                except Exception:
                    pass
            else:
                usage = getattr(result, "usage", None)
                prompt_tokens = float(getattr(usage, "prompt_tokens", 0) or 0)
                completion_tokens = float(getattr(usage, "completion_tokens", 0) or 0)
                if prompt_tokens or completion_tokens:
                    cost = (
                        (prompt_tokens / 1000.0) * policy.prompt_cost_per_1k
                        + (completion_tokens / 1000.0) * policy.completion_cost_per_1k
                    )
            merged_extra = dict(extra or {})
            if extra_builder is not None:
                try:
                    built_extra = extra_builder(result) or {}
                    if isinstance(built_extra, dict):
                        merged_extra.update(built_extra)
                except Exception:
                    pass
            await record_pipeline_metric(
                metric_kind="provider",
                status="success",
                duration_ms=latency_ms,
                provider_latency_ms=latency_ms,
                estimated_cost_usd=cost,
                retries=attempt - 1,
                step_name=step_name,
                provider=policy.provider,
                extra=merged_extra,
            )
            if attempt_step_id:
                await finish_pipeline_step(
                    attempt_step_id,
                    status="completed",
                    output={
                        "duration_ms": latency_ms,
                        "estimated_cost_usd": cost,
                        "retries_before_success": attempt - 1,
                        "extra": merged_extra,
                    },
                    provider=policy.provider,
                    provider_model=merged_extra.get("model"),
                    provider_task_id=merged_extra.get("task_id") or merged_extra.get("provider_task_id"),
                    provider_request_id=merged_extra.get("request_id") or merged_extra.get("provider_request_id"),
                )
            return result
        except Exception as exc:
            last_exc = exc
            latency_ms = int((time.perf_counter() - start) * 1000)
            retryable = _is_retryable(exc)
            if attempt_step_id:
                try:
                    await finish_pipeline_step(
                        attempt_step_id,
                        status="retryable" if retryable and attempt < policy.max_attempts else "failed",
                        output={
                            "duration_ms": latency_ms,
                            "will_retry": bool(retryable and attempt < policy.max_attempts),
                            "max_attempts": policy.max_attempts,
                            "extra": extra or {},
                        },
                        error=str(exc),
                        provider=policy.provider,
                        provider_model=(extra or {}).get("model"),
                        provider_task_id=(extra or {}).get("task_id") or (extra or {}).get("provider_task_id"),
                        provider_request_id=(extra or {}).get("request_id") or (extra or {}).get("provider_request_id"),
                    )
                except Exception as trace_exc:
                    print(f"[provider_policy] Failed to finish provider attempt trace: {trace_exc}")
            await record_pipeline_metric(
                metric_kind="provider",
                status="retryable" if retryable else "failed",
                duration_ms=latency_ms,
                provider_latency_ms=latency_ms,
                estimated_cost_usd=policy.estimated_cost_usd,
                retries=attempt - 1,
                step_name=step_name,
                provider=policy.provider,
                error=str(exc)[:1000],
                extra=extra or {},
            )
            if retryable and attempt < policy.max_attempts:
                await asyncio.sleep(_backoff_seconds(policy, attempt))
                continue
            raise
