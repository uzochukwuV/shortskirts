# Chat Systems Consolidation Plan

## Current State Analysis

### Implementation 1: `routes/chat.py` (from main)
| Aspect | Details |
|--------|---------|
| **LLM** | OpenHands Agent SDK (`openhands.sdk`) |
| **Tools** | Built-in, simple implementations (10 tools) |
| **Storage** | Redis for conversations |
| **Streaming** | None (request/response only) |
| **Model** | `qwen-plus` via DashScope |
| **Tool Format** | OpenAPI-style function definitions |

### Implementation 2: `routes/agent.py` + `agent_*.py` (our work)
| Aspect | Details |
|--------|---------|
| **LLM** | Custom `agent_llm.py` with function calling |
| **Tools** | 29 production tools registered |
| **Storage** | PostgreSQL (CockroachDB) |
| **Streaming** | SSE with custom events |
| **Model** | TokenRouter (moonshotai/kimi-k3-free) |
| **Tool Format** | Pydantic dataclass + dict |

### Streaming: `streaming_orchestrator.py` + `providers/dashscope.py`
| Aspect | Details |
|--------|---------|
| **SDK** | GenBlaze SDK |
| **Provider** | DashScopeVideoProvider |
| **Events** | GenBlaze-style ProgressEvent |
| **Storage** | B2 via genblaze-s3 |
| **Features** | Real-time progress, polling |

---

## Consolidation Strategy

### Keep from Each

| From | Keep | Rationale |
|------|------|-----------|
| `chat.py` | OpenHands SDK integration | Well-structured SDK usage |
| `agent.py` | Route structure | Cleaner API design |
| `agent_tools.py` | Tool registry pattern | Better organization |
| `agent_service.py` | Executor + conversation manager | More features |
| `agent_llm.py` | TokenRouter support | Our LLM infrastructure |
| `agent_media_tools.py` | 29 production tools | Complete coverage |
| `agent_production_tools.py` | Assembly, SEO, thumbnails | Post-production |
| `streaming_orchestrator.py` | GenBlaze events | Industry standard |
| `providers/dashscope.py` | Custom GenBlaze provider | Already integrated |

---

## Architecture After Consolidation

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                             │
│                  AgentChat.jsx - EventSource                      │
└────────────────────────────┬────────────────────────────────────┘
                              │ SSE / HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Routes                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  routes/chat.py │  │ routes/agent.py │  │routes/stream.py │  │
│  │ (OpenHands SDK) │  │  (Our executor) │  │  (SSE events)  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED AGENT SYSTEM                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              AgentLLM (TokenRouter + DashScope)            │ │
│  │  • Function calling support                                 │ │
│  │  • Streaming responses                                      │ │
│  │  • Tool execution loop                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Tool Registry (29 tools)                       │ │
│  │  • Scene/Story CRUD                                        │ │
│  │  • Video Generation (DashScope)                            │ │
│  │  • Frame Extraction (FFmpeg)                               │ │
│  │  • Assembly/Audio/SEO                                      │ │
│  │  • Continuity/Character refs                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           Conversation Manager (DB-backed)                  │ │
│  │  • Story-linked conversations                               │ │
│  │  • Message history                                         │ │
│  │  • Context injection                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  DashScope API │ │  DashScope API   │ │     B2 S3      │
│  (Video Gen)   │ │  (LLM - TokenRouter)│ │   (Storage)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Unified API Design

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/pipeline/agent/conversations` | Create conversation |
| GET | `/pipeline/agent/conversations/{id}` | Get conversation |
| DELETE | `/pipeline/agent/conversations/{id}` | Delete conversation |
| POST | `/pipeline/agent/chat` | Send message (sync) |
| GET | `/pipeline/agent/chat-stream` | SSE chat stream |
| GET | `/pipeline/agent/tools` | List all tools |
| POST | `/pipeline/agent/tools/execute` | Execute single tool |
| GET | `/pipeline/agent/stories/{id}/context` | Get story context |
| GET | `/pipeline/agent/stories/{id}/timeline` | Get scene timeline |

### Event Types (SSE)

```typescript
// Connection
{ type: "connected", conversation_id: string }

// Message streaming
{ type: "message", content: string, done: boolean }

// Tool execution
{ type: "tool_start", tool: string, arguments: object }
{ type: "tool_progress", tool: string, message: string }
{ type: "tool_complete", tool: string, result: object }
{ type: "tool_error", tool: string, error: string }

// Generation events (from streaming_orchestrator)
{ type: "generation.started", scene_id: number }
{ type: "generation.progress", scene_id: number, pct: 0-100 }
{ type: "generation.completed", scene_id: number, video_url: string }
{ type: "generation.failed", scene_id: number, error: string }

