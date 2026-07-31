# Asset Management & Assembly Analysis

## Current Environment

### Credentials & Services

| Service | Status | Configuration |
|---------|--------|---------------|
| **Storage (B2)** | ✅ Configured | Backblaze B2 S3-compatible |
| **Database (CockroachDB)** | ✅ Configured | PostgreSQL-compatible |
| **Job Queue (Redis)** | ✅ Configured | For background processing |
| **LLM (TokenRouter)** | ✅ Configured | moonshotai/kimi-k3-free |
| **Genblaze API** | ❌ Not Set | Needs `GENBLAZE_API_KEY` |
| **OpenAI API** | ❌ Not Set | Needs `OPENAI_API_KEY` for TTS |

### Current .env Configuration

```
# Storage - Backblaze B2
B2_BUCKET_NAME=anime-shorts
B2_ENDPOINT_URL=s3.us-east-005.backblazeb2.com
B2_KEY_ID=0051935951af6d10000000009
B2_APPLICATION_KEY=K005FsPtL5NmlQXMWvpi1iWdB1qsHTE
B2_READ_KEY_ID=0051935951af6d10000000008
B2_READ_APPLICATION_KEY=K005yL19e+AQK93JigzxjC8W87XdjCs

# Database - CockroachDB
COCKROACHDB_URL=postgresql://anime-shorts:...@anime-shorts-28316.j77.aws-eu-central-1.cockroachlabs.cloud:26257/defaultdb

# Job Queue - Redis
REDIS_URL=redis://default:...@decision-hair-flavor-24816.db.redis.io:10965

# LLM - TokenRouter
TOKENROUTER_API_KEY=sk-qoEDCqdBz4PIXGJruX3Io4BNjLcpwyVTSPhC2INuZDaQv0zV
TOKENROUTER_API_URL=https://api.tokenrouter.com/v1
TOKENROUTER_MODEL=moonshotai/kimi-k3-free

# Missing for Full Agentic Workflow
GENBLAZE_API_KEY=<NOT SET>
OPENAI_API_KEY=<NOT SET>
```

---

## Storage Architecture (B2)

### Current Implementation (`storage/b2.py`)

```python
# Write operations (uploads)
get_write_client() → B2_KEY_ID + B2_APPLICATION_KEY

# Read operations (presigned URLs)  
get_read_client() → B2_READ_KEY_ID + B2_READ_APPLICATION_KEY

# Storage paths
build_key(story_id, *parts) → "stories/{story_id}/{parts}"
```

### Storage Buckets & Keys

```
Bucket: anime-shorts
├── stories/
│   └── {story_id}/
│       ├── scenes/
│       │   └── {scene_id}/
│       │       ├── clip.mp4
│       │       ├── thumbnail.jpg
│       │       └── frame_001.jpg
│       ├── episodes/
│       │   └── {episode_id}/
│       │       └── assembled.mp4
│       ├── references/
│       │   └── {character_id}/
│       │       └── ref_001.jpg
│       └── narration/
│           └── {scene_id}.mp3
└── uploads/
    └── references/
        └── {uuid}.jpg
```

---

## Asset Management - What We Have

### Scene Assets

| Asset Type | Storage | Status |
|------------|---------|--------|
| `clip_url` | B2 storage | ✅ Stored |
| `image_url` | B2 storage | ✅ Stored |
| `exit_frame_url` | B2 storage | ✅ Stored |
| `thumbnail_url` | B2 storage | ✅ Stored |
| `narration_url` | B2 storage | ✅ Supported |

### Reference Images

| Type | Storage | Status |
|------|---------|--------|
| Scene references | `reference_image_urls` in metadata | ✅ |
| Character references | `ref_image_urls` on characters | ✅ |
| Continuity references | `continuity_reference` in metadata | ✅ |

### Generation Jobs

```sql
generation_jobs (
  id, entity_type, entity_id, status,
  job_type, result, error,
  created_at, started_at, completed_at
)
```

---

## What We Need - Asset Management Gaps

### 1. ❌ Centralized Asset Library

**Current:** Assets are scattered across scenes in JSON metadata
**Needed:**
- Dedicated `assets` table for asset tracking
- Version history for assets
- Asset relationships (derived_from, copies)

### 2. ❌ Asset Search & Discovery

**Current:** Basic ILIKE search
**Needed:**
- Full-text search with Elasticsearch/OpenSearch
- Tag-based filtering
- AI-powered semantic search

### 3. ❌ Asset Cleanup & Storage Management

**Current:** No cleanup
**Needed:**
- Orphaned asset detection
- Storage quota tracking
- Auto-archive old assets

### 4. ❌ Assembly Pipeline

**Current:** `assemble_episode` tool creates job, but no worker handler
**Needed:**
- FFmpeg-based video stitching
- Transition application
- Audio mixing (narration + music)
- Export & encoding

---

## Recommended Asset Management System

### 1. Database Schema

