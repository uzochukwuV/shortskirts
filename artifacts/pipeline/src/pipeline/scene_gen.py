import os
import io
import asyncio
import httpx
import time
from typing import Optional

from storage.b2 import upload_bytes, download_and_upload, build_key
from pipeline.story_agent import build_scene_prompt

AIML_BASE_URL = "https://api.aimlapi.com"

# Image-to-video (uses character reference images) — preferred when refs available
I2V_MODEL = "alibaba/wan2.7-i2v"
# Text-to-video fallback when no refs
T2V_MODEL = "alibaba/wan2.1-t2v-turbo"


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

    # Decide i2v vs t2v based on available refs
    # i2v: use first ref image (character) or exit frame as the reference image
    reference_image = None
    if character_refs:
        reference_image = character_refs[0]
    elif previous_exit_frame_url:
        reference_image = previous_exit_frame_url

    task_id = await _submit_video_task(prompt, reference_image)
    video_url = await _poll_video_task(task_id)

    clip_key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}.mp4")
    b2_clip_url = await download_and_upload(video_url, clip_key, "video/mp4")

    exit_frame_url = await extract_exit_frame(b2_clip_url, story_id, episode_id, scene_number)

    return {
        "clip_url": b2_clip_url,
        "exit_frame_url": exit_frame_url,
        "duration": 5.0,
        "prompt": prompt,
        "refs_used": 1 if reference_image else 0,
    }


async def _submit_video_task(prompt: str, image_url: Optional[str] = None) -> str:
    headers = {
        "Authorization": f"Bearer {os.environ['AIML_API_KEY']}",
        "Content-Type": "application/json",
    }

    if image_url:
        payload = {
            "model": I2V_MODEL,
            "prompt": prompt,
            "image_url": image_url,
            "duration": 5,
        }
    else:
        payload = {
            "model": T2V_MODEL,
            "prompt": prompt,
            "duration": 5,
        }

    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{AIML_BASE_URL}/v2/video/generations",
            headers=headers,
            json=payload,
        )
        if r.status_code != 200:
            # Fallback: if i2v fails, retry as t2v
            if image_url:
                print(f"[scene_gen] i2v failed ({r.status_code}), falling back to t2v")
                payload = {
                    "model": T2V_MODEL,
                    "prompt": prompt,
                    "duration": 5,
                }
                r = await http.post(
                    f"{AIML_BASE_URL}/v2/video/generations",
                    headers=headers,
                    json=payload,
                )
        r.raise_for_status()
        data = r.json()

    task_id = data.get("id") or data.get("generation_id") or data.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task ID from video generation: {data}")
    return task_id


async def _poll_video_task(task_id: str, timeout: int = 600) -> str:
    headers = {"Authorization": f"Bearer {os.environ['AIML_API_KEY']}"}
    deadline = time.time() + timeout

    while time.time() < deadline:
        await asyncio.sleep(15)
        try:
            async with httpx.AsyncClient(timeout=30) as http:
                r = await http.get(
                    f"{AIML_BASE_URL}/v2/video/generations",
                    headers=headers,
                    params={"generation_id": task_id},
                )
                r.raise_for_status()
                data = r.json()

            status = (
                data.get("status")
                or data.get("task_status")
                or ""
            ).lower()

            print(f"[scene_gen] Task {task_id}: {status}")

            if status in ("completed", "succeeded", "success", "finished"):
                video_url = (
                    data.get("video_url")
                    or data.get("url")
                    or (data.get("output") or {}).get("video_url")
                    or (data.get("result") or {}).get("url")
                )
                if video_url:
                    return video_url
                # Nested output
                for key in ["output", "result", "data", "generation"]:
                    nested = data.get(key)
                    if isinstance(nested, dict):
                        for vkey in ["video_url", "url", "video", "output_url"]:
                            if nested.get(vkey):
                                return nested[vkey]
                raise RuntimeError(f"Task succeeded but no video URL found: {data}")

            elif status in ("failed", "error", "cancelled", "canceled"):
                raise RuntimeError(f"Video task failed: {data}")

        except asyncio.TimeoutError:
            continue
        except Exception as e:
            if "failed" in str(e).lower() or "error" in str(e).lower():
                raise
            print(f"[scene_gen] Poll error (will retry): {e}")
            await asyncio.sleep(5)

    raise TimeoutError(f"Video task {task_id} timed out after {timeout}s")


async def extract_exit_frame(
    clip_url: str,
    story_id: str,
    episode_id: str,
    scene_number: int,
) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            r = await http.get(clip_url, follow_redirects=True)
            r.raise_for_status()
            clip_bytes = r.content

        import tempfile, os as _os
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
