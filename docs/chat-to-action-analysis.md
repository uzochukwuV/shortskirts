# Chat-to-Action: Conversational Orchestration Analysis

## Current State

### What's Implemented

The codebase has a **ConversationalOrchestrator** class (`src/pipeline/conversational_orchestrator.py`) with chat-based scene generation capabilities:

```python
orchestrator = ConversationalOrchestrator()

# Create story
story = await orchestrator.create_story("A samurai story")

# Chat to generate scenes
response = await orchestrator.chat(story.id, "Generate scene 1 with master introducing himself")
response = await orchestrator.chat(story.id, "Add scene 2 where student responds")
response = await orchestrator.chat(story.id, "Combine scenes 1-3")
```

**Supported Commands:**
- `generate scene` / `add scene` / `create scene` - Create new scene
- `regenerate scene N` - Regenerate existing scene
- `combine` / `concatenate` / `join` - Concatenate scenes
- `timeline` / `show scenes` / `list scenes` - View timeline
- `dialogue` / `character` - Add dialogue (partial)

---

## Critical Limitations

### 1. **No HTTP Endpoint for Chat Interface**

| Issue | Evidence |
|-------|----------|
| ConversationalOrchestrator exists but has NO API route | `conversational_orchestrator.py` is never imported in routes |
| Main.py documents `/pipeline/stories/{id}/operations-agent` but endpoint doesn't exist | Line 114: `"POST   /pipeline/stories/{id}/operations-agent"` |
| Frontend cannot invoke chat-based workflow | Only `POST /stories/{id}/assistant` exists (for LLM suggestions, not execution) |

**Impact:** Users must use rigid REST endpoints instead of natural chat.

---

### 2. **In-Memory State Only**

```python
class ConversationalOrchestrator:
    def __init__(self):
        self._stories: dict[str, Story] = {}  # ← In-memory only!
```

**Problems:**
- Stories lost on server restart
- Cannot scale horizontally (multiple workers = different memory)
- No persistence to database or B2

**Current workaround:** Uses B2 for state persistence (`load_story_from_b2`, `save_story_to_b2`) but not integrated.

---

### 3. **Primitive Intent Parsing**

```python
# Current approach - simple string matching
message = message.lower().strip()

if "generate scene" in message or "add scene" in message or "create scene" in message:
    # ...
elif "regenerate scene" in message:
    # ...
elif "combine" in message:
    # ...
```

**Problems:**
- No LLM-powered understanding
- Cannot handle variations: "make a new scene", "I need another clip", "add a new shot"
- No context awareness (previous commands)
- No error recovery for malformed requests

---

### 4. **Database/Backend Not Integrated**

The ConversationalOrchestrator operates on its own data structures:

```python
@dataclass
class Scene:
    id: int
    title: str
    prompt: str
    dialogues: list[DialogueLine]
    references: list[SceneReference]
    status: SceneStatus
    video_url: Optional[str]
```

**Problems:**
- No foreign keys to actual database records
- Cannot query via REST API
- Story state exists in two places (DB + orchestrator memory)
- Sync issues on partial failures

---

### 5. **No Conversation History**

```python
async def chat(self, story_id: str, message: str) -> dict:
    # No conversation_id parameter
    # No message history stored
```

**Problems:**
- No context between messages
- Cannot reference "the scene we just created"
- No undo/redo capability

---

### 6. **Missing Features in Chat Interface**

| Feature | Status | Notes |
|---------|--------|-------|
| Character references | ❌ Not integrated | Can define but not generate |
| Scene approval workflow | ❌ Missing | No checkpoint/review system |
| Parallel scene generation | ⚠️ Partial | Orchestrator doesn't use it |
| Frame extraction | ✅ Implemented | `extract_frame()` exists |
| Continuity (exit frames) | ⚠️ Code exists | Not wired to chat |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  Chat Interface ──► /pipeline/stories/{id}/operations-agent      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  ❌ ENDPOINT DOESN'T EXIST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API ROUTES (stories.py)                     │
│  POST /stories/{id}/assistant ──► suggest_story_edit()          │
│         │                                                       │
│         └──► Returns PATCH, doesn't execute                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│            EXISTING GENERATION WORKFLOW                          │
│                                                                  │
│  POST /stories ──► Create Story (LLM generates outline)         │
│  PUT /approve-outline ──► Approve                                │
│  POST /generate ──► Queue Job ──► job_handlers.py ──► Orchestrator│
│                                                                  │
│  ❌ Not triggered by chat commands                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│          ConversationalOrchestrator (NEVER CALLED!)               │
│                                                                  │
│  ✅ chat() method exists                                          │
│  ✅ Scene generation methods exist                                 │
│  ✅ Frame extraction exists                                       │
│  ❌ No HTTP endpoint integration                                  │
│  ❌ In-memory only                                               │
│  ❌ No DB sync                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Improvement Roadmap

### Phase 1: HTTP Endpoint Integration (High Priority)

**Goal:** Make chat accessible via HTTP

