import os
import json
import asyncio
import httpx
import time
from typing import Optional

from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from pipeline.character_gen import generate_image_bytes
from pipeline.story_agent import build_scene_prompt
from pipeline.provider_status import get_provider_status
from pipeline.provider_policy import run_provider_step
from pipeline.pipeline_config import normalize_pipeline_config
from pipeline.media_tools import extract_last_frame_jpeg
from pipeline.generation_agent import plan_scene_video
from pipeline.provider_executor import execute_ordered_attempts
from pipeline.runtime_context import get_job_context

# ─── Model config ─────────────────────────────────────────────────────────────

DASHSCOPE_VIDEO_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"
AIML_BASE_URL = "https://api.aimlapi.com"

# Video models
DASHSCOPE_HAPPYHORSE_I2V_MODEL = os.getenv("DASHSCOPE_HAPPYHORSE_I2V_MODEL", "happyhorse-1.1-i2v")
DASHSCOPE_HAPPYHORSE_T2V_MODEL = os.getenv("DASHSCOPE_HAPPYHORSE_T2V_MODEL", "happyhorse-1.1-t2v")
DASHSCOPE_HAPPYHORSE_R2V_MODEL = os.getenv("DASHSCOPE_HAPPYHORSE_R2V_MODEL", "happyhorse-1.1-r2v")
DASHSCOPE_WAN_I2V_MODEL = os.getenv("DASHSCOPE_WAN_I2V_MODEL", "wan2.7-i2v")
DASHSCOPE_WAN_T2V_MODEL = os.getenv("DASHSCOPE_WAN_T2V_MODEL", "wan2.7-t2v")
DASHSCOPE_WAN_R2V_MODEL = os.getenv("DASHSCOPE_WAN_R2V_MODEL", "wan2.7-r2v")
AIML_I2V_MODEL = "alibaba/wan2.7-i2v"
AIML_T2V_MODEL = "alibaba/wan2.7-t2v"


# ─── Public API ───────────────────────────────────────────────────────────────

async def generate_scene_clip(
    story_id: str,
    episode_id: str,
    scene: dict,
    story_context: dict,
    character_refs: list[str],
    previous_exit_frame_url: Optional[str],
    previous_scene_summary: str = "",
    style: str = "anime",
    preferred_provider: Optional[str] = None,
) -> dict:
    scene_number = scene["scene_number"]
    prompt = await build_scene_prompt(scene, story_context, previous_scene_summary, style)
    pipeline_config = normalize_pipeline_config(
        story_context.get("pipeline_config"),
        workflow_state=story_context.get("workflow_state"),
    )
    media_config = pipeline_config.get("media", {})
    continuity_config = pipeline_config.get("continuity", {})
    requested_ratio = _requested_video_ratio(story_context, pipeline_config)
    requested_duration = int(media_config.get("duration_seconds") or 5)
    max_refs = int(continuity_config.get("max_reference_images") or 8)
    reference_images = [u for u in character_refs if u][:max_refs]
    if not reference_images and previous_exit_frame_url:
        reference_images = [previous_exit_frame_url]

    seed_frame_url = None
    provider_status = await get_provider_status()
    job_ctx = get_job_context() or {}
    agent_plan = await plan_scene_video(
        story_id=story_id,
        episode_id=episode_id,
        scene_id=str(scene.get("id")) if scene.get("id") else None,
        job_id=job_ctx.get("job_id"),
        scene_number=scene_number,
        reference_count=len(reference_images),
        provider_status=provider_status,
        pipeline_config=pipeline_config,
        preferred_provider=preferred_provider,
    )
    if agent_plan.should_handoff:
        raise RuntimeError(agent_plan.user_message or agent_plan.handoff_reason or "Video generation requires user intervention")

    if reference_images:
        prompt = f"{prompt}\n\nMaintain continuity with the available character and scene reference images."

    async def _run_attempt(attempt: dict) -> Optional[str]:
        attempt_refs = _reference_images_for_attempt(reference_images, attempt)
        if attempt.get("provider") == "dashscope":
            return await _try_dashscope_video(
                prompt,
                reference_images=attempt_refs,
                requested_ratio=requested_ratio,
                requested_duration=requested_duration,
                model=attempt.get("model"),
                capability=attempt.get("capability"),
            )
        if attempt.get("provider") == "aiml":
            return await _try_aiml_video(
                prompt,
                image_url=attempt_refs[0] if attempt_refs else None,
                requested_duration=requested_duration,
                model=attempt.get("model"),
            )
        return None

    video_url, selected_attempt, failed_attempts = await execute_ordered_attempts(agent_plan.attempts, _run_attempt)
    provider_used = selected_attempt.get("provider")

    # Download once — reuse for both B2 upload and exit frame extraction
    clip_bytes = await download_url_to_bytes(video_url)

    clip_key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}.mp4")
    b2_clip_url = upload_bytes(clip_bytes, clip_key, "video/mp4")

    # Extract exit frame from in-memory bytes (no B2 read needed)
    exit_frame_url = await extract_exit_frame_from_bytes(clip_bytes, story_id, episode_id, scene_number)

    return {
        "clip_url": b2_clip_url,
        "exit_frame_url": exit_frame_url,
        "duration": float(requested_duration),
        "prompt": prompt,
        "refs_used": len(reference_images),
        "seed_frame_url": seed_frame_url,
        "video_provider": provider_used,
        "video_model": selected_attempt.get("model"),
        "video_ratio": requested_ratio,
        "agent_video_plan": agent_plan.model_dump(),
        "failed_video_attempts": failed_attempts,
    }


