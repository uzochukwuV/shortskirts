# LLM Agent Orchestrator - Dysentry Video Production

**Status:** Design & Implementation Plan  
**Target:** Make Dysentry truly agentic - chat-driven video production assistant  
**Media Path:** Uses existing `generation_coordinator` → `scene_gen` pipeline (DashScope/AIML)

---

## Executive Summary

Transform Dysentry from a manual workflow-driven app into an agentic system where users can **chat naturally** with an AI production assistant that:

1. Understands production context (stories, characters, scenes, continuity)
2. Executes complex multi-step tasks (create scenes, modify scripts, manage continuity)
3. Monitors generation progress and reports back
4. Maintains visual consistency across scenes via exit frame continuity
5. Provides intelligent suggestions and automations

### Target User Experience

```
User: "Create a new scene where Mara enters the coffee shop. Use the rainy street vibe from scene 2."

Agent: "Got it! I'll create a new scene (Scene 6) with Mara entering a cozy coffee shop, 
       maintaining the rainy atmosphere. The previous exit frame from Scene 2 shows the 
       street at night - I'll reference that for continuity. Should I also add dialogue 
       or keep it as a visual-only scene?"

User: "Add some dialogue where she orders a latte"

Agent: "Perfect. Creating Scene 6 with:
       - Location: Coffee shop interior, rain visible through windows
       - Characters: Mara (primary)
       - Mood: Warm contrast against cold exterior
       - Duration: ~6 seconds
       - Dialogue: Mara orders a latte
       
       Queuing scene generation... [Status: Generating]
       
       ✅ Scene 6 complete! The scene shows Mara stepping in from the rain, 
       shaking off her umbrella. The warm coffee shop lighting contrasts beautifully 
       with the blue-gray street outside. Exit frame captured for Scene 7 continuity."
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                               │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────────────────┐│
│  │   Editor    │  │   Agent Chat UI   │  │    Generation Progress Panel     ││
│  │   (Scene    │  │  (New Component) │  │    (Polling & Streaming)        ││
│  │   Editor)   │  │                  │  │                                  ││
│  └─────────────┘  └──────────────────┘  └─────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND: FastAPI Pipeline                           │
│                                                                              │
│  ┌────────────────┐    ┌──────────────────────┐    ┌───────────────────────┐ │
│  │   Existing     │    │   Agent Orchestrator │    │   Job Queue &        │ │
│  │   REST API     │◄──►│   (NEW SERVICE)     │───►│   Background Workers │ │
│  │   Routes       │    │                     │    │                       │ │
│  └────────────────┘    └──────────────────────┘    └───────────────────────┘ │
│           ▲                      │                                            │
│           │                      ▼                                            │
│           │            ┌──────────────────────┐                             │
│           │            │   Tool Registry       │                             │
│           │            │   (Typed, Validated)  │                             │
│           │            └──────────────────────┘                             │
│           │                      │                                            │
│           ▼                      ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    EXISTING PIPELINE COMPONENTS                         │ │
│  │  generation_coordinator → scene_gen → provider_executor → scene_gen   │ │
│  │  story_agent (LLM calls)  │  operations_agent  │  assembler           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         DATA LAYER                                     │ │
│  │  PostgreSQL (CockroachDB)  │  Redis  │  B2 Storage                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Service Design

### 1. Session Management

```python
# New table: agent_conversations
class AgentConversation(BaseModel):
    id: UUID
    user_id: UUID
    story_id: UUID
    session_id: str  # OpenHands SDK session identifier
    created_at: datetime
    updated_at: datetime
```

### 2. Message Protocol

```python
class AgentMessage(BaseModel):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[ToolResult]] = None
    created_at: datetime

class AgentRequest(BaseModel):
    conversation_id: Optional[UUID] = None
    story_id: UUID
    message: str
    context_snapshot: Optional[dict] = None  # Current editor state

class AgentResponse(BaseModel):
    conversation_id: UUID
    message: str
    tool_calls: List[ToolCall] = []
    action_summary: Optional[dict] = None
    streaming: bool = False
