"""
Agent API routes for Dysentry Video Production.

Provides chat-based AI assistant for video production workflows.
"""

from __future__ import annotations

import json
from typing import Optional, AsyncGenerator
from pydantic import BaseModel, Field

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
    include_context: bool = True


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


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

async def _stream_agent_chat(
    pool,
    conversation,
    user_message: str,
    include_context: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Stream agent chat responses as Server-Sent Events.
    Events: tool_start, tool_complete, tool_error, message, done
    """
    from pipeline.agent_service import (
        get_agent_executor,
        get_all_tools,
    )
    from pipeline.agent_llm import ChatMessage, agent_chat
    
    executor = get_agent_executor()
    tools = get_all_tools()
    
    # Build messages
    messages = []
    
    # Add context
    if include_context and conversation.story_id:
        try:
            from pipeline.agent_tools import get_story_context_impl
            story_context = await get_story_context_impl(pool, conversation.story_id)
            context_msg = f"""Current Story Context:
{json.dumps(story_context, indent=2, default=str)}

---"""
            messages.append(ChatMessage(role="system", content=context_msg))
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': f'Context error: {e}'})}\n\n"
    
    # Add history
    for msg in conversation.messages:
        messages.append(ChatMessage(
            role=msg["role"],
            content=msg["content"],
        ))
    
    # Add user message
    messages.append(ChatMessage(role="user", content=user_message))
    
    # LLM interaction loop
    iteration = 0
    response_content = ""
    
    while iteration < executor.max_iterations:
        iteration += 1
        retry_count = 0
        max_retries = 3
        
        # Call LLM with retry
        response = None
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
                retry_count += 1
                if retry_count < max_retries:
                    import asyncio
                    await asyncio.sleep(2)
                else:
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': f'LLM error: {e}'})}\n\n"
                    return
        
        # Send message chunk
        if response.content:
            response_content = response.content
            yield f"event: message\ndata: {json.dumps({'type': 'message', 'content': response.content})}\n\n"
        
        # Add to messages
        messages.append(ChatMessage(role="assistant", content=response.content))
        
        # Process tool calls
        if not response.tool_calls:
            break
        
        for tc in response.tool_calls:
            tool_name = tc.name
            arguments = tc.arguments
            tool_call_id = tc.id or f"call_{iteration}_{tool_name}"
            
            # Send tool start event
            yield f"event: tool_start\ndata: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'arguments': arguments, 'id': tool_call_id})}\n\n"
            
            # Execute tool
            try:
                from pipeline.agent_service import execute_tool
                tool_result = await execute_tool(tool_name, arguments, pool)
                
                # Send tool complete event
                yield f"event: tool_complete\ndata: {json.dumps({'type': 'tool_complete', 'tool': tool_name, 'id': tool_call_id, 'result': tool_result})}\n\n"
            except Exception as e:
                # Send tool error event
                yield f"event: tool_error\ndata: {json.dumps({'type': 'tool_error', 'tool': tool_name, 'id': tool_call_id, 'error': str(e)})}\n\n"
                tool_result = {"success": False, "error": str(e)}
            
            # Add tool result to messages
            result_str = json.dumps(tool_result, default=str)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": f"Tool {tool_name} result: {result_str}",
                "name": tool_name,
            })
    
    # Send done event
    yield f"event: done\ndata: {json.dumps({'type': 'done', 'message': response_content})}\n\n"


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
