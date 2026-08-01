"""
Unified Agent System - Consolidated Chat + Streaming + Tools

This module provides a unified agent interface that combines:
- TokenRouter LLM for chat
- 29+ production tools
- GenBlaze-style streaming events
- DashScope video generation
- Asset management

Usage:
    from pipeline.unified_agent import UnifiedAgent, UnifiedStreamingOrchestrator
    
    agent = UnifiedAgent()
    orchestrator = UnifiedStreamingOrchestrator()
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional, AsyncGenerator

import httpx

# ─── LLM ──────────────────────────────────────────────────────────────────────
from pipeline.agent_llm import TokenRouterClient, ChatMessage, ToolCall, ChatResponse, get_agent_llm

# ─── GenBlaze Provider ─────────────────────────────────────────────────────────
from pipeline.providers.dashscope import DashScopeVideoProvider

# ─── Storage ──────────────────────────────────────────────────────────────────
from storage.b2 import upload_bytes, download_url_to_bytes, build_key, BUCKET

# ─── Media Tools ──────────────────────────────────────────────────────────────
from pipeline.media_tools import extract_last_frame_png


# ══════════════════════════════════════════════════════════════════════════════
# EVENT TYPES (GenBlaze-compatible)
# ══════════════════════════════════════════════════════════════════════════════

class EventType(str, Enum):
    """GenBlaze-compatible event types."""
    # Connection
    CONNECTED = "connected"
    HEARTBEAT = "heartbeat"
    STREAM_CLOSED = "stream.closed"
    
    # Pipeline
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_PROGRESS = "pipeline.progress"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    
    # Step/Scene
    STEP_QUEUED = "step.queued"
    STEP_STARTED = "step.started"
    STEP_PROGRESS = "step.progress"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    
    # Chat
    MESSAGE = "message"
    TOOL_START = "tool_start"
    TOOL_PROGRESS = "tool_progress"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"
    
    # Done
    DONE = "done"
    ERROR = "error"


@dataclass
class StreamEvent:
    """A streaming event (GenBlaze-style)."""
    type: str
    timestamp: str = ""
    data: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_sse(self) -> str:
        """Convert to SSE format."""
        return f"data: {json.dumps({'type': self.type, **self.data, 'timestamp': self.timestamp})}\n\n"
    
    def to_dict(self) -> dict:
        return {"type": self.type, **self.data, "timestamp": self.timestamp}


# ══════════════════════════════════════════════════════════════════════════════
# ASSET MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Asset:
    """Represents a media asset."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    story_id: str = ""
    entity_type: str = ""  # scene, character, episode
    entity_id: str = ""
    asset_type: str = ""  # video, image, audio, document
    storage_key: str = ""
    storage_url: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    checksum: str = ""  # SHA256
    version: int = 1
    parent_asset_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


