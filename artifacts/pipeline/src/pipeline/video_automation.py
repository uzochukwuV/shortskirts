"""
Video Automation - Generate, Upload, and Publish Pipeline

Automated workflow for:
1. Generate video scenes via ConversationalOrchestrator
2. Concatenate scenes into final video
3. Upload to B2
4. Publish to YouTube/TikTok (if configured)

Usage:
    from pipeline.video_automation import VideoAutomation
    
    automation = VideoAutomation()
    
    # Generate and upload
    result = await automation.generate_and_upload(
        title="My Story",
        scenes=[...],
        characters={...},
        publish_targets=["youtube"],
    )
    
    print(f"Video: {result['video_url']}")
    print(f"YouTube: {result['youtube_url']}")
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx

from pipeline.conversational_orchestrator import (
    ConversationalOrchestrator,
    DialogueLine,
)
from pipeline.media_tools import concatenate_video_files
from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from pipeline.publishers.youtube import YouTubePublisher
from pipeline.publishers.tiktok import TikTokPublisher


class PublishStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class PublishTarget:
    """A publish target (YouTube, TikTok, etc.)."""
    platform: str  # "youtube", "tiktok"
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    privacy: str = "public"  # youtube: "public", "unlisted", "private"
    schedule_time: Optional[datetime] = None


@dataclass
class AutomationResult:
    """Result from automated video generation."""
    story_id: str
    run_id: str
    video_url: str  # B2 URL
    video_path: str  # Local path (temp)
    
    # Scene results
    scenes: list[dict] = field(default_factory=list)
    
    # Publish results
    publish_results: dict[str, str] = field(default_factory=dict)  # platform -> url
    publish_status: dict[str, str] = field(default_factory=dict)
    
    # Metadata
    total_duration: int = 0
    total_scenes: int = 0
    status: str = "generating"
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "story_id": self.story_id,
            "run_id": self.run_id,
            "video_url": self.video_url,
            "scenes": self.scenes,
            "publish_results": self.publish_results,
            "publish_status": self.publish_status,
            "total_duration": self.total_duration,
            "total_scenes": self.total_scenes,
            "status": self.status,
            "error": self.error,
        }


class VideoAutomation:
    """
    Automated video generation and publishing pipeline.
    
    Workflow:
    1. Generate scenes via ConversationalOrchestrator
    2. Concatenate into final video
    3. Upload to B2
    4. Optionally publish to YouTube/TikTok
    """
    
    def __init__(self):
        self._orchestrator = ConversationalOrchestrator()
        self._youtube: Optional[YouTubePublisher] = None
        self._tiktok: Optional[TikTokPublisher] = None
    
    def _get_youtube(self) -> Optional[YouTubePublisher]:
        """Get YouTube publisher if configured."""
        if self._youtube is None:
            try:
                self._youtube = YouTubePublisher()
            except Exception as e:
                print(f"[automation] YouTube not configured: {e}")
        return self._youtube
    
    def _get_tiktok(self) -> Optional[TikTokPublisher]:
        """Get TikTok publisher if configured."""
        if self._tiktok is None:
            try:
                self._tiktok = TikTokPublisher()
            except Exception as e:
                print(f"[automation] TikTok not configured: {e}")
        return self._tiktok
    
    async def generate_and_upload(
        self,
        title: str,
        scenes: list[dict],
        characters: Optional[dict[str, dict]] = None,
        description: str = "",
        tags: Optional[list[str]] = None,
        publish_targets: Optional[list[str]] = None,
        callback_url: Optional[str] = None,
    ) -> AutomationResult:
        """
        Generate video and optionally publish.
        
        Args:
            title: Video/story title
            scenes: List of scene definitions with prompt, dialogues
            characters: Character definitions with names, voices
            description: Video description
            tags: YouTube tags
            publish_targets: List of platforms ["youtube", "tiktok"]
            callback_url: URL to call when complete
        
        Returns:
            AutomationResult with video URL and publish URLs
        """
        story_id = str(uuid.uuid4())[:8]
        run_id = str(uuid.uuid4())[:8]
        publish_targets = publish_targets or []
        tags = tags or []
        
        print(f"[automation:{run_id}] Starting: {title}")
        print(f"[automation:{run_id}] Scenes: {len(scenes)}")
        print(f"[automation:{run_id}] Publish targets: {publish_targets}")
        
        result = AutomationResult(
            story_id=story_id,
            run_id=run_id,
            video_url="",
            video_path="",
            total_scenes=len(scenes),
        )
        
        try:
            # Create story
            story = await self._orchestrator.create_story(
                title=title,
                description=description,
                characters=characters or {},
            )
            
            # Generate scenes
            print(f"[automation:{run_id}] Generating scenes...")
            scene_results = []
            
            for i, scene_def in enumerate(scenes):
                scene_num = i + 1
                scene_title = scene_def.get("title", f"Scene {scene_num}")
                prompt = scene_def.get("prompt", "")
                dialogues = scene_def.get("dialogues", [])
                
                print(f"[automation:{run_id}] Scene {scene_num}: {scene_title}")
                
                # Convert dialogues
                dialogue_lines = []
                for j, dl in enumerate(dialogues):
                    if isinstance(dl, str):
                        dialogue_lines.append(DialogueLine(
                            character_id=dl.get("character_id", "narrator"),
                            character_name=dl.get("character_name", "Narrator"),
                            text=dl.get("text", dl) if isinstance(dl, dict) else dl,
                            order=j,
                        ))
                    else:
                        dialogue_lines.append(DialogueLine(
                            character_id=dl.get("character_id", "narrator"),
                            character_name=dl.get("character_name", "Narrator"),
                            text=str(dl),
                            order=j,
                        ))
                
                # Generate scene
                scene = await self._orchestrator.generate_scene(
                    story_id=story.id,
                    title=scene_title,
                    prompt=prompt,
                    dialogues=dialogue_lines,
                )
                
                scene_results.append({
                    "id": scene.id,
                    "title": scene.title,
                    "video_url": scene.video_url,
                    "exit_frame_url": scene.exit_frame_url,
                    "status": "completed",
                })
            
            result.scenes = scene_results
            print(f"[automation:{run_id}] All scenes generated")
            
            # Concatenate
            print(f"[automation:{run_id}] Concatenating scenes...")
            local_path = f"/tmp/{story_id}_final.mp4"
            await concatenate_video_files(
                [s.local_path for s in story.scenes if s.local_path],
                local_path,
            )
            result.video_path = local_path
            result.total_duration = len(story.scenes) * 5
            
            # Upload to B2
            print(f"[automation:{run_id}] Uploading to B2...")
            with open(local_path, 'rb') as f:
                video_bytes = f.read()
            
            video_key = build_key("automations", run_id, "video.mp4")
            result.video_url = upload_bytes(video_bytes, video_key, "video/mp4")
            print(f"[automation:{run_id}] B2 URL: {result.video_url}")
            
            # Publish to targets
            if publish_targets:
                await self._publish(
                    result=result,
                    video_path=local_path,
                    title=title,
                    description=description,
                    tags=tags,
                    targets=publish_targets,
                )
            
            result.status = "completed"
            print(f"[automation:{run_id}] Complete!")
            
            # Cleanup local file
            try:
                os.unlink(local_path)
            except:
                pass
            
            # Call callback if provided
            if callback_url:
                await self._call_callback(callback_url, result)
            
            return result
            
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            print(f"[automation:{run_id}] Failed: {e}")
            
            if callback_url:
                await self._call_callback(callback_url, result)
            
            return result
    
    async def _publish(
        self,
        result: AutomationResult,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        targets: list[str],
    ) -> None:
        """Publish to configured platforms."""
        
        # YouTube
        if "youtube" in targets:
            youtube = self._get_youtube()
            if youtube:
                try:
                    result.publish_status["youtube"] = PublishStatus.PUBLISHING.value
                    print(f"[automation:{result.run_id}] Publishing to YouTube...")
                    
                    # Upload
                    with open(video_path, 'rb') as f:
                        video_bytes = f.read()
                    
                    youtube_url = youtube.upload_video(
                        video_data=video_bytes,
                        title=title,
                        description=description,
                        tags=tags,
                    )
                    
                    result.publish_results["youtube"] = youtube_url
                    result.publish_status["youtube"] = PublishStatus.PUBLISHED.value
                    print(f"[automation:{result.run_id}] YouTube: {youtube_url}")
                    
                except Exception as e:
                    result.publish_status["youtube"] = PublishStatus.FAILED.value
                    print(f"[automation:{result.run_id}] YouTube failed: {e}")
        
        # TikTok
        if "tiktok" in targets:
            tiktok = self._get_tiktok()
            if tiktok:
                try:
                    result.publish_status["tiktok"] = PublishStatus.PUBLISHING.value
                    print(f"[automation:{result.run_id}] Publishing to TikTok...")
                    
                    with open(video_path, 'rb') as f:
                        video_bytes = f.read()
                    
                    tiktok_url = tiktok.upload_video(
                        video_data=video_bytes,
                        title=title,
                        description=description,
                    )
                    
                    result.publish_results["tiktok"] = tiktok_url
                    result.publish_status["tiktok"] = PublishStatus.PUBLISHED.value
                    print(f"[automation:{result.run_id}] TikTok: {tiktok_url}")
                    
                except Exception as e:
                    result.publish_status["tiktok"] = PublishStatus.FAILED.value
                    print(f"[automation:{result.run_id}] TikTok failed: {e}")
    
    async def _call_callback(self, url: str, result: AutomationResult) -> None:
        """Call callback URL with result."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(url, json=result.to_dict())
        except Exception as e:
            print(f"[automation] Callback failed: {e}")


