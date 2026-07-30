"""
Streaming Orchestrator - Real-time event streaming for frontend

Provides Server-Sent Events (SSE) streaming of generation progress
with GenBlaze-style events for real-time UI updates.

Features:
- SSE endpoint for streaming events to frontend
- ProgressEvent support from GenBlaze
- Scene-level status updates
- Tool call notifications
- Preview URL support

Usage:
    from pipeline.streaming_orchestrator import StreamingOrchestrator
    
    orchestrator = StreamingOrchestrator()
    
    async with orchestrator.stream(story_id) as events:
        async for event in events:
            # Send to frontend via SSE
            yield f"data: {event.json()}\n\n"
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncGenerator, Optional

import httpx

from pipeline.providers.dashscope import DashScopeVideoProvider
from pipeline.catalog import ContinuityState, build_scene_context, inject_continuity_into_prompt
from pipeline.media_tools import extract_last_frame_png, concatenate_video_files
from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from genblaze_core.models.step import Step
from genblaze_core import Modality


# ─── Event Types (matching GenBlaze StreamEvent) ────────────────────────────────

class StreamEventType(str, Enum):
    """GenBlaze-compatible event types."""
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    STEP_QUEUED = "step.queued"
    STEP_STARTED = "step.started"
    STEP_PROGRESS = "step.progress"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    AGENT_ITERATION_STARTED = "agent.iteration.started"
    AGENT_ITERATION_EVALUATED = "agent.iteration.evaluated"


@dataclass
class SceneProgressEvent:
    """Progress event for scene generation."""
    type: str = "step.progress"
    timestamp: str = ""
    run_id: str = ""
    step_id: str = ""
    provider: str = "dashscope-video"
    model: str = ""
    status: str = "processing"  # submitted, processing, succeeded, failed
    progress_pct: float = 0.0
    elapsed_sec: float = 0.0
    message: str = ""
    preview_url: Optional[str] = None
    request_id: Optional[str] = None
    scene_id: Optional[int] = None
    scene_title: str = ""
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "elapsed_sec": self.elapsed_sec,
            "message": self.message,
            "preview_url": self.preview_url,
            "request_id": self.request_id,
            "scene_id": self.scene_id,
            "scene_title": self.scene_title,
        })
    
    def to_sse(self) -> str:
        return f"data: {self.to_json()}\n\n"


@dataclass
class ToolCallEvent:
    """Event for tool calls (LLM tool invocations)."""
    type: str = "tool.call"
    timestamp: str = ""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    result: Optional[dict] = None
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "result": self.result,
        })


# ─── Streaming Orchestrator ────────────────────────────────────────────────────

class StreamingOrchestrator:
    """
    Orchestrator with SSE streaming support.
    
    Wraps ConversationalOrchestrator with real-time event streaming
    for frontend integration.
    """
    
    def __init__(self):
        self._active_streams: dict[str, asyncio.Queue] = {}
        self._provider = DashScopeVideoProvider()
    
    async def emit(
        self,
        story_id: str,
        event: SceneProgressEvent,
    ) -> None:
        """Emit an event to all stream subscribers for this story."""
        if story_id in self._active_streams:
            await self._active_streams[story_id].put(event)
    
    async def _put_event(self, story_id: str, event: SceneProgressEvent) -> None:
        """Internal method to put event into queue (also prints for testing)."""
        if story_id in self._active_streams:
            await self._active_streams[story_id].put(event)
        # Also print for visibility
        print(f"  [{event.type}] {event.status}: {event.message}")
    
    async def stream(
        self,
        story_id: str,
    ) -> AsyncGenerator[SceneProgressEvent, None]:
        """Get async generator for streaming events."""
        queue: asyncio.Queue[SceneProgressEvent] = asyncio.Queue()
        self._active_streams[story_id] = queue
        
        try:
            while True:
                event = await queue.get()
                yield event
                if event.status in ("succeeded", "failed"):
                    break
        finally:
            del self._active_streams[story_id]
    
    async def generate_scene_streaming(
        self,
        story_id: str,
        title: str,
        prompt: str,
        scene_id: int,
        model: str = "happyhorse-1.1-t2v",
        references: Optional[list[str]] = None,
    ) -> tuple[str, str, bytes, str]:
        """
        Generate scene with streaming events.
        
        Emits progress events while generating.
        Returns (video_url, exit_frame_url, video_bytes, task_id).
        """
        run_id = str(uuid.uuid4())[:8]
        step_id = f"scene_{scene_id}"
        references = references or []
        start_time = time.time()
        
        # Emit started event
        event = SceneProgressEvent(
            type=StreamEventType.STEP_STARTED.value,
            timestamp=datetime.utcnow().isoformat(),
            run_id=run_id,
            step_id=step_id,
            model=model,
            status="submitted",
            progress_pct=0.0,
            elapsed_sec=0.0,
            message=f"Starting scene {scene_id}: {title}",
            scene_id=scene_id,
            scene_title=title,
        )
        await self._put_event(story_id, event)
        
        # Build step
        step = Step(provider='dashscope-video', model=model, prompt=prompt)
        step.params = {
            'duration': 5,
            'resolution': '1080P',
            'ratio': '16:9',
            'seed': int(time.time()) % 10000,
        }
        step.inputs = references
        step.modality = Modality.VIDEO
        
        # Submit
        print(f"[streaming] Submitting task for scene {scene_id}")
        task_id = self._provider.submit(step)
        
        # Emit processing event
        event = SceneProgressEvent(
            type=StreamEventType.STEP_PROGRESS.value,
            timestamp=datetime.utcnow().isoformat(),
            run_id=run_id,
            step_id=step_id,
            model=model,
            status="processing",
            progress_pct=0.1,
            elapsed_sec=time.time() - start_time,
            message="Task submitted, waiting for processing...",
            request_id=task_id,
            scene_id=scene_id,
            scene_title=title,
        )
        await self._put_event(story_id, event)
        
        # Poll with progress updates
        last_pct = 0.1
        while True:
            await asyncio.sleep(15)  # Poll every 15 seconds
            
            status = self._provider._poll_status(task_id, timeout=5)
            elapsed = time.time() - start_time
            
            if status == "RUNNING":
                # Estimate progress (DashScope typically takes 60-120s)
                last_pct = min(0.1 + (elapsed / 90) * 0.7, 0.9)
                
                event = SceneProgressEvent(
                    type=StreamEventType.STEP_PROGRESS.value,
                    timestamp=datetime.utcnow().isoformat(),
                    run_id=run_id,
                    step_id=step_id,
                    model=model,
                    status="processing",
                    progress_pct=last_pct,
                    elapsed_sec=elapsed,
                    message=f"Generating video... {int(last_pct * 100)}% complete",
                    request_id=task_id,
                    scene_id=scene_id,
                    scene_title=title,
                )
                await self._put_event(story_id, event)
            
            elif status == "SUCCEEDED":
                event = SceneProgressEvent(
                    type=StreamEventType.STEP_COMPLETED.value,
                    timestamp=datetime.utcnow().isoformat(),
                    run_id=run_id,
                    step_id=step_id,
                    model=model,
                    status="succeeded",
                    progress_pct=1.0,
                    elapsed_sec=elapsed,
                    message="Video generated successfully!",
                    request_id=task_id,
                    scene_id=scene_id,
                    scene_title=title,
                )
                await self._put_event(story_id, event)
                break
            
            elif status == "FAILED":
                event = SceneProgressEvent(
                    type=StreamEventType.STEP_FAILED.value,
                    timestamp=datetime.utcnow().isoformat(),
                    run_id=run_id,
                    step_id=step_id,
                    model=model,
                    status="failed",
                    progress_pct=last_pct,
                    elapsed_sec=elapsed,
                    message="Video generation failed",
                    request_id=task_id,
                    scene_id=scene_id,
                    scene_title=title,
                )
                await self._put_event(story_id, event)
                raise Exception("Video generation failed")
        
        # Fetch output
        print(f"[streaming] Fetching output for task {task_id}")
        step = self._provider.fetch_output(task_id, step)
        video_url = step.assets[0].url
        
        # Download video
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(video_url)
            video_bytes = resp.content
        
        # Extract exit frame
        exit_frame = await extract_last_frame_png(video_bytes)
        exit_frame_url = upload_bytes(
            exit_frame,
            build_key("stories", story_id, "scenes", f"scene_{scene_id}_exit.png"),
            "image/png",
        )
        
        return video_url, exit_frame_url, video_bytes, task_id
    
    async def generate_story_streaming(
        self,
        story_id: str,
        scenes: list[dict],
    ) -> dict:
        """
        Generate multiple scenes with streaming.
        
        Returns final result with all video URLs.
        """
        run_id = str(uuid.uuid4())[:8]
        
        # Emit pipeline started
        await self.emit(story_id, SceneProgressEvent(
            type=StreamEventType.PIPELINE_STARTED.value,
            timestamp=datetime.utcnow().isoformat(),
            run_id=run_id,
            message=f"Starting story generation: {len(scenes)} scenes",
        ))
        
        results = []
        previous_exit_url = None
        
        for i, scene in enumerate(scenes):
            scene_id = scene.get("id", i + 1)
            title = scene.get("title", f"Scene {scene_id}")
            prompt = scene.get("prompt", "")
            
            # Determine model
            model = "happyhorse-1.1-t2v" if i == 0 else "happyhorse-1.1-i2v"
            references = [previous_exit_url] if previous_exit_url else None
            
            try:
                video_url, exit_frame_url, video_bytes, task_id = await self.generate_scene_streaming(
                    story_id=story_id,
                    title=title,
                    prompt=prompt,
                    scene_id=scene_id,
                    model=model,
                    references=references,
                )
                
                results.append({
                    "scene_id": scene_id,
                    "title": title,
                    "video_url": video_url,
                    "exit_frame_url": exit_frame_url,
                    "task_id": task_id,
                    "status": "completed",
                })
                
                previous_exit_url = exit_frame_url
                
            except Exception as e:
                results.append({
                    "scene_id": scene_id,
                    "title": title,
                    "status": "failed",
                    "error": str(e),
                })
        
        # Emit pipeline completed
        status = "completed" if all(r.get("status") == "completed" for r in results) else "failed"
        await self.emit(story_id, SceneProgressEvent(
            type=StreamEventType.PIPELINE_COMPLETED.value if status == "completed" 
                else StreamEventType.PIPELINE_FAILED.value,
            timestamp=datetime.utcnow().isoformat(),
            run_id=run_id,
            message=f"Story generation {status}: {len(results)} scenes",
        ))
        
        return {
            "story_id": story_id,
            "run_id": run_id,
            "scenes": results,
            "status": status,
        }


# ─── Global Instance ───────────────────────────────────────────────────────────

_streaming_orchestrator: Optional[StreamingOrchestrator] = None


def get_streaming_orchestrator() -> StreamingOrchestrator:
    """Get the global streaming orchestrator instance."""
    global _streaming_orchestrator
    if _streaming_orchestrator is None:
        _streaming_orchestrator = StreamingOrchestrator()
    return _streaming_orchestrator
