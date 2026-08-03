from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any


VALID_MEDIA_KINDS = {"auto", "video", "image"}
VALID_RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4"}


# Feature flags for Agent SDK integration
# These flags control which new capabilities are enabled
FEATURE_FLAG_DEFAULTS: dict[str, bool] = {
    "structured_plans": False,       # Enable structured shot planning
    "continuity_references": False,  # Enable reference catalog for continuity
    "dialogue_audio": False,        # Enable dialogue/voice synthesis
    "timeline_assembly": False,      # Enable AI-powered timeline assembly
    "agent_chat": False,            # Enable conversational agent interface
    "parallel_generation": True,     # Enable parallel scene generation (BUG-7 fix)
    "use_genblaze": True,           # Route media through the GenBlaze adapters
}


# GenBlaze provider mappings
# Maps Dysentry provider names to GenBlaze models
GENBLaze_VIDEO_MODELS = {
    "dashscope": "happyhorse-1.1-t2v",
    "qwen": "happyhorse-1.1-t2v",
    "novita": "wan2.7-t2v",
    "replicate": "luosi-npn/ltxv-hunyuan-t2v",
    "veo3": "veo3",
    "sora": "sora-2",
    "veo": "veo3",
    "kling": "Kling-Text2Video-V2.1-Master",
    "wan": "wan2.6-t2v",
    "cosmos": "cosmos-2.0",
    "runway": "gen4_turbo",
    "luma": "ray-2",
}

GENBLaze_IMAGE_MODELS = {
    "qwen-image-edit-plus": "seedream-5.0-lite",
    "qwen-image-plus": "seedream-5.0-lite",
    "dall-e": "dall-e-3",
    "imagen": "imagen-3.0",
    "flux": "flux-schnell",
    "seedream": "seedream-5.0-lite",
}


DEFAULT_PIPELINE_CONFIG: dict[str, Any] = {
    "media": {
        "kind": "auto",
        "ratio": "16:9",
        "duration_seconds": 3,
        "quality": "standard",
    },
    "approvals": {
        "outline_required": True,
        "checkpoint_batch_size": 3,
        "publish_requires_approval": True,
    },
    "providers": {
        "video_preference": ["dashscope", "novita", "replicate", "veo3"],
        "image_preference": ["qwen-image-edit-plus", "qwen-image-plus"],
        "allow_fallback_to_image": False,
    },
    "continuity": {
        "use_character_refs": True,
        "use_previous_exit_frame": True,
        "max_reference_images": 8,
    },
    "feature_flags": FEATURE_FLAG_DEFAULTS.copy(),
}


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def normalize_pipeline_config(
    config: dict[str, Any] | None = None,
    *,
    workflow_state: dict[str, Any] | str | None = None,
    workflow_type: str | None = None,
    requested_media_kind: str | None = None,
    frame_ratio: str | None = None,
    requested_video_ratio: str | None = None,
) -> dict[str, Any]:
    state = _safe_dict(workflow_state)
    raw_config = _safe_dict(config) or _safe_dict(state.get("pipeline_config"))
    normalized = _deep_merge(DEFAULT_PIPELINE_CONFIG, raw_config)

    media = normalized.setdefault("media", {})
    legacy_kind = requested_media_kind or state.get("requested_media_kind")
    if legacy_kind in VALID_MEDIA_KINDS:
        media["kind"] = legacy_kind
    if workflow_type == "narrated_image_story":
        media["kind"] = "image"
    if media.get("kind") not in VALID_MEDIA_KINDS:
        media["kind"] = "auto"

    ratio = requested_video_ratio or state.get("requested_video_ratio") or frame_ratio or state.get("frame_ratio")
    if ratio in VALID_RATIOS:
        media["ratio"] = ratio
    if media.get("ratio") not in VALID_RATIOS:
        media["ratio"] = os.getenv("VIDEO_DEFAULT_RATIO", "16:9")

    try:
        duration = int(media.get("duration_seconds") or 3)
    except Exception:
        duration = 3
    # Keep every render within the project's credit-safe 2–3 second window.
    media["duration_seconds"] = max(3, min(duration, 3))

    providers = normalized.setdefault("providers", {})
    video_pref = providers.get("video_preference")
    if not isinstance(video_pref, list) or not video_pref:
        video_pref = ["dashscope", "novita", "replicate", "veo3"]
    providers["video_preference"] = [
        str(provider)
        for provider in video_pref
        if provider and str(provider).lower() != "aiml"
    ] or ["dashscope", "novita", "replicate", "veo3"]

    image_pref = providers.get("image_preference")
    if not isinstance(image_pref, list) or not image_pref:
        image_pref = ["qwen-image-edit-plus", "qwen-image-plus"]
    providers["image_preference"] = [str(provider) for provider in image_pref if provider]
    providers["allow_fallback_to_image"] = bool(providers.get("allow_fallback_to_image", False))

    continuity = normalized.setdefault("continuity", {})
    continuity["use_character_refs"] = bool(continuity.get("use_character_refs", True))
    continuity["use_previous_exit_frame"] = bool(continuity.get("use_previous_exit_frame", True))
    try:
        max_refs = int(continuity.get("max_reference_images") or 8)
    except Exception:
        max_refs = 8
    continuity["max_reference_images"] = max(0, min(max_refs, 9))

    approvals = normalized.setdefault("approvals", {})
    try:
        batch_size = int(approvals.get("checkpoint_batch_size") or 3)
    except Exception:
        batch_size = 3
    approvals["checkpoint_batch_size"] = max(0, min(batch_size, 10))
    approvals["outline_required"] = bool(approvals.get("outline_required", True))
    approvals["publish_requires_approval"] = bool(approvals.get("publish_requires_approval", True))

    return normalized


