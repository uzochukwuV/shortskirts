"""
Providers package for Dysentry.

Exports:
- Veo3VideoProvider
- DashScopeVideoProvider
- DashScopeImageProvider  
- ReplicateProvider
- DecartVideoProvider (V2V only - not for T2V)
- VideoProviderRouter
- ProviderType
- get_router
"""

from pipeline.providers.veo3 import Veo3VideoProvider

from pipeline.providers.dashscope import (
    DashScopeVideoProvider,
    DashScopeImageProvider,
)

from pipeline.providers.replicate import ReplicateProvider

from pipeline.providers.decart import (
    DecartVideoProvider,
    DecartImageProvider,
)

from pipeline.providers.provider_router import (
    VideoProviderRouter,
    ProviderType,
    get_router,
    generate_video,
)

__all__ = [
    # Veo 3
    "Veo3VideoProvider",
    # DashScope
    "DashScopeVideoProvider",
    "DashScopeImageProvider",
    # Replicate
    "ReplicateProvider",
    # Decart (V2V only)
    "DecartVideoProvider",
    "DecartImageProvider",
    # Router
    "VideoProviderRouter",
    "ProviderType",
    "get_router",
    "generate_video",
]