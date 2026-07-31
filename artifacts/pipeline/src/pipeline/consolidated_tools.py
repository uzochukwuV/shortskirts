"""
Consolidated Agent Tools Registry

This module consolidates all agent tools into a single registry.
Tools are organized by category and registered with the executor.

Usage:
    from pipeline.consolidated_tools import register_all_tools
    
    executor = UnifiedAgentExecutor()
    register_all_tools(executor)
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import uuid
from typing import Any, Optional
from datetime import datetime

import httpx

# Provider router for video generation
try:
    from pipeline.providers.provider_router import (
        VideoProviderRouter,
        ProviderType,
        get_router,
    )
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False
    VideoProviderRouter = None
    ProviderType = None
    get_router = None


# ══════════════════════════════════════════════════════════════════════════════
# STORY & CONTEXT TOOLS
# ══════════════════════════════════════════════════════════════════════════════

async def get_story_context(pool: Any, story_id: str) -> dict:
    """Get complete story context including all episodes, scenes, characters."""
    story = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
    if not story:
        raise ValueError(f"Story not found: {story_id}")
    
    episodes = await pool.fetch(
        "SELECT * FROM episodes WHERE story_id = $1 ORDER BY episode_number",
        story_id,
    )
    
    characters = await pool.fetch(
        "SELECT * FROM characters WHERE story_id = $1",
        story_id,
    )
    
    # Get scenes
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
            ep_id = str(scene["episode_id"])
            if ep_id not in all_scenes:
                all_scenes[ep_id] = []
            all_scenes[ep_id].append(dict(scene))
    
    # Parse character references
    char_list = []
    for char in characters:
        c = dict(char)
        refs = char.get("ref_image_urls") or []
        if isinstance(refs, str):
            try:
                refs = json.loads(refs)
            except:
                refs = []
        c["ref_image_urls"] = refs
        char_list.append(c)
    
    return {
        "story": dict(story),
        "episodes": [dict(ep) for ep in episodes],
        "scenes_by_episode": all_scenes,
        "characters": char_list,
        "total_scenes": sum(len(s) for s in all_scenes.values()),
    }


async def get_scene_timeline(pool: Any, story_id: str, scene_id: str) -> dict:
    """Get scene with adjacent scenes for continuity planning."""
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id, e.episode_number, e.title as episode_title
           FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    ep_id = str(scene["episode_id"])
    scene_num = scene["scene_number"]
    
    # Get previous scene
    prev_scene = await pool.fetchrow(
        """SELECT * FROM scenes 
           WHERE episode_id = $1 AND scene_number < $2
           ORDER BY scene_number DESC LIMIT 1""",
        ep_id, scene_num,
    )
    
    # Get next scene
    next_scene = await pool.fetchrow(
        """SELECT * FROM scenes 
           WHERE episode_id = $1 AND scene_number > $2
           ORDER BY scene_number ASC LIMIT 1""",
        ep_id, scene_num,
    )
    
    return {
        "scene": dict(scene),
        "previous_scene": dict(prev_scene) if prev_scene else None,
        "next_scene": dict(next_scene) if next_scene else None,
    }


async def list_stories(pool: Any, user_id: Optional[str] = None) -> list[dict]:
    """List all stories, optionally filtered by user."""
    if user_id:
        stories = await pool.fetch(
            "SELECT * FROM stories WHERE owner_id = $1 ORDER BY created_at DESC",
            user_id,
        )
    else:
        stories = await pool.fetch("SELECT * FROM stories ORDER BY created_at DESC")
    return [dict(s) for s in stories]


async def create_story(
    pool: Any,
    title: str,
    description: str = "",
    user_id: Optional[str] = None,
    style: str = "anime",
) -> dict:
    """Create a new story."""
    story_id = str(uuid.uuid4())
    
    await pool.execute(
        """INSERT INTO stories (id, title, prompt, owner_id, workflow_type, created_at)
           VALUES ($1, $2, $3, $4, $5, now())""",
        story_id, title, description, user_id or "default", style,
    )
    
    return {"id": story_id, "title": title, "status": "created"}


# ══════════════════════════════════════════════════════════════════════════════
# SCENE MANAGEMENT TOOLS
# ══════════════════════════════════════════════════════════════════════════════

async def create_scene(
    pool: Any,
    story_id: str,
    episode_id: str,
    prompt: str,
    scene_number: Optional[int] = None,
    title: str = "",
) -> dict:
    """Create a new scene in an episode."""
    # Get next scene number if not provided
    if scene_number is None:
        max_scene = await pool.fetchrow(
            "SELECT MAX(scene_number) as max_num FROM scenes WHERE episode_id = $1",
            episode_id,
        )
        scene_number = (max_scene["max_num"] or 0) + 1
    
    scene_id = str(uuid.uuid4())
    
    await pool.execute(
        """INSERT INTO scenes (id, episode_id, scene_number, prompt, status, created_at)
           VALUES ($1, $2, $3, $4, 'pending', now())""",
        scene_id, episode_id, scene_number, prompt,
    )
    
    return {
        "id": scene_id,
        "episode_id": episode_id,
        "scene_number": scene_number,
        "title": title,
        "status": "pending",
    }


async def update_scene(
    pool: Any,
    story_id: str,
    scene_id: str,
    **updates,
) -> dict:
    """Update scene properties."""
    scene = await pool.fetchrow(
        """SELECT s.* FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    # Build update query
    allowed_fields = ["prompt", "title", "status", "approval_status", "duration"]
    set_clause = []
    values = []
    idx = 1
    
    for field, value in updates.items():
        if field in allowed_fields:
            set_clause.append(f"{field} = ${idx}")
            values.append(value)
            idx += 1
    
    if not set_clause:
        return {"error": "No valid fields to update"}
    
    set_clause.append("updated_at = now()")
    values.append(scene_id)
    
    await pool.execute(
        f"UPDATE scenes SET {', '.join(set_clause)} WHERE id = ${idx}",
        *values,
    )
    
    return {"id": scene_id, "updated": True}


