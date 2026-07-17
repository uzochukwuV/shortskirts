from __future__ import annotations

import os
from typing import Any

WORKFLOW_VERSION = os.getenv("WORKFLOW_VERSION", "v1")
GENERATION_VERSION = os.getenv("GENERATION_VERSION", "v1")
IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL_NAME", "qwen-image-plus")
IMAGE_MODEL_VERSION = os.getenv("IMAGE_MODEL_VERSION", IMAGE_MODEL_NAME)
IMAGE_EDIT_MODEL_NAME = os.getenv("IMAGE_EDIT_MODEL_NAME", "qwen-image-edit-max")
IMAGE_EDIT_MODEL_VERSION = os.getenv("IMAGE_EDIT_MODEL_VERSION", IMAGE_EDIT_MODEL_NAME)


def build_state_snapshot(*, story: dict[str, Any], checkpoint: dict[str, Any] | None = None, scene: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "workflow_version": story.get("workflow_version", WORKFLOW_VERSION),
        "generation_version": story.get("generation_version", GENERATION_VERSION),
        "story_id": str(story["id"]),
    }
    if checkpoint:
        snapshot["checkpoint"] = checkpoint
    if scene:
        snapshot["scene"] = scene
    if extra:
        snapshot.update(extra)
    return snapshot
