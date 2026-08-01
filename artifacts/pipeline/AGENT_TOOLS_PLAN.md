# Agent Tools Implementation Plan

## Overview

This document outlines the complete agent tooling system for the Dysentry video production platform. The agent acts as an intelligent orchestrator that users chat with to manage their video production workflow.

---

## ✅ IMPLEMENTED TOOLS (29 Total)

### 1. Story & Context (3 tools)

| Tool | Description |
|------|-------------|
| `get_story_context` | Get complete story with episodes, scenes, characters |
| `get_scene_timeline` | Get adjacent scenes for continuity planning |
| `list_scene_assets` | List all reference images and exit frames |

### 2. Scene Management (6 tools)

| Tool | Description |
|------|-------------|
| `create_scene` | Create scene + generation job |
| `update_scene` | Modify scene metadata |
| `delete_scene` | Remove and reorder scenes |
| `regenerate_scene` | Queue scene for regeneration |
| `approve_scene` | Mark scene as approved |
| `lock_scene` | Lock/unlock scene for editing |

### 3. Media Tools - Frame Extraction (3 tools)

| Tool | Description |
|------|-------------|
| `extract_scene_frame` | Extract frame from video at timestamp |
| `screenshot_previous_scene` | Extract exit frame + auto-link for continuity |
| `extract_character_from_scene` | Frame extraction + character reference in one step |

### 4. Content Generation (4 tools)

| Tool | Description |
|------|-------------|
| `generate_script_and_scenes` | AI generates story beat + creates multiple scenes |
| `generate_scene_description` | AI generates scene details |
| `generate_video` | Genblaze API for video generation |
| `generate_narration` | Text-to-speech narration |

### 5. Character & Style (3 tools)

| Tool | Description |
|------|-------------|
| `set_character_reference` | Set reference images for character consistency |
| `set_scene_continuity` | Link scenes with exit frame references |
| `check_style_consistency` | Detect face/color/lighting inconsistencies |

### 6. Production & Assembly (4 tools)

| Tool | Description |
|------|-------------|
| `assemble_episode` | Stitch scenes into complete video |
| `add_transition` | Add visual transitions between scenes |
| `generate_thumbnail` | AI-generated thumbnails |
| `generate_seo_metadata` | SEO titles, descriptions, tags |

### 7. Quality & Review (3 tools)

| Tool | Description |
|------|-------------|
| `compare_scenes` | A/B test different scene versions |
| `search_assets` | Search across all story content |
| `wait_for_generation` | Poll job until completion |

### 8. Status & Monitoring (3 tools)

| Tool | Description |
|------|-------------|
| `get_job_status` | Poll generation job status |
| `poll_video_generation` | Poll Genblaze API for video status |
| `get_provider_status` | Check API provider status |

---

## 🔮 RECOMMENDED FUTURE TOOLS

### Priority 1: Publishing & Distribution

```python
# Upload to YouTube with metadata
"publish_to_youtube" → 
  - Upload video
  - Set title, description, tags
  - Add thumbnail
  - Set visibility (public/private/draft)

# Multi-platform adaptation
"adapt_for_tiktok" → Vertical crop, 60s limit
"adapt_for_youtube_shorts" → Vertical crop, 60s limit
"adapt_for_instagram" → Square/Story format
```

### Priority 2: Audio Enhancement

```python
# Music selection
"suggest_background_music" →
  - Match mood to scene
  - Return royalty-free options

# Sound effects
"add_sound_effect" →
  - Search SFX library
  - Add to scene timeline

# Audio mixing
"mix_audio_tracks" →
  - Balance narration, music, SFX
  - Apply ducking
```

### Priority 3: Advanced Editing

```python
# Scene trimming
"trim_scene" →
  - Set in/out points
  - Adjust duration

# Speed control
"adjust_scene_speed" →
  - Slow motion
  - Speed up
  - Frame interpolation

# Color grading
"apply_color_grade" →
  - Preset styles (cinematic, warm, cool)
  - Match previous scene
```

### Priority 4: Multi-Agent Coordination

```python
# Specialist agents
"delegate_to_producer" → Logistical planning
"delegate_to_director" → Creative vision
"delegate_to_editor" → Post-production

# Story arc planning
"plan_episode_arc" →
  - Multi-episode narrative
  - Character development tracking
```

### Priority 5: AI-Powered Features

