"""
Chat API - Conversational interface for video production workflow

Provides a natural language interface to the entire Dysentry video production system
using the OpenHands Agent SDK.

Features:
- Natural language scene generation
- Story creation from prompts
- Scene regeneration and editing
- Job status monitoring
- Video screenshot extraction
- Character reference management
- Conversation history
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user, user_id
from db.connection import get_pool
from job_queue import enqueue_job, WORKLOAD_STORY, WORKLOAD_MEDIA
from pipeline.story_agent import get_client
from pipeline.media_tools import extract_last_frame_png
from storage.b2 import upload_bytes, build_key


router = APIRouter(prefix="/pipeline/chat", tags=["chat"])


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: str = Field(description="ISO timestamp")
    action: Optional[str] = Field(None, description="Action taken, if any")
    tool_calls: Optional[list[dict]] = Field(None, description="Tool calls made")


class ChatConversation(BaseModel):
    id: str
    user_id: str
    story_id: Optional[str] = None
    messages: list[ChatMessage] = []
    created_at: str
    updated_at: str
    title: Optional[str] = "New Conversation"


class ChatRequest(BaseModel):
    message: str = Field(description="User message")
    conversation_id: Optional[str] = Field(None, description="Continue existing conversation")
    story_id: Optional[str] = Field(None, description="Associated story ID")
    system_context: Optional[str] = Field(None, description="Additional system context")
    title: Optional[str] = Field(None, description="Story title to use when creating a draft")
    brief: Optional[str] = Field(None, description="Short project brief")
    duration_seconds: Optional[int] = Field(None, ge=1, le=60, description="Target duration in seconds")
    frame_ratio: Optional[str] = Field(None, description="Aspect ratio such as 16:9 or 9:16")
    create_story: bool = Field(default=False, description="Create a new draft story from the brief")


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    action: Optional[str] = None
    data: Optional[dict] = None
    suggestions: Optional[list[str]] = None
    needs_approval: bool = False


class ConversationListResponse(BaseModel):
    conversations: list[dict]
    total: int


# ─── Redis Keys ───────────────────────────────────────────────────────────────

def _chat_key(user_id: str, conv_id: str) -> str:
    return f"chat:conversation:{user_id}:{conv_id}"


def _chat_index_key(user_id: str) -> str:
    return f"chat:index:{user_id}"


# ─── LLM Client ──────────────────────────────────────────────────────────────

async def _get_llm_response(messages: list[dict], tools: list[dict]) -> dict:
    """Get response from LLM with tools using OpenHands SDK."""
    try:
        from openhands.sdk import LLM, Agent, Conversation
        from openhands.tools.file_editor import FileEditorTool
        from openhands.tools.terminal import TerminalTool
        import os
        
        # Build system prompt
        system_prompt = """You are an expert video production assistant for Dysentry, an AI-powered video creation platform.

You help users create professional short-form video content through natural conversation.

Your capabilities:
1. Create stories from natural language descriptions
2. Generate video scenes with AI
3. Manage characters and references
4. Monitor generation progress
5. Edit and regenerate scenes
6. Extract frames from videos
7. Combine scenes into final videos

Always be helpful, concise, and guide users through the video creation process.
Ask clarifying questions when needed.
Suggest next steps when appropriate.

