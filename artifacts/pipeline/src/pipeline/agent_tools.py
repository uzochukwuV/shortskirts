"""
Agent Tool Registry for Dysentry Video Production.

This module defines all tools available to the agent orchestrator.
Tools are typed, validated functions that interact with the production pipeline.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Import tools for registration
from pipeline.agent_media_tools import register_media_tools
from pipeline.agent_production_tools import register_production_tools


@dataclass
class ToolDefinition:
    """Definition of an agent tool."""
    name: str
    description: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False
    category: str = "general"


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None


# ─── Tool Registry ────────────────────────────────────────────────────────────

TOOL_DEFINITIONS: dict[str, ToolDefinition] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    requires_confirmation: bool = False,
    category: str = "general",
) -> Callable:
    """Decorator to register a tool."""
    def decorator(func: Callable) -> Callable:
        TOOL_DEFINITIONS[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
            category=category,
        )
        return func
    return decorator


def get_tool_definition(name: str) -> Optional[ToolDefinition]:
    """Get a tool definition by name."""
    return TOOL_DEFINITIONS.get(name)


def get_all_tools() -> list[dict[str, Any]]:
    """Get all tool definitions for LLM function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in TOOL_DEFINITIONS.values()
    ]


# ─── Tool Implementations ─────────────────────────────────────────────────────

async def get_story_context_impl(
    pool: Any,
    story_id: str,
) -> dict[str, Any]:
    """
    Get complete story context for the agent.
    Includes all episodes, scenes, characters, and current status.
    """
    # Get story
    story = await pool.fetchrow(
        "SELECT * FROM stories WHERE id = $1",
        story_id,
    )
    if not story:
        raise ValueError(f"Story not found: {story_id}")
    
    # Get episodes
    episodes = await pool.fetch(
        "SELECT * FROM episodes WHERE story_id = $1 ORDER BY episode_number",
        story_id,
    )
    
    # Get characters
    characters = await pool.fetch(
        "SELECT * FROM characters WHERE story_id = $1",
        story_id,
    )
    
    # Get all scenes grouped by episode
    episode_ids = [str(ep["id"]) for ep in episodes]
    all_scenes = {}
    if episode_ids:
        scenes = await pool.fetch(
            f"""SELECT s.*, e.episode_number 
                FROM scenes s 
                JOIN episodes e ON s.episode_id = e.id 
                WHERE s.episode_id = ANY($1::uuid[])
                ORDER BY s.scene_number""",
            episode_ids,
        )
        for scene in scenes:
            # Handle both dict-like and attribute-like rows
            ep_id = str(getattr(scene, 'episode_id', scene.get('episode_id', '')))
            if not ep_id:
                continue
            if ep_id not in all_scenes:
                all_scenes[ep_id] = []
            # Convert to dict if needed
            scene_dict = dict(scene) if not isinstance(scene, dict) else scene
            all_scenes[ep_id].append(scene_dict)
    
    # Get active jobs
    jobs = await pool.fetch(
        """SELECT * FROM generation_jobs 
           WHERE entity_type = 'story' AND entity_id = $1 
           AND status IN ('pending', 'running', 'retrying')
           ORDER BY created_at DESC LIMIT 5""",
        story_id,
    )
    
    # Get bibles
    bibles = await pool.fetch(
        "SELECT * FROM bibles WHERE story_id = $1",
        story_id,
    )
    
    # Parse JSON fields
    episode_plan = story.get("episode_plan")
    if isinstance(episode_plan, str):
        try:
            episode_plan = json.loads(episode_plan)
        except:
            episode_plan = {}
    
    workflow_state = story.get("workflow_state")
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except:
            workflow_state = {}
    
    return {
        "id": str(story["id"]),
        "title": story["title"],
        "prompt": story["prompt"],
        "status": story["status"],
        "workflow_type": story.get("workflow_type", "creator_series"),
        "episode_plan": episode_plan,
        "workflow_state": workflow_state,
        "episodes": [
            {
                "id": str(ep["id"]),
                "episode_number": ep["episode_number"],
                "title": ep["title"],
                "status": ep["status"],
                "scenes": [
                    {
                        "id": str(s["id"]),
                        "scene_number": s["scene_number"],
                        "title": json.loads(s.get("generation_metadata", "{}")).get("title", f"Scene {s['scene_number']}"),
                        "description": json.loads(s.get("generation_metadata", "{}")).get("description", ""),
                        "status": s["status"],
                        "clip_url": s.get("clip_url"),
                        "image_url": s.get("image_url"),
                        "exit_frame_url": s.get("exit_frame_url"),
                        "duration": s.get("duration"),
                        "approval_status": s.get("approval_status", "pending"),
                        "locked": s.get("locked", False),
                    }
                    for s in all_scenes.get(str(ep["id"]), [])
                ],
            }
            for ep in episodes
        ],
        "characters": [
            {
                "id": str(c["id"]),
                "name": c["name"],
                "role": c["role"],
                "description": c["description"],
                "ref_image_urls": c.get("ref_image_urls", []),
                "approval_status": c.get("approval_status", "pending"),
            }
            for c in characters
        ],
        "active_jobs": [
            {
                "id": str(j["id"]),
                "status": j["status"],
                "job_type": j.get("job_type", "unknown"),
                "current_step": j.get("current_step", ""),
                "progress": j.get("progress", 0),
                "total_steps": j.get("total_steps", 0),
            }
            for j in jobs
        ],
        "bibles": [
            {
                "id": str(b["id"]),
                "bible_type": b["bible_type"],
                "name": b["name"],
                "content": b.get("content", {}),
            }
            for b in bibles
        ],
    }


