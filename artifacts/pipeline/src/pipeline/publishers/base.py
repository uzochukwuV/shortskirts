from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class PublishRequest:
    target_id: str
    platform: str
    media_url: str
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    privacy_status: str = "private"
    metadata: dict[str, Any] = field(default_factory=dict)
    access_token: str | None = None


@dataclass
class PublishResult:
    status: str
    platform_post_id: str | None = None
    public_url: str | None = None
    upload_session_id: str | None = None
    response: dict[str, Any] = field(default_factory=dict)


class Publisher(Protocol):
    async def publish(self, request: PublishRequest) -> PublishResult:
        ...

