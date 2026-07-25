from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal


VideoCapability = Literal["t2v", "i2v", "r2v", "video_edit"]


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    provider: str
    capability: str
    supports_refs: bool = False
    max_refs: int = 0
    supports_ratio: bool = True
    max_duration_seconds: int = 10
    cost_tier: str = "standard"
    priority: int = 100


VIDEO_MODELS: dict[str, ModelSpec] = {
    "happyhorse-1.1-r2v": ModelSpec(
        model_id="happyhorse-1.1-r2v",
        provider="dashscope",
        capability="r2v",
        supports_refs=True,
        max_refs=9,
        cost_tier="medium",
        priority=10,
    ),
    "wan2.7-r2v-2026-06-12": ModelSpec(
        model_id="wan2.7-r2v-2026-06-12",
        provider="dashscope",
        capability="r2v",
        supports_refs=True,
        max_refs=5,
        cost_tier="high",
        priority=20,
    ),
    "happyhorse-1.1-i2v": ModelSpec(
        model_id="happyhorse-1.1-i2v",
        provider="dashscope",
        capability="i2v",
        supports_refs=True,
        max_refs=1,
        cost_tier="medium",
        priority=30,
    ),
    "wan2.7-i2v": ModelSpec(
        model_id="wan2.7-i2v",
        provider="dashscope",
        capability="i2v",
        supports_refs=True,
        max_refs=1,
        cost_tier="high",
        priority=40,
    ),
    "happyhorse-1.1-t2v": ModelSpec(
        model_id="happyhorse-1.1-t2v",
        provider="dashscope",
        capability="t2v",
        cost_tier="medium",
        priority=50,
    ),
    "wan2.7-t2v": ModelSpec(
        model_id="wan2.7-t2v",
        provider="dashscope",
        capability="t2v",
        cost_tier="high",
        priority=60,
    ),
    "alibaba/wan2.7-i2v": ModelSpec(
        model_id="alibaba/wan2.7-i2v",
        provider="aiml",
        capability="i2v",
        supports_refs=True,
        max_refs=1,
        cost_tier="high",
        priority=90,
    ),
    "alibaba/wan2.7-t2v": ModelSpec(
        model_id="alibaba/wan2.7-t2v",
        provider="aiml",
        capability="t2v",
        cost_tier="high",
        priority=100,
    ),
}


IMAGE_MODELS: dict[str, ModelSpec] = {
    "wan2.7-image-pro": ModelSpec("wan2.7-image-pro", "dashscope", "image", supports_refs=True, max_refs=9, priority=10),
    "qwen-image-edit-max": ModelSpec("qwen-image-edit-max", "dashscope", "image_edit", supports_refs=True, max_refs=3, priority=20),
    "qwen-image-edit-plus": ModelSpec("qwen-image-edit-plus", "dashscope", "image_edit", supports_refs=True, max_refs=3, priority=30),
    "qwen-image-edit": ModelSpec("qwen-image-edit", "dashscope", "image_edit", supports_refs=True, max_refs=3, priority=40),
    "qwen-image-plus": ModelSpec("qwen-image-plus", "dashscope", "image", priority=50),
    "qwen-image": ModelSpec("qwen-image", "dashscope", "image", priority=60),
    "wan2.1-t2i-plus": ModelSpec("wan2.1-t2i-plus", "dashscope", "image", priority=70),
}


TEXT_MODELS: dict[str, ModelSpec] = {
    "qwen3.7-max": ModelSpec("qwen3.7-max", "dashscope", "text", priority=10),
    "qwen3.7-plus": ModelSpec("qwen3.7-plus", "dashscope", "text_vision", priority=20),
    "qwen-max": ModelSpec("qwen-max", "dashscope", "text", priority=30),
    "qwen-plus": ModelSpec("qwen-plus", "dashscope", "text", priority=40),
    "qwen3.6-flash": ModelSpec("qwen3.6-flash", "dashscope", "text_vision", priority=50),
    "qwen3.5-flash": ModelSpec("qwen3.5-flash", "dashscope", "text_vision", priority=60),
}


def _is_available(spec: ModelSpec, provider_status: dict[str, Any]) -> bool:
    if spec.provider == "aiml":
        return bool(os.environ.get("AIML_API_KEY", ""))
    if spec.provider == "dashscope":
        return bool(os.environ.get("DASHSCOPE_API_KEY", ""))
    return True


def _preferred_keys(preferences: list[Any], provider: str) -> tuple[int, int]:
    normalized = [str(item) for item in preferences if item]
    model_index = normalized.index(provider) if provider in normalized else 999
    return model_index, 0


def _candidate_video_models(reference_count: int) -> list[ModelSpec]:
    specs = sorted(VIDEO_MODELS.values(), key=lambda item: item.priority)
    if reference_count >= 2:
        desired = ["r2v", "i2v", "t2v"]
    elif reference_count == 1:
        desired = ["i2v", "r2v", "t2v"]
    else:
        desired = ["t2v"]
    return [spec for capability in desired for spec in specs if spec.capability == capability]


def build_video_attempts(
    *,
    reference_count: int,
    provider_status: dict[str, Any],
    pipeline_config: dict[str, Any],
    preferred_provider: str | None = None,
) -> list[dict[str, Any]]:
    preferences = list(pipeline_config.get("providers", {}).get("video_preference") or [])
    if preferred_provider:
        preferences = [preferred_provider, *preferences]

    candidates = []
    for spec in _candidate_video_models(reference_count):
        if not _is_available(spec, provider_status):
            continue
        if spec.supports_refs and reference_count == 0:
            continue
        candidates.append(spec)

    def _sort_key(spec: ModelSpec) -> tuple[int, int, int]:
        normalized = [str(item) for item in preferences if item]
        if spec.model_id in normalized:
            preference_rank = normalized.index(spec.model_id)
        elif spec.provider in normalized:
            preference_rank = normalized.index(spec.provider)
        else:
            preference_rank = 999
        return preference_rank, spec.priority, 0

    attempts = []
    seen: set[str] = set()
    for spec in sorted(candidates, key=_sort_key):
        if spec.model_id in seen:
            continue
        seen.add(spec.model_id)
        attempts.append(
            {
                "provider": spec.provider,
                "model": spec.model_id,
                "capability": spec.capability,
                "max_refs": spec.max_refs,
                "supports_ratio": spec.supports_ratio,
                "max_duration_seconds": spec.max_duration_seconds,
                "reason": _attempt_reason(spec, reference_count),
            }
        )
    return attempts


def _attempt_reason(spec: ModelSpec, reference_count: int) -> str:
    if spec.capability == "r2v":
        return f"Use reference-to-video for continuity with {min(reference_count, spec.max_refs)} references."
    if spec.capability == "i2v":
        return "Use image-to-video from the strongest available reference frame."
    return "Use text-to-video when reference video models are unavailable or not applicable."
