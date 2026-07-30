from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class PipelineRunResponse(BaseModel):
    id: str
    owner_id: Optional[str] = None
    story_id: Optional[str] = None
    job_id: Optional[str] = None
    run_type: str
    status: str
    config: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PipelineStepResponse(BaseModel):
    id: str
    run_id: str
    parent_step_id: Optional[str] = None
    story_id: Optional[str] = None
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    job_id: Optional[str] = None
    step_key: str
    step_type: str
    status: str
    attempt: int = 1
    provider: Optional[str] = None
    provider_model: Optional[str] = None
    provider_task_id: Optional[str] = None
    provider_request_id: Optional[str] = None
    input: dict[str, Any] = {}
    output: dict[str, Any] = {}
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PipelineArtifactResponse(BaseModel):
    id: str
    run_id: str
    step_id: Optional[str] = None
    story_id: Optional[str] = None
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    artifact_type: str
    media_kind: Optional[str] = None
    url: Optional[str] = None
    content: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = {}
    created_at: datetime


class PipelineRunDetailResponse(BaseModel):
    run: PipelineRunResponse
    steps: list[PipelineStepResponse] = []
    artifacts: list[PipelineArtifactResponse] = []


# Agent SDK Pydantic Contracts for Phase 1

class ShotType(str, Enum):
    """Shot types for structured scene planning."""
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    POINT_OF_VIEW = "point_of_view"
    ESTABLISHING = "establishing"
    INSERT = "insert"
    CUTAWAY = "cutaway"
    TWO_SHOT = "two_shot"
    GROUP = "group"


class BeatType(str, Enum):
    """Story beat types for scene structure."""
    OPENING = "opening"
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    TRANSITION = "transition"


class TransitionType(str, Enum):
    """Transition types between shots/scenes."""
    CUT = "cut"
    MATCH_CUT = "match_cut"
    DISSOLVE = "dissolve"
    FADE = "fade"
    WIPE = "wipe"
    SWISH_PAN = "swish_pan"


class CameraMovement(str, Enum):
    """Camera movement types."""
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY = "dolly"
    TRACK = "track"
    CRANE = "crane"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"
    ZOOM = "zoom"


class LightingMood(str, Enum):
    """Lighting mood descriptors."""
    NATURAL = "natural"
    DRAMATIC = "dramatic"
    SOFT = "soft"
    HIGH_KEY = "high_key"
    LOW_KEY = "low_key"
    SILHOUETTE = "silhouette"
    RIM = "rim"
    BACKLIT = "backlit"


class StyleProfile(BaseModel):
    """
    Style constraints and preferences for video generation.
    Controls visual direction without hardcoding specific aesthetics.
    """
    style_description: str = Field(
        default="",
        description="Natural language description of the desired visual style"
    )
    mood: str = Field(
        default="",
        description="Mood/emotional quality (e.g., 'serene', 'intense', 'whimsical')"
    )
    color_palette: list[str] = Field(
        default_factory=list,
        description="Preferred color palette keywords"
    )
    lighting: LightingMood = Field(
        default=LightingMood.NATURAL,
        description="Lighting mood"
    )
    camera_movement: CameraMovement = Field(
        default=CameraMovement.STATIC,
        description="Primary camera movement style"
    )
    exclusions: list[str] = Field(
        default_factory=list,
        description="Elements to avoid in generation"
    )
    reference_assets: list[str] = Field(
        default_factory=list,
        description="URLs of reference images/videos for style guidance"
    )
    visual_keywords: list[str] = Field(
        default_factory=list,
        description="Positive visual keywords to emphasize"
    )
    
    class Config:
        use_enum_values = True


class ShotPlan(BaseModel):
    """
    Structured plan for a single shot within a scene.
    Used when structured_plans feature flag is enabled.
    """
    shot_number: int = Field(description="Sequence number of this shot")
    shot_type: ShotType = Field(description="Type of camera shot")
    beat: BeatType = Field(description="Story beat this shot represents")
    duration_seconds: float = Field(description="Target duration of this shot")
    description: str = Field(description="Visual description of the shot")
    camera_movement: CameraMovement = Field(
        default=CameraMovement.STATIC,
        description="Camera movement for this shot"
    )
    characters_in_frame: list[str] = Field(
        default_factory=list,
        description="Characters visible in this shot"
    )
    reference_urls: list[str] = Field(
        default_factory=list,
        description="Reference images for this specific shot"
    )
    emotional_tone: str = Field(
        default="",
        description="Emotional tone of this shot"
    )
    
    class Config:
        use_enum_values = True


