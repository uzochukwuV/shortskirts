# StoryForge Anime

An agentic AI pipeline that generates consistent multi-episode anime series — from story prompt to assembled video — using Qwen/Wan for generation, Backblaze B2 for storage, and CockroachDB for persistent character and story memory.

## Run & Operate

- `bash artifacts/pipeline/run.sh` — run the Python FastAPI pipeline (port 5001)
- `bash artifacts/pipeline/run-worker-story.sh` — run a story worker lane
- `bash artifacts/pipeline/run-worker-media.sh` — run a media worker lane
- `pnpm --filter @workspace/api-server run dev` — run the Node.js API server (port 5000, path `/api`)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string (Node.js API)
- Required env: `COCKROACHDB_URL`, `DASHSCOPE_API_KEY`, `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_ENDPOINT_URL`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9 (Node API)
- **Python 3.11 + FastAPI + uvicorn** (anime pipeline — primary backend)
- API: Express 5 (Node), FastAPI (Python)
- DB: PostgreSQL + Drizzle ORM (Node); CockroachDB + asyncpg (Python)
- Validation: Zod (`zod/v4`), `drizzle-zod` (Node); Pydantic v2 (Python)
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)
- AI: Qwen/DashScope (LLM + Wan video + image gen)
- Storage: Backblaze B2 (via boto3 S3-compatible API)
- Memory: CockroachDB (story state, character profiles, embeddings as JSONB)

## Where things live

- `artifacts/pipeline/` — Python FastAPI pipeline (PRIMARY backend for hackathon)
  - `src/main.py` — FastAPI app entry point
  - `src/routes/` — stories, characters, episodes, jobs endpoints
  - `src/pipeline/` — story_agent (Qwen LLM), character_gen (image refs), scene_gen (Wan video), assembler (moviepy stitch), orchestrator (full pipeline runner)
  - `src/storage/b2.py` — Backblaze B2 wrapper (boto3 S3-compatible)
  - `src/db/` — CockroachDB connection pool + schema
  - `src/models/story.py` — Pydantic models for all entities
  - `src/db/schema.sql` — CockroachDB table definitions
- `artifacts/api-server/` — Node.js API server (path `/api`, port 8080)
- `lib/api-spec/openapi.yaml` — OpenAPI spec (Node API)

## Architecture decisions

- **Python for the pipeline** — Genblaze SDK is Python-only; the entire generation pipeline (story, character, scene, assembly) lives in Python/FastAPI. Node.js api-server is kept as-is for other API needs.
- **CockroachDB as story memory** — Character profiles, story state, scene graph, and generation jobs all persist in CockroachDB. Embeddings stored as JSONB (not native vector) for compatibility.
- **B2 for all media** — Every generated asset (character ref images, scene clips, exit frames, assembled episodes, manifests) is uploaded to Backblaze B2 immediately after generation, because Qwen video URLs expire after 24h.
- **Frame bridging** — The last frame of scene N is uploaded to B2 and fed as a reference image into scene N+1, enabling visual continuity across clips.
- **Background job tracking** — Generation runs as a FastAPI background task; progress is tracked in `generation_jobs` table so clients can poll `GET /pipeline/jobs/{id}`.
- **Explicit worker lanes** — Story planning runs on the `story` queue family. Character and scene work runs on the `media` queue family. The worker launcher accepts `WORKER_WORKLOAD=story|media|all`, and the ready/delayed Redis keys are partitioned by lane.
- **Path routing** — Python pipeline owns `/pipeline/*`; Node.js owns `/api/*`. Both run as separate processes through Replit's shared proxy.

## Horizontal Scaling

Run as many independent worker processes as needed per lane.

- Story workers: `bash artifacts/pipeline/run-worker-story.sh`
- Media workers: `bash artifacts/pipeline/run-worker-media.sh`

Scale out by starting more copies of the same lane. Story workers only consume story-plan jobs. Media workers only consume character-ref and scene-regeneration jobs. The Redis queue keys and job recovery logic are already partitioned by workload, so additional worker replicas do not need code changes.

## Product

1. Create a story with a prompt, genre, and style → Qwen LLM generates a full episode plan with characters and scene breakdowns
2. Characters get 3 reference images generated → stored in B2, embeddings in CockroachDB
3. Trigger episode generation → scenes generated with Wan 2.7 video model using character refs + frame bridging
4. Scenes assembled into a full episode → manifest stored in B2 for provenance

## API Endpoints (Python pipeline on port 5001)

```
POST   /pipeline/stories                    Create story (triggers Qwen LLM plan)
GET    /pipeline/stories                    List all stories
GET    /pipeline/stories/{id}               Get story + episode plan
POST   /pipeline/stories/{id}/generate      Kick off full episode generation (async)
POST   /pipeline/characters                 Create character + trigger ref image gen
GET    /pipeline/characters/story/{id}      List characters for a story
GET    /pipeline/characters/{id}            Get character with ref image URLs
GET    /pipeline/episodes/story/{id}        List episodes with scenes
GET    /pipeline/episodes/{id}              Get episode details
GET    /pipeline/jobs/{id}                  Poll job status + progress
GET    /pipeline/jobs/entity/{type}/{id}    List jobs for an entity
GET    /pipeline/health                     Health check
GET    /pipeline/                           API index
```

## Hackathon Submission Notes

- **Backblaze Hackathon**: B2 used for all generated media (clips, character refs, exit frames, manifests). Genblaze SDK to be added for provenance-aware orchestration.
- **Qwen Hackathon (Track 2: AI Showrunner)**: Full script→storyboard→video pipeline using Wan 2.7, multi-shot prompts, character consistency via reference images.
- **CockroachDB × AWS**: Story state, character profiles, scene graph, embeddings all in CockroachDB. MCP Server integration can connect agent tooling directly.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- **DashScope model access**: Your API key requires model activation at console.dashscope.aliyun.com. Enable `qwen-turbo` (free tier) or `qwen-plus` to use LLM endpoints.
- **Qwen video URLs expire** in 24h — the pipeline downloads and re-uploads to B2 immediately.
- **Wan 2.7 max 5 reference assets** — the scene generator caps at 4 character refs + 1 exit frame.
- **moviepy + ffmpeg** required for episode assembly — both installed via Nix.
- Python packages installed globally to `.pythonlibs` (not a venv) — `uvicorn` is on PATH after `python-3.11` module install.
- `PORT` env var controls pipeline port (default 5001 in dev).
- CockroachDB connection uses `ssl=verify-full` with `ssl.CERT_NONE` for asyncpg compatibility.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details






