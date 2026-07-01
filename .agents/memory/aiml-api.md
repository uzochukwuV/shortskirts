---
name: AIML API response format
description: Key response shapes and endpoint patterns for AIML API video/image/LLM generation
---

## Video generation
- Submit: `POST https://api.aimlapi.com/v2/video/generations`
- Body: `{"model": "alibaba/wan2.1-t2v-turbo", "prompt": "...", "duration": 5}`
- Response: `{"id": "TASK_ID", "status": "queued"}`
- Poll: `GET https://api.aimlapi.com/v2/video/generations?generation_id=TASK_ID`
- Completed response shape: `{"id":"...", "status":"completed", "video":{"url":"https://s3.aimlapi.com/..."}, "meta":{...}}`
- **Video URL is nested**: `data["video"]["url"]` — NOT `data["video_url"]` or `data["url"]`
- Generation time: ~99s for wan2.1-t2v-turbo at 5s clip

## Image generation
- `POST https://api.aimlapi.com/v1/images/generations`
- Body: `{"model": "flux/schnell", "prompt": "...", "n": 1, "size": "1024x1024"}`
- Response: `{"data": [{"url": "https://s3.aimlapi.com/..."}]}`

## LLM
- `POST https://api.aimlapi.com/v1/chat/completions` (OpenAI-compatible)
- Working models: `Qwen/Qwen2.5-7B-Instruct-Turbo`, `gpt-4o-mini`, `gpt-4o`
- Base URL: `https://api.aimlapi.com/v1`

## i2v (image-to-video)
- Model: `alibaba/wan2.7-i2v` or `alibaba/wan2.2-i2v-plus`
- Body adds: `"image_url": "https://..."` field

**Why:** Discovered through live API probing — AIML API deviates from OpenAI response shape for video.