```

### 3. Tool Registry Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AGENT TOOL REGISTRY                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  READ TOOLS (always available)                                       │
│  ├── get_story_context          → Story, episode plan, status       │
│  ├── get_scene_timeline         → Adjacent scenes, continuity state  │
│  ├── list_scene_assets          → Character refs, exit frames       │
│  ├── get_provider_status        → DashScope/AIML availability       │
│  ├── get_job_status             → Active generation jobs            │
│  ├── search_reference_library   → Approved assets by tags           │
│  └── get_generation_history     → Event sourcing audit trail        │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  MUTATION TOOLS (require confirmation for destructive actions)       │
│  ├── create_scene               → New scene with auto-numbering      │
│  ├── update_scene               → Edit script/prompt/metadata        │
│  ├── delete_scene               → Remove scene (with confirmation)   │
│  ├── reorder_scenes             → Change scene sequence              │
│  ├── set_scene_continuity      → Assign exit frame reference        │
│  ├── regenerate_scene           → Re-generate scene media            │
│  ├── approve_scene             → Mark scene as approved             │
│  ├── lock_scene                 → Prevent accidental regeneration  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  GENERATION TOOLS (orchestrate via existing pipeline)                │
│  ├── enqueue_scene_generation  → Trigger gen via coordinator       │
│  ├── enqueue_episode_assembly   → Assemble final episode            │
│  ├── wait_for_generation        → Poll job status until complete    │
│  └── cancel_active_generation   → Cancel running jobs               │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ASSISTANT TOOLS (LLM-powered suggestions)                           │
│  ├── suggest_scene_improvements → LLM analysis of scene script      │
│  ├── suggest_continuity_fix     → Recommend reference adjustments   │
│  └── generate_scene_description → Create scene from natural language│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tool Specifications

### A. Read Tools

#### `get_story_context`
```python
async def get_story_context(story_id: str) -> dict:
    """
    Returns complete story state for agent context.
    
    Response:
    {
        "id": "uuid",
        "title": "...",
        "status": "draft|generating|completed|...",
        "workflow_type": "creator_series|...",
        "episode_plan": { synopsis, characters, episodes[...] },
        "characters": [...],
        "scenes": [...],  # All scenes with status, media URLs
        "checkpoints": [...],
        "pipeline_config": {...},
        "bibles": [...],
        "active_jobs": [...],
    }
    """
```

#### `get_scene_timeline`
```python
async def get_scene_timeline(story_id: str, scene_id: str) -> dict:
    """
    Returns adjacent scene context for continuity planning.
    
    Response:
    {
        "previous_scene": {
            "id": "...",
            "scene_number": 2,
            "exit_frame_url": "https://...",
            "exit_summary": "Mara standing on rainy street, looking at coffee shop",
            "characters": ["Mara"],
        },
        "current_scene": {...},
        "next_scene": {
            "id": "...",
            "scene_number": 4,
            "entry_frame_description": "Mara enters coffee shop",
        },
        "continuity_notes": "Rainy street → coffee shop transition"
    }
    """
```

#### `get_provider_status`
```python
async def get_provider_status() -> dict:
    """
    Returns real-time provider availability.
    
    Response:
    {
        "dashscope": {
            "wan2.7_i2v": {"available": true, "queue_time": "2min"},
            "wan2.7_t2v": {"available": true, "queue_time": "1min"},
            "happyhorse": {"available": true},
        },
        "aiml": {
            "wan2.7_i2v": {"available": true},
        },
        "recommendation": "dashscope"  # Preferred provider
    }
    """
```

### B. Mutation Tools

#### `create_scene`
```python
async def create_scene(
    story_id: str,
    episode_id: str,
    scene_data: dict,  # title, description, prompt, location, mood, etc.
    insert_after: Optional[int] = None,  # Scene number to insert after
    auto_reorder: bool = True,
) -> dict:
    """
    Creates a new scene with proper numbering.
    Optionally reorders subsequent scenes.
    """
    # Returns: {scene_id, scene_number, scene_data, affected_scenes: [...]}
```

#### `set_scene_continuity`
```python
async def set_scene_continuity(
    source_scene_id: str,
    target_scene_id: str,
    continuity_type: Literal["exit_frame", "character_ref", "style_ref"],
    extract_frame: bool = True,  # Auto-extract from source if video
) -> dict:
    """
    Links scenes for continuity. Optionally extracts exit frame from video.
    """
    # Returns: {continuity_link_id, exit_frame_url, summary}
```

#### `wait_for_generation`
```python
async def wait_for_generation(
    job_id: str,
    poll_interval_seconds: int = 5,
    timeout_seconds: int = 600,
) -> dict:
    """
    Polls job status until completion. Returns final state.
    Streams progress via SSE/WebSocket.
    """
    # Yields: {"status": "running", "progress": "Scene 3/8"}
    # Final: {"status": "completed", "scene_id": "...", "media_url": "..."}
```

### C. Assistant Tools

#### `generate_scene_description`
```python
async def generate_scene_description(
    story_id: str,
    instruction: str,  # "Mara enters the coffee shop on a rainy day"
) -> dict:
    """
    LLM-powered scene generation from natural language.
    Returns structured scene data ready for creation.
    """
    # Returns: {scene_data, suggested_media_kind, estimated_duration}
```

---

## API Endpoints

### Agent Service Routes

```python
# /pipeline/agent/conversations
POST   /conversations           # Start new conversation for a story
GET    /conversations/{id}     # Get conversation history
DELETE /conversations/{id}      # End conversation

