"""
GenBlaze Adapter for Dysentry Video Production System

This module provides a unified interface to GenBlaze's Pipeline API for
generating video, image, and audio content with built-in provenance tracking.

Supported Providers:
- DashScope/Qwen: wan2.7-t2v/i2v/r2v, happyhorse, qwen-image (via custom provider)
- GMICloud: Seedance, Kling, Veo, Wan (video); Seedream, FLUX (image)
- OpenAI: Sora (video), DALL-E (image), TTS (audio)
- Google: Veo (video), Imagen (image)
- NVIDIA NIM: Cosmos (video), SDXL/FLUX (image)

Usage:
    from pipeline.genblaze_adapter import GenBlazeAdapter
    
    adapter = GenBlazeAdapter()
    result = await adapter.generate_video(
        prompt="A drone shot over mountains",
        reference_images=["https://..."],
        model="wan2.7-t2v",
    )
"""

import os
import io
import asyncio
from typing import Optional
from dataclasses import dataclass
from enum import Enum

# GenBlaze imports
from genblaze_core import Modality, Pipeline, ObjectStorageSink, KeyStrategy
from genblaze_s3 import S3StorageBackend


class VideoModel(str, Enum):
    """Supported video generation models."""
    # DashScope/Qwen (via custom provider)
    WAN_T2V = "wan2.7-t2v"
    WAN_I2V = "wan2.7-i2v"
    WAN_R2V = "wan2.7-r2v"
    HAPPYHORSE_T2V = "happyhorse-1.1-t2v"
    HAPPYHORSE_I2V = "happyhorse-1.1-i2v"
    HAPPYHORSE_R2V = "happyhorse-1.1-r2v"
    # GMICloud
    KLING_T2V = "Kling-Text2Video-V2.1-Master"
    KLING_I2V = "Kling-Image2Video-V2.1-Master"
    VEO3 = "veo3"
    # OpenAI
    SORA_2 = "sora-2"
    # NVIDIA
    COSMOS_2 = "cosmos-2.0"
    # Runway
    GEN4_TURBO = "gen4_turbo"
    # Luma
    RAY_2 = "ray-2"


class ImageModel(str, Enum):
    """Supported image generation models."""
    # DashScope/Qwen (via custom provider)
    QWEN_IMAGE_PLUS = "qwen-image-plus"
    WANX_T2I = "wanx2.1-t2i-turbo"
    QWEN_EDIT = "qwen-image-edit-plus"
    # GMICloud
    SEEDREAM = "seedream-5.0-lite"
    SEEDANCE = "seedance-2.0"
    # OpenAI
    DALL_E_3 = "dall-e-3"
    GPT_IMAGE = "gpt-image-3"
    # Google
    IMAGEN_3 = "imagen-3.0"
    # Replicate
    FLUX_SCHNELL = "flux-schnell"


@dataclass
class GenerationResult:
    """Result from a generation operation."""
    url: str
    sha256: Optional[str] = None
    provider: str = ""
    model: str = ""
    cost_usd: Optional[float] = None
    manifest: Optional[dict] = None
    error: Optional[str] = None


