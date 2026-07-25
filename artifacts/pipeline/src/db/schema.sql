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
ALTER TABLE stories ADD COLUMN IF NOT EXISTS workflow_version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS generation_version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS workflow_state JSONB NOT NULL DEFAULT '{}';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'pending_approval';
ALTER TABLE stories ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;

-- ── Story history ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS story_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    revision INT NOT NULL,
    event_type TEXT NOT NULL,
    workflow_version TEXT NOT NULL DEFAULT 'v1',
    generation_version TEXT NOT NULL DEFAULT 'v1',
    source_job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    state_snapshot JSONB NOT NULL DEFAULT '{}',
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(story_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_story_history_story_id ON story_history(story_id);
CREATE INDEX IF NOT EXISTS idx_story_history_created_at ON story_history(created_at);

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
    image_url TEXT,
    exit_frame_url TEXT,
    duration FLOAT,
    status TEXT NOT NULL DEFAULT 'pending',
    generation_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(episode_id, scene_number)
);

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS locked BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS regeneration_count INT NOT NULL DEFAULT 0;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS generation_version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS image_model TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS image_model_version TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS edit_model TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS edit_model_version TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS source_scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS state_snapshot JSONB NOT NULL DEFAULT '{}';

-- ── Scene history ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scene_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    revision INT NOT NULL,
    event_type TEXT NOT NULL,
    generation_version TEXT NOT NULL DEFAULT 'v1',
    image_model TEXT,
    image_model_version TEXT,
    edit_model TEXT,
    edit_model_version TEXT,
    source_job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    state_snapshot JSONB NOT NULL DEFAULT '{}',
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(scene_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_scene_history_scene_id ON scene_history(scene_id);
CREATE INDEX IF NOT EXISTS idx_scene_history_story_id ON scene_history(story_id);
CREATE INDEX IF NOT EXISTS idx_scene_history_created_at ON scene_history(created_at);

CREATE INDEX IF NOT EXISTS idx_scenes_episode_id ON scenes(episode_id);

-- ── Story checkpoints ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS story_generation_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    resume_job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    batch_number INT NOT NULL DEFAULT 1,
    batch_size INT NOT NULL DEFAULT 3,
    start_episode_number INT NOT NULL DEFAULT 1,
    start_scene_number INT NOT NULL DEFAULT 1,
    end_episode_number INT NOT NULL DEFAULT 1,
    end_scene_number INT NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending_review',
    generation_version TEXT NOT NULL DEFAULT 'v1',
    narration_model TEXT,
    narration_voice TEXT,
    narration_text TEXT,
    audio_job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    audio_status TEXT NOT NULL DEFAULT 'pending',
    narration_audio_url TEXT,
    narration_audio_manifest_url TEXT,
    state_snapshot JSONB NOT NULL DEFAULT '{}',
    resume_state JSONB,
    reviewer_notes TEXT,
    approved_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS generation_version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS state_snapshot JSONB NOT NULL DEFAULT '{}';
ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS narration_voice TEXT;
ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS narration_text TEXT;
ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS narration_audio_url TEXT;
ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS narration_audio_manifest_url TEXT;
ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS audio_job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL;
ALTER TABLE story_generation_checkpoints ADD COLUMN IF NOT EXISTS audio_status TEXT NOT NULL DEFAULT 'pending';

-- ── Checkpoint history ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS checkpoint_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checkpoint_id UUID NOT NULL REFERENCES story_generation_checkpoints(id) ON DELETE CASCADE,
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    revision INT NOT NULL,
    event_type TEXT NOT NULL,
    generation_version TEXT NOT NULL DEFAULT 'v1',
    source_job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    state_snapshot JSONB NOT NULL DEFAULT '{}',
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(checkpoint_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_checkpoint_history_checkpoint_id ON checkpoint_history(checkpoint_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_history_story_id ON checkpoint_history(story_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_history_created_at ON checkpoint_history(created_at);

CREATE INDEX IF NOT EXISTS idx_story_checkpoints_story_id ON story_generation_checkpoints(story_id);
CREATE INDEX IF NOT EXISTS idx_story_checkpoints_status ON story_generation_checkpoints(status);

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
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS attempts INT NOT NULL DEFAULT 0;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS max_attempts INT NOT NULL DEFAULT 3;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS worker_id TEXT;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS leased_at TIMESTAMPTZ;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMPTZ;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_jobs_entity ON generation_jobs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON generation_jobs(status);

-- ── Pipeline runs / steps / artifacts ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    run_type TEXT NOT NULL DEFAULT 'story_generation',
    status TEXT NOT NULL DEFAULT 'pending',
    config JSONB NOT NULL DEFAULT '{}',
    summary JSONB NOT NULL DEFAULT '{}',
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS story_id UUID REFERENCES stories(id) ON DELETE CASCADE;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS run_type TEXT NOT NULL DEFAULT 'story_generation';
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}';
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS summary JSONB NOT NULL DEFAULT '{}';
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_owner_id ON pipeline_runs(owner_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_story_id ON pipeline_runs(story_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_job_id ON pipeline_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created_at ON pipeline_runs(created_at);

CREATE TABLE IF NOT EXISTS pipeline_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    parent_step_id UUID REFERENCES pipeline_steps(id) ON DELETE SET NULL,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL,
    scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL,
    job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    step_key TEXT NOT NULL,
    step_type TEXT NOT NULL DEFAULT 'operation',
    status TEXT NOT NULL DEFAULT 'pending',
    attempt INT NOT NULL DEFAULT 1,
    provider TEXT,
    provider_model TEXT,
    provider_task_id TEXT,
    provider_request_id TEXT,
    input JSONB NOT NULL DEFAULT '{}',
    output JSONB NOT NULL DEFAULT '{}',
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS parent_step_id UUID REFERENCES pipeline_steps(id) ON DELETE SET NULL;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS story_id UUID REFERENCES stories(id) ON DELETE CASCADE;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS step_type TEXT NOT NULL DEFAULT 'operation';
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS attempt INT NOT NULL DEFAULT 1;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS provider TEXT;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS provider_model TEXT;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS provider_task_id TEXT;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS provider_request_id TEXT;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS input JSONB NOT NULL DEFAULT '{}';
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS output JSONB NOT NULL DEFAULT '{}';
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE pipeline_steps ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_pipeline_steps_run_id ON pipeline_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_story_id ON pipeline_steps(story_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_scene_id ON pipeline_steps(scene_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_job_id ON pipeline_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_status ON pipeline_steps(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_step_key ON pipeline_steps(step_key);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_created_at ON pipeline_steps(created_at);

CREATE TABLE IF NOT EXISTS pipeline_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES pipeline_steps(id) ON DELETE SET NULL,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL,
    scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL,
    artifact_type TEXT NOT NULL,
    media_kind TEXT,
    url TEXT,
    content JSONB,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS step_id UUID REFERENCES pipeline_steps(id) ON DELETE SET NULL;
ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS story_id UUID REFERENCES stories(id) ON DELETE CASCADE;
ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL;
ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL;
ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS media_kind TEXT;
ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS content JSONB;
ALTER TABLE pipeline_artifacts ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_run_id ON pipeline_artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_step_id ON pipeline_artifacts(step_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_story_id ON pipeline_artifacts(story_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_scene_id ON pipeline_artifacts(scene_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_type ON pipeline_artifacts(artifact_type);

-- ── Social accounts / publishing / schedules ───────────────────────────────

CREATE TABLE IF NOT EXISTS social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    platform_user_id TEXT,
    display_name TEXT,
    scopes JSONB NOT NULL DEFAULT '[]',
    token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'connected',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(owner_id, platform, platform_user_id)
);

ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS platform_user_id TEXT;
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS scopes JSONB NOT NULL DEFAULT '[]';
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS token_encrypted TEXT;
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS refresh_token_encrypted TEXT;
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ;
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'connected';
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_social_accounts_owner_id ON social_accounts(owner_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_platform ON social_accounts(platform);
CREATE INDEX IF NOT EXISTS idx_social_accounts_status ON social_accounts(status);

CREATE TABLE IF NOT EXISTS publish_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    social_account_id UUID REFERENCES social_accounts(id) ON DELETE SET NULL,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL,
    scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL,
    artifact_id UUID REFERENCES pipeline_artifacts(id) ON DELETE SET NULL,
    platform TEXT NOT NULL,
    asset_kind TEXT NOT NULL DEFAULT 'episode',
    media_url TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags JSONB NOT NULL DEFAULT '[]',
    privacy_status TEXT NOT NULL DEFAULT 'private',
    publish_mode TEXT NOT NULL DEFAULT 'manual',
    requires_approval BOOLEAN NOT NULL DEFAULT true,
    approved_at TIMESTAMPTZ,
    scheduled_for TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'draft',
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS social_account_id UUID REFERENCES social_accounts(id) ON DELETE SET NULL;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS story_id UUID REFERENCES stories(id) ON DELETE CASCADE;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS artifact_id UUID REFERENCES pipeline_artifacts(id) ON DELETE SET NULL;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS asset_kind TEXT NOT NULL DEFAULT 'episode';
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS media_url TEXT;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]';
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS privacy_status TEXT NOT NULL DEFAULT 'private';
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS publish_mode TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';
ALTER TABLE publish_targets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_publish_targets_owner_id ON publish_targets(owner_id);
CREATE INDEX IF NOT EXISTS idx_publish_targets_story_id ON publish_targets(story_id);
CREATE INDEX IF NOT EXISTS idx_publish_targets_episode_id ON publish_targets(episode_id);
CREATE INDEX IF NOT EXISTS idx_publish_targets_status ON publish_targets(status);
CREATE INDEX IF NOT EXISTS idx_publish_targets_scheduled_for ON publish_targets(scheduled_for);

CREATE TABLE IF NOT EXISTS publish_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publish_target_id UUID NOT NULL REFERENCES publish_targets(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    platform_post_id TEXT,
    public_url TEXT,
    upload_session_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    response JSONB NOT NULL DEFAULT '{}',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE publish_posts ADD COLUMN IF NOT EXISTS platform_post_id TEXT;
ALTER TABLE publish_posts ADD COLUMN IF NOT EXISTS public_url TEXT;
ALTER TABLE publish_posts ADD COLUMN IF NOT EXISTS upload_session_id TEXT;
ALTER TABLE publish_posts ADD COLUMN IF NOT EXISTS response JSONB NOT NULL DEFAULT '{}';
ALTER TABLE publish_posts ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE publish_posts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_publish_posts_target_id ON publish_posts(publish_target_id);
CREATE INDEX IF NOT EXISTS idx_publish_posts_platform ON publish_posts(platform);
CREATE INDEX IF NOT EXISTS idx_publish_posts_status ON publish_posts(status);

CREATE TABLE IF NOT EXISTS automation_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    cadence TEXT NOT NULL DEFAULT 'once',
    cadence_config JSONB NOT NULL DEFAULT '{}',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    next_run_at TIMESTAMPTZ,
    enabled BOOLEAN NOT NULL DEFAULT true,
    pipeline_config JSONB NOT NULL DEFAULT '{}',
    publish_config JSONB NOT NULL DEFAULT '{}',
    approval_policy TEXT NOT NULL DEFAULT 'require_approval',
    status TEXT NOT NULL DEFAULT 'active',
    last_run_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS story_id UUID REFERENCES stories(id) ON DELETE CASCADE;
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS cadence TEXT NOT NULL DEFAULT 'once';
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS cadence_config JSONB NOT NULL DEFAULT '{}';
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC';
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ;
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS pipeline_config JSONB NOT NULL DEFAULT '{}';
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS publish_config JSONB NOT NULL DEFAULT '{}';
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS approval_policy TEXT NOT NULL DEFAULT 'require_approval';
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ;
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE automation_schedules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_automation_schedules_owner_id ON automation_schedules(owner_id);
CREATE INDEX IF NOT EXISTS idx_automation_schedules_story_id ON automation_schedules(story_id);
CREATE INDEX IF NOT EXISTS idx_automation_schedules_due ON automation_schedules(enabled, next_run_at);
CREATE INDEX IF NOT EXISTS idx_automation_schedules_status ON automation_schedules(status);

CREATE TABLE IF NOT EXISTS scheduled_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES automation_schedules(id) ON DELETE SET NULL,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    story_id UUID REFERENCES stories(id) ON DELETE SET NULL,
    episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL,
    publish_target_id UUID REFERENCES publish_targets(id) ON DELETE SET NULL,
    job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL,
    run_type TEXT NOT NULL,
    due_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending',
    result JSONB NOT NULL DEFAULT '{}',
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS schedule_id UUID REFERENCES automation_schedules(id) ON DELETE SET NULL;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS story_id UUID REFERENCES stories(id) ON DELETE SET NULL;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS episode_id UUID REFERENCES episodes(id) ON DELETE SET NULL;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS publish_target_id UUID REFERENCES publish_targets(id) ON DELETE SET NULL;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES generation_jobs(id) ON DELETE SET NULL;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS result JSONB NOT NULL DEFAULT '{}';
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE scheduled_runs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_scheduled_runs_schedule_id ON scheduled_runs(schedule_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_runs_owner_id ON scheduled_runs(owner_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_runs_status ON scheduled_runs(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_runs_job_id ON scheduled_runs(job_id);

-- ── Metrics ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pipeline_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms INT,
    provider_latency_ms INT,
    estimated_cost_usd DECIMAL(12,6),
    retries INT NOT NULL DEFAULT 0,
    step_name TEXT,
    provider TEXT,
    provider_task_id TEXT,
    provider_request_id TEXT,
    error TEXT,
    job_id UUID,
    entity_type TEXT,
    entity_id UUID,
    workload TEXT,
    extra JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE pipeline_metrics ADD COLUMN IF NOT EXISTS provider_task_id TEXT;
ALTER TABLE pipeline_metrics ADD COLUMN IF NOT EXISTS provider_request_id TEXT;

CREATE TABLE IF NOT EXISTS admin_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_admin_sessions_token_hash ON admin_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires_at ON admin_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_kind ON pipeline_metrics(metric_kind);
CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_job_id ON pipeline_metrics(job_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_metrics_created_at ON pipeline_metrics(created_at);
