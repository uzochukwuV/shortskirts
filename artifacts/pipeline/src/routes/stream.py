"""
Streaming Routes - SSE endpoints for real-time frontend updates

Provides Server-Sent Events (SSE) streaming for:
- Scene generation progress
- Story generation progress
- Tool call notifications

Usage:
    # Frontend connects to SSE stream
    EventSource('/pipeline/stories/{story_id}/stream')
    
    # Server pushes events
    event: {type: "step.progress", progress_pct: 0.5, message: "Generating..."}
    event: {type: "step.completed", video_url: "..."}
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_user, user_id
from pipeline.streaming_orchestrator import (
    StreamingOrchestrator,
    SceneProgressEvent,
    get_streaming_orchestrator,
)


router = APIRouter(prefix="/pipeline/stories", tags=["streaming"])


class StreamRequest(BaseModel):
    """Request to start streaming a story generation."""
    story_id: str
    scenes: list[dict]


@router.get("/{story_id}/stream")
async def stream_story_events(
    story_id: str,
    user=Depends(get_current_user),
    orchestrator: StreamingOrchestrator = Depends(get_streaming_orchestrator),
) -> StreamingResponse:
    """
    SSE endpoint for streaming story generation events.
    
    Connect via EventSource to receive real-time updates.
    
    Event types:
    - pipeline.started: Generation started
    - step.started: Scene generation started
    - step.progress: Progress update (progress_pct: 0-1)
    - step.completed: Scene completed (includes video_url)
    - step.failed: Scene failed
    - pipeline.completed: All scenes done
    - pipeline.failed: Generation failed
    
    Example JavaScript:
    ```javascript
    const es = new EventSource('/pipeline/stories/my-story-123/stream');
    es.addEventListener('step.progress', (e) => {
        const data = JSON.parse(e.data);
        console.log(`Progress: ${data.progress_pct * 100}%`);
    });
    es.addEventListener('step.completed', (e) => {
        const data = JSON.parse(e.data);
        console.log(`Video ready: ${data.video_url}`);
    });
    ```
    """
    
    async def event_generator() -> AsyncGenerator[bytes, None]:
        """Generate SSE events for the story."""
        queue: asyncio.Queue[SceneProgressEvent] = asyncio.Queue()
        orchestrator._active_streams[story_id] = queue
        
        try:
            # Send initial connection event
            yield b"data: {\"type\": \"connected\", \"story_id\": \"" + story_id.encode() + b"\"}\n\n"
            
            # Stream events as they come
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield event.to_sse().encode()
                    
                    # End stream on terminal events
                    if event.status in ("succeeded", "failed"):
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield b"data: {\"type\": \"heartbeat\", \"timestamp\": \"" + \
                         f"{event.timestamp}".encode() + b"\"}\n\n"
                        
        except asyncio.CancelledError:
            pass
        finally:
            if story_id in orchestrator._active_streams:
                del orchestrator._active_streams[story_id]
            yield b"data: {\"type\": \"stream.closed\"}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/{story_id}/generate")
async def start_streaming_generation(
    story_id: str,
    request: StreamRequest,
    user=Depends(get_current_user),
    orchestrator: StreamingOrchestrator = Depends(get_streaming_orchestrator),
):
    """
    Start streaming generation for a story.
    
    This endpoint starts the generation in the background
    and returns immediately. Use the SSE stream to receive updates.
    
    Request body:
    ```json
    {
        "story_id": "my-story-123",
        "scenes": [
            {
                "id": 1,
                "title": "Scene 1",
                "prompt": "A samurai at dawn..."
            },
            ...
        ]
    }
    ```
    """
    # Start generation in background
    asyncio.create_task(
        orchestrator.generate_story_streaming(
            story_id=story_id,
            scenes=request.scenes,
        )
    )
    
    return {
        "status": "started",
        "story_id": story_id,
        "scenes_count": len(request.scenes),
        "stream_url": f"/pipeline/stories/{story_id}/stream",
    }


@router.get("/{story_id}/events")
async def get_story_events(
    story_id: str,
    limit: int = 50,
    user=Depends(get_current_user),
) -> dict:
    """
    Get recent events for a story (polling fallback).
    
    Use this as fallback if SSE is not available.
    Returns the last N events for the story.
    """
    # For now, return empty - events are transient
    # In production, you'd store events in Redis/DB
    return {
        "story_id": story_id,
        "events": [],
        "note": "Use SSE stream for real-time events",
    }