async def _build_seed_frame(story_id: str, episode_id: str, scene_number: int, prompt: str) -> Optional[str]:
    image_bytes = await generate_image_bytes(f"{prompt}, single cinematic first frame, anime style")
    if not image_bytes:
        return None
    key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}_seed.jpg")
    return upload_bytes(image_bytes, key, "image/jpeg")


def _requested_video_ratio(story_context: dict, pipeline_config: dict | None = None) -> str:
    configured_ratio = (pipeline_config or {}).get("media", {}).get("ratio")
    if configured_ratio in {"16:9", "9:16", "1:1", "4:3", "3:4"}:
        return configured_ratio
    workflow_state = story_context.get("workflow_state") or {}
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except Exception:
            workflow_state = {}
    if not isinstance(workflow_state, dict):
        workflow_state = {}
    ratio = workflow_state.get("requested_video_ratio") or story_context.get("requested_video_ratio")
    if ratio in {"16:9", "9:16", "1:1", "4:3", "3:4"}:
        return ratio
    return os.getenv("VIDEO_DEFAULT_RATIO", "16:9")


# ─── DashScope video ──────────────────────────────────────────────────────────

def _dashscope_video_payload(
    prompt: str,
    *,
    reference_images: list[str],
    requested_ratio: str,
    requested_duration: int,
    model: str | None = None,
    capability: str | None = None,
) -> tuple[str, dict]:
    endpoint = f"{DASHSCOPE_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
    capability = capability or ("r2v" if len(reference_images) >= 2 else "i2v" if len(reference_images) == 1 else "t2v")
    if capability == "r2v" and reference_images:
        payload = {
            "model": model or DASHSCOPE_HAPPYHORSE_R2V_MODEL,
            "input": {
                "prompt": _reference_prompt(prompt, len(reference_images)),
                "media": [{"type": "reference_image", "url": url} for url in reference_images[:9]],
            },
            "parameters": {
                "resolution": "1080P",
                "ratio": requested_ratio,
                "duration": requested_duration,
                "watermark": False,
            },
        }
        return endpoint, payload
    if capability == "i2v" and reference_images:
        payload = {
            "model": model or DASHSCOPE_HAPPYHORSE_I2V_MODEL,
            "input": {
                "prompt": prompt,
                "media": [{"type": "first_frame", "url": reference_images[0]}],
            },
            "parameters": {"resolution": "1080P", "ratio": requested_ratio, "duration": requested_duration, "watermark": False},
        }
        return endpoint, payload
    payload = {
        "model": model or DASHSCOPE_HAPPYHORSE_T2V_MODEL,
        "input": {
            "prompt": prompt,
        },
        "parameters": {
            "resolution": "1080P",
            "ratio": requested_ratio,
            "duration": requested_duration,
            "prompt_extend": True,
            "watermark": False,
        },
    }
    return endpoint, payload


def _reference_prompt(prompt: str, ref_count: int) -> str:
    if ref_count <= 0:
        return prompt
    if ref_count == 1:
        return f"{prompt}\n\nPreserve the appearance from [Image 1] throughout the shot."
    refs = ", ".join(f"[Image {i}]" for i in range(1, ref_count + 1))
    return f"{prompt}\n\nUse {refs} as the reference set. Keep identities, outfits, and scene styling consistent across them."


