from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    name: str
    schedule_type: str = Field(
        pattern="^(generate_only|publish_existing|generate_and_publish|series_continuation)$"
    )
    story_id: Optional[str] = None
    cadence: str = Field(default="once", pattern="^(once|interval_hours|daily|weekly)$")
    cadence_config: dict[str, Any] = Field(default_factory=dict)
    timezone: str = "UTC"
    next_run_at: Optional[datetime] = None
    enabled: bool = True
    pipeline_config: dict[str, Any] = Field(default_factory=dict)
    publish_config: dict[str, Any] = Field(default_factory=dict)
    approval_policy: str = Field(default="require_approval", pattern="^(require_approval|auto_publish|generate_only)$")


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cadence: Optional[str] = Field(default=None, pattern="^(once|interval_hours|daily|weekly)$")
    cadence_config: Optional[dict[str, Any]] = None
    timezone: Optional[str] = None
    next_run_at: Optional[datetime] = None
    enabled: Optional[bool] = None
    pipeline_config: Optional[dict[str, Any]] = None
    publish_config: Optional[dict[str, Any]] = None
    approval_policy: Optional[str] = Field(default=None, pattern="^(require_approval|auto_publish|generate_only)$")
    status: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: str
    story_id: Optional[str] = None
    name: str
    schedule_type: str
    cadence: str
    cadence_config: dict[str, Any] = Field(default_factory=dict)
    timezone: str
    next_run_at: Optional[datetime] = None
    enabled: bool
    pipeline_config: dict[str, Any] = Field(default_factory=dict)
    publish_config: dict[str, Any] = Field(default_factory=dict)
    approval_policy: str
    status: str
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ScheduledRunResponse(BaseModel):
    id: str
    schedule_id: Optional[str] = None
    story_id: Optional[str] = None
    episode_id: Optional[str] = None
    publish_target_id: Optional[str] = None
    job_id: Optional[str] = None
    run_type: str
    due_at: Optional[datetime] = None
    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ScheduleRunNowResponse(BaseModel):
    scheduled_run: ScheduledRunResponse

