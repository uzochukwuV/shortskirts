"""
GenBlaze Replicate Provider

A GenBlaze provider adapter for Replicate's API.

Replicate provides access to various AI models including:
- Video generation: ltxv, minimax, etc.
- Image generation: Stable Diffusion, FLUX, etc.
- Audio, etc.

API Docs: https://replicate.com/docs

Note: Requires REPLICATE_API_TOKEN in environment.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Optional

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

DEFAULT_BASE_URL = "https://api.replicate.com"

# Video models
HUNYUAN_MODEL = "tencent/hunyuan-video"
LTXV_MODEL = "luosi-npn/ltxv-hunyuan-t2v"
P_VIDEO_MODEL = "prunaai/p-video"


def _map_replicate_error(status_code: int, response_text: str) -> ProviderErrorCode:
    """Map HTTP status codes to provider error codes."""
    if status_code == 401:
        return ProviderErrorCode.AUTH_FAILURE
    if status_code == 402:
        return ProviderErrorCode.RATE_LIMIT  # Insufficient credit
    if status_code == 429:
        return ProviderErrorCode.RATE_LIMIT
    if status_code >= 500:
        return ProviderErrorCode.TRANSIENT_FAILURE
    return ProviderErrorCode.UNKNOWN


class ReplicateProvider(BaseProvider):
    """GenBlaze provider for Replicate API."""
    
    name = "replicate"
    discovery_support = DiscoverySupport.NONE

    def __init__(
        self,
        api_token: str | None = None,
        base_url: str | None = None,
        http_timeout: float = 300.0,
        models: ModelRegistry | None = None,
        retry_policy: RetryPolicy | None = None,
        poll_interval: float = 5.0,
    ):
        super().__init__(models=models, retry_policy=retry_policy)
        # Support both REPLICATE_API_TOKEN and REPLICATE_API_KEY
        self._api_token = api_token or os.environ.get("REPLICATE_API_TOKEN") or os.environ.get("REPLICATE_API_KEY")
        self._base_url = base_url or DEFAULT_BASE_URL
        self._http_timeout = http_timeout
        self._http_client: httpx.Client | None = None
        self._poll_interval = poll_interval

    def _get_headers(self) -> dict[str, str]:
        if not self._api_token:
            raise ProviderError(
                "No Replicate API token found. Set REPLICATE_API_TOKEN or REPLICATE_API_KEY env var.",
                error_code=ProviderErrorCode.AUTH_FAILURE,
            )
        return {
            "Authorization": f"Token {self._api_token}",
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
        """Create model registry for Replicate."""
        video_family = ModelFamily(
            name="replicate-video",
            pattern=re.compile(r"^.*video.*$", re.IGNORECASE),
            spec_template=ModelSpec(
                model_id="*",
                modality=Modality.VIDEO,
                input_mapping=route_images(slots=("image",)),
            ),
            description="Replicate video generation models",
            example_slugs=("ltxv", "minimax", "p-video"),
        )
        
        image_family = ModelFamily(
            name="replicate-image",
            pattern=re.compile(r"^.*(image|flux|sd|stable-diffusion).*$", re.IGNORECASE),
            spec_template=ModelSpec(
                model_id="*",
                modality=Modality.IMAGE,
                input_mapping=route_images(slots=("image",)),
            ),
            description="Replicate image generation models",
            example_slugs=("flux", "sdxl"),
        )
        
        return ModelRegistry(provider_families=(video_family, image_family))

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_modalities=[Modality.VIDEO, Modality.IMAGE],
            supported_inputs=["text", "image"],
            accepts_chain_input=True,
            output_formats=["video/mp4", "image/png"],
        )

    def submit(self, step: Step, config: Any | None = None) -> str:
        """Submit a prediction request."""
        model = step.model or LTXV_MODEL
        prompt = step.prompt or ""
        images = step.inputs or []
        
        # Build model path
        if "/" not in model:
            model = f"zsigmask/{model}"
        
        # Build input payload
        input_payload: dict[str, Any] = {
            "prompt": prompt,
        }
        
        # Add parameters from step
        if step.params.get("aspect_ratio"):
            input_payload["aspect_ratio"] = step.params["aspect_ratio"]
        
        if step.params.get("duration"):
            input_payload["duration"] = step.params["duration"]
        
        if step.params.get("num_frames"):
            input_payload["num_frames"] = step.params["num_frames"]
        
        if step.params.get("resolution"):
            input_payload["resolution"] = step.params["resolution"]
        
        # Add image URLs for image-to-video
        if images:
            for img in images:
                if hasattr(img, 'url'):
                    input_payload["image"] = img.url
                    break
        
        # Create prediction
        client = self._get_client()
        
        try:
            resp = client.post(
                f"/v1/models/{model}/predictions",
                json={"input": input_payload},
            )
            
            if resp.status_code >= 400:
                error_text = resp.text[:500]
                raise ProviderError(
                    f"Replicate submit failed ({resp.status_code}): {error_text}",
                    error_code=_map_replicate_error(resp.status_code, resp.text),
                )
            
            data = resp.json()
            
            # Get prediction ID
            prediction_id = data.get("id")
            if not prediction_id:
                raise ProviderError(f"No prediction ID in response: {data}")
            
            print(f"[replicate] Prediction created: {prediction_id}")
            return prediction_id
            
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"Replicate submit failed: {exc}",
                error_code=ProviderErrorCode.UNKNOWN,
            ) from exc

    def poll(self, prediction_id: str | dict, config: Any | None = None) -> bool:
        """Poll for prediction completion."""
        if isinstance(prediction_id, dict):
            status = prediction_id.get("status", "")
            return status in ("succeeded", "failed", "canceled")
        
        client = self._get_client()
        
        try:
            resp = client.get(f"/v1/predictions/{prediction_id}")
            
            if resp.status_code >= 400:
                return False
            
            data = resp.json()
            status = data.get("status", "")
            
            print(f"[replicate] Prediction {prediction_id}: {status}")
            
            return status in ("succeeded", "failed", "canceled")
            
        except Exception:
            return False

    def fetch_output(self, prediction_id: str | dict, step: Step) -> Step:
        """Fetch prediction output."""
        if isinstance(prediction_id, dict):
            pred_data = prediction_id
            prediction_id = pred_data.get("id", str(prediction_id))
        else:
            # Fetch prediction data
            client = self._get_client()
            resp = client.get(f"/v1/predictions/{prediction_id}")
            
            if resp.status_code >= 400:
                raise ProviderError(
                    f"Replicate fetch failed ({resp.status_code}): {resp.text[:200]}",
                    error_code=_map_replicate_error(resp.status_code, resp.text),
                )
            
            pred_data = resp.json()
        
        status = pred_data.get("status", "")
        
        if status == "failed":
            error = pred_data.get("error", "Unknown error")
            raise ProviderError(f"Replicate prediction failed: {error}")
        
        if status == "canceled":
            raise ProviderError("Replicate prediction was canceled")
        
        if status != "succeeded":
            raise ProviderError(f"Replicate prediction not complete: {status}")
        
        # Get output
        output = pred_data.get("output")
        
        if not output:
            raise ProviderError("No output in prediction result")
        
        # Handle different output types
        if isinstance(output, list):
            output = output[0]
        
        # Determine asset type
        if isinstance(output, str):
            if output.endswith(".mp4") or "video" in output.lower():
                asset = Asset(url=output, media_type="video/mp4")
                asset.video = VideoMetadata(has_audio=True)
            else:
                asset = Asset(url=output, media_type="image/png")
        else:
            asset = Asset(url=str(output), media_type="video/mp4")
        
        step.assets.append(asset)
        step.provider_payload = {"replicate": {"prediction_id": prediction_id}}
        
        return step

    def _poll_prediction(self, prediction_id: str, max_wait: int = 600) -> dict:
        """Poll until prediction completes."""
        start = time.time()
        
        while time.time() - start < max_wait:
            client = self._get_client()
            
            resp = client.get(f"/v1/predictions/{prediction_id}")
            
            if resp.status_code >= 400:
                raise ProviderError(f"Polling failed: {resp.status_code}")
            
            data = resp.json()
            status = data.get("status", "")
            
            print(f"[replicate] Status: {status} ({int(time.time() - start)}s)")
            
            if status == "succeeded":
                return data
            elif status in ("failed", "canceled"):
                error = data.get("error", "Unknown")
                raise ProviderError(f"Prediction {status}: {error}")
            
            time.sleep(self._poll_interval)
        
        raise ProviderError(f"Timeout waiting for prediction after {max_wait}s")

    def extend_video(self, task_id: str, prompt: str) -> str:
        """Extend a video prediction."""
        # Replicate doesn't have a native extend API
        # Would need to use the model with previous output
        raise NotImplementedError("Video extension not supported in Replicate provider")

    def get_1080p(self, task_id: str) -> str:
        """Upscale to 1080p - not directly supported."""
        raise NotImplementedError("1080p upscaling not supported in Replicate provider")
