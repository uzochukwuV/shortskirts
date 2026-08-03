from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from pipeline.pipeline_runtime import finish_pipeline_step, start_pipeline_step
from pipeline.scene_gen import GENBLAZE_PROVIDER_TYPES, _genblaze_model
from pipeline.providers.provider_router import get_router


class AgentScenePlan(BaseModel):
    selected_media_kind: str
    selected_route: str
    attempts: list[dict[str, Any]] = Field(default_factory=list)
    should_handoff: bool = False
    handoff_reason: Optional[str] = None
    user_message: Optional[str] = None
    reason: str = ""


def _build_genblaze_attempts(
    *,
    reference_count: int,
    pipeline_config: dict[str, Any],
    preferred_provider: str | None,
) -> list[dict[str, Any]]:
    """Build attempts from the live GenBlaze adapters only.

    This intentionally does not consult the legacy model registry. Existing
    stories may contain older workflow state, but that state must not be able
    to re-enable AIML or bypass the GenBlaze route.
    """
    router = get_router()
    available = {
        provider.value
        for provider in router.available_providers
        if provider.value in GENBLAZE_PROVIDER_TYPES
    }
    preferences = pipeline_config.get("providers", {}).get("video_preference") or []
    order: list[str] = []
    for provider in [preferred_provider, *preferences, *sorted(available)]:
        normalized = str(provider or "").lower()
        if normalized in available and normalized not in order:
            order.append(normalized)

    attempts: list[dict[str, Any]] = []
    for provider in order:
        if reference_count >= 2 and provider in {"dashscope", "novita"}:
            capability = "r2v"
            max_refs = 9 if provider == "dashscope" else 4
        elif reference_count >= 1 and provider in {"dashscope", "novita", "veo3"}:
            capability = "i2v"
            max_refs = 1
        else:
            capability = "t2v"
            max_refs = 0
        attempts.append(
            {
                "provider": provider,
                "path": "genblaze",
                "model": _genblaze_model(provider, reference_count),
                "capability": capability,
                "max_refs": max_refs,
                "supports_ratio": True,
                "max_duration_seconds": 3,
                "reason": (
                    f"Use GenBlaze {capability} through the configured "
                    f"{provider} adapter."
                ),
            }
        )
    return attempts


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
    attempts = _build_genblaze_attempts(
        reference_count=reference_count,
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
