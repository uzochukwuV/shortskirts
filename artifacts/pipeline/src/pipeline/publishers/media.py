from __future__ import annotations

import json


def _json_object(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value or {}


async def resolve_publish_media(pool, target: dict) -> str:
    if target.get("media_url"):
        return target["media_url"]

    asset_kind = target.get("asset_kind") or "episode"
    if asset_kind == "episode":
        episode_id = target.get("episode_id")
        if not episode_id:
            raise ValueError("episode_id is required for episode publishing")
        url = await pool.fetchval("SELECT assembled_video_url FROM episodes WHERE id=$1", str(episode_id))
        if not url:
            raise ValueError("Episode has no assembled video URL yet")
        return url

    if asset_kind == "scene":
        scene_id = target.get("scene_id")
        if not scene_id:
            raise ValueError("scene_id is required for scene publishing")
        row = await pool.fetchrow("SELECT clip_url, image_url, generation_metadata, state_snapshot FROM scenes WHERE id=$1", str(scene_id))
        if not row:
            raise ValueError("Scene not found")
        metadata = _json_object(row.get("generation_metadata"))
        snapshot = _json_object(row.get("state_snapshot"))
        url = row.get("clip_url") or row.get("image_url") or metadata.get("media_url") or snapshot.get("media_url")
        if not url:
            raise ValueError("Scene has no publishable media URL yet")
        return url

    if asset_kind == "artifact":
        artifact_id = target.get("artifact_id")
        if not artifact_id:
            raise ValueError("artifact_id is required for artifact publishing")
        url = await pool.fetchval("SELECT url FROM pipeline_artifacts WHERE id=$1", str(artifact_id))
        if not url:
            raise ValueError("Artifact has no media URL")
        return url

    raise ValueError(f"Unsupported publish asset kind: {asset_kind}")

