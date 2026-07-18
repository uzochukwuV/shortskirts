from __future__ import annotations

import json
from typing import Any

from pipeline.versioning import build_state_snapshot


def _as_dict(row: Any) -> dict[str, Any]:
    return dict(row) if not isinstance(row, dict) else row


def _json_value(value: Any) -> str:
    return json.dumps(value if value is not None else {}, default=str)


async def _next_revision(pool, table: str, entity_column: str, entity_id: str) -> int:
    query = f"SELECT COALESCE(MAX(revision), 0) + 1 FROM {table} WHERE {entity_column} = $1"
    return int(await pool.fetchval(query, entity_id))


async def record_story_history(
    pool,
    *,
    story: dict[str, Any],
    event_type: str,
    source_job_id: str | None = None,
    payload: dict[str, Any] | None = None,
    state_snapshot: dict[str, Any] | None = None,
) -> None:
    try:
        story_row = _as_dict(story)
        revision = await _next_revision(pool, "story_history", "story_id", str(story_row["id"]))
        snapshot = state_snapshot or build_state_snapshot(story=story_row, extra=payload or {})
        await pool.execute(
            """INSERT INTO story_history
               (story_id, revision, event_type, workflow_version, generation_version, source_job_id,
                state_snapshot, payload)
               VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb)""",
            str(story_row["id"]),
            revision,
            event_type,
            story_row.get("workflow_version", "v1"),
            story_row.get("generation_version", "v1"),
            source_job_id,
            _json_value(snapshot),
            _json_value(payload or {}),
        )
    except Exception as exc:
        print(f"[history] story history write failed: {exc}")


async def record_scene_history(
    pool,
    *,
    story: dict[str, Any],
    scene: dict[str, Any],
    event_type: str,
    source_job_id: str | None = None,
    payload: dict[str, Any] | None = None,
    state_snapshot: dict[str, Any] | None = None,
) -> None:
    try:
        story_row = _as_dict(story)
        scene_row = _as_dict(scene)
        revision = await _next_revision(pool, "scene_history", "scene_id", str(scene_row["id"]))
        snapshot = state_snapshot or build_state_snapshot(story=story_row, scene=scene_row, extra=payload or {})
        await pool.execute(
            """INSERT INTO scene_history
               (scene_id, story_id, episode_id, revision, event_type, generation_version,
                image_model, image_model_version, edit_model, edit_model_version, source_job_id,
                state_snapshot, payload)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13::jsonb)""",
            str(scene_row["id"]),
            str(story_row["id"]),
            str(scene_row["episode_id"]),
            revision,
            event_type,
            scene_row.get("generation_version", "v1"),
            scene_row.get("image_model"),
            scene_row.get("image_model_version"),
            scene_row.get("edit_model"),
            scene_row.get("edit_model_version"),
            source_job_id,
            _json_value(snapshot),
            _json_value(payload or {}),
        )
    except Exception as exc:
        print(f"[history] scene history write failed: {exc}")


async def record_checkpoint_history(
    pool,
    *,
    story: dict[str, Any],
    checkpoint: dict[str, Any],
    event_type: str,
    source_job_id: str | None = None,
    payload: dict[str, Any] | None = None,
    state_snapshot: dict[str, Any] | None = None,
) -> None:
    try:
        story_row = _as_dict(story)
        checkpoint_row = _as_dict(checkpoint)
        revision = await _next_revision(pool, "checkpoint_history", "checkpoint_id", str(checkpoint_row["id"]))
        snapshot = state_snapshot or build_state_snapshot(story=story_row, checkpoint=checkpoint_row, extra=payload or {})
        await pool.execute(
            """INSERT INTO checkpoint_history
               (checkpoint_id, story_id, revision, event_type, generation_version, source_job_id,
                state_snapshot, payload)
               VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb)""",
            str(checkpoint_row["id"]),
            str(story_row["id"]),
            revision,
            event_type,
            checkpoint_row.get("generation_version", "v1"),
            source_job_id,
            _json_value(snapshot),
            _json_value(payload or {}),
        )
    except Exception as exc:
        print(f"[history] checkpoint history write failed: {exc}")
