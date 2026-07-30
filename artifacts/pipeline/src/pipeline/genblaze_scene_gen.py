"""
GenBlaze-based Scene Generation

This module provides scene generation using GenBlaze's Pipeline API,
offering provider-agnostic video generation with built-in provenance.

Usage:
    from pipeline.genblaze_scene_gen import GenBlazeSceneGenerator
    
    generator = GenBlazeSceneGenerator()
    result = await generator.generate_scene(
        prompt="A drone shot over mountains",
        reference_images=["https://..."],
        duration=5,
        aspect_ratio="16:9",
    )
"""

import os
import asyncio
from typing import Optional
from dataclasses import dataclass

from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from pipeline.media_tools import extract_last_frame_jpeg


@dataclass
class SceneResult:
    """Result from scene generation."""
    clip_url: Optional[str] = None
    exit_frame_url: Optional[str] = None
    duration: float = 0.0
    prompt: str = ""
    provider: str = ""
    model: str = ""
    error: Optional[str] = None


class GenBlazeSceneGenerator:
    """
    Scene generator using GenBlaze Pipeline API.
    
    This provides an alternative to the legacy DashScope/AIML providers,
    with built-in provenance tracking and multi-provider fallback.
    """
    
    def __init__(self):
        """Initialize the generator."""
        self._adapter = None
    
    async def _get_adapter(self):
        """Lazy-load the GenBlaze adapter."""
        if self._adapter is None:
            from pipeline.genblaze_adapter import GenBlazeAdapter
            self._adapter = GenBlazeAdapter()
        return self._adapter
    
    async def generate_scene(
        self,
        prompt: str,
        reference_images: Optional[list[str]] = None,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        model: str = "Kling-Text2Video-V2.1-Master",
        timeout: int = 600,
    ) -> SceneResult:
        """
        Generate a video scene using GenBlaze.
        
        Args:
            prompt: Scene description
            reference_images: Optional reference images for I2V
            duration: Video duration in seconds
            aspect_ratio: Video aspect ratio
            model: Video model to use
            timeout: Maximum generation time
            
        Returns:
            SceneResult with video URL and exit frame
        """
        adapter = await self._get_adapter()
        
        # Generate video
        result = await adapter.generate_video(
            prompt=prompt,
            reference_images=reference_images,
            model=model,
            duration=duration,
            aspect_ratio=aspect_ratio,
            timeout=timeout,
        )
        
        if result.error:
            return SceneResult(error=result.error)
        
        # Download and re-upload to ensure B2 storage
        # (GenBlaze may return CDN URLs that need conversion)
        try:
            clip_bytes = await download_url_to_bytes(result.url)
        except Exception as e:
            # If download fails, use the original URL
            clip_bytes = None
        
        if clip_bytes:
            # Upload to B2 with proper key structure
            # Note: In production, we'd use GenBlaze's sink directly
            # For now, re-upload through our storage layer
            clip_key = build_key(
                "genblaze",
                "scenes",
                f"scene_{hash(prompt) % 100000}.mp4"
            )
            clip_url = upload_bytes(clip_bytes, clip_key, "video/mp4")
        else:
            clip_url = result.url
        
        # Extract exit frame
        exit_frame_url = None
        if clip_bytes:
            try:
                exit_frame_url = await self._extract_exit_frame(
                    clip_bytes,
                    clip_key.replace(".mp4", "_exit.jpg")
                )
            except Exception as e:
                print(f"[genblaze_scene] Exit frame extraction failed: {e}")
        
        return SceneResult(
            clip_url=clip_url,
            exit_frame_url=exit_frame_url,
            duration=float(duration),
            prompt=prompt,
            provider=result.provider,
            model=result.model,
        )
    
    async def _extract_exit_frame(
        self,
        clip_bytes: bytes,
        key: str,
    ) -> Optional[str]:
        """Extract last frame from video and upload to B2."""
        try:
            frame_bytes = await extract_last_frame_jpeg(clip_bytes)
            return upload_bytes(frame_bytes, key, "image/jpeg")
        except Exception as e:
            print(f"[genblaze_scene] Frame extraction failed: {e}")
            return None


async def test_generation():
    """Test the GenBlaze scene generator."""
    generator = GenBlazeSceneGenerator()
    
    result = await generator.generate_scene(
        prompt="A serene mountain lake at dawn with mist rising",
        duration=5,
        aspect_ratio="16:9",
        model="Kling-Text2Video-V2.1-Master",
        timeout=300,
    )
    
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Generated: {result.clip_url}")
        print(f"Exit frame: {result.exit_frame_url}")
        print(f"Provider: {result.provider}")
        print(f"Model: {result.model}")


if __name__ == "__main__":
    asyncio.run(test_generation())
