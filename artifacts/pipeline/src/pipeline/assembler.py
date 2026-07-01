import os
import io
import json
import uuid
import tempfile
import asyncio
import httpx
from datetime import datetime
from typing import Optional

from storage.b2 import upload_bytes, build_key


async def assemble_episode(
    story_id: str,
    episode_id: str,
    episode_number: int,
    scenes: list[dict],
) -> dict:
    clip_urls = [s["clip_url"] for s in scenes if s.get("clip_url")]
    if not clip_urls:
        raise ValueError("No clips to assemble")

    clip_paths = []
    tmp_files = []

    try:
        for i, url in enumerate(clip_urls):
            async with httpx.AsyncClient(timeout=60) as http:
                r = await http.get(url, follow_redirects=True)
                r.raise_for_status()
                data = r.content

            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.write(data)
            tmp.close()
            clip_paths.append(tmp.name)
            tmp_files.append(tmp.name)

        from moviepy.editor import VideoFileClip, concatenate_videoclips
        clips = [VideoFileClip(p) for p in clip_paths]
        final = concatenate_videoclips(clips, method="compose")

        out_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        out_tmp.close()
        tmp_files.append(out_tmp.name)

        final.write_videofile(out_tmp.name, codec="libx264", audio_codec="aac", logger=None)
        for c in clips:
            c.close()
        final.close()

        with open(out_tmp.name, "rb") as f:
            assembled_bytes = f.read()

        key = build_key(story_id, "episodes", episode_id, "assembled.mp4")
        assembled_url = upload_bytes(assembled_bytes, key, "video/mp4")

        manifest = {
            "version": "1.0",
            "story_id": story_id,
            "episode_id": episode_id,
            "episode_number": episode_number,
            "assembled_at": datetime.utcnow().isoformat(),
            "scenes": [
                {
                    "scene_number": s.get("scene_number"),
                    "clip_url": s.get("clip_url"),
                    "duration": s.get("duration"),
                    "prompt": s.get("prompt"),
                }
                for s in scenes
            ],
            "total_duration": sum(s.get("duration", 0) for s in scenes),
            "assembled_video_url": assembled_url,
        }
        manifest_bytes = json.dumps(manifest, indent=2).encode()
        manifest_key = build_key(story_id, "episodes", episode_id, "manifest.json")
        manifest_url = upload_bytes(manifest_bytes, manifest_key, "application/json")

        return {"assembled_video_url": assembled_url, "manifest_url": manifest_url, "manifest": manifest}

    finally:
        for path in tmp_files:
            try:
                os.unlink(path)
            except Exception:
                pass