async def get_scene_timeline_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
) -> dict[str, Any]:
    """
    Get adjacent scenes for continuity planning.
    Returns previous and next scene context.
    """
    # Get the scene
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id, e.episode_id, e.episode_number
           FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    scene_num = scene["scene_number"]
    episode_id = str(scene["episode_id"])
    
    # Get previous scene (same episode or previous)
    prev_scene = await pool.fetchrow(
        """SELECT s.*, e.episode_number
           FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE e.story_id = $1 
           AND (
               (e.episode_id = $2 AND s.scene_number < $3)
               OR e.episode_number = (
                   SELECT MAX(episode_number) FROM episodes 
                   WHERE story_id = $1 AND episode_number < $4
               )
           )
           ORDER BY e.episode_number DESC, s.scene_number DESC
           LIMIT 1""",
        story_id, episode_id, scene_num, scene["episode_number"],
    )
    
    # Get next scene
    next_scene = await pool.fetchrow(
        """SELECT s.*, e.episode_number
           FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE e.story_id = $1 
           AND (
               (e.episode_id = $2 AND s.scene_number > $3)
               OR e.episode_number = (
                   SELECT MIN(episode_number) FROM episodes 
                   WHERE story_id = $1 AND episode_number > $4
               )
           )
           ORDER BY e.episode_number ASC, s.scene_number ASC
           LIMIT 1""",
        story_id, episode_id, scene_num, scene["episode_number"],
    )
    
    # Get scene characters
    scene_chars = await pool.fetch(
        """SELECT c.id, c.name, c.role
           FROM characters c
           JOIN scene_characters sc ON c.id = sc.character_id
           WHERE sc.scene_id = $1""",
        scene_id,
    )
    
    def scene_to_dict(s) -> Optional[dict]:
        if not s:
            return None
        meta = json.loads(s.get("generation_metadata") or "{}")
        return {
            "id": str(s["id"]),
            "scene_number": s["scene_number"],
            "episode_number": s["episode_number"],
            "exit_frame_url": s.get("exit_frame_url"),
            "description": meta.get("description", ""),
            "location": meta.get("location", ""),
            "mood": meta.get("mood", ""),
            "characters": [],
        }
    
    return {
        "current_scene": {
            "id": str(scene["id"]),
            "scene_number": scene["scene_number"],
            "episode_number": scene["episode_number"],
            "exit_frame_url": scene.get("exit_frame_url"),
            "description": json.loads(scene.get("generation_metadata") or "{}").get("description", ""),
            "characters": [{"id": str(c["id"]), "name": c["name"]} for c in scene_chars],
        },
        "previous_scene": scene_to_dict(prev_scene),
        "next_scene": scene_to_dict(next_scene),
    }


