---
name: StoryForge pipeline model choices
description: Confirmed working models and key infrastructure gotchas for StoryForge Anime
---

## Confirmed working models (AIML API)
- LLM: `Qwen/Qwen2.5-7B-Instruct-Turbo`, `gpt-4o-mini`, `gpt-4o`
- Image gen: `flux/schnell`, `alibaba/wan2.7-image`
- Video t2v: `alibaba/wan2.1-t2v-turbo` (fast, ~99s per 5s clip)
- Video i2v: `alibaba/wan2.7-i2v`, `alibaba/wan2.2-i2v-plus`

## B2 key permissions
- The B2 application key MUST have "Read and Write" access, not just read.
- Error when read-only: `AccessDenied: not entitled` on PutObject
- Fix: create new key in Backblaze console with R+W access to the specific bucket

## CockroachDB asyncpg SSL
- Use `ssl.CERT_NONE` with `ssl.create_default_context()` for asyncpg with CockroachDB Cloud
- No native pgvector — store embeddings as JSONB arrays

## Pipeline path routing
- Python FastAPI pipeline runs on port 5001, prefix `/pipeline/*`
- Node.js api-server runs on port 8080, prefix `/api/*`
- Both behind shared Replit proxy

**Why:** Discovered during build and live testing.