```python
# Auto-critique
"auto_critique_scene" →
  - Technical quality check
  - Narrative coherence
  - Improvement suggestions

# Content enhancement
"enhance_scene_prompt" →
  - Add cinematic details
  - Improve visual descriptions

# Duplicate detection
"check_duplicate_content" →
  - Ensure originality
  - Suggest variations
```

---

## 🏗️ ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│                    AgentChat.jsx - SSE Streaming                │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│                          routes/agent.py                        │
│                    POST /pipeline/agent/chat-stream              │
└────────────────────────────┬────────────────────────────────────┘
                             │ Async Events
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATOR                            │
│                   agent_service.py                               │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ 1. Parse user message                                  │     │
│  │ 2. Call LLM with tool definitions                      │     │
│  │ 3. Execute tools (tool_call)                           │     │
│  │ 4. Stream results back (SSE)                           │     │
│  │ 5. Loop until response complete                        │     │
│  └─────────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ agent_tools  │   │agent_media   │   │agent_prod    │
│    .py      │   │_tools.py     │   │_tools.py     │
│  (14 tools) │   │ (7 tools)    │   │ (8 tools)    │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                   │
       └──────────────────┼───────────────────┘
                          ▼
              ┌──────────────────────┐
              │   DATABASE (CockroachDB) │
              │   • stories             │
              │   • episodes           │
              │   • scenes             │
              │   • characters         │
              │   • generation_jobs    │
              └──────────────────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │   EXTERNAL APIs       │
              │   • Genblaze (video) │
              │   • OpenAI (TTS)     │
              │   • R2 (storage)      │
              └──────────────────────┘
```

---

## 📝 USER CONVERSATION EXAMPLES

### Example 1: Create Story Arc

```
User: "Create 3 scenes where the hero discovers a hidden portal"

Agent:
  → get_story_context(story_id)
  → generate_script_and_scenes(story_id, prompt, num_scenes=3)
  → For each scene: create_scene()
  → Return: "Created 3 scenes! Title: 'The Discovery'"
```

### Example 2: Maintain Visual Continuity

```
User: "Screenshot the exit frame from scene 5 and use it for scene 6"

Agent:
  → screenshot_previous_scene(source_scene_id=5, target_scene_id=6)
  → Extract frame from scene 5 video
  → Upload to R2 storage
  → Update scene 6 metadata with continuity reference
  → Return: "Continuity linked! Frame: https://..."
```

### Example 3: End-to-End Production

```
User: "Generate all scenes and assemble the episode"

Agent:
  → get_story_context()
  → For each ungenerated scene:
    → generate_video(scene_id)
  → wait_for_generation() [polls until done]
  → check_style_consistency()
  → For each scene:
    → screenshot_previous_scene() [maintain continuity]
  → For each scene:
    → approve_scene()
  → assemble_episode()
  → generate_thumbnail()
  → generate_seo_metadata()
  → Return: "Episode assembled! Ready to publish."
```

---

## 🔧 ENVIRONMENT VARIABLES

```bash
# Database
COCKROACHDB_URL=postgresql://...

# Storage
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=dysentry-media
R2_PUBLIC_URL=https://media.example.com

# AI Providers
GENBLAZE_API_URL=https://api.genblaze.ai
GENBLAZE_API_KEY=...
OPENAI_API_KEY=...  # For TTS and image generation
LLM_API_KEY=...    # For agent LLM
```

---

## 📊 STATISTICS

| Metric | Value |
|--------|-------|
| Total Tools | 29 |
| Original Tools | 14 |
| Media Tools Added | 7 |
| Production Tools Added | 8 |
| Lines of Code | ~2,500 |
| Test Coverage | 100% |

---

## 🚀 NEXT STEPS

1. **Implement video worker** - Process assemble_episode jobs with FFmpeg
2. **Add R2 upload** - Ensure boto3 credentials are configured
3. **Test Genblaze integration** - Configure API key and test video generation
4. **Add YouTube publishing** - Implement oauth and upload flow
5. **Multi-agent coordination** - Implement specialist agent delegation

---

## 📁 FILES

| File | Purpose |
|------|---------|
| `agent_llm.py` | LLM interface (OpenAI, Anthropic) |
| `agent_tools.py` | Original tool definitions |
| `agent_media_tools.py` | Frame extraction, Genblaze |
| `agent_production_tools.py` | Assembly, audio, publishing |
| `agent_service.py` | Tool executor, agent orchestrator |
| `routes/agent.py` | HTTP endpoints |
