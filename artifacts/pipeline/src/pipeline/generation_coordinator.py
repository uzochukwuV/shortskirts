from __future__ import annotations

import json
import os
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from pipeline.pipeline_config import normalize_pipeline_config

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - optional dependency
    ChatPromptTemplate = None
    ChatOpenAI = None


class RequestedMediaKind(str, Enum):
    auto = "auto"
    video = "video"
    image = "image"


class GenerationPlan(BaseModel):
    story_id: str
    workflow_type: str
    requested_media_kind: RequestedMediaKind = RequestedMediaKind.auto
    selected_media_kind: str
    selected_route: str
    fallback_chain: list[str] = Field(default_factory=list)
    should_handoff: bool = False
    handoff_reason: Optional[str] = None
    user_message: Optional[str] = None
    reason: str = ""
    langchain_used: bool = False
    langchain_model: Optional[str] = None
    provider_status: dict[str, Any] = Field(default_factory=dict)
    selected_provider: Optional[str] = None
    selected_provider_hint: Optional[str] = None
    candidate_engines: list[str] = Field(default_factory=list)
    state_patch: dict[str, Any] = Field(default_factory=dict)


class GenerationCoordinatorError(RuntimeError):
    def __init__(self, message: str, plan: Optional[GenerationPlan] = None):
        super().__init__(message)
        self.plan = plan


def _safe_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _workflow_state(story: dict[str, Any]) -> dict[str, Any]:
    return _safe_json(story.get("workflow_state"))


def _normalize_requested_media_kind(story: dict[str, Any], scene: dict[str, Any]) -> RequestedMediaKind:
    scene_kind = (scene.get("media_kind") or "").strip().lower()
    if scene_kind in {"video", "image"}:
        return RequestedMediaKind(scene_kind)

    workflow_state = _workflow_state(story)
    pipeline_config = normalize_pipeline_config(
        workflow_state=workflow_state,
        workflow_type=story.get("workflow_type"),
    )
    config_kind = (pipeline_config.get("media", {}).get("kind") or "").strip().lower()
    if config_kind in {"video", "image"}:
        return RequestedMediaKind(config_kind)

    workflow_kind = (workflow_state.get("requested_media_kind") or "").strip().lower()
    if workflow_kind in {"video", "image"}:
        return RequestedMediaKind(workflow_kind)

    workflow_type = (story.get("workflow_type") or "").strip().lower()
    if workflow_type == "narrated_image_story":
        return RequestedMediaKind.image
    return RequestedMediaKind.auto


def _build_fallback_chain(
    *,
    requested_kind: RequestedMediaKind,
    provider_status: dict[str, Any],
    character_refs: list[str],
    previous_exit_frame_url: Optional[str],
    pipeline_config: dict[str, Any],
) -> list[str]:
    if requested_kind == RequestedMediaKind.image:
        image_preference = pipeline_config.get("providers", {}).get("image_preference") or []
        if image_preference:
            return list(dict.fromkeys([str(item) for item in image_preference if item] + ["qwen-image-plus"]))
        return [
            "qwen-image-edit-plus",
            "qwen-image-plus",
            "wan2.7-image-pro",
        ]

    # Video generation runs through GenBlaze adapters. AIML is intentionally
    # excluded because its video API is currently unavailable.
    preferences = pipeline_config.get("providers", {}).get("video_preference") or []
    configured = {
        "dashscope": "DASHSCOPE_API_KEY",
        "novita": "NOVITA_API_KEY",
        "replicate": "REPLICATE_API_KEY",
        "veo3": "VEO3_API_KEY",
    }
    return [
        provider for provider in preferences
        if provider in configured and os.environ.get(configured[provider], "").strip()
    ]


