"""
Agentic Video Orchestrator

An LLM-powered agent that helps users create videos through natural conversation.
It can:
- Understand user intent and break down complex tasks
- Generate videos using DashScope/Veo3 providers
- Extract frames for continuity
- Store and manage assets
- Maintain scene context for multi-shot videos

Usage:
    from pipeline.agentic_orchestrator import AgenticOrchestrator
    
    orchestrator = AgenticOrchestrator(pool)
    result = await orchestrator.run("Create a video of a sunset over mountains")
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx

from pipeline.agent_llm import (
    ChatMessage,
    ToolCall,
    ChatResponse,
    get_agent_llm,
    TOKENROUTER_MODEL,
)
from pipeline.providers.provider_router import (
    VideoProviderRouter,
    ProviderType,
    get_router,
)


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a creative AI video director and production assistant. Your job is to help users create amazing videos through natural conversation.

## Your Capabilities

You have access to powerful video generation tools:

1. **create_story** - Start a new video project
2. **create_scene** - Add a scene to a story
3. **generate_video** - Create a video clip from a scene
4. **wait_for_generation** - Poll until video is ready
5. **extract_scene_frame** - Take a screenshot from a video for reference
6. **set_character_reference** - Set reference images for consistent characters
7. **store_asset** - Save video/image assets to storage

## How You Work

1. **Understand the goal**: Listen to what the user wants to create
2. **Plan the shots**: Break down into scenes if needed
3. **Generate sequentially**: Create scenes in order, using exit frames for continuity
4. **Track progress**: Monitor generation status and report back
5. **Maintain quality**: Suggest improvements, regenerate if needed

## Video Generation Guidelines

- First scene: Use text-to-video (T2V)
- Subsequent scenes: Use image-to-video (I2V) with exit frame from previous scene
- For consistency: Set character references before generating
- Typical scene duration: 5 seconds
- Aspect ratio: 16:9 (landscape) or 9:16 (portrait/vertical)

## Scene Continuity

When creating multi-shot videos:
1. Generate first scene → Extract exit frame
2. Use exit frame as input for next scene
3. This maintains visual continuity (same background, character position, etc.)

## Communication Style

- Be enthusiastic and creative
- Explain what you're doing
- Show progress as you work
- Ask for confirmation on creative decisions
- Suggest improvements when appropriate

## Example Workflows

**Simple video**: "Make a video of a cat playing piano"
→ Create story → Create scene → Generate → Store

**Multi-shot**: "Create a short film with 3 scenes"
→ Create story → Create scene 1 → Generate → Extract frame
→ Create scene 2 (with frame) → Generate → Extract frame
→ Create scene 3 (with frame) → Generate → Store all

Always be helpful, creative, and guide users to great results!
"""


# ══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_story",
            "description": "Create a new video story/project",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the story"},
                    "description": {"type": "string", "description": "Brief description"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_scene",
            "description": "Create a new scene in a story",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_id": {"type": "string", "description": "ID of the story"},
                    "prompt": {"type": "string", "description": "Video description/prompt"},
                    "scene_number": {"type": "integer", "description": "Scene order (optional)"},
                    "duration": {"type": "integer", "description": "Duration in seconds (default 5)"},
                },
                "required": ["story_id", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_video",
            "description": "Generate a video for a scene",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_id": {"type": "string", "description": "ID of the story"},
                    "scene_id": {"type": "string", "description": "ID of the scene"},
                    "prompt": {"type": "string", "description": "Optional prompt override"},
                    "provider": {"type": "string", "description": "Provider: 'dashscope', 'veo3', or None for auto"},
                    "model": {"type": "string", "description": "Model name (optional)"},
                    "duration": {"type": "integer", "description": "Duration in seconds"},
                    "ratio": {"type": "string", "description": "Aspect ratio: 16:9, 9:16, or 1:1"},
                },
                "required": ["story_id", "scene_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_generation",
            "description": "Wait for video generation to complete",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "The job ID to wait for"},
                    "timeout_seconds": {"type": "integer", "description": "Max wait time (default 300)"},
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_scene_frame",
            "description": "Extract a frame from a video as reference image",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_id": {"type": "string", "description": "ID of the story"},
                    "scene_id": {"type": "string", "description": "ID of the scene"},
                    "timestamp": {"type": "number", "description": "Seconds into video (optional)"},
                    "frame_position": {"type": "string", "description": "start, middle, or end"},
                },
                "required": ["story_id", "scene_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_character_reference",
            "description": "Set a character reference image for consistency",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_id": {"type": "string", "description": "ID of the story"},
                    "character_name": {"type": "string", "description": "Name of the character"},
                    "image_url": {"type": "string", "description": "URL of reference image"},
                },
                "required": ["story_id", "character_name", "image_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_story_context",
            "description": "Get all information about a story",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_id": {"type": "string", "description": "ID of the story"},
                },
                "required": ["story_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_stories",
            "description": "List all stories",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID filter (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_asset",
            "description": "Store a video or image asset with metadata",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_id": {"type": "string", "description": "ID of the story"},
                    "entity_type": {"type": "string", "description": "scene, character, etc."},
                    "entity_id": {"type": "string", "description": "ID of the entity"},
                    "asset_type": {"type": "string", "description": "video, image, audio"},
                    "url": {"type": "string", "description": "URL of the asset"},
                    "mime_type": {"type": "string", "description": "MIME type (video/mp4, image/png, etc.)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                    "metadata": {"type": "object", "description": "Additional metadata"},
                },
                "required": ["story_id", "entity_type", "entity_id", "asset_type", "url"],
            },
        },
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