```python
# New route: POST /pipeline/stories/{story_id}/chat
@router.post("/{story_id}/chat")
async def chat_with_story(
    story_id: str,
    body: ChatRequest,
    user=Depends(get_current_user),
    orchestrator: ConversationalOrchestrator = Depends(get_orchestrator),
):
    """
    Chat interface for conversational story generation.
    
    Request:
    {
        "message": "Generate scene 1 with master introducing himself",
        "conversation_id": "optional-tracking-id"
    }
    
    Response:
    {
        "success": true,
        "message": "Generated Scene 1",
        "action": "scene_generated",
        "data": {
            "scene_id": 1,
            "video_url": "https://...",
            "status": "completed"
        }
    }
    """
    result = await orchestrator.chat(story_id, body.message)
    
    # Sync to database if action was taken
    if result.get("success"):
        await _sync_orchestrator_to_db(orchestrator, story_id)
    
    return result
```

**Tasks:**
- [ ] Create `ChatRequest` Pydantic model
- [ ] Add POST endpoint to stories.py
- [ ] Inject orchestrator via dependency
- [ ] Handle authentication
- [ ] Return proper error codes

---

### Phase 2: Persistent State (High Priority)

**Goal:** Survive restarts and scale horizontally

```python
class ConversationalOrchestrator:
    def __init__(self, db_pool=None, b2_storage=None):
        self._stories: dict[str, Story] = {}
        self._pool = db_pool  # PostgreSQL connection pool
        self._b2 = b2_storage
        
    async def _persist_state(self, story_id: str):
        """Save to DB + B2 for durability."""
        story = self._stories[story_id]
        
        # Save to B2 for full state
        await self.save_story_to_b2(story)
        
        # Update DB records for API queries
        await self._sync_scenes_to_db(story)
        
    async def _load_from_db(self, story_id: str) -> Optional[Story]:
        """Load story from DB + hydrate from B2."""
        # Load from DB first
        row = await self._pool.fetchrow(
            "SELECT * FROM stories WHERE id = $1", story_id
        )
        if not row:
            return None
            
        # Hydrate scenes from DB
        scene_rows = await self._pool.fetch(
            "SELECT * FROM scenes WHERE story_id = $1", story_id
        )
        
        # Load full state from B2
        return await self.load_story_from_b2(story_id)
```

**Tasks:**
- [ ] Add database pool to orchestrator
- [ ] Implement `_sync_orchestrator_to_db()`
- [ ] Implement `_load_from_db()`
- [ ] Add lifecycle hooks (startup/shutdown)

---

### Phase 3: LLM-Powered Intent Parsing (Medium Priority)

**Goal:** Handle natural language variations

```python
from pipeline.story_agent import get_client, _chat

async def parse_intent(self, story_id: str, message: str) -> dict:
    """Use LLM to understand user intent."""
    
    system_prompt = """You are a video production assistant. Parse user messages into structured actions.
    
    Available actions:
    - generate_scene: Create a new video scene
    - regenerate_scene: Regenerate an existing scene
    - combine_scenes: Concatenate multiple scenes
    - add_dialogue: Add character dialogue
    - set_reference: Use a reference image
    - approve_scene: Approve for final output
    - show_timeline: Display scene timeline
    
    Return JSON:
    {
        "action": "action_name",
        "params": {
            "scene_number": 1,  // optional
            "description": "...",  // for generation
            "scene_ids": [1, 2, 3]  // for combine
        },
        "confidence": 0.95
    }
    
    If ambiguous, ask clarifying question."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Story: {self.get_story(story_id).title}\nMessage: {message}"}
    ]
    
    response = await _chat(messages)
    
    try:
        return json.loads(response)
    except:
        return {"action": "unknown", "confidence": 0}
```

**Tasks:**
- [ ] Implement LLM intent parser
- [ ] Add confidence threshold (fallback to simple parser)
- [ ] Handle clarification questions
- [ ] Support multi-turn refinement

---

### Phase 4: Conversation History (Medium Priority)

**Goal:** Context-aware chat

```python
@dataclass
class Conversation:
    id: str
    story_id: str
    messages: list[ChatMessage]
    created_at: datetime
    
@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    action_taken: Optional[str]
    timestamp: datetime

async def chat(self, story_id: str, message: str, conversation_id: str = None) -> dict:
    # Load or create conversation
    if conversation_id:
        conv = self._conversations.get(conversation_id)
    else:
        conv = Conversation(
            id=str(uuid.uuid4()),
            story_id=story_id,
            messages=[],
            created_at=datetime.utcnow()
        )
        self._conversations[conv.id] = conv
    
    # Add to history
    conv.messages.append(ChatMessage(
        role="user",
        content=message,
        action_taken=None
    ))
    
    # Process with context
    response = await self._process_with_context(story_id, conv)
    
    # Save to history
    conv.messages.append(ChatMessage(
        role="assistant",
        content=response.get("message", ""),
        action_taken=response.get("action")
    ))
    
    return {**response, "conversation_id": conv.id}
```

**Tasks:**
- [ ] Add conversation storage (Redis or DB)
- [ ] Implement context window (last N messages)
- [ ] Add conversation management endpoints
- [ ] Implement "undo" via history

