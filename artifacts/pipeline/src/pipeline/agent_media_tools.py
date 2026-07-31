"""
Advanced Media Tools for Agent - Frame extraction, screenshot, Genblaze integration.

These tools enable truly agentic video production workflows.
"""

import os
import json
import asyncio
import subprocess
import tempfile
import uuid
from typing import Any, Optional
from urllib.parse import urlparse
import httpx
import ssl

# Use existing B2 storage (from storage/b2.py)
# Import the upload functions for consistent storage
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from storage.b2 import upload_file, public_url, BUCKET, build_key

# Genblaze API
GENBLAZE_API_URL = os.environ.get("GENBLAZE_API_URL", "https://api.genblaze.ai")
GENBLAZE_API_KEY = os.environ.get("GENBLAZE_API_KEY", "")


def _row_to_dict(row) -> dict:
    """Convert asyncpg Row to dict."""
    if hasattr(row, 'keys'):
        return dict(zip(row.keys(), row.values()))
    return dict(row)


async def download_file(url: str, output_path: str) -> bool:
    """Download a file from URL to local path."""
    try:
        # Handle R2/S3 URLs
        if "r2.dev" in url or ".cloudflarestorage.com" in url:
            # Try direct download first
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return True
        
        # Try with signed URL generation for R2
        if R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY:
            try:
                import boto3
                s3_client = boto3.client(
                    's3',
                    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                    aws_access_key_id=R2_ACCESS_KEY_ID,
                    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                )
                
                # Extract key from URL
                parsed = urlparse(url)
                key = parsed.path.lstrip('/')
                
                s3_client.download_file(R2_BUCKET, key, output_path)
                return True
            except Exception as e:
                print(f"S3 download error: {e}")
        
        # Fallback to direct HTTP download
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
        
        return False
    except Exception as e:
        print(f"Download error: {e}")
        return False


async def upload_to_b2(local_path: str, remote_key: str) -> Optional[str]:
    """Upload file to Backblaze B2 and return presigned URL."""
    try:
        # Use synchronous upload (blocking) in async context
        # This is acceptable for small/medium files
        url = upload_file(local_path, remote_key, "image/jpeg")
        return url
    except Exception as e:
        print(f"Upload error: {e}")
        return None


# Alias for backwards compatibility
upload_to_r2 = upload_to_b2


async def extract_frame_ffmpeg(
    video_url: str,
    timestamp: float,
    output_path: str,
) -> bool:
    """
    Extract a single frame from a video at given timestamp.
    Uses ffmpeg for extraction.
    """
    try:
        # Create temp dir if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Extract frame using ffmpeg
        # timestamp can be seconds (float) or HH:MM:SS format
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-ss", str(timestamp),
            "-i", video_url,
            "-vframes", "1",
            "-q:v", "2",  # Quality setting
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        
        # Try downloading if video URL is remote
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp_path = tmp.name
        
        downloaded = await download_file(video_url, tmp_path)
        if downloaded:
            cmd[cmd.index(video_url)] = tmp_path
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            os.unlink(tmp_path)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return True
        
        return False
        
    except Exception as e:
        print(f"Frame extraction error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# TOOL: extract_scene_frame
# ══════════════════════════════════════════════════════════════════════════════

async def extract_scene_frame_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
    timestamp: Optional[float] = None,
    frame_position: str = "middle",
) -> dict[str, Any]:
    """
    Extract a frame from a scene's generated video at a specific timestamp.
    
    This enables the agent to capture reference images from generated content
    for use in continuity and future scene generation.
    
    Args:
        story_id: The story ID
        scene_id: Scene to extract frame from
        timestamp: Specific timestamp in seconds (optional)
        frame_position: 'first', 'middle', 'last' if timestamp not provided
    """
    # Verify ownership and get scene
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    # Check if scene has media
    video_url = scene.get("clip_url") or scene.get("media_url") or scene.get("image_url")
    
    if not video_url:
        return {
            "success": False,
            "error": "Scene has no generated media yet",
            "scene_status": scene.get("status"),
            "hint": "Wait for scene generation to complete or provide an image_url manually",
        }
    
    # Determine timestamp if not provided
    if timestamp is None:
        duration = scene.get("duration") or 5.0  # Default 5 seconds
        if frame_position == "first":
            timestamp = 0.5
        elif frame_position == "middle":
            timestamp = duration / 2
        elif frame_position == "last":
            timestamp = max(0.5, duration - 0.5)
        else:
            timestamp = duration / 2
    
    # Create temp file for extracted frame
    frame_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"frame_{scene_id[:8]}_{frame_id}.jpg")
    
    # Extract frame
    success = await extract_frame_ffmpeg(video_url, timestamp, temp_path)
    
    if not success:
        return {
            "success": False,
            "error": "Failed to extract frame from video",
            "video_url": video_url,
            "timestamp": timestamp,
        }
    
    # Upload to R2
    remote_key = f"frames/{story_id}/{scene_id}/frame_{frame_id}.jpg"
    frame_url = await upload_to_r2(temp_path, remote_key)
    
    # Cleanup temp file
    try:
        os.unlink(temp_path)
    except:
        pass
    
    if not frame_url:
        return {
            "success": False,
            "error": "Failed to upload frame to storage",
            "local_path": temp_path,
        }
    
    return {
        "success": True,
        "frame_url": frame_url,
        "scene_id": scene_id,
        "timestamp": timestamp,
        "frame_position": frame_position,
        "video_url": video_url,
    }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL: screenshot_previous_scene  