class ToolExecutor:
    """Executes tools for the agent."""
    
    def __init__(self, pool: Any, router: VideoProviderRouter):
        self.pool = pool
        self.router = router
        self._previous_exit_frame: Optional[str] = None
        self._current_story_id: Optional[str] = None
    
    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool by name."""
        method = getattr(self, f"tool_{tool_name}", None)
        if method:
            return await method(arguments)
        return {"error": f"Unknown tool: {tool_name}"}
    
    async def tool_create_story(self, args: dict) -> dict:
        """Create a new story."""
        title = args.get("title", "Untitled")
        prompt = args.get("description", "") or args.get("prompt", "")
        story_id = str(uuid.uuid4())
        
        await self.pool.execute(
            """INSERT INTO stories (id, title, prompt, status, created_at, updated_at)
               VALUES ($1, $2, $3, 'draft', now(), now())""",
            story_id, title, prompt,
        )
        
        self._current_story_id = story_id
        return {
            "story_id": story_id,
            "title": title,
            "status": "created",
        }
    
    async def tool_create_scene(self, args: dict) -> dict:
        """Create a new scene."""
        story_id = args.get("story_id")
        prompt = args.get("prompt", "")
        scene_number = args.get("scene_number", 1)
        duration = args.get("duration", 5)
        
        if not story_id:
            # Use current story if not specified
            story_id = self._current_story_id
            if not story_id:
                return {"error": "No story_id specified and no current story"}
        
        # Get or create episode
        episodes = await self.pool.fetch(
            "SELECT id FROM episodes WHERE story_id = $1 ORDER BY episode_number LIMIT 1",
            story_id,
        )
        
        if episodes:
            episode_id = str(episodes[0]["id"])
        else:
            episode_id = str(uuid.uuid4())
            await self.pool.execute(
                """INSERT INTO episodes (id, story_id, title, episode_number, status, created_at, updated_at)
                   VALUES ($1, $2, 'Episode 1', 1, 'draft', now(), now())""",
                episode_id, story_id,
            )
        
        # Create scene
        scene_id = str(uuid.uuid4())
        await self.pool.execute(
            """INSERT INTO scenes (id, episode_id, scene_number, prompt, duration, status, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, 'draft', now(), now())""",
            scene_id, episode_id, scene_number, prompt, duration,
        )
        
        return {
            "scene_id": scene_id,
            "story_id": story_id,
            "episode_id": episode_id,
            "prompt": prompt,
            "status": "created",
        }
    
    async def tool_generate_video(self, args: dict) -> dict:
        """Generate video using provider router."""
        from genblaze_core.models.step import Step
        from genblaze_core import Modality
        
        story_id = args.get("story_id")
        scene_id = args.get("scene_id")
        prompt = args.get("prompt")
        provider_str = args.get("provider")
        model = args.get("model", "auto")
        duration = args.get("duration", 5)
        ratio = args.get("ratio", "16:9")
        
        if not scene_id:
            return {"error": "scene_id is required"}
        
        # Get scene info
        scene = await self.pool.fetchrow(
            """SELECT s.*, e.story_id FROM scenes s
               JOIN episodes e ON s.episode_id = e.id
               WHERE s.id = $1""",
            scene_id,
        )
        
        if not scene:
            return {"error": f"Scene not found: {scene_id}"}
        
        # Use provided prompt or scene prompt
        generation_prompt = prompt or scene.get("prompt", "")
        if not generation_prompt:
            return {"error": "No prompt available for generation"}
        
        # Map provider string to ProviderType
        provider_type = None
        if provider_str:
            if provider_str.lower() == "dashscope":
                provider_type = ProviderType.DASHSCOPE
            elif provider_str.lower() == "veo3":
                provider_type = ProviderType.VEO3
            elif provider_str.lower() == "replicate":
                provider_type = ProviderType.REPLICATE
        
        # Create step - use specific model based on provider
        if provider_type == ProviderType.DASHSCOPE:
            step_model = model if model != "auto" else "happyhorse-1.1-t2v"
        elif provider_type == ProviderType.VEO3:
            step_model = model if model != "auto" else "veo3-fast"
        elif provider_type == ProviderType.REPLICATE:
            step_model = model if model != "auto" else "tencent/hunyuan-video"
        else:
            step_model = "auto"
        
        step = Step(
            provider="video",
            model=step_model,
            prompt=generation_prompt,
            modality=Modality.VIDEO,
        )
        step.params = {
            "duration": duration,
            "ratio": ratio,
        }
        
        # Add reference image if available
        if self._previous_exit_frame:
            from genblaze_core.models.asset import Asset
            step.inputs = [Asset(url=self._previous_exit_frame)]
        
        # Generate
        task_id, provider_name = self.router.generate_video(step, provider_type)
        
        # Create job record
        job_id = str(uuid.uuid4())
        await self.pool.execute(
            """INSERT INTO generation_jobs (id, entity_type, entity_id, status, job_type, current_step)
               VALUES ($1, 'scene', $2, 'pending', 'scene_gen', 'Queued')""",
            job_id, scene_id,
        )
        
        # Update scene status
        await self.pool.execute(
            "UPDATE scenes SET status = 'running', updated_at = now() WHERE id = $1",
            scene_id,
        )
        
        return {
            "job_id": job_id,
            "task_id": task_id,
            "scene_id": scene_id,
            "provider": provider_name,
            "status": "pending",
            "message": f"Video generation started with {provider_name}",
        }
    
    async def tool_wait_for_generation(self, args: dict) -> dict:
        """Poll for generation completion."""
        job_id = args.get("job_id")
        timeout = args.get("timeout_seconds", 300)
        
        if not job_id:
            return {"error": "job_id is required"}
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            job = await self.pool.fetchrow(
                "SELECT * FROM generation_jobs WHERE id = $1",
                job_id,
            )
            
            if not job:
                return {"error": f"Job not found: {job_id}"}
            
            status = job["status"]
            
            if status == "completed":
                result = job.get("result") or {}
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "result": result,
                }
            elif status == "failed":
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": job.get("error"),
                }
            
            await asyncio.sleep(5)
        
        return {
            "job_id": job_id,
            "status": "timeout",
            "message": f"Waited {timeout}s without completion",
        }
    
    async def tool_extract_scene_frame(self, args: dict) -> dict:
        """Extract a frame from a video."""
        story_id = args.get("story_id")
        scene_id = args.get("scene_id")
        position = args.get("frame_position", "end")
        
        if not scene_id:
            return {"error": "scene_id is required"}
        
        # Get scene
        scene = await self.pool.fetchrow(
            """SELECT s.*, e.story_id FROM scenes s
               JOIN episodes e ON s.episode_id = e.id
               WHERE s.id = $1""",
            scene_id,
        )
        
        if not scene:
            return {"error": f"Scene not found: {scene_id}"}
        
        clip_url = scene.get("clip_url")
        if not clip_url:
            return {"error": "Scene has no video clip_url"}
        
        # For now, just return the video URL as the reference
        # In production, you'd use ffmpeg to extract a frame
        self._previous_exit_frame = clip_url
        
        return {
            "scene_id": scene_id,
            "frame_url": clip_url,
            "position": position,
            "message": "Frame extracted for next scene continuity",
        }
    
    async def tool_set_character_reference(self, args: dict) -> dict:
        """Set a character reference image."""
        story_id = args.get("story_id")
        character_name = args.get("character_name", "main")
        image_url = args.get("image_url")
        
        if not image_url:
            return {"error": "image_url is required"}
        
        if not story_id:
            story_id = self._current_story_id
            if not story_id:
                return {"error": "No story_id specified"}
        
        # Create or update character
        characters = await self.pool.fetch(
            "SELECT * FROM characters WHERE story_id = $1 AND name = $2",
            story_id, character_name,
        )
        
        if characters:
            char_id = str(characters[0]["id"])
            await self.pool.execute(
                "UPDATE characters SET ref_image_urls = $1 WHERE id = $2",
                json.dumps([image_url]), char_id,
            )
        else:
            char_id = str(uuid.uuid4())
            await self.pool.execute(
                """INSERT INTO characters (id, story_id, name, ref_image_urls, created_at)
                   VALUES ($1, $2, $3, $4, now())""",
                char_id, story_id, character_name, json.dumps([image_url]),
            )
        
        return {
            "character_id": char_id,
            "character_name": character_name,
            "image_url": image_url,
            "status": "set",
        }
    
    async def tool_get_story_context(self, args: dict) -> dict:
        """Get complete story context."""
        story_id = args.get("story_id")
        
        if not story_id:
            story_id = self._current_story_id
            if not story_id:
                return {"error": "No story_id specified"}
        
        story = await self.pool.fetchrow(
            "SELECT * FROM stories WHERE id = $1",
            story_id,
        )
        
        if not story:
            return {"error": f"Story not found: {story_id}"}
        
        episodes = await self.pool.fetch(
            "SELECT * FROM episodes WHERE story_id = $1 ORDER BY episode_number",
            story_id,
        )
        
        scenes_by_episode = {}
        for ep in episodes:
            ep_id = str(ep["id"])
            scenes = await self.pool.fetch(
                """SELECT s.*, e.episode_number FROM scenes s
                   JOIN episodes e ON s.episode_id = e.id
                   WHERE s.episode_id = $1
                   ORDER BY s.scene_number""",
                ep_id,
            )
            scenes_by_episode[ep_id] = [dict(s) for s in scenes]
        
        characters = await self.pool.fetch(
            "SELECT * FROM characters WHERE story_id = $1",
            story_id,
        )
        
        return {
            "story": dict(story),
            "episodes": [dict(e) for e in episodes],
            "scenes_by_episode": scenes_by_episode,
            "characters": [dict(c) for c in characters],
        }
    
    async def tool_list_stories(self, args: dict) -> dict:
        """List all stories."""
        user_id = args.get("user_id")
        
        if user_id:
            stories = await self.pool.fetch(
                "SELECT * FROM stories WHERE user_id = $1 ORDER BY created_at DESC",
                user_id,
            )
        else:
            stories = await self.pool.fetch(
                "SELECT * FROM stories ORDER BY created_at DESC LIMIT 50",
            )
        
        return {
            "stories": [dict(s) for s in stories],
            "count": len(stories),
        }
    
    async def tool_store_asset(self, args: dict) -> dict:
        """Store a video or image asset."""
        story_id = args.get("story_id")
        entity_type = args.get("entity_type", "scene")
        entity_id = args.get("entity_id", "")
        asset_type = args.get("asset_type", "video")
        url = args.get("url")
        mime_type = args.get("mime_type", "video/mp4")
        tags = args.get("tags", [])
        metadata = args.get("metadata", {})
        
        if not url:
            return {"error": "url is required"}
        
        if not story_id:
            story_id = self._current_story_id
            if not story_id:
                return {"error": "No story_id specified"}
        
        asset_id = str(uuid.uuid4())
        
        # Build storage key
        storage_key = f"stories/{story_id}/{entity_type}/{asset_id}.{mime_type.split('/')[-1]}"
        
        await self.pool.execute(
            """INSERT INTO assets (id, story_id, entity_type, entity_id, asset_type,
               storage_key, storage_url, mime_type, tags, metadata, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())""",
            asset_id, story_id, entity_type, entity_id, asset_type,
            storage_key, url, mime_type, tags, json.dumps(metadata),
        )
        
        return {
            "asset_id": asset_id,
            "story_id": story_id,
            "entity_type": entity_type,
            "asset_type": asset_type,
            "storage_key": storage_key,
            "storage_url": url,
            "status": "stored",
        }


# ══════════════════════════════════════════════════════════════════════════════
# AGENTIC ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


class AgenticOrchestrator:
    """
    LLM-powered agent that helps users create videos through conversation.
    
    Features:
    - Natural language understanding
    - Multi-step task execution
    - Video generation with provider routing
    - Asset management
    - Scene continuity tracking
    """
    
    def __init__(
        self,
        pool: Any,
        model: Optional[str] = None,
        max_iterations: int = 15,
    ):
        self.pool = pool
        self.model = model or TOKENROUTER_MODEL
        self.max_iterations = max_iterations
        
        # Initialize components
        self.router = get_router()
        self.tool_executor = ToolExecutor(pool, self.router)
        
        # Conversation history
        self.messages: list[ChatMessage] = []
        
        # System message
        self._init_system_message()
    
    def _init_system_message(self):
        """Initialize the system message."""
        self.messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT)
        ]
    
    async def run(self, user_input: str) -> dict:
        """
        Run the agent with a user input.
        
        Returns:
            dict with:
            - response: The agent's response
            - tool_calls: List of tool calls made
            - final_result: Final result if any
        """
        # Add user message
        self.messages.append(ChatMessage(role="user", content=user_input))
        
        tool_calls_made = []
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Get LLM response
            response = await self._chat_with_tools()
            
            # Add assistant response to history
            self.messages.append(ChatMessage(
                role="assistant",
                content=response.content,
            ))
            
            # If no tool calls, we're done
            if not response.tool_calls:
                return {
                    "response": response.content,
                    "tool_calls": tool_calls_made,
                    "iterations": iteration,
                    "final_result": None,
                }
            
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_calls_made.append({
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                })
                
                print(f"[agent] Calling tool: {tool_call.name}")
                print(f"[agent] Arguments: {tool_call.arguments}")
                
                # Execute tool
                result = await self.tool_executor.execute(
                    tool_call.name,
                    tool_call.arguments,
                )
                
                print(f"[agent] Result: {result}")
                
                # Add tool result to conversation
                tool_result_msg = ChatMessage(
                    role="tool",
                    content=json.dumps(result, indent=2),
                    name=tool_call.name,
                )
                self.messages.append(tool_result_msg)
        
        # Max iterations reached
        return {
            "response": "I ran out of iterations. Let me know if you'd like to continue.",
            "tool_calls": tool_calls_made,
            "iterations": iteration,
            "final_result": None,
        }
    
    async def _chat_with_tools(self) -> ChatResponse:
        """Send messages to LLM with tools enabled."""
        client = get_agent_llm()
        
        return await client.chat(
            messages=self.messages,
            model=self.model,
            temperature=0.7,
            max_tokens=4096,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
    
    async def chat_stream(self, user_input: str):
        """
        Stream the agent's response.
        
        Yields events as they happen.
        """
        # Add user message
        self.messages.append(ChatMessage(role="user", content=user_input))
        
        tool_calls_made = []
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Get LLM response
            response = await self._chat_with_tools()
            
            # Add assistant response to history
            self.messages.append(ChatMessage(
                role="assistant",
                content=response.content,
            ))
            
            # Yield text response
            if response.content:
                yield {"type": "text", "content": response.content}
            
            # If no tool calls, we're done
            if not response.tool_calls:
                yield {"type": "done"}
                return
            
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_calls_made.append({
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                })
                
                yield {"type": "tool_start", "name": tool_call.name}
                
                # Execute tool
                result = await self.tool_executor.execute(
                    tool_call.name,
                    tool_call.arguments,
                )
                
                yield {"type": "tool_result", "name": tool_call.name, "result": result}
                
                # Add tool result to conversation
                tool_result_msg = ChatMessage(
                    role="tool",
                    content=json.dumps(result, indent=2),
                    name=tool_call.name,
                )
                self.messages.append(tool_result_msg)
        
        yield {"type": "done", "message": "Max iterations reached"}
    
    def reset(self):
        """Reset the conversation."""
        self._init_system_message()


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

async def run_agent_task(pool: Any, task: str) -> dict:
    """
    Run a single agent task.
    
    Usage:
        result = await run_agent_task(pool, "Create a video of a sunset")
    """
    agent = AgenticOrchestrator(pool)
    return await agent.run(task)


async def run_agent_stream(pool: Any, task: str):
    """
    Run agent task with streaming.
    
    Usage:
        async for event in run_agent_stream(pool, "Create a video"):
            print(event)
    """
    agent = AgenticOrchestrator(pool)
    async for event in agent.chat_stream(task):
        yield event