// Final
{ type: "done", message: string }
```

---

## Tool Consolidation

### Merged Tool List (Priority)

**Phase 1 - Core (Must have)**
| Tool | Source | Description |
|------|--------|-------------|
| `create_story` | chat.py | Create new story |
| `get_story` | chat.py + agent | Get story details |
| `list_stories` | chat.py | List user's stories |
| `create_scene` | agent | Add scene to episode |
| `update_scene` | agent | Modify scene |
| `delete_scene` | agent | Remove scene |
| `get_scene_timeline` | agent | Get adjacent scenes |
| `generate_video` | agent | Generate scene video |
| `wait_for_generation` | agent | Poll job status |
| `approve_scene` | chat.py + agent | Approve for assembly |
| `assemble_episode` | agent + chat | Stitch scenes |

**Phase 2 - Media (Important)**
| Tool | Source | Description |
|------|--------|-------------|
| `extract_scene_frame` | agent | Extract frame at timestamp |
| `screenshot_previous_scene` | agent | Get exit frame |
| `extract_character_from_scene` | agent | Extract + set ref |
| `set_character_reference` | agent | Set face consistency |
| `set_scene_continuity` | agent | Link scenes |

**Phase 3 - Advanced (Nice to have)**
| Tool | Source | Description |
|------|--------|-------------|
| `generate_script_and_scenes` | agent | AI script + scenes |
| `generate_narration` | agent | Text-to-speech |
| `generate_thumbnail` | agent | AI thumbnail |
| `generate_seo_metadata` | agent | SEO tags |
| `add_transition` | agent | Fade/dissolve |
| `check_style_consistency` | agent | Detect issues |
| `compare_scenes` | agent | A/B testing |
| `search_assets` | agent | Search content |

---

## Implementation Steps

### Step 1: Create Unified Agent Module

```python
# pipeline/unified_agent.py
"""
Unified Agent System
- Combines best of both implementations
- Uses TokenRouter for LLM
- Uses DashScopeVideoProvider for video
- GenBlaze-style events for streaming
"""

from pipeline.agent_llm import AgentLLM, ChatMessage
from pipeline.agent_tools import ToolRegistry, register_tools
from pipeline.agent_service import ConversationManager, ToolExecutor
from pipeline.streaming_orchestrator import StreamingOrchestrator
```

### Step 2: Merge Tool Registries

```python
# Consolidate into single registry
TOOLS = {
    # From chat.py
    "create_story": create_story_impl,
    "list_stories": list_stories_impl,
    "get_story": get_story_impl,
    "approve_outline": approve_outline_impl,
    # From agent_tools
    "get_story_context": get_story_context_impl,
    "get_scene_timeline": get_scene_timeline_impl,
    # From agent_media_tools
    "extract_scene_frame": extract_scene_frame_impl,
    "screenshot_previous_scene": screenshot_previous_scene_impl,
    # ... etc
}
```

### Step 3: Unify LLM Client

```python
# Use TokenRouter + DashScope (existing)
LLM_CONFIG = {
    "provider": "tokenrouter",  # or "dashscope"
    "model": "moonshotai/kimi-k3-free",
    "api_key": os.getenv("TOKENROUTER_API_KEY"),
    "base_url": "https://api.tokenrouter.com/v1",
}

# Fallback to DashScope if needed
if not LLM_CONFIG["api_key"]:
    LLM_CONFIG = {
        "provider": "dashscope",
        "model": "qwen-plus",
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
```

### Step 4: Integrate Streaming Events

```python
# In chat streaming
async def chat_stream(request):
    orchestrator = StreamingOrchestrator()
    
    async def event_generator():
        # Send generation events
        async for event in orchestrator.stream(story_id):
            yield f"data: {event.to_json()}\n\n"
        
        # Send chat response
        yield f"event: message\ndata: {{'type': 'message', 'content': '{response}'}}\n\n"
        
        yield "data: {\"type\": \"done\"}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `pipeline/unified_agent.py` | Create | Main unified module |
| `pipeline/agent_tools_merged.py` | Create | Consolidated tool implementations |
| `routes/agent.py` | Modify | Use unified agent |
| `routes/chat.py` | Deprecate | Keep for compatibility |
| `routes/stream.py` | Modify | Integrate with unified agent |
| `main.py` | Modify | Register unified routers |

---

## Migration Path

1. **Week 1**: Create `unified_agent.py`, merge tools
2. **Week 2**: Update `routes/agent.py` to use unified module
3. **Week 3**: Add streaming from `streaming_orchestrator`
4. **Week 4**: Deprecate `chat.py`, keep for backward compat
5. **Week 5**: Test and polish

---

## Summary

**Best features to keep:**
- ✅ Our 29 production tools (most complete)
- ✅ TokenRouter-based LLM (flexible)
- ✅ DB-backed conversations (persistent)
- ✅ SSE streaming (real-time)
- ✅ GenBlaze-style events (industry standard)
- ✅ DashScopeVideoProvider (video generation)

**Best features to add:**
- ⭐ OpenHands SDK pattern for agent creation
- ⭐ Simpler conversation model from chat.py

**Result:** A unified agent system that uses our comprehensive toolset with the clean architecture patterns from both implementations.
