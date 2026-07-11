from pydantic import BaseModel, Field, computed_field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class WorkflowType(str, Enum):
    creator_series  = "creator_series"    # Serialized anime / fiction series
    brand_campaign  = "brand_campaign"    # Ad concepts from product brief
    social_short    = "social_short"      # TikTok / Reels / Shorts vertical
    educational     = "educational"       # Animated explainer / course lesson
    game_lore       = "game_lore"         # IP bible → lore trailers / teasers


class BibleType(str, Enum):
    brand     = "brand"       # Colors, tone, forbidden claims, CTAs
    character = "character"   # Face, outfit, personality, voice
    world     = "world"       # Locations, rules, visual motifs
    campaign  = "campaign"    # Target audience, offer, compliance, platforms


class StoryStatus(str, Enum):
    draft            = "draft"             # Plan generated — awaiting approval
    approved         = "approved"          # Outline approved — ready to generate
    generating       = "generating"        # Generation running
    ready            = "ready"             # Legacy alias for completed
    completed        = "completed"
    failed           = "failed"


class ApprovalStatus(str, Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"
    locked   = "locked"


class JobStatus(str, Enum):
    pending   = "pending"
    running   = "running"
    completed = "completed"
    failed    = "failed"


# ─── Bibles ───────────────────────────────────────────────────────────────────

class BibleCreate(BaseModel):
    story_id: Optional[str] = None
    bible_type: BibleType = BibleType.brand
    name: str
    content: dict = Field(default_factory=dict)


class BibleResponse(BaseModel):
    id: str
    story_id: Optional[str] = None
    bible_type: BibleType
    name: str
    content: dict
    created_at: datetime
    updated_at: datetime


# ─── Stories ──────────────────────────────────────────────────────────────────

class StoryCreate(BaseModel):
    title: str
    prompt: str
    genre: str = "action"
    style: str = "anime"
    num_episodes: int = Field(default=1, ge=1, le=5)
    num_scenes: int = Field(default=5, ge=3, le=10)
    workflow_type: WorkflowType = WorkflowType.creator_series
    bible_ids: list[str] = Field(default_factory=list)


class StoryResponse(BaseModel):
    id: str
    title: str
    prompt: str
    genre: str
    style: str
    num_episodes: int
    num_scenes: int
    status: StoryStatus
    workflow_type: WorkflowType = WorkflowType.creator_series
    approval_status: str = "pending_approval"
    episode_plan: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


# ─── Characters ───────────────────────────────────────────────────────────────

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
    approval_status: str = "pending"
    locked: bool = False
    created_at: datetime


# ─── Scenes ───────────────────────────────────────────────────────────────────

class SceneResponse(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    prompt: str
    clip_url: Optional[str] = None
    exit_frame_url: Optional[str] = None
    duration: Optional[float] = None
    status: str
    approval_status: str = "pending"
    locked: bool = False
    regeneration_count: int = 0
    created_at: datetime

    # Fields from generation_metadata
    title: Optional[str] = None
    description: Optional[str] = None
    visual_prompt: Optional[str] = None
    mood: Optional[str] = None
    location: Optional[str] = None

    @computed_field
    @property
    def video_url(self) -> Optional[str]:
        """Alias for clip_url — matches frontend Scene.video_url field."""
        return self.clip_url


# ─── Episodes ─────────────────────────────────────────────────────────────────

class EpisodeResponse(BaseModel):
    id: str
    story_id: str
    episode_number: int
    title: str
    summary: Optional[str] = None
    assembled_video_url: Optional[str] = None
    manifest_url: Optional[str] = None
    status: str
    scenes: list[SceneResponse] = []
    created_at: datetime


# ─── Jobs ─────────────────────────────────────────────────────────────────────

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
    job_type: str = "full_episode"
