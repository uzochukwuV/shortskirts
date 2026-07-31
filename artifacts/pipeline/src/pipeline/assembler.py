import os
import json
import tempfile
import asyncio
import httpx
from datetime import datetime

from storage.b2 import upload_bytes, build_key
from pipeline.media_tools import concatenate_video_files


async def _download_clip(url: str, timeout: int = 60) -> bytes:
    """Download a single clip and return its bytes."""
    async with httpx.AsyncClient(timeout=timeout) as http:
        r = await http.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.content


async def assemble_episode(
    story_id: str,
    episode_id: str,
    episode_number: int,
    scenes: list[dict],
) -> dict:
    clip_urls = [s["clip_url"] for s in scenes if s.get("clip_url")]
    if not clip_urls:
        raise ValueError("No clips to assemble")

    # Track all temp files for cleanup
    tmp_files: list[str] = []

    def _track_temp(suffix: str = ".mp4") -> str:
        """Create a tracked temp file."""
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        path = tmp.name
        tmp_files.append(path)  # Track immediately
        return path

    def _cleanup():
        """Clean up all tracked temp files."""
        for path in tmp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass
        tmp_files.clear()

    try:
        # Download all clips in parallel for faster assembly
        clip_bytes_list = await asyncio.gather(*[
            _download_clip(url) for url in clip_urls
        ])

        # Write downloaded clips to temp files
        clip_paths: list[str] = []
        for i, data in enumerate(clip_bytes_list):
            tmp_path = _track_temp(suffix=".mp4")
            with open(tmp_path, "wb") as tmp:
                tmp.write(data)
            clip_paths.append(tmp_path)

        # Create output temp file
        out_path = _track_temp(suffix=".mp4")

        await concatenate_video_files(clip_paths, out_path)

        with open(out_path, "rb") as f:
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
        _cleanup()