async def list_scene_assets_impl(
    pool: Any,
    story_id: str,
    asset_type: Optional[str] = None,  # "character_ref", "exit_frame", "style_ref"
) -> dict[str, Any]:
    """
    List all assets (references, exit frames) for a story.
    """
    assets = {"character_refs": [], "exit_frames": [], "style_refs": []}
    
    # Character references
    characters = await pool.fetch(
        """SELECT c.id, c.name, c.ref_image_urls
           FROM characters c WHERE c.story_id = $1""",
        story_id,
    )
    for c in characters:
        for url in (c.get("ref_image_urls") or []):
            assets["character_refs"].append({
                "id": str(c["id"]),
                "name": c["name"],
                "url": url,
                "type": "character_ref",
            })
    
    # Exit frames from scenes
    scenes = await pool.fetch(
        """SELECT s.id, s.scene_number, s.exit_frame_url, e.episode_number
           FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE e.story_id = $1 AND s.exit_frame_url IS NOT NULL""",
        story_id,
    )
    for s in scenes:
        assets["exit_frames"].append({
            "id": str(s["id"]),
            "scene_number": s["scene_number"],
            "episode_number": s["episode_number"],
            "url": s["exit_frame_url"],
            "type": "exit_frame",
        })
    
    # Filter by type if requested
    if asset_type:
        return {"assets": [a for a in assets.get(f"{asset_type}s", []) if a.get("type") == asset_type]}
    
    return assets


async def get_provider_status_impl() -> dict[str, Any]:
    """
    Get current AI provider availability.
    """
    from pipeline.provider_status import get_provider_status
    status = await get_provider_status()
    return status


