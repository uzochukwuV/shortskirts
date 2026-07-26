from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from pipeline.model_registry import build_video_attempts
from pipeline.pipeline_runtime import finish_pipeline_step, start_pipeline_step


class AgentScenePlan(BaseModel):
    selected_media_kind: str
    selected_route: str
    attempts: list[dict[str, Any]] = Field(default_factory=list)
    should_handoff: bool = False
    handoff_reason: Optional[str] = None
    user_message: Optional[str] = None
    reason: str = ""


async def plan_scene_video(
    *,
    story_id: str,
    episode_id: str,
    scene_id: str | None,
    job_id: str | None,
    scene_number: int,
    reference_count: int,
    provider_status: dict[str, Any],
    pipeline_config: dict[str, Any],
    preferred_provider: str | None = None,
) -> AgentScenePlan:
    step_id = await start_pipeline_step(
        story_id=story_id,
        episode_id=episode_id,
        scene_id=scene_id,
        job_id=job_id,
        step_key=f"agent_decision:scene:{scene_number}",
        step_type="agent_decision",
        input={
            "scene_number": scene_number,
            "reference_count": reference_count,
            "preferred_provider": preferred_provider,
            "media": pipeline_config.get("media", {}),
            "provider_preferences": pipeline_config.get("providers", {}).get("video_preference"),
        },
    )
    attempts = build_video_attempts(
        reference_count=reference_count,
        provider_status=provider_status,
        pipeline_config=pipeline_config,
        preferred_provider=preferred_provider,
    )
    plan = AgentScenePlan(
        selected_media_kind="video",
        selected_route=attempts[0]["capability"] if attempts else "video",
        attempts=attempts,
        should_handoff=not bool(attempts),
        handoff_reason=None if attempts else "No video-capable model is currently available.",
        user_message=None if attempts else "Video rendering is unavailable right now. Please retry later or switch to narrated images.",
        reason="Agent selected concrete video model attempts based on references, provider health, and user pipeline config.",
    )
    await finish_pipeline_step(
        step_id,
        status="completed" if attempts else "failed",
        output=plan.model_dump(),
    )
    return plan