# ══════════════════════════════════════════════════════════════════════════════

async def screenshot_previous_scene_impl(
    pool: Any,
    story_id: str,
    source_scene_id: str,
    target_scene_id: Optional[str] = None,
    frame_position: str = "last",
) -> dict[str, Any]:
    """
    Extract the last frame from a source scene and optionally link it to a target scene.
    
    This is the core "screenshot previous scene" functionality for maintaining
    visual continuity between scenes. The agent uses this to automatically capture
    reference images from completed scenes.
    
    Args:
        story_id: The story ID
        source_scene_id: Scene to extract frame from
        target_scene_id: Optional scene to link the frame to (for continuity)
        frame_position: 'first', 'middle', 'last' (default: 'last')
    """
    # Get source scene
    source = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        source_scene_id, story_id,
    )
    
    if not source:
        raise ValueError(f"Source scene not found: {source_scene_id}")
    
    # Get source media URL
    source_video_url = source.get("clip_url") or source.get("media_url") or source.get("image_url")
    
    if not source_video_url:
        return {
            "success": False,
            "error": "Source scene has no generated media",
            "source_scene_id": source_scene_id,
            "source_status": source.get("status"),
        }
    
    # Determine timestamp
    duration = source.get("duration") or 5.0
    if frame_position == "first":
        timestamp = 0.5
    elif frame_position == "middle":
        timestamp = duration / 2
    elif frame_position == "last":
        timestamp = max(0.5, duration - 0.5)
    else:
        timestamp = duration / 2
    
    # Extract frame
    frame_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"screenshot_{source_scene_id[:8]}_{frame_id}.jpg")
    
    success = await extract_frame_ffmpeg(source_video_url, timestamp, temp_path)
    
    if not success:
        return {
            "success": False,
            "error": "Failed to extract screenshot from video",
            "source_video_url": source_video_url,
        }
    
    # Upload to R2
    remote_key = f"screenshots/{story_id}/{source_scene_id}/exit_frame_{frame_id}.jpg"
    screenshot_url = await upload_to_r2(temp_path, remote_key)
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass
    
    if not screenshot_url:
        return {
            "success": False,
            "error": "Failed to upload screenshot to storage",
        }
    
    result = {
        "success": True,
        "screenshot_url": screenshot_url,
        "source_scene_id": source_scene_id,
        "source_scene_number": source.get("scene_number"),
        "frame_position": frame_position,
        "timestamp": timestamp,
    }
    
    # If target_scene_id provided, link the screenshot for continuity
    if target_scene_id:
        target = await pool.fetchrow(
            """SELECT s.*, e.story_id FROM scenes s
               JOIN episodes e ON s.episode_id = e.id
               WHERE s.id = $1 AND e.story_id = $2""",
            target_scene_id, story_id,
        )
        
        if target:
            # Update target's metadata with continuity reference
            existing_meta = json.loads(target.get("generation_metadata") or "{}")
            existing_meta["continuity_reference"] = {
                "source_scene_id": source_scene_id,
                "source_scene_number": source.get("scene_number"),
                "exit_frame_url": screenshot_url,
                "type": "exit_frame",
                "extracted_at": str(uuid.uuid4()),  # Unique ID for this extraction
            }
            
            # Add to reference images
            ref_urls = existing_meta.get("reference_image_urls", [])
            if screenshot_url not in ref_urls:
                ref_urls.insert(0, screenshot_url)
            existing_meta["reference_image_urls"] = ref_urls
            
            await pool.execute(
                """UPDATE scenes SET generation_metadata = $1::jsonb, updated_at = now()
                   WHERE id = $2""",
                json.dumps(existing_meta), target_scene_id,
            )
            
            result["continuity_linked"] = True
            result["target_scene_id"] = target_scene_id
            result["target_scene_number"] = target.get("scene_number")
        else:
            result["continuity_linked"] = False
            result["target_error"] = f"Target scene not found: {target_scene_id}"
    
    return result