class AssetManager:
    """
    Manages media assets for stories.
    
    Provides:
    - Asset registration and versioning
    - Asset linking (continuity, references)
    - Asset search and retrieval
    - Storage management
    """
    
    def __init__(self, pool: Any):
        self.pool = pool
    
    async def register_asset(
        self,
        story_id: str,
        entity_type: str,
        entity_id: str,
        asset_type: str,
        storage_key: str,
        storage_url: str,
        mime_type: str,
        size_bytes: int = 0,
        checksum: str = "",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
        parent_asset_id: Optional[str] = None,
    ) -> Asset:
        """Register a new asset."""
        asset_id = str(uuid.uuid4())
        
        await self.pool.execute(
            """INSERT INTO assets (id, story_id, entity_type, entity_id, asset_type,
               storage_key, storage_url, mime_type, size_bytes, checksum, tags, metadata,
               parent_asset_id, version, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 1, now())""",
            asset_id, story_id, entity_type, entity_id, asset_type,
            storage_key, storage_url, mime_type, size_bytes, checksum,
            tags or [], json.dumps(metadata or {}),
            parent_asset_id,
        )
        
        return Asset(
            id=asset_id,
            story_id=story_id,
            entity_type=entity_type,
            entity_id=entity_id,
            asset_type=asset_type,
            storage_key=storage_key,
            storage_url=storage_url,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum=checksum,
            tags=tags or [],
            metadata=metadata or {},
            parent_asset_id=parent_asset_id,
        )
    
    async def get_assets(
        self,
        story_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        asset_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 50,
    ) -> list[Asset]:
        """Get assets with filters."""
        query = "SELECT * FROM assets WHERE story_id = $1"
        params = [story_id]
        idx = 2
        
        if entity_type:
            query += f" AND entity_type = ${idx}"
            params.append(entity_type)
            idx += 1
        
        if entity_id:
            query += f" AND entity_id = ${idx}"
            params.append(entity_id)
            idx += 1
        
        if asset_type:
            query += f" AND asset_type = ${idx}"
            params.append(asset_type)
            idx += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${idx}"
        params.append(limit)
        
        rows = await self.pool.fetch(query, *params)
        
        assets = []
        for row in rows:
            tags = row.get("tags") or []
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            
            metadata = row.get("metadata") or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            assets.append(Asset(
                id=str(row["id"]),
                story_id=str(row["story_id"]),
                entity_type=row.get("entity_type", ""),
                entity_id=str(row.get("entity_id", "")),
                asset_type=row.get("asset_type", ""),
                storage_key=row.get("storage_key", ""),
                storage_url=row.get("storage_url", ""),
                mime_type=row.get("mime_type", ""),
                size_bytes=row.get("size_bytes", 0),
                checksum=row.get("checksum", ""),
                tags=tags,
                metadata=metadata,
                parent_asset_id=str(row["parent_asset_id"]) if row.get("parent_asset_id") else None,
                version=row.get("version", 1),
                created_at=str(row["created_at"]) if row.get("created_at") else "",
            ))
        
        return assets
    
    async def link_assets(
        self,
        source_asset_id: str,
        target_asset_id: str,
        relationship_type: str,
    ) -> dict:
        """Create asset relationship."""
        rel_id = str(uuid.uuid4())
        
        await self.pool.execute(
            """INSERT INTO asset_relationships (id, source_asset_id, target_asset_id, relationship_type)
               VALUES ($1, $2, $3, $4)""",
            rel_id, source_asset_id, target_asset_id, relationship_type,
        )
        
        return {"id": rel_id, "source": source_asset_id, "target": target_asset_id, "type": relationship_type}
    
    async def search_assets(
        self,
        story_id: str,
        query: str,
        asset_type: Optional[str] = None,
    ) -> list[Asset]:
        """Search assets by tags or metadata."""
        # CockroachDB requires explicit casts for ILIKE with placeholders
        sql = """
            SELECT * FROM assets 
            WHERE story_id = $1::uuid
              AND (
                  $2::text = ANY(SELECT jsonb_array_elements_text(tags))
                  OR storage_key ILIKE '%' || $2::text || '%'
                  OR metadata::text ILIKE '%' || $2::text || '%'
              )
        """
        params = [story_id, query]
        
        if asset_type:
            sql += " AND asset_type = $3"
            params.append(asset_type)
        
        sql += " ORDER BY created_at DESC LIMIT 20"
        
        rows = await self.pool.fetch(sql, *params)
        
        assets = []
        for row in rows:
            assets.append(Asset(
                id=str(row["id"]),
                story_id=str(row["story_id"]),
                entity_type=row.get("entity_type", ""),
                entity_id=str(row.get("entity_id", "")),
                asset_type=row.get("asset_type", ""),
                storage_key=row.get("storage_key", ""),
                storage_url=row.get("storage_url", ""),
                mime_type=row.get("mime_type", ""),
                tags=row.get("tags") or [],
                metadata=row.get("metadata") or {},
            ))
        
        return assets


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED STREAMING ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