Available data:
- Stories have episodes, which have scenes (5 seconds each)
- Characters need reference images before scene generation
- Scenes have status: pending → generating → completed → approved
- Final video is created by combining approved scenes
"""
        
        # Get API key
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            return {"content": "LLM API key not configured", "tool_calls": None}
        
        # Initialize LLM
        llm = LLM(
            model="qwen-plus",
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # Create agent with tools
        agent = Agent(
            llm=llm,
            tools=[],
            system_prompt=system_prompt
        )
        
        # Build conversation
        conversation = Conversation(agent=agent, workspace="/workspace")
        
        # Add messages to conversation
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                conversation.send_message(content, image_urls=msg.get("image_urls"))
            elif role == "assistant":
                pass  # Skip assistant messages
        
        # Run agent
        conversation.run()
        
        # Get final response
        response = conversation.get_final_response()
        return {"content": response, "tool_calls": None}
        
    except ImportError as e:
        return {"content": f"OpenHands SDK not available: {str(e)}. Using simple response.", "tool_calls": None}
    except Exception as e:
        return {"content": f"I encountered an error: {str(e)}", "tool_calls": None}


# ─── Tool Definitions ─────────────────────────────────────────────────────────

def get_tool_definitions() -> list[dict]:
    """Return OpenAPI-style tool definitions for the agent."""
    return [
        {
            "type": "function",
            "function": {
                "name": "create_story",
                "description": "Create a new video story from a description. The story will have episodes and scenes automatically planned.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Story title"},
                        "description": {"type": "string", "description": "Detailed description of the story"},
                        "style": {"type": "string", "description": "Visual style (cinematic, anime, realistic)", "default": "cinematic"},
                        "num_scenes": {"type": "integer", "description": "Number of scenes (default 5)", "default": 5},
                        "duration_seconds": {"type": "integer", "description": "Target duration in seconds", "default": 5},
                        "frame_ratio": {"type": "string", "description": "Aspect ratio such as 16:9 or 9:16", "default": "16:9"},
                        "workflow_type": {"type": "string", "description": "Workflow type", "default": "brand_campaign"}
                    },
                    "required": ["title", "description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_story",
                "description": "Get details about a story including episodes and scenes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID"}
                    },
                    "required": ["story_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_stories",
                "description": "List all stories for the current user.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "approve_outline",
                "description": "Approve a story outline to start generation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID"}
                    },
                    "required": ["story_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "start_generation",
                "description": "Start video generation for a story. This queues generation jobs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID"}
                    },
                    "required": ["story_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_job_status",
                "description": "Get the status of a generation job.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "description": "Job ID"}
                    },
                    "required": ["job_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "wait_for_job",
                "description": "Wait for a job to complete. Poll until done.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "description": "Job ID"},
                        "timeout_seconds": {"type": "integer", "description": "Max wait time", "default": 300}
                    },
                    "required": ["job_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "regenerate_scene",
                "description": "Regenerate a specific scene with a new prompt.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "string", "description": "Scene ID"},
                        "new_prompt": {"type": "string", "description": "New scene description"}
                    },
                    "required": ["scene_id", "new_prompt"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_scene",
                "description": "Get details about a specific scene.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "string", "description": "Scene ID"}
                    },
                    "required": ["scene_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "approve_scene",
                "description": "Approve a scene for final video assembly.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "string", "description": "Scene ID"}
                    },
                    "required": ["scene_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_video_frame",
                "description": "Extract a frame from a video as a screenshot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_url": {"type": "string", "description": "URL of the video"},
                        "timestamp": {"type": "number", "description": "Seconds into the video", "default": 3.0}
                    },
                    "required": ["video_url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "assemble_episode",
                "description": "Assemble all approved scenes into a final video.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "episode_id": {"type": "string", "description": "Episode ID"}
                    },
                    "required": ["episode_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_character",
                "description": "Create a new character for a story.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID"},
                        "name": {"type": "string", "description": "Character name"},
                        "description": {"type": "string", "description": "Character description"}
                    },
                    "required": ["story_id", "name", "description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_characters",
                "description": "Get all characters for a story.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID"}
                    },
                    "required": ["story_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "regenerate_outline",
                "description": "Regenerate the story outline from the brief.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID"}
                    },
                    "required": ["story_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_story",
                "description": "Update story properties like title, num_scenes, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID"},
                        "title": {"type": "string", "description": "New title"},
                        "num_scenes": {"type": "integer", "description": "Number of scenes"}
                    },
                    "required": ["story_id"]
                }
            }
        }
    ]


# ─── Tool Implementations ───

async def _tool_create_story(params: dict, user_id: str) -> dict:
    """Create a new story."""
    pool = await get_pool()
    
    # Create story via existing endpoint logic
    title = params.get("title", "Untitled Story")
    description = params.get("description", "")
    style = params.get("style", "cinematic")
    num_scenes = params.get("num_scenes", 5)
    
    row = await pool.fetchrow(
        """INSERT INTO stories (title, prompt, genre, style, num_scenes, workflow_type, status, owner_id)
           VALUES ($1, $2, 'action', $3, $4, 'creator_series', 'draft', $5)
           RETURNING id, title, status""",
        title, description, style, num_scenes, user_id
    )
    
    return {"story_id": row["id"], "title": row["title"], "status": row["status"]}


async def _tool_get_story(params: dict, user_id: str) -> dict:
    """Get story details."""
    pool = await get_pool()
    story_id = params["story_id"]
    
    row = await pool.fetchrow(
        "SELECT * FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id
    )
    
    if not row:
        raise ValueError(f"Story not found: {story_id}")
    
    # Get episodes and scenes
    episodes = await pool.fetch(
        "SELECT * FROM episodes WHERE story_id = $1 ORDER BY episode_number",
        story_id
    )
    
    scenes = await pool.fetch(
        """SELECT s.*, e.episode_number 
           FROM scenes s JOIN episodes e ON s.episode_id = e.id
           WHERE e.story_id = $1
           ORDER BY e.episode_number, s.scene_number""",
        story_id
    )
    
    return {
        "story_id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "episodes": [dict(ep) for ep in episodes],
        "scenes": [dict(sc) for sc in scenes],
        "created_at": str(row["created_at"])
    }


async def _tool_list_stories(params: dict, user_id: str) -> dict:
    """List all stories."""
    pool = await get_pool()
    
    rows = await pool.fetch(
        """SELECT id, title, status, created_at 
           FROM stories WHERE owner_id = $1 
           ORDER BY created_at DESC LIMIT 50""",
        user_id
    )
    
    return {"stories": [dict(r) for r in rows]}


async def _tool_approve_outline(params: dict, user_id: str) -> dict:
    """Approve story outline."""
    pool = await get_pool()
    story_id = params["story_id"]
    
    row = await pool.fetchrow(
        """UPDATE stories SET status = 'approved', approval_status = 'approved', approved_at = now()
           WHERE id = $1 AND owner_id = $2 AND status = 'draft'
           RETURNING id, status""",
        story_id, user_id
    )
    
    if not row:
        raise ValueError("Story not found or already approved")
    
    return {"story_id": row["id"], "status": row["status"]}


async def _tool_start_generation(params: dict, user_id: str) -> dict:
    """Start story generation."""
    pool = await get_pool()
    story_id = params["story_id"]
    
    # Atomic update to prevent race conditions
    story = await pool.fetchrow(
        """UPDATE stories SET status = 'generating'
           WHERE id = $1 AND owner_id = $2 AND status = 'approved'
           RETURNING id""",
        story_id, user_id
    )
    
    if not story:
        raise ValueError("Story not found or not approved")
    
    # Create job
    job = await pool.fetchrow(
        """INSERT INTO generation_jobs (entity_type, entity_id, status, job_type)
           VALUES ('story', $1, 'pending', 'full_episode')
           RETURNING id""",
        story_id
    )
    
    job_id = str(job["id"])
    await enqueue_job(job_id, WORKLOAD_STORY)
    
    return {"job_id": job_id, "story_id": story_id, "status": "queued"}


async def _tool_get_job_status(params: dict, user_id: str) -> dict:
    """Get job status."""
    pool = await get_pool()
    job_id = params["job_id"]
    
    row = await pool.fetchrow(
        """SELECT j.*, s.title as story_title 
           FROM generation_jobs j JOIN stories s ON j.entity_id = s.id
           WHERE j.id = $1 AND s.owner_id = $2""",
        job_id, user_id
    )
    
    if not row:
        raise ValueError(f"Job not found: {job_id}")
    
    return {
        "job_id": str(row["id"]),
        "status": row["status"],
        "progress": row.get("progress", 0),
        "current_step": row.get("current_step", "queued"),
        "error": row.get("error")
    }


async def _tool_wait_for_job(params: dict, user_id: str) -> dict:
    """Wait for job completion (with polling)."""
    import asyncio
    pool = await get_pool()
    job_id = params["job_id"]
    timeout = params.get("timeout_seconds", 300)
    start = datetime.utcnow()
    
    while (datetime.utcnow() - start).total_seconds() < timeout:
        row = await pool.fetchrow(
            """SELECT j.* FROM generation_jobs j 
               JOIN stories s ON j.entity_id = s.id
               WHERE j.id = $1 AND s.owner_id = $2""",
            job_id, user_id
        )
        
        if not row:
            raise ValueError(f"Job not found: {job_id}")
        
        status = row["status"]
        if status in ("completed", "failed", "cancelled"):
            return {
                "job_id": job_id,
                "status": status,
                "progress": row.get("progress", 100 if status == "completed" else 0)
            }
        
        await asyncio.sleep(5)
    
    return {"job_id": job_id, "status": "timeout", "message": "Job still running"}


async def _tool_regenerate_scene(params: dict, user_id: str) -> dict:
    """Regenerate a scene."""
    pool = await get_pool()
    scene_id = params["scene_id"]
    new_prompt = params.get("new_prompt", "")
    
    # Update scene prompt
    row = await pool.fetchrow(
        """UPDATE scenes SET prompt = $1, status = 'pending'
           WHERE id = $2 
           AND episode_id IN (SELECT id FROM episodes WHERE story_id IN 
               (SELECT id FROM stories WHERE owner_id = $3))
           RETURNING id, status""",
        new_prompt, scene_id, user_id
    )
    
    if not row:
        raise ValueError("Scene not found")
    
    # Create regeneration job
    job = await pool.fetchrow(
        """INSERT INTO generation_jobs (entity_type, entity_id, status, job_type)
           VALUES ('scene', $1, 'pending', 'scene_regen')
           RETURNING id""",
        scene_id
    )
    
    job_id = str(job["id"])
    await enqueue_job(job_id, WORKLOAD_MEDIA)
    
    return {"job_id": job_id, "scene_id": row["id"], "status": "queued"}


async def _tool_get_scene(params: dict, user_id: str) -> dict:
    """Get scene details."""
    pool = await get_pool()
    scene_id = params["scene_id"]
    
    row = await pool.fetchrow(
        """SELECT s.*, e.story_id, e.episode_number 
           FROM scenes s JOIN episodes e ON s.episode_id = e.id
           WHERE s.id = $1 AND e.story_id IN (SELECT id FROM stories WHERE owner_id = $2)""",
        scene_id, user_id
    )
    
    if not row:
        raise ValueError("Scene not found")
    
    return dict(row)


async def _tool_approve_scene(params: dict, user_id: str) -> dict:
    """Approve a scene."""
    pool = await get_pool()
    scene_id = params["scene_id"]
    
    row = await pool.fetchrow(
        """UPDATE scenes SET approved = true
           WHERE id = $1 
           AND episode_id IN (SELECT id FROM episodes WHERE story_id IN 
               (SELECT id FROM stories WHERE owner_id = $2))
           RETURNING id, approved""",
        scene_id, user_id
    )
    
    if not row:
        raise ValueError("Scene not found")
    
    return {"scene_id": row["id"], "approved": row["approved"]}


async def _tool_extract_frame(params: dict, user_id: str) -> dict:
    """Extract frame from video."""
    video_url = params["video_url"]
    timestamp = params.get("timestamp", 3.0)
    
    frame_bytes = await extract_last_frame_png(video_url, timestamp)
    if not frame_bytes:
        raise ValueError("Failed to extract frame")
    
    key = build_key("frames", str(uuid.uuid4())[:8], "frame.png")
    url = upload_bytes(frame_bytes, key, "image/png")
    
    return {"screenshot_url": url, "timestamp": timestamp}


async def _tool_assemble_episode(params: dict, user_id: str) -> dict:
    """Assemble episode from approved scenes."""
    pool = await get_pool()
    episode_id = params["episode_id"]
    
    # Verify ownership
    ep = await pool.fetchrow(
        """SELECT e.* FROM episodes e 
           JOIN stories s ON e.story_id = s.id
           WHERE e.id = $1 AND s.owner_id = $2""",
        episode_id, user_id
    )
    
    if not ep:
        raise ValueError("Episode not found")
    
    # Create assembly job
    job = await pool.fetchrow(
        """INSERT INTO generation_jobs (entity_type, entity_id, status, job_type)
           VALUES ('episode', $1, 'pending', 'assemble_episode')
           RETURNING id""",
        episode_id
    )
    
    job_id = str(job["id"])
    await enqueue_job(job_id, WORKLOAD_STORY)
    
    return {"job_id": job_id, "episode_id": episode_id, "status": "queued"}


async def _tool_create_character(params: dict, user_id: str) -> dict:
    """Create a character."""
    pool = await get_pool()
    story_id = params["story_id"]
    name = params["name"]
    description = params["description"]
    
    row = await pool.fetchrow(
        """INSERT INTO characters (story_id, name, description, status, owner_id)
           VALUES ($1, $2, $3, 'draft', $4)
           RETURNING id, name, status""",
        story_id, name, description, user_id
    )
    
    return {"character_id": str(row["id"]), "name": row["name"], "status": row["status"]}


async def _tool_get_characters(params: dict, user_id: str) -> dict:
    """Get story characters."""
    pool = await get_pool()
    story_id = params["story_id"]
    
    rows = await pool.fetch(
        """SELECT * FROM characters WHERE story_id = $1 AND owner_id = $2""",
        story_id, user_id
    )
    
    return {"characters": [dict(r) for r in rows]}


async def _tool_regenerate_outline(params: dict, user_id: str) -> dict:
    """Regenerate story outline."""
    pool = await get_pool()
    story_id = params["story_id"]
    new_prompt = params.get("new_prompt", "")
    
    row = await pool.fetchrow(
        """UPDATE stories SET status = 'draft', prompt = COALESCE(NULLIF($1, ''), prompt)
           WHERE id = $2 AND owner_id = $3
           RETURNING id, status""",
        new_prompt, story_id, user_id
    )
    
    if not row:
        raise ValueError("Story not found")
    
    # Create regeneration job
    job = await pool.fetchrow(
        """INSERT INTO generation_jobs (entity_type, entity_id, status, job_type)
           VALUES ('story', $1, 'pending', 'regenerate_outline')
           RETURNING id""",
        story_id
    )
    
    job_id = str(job["id"])
    await enqueue_job(job_id, WORKLOAD_STORY)
    
    return {"job_id": job_id, "story_id": row["id"], "status": "queued"}


async def _tool_update_story(params: dict, user_id: str) -> dict:
    """Update story properties."""
    pool = await get_pool()
    story_id = params["story_id"]
    
    updates = []
    values = []
    idx = 1
    
    if "title" in params:
        updates.append(f"title = ${idx}")
        values.append(params["title"])
        idx += 1
    
    if "num_scenes" in params:
        updates.append(f"num_scenes = ${idx}")
        values.append(params["num_scenes"])
        idx += 1
    
    if not updates:
        raise ValueError("No updates provided")
    
    values.extend([story_id, user_id])
    
    row = await pool.fetchrow(
        f"""UPDATE stories SET {', '.join(updates)}
            WHERE id = ${idx} AND owner_id = ${idx + 1}
            RETURNING id, title, num_scenes""",
        *values
    )
    
    if not row:
        raise ValueError("Story not found")
    
    return dict(row)


# ─── Tool Registry ────────────────────────────────────────────────────────────

TOOL_HANDLERS = {
    "create_story": _tool_create_story,
    "get_story": _tool_get_story,
    "list_stories": _tool_list_stories,
    "approve_outline": _tool_approve_outline,
    "start_generation": _tool_start_generation,
    "get_job_status": _tool_get_job_status,
    "wait_for_job": _tool_wait_for_job,
    "regenerate_scene": _tool_regenerate_scene,
    "get_scene": _tool_get_scene,
    "approve_scene": _tool_approve_scene,
    "extract_video_frame": _tool_extract_frame,
    "assemble_episode": _tool_assemble_episode,
    "create_character": _tool_create_character,
    "get_characters": _tool_get_characters,
    "regenerate_outline": _tool_regenerate_outline,
    "update_story": _tool_update_story,
}


# ─── Conversation Management ──────────────────────────────────────────────────

async def _get_redis() -> redis.Redis:
    return redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True
    )


async def _save_conversation(conv: ChatConversation) -> None:
    """Save conversation to Redis."""
    r = await _get_redis()
    key = _chat_key(conv.user_id, conv.id)
    await r.setex(key, timedelta(days=30), json.dumps(conv.model_dump()))
    
    # Update index - convert ISO string to timestamp
    index_key = _chat_index_key(conv.user_id)
    updated_ts = datetime.fromisoformat(conv.updated_at.replace("Z", "+00:00")).timestamp()
    await r.zadd(index_key, {conv.id: updated_ts})
    await r.aclose()


async def _load_conversation(user_id: str, conv_id: str) -> Optional[ChatConversation]:
    """Load conversation from Redis."""
    r = await _get_redis()
    key = _chat_key(user_id, conv_id)
    data = await r.get(key)
    await r.aclose()
    
    if data:
        return ChatConversation(**json.loads(data))
    return None


async def _list_conversations(user_id: str, limit: int = 20) -> list[ChatConversation]:
    """List user's conversations."""
    r = await _get_redis()
    index_key = _chat_index_key(user_id)
    conv_ids = await r.zrevrange(index_key, 0, limit - 1)
    
    conversations = []
    for conv_id in conv_ids:
        conv = await _load_conversation(user_id, conv_id)
        if conv:
            conversations.append(conv)
    
    await r.aclose()
    return conversations


