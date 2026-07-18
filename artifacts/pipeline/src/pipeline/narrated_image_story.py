import json
import os
import tempfile
from datetime import datetime
from typing import Optional

import httpx

from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from pipeline.character_gen import generate_image_bytes
from pipeline.story_agent import build_scene_prompt


def _scene_duration(scene: dict) -> float:
    raw = scene.get("duration_seconds", scene.get("duration", 6))
    try:
        value = float(raw)
    except Exception:
        value = 6.0
    return max(5.0, min(10.0, value))


async def generate_narrated_scene_image(
    story_id: str,
    episode_id: str,
    scene: dict,
    story_context: dict,
    character_refs: list[str],
    previous_scene_image_url: Optional[str],
    previous_scene_summary: str = "",
    style: str = "anime",
) -> dict:
    scene_number = scene["scene_number"]
    prompt = await build_scene_prompt(
        scene,
        story_context,
        previous_scene_summary,
        style,
        media_kind="image",
    )

    continuity_bits = []
    if character_refs:
        continuity_bits.append(f"Character reference count: {len(character_refs)}")
    if previous_scene_image_url:
        continuity_bits.append("Continuity from the previous scene image must be preserved.")
    if scene.get("narration"):
        continuity_bits.append(f"Narration cue: {scene['narration']}")

    if continuity_bits:
        prompt = f"{prompt} {' '.join(continuity_bits)}"

    reference_image_urls = list(character_refs[:8])
    if previous_scene_image_url:
        reference_image_urls.append(previous_scene_image_url)

    image_bytes = await generate_image_bytes(
        prompt,
        reference_image_urls=reference_image_urls,
    )
    if not image_bytes:
        raise RuntimeError("Image generation failed")

    image_key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}.jpg")
    image_url = upload_bytes(image_bytes, image_key, "image/jpeg")

    return {
        "image_url": image_url,
        "exit_frame_url": image_url,
        "duration": _scene_duration(scene),
        "prompt": prompt,
        "refs_used": len(character_refs[:4]),
        "media_kind": "image",
        "narration": scene.get("narration") or scene.get("description", ""),
    }


async def assemble_narrated_episode(
    story_id: str,
    episode_id: str,
    episode_number: int,
    scenes: list[dict],
) -> dict:
    image_urls = [s.get("image_url") or s.get("media_url") for s in scenes if s.get("image_url") or s.get("media_url")]
    if not image_urls:
        raise ValueError("No images to assemble")

    tmp_files: list[str] = []
    image_paths: list[str] = []

    try:
        for url in image_urls:
            data = await download_url_to_bytes(url)
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp.write(data)
            tmp.close()
            image_paths.append(tmp.name)
            tmp_files.append(tmp.name)

        from moviepy.editor import ImageClip, concatenate_videoclips

        clips = []
        for path, scene in zip(image_paths, scenes):
            clip = ImageClip(path).set_duration(max(5.0, float(scene.get("duration", 6.0) or 6.0))).set_fps(24)
            clips.append(clip)

        final = concatenate_videoclips(clips, method="compose")
        final = final.set_fps(24)

        out_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        out_tmp.close()
        tmp_files.append(out_tmp.name)

        final.write_videofile(out_tmp.name, codec="libx264", audio=False, fps=24, logger=None)
        for clip in clips:
            clip.close()
        final.close()

        with open(out_tmp.name, "rb") as f:
            assembled_bytes = f.read()

        assembled_key = build_key(story_id, "episodes", episode_id, "narrated_assembled.mp4")
        assembled_url = upload_bytes(assembled_bytes, assembled_key, "video/mp4")

        manifest = {
            "version": "1.0",
            "format": "narrated_image_story",
            "story_id": story_id,
            "episode_id": episode_id,
            "episode_number": episode_number,
            "assembled_at": datetime.utcnow().isoformat(),
            "scenes": [
                {
                    "scene_number": s.get("scene_number"),
                    "image_url": s.get("image_url") or s.get("media_url"),
                    "duration": s.get("duration"),
                    "prompt": s.get("prompt"),
                    "narration": s.get("narration"),
                }
                for s in scenes
            ],
            "total_duration": sum(float(s.get("duration", 0) or 0) for s in scenes),
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
