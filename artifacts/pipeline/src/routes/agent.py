"""
Agent API routes for Dysentry Video Production.

Provides chat-based AI assistant for video production workflows.
"""

from __future__ import annotations

import json
import asyncio
from dataclasses import asdict as _dataclass_asdict
from typing import Optional, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from db.connection import get_pool
from auth import get_current_user


router = APIRouter(prefix="/pipeline/agent", tags=["agent"])


# ─── Request/Response Models ─────────────────────────────────────────────────

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
    # story_id is required so ownership can be validated before any tool runs
    story_id: str


# ─── Initialize Agent Components ─────────────────────────────────────────────

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


# ─── Streaming helper ─────────────────────────────────────────────────────────

async def _stream_agent_chat(
    pool, conversation, message: str, include_context: bool = True
) -> AsyncGenerator[bytes, None]:
    """Generate SSE events for a chat interaction."""
    components = _get_agent_components()
    executor = components["executor"]
    llm = components["llm"]

    try:
        yield f"data: {json.dumps({'type': 'started'})}\n\n".encode()

        messages = [{"role": "system", "content": components["system_prompt"]}]

        if conversation.story_id and include_context:
            try:
                ctx = await executor.execute(
                    "get_story_context", {"story_id": conversation.story_id}, pool
                )
                if ctx.success:
                    messages.append({
                        "role": "system",
                        "content": f"Story Context:\n{json.dumps(ctx.result, indent=2, default=str)}\n---\n",
                    })
            except Exception as ctx_err:
                print(f"[agent stream] context error: {ctx_err}")

        for msg in conversation.messages:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        messages.append({"role": "user", "content": message})

        tools = executor.get_tool_definitions()
        response = await llm.chat(
            messages=messages,
            tools=tools or None,
            temperature=0.7,
            max_tokens=2000,
        )

        if response.content:
            yield f"data: {json.dumps({'type': 'message', 'content': response.content})}\n\n".encode()

        actions = []
        for tc in response.tool_calls:
            yield f"data: {json.dumps({'type': 'tool_start', 'tool': tc.name})}\n\n".encode()
            tool_args = {k: v for k, v in tc.arguments.items() if k != "confirm"}
            tool_result = await executor.execute(tc.name, tool_args, pool)
            action = {
                "tool": tc.name,
                "arguments": tool_args,
                "result": tool_result.result if tool_result.success else None,
                "error": tool_result.error,
            }
            actions.append(action)
            event_type = "tool_complete" if tool_result.success else "tool_error"
            yield f"data: {json.dumps({'type': event_type, **action})}\n\n".encode()
            messages.append({
                "role": "tool",
                "content": json.dumps(tool_result.result if tool_result.success else {"error": tool_result.error}),
            })

        await components["conversation_manager"].add_message(
            pool, conversation.id, "assistant", response.content
        )
        yield f"data: {json.dumps({'type': 'done', 'message': response.content, 'actions': actions})}\n\n".encode()

    except Exception as err:
        yield f"data: {json.dumps({'type': 'error', 'message': str(err)})}\n\n".encode()


# ─── Conversation Endpoints ───────────────────────────────────────────────────

@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    user_id = str(user["id"])
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        request.story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    from pipeline.agent_service import create_agent_conversation
    return await create_agent_conversation(pool, user_id, request.story_id)


