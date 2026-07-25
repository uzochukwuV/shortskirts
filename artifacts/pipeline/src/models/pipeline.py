from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


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