async def get_job_status_impl(
    pool: Any,
    job_id: str,
) -> dict[str, Any]:
    """
    Get status of a generation job.
    """
    job = await pool.fetchrow(
        "SELECT * FROM generation_jobs WHERE id = $1",
        job_id,
    )
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    return {
        "id": str(job["id"]),
        "entity_type": job["entity_type"],
        "entity_id": str(job["entity_id"]),
        "status": job["status"],
        "job_type": job.get("job_type"),
        "current_step": job.get("current_step", ""),
        "progress": job.get("progress", 0),
        "total_steps": job.get("total_steps", 0),
        "error": job.get("error"),
        "result": job.get("result"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "created_at": job.get("created_at"),
    }


async def create_scene_impl(
    pool: Any,
    story_id: str,
    episode_id: str,
    scene_data: dict[str, Any],
    insert_after: Optional[int] = None,
    auto_generate: bool = True,
) -> dict[str, Any]:
    """
    Create a new scene in an episode.
    Optionally inserts after a specific scene number.
    If auto_generate=True, creates a generation job and returns job_id.
    """
    # Verify ownership
    episode = await pool.fetchrow(
        """SELECT e.* FROM episodes e
           JOIN stories s ON e.story_id = s.id
           WHERE e.id = $1 AND s.id = $2""",
        episode_id, story_id,
    )
    if not episode:
        raise ValueError(f"Episode not found: {episode_id}")
    
    # Get max scene number and keep insertion collision-safe.
    max_scene = await pool.fetchval(
        "SELECT COALESCE(MAX(scene_number), 0) FROM scenes WHERE episode_id = $1",
        episode_id,
    )

    effective_insert_after = insert_after if insert_after is not None else None
    if effective_insert_after is not None:
        effective_insert_after = min(effective_insert_after, max_scene)

    new_scene_num = (effective_insert_after + 1) if effective_insert_after is not None else max_scene + 1
    previous_scene_num = effective_insert_after if effective_insert_after is not None else max_scene

    # Generate metadata
    metadata = {
        "title": scene_data.get("title", f"Scene {new_scene_num}"),
        "description": scene_data.get("description", ""),
        "visual_prompt": scene_data.get("visual_prompt", scene_data.get("prompt", "")),
        "mood": scene_data.get("mood", ""),
        "location": scene_data.get("location", ""),
        "narration": scene_data.get("narration", ""),
        "action": scene_data.get("action", ""),
        "media_kind": scene_data.get("media_kind", "video"),
        "duration_seconds": scene_data.get("duration_seconds", 5),
    }

    result = None
    async with pool.acquire() as conn:
        async with conn.transaction():
            if effective_insert_after is not None and effective_insert_after < max_scene:
                temp_offset = max_scene + 1000
                await conn.execute(
                    """UPDATE scenes
                       SET scene_number = scene_number + $3
                       WHERE episode_id = $1 AND scene_number > $2""",
                    episode_id, effective_insert_after, temp_offset,
                )

            result = await conn.fetchrow(
                """INSERT INTO scenes (
                       episode_id,
                       scene_number,
                       prompt,
                       status,
                       generation_metadata,
                       source_scene_id
                   )
                   VALUES ($1, $2, $3, 'pending', $4::jsonb, $5)
                   RETURNING *""",
                episode_id,
                new_scene_num,
                scene_data.get("prompt", f"Scene {new_scene_num}"),
                json.dumps(metadata),
                None,
            )

            if previous_scene_num > 0:
                prev_scene = await conn.fetchrow(
                    """SELECT id, scene_number, exit_frame_url, clip_url, image_url
                       FROM scenes
                       WHERE episode_id = $1 AND scene_number = $2""",
                    episode_id,
                    previous_scene_num,
                )
                if prev_scene:
                    continuity_url = (
                        prev_scene.get("exit_frame_url")
                        or prev_scene.get("image_url")
                    )
                    continuity_meta = dict(metadata)
                    if continuity_url:
                        continuity_meta["continuity_reference"] = {
                            "source_scene_id": str(prev_scene["id"]),
                            "source_scene_number": prev_scene["scene_number"],
                            "exit_frame_url": continuity_url,
                            "type": "exit_frame",
                        }
                        continuity_meta["reference_image_urls"] = [continuity_url]

                    await conn.execute(
                        """UPDATE scenes
                           SET source_scene_id = $2,
                               generation_metadata = $3::jsonb,
                               updated_at = now()
                           WHERE id = $1""",
                        result["id"],
                        prev_scene["id"],
                        json.dumps(continuity_meta),
                    )

            if effective_insert_after is not None and effective_insert_after < max_scene:
                temp_offset = max_scene + 1000
                await conn.execute(
                    """UPDATE scenes
                       SET scene_number = scene_number - $3 + 1
                       WHERE episode_id = $1 AND scene_number > $2 + $3""",
                    episode_id, effective_insert_after, temp_offset,
                )

    # Handle both dict-like and row-like objects
    result_id = getattr(result, "id", result.get("id") if hasattr(result, "get") else None)
    result_scene_num = getattr(result, "scene_number", result.get("scene_number") if hasattr(result, "get") else None)
    result_status = getattr(result, "status", result.get("status") if hasattr(result, "get") else None)
    scene_id = str(result_id) if result_id else "unknown"
    
    # Create generation job if auto_generate is enabled
    job_id = None
    if auto_generate:
        job_row = await pool.fetchrow(
            """INSERT INTO generation_jobs
               (entity_type, entity_id, status, total_steps, current_step, job_type)
               VALUES ('scene', $1, 'pending', 1, 'Queued for generation', 'scene_gen')
               RETURNING *""",
            scene_id,
        )
        job_id = str(job_row["id"])
        
        # Try to enqueue the job (may fail if job_queue not available)
        try:
            from job_queue import enqueue_job, WORKLOAD_MEDIA
            await enqueue_job(job_id, workload=WORKLOAD_MEDIA)
        except Exception:
            pass  # Job is created but may not be queued
    
    return {
        "id": scene_id,
        "scene_number": result_scene_num if result_scene_num else new_scene_num,
        "title": metadata["title"],
        "description": metadata["description"],
        "status": result_status if result_status else "pending",
        "job_id": job_id,  # Return job_id for polling
        "poll_url": f"/pipeline/jobs/{job_id}" if job_id else None,
    }


async def update_scene_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Update an existing scene.
    """
    # Verify ownership
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    if scene.get("locked"):
        raise ValueError("Scene is locked and cannot be updated")
    
    # Build update
    set_clauses = []
    params = [scene_id]
    param_idx = 2
    
    if "prompt" in updates:
        set_clauses.append(f"prompt = ${param_idx}")
        params.append(updates["prompt"])
        param_idx += 1
    
    if "title" in updates or "description" in updates or "mood" in updates or "location" in updates or "narration" in updates:
        # Merge with existing metadata
        existing_meta = json.loads(scene.get("generation_metadata") or "{}")
        existing_meta.update({k: v for k, v in updates.items() if k in ["title", "description", "mood", "location", "narration", "visual_prompt", "action", "media_kind"]})
        set_clauses.append(f"generation_metadata = ${param_idx}::jsonb")
        params.append(json.dumps(existing_meta))
        param_idx += 1
    
    if not set_clauses:
        return {"id": str(scene["id"]), "message": "No updates provided"}
    
    set_clauses.append("updated_at = now()")
    
    query = f"""UPDATE scenes SET {', '.join(set_clauses)}
                WHERE id = $1 RETURNING *"""
    
    result = await pool.fetchrow(query, *params)
    
    return {
        "id": str(result["id"]),
        "scene_number": result["scene_number"],
        "updated": True,
    }


async def delete_scene_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
) -> dict[str, Any]:
    """
    Delete a scene and reorder subsequent scenes.
    """
    # Verify ownership
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id, e.id as ep_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    scene_num = scene["scene_number"]
    episode_id = str(scene["ep_id"])
    
    # Delete scene
    await pool.execute("DELETE FROM scenes WHERE id = $1", scene_id)
    
    # Reorder subsequent scenes (no ORDER BY needed for simple decrement)
    await pool.execute(
        """UPDATE scenes SET scene_number = scene_number - 1
           WHERE episode_id = $1 AND scene_number > $2""",
        episode_id, scene_num,
    )
    
    return {"deleted": True, "scene_number": scene_num}


async def regenerate_scene_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
) -> dict[str, Any]:
    """
    Queue a scene for regeneration via the existing job system.
    """
    from job_queue import enqueue_job, WORKLOAD_MEDIA
    
    # Verify ownership and get scene
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    if scene.get("locked"):
        raise ValueError("Scene is locked and cannot be regenerated")
    
    if scene.get("status") == "running":
        raise ValueError("Scene is already being regenerated")
    
    # Update scene status
    await pool.execute(
        """UPDATE scenes SET status = 'running', updated_at = now()
           WHERE id = $1""",
        scene_id,
    )
    
    # Increment regeneration count
    await pool.execute(
        """UPDATE scenes SET regeneration_count = COALESCE(regeneration_count, 0) + 1
           WHERE id = $1""",
        scene_id,
    )
    
    # Create job
    job = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type, result)
           VALUES ('scene', $1, 'pending', 1, 'Queued for regeneration', 'scene_regen', '{}'::jsonb)
           RETURNING *""",
        scene_id,
    )
    
    # Enqueue
    await enqueue_job(str(job["id"]), workload=WORKLOAD_MEDIA)
    
    return {
        "job_id": str(job["id"]),
        "status": "queued",
        "scene_id": scene_id,
    }