# ─── API Endpoints ───────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user=Depends(get_current_user),
):
    """
    Chat with the video production assistant.
    
    This endpoint provides a natural language interface to the entire
    video production workflow. The assistant can:
    - Create and manage stories
    - Generate video scenes
    - Monitor job progress
    - Edit and regenerate content
    - Extract frames from videos
    """
    uid = user_id(user)
    
    # Load or create conversation
    if body.conversation_id:
        conv = await _load_conversation(uid, body.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = ChatConversation(
            id=str(uuid.uuid4())[:12],
            user_id=uid,
            story_id=body.story_id,
            messages=[],
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            title="New Conversation"
        )
    
    # Add system context if provided
    if body.system_context:
        conv.messages.append(ChatMessage(
            role="system",
            content=body.system_context,
            timestamp=datetime.utcnow().isoformat()
        ))
    
    # Add user message
    user_msg = ChatMessage(
        role="user",
        content=body.message,
        timestamp=datetime.utcnow().isoformat()
    )
    conv.messages.append(user_msg)
    
    # Get tool definitions
    tools = get_tool_definitions()
    
    # Convert messages for LLM
    llm_messages = [
        {"role": m.role, "content": m.content}
        for m in conv.messages
        if m.role in ("user", "assistant", "system")
    ]
    
    # Get LLM response with tools
    response = await _get_llm_response(llm_messages, tools)
    
    # Parse response - handle potential tool calls
    assistant_content = response.get("content", "")
    
    # Check if response indicates tool usage
    action = None
    data = None
    
    # Simple response parsing
    if "story_id" in assistant_content.lower() or "scene" in assistant_content.lower():
        # Try to extract structured info
        for line in assistant_content.split("\n"):
            if "story_id:" in line.lower():
                data = {"info": assistant_content}
                break
    
    # Create assistant message
    assistant_msg = ChatMessage(
        role="assistant",
        content=assistant_content,
        timestamp=datetime.utcnow().isoformat(),
        action=action
    )
    conv.messages.append(assistant_msg)
    
    # Update conversation
    conv.updated_at = datetime.utcnow().isoformat()
    if not conv.title or conv.title == "New Conversation":
        # Generate title from first user message
        conv.title = body.message[:50] + ("..." if len(body.message) > 50 else "")
    
    await _save_conversation(conv)
    
    # Generate suggestions
    suggestions = []
    if "story" in body.message.lower() and "create" in body.message.lower():
        suggestions = [
            "Approve the outline to start generation",
            "Tell me more about the story direction",
            "Add characters to the story"
        ]
    elif "generate" in body.message.lower():
        suggestions = [
            "Check the generation progress",
            "Wait for scenes to complete",
            "View the generated scenes"
        ]
    
    return ChatResponse(
        conversation_id=conv.id,
        message=assistant_content,
        action=action,
        data=data,
        suggestions=suggestions if suggestions else None
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 20,
    user=Depends(get_current_user),
):
    """List all conversations for the current user."""
    uid = user_id(user)
    conversations = await _list_conversations(uid, limit)
    
    return ConversationListResponse(
        conversations=[
            {
                "id": c.id,
                "title": c.title,
                "story_id": c.story_id,
                "message_count": len(c.messages),
                "created_at": c.created_at,
                "updated_at": c.updated_at
            }
            for c in conversations
        ],
        total=len(conversations)
    )


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user=Depends(get_current_user),
):
    """Get a specific conversation with all messages."""
    uid = user_id(user)
    conv = await _load_conversation(uid, conversation_id)
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conv


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user=Depends(get_current_user),
):
    """Delete a conversation."""
    uid = user_id(user)
    r = await _get_redis()
    
    key = _chat_key(uid, conversation_id)
    index_key = _chat_index_key(uid)
    
    await r.delete(key)
    await r.zrem(index_key, conversation_id)
    await r.aclose()
    
    return {"status": "deleted", "conversation_id": conversation_id}