def workflow_state_with_pipeline_config(
    workflow_state: dict[str, Any] | str | None,
    pipeline_config: dict[str, Any],
) -> dict[str, Any]:
    state = _safe_dict(workflow_state)
    state["pipeline_config"] = pipeline_config
    state["requested_media_kind"] = pipeline_config["media"]["kind"]
    state["requested_video_ratio"] = pipeline_config["media"]["ratio"]
    state.setdefault("frame_ratio", pipeline_config["media"]["ratio"])
    return state


# Feature flag helpers for Agent SDK integration

def get_feature_flags(
    workflow_state: dict[str, Any] | str | None = None,
    pipeline_config: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """Get feature flags from workflow_state or pipeline_config with defaults applied."""
    flags = FEATURE_FLAG_DEFAULTS.copy()
    
    if pipeline_config:
        config_flags = _safe_dict(pipeline_config).get("feature_flags", {})
        flags.update(config_flags)
    
    if workflow_state:
        state = _safe_dict(workflow_state)
        if "feature_flags" in state:
            flags.update(state["feature_flags"])
        elif "pipeline_config" in state:
            config_flags = _safe_dict(state["pipeline_config"]).get("feature_flags", {})
            flags.update(config_flags)
    
    return flags


def is_feature_enabled(
    flag_name: str,
    workflow_state: dict[str, Any] | str | None = None,
    pipeline_config: dict[str, Any] | None = None,
) -> bool:
    """Check if a specific feature flag is enabled."""
    flags = get_feature_flags(workflow_state, pipeline_config)
    return bool(flags.get(flag_name, False))


def get_enabled_features(
    workflow_state: dict[str, Any] | str | None = None,
    pipeline_config: dict[str, Any] | None = None,
) -> list[str]:
    """Get list of enabled feature flag names."""
    flags = get_feature_flags(workflow_state, pipeline_config)
    return [name for name, enabled in flags.items() if enabled]


def update_feature_flags(
    workflow_state: dict[str, Any] | str | None,
    updates: dict[str, bool],
) -> dict[str, Any]:
    """Update feature flags in workflow_state, preserving other state."""
    state = _safe_dict(workflow_state)
    
    if "feature_flags" not in state:
        state["feature_flags"] = FEATURE_FLAG_DEFAULTS.copy()
    
    state["feature_flags"].update(updates)
    
    # Also update pipeline_config if present
    if "pipeline_config" in state:
        state["pipeline_config"]["feature_flags"] = state["feature_flags"]
    
    return state


# GenBlaze helper functions

def get_genblaze_video_model(provider_name: str) -> str | None:
    """Get the GenBlaze video model for a given provider name."""
    return GENBLaze_VIDEO_MODELS.get(provider_name.lower())


def get_genblaze_image_model(provider_name: str) -> str | None:
    """Get the GenBlaze image model for a given provider name."""
    return GENBLaze_IMAGE_MODELS.get(provider_name.lower())


def should_use_genblaze(
    workflow_state: dict[str, Any] | str | None = None,
    pipeline_config: dict[str, Any] | None = None,
) -> bool:
    """Check if GenBlaze SDK should be used for generation."""
    return is_feature_enabled("use_genblaze", workflow_state, pipeline_config)


def get_genblaze_preferred_model(
    pipeline_config: dict[str, Any] | None = None,
    modality: str = "video",
) -> str | None:
    """Get the preferred GenBlaze model from pipeline config.
    
    Args:
        pipeline_config: Pipeline configuration
        modality: Either "video" or "image"
    
    Returns:
        GenBlaze model name or None
    """
    if not pipeline_config:
        return None
    
    providers = pipeline_config.get("providers", {})
    if modality == "video":
        pref_list = providers.get("video_preference", [])
    else:
        pref_list = providers.get("image_preference", [])
    
    if not pref_list:
        return None
    
    # Try each provider in order
    model_map = GENBLaze_VIDEO_MODELS if modality == "video" else GENBLaze_IMAGE_MODELS
    for provider in pref_list:
        model = model_map.get(provider.lower())
        if model:
            return model
    
    return None
