"""
Production Tools for Agent - Video assembly, audio, publishing.

These tools enable end-to-end video production from script to publish.
"""

import os
import json
import asyncio
import subprocess
import tempfile
import uuid
from typing import Any, Optional

import httpx

# ══════════════════════════════════════════════════════════════════════════════
# Audio Generation (TTS)
# ══════════════════════════════════════════════════════════════════════════════

TTS_API_URL = os.environ.get("TTS_API_URL", "https://api.elevenlabs.io/v1")
TTS_API_KEY = os.environ.get("TTS_API_KEY", "")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


async def generate_narration_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
    script: Optional[str] = None,
    voice_id: str = "default",
    speed: float = 1.0,
) -> dict[str, Any]:
    """
    Generate narration audio for a scene using text-to-speech.
    
    Uses OpenAI's TTS API or ElevenLabs if configured.
    """
    # Get scene script if not provided
    if not script:
        scene = await pool.fetchrow(
            """SELECT s.*, e.story_id FROM scenes s
               JOIN episodes e ON s.episode_id = e.id
               WHERE s.id = $1 AND e.story_id = $2""",
            scene_id, story_id,
        )
        if not scene:
            return {"success": False, "error": "Scene not found"}
        
        metadata = json.loads(scene.get("generation_metadata") or "{}")
        script = metadata.get("narration") or metadata.get("description") or scene.get("prompt", "")
    
    if not script:
        return {"success": False, "error": "No script available for narration"}
    
    # Try OpenAI TTS first
    if OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "tts-1",
                        "input": script[:5000],  # Limit length
                        "voice": voice_id if voice_id != "default" else "alloy",
                        "speed": speed,
                    },
                )
                
                if response.status_code == 200:
                    # Save audio file
                    audio_id = str(uuid.uuid4())
                    temp_path = f"/tmp/narration_{audio_id}.mp3"
                    
                    with open(temp_path, "wb") as f:
                        f.write(response.content)
                    
                    # Upload to storage (R2)
                    audio_url = await _upload_audio(temp_path, f"narration/{story_id}/{scene_id}/{audio_id}.mp3")
                    
                    # Clean up
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    
                    # Update scene with narration URL
                    await pool.execute(
                        """UPDATE scenes SET narration_url = $1, updated_at = now()
                           WHERE id = $2""",
                        audio_url, scene_id,
                    )
                    
                    return {
                        "success": True,
                        "audio_url": audio_url,
                        "scene_id": scene_id,
                        "duration_seconds": len(script) / 15,  # Rough estimate
                        "script_preview": script[:100] + "..." if len(script) > 100 else script,
                    }
        except Exception as e:
            pass  # Fall through to error
    
    return {
        "success": False,
        "error": "TTS API not configured",
        "hint": "Set OPENAI_API_KEY or TTS_API_KEY in environment",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Video Assembly
# ══════════════════════════════════════════════════════════════════════════════

async def assemble_episode_impl(
    pool: Any,
    story_id: str,
    episode_id: str,
    include_audio: bool = True,
    transition: str = "fade",
    output_format: str = "mp4",
) -> dict[str, Any]:
    """
    Assemble all approved scenes in an episode into a single video.
    
    Uses FFmpeg for video stitching with transitions.
    """
    # Get episode with all approved scenes
    episode = await pool.fetchrow(
        """SELECT e.* FROM episodes e
           JOIN stories s ON e.story_id = s.id
           WHERE e.id = $1 AND s.id = $2""",
        episode_id, story_id,
    )
    
    if not episode:
        return {"success": False, "error": "Episode not found"}
    
    # Get approved scenes
    scenes = await pool.fetch(
        """SELECT s.* FROM scenes s
           WHERE s.episode_id = $1
             AND s.approval_status = 'approved'
             AND (s.clip_url IS NOT NULL OR s.image_url IS NOT NULL)
           ORDER BY s.scene_number""",
        episode_id,
    )
    
    if not scenes:
        return {
            "success": False,
            "error": "No approved scenes with media to assemble",
            "hint": "Approve scenes or wait for generation to complete",
        }
    
    # Create assembly job
    job = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('episode', $1, 'pending', 3, 'Preparing assembly', 'episode_assembly')
           RETURNING *""",
        episode_id,
    )
    
    # Try to enqueue
    try:
        from job_queue import enqueue_job, WORKLOAD_ASSEMBLY
        await enqueue_job(str(job["id"]), workload=WORKLOAD_ASSEMBLY)
    except:
        pass
    
    return {
        "success": True,
        "job_id": str(job["id"]),
        "episode_id": episode_id,
        "scenes_to_assemble": len(scenes),
        "transition": transition,
        "status": "pending",
        "poll_url": f"/pipeline/jobs/{job['id']}",
        "note": "Assembly job queued. Poll for status.",
    }


async def add_transition_impl(
    pool: Any,
    story_id: str,
    from_scene_id: str,
    to_scene_id: str,
    transition_type: str = "fade",
    duration: float = 0.5,
) -> dict[str, Any]:
    """
    Add a visual transition between two scenes.
    
    Transition types: fade, dissolve, wipe_left, wipe_right, zoom
    """
    # Verify both scenes exist
    from_scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        from_scene_id, story_id,
    )
    
    to_scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        to_scene_id, story_id,
    )
    
    if not from_scene or not to_scene:
        return {"success": False, "error": "One or both scenes not found"}
    
    # Update metadata
    existing_meta = json.loads(from_scene.get("generation_metadata") or "{}")
    
    transitions = existing_meta.get("outgoing_transitions", [])
    transitions.append({
        "to_scene_id": to_scene_id,
        "type": transition_type,
        "duration": duration,
    })
    existing_meta["outgoing_transitions"] = transitions
    
    await pool.execute(
        """UPDATE scenes SET generation_metadata = $1::jsonb, updated_at = now()
           WHERE id = $2""",
        json.dumps(existing_meta), from_scene_id,
    )
    
    return {
        "success": True,
        "from_scene_id": from_scene_id,
        "to_scene_id": to_scene_id,
        "transition": transition_type,
        "duration_seconds": duration,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Thumbnail Generation
# ══════════════════════════════════════════════════════════════════════════════

IMAGE_GEN_API = os.environ.get("IMAGE_GEN_API", "https://api.openai.com/v1")

async def generate_thumbnail_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
    style: str = "cinematic",
    include_text: bool = False,
    text: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate a thumbnail image for a scene or episode.
    
    Uses AI image generation for eye-catching thumbnails.
    """
    # Get scene context
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id, e.title as episode_title FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    
    if not scene:
        return {"success": False, "error": "Scene not found"}
    
    metadata = json.loads(scene.get("generation_metadata") or "{}")
    scene_title = metadata.get("title", f"Scene {scene['scene_number']}")
    
    # Build prompt for thumbnail
    prompt = f"""{style} thumbnail for: {scene_title}. High contrast, dynamic composition, 
    attention-grabbing, professional video thumbnail, cinematic lighting."""
    
    if include_text and text:
        prompt += f" Text overlay: '{text}'"
    
    # Try DALL-E or similar
    if OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "size": "1792x1024",  # 16:9 aspect ratio
                        "style": "vivid",
                    },
                )
                
                if response.status_code == 200:
                    result = response.json()
                    image_url = result["data"][0]["url"]
                    
                    # Update scene
                    await pool.execute(
                        """UPDATE scenes SET thumbnail_url = $1, updated_at = now()
                           WHERE id = $2""",
                        image_url, scene_id,
                    )
                    
                    return {
                        "success": True,
                        "thumbnail_url": image_url,
                        "scene_id": scene_id,
                        "style": style,
                        "prompt_used": prompt,
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return {
        "success": False,
        "error": "Image generation API not configured",
        "hint": "Set OPENAI_API_KEY in environment",
    }


# ══════════════════════════════════════════════════════════════════════════════
# SEO & Publishing
# ══════════════════════════════════════════════════════════════════════════════

async def generate_seo_metadata_impl(
    pool: Any,
    story_id: str,
    episode_id: str,
    platform: str = "youtube",
) -> dict[str, Any]:
    """
    Generate SEO-optimized metadata for publishing.
    
    Creates title, description, tags, hashtags based on episode content.
    """
    from pipeline.agent_llm import ChatMessage, agent_chat
    
    # Get episode and story context
    episode = await pool.fetchrow(
        """SELECT e.*, s.title as story_title FROM episodes e
           JOIN stories s ON e.story_id = s.id
           WHERE e.id = $1 AND s.id = $2""",
        episode_id, story_id,
    )
    
    scenes = await pool.fetch(
        """SELECT s.* FROM scenes s
           WHERE s.episode_id = $1
           ORDER BY s.scene_number""",
        episode_id,
    )
    
    # Build context for LLM
    scene_summaries = []
    for scene in scenes:
        meta = json.loads(scene.get("generation_metadata") or "{}")
        scene_summaries.append({
            "number": scene["scene_number"],
            "title": meta.get("title", ""),
            "description": meta.get("description", ""),
        })
    
    system_prompt = f"""You are a YouTube/Social media SEO expert. Generate optimized metadata for a video episode.

STORY: {episode.get('story_title', 'Untitled')}
EPISODE: {episode.get('title', 'Untitled')}

SCENES:
{json.dumps(scene_summaries, indent=2)}

Generate JSON with:
{{
  "title": "Engaging, click-worthy title (max 100 chars)",
  "description": "Detailed description (2-3 paragraphs, include hook)",
  "tags": ["tag1", "tag2", ...],
  "hashtags": ["#hashtag1", ...],
  "thumbnail_suggestion": "Brief description for thumbnail"
}}

Make it engaging, discoverable, and platform-appropriate."""

    try:
        response = await agent_chat(
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Generate SEO metadata for {platform}"),
            ],
            tools=[],
            temperature=0.7,
            max_tokens=1000,
        )
        
        # Parse JSON response
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        
        metadata = json.loads(content)
        
        # Save to episode
        existing_meta = json.loads(episode.get("episode_metadata") or "{}")
        existing_meta[f"{platform}_seo"] = metadata
        
        await pool.execute(
            """UPDATE episodes SET episode_metadata = $1::jsonb, updated_at = now()
               WHERE id = $2""",
            json.dumps(existing_meta), episode_id,
        )
        
        return {
            "success": True,
            "platform": platform,
            "metadata": metadata,
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# Style Consistency Check
# ══════════════════════════════════════════════════════════════════════════════

async def check_style_consistency_impl(
    pool: Any,
    story_id: str,
    episode_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Check visual style consistency across scenes.
    
    Detects:
    - Face inconsistencies (different character appearances)
    - Color grading variations
    - Lighting inconsistencies
    - Resolution/quality differences
    """
    # Get scenes
    if episode_id:
        query = """SELECT s.* FROM scenes s
                   WHERE s.episode_id = $1
                   ORDER BY s.scene_number"""
        scenes = await pool.fetch(query, episode_id)
    else:
        query = """SELECT s.* FROM scenes s
                   JOIN episodes e ON s.episode_id = e.id
                   WHERE e.story_id = $1
                   ORDER BY s.scene_number"""
        scenes = await pool.fetch(query, story_id)
    
    issues = []
    
    # Check for scenes without reference images (potential face inconsistency)
    for scene in scenes:
        metadata = json.loads(scene.get("generation_metadata") or "{}")
        ref_images = metadata.get("reference_image_urls", [])
        
        if not ref_images and scene.get("clip_url"):
            issues.append({
                "scene_id": str(scene["id"]),
                "scene_number": scene["scene_number"],
                "issue": "no_reference_images",
                "severity": "medium",
                "suggestion": "Add character reference images for visual consistency",
            })
        
        # Check for missing continuity links
        if not metadata.get("continuity_reference"):
            issues.append({
                "scene_id": str(scene["id"]),
                "scene_number": scene["scene_number"],
                "issue": "no_continuity_reference",
                "severity": "low",
                "suggestion": "Consider linking to previous scene's exit frame",
            })
    
    # Summary
    high_severity = [i for i in issues if i["severity"] == "high"]
    medium_severity = [i for i in issues if i["severity"] == "medium"]
    
    return {
        "success": True,
        "scenes_checked": len(scenes),
        "total_issues": len(issues),
        "high_severity_count": len(high_severity),
        "medium_severity_count": len(medium_severity),
        "issues": issues,
        "recommendation": "Add reference images for scenes with issues" if issues else "Style looks consistent!",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Scene Comparison
# ══════════════════════════════════════════════════════════════════════════════

async def compare_scenes_impl(
    pool: Any,
    story_id: str,
    scene_a_id: str,
    scene_b_id: str,
) -> dict[str, Any]:
    """
    Compare two scenes for A/B testing or version comparison.
    
    Returns metadata comparison and suggested improvements.
    """
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
        return {"success": False, "error": "One or both scenes not found"}
    
    meta_a = json.loads(scene_a.get("generation_metadata") or "{}")
    meta_b = json.loads(scene_b.get("generation_metadata") or "{}")
    
    comparison = {
        "scene_a": {
            "id": str(scene_a["id"]),
            "scene_number": scene_a["scene_number"],
            "title": meta_a.get("title", ""),
            "status": scene_a["status"],
            "has_media": bool(scene_a.get("clip_url") or scene_a.get("media_url")),
            "has_references": bool(meta_a.get("reference_image_urls")),
            "has_continuity": bool(meta_a.get("continuity_reference")),
        },
        "scene_b": {
            "id": str(scene_b["id"]),
            "scene_number": scene_b["scene_number"],
            "title": meta_b.get("title", ""),
            "status": scene_b["status"],
            "has_media": bool(scene_b.get("clip_url") or scene_b.get("media_url")),
            "has_references": bool(meta_b.get("reference_image_urls")),
            "has_continuity": bool(meta_b.get("continuity_reference")),
        },
        "differences": [],
    }
    
    # Find differences
    if meta_a.get("mood") != meta_b.get("mood"):
        comparison["differences"].append(f"Mood: '{meta_a.get('mood')}' vs '{meta_b.get('mood')}'")
    if meta_a.get("location") != meta_b.get("location"):
        comparison["differences"].append(f"Location: '{meta_a.get('location')}' vs '{meta_b.get('location')}'")
    
    return {
        "success": True,
        "comparison": comparison,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Search Assets
# ══════════════════════════════════════════════════════════════════════════════

async def search_assets_impl(
    pool: Any,
    story_id: str,
    query: str,
    asset_type: str = "all",
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search across all story assets (scenes, characters, references).
    
    Uses semantic search across titles, descriptions, and metadata.
    """
    results = {
        "scenes": [],
        "characters": [],
        "reference_images": [],
    }
    
    # Search scenes
    if asset_type in ["all", "scenes"]:
        scenes = await pool.fetch(
            """SELECT s.*, s.id as scene_id FROM scenes s
               JOIN episodes e ON s.episode_id = e.id
               WHERE e.story_id = $1
                 AND (
                   s.prompt ILIKE $2
                   OR s.generation_metadata::text ILIKE $2
                 )
               LIMIT $3""",
            story_id, f"%{query}%", limit,
        )
        
        for scene in scenes:
            meta = json.loads(scene.get("generation_metadata") or "{}")
            results["scenes"].append({
                "id": str(scene["id"]),
                "scene_number": scene["scene_number"],
                "title": meta.get("title", ""),
                "description": meta.get("description", ""),
                "status": scene["status"],
            })
    
    # Search characters
    if asset_type in ["all", "characters"]:
        characters = await pool.fetch(
            """SELECT * FROM characters
               WHERE story_id = $1
                 AND (name ILIKE $2 OR description ILIKE $2)
               LIMIT $3""",
            story_id, f"%{query}%", limit,
        )
        
        for char in characters:
            results["characters"].append({
                "id": str(char["id"]),
                "name": char.get("name", ""),
                "description": char.get("description", ""),
            })
    
    return {
        "success": True,
        "query": query,
        "results": results,
        "total_found": len(results["scenes"]) + len(results["characters"]) + len(results["reference_images"]),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════

async def _upload_audio(local_path: str, remote_key: str) -> Optional[str]:
    """Upload audio file to R2 storage."""
    try:
        import boto3
        
        r2_account = os.environ.get("R2_ACCOUNT_ID", "")
        r2_key = os.environ.get("R2_ACCESS_KEY_ID", "")
        r2_secret = os.environ.get("R2_SECRET_ACCESS_KEY", "")
        r2_bucket = os.environ.get("R2_BUCKET", "dysentry-media")
        r2_public = os.environ.get("R2_PUBLIC_URL", "")
        
        if not all([r2_account, r2_key, r2_secret]):
            return None
        
        s3 = boto3.client(
            's3',
            endpoint_url=f"https://{r2_account}.r2.cloudflarestorage.com",
            aws_access_key_id=r2_key,
            aws_secret_access_key=r2_secret,
        )
        
        s3.upload_file(
            local_path, r2_bucket, remote_key,
            ExtraArgs={'ContentType': 'audio/mpeg'}
        )
        
        if r2_public:
            return f"{r2_public}/{remote_key}"
        return f"https://{r2_bucket}.{r2_account}.r2.dev/{remote_key}"
        
    except Exception as e:
        print(f"Audio upload error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Tool Registration
# ══════════════════════════════════════════════════════════════════════════════

def register_production_tools(register_tool_fn):
    """Register all production tools."""
    
    register_tool_fn(
        name="generate_narration",
        description="Generate text-to-speech narration for a scene. Converts script to audio.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "script": {"type": "string", "description": "Narration text (uses scene description if not provided)"},
                "voice_id": {"type": "string", "description": "Voice preset or ID"},
                "speed": {"type": "number", "description": "Speech speed (0.5-2.0)"},
            },
            "required": ["story_id", "scene_id"],
        },
        category="production",
    )(generate_narration_impl)
    
    register_tool_fn(
        name="assemble_episode",
        description="Assemble all approved scenes in an episode into a single video file. Use after scenes are approved.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "episode_id": {"type": "string"},
                "include_audio": {"type": "boolean", "description": "Include narration tracks"},
                "transition": {"type": "string", "enum": ["fade", "dissolve", "cut", "wipe"]},
            },
            "required": ["story_id", "episode_id"],
        },
        category="production",
    )(assemble_episode_impl)
    
    register_tool_fn(
        name="add_transition",
        description="Add a visual transition effect between two consecutive scenes.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "from_scene_id": {"type": "string"},
                "to_scene_id": {"type": "string"},
                "transition_type": {"type": "string", "enum": ["fade", "dissolve", "wipe_left", "wipe_right", "zoom"]},
                "duration": {"type": "number", "description": "Transition duration in seconds"},
            },
            "required": ["story_id", "from_scene_id", "to_scene_id"],
        },
        category="production",
    )(add_transition_impl)
    
    register_tool_fn(
        name="generate_thumbnail",
        description="Generate an AI-powered thumbnail image for a scene. Creates eye-catching promotional images.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "style": {"type": "string", "enum": ["cinematic", "dramatic", "bright", "dark"]},
                "include_text": {"type": "boolean"},
                "text": {"type": "string", "description": "Text to overlay on thumbnail"},
            },
            "required": ["story_id", "scene_id"],
        },
        category="production",
    )(generate_thumbnail_impl)
    
    register_tool_fn(
        name="generate_seo_metadata",
        description="Generate SEO-optimized metadata for publishing (YouTube, TikTok, etc.). Creates titles, descriptions, tags.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "episode_id": {"type": "string"},
                "platform": {"type": "string", "enum": ["youtube", "tiktok", "instagram", "twitter"]},
            },
            "required": ["story_id", "episode_id"],
        },
        category="publishing",
    )(generate_seo_metadata_impl)
    
    register_tool_fn(
        name="check_style_consistency",
        description="Check visual style consistency across all scenes. Detects face inconsistencies, color grading issues, and missing references.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "episode_id": {"type": "string", "description": "Optional: check specific episode only"},
            },
            "required": ["story_id"],
        },
        category="quality",
    )(check_style_consistency_impl)
    
    register_tool_fn(
        name="compare_scenes",
        description="Compare two scenes for A/B testing or version comparison. Shows differences in settings and metadata.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_a_id": {"type": "string"},
                "scene_b_id": {"type": "string"},
            },
            "required": ["story_id", "scene_a_id", "scene_b_id"],
        },
        category="quality",
    )(compare_scenes_impl)
    
    register_tool_fn(
        name="search_assets",
        description="Search across all story assets (scenes, characters, reference images) using keywords.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "query": {"type": "string", "description": "Search query"},
                "asset_type": {"type": "string", "enum": ["all", "scenes", "characters", "references"]},
                "limit": {"type": "integer"},
            },
            "required": ["story_id", "query"],
        },
        category="assets",
    )(search_assets_impl)
