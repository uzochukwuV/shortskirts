"""
Agent Service - Main orchestrator for the AI production assistant.

This service manages conversations, executes tools, and coordinates
with the existing pipeline.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field

from pipeline.agent_llm import (
    ChatMessage,
    agent_chat,
    get_agent_llm,
    ToolCall,
    ChatResponse,
)
from pipeline.agent_tools import get_all_tools
from pipeline.agent_tools import (
    get_tool_definition,
    get_story_context_impl,
    get_scene_timeline_impl,
    list_scene_assets_impl,
    get_provider_status_impl,
    get_job_status_impl,
    create_scene_impl,
    update_scene_impl,
    delete_scene_impl,
    regenerate_scene_impl,
    set_scene_continuity_impl,
    approve_scene_impl,
    lock_scene_impl,
    generate_scene_description_impl,
    poll_job_until_complete_impl,
)


# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI production assistant for Dysentry - an AI video generation platform.

Your role is to help users create video content by:
- Understanding their production goals
- Creating and managing scenes
- Maintaining visual continuity across scenes
- Coordinating with the generation pipeline

You have access to tools that let you:
- Read story, scene, and character data
- Create, update, and delete scenes
- Set continuity references between scenes
- Trigger scene regeneration
- Monitor job status

When a user asks to do something:
1. First understand what they want
2. Use get_story_context to understand the current state
3. Use the appropriate tools to make changes
4. Confirm what you did and any next steps

Be conversational but precise. When creating scenes:
- Suggest appropriate locations, moods, and actions
- Consider continuity with previous scenes
- Use character names the user has defined

Always be helpful and guide users through the production process."""


# ─── Tool Executor ────────────────────────────────────────────────────────────

# Import media tool implementations
from pipeline.agent_media_tools import (
    extract_scene_frame_impl,
    screenshot_previous_scene_impl,
    generate_script_and_scenes_impl,
    set_character_reference_impl,
    extract_character_from_scene_impl,
    generate_video_genblaze_impl,
    poll_genblaze_status_impl,
)

# Import production tool implementations
from pipeline.agent_production_tools import (
    generate_narration_impl,
    assemble_episode_impl,
    add_transition_impl,
    generate_thumbnail_impl,
    generate_seo_metadata_impl,
    check_style_consistency_impl,
    compare_scenes_impl,
    search_assets_impl,
)

TOOL_IMPLEMENTATIONS = {
    # Original tools
    "get_story_context": get_story_context_impl,
    "get_scene_timeline": get_scene_timeline_impl,
    "list_scene_assets": list_scene_assets_impl,
    "get_provider_status": get_provider_status_impl,
    "get_job_status": get_job_status_impl,
    "create_scene": create_scene_impl,
    "update_scene": update_scene_impl,
    "delete_scene": delete_scene_impl,
    "regenerate_scene": regenerate_scene_impl,
    "set_scene_continuity": set_scene_continuity_impl,
    "approve_scene": approve_scene_impl,
    "lock_scene": lock_scene_impl,
    "generate_scene_description": generate_scene_description_impl,
    "wait_for_generation": poll_job_until_complete_impl,
    # Media tools (frame extraction, Genblaze, etc.)
    "extract_scene_frame": extract_scene_frame_impl,
    "screenshot_previous_scene": screenshot_previous_scene_impl,
    "generate_script_and_scenes": generate_script_and_scenes_impl,
    "set_character_reference": set_character_reference_impl,
    "extract_character_from_scene": extract_character_from_scene_impl,
    "generate_video": generate_video_genblaze_impl,
    "poll_video_generation": poll_genblaze_status_impl,
    # Production tools (assembly, audio, publishing, etc.)
    "generate_narration": generate_narration_impl,
    "assemble_episode": assemble_episode_impl,
    "add_transition": add_transition_impl,
    "generate_thumbnail": generate_thumbnail_impl,
    "generate_seo_metadata": generate_seo_metadata_impl,
    "check_style_consistency": check_style_consistency_impl,
    "compare_scenes": compare_scenes_impl,
    "search_assets": search_assets_impl,
}


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    pool: Any,
) -> dict[str, Any]:
    """
    Execute a tool by name with the given arguments.
    Returns the result or error.
    """
    impl = TOOL_IMPLEMENTATIONS.get(tool_name)
    if not impl:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        # Inject pool for tools that need it
        import inspect
        sig = inspect.signature(impl)
        if "pool" in sig.parameters:
            result = await impl(pool=pool, **arguments)
        else:
            result = await impl(**arguments)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Agent Response ────────────────────────────────────────────────────────────