async def delete_scene(pool: Any, story_id: str, scene_id: str) -> dict:
    """Delete a scene and renumber remaining scenes."""
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id, e.id as ep_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    ep_id = scene["ep_id"]
    scene_num = scene["scene_number"]
    
    # Delete scene
    await pool.execute("DELETE FROM scenes WHERE id = $1", scene_id)
    
    # Renumber remaining scenes
    await pool.execute(
        """UPDATE scenes SET scene_number = scene_number - 1
           WHERE episode_id = $1 AND scene_number > $2""",
        ep_id, scene_num,
    )
    
    return {"id": scene_id, "deleted": True, "renumbered": True}


async def approve_scene(pool: Any, story_id: str, scene_id: str) -> dict:
    """Mark a scene as approved."""
    await pool.execute(
        """UPDATE scenes SET approval_status = 'approved', approved_at = now(), updated_at = now()
           WHERE id = $1""",
        scene_id,
    )
    return {"id": scene_id, "approval_status": "approved"}


async def lock_scene(pool: Any, story_id: str, scene_id: str, locked: bool = True) -> dict:
    """Lock/unlock a scene for editing."""
    await pool.execute(
        "UPDATE scenes SET locked = $1, updated_at = now() WHERE id = $2",
        locked, scene_id,
    )
    return {"id": scene_id, "locked": locked}


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO GENERATION TOOLS
# ══════════════════════════════════════════════════════════════════════════════

async def generate_video(
    pool: Any,
    story_id: str,
    scene_id: str,
    prompt: Optional[str] = None,
    model: str = "auto",
    provider: Optional[str] = None,
    duration: int = 5,
    ratio: str = "16:9",
) -> dict:
    """
    Generate video for a scene using the provider router.
    
    Args:
        pool: Database connection pool
        story_id: The story ID
        scene_id: The scene ID to generate video for
        prompt: Override prompt (uses scene prompt if not provided)
        model: Model name or "auto" to use default
        provider: "dashscope", "decart", or None for auto-select
        duration: Video duration in seconds (max varies by provider)
        ratio: Aspect ratio (16:9, 9:16, 1:1)
    """
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    generation_prompt = prompt or scene.get("prompt", "")
    if not generation_prompt:
        return {"error": "No prompt available for generation"}
    
    if not ROUTER_AVAILABLE:
        return {"error": "Provider router not available"}
    
    # Map provider string to ProviderType
    provider_type = None
    if provider:
        provider_lower = provider.lower()
        if provider_lower == "dashscope":
            provider_type = ProviderType.DASHSCOPE
        elif provider_lower == "decart":
            provider_type = ProviderType.DECART
    
    router = get_router()
    
    # Get available providers
    available = router.available_providers
    if not available:
        return {"error": "No video providers available"}
    
    # Create generation job
    job_id = str(uuid.uuid4())
    await pool.execute(
        """INSERT INTO generation_jobs (id, entity_type, entity_id, status, job_type, current_step)
           VALUES ($1, 'scene', $2, 'pending', 'scene_gen', 'Queued')""",
        job_id, scene_id,
    )
    
    # Update scene status
    await pool.execute(
        "UPDATE scenes SET status = 'running', updated_at = now() WHERE id = $1",
        scene_id,
    )
    
    # Get provider info
    selected_provider = router.get_provider(provider_type)
    provider_name = selected_provider.name
    provider_type_val = provider_type.value if provider_type else "auto"
    
    return {
        "job_id": job_id,
        "scene_id": scene_id,
        "status": "pending",
        "poll_url": f"/pipeline/jobs/{job_id}",
        "provider": provider_name,
        "provider_type": provider_type_val,
        "model": model,
        "prompt": generation_prompt,
        "available_providers": [p.value for p in available],
        "message": f"Video generation queued with {provider_name}",
    }


