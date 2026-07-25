from __future__ import annotations

from .base import PublishRequest, PublishResult


class MockPublisher:
    async def publish(self, request: PublishRequest) -> PublishResult:
        post_id = f"mock-{request.target_id}"
        return PublishResult(
            status="published",
            platform_post_id=post_id,
            public_url=f"https://storyforge.local/published/{post_id}",
            response={
                "mock": True,
                "title": request.title,
                "media_url": request.media_url,
                "privacy_status": request.privacy_status,
            },
        )

