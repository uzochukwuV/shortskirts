# QwenVideo — StoryForge / Dysentry

> **AI-powered serialized short-form story production platform.**  
> Create, edit, approve, and publish animated video series — all from a text prompt.

---

## Overview

**QwenVideo** (also known as **StoryForge** / **Dysentry**) is a full-stack platform for producing **serialized short-form animated stories** with AI. It combines a Python/FastAPI backend pipeline with a modern React frontend to deliver a complete story production workflow:

1. **Plan** — Describe your story idea → AI generates episode outlines, character descriptions, and scene breakdowns
2. **Generate** — AI creates video scenes, narrated images, and character reference assets using state-of-the-art models (Wan2.7, HappyHorse, Qwen)
3. **Review** — Human-in-the-loop approval gates at every stage (outline → characters → scenes → checkpoints)
4. **Publish** — Schedule and auto-publish finished episodes to YouTube and TikTok via OAuth2

---

## Architecture

```
qwenvideo/
├── artifacts/pipeline/      # Backend: StoryForge Anime Pipeline (FastAPI + Python)
├── web/                     # Frontend: Dysentry Studio (React + Vite + Tailwind)
└── scripts/                 # Utility scripts
```

### Backend: [StoryForge Anime Pipeline](artifacts/pipeline/PIPELINE.md)

AI showrunner API built with FastAPI, CockroachDB, Redis, and AI providers (DashScope, AIML).

| Component | Technology |
|---|---|
| **API Framework** | FastAPI (Python 3.11+) |
| **Database** | CockroachDB (asyncpg) |
| **Job Queue** | Redis (BLPOP workers) |
| **Media Storage** | Backblaze B2 (S3-compatible) |
| **AI Providers** | DashScope, AIML API |
| **Auth** | PBKDF2-SHA256 + Bearer tokens |
| **OAuth** | YouTube Data API v3, TikTok API |

### Frontend: [Dysentry Studio](web/README.md)

Story creation studio built with React 18, Vite, Tailwind CSS, and shadcn/ui.

| Component | Technology |
|---|---|
| **UI Framework** | React 18 |
| **Build Tool** | Vite 6 |
| **Styling** | Tailwind CSS 3 + CSS Variables |
| **Routing** | react-router-dom v6 |
| **State Mgmt** | React Context + TanStack Query |
| **UI Library** | shadcn/ui (Radix primitives) |

---

## Key Features

### Story Generation Pipeline
- **6 workflow types**: Creator Series, Brand Campaign, Social Short, Educational, Game Lore, Narrated Image Story
- **AI story planning**: prompt → episode outlines → character descriptions → scene breakdowns
- **Multi-model video generation**: auto-selects from 8+ video models based on reference availability and cost
- **Per-scene regeneration**: regenerate individual scenes without losing context
- **Checkpoint-based generation**: pauses every N scenes for human review (with TTS narration)

### Approval Gates
- Outline approval → Characters approval → Scene review → Checkpoint review → Publish approval
- Lock mechanism to prevent edits after approval
- Full event-sourced history for all entities

### Publishing & Scheduling
- **YouTube & TikTok**: OAuth2-based publishing with encrypted token storage
- **Automated scheduling**: once, daily, weekly, interval-based cadences
- **4 schedule types**: generate only, publish existing, generate-and-publish, series continuation



---

## Quick Start

### Backend

```bash
cd artifacts/pipeline
pip install -r requirements.txt

# Set env vars (see PIPELINE.md for full list)
export COCKROACHDB_URL=postgresql://...
export REDIS_URL=redis://...
export DASHSCOPE_API_KEY=sk-...
export B2_KEY_ID=...
export B2_APPLICATION_KEY=...
export B2_BUCKET_NAME=...

# Start server
cd src && uvicorn main:app --host 0.0.0.0 --port 5001

# Start workers (separate terminals)
python -m worker              # All workloads
python -m scheduler           # Automation scheduler
```

### Frontend

```bash
cd web
pnpm install
pnpm run dev                  # Dev server on :5173
```

### Environment

```bash
# web/.env
VITE_API_BASE_URL=http://localhost:5001
```

---

## Project Structure

```
qwenvideo/
├── artifacts/
│   └── pipeline/                  # Backend API & workers
│       ├── requirements.txt       # Python dependencies
│       ├── PIPELINE.md            # Detailed pipeline docs
│       ├── run.sh / run-worker*.sh
│       └── src/
│           ├── main.py            # FastAPI entry point
│           ├── worker.py          # Background job worker
│           ├── scheduler.py       # Automation scheduler
│           ├── auth.py            # Authentication
│           ├── job_queue.py       # Redis queue abstraction
│           ├── db/                # Database schema & connection
│           ├── models/            # Pydantic models
│           ├── routes/            # 16+ API route modules
│           ├── pipeline/          # Core pipeline engine
│           │   ├── orchestrator.py       # Generation orchestrator
│           │   ├── model_registry.py     # AI model catalog
│           │   ├── scene_gen.py          # Scene generation
│           │   ├── character_gen.py      # Character refs
│           │   ├── audio_gen.py          # TTS narration
│           │   ├── publishers/           # YouTube/TikTok/Mock
│           │   └── social/              # OAuth token management
│           └── storage/           # Backblaze B2 storage
├── web/                            # Frontend React app
│   ├── README.md                  # Detailed frontend docs
│   ├── package.json               # Node dependencies
│   ├── vite.config.js             # Vite configuration
│   └── src/
│       ├── App.jsx                # Root component & routing
│       ├── api/                   # API clients
│       ├── pages/                 # 9 route-level pages
│       └── components/            # UI + app-specific components
└── scripts/                       # Utility scripts
```

---

## API Endpoints (Backend)

All routes under `/pipeline` prefix:

| Category | Key Endpoints |
|---|---|
| Auth | register, login, logout, me |
| Stories | CRUD, generate, approve-outline, history |
| Episodes | List by story, get detail with scenes |
| Scenes | Get, approve, reject, lock, regenerate, history |
| Characters | CRUD, approve, lock, regenerate refs |
| Checkpoints | Get, approve, reject, audio regenerate |
| Bibles | Brand/character/world/campaign memory CRUD |
| Pipeline Runs | Run/step/artifact tracking, retry, cancel |
| Jobs | Status, cancel, retry, metrics |
| Publish | CRUD targets, approve, publish-now, retry |
| Social | Accounts, OAuth connect/callback |
| Schedules | CRUD, run-now, dispatch-due |

---

## Frontend Pages

| Path | Page | Description |
|---|---|---|
| `/` | Landing | Public marketing site |
| `/login` / `/register` | Auth | Email/password authentication |
| `/dashboard` | Dashboard | Story overview, stats, runs |
| `/editor/:seriesId` | Editor | 3-column scene editor with AI assistant |
| `/schedule` | Schedule | Automation job management |
| `/settings` | Settings | Account & social connections |

---

## Detailed Documentation

- **[Pipeline Architecture](artifacts/pipeline/PIPELINE.md)** — Full backend reference: schema, routes, engine, workers, providers, publishing, scheduling, metrics, authentication
- **[Frontend Reference](web/README.md)** — Complete frontend docs: components, API layer, editor architecture, styling, auth flow, build & deployment

---

## License

Proprietary — All rights reserved.