# ─── Cron Automation for Scheduled Publishing ────────────────────────────────────

class ScheduledVideoAutomation:
    """
    Cron-based video automation.
    
    Use with OpenHands Automation for scheduled video generation.
    """
    
    def __init__(self):
        self._automation = VideoAutomation()
    
    async def run_scheduled(
        self,
        config: dict,
    ) -> dict:
        """
        Run scheduled video generation.
        
        Config format (from cron trigger):
        ```json
        {
            "title": "Weekly Update",
            "scenes": [...],
            "characters": {...},
            "publish_targets": ["youtube"],
            "callback_url": "https://..."
        }
        ```
        """
        result = await self._automation.generate_and_upload(
            title=config.get("title", "Automated Video"),
            scenes=config.get("scenes", []),
            characters=config.get("characters", {}),
            description=config.get("description", ""),
            tags=config.get("tags", []),
            publish_targets=config.get("publish_targets", []),
            callback_url=config.get("callback_url"),
        )
        
        return result.to_dict()


# ─── Global Instance ────────────────────────────────────────────────────────────

_automation: Optional[VideoAutomation] = None


def get_video_automation() -> VideoAutomation:
    """Get the global video automation instance."""
    global _automation
    if _automation is None:
        _automation = VideoAutomation()
    return _automation
