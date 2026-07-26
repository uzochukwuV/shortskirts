from __future__ import annotations

import json
from typing import Any

from models.story import ValidActionResponse
from pipeline.story_agent import suggest_scene_edit, suggest_story_edit, suggest_story_operation


def _action(
    key: str,
    label: str,
    target: str,
    enabled: bool,
    *,
    requires_confirmation: bool = False,
    reason: str | None = None,
) -> ValidActionResponse:
    return ValidActionResponse(
        key=key,
        label=label,
        target=target,
        enabled=enabled,
        requires_confirmation=requires_confirmation,
        reason=reason,
    )


def build_story_capabilities(
    *,
    story: dict[str, Any],
    selected_scene: dict[str, Any] | None = None,
    selected_checkpoint: dict[str, Any] | None = None,
    active_job: dict[str, Any] | None = None,
) -> dict[str, list[ValidActionResponse]]:
    story_status = (story.get("status") or "").strip().lower()
    job_status = (active_job or {}).get("status", "").strip().lower()
    scene_locked = bool((selected_scene or {}).get("locked"))
    scene_running = ((selected_scene or {}).get("status") or "").strip().lower() == "running"
    scene_present = selected_scene is not None
    checkpoint_present = selected_checkpoint is not None
    checkpoint_status = ((selected_checkpoint or {}).get("status") or "").strip().lower()
    checkpoint_audio_status = ((selected_checkpoint or {}).get("audio_status") or "").strip().lower()

    can_generate = story_status not in {"generating", "checkpoint_review"} and story_status != "draft"
    can_approve_outline = story_status == "draft"
    can_regenerate_outline = story_status not in {"generating", "checkpoint_review"}
    can_edit_story = story_status != "generating"
    can_cancel_run = story_status in {"generating", "checkpoint_review"} or job_status in {"pending", "running", "retrying"}

    story_actions = [
        _action("edit_story", "Edit story", "story", can_edit_story, reason=None if can_edit_story else "Story is generating right now."),
        _action("approve_outline", "Approve outline", "story", can_approve_outline, reason=None if can_approve_outline else "Outline is already approved or generation has started."),
        _action("regenerate_outline", "Regenerate outline", "story", can_regenerate_outline, requires_confirmation=True, reason=None if can_regenerate_outline else "Cancel the active generation before regenerating the outline."),
        _action("start_generation", "Start generation", "story", can_generate, reason=None if can_generate else "Story must be approved and not currently generating."),
        _action("cancel_run", "Cancel run", "run", can_cancel_run, requires_confirmation=True, reason=None if can_cancel_run else "There is no active run to cancel."),
    ]

    scene_actions = [
        _action("edit_scene", "Edit selected scene", "scene", scene_present and not scene_running, reason=None if scene_present and not scene_running else "Choose an idle scene first."),
        _action("regenerate_scene", "Regenerate selected scene", "scene", scene_present and not scene_locked and not scene_running, reason=None if scene_present and not scene_locked and not scene_running else "Scene is missing, locked, or already running."),
    ]

    checkpoint_actions = [
        _action(
            "approve_checkpoint",
            "Approve checkpoint",
            "checkpoint",
            checkpoint_present and checkpoint_status == "pending_review" and checkpoint_audio_status not in {"pending", "running"},
            reason=None if checkpoint_present and checkpoint_status == "pending_review" and checkpoint_audio_status not in {"pending", "running"} else "Checkpoint is not ready for approval.",
        ),
    ]

    run_actions = [
        _action("retry_failed_step", "Retry failed step", "run", bool(active_job and active_job.get("status") == "failed"), reason=None if active_job and active_job.get("status") == "failed" else "No failed run is available for retry."),
    ]

    return {
        "story_actions": story_actions,
        "scene_actions": scene_actions,
        "checkpoint_actions": checkpoint_actions,
        "run_actions": run_actions,
    }


async def plan_operation(
    *,
    story: dict[str, Any],
    selected_scene: dict[str, Any] | None,
    selected_checkpoint: dict[str, Any] | None,
    active_job: dict[str, Any] | None,
    instruction: str,
) -> dict[str, Any]:
    capabilities = build_story_capabilities(
        story=story,
        selected_scene=selected_scene,
        selected_checkpoint=selected_checkpoint,
        active_job=active_job,
    )
    valid_actions = [
        action.key
        for group in capabilities.values()
        for action in group
        if action.enabled
    ]
    operation_plan = await suggest_story_operation(
        story=story,
        scene=selected_scene,
        checkpoint=selected_checkpoint,
        instruction=instruction,
        valid_actions=valid_actions,
    )
    operation = str(operation_plan.get("operation") or "unsupported").strip()
    message = str(operation_plan.get("message") or "No operation selected.").strip()
    requires_confirmation = bool(operation_plan.get("requires_confirmation"))
    target = str(operation_plan.get("target") or "story").strip()

    story_patch: dict[str, Any] = {}
    scene_patch: dict[str, Any] = {}

    if operation == "edit_story":
        drafted = await suggest_story_edit(story, instruction)
        story_patch = drafted.get("story_patch") or {}
        message = drafted.get("message") or message
    elif operation == "edit_scene" and selected_scene:
        drafted = await suggest_scene_edit(story, selected_scene, instruction)
        scene_patch = drafted.get("scene_patch") or {}
        message = drafted.get("message") or message

    allowed = operation in valid_actions
    if not allowed:
        for group in capabilities.values():
            for action in group:
                if action.key == operation:
                    message = action.reason or message
                    break

    return {
        "operation": operation,
        "target": target,
        "message": message,
        "allowed": allowed,
        "requires_confirmation": requires_confirmation,
        "story_patch": story_patch,
        "scene_patch": scene_patch,
        "valid_actions": valid_actions,
        "capabilities": capabilities,
    }
