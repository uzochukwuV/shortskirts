"""
GenBlaze DashScope/Qwen Provider

A custom GenBlaze provider adapter for Alibaba DashScope API (Qwen/Wan video and image models).

This provider enables GenBlaze Pipeline API integration with:
    - Video: happyhorse-1.1-i2v, happyhorse-1.1-t2v, happyhorse-1.1-r2v
- Image: qwen-image, wanx2.1-t2i-turbo, wan2.7-image-pro
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


DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/api/v1"

# Default models (matching existing Dysentry configuration)
DASHSCOPE_HAPPYHORSE_T2V_MODEL = "happyhorse-1.1-t2v"
DASHSCOPE_HAPPYHORSE_I2V_MODEL = "happyhorse-1.1-i2v"
DASHSCOPE_HAPPYHORSE_R2V_MODEL = "happyhorse-1.1-r2v"


def _classify_capability(model: str, reference_images: list | None = None) -> str:
    if not reference_images:
        return "t2v"
    if len(reference_images) >= 2:
        return "r2v"
    return "i2v"


def _map_dashscope_error(status_code: int, response_text: str) -> ProviderErrorCode:
    if status_code == 401 or status_code == 403:
        return ProviderErrorCode.AUTH_FAILURE
    if status_code == 429:
        return ProviderErrorCode.RATE_LIMIT
    if status_code >= 500:
        return ProviderErrorCode.TRANSIENT_FAILURE
    return ProviderErrorCode.UNKNOWN


class DashScopeBase(BaseProvider):
    discovery_support = DiscoverySupport.NONE

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        http_timeout: float = 120.0,
        models: ModelRegistry | None = None,
        retry_policy: RetryPolicy | None = None,
        poll_interval: float = 10.0,
    ):
        super().__init__(models=models, retry_policy=retry_policy)
        self._api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self._base_url = base_url or os.environ.get("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL
        self._http_timeout = http_timeout
        self._http_client: httpx.Client | None = None
        self._poll_interval = poll_interval
        self.poll_transient_retries = 10

    def _get_http_client(self) -> httpx.Client:
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
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None


class DashScopeVideoProvider(DashScopeBase):
    """GenBlaze provider for DashScope/Qwen video generation."""
    
    name = "dashscope-video"

    @classmethod
    def create_registry(cls) -> ModelRegistry:
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
        
        return ModelRegistry(provider_families=(happyhorse_family,))

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modalities=[Modality.VIDEO],
            supported_inputs=["text", "image"],
            accepts_chain_input=True,
            output_formats=["video/mp4"],
        )

    def submit(self, step: Step, config: RunnableConfig | None = None) -> Any:
        """Submit video generation request with async header."""
        try:
            endpoint, payload = self._build_video_payload(step)
            
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",  # Enable async mode
            }
            
            client = self._get_http_client()
            resp = client.post(endpoint, headers=headers, json=payload)
            
            if resp.status_code >= 400:
                error_text = resp.text[:500]
                raise ProviderError(
                    f"DashScope video submit failed ({resp.status_code}): {error_text}",
                    error_code=_map_dashscope_error(resp.status_code, resp.text),
                )
            
            data = resp.json()
            task_id = data.get("output", {}).get("task_id")
            if not task_id:
                raise ProviderError(f"DashScope submit succeeded but no task_id: {data}")
            
            print(f"[dashscope] Video task submitted: {task_id}")
            return task_id
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"DashScope video submit failed: {exc}",
                error_code=ProviderErrorCode.UNKNOWN,
            ) from exc

    def _build_video_payload(self, step: Step) -> tuple[str, dict]:
        """Build DashScope video payload with enhanced quality parameters.
        
        Returns (endpoint, payload) tuple.
        """
        import random
        
        model = step.model
        prompt = step.prompt or ""
        images = [getattr(asset, "url", asset) for asset in (step.inputs or [])]
        capability = _classify_capability(model, images)
        
        endpoint = "/services/aigc/video-generation/video-synthesis"
        
        # Select model based on capability (prefer reference models for quality)
        if capability == "t2v":
            model = model or DASHSCOPE_HAPPYHORSE_T2V_MODEL
        elif capability == "i2v":
            model = model or DASHSCOPE_HAPPYHORSE_I2V_MODEL
        elif capability == "r2v":
            model = model or DASHSCOPE_HAPPYHORSE_R2V_MODEL
        
        resolution = step.params.get("resolution", "1080P")
        ratio = step.params.get("ratio", "16:9")
        # Keep test renders cheap. HappyHorse video requests require at least 3s.
        test_cap = max(3, int(os.environ.get("DASHSCOPE_TEST_MAX_DURATION_SECONDS", "3")))
        requested_duration = int(step.params.get("duration", test_cap))
        duration = max(3, min(requested_duration, test_cap, 8))
        
        # Enhanced quality parameters
        seed = step.params.get("seed")
        if seed is None:
            seed = random.randint(0, 2147483647)  # DashScope seed limit
        
        # Build base parameters
        params = {
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "watermark": False,
            "seed": seed,
        }
        
        # Add quality-enhancing parameters
        # prompt_extend enhances the prompt for better results
        if capability == "t2v":
            params["prompt_extend"] = True
        
        # For better quality, can add these if supported by the model
        if step.params.get("short_video_model") is not None:
            params["short_video_model"] = step.params.get("short_video_model")
        
        if capability == "r2v" and images:
            payload = {
                "model": model,
                "input": {
                    "prompt": prompt,
                    "media": [{"type": "reference_image", "url": url} for url in images[:9]],
                },
                "parameters": params,
            }
        elif capability == "i2v" and images:
            payload = {
                "model": model,
                "input": {
                    "prompt": prompt,
                    "media": [{"type": "first_frame", "url": images[0]}],
                },
                "parameters": params,
            }
        else:
            payload = {
                "model": model,
                "input": {"prompt": prompt},
                "parameters": params,
            }
        
        return endpoint, payload

    def poll(self, prediction_id: Any, config: RunnableConfig | None = None) -> bool:
        """Poll video task status."""
        try:
            status = self._poll_status(prediction_id)
            return status in ("SUCCEEDED", "SUCCESS")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope video poll failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)

    def _poll_status(self, task_id: str, timeout: int = 600) -> str:
        """Poll task status using /tasks/{task_id} endpoint."""
        client = self._get_http_client()
        endpoint = f"/tasks/{task_id}"
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                resp = client.get(endpoint)
                if resp.status_code >= 400:
                    raise ProviderError(
                        f"DashScope poll failed ({resp.status_code}): {resp.text[:200]}",
                        error_code=_map_dashscope_error(resp.status_code, resp.text),
                    )
                
                data = resp.json()
                status = data.get("output", {}).get("task_status", "").upper()
                
                print(f"[dashscope] Task {task_id}: {status}")
                
                if status in ("SUCCEEDED", "SUCCESS"):
                    return status
                elif status in ("FAILED", "CANCELLED", "CANCELED"):
                    error_msg = data.get("output", {}).get("message") or status
                    raise ProviderError(f"DashScope video task {status}: {error_msg}")
                
                time.sleep(self._poll_interval)
                
            except ProviderError:
                raise
            except Exception:
                time.sleep(self._poll_interval)
        
        raise ProviderError(
            f"DashScope video task {task_id} timed out after {timeout}s",
            error_code=ProviderErrorCode.TIMEOUT,
        )

    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Fetch video generation result."""
        try:
            client = self._get_http_client()
            resp = client.get(f"/tasks/{prediction_id}")
            
            if resp.status_code >= 400:
                raise ProviderError(
                    f"DashScope fetch failed ({resp.status_code}): {resp.text[:200]}",
                    error_code=_map_dashscope_error(resp.status_code, resp.text),
                )
            
            data = resp.json()
            output = data.get("output", {})
            status = output.get("task_status", "").upper()
            
            if status in ("FAILED", "CANCELLED", "CANCELED"):
                raise ProviderError(f"DashScope video task {status}")
            if status != "SUCCEEDED":
                raise ProviderError(f"DashScope video task not complete: {status}")
            
            # Extract video URL
            video_url = (
                output.get("video_url")
                or output.get("video", {}).get("url")
                or output.get("url")
            )
            
            if not video_url:
                results = output.get("results", [])
                if results and isinstance(results, list):
                    video_url = results[0].get("video_url") or results[0].get("url")
            
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
    """GenBlaze provider for DashScope/Qwen image generation."""
    
    name = "dashscope-image"

    @classmethod
    def create_registry(cls) -> ModelRegistry:
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
        """Submit image generation request.
        
        Images are synchronous - we submit and get result immediately.
        Returns a dict with the result for fetch_output to process.
        """
        try:
            payload = self._build_image_payload(step)
            
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            
            client = self._get_http_client()
            endpoint = "/services/aigc/multimodal-generation/generation"
            resp = client.post(endpoint, headers=headers, json=payload)
            
            if resp.status_code >= 400:
                error_text = resp.text[:500]
                raise ProviderError(
                    f"DashScope image submit failed ({resp.status_code}): {error_text}",
                    error_code=_map_dashscope_error(resp.status_code, resp.text),
                )
            
            data = resp.json()
            
            # For images, the result comes immediately
            # Return the full response data for fetch_output to extract URL
            print(f"[dashscope] Image generated successfully")
            return data  # Return full response for sync images
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope image submit failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)

    def _build_image_payload(self, step: Step) -> dict:
        """Build DashScope image payload."""
        model = step.model
        prompt = step.prompt or ""
        images = [getattr(asset, "url", asset) for asset in (step.inputs or [])]
        
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
            content = [{"image": img} for img in images] + [{"text": prompt}]
            payload["input"]["messages"][0]["content"] = content
        
        return payload

    def poll(self, prediction_id: Any, config: RunnableConfig | None = None) -> bool:
        """Poll image task status.
        
        For sync images, prediction_id is the full response data.
        """
        # Sync images return immediately - always done
        return True

    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Fetch image generation result.
        
        For sync images, prediction_id is the full response data.
        """
        try:
            # prediction_id is the full response for sync images
            data = prediction_id if isinstance(prediction_id, dict) else {}
            output = data.get("output", {})
            
            # Extract image URL from choices (sync response format)
            choices = output.get("choices", [])
            image_url = None
            
            if choices and isinstance(choices, list):
                message = choices[0].get("message", {})
                content = message.get("content", [])
                if content and isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("image"):
                            image_url = item["image"]
                            break
            
            # Fallback to other extraction methods
            if not image_url:
                image_url = (
                    output.get("image_url")
                    or output.get("url")
                )
            
            if not image_url:
                results = output.get("results", [])
                if results and isinstance(results, list):
                    image_url = results[0].get("image_url") or results[0].get("url")
            
            if not image_url:
                raise ProviderError(f"DashScope image succeeded but no image_url: {output}")
            
            media_type = "image/png"
            url_str = str(image_url).lower()
            if "jpg" in url_str or "jpeg" in url_str:
                media_type = "image/jpeg"
            elif "webp" in url_str:
                media_type = "image/webp"
            
            asset = Asset(url=str(image_url), media_type=media_type)
            step.assets.append(asset)
            step.provider_payload = {"dashscope": {"type": "sync_image"}}
            
            return step
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"DashScope image fetch_output failed: {exc}", error_code=ProviderErrorCode.UNKNOWN)