class ContinuityState(BaseModel):
    """
    State information passed between scenes for continuity.
    Stores the exit state of a scene to inform the next scene.
    """
    exit_frame_url: Optional[str] = Field(
        description="URL of the last frame of the scene"
    )
    character_positions: dict[str, str] = Field(
        default_factory=dict,
        description="Character ID to position description mapping"
    )
    lighting_description: str = Field(
        default="",
        description="Description of the lighting at scene end"
    )
    camera_state: str = Field(
        default="",
        description="Camera position/movement at scene end"
    )
    blocking_summary: str = Field(
        default="",
        description="Summary of character positions/blocking"
    )
    time_of_day: str = Field(
        default="",
        description="Time of day at scene end"
    )
    emotional_continuity: str = Field(
        default="",
        description="Emotional state to carry forward"
    )
    props_in_scene: list[str] = Field(
        default_factory=list,
        description="List of notable props visible"
    )


class DialogueTurn(BaseModel):
    """
    A single dialogue turn with timing information.
    Used when dialogue_audio feature flag is enabled.
    """
    character_id: str = Field(description="ID of speaking character")
    character_name: str = Field(description="Name of speaking character")
    text: str = Field(description="Dialogue text")
    emotion: str = Field(
        default="",
        description="Emotional quality of the delivery"
    )
    start_time_seconds: float = Field(
        description="When this dialogue starts in the scene"
    )
    end_time_seconds: float = Field(
        description="When this dialogue ends in the scene"
    )
    priority: int = Field(
        default=0,
        description="Priority for overlap handling (higher = more prominent)"
    )


class VoiceCast(BaseModel):
    """
    Voice assignment for a character with consent tracking.
    """
    character_id: str = Field(description="ID of the character")
    character_name: str = Field(description="Name of the character")
    voice_id: str = Field(
        description="ID of the voice model to use"
    )
    voice_description: str = Field(
        default="",
        description="Description of the voice characteristics"
    )
    consent_status: str = Field(
        default="pending",
        description="Consent status: granted, pending, denied"
    )
    consent_source: Optional[str] = Field(
        description="Source of consent (e.g., 'user', 'tos_accepted')"
    )
    language: str = Field(
        default="en-US",
        description="Language code for the voice"
    )


class TransitionPlan(BaseModel):
    """
    Planned transition between scenes.
    """
    transition_type: TransitionType = Field(
        description="Type of transition to use"
    )
    source_scene_number: int = Field(
        description="Scene number of the source scene"
    )
    target_scene_number: int = Field(
        description="Scene number of the target scene"
    )
    duration_seconds: float = Field(
        default=0.5,
        description="Duration of the transition"
    )
    rationale: str = Field(
        default="",
        description="Why this transition was chosen"
    )
    match_cut_subject: Optional[str] = Field(
        description="Subject to match for match cut"
    )
    
    class Config:
        use_enum_values = True


class ReferenceManifest(BaseModel):
    """
    Collection of references used in a scene with provenance.
    Tracks reference selection rationale for reproducibility.
    """
    reference_ids: list[str] = Field(
        description="IDs of selected references"
    )
    provenance: dict[str, str] = Field(
        default_factory=dict,
        description="Reference ID to source mapping (e.g., 'catalog', 'user_upload')"
    )
    selection_rationale: str = Field(
        default="",
        description="Why these references were selected"
    )
    continuity_score: Optional[float] = Field(
        description="AI-assessed continuity score (0-1)"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings about reference usage"
    )


class SceneContinuityContext(BaseModel):
    """
    Full continuity context for scene generation.
    Combines exit frame, references, and history.
    """
    previous_scene_exit: Optional[ContinuityState] = Field(
        description="Exit state from previous scene"
    )
    previous_episode_exit: Optional[ContinuityState] = Field(
        description="Exit state from last scene of previous episode"
    )
    character_references: list[str] = Field(
        default_factory=list,
        description="Character reference image URLs"
    )
    scene_references: list[str] = Field(
        default_factory=list,
        description="Scene reference image URLs"
    )
    reference_manifest: Optional[ReferenceManifest] = Field(
        description="Manifest of all references used"
    )
    continuity_check_passed: bool = Field(
        default=True,
        description="Whether automated continuity check passed"
    )
    continuity_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings from continuity analysis"
    )


class ScenePlan(BaseModel):
    """
    Complete scene plan with structured shots and dialogue.
    Used when structured_plans feature flag is enabled.
    """
    scene_number: int = Field(description="Sequence number of this scene")
    title: str = Field(description="Title of the scene")
    description: str = Field(description="Narrative description")
    duration_seconds: float = Field(description="Target duration")
    shots: list[ShotPlan] = Field(
        default_factory=list,
        description="Individual shot plans"
    )
    dialogue: list[DialogueTurn] = Field(
        default_factory=list,
        description="Dialogue turns with timing"
    )
    style_profile: StyleProfile = Field(
        description="Style guidance for this scene"
    )
    continuity: SceneContinuityContext = Field(
        description="Continuity context from previous scenes"
    )
    transition_from_previous: Optional[TransitionPlan] = Field(
        description="Transition from previous scene"
    )