async def set_scene_continuity_impl(
    pool: Any,
    story_id: str,
    source_scene_id: str,
    target_scene_id: str,
    continuity_type: str = "exit_frame",
    exit_frame_url: Optional[str] = None,
    reference_image_url: Optional[str] = None,
) -> dict[str, Any]:
    """
    Link scenes for continuity - set a source scene's exit frame or reference image.
    """
    # Verify ownership
    source = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        source_scene_id, story_id,
    )
    target = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        target_scene_id, story_id,
    )
    
    if not source or not target:
        raise ValueError("Source or target scene not found")
    
    # Use provided exit_frame_url or get from source
    ref_url = exit_frame_url or source.get("exit_frame_url") or reference_image_url
    
    # Update target's generation metadata with continuity reference
    existing_meta = json.loads(target.get("generation_metadata") or "{}")
    existing_meta["continuity_reference"] = {
        "source_scene_id": str(source["id"]),
        "source_scene_number": source["scene_number"],
        "exit_frame_url": ref_url,
        "type": continuity_type,
    }
    
    # Also add to reference_image_urls if provided
    if ref_url:
        ref_urls = existing_meta.get("reference_image_urls", [])
        if ref_url not in ref_urls:
            ref_urls.insert(0, ref_url)
        existing_meta["reference_image_urls"] = ref_urls
    
    await pool.execute(
        """UPDATE scenes SET generation_metadata = $1::jsonb, updated_at = now()
           WHERE id = $2""",
        json.dumps(existing_meta), target_scene_id,
    )
    
    return {
        "continuity_set": True,
        "target_scene_id": target_scene_id,
        "source_scene_id": source_scene_id,
        "exit_frame_url": ref_url,
    }


