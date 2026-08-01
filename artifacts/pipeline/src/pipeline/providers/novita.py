"""
Novita AI Provider for GenBlaze

Novita AI provides access to various video generation models including:
- Wan 2.7 T2V (Text-to-Video)
- Wan 2.7 I2V (Image-to-Video)
- Wan 2.7 R2V (Reference-to-Video)
- Wan 2.7 Video Editing

API Docs: https://novita.ai/docs/api-reference/model-apis-wan2.7-t2v

Note: Requires NOVITA_API_KEY in environment.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx

from genblaze_core.exceptions import ProviderError
from genblaze_core.models.asset import Asset, VideoMetadata
from genblaze_core.models.enums import Modality, ProviderErrorCode
from genblaze_core.models.step import Step
from genblaze_core.providers import (
    DiscoverySupport,
    ModelFamily,
    ModelRegistry,
    ModelSpec,
    ProviderCapabilities,
    RetryPolicy,
)
from genblaze_core.providers.base import BaseProvider


DEFAULT_BASE_URL = "https://api.novita.ai"

# Novita API endpoints
WAN_T2V_ENDPOINT = "/v3/async/wan2.7-t2v"
WAN_I2V_ENDPOINT = "/v3/async/wan2.7-i2v"
WAN_R2V_ENDPOINT = "/v3/async/wan2.7-r2v"
WAN_VIDEO_EDIT_ENDPOINT = "/v3/async/wan2.7-videoedit"
TASK_RESULT_ENDPOINT = "/v3/async/task-result"
BALANCE_ENDPOINT = "/v3/user/balance"


class NovitaVideoMode:
    """Video generation modes supported by Novita."""
    T2V = "t2v"  # Text-to-Video
    I2V = "i2v"  # Image-to-Video
    R2V = "r2v"  # Reference-to-Video (character appearance + motion)
    VIDEO_EDIT = "videoedit"  # Video editing


def _map_novita_error(code: int, message: str) -> ProviderErrorCode:
    """Map Novita error codes to provider error codes."""
    if code == 401 or code == 403:
        if "auth" in message.lower() or "token" in message.lower():
            return ProviderErrorCode.AUTH_FAILURE
        return ProviderErrorCode.RATE_LIMIT  # Insufficient balance
    if code == 429:
        return ProviderErrorCode.RATE_LIMIT
    if code >= 500:
        return ProviderErrorCode.TRANSIENT_FAILURE
    return ProviderErrorCode.UNKNOWN


class NovitaVideoProvider(BaseProvider):
    """
    GenBlaze provider for Novita AI Video Generation API.
    
    Supports Wan 2.7 models for:
    - Text-to-Video (T2V)
    - Image-to-Video (I2V) 
    - Reference-to-Video (R2V) - character consistency
    - Video Editing
    """
    
    name = "novita-video"
    discovery_support = DiscoverySupport.NONE

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        http_timeout: float = 300.0,
        models: ModelRegistry | None = None,
        retry_policy: RetryPolicy | None = None,
        poll_interval: float = 5.0,
    ):
        super().__init__(models=models, retry_policy=retry_policy)
        self._api_key = api_key or os.environ.get("NOVITA_API_KEY")
        self._base_url = base_url or DEFAULT_BASE_URL
        self._http_timeout = http_timeout
        self._http_client: httpx.Client | None = None
        self._poll_interval = poll_interval

    def _get_headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError(
                "No Novita API key found. Set NOVITA_API_KEY env var.",
                error_code=ProviderErrorCode.AUTH_FAILURE,
            )
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                base_url=self._base_url,
                headers=self._get_headers(),
                timeout=self._http_timeout,
            )
        return self._http_client

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    @classmethod
    def create_registry(cls) -> ModelRegistry:
        """Create model registry for Novita."""
        video_family = ModelFamily(
            name="novita-video",
            pattern=re.compile(r"^.*wan.*video.*$", re.IGNORECASE),
            spec_template=ModelSpec(
                model_id="wan2.7-t2v",
                modality=Modality.VIDEO,
                input_mapping={},  # Will be handled per-mode
            ),
            description="Novita Wan 2.7 video generation models",
            example_slugs=("wan2.7-t2v", "wan2.7-i2v", "wan2.7-r2v"),
        )
        
        return ModelRegistry(provider_families=(video_family,))

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modalities=[Modality.VIDEO],
            supported_inputs=["text", "image", "video"],
            accepts_chain_input=True,
            output_formats=["video/mp4"],
        )

    def get_balance(self) -> dict[str, Any]:
        """Get account balance info.
        
        Note: The /v3/user/balance endpoint may not work for all accounts.
        This is informational only - the provider doesn't require balance checks.
        """
        client = self._get_client()
        
        try:
            resp = client.get(BALANCE_ENDPOINT)
            
            if resp.status_code >= 400:
                data = resp.json()
                # Check if it's a fusion model error (common with new accounts)
                if data.get("reason") == "FUSION_MODEL_NOT_FOUND":
                    return {"status": "unknown", "message": "Balance API not available"}
                return {"error": data.get("message", "Failed to get balance")}
            
            return resp.json()
        except Exception as e:
            return {"status": "unknown", "message": str(e)}

    def submit(self, step: Step, config: Any | None = None) -> str:
        """
        Submit a video generation task.
        
        Supports:
        - T2V: Text-to-Video (default)
        - I2V: Image-to-Video (when step.inputs contains images)
        - R2V: Reference-to-Video (when step.params['mode'] = 'r2v')
        """
        prompt = step.prompt or ""
        
        if not prompt:
            raise ProviderError("No prompt provided for video generation")
        
        # Determine generation mode
        mode = step.params.get("mode", "t2v") if step.params else "t2v"
        images = step.inputs or []
        
        # Build endpoint and payload based on mode
        if mode == "r2v":
            endpoint = WAN_R2V_ENDPOINT
            payload = self._build_r2v_payload(prompt, images, step.params or {})
        elif mode == "i2v" and images:
            endpoint = WAN_I2V_ENDPOINT
            payload = self._build_i2v_payload(prompt, images, step.params or {})
        elif mode == "videoedit":
            endpoint = WAN_VIDEO_EDIT_ENDPOINT
            payload = self._build_videoedit_payload(prompt, images, step.params or {})
        else:
            endpoint = WAN_T2V_ENDPOINT
            payload = self._build_t2v_payload(prompt, step.params or {})
        
        client = self._get_client()
        
        try:
            resp = client.post(endpoint, json=payload)
            
            if resp.status_code >= 400:
                data = resp.json()
                error_msg = data.get("message", data.get("reason", "Unknown error"))
                error_code = _map_novita_error(resp.status_code, error_msg)
                raise ProviderError(
                    f"Novita submit failed ({resp.status_code}): {error_msg}",
                    error_code=error_code,
                )
            
            data = resp.json()
            
            task_id = data.get("task_id")
            if not task_id:
                raise ProviderError(f"No task_id in response: {data}")
            
            print(f"[novita] Task created: {task_id}")
            return task_id
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"Novita submit failed: {exc}",
                error_code=ProviderErrorCode.UNKNOWN,
            ) from exc

    def _build_t2v_payload(self, prompt: str, params: dict) -> dict:
        """Build T2V request payload."""
        payload = {
            "prompt": prompt,
            "size": params.get("size", "1920*1080"),
            "duration": params.get("duration", 5),
            "watermark": params.get("watermark", False),
            "prompt_extend": params.get("prompt_extend", True),
        }
        
        if params.get("seed"):
            payload["seed"] = params["seed"]
        
        if params.get("negative_prompt"):
            payload["negative_prompt"] = params["negative_prompt"]
        
        if params.get("audio_url"):
            payload["audio_url"] = params["audio_url"]
        
        return payload

    def _build_i2v_payload(self, prompt: str, images: list, params: dict) -> dict:
        """Build I2V (Image-to-Video) request payload."""
        payload = self._build_t2v_payload(prompt, params)
        
        # Add image as first frame
        image_url = self._get_image_url(images)
        if image_url:
            payload["image_url"] = image_url
        
        return payload

    def _build_r2v_payload(self, prompt: str, images: list, params: dict) -> dict:
        """Build R2V (Reference-to-Video) request payload.
        
        R2V uses reference images/videos for character appearance,
        motion, and voice cloning.
        """
        payload = {
            "prompt": prompt,
            "size": params.get("size", "1920*1080"),
            "duration": params.get("duration", 5),
            "watermark": params.get("watermark", False),
            "shot_type": params.get("shot_type", "single"),
            "audio": params.get("audio", True),
        }
        
        if params.get("seed"):
            payload["seed"] = params["seed"]
        
        if params.get("negative_prompt"):
            payload["negative_prompt"] = params["negative_prompt"]
        
        # Add reference media
        media = []
        for idx, img in enumerate(images[:5]):  # Max 5 media items
            media_url = self._get_image_url([img]) or (img.url if hasattr(img, 'url') else None)
            if media_url:
                media.append({
                    "url": media_url,
                    "type": params.get(f"media_{idx}_type", "reference_image"),
                })
        
        if media:
            payload["media"] = media
        
        return payload

    def _build_videoedit_payload(self, prompt: str, videos: list, params: dict) -> dict:
        """Build video editing request payload."""
        payload = {
            "prompt": prompt,
            "size": params.get("size", "1920*1080"),
            "watermark": params.get("watermark", False),
        }
        
        # Add video input
        if videos:
            video_url = self._get_video_url(videos)
            if video_url:
                payload["video_url"] = video_url
        
        return payload

    def _get_image_url(self, assets: list) -> str | None:
        """Extract image URL from assets."""
        for asset in assets:
            if hasattr(asset, 'url') and asset.url:
                return asset.url
            elif isinstance(asset, dict) and asset.get('url'):
                return asset['url']
        return None

    def _get_video_url(self, assets: list) -> str | None:
        """Extract video URL from assets."""
        for asset in assets:
            url = None
            if hasattr(asset, 'url'):
                url = asset.url
            elif isinstance(asset, dict):
                url = asset.get('url')
            
            if url and any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi', '.webm']):
                return url
        return None

    def poll(self, task_id: str | dict, config: Any | None = None) -> bool:
        """Poll for task completion."""
        if isinstance(task_id, dict):
            status = task_id.get("status", "")
            return status in ("TASK_STATUS_SUCCEED", "TASK_STATUS_FAILED", "TASK_STATUS_CANCELLED")
        
        client = self._get_client()
        
        try:
            resp = client.get(
                TASK_RESULT_ENDPOINT,
                params={"task_id": task_id},
            )
            
            if resp.status_code >= 400:
                return False
            
            data = resp.json()
            status = data.get("task", {}).get("status", "")
            
            print(f"[novita] Task {task_id}: {status}")
            
            return status in ("TASK_STATUS_SUCCEED", "TASK_STATUS_FAILED", "TASK_STATUS_CANCELLED")
            
        except Exception:
            return False

    def fetch_output(self, task_id: str | dict, step: Step) -> Step:
        """Fetch task output."""
        if isinstance(task_id, dict):
            result = task_id
            task_id = result.get("task_id", str(task_id))
        else:
            # Fetch task result
            client = self._get_client()
            resp = client.get(
                TASK_RESULT_ENDPOINT,
                params={"task_id": task_id},
            )
            
            if resp.status_code >= 400:
                raise ProviderError(
                    f"Novita fetch failed ({resp.status_code}): {resp.text[:200]}",
                    error_code=_map_novita_error(resp.status_code, resp.text),
                )
            
            result = resp.json()
        
        # Handle both nested and flat response formats
        task_info = result.get("task", result)  # Fallback to result itself
        status = task_info.get("status", "")
        
        if status == "TASK_STATUS_FAILED":
            error = task_info.get("reason", "Unknown error")
            raise ProviderError(f"Novita task failed: {error}")
        
        if status == "TASK_STATUS_CANCELLED":
            raise ProviderError("Novita task was cancelled")
        
        if status != "TASK_STATUS_SUCCEED":
            raise ProviderError(f"Novita task not complete: {status}")
        
        # Get video URL from result (check both locations)
        videos = result.get("videos", task_info.get("videos", []))
        
        if not videos:
            raise ProviderError("No video in task result")
        
        video_data = videos[0]
        video_url = video_data.get("video_url")
        video_type = video_data.get("video_type", "mp4")
        
        if not video_url:
            raise ProviderError("No video URL in task result")
        
        # Check for audio (videos may have audio embedded)
        has_audio = bool(result.get("audios")) or video_type == "mp4"
        
        # Create asset
        asset = Asset(
            url=video_url,
            media_type=f"video/{video_type}",
        )
        asset.video = VideoMetadata(has_audio=has_audio)
        
        step.assets.append(asset)
        step.provider_payload = {
            "novita": {
                "task_id": task_id,
                "status": status,
                "task_type": task_info.get("task_type"),
                "duration": video_data.get("duration"),
            }
        }
        
        return step

    def _poll_task(self, task_id: str, max_wait: int = 600) -> dict:
        """Poll until task completes."""
        start = time.time()
        
        while time.time() - start < max_wait:
            client = self._get_client()
            
            resp = client.get(
                TASK_RESULT_ENDPOINT,
                params={"task_id": task_id},
            )
            
            if resp.status_code >= 400:
                raise ProviderError(f"Polling failed: {resp.status_code}")
            
            data = resp.json()
            task_info = data.get("task", {})
            status = task_info.get("status", "")
            
            print(f"[novita] Status: {status} ({int(time.time() - start)}s)")
            
            if status == "TASK_STATUS_SUCCEED":
                return data
            elif status in ("TASK_STATUS_FAILED", "TASK_STATUS_CANCELLED"):
                error = task_info.get("reason", "Unknown")
                raise ProviderError(f"Task {status}: {error}")
            
            # Show progress if available
            progress = task_info.get("progress_percent")
            if progress:
                print(f"[novita] Progress: {progress}%")
            
            time.sleep(self._poll_interval)
        
        raise ProviderError(f"Timeout waiting for task after {max_wait}s")

    # GenBlaze compatibility methods
    def generate(self, step: Step) -> Step:
        """Generate video (sync wrapper)."""
        task_id = self.submit(step)
        
        # Poll for completion
        self._poll_task(task_id)
        
        # Fetch result
        return self.fetch_output(task_id, step)

    def status(self, task_id: str) -> str:
        """Get task status."""
        client = self._get_client()
        resp = client.get(
            TASK_RESULT_ENDPOINT,
            params={"task_id": task_id},
        )
        
        if resp.status_code >= 400:
            return "ERROR"
        
        data = resp.json()
        return data.get("task", {}).get("status", "UNKNOWN")

    def get_video(self, task_id: str) -> str:
        """Get video URL for completed task."""
        client = self._get_client()
        resp = client.get(
            TASK_RESULT_ENDPOINT,
            params={"task_id": task_id},
        )
        
        if resp.status_code >= 400:
            raise ProviderError(f"Failed to get video: {resp.status_code}")
        
        data = resp.json()
        task_info = data.get("task", {})
        
        if task_info.get("status") != "TASK_STATUS_SUCCEED":
            raise ProviderError(f"Task not complete: {task_info.get('status')}")
        
        videos = task_info.get("videos", [])
        if not videos:
            raise ProviderError("No video in result")
        
        return videos[0].get("video_url")