async def wait_for_generation(pool: Any, job_id: str, timeout_seconds: int = 300) -> dict:
    """Wait for a generation job to complete."""
    import asyncio
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        job = await pool.fetchrow(
            "SELECT * FROM generation_jobs WHERE id = $1",
            job_id,
        )
        
        if not job:
            return {"error": "Job not found", "job_id": job_id}
        
        status = job["status"]
        
        if status == "completed":
            return {
                "job_id": job_id,
                "status": "completed",
                "result": job.get("result"),
            }
        elif status == "failed":
            return {
                "job_id": job_id,
                "status": "failed",
                "error": job.get("error"),
            }
        
        await asyncio.sleep(5)  # Poll every 5 seconds
    
    return {
        "job_id": job_id,
        "status": "timeout",
        "message": f"Waited {timeout_seconds}s without completion",
    }


# ══════════════════════════════════════════════════════════════════════════════
# FRAME EXTRACTION TOOLS
# ══════════════════════════════════════════════════════════════════════════════

async def extract_scene_frame(
    pool: Any,
    story_id: str,
    scene_id: str,
    timestamp: Optional[float] = None,
    frame_position: str = "middle",
) -> dict:
    """Extract a frame from a scene's video."""
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    clip_url = scene.get("clip_url")
    if not clip_url:
        return {"error": "Scene has no video clip"}
    
    # Download video
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(clip_url)
            video_bytes = resp.content
    except Exception as e:
        return {"error": f"Failed to download video: {e}"}
    
    # Extract frame with FFmpeg
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
        tmp_in.write(video_bytes)
        tmp_in_path = tmp_in.name
    
    tmp_out_path = tmp_in_path.replace(".mp4", f"_frame_{timestamp or frame_position}.jpg")
    
    try:
        # Get timestamp
        if timestamp is None:
            duration = scene.get("duration") or 5
            if frame_position == "first":
                ts = 0.5
            elif frame_position == "last":
                ts = duration - 0.5
            else:
                ts = duration / 2
        else:
            ts = timestamp
        
        # Extract frame
        result = subprocess.run([
            "ffmpeg", "-y", "-i", tmp_in_path,
            "-ss", str(ts), "-vframes", "1",
            "-q:v", "2", tmp_out_path
        ], capture_output=True, timeout=30)
        
        if result.returncode != 0:
            return {"error": "FFmpeg failed", "details": result.stderr.decode()}
        
        # Upload to B2
        from storage.b2 import upload_bytes, build_key
        frame_key = build_key("stories", story_id, "scenes", f"frame_{scene_id}_{ts:.1f}.jpg")
        frame_url = upload_bytes(open(tmp_out_path, "rb").read(), frame_key, "image/jpeg")
        
        return {
            "scene_id": scene_id,
            "frame_url": frame_url,
            "timestamp": ts,
            "position": frame_position,
        }
        
    finally:
        # Cleanup
        for p in [tmp_in_path, tmp_out_path]:
            if os.path.exists(p):
                os.unlink(p)


