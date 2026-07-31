"""
Video Provider Router

A smart router that selects the appropriate video generation provider
based on availability, cost, capability, or explicit selection.

Supported providers:
- veo3: Google Veo 3 via Veo3API (T2V + i2v, high quality)
- dashscope: Alibaba DashScope (WanX, HappyHorse) - lower cost
- replicate: Replicate API (various models)
- decart: Decart Lucy (V2V only - video editing, NOT T2V)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from genblaze_core.models.step import Step
from genblaze_core.providers.base import RunnableConfig


class ProviderType(Enum):
    """Supported provider types."""
    VEO3 = "veo3"
    DASHSCOPE = "dashscope"
    REPLICATE = "replicate"
    DECART = "decart"


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    provider_type: ProviderType
    enabled: bool = True
    priority: int = 0  # Lower = higher priority
    api_key: str | None = None


class VideoProviderRouter:
    """
    Router that manages multiple video generation providers.
    
    Selection logic:
    1. If explicit provider is requested, use it if available
    2. Otherwise, use the highest priority available provider
    3. Fall back to next available provider on failure
    """
    
    def __init__(self):
        self._providers: dict[ProviderType, Any] = {}
        self._configs: dict[ProviderType, ProviderConfig] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers."""
        
        # Veo 3 - Highest priority (best quality T2V)
        veo3_enabled = bool(os.environ.get("VEO3_API_KEY"))
        self._configs[ProviderType.VEO3] = ProviderConfig(
            provider_type=ProviderType.VEO3,
            enabled=veo3_enabled,
            priority=1,
            api_key=os.environ.get("VEO3_API_KEY"),
        )
        
        if veo3_enabled:
            try:
                from pipeline.providers.veo3 import Veo3VideoProvider
                self._providers[ProviderType.VEO3] = Veo3VideoProvider()
                print("[router] Veo 3 provider initialized")
            except ImportError as e:
                print(f"[router] Veo 3 not available: {e}")
                self._configs[ProviderType.VEO3].enabled = False
        
        # DashScope - Second priority
        dashscope_enabled = bool(os.environ.get("DASHSCOPE_API_KEY"))
        self._configs[ProviderType.DASHSCOPE] = ProviderConfig(
            provider_type=ProviderType.DASHSCOPE,
            enabled=dashscope_enabled,
            priority=2,
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
        )
        
        if dashscope_enabled:
            try:
                from pipeline.providers.dashscope import DashScopeVideoProvider
                self._providers[ProviderType.DASHSCOPE] = DashScopeVideoProvider()
                print("[router] DashScope provider initialized")
            except ImportError as e:
                print(f"[router] DashScope not available: {e}")
                self._configs[ProviderType.DASHSCOPE].enabled = False
        
        # Replicate - Third priority
        replicate_enabled = bool(os.environ.get("REPLICATE_API_TOKEN") or os.environ.get("REPLICATE_API_KEY"))
        self._configs[ProviderType.REPLICATE] = ProviderConfig(
            provider_type=ProviderType.REPLICATE,
            enabled=replicate_enabled,
            priority=3,
            api_key=os.environ.get("REPLICATE_API_TOKEN") or os.environ.get("REPLICATE_API_KEY"),
        )
        
        if replicate_enabled:
            try:
                from pipeline.providers.replicate import ReplicateProvider
                self._providers[ProviderType.REPLICATE] = ReplicateProvider()
                print("[router] Replicate provider initialized")
            except ImportError as e:
                print(f"[router] Replicate not available: {e}")
                self._configs[ProviderType.REPLICATE].enabled = False
        
        # Decart - Lowest priority (NOTE: V2V only, not T2V!)
        decart_enabled = bool(os.environ.get("DECART_API_KEY"))
        self._configs[ProviderType.DECART] = ProviderConfig(
            provider_type=ProviderType.DECART,
            enabled=decart_enabled,
            priority=4,
            api_key=os.environ.get("DECART_API_KEY"),
        )
        
        if decart_enabled:
            try:
                from pipeline.providers.decart import DecartVideoProvider
                self._providers[ProviderType.DECART] = DecartVideoProvider()
                print("[router] Decart provider initialized (NOTE: V2V only)")
            except ImportError as e:
                print(f"[router] Decart not available: {e}")
                self._configs[ProviderType.DECART].enabled = False
            except ValueError as e:
                print(f"[router] Decart not configured: {e}")
                self._configs[ProviderType.DECART].enabled = False
    
    @property
    def available_providers(self) -> list[ProviderType]:
        """Get list of available (enabled) providers sorted by priority."""
        return [
            pt for pt, cfg in sorted(
                self._configs.items(),
                key=lambda x: x[1].priority
            ) if cfg.enabled and pt in self._providers
        ]
    
    def get_provider(self, provider_type: ProviderType | None = None) -> Any:
        """
        Get the specified provider or the best available one.
        
        Args:
            provider_type: Explicit provider to use, or None for auto-select
            
        Returns:
            The selected provider instance
            
        Raises:
            ValueError: If no providers are available
        """
        if provider_type:
            if provider_type not in self._providers:
                raise ValueError(
                    f"Provider {provider_type.value} not available. "
                    f"Available: {[p.value for p in self.available_providers]}"
                )
            if not self._configs[provider_type].enabled:
                raise ValueError(f"Provider {provider_type.value} is disabled")
            return self._providers[provider_type]
        
        # Auto-select: use highest priority available
        available = self.available_providers
        if not available:
            raise ValueError("No video providers available")
        
        selected = available[0]
        print(f"[router] Auto-selected provider: {selected.value}")
        return self._providers[selected]
    
    def generate_video(
        self,
        step: Step,
        provider_type: ProviderType | None = None,
    ) -> tuple[str, str]:
        """
        Generate video using the selected provider.
        
        Args:
            step: The generation step with prompt and parameters
            provider_type: Specific provider to use, or None for auto
            
        Returns:
            Tuple of (task_id, provider_name)
        """
        provider = self.get_provider(provider_type)
        provider_name = provider.name
        
        print(f"[router] Generating video with {provider_name}")
        print(f"[router]   Model: {step.model}")
        print(f"[router]   Prompt: {step.prompt[:80] if step.prompt else 'N/A'}...")
        
        task_id = provider.submit(step)
        
        return task_id, provider_name
    
    def poll_status(self, task_id: str, provider_name: str) -> str:
        """
        Poll the status of a video generation task.
        
        Args:
            task_id: The task ID returned from generate_video
            provider_name: The name of the provider that was used
            
        Returns:
            Status string: 'PROCESSING', 'SUCCEEDED', 'FAILED'
        """
        # Find the provider by name
        provider = None
        for pt, p in self._providers.items():
            if p.name == provider_name:
                provider = p
                break
        
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        # Use provider-specific polling
        if hasattr(provider, '_poll_status'):
            return provider._poll_status(task_id)
        
        # Generic polling
        done = provider.poll(task_id)
        return "SUCCEEDED" if done else "PROCESSING"
    
    def fetch_video(
        self,
        task_id: str,
        step: Step,
        provider_name: str,
    ) -> Step:
        """
        Fetch the generated video.
        
        Args:
            task_id: The task ID
            step: The original step object (will be modified)
            provider_name: The provider that was used
            
        Returns:
            The step with the generated video asset
        """
        # Find the provider by name
        provider = None
        for pt, p in self._providers.items():
            if p.name == provider_name:
                provider = p
                break
        
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        return provider.fetch_output(task_id, step)
    
    def get_status_summary(self) -> dict:
        """Get a summary of all providers and their status."""
        return {
            "available": [p.value for p in self.available_providers],
            "providers": {
                pt.value: {
                    "enabled": cfg.enabled,
                    "priority": cfg.priority,
                    "has_api_key": bool(cfg.api_key),
                }
                for pt, cfg in self._configs.items()
            }
        }


