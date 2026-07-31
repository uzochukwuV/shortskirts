"""
Episode Assembly Worker Handler

Assembles approved scenes into a complete episode video.
Uses FFmpeg for video processing and B2 for storage.
"""

import os
import json
import asyncio
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

import asyncpg

# Storage
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from storage.b2 import upload_file, download_and_upload, get_presigned_url


class AssemblyError(Exception):
    """Custom exception for assembly errors."""
    pass


async def download_scene_clip(pool, scene_id: str, output_path: str) -> bool:
    """Download a scene's clip to local file."""
    scene = await pool.fetchrow(
        "SELECT clip_url, media_url FROM scenes WHERE id = $1",
        scene_id
    )
    
    clip_url = scene.get("clip_url") or scene.get("media_url")
    if not clip_url:
        return False
    
    # Download via B2's download_and_upload or direct download
    try:
        async with asyncio.timeout(300):  # 5 min timeout
            # If it's a presigned B2 URL, download directly
            if "backblazeb2.com" in clip_url or "s3" in clip_url:
                # Extract key and get fresh presigned URL
                # For now, try direct download
                result = await asyncio.create_subprocess_exec(
                    "curl", "-L", "-o", output_path, clip_url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await result.communicate()
                return result.returncode == 0
            else:
                # Direct URL
                result = await asyncio.create_subprocess_exec(
                    "curl", "-L", "-o", output_path, clip_url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await result.communicate()
                return result.returncode == 0
    except Exception as e:
        print(f"Download error: {e}")
        return False


async def apply_transition_ffmpeg(
    input_files: list[str],
    transitions: list[dict],
    output_file: str,
) -> bool:
    """
    Concatenate videos with transitions using FFmpeg.
    
    Args:
        input_files: List of input video paths
        transitions: List of transition configs
        output_file: Output path
    
    Returns:
        True if successful
    """
    if len(input_files) < 2:
        # No concatenation needed
        if input_files:
            import shutil
            shutil.copy(input_files[0], output_file)
            return True
        return False
    
    # Create FFmpeg concat with transitions
    # For simplicity, using a basic concat filter
    # More advanced transitions can be added later
    
    filter_complex = []
    inputs = []
    
    for i, f in enumerate(input_files):
        inputs.extend(["-i", f])
    
    # Build simple concat
    n = len(input_files)
    filter_complex.append(f"[0:v]split={n}[v0]")
    for i in range(1, n):
        filter_complex.append(f"[v{i-1}][{i}:v]concat=n=2:v=1:a=0[v{i}]")
    
    filter_str = ";".join(filter_complex) + f";[v{n-1}]copy[outv]"
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        output_file,
    ]
    
    try:
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode != 0:
            print(f"FFmpeg error: {stderr.decode()}")
            return False
        return True
    except Exception as e:
        print(f"FFmpeg error: {e}")
        return False


async def mix_audio_ffmpeg(
    video_path: str,
    audio_tracks: list[dict],  # [{"url": str, "start": float, "volume": float}]
    narration_path: Optional[str],
    music_path: Optional[str],
    output_path: str,
) -> bool:
    """
    Mix audio tracks with video.
    
    Args:
        video_path: Input video
        audio_tracks: Additional audio to mix
        narration_path: Narration audio
        music_path: Background music
        output_path: Output path
    
    Returns:
        True if successful
    """
    cmd = ["ffmpeg", "-y", "-i", video_path]
    
    audio_inputs = []
    audio_filters = []
    
    # Add narration
    if narration_path:
        cmd.extend(["-i", narration_path])
        audio_inputs.append(f"{len(cmd) - 2}:a")
    
    # Add music
    if music_path:
        cmd.extend(["-i", music_path])
        audio_inputs.append(f"{len(cmd) - 2}:a")
    
    # Build audio mix filter
    if audio_inputs:
        if len(audio_inputs) == 1:
            audio_filters.append(f"[{audio_inputs[0]}]anull[outa]")
        else:
            audio_filters.append(
                f"{audio_inputs[0]}[{audio_inputs[1]}]amix=inputs={len(audio_inputs)}:duration=longest[outa]"
            )
        
        cmd.extend(["-filter_complex", ";".join(audio_filters)])
        cmd.extend(["-map", "0:v", "-map", "[outa]"])
    else:
        cmd.extend(["-map", "0:v", "-map", "0:a?"])
    
    cmd.extend([
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])
    
    try:
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        return result.returncode == 0
    except Exception as e:
        print(f"Audio mix error: {e}")
        return False


async def run_assembly_job(
    pool: asyncpg.Pool,
    job_id: str,
    worker_id: str,
) -> dict:
    """
    Main assembly job handler.
    
    Process:
    1. Get episode and approved scenes
    2. Download scene clips
    3. Apply transitions
    4. Mix audio
    5. Upload to B2
    6. Update episode record
    """
    job = await pool.fetchrow(
        "SELECT * FROM generation_jobs WHERE id = $1",
        job_id
    )
    
    if not job:
        return {"error": "Job not found"}
    
    episode_id = str(job["entity_id"])
    result_data = json.loads(job.get("result") or "{}")
    
    # Get episode
    episode = await pool.fetchrow(
        "SELECT * FROM episodes WHERE id = $1",
        episode_id
    )
    
    if not episode:
        return {"error": "Episode not found"}
    
    story_id = str(episode["story_id"])
    
    # Update job status
    await pool.execute(
        """UPDATE generation_jobs SET status = 'running', started_at = now(),
           current_step = 'Gathering scenes'
           WHERE id = $1""",
        job_id,
    )
    
    # Get approved scenes
    scenes = await pool.fetch(
        """SELECT s.* FROM scenes s
           WHERE s.episode_id = $1
             AND s.approval_status = 'approved'
             AND (s.clip_url IS NOT NULL OR s.media_url IS NOT NULL)
           ORDER BY s.scene_number""",
        episode_id,
    )
    
    if not scenes:
        return {"error": "No approved scenes with media"}
    
    print(f"Assembling {len(scenes)} scenes for episode {episode_id}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        clip_paths = []
        
        # Download each scene clip
        for i, scene in enumerate(scenes):
            clip_path = os.path.join(tmpdir, f"scene_{i:03d}.mp4")
            success = await download_scene_clip(pool, str(scene["id"]), clip_path)
            
            if success and os.path.exists(clip_path):
                clip_paths.append(clip_path)
            else:
                print(f"Failed to download scene {scene['id']}")
        
        if not clip_paths:
            return {"error": "No scenes could be downloaded"}
        
        # Update job
        await pool.execute(
            """UPDATE generation_jobs SET current_step = 'Concatenating scenes'
               WHERE id = $1""",
            job_id,
        )
        
        # Concatenate videos
        concat_output = os.path.join(tmpdir, "concat_raw.mp4")
        success = await apply_transition_ffmpeg(clip_paths, [], concat_output)
        
        if not success:
            return {"error": "Failed to concatenate scenes"}
        
        # Check for narration/music
        narration_path = None
        music_path = None
        
        # Mix audio
        audio_mix_output = os.path.join(tmpdir, "audio_mix.mp4")
        has_audio_mix = await mix_audio_ffmpeg(
            concat_output,
            [],
            narration_path,
            music_path,
            audio_mix_output,
        )
        
        final_output = audio_mix_output if has_audio_mix else concat_output
        
        # Update job
        await pool.execute(
            """UPDATE generation_jobs SET current_step = 'Uploading to storage'
               WHERE id = $1""",
            job_id,
        )
        
        # Upload to B2
        key = f"stories/{story_id}/episodes/{episode_id}/assembled_{job_id[:8]}.mp4"
        
        try:
            episode_url = upload_file(final_output, key, "video/mp4")
        except Exception as e:
            return {"error": f"Upload failed: {e}"}
        
        # Update episode
        await pool.execute(
            """UPDATE episodes SET 
               episode_url = $1,
               duration_seconds = $2,
               status = 'completed',
               updated_at = now()
               WHERE id = $3""",
            episode_url,
            0,  # Would need to calculate from scenes
            episode_id,
        )
        
        # Mark job complete
        await pool.execute(
            """UPDATE generation_jobs SET 
               status = 'completed',
               completed_at = now(),
               current_step = 'Done',
               result = $1::jsonb
               WHERE id = $2""",
            json.dumps({"episode_url": episode_url, "scenes_used": len(scenes)}),
            job_id,
        )
        
        return {
            "success": True,
            "episode_url": episode_url,
            "scenes_used": len(scenes),
        }


# ─── Integration Helper ────────────────────────────────────────────────────────

def register_assembly_handlers():
    """Add assembly job types to worker.py."""
    pass  # Implementation depends on worker architecture


# Example usage when integrated with worker.py:
"""
# In worker.py _run_handler():
if entity_type == "episode" or job_type == "episode_assembly":
    return await run_assembly_job(pool, str(row["id"]), worker_id)
"""
