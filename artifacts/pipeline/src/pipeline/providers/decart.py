"""
GenBlaze Decart Provider Wrapper

A wrapper around genblaze-decart for Decart Lucy video/image generation.
"""

from __future__ import annotations

import os
from typing import Any

from genblaze_core.models.step import Step
from genblaze_core.providers.base import RunnableConfig

try:
    from genblaze_decart import DecartVideoProvider as _DecartVideoProvider
    from genblaze_decart import DecartImageProvider as _DecartImageProvider
    DECART_AVAILABLE = True
except ImportError:
    DECART_AVAILABLE = False
    _DecartVideoProvider = None
    _DecartImageProvider = None


class DecartVideoProvider:
    """GenBlaze provider wrapper for Decart Lucy video generation."""
    
    name = "decart-video"
    
    def __init__(
        self,
        api_key: str | None = None,
        poll_interval: float = 5.0,
    ):
        if not DECART_AVAILABLE:
            raise ImportError(
                "genblaze-decart is not installed. "
                "Install it with: pip install genblaze-decart"
            )
        
        self._api_key = api_key or os.environ.get("DECART_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Decart API key required. Set DECART_API_KEY env var or pass api_key=."
            )
        
        self._provider = _DecartVideoProvider(
            api_key=self._api_key,
            poll_interval=poll_interval,
        )
    
    @property
    def models(self):
        return self._provider.models
    
    @property
    def name(self):
        return "decart-video"
    
    def get_capabilities(self):
        return self._provider.get_capabilities()
    
    def submit(self, step: Step, config: RunnableConfig | None = None) -> Any:
        """Submit video generation request."""
        return self._provider.submit(step, config)
    
    def poll(self, prediction_id: Any, config: RunnableConfig | None = None) -> bool:
        """Poll for task completion."""
        return self._provider.poll(prediction_id, config)
    
    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Fetch the generated video."""
        return self._provider.fetch_output(prediction_id, step)
    
    def _poll_status(self, prediction_id: str) -> str:
        """Poll status and return status string."""
        done = self._provider.poll(prediction_id)
        if done:
            return "SUCCEEDED"
        return "PROCESSING"


class DecartImageProvider:
    """GenBlaze provider wrapper for Decart Lucy image generation."""
    
    name = "decart-image"
    
    def __init__(
        self,
        api_key: str | None = None,
        poll_interval: float = 5.0,
    ):
        if not DECART_AVAILABLE:
            raise ImportError(
                "genblaze-decart is not installed. "
                "Install it with: pip install genblaze-decart"
            )
        
        self._api_key = api_key or os.environ.get("DECART_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Decart API key required. Set DECART_API_KEY env var or pass api_key=."
            )
        
        self._provider = _DecartImageProvider(
            api_key=self._api_key,
            poll_interval=poll_interval,
        )
    
    @property
    def models(self):
        return self._provider.models
    
    @property
    def name(self):
        return "decart-image"
    
    def get_capabilities(self):
        return self._provider.get_capabilities()
    
    def submit(self, step: Step, config: RunnableConfig | None = None) -> Any:
        """Submit image generation request."""
        return self._provider.submit(step, config)
    
    def poll(self, prediction_id: Any, config: RunnableConfig | None = None) -> bool:
        """Poll for task completion."""
        return self._provider.poll(prediction_id, config)
    
    def fetch_output(self, prediction_id: Any, step: Step) -> Step:
        """Fetch the generated image."""
        return self._provider.fetch_output(prediction_id, step)