# /pipeline/agent/chat
POST   /chat                    # Send message, get response + tool calls
WS     /ws/chat/{conv_id}       # WebSocket for streaming responses

# /pipeline/agent/tools
GET    /tools                   # List available tools
GET    /tools/{tool_name}       # Get tool schema

# /pipeline/agent/stories/{story_id}
GET    /context                 # Get full story context for agent
GET    /timeline/{scene_id}     # Get continuity timeline
POST   /execute                 # Execute tool call directly (bypass chat)
```

### Request/Response Examples

#### Start Conversation
```http
POST /pipeline/agent/conversations
Content-Type: application/json

{
    "story_id": "uuid",
    "system_prompt": "You are a video production assistant..."  # Optional
}

Response 201:
{
    "conversation_id": "uuid",
    "session_id": "sdk-session-id",
    "story_context": {...}  // Immediate context dump
}
```

#### Send Message
```http
POST /pipeline/agent/chat
Content-Type: application/json

{
    "conversation_id": "uuid",
    "message": "Create a new scene where Mara enters the coffee shop",
    "include_context": true  // Include story snapshot
}

Response 200 (streaming):
event: tool_call
data: {"tool": "create_scene", "args": {...}}

event: tool_result
data: {"tool": "create_scene", "result": {"scene_id": "...", ...}}

event: message
data: {"content": "Created Scene 6 - Mara entering the coffee shop..."}

event: done
data: {"summary": {...}}
```

---

## Frontend Integration

### New Components

```
web/src/
├── components/
│   └── agent/
│       ├── AgentChat.tsx           # Main chat interface
│       ├── AgentMessage.tsx        # Message bubble component
│       ├── ToolCallCard.tsx        # Tool execution display
│       ├── GenerationProgress.tsx   # Live job progress
│       └── ScenePreview.tsx        # Inline scene preview
```

### AgentChat Component

```tsx
interface AgentChatProps {
    storyId: string;
    conversationId?: string;
    onSceneCreated?: (scene: Scene) => void;
    onGenerationStarted?: (job: Job) => void;
}

// Features:
// - Message input with @-mentions for scenes/characters
// - Tool call visualization cards
// - Inline scene previews from media URLs
// - Generation progress integration
// - Voice input support (future)
```

### Integration with Editor

```tsx
// Editor.jsx additions
const [agentConversationId, setAgentConversationId] = useState<string | null>(null);
const [showAgentPanel, setShowAgentPanel] = useState(false);

// Agent panel toggle button in toolbar
<Button onClick={() => setShowAgentPanel(!showAgentPanel)}>
    <SparklesIcon /> AI Assistant
</Button>

// Slide-out agent panel
{showAgentPanel && (
    <AgentChat 
        storyId={storyId}
        conversationId={agentConversationId}
        onConversationCreated={setAgentConversationId}
        onSceneCreated={(scene) => {
            // Refresh scene list
            refreshScenes();
            // Optionally select the new scene
            selectScene(scene.id);
        }}
    />
)}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Core agent service with session management and read tools

- [ ] Create `agent_service.py` module
- [ ] Add `agent_conversations` table to schema
- [ ] Implement session creation/deletion endpoints
- [ ] Build tool registry with base read tools:
  - `get_story_context`
  - `get_scene_timeline`
  - `list_scene_assets`
- [ ] Basic chat endpoint with LLM integration
- [ ] Simple text response (no tool execution yet)

### Phase 2: Tool Execution (Week 2)
**Goal:** Full tool execution with confirmation flows

- [ ] Complete tool registry (all read + mutation tools)
- [ ] Tool call parsing and execution engine
- [ ] Confirmation modal for destructive actions
- [ ] Tool result formatting for LLM context
- [ ] Error handling and retry logic

### Phase 3: Continuity Engine (Week 3)
**Goal:** Visual continuity management

- [ ] Exit frame extraction service (from video bytes)
- [ ] `set_scene_continuity` tool
- [ ] Continuity validation on scene creation
- [ ] Reference frame injection into generation prompts
- [ ] Continuity report tool

### Phase 4: Job Orchestration (Week 4)
**Goal:** Generation job management and streaming

- [ ] Job polling service with SSE streaming
- [ ] `wait_for_generation` with progress callbacks
- [ ] Background job status aggregation
- [ ] Notification system for completion/failure
- [ ] Automatic continuation suggestion after completion

### Phase 5: Frontend Integration (Week 5)
**Goal:** User-facing chat interface

- [ ] AgentChat component with message history
- [ ] Tool call visualization cards
- [ ] Scene preview thumbnails
- [ ] Generation progress integration
- [ ] @-mention autocomplete for scenes/characters
- [ ] Mobile-responsive design

### Phase 6: Polish & Testing (Week 6)
**Goal:** Production-ready