@dataclass
class AgentAction:
    """An action taken by the agent."""
    tool_name: str
    arguments: dict[str, Any]
    result: Any = None
    error: Optional[str] = None


@dataclass
class AgentResponse:
    """Response from the agent."""
    message: str
    actions: list[AgentAction] = field(default_factory=list)
    finished: bool = True


# ─── Conversation Manager ───────────────────────────────────────────────────────

@dataclass
class Conversation:
    """A conversation session."""
    id: str
    user_id: str
    story_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ConversationManager:
    """
    Manages agent conversations.
    In production, this would persist to the database.
    """
    
    def __init__(self):
        self._conversations: dict[str, Conversation] = {}
    
    async def create_conversation(
        self,
        pool: Any,
        user_id: str,
        story_id: str,
    ) -> Conversation:
        """Create a new conversation."""
        conv_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conv_id,
            user_id=user_id,
            story_id=story_id,
            messages=[],
        )
        self._conversations[conv_id] = conversation
        
        # Persist to database
        await pool.execute(
            """INSERT INTO agent_conversations (id, user_id, story_id, created_at, updated_at)
               VALUES ($1, $2, $3, now(), now())""",
            conv_id, user_id, story_id,
        )
        
        return conversation
    
    async def get_conversation(
        self,
        pool: Any,
        conversation_id: str,
        user_id: str,
    ) -> Optional[Conversation]:
        """Get a conversation by ID."""
        row = await pool.fetchrow(
            """SELECT * FROM agent_conversations 
               WHERE id = $1 AND user_id = $2""",
            conversation_id, user_id,
        )
        if not row:
            return None
        
        conv = Conversation(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            story_id=str(row["story_id"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        
        # Load messages
        msg_rows = await pool.fetch(
            """SELECT * FROM agent_messages 
               WHERE conversation_id = $1 
               ORDER BY created_at ASC""",
            conversation_id,
        )
        conv.messages = [
            {
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
            for r in msg_rows
        ]
        
        self._conversations[conversation_id] = conv
        return conv
    
    async def add_message(
        self,
        pool: Any,
        conversation_id: str,
        role: str,
        content: str,
    ) -> dict[str, Any]:
        """Add a message to a conversation."""
        msg_id = str(uuid.uuid4())
        await pool.execute(
            """INSERT INTO agent_messages (id, conversation_id, role, content, created_at)
               VALUES ($1, $2, $3, $4, now())""",
            msg_id, conversation_id, role, content,
        )
        await pool.execute(
            "UPDATE agent_conversations SET updated_at = now() WHERE id = $1",
            conversation_id,
        )
        return {"id": msg_id, "role": role, "content": content}
    
    async def delete_conversation(
        self,
        pool: Any,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a conversation."""
        result = await pool.execute(
            """DELETE FROM agent_conversations 
               WHERE id = $1 AND user_id = $2""",
            conversation_id, user_id,
        )
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
        return "DELETE 1" in result


# Global conversation manager
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


# ─── Agent Executor ────────────────────────────────────────────────────────────

class AgentExecutor:
    """
    Executes agent conversations with tool calling.
    """
    
    def __init__(self):
        self.max_iterations = 10  # Prevent infinite loops
    
    async def chat(
        self,
        pool: Any,
        conversation: Conversation,
        user_message: str,
        include_context: bool = True,
    ) -> AgentResponse:
        """
        Process a user message and return agent response.
        May execute multiple tool calls in a loop.
        """
        # Add user message to conversation
        await get_conversation_manager().add_message(
            pool, conversation.id, "user", user_message
        )
        
        # Build messages for LLM
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
        ]
        
        # Add context if requested
        if include_context:
            try:
                story_context = await get_story_context_impl(pool, conversation.story_id)
                context_msg = f"""Current Story Context:
{json.dumps(story_context, indent=2, default=str)}

---"""
                messages.append(ChatMessage(role="system", content=context_msg))
            except Exception as e:
                messages.append(ChatMessage(
                    role="system", 
                    content=f"Note: Could not load story context: {e}"
                ))
        
        # Add conversation history
        for msg in conversation.messages:
            messages.append(ChatMessage(
                role=msg["role"],
                content=msg["content"],
            ))
        
        # Add current user message
        messages.append(ChatMessage(role="user", content=user_message))
        
        # Get available tools
        tools = get_all_tools()
        
        # LLM interaction loop
        actions: list[AgentAction] = []
        iteration = 0
        all_tool_results = []
        max_retries = 3
        
        while iteration < self.max_iterations:
            iteration += 1
            retry_count = 0
            
            # Call LLM with retry logic
            response = None
            last_error = None
            while retry_count < max_retries:
                try:
                    response = await agent_chat(
                        messages=messages,
                        tools=tools,
                        temperature=0.7,
                        max_tokens=1500,
                    )
                    break
                except Exception as e:
                    last_error = e
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(2)  # Wait before retry
                    continue
            
            if response is None or last_error:
                # If all retries failed, return error response
                error_msg = f"LLM call failed after {max_retries} attempts: {last_error}"
                return AgentResponse(
                    message=f"I encountered an error while processing your request: {error_msg}",
                    actions=actions,
                    finished=True,
                )
            
            # Add assistant response to messages
            messages.append(ChatMessage(role="assistant", content=response.content))
            
            # Process tool calls
            if not response.tool_calls:
                # No more tool calls - we're done
                break
            
            for tc in response.tool_calls:
                tool_name = tc.name
                arguments = tc.arguments
                tool_call_id = tc.id or f"call_{iteration}_{tool_name}"
                
                # Execute tool
                try:
                    tool_result = await execute_tool(tool_name, arguments, pool)
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}
                
                action = AgentAction(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=tool_result.get("result"),
                    error=tool_result.get("error"),
                )
                actions.append(action)
                all_tool_results.append((tool_name, tool_result))
                
                # Add tool result to messages (must include tool name for Kimi K3)
                result_str = json.dumps(tool_result, default=str)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Tool {tool_name} result: {result_str}",
                    "name": tool_name,  # Required for Kimi K3
                })
        
        # Save assistant message to database
        await get_conversation_manager().add_message(
            pool, conversation.id, "assistant", response.content
        )
        
        return AgentResponse(
            message=response.content,
            actions=actions,
            finished=True,
        )


# Global executor
_agent_executor: Optional[AgentExecutor] = None


def get_agent_executor() -> AgentExecutor:
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = AgentExecutor()
    return _agent_executor


# ─── Convenience Functions ─────────────────────────────────────────────────────

async def create_agent_conversation(
    pool: Any,
    user_id: str,
    story_id: str,
) -> dict[str, Any]:
    """Create a new agent conversation."""
    manager = get_conversation_manager()
    conversation = await manager.create_conversation(pool, user_id, story_id)
    
    # Get initial context
    context = await get_story_context_impl(pool, story_id)
    
    return {
        "conversation_id": conversation.id,
        "story_id": story_id,
        "created_at": conversation.created_at.isoformat(),
        "context": context,
    }


async def agent_chat_message(
    pool: Any,
    conversation_id: str,
    user_id: str,
    message: str,
) -> dict[str, Any]:
    """Send a message to an agent conversation."""
    manager = get_conversation_manager()
    executor = get_agent_executor()
    
    # Get conversation
    conversation = await manager.get_conversation(pool, conversation_id, user_id)
    if not conversation:
        raise ValueError(f"Conversation not found: {conversation_id}")
    
    # Process message
    response = await executor.chat(pool, conversation, message)
    
    # Format response
    return {
        "message": response.message,
        "actions": [
            {
                "tool": a.tool_name,
                "arguments": a.arguments,
                "result": a.result,
                "error": a.error,
            }
            for a in response.actions
        ],
        "finished": response.finished,
    }
