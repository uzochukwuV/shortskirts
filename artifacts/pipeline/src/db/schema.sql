-- StoryForge Anime - CockroachDB Schema
-- All statements are idempotent (IF NOT EXISTS / IF NOT EXISTS guards)


-- Auth -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions(expires_at);

-- ── Stories ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    genre TEXT NOT NULL DEFAULT 'action',
    style TEXT NOT NULL DEFAULT 'anime',
    num_episodes INT NOT NULL DEFAULT 1,
    num_scenes INT NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'draft',
    episode_plan JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- New columns on stories (safe to re-run)
ALTER TABLE stories ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE stories ADD COLUMN IF NOT EXISTS workflow_type TEXT NOT NULL DEFAULT 'creator_series';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'pending_approval';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;

-- ── Bibles ────────────────────────────────────────────────────────────────────
-- Persistent memory: brand bibles, character bibles, world bibles, campaign bibles

CREATE TABLE IF NOT EXISTS bibles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    bible_type TEXT NOT NULL DEFAULT 'brand',
    name TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE bibles ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_bibles_owner_id ON bibles(owner_id);
CREATE INDEX IF NOT EXISTS idx_bibles_story_id ON bibles(story_id);

-- ── Characters ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'main',
    personality TEXT NOT NULL DEFAULT '',
    appearance TEXT NOT NULL DEFAULT '',
    ref_image_urls JSONB NOT NULL DEFAULT '[]',
    voice_ref_url TEXT,
    embedding JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE characters ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE characters ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE characters ADD COLUMN IF NOT EXISTS locked BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_characters_story_id ON characters(story_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_characters_story_name ON characters(story_id, name);

-- ── Episodes ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    episode_number INT NOT NULL,
    title TEXT NOT NULL,
    assembled_video_url TEXT,
    manifest_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(story_id, episode_number)
);

CREATE INDEX IF NOT EXISTS idx_stories_owner_id ON stories(owner_id);
CREATE INDEX IF NOT EXISTS idx_episodes_story_id ON episodes(story_id);

-- ── Scenes ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scenes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    scene_number INT NOT NULL,
    prompt TEXT NOT NULL,
    clip_url TEXT,
    exit_frame_url TEXT,
    duration FLOAT,
    status TEXT NOT NULL DEFAULT 'pending',
    generation_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(episode_id, scene_number)
);

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS locked BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS regeneration_count INT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_scenes_episode_id ON scenes(episode_id);

-- ── Scene-character join ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scene_characters (
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (scene_id, character_id)
);

-- ── Generation jobs ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress INT NOT NULL DEFAULT 0,
    total_steps INT NOT NULL DEFAULT 0,
    current_step TEXT NOT NULL DEFAULT '',
    error TEXT,
    result JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS job_type TEXT NOT NULL DEFAULT 'full_episode';

CREATE INDEX IF NOT EXISTS idx_jobs_entity ON generation_jobs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON generation_jobs(status);