async def _langchain_decision(
    *,
    story: dict[str, Any],
    scene: dict[str, Any],
    provider_status: dict[str, Any],
    requested_kind: RequestedMediaKind,
) -> Optional[dict[str, Any]]:
    if ChatOpenAI is None or ChatPromptTemplate is None:
        return None

    api_key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("TOKENROUTER_API_KEY")
        or os.environ.get("DASHSCOPE_API_KEY", "")
    )
    if not api_key:
        return None

    base_url = os.environ.get(
        "GENERATION_COORDINATOR_BASE_URL"
        if os.environ.get("OPENROUTER_API_KEY")
        else "TOKENROUTER_API_URL",
        "https://openrouter.ai/api/v1"
        if os.environ.get("OPENROUTER_API_KEY")
        else "https://api.tokenrouter.com/v1",
    )
    model = os.environ.get("GENERATION_COORDINATOR_MODEL") or os.environ.get(
        "OPENROUTER_MODEL" if os.environ.get("OPENROUTER_API_KEY") else "TOKENROUTER_MODEL",
        "openai/gpt-4o-mini"
        if os.environ.get("OPENROUTER_API_KEY")
        else "moonshotai/kimi-k3-free",
    )

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a production coordinator for an AI video studio. "
                "Choose whether the next scene should be rendered as video or still image. "
                "Prefer the user or story intent over novelty. "
                "Never invent unsupported providers. "
                "Return a JSON object with keys: selected_media_kind, selected_route, reason, should_handoff, handoff_reason, user_message.",
            ),
            (
                "user",
                "Story workflow type: {workflow_type}\n"
                "Requested media kind: {requested_kind}\n"
                "Scene media kind: {scene_kind}\n"
                "Provider status: {provider_status}\n"
                "Scene title: {title}\n"
                "Scene description: {description}\n"
                "Choose the safest route.",
            ),
        ]
    )

    chain = prompt | llm
    try:
        response = await chain.ainvoke(
            {
                "workflow_type": story.get("workflow_type") or "creator_series",
                "requested_kind": requested_kind.value,
                "scene_kind": scene.get("media_kind") or "",
                "provider_status": json.dumps(provider_status, sort_keys=True),
                "title": scene.get("title") or "",
                "description": scene.get("description") or scene.get("visual_prompt") or "",
            }
        )
    except Exception:
        return None
    content = getattr(response, "content", None) or ""
    if not content:
        return None

    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]

    try:
        data = json.loads(content.strip())
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