@router.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    pool = await get_pool()
    user_id = str(user["id"])
    rows = await pool.fetch(
        """SELECT id, story_id, created_at, updated_at
           FROM agent_conversations
           WHERE user_id = $1
           ORDER BY updated_at DESC LIMIT 50""",
        user_id,
    )
    return [
        {
            "conversation_id": str(r["id"]),
            "story_id": str(r["story_id"]) if r.get("story_id") else None,
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
        }
        for r in rows
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
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
    pool = await get_pool()
    user_id = str(user["id"])
    from pipeline.agent_service import get_conversation_manager
    manager = get_conversation_manager()
    deleted = await manager.delete_conversation(pool, conversation_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


# ─── Chat Endpoint (sync) ────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """Send a message to the agent and get a synchronous response."""
    pool = await get_pool()
    user_id = str(user["id"])

    components = _get_agent_components()
    executor = components["executor"]
    llm = components["llm"]

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
        story = await pool.fetchrow(
            "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
            story_id, user_id,
        )
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
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
    messages = [{"role": "system", "content": components["system_prompt"]}]

    if story_id and request.include_context:
        try:
            ctx = await executor.execute("get_story_context", {"story_id": story_id}, pool)
            if ctx.success:
                messages.append({
                    "role": "system",
                    "content": f"Story Context:\n{json.dumps(ctx.result, indent=2, default=str)}\n---\n",
                })
        except Exception as e:
            print(f"[agent chat] context error: {e}")

    for msg in conversation.messages:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    messages.append({"role": "user", "content": request.message})

    tools = executor.get_tool_definitions()
    response = await llm.chat(
        messages=messages,
        tools=tools or None,
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
        from pipeline.agent_tools import get_tool_definition
        tool_def = get_tool_definition(tc.name)
        if tool_def and tool_def.requires_confirmation and not tc.arguments.get("confirm"):
            actions.append({
                "tool": tc.name,
                "arguments": tc.arguments,
                "result": None,
                "error": "Confirmation required",
                "requires_confirmation": True,
            })
            continue

        tool_args = {k: v for k, v in tc.arguments.items() if k != "confirm"}
        tool_result = await executor.execute(tc.name, tool_args, pool)
        actions.append({
            "tool": tc.name,
            "arguments": tool_args,
            "result": tool_result.result if tool_result.success else None,
            "error": tool_result.error,
        })
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


# ─── Streaming Chat ───────────────────────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """Stream agent chat responses as Server-Sent Events."""
    pool = await get_pool()
    user_id = str(user["id"])

    from pipeline.agent_service import (
        get_conversation_manager,
        create_agent_conversation,
    )
    manager = get_conversation_manager()

    conversation_id = request.conversation_id
    story_id = request.story_id

    if conversation_id:
        conversation = await manager.get_conversation(pool, conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    elif story_id:
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
        raise HTTPException(status_code=400, detail="Either conversation_id or story_id is required")

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


@router.get("/chat-stream/{conversation_id}")
async def stream_chat_sse(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """SSE endpoint for streaming agent chat (connection setup only)."""
    pool = await get_pool()
    user_id = str(user["id"])

    from pipeline.agent_service import get_conversation_manager
    manager = get_conversation_manager()
    conversation = await manager.get_conversation(pool, conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_generator():
        yield f"data: {json.dumps({'type': 'connected', 'conversation_id': conversation_id})}\n\n".encode()
        yield f"data: {json.dumps({'type': 'ready'})}\n\n".encode()
        yield f"data: {json.dumps({'type': 'done', 'message': 'Use POST /chat/stream to send messages'})}\n\n".encode()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ─── Tool Endpoints ───────────────────────────────────────────────────────────

@router.get("/tools")
async def list_tools(user: dict = Depends(get_current_user)):
    """List all available agent tools."""
    from pipeline.agent_tools import TOOL_DEFINITIONS
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "requires_confirmation": t.requires_confirmation,
                "category": t.category,
            }
            for t in TOOL_DEFINITIONS.values()
        ]
    }


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str, user: dict = Depends(get_current_user)):
    """Get details of a specific tool."""
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
    user: dict = Depends(get_current_user),
):
    """Execute a single tool directly (no LLM).

    Requires a story_id that the authenticated user owns. The validated
    story_id is injected into tool arguments so tools cannot be redirected
    to operate on another user's resources via a spoofed argument.
    """
    pool = await get_pool()
    user_id = str(user["id"])

    # ── Ownership gate ──────────────────────────────────────────────────────
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        request.story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Validate the tool exists
    from pipeline.agent_tools import get_tool_definition
    tool_def = get_tool_definition(request.tool_name)
    if not tool_def:
        raise HTTPException(status_code=404, detail="Tool not found")

    if tool_def.requires_confirmation and not request.arguments.get("confirm"):
        raise HTTPException(status_code=400, detail="This tool requires confirmation")

    # Strip the sentinel key and force story_id to the validated value so
    # no argument can redirect execution to another user's story.
    tool_args = {k: v for k, v in request.arguments.items() if k != "confirm"}
    tool_args["story_id"] = request.story_id  # override / inject validated id

    components = _get_agent_components()
    executor = components["executor"]
    result = await executor.execute(request.tool_name, tool_args, pool)

    return {
        "tool": request.tool_name,
        "story_id": request.story_id,
        "arguments": tool_args,
        "success": result.success,
        "result": result.result,
        "error": result.error,
    }


# ─── Story Context Endpoints ──────────────────────────────────────────────────

@router.get("/stories/{story_id}/context")
async def get_story_context(
    story_id: str,
    user: dict = Depends(get_current_user),
):
    """Get complete story context for the agent."""
    pool = await get_pool()
    user_id = str(user["id"])
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
    """Get scene with adjacent scenes for continuity planning."""
    pool = await get_pool()
    user_id = str(user["id"])
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    components = _get_agent_components()
    result = await components["executor"].execute(
        "get_scene_timeline", {"story_id": story_id, "scene_id": scene_id}, pool
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.result


@router.get("/stories/{story_id}/assets")
async def list_story_assets(
    story_id: str,
    asset_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List all assets for a story."""
    pool = await get_pool()
    user_id = str(user["id"])
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    components = _get_agent_components()
    asset_manager = components["asset_manager_class"](pool)
    assets = await asset_manager.get_assets(
        story_id=story_id, asset_type=asset_type, entity_type=entity_type,
    )
    try:
        assets_data = [_dataclass_asdict(a) for a in assets]
    except Exception:
        assets_data = [a.__dict__ if hasattr(a, "__dict__") else dict(a) for a in assets]
    return {"story_id": story_id, "assets": assets_data, "total": len(assets_data)}


@router.get("/stories/{story_id}/assets/search")
async def search_story_assets(
    story_id: str,
    q: str,
    asset_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Search assets within a story."""
    pool = await get_pool()
    user_id = str(user["id"])
    story = await pool.fetchrow(
        "SELECT id FROM stories WHERE id = $1 AND owner_id = $2",
        story_id, user_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    components = _get_agent_components()
    asset_manager = components["asset_manager_class"](pool)
    assets = await asset_manager.search_assets(story_id=story_id, query=q, asset_type=asset_type)
    try:
        assets_data = [_dataclass_asdict(a) for a in assets]
    except Exception:
        assets_data = [a.__dict__ if hasattr(a, "__dict__") else dict(a) for a in assets]
    return {"query": q, "results": assets_data, "total": len(assets_data)}


# ─── Provider Status ──────────────────────────────────────────────────────────

@router.get("/providers/status")
async def get_provider_status(user: dict = Depends(get_current_user)):
    """Get status of video generation providers."""
    try:
        from pipeline.provider_status import get_provider_status
        return await get_provider_status()
    except Exception as e:
        return {"error": str(e), "providers": {"dashscope": {"status": "unknown"}}}