class UnifiedStreamingOrchestrator:
    """
    Unified orchestrator with GenBlaze-style SSE streaming.
    
    Combines:
    - Scene generation with DashScopeVideoProvider
    - Real-time progress events
    - Frame extraction
    - B2 storage
    """
    
    def __init__(self):
        self._active_streams: dict[str, asyncio.Queue] = {}
        self._provider = DashScopeVideoProvider()
    
    async def emit(self, stream_id: str, event: StreamEvent) -> None:
        """Emit an event to all subscribers of a stream."""
        if stream_id in self._active_streams:
            await self._active_streams[stream_id].put(event)
    
    async def subscribe(self, stream_id: str) -> AsyncGenerator[StreamEvent, None]:
        """Subscribe to events for a stream."""
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        self._active_streams[stream_id] = queue
        
        try:
            while True:
                event = await queue.get()
                yield event
                if event.type in (EventType.PIPELINE_COMPLETED, EventType.PIPELINE_FAILED, EventType.STREAM_CLOSED):
                    break
        finally:
            if stream_id in self._active_streams:
                del self._active_streams[stream_id]
    
    async def generate_scene(
        self,
        story_id: str,
        scene_id: int,
        title: str,
        prompt: str,
        model: str = "happyhorse-1.1-t2v",
        references: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate a scene video with streaming events.
        
        Returns dict with video_url, exit_frame_url, task_id
        """
        run_id = str(uuid.uuid4())[:8]
        step_id = f"scene_{scene_id}"
        references = references or []
        start_time = time.time()
        
        # Emit started event
        await self.emit(story_id, StreamEvent(
            type=EventType.STEP_STARTED,
            data={
                "run_id": run_id,
                "step_id": step_id,
                "scene_id": scene_id,
                "scene_title": title,
                "model": model,
                "status": "submitted",
                "message": f"Starting scene {scene_id}: {title}",
            }
        ))
        
        # Submit to DashScope
        from genblaze_core.models.step import Step
        from genblaze_core import Modality
        
        step = Step(provider='dashscope-video', model=model, prompt=prompt)
        step.params = {
            'duration': 5,
            'resolution': '1080P',
            'ratio': '16:9',
            'seed': int(time.time()) % 10000,
        }
        step.inputs = references
        step.modality = Modality.VIDEO
        
        task_id = self._provider.submit(step)
        
        # Progress loop
        last_pct = 0.1
        while True:
            await asyncio.sleep(15)
            
            status = self._provider._poll_status(task_id, timeout=5)
            elapsed = time.time() - start_time
            
            if status == "RUNNING":
                last_pct = min(0.1 + (elapsed / 90) * 0.7, 0.9)
                await self.emit(story_id, StreamEvent(
                    type=EventType.STEP_PROGRESS,
                    data={
                        "run_id": run_id,
                        "step_id": step_id,
                        "scene_id": scene_id,
                        "progress_pct": last_pct,
                        "elapsed_sec": elapsed,
                        "status": "processing",
                        "message": f"Generating video... {int(last_pct * 100)}%",
                    }
                ))
            
            elif status == "SUCCEEDED":
                await self.emit(story_id, StreamEvent(
                    type=EventType.STEP_COMPLETED,
                    data={
                        "run_id": run_id,
                        "step_id": step_id,
                        "scene_id": scene_id,
                        "progress_pct": 1.0,
                        "elapsed_sec": elapsed,
                        "status": "succeeded",
                        "message": "Video generated!",
                        "task_id": task_id,
                    }
                ))
                break
            
            elif status == "FAILED":
                await self.emit(story_id, StreamEvent(
                    type=EventType.STEP_FAILED,
                    data={
                        "run_id": run_id,
                        "step_id": step_id,
                        "scene_id": scene_id,
                        "status": "failed",
                        "message": "Video generation failed",
                    }
                ))
                raise Exception("Video generation failed")
        
        # Fetch output
        step = self._provider.fetch_output(task_id, step)
        video_url = step.assets[0].url
        
        # Download and extract exit frame
        video_bytes = await download_url_to_bytes(video_url)
        exit_frame = extract_last_frame_png(video_bytes)
        
        exit_frame_key = build_key("stories", story_id, "scenes", f"scene_{scene_id}_exit.png")
        exit_frame_url = upload_bytes(exit_frame, exit_frame_key, "image/png")
        
        return {
            "video_url": video_url,
            "exit_frame_url": exit_frame_url,
            "task_id": task_id,
            "run_id": run_id,
        }
    
    async def generate_story(
        self,
        story_id: str,
        scenes: list[dict],
        pool: Any,
    ) -> dict:
        """
        Generate multiple scenes with streaming.
        
        Each scene links to previous via exit frame.
        """
        run_id = str(uuid.uuid4())[:8]
        
        await self.emit(story_id, StreamEvent(
            type=EventType.PIPELINE_STARTED,
            data={
                "run_id": run_id,
                "message": f"Starting story generation: {len(scenes)} scenes",
                "total_scenes": len(scenes),
            }
        ))
        
        asset_manager = AssetManager(pool)
        results = []
        previous_exit_url = None
        
        for i, scene in enumerate(scenes):
            scene_id = scene.get("id", i + 1)
            title = scene.get("title", f"Scene {scene_id}")
            prompt = scene.get("prompt", "")
            
            # Use i2v model after first scene
            model = "happyhorse-1.1-t2v" if i == 0 else "happyhorse-1.1-i2v"
            refs = [previous_exit_url] if previous_exit_url else None
            
            try:
                result = await self.generate_scene(
                    story_id=story_id,
                    scene_id=scene_id,
                    title=title,
                    prompt=prompt,
                    model=model,
                    references=refs,
                )
                
                # Register assets
                video_asset = await asset_manager.register_asset(
                    story_id=story_id,
                    entity_type="scene",
                    entity_id=str(scene_id),
                    asset_type="video",
                    storage_key=f"stories/{story_id}/scenes/scene_{scene_id}.mp4",
                    storage_url=result["video_url"],
                    mime_type="video/mp4",
                    tags=["generated", f"scene_{scene_id}"],
                    metadata={"run_id": run_id, "model": model},
                )
                
                exit_asset = await asset_manager.register_asset(
                    story_id=story_id,
                    entity_type="scene",
                    entity_id=str(scene_id),
                    asset_type="image",
                    storage_key=build_key("stories", story_id, "scenes", f"scene_{scene_id}_exit.png"),
                    storage_url=result["exit_frame_url"],
                    mime_type="image/png",
                    tags=["exit_frame", f"scene_{scene_id}"],
                    metadata={"source_scene": i},
                    parent_asset_id=video_asset.id,
                )
                
                results.append({
                    "scene_id": scene_id,
                    "title": title,
                    "video_url": result["video_url"],
                    "exit_frame_url": result["exit_frame_url"],
                    "video_asset_id": video_asset.id,
                    "exit_asset_id": exit_asset.id,
                    "status": "completed",
                })
                
                previous_exit_url = result["exit_frame_url"]
                
            except Exception as e:
                results.append({
                    "scene_id": scene_id,
                    "title": title,
                    "status": "failed",
                    "error": str(e),
                })
        
        # Emit completion
        status = "completed" if all(r.get("status") == "completed" for r in results) else "failed"
        await self.emit(story_id, StreamEvent(
            type=EventType.PIPELINE_COMPLETED if status == "completed" else EventType.PIPELINE_FAILED,
            data={
                "run_id": run_id,
                "status": status,
                "completed": sum(1 for r in results if r.get("status") == "completed"),
                "failed": sum(1 for r in results if r.get("status") == "failed"),
            }
        ))
        
        return {"story_id": story_id, "run_id": run_id, "scenes": results, "status": status}


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED AGENT EXECUTOR
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None


class UnifiedAgentExecutor:
    """
    Executes tools for the unified agent.
    
    Handles:
    - Tool lookup and execution
    - Tool result formatting
    - Error handling
    """
    
    def __init__(self):
        self._tools: dict[str, callable] = {}
        self.max_iterations = 10
    
    def register_tool(self, name: str, func: callable) -> None:
        """Register a tool function."""
        self._tools[name] = func
    
    async def execute(
        self,
        tool_name: str,
        arguments: dict,
        pool: Any,
    ) -> ToolResult:
        """Execute a tool by name."""
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
        
        try:
            func = self._tools[tool_name]
            result = await func(pool, **arguments)
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
            )
    
    def get_tool_definitions(self) -> list[dict]:
        """Get OpenAPI-style tool definitions for LLM."""
        definitions = []
        for name, func in self._tools.items():
            # Try to get docstring info
            doc = func.__doc__ or ""
            desc = doc.split("\n")[0] if doc else name
            
            # Try to get parameters from signature
            import inspect
            sig = inspect.signature(func)
            params = {
                "type": "object",
                "properties": {},
                "required": [],
            }
            
            for param_name, param in sig.parameters.items():
                if param_name == "pool":
                    continue
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                
                params["properties"][param_name] = {
                    "type": param_type,
                    "description": f"Parameter: {param_name}",
                }
            
            definitions.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": params,
                },
            })
        
        return definitions


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert AI production assistant for Dysentry, an AI-powered video creation platform.

Your role is to help users create professional short-form video content through natural conversation.

## Your Capabilities

1. **Story Management**: Create, edit, and manage video stories with episodes and scenes
2. **Scene Generation**: Generate 5-second video clips using AI (DashScope/Wan models)
3. **Character Consistency**: Maintain visual consistency using reference images
4. **Frame Extraction**: Extract screenshots from videos for reference
5. **Scene Continuity**: Link scenes using exit frames for smooth transitions
6. **Video Assembly**: Combine approved scenes into final episodes
7. **Quality Control**: Review and approve scenes, regenerate if needed
8. **Asset Management**: Track all media assets with versioning

## Data Model

- **Stories** contain **Episodes**
- **Episodes** contain **Scenes** (each ~5 seconds)
- **Characters** have reference images for consistency
- **Assets** track all media (video, images, audio) with versions

## Scene Workflow

1. Create story → Add scenes → Generate videos
2. Each scene needs: prompt, optional reference images
3. First scene: T2V (text-to-video)
4. Subsequent scenes: I2V (image-to-video) with exit frame from previous
5. Approve scenes → Assemble episode → Export

## Guidelines

- Be helpful, concise, and guide users through video creation
- Ask clarifying questions when needed
- Suggest next steps when appropriate
- For complex tasks, explain what you're doing step by step
- Always confirm before making significant changes

## Tool Usage

Use tools to:
- Create and modify stories, episodes, scenes
- Generate videos and track progress
- Manage characters and references
- Extract frames and screenshots
- Assemble final videos
"""


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ══════════════════════════════════════════════════════════════════════════════

_orchestrator: Optional[UnifiedStreamingOrchestrator] = None
_executor: Optional[UnifiedAgentExecutor] = None


def get_orchestrator() -> UnifiedStreamingOrchestrator:
    """Get or create the global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = UnifiedStreamingOrchestrator()
    return _orchestrator


def get_executor() -> UnifiedAgentExecutor:
    """Get or create the global executor."""
    global _executor
    if _executor is None:
        _executor = UnifiedAgentExecutor()
    return _executor