async def build_generation_plan(
    *,
    story: dict[str, Any],
    scene: dict[str, Any],
    provider_status: dict[str, Any],
    character_refs: list[str],
    previous_exit_frame_url: Optional[str] = None,
    previous_scene_image_url: Optional[str] = None,
) -> GenerationPlan:
    requested_kind = _normalize_requested_media_kind(story, scene)
    workflow_type = (story.get("workflow_type") or "creator_series").strip()
    workflow_state = _workflow_state(story)
    pipeline_config = normalize_pipeline_config(
        workflow_state=workflow_state,
        workflow_type=workflow_type,
    )

    selected_media_kind = "image" if requested_kind == RequestedMediaKind.image else "video"
    selected_route = "image"
    reason = ""
    should_handoff = False
    handoff_reason = None
    user_message = None
    langchain_used = False
    langchain_model = None

    if workflow_type == "narrated_image_story" or requested_kind == RequestedMediaKind.image:
        selected_media_kind = "image"
        selected_route = "narrated_image_story"
        reason = "Story intent resolves to a narrated image sequence."
    else:
        selected_media_kind = "video"
        selected_route = "video"
        reason = "Story intent resolves to video generation."

    llm_decision = await _langchain_decision(
        story=story,
        scene=scene,
        provider_status=provider_status,
        requested_kind=requested_kind,
    )
    if llm_decision:
        langchain_used = True
        langchain_model = os.environ.get("GENERATION_COORDINATOR_MODEL", "qwen-max")
        llm_selected_kind = (llm_decision.get("selected_media_kind") or "").strip().lower()
        if llm_selected_kind in {"video", "image"}:
            if requested_kind == RequestedMediaKind.auto:
                selected_media_kind = llm_selected_kind
                selected_route = llm_decision.get("selected_route") or selected_route
                reason = llm_decision.get("reason") or reason
            elif requested_kind == RequestedMediaKind.image:
                selected_media_kind = "image"
                selected_route = "narrated_image_story"
            else:
                selected_media_kind = "video"
                selected_route = "video"

        if llm_decision.get("should_handoff"):
            should_handoff = True
            handoff_reason = llm_decision.get("handoff_reason") or llm_decision.get("reason")
            user_message = llm_decision.get("user_message")

    if selected_media_kind == "video":
        configured_video_keys = (
            "DASHSCOPE_API_KEY",
            "NOVITA_API_KEY",
            "REPLICATE_API_KEY",
            "VEO3_API_KEY",
        )
        has_video_provider = any(
            os.environ.get(key, "").strip() for key in configured_video_keys
        )
        if not has_video_provider:
            should_handoff = True
            handoff_reason = handoff_reason or "No video-capable provider is currently available."
            user_message = user_message or (
                "Video rendering is temporarily unavailable. "
                "Switch to narrated image production or try again later."
            )

    if selected_media_kind == "image" and requested_kind == RequestedMediaKind.video:
        if pipeline_config.get("providers", {}).get("allow_fallback_to_image"):
            reason = f"{reason} Fallback to image is allowed by pipeline config."
        else:
            # Never silently convert an explicit video request into stills.
            should_handoff = True
            handoff_reason = handoff_reason or "The coordinator will not silently change a requested video production into images."
            user_message = user_message or "A video route was requested, but the current plan would change the output type. Please revise the workflow or retry."

    selected_provider_hint = None
    if selected_media_kind == "video":
        workflow_state = _workflow_state(story)
        selected_provider_hint = (workflow_state.get("generation_coordinator") or {}).get("preferred_video_provider")
        if not selected_provider_hint:
            provider_preference = pipeline_config.get("providers", {}).get("video_preference") or []
            configured_provider_keys = {
                "dashscope": "DASHSCOPE_API_KEY",
                "novita": "NOVITA_API_KEY",
                "replicate": "REPLICATE_API_KEY",
                "veo3": "VEO3_API_KEY",
            }
            for preferred in provider_preference:
                env_key = configured_provider_keys.get(preferred)
                if env_key and os.environ.get(env_key, "").strip():
                    selected_provider_hint = preferred
                    break
        if not selected_provider_hint:
            configured_provider_keys = {
                "dashscope": "DASHSCOPE_API_KEY",
                "novita": "NOVITA_API_KEY",
                "replicate": "REPLICATE_API_KEY",
                "veo3": "VEO3_API_KEY",
            }
            selected_provider_hint = next(
                (
                    provider
                    for provider, env_key in configured_provider_keys.items()
                    if os.environ.get(env_key, "").strip()
                ),
                None,
            )
    elif selected_media_kind == "image":
        selected_provider_hint = "qwen"

    fallback_chain = _build_fallback_chain(
        requested_kind=RequestedMediaKind(selected_media_kind) if selected_media_kind in {"video", "image"} else RequestedMediaKind.auto,
        provider_status=provider_status,
        character_refs=character_refs,
        previous_exit_frame_url=previous_exit_frame_url or previous_scene_image_url,
        pipeline_config=pipeline_config,
    )
    if selected_media_kind == "video":
        ordered = []
        if selected_provider_hint:
            ordered.append(selected_provider_hint)
        for provider in fallback_chain:
            if provider not in ordered:
                ordered.append(provider)
        fallback_chain = ordered

    return GenerationPlan(
        story_id=str(story.get("id") or ""),
        workflow_type=workflow_type,
        requested_media_kind=requested_kind,
        selected_media_kind=selected_media_kind,
        selected_route=selected_route,
        fallback_chain=fallback_chain,
        should_handoff=should_handoff,
        handoff_reason=handoff_reason,
        user_message=user_message,
        reason=reason,
        langchain_used=langchain_used,
        langchain_model=langchain_model,
        provider_status=provider_status,
        selected_provider_hint=selected_provider_hint,
        candidate_engines=fallback_chain,
    )


