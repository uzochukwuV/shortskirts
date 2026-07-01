import os
import io
import uuid
import asyncio
import httpx
import time
from typing import Optional
from openai import AsyncOpenAI

from storage.b2 import upload_bytes, download_and_upload, build_key
from pipeline.story_agent import get_client, build_scene_prompt


async def poll_video_task(task_id: str, timeout: int = 300) -> Optional[str]:
    client = get_client()
    deadline = time.time() + timeout
    while time.time() < deadline:
        await asyncio.sleep(10)
        try:
            result = await client.get(
                f"/tasks/{task_id}",
            )
            status = result.get("output", {}).get("task_status")
            if status == "SUCCEEDED":
                return result.get("output", {}).get("video_url")
            elif status in ("FAILED", "CANCELED"):
                raise RuntimeError(f"Video task {task_id} {status}: {result}")
        except Exception as e:
            print(f"[scene_gen] Poll error: {e}")
    raise TimeoutError(f"Video task {task_id} timed out after {timeout}s")


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
    client = get_client()
    scene_number = scene["scene_number"]

    prompt = await build_scene_prompt(scene, story_context, previous_scene_summary, style)

    refs = []
    for url in character_refs[:4]:
        refs.append({"type": "image", "url": url})
    if previous_exit_frame_url and len(refs) < 5:
        refs.append({"type": "image", "url": previous_exit_frame_url})

    try:
        if refs:
            payload = {
                "model": "wan2.1-i2v-turbo",
                "input": {
                    "prompt": prompt,
                    "reference_images": [r["url"] for r in refs[:5]],
                },
                "parameters": {
                    "duration": 5,
                    "resolution": "576P",
                },
            }
        else:
            payload = {
                "model": "wan2.1-t2v-turbo",
                "input": {"prompt": prompt},
                "parameters": {
                    "duration": 5,
                    "resolution": "576P",
                },
            }

        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.post(
                "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
                headers={
                    "Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
                json=payload,
            )
            r.raise_for_status()
            result = r.json()

        task_id = result.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"No task_id from video generation: {result}")

        video_url = await _poll_dashscope_task(task_id)

        clip_key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}.mp4")
        b2_clip_url = await download_and_upload(video_url, clip_key, "video/mp4")

        exit_frame_url = await extract_exit_frame(b2_clip_url, story_id, episode_id, scene_number)

        return {
            "clip_url": b2_clip_url,
            "exit_frame_url": exit_frame_url,
            "duration": 5.0,
            "prompt": prompt,
            "refs_used": len(refs),
        }

    except Exception as e:
        print(f"[scene_gen] Scene {scene_number} generation failed: {e}")
        raise


async def _poll_dashscope_task(task_id: str, timeout: int = 600) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        await asyncio.sleep(15)
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.get(
                f"https://dashscope-intl.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}"},
            )
            r.raise_for_status()
            data = r.json()

        status = data.get("output", {}).get("task_status", "")
        if status == "SUCCEEDED":
            video_url = data.get("output", {}).get("video_url", "")
            if not video_url:
                raise RuntimeError(f"SUCCEEDED but no video_url: {data}")
            return video_url
        elif status in ("FAILED", "CANCELED"):
            raise RuntimeError(f"Task {task_id} {status}: {data}")

    raise TimeoutError(f"Task {task_id} timed out")


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
                last_frame = clip.get_frame(clip.duration - 0.1)
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
