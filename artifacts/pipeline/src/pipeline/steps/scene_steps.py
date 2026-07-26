from __future__ import annotations

from typing import Any

from pipeline.pipeline_runtime import finish_pipeline_step, record_pipeline_artifact


async def complete_scene_render_step(
    *,
    run_id: str,
    step_id: str,
    story_id: str,
    episode_id: str,
    scene_id: str,
    result: dict[str, Any],
    generation_plan: Any,
    episode_number: int,
    scene_number: int,
    default_media_kind: str,
    extra_metadata: dict[str, Any] | None = None,
) -> str | None:
    media_url = result.get("image_url") or result.get("clip_url")
    metadata = {
        "episode_number": episode_number,
        "scene_number": scene_number,
        "duration": result.get("duration"),
        "provider": result.get("video_provider"),
        "model": result.get("video_model"),
        "refs_used": result.get("refs_used", 0),
    }
    metadata.update(extra_metadata or {})

    if media_url:
        await record_pipeline_artifact(
            run_id=run_id,
            step_id=step_id,
            story_id=story_id,
            episode_id=episode_id,
            scene_id=scene_id,
            artifact_type="scene_media",
            media_kind=result.get("media_kind", default_media_kind),
            url=media_url,
            metadata=metadata,
        )

    plan_output = generation_plan.model_dump() if hasattr(generation_plan, "model_dump") else generation_plan
    await finish_pipeline_step(
        step_id,
        output={
            "media_url": media_url,
            "exit_frame_url": result.get("exit_frame_url"),
            "duration": result.get("duration"),
            "provider": result.get("video_provider"),
            "model": result.get("video_model"),
            "agent_video_plan": result.get("agent_video_plan"),
            "failed_video_attempts": result.get("failed_video_attempts", []),
            "generation_plan": plan_output,
        },
        provider=result.get("video_provider"),
    )
    return media_url
