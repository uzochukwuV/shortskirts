"""
Agent API routes for Dysentry Video Production.

Provides chat-based AI assistant for video production workflows.
Uses unified agent system with TokenRouter LLM and GenBlaze-style streaming.
"""

from __future__ import annotations

import json
import asyncio
from typing import Optional, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from db.connection import get_pool
from auth import get_current_user


router = APIRouter(prefix="/pipeline/agent", tags=["agent"])


# ─── Request/Response Models ────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    story_id: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    story_id: Optional[str] = None
    include_context: bool = True


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


# ─── Initialize Unified Agent ──────────────────────────────────────────────────

def _get_agent_components():
    """Lazy import to avoid circular imports."""
    from pipeline.unified_agent import (
        get_orchestrator,
        get_executor,
        UnifiedStreamingOrchestrator,
        UnifiedAgentExecutor,
        StreamEvent,
        EventType,
        SYSTEM_PROMPT,
        AssetManager,
    )
    from pipeline.agent_llm import ChatMessage, get_agent_llm
    from pipeline.consolidated_tools import register_all_tools
    from pipeline.agent_service import ConversationManager
    
    # Initialize executor with tools
    executor = get_executor()
    if not executor._tools:
        register_all_tools(executor)
    
    return {
        "orchestrator": get_orchestrator(),
        "executor": executor,
        "llm": get_agent_llm(),
        "conversation_manager": ConversationManager(),
        "asset_manager_class": AssetManager,
        "stream_event": StreamEvent,
        "event_type": EventType,
        "chat_message": ChatMessage,
        "system_prompt": SYSTEM_PROMPT,
    }


# ─── Conversation Endpoints ─────────────────────────────────────────────────────

@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    user: dict = Depends(get_current_user),
):
    """
    Start a new agent conversation for a story.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    story_id = request.story_id
    
    # Verify story ownership
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    from pipeline.agent_service import create_agent_conversation
    
    result = await create_agent_conversation(pool, user_id, story_id)
    return result


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get a conversation and its messages.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    from pipeline.agent_service import get_conversation_manager
    
    manager = get_conversation_manager()
    conversation = await manager.get_conversation(pool, conversation_id, user_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation.id,
        "story_id": conversation.story_id,
        "messages": conversation.messages,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """
    End and delete a conversation.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    from pipeline.agent_service import get_conversation_manager
    
    manager = get_conversation_manager()
    deleted = await manager.delete_conversation(pool, conversation_id, user_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"deleted": True}


