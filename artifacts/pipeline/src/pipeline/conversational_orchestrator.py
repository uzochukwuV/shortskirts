"""
Conversational Orchestrator for Dysentry Video Production

Replaces rigid checkpoint system with a flexible, chat-based workflow.

Features:
- Chat-based scene generation commands
- Multi-character dialogue per scene (up to 3 lines)
- Frame extraction from existing scenes as references
- Scene regeneration with context preservation
- Timeline-based story management
- Automatic concatenation on demand

Usage:
    orchestrator = ConversationalOrchestrator()
    
    # Create story
    story = await orchestrator.create_story("A samurai story")
    
    # Generate scenes via chat
    response = await orchestrator.chat(story.id, "Generate scene 1 with master introducing himself")
    response = await orchestrator.chat(story.id, "Add scene 2 where student responds")
    response = await orchestrator.chat(story.id, "Use frame from scene 1 at 3s for scene 2")
    
    # Concatenate
    response = await orchestrator.chat(story.id, "Combine scenes 1-3")
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx

from pipeline.providers.dashscope import DashScopeVideoProvider
from pipeline.catalog import ContinuityState, build_scene_context, inject_continuity_into_prompt
from pipeline.media_tools import extract_last_frame_png, concatenate_video_files
from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from genblaze_core.models.step import Step
from genblaze_core import Modality


# ─── Data Models ────────────────────────────────────────────────────────────────

class SceneStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DialogueLine:
    """A single dialogue line from a character."""
    character_id: str
    character_name: str
    text: str
    voice: str = "longanfengyue"  # Default voice
    order: int = 0  # Order within the scene

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DialogueLine:
        return cls(**data)


@dataclass
class SceneReference:
    """A reference image used for scene generation."""
    source_scene_id: int
    timestamp: float  # Seconds into the video
    url: str
    exit_frame: bool = True  # True = exit frame, False = extracted frame

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scene:
    """A single video scene (max 5 seconds)."""
    id: int
    title: str
    prompt: str
    dialogues: list[DialogueLine] = field(default_factory=list)
    references: list[SceneReference] = field(default_factory=list)
    
    # Generation state
    status: SceneStatus = SceneStatus.PENDING
    video_url: Optional[str] = None
    exit_frame_url: Optional[str] = None
    local_path: Optional[str] = None  # Local file path for concatenation
    
    # Continuity
    continuity: Optional[dict] = None  # Previous scene continuity state
    
    # Timing
    created_at: str = ""
    updated_at: str = ""
    
    # Provider info
    model: str = "happyhorse-1.1-t2v"
    seed: int = 0
    task_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "prompt": self.prompt,
            "dialogues": [d.to_dict() for d in self.dialogues],
            "references": [r.to_dict() for r in self.references],
            "status": self.status.value if isinstance(self.status, SceneStatus) else self.status,
            "video_url": self.video_url,
            "exit_frame_url": self.exit_frame_url,
            "continuity": self.continuity,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "model": self.model,
            "seed": self.seed,
            "task_id": self.task_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Scene:
        data = dict(data)
        if "dialogues" in data and data["dialogues"]:
            data["dialogues"] = [DialogueLine.from_dict(d) for d in data["dialogues"]]
        if "references" in data and data["references"]:
            data["references"] = [SceneReference(**r) for r in data["references"]]
        if "status" in data and isinstance(data["status"], str):
            data["status"] = SceneStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Story:
    """A story containing multiple scenes."""
    id: str
    title: str
    description: str = ""
    scenes: list[Scene] = field(default_factory=list)
    characters: dict[str, dict] = field(default_factory=dict)
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    combined_video_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "scenes": [s.to_dict() for s in self.scenes],
            "characters": self.characters,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "combined_video_url": self.combined_video_url,
            "scene_count": len(self.scenes),
            "total_duration": len(self.scenes) * 5,  # 5s per scene
        }

    def add_scene(self, scene: Scene) -> None:
        self.scenes.append(scene)
        self.updated_at = datetime.utcnow().isoformat()


# ─── Orchestrator ──────────────────────────────────────────────────────────────

class ConversationalOrchestrator:
    """
    Chat-based video orchestrator.
    
    Provides a conversational interface for generating, regenerating,
    and managing video scenes.
    """

    def __init__(self):
        self._stories: dict[str, Story] = {}
        self._provider = DashScopeVideoProvider()

    # ─── Story Management ────────────────────────────────────────────────────

    async def create_story(
        self,
        title: str,
        description: str = "",
        characters: Optional[dict[str, dict]] = None,
    ) -> Story:
        """Create a new story."""
        story_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()
        
        story = Story(
            id=story_id,
            title=title,
            description=description,
            characters=characters or {},
            created_at=now,
            updated_at=now,
        )
        
        self._stories[story_id] = story
        print(f"[orchestrator] Created story: {story_id} - {title}")
        
        return story

    def get_story(self, story_id: str) -> Optional[Story]:
        """Get a story by ID."""
        return self._stories.get(story_id)

    def list_stories(self) -> list[Story]:
        """List all stories."""
        return list(self._stories.values())

    async def load_story_from_b2(self, story_id: str) -> Optional[Story]:
        """Load story state from B2."""
        try:
            from storage.b2 import download_url_to_bytes
            
            key = build_key("stories", story_id, "state.json")
            bytes_data = await download_url_to_bytes(key)
            data = json.loads(bytes_data)
            
            story = Story(
                id=data["id"],
                title=data["title"],
                description=data.get("description", ""),
                characters=data.get("characters", {}),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
                combined_video_url=data.get("combined_video_url"),
            )
            
            for scene_data in data.get("scenes", []):
                story.scenes.append(Scene.from_dict(scene_data))
            
            self._stories[story_id] = story
            return story
            
        except Exception as e:
            print(f"[orchestrator] Failed to load story: {e}")
            return None

    async def save_story_to_b2(self, story: Story) -> str:
        """Save story state to B2."""
        key = build_key("stories", story.id, "state.json")
        data = story.to_dict()
        bytes_data = json.dumps(data, indent=2).encode()
        url = upload_bytes(bytes_data, key, "application/json")
        print(f"[orchestrator] Saved story state: {key}")
        return url

    # ─── Scene Generation ─────────────────────────────────────────────────────

    async def generate_scene(
        self,
        story_id: str,
        title: str,
        prompt: str,
        dialogues: Optional[list[DialogueLine]] = None,
        references: Optional[list[SceneReference]] = None,
        use_previous_exit_frame: bool = True,
        model: str = "happyhorse-1.1-t2v",
    ) -> Scene:
        """Generate a new scene."""
        story = self.get_story(story_id)
        if not story:
            raise ValueError(f"Story not found: {story_id}")
        
        # Determine scene ID
        scene_id = len(story.scenes) + 1
        
        # Determine if T2V or I2V based on references
        if references or (use_previous_exit_frame and story.scenes):
            model = model.replace("t2v", "i2v") if "t2v" in model else model
            if "i2v" not in model and "r2v" not in model:
                model = "happyhorse-1.1-i2v"
        
        # Build the scene
        scene = Scene(
            id=scene_id,
            title=title,
            prompt=prompt,
            dialogues=dialogues or [],
            references=references or [],
            status=SceneStatus.GENERATING,
            model=model,
            seed=int(time.time()) % 10000,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        
        # Add continuity from previous scene
        if use_previous_exit_frame and story.scenes:
            prev_scene = story.scenes[-1]
            if prev_scene.exit_frame_url:
                scene.references.insert(0, SceneReference(
                    source_scene_id=prev_scene.id,
                    timestamp=5.0,  # Exit frame
                    url=prev_scene.exit_frame_url,
                    exit_frame=True,
                ))
                scene.continuity = prev_scene.continuity
        
        print(f"[orchestrator] Generating scene {scene_id}: {title}")
        
        # Generate video
        video_url, video_bytes, task_id = await self._generate_video(
            prompt=prompt,
            model=model,
            seed=scene.seed,
            references=[r.url for r in scene.references if r.url],
        )
        
        scene.video_url = video_url
        scene.task_id = task_id
        scene.status = SceneStatus.COMPLETED
        scene.updated_at = datetime.utcnow().isoformat()
        
        # Extract and upload exit frame
        exit_frame = await extract_last_frame_png(video_bytes)
        exit_frame_url = upload_bytes(
            exit_frame,
            build_key("stories", story_id, "scenes", f"scene_{scene_id}_exit.png"),
            "image/png",
        )
        scene.exit_frame_url = exit_frame_url
        
        # Save local copy for concatenation
        local_path = f"/tmp/{story_id}_scene_{scene_id}.mp4"
        with open(local_path, 'wb') as f:
            f.write(video_bytes)
        scene.local_path = local_path
        
        # Update continuity state
        scene.continuity = {
            "lighting_type": "natural",
            "camera_angle": "eye_level",
            "camera_motion": "static",
        }
        
        # Add to story
        story.add_scene(scene)
        
        # Save state
        await self.save_story_to_b2(story)
        
        print(f"[orchestrator] Scene {scene_id} complete: {video_url}")
        
        return scene

    async def regenerate_scene(
        self,
        story_id: str,
        scene_id: int,
        new_prompt: Optional[str] = None,
        keep_references: bool = True,
    ) -> Scene:
        """Regenerate an existing scene."""
        story = self.get_story(story_id)
        if not story:
            raise ValueError(f"Story not found: {story_id}")
        
        scene = next((s for s in story.scenes if s.id == scene_id), None)
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")
        
        # Update prompt if provided
        if new_prompt:
            scene.prompt = new_prompt
        
        scene.status = SceneStatus.GENERATING
        scene.seed = int(time.time()) % 10000
        scene.updated_at = datetime.utcnow().isoformat()
        
        print(f"[orchestrator] Regenerating scene {scene_id}")
        
        # Generate video
        video_url, video_bytes, task_id = await self._generate_video(
            prompt=scene.prompt,
            model=scene.model,
            seed=scene.seed,
            references=[r.url for r in scene.references] if keep_references else None,
        )
        
        scene.video_url = video_url
        scene.task_id = task_id
        scene.status = SceneStatus.COMPLETED
        
        # Update exit frame
        exit_frame = await extract_last_frame_png(video_bytes)
        exit_frame_url = upload_bytes(
            exit_frame,
            build_key("stories", story_id, "scenes", f"scene_{scene_id}_exit.png"),
            "image/png",
        )
        scene.exit_frame_url = exit_frame_url
        
        # Update local file
        if scene.local_path:
            with open(scene.local_path, 'wb') as f:
                f.write(video_bytes)
        
        # Save state
        await self.save_story_to_b2(story)
        
        return scene

    async def extract_frame(
        self,
        story_id: str,
        scene_id: int,
        timestamp: float,
    ) -> Optional[str]:
        """Extract a frame from a scene at a specific timestamp."""
        story = self.get_story(story_id)
        if not story:
            return None
        
        scene = next((s for s in story.scenes if s.id == scene_id), None)
        if not scene or not scene.video_url:
            return None
        
        try:
            # Download video
            video_bytes = await download_url_to_bytes(scene.video_url)
            
            # Extract frame at timestamp (using ffmpeg)
            from pipeline.media_tools import extract_middle_frame_png
            
            # For non-exit frames, we'd need a more sophisticated approach
            # For now, return the exit frame
            return scene.exit_frame_url
            
        except Exception as e:
            print(f"[orchestrator] Frame extraction failed: {e}")
            return None

    async def concatenate_scenes(
        self,
        story_id: str,
        start_scene: int = 1,
        end_scene: Optional[int] = None,
    ) -> str:
        """Concatenate scenes and return B2 URL."""
        story = self.get_story(story_id)
        if not story:
            raise ValueError(f"Story not found: {story_id}")
        
        end_scene = end_scene or len(story.scenes)
        
        # Collect completed scenes
        scenes_to_concat = [
            s for s in story.scenes
            if start_scene <= s.id <= end_scene and s.local_path
        ]
        
        if not scenes_to_concat:
            raise ValueError("No completed scenes to concatenate")
        
        # Sort by ID
        scenes_to_concat.sort(key=lambda s: s.id)
        
        print(f"[orchestrator] Concatenating {len(scenes_to_concat)} scenes")
        
        # Concatenate
        output_path = f"/tmp/{story_id}_scenes_{start_scene}-{end_scene}.mp4"
        await concatenate_video_files(
            [s.local_path for s in scenes_to_concat],
            output_path,
        )
        
        # Upload to B2
        with open(output_path, 'rb') as f:
            combined_bytes = f.read()
        
        key = build_key("stories", story_id, f"combined_{start_scene}-{end_scene}.mp4")
        combined_url = upload_bytes(combined_bytes, key, "video/mp4")
        
        # Update story
        if start_scene == 1 and end_scene == len(story.scenes):
            story.combined_video_url = combined_url
            await self.save_story_to_b2(story)
        
        # Cleanup
        try:
            os.unlink(output_path)
        except:
            pass
        
        print(f"[orchestrator] Concatenated video: {combined_url}")
        
        return combined_url

    # ─── Internal ────────────────────────────────────────────────────────────

    async def _generate_video(
        self,
        prompt: str,
        model: str,
        seed: int,
        references: Optional[list[str]] = None,
    ) -> tuple[str, bytes, str]:
        """Generate video and return (url, bytes, task_id)."""
        references = references or []
        
        step = Step(provider='dashscope-video', model=model, prompt=prompt)
        step.params = {
            'duration': 5,
            'resolution': '1080P',
            'ratio': '16:9',
            'seed': seed,
        }
        step.inputs = references
        step.modality = Modality.VIDEO
        
        # Submit
        task_id = self._provider.submit(step)
        print(f"[orchestrator] Task submitted: {task_id}")
        
        # Poll
        status = self._provider._poll_status(task_id, timeout=300)
        
        if status != "SUCCEEDED":
            raise Exception(f"Video generation failed: {status}")
        
        # Fetch
        step = self._provider.fetch_output(task_id, step)
        video_url = step.assets[0].url
        
        # Download
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(video_url)
            video_bytes = resp.content
        
        return video_url, video_bytes, task_id


# ─── Chat Interface ────────────────────────────────────────────────────────────

    async def chat(self, story_id: str, message: str) -> dict:
        """
        Process a chat message and execute the appropriate action.
        
        Examples:
        - "generate scene 1 with master introducing himself"
        - "add scene 2 where student responds"  
        - "regenerate scene 2 with more action"
        - "use frame from scene 1 at 3s"
        - "combine scenes 1-3"
        - "show timeline"
        """
        message = message.lower().strip()
        story = self.get_story(story_id)
        
        response = {
            "success": False,
            "message": "",
            "data": None,
        }
        
        # Parse intent
        if "generate scene" in message or "add scene" in message or "create scene" in message:
            # Extract scene number and description
            scene_num = len(story.scenes) + 1 if story else 1
            title = message.replace("generate scene", "").replace("add scene", "").replace("create scene", "").strip()
            if not title:
                title = f"Scene {scene_num}"
            
            # Build prompt from message
            prompt = self._build_prompt_from_description(title)
            
            # Generate
            scene = await self.generate_scene(
                story_id=story_id,
                title=title,
                prompt=prompt,
            )
            
            response["success"] = True
            response["message"] = f"Generated {title}"
            response["data"] = scene.to_dict()
            
        elif "regenerate scene" in message:
            # Extract scene number
            parts = message.split("regenerate scene")
            if len(parts) > 1:
                scene_num = int(parts[1].split()[0])
                
                # Extract new description if provided
                new_prompt = None
                if "with" in message:
                    new_desc = message.split("with", 1)[1].strip()
                    new_prompt = self._build_prompt_from_description(new_desc)
                
                scene = await self.regenerate_scene(
                    story_id=story_id,
                    scene_id=scene_num,
                    new_prompt=new_prompt,
                )
                
                response["success"] = True
                response["message"] = f"Regenerated scene {scene_num}"
                response["data"] = scene.to_dict()
            else:
                response["message"] = "Please specify scene number"
                
        elif "combine" in message or "concatenate" in message or "join" in message:
            # Extract scene range
            parts = message.replace("combine", "").replace("concatenate", "").replace("join", "").strip()
            if "-" in parts:
                start, end = parts.split("-")
                start = int(start.strip())
                end = int(end.strip())
            else:
                start, end = 1, len(story.scenes)
            
            url = await self.concatenate_scenes(story_id, start, end)
            
            response["success"] = True
            response["message"] = f"Combined scenes {start}-{end}"
            response["data"] = {"url": url}
            
        elif "timeline" in message or "show scenes" in message or "list scenes" in message:
            scenes = [s.to_dict() for s in story.scenes] if story else []
            
            response["success"] = True
            response["message"] = f"{len(scenes)} scenes"
            response["data"] = {
                "scenes": scenes,
                "total_duration": len(scenes) * 5,
            }
            
        elif "dialogue" in message or "character" in message:
            # Add dialogue to current scene
            if story and story.scenes:
                scene = story.scenes[-1]
                # Parse dialogue...
                response["message"] = "Dialogue support - specify character and text"
            else:
                response["message"] = "No scenes yet to add dialogue"
        else:
            response["message"] = "I didn't understand. Try: generate scene, regenerate scene N, combine, or timeline"
        
        return response

    def _build_prompt_from_description(self, description: str) -> str:
        """Build a cinematic prompt from a description."""
        # Simple prompt builder - can be enhanced with LLM
        return f"""{description}
Medium shot. Cinematic lighting. Smooth camera movement.
Frame ratio: 16:9, professional film quality.
High production value, detailed, emotional depth."""


# ─── Global Instance ──────────────────────────────────────────────────────────

_orchestrator: Optional[ConversationalOrchestrator] = None


def get_orchestrator() -> ConversationalOrchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ConversationalOrchestrator()
    return _orchestrator