# ══════════════════════════════════════════════════════════════════════════════
# TOOL: generate_script_and_scenes
# ══════════════════════════════════════════════════════════════════════════════

async def generate_script_and_scenes_impl(
    pool: Any,
    story_id: str,
    episode_id: str,
    prompt: str,
    num_scenes: int = 3,
) -> dict[str, Any]:
    """
    Generate a script outline and create multiple scenes from a text prompt.
    
    Uses the LLM to:
    1. Generate a coherent story beat/script
    2. Break it down into scene descriptions
    3. Create scenes in the database
    
    Args:
        story_id: The story ID
        episode_id: Episode to add scenes to
        prompt: Natural language description of what should happen
        num_scenes: Number of scenes to generate (default: 3)
    """
    from pipeline.agent_llm import ChatMessage, agent_chat
    from pipeline.agent_tools import get_story_context_impl
    
    # Get story context for the LLM
    context = await get_story_context_impl(pool, story_id)
    
    # Build prompt for scene generation
    system_prompt = f"""You are a creative screenwriter for video content. Generate a compelling story beat with {num_scenes} distinct scenes.

STORY CONTEXT:
- Title: {context.get('title', 'Untitled')}
- Existing Episodes: {len(context.get('episodes', []))}
- Characters: {[c.get('name') for c in context.get('characters', [])]}

Generate a JSON response with this structure:
{{
  "title": "Beat title",
  "description": "Brief description of this story beat",
  "scenes": [
    {{
      "title": "Scene title",
      "description": "What happens in this scene",
      "location": "Setting/location",
      "mood": "Emotional tone",
      "action": "Key action or movement",
      "duration_seconds": 5
    }}
  ]
}}

Make each scene visually distinct and ensure continuity between them. Focus on action and visual storytelling."""
    
    try:
        response = await agent_chat(
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Generate {num_scenes} scenes for: {prompt}"),
            ],
            tools=[],  # No tools for this call
            temperature=0.8,
            max_tokens=2000,
        )
        
        # Parse response
        content = response.content.strip()
        
        # Try to extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        script_data = json.loads(content)
        
        # Create scenes
        created_scenes = []
        for i, scene_data in enumerate(script_data.get("scenes", [])):
            from pipeline.agent_tools import create_scene_impl
            
            # Add to episode at the end
            result = await create_scene_impl(
                pool=pool,
                story_id=story_id,
                episode_id=episode_id,
                scene_data=scene_data,
                insert_after=None,
                auto_generate=True,  # Queue for generation
            )
            created_scenes.append(result)
        
        return {
            "success": True,
            "script_title": script_data.get("title"),
            "script_description": script_data.get("description"),
            "scenes_created": len(created_scenes),
            "scenes": created_scenes,
            "raw_script": content[:500] + "..." if len(content) > 500 else content,
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse LLM response as JSON: {e}",
            "llm_response": response.content[:500] if response.content else "Empty response",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL: set_character_reference
# ══════════════════════════════════════════════════════════════════════════════

async def set_character_reference_impl(
    pool: Any,
    story_id: str,
    character_id: str,
    reference_image_url: str,
    is_primary: bool = True,
) -> dict[str, Any]:
    """
    Set a reference image for a character to maintain visual consistency.
    
    This enables the agent to capture and store character reference images
    that can be used in prompt augmentation for consistent character appearance.
    
    Args:
        story_id: The story ID
        character_id: Character to set reference for
        reference_image_url: URL of the reference image (can be from extracted frame)
        is_primary: Whether this is the primary reference
    """
    # Verify ownership and get character
    character = await pool.fetchrow(
        """SELECT c.* FROM characters c
           JOIN stories s ON c.story_id = s.id
           WHERE c.id = $1 AND s.id = $2""",
        character_id, story_id,
    )
    
    if not character:
        raise ValueError(f"Character not found: {character_id}")
    
    # Get existing ref images - handle both string (JSON) and list formats
    ref_image_urls = character.get("ref_image_urls")
    if isinstance(ref_image_urls, str):
        try:
            existing_urls = json.loads(ref_image_urls)
        except:
            existing_urls = []
    elif isinstance(ref_image_urls, list):
        existing_urls = list(ref_image_urls)
    else:
        existing_urls = []
    
    # Add new reference if not already present
    if reference_image_url not in existing_urls:
        if is_primary:
            # Insert at beginning for primary
            existing_urls.insert(0, reference_image_url)
        else:
            existing_urls.append(reference_image_url)
    
    # Update character - store as JSON string
    await pool.execute(
        """UPDATE characters 
           SET ref_image_urls = $1::jsonb, updated_at = now()
           WHERE id = $2""",
        json.dumps(existing_urls), character_id,
    )
    
    return {
        "success": True,
        "character_id": character_id,
        "character_name": character.get("name"),
        "reference_image_url": reference_image_url,
        "is_primary": is_primary,
        "total_references": len(existing_urls),
        "all_references": existing_urls,
    }


async def extract_character_from_scene_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
    character_id: str,
    timestamp: Optional[float] = None,
) -> dict[str, Any]:
    """
    Extract a character reference image from a scene's video.
    
    This combines screenshot extraction with character reference setting
    for a seamless workflow.
    """
    # First extract the frame
    frame_result = await extract_scene_frame_impl(
        pool=pool,
        story_id=story_id,
        scene_id=scene_id,
        timestamp=timestamp,
        frame_position="middle",
    )
    
    if not frame_result.get("success"):
        return frame_result
    
    # Then set as character reference
    ref_result = await set_character_reference_impl(
        pool=pool,
        story_id=story_id,
        character_id=character_id,
        reference_image_url=frame_result["frame_url"],
        is_primary=True,
    )
    
    return {
        "success": True,
        "frame_url": frame_result["frame_url"],
        "character_id": character_id,
        "character_name": ref_result.get("character_name"),
        "scene_id": scene_id,
        "timestamp": frame_result.get("timestamp"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL: generate_video_genblaze
# ══════════════════════════════════════════════════════════════════════════════

async def generate_video_genblaze_impl(
    pool: Any,
    story_id: str,
    scene_id: str,
    prompt: Optional[str] = None,
    reference_image_url: Optional[str] = None,
    character_ref_urls: Optional[list[str]] = None,
    style: str = "anime",
    duration: int = 5,
) -> dict[str, Any]:
    """
    Generate a video using Genblaze API.
    
    This tool integrates with Genblaze for actual video generation.
    It supports:
    - Text-to-video generation
    - Image-to-video (using reference images)
    - Character consistency via reference URLs
    
    Args:
        story_id: The story ID
        scene_id: Scene to generate video for
        prompt: Video generation prompt
        reference_image_url: Initial image for img2video
        character_ref_urls: Character reference images for consistency
        style: Video style (anime, realistic, etc.)
        duration: Video duration in seconds
    """
    # Get scene data
    scene = await pool.fetchrow(
        """SELECT s.*, e.story_id FROM scenes s
           JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id = $2""",
        scene_id, story_id,
    )
    
    if not scene:
        raise ValueError(f"Scene not found: {scene_id}")
    
    # Build generation prompt
    generation_prompt = prompt or scene.get("prompt") or scene.get("generation_metadata", {}).get("visual_prompt", "")
    
    if not generation_prompt:
        return {
            "success": False,
            "error": "No prompt available for generation",
            "hint": "Provide a prompt or ensure scene has a visual_prompt in metadata",
        }
    
    # Get metadata for additional context
    metadata = json.loads(scene.get("generation_metadata") or "{}")
    
    # Build Genblaze API request
    genblaze_payload = {
        "prompt": generation_prompt,
        "duration": duration,
        "style": style,
        "aspect_ratio": metadata.get("frame_ratio", "16:9"),
    }
    
    # Add reference images
    all_refs = []
    if reference_image_url:
        all_refs.append(reference_image_url)
    if character_ref_urls:
        all_refs.extend(character_ref_urls)
    
    # Also check for reference_image_urls in scene metadata
    scene_refs = metadata.get("reference_image_urls", [])
    all_refs.extend(scene_refs)
    
    if all_refs:
        genblaze_payload["image_urls"] = all_refs[:5]  # Limit to 5 images
    
    # Add continuation context if available
    continuity = metadata.get("continuity_reference")
    if continuity:
        genblaze_payload["continuation"] = {
            "source_scene_id": continuity.get("source_scene_id"),
            "exit_frame_url": continuity.get("exit_frame_url"),
        }
    
    # Call Genblaze API
    if not GENBLAZE_API_KEY:
        return {
            "success": False,
            "error": "Genblaze API key not configured",
            "hint": "Set GENBLAZE_API_KEY in environment",
        }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GENBLAZE_API_URL}/v1/generate/video",
                headers={
                    "Authorization": f"Bearer {GENBLAZE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=genblaze_payload,
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Genblaze API error: {response.status_code}",
                    "details": response.text[:500],
                }
            
            result = response.json()
            
            # Create a generation job to track progress
            job = await pool.fetchrow(
                """INSERT INTO generation_jobs
                   (entity_type, entity_id, status, total_steps, current_step, job_type, result)
                   VALUES ('scene', $1, 'pending', 1, 'Queued for Genblaze', 'genblaze_video', $2::jsonb)
                   RETURNING *""",
                scene_id,
                json.dumps({
                    "genblaze_task_id": result.get("task_id"),
                    "prompt": generation_prompt,
                    "reference_images": len(all_refs),
                }),
            )
            
            # Update scene status
            await pool.execute(
                """UPDATE scenes SET status = 'running', updated_at = now()
                   WHERE id = $1""",
                scene_id,
            )
            
            # Enqueue job
            try:
                from job_queue import enqueue_job, WORKLOAD_MEDIA
                await enqueue_job(str(job["id"]), workload=WORKLOAD_MEDIA)
            except:
                pass  # Queue might not be available
            
            return {
                "success": True,
                "job_id": str(job["id"]),
                "genblaze_task_id": result.get("task_id"),
                "status": "pending",
                "poll_url": f"/pipeline/jobs/{job['id']}",
                "api_response": result,
            }
            
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Genblaze API timeout",
            "hint": "Try again or use a shorter prompt",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL: poll_genblaze_status
# ══════════════════════════════════════════════════════════════════════════════

async def poll_genblaze_status_impl(
    job_id: str,
    pool: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Poll Genblaze API for video generation status.
    
    Args:
        job_id: The generation_jobs ID
        pool: Database pool (optional)
    """
    if not GENBLAZE_API_KEY:
        return {
            "success": False,
            "error": "Genblaze API key not configured",
        }
    
    # Get job from database
    job = None
    if pool:
        job = await pool.fetchrow(
            "SELECT * FROM generation_jobs WHERE id = $1",
            job_id,
        )
        
        if job:
            result_data = json.loads(job.get("result") or "{}")
            genblaze_task_id = result_data.get("genblaze_task_id")
            
            if genblaze_task_id:
                # Poll Genblaze
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(
                            f"{GENBLAZE_API_URL}/v1/tasks/{genblaze_task_id}",
                            headers={"Authorization": f"Bearer {GENBLAZE_API_KEY}"},
                        )
                        
                        if response.status_code == 200:
                            task_result = response.json()
                            
                            status = task_result.get("status", "unknown")
                            video_url = task_result.get("video_url")
                            
                            # Update job in database
                            if pool:
                                update_data = {
                                    "status": status,
                                    "current_step": f"Genblaze: {status}",
                                }
                                
                                if status == "completed" and video_url:
                                    update_data["result"] = json.dumps({
                                        "video_url": video_url,
                                        "genblaze_task_id": genblaze_task_id,
                                    })
                                    
                                    # Update scene with video URL
                                    await pool.execute(
                                        """UPDATE scenes 
                                           SET clip_url = $1, status = 'completed', updated_at = now()
                                           WHERE id = $2""",
                                        video_url, job["entity_id"],
                                    )
                                    
                                elif status == "failed":
                                    update_data["error"] = task_result.get("error", "Generation failed")
                                    update_data["completed_at"] = "now()"
                                    
                                    await pool.execute(
                                        """UPDATE scenes SET status = 'failed', updated_at = now()
                                           WHERE id = $1""",
                                        job["entity_id"],
                                    )
                                
                                await pool.execute(
                                    """UPDATE generation_jobs 
                                       SET status = $1, current_step = $2, result = COALESCE(result, '{}'::jsonb) || $3::jsonb,
                                           completed_at = CASE WHEN $1 IN ('completed', 'failed') THEN now() ELSE completed_at END
                                       WHERE id = $4""",
                                    status,
                                    update_data.get("current_step"),
                                    json.dumps({"genblaze_response": task_result}),
                                    job_id,
                                )
                            
                            return {
                                "success": True,
                                "job_id": job_id,
                                "status": status,
                                "video_url": video_url,
                                "task_result": task_result,
                            }
                        
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                    }
    
    return {
        "success": False,
        "error": "Job not found or pool not provided",
    }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def register_media_tools(register_tool_fn):
    """Register all media tools with the agent system."""
    
    # 1. Frame Extraction
    register_tool_fn(
        name="extract_scene_frame",
        description="Extract a frame from a scene's video at a specific timestamp. Returns a downloadable image URL that can be used as reference for continuity.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "timestamp": {"type": "number", "description": "Timestamp in seconds (optional)"},
                "frame_position": {"type": "string", "enum": ["first", "middle", "last"], "description": "Position if timestamp not provided"},
            },
            "required": ["story_id", "scene_id"],
        },
        category="media",
    )(extract_scene_frame_impl)
    
    # 2. Screenshot Previous Scene
    register_tool_fn(
        name="screenshot_previous_scene",
        description="Extract the last frame from a source scene and optionally link it to a target scene for visual continuity. This is the key tool for maintaining consistent visual flow between scenes.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "source_scene_id": {"type": "string", "description": "Scene to extract screenshot from"},
                "target_scene_id": {"type": "string", "description": "Optional scene to link the screenshot to"},
                "frame_position": {"type": "string", "enum": ["first", "middle", "last"], "description": "Which frame to extract"},
            },
            "required": ["story_id", "source_scene_id"],
        },
        category="media",
    )(screenshot_previous_scene_impl)
    
    # 3. Generate Script and Scenes
    register_tool_fn(
        name="generate_script_and_scenes",
        description="Generate a story beat with multiple scene descriptions from a text prompt, and create all scenes in the database. Use this when users want to create multiple related scenes at once.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "episode_id": {"type": "string"},
                "prompt": {"type": "string", "description": "Natural language description of the story beat"},
                "num_scenes": {"type": "integer", "description": "Number of scenes to generate (default: 3)"},
            },
            "required": ["story_id", "episode_id", "prompt"],
        },
        category="generation",
    )(generate_script_and_scenes_impl)
    
    # 4. Set Character Reference
    register_tool_fn(
        name="set_character_reference",
        description="Set a reference image for a character to maintain visual consistency across scenes. Reference images help ensure the same character looks consistent in all generations.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "character_id": {"type": "string"},
                "reference_image_url": {"type": "string", "description": "URL of the reference image"},
                "is_primary": {"type": "boolean", "description": "Whether this is the primary reference (default: true)"},
            },
            "required": ["story_id", "character_id", "reference_image_url"],
        },
        category="media",
    )(set_character_reference_impl)
    
    # 5. Extract Character from Scene
    register_tool_fn(
        name="extract_character_from_scene",
        description="Extract a frame from a scene and set it as a character's reference image in one step. This combines screenshot and character reference setting.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "character_id": {"type": "string"},
                "timestamp": {"type": "number", "description": "Optional timestamp"},
            },
            "required": ["story_id", "scene_id", "character_id"],
        },
        category="media",
    )(extract_character_from_scene_impl)
    
    # 6. Generate Video (Genblaze)
    register_tool_fn(
        name="generate_video",
        description="Generate a video using the Genblaze AI video generation API. Supports text-to-video and image-to-video with character references for consistency.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {"type": "string"},
                "scene_id": {"type": "string"},
                "prompt": {"type": "string", "description": "Video generation prompt (uses scene prompt if not provided)"},
                "reference_image_url": {"type": "string", "description": "Initial image for img2video"},
                "character_ref_urls": {"type": "array", "items": {"type": "string"}},
                "style": {"type": "string", "description": "Video style (anime, realistic, etc.)"},
                "duration": {"type": "integer", "description": "Duration in seconds (default: 5)"},
            },
            "required": ["story_id", "scene_id"],
        },
        category="generation",
    )(generate_video_genblaze_impl)
    
    # 7. Poll Genblaze Status
    register_tool_fn(
        name="poll_video_generation",
        description="Poll the Genblaze API for video generation status and update the job/scene in the database.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
        category="generation",
    )(poll_genblaze_status_impl)
