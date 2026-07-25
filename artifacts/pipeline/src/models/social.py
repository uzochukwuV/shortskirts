from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SocialAccountResponse(BaseModel):
    id: str
    platform: str
    platform_user_id: Optional[str] = None
    display_name: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    status: str = "connected"
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SocialAccountMockCreate(BaseModel):
    platform: str = Field(pattern="^(mock|youtube|tiktok)$")
    platform_user_id: Optional[str] = None
    display_name: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class PublishTargetCreate(BaseModel):
    platform: str = Field(pattern="^(mock|youtube|tiktok)$")
    social_account_id: Optional[str] = None
    story_id: Optional[str] = None
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    artifact_id: Optional[str] = None
    asset_kind: str = Field(default="episode", pattern="^(episode|scene|artifact|external_url)$")
    media_url: Optional[str] = None
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    privacy_status: str = "private"
    publish_mode: str = Field(default="manual", pattern="^(manual|scheduled|auto_after_generation)$")
    requires_approval: bool = True
    scheduled_for: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublishTargetResponse(BaseModel):
    id: str
    platform: str
    social_account_id: Optional[str] = None
    story_id: Optional[str] = None
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    artifact_id: Optional[str] = None
    asset_kind: str
    media_url: Optional[str] = None
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    privacy_status: str
    publish_mode: str
    requires_approval: bool
    approved_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    status: str
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PublishPostResponse(BaseModel):
    id: str
    publish_target_id: str
    platform: str
    platform_post_id: Optional[str] = None
    public_url: Optional[str] = None
    upload_session_id: Optional[str] = None
    status: str
    response: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PublishTargetDetailResponse(PublishTargetResponse):
    posts: list[PublishPostResponse] = Field(default_factory=list)