def _reference_images_for_attempt(reference_images: list[str], attempt: dict) -> list[str]:
    capability = attempt.get("capability")
    max_refs = int(attempt.get("max_refs") or 0)
    if capability == "t2v" or max_refs <= 0:
        return []
    if capability == "i2v":
        return reference_images[:1]
    return reference_images[:max_refs]


def _provider_preference_order(preferred_provider: Optional[str]) -> list[str]:
    if preferred_provider == "aiml":
        return ["aiml", "dashscope"]
    if preferred_provider == "dashscope":
        return ["dashscope", "aiml"]
    return ["dashscope", "aiml"]


async def _try_dashscope_video(
    prompt: str,
    *,
    reference_images: list[str] | None = None,
    requested_ratio: str = "16:9",
    requested_duration: int = 5,
    model: str | None = None,
    capability: str | None = None,
) -> Optional[str]:
    """Try DashScope (Qwen Cloud) video generation. Returns video URL or None on failure."""
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return None

    try:
        headers = {
            "Authorization": f"Bearer {dashscope_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        endpoint, payload = _dashscope_video_payload(
            prompt,
            reference_images=reference_images or [],
            requested_ratio=requested_ratio,
            requested_duration=requested_duration,
            model=model,
            capability=capability,
        )

        async with httpx.AsyncClient(timeout=30) as http:
            data = await run_provider_step(
                "dashscope_video_submit",
                "video:dashscope:submit",
                lambda: _post_json(http, endpoint, headers, payload),
                extra={"model": payload["model"]},
                extra_builder=lambda result: {
                    "model": payload["model"],
                    "task_id": result.get("output", {}).get("task_id"),
                    "provider_status": result.get("output", {}).get("task_status"),
                },
            )

        task_id = data["output"]["task_id"]
        print(f"[scene_gen] DashScope video task submitted: {task_id}")
        return await _poll_dashscope_video(task_id, dashscope_key)

    except Exception as e:
        print(f"[scene_gen] DashScope video failed: {str(e)[:120]}")
        return None


async def _poll_dashscope_video(task_id: str, api_key: str, timeout: int = 600) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + timeout

    while time.time() < deadline:
        await asyncio.sleep(10)
        try:
            async with httpx.AsyncClient(timeout=30) as http:
                data = await run_provider_step(
                    "dashscope_video_poll",
                    "video:dashscope:poll",
                    lambda: _get_json(
                        http,
                        f"{DASHSCOPE_VIDEO_BASE}/tasks/{task_id}",
                        headers=headers,
                    ),
                    extra={"task_id": task_id},
                )

            status = data["output"]["task_status"].lower()
            print(f"[scene_gen] DashScope task {task_id}: {status}")

            if status == "succeeded":
                video_url = data["output"].get("video_url") or data["output"].get("results", [{}])[0].get("url")
                if video_url:
                    return video_url
                raise RuntimeError(f"DashScope task succeeded but no video_url: {data}")
            elif status in ("failed", "cancelled", "unknown"):
                raise RuntimeError(f"DashScope video task failed: {data['output'].get('message', status)}")

        except asyncio.TimeoutError:
            continue
        except RuntimeError:
            raise
        except Exception as e:
            print(f"[scene_gen] DashScope poll error: {e}")
            await asyncio.sleep(5)

    raise TimeoutError(f"DashScope video task {task_id} timed out after {timeout}s")


# ─── AIML video ───────────────────────────────────────────────────────────────

async def _try_aiml_video(
    prompt: str,
    image_url: Optional[str] = None,
    requested_duration: int = 5,
    model: str | None = None,
) -> str:
    """AIML video generation — primary if DashScope unavailable, else fallback."""
    aiml_key = os.environ.get("AIML_API_KEY", "")
    if not aiml_key:
        raise RuntimeError("No AIML_API_KEY configured for video fallback")

    headers = {
        "Authorization": f"Bearer {aiml_key}",
        "Content-Type": "application/json",
    }

    if image_url:
        payload = {"model": model or AIML_I2V_MODEL, "prompt": prompt, "image_url": image_url, "duration": requested_duration}
    else:
        payload = {"model": model or AIML_T2V_MODEL, "prompt": prompt, "duration": requested_duration}

    async with httpx.AsyncClient(timeout=30) as http:
        data = await run_provider_step(
            "aiml_video_submit",
            "video:aiml:submit",
            lambda: _post_json(http, f"{AIML_BASE_URL}/v2/video/generations", headers, payload),
            extra={"model": payload["model"]},
            extra_builder=lambda result: {
                "model": payload["model"],
                "task_id": result.get("id") or result.get("generation_id") or result.get("task_id"),
            },
        )

    task_id = data.get("id") or data.get("generation_id") or data.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task ID from AIML video generation: {data}")

    return await _poll_aiml_video(task_id, aiml_key)


