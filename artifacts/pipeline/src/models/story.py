from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class StoryStatus(str, Enum):
    draft = "draft"
    generating = "generating"
    ready = "ready"
    failed = "failed"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class StoryCreate(BaseModel):
    title: str
    prompt: str
    genre: str = "action"
    style: str = "anime"
    num_episodes: int = Field(default=1, ge=1, le=5)
    num_scenes: int = Field(default=5, ge=3, le=10)


class StoryResponse(BaseModel):
    id: str
    title: str
    prompt: str
    genre: str
    style: str
    num_episodes: int
    num_scenes: int
    status: StoryStatus
    episode_plan: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class CharacterCreate(BaseModel):
    story_id: str
    name: str
    description: str
    role: str = "main"
    personality: str = ""
    appearance: str = ""


class CharacterResponse(BaseModel):
    id: str
    story_id: str
    name: str
    description: str
    role: str
    personality: str
    appearance: str
    ref_image_urls: list[str] = []
    voice_ref_url: Optional[str] = None
    embedding: Optional[list[float]] = None
    created_at: datetime


class SceneResponse(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    prompt: str
    clip_url: Optional[str] = None
    exit_frame_url: Optional[str] = None
    duration: Optional[float] = None
    status: JobStatus
    created_at: datetime


class EpisodeResponse(BaseModel):
    id: str
    story_id: str
    episode_number: int
    title: str
    assembled_video_url: Optional[str] = None
    manifest_url: Optional[str] = None
    status: JobStatus
    scenes: list[SceneResponse] = []
    created_at: datetime


class GenerationJobResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    status: JobStatus
    progress: int = 0
    total_steps: int = 0
    current_step: str = ""
    error: Optional[str] = None
    result: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
