"""
GenBlaze DashScope/Qwen Provider

A custom GenBlaze provider adapter for Alibaba DashScope API (Qwen/Wan video and image models).

This provider enables GenBlaze Pipeline API integration with:
- Video: wan2.7-i2v, wan2.7-t2v, wan2.7-r2v, happyhorse models
- Image: qwen-image, wanx2.1-t2i-turbo, wan2.7-image-pro

Usage:
    from pipeline.providers.dashscope import DashScopeVideoProvider, DashScopeImageProvider
    
    # Video generation
    provider = DashScopeVideoProvider()
    result = (
        Pipeline("my-video")
        .step(provider, model="wan2.7-t2v", prompt="A cat playing piano", modality=Modality.VIDEO)
        .run(timeout=600)
    )
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


# Default DashScope API base URL
DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/api/v1"


def _classify_capability(model: str, reference_images: list | None = None) -> str:
    """Determine the DashScope capability based on model and inputs."""
    if not reference_images:
        return "t2v"
    if len(reference_images) >= 2:
        return "r2v"
    return "i2v"


def _map_dashscope_error(status_code: int, response_text: str) -> ProviderErrorCode:
    """Map DashScope HTTP errors to GenBlaze error codes."""
    if status_code == 401 or status_code == 403:
        return ProviderErrorCode.AUTH_FAILURE
    if status_code == 429:
        return ProviderErrorCode.RATE_LIMIT
    if status_code >= 500:
        return ProviderErrorCode.TRANSIENT_FAILURE
    return ProviderErrorCode.UNKNOWN


class DashScopeBase(BaseProvider):
    """Base class for DashScope/Qwen providers.
    
    Handles authentication, HTTP client, and common request handling
    for DashScope API.
    """
    
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
        super().__init__(
            models=models,
            retry_policy=retry_policy,
        )
        self._api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self._base_url = base_url or os.environ.get("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL
        self._http_timeout = http_timeout
        self._http_client: httpx.Client | None = None
        self._poll_interval = poll_interval
        self.poll_transient_retries = 10

    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client with auth."""
        if self._http_client is None:
            if not self._api_key:
                raise ProviderError(
                    "No DashScope API key found. Set DASHSCOPE_API_KEY env var or pass api_key=.",
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
        """Close HTTP client."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def _submit_video_request(self, model: str, payload: dict) -> str:
        """Submit a video generation request and return task_id."""
        client = self._get_http_client()
        endpoint = "/services/aigc/video-generation/video-synthesis"
        
        resp = client.post(endpoint, json=payload)
        if resp.status_code >= 400:
            error_text = resp.text[:500]
            raise ProviderError(
                f"DashScope video submit failed ({resp.status_code}): {error_text}",
                error_code=_map_dashscope_error(resp.status_code, resp.text),
            )
        
        data = resp.json()
        output = data.get("output", {})
        task_id = output.get("task_id")
        if not task_id:
            raise ProviderError(f"DashScope submit succeeded but no task_id: {data}")
        
        return task_id

    def _submit_image_request(self, model: str, payload: dict) -> str:
        """Submit an image generation request and return task_id."""
        client = self._get_http_client()
        endpoint = "/services/aigc/multimodal-generation/generation"
        
        resp = client.post(endpoint, json=payload)
        if resp.status_code >= 400:
            error_text = resp.text[:500]
            raise ProviderError(
                f"DashScope image submit failed ({resp.status_code}): {error_text}",
                error_code=_map_dashscope_error(resp.status_code, resp.text),
            )
        
        data = resp.json()
        output = data.get("output", {})
        task_id = output.get("task_id")
        if not task_id:
            raise ProviderError(f"DashScope submit succeeded but no task_id: {data}")
        
        return task_id

    def _poll_video_status(self, task_id: str, timeout: int = 600) -> dict:
        """Poll video task status until completion."""
        client = self._get_http_client()
        endpoint = "/services/aigc/video-generation/video-synthesis"
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                resp = client.get(endpoint, params={"task_id": task_id})
                if resp.status_code >= 400:
                    raise ProviderError(
                        f"DashScope poll failed ({resp.status_code}): {resp.text[:200]}",
                        error_code=_map_dashscope_error(resp.status_code, resp.text),
                    )
                
                data = resp.json()
                output = data.get("output", {})
                status = output.get("task_status", "").upper()
                
                if status in ("SUCCEEDED", "SUCCESS"):
                    return output
                elif status in ("FAILED", "CANCELLED", "CANCELED"):
                    error_msg = output.get("message") or output.get("error") or status
                    raise ProviderError(
                        f"DashScope video task {status}: {error_msg}",
                        error_code=ProviderErrorCode.UNKNOWN,
                    )
                
                time.sleep(self._poll_interval)
                
            except ProviderError:
                raise
            except Exception:
                time.sleep(self._poll_interval)
        
        raise ProviderError(
            f"DashScope video task {task_id} timed out after {timeout}s",
            error_code=ProviderErrorCode.TIMEOUT,
        )

    def _poll_image_status(self, task_id: str, timeout: int = 120) -> dict:
        """Poll image task status until completion."""
        client = self._get_http_client()
        endpoint = "/services/aigc/multimodal-generation/generation"
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                resp = client.get(endpoint, params={"task_id": task_id})
                if resp.status_code >= 400:
                    raise ProviderError(
                        f"DashScope poll failed ({resp.status_code}): {resp.text[:200]}",
                        error_code=_map_dashscope_error(resp.status_code, resp.text),
                    )
                
                data = resp.json()
                output = data.get("output", {})
                status = output.get("task_status", "").upper()
                
                if status in ("SUCCEEDED", "SUCCESS"):
                    return output
                elif status in ("FAILED", "CANCELLED", "CANCELED"):
                    error_msg = output.get("message") or output.get("error") or status
                    raise ProviderError(
                        f"DashScope image task {status}: {error_msg}",
                        error_code=ProviderErrorCode.UNKNOWN,
                    )
                
                time.sleep(5)
                
            except ProviderError:
                raise
            except Exception:
                time.sleep(5)
        
        raise ProviderError(
            f"DashScope image task {task_id} timed out after {timeout}s",
            error_code=ProviderErrorCode.TIMEOUT,
        )


class DashScopeVideoProvider(DashScopeBase):
    """GenBlaze provider for DashScope/Qwen video generation.
    
    Supports:
    - Text-to-Video (t2v): wan2.7-t2v, happyhorse-1.1-t2v
    - Image-to-Video (i2v): wan2.7-i2v, happyhorse-1.1-i2v
    - Reference-to-Video (r2v): wan2.7-r2v, happyhorse-1.1-r2v
    
    Args:
        api_key: DashScope API key. Falls back to DASHSCOPE_API_KEY env var.
        base_url: DashScope API base URL. Defaults to https://dashscope-intl.aliyuncs.com/api/v1
        http_timeout: HTTP request timeout in seconds (default 120).
        models: Optional custom ModelRegistry.
    """
    
    name = "dashscope-video"

    @classmethod
    def create_registry(cls) -> ModelRegistry:
        """Create the DashScope video model registry."""
        
        # Wan family
        wan_family = ModelFamily(
            name="dashscope-wan",
            pattern=re.compile(r"^wan\d+\.\d+-(?:t2v|i2v|r2v)$"),
            spec_template=ModelSpec(
                model_id="*",
                modality=Modality.VIDEO,
                input_mapping=route_images(slots=("image_url",)),
            ),
            description="Alibaba Wan video family",
            example_slugs=("wan2.7-t2v", "wan2.7-i2v", "wan2.7-r2v"),
        )
        
        # HappyHorse family
        happyhorse_family = ModelFamily(
            name="dashscope-happyhorse",
            pattern=re.compile(r"^happyhorse-\d+\.\d+-(?:t2v|i2v|r2v)$"),
            spec_template=ModelSpec(
                model_id="*",
                modality=Modality.VIDEO,
                input_mapping=route_images(slots=("image_url",)),
            ),
            description="HappyHorse video family",
            example_slugs=("happyhorse-1.1-t2v", "happyhorse-1.1-i2v", "happyhorse-1.1-r2v"),
        )
        
        return ModelRegistry(
            provider_families=(wan_family, happyhorse_family),
        )

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
            task_id = self._submit_video_request(step.model, payload)
            return task_id
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"DashScope video submit failed: {exc}",
                error_code=ProviderErrorCode.UNKNOWN,
            ) from exc

    def _build_video_payload(self, step: Step) -> dict:
        """Build DashScope video payload from step."""
        model = step.model
        prompt = step.prompt or ""
        images = step.inputs or []
        capability = _classify_capability(model, images)
        
        payload: dict = {
            "model": model,
            "input": {"prompt": prompt},
            "parameters": {
                "duration": step.params.get("duration", 5),
                "resolution": step.params.get("resolution", "720p"),
            }
        }
        
        if capability in ("i2v", "r2v") and images:
            if capability == "r2v" and len(images) >= 2:
                payload["input"]["images"] = images[:2]
            else:
                payload["input"]["images"] = images[:1]
        
        return payload

    def poll(self, prediction_id: Any, config: RunnableConfig | None = None) -> bool:
        """Poll video task status."""
        try:
            output = self._poll_video_status(prediction_id)
            status = output.get("task_status", "").upper()
            return status in ("SUCCEEDED", "SUCCESS")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope video poll failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)

    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Fetch video generation result."""
        try:
            output = self._poll_video_status(prediction_id)
            
            video_url = (
                output.get("video_url") 
                or output.get("video", {}).get("url")
                or (output.get("results", [{}])[0].get("url") if output.get("results") else None)
            )
            
            if not video_url:
                raise ProviderError(f"DashScope video task succeeded but no video_url: {output}")
            
            asset = Asset(url=str(video_url), media_type="video/mp4")
            asset.video = VideoMetadata(has_audio=False)
            
            step.assets.append(asset)
            step.provider_payload = {"dashscope": {"task_id": prediction_id}}
            
            return step
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope video fetch_output failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)


