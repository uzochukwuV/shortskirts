# Dysentry — AI Video Production App

## Overview
Dysentry is a chat-first AI video production platform. Users describe a story, the model brain generates a structured outline with scenes, and the pipeline renders each scene as a short video clip through the GenBlaze provider adapters. The final result is an assembled video episode.

## Architecture

| Layer | Tech | Port |
|---|---|---|
| Frontend | React 18 + Vite + Tailwind CSS | 5000 |
| Backend API | FastAPI (Python 3.11) + uvicorn | 8000 |
| Media Worker | Python worker process | — |
| Database | CockroachDB (via `COCKROACHDB_URL`) | — |
| Queue / Cache | Redis (via `REDIS_URL`) | — |
| AI | Qwen/HappyHorse through the DashScope GenBlaze adapter, model brain via TokenRouter/OpenRouter-compatible API | — |
| Storage | Backblaze B2 (`B2_*` keys) | — |

## Directory Structure
```
app-frontend/          React/Vite frontend
  src/
    pages/             Dashboard.jsx, Workspace.jsx, Login.jsx, Register.jsx, Home.jsx
    services/          storyService, agentService, episodeService, characterService, jobService, sceneService
    lib/               AuthContext.jsx, session.js, utils.js
    components/        UI components

artifacts/pipeline/src/   FastAPI backend
  main.py              App entry + CORS config
  routes/              agent.py, stories.py, episodes.py, scenes.py, auth.py, jobs.py, characters.py
  db/                  Database models + migrations
  worker.py            Media generation worker
```

## Running Locally

Three workflows must all be running:

1. **Start application** (port 5000, Replit webview)  
   `cd app-frontend && npm install && npm run dev`

2. **Backend API** (port 8000, console)  
   `cd artifacts/pipeline/src && python -m uvicorn main:app --host 0.0.0.0 --port 8000`

3. **Media Worker** (console)  
   `cd artifacts/pipeline/src && python worker.py media`

## Story Production Flow
1. User enters a prompt → `POST /pipeline/stories` (status: `draft`)
2. Model brain generates outline — episodes and scenes created automatically
3. User approves outline → `PUT /pipeline/stories/{id}/approve-outline` (status: `approved`)
4. User launches generation → `POST /pipeline/stories/{id}/generate` (status: `generating`)
5. Worker picks up jobs, renders each scene as a 2–3s video through GenBlaze
6. Status flows: `generating` → `checkpoint_review` → `completed`

## Frontend Proxy
Vite proxies `/pipeline/*` → `http://127.0.0.1:8000` so the frontend never hardcodes the backend host.

## Key Decisions
- No Base44 SDK — completely removed; auth is JWT-based via custom `authService` + `AuthContext`
- Video duration kept to the provider-safe 3 seconds per scene to conserve generation credits
- `react`, `react-dom`, `react-router-dom` are deduplicated via `vite.config.js resolve.dedupe`
- Backend CORS allows all `.replit.dev` and `.repl.co` domains via regex

## User Preferences
- Keep video generation short (3 seconds per clip; HappyHorse requires at least 3 seconds) to conserve AI credits
- Use Qwen/HappyHorse through the DashScope GenBlaze adapter for video; Wan models are reserved for the separate Novita adapter
- AIML is disabled until its API is restored
- Dark theme UI (#0a0a0a background, #dfff1e accent color)
