from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from job_queue import get_redis
from pipeline.provider_policy import run_provider_step

WAN_VIDEO_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"
WAN_SAMPLE_IMAGE_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250925/thtclx/input1.png"
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


async def _probe_wan_t2v() -> dict[str, Any]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return {
            "available": False,
            "model": "wan2.7-t2v-2026-06-12",
            "error": "DASHSCOPE_API_KEY is missing",
        }

    endpoint = f"{WAN_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
    payload = {
        "model": "wan2.7-t2v-2026-06-12",
        "input": {"prompt": "Probe access for Wan text-to-video"},
        "parameters": {"resolution": "720P", "duration": 5},
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


async def _probe_wan_i2v() -> dict[str, Any]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return {
            "available": False,
            "model": "wan2.7-i2v-2026-04-25",
            "error": "DASHSCOPE_API_KEY is missing",
        }

    endpoint = f"{WAN_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
    payload = {
        "model": "wan2.7-i2v-2026-04-25",
        "input": {
            "prompt": "Probe access for Wan image-to-video",
            "media": [{"type": "first_frame", "url": WAN_SAMPLE_IMAGE_URL}],
        },
        "parameters": {"resolution": "720P", "duration": 5},
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


async def get_provider_status(force_refresh: bool = False) -> dict[str, Any]:
    if not force_refresh:
        cached = await _load_cached_status()
        if cached:
            return cached

    payload = {
        "checked_at": _utc_now(),
        "wan": {
            "t2v": await _probe_wan_t2v(),
            "i2v": await _probe_wan_i2v(),
        },
    }
    if payload["wan"]["i2v"].get("available"):
        payload["recommended_mode"] = "wan_i2v"
    elif payload["wan"]["t2v"].get("available"):
        payload["recommended_mode"] = "wan_t2v"
    else:
        payload["recommended_mode"] = "narrated_image_story"
    await _store_cached_status(payload)
    return payload


async def _post_json(http: httpx.AsyncClient, url: str, headers: dict, payload: dict):
    r = await http.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()