class DashScopeImageProvider(DashScopeBase):
    """GenBlaze provider for DashScope/Qwen image generation.
    
    Supports: qwen-image-plus, wanx2.1-t2i-turbo, wan2.7-image-pro, etc.
    
    Args:
        api_key: DashScope API key. Falls back to DASHSCOPE_API_KEY env var.
        base_url: DashScope API base URL.
        http_timeout: HTTP request timeout in seconds (default 120).
        models: Optional custom ModelRegistry.
    """
    
    name = "dashscope-image"

    @classmethod
    def create_registry(cls) -> ModelRegistry:
        """Create the DashScope image model registry."""
        
        image_family = ModelFamily(
            name="dashscope-image",
            pattern=re.compile(r"^(?:qwen|wanx|wan\d*\.?\d*)-(?:image|t2i|edit)(?:-\S+)?$"),
            spec_template=ModelSpec(
                model_id="*",
                modality=Modality.IMAGE,
                input_mapping=route_images(slots=("image",)),
            ),
            description="DashScope image generation family",
            example_slugs=("qwen-image-plus", "wanx2.1-t2i-turbo", "qwen-image-edit-plus"),
        )
        
        return ModelRegistry(provider_families=(image_family,))

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modalities=[Modality.IMAGE],
            supported_inputs=["text", "image"],
            accepts_chain_input=True,
            output_formats=["image/jpeg", "image/png", "image/webp"],
        )

    def submit(self, step: Step, config: RunnableConfig | None = None) -> Any:
        """Submit image generation request."""
        try:
            payload = self._build_image_payload(step)
            task_id = self._submit_image_request(step.model, payload)
            return task_id
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope image submit failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)

    def _build_image_payload(self, step: Step) -> dict:
        """Build DashScope image payload from step."""
        model = step.model
        prompt = step.prompt or ""
        images = step.inputs or []
        
        payload: dict = {
            "model": model,
            "input": {
                "messages": [{"role": "user", "content": [{"text": prompt}]}]
            },
            "parameters": {
                "n": step.params.get("n", 1),
                "watermark": step.params.get("watermark", False),
            }
        }
        
        if images and "edit" in model.lower():
            payload["input"]["messages"][0]["content"] = [{"image": images[0]}, {"text": prompt}]
        
        return payload

    def poll(self, prediction_id: Any, config: RunnableConfig | None = None) -> bool:
        """Poll image task status."""
        try:
            output = self._poll_image_status(prediction_id)
            status = output.get("task_status", "").upper()
            return status in ("SUCCEEDED", "SUCCESS")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope image poll failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)

    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Fetch image generation result."""
        try:
            output = self._poll_image_status(prediction_id)
            
            image_url = (
                output.get("image_url")
                or output.get("url")
                or (output.get("results", [{}])[0].get("url") if output.get("results") else None)
                or output.get("output", {}).get("image_url")
            )
            
            if not image_url:
                raise ProviderError(f"DashScope image task succeeded but no image_url: {output}")
            
            media_type = "image/png"
            url_str = str(image_url).lower()
            if "jpg" in url_str or "jpeg" in url_str:
                media_type = "image/jpeg"
            elif "webp" in url_str:
                media_type = "image/webp"
            
            asset = Asset(url=str(image_url), media_type=media_type)
            step.assets.append(asset)
            step.provider_payload = {"dashscope": {"task_id": prediction_id}}
            
            return step
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope image fetch_output failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)