---

### Phase 5: Integration with Existing Workflow (High Priority)

**Goal:** Unify orchestrator with job queue system

```python
async def chat(self, story_id: str, message: str) -> dict:
    intent = await self.parse_intent(message)
    
    # Route to appropriate handler
    if intent["action"] == "generate_scene":
        # Use existing job queue for async processing
        scene = await self.generate_scene(story_id, ...)
        
        # Queue as background job
        await enqueue_scene_generation(
            story_id=story_id,
            scene_id=scene.id,
            job_type="chat_triggered"
        )
        
        return {
            "success": True,
            "action": "scene_queued",
            "data": {"scene_id": scene.id, "job_id": job_id}
        }
    
    elif intent["action"] == "regenerate_scene":
        # Use existing scene_regen flow
        return await self._regenerate_via_job_queue(story_id, intent["params"])
```

**Tasks:**
- [ ] Map orchestrator actions to job handlers
- [ ] Add `job_type="chat_triggered"` for tracking
- [ ] Connect to SSE stream for progress
- [ ] Handle partial failures

---

### Phase 6: Advanced Features (Lower Priority)

#### 6.1 Multi-Character Dialogue

```python
async def chat(self, story_id: str, message: str) -> dict:
    if "dialogue" in message.lower():
        # Parse multi-turn dialogue
        dialogues = self._parse_dialogue(message)  # Returns list of DialogueLine
        
        for dl in dialogues:
            await self.add_dialogue(story_id, scene_num, dl)
        
        return {
            "success": True,
            "action": "dialogue_added",
            "data": {"count": len(dialogues)}
        }
```

#### 6.2 Reference Image Chat

```python
async def chat(self, story_id: str, message: str) -> dict:
    if "reference" in message.lower() or "use" in message.lower():
        # Extract frame from existing scene
        parts = message.split()
        src_scene = int(parts[parts.index("scene") + 1])
        timestamp = float(parts[parts.index("at") + 1]) if "at" in parts else 3.0
        
        frame_url = await self.extract_frame(story_id, src_scene, timestamp)
        
        # Add to target scene references
        if "for scene" in message:
            target = int(parts[parts.index("scene") + 1])
            await self.add_reference(story_id, target, frame_url)
```

#### 6.3 Scene Approval Workflow

```python
async def chat(self, story_id: str, message: str) -> dict:
    if "approve" in message.lower():
        scene_num = self._extract_scene_num(message)
        
        # Update DB status
        await pool.execute(
            "UPDATE scenes SET status = 'approved' WHERE story_id = $1 AND scene_number = $2",
            story_id, scene_num
        )
        
        # Check if all approved → ready for concatenation
        approved_count = await self._count_approved(story_id)
        total_count = len(self.get_story(story_id).scenes)
        
        if approved_count == total_count:
            return {
                "success": True,
                "message": "All scenes approved! Ready to combine.",
                "action": "ready_for_concat",
                "suggestion": "Say 'combine all scenes' to create final video"
            }
```

---

## Testing Plan

```bash
# 1. Register user
TOKEN=$(curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","name":"Test"}' \
  | jq -r '.token')

# 2. Create story (via REST - chat doesn't exist yet)
STORY_ID=$(curl -s -X POST "$API/stories" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A samurai story","title":"Samurai","workflow_type":"creator_series"}' \
  | jq -r '.id')

# 3. Approve outline
curl -s -X PUT "$API/stories/$STORY_ID/approve-outline" \
  -H "Authorization: Bearer $TOKEN"

# 4. Generate (still via REST, not chat)
JOB_ID=$(curl -s -X POST "$API/stories/$STORY_ID/generate" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.id')

# 5. Monitor
for i in {1..20}; do
  STATUS=$(curl -s "$API/jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  echo "Status: $STATUS"
  if [ "$STATUS" = "completed" ]; then break; fi
  sleep 30
done
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Chat endpoint exists | ❌ No | ✅ Yes |
| Story state persists | ❌ No | ✅ Yes |
| Natural language understood | ❌ String match | ✅ LLM-powered |
| Multi-turn context | ❌ No | ✅ Yes |
| Horizontal scaling | ❌ No | ✅ Yes |
| Async generation via chat | ❌ No | ✅ Yes |

---

## Implementation Priority

1. **Phase 1** (HTTP Endpoint) - Blocked, must do first
2. **Phase 2** (Persistence) - Required for production
3. **Phase 5** (Job Queue Integration) - Unify existing code
4. **Phase 3** (LLM Parsing) - Better UX
5. **Phase 4** (History) - Context awareness
6. **Phase 6** (Advanced) - Polish

---

## Related Files

- `src/pipeline/conversational_orchestrator.py` - Main orchestrator
- `src/routes/stories.py` - API routes (needs chat endpoint)
- `src/pipeline/job_handlers.py` - Background job processing
- `src/pipeline/streaming_orchestrator.py` - SSE events
- `src/pipeline/story_agent.py` - LLM integration
- `storage/b2.py` - B2 persistence (unused by orchestrator)