# Global router instance
_router: VideoProviderRouter | None = None


def get_router() -> VideoProviderRouter:
    """Get the global router instance."""
    global _router
    if _router is None:
        _router = VideoProviderRouter()
    return _router


def generate_video(
    prompt: str,
    model: str | None = None,
    provider_type: ProviderType | None = None,
    **params,
) -> tuple[str, str, str]:
    """
    Convenience function to generate a video.
    
    Args:
        prompt: Text description of the video
        model: Model name (optional, uses provider default)
        provider_type: Specific provider to use
        **params: Additional parameters (duration, ratio, etc.)
        
    Returns:
        Tuple of (video_url, task_id, provider_name)
    """
    from genblaze_core.models.step import Step
    from genblaze_core import Modality
    
    router = get_router()
    
    # Create step
    step = Step(
        provider=router.get_provider(provider_type).name,
        model=model or "auto",
        prompt=prompt,
        modality=Modality.VIDEO,
    )
    step.params = params
    
    # Generate
    task_id, provider_name = router.generate_video(step, provider_type)
    
    # Poll for completion
    import time
    while True:
        status = router.poll_status(task_id, provider_name)
        if status == "SUCCEEDED":
            break
        elif status == "FAILED":
            raise RuntimeError("Video generation failed")
        print(f"[video] Status: {status}, waiting...")
        time.sleep(5)
    
    # Fetch result
    step = router.fetch_video(task_id, step, provider_name)
    
    if not step.assets:
        raise RuntimeError("No video asset returned")
    
    video_url = step.assets[0].url
    
    return video_url, task_id, provider_name
