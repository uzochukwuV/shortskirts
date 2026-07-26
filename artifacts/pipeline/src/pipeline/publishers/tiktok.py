from __future__ import annotations

import httpx

from storage.b2 import download_url_to_bytes

from .base import PublishRequest, PublishResult


class TikTokPublisher:
    async def publish(self, request: PublishRequest) -> PublishResult:
        if not request.access_token:
            raise RuntimeError("TikTok access token is required")

        video_bytes = await download_url_to_bytes(request.media_url)
        post_mode = request.metadata.get("post_mode") or "DIRECT_POST"
        privacy = request.metadata.get("privacy_level") or "SELF_ONLY"
        init_payload = {
            "post_info": {
                "title": request.title,
                "description": request.description,
                "privacy_level": privacy,
                "disable_duet": bool(request.metadata.get("disable_duet", False)),
                "disable_comment": bool(request.metadata.get("disable_comment", False)),
                "disable_stitch": bool(request.metadata.get("disable_stitch", False)),
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": len(video_bytes),
                "chunk_size": len(video_bytes),
                "total_chunk_count": 1,
            },
        }
        headers = {
            "Authorization": f"Bearer {request.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        endpoint = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        if post_mode == "UPLOAD":
            endpoint = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"

        async with httpx.AsyncClient(timeout=120) as client:
            init = await client.post(endpoint, headers=headers, json=init_payload)
            init.raise_for_status()
            init_response = init.json()
            data = init_response.get("data") or {}
            upload_url = data.get("upload_url")
            publish_id = data.get("publish_id")
            if not upload_url or not publish_id:
                raise RuntimeError(f"TikTok did not return upload_url/publish_id: {init_response}")

            upload = await client.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(video_bytes)),
                    "Content-Range": f"bytes 0-{len(video_bytes) - 1}/{len(video_bytes)}",
                },
                content=video_bytes,
            )
            upload.raise_for_status()

        return PublishResult(
            status="processing",
            platform_post_id=publish_id,
            upload_session_id=upload_url,
            response=init_response,
        )

