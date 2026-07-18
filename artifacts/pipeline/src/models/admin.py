from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminProfileResponse(BaseModel):
    email: str
    role: str = "admin"


class AdminAuthResponse(BaseModel):
    token: str
    admin: AdminProfileResponse


class AdminStorySummary(BaseModel):
    id: str
    title: str
    status: str
    approval_status: str
    workflow_type: str
    workflow_version: Optional[str] = None
    generation_version: Optional[str] = None
    episode_count: int = 0
    completed_episode_count: int = 0
    failed_episode_count: int = 0
    job_count: int = 0
    failed_job_count: int = 0
    updated_at: datetime
    created_at: datetime


class AdminUserSummary(BaseModel):
    id: str
    email: str
    created_at: datetime
    updated_at: datetime
    story_count: int = 0
    draft_story_count: int = 0
    approved_story_count: int = 0
    generating_story_count: int = 0
    checkpoint_story_count: int = 0
    completed_story_count: int = 0
    failed_story_count: int = 0
    total_job_count: int = 0
    completed_job_count: int = 0
    failed_job_count: int = 0
    last_activity_at: Optional[datetime] = None
    last_story_title: Optional[str] = None
    last_story_status: Optional[str] = None


class AdminActivityItem(BaseModel):
    kind: str
    id: str
    title: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class AdminMetricPoint(BaseModel):
    day: str
    count: int


class AdminOverviewResponse(BaseModel):
    totals: dict
    story_status_breakdown: list[dict]
    job_status_breakdown: list[dict]
    daily_activity: list[AdminMetricPoint]
    provider_costs: dict
    provider_latency: dict
    top_failure_steps: list[dict]
    recent_failures: list[dict]


class AdminUserDetailResponse(BaseModel):
    user: AdminUserSummary
    stories: list[AdminStorySummary]
    recent_jobs: list[dict]
    recent_activity: list[AdminActivityItem]