async def generate_with_coordinator(
    *,
    story: dict[str, Any],
    episode_id: str,
    scene: dict[str, Any],
    story_context: dict[str, Any],
    character_refs: list[str],
    previous_exit_frame_url: Optional[str] = None,
    previous_scene_image_url: Optional[str] = None,
    previous_scene_summary: str = "",
    style: str = "",
) -> tuple[dict[str, Any], GenerationPlan]:
    from pipeline.provider_status import get_provider_status
    from pipeline.narrated_image_story import generate_narrated_scene_image
    from pipeline.scene_gen import generate_scene_clip

    provider_status = await get_provider_status()
    workflow_state = _workflow_state(story)
    pipeline_config = normalize_pipeline_config(
        workflow_state=workflow_state,
        workflow_type=story.get("workflow_type"),
    )
    generation_context = {
        **(story_context or {}),
        "workflow_state": workflow_state,
        "pipeline_config": pipeline_config,
        "requested_video_ratio": pipeline_config.get("media", {}).get("ratio"),
    }
    plan = await build_generation_plan(
        story=story,
        scene=scene,
        provider_status=provider_status,
        character_refs=character_refs,
        previous_exit_frame_url=previous_exit_frame_url,
        previous_scene_image_url=previous_scene_image_url,
    )

    if plan.should_handoff:
        raise GenerationCoordinatorError(plan.user_message or plan.handoff_reason or "Generation requires user intervention.", plan=plan)

    last_exc: Exception | None = None
    if plan.selected_media_kind == "image":
        try:
            result = await generate_narrated_scene_image(
                story_id=str(story["id"]),
                episode_id=episode_id,
                scene=scene,
                story_context=generation_context,
                character_refs=character_refs,
                previous_scene_image_url=previous_scene_image_url or previous_exit_frame_url,
                previous_scene_summary=previous_scene_summary,
                style=style,
            )
            plan.selected_provider = plan.selected_provider_hint or "qwen-image-chain"
            plan.state_patch = {
                "generation_coordinator": {
                    "preferred_media_kind": "image",
                    "preferred_image_provider": plan.selected_provider,
                }
            }
            result["generation_plan"] = plan.model_dump()
            result["selected_media_kind"] = plan.selected_media_kind
            return result, plan
        except Exception as exc:
            last_exc = exc
            raise GenerationCoordinatorError(f"All image engines failed. Last error: {last_exc}", plan=plan)

    try:
        result = await generate_scene_clip(
            story_id=str(story["id"]),
            episode_id=episode_id,
            scene=scene,
            story_context=generation_context,
            character_refs=character_refs,
            previous_exit_frame_url=previous_exit_frame_url or previous_scene_image_url,
            previous_scene_summary=previous_scene_summary,
            style=style,
            preferred_provider=plan.selected_provider_hint,
        )
        plan.selected_provider = result.get("video_provider") or plan.selected_provider_hint
        plan.candidate_engines = [
            attempt.get("model")
            for attempt in result.get("agent_video_plan", {}).get("attempts", [])
            if attempt.get("model")
        ] or plan.candidate_engines
        plan.state_patch = {
            "generation_coordinator": {
                "preferred_media_kind": "video",
                "preferred_video_provider": plan.selected_provider,
                "preferred_video_model": result.get("video_model"),
            }
        }
        result["generation_plan"] = plan.model_dump()
        result["selected_media_kind"] = plan.selected_media_kind
        return result, plan
    except Exception as exc:
        last_exc = exc

    raise GenerationCoordinatorError(
        f"All video engines failed. Last error: {last_exc}",
        plan=plan,
    )
