# StoryForge Anime Pipeline — Architecture & Reference

> **Version:** 2.0.0 · **Service:** StoryForge Anime Pipeline · **Kind:** `api` · **Port:** 5001 · **Base Path:** `/pipeline`

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Directory Structure](#directory-structure)
4. [Entry Points](#entry-points)
5. [Database Schema](#database-schema)
6. [API Routes](#api-routes)
7. [Pipeline Engine](#pipeline-engine)
8. [Workers & Job Queue](#workers--job-queue)
9. [Workflow Types](#workflow-types)
10. [AI Provider Integration](#ai-provider-integration)
11. [Publishing & Social](#publishing--social)
12. [Scheduling](#scheduling)
13. [Metrics & Observability](#metrics--observability)
14. [Authentication](#authentication)
15. [Running the Pipeline](#running-the-pipeline)

---

## Overview

The **StoryForge Anime Pipeline** is an AI-powered showrunner API that generates branded short-form animated video series from text prompts. It transforms a user's story concept into a complete episode plan, generates scenes (video or narrated images) using AI models, supports human-in-the-loop approval checkpoints, and publishes finished episodes to social media platforms (YouTube, TikTok).

**Core capabilities:**

- AI story planning from a short prompt → episode outlines → character descriptions
- Scene generation via video/image AI models (Wan2.7, HappyHorse, Qwen)
- Human-in-the-loop approval gates (outline → characters → scenes)
- Checkpoint-based generation with TTS narration for narrated-image stories
- Automated scheduling with cadences (once, daily, weekly, interval-based)
- Publishing to YouTube and TikTok via OAuth2
- Per-scene regeneration without losing surrounding context
- Brand/character/world/campaign memory ("bibles")
- Event-sourced history tracking for all entities
- Pipeline run/step/artifact tracing for observability

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python 3.11+) |
| **Server** | Uvicorn |
| **Database** | CockroachDB (PostgreSQL-compatible via asyncpg) |
| **Queue** | Redis (redis.asyncio with BLPOP) |
| **Media Storage** | Backblaze B2 (S3-compatible via boto3) |
| **AI Providers** | DashScope (Alibaba Cloud) · AIML API |
| **Video Processing** | moviepy · imageio-ffmpeg |
| **Auth** | PBKDF2-SHA256 · Bearer tokens |
| **OAuth** | YouTube Data API v3 · TikTok API |



---

## Directory Structure

```
artifacts/pipeline/
├── .env                          # Environment variables (credentials)
├── .gitignore
├── .replit-artifact/
│   └── artifact.edit.toml        # Replit deployment config
├── .venv/                        # Python virtual env (Windows)
├── .venv-py311/                  # Python virtual env (Linux/Replit)
├── requirements.txt              # Python dependencies
├── run.sh                        # Start API server
├── run-worker.sh                 # Start worker (all workloads)
├── run-worker-story.sh           # Start story workload worker
├── run-worker-media.sh           # Start media workload worker
├── run-worker-audio.sh           # Start audio workload worker
└── src/
    ├── __init__.py
    ├── main.py                   # FastAPI app entry point
    ├── worker.py                 # Background job worker
    ├── scheduler.py              # Automation scheduler process
    ├── alibaba_entry.py          # Alibaba Cloud SPA entry point
    ├── auth.py                   # Authentication routes
    ├── job_queue.py              # Redis job queue abstraction
    ├── db/
    │   ├── __init__.py
    │   ├── connection.py         # asyncpg pool management
    │   └── schema.sql            # Full database schema (idempotent)
    ├── models/
    │   ├── __init__.py
    │   ├── story.py              # Story, Scene, Episode, Character, Job, Checkpoint models
    │   ├── pipeline.py           # PipelineRun, PipelineStep, PipelineArtifact models
    │   ├── schedule.py           # Schedule, ScheduledRun models
    │   ├── social.py             # SocialAccount, PublishTarget models
    │   └── admin.py              # Admin dashboard models
    ├── routes/
    │   ├── __init__.py
    │   ├── stories.py            # Story CRUD, generate, operations agent
    │   ├── episodes.py           # Episode listing & detail
    │   ├── scenes.py             # Scene CRUD, approve, reject, lock, regenerate
    │   ├── characters.py         # Character CRUD, approve, lock, regenerate refs
    │   ├── checkpoints.py        # Generation checkpoint management & audio
    │   ├── bibles.py             # Brand/character/world/campaign bibles
    │   ├── pipeline_runs.py      # Pipeline run/step/artifact tracking
    │   ├── jobs.py               # Job status, cancel, retry, metrics
    │   ├── publish.py            # Publish targets CRUD, approve, publish-now
    │   ├── social.py             # Social accounts, OAuth connect/callback
    │   ├── schedules.py          # Automation schedules CRUD, run-now, dispatch
    │   ├── gallery.py            # Media gallery (scenes & episodes)
    │   ├── providers.py          # AI provider status
    │   ├── uploads.py            # File upload handler
    │   └── admin.py              # Admin dashboard endpoints
    ├── pipeline/
    │   ├── __init__.py
    │   ├── orchestrator.py       # Main generation orchestrator
    │   ├── pipeline_runtime.py   # Run/step context managers & artifact recording
    │   ├── job_handlers.py       # All job handler functions
    │   ├── job_runtime.py        # Job state update utilities
    │   ├── generation_coordinator.py  # AI provider coordination with fallback
    │   ├── provider_executor.py  # Ordered attempt execution
    │   ├── model_registry.py     # Video/Image/Text model catalog
    │   ├── scene_gen.py          # Scene video/image generation
    │   ├── character_gen.py      # Character reference generation
    │   ├── audio_gen.py          # Narration script & TTS generation
    │   ├── assembler.py          # Episode video assembly
    │   ├── narrated_image_story.py  # Narrated-image story assembly
    │   ├── story_agent.py        # LLM story planning
    │   ├── operations_agent.py   # Story operations agent
    │   ├── pipeline_config.py    # Pipeline configuration normalization
    │   ├── history.py            # Event history recording
    │   ├── metrics.py            # Pipeline metrics recording
    │   ├── versioning.py         # Version constants
    │   ├── provider_policy.py    # Provider selection policies
    │   ├── provider_status.py    # Provider health check
    │   ├── media_tools.py        # FFmpeg utilities
    │   ├── runtime_context.py    # ContextVar runtime context
    │   ├── scheduler.py          # Due schedule enqueuing logic
    │   ├── generation_agent.py   # Agent-based generation with tool calling
    │   ├── steps/
    │   │   ├── __init__.py
    │   │   └── scene_steps.py    # Scene render step completion
    │   ├── social/
    │   │   ├── oauth.py          # YouTube/TikTok OAuth URL builders
    │   │   └── token_store.py    # Encrypted token storage (Fernet)
    │   └── publishers/
    │       ├── base.py           # BasePublisher abstract class
    │       ├── mock.py           # Mock publisher (testing)
    │       ├── youtube.py        # YouTube Data API publisher
    │       ├── tiktok.py         # TikTok API publisher
    │       └── media.py          # Media URL resolution
    └── storage/
        ├── __init__.py


---

## Entry Points

### `main.py` — API Server

The FastAPI application with:

- **Lifespan**: initializes DB pool on startup, closes on shutdown
- **CORS**: wide-open for development
- **Router registration**: all 16+ route modules
- **Health endpoint**: `GET /pipeline/health` — reports service status, FFmpeg availability
- **Root endpoint**: `GET /pipeline` — full API reference with all endpoints listed

### `worker.py` — Background Worker

A long-running process that:

1. Initializes DB and Redis connections
2. Recovers expired jobs on startup (re-queues them)
3. Polls Redis ready queues per workload using `BLPOP`
4. Claims jobs atomically in PostgreSQL (lease-based to prevent double-processing)
5. Dispatches to the appropriate handler based on `entity_type` and `job_type`
6. Sends heartbeats to keep leases alive
7. Handles retries with exponential backoff and permanent failure after `max_attempts`

### `scheduler.py` — Scheduler Process

A simple polling loop that checks `automation_schedules` for due schedules and enqueues them as jobs. Configurable poll interval (default 60s).

### `alibaba_entry.py` — Alibaba Cloud Entry

Wraps the main FastAPI app with SPA static file serving for deployment on Alibaba Cloud.

---

## Database Schema

The schema is defined in `src/db/schema.sql` (~650 lines) and is **idempotent** — all statements use `IF NOT EXISTS` / `ALTER TABLE ADD COLUMN IF NOT EXISTS` guards.

### Core Tables

| Table | Purpose |
|---|---|
| `users` | User accounts with PBKDF2 password hashes |
| `auth_sessions` | Bearer token sessions (SHA256-hashed tokens) |
| `stories` | Story projects — prompt, genre, style, workflow type, approval status |
| `bibles` | Brand/Character/World/Campaign memory bibles (JSONB content) |
| `episodes` | Episodes within a story |
| `scenes` | Individual scenes — prompt, media URLs, approval status, generation metadata |
| `characters` | Character definitions with reference image URLs |
| `scene_characters` | Many-to-many scene↔character associations |
| `generation_jobs` | Async job queue — status, progress, leasing, retries |
| `pipeline_runs` | High-level pipeline execution tracking |
| `pipeline_steps` | Individual steps within a pipeline run |
| `pipeline_artifacts` | Output artifacts (media URLs, content) from pipeline steps |
| `story_generation_checkpoints` | Human-review checkpoints (pauses every N scenes) |
| `story_history` | Event-sourced audit log for stories |
| `scene_history` | Event-sourced audit log for scenes |
| `checkpoint_history` | Event-sourced audit log for checkpoints |
| `social_accounts` | Connected social media accounts (encrypted tokens) |
| `publish_targets` | Publishing targets (platform + episode/scene) |
| `publish_posts` | Individual publish post records |
| `automation_schedules` | Automated scheduling rules |
| `scheduled_runs` | Individual scheduled run executions |
| `pipeline_metrics` | Cost, latency, and error metrics |


---

## API Routes

All routes are under the `/pipeline` prefix.

### Auth (`/pipeline/auth`)

| Method | Path | Description |
|---|---|---|
| POST | `/pipeline/auth/register` | Register new user |
| POST | `/pipeline/auth/login` | Login with email/password |
| GET | `/pipeline/auth/me` | Get current user |
| POST | `/pipeline/auth/logout` | Logout (invalidate session) |

### Stories (`/pipeline/stories`)

| Method | Path | Description |
|---|---|---|
| POST | `/pipeline/stories` | Create a story |
| GET | `/pipeline/stories` | List user's stories |
| GET | `/pipeline/stories/{id}` | Get story detail |
| PUT | `/pipeline/stories/{id}` | Update story |
| DELETE | `/pipeline/stories/{id}` | Delete story |
| POST | `/pipeline/stories/{id}/generate` | Start generation job |
| PUT | `/pipeline/stories/{id}/approve-outline` | Approve episode outline |
| POST | `/pipeline/stories/{id}/operations-agent` | Run operations agent |
| GET | `/pipeline/stories/{id}/capabilities` | Get story capabilities |
| GET | `/pipeline/stories/{id}/history` | Get story history |
| PUT | `/pipeline/stories/{id}/pipeline-config` | Update pipeline config |

### Episodes (`/pipeline/episodes`)

| Method | Path | Description |
|---|---|---|
| GET | `/pipeline/episodes/story/{story_id}` | List episodes for a story |
| GET | `/pipeline/episodes/{id}` | Get episode detail with scenes |

### Scenes (`/pipeline/scenes`)

| Method | Path | Description |
|---|---|---|
| GET | `/pipeline/scenes/{id}` | Get scene detail |
| PUT | `/pipeline/scenes/{id}` | Update scene |
| PUT | `/pipeline/scenes/{id}/approve` | Approve scene |
| PUT | `/pipeline/scenes/{id}/reject` | Reject scene |
| PUT | `/pipeline/scenes/{id}/lock` | Lock scene (prevent regeneration) |
| POST | `/pipeline/scenes/{id}/regenerate` | Regenerate scene media |
| GET | `/pipeline/scenes/{id}/history` | Get scene history |

### Characters (`/pipeline/characters`)

| Method | Path | Description |
|---|---|---|
| POST | `/pipeline/characters` | Create character |
| GET | `/pipeline/characters/story/{story_id}` | List story characters |
| GET | `/pipeline/characters/{id}` | Get character |
| PUT | `/pipeline/characters/{id}` | Update character |
| DELETE | `/pipeline/characters/{id}` | Delete character |
| PUT | `/pipeline/characters/{id}/approve` | Approve character |
| PUT | `/pipeline/characters/{id}/lock` | Lock character |
| POST | `/pipeline/characters/{id}/regenerate-refs` | Regenerate character refs |

### Checkpoints (`/pipeline/stories/.../checkpoints`)

| Method | Path | Description |
|---|---|---|
| GET | `/pipeline/stories/{story_id}/checkpoints` | List checkpoints |
| GET | `/pipeline/stories/{story_id}/checkpoints/{id}` | Get checkpoint |
| PUT | `/pipeline/stories/{story_id}/checkpoints/{id}/approve` | Approve checkpoint |
| PUT | `/pipeline/stories/{story_id}/checkpoints/{id}/reject` | Reject checkpoint |
| POST | `/pipeline/stories/{story_id}/checkpoints/{id}/audio/regenerate` | Regenerate narration audio |

### Pipeline Runs (`/pipeline/runs`)

| Method | Path | Description |
|---|---|---|
| GET | `/pipeline/runs/story/{story_id}` | List runs for story |
| GET | `/pipeline/runs/{run_id}` | Get run detail |
| GET | `/pipeline/runs/{run_id}/steps` | List run steps |
| GET | `/pipeline/runs/{run_id}/artifacts` | List run artifacts |
| GET | `/pipeline/runs/steps/{step_id}` | Get step detail |
| POST | `/pipeline/runs/steps/{step_id}/retry` | Retry failed step |
| POST | `/pipeline/runs/{run_id}/cancel` | Cancel running run |

### Jobs (`/pipeline/jobs`)

| Method | Path | Description |
|---|---|---|
| GET | `/pipeline/jobs/{id}` | Get job status |
| GET | `/pipeline/jobs/entity/{type}/{entity_id}` | List entity jobs |
| GET | `/pipeline/jobs/{id}/metrics` | Get job metrics |
| POST | `/pipeline/jobs/{id}/cancel` | Cancel job |
| POST | `/pipeline/jobs/{id}/retry` | Retry failed job |

### Publishing (`/pipeline/publish-targets`)

| Method | Path | Description |
|---|---|---|
| POST | `/pipeline/publish-targets` | Create publish target |
| GET | `/pipeline/publish-targets` | List publish targets |
| GET | `/pipeline/publish-targets/{id}` | Get publish target |
| POST | `/pipeline/publish-targets/{id}/approve` | Approve for publishing |
| POST | `/pipeline/publish-targets/{id}/publish-now` | Publish immediately |
| POST | `/pipeline/publish-targets/{id}/retry` | Retry failed publish |
| POST | `/pipeline/publish-targets/{id}/cancel` | Cancel pending publish |

### Social (`/pipeline/social`)

| Method | Path | Description |
|---|---|---|
| GET | `/pipeline/social/accounts` | List connected accounts |
| POST | `/pipeline/social/accounts/mock` | Create mock account (testing) |
| POST | `/pipeline/social/{platform}/connect` | Start OAuth connection |
| GET | `/pipeline/social/{platform}/callback` | OAuth callback handler |
| DELETE | `/pipeline/social/accounts/{id}` | Disconnect account |

### Schedules (`/pipeline/schedules`)

| Method | Path | Description |
|---|---|---|
| POST | `/pipeline/schedules` | Create automation schedule |
| GET | `/pipeline/schedules` | List schedules |
| GET | `/pipeline/schedules/{id}` | Get schedule |
| PATCH | `/pipeline/schedules/{id}` | Update schedule |
| DELETE | `/pipeline/schedules/{id}` | Delete schedule |
| POST | `/pipeline/schedules/{id}/run-now` | Run schedule immediately |
| POST | `/pipeline/schedules/dispatch-due` | Dispatch all due schedules |
| GET | `/pipeline/schedules/{id}/runs` | List schedule runs |

### Other

| Route | Description |
|---|---|
| `/pipeline/bibles` | Brand/character/world/campaign memory CRUD |
| `/pipeline/gallery` | Media gallery (scenes + episodes with media) |
| `/pipeline/gallery/public` | Public gallery |
| `/pipeline/providers/status` | AI provider health status |
| `/pipeline/uploads/image` | Upload reference image |


---

## Pipeline Engine

### Generation Flow

1. **Story Creation** — User submits title, prompt, genre, style, workflow type
2. **Story Planning** — `story_agent.py` uses LLM to generate episode plan (outline, character descriptions)
3. **Outline Approval** — User reviews and approves the outline
4. **Generation** — `POST /stories/{id}/generate` enqueues a `full_episode` job
5. **Orchestrator** (`orchestrator.py`):
   - Creates episodes and scenes in DB
   - Generates character reference images (via `character_gen.py`)
   - Generates each scene sequentially:
     - For video: selects best model from registry (r2v > i2v > t2v based on reference count)
     - For narrated-image: generates image + narration script
   - After N scenes (configurable batch size): creates a **checkpoint** for human review
   - After final scene: assembles episode video (concatenates clips + optional narration audio)
6. **Review** — User approves/rejects checkpoints or individual scenes
7. **Publishing** — Create publish target → approve → publish to YouTube/TikTok

### Pipeline Run/Step Tracking

Each generation execution creates a **pipeline run** containing multiple **pipeline steps** and **artifacts**:

- **Run** — Represents one complete generation session (e.g., "generate episode 1")
- **Step** — Individual operations within a run (e.g., "generate scene 1", "assemble episode")
- **Artifact** — Outputs produced by steps (e.g., video URL, image URL, manifest)

Runtime context is managed via `ContextVar` and context managers:

```python
async with pipeline_run_context(run_type="story_generation") as run_id:
    async with pipeline_step_context(step_key="generate_scene:1") as step_id:
        # ... generate scene ...
        await record_pipeline_artifact(artifact_type="scene_video", url=...)
```

### Pipeline Config

Each story has a `pipeline_config` (stored in `workflow_state`) that controls:
- **Providers**: preferred AI models/providers for video, image, text
- **Editor**: style memory, reference URLs
- **Generation**: batch size, approval policy

### Model Registry (`model_registry.py`)

Models are ranked by priority and capability:

**Video Models** (priority order):
| Model | Provider | Capability | Cost Tier |
|---|---|---|---|
| `happyhorse-1.1-r2v` | DashScope | r2v (reference-to-video) | Medium |
| `wan2.7-r2v-2026-06-12` | DashScope | r2v | High |
| `happyhorse-1.1-i2v` | DashScope | i2v (image-to-video) | Medium |
| `wan2.7-i2v` | DashScope | i2v | High |
| `happyhorse-1.1-t2v` | DashScope | t2v (text-to-video) | Medium |
| `wan2.7-t2v` | DashScope | t2v | High |
| `alibaba/wan2.7-i2v` | AIML | i2v | High |
| `alibaba/wan2.7-t2v` | AIML | t2v | High |

**Image Models**: `wan2.7-image-pro`, `qwen-image-edit-*`, `qwen-image-*`, `wan2.1-t2i-plus`

**Text Models**: `qwen3.7-max`, `qwen3.7-plus`, `qwen-max`, `qwen-plus`, `qwen3.6-flash`, `qwen3.5-flash`

The system automatically selects the best model based on:
- Number of reference images available (determines r2v vs i2v vs t2v)
- Provider availability (API key configured)
- User preferences (from pipeline_config)


---

## Workers & Job Queue

### Queue Architecture (Redis)

Jobs are categorized into **5 workloads**:

| Workload | Queue Key | Job Types | Handler |
|---|---|---|---|
| `story` | `storyforge:jobs:ready:story` | `full_episode`, `full_episode_resume` | `run_story_generation()` |
| `media` | `storyforge:jobs:ready:media` | `char_refs`, `scene_regen` | `run_character_ref_job()`, `run_scene_regen_job()` |
| `audio` | `storyforge:jobs:ready:audio` | `checkpoint_audio` | `run_checkpoint_audio_job()` |
| `publish` | `storyforge:jobs:ready:publish` | `publish_target`, `publish_episode` | `run_publish_target_job()` |
| `scheduler` | `storyforge:jobs:ready:scheduler` | `scheduled_*` | `run_scheduled_job()` |

Each workload has both a **ready queue** (Redis LIST) and a **delayed queue** (Redis ZSET).

### Worker Process

1. Workers use `BLPOP` (blocking list pop) with 1-second timeout for efficient polling
2. Jobs are **claimed** atomically in PostgreSQL using `UPDATE ... WHERE status='pending' OR lease_expired`
3. Workers send periodic **heartbeats** to keep the lease alive (default every 30s)
4. If a worker crashes, the lease expires and another worker picks up the job
5. Exponential backoff retry: `RETRY_BASE * (2^attempt)` with configurable max attempts

### Dedicated Workers

Separate worker processes handle different workloads for isolation:

```bash
run-worker-story.sh    # Story generation only
run-worker-media.sh    # Media generation only
run-worker-audio.sh    # Audio narration only
run-worker.sh          # All workloads (WORKER_WORKLOAD=all)
```

---

## Workflow Types

The system supports **6 story workflow types**:

| Type | Description | Media |
|---|---|---|
| `creator_series` | Serialized anime/fiction series | Video |
| `brand_campaign` | Ad concepts from product brief | Video/Image |
| `social_short` | TikTok/Reels/Shorts vertical content | Video |
| `educational` | Animated explainer or course lesson | Video/Image |
| `game_lore` | IP lore trailers or teasers | Video/Image |
| `narrated_image_story` | Still-image story with TTS narration | Image + Audio |

Media kinds: `auto` (let system decide), `video`, `image`

---

## AI Provider Integration

### DashScope (Alibaba Cloud)

- API key: `DASHSCOPE_API_KEY`
- Models: Qwen (text), Wan2.7 (video/image), HappyHorse (video)
- OpenAI-compatible API (used via `openai` Python package)

### AIML API

- API key: `AIML_API_KEY`
- Models: `alibaba/wan2.7-i2v`, `alibaba/wan2.7-t2v`
- Fallback provider when DashScope is unavailable

### Provider Executor

The `provider_executor.py` implements a **fallback chain** pattern:

```python
attempts = build_video_attempts(reference_count=n, ...)
result, used_attempt, failures = await execute_ordered_attempts(
    attempts=attempts, operation=call_provider,
)
```



---

## Publishing & Social

### Social Accounts

- **YouTube**: OAuth2 with Google, upload via YouTube Data API v3
- **TikTok**: OAuth2 with TikTok, upload via TikTok API
- **Mock**: Local testing without real API calls

OAuth tokens are encrypted with **Fernet** (symmetric encryption from `cryptography` package) before storage.

### Publishing Flow

1. Create a **publish target** linked to an episode or scene
2. Optionally require **approval** before publishing
3. Call `publish-now` to enqueue a publish job
4. Worker executes: resolves media URL → calls platform API → records post
5. Track publish status and platform post ID

---

## Scheduling

### Schedule Types

| Type | Description |
|---|---|
| `generate_only` | Generate new content only |
| `publish_existing` | Publish an already-generated episode |
| `generate_and_publish` | Generate then publish |
| `series_continuation` | Continue a series with next episode |

### Cadences

| Cadence | Behavior |
|---|---|
| `once` | Single run, then disable |
| `interval_hours` | Run every N hours |
| `daily` | Run every 24h |
| `weekly` | Run every 7 days |

### Approval Policies

| Policy | Behavior |
|---|---|
| `require_approval` | Generate but wait for human approval before publish |
| `auto_publish` | Auto-publish without waiting |
| `generate_only` | Generate only, no publishing |

---

## Metrics & Observability

### Pipeline Metrics Table

Records per-operation metrics:
- `duration_ms` — Operation duration
- `provider_latency_ms` — AI provider response time
- `estimated_cost_usd` — Cost estimation per operation
- `retries` — Number of retry attempts
- `step_name`, `provider`, `provider_task_id` — Operation details
- `error` — Error message on failure
- `job_id`, `entity_type`, `entity_id` — Entity linkage

### History Tables (Event Sourcing)

Three history tables provide full audit trails:
- **`story_history`** — Story-level events (created, outline_approved, generation_started, etc.)
- **`scene_history`** — Scene-level events (created, regenerated, approved, rejected, locked)
- **`checkpoint_history`** — Checkpoint events (created, approved, rejected, audio_generated)

Each history entry includes: `revision` (monotonic per entity), `state_snapshot`, `payload`, `source_job_id`.

### Admin Dashboard

The admin routes provide:
- Overview metrics (totals, status breakdowns, daily activity)
- Provider cost and latency summaries
- Top failure steps and recent failures
- Per-user activity, story and job summaries

---

## Authentication

### User Authentication

- **Password hashing**: PBKDF2-SHA256 with 210,000 iterations and random salt
- **Session tokens**: Random URL-safe tokens stored as SHA256 hashes in DB
- **Session TTL**: Configurable via `SESSION_TTL_DAYS` (default 30 days)
- **Endpoints**: `register`, `login`, `logout`, `me`
- **Auth middleware**: Bearer token extraction via `HTTPBearer`

### Admin Authentication

- Separate session table (`admin_sessions`)
- Configurable admin credentials via `ADMIN_EMAIL` + `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH`
- Admin-specific endpoints for monitoring and user management

### OAuth (Social Publishing)

- YouTube: Standard OAuth2 with Google
- TikTok: Standard OAuth2 with TikTok
- Tokens encrypted with Fernet before storage
- Refresh tokens stored for token renewal

---

## Running the Pipeline

### Prerequisites

- Python 3.11+
- CockroachDB instance (or PostgreSQL)
- Redis instance
- Backblaze B2 bucket (or S3-compatible storage)
- API keys: DashScope and/or AIML

### Environment Variables

Required:
```
COCKROACHDB_URL=postgresql://...
REDIS_URL=redis://...
DASHSCOPE_API_KEY=sk-...
SESSION_SECRET=...
B2_KEY_ID=...
B2_APPLICATION_KEY=...
B2_BUCKET_NAME=...
B2_ENDPOINT_URL=...
```

Optional:
```
AIML_API_KEY=...                   # Fallback AI provider
ADMIN_EMAIL=...                    # Admin credentials
ADMIN_PASSWORD=...                 # Admin credentials
JOB_LEASE_SECONDS=600              # Job lease duration
JOB_HEARTBEAT_SECONDS=30           # Heartbeat interval
JOB_RETRY_BASE_SECONDS=15          # Retry backoff base
JOB_MAX_ATTEMPTS=3                 # Max retry attempts
SCHEDULER_POLL_SECONDS=60          # Scheduler poll interval
WORKER_ID=...                      # Worker identifier
```

### .env File Auto-Loading

The backend automatically loads environment variables from a `.env` file located at the pipeline root (`artifacts/pipeline/.env`). This file is **not tracked by git** (see `.gitignore`).

Copy or create `.env` from `.env.example`:
```bash
cd artifacts/pipeline
copy .env.example .env
```

All Python entry points (`main.py`, `worker.py`, `scheduler.py`) call `load_dotenv()` at startup, so environment variables are available before any database or external service connections are made.

### Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
cd src
uvicorn main:app --host 0.0.0.0 --port 5001 --reload

# Start workers (separate terminals)
cd src
python -m worker              # All workloads
WORKER_WORKLOAD=story python -m worker   # Story only
WORKER_WORKLOAD=media python -m worker   # Media only
WORKER_WORKLOAD=audio python -m worker   # Audio only

# Start scheduler
cd src
python -m scheduler

# Or use shell scripts
bash run.sh                    # API server
bash run-worker-story.sh       # Story worker
bash run-worker-media.sh       # Media worker
bash run-worker-audio.sh       # Audio worker
```

