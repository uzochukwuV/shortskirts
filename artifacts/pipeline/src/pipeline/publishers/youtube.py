from __future__ import annotations

import httpx

from storage.b2 import download_url_to_bytes

from .base import PublishRequest, PublishResult


class YouTubePublisher:
    async def publish(self, request: PublishRequest) -> PublishResult:
        if not request.access_token:
            raise RuntimeError("YouTube access token is required")

        video_bytes = await download_url_to_bytes(request.media_url)
        metadata = {
            "snippet": {
                "title": request.title,
                "description": request.description,
                "tags": request.tags,
            },
            "status": {
                "privacyStatus": request.privacy_status if request.privacy_status in {"private", "public", "unlisted"} else "private",
            },
        }
        headers = {
            "Authorization": f"Bearer {request.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(len(video_bytes)),
        }
        params = {"part": "snippet,status", "uploadType": "resumable"}
        async with httpx.AsyncClient(timeout=120) as client:
            init = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                params=params,
                headers=headers,
                json=metadata,
            )
            init.raise_for_status()
            upload_url = init.headers.get("location")
            if not upload_url:
                raise RuntimeError("YouTube did not return a resumable upload URL")

            upload = await client.put(
                upload_url,
                headers={"Content-Type": "video/mp4", "Content-Length": str(len(video_bytes))},
                content=video_bytes,
            )
            upload.raise_for_status()
            response = upload.json()

        video_id = response.get("id")
        return PublishResult(
            status="published",
            platform_post_id=video_id,
            public_url=f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
            upload_session_id=upload_url,
            response=response,
        )

