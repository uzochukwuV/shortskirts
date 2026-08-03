"""
scene_gen.py — Video clip generation for a single scene.

Implements generate_scene_clip(), the core function called by
generation_coordinator.py to turn a scene plan into an actual video clip.

Provider priority:
  1. DashScope (Alibaba) — through the GenBlaze adapter
  2. Novita AI             — through the GenBlaze adapter
  3. Replicate / Veo3     — through the GenBlaze adapters

Each provider is tried in order; the first successful result is returned.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any

import httpx

from storage.b2 import build_key, upload_bytes, download_url_to_bytes
from pipeline.media_tools import extract_last_frame_png
from pipeline.providers.provider_router import ProviderType, get_router
from genblaze_core import Modality
from genblaze_core.models.asset import Asset
from genblaze_core.models.step import Step

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/api/v1"
)
NOVITA_BASE_URL = "https://api.novita.ai"

# Max duration — cap at 3 s to conserve credits (user preference)
MAX_DURATION_SECONDS = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "3"))
# HappyHorse/DashScope requires at least 3 seconds.
MIN_DURATION_SECONDS = 3

POLL_INTERVAL = 8  # seconds between status polls
MAX_POLL_SECONDS = 600  # 10 minutes per attempt

GENBLAZE_PROVIDER_TYPES = {
    "dashscope": ProviderType.DASHSCOPE,
    "novita": ProviderType.NOVITA,
    "replicate": ProviderType.REPLICATE,
    "veo3": ProviderType.VEO3,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp_duration(requested: int | float | None) -> int:
    """Return a safe duration in [MIN, MAX]."""
    d = int(requested or MAX_DURATION_SECONDS)
    return max(MIN_DURATION_SECONDS, min(d, MAX_DURATION_SECONDS))


def _build_prompt(scene: dict[str, Any], style: str = "", previous_summary: str = "") -> str:
    """Assemble a rich video generation prompt from scene metadata."""
    parts: list[str] = []

    if style:
        parts.append(f"{style} style,")

    vp = scene.get("visual_prompt") or scene.get("description") or scene.get("prompt") or ""
    if vp:
        parts.append(vp)

    location = scene.get("location", "")
    if location:
        parts.append(f"Setting: {location}.")

    mood = scene.get("mood", "")
    if mood:
        parts.append(f"Mood: {mood}.")

    action = scene.get("action", "")
    if action:
        parts.append(f"Action: {action}.")

    if previous_summary:
        parts.append(f"Continuing from: {previous_summary}.")

    return " ".join(parts)[:1000]


# ---------------------------------------------------------------------------
# DashScope provider
# ---------------------------------------------------------------------------


async def _dashscope_generate_video(
    prompt: str,
    reference_images: list[str],
    duration: int,
    ratio: str = "16:9",
) -> str:
    """Submit a DashScope video generation task, poll until done, return video URL."""
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    # Choose model and capability based on number of reference images
    num_refs = len([u for u in reference_images if u])
    if num_refs >= 2:
        model = os.getenv("DASHSCOPE_R2V_MODEL", "happyhorse-1.1-r2v")
        capability = "r2v"
    elif num_refs == 1:
        model = os.getenv("DASHSCOPE_I2V_MODEL", "happyhorse-1.1-i2v")
        capability = "i2v"
    else:
        model = os.getenv("DASHSCOPE_T2V_MODEL", "happyhorse-1.1-t2v")
        capability = "t2v"

    import random

    seed = random.randint(0, 2_147_483_647)
    params: dict[str, Any] = {
        "resolution": "720P",
        "ratio": ratio,
        "duration": duration,
        "watermark": False,
        "seed": seed,
    }

    endpoint = "/services/aigc/video-generation/video-synthesis"

    clean_refs = [u for u in reference_images if u]

    if capability == "r2v" and clean_refs:
        payload = {
            "model": model,
            "input": {
                "prompt": prompt,
                "reference_images": [{"image": u} for u in clean_refs[:8]],
            },
            "parameters": params,
        }
    elif capability == "i2v" and clean_refs:
        payload = {
            "model": model,
            "input": {
                "prompt": prompt,
                "img_url": clean_refs[0],
            },
            "parameters": params,
        }
    else:
        # t2v
        params["prompt_extend"] = True
        payload = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": params,
        }

    async with httpx.AsyncClient(
        base_url=DASHSCOPE_BASE_URL,
        timeout=120,
    ) as client:
        resp = await client.post(endpoint, headers=headers, json=payload)

    if resp.status_code >= 400:
        raise RuntimeError(
            f"DashScope submit failed ({resp.status_code}): {resp.text[:500]}"
        )

    data = resp.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"DashScope submit returned no task_id: {data}")

    print(f"[scene_gen:dashscope] task submitted: {task_id} model={model}")

    # Poll for completion
    deadline = time.monotonic() + MAX_POLL_SECONDS
    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        async with httpx.AsyncClient(
            base_url=DASHSCOPE_BASE_URL,
            timeout=30,
        ) as client:
            poll_resp = await client.get(
                f"/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )

        if poll_resp.status_code >= 400:
            raise RuntimeError(
                f"DashScope poll failed ({poll_resp.status_code}): {poll_resp.text[:300]}"
            )

        poll_data = poll_resp.json()
        status = poll_data.get("output", {}).get("task_status", "").upper()
        print(f"[scene_gen:dashscope] task {task_id}: {status}")

        if status in ("SUCCEEDED", "SUCCESS"):
            output = poll_data["output"]
            video_url = (
                output.get("video_url")
                or output.get("url")
                or (
                    output.get("results", [{}])[0].get("video_url")
                    if output.get("results")
                    else None
                )
            )
            if not video_url:
                raise RuntimeError(
                    f"DashScope task succeeded but no video_url: {output}"
                )
            return video_url

        if status in ("FAILED", "CANCELLED", "CANCELED"):
            msg = poll_data.get("output", {}).get("message") or status
            raise RuntimeError(f"DashScope task {status}: {msg}")

    raise RuntimeError(f"DashScope task {task_id} timed out after {MAX_POLL_SECONDS}s")


# ---------------------------------------------------------------------------
# Novita provider
# ---------------------------------------------------------------------------


async def _novita_generate_video(
    prompt: str,
    reference_images: list[str],
    duration: int,
) -> str:
    """Submit Novita AI wan2.7 task, poll until done, return video URL."""
    api_key = os.environ.get("NOVITA_API_KEY", "")
    if not api_key:
        raise RuntimeError("NOVITA_API_KEY not set")

    clean_refs = [u for u in reference_images if u]
    num_refs = len(clean_refs)

    if num_refs >= 2:
        endpoint = "/v3/async/wan2.7-r2v"
        payload = {
            "model_name": "wan2.7-r2v",
            "extra": {"response_image_type": "png"},
            "request": {
                "prompt": prompt,
                "negative_prompt": "",
                "reference_images": [{"image_url": u} for u in clean_refs[:4]],
                "width": 1280,
                "height": 720,
                "duration": duration,
            },
        }
    elif num_refs == 1:
        endpoint = "/v3/async/wan2.7-i2v"
        payload = {
            "model_name": "wan2.7-i2v",
            "extra": {"response_image_type": "png"},
            "request": {
                "prompt": prompt,
                "image_url": clean_refs[0],
                "width": 1280,
                "height": 720,
                "duration": duration,
            },
        }
    else:
        endpoint = "/v3/async/wan2.7-t2v"
        payload = {
            "model_name": "wan2.7-t2v",
            "extra": {"response_image_type": "png"},
            "request": {
                "prompt": prompt,
                "width": 1280,
                "height": 720,
                "duration": duration,
            },
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=NOVITA_BASE_URL, timeout=120) as client:
        resp = await client.post(endpoint, headers=headers, json=payload)

    if resp.status_code >= 400:
        raise RuntimeError(
            f"Novita submit failed ({resp.status_code}): {resp.text[:500]}"
        )

    data = resp.json()
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError(f"Novita submit returned no task_id: {data}")

    print(f"[scene_gen:novita] task submitted: {task_id}")

    deadline = time.monotonic() + MAX_POLL_SECONDS
    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        async with httpx.AsyncClient(base_url=NOVITA_BASE_URL, timeout=30) as client:
            poll_resp = await client.get(
                f"/v3/async/task-result?task_id={task_id}",
                headers=headers,
            )

        if poll_resp.status_code >= 400:
            raise RuntimeError(
                f"Novita poll failed ({poll_resp.status_code}): {poll_resp.text[:300]}"
            )

        poll_data = poll_resp.json()
        status = (poll_data.get("task", {}).get("status") or "").upper()
        print(f"[scene_gen:novita] task {task_id}: {status}")

        if status in ("SUCCEED", "SUCCEEDED"):
            videos = poll_data.get("videos") or []
            if videos:
                return videos[0].get("video_url") or videos[0].get("url") or ""
            raise RuntimeError(f"Novita task succeeded but no video: {poll_data}")

        if status in ("FAILED", "CANCELED"):
            raise RuntimeError(f"Novita task {status}: {poll_data}")

    raise RuntimeError(f"Novita task {task_id} timed out after {MAX_POLL_SECONDS}s")


# ---------------------------------------------------------------------------
# AIML provider (fallback)
# ---------------------------------------------------------------------------


async def _aiml_generate_video(
    prompt: str,
    reference_images: list[str],
    duration: int,
) -> str:
    """Submit AIML API wan2.7 task, poll until done, return video URL."""
    api_key = os.environ.get("AIML_API_KEY", "")
    if not api_key:
        raise RuntimeError("AIML_API_KEY not set")

    clean_refs = [u for u in reference_images if u]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if clean_refs:
        model = "alibaba/wan2.7-i2v"
        payload = {
            "model": model,
            "prompt": prompt,
            "image_url": clean_refs[0],
            "duration": duration,
        }
    else:
        model = "alibaba/wan2.7-t2v"
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
        }

    async with httpx.AsyncClient(base_url=AIML_BASE_URL, timeout=120) as client:
        resp = await client.post("/v1/video/generations", headers=headers, json=payload)

    if resp.status_code >= 400:
        raise RuntimeError(
            f"AIML submit failed ({resp.status_code}): {resp.text[:500]}"
        )

    data = resp.json()
    generation_id = data.get("id")
    if not generation_id:
        raise RuntimeError(f"AIML submit returned no id: {data}")

    print(f"[scene_gen:aiml] generation submitted: {generation_id} model={model}")

    deadline = time.monotonic() + MAX_POLL_SECONDS
    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_INTERVAL)
        async with httpx.AsyncClient(base_url=AIML_BASE_URL, timeout=30) as client:
            poll_resp = await client.get(
                f"/v1/video/generations/{generation_id}",
                headers=headers,
            )

        if poll_resp.status_code >= 400:
            raise RuntimeError(
                f"AIML poll failed ({poll_resp.status_code}): {poll_resp.text[:300]}"
            )

        poll_data = poll_resp.json()
        status = (poll_data.get("status") or "").lower()
        print(f"[scene_gen:aiml] generation {generation_id}: {status}")

        if status in ("completed", "succeeded", "success"):
            url = (
                poll_data.get("video", {}).get("url")
                or poll_data.get("output", {}).get("url")
                or poll_data.get("url")
            )
            if url:
                return url
            raise RuntimeError(f"AIML generation completed but no video URL: {poll_data}")

        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"AIML generation {status}: {poll_data}")

    raise RuntimeError(f"AIML generation {generation_id} timed out after {MAX_POLL_SECONDS}s")


def _genblaze_model(provider: str, ref_count: int) -> str:
    """Select a model understood by the selected GenBlaze adapter."""
    if provider == "dashscope":
        if ref_count >= 2:
            return os.getenv("DASHSCOPE_R2V_MODEL", "happyhorse-1.1-r2v")
        if ref_count == 1:
            return os.getenv("DASHSCOPE_I2V_MODEL", "happyhorse-1.1-i2v")
        return os.getenv("DASHSCOPE_T2V_MODEL", "happyhorse-1.1-t2v")
    if provider == "novita":
        if ref_count >= 2:
            return "wan2.7-r2v"
        if ref_count == 1:
            return "wan2.7-i2v"
        return "wan2.7-t2v"
    if provider == "replicate":
        return os.getenv("REPLICATE_VIDEO_MODEL", "luosi-npn/ltxv-hunyuan-t2v")
    if provider == "veo3":
        return os.getenv("VEO3_VIDEO_MODEL", "veo3")
    raise RuntimeError(f"Unsupported GenBlaze video provider: {provider}")


def _genblaze_generate_video_sync(
    *,
    provider: str,
    prompt: str,
    reference_images: list[str],
    duration: int,
    ratio: str,
) -> tuple[str, str]:
    """Run GenBlaze submit → poll → fetch using the repository's provider router.

    The adapters are synchronous, so the async caller runs this function in a
    worker thread. This keeps the event loop available for job heartbeats.
    """
    provider_type = GENBLAZE_PROVIDER_TYPES.get(provider)
    if provider_type is None:
        raise RuntimeError(f"Unsupported GenBlaze video provider: {provider}")

    ref_assets = [Asset(url=url, media_type="image/*") for url in reference_images if url]
    model = _genblaze_model(provider, len(ref_assets))
    params: dict[str, Any] = {
        "duration": duration,
        "ratio": ratio,
        "resolution": "720P",
        "watermark": False,
    }
    if provider == "novita":
        params["mode"] = "r2v" if len(ref_assets) >= 2 else "i2v" if ref_assets else "t2v"
        params["size"] = "1280*720"
    if provider == "replicate":
        params["aspect_ratio"] = ratio

    router = get_router()
    step = Step(
        provider=router.get_provider(provider_type).name,
        model=model,
        prompt=prompt,
        modality=Modality.VIDEO,
        inputs=ref_assets,
        params=params,
    )
    task_id, provider_name = router.generate_video(step, provider_type)
    print(f"[scene_gen:genblaze] submitted provider={provider} task={task_id} model={model}")

    deadline = time.monotonic() + MAX_POLL_SECONDS
    while time.monotonic() < deadline:
        status = router.poll_status(task_id, provider_name)
        print(f"[scene_gen:genblaze] provider={provider} task={task_id} status={status}")
        if status in {"SUCCEEDED", "SUCCESS"}:
            break
        if status in {"FAILED", "CANCELLED", "CANCELED"}:
            raise RuntimeError(f"GenBlaze {provider} task {task_id} failed: {status}")
        time.sleep(1)
    else:
        raise RuntimeError(f"GenBlaze {provider} task {task_id} timed out")

    completed_step = router.fetch_video(task_id, step, provider_name)
    if not completed_step.assets:
        raise RuntimeError(f"GenBlaze {provider} returned no video asset")
    return str(completed_step.assets[0].url), model


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def generate_scene_clip(
    *,
    story_id: str,
    episode_id: str,
    scene: dict[str, Any],
    story_context: dict[str, Any] | None = None,
    character_refs: list[str] | None = None,
    previous_exit_frame_url: str | None = None,
    previous_scene_summary: str = "",
    style: str = "",
    preferred_provider: str | None = None,
) -> dict[str, Any]:
    """
    Generate a video clip for a single scene.

    Returns a dict with:
        clip_url        — B2 URL of the generated .mp4
        exit_frame_url  — B2 URL of the last frame (PNG) for continuity
        image_url       — None (video output)
        video_provider  — provider name used
        video_model     — model name used
        duration        — actual duration in seconds
        refs_used       — number of reference images used
        media_kind      — "video"
        prompt          — prompt sent to the provider
        agent_video_plan — {"attempts": [...]}
    """
    character_refs = character_refs or []
    story_context = story_context or {}

    # Build the prompt
    prompt = _build_prompt(scene, style=style, previous_summary=previous_scene_summary)

    # Assemble reference images (continuity frame first, then character refs)
    ref_images: list[str] = []
    if previous_exit_frame_url:
        ref_images.append(previous_exit_frame_url)
    for ref in character_refs:
        if ref and ref not in ref_images:
            ref_images.append(ref)

    # Requested duration (capped)
    pipeline_config = story_context.get("pipeline_config", {})
    requested_duration = (
        pipeline_config.get("media", {}).get("duration_seconds")
        or scene.get("duration_seconds")
        or MAX_DURATION_SECONDS
    )
    duration = _clamp_duration(requested_duration)

    ratio = pipeline_config.get("media", {}).get("ratio", "16:9")

    # Build provider attempt order. AIML is intentionally excluded until its
    # API is restored; all active video calls go through GenBlaze adapters.
    providers_order: list[str] = []
    if preferred_provider and preferred_provider != "aiml":
        providers_order.append(preferred_provider)

    pipeline_prefs = (
        pipeline_config.get("providers", {}).get("video_preference") or []
    )
    for p in pipeline_prefs:
        if p != "aiml" and p not in providers_order:
            providers_order.append(p)

    # Always include configured GenBlaze providers as fallbacks
    for p in ("dashscope", "novita", "replicate", "veo3"):
        if p not in providers_order:
            providers_order.append(p)

    attempts: list[dict] = []
    last_error: Exception | None = None
    video_url: str | None = None
    used_provider: str = ""
    used_model: str = ""

    for provider in providers_order:
        try:
            if provider not in GENBLAZE_PROVIDER_TYPES:
                continue
            env_key = {
                "dashscope": "DASHSCOPE_API_KEY",
                "novita": "NOVITA_API_KEY",
                "replicate": "REPLICATE_API_KEY",
                "veo3": "VEO3_API_KEY",
            }[provider]
            if not os.environ.get(env_key):
                continue
            print(f"[scene_gen] Trying GenBlaze/{provider} (duration={duration}s, refs={len(ref_images)})")
            video_url, used_model = await asyncio.to_thread(
                _genblaze_generate_video_sync,
                provider=provider,
                prompt=prompt,
                reference_images=ref_images,
                duration=duration,
                ratio=ratio,
            )
            used_provider = provider
            attempts.append({
                "provider": provider,
                "path": "genblaze",
                "model": used_model,
                "status": "success",
            })
            break

        except Exception as exc:
            print(f"[scene_gen] Provider {provider} failed: {exc}")
            attempts.append({"provider": provider, "model": "", "status": "failed", "error": str(exc)[:200]})
            last_error = exc
            continue

    if not video_url:
        raise RuntimeError(
            f"All provider attempts failed. Last error: {last_error}"
        )

    print(f"[scene_gen] Video generated by {used_provider}: {video_url[:80]}...")

    # Download video bytes and upload to B2 for permanent storage
    scene_num = scene.get("scene_number", uuid.uuid4().hex[:6])
    clip_key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_num}.mp4")

    try:
        video_bytes = await download_url_to_bytes(video_url)
        clip_b2_url = upload_bytes(video_bytes, clip_key, "video/mp4")
        print(f"[scene_gen] Uploaded clip to B2: {clip_key}")
    except Exception as exc:
        print(f"[scene_gen] WARNING: Could not upload to B2, using provider URL: {exc}")
        clip_b2_url = video_url
        video_bytes = None

    # Extract exit frame (last frame) for scene continuity
    exit_frame_url: str | None = None
    if video_bytes:
        try:
            frame_bytes = await extract_last_frame_png(video_bytes)
            frame_key = build_key(
                story_id, "episodes", episode_id, "scenes", f"scene_{scene_num}_exit.png"
            )
            exit_frame_url = upload_bytes(frame_bytes, frame_key, "image/png")
            print(f"[scene_gen] Uploaded exit frame to B2: {frame_key}")
        except Exception as exc:
            print(f"[scene_gen] WARNING: Could not extract exit frame: {exc}")

    return {
        "clip_url": clip_b2_url,
        "image_url": None,
        "exit_frame_url": exit_frame_url,
        "video_provider": used_provider,
        "video_model": used_model,
        "duration": float(duration),
        "refs_used": len([u for u in ref_images if u]),
        "media_kind": "video",
        "prompt": prompt,
        "agent_video_plan": {"attempts": attempts},
    }