- [ ] Rate limiting and cost controls
- [ ] Prompt injection prevention
- [ ] Comprehensive error messages
- [ ] Unit tests for all tools
- [ ] Integration tests for conversation flows
- [ ] Performance optimization
- [ ] Documentation

---

## Key Design Decisions

### 1. Keep Existing Pipeline Intact
The agent **wraps** existing services, never replaces them:
- Agent calls `enqueue_job()` → same Redis queue
- Agent uses `generation_coordinator` → same media generation flow
- Agent reads from same PostgreSQL tables

### 2. Tool Calls are Explicit
Every action goes through typed, validated tools:
- Agent can't directly modify database
- All mutations are auditable
- Confirmation required for destructive operations

### 3. Continuity as First-Class
Exit frames stored and injected automatically:
- Every scene generates exit frame on completion
- New scenes can reference any prior exit frame
- Continuity state passed to generation prompt

### 4. Streaming Everywhere
User sees real-time progress:
- SSE for generation status
- Tool call visualization as they execute
- Incremental scene previews

### 5. Session-Based Context
Conversations persist context:
- User can reference previous messages
- Agent maintains story understanding
- Easy to resume abandoned conversations

---

## Data Flow Examples

### Scene Creation Flow
```
User: "Add a scene where Mara enters the coffee shop"
    │
    ▼
Agent (LLM) parses intent
    │
    ▼
Tool Call: create_scene({
    story_id: "...",
    episode_id: "...",
    scene_data: {
        title: "Mara Enters the Coffee Shop",
        description: "...",
        location: "Coffee shop interior",
        mood: "warm contrast to rainy exterior",
        ...
    },
    insert_after: 5  // After current last scene
})
    │
    ▼
API validates ownership, checks story status
    │
    ▼
Database INSERT with scene number reordering
    │
    ▼
Response: {scene_id, scene_number, affected_scenes}
    │
    ▼
Agent: "Created Scene 6. Want me to generate it now?"
```

### Generation with Continuity Flow
```
User: "Generate scene 6"
    │
    ▼
Tool Call: enqueue_scene_generation({
    scene_id: "...",
    use_continuity: true,
    continuity_from_scene: 2  // Reference exit frame from scene 2
})
    │
    ▼
System extracts exit frame from scene 2 (if not cached)
    │
    ▼
generation_coordinator.build_scene_prompt() includes:
    - Previous exit frame URL
    - Continuity description
    - Style consistency notes
    │
    ▼
Job enqueued to Redis
    │
    ▼
Agent waits via SSE polling
    │
    ▼
On completion:
    - Extract new exit frame
    - Update scene.exit_frame_url
    - Agent confirms: "Scene 6 complete!"
```

---

## Configuration

### Environment Variables
```bash
# Agent Service
AGENT_MODEL=qwen-max
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOOLS_PER_RESPONSE=3
AGENT_CONFIRM_THRESHOLD=medium  # low|medium|high
AGENT_SESSION_TIMEOUT_MINUTES=60

# Streaming
AGENT_SSE_POLL_INTERVAL=2  # seconds
AGENT_JOB_POLL_INTERVAL=5  # seconds

# Cost Controls
AGENT_MAX_MUTATIONS_PER_SESSION=50
AGENT_COST_LIMIT_USD=10.0
```

### Feature Flags
```python
AGENT_ENABLED = os.getenv("AGENT_ENABLED", "true")
AGENT_TOOLS_MUTATION_ENABLED = os.getenv("AGENT_TOOLS_MUTATION_ENABLED", "true")
AGENT_STREAMING_ENABLED = os.getenv("AGENT_STREAMING_ENABLED", "true")
CONTINUITY_AUTO_EXTRACT = os.getenv("CONTINUITY_AUTO_EXTRACT", "true")
```

---

## Security Considerations

1. **Authorization**: All tools validate user ownership of story/scene
2. **Rate Limiting**: Per-user limits on tool calls and LLM calls
3. **Prompt Injection**: Untrusted user input sanitized before LLM context
4. **Audit Trail**: All tool calls logged with user, timestamp, result
5. **Cost Controls**: Budget limits per conversation

---

## Success Metrics

1. **Engagement**: Users with agent conversations vs. total users
2. **Task Completion**: % of agent requests that complete successfully
3. **Time to Action**: Average time from request to scene creation/generation
4. **Continuity Quality**: Manual review of scene transitions
5. **User Satisfaction**: Feedback surveys in chat UI

---

## References

- Existing plan: `docs/video-series-agent-sdk-plan.md`
- Current pipeline: `artifacts/pipeline/PIPELINE.md`
- Database schema: `artifacts/pipeline/src/db/schema.sql`
- Frontend client: `web/src/api/dysentryClient.js`