class GenBlazeAdapter:
    """
    Unified adapter for GenBlaze-based content generation.
    
    This adapter provides a simple interface for generating video, images,
    and audio using multiple providers through GenBlaze's Pipeline API.
    
    Features:
    - Provider-agnostic generation (swap providers without code changes)
    - Built-in B2/S3 storage integration
    - SHA-256 provenance tracking
    - Fallback chains
    - Cost tracking
    """
    
    def __init__(
        self,
        bucket: Optional[str] = None,
        b2_key_id: Optional[str] = None,
        b2_app_key: Optional[str] = None,
        region: str = "us-west-004",
    ):
        """
        Initialize the GenBlaze adapter.
        
        Args:
            bucket: B2 bucket name (defaults to B2_BUCKET env var)
            b2_key_id: B2 key ID (defaults to B2_KEY_ID env var)
            b2_app_key: B2 app key (defaults to B2_APP_KEY env var)
            region: B2 region (defaults to us-west-004)
        """
        self.bucket = bucket or os.getenv("B2_BUCKET", "dysentry-assets")
        self.b2_key_id = b2_key_id or os.getenv("B2_KEY_ID")
        self.b2_app_key = b2_app_key or os.getenv("B2_APP_KEY")
        self.region = region
        self._sink: Optional[ObjectStorageSink] = None
        self._sink_lock = asyncio.Lock()
    
    def _get_storage_sink(self) -> Optional[ObjectStorageSink]:
        """Get or create the storage sink."""
        if not self.b2_key_id or not self.b2_app_key:
            return None
        
        backend = S3StorageBackend.for_backblaze(
            self.bucket,
            region=self.region,
        )
        return ObjectStorageSink(
            backend,
            prefix="dysentry",
            key_strategy=KeyStrategy.HIERARCHICAL,
        )
    
    async def generate_video(
        self,
        prompt: str,
        reference_images: Optional[list[str]] = None,
        model: str = VideoModel.WAN_T2V.value,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        timeout: int = 600,
    ) -> GenerationResult:
        """
        Generate a video using GenBlaze Pipeline.
        
        Args:
            prompt: Text prompt for video generation
            reference_images: Optional list of reference image URLs
            model: Video model to use (defaults to wan2.7-t2v via DashScope)
            duration: Video duration in seconds
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16")
            timeout: Maximum wait time in seconds
            
        Returns:
            GenerationResult with URL and provenance data
        """
        try:
            # Import providers lazily to avoid circular imports
            from genblaze_gmicloud import GMICloudVideoProvider
            from genblaze_openai import SoraProvider
            from genblaze_google import VeoVideoProvider
            from genblaze_nvidia import CosmosVideoProvider
            from genblaze_runway import RunwayProvider
            from genblaze_luma import LumaProvider
            
            # Select provider based on model
            provider = self._get_video_provider(model)
            if provider is None:
                return GenerationResult(
                    error=f"Unknown video model: {model}"
                )
            
            # Build pipeline step
            step_config = {
                "model": model,
                "prompt": prompt,
                "modality": Modality.VIDEO,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            }
            
            # Add reference images for I2V models
            if reference_images and self._supports_image_input(model):
                step_config["image_url"] = reference_images[0]
            
            # Execute pipeline
            result = (
                Pipeline(f"video-{model}")
                .step(provider, **step_config)
                .run(sink=self._sink, timeout=timeout)
            )
            
            if result.run.steps and result.run.steps[0].assets:
                asset = result.run.steps[0].assets[0]
                return GenerationResult(
                    url=asset.url,
                    sha256=asset.sha256,
                    provider=result.run.steps[0].provider,
                    model=result.run.steps[0].model,
                    cost_usd=result.run.steps[0].cost_usd,
                    manifest={
                        "canonical_hash": result.manifest.canonical_hash,
                        "manifest_uri": result.manifest.manifest_uri,
                    },
                )
            
            return GenerationResult(
                error="No assets generated"
            )
            
        except Exception as e:
            return GenerationResult(
                error=f"Video generation failed: {str(e)}"
            )
    
    async def generate_image(
        self,
        prompt: str,
        model: str = ImageModel.QWEN_IMAGE_PLUS.value,
        size: str = "1024x1024",
        timeout: int = 120,
    ) -> GenerationResult:
        """
        Generate an image using GenBlaze Pipeline.
        
        Args:
            prompt: Text prompt for image generation
            model: Image model to use (defaults to qwen-image-plus via DashScope)
            size: Image size (e.g., "1024x1024", "768x768")
            timeout: Maximum wait time in seconds
            
        Returns:
            GenerationResult with URL and provenance data
        """
        try:
            # Import providers lazily
            from genblaze_gmicloud import GMICloudImageProvider
            from genblaze_openai import DalleProvider
            from genblaze_google import ImagenProvider
            
            # Select provider based on model
            provider = self._get_image_provider(model)
            if provider is None:
                return GenerationResult(
                    error=f"Unknown image model: {model}"
                )
            
            # Execute pipeline
            result = (
                Pipeline(f"image-{model}")
                .step(
                    provider,
                    model=model,
                    prompt=prompt,
                    size=size,
                )
                .run(sink=self._sink, timeout=timeout)
            )
            
            if result.run.steps and result.run.steps[0].assets:
                asset = result.run.steps[0].assets[0]
                return GenerationResult(
                    url=asset.url,
                    sha256=asset.sha256,
                    provider=result.run.steps[0].provider,
                    model=result.run.steps[0].model,
                    cost_usd=result.run.steps[0].cost_usd,
                    manifest={
                        "canonical_hash": result.manifest.canonical_hash,
                        "manifest_uri": result.manifest.manifest_uri,
                    },
                )
            
            return GenerationResult(
                error="No assets generated"
            )
            
        except Exception as e:
            return GenerationResult(
                error=f"Image generation failed: {str(e)}"
            )
    
    def _get_video_provider(self, model: str):
        """Get the appropriate video provider for a model."""
        from genblaze_gmicloud import GMICloudVideoProvider
        from genblaze_openai import SoraProvider
        from genblaze_google import VeoProvider
        
        # DashScope/Qwen models (wan2.7, happyhorse)
        if any(m in model.lower() for m in ["wan2.7", "wan2.6", "happyhorse"]):
            from pipeline.providers.dashscope import DashScopeVideoProvider
            return DashScopeVideoProvider()
        
        # GMICloud models (Kling, Veo on GMI, Seedance)
        if any(m in model for m in ["Kling", "seedance"]):
            return GMICloudVideoProvider()
        
        # OpenAI models
        if "sora" in model.lower():
            return SoraProvider()
        
        # Google Veo models
        if "veo" in model.lower():
            return VeoProvider()
        
        return GMICloudVideoProvider()  # Default fallback
    
    def _get_image_provider(self, model: str):
        """Get the appropriate image provider for a model."""
        from genblaze_gmicloud import GMICloudImageProvider
        from genblaze_openai import DalleProvider
        from genblaze_google import ImagenProvider
        
        # DashScope/Qwen image models
        if any(m in model.lower() for m in ["qwen", "wanx", "wan2.7-image", "qwen-image"]):
            from pipeline.providers.dashscope import DashScopeImageProvider
            return DashScopeImageProvider()
        
        # GMICloud models
        if any(m in model for m in ["seedream", "seedance", "flux"]):
            return GMICloudImageProvider()
        
        # OpenAI models
        if any(m in model for m in ["dall-e", "gpt-image"]):
            return DalleProvider()
        
        # Google models
        if "imagen" in model.lower():
            return ImagenProvider()
        
        return GMICloudImageProvider()  # Default fallback
    
    def _supports_image_input(self, model: str) -> bool:
        """Check if a model supports image input (I2V)."""
        return any(m in model.lower() for m in ["i2v", "image2video", "veo"])
    
    @property
    def storage_sink(self) -> Optional[ObjectStorageSink]:
        """Get the storage sink (lazy initialization)."""
        if self._sink is None and self.b2_key_id and self.b2_app_key:
            self._sink = self._get_storage_sink()
        return self._sink


def get_default_adapter() -> GenBlazeAdapter:
    """Get the default GenBlaze adapter instance."""
    return GenBlazeAdapter()
