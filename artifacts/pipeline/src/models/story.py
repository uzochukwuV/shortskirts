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
    narrated_image_story = "narrated_image_story"  # Still-image story beats with narration


class MediaKind(str, Enum):
    auto = "auto"
    video = "video"
    image = "image"


class BibleType(str, Enum):
    brand     = "brand"       # Colors, tone, forbidden claims, CTAs
    character = "character"   # Face, outfit, personality, voice
    world     = "world"       # Locations, rules, visual motifs
    campaign  = "campaign"    # Target audience, offer, compliance, platforms


class StoryStatus(str, Enum):
    draft            = "draft"             # Plan generated — awaiting approval
    approved         = "approved"          # Outline approved — ready to generate
    generating       = "generating"        # Generation running
    checkpoint_review = "checkpoint_review"  # Paused at a human review checkpoint
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
    canceled  = "canceled"


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
    frame_ratio: str = "16:9"
    requested_video_ratio: str = "16:9"
    num_episodes: int = Field(default=1, ge=1, le=5)
    num_scenes: int = Field(default=5, ge=3, le=10)
    workflow_type: WorkflowType = WorkflowType.creator_series
    requested_media_kind: MediaKind = MediaKind.auto
    bible_ids: list[str] = Field(default_factory=list)
    style_reference_urls: list[str] = Field(default_factory=list)
    character_reference_urls: list[str] = Field(default_factory=list)
    scene_reference_urls: list[str] = Field(default_factory=list)
    pipeline_config: dict[str, Any] = Field(default_factory=dict)


class StoryPipelineConfigUpdate(BaseModel):
    pipeline_config: dict[str, Any] = Field(default_factory=dict)


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    genre: Optional[str] = None
    style: Optional[str] = None
    synopsis: Optional[str] = None
    setting: Optional[str] = None
    themes: Optional[list[str]] = None


class StoryAssistantRequest(BaseModel):
    instruction: str
    target: str = "story"
    scene_id: Optional[str] = None


class StoryAssistantResponse(BaseModel):
    target: str
    message: str
    story_patch: dict[str, Any] = Field(default_factory=dict)
    scene_patch: dict[str, Any] = Field(default_factory=dict)


class ValidActionResponse(BaseModel):
    key: str
    label: str
    target: str
    enabled: bool = True
    requires_confirmation: bool = False
    reason: Optional[str] = None


class StoryResponse(BaseModel):
    id: str
    title: str
    prompt: str
    genre: str
    style: str
    frame_ratio: str = "16:9"
    requested_video_ratio: str = "16:9"
    num_episodes: int
    num_scenes: int
    status: StoryStatus
    workflow_type: WorkflowType = WorkflowType.creator_series
    requested_media_kind: MediaKind = MediaKind.auto
    workflow_version: str = "v1"
    generation_version: str = "v1"
    approval_status: str = "pending_approval"
    pipeline_config: Optional[dict] = None
    workflow_state: Optional[dict] = None
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


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    personality: Optional[str] = None
    appearance: Optional[str] = None
    ref_image_urls: Optional[list[str]] = None
    approval_status: Optional[str] = None
    locked: Optional[bool] = None


class SceneCreate(BaseModel):
    episode_id: str
    scene_number: int
    prompt: str
    title: Optional[str] = None
    description: Optional[str] = None
    visual_prompt: Optional[str] = None
    mood: Optional[str] = None
    location: Optional[str] = None
    action: Optional[str] = None
    narration: Optional[str] = None
    duration: Optional[float] = None
    media_kind: str = "video"
    frame_ratio: str = "16:9"
    character_ids: list[str] = Field(default_factory=list)
    reference_image_urls: list[str] = Field(default_factory=list)
    generate: bool = False


class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    prompt: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    visual_prompt: Optional[str] = None
    mood: Optional[str] = None
    location: Optional[str] = None
    action: Optional[str] = None
    narration: Optional[str] = None
    duration: Optional[float] = None
    media_kind: Optional[str] = None
    frame_ratio: Optional[str] = None
    character_ids: Optional[list[str]] = None
    primary_character_ids: Optional[list[str]] = None
    reference_image_urls: Optional[list[str]] = None
    approval_status: Optional[str] = None
    locked: Optional[bool] = None


class SceneCharactersUpdate(BaseModel):
    character_ids: list[str] = Field(default_factory=list)
    primary_character_ids: list[str] = Field(default_factory=list)


class SceneReorderRequest(BaseModel):
    new_scene_number: int = Field(ge=1)


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
    scene_ids: list[str] = []
    created_at: datetime


# ─── Scenes ───────────────────────────────────────────────────────────────────

class SceneResponse(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    prompt: str
    clip_url: Optional[str] = None
    image_url: Optional[str] = None
    exit_frame_url: Optional[str] = None
    duration: Optional[float] = None
    status: str
    approval_status: str = "pending"
    locked: bool = False
    regeneration_count: int = 0
    generation_version: str = "v1"
    image_model: Optional[str] = None
    image_model_version: Optional[str] = None
    edit_model: Optional[str] = None
    edit_model_version: Optional[str] = None
    source_scene_id: Optional[str] = None
    state_snapshot: Optional[dict] = None
    character_ids: list[str] = []
    primary_character_ids: list[str] = []
    created_at: datetime

    # Fields from generation_metadata
    title: Optional[str] = None
    description: Optional[str] = None
    visual_prompt: Optional[str] = None
    mood: Optional[str] = None
    location: Optional[str] = None
    narration: Optional[str] = None
    media_kind: Optional[str] = None
    frame_ratio: Optional[str] = None

    @computed_field
    @property
    def video_url(self) -> Optional[str]:
        """Alias for clip_url — matches frontend Scene.video_url field."""
        return self.clip_url

    @computed_field
    @property
    def media_url(self) -> Optional[str]:
        return self.image_url or self.clip_url


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


class GalleryItemResponse(BaseModel):
    id: str
    kind: str
    media_kind: Optional[str] = None
    story_id: str
    story_title: str
    episode_id: str
    episode_number: int
    scene_id: Optional[str] = None
    scene_number: Optional[int] = None
    title: str
    summary: Optional[str] = None
    media_url: str
    duration: Optional[float] = None
    created_at: datetime


class GenerationCheckpointResponse(BaseModel):
    id: str
    story_id: str
    job_id: Optional[str] = None
    resume_job_id: Optional[str] = None
    batch_number: int = 1
    batch_size: int = 3
    start_episode_number: int = 1
    start_scene_number: int = 1
    end_episode_number: int = 1
    end_scene_number: int = 1
    status: str = "pending_review"
    generation_version: str = "v1"
    narration_model: Optional[str] = None
    narration_voice: Optional[str] = None
    narration_text: Optional[str] = None
    audio_job_id: Optional[str] = None
    audio_status: Optional[str] = None
    narration_audio_url: Optional[str] = None
    narration_audio_manifest_url: Optional[str] = None
    state_snapshot: Optional[dict] = None
    resume_state: Optional[dict] = None
    reviewer_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class HistoryEntryResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    revision: int
    event_type: str
    workflow_version: Optional[str] = None
    generation_version: str = "v1"
    source_job_id: Optional[str] = None
    state_snapshot: Optional[dict] = None
    payload: Optional[dict] = None
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
    attempts: int = 0
    max_attempts: int = 3
    worker_id: Optional[str] = None
    leased_at: Optional[datetime] = None
    lease_expires_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
