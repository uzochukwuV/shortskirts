# StoryForge Studio

AI showrunner for serialized short-form media. The app turns a prompt into outlines, characters, scenes, narration, and generated media with approval checkpoints and persistent history.

## Stack

- Frontend: React, Vite, Tailwind, Radix UI
- Backend: FastAPI, Redis, CockroachDB
- Models: Qwen Cloud / DashScope, Wan, CosyVoice
- Storage: Backblaze B2
- Deployment: Alibaba Cloud ECS

## Local Development

```bash
pnpm install
pnpm run dev:frontend
pnpm run dev:backend
pnpm run dev:worker:story
pnpm run dev:worker:media
```

## Build

```bash
pnpm run build
```

## Key Docs

- `API_ENDPOINTS.md`
- `artifacts/pipeline/src/routes/`
- `artifacts/pipeline/src/pipeline/`

## Deployment

Production backend runs on Alibaba Cloud ECS. The frontend is deployed separately.