```sql
-- Asset registry
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id),
    asset_type TEXT NOT NULL, -- 'video', 'image', 'audio', 'document'
    storage_key TEXT NOT NULL, -- B2 key
    storage_url TEXT, -- Presigned URL
    metadata JSONB DEFAULT '{}',
    size_bytes BIGINT,
    mime_type TEXT,
    checksum TEXT, -- SHA256 for dedup
    version INT DEFAULT 1,
    parent_asset_id UUID REFERENCES assets(id), -- For versioning
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Search
    tags TEXT[] DEFAULT '{}',
    description TEXT,
    
    -- Usage tracking
    used_in_scenes UUID[] DEFAULT '{}',
    used_in_episodes UUID[] DEFAULT '{}'
);

-- Asset relationships
CREATE TABLE asset_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_asset_id UUID REFERENCES assets(id),
    target_asset_id UUID REFERENCES assets(id),
    relationship_type TEXT, -- 'reference', 'continuity', 'derivative', 'backup'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Storage usage tracking
CREATE TABLE storage_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID REFERENCES stories(id),
    total_bytes BIGINT DEFAULT 0,
    asset_count INT DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT now()
);
```

### 2. Agent Tools

```python
# Asset Management Tools
register_tool("upload_asset", ...)
register_tool("list_assets", ...)  
register_tool("search_assets", ...)
register_tool("link_assets", ...)  # Create relationships
register_tool("get_asset_versions", ...)
register_tool("delete_asset", ...)

# Assembly Tools (needs worker)
register_tool("assemble_episode", ...)  # Currently creates job, needs handler
register_tool("apply_transition", ...)  # FFmpeg-based
register_tool("mix_audio", ...)  # FFmpeg-based
register_tool("export_episode", ...)  # Final export
```

### 3. Worker Handlers

```python
# worker.py - Add handlers
WORKLOAD_ASSEMBLY = "assembly"

async def run_assembly_job(pool, job_id: str):
    # 1. Download all scene clips
    # 2. Apply transitions with FFmpeg
    # 3. Mix audio tracks
    # 4. Encode final video
    # 5. Upload to B2
    # 6. Update episode record
    pass
```

---

## Assembly Pipeline Design

### Video Assembly Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASSEMBLY PIPELINE                            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │ Scene 1  │          │ Scene 2 │          │ Scene 3 │
   │ clip.mp4 │          │ clip.mp4│          │ clip.mp4│
   └────┬─────┘          └────┬─────┘          └────┬─────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │ Download from B2
                              ▼
                   ┌─────────────────────┐
                   │  FFmpeg Processing  │
                   │  • Concatenate     │
                   │  • Apply transitions│
                   │  • Mix audio        │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │   Output Video      │
                   │   episode_final.mp4 │
                   └──────────┬──────────┘
                              │
                              ▼
                       Upload to B2
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Update Episode DB   │
                   │ episode_url = ...   │
                   └─────────────────────┘
```

### FFmpeg Assembly Command

```bash
# Concatenate scenes with transitions
ffmpeg \
  -i scene1.mp4 \
  -i scene2.mp4 \
  -i scene3.mp4 \
  -filter_complex "
    [0:v]fade=t=out:st=4:d=0.5[v1];
    [1:v]fade=t=in:st=0:d=0.5,fade=t=out:st=4:d=0.5[v2];
    [2:v]fade=t=in:st=0:d=0.5[v3];
    [v1][0:a][v2][1:a][v3][2:a]concat=n=3:v=1:a=1[outv][outa]
  " \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  assembled_episode.mp4
```

---

## Missing Environment Variables

### Required for Full Agentic Workflow

```bash
# Add to .env

# Genblaze (Video Generation)
GENBLAZE_API_URL=https://api.genblaze.ai
GENBLAZE_API_KEY=your_genblaze_api_key

# OpenAI (TTS, Image Gen)
OPENAI_API_KEY=sk-...

# Optional: Asset Management
# ASSET_STORAGE_BUCKET=anime-shorts (already set)
# ASSET_MAX_SIZE_GB=100
```

---

## Implementation Priority

### Phase 1: Asset Registry (1-2 days)
- [ ] Add `assets` table to schema
- [ ] Add `asset_relationships` table
- [ ] Create asset upload tool
- [ ] Migrate existing scene assets

### Phase 2: Asset Discovery (1 day)
- [ ] Add full-text search
- [ ] Tag-based filtering
- [ ] Semantic search (optional)

### Phase 3: Assembly Pipeline (2-3 days)
- [ ] Add `run_assembly_job` to worker
- [ ] FFmpeg scene concatenation
- [ ] Transition effects
- [ ] Audio mixing
- [ ] Export & upload

### Phase 4: Advanced Features (Ongoing)
- [ ] Asset versioning
- [ ] Duplicate detection
- [ ] Storage optimization
- [ ] CDN integration

---

## Current vs Required State

| Feature | Current | Required |
|---------|---------|----------|
| Asset Storage | ✅ B2 configured | ✅ Ready |
| Asset Tracking | ❌ JSON metadata | Need `assets` table |
| Asset Search | ❌ ILIKE only | Full-text + tags |
| Video Assembly | ⚠️ Job created, no handler | Needs worker |
| Transitions | ⚠️ Metadata stored | Needs FFmpeg |
| Audio Mixing | ⚠️ TTS tool exists | Needs assembly |
| Genblaze | ❌ Not configured | Add key |
| OpenAI | ❌ Not configured | Add key for TTS |

---

## Quick Wins

1. **Update `_upload_audio` to use existing B2 storage** instead of R2
2. **Add assembly worker handler** to `worker.py`
3. **Create `assets` table** and migration script
4. **Add Genblaze API key** to `.env`