async def approve_scene_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
) -> dict[str, Any]:
    """
    Approve a scene for final assembly.
    """
    # Verify ownership
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    await pool.execute(
        """UPDATE scenes 
           SET approval_status = 'approved', approved_at = now(), updated_at = now()
           WHERE id = $1""",
        scene_id,
    )
    
    return {"id": scene_id, "approval_status": "approved"}


async def approve_story_outline_impl(
    pool: Any,
    story_id: str,
) -> dict[str, Any]:
    """
    Approve a story outline for generation.
    """
    story = await pool.fetchrow(
        "SELECT * FROM stories WHERE id = $1",
        story_id,
    )
    if not story:
        raise ValueError(f"Story not found: {story_id}")

    if (story.get("status") or "").strip().lower() != "draft":
        raise ValueError("Outline approval is only allowed for draft stories")

    updated = await pool.fetchrow(
        """UPDATE stories
           SET status='approved', approval_status='approved', approved_at=now(), updated_at=now()
           WHERE id=$1
           RETURNING *""",
        story_id,
    )
    if not updated:
        raise ValueError(f"Story not found: {story_id}")

    try:
        from pipeline.history import record_story_history
        await record_story_history(
            pool,
            story=updated,
            event_type="outline_approved",
            payload={
                "status": updated["status"],
                "approval_status": updated.get("approval_status"),
            },
        )
    except Exception:
        pass

    return {
        "id": str(updated["id"]),
        "status": updated.get("status"),
        "approval_status": updated.get("approval_status"),
        "approved_at": updated.get("approved_at"),
    }


async def launch_story_generation_impl(
    pool: Any,
    story_id: str,
) -> dict[str, Any]:
    """
    Approve a draft outline if needed, then start story generation.
    """
    story = await pool.fetchrow(
        "SELECT * FROM stories WHERE id = $1",
        story_id,
    )
    if not story:
        raise ValueError(f"Story not found: {story_id}")

    story_status = (story.get("status") or "").strip().lower()
    if story_status == "draft":
        await approve_story_outline_impl(pool, story_id)

    updated_story = await pool.fetchrow(
        """UPDATE stories
           SET status='generating', updated_at=now()
           WHERE id=$1
           AND status NOT IN ('generating', 'checkpoint_review')
           RETURNING *""",
        story_id,
    )

    if not updated_story:
        existing_story = await pool.fetchrow(
            "SELECT * FROM stories WHERE id=$1",
            story_id,
        )
        if not existing_story:
            raise ValueError(f"Story not found: {story_id}")
        if (existing_story.get("status") or "").strip().lower() in {"generating", "checkpoint_review"}:
            raise ValueError("Generation already in progress")
        raise ValueError("Cannot start generation")

    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('story',$1,'pending',0,'Queued','full_episode')
           RETURNING *""",
        story_id,
    )
    job_id = str(job_row["id"])

    try:
        from job_queue import enqueue_job, WORKLOAD_STORY
        await enqueue_job(job_id, workload=WORKLOAD_STORY)
    except Exception:
        pass

    return {
        "id": job_id,
        "entity_type": "story",
        "entity_id": story_id,
        "status": "pending",
        "progress": 0,
        "total_steps": 0,
        "current_step": "Queued",
    }
async def lock_scene_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
    locked: bool = True,
) -> dict[str, Any]:
    """
    Lock or unlock a scene to prevent/allow regeneration.
    """
    # Verify ownership
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    await pool.execute(
        "UPDATE scenes SET locked = $1, updated_at = now() WHERE id = $2",
        locked, scene_id,
    )
    
    return {"id": scene_id, "locked": locked}


async def generate_scene_description_impl(
    story_id: str,
    episode_id: str,
    instruction: str,
    story_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Use LLM to generate scene data from natural language instruction.
    """
    from pipeline.agent_llm import agent_chat_simple, ChatMessage
    
    # Build context
    context_parts = []
    if story_context:
        context_parts.append(f"Story: {story_context.get('title', 'Untitled')}")
        plan = story_context.get("episode_plan", {})
        if plan:
            context_parts.append(f"Synopsis: {plan.get('synopsis', '')}")
        
        characters = story_context.get("characters", [])
        if characters:
            context_parts.append(f"Characters: {', '.join(c['name'] for c in characters)}")
    
    system_prompt = """You are a video production assistant that creates scene descriptions.
Given a natural language instruction, generate structured scene data.
Return JSON with this structure:
{
    "title": "Scene title",
    "description": "What happens in the scene",
    "prompt": "Visual generation prompt",
    "location": "Where the scene takes place",
    "mood": "Emotional tone",
    "action": "Key action",
    "duration_seconds": 5,
    "narration": "Optional dialogue/narration"
}
Keep descriptions concise but vivid. Focus on visuals that can be generated."""
    
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=f"Context:\n" + "\n".join(context_parts) + f"\n\nInstruction: {instruction}"),
    ]
    
    try:
        response = await agent_chat_simple(messages, temperature=0.7, max_tokens=1000)
        # Try to parse JSON
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        result = json.loads(response.strip())
        return result
    except json.JSONDecodeError:
        raise ValueError(f"Could not parse scene description: {response[:200]}")


