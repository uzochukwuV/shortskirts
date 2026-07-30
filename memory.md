# Deployment Status (2026-07-28)

## Infrastructure
- ECS Instance: `i-t4n8gt40krtdeqh894ke`
- Region: ap-southeast-1 (Singapore)
- Public IP: 8.222.176.62
- Work URLs: 
  - https://work-1-knghwnsaumfvkfyg.prod-runtime.all-hands.dev/ (port 12000)
  - https://work-2-knghwnsaumfvkfyg.prod-runtime.all-hands.dev/ (port 12001)

## Deployment Status
- ✅ Backend running on port 8080
- ✅ Frontend accessible via public IP (http://8.222.176.62/)
- ✅ Health endpoints working (/health, /api/health)
- ❌ Work URLs showing Bad Gateway (OpenHands Cloud Runtime issue)

## Key Files
- Deployment: `/root/project/`
- Entry: `/root/project/artifacts/pipeline/src/alibaba_entry.py`
- Venv: `/root/storyforge-venv/`
- Static files: `/root/project/public/`

## Notes
The app is functional on the public IP. The work-1/work-2 URLs are managed by OpenHands Cloud Runtime and need further investigation.

---

# StoryForge Platform Analysis

## Executive Summary

The StoryForge platform has a **well-developed backend** with comprehensive APIs for video production workflows, but the **frontend UI is incomplete**. While the foundation exists (scene editing, character management, episode listing), critical workflow features are missing.

---

## PART 1: BACKEND CAPABILITIES (Pipeline/APIs)

### ✅ Fully Implemented Backend Features

#### 1. **Story/Series Management**
- `POST /pipeline/stories` - Create stories with rich metadata (title, prompt, genre, style, workflow_type, reference URLs)
- `GET /pipeline/stories` - List all stories
- `GET /pipeline/stories/{id}` - Full story details including `episode_plan` (generated outline)
- `PUT /pipeline/stories/{id}/approve-outline` - Approve generated outline
- `PUT /pipeline/stories/{id}/generate` - Start generation
- `PUT /pipeline/stories/{id}/pipeline-config` - Update pipeline configuration
- `GET /pipeline/stories/{id}/history` - Event history

#### 2. **Reference Images & Assets (Backend-Supported, UI Missing)**
The backend accepts these on story creation:
```python
style_reference_urls: list[str]      # Style reference images
character_reference_urls: list[str]  # Character reference images  
scene_reference_urls: list[str]      # Scene reference images
```

**Upload endpoint:** `POST /pipeline/uploads/image` - Upload reference images

#### 3. **Character Management**
- Full CRUD operations
- `ref_image_urls` - Multiple reference images per character
- `lock`/`unlock` - Prevent accidental modifications
- `approve`/`reject` - Review workflow
- `regenerate-refs` - Regenerate character reference images
- Voice reference support (`voice_ref_url`)

#### 4. **Scene Management**
- Full CRUD with rich metadata
- `approve`/`reject`/`lock`/`unlock`
- `regenerate` - Regenerate scene media
- Character associations (`character_ids`, `primary_character_ids`)
- Reference images (`reference_image_urls`)
- Multiple media kinds: `video`, `image` (narrated), `voice`

#### 5. **Episode Management**
- `GET /pipeline/episodes/story/{story_id}` - All episodes with scenes
- `POST /pipeline/episodes/{id}/bulk-approve` - Approve all scenes
- `POST /pipeline/episodes/{id}/assemble` - Stitch video from approved scenes
- Episode summaries from `episode_plan`

#### 6. **Generation Checkpoints (Critical for Production Workflow)**
- `GET /pipeline/stories/{id}/checkpoints` - List checkpoints
- `PUT /pipeline/stories/{id}/checkpoints/{id}/approve` - Approve checkpoint & resume
- `POST /pipeline/stories/{id}/checkpoints/{id}/audio/regenerate` - Regenerate narration audio
- Checkpoints include: `narration_text`, `narration_voice`, `narration_audio_url`, `batch_size`, episode/scene ranges

#### 7. **Pipeline Config (Workflow Settings)**
```python
pipeline_config: {
  media: { kind, ratio, duration_seconds, quality },
  approvals: { outline_required, checkpoint_batch_size, publish_requires_approval },
  providers: { video_preference, image_preference, allow_fallback_to_image },
  continuity: { use_character_refs, use_previous_exit_frame, max_reference_images }
}
```

#### 8. **Job Tracking**
- `GET /pipeline/jobs/{id}` - Job status
- `POST /pipeline/jobs/{id}/cancel`
- `POST /pipeline/jobs/{id}/retry`
- `GET /pipeline/jobs/{id}/metrics` - Cost, latency, retries

#### 9. **Pipeline Runs/Debug**
- `GET /pipeline/runs/story/{story_id}` - Recent runs
- `GET /pipeline/runs/{run_id}` - Run with steps and artifacts
- `POST /pipeline/runs/{run_id}/cancel`
- `POST /pipeline/runs/steps/{step_id}/retry`

#### 10. **Publishing & Social**
- Social account OAuth (YouTube, TikTok)
- `POST /pipeline/publish-targets` - Create publish targets
- `POST /pipeline/publish-targets/{id}/publish-now`
- Approval workflows for publishing

#### 11. **Scheduling**
- Schedule types: `generate_only`, `publish_existing`, `generate_and_publish`, `series_continuation`
- Cadences: `once`, `interval_hours`, `daily`, `weekly`
- Approval policies: `require_approval`, `auto_publish`, `generate_only`

---

## PART 2: FRONTEND UI ANALYSIS

### ✅ What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| Dashboard | ✅ Basic | Lists stories, stats, schedules, recent runs |
| Create Story Modal | ✅ Basic | Captures title, prompt, genre, style, ratio, episodes/scenes |
| Editor Layout | ✅ Framework | 3-column layout with SceneList, SceneStage, AiChatPanel |
| Scene Stage | ✅ Editing | Title, visual prompt, script, narration, mood, location |
| Scene List | ✅ Basic | Scene listing with status indicators |
| Character Sheet | ✅ Basic CRUD | Add/edit/delete characters with name, role, description |
| AI Assistant | ✅ Basic | Chat panel for scene revisions |
| Episode Management | ✅ Add | Can add new episodes |
| Approve All | ✅ Button | Bulk approve scenes |
| Assemble | ✅ Button | Assemble episode video |
| Style Memory | ✅ Dialog | Save style preferences |
| Export Menu | ✅ Framework | Export options |
| Schedule Page | ✅ Basic | List and create schedules |
| Social Accounts | ⚠️ Settings only | Settings page exists |

### ❌ What's Missing (Frontend Gaps)

#### **GAP 1: Story Creation - Reference Images**
- ❌ Upload interface for style reference images
- ❌ Upload interface for character reference images
- ❌ Upload interface for scene reference images
- ❌ Preview thumbnails of uploaded references
- ❌ Remove/reorder reference images
- ❌ Bible/reference management

#### **GAP 2: Editor - Series/Story Details Panel**
- ❌ Display `episode_plan` (generated outline) - synopsis, episode summaries
- ❌ Story status indicator (draft → approved → generating → completed)
- ❌ "Approve Outline" button (when status is `draft`)
- ❌ "Start Generation" button (when status is `approved`)
- ❌ Generation progress indicator
- ❌ Pipeline config panel (media settings, approval settings)
- ❌ Story metadata display (genre, style, workflow type)

#### **GAP 3: Editor - Checkpoint Review UI**
- ❌ Checkpoint list panel/tab
- ❌ Checkpoint review interface showing scenes to approve
- ❌ "Approve Checkpoint & Continue" button
- ❌ Narration voice selection per checkpoint
- ❌ Audio preview for checkpoints
- ❌ Checkpoint status indicators

#### **GAP 4: Editor - Character Reference Images**
- ❌ Upload button for character reference images
- ❌ View/expand reference images gallery
- ❌ Set primary reference image
- ❌ "Regenerate References" button
- ❌ Approve/reject character references

#### **GAP 5: Editor - Scene Reference Images & Continuity**
- ❌ Upload reference images to scenes
- ❌ Character assignment to scenes (visual picker)
- ❌ Primary character selection

#### **GAP 6: Generation Workflow Buttons**
- ❌ "Approve Outline" button (for draft stories)
- ❌ "Generate" / "Start Generation" button
- ❌ Generation status/progress indicator
- ❌ "Cancel Generation" button

#### **GAP 7: Episode-Level Features**
- ❌ Episode title editing
- ❌ Episode summary display
- ❌ "Start New Episode" after completing one
- ❌ Episode video preview

#### **GAP 8: Narration/Checkpoint Audio**
- ❌ Narration voice selector
- ❌ Audio preview player

---

## IMPLEMENTATION ROADMAP

### Phase 1: Core Workflow (Priority)
1. ✅ **Story Creation** - Add reference image upload section
2. ✅ **Outline Approval** - Add "Approve Outline" button and outline display
3. ✅ **Generate Button** - Add "Start Generation" with status
4. ✅ **Checkpoint UI** - Basic checkpoint listing and approval

### Phase 2: Character Enhancement ✅ COMPLETED
5. ✅ **Character Refs Upload** - Add upload to CharacterSheet with gallery
6. ✅ **Character-Regeneration** - Add regenerate refs button
7. ✅ **Character Assignment** - Add to scene editing

### Phase 3: Production Polish ✅ COMPLETED
8. ✅ **Episode Management** - Episode titles, summaries, assembled video preview
9. ✅ **Narration Audio** - Voice selection per scene with preview
10. ✅ **Publishing** - PublishSheet component for publish targets and history

### Phase 4: Advanced Features ✅ COMPLETED
11. ✅ **Gallery View** - GalleryPage.jsx with grid/list views, filtering, lightbox preview
12. ✅ **Pipeline Config UI** - PipelineConfigDialog with media/approval/provider/continuity settings
13. ✅ **Bible Management** - BibleSheet component for brand/character/world/style bibles
14. ✅ **Routing & Integration** - Added Gallery route to App.jsx and navigation sidebar

### Phase 5: Testing (Requires External Backend)
15. ⚠️ Backend testing requires CockroachDB and Redis connections

---

## Key Files Reference

### Frontend
- `/web/src/pages/Editor.jsx` - Main editor page
- `/web/src/pages/Dashboard.jsx` - Dashboard page
- `/web/src/pages/Gallery.jsx` - Gallery view (NEW)
- `/web/src/components/dysentry/CreateStoryModal.jsx` - Story creation modal
- `/web/src/components/dysentry/editor/SceneStage.jsx` - Scene editing panel
- `/web/src/components/dysentry/editor/CharacterSheet.jsx` - Character management (with ref upload)
- `/web/src/components/dysentry/editor/CheckpointReviewSheet.jsx` - Checkpoint review
- `/web/src/components/dysentry/editor/PublishSheet.jsx` - Publishing UI
- `/web/src/components/dysentry/editor/BibleSheet.jsx` - Bible management (NEW)
- `/web/src/components/dysentry/editor/PipelineConfigDialog.jsx` - Pipeline settings (NEW)
- `/web/src/components/dysentry/AppChrome.jsx` - Navigation sidebar
- `/web/src/api/dysentryClient.js` - API client functions
- `/web/src/App.jsx` - Routes configuration

### Backend
- `/artifacts/pipeline/src/routes/stories.py` - Story API routes
- `/artifacts/pipeline/src/routes/checkpoints.py` - Checkpoint API routes
- `/artifacts/pipeline/src/routes/gallery.py` - Gallery API
- `/artifacts/pipeline/src/routes/bibles.py` - Bibles API
- `/artifacts/pipeline/src/routes/characters.py` - Character API routes
- `/artifacts/pipeline/src/models/story.py` - Pydantic models

---

## Tech Stack
- **Frontend**: React, Vite, TailwindCSS, React Router, Lucide icons
- **Backend**: FastAPI, PostgreSQL/CockroachDB, Redis, Backblaze B2
- **AI Providers**: DashScope (Qwen, Wan2.7), AIML API
