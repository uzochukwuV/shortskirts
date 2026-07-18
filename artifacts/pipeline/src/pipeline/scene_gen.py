import os
import io
import asyncio
import httpx
import time
from typing import Optional

from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from pipeline.story_agent import build_scene_prompt
from pipeline.provider_policy import run_provider_step

# ─── Model config ─────────────────────────────────────────────────────────────

DASHSCOPE_VIDEO_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"
AIML_BASE_URL = "https://api.aimlapi.com"

# Video models
DASHSCOPE_I2V_MODEL = "wan2.7-i2v-2026-04-25"
DASHSCOPE_T2V_MODEL = "wan2.7-t2v-2026-06-12"
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
) -> dict:
    scene_number = scene["scene_number"]
    prompt = await build_scene_prompt(scene, story_context, previous_scene_summary, style)

    # Reference image: prefer character ref, then exit frame for continuity
    reference_image = None
    if character_refs:
        reference_image = character_refs[0]
    elif previous_exit_frame_url:
        reference_image = previous_exit_frame_url

    # Try DashScope video first, fall back to AIML
    video_url = await _generate_video(prompt, reference_image)

    # Download once — reuse for both B2 upload and exit frame extraction
    clip_bytes = await download_url_to_bytes(video_url)

    clip_key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}.mp4")
    b2_clip_url = upload_bytes(clip_bytes, clip_key, "video/mp4")

    # Extract exit frame from in-memory bytes (no B2 read needed)
    exit_frame_url = await extract_exit_frame_from_bytes(clip_bytes, story_id, episode_id, scene_number)

    return {
        "clip_url": b2_clip_url,
        "exit_frame_url": exit_frame_url,
        "duration": 5.0,
        "prompt": prompt,
        "refs_used": 1 if reference_image else 0,
    }


# ─── DashScope video ──────────────────────────────────────────────────────────

async def _try_dashscope_video(prompt: str, image_url: Optional[str] = None) -> Optional[str]:
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

        if image_url:
            endpoint = f"{DASHSCOPE_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
            payload = {
                "model": DASHSCOPE_I2V_MODEL,
                "input": {
                    "prompt": prompt,
                    "media": [{"type": "first_frame", "url": image_url}],
                },
                "parameters": {"resolution": "720P", "duration": 5},
            }
        else:
            endpoint = f"{DASHSCOPE_VIDEO_BASE}/services/aigc/video-generation/video-synthesis"
            payload = {
                "model": DASHSCOPE_T2V_MODEL,
                "input": {"prompt": prompt},
                "parameters": {"resolution": "720P", "duration": 5},
            }

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

async def _try_aiml_video(prompt: str, image_url: Optional[str] = None) -> str:
    """AIML video generation — primary if DashScope unavailable, else fallback."""
    aiml_key = os.environ.get("AIML_API_KEY", "")
    if not aiml_key:
        raise RuntimeError("No AIML_API_KEY configured for video fallback")

    headers = {
        "Authorization": f"Bearer {aiml_key}",
        "Content-Type": "application/json",
    }

    if image_url:
        payload = {"model": AIML_I2V_MODEL, "prompt": prompt, "image_url": image_url, "duration": 5}
    else:
        payload = {"model": AIML_T2V_MODEL, "prompt": prompt, "duration": 5}

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


async def _generate_video(prompt: str, image_url: Optional[str] = None) -> str:
    """Try DashScope first, fall back to AIML."""
    result = await _try_dashscope_video(prompt, image_url)
    if result:
        print("[scene_gen] Video generated via DashScope (Qwen Cloud)")
        return result

    print("[scene_gen] DashScope unavailable, using AIML fallback")
    return await _try_aiml_video(prompt, image_url)


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
        import tempfile
        import os as _os

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(clip_bytes)
            tmp_path = tmp.name

        try:
            from moviepy.editor import VideoFileClip
            with VideoFileClip(tmp_path) as clip:
                last_frame = clip.get_frame(max(0, clip.duration - 0.1))
        finally:
            _os.unlink(tmp_path)

        from PIL import Image
        img = Image.fromarray(last_frame.astype("uint8"))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        frame_bytes = buf.getvalue()

        key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}_exit.jpg")
        return upload_bytes(frame_bytes, key, "image/jpeg")

    except Exception as e:
        print(f"[scene_gen] Exit frame extraction failed: {e}")
        return None