async def poll_job_until_complete_impl(
    pool: Any,
    job_id: str,
    poll_interval: int = 5,
    timeout: int = 600,
) -> dict[str, Any]:
    """
    Poll a job until it completes or times out.
    This is typically used with streaming - for now just returns current status.
    """
    import asyncio
    import time
    
    deadline = time.time() + timeout
    
    while time.time() < deadline:
        job = await pool.fetchrow(
            "SELECT * FROM generation_jobs WHERE id = $1",
            job_id,
        )
        
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        status = job["status"]
        if status in ("completed", "failed", "canceled"):
            return {
                "job_id": job_id,
                "status": status,
                "result": job.get("result"),
                "error": job.get("error"),
            }
        
        await asyncio.sleep(poll_interval)
    
    return {
        "job_id": job_id,
        "status": "timeout",
        "message": f"Job polling timed out after {timeout} seconds",
    }


# ─── Register All Tools ───────────────────────────────────────────────────────

def register_all_tools():
    """Register all tools with their definitions."""
    
    # Register advanced media tools (frame extraction, Genblaze, etc.)
    register_media_tools(register_tool)
    
    # Register production tools (assembly, audio, publishing, etc.)
    register_production_tools(register_tool)
    
    # Read tools
    register_tool(
        name="get_story_context",
        description="Get complete story context including episodes, scenes, characters, and status. Use this to understand the current state of a story.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "The story ID"},
            },
            "required": ["story_id"],
        },
        category="read",
    )(get_story_context_impl)
    
    register_tool(
        name="get_scene_timeline",
        description="Get adjacent scenes for continuity planning. Returns previous and next scene context.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "The story ID"},
                "scene_id": {"type": "string", "description": "The scene ID to get timeline for"},
            },
            "required": ["story_id", "scene_id"],
        },
        category="read",
    )(get_scene_timeline_impl)
    
    register_tool(
        name="list_scene_assets",
        description="List all reference images and exit frames for a story.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "The story ID"},
                "asset_type": {"type": "string", "enum": ["character_ref", "exit_frame", "style_ref"], "description": "Filter by asset type"},
            },
            "required": ["story_id"],
        },
        category="read",
    )(list_scene_assets_impl)
    
    register_tool(
        name="get_provider_status",
        description="Get current AI provider availability and status.",
        parameters={"type": "object", "properties": {}},
        category="read",
    )(get_provider_status_impl)
    
    register_tool(
        name="get_job_status",
        description="Get the status of a generation job.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The job ID"},
            },
            "required": ["job_id"],
        },
        category="read",
    )(get_job_status_impl)

    register_tool(
        name="approve_story_outline",
        description="Approve a story outline so generation can begin.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "The story ID"},
            },
            "required": ["story_id"],
        },
        category="mutation",
    )(approve_story_outline_impl)

    register_tool(
        name="launch_story_generation",
        description="Approve the outline if needed and start story generation.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "The story ID"},
            },
            "required": ["story_id"],
        },
        category="generation",
    )(launch_story_generation_impl)    
    # Mutation tools
    register_tool(
        name="create_scene",
        description="Create a new scene in an episode. Returns a job_id that can be polled for generation status.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "The story ID"},
                "episode_id": {"type": "string", "description": "The episode ID to add scene to"},
                "scene_data": {
                    "type": "object",
                    "description": "Scene data including title, description, prompt, location, mood, etc.",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "prompt": {"type": "string"},
                        "visual_prompt": {"type": "string"},
                        "location": {"type": "string"},
                        "mood": {"type": "string"},
                        "narration": {"type": "string"},
                        "action": {"type": "string"},
                        "duration_seconds": {"type": "number"},
                    },
                },
                "insert_after": {"type": "integer", "description": "Scene number to insert after"},
                "auto_generate": {"type": "boolean", "description": "Whether to auto-start video generation (default: true)"},
            },
            "required": ["story_id", "episode_id", "scene_data"],
        },
        requires_confirmation=False,
        category="mutation",
    )(create_scene_impl)
    
    register_tool(
        name="update_scene",
        description="Update an existing scene's content or metadata.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "updates": {
                    "type": "object",
                    "description": "Fields to update",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "prompt": {"type": "string"},
                        "visual_prompt": {"type": "string"},
                        "mood": {"type": "string"},
                        "location": {"type": "string"},
                        "narration": {"type": "string"},
                    },
                },
            },
            "required": ["story_id", "scene_id", "updates"],
        },
        category="mutation",
    )(update_scene_impl)
    
    register_tool(
        name="delete_scene",
        description="Delete a scene. Subsequent scenes will be reordered.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
            },
            "required": ["story_id", "scene_id"],
        },
        requires_confirmation=True,
        category="mutation",
    )(delete_scene_impl)
    
    register_tool(
        name="regenerate_scene",
        description="Queue a scene for regeneration. Creates a new generation job.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
            },
            "required": ["story_id", "scene_id"],
        },
        category="generation",
    )(regenerate_scene_impl)
    
    register_tool(
        name="set_scene_continuity",
        description="Link scenes for visual continuity. Sets a source scene's exit frame or reference image for the next scene.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "source_scene_id": {"type": "string", "description": "Scene to reference for continuity"},
                "target_scene_id": {"type": "string", "description": "Scene to apply continuity to"},
                "continuity_type": {"type": "string", "enum": ["exit_frame", "character_ref", "style_ref"]},
                "exit_frame_url": {"type": "string", "description": "Optional: Custom exit frame URL (uses source scene's if not provided)"},
                "reference_image_url": {"type": "string", "description": "Optional: Custom reference image URL"},
            },
            "required": ["story_id", "source_scene_id", "target_scene_id"],
        },
        category="mutation",
    )(set_scene_continuity_impl)
    
    register_tool(
        name="approve_scene",
        description="Approve a scene for final assembly.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
            },
            "required": ["story_id", "scene_id"],
        },
        category="mutation",
    )(approve_scene_impl)
    
    register_tool(
        name="lock_scene",
        description="Lock or unlock a scene to prevent/allow regeneration.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "locked": {"type": "boolean"},
            },
            "required": ["story_id", "scene_id", "locked"],
        },
        category="mutation",
    )(lock_scene_impl)
    
    # Assistant tools
    register_tool(
        name="generate_scene_description",
        description="Generate structured scene data from natural language instruction.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "episode_id": {"type": "string"},
                "instruction": {"type": "string", "description": "Natural language description of the scene"},
                "story_context": {"type": "object", "description": "Optional story context from get_story_context"},
            },
            "required": ["story_id", "episode_id", "instruction"],
        },
        category="assistant",
    )(generate_scene_description_impl)
    
    register_tool(
        name="wait_for_generation",
        description="Poll a job until it completes or times out.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "poll_interval": {"type": "integer", "description": "Seconds between polls"},
                "timeout": {"type": "integer", "description": "Max seconds to wait"},
            },
            "required": ["job_id"],
        },
        category="generation",
    )(poll_job_until_complete_impl)


# Initialize tools on module load
register_all_tools()