async def _poll_aiml_video(task_id: str, api_key: str, timeout: int = 600) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + timeout

    while time.time() < deadline:
        await asyncio.sleep(15)
        try:
            async with httpx.AsyncClient(timeout=30) as http:
                data = await run_provider_step(
                    "aiml_video_poll",
                    "video:aiml:poll",
                    lambda: _get_json(
                        http,
                        f"{AIML_BASE_URL}/v2/video/generations",
                        headers=headers,
                        params={"generation_id": task_id},
                    ),
                    extra={"task_id": task_id},
                )

            status = (data.get("status") or data.get("task_status") or "").lower()
            print(f"[scene_gen] AIML task {task_id}: {status}")

            if status in ("completed", "succeeded", "success", "finished"):
                video_obj = data.get("video")
                if isinstance(video_obj, dict) and video_obj.get("url"):
                    return video_obj["url"]
                for key in ["video_url", "url", "output_url"]:
                    if data.get(key):
                        return data[key]
                for nest_key in ["output", "result", "data", "generation"]:
                    nested = data.get(nest_key)
                    if isinstance(nested, dict):
                        inner = nested.get("video")
                        if isinstance(inner, dict) and inner.get("url"):
                            return inner["url"]
                        for vkey in ["video_url", "url"]:
                            if nested.get(vkey):
                                return nested[vkey]
                raise RuntimeError(f"AIML task succeeded but no video URL: {data}")

            elif status in ("failed", "error", "cancelled", "canceled"):
                raise RuntimeError(f"AIML video task failed: {data}")

        except (asyncio.TimeoutError, RuntimeError):
            raise
        except Exception as e:
            print(f"[scene_gen] AIML poll error (will retry): {e}")
            await asyncio.sleep(5)

    raise TimeoutError(f"AIML video task {task_id} timed out after {timeout}s")


async def _generate_video(
    prompt: str,
    *,
    reference_images: list[str] | None = None,
    requested_ratio: str = "16:9",
    requested_duration: int = 5,
    preferred_provider: Optional[str] = None,
) -> tuple[str, str]:
    """Generate video with provider ordering controlled by the coordinator."""
    reference_images = [u for u in (reference_images or []) if u][:9]
    provider_order = _provider_preference_order(preferred_provider)
    first_ref = reference_images[0] if reference_images else None

    for provider in provider_order:
        try:
            if provider == "dashscope":
                result = await _try_dashscope_video(
                    prompt,
                    reference_images=reference_images,
                    requested_ratio=requested_ratio,
                    requested_duration=requested_duration,
                )
                if result:
                    print("[scene_gen] Video generated via DashScope (Qwen Cloud)")
                    return result, "dashscope"
                if reference_images:
                    result = await _try_dashscope_video(
                        prompt,
                        reference_images=[],
                        requested_ratio=requested_ratio,
                        requested_duration=requested_duration,
                    )
                    if result:
                        print("[scene_gen] Video generated via DashScope T2V fallback")
                        return result, "dashscope"
            else:
                result = await _try_aiml_video(prompt, first_ref, requested_duration=requested_duration)
                if result:
                    print("[scene_gen] Video generated via AIML fallback")
                    return result, "aiml"
        except Exception as exc:
            print(f"[scene_gen] {provider} generation failed: {str(exc)[:140]}")
            continue

    raise RuntimeError("All video providers failed")


async def _post_json(http: httpx.AsyncClient, url: str, headers: dict, payload: dict):
    r = await http.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


async def _get_json(http: httpx.AsyncClient, url: str, headers: dict, params: dict | None = None):
    r = await http.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


# ─── Exit frame extraction ────────────────────────────────────────────────────

async def extract_exit_frame_from_bytes(
    clip_bytes: bytes,
    story_id: str,
    episode_id: str,
    scene_number: int,
) -> Optional[str]:
    """Extract last frame from in-memory video bytes and upload to B2.
    Never reads from B2 — works entirely from bytes we already downloaded."""
    try:
        frame_bytes = await extract_last_frame_jpeg(clip_bytes)
        key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}_exit.jpg")
        return upload_bytes(frame_bytes, key, "image/jpeg")

    except Exception as e:
        print(f"[scene_gen] Exit frame extraction failed: {e}")
        return None
