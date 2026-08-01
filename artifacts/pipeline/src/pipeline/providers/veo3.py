"""
GenBlaze Veo 3 Provider

A custom GenBlaze provider adapter for Google Veo 3 via the Veo3API service.

This provider enables GenBlaze Pipeline API integration with:
- Video: veo3 (high quality), veo3-fast (fast generation)
- Image-to-video: via image_urls parameter
- Video extension: continue from previous video
- 1080P upscaling: free HD upgrade

API Docs: https://veo3api.com/docs
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
    route_images,
)
from genblaze_core.providers.base import BaseProvider

DEFAULT_BASE_URL = "https://veo3api.com"

# Default models
VEO3_MODEL = "veo3"
VEO3_FAST_MODEL = "veo3-fast"


def _map_veo3_error(status_code: int, response_text: str) -> ProviderErrorCode:
    """Map HTTP status codes to provider error codes."""
    if status_code == 401:
        return ProviderErrorCode.AUTH_FAILURE
    if status_code == 402:
        return ProviderErrorCode.RATE_LIMIT  # No credits
    if status_code == 429:
        return ProviderErrorCode.RATE_LIMIT
    if status_code >= 500:
        return ProviderErrorCode.TRANSIENT_FAILURE
    return ProviderErrorCode.UNKNOWN


class Veo3Base(BaseProvider):
    """Base class for Veo 3 providers."""
    
    discovery_support = DiscoverySupport.NONE

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        http_timeout: float = 120.0,
        models: ModelRegistry | None = None,
        retry_policy: RetryPolicy | None = None,
        poll_interval: float = 5.0,
    ):
        super().__init__(models=models, retry_policy=retry_policy)
        self._api_key = api_key or os.environ.get("VEO3_API_KEY")
        self._base_url = base_url or DEFAULT_BASE_URL
        self._http_timeout = http_timeout
        self._http_client: httpx.Client | None = None
        self._poll_interval = poll_interval
        self.poll_transient_retries = 60  # Allow up to 5 minutes of polling

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            if not self._api_key:
                raise ProviderError(
                    "No Veo 3 API key found. Set VEO3_API_KEY env var or pass api_key=.",
                    error_code=ProviderErrorCode.AUTH_FAILURE,
                )
            self._http_client = httpx.Client(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._http_timeout,
            )
        return self._http_client

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None


class Veo3VideoProvider(Veo3Base):
    """GenBlaze provider for Veo 3 video generation."""
    
    name = "veo3-video"

    @classmethod
    def create_registry(cls) -> ModelRegistry:
        veo3_family = ModelFamily(
            name="veo3",
            pattern=re.compile(r"^veo3(?:-\S+)?$"),
            spec_template=ModelSpec(
                model_id="*",
                modality=Modality.VIDEO,
                input_mapping=route_images(slots=("image_urls",)),
            ),
            description="Google Veo 3 video generation",
            example_slugs=("veo3", "veo3-fast"),
        )
        
        return ModelRegistry(provider_families=(veo3_family,))

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modalities=[Modality.VIDEO],
            supported_inputs=["text", "image"],
            accepts_chain_input=True,
            output_formats=["video/mp4"],
        )

    def submit(self, step: Step, config: RunnableConfig | None = None) -> Any:
        """Submit video generation request."""
        try:
            payload = self._build_video_payload(step)
            
            client = self._get_http_client()
            resp = client.post("/generate", json=payload)
            
            if resp.status_code >= 400:
                error_text = resp.text[:500]
                raise ProviderError(
                    f"Veo 3 submit failed ({resp.status_code}): {error_text}",
                    error_code=_map_veo3_error(resp.status_code, resp.text),
                )
            
            data = resp.json()
            
            # Check API-level response
            if data.get("code") != 200:
                raise ProviderError(
                    f"Veo 3 API error: {data.get('message', 'Unknown error')}",
                    error_code=ProviderErrorCode.UNKNOWN,
                )
            
            task_id = data.get("data", {}).get("task_id")
            if not task_id:
                raise ProviderError(f"Veo 3 submit succeeded but no task_id: {data}")
            
            print(f"[veo3] Video task submitted: {task_id}")
            return task_id
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"Veo 3 video submit failed: {exc}",
                error_code=ProviderErrorCode.UNKNOWN,
            ) from exc

    def _build_video_payload(self, step: Step) -> dict:
        """Build Veo 3 video payload."""
        model = step.model or VEO3_FAST_MODEL
        prompt = step.prompt or ""
        images = step.inputs or []
        
        payload: dict = {
            "prompt": prompt,
            "model": model,
            "watermark": "veo",
        }
        
        # Add aspect ratio from params
        ratio = step.params.get("aspect_ratio") or step.params.get("ratio") or "16:9"
        if ratio == "9:16":
            payload["aspect_ratio"] = "9:16"
        elif ratio == "1:1":
            payload["aspect_ratio"] = "1:1"
        else:
            payload["aspect_ratio"] = "16:9"
        
        # Add seed if specified
        seed = step.params.get("seed")
        if seed is not None:
            payload["seeds"] = seed
        
        # Add image URLs for image-to-video
        if images:
            image_urls = []
            for img in images:
                if hasattr(img, 'url'):
                    image_urls.append(img.url)
                else:
                    image_urls.append(str(img))
            if image_urls:
                payload["image_urls"] = image_urls
        
        return payload

    def poll(self, prediction_id: Any, config: RunnableConfig | None = None) -> bool:
        """Poll for task completion."""
        if isinstance(prediction_id, dict):
            # Prediction ID might be a dict with status
            status = prediction_id.get("status", "")
            return status in ("COMPLETED", "FAILED")
        
        task_id = prediction_id
        client = self._get_http_client()
        
        try:
            resp = client.get(f"/feed?task_id={task_id}")
            
            if resp.status_code >= 400:
                return False
            
            data = resp.json()
            status = data.get("data", {}).get("status", "")
            
            return status in ("COMPLETED", "FAILED")
            
        except Exception:
            return False

    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Fetch the generated video."""
        try:
            task_id = prediction_id
            if isinstance(prediction_id, dict):
                task_id = prediction_id.get("task_id", prediction_id.get("id"))
            
            client = self._get_http_client()
            resp = client.get(f"/feed?task_id={task_id}")
            
            if resp.status_code >= 400:
                raise ProviderError(
                    f"Veo 3 fetch failed ({resp.status_code}): {resp.text[:200]}",
                    error_code=_map_veo3_error(resp.status_code, resp.text),
                )
            
            data = resp.json()
            result = data.get("data", {})
            status = result.get("status", "")
            
            if status == "FAILED":
                raise ProviderError("Veo 3 video generation failed")
            
            if status != "COMPLETED":
                raise ProviderError(f"Veo 3 video task not complete: {status}")
            
            # Extract video URL
            video_urls = result.get("response", [])
            video_url = video_urls[0] if video_urls else None
            
            if not video_url:
                raise ProviderError(f"Veo 3 video task succeeded but no video URL: {result}")
            
            asset = Asset(url=str(video_url), media_type="video/mp4")
            asset.video = VideoMetadata(has_audio=False)
            
            step.assets.append(asset)
            step.provider_payload = {"veo3": {"task_id": task_id}}
            
            return step
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"Veo 3 video fetch_output failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)

    def _poll_status(self, task_id: str) -> str:
        """Poll status and return status string."""
        client = self._get_http_client()
        
        resp = client.get(f"/feed?task_id={task_id}")
        
        if resp.status_code >= 400:
            return "FAILED"
        
        data = resp.json()
        status = data.get("data", {}).get("status", "")
        
        return status or "PROCESSING"

    def extend_video(self, task_id: str, prompt: str, seed: int | None = None) -> str:
        """Extend an existing video with a new prompt."""
        client = self._get_http_client()
        
        payload: dict = {
            "task_id": task_id,
            "prompt": prompt,
            "watermark": "veo",
        }
        
        if seed is not None:
            payload["seeds"] = seed
        
        resp = client.post("/extend", json=payload)
        
        if resp.status_code >= 400:
            raise ProviderError(
                f"Veo 3 extend failed ({resp.status_code}): {resp.text[:200]}",
                error_code=_map_veo3_error(resp.status_code, resp.text),
            )
        
        data = resp.json()
        
        if data.get("code") != 200:
            raise ProviderError(
                f"Veo 3 extend API error: {data.get('message', 'Unknown error')}",
                error_code=ProviderErrorCode.UNKNOWN,
            )
        
        new_task_id = data.get("data", {}).get("task_id")
        print(f"[veo3] Video extended: {task_id} -> {new_task_id}")
        return new_task_id

    def get_1080p(self, task_id: str) -> str:
        """Get 1080P version of a video (free)."""
        client = self._get_http_client()
        
        resp = client.get(f"/get-1080p?task_id={task_id}")
        
        if resp.status_code >= 400:
            raise ProviderError(
                f"Veo 3 1080P failed ({resp.status_code}): {resp.text[:200]}",
                error_code=_map_veo3_error(resp.status_code, resp.text),
            )
        
        data = resp.json()
        
        if data.get("code") != 200:
            raise ProviderError(
                f"Veo 3 1080P API error: {data.get('message', 'Unknown error')}",
                error_code=ProviderErrorCode.UNKNOWN,
            )
        
        result_url = data.get("data", {}).get("result_url")
        print(f"[veo3] 1080P video: {result_url}")
        return result_url


# Type alias for RunnableConfig
RunnableConfig = Any
