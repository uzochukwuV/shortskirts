from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from job_queue import get_redis
from pipeline.provider_policy import run_provider_step

QWEN_VIDEO_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"
WAN_SAMPLE_IMAGE_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250925/thtclx/input1.png"
COVER_SAMPLE_IMAGE_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20260424/mvzfud/hh-v2v-girl.jpg"
CACHE_KEY = "storyforge:provider_status:v1"
CACHE_TTL_SECONDS = int(os.getenv("PROVIDER_STATUS_CACHE_TTL_SECONDS", "900"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(data: str | None) -> dict[str, Any]:
    if not data:
        return {}
    try:
        parsed = json.loads(data)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _error_details(exc: Exception) -> dict[str, Any]:
    details: dict[str, Any] = {
        "available": False,
        "error": str(exc),
    }
    response = getattr(exc, "response", None)
    if response is not None:
        details["status_code"] = response.status_code
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            details["code"] = payload.get("code")
            details["message"] = payload.get("message") or payload.get("detail")
            details["request_id"] = payload.get("request_id")
    return details


async def _load_cached_status() -> dict[str, Any] | None:
    client = await get_redis()
    raw = await client.get(CACHE_KEY)
    return _safe_json(raw)


async def _store_cached_status(payload: dict[str, Any]) -> None:
    client = await get_redis()
    await client.set(CACHE_KEY, json.dumps(payload), ex=CACHE_TTL_SECONDS)


async def _probe_qwen_t2v() -> dict[str, Any]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return {
            "available": False,
            "model": "happyhorse-1.1-t2v",
            "error": "DASHSCOPE_API_KEY is missing",
        }

    endpoint = f"{QWEN_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
    payload = {
        "model": "happyhorse-1.1-t2v",
        "input": {"prompt": "Probe access for Wan text-to-video"},
        "parameters": {"resolution": "720P", "duration": 5, "watermark": False},
    }
    headers = {
        "Authorization": f"Bearer {dashscope_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            data = await run_provider_step(
                "dashscope_video_submit",
                "video:wan2.7-t2v:probe",
                lambda: _post_json(http, endpoint, headers, payload),
                extra={"model": payload["model"], "probe": True},
            )
        return {
            "available": bool(data.get("output", {}).get("task_id")),
            "model": payload["model"],
            "task_id": data.get("output", {}).get("task_id"),
            "task_status": data.get("output", {}).get("task_status"),
        }
    except Exception as exc:
        details = _error_details(exc)
        details.update({"model": payload["model"]})
        return details


async def _probe_qwen_i2v() -> dict[str, Any]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return {
            "available": False,
            "model": "happyhorse-1.1-i2v",
            "error": "DASHSCOPE_API_KEY is missing",
        }

    endpoint = f"{QWEN_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
    payload = {
        "model": "happyhorse-1.1-i2v",
        "input": {
            "prompt": "Probe access for Wan image-to-video",
            "media": [{"type": "first_frame", "url": WAN_SAMPLE_IMAGE_URL}],
        },
        "parameters": {"resolution": "720P", "duration": 5, "watermark": False},
    }
    headers = {
        "Authorization": f"Bearer {dashscope_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            data = await run_provider_step(
                "dashscope_video_submit",
                "video:wan2.7-i2v:probe",
                lambda: _post_json(http, endpoint, headers, payload),
                extra={"model": payload["model"], "probe": True},
            )
        return {
            "available": bool(data.get("output", {}).get("task_id")),
            "model": payload["model"],
            "task_id": data.get("output", {}).get("task_id"),
            "task_status": data.get("output", {}).get("task_status"),
        }
    except Exception as exc:
        details = _error_details(exc)
        details.update({"model": payload["model"]})
        return details


async def _probe_qwen_r2v() -> dict[str, Any]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return {
            "available": False,
            "model": "happyhorse-1.1-r2v",
            "error": "DASHSCOPE_API_KEY is missing",
        }

    endpoint = f"{QWEN_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
    payload = {
        "model": "happyhorse-1.1-r2v",
        "input": {
            "prompt": "The woman from [Image 1] walks forward with calm confidence.",
            "media": [{"type": "reference_image", "url": COVER_SAMPLE_IMAGE_URL}],
        },
        "parameters": {"resolution": "720P", "ratio": "16:9", "duration": 5, "watermark": False},
    }
    headers = {
        "Authorization": f"Bearer {dashscope_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            data = await run_provider_step(
                "dashscope_video_submit",
                "video:happyhorse-1.1-r2v:probe",
                lambda: _post_json(http, endpoint, headers, payload),
                extra={"model": payload["model"], "probe": True},
            )
        return {
            "available": bool(data.get("output", {}).get("task_id")),
            "model": payload["model"],
            "task_id": data.get("output", {}).get("task_id"),
            "task_status": data.get("output", {}).get("task_status"),
        }
    except Exception as exc:
        details = _error_details(exc)
        details.update({"model": payload["model"]})
        return details


async def get_provider_status(force_refresh: bool = False) -> dict[str, Any]:
    """Return Qwen/DashScope configuration status without submitting billable probes."""
    configured = bool(os.environ.get("DASHSCOPE_API_KEY", "").strip())
    model = os.environ.get("DASHSCOPE_T2V_MODEL", "happyhorse-1.1-t2v")
    models = {
        "t2v": model,
        "i2v": os.environ.get("DASHSCOPE_I2V_MODEL", "happyhorse-1.1-i2v"),
        "r2v": os.environ.get("DASHSCOPE_R2V_MODEL", "happyhorse-1.1-r2v"),
    }
    error = None if configured else "DASHSCOPE_API_KEY is missing"
    capability = {
        mode: {
            "available": configured,
            "provider": "qwen",
            "adapter": "dashscope",
            "model": selected_model,
            "mode": "configuration_only",
            "error": error,
        }
        for mode, selected_model in models.items()
    }
    return {
        "checked_at": _utc_now(),
        "mode": "configuration_only",
        "qwen": capability,
        "recommended_mode": "qwen_i2v" if configured else "narrated_image_story",
    }

async def _post_json(http: httpx.AsyncClient, url: str, headers: dict, payload: dict):
    r = await http.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()