async def screenshot_previous_scene(
    pool: Any,
    source_scene_id: str,
    target_scene_id: str,
) -> dict:
    """
    Extract exit frame from source scene and link to target scene.
    This maintains visual continuity between scenes.
    """
    # Get source scene
    source = await pool.fetchrow("SELECT * FROM scenes WHERE id = $1", source_scene_id)
    if not source:
        raise ValueError(f"Source scene not found: {source_scene_id}")
    
    # Check for existing exit frame
    exit_frame_url = source.get("exit_frame_url")
    if not exit_frame_url:
        # Extract from clip
        clip_url = source.get("clip_url")
        if not clip_url:
            return {"error": "Source scene has no clip"}
        
        # Use media_tools
        from pipeline.media_tools import extract_last_frame_png
        from storage.b2 import upload_bytes, build_key
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(clip_url)
                video_bytes = resp.content
            
            exit_frame = extract_last_frame_png(video_bytes)
            
            story_id = str(source["episode_id"])  # Would need proper lookup
            # This is simplified - in production you'd look up the story
            exit_frame_key = f"scenes/{source_scene_id}/exit_frame.png"
            exit_frame_url = upload_bytes(exit_frame, exit_frame_key, "image/png")
            
            # Save to source scene
            await pool.execute(
                "UPDATE scenes SET exit_frame_url = $1 WHERE id = $2",
                exit_frame_url, source_scene_id,
            )
        except Exception as e:
            return {"error": f"Failed to extract exit frame: {e}"}
    
    # Get target scene
    target = await pool.fetchrow("SELECT * FROM scenes WHERE id = $1", target_scene_id)
    if not target:
        raise ValueError(f"Target scene not found: {target_scene_id}")
    
    # Update target with continuity reference
    metadata = json.loads(target.get("generation_metadata") or "{}")
    metadata["continuity_reference"] = {
        "source_scene_id": source_scene_id,
        "exit_frame_url": exit_frame_url,
    }
    
    await pool.execute(
        "UPDATE scenes SET generation_metadata = $1::jsonb WHERE id = $2",
        json.dumps(metadata), target_scene_id,
    )
    
    return {
        "source_scene_id": source_scene_id,
        "target_scene_id": target_scene_id,
        "exit_frame_url": exit_frame_url,
        "linked": True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CHARACTER & REFERENCE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

async def set_character_reference(
    pool: Any,
    story_id: str,
    character_id: str,
    reference_image_url: str,
    is_primary: bool = True,
) -> dict:
    """Set a reference image for character consistency."""
    character = await pool.fetchrow(
        "SELECT * FROM characters WHERE id = $1 AND story_id = $2",
        character_id, story_id,
    )
    if not character:
        raise ValueError(f"Character not found: {character_id}")
    
    # Get existing refs
    refs = character.get("ref_image_urls") or []
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except:
            refs = []
    
    # Add new ref
    if reference_image_url not in refs:
        if is_primary:
            refs.insert(0, reference_image_url)
        else:
            refs.append(reference_image_url)
    
    # Update
    await pool.execute(
        "UPDATE characters SET ref_image_urls = $1::jsonb, updated_at = now() WHERE id = $2",
        json.dumps(refs), character_id,
    )
    
    return {
        "character_id": character_id,
        "reference_image_url": reference_image_url,
        "is_primary": is_primary,
        "total_references": len(refs),
    }


async def set_scene_continuity(
    pool: Any,
    story_id: str,
    scene_id: str,
    source_scene_id: str,
    exit_frame_url: str,
) -> dict:
    """Link scene to source scene for continuity."""
    metadata = await pool.fetchval(
        "SELECT generation_metadata FROM scenes WHERE id = $1",
        scene_id,
    )
    metadata = json.loads(metadata or "{}")
    
    metadata["continuity_reference"] = {
        "source_scene_id": source_scene_id,
        "exit_frame_url": exit_frame_url,
    }
    
    await pool.execute(
        "UPDATE scenes SET generation_metadata = $1::jsonb WHERE id = $2",
        json.dumps(metadata), scene_id,
    )
    
    return {
        "scene_id": scene_id,
        "source_scene_id": source_scene_id,
        "continuity_set": True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTION TOOLS
# ══════════════════════════════════════════════════════════════════════════════

async def assemble_episode(
    pool: Any,
    story_id: str,
    episode_id: str,
) -> dict:
    """Queue episode assembly job."""
    episode = await pool.fetchrow(
        "SELECT * FROM episodes WHERE id = $1 AND story_id = $2",
        episode_id, story_id,
    )
    if not episode:
        raise ValueError(f"Episode not found: {episode_id}")
    
    # Get approved scenes
    scenes = await pool.fetch(
        """SELECT * FROM scenes 
           WHERE episode_id = $1 AND approval_status = 'approved'
           AND clip_url IS NOT NULL
           ORDER BY scene_number""",
        episode_id,
    )
    
    if not scenes:
        return {"error": "No approved scenes with clips to assemble"}
    
    # Create assembly job
    job_id = str(uuid.uuid4())
    await pool.execute(
        """INSERT INTO generation_jobs (id, entity_type, entity_id, status, job_type, current_step)
           VALUES ($1, 'episode', $2, 'pending', 'episode_assembly', 'Gathering scenes')""",
        job_id, episode_id,
    )
    
    try:
        from job_queue import enqueue_job, WORKLOAD_ASSEMBLY
        await enqueue_job(job_id, workload=WORKLOAD_ASSEMBLY)
    except:
        pass
    
    return {
        "job_id": job_id,
        "episode_id": episode_id,
        "scenes_to_assemble": len(scenes),
        "status": "pending",
    }


async def add_transition(
    pool: Any,
    story_id: str,
    from_scene_id: str,
    to_scene_id: str,
    transition_type: str = "fade",
    duration: float = 0.5,
) -> dict:
    """Add a transition between two scenes."""
    from_scene = await pool.fetchrow(
        """SELECT s.* FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        from_scene_id, story_id,
    )
    if not from_scene:
        raise ValueError(f"From scene not found: {from_scene_id}")
    
    # Store transition in metadata
    metadata = json.loads(from_scene.get("generation_metadata") or "{}")
    
    if "transitions" not in metadata:
        metadata["transitions"] = {}
    
    metadata["transitions"][to_scene_id] = {
        "type": transition_type,
        "duration": duration,
    }
    
    await pool.execute(
        "UPDATE scenes SET generation_metadata = $1::jsonb WHERE id = $2",
        json.dumps(metadata), from_scene_id,
    )
    
    return {
        "from_scene_id": from_scene_id,
        "to_scene_id": to_scene_id,
        "transition": transition_type,
        "duration_seconds": duration,
    }


async def generate_seo_metadata(
    pool: Any,
    story_id: str,
    episode_id: str,
    platform: str = "youtube",
) -> dict:
    """Generate SEO metadata for an episode."""
    story = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
    episode = await pool.fetchrow("SELECT * FROM episodes WHERE id = $1", episode_id)
    
    if not story or not episode:
        return {"error": "Story or episode not found"}
    
    # Generate basic SEO
    title = episode.get("title", story.get("title", ""))
    description = f"{title} - AI-generated short video series"
    
    # Platform-specific
    if platform == "youtube":
        tags = ["shorts", "ai video", "anime", title.lower().replace(" ", "")]
        return {
            "title": title,
            "description": description[:5000],
            "tags": tags[:15],
            "category": "Entertainment",
            "privacy": "public",
        }
    elif platform == "tiktok":
        return {
            "title": title[:100],
            "description": description[:150],
            "hashtags": ["#anime", "#shorts", "#ai"],
        }
    
    return {"title": title, "description": description}


# ══════════════════════════════════════════════════════════════════════════════
# QUALITY & REVIEW TOOLS
# ══════════════════════════════════════════════════════════════════════════════

async def check_style_consistency(pool: Any, story_id: str) -> dict:
    """Check visual consistency across scenes."""
    # Get all scenes with images/clips
    scenes = await pool.fetch(
        """SELECT s.*, e.episode_number FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE e.story_id = $1
           AND (s.clip_url IS NOT NULL OR s.image_url IS NOT NULL)
           ORDER BY e.episode_number, s.scene_number""",
        story_id,
    )
    
    issues = []
    for i, scene in enumerate(scenes):
        scene_dict = dict(scene)
        
        # Check for missing references
        metadata = json.loads(scene.get("generation_metadata") or "{}")
        has_refs = bool(metadata.get("reference_image_urls")) or bool(metadata.get("continuity_reference"))
        
        if i > 0 and not has_refs:
            issues.append({
                "scene_id": str(scene["id"]),
                "scene_number": scene["scene_number"],
                "issue": "No visual reference for continuity",
                "severity": "medium",
            })
        
        # Check for locked status
        if scene.get("locked"):
            issues.append({
                "scene_id": str(scene["id"]),
                "scene_number": scene["scene_number"],
                "issue": "Scene is locked",
                "severity": "info",
            })
    
    return {
        "scenes_checked": len(scenes),
        "total_issues": len(issues),
        "issues": issues,
        "status": "passed" if len(issues) == 0 else "warnings",
    }


async def compare_scenes(
    pool: Any,
    story_id: str,
    scene_a_id: str,
    scene_b_id: str,
) -> dict:
    """Compare two scenes for A/B testing."""
    scene_a = await pool.fetchrow(
        """SELECT s.* FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_a_id, story_id,
    )
    scene_b = await pool.fetchrow(
        """SELECT s.* FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_b_id, story_id,
    )
    
    if not scene_a or not scene_b:
        return {"error": "One or both scenes not found"}
    
    return {
        "comparison": {
            "scene_a": {
                "id": str(scene_a["id"]),
                "scene_number": scene_a["scene_number"],
                "prompt": scene_a.get("prompt", ""),
                "clip_url": scene_a.get("clip_url"),
                "status": scene_a.get("status"),
                "approval_status": scene_a.get("approval_status"),
            },
            "scene_b": {
                "id": str(scene_b["id"]),
                "scene_number": scene_b["scene_number"],
                "prompt": scene_b.get("prompt", ""),
                "clip_url": scene_b.get("clip_url"),
                "status": scene_b.get("status"),
                "approval_status": scene_b.get("approval_status"),
            },
        },
        "differences": {
            "prompt_changed": scene_a.get("prompt") != scene_b.get("prompt"),
            "regen_count_diff": abs((scene_a.get("regeneration_count") or 0) - (scene_b.get("regeneration_count") or 0)),
        },
    }


async def search_assets(
    pool: Any,
    story_id: str,
    query: str,
    asset_type: Optional[str] = None,
) -> dict:
    """Search across story content."""
    # Search in scenes
    scene_query = """
        SELECT s.*, 'scene' as asset_type FROM scenes s
        JOIN episodes e ON s.episode_id = e.id
        WHERE e.story_id = $1
        AND (
            s.prompt ILIKE '%' || $2 || '%'
            OR s.title ILIKE '%' || $2 || '%'
        )
    """
    scenes = await pool.fetch(scene_query, story_id, query)
    
    # Search in characters
    char_query = """
        SELECT c.*, 'character' as asset_type FROM characters c
        WHERE c.story_id = $1
        AND (
            c.name ILIKE '%' || $2 || '%'
            OR c.description ILIKE '%' || $2 || '%'
        )
    """
    characters = await pool.fetch(char_query, story_id, query)
    
    # Filter by type if specified
    if asset_type == "scene":
        characters = []
    elif asset_type == "character":
        scenes = []
    
    return {
        "query": query,
        "results": {
            "scenes": [
                {"id": str(s["id"]), "title": s.get("title"), "prompt": s.get("prompt", "")[:200]}
                for s in scenes
            ],
            "characters": [
                {"id": str(c["id"]), "name": c.get("name"), "description": c.get("description", "")[:200]}
                for c in characters
            ],
        },
        "total_found": len(scenes) + len(characters),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def register_all_tools(executor: Any) -> None:
    """Register all tools with the executor."""
    
    # Story & Context
    executor.register_tool("get_story_context", get_story_context)
    executor.register_tool("get_scene_timeline", get_scene_timeline)
    executor.register_tool("list_stories", list_stories)
    executor.register_tool("create_story", create_story)
    
    # Scene Management
    executor.register_tool("create_scene", create_scene)
    executor.register_tool("update_scene", update_scene)
    executor.register_tool("delete_scene", delete_scene)
    executor.register_tool("approve_scene", approve_scene)
    executor.register_tool("lock_scene", lock_scene)
    
    # Video Generation
    executor.register_tool("generate_video", generate_video)
    executor.register_tool("wait_for_generation", wait_for_generation)
    
    # Frame Extraction
    executor.register_tool("extract_scene_frame", extract_scene_frame)
    executor.register_tool("screenshot_previous_scene", screenshot_previous_scene)
    
    # Character & Reference
    executor.register_tool("set_character_reference", set_character_reference)
    executor.register_tool("set_scene_continuity", set_scene_continuity)
    
    # Production
    executor.register_tool("assemble_episode", assemble_episode)
    executor.register_tool("add_transition", add_transition)
    executor.register_tool("generate_seo_metadata", generate_seo_metadata)
    
    # Quality & Review
    executor.register_tool("check_style_consistency", check_style_consistency)
    executor.register_tool("compare_scenes", compare_scenes)
    executor.register_tool("search_assets", search_assets)


# Import time for wait_for_generation
import time
import os