# ─── Chat Endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    request: ChatRequest,
    conversation_id: Optional[str] = None,
    story_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Send a message to the agent.
    
    If conversation_id is provided, continues the existing conversation.
    If story_id is provided without conversation_id, creates a new conversation.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    from pipeline.agent_service import (
        get_conversation_manager,
        get_agent_executor,
        create_agent_conversation,
    )
    
    manager = get_conversation_manager()
    executor = get_agent_executor()
    
    # Get or create conversation
    if conversation_id:
        conversation = await manager.get_conversation(pool, conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    elif story_id:
        # Verify story ownership
        story = await pool.fetchrow(
            "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
            story_id, user_id,
        )
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        result = await create_agent_conversation(pool, user_id, story_id)
        conversation_id = result["conversation_id"]
        
        # Get the conversation object
        conversation = await manager.get_conversation(pool, conversation_id, user_id)
    else:
        raise HTTPException(
            status_code=400, 
            detail="Either conversation_id or story_id is required"
        )
    
    # Process message
    response = await executor.chat(pool, conversation, request.message)
    
    return {
        "conversation_id": conversation_id,
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


# ─── Streaming Chat Endpoint ───────────────────────────────────────────────────

@router.get("/chat-stream/{conversation_id}")
async def stream_chat(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """
    SSE endpoint for streaming agent chat responses.
    
    Supports GenBlaze-style events:
    - connected: Initial connection
    - message: Streaming response content
    - tool_start: Tool execution started
    - tool_progress: Tool execution progress
    - tool_complete: Tool execution completed
    - tool_error: Tool execution failed
    - done: Response complete
    - error: Connection error
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Get components
    components = _get_agent_components()
    executor = components["executor"]
    llm = components["llm"]
    
    # Get conversation
    conversation = await components["conversation_manager"].get_conversation(
        pool, conversation_id, user_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    async def event_generator() -> AsyncGenerator[bytes, None]:
        """Generate SSE events for the chat."""
        try:
            # Send connected event
            yield f"data: {json.dumps({'type': 'connected', 'conversation_id': conversation_id})}\n\n".encode()
            
            # Build messages
            messages = []
            
            # Add system prompt
            messages.append({"role": "system", "content": components["system_prompt"]})
            
            # Add story context
            if conversation.story_id:
                try:
                    story_context = await executor.execute(
                        "get_story_context", {"story_id": conversation.story_id}, pool
                    )
                    if story_context.success:
                        context_msg = f"""Current Story Context:
{json.dumps(story_context.result, indent=2, default=str)}

---"""
                        messages.append({"role": "system", "content": context_msg})
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'warning', 'message': f'Context error: {str(e)}'})}\n\n".encode()
            
            # Add conversation history
            for msg in conversation.messages:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })
            
            # Send ready event
            yield f"data: {json.dumps({'type': 'ready'})}\n\n".encode()
            
            # Note: Actual message content should be sent via POST /chat
            # This endpoint provides SSE infrastructure
            yield f"data: {json.dumps({'type': 'done', 'message': 'Use POST /chat to send messages'})}\n\n".encode()
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """
    Send a message to the agent (sync response).
    
    For streaming responses, use GET /chat-stream/{conversation_id}
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Get components
    components = _get_agent_components()
    executor = components["executor"]
    llm = components["llm"]
    
    # Get or create conversation
    conversation_id = request.conversation_id
    story_id = request.story_id
    
    if conversation_id:
        conversation = await components["conversation_manager"].get_conversation(
            pool, conversation_id, user_id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        story_id = story_id or conversation.story_id
    elif story_id:
        # Verify story ownership
        story = await pool.fetchrow(
            "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
            story_id, user_id,
        )
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Create conversation
        conv_result = await components["conversation_manager"].create_conversation(
            pool, user_id, story_id
        )
        conversation_id = conv_result["conversation_id"]
        conversation = conv_result["conversation"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Either conversation_id or story_id is required",
        )
    
    # Build messages
    messages = []
    
    # System prompt
    messages.append({"role": "system", "content": components["system_prompt"]})
    
    # Story context
    if story_id and request.include_context:
        try:
            ctx_result = await executor.execute("get_story_context", {"story_id": story_id}, pool)
            if ctx_result.success:
                messages.append({
                    "role": "system",
                    "content": f"Story Context:\n{json.dumps(ctx_result.result, indent=2, default=str)}\n\n---\n",
                })
        except Exception as e:
            print(f"Context error: {e}")
    
    # Conversation history
    for msg in conversation.messages:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })
    
    # User message
    messages.append({"role": "user", "content": request.message})
    
    # Call LLM with tools
    tools = executor.get_tool_definitions()
    response = await llm.chat(
        messages=messages,
        tools=tools if tools else None,
        temperature=0.7,
        max_tokens=2000,
    )
    
    # Save user message
    await components["conversation_manager"].add_message(
        pool, conversation_id, "user", request.message
    )
    
    # Process tool calls
    actions = []
    for tc in response.tool_calls:
        tool_result = await executor.execute(tc.name, tc.arguments, pool)
        actions.append({
            "tool": tc.name,
            "arguments": tc.arguments,
            "result": tool_result.result if tool_result.success else None,
            "error": tool_result.error,
        })
        
        # Add tool result to messages for final response
        messages.append({
            "role": "tool",
            "content": json.dumps(tool_result.result if tool_result.success else {"error": tool_result.error}),
        })
    
    # Save assistant response
    await components["conversation_manager"].add_message(
        pool, conversation_id, "assistant", response.content
    )
    
    return {
        "conversation_id": conversation_id,
        "message": response.content,
        "actions": actions,
        "has_tool_calls": len(response.tool_calls) > 0,
    }


# ─── Tool Execution Endpoint ─────────────────────────────────────────────────────

@router.post("/tools/execute")
async def execute_tool(
    request: ToolExecuteRequest,
    user: dict = Depends(get_current_user),
):
    """
    Execute a single tool directly (no LLM).
    """
    pool = await get_pool()
    
    components = _get_agent_components()
    executor = components["executor"]
    
    result = await executor.execute(request.tool_name, request.arguments, pool)
    
    return {
        "tool": request.tool_name,
        "arguments": request.arguments,
        "success": result.success,
        "result": result.result,
        "error": result.error,
    }


@router.get("/tools")
async def list_tools(user: dict = Depends(get_current_user)):
    """
    List all available agent tools.
    """
    components = _get_agent_components()
    tools = components["executor"].get_tool_definitions()
    
    return {
        "tools": tools,
        "total": len(tools),
    }


# ─── Story Context Endpoints ─────────────────────────────────────────────────────

@router.get("/stories/{story_id}/context")
async def get_story_context(
    story_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get complete story context for the agent.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Verify ownership
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    components = _get_agent_components()
    result = await components["executor"].execute("get_story_context", {"story_id": story_id}, pool)
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    
    return result.result


@router.get("/stories/{story_id}/timeline/{scene_id}")
async def get_scene_timeline(
    story_id: str,
    scene_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get scene with adjacent scenes for continuity planning.
    """
    pool = await get_pool()
    
    components = _get_agent_components()
    result = await components["executor"].execute(
        "get_scene_timeline", {"story_id": story_id, "scene_id": scene_id}, pool
    )
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    
    return result.result


# ─── Asset Management Endpoints ─────────────────────────────────────────────────

@router.get("/stories/{story_id}/assets")
async def list_story_assets(
    story_id: str,
    asset_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    List all assets for a story.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Verify ownership
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    components = _get_agent_components()
    asset_manager = components["asset_manager_class"](pool)
    
    assets = await asset_manager.get_assets(
        story_id=story_id,
        asset_type=asset_type,
        entity_type=entity_type,
    )
    
    return {
        "story_id": story_id,
        "assets": [asdict(a) for a in assets],
        "total": len(assets),
    }


@router.get("/stories/{story_id}/assets/search")
async def search_story_assets(
    story_id: str,
    q: str,
    asset_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Search assets within a story.
    """
    pool = await get_pool()
    
    components = _get_agent_components()
    asset_manager = components["asset_manager_class"](pool)
    
    assets = await asset_manager.search_assets(
        story_id=story_id,
        query=q,
        asset_type=asset_type,
    )
    
    return {
        "query": q,
        "results": [asdict(a) for a in assets],
        "total": len(assets),
    }


# ─── Provider Status ─────────────────────────────────────────────────────────────

@router.get("/providers/status")
async def get_provider_status(user: dict = Depends(get_current_user)):
    """
    Get status of video generation providers.
    """
    try:
        from pipeline.provider_status import get_provider_status
        
        status = await get_provider_status()
        return status
    except Exception as e:
        return {
            "error": str(e),
            "providers": {
                "dashscope": {"status": "unknown"},
            },
        }


# ─── Missing endpoints from original ─────────────────────────────────────────────

async def get_conversation_manager():
    """Get conversation manager."""
    from pipeline.agent_service import get_conversation_manager
    return get_conversation_manager()


async def get_agent_executor():
    """Get agent executor."""
    from pipeline.agent_service import get_agent_executor
    return get_agent_executor()


async def create_agent_conversation(pool, user_id, story_id):
    """Create new conversation."""
    from pipeline.agent_service import create_agent_conversation
    return await create_agent_conversation(pool, user_id, story_id)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    conversation_id: Optional[str] = None,
    story_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Stream agent chat responses as Server-Sent Events.
    
    Events:
    - message: LLM text response
    - tool_start: Tool execution started
    - tool_complete: Tool execution completed (includes result)
    - tool_error: Tool execution failed
    - done: Conversation finished
    - error: Error occurred
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    from pipeline.agent_service import (
        get_conversation_manager,
        create_agent_conversation,
    )
    
    manager = get_conversation_manager()
    
    # Get or create conversation
    if conversation_id:
        conversation = await manager.get_conversation(pool, conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    elif story_id:
        # Verify story ownership
        story = await pool.fetchrow(
            "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
            story_id, user_id,
        )
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        result = await create_agent_conversation(pool, user_id, story_id)
        conversation_id = result["conversation_id"]
        conversation = await manager.get_conversation(pool, conversation_id, user_id)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either conversation_id or story_id is required"
        )
    
    # Save user message
    await manager.add_message(pool, conversation_id, "user", request.message)
    
    return StreamingResponse(
        _stream_agent_chat(pool, conversation, request.message, request.include_context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Tool Endpoints ────────────────────────────────────────────────────────────

@router.get("/tools")
async def list_tools():
    """
    List all available agent tools.
    """
    from pipeline.agent_tools import TOOL_DEFINITIONS
    
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "requires_confirmation": tool.requires_confirmation,
                "category": tool.category,
            }
            for tool in TOOL_DEFINITIONS.values()
        ]
    }


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """
    Get details of a specific tool.
    """
    from pipeline.agent_tools import get_tool_definition
    
    tool = get_tool_definition(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
        "requires_confirmation": tool.requires_confirmation,
        "category": tool.category,
    }


@router.post("/tools/execute")
async def execute_tool(
    request: ToolExecuteRequest,
    story_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Execute a tool directly (bypassing chat).
    Useful for programmatic access.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Verify story ownership
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    from pipeline.agent_tools import get_tool_definition
    from pipeline.agent_service import execute_tool
    
    tool = get_tool_definition(request.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Add story_id to arguments if not present
    arguments = request.arguments.copy()
    if "story_id" not in arguments:
        arguments["story_id"] = story_id
    
    result = await execute_tool(request.tool_name, arguments, pool)
    
    return {
        "tool": request.tool_name,
        "arguments": arguments,
        "result": result.get("result"),
        "error": result.get("error"),
    }


# ─── Context Endpoints ────────────────────────────────────────────────────────

@router.get("/stories/{story_id}/context")
async def get_story_context_for_agent(
    story_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get full story context for agent use.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Verify story ownership
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    from pipeline.agent_tools import get_story_context_impl
    
    context = await get_story_context_impl(pool, story_id)
    return context


@router.get("/stories/{story_id}/timeline/{scene_id}")
async def get_scene_timeline(
    story_id: str,
    scene_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get scene timeline for continuity planning.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Verify story ownership
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    from pipeline.agent_tools import get_scene_timeline_impl
    
    timeline = await get_scene_timeline_impl(pool, story_id, scene_id)
    return timeline


@router.get("/stories/{story_id}/assets")
async def list_story_assets(
    story_id: str,
    asset_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    List all assets for a story.
    """
    pool = await get_pool()
    user_id = str(user["id"])
    
    # Verify story ownership
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    from pipeline.agent_tools import list_scene_assets_impl
    
    assets = await list_scene_assets_impl(pool, story_id, asset_type)
    return assets


@router.get("/providers/status")
async def get_provider_status():
    """
    Get current AI provider status.
    """
    from pipeline.agent_tools import get_provider_status_impl
    
    status = await get_provider_status_impl()
    return status
