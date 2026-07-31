-- Assets table migration for unified agent system
-- CockroachDB-compatible migration
-- Run this migration to add asset management to the database

-- ══════════════════════════════════════════════════════════════════════════════
-- ASSETS TABLE - Centralized media asset tracking
-- ══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    
    -- Asset classification
    entity_type TEXT NOT NULL,  -- 'scene', 'character', 'episode', 'story'
    entity_id UUID NOT NULL,    -- ID of the owning entity
    
    -- Media type
    asset_type TEXT NOT NULL,   -- 'video', 'image', 'audio', 'document'
    
    -- Storage info
    storage_key TEXT NOT NULL, -- B2/S3 key
    storage_url TEXT,          -- Presigned or public URL
    mime_type TEXT,            -- MIME type (video/mp4, image/png, etc.)
    size_bytes BIGINT DEFAULT 0,-- File size
    
    -- Integrity
    checksum TEXT,              -- SHA256 hash for verification
    
    -- Versioning
    version INT DEFAULT 1,      -- Asset version
    parent_asset_id UUID,       -- For derived assets (FK added after table exists)
    
    -- Organization
    tags JSONB DEFAULT '[]',    -- Searchable tags (CockroachDB uses JSONB)
    metadata JSONB DEFAULT '{}', -- Additional metadata
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Add FK constraint separately for CockroachDB compatibility
ALTER TABLE assets ADD CONSTRAINT fk_assets_parent 
    FOREIGN KEY (parent_asset_id) REFERENCES assets(id) ON DELETE CASCADE;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_assets_story_id ON assets(story_id);
CREATE INDEX IF NOT EXISTS idx_assets_entity ON assets(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_parent ON assets(parent_asset_id);
CREATE INDEX IF NOT EXISTS idx_assets_created ON assets(created_at DESC);

-- Full-text search on metadata
CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_assets_metadata ON assets USING GIN(metadata);


-- ══════════════════════════════════════════════════════════════════════════════
-- ASSET RELATIONSHIPS TABLE - Track relationships between assets
-- ══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS asset_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source_asset_id UUID NOT NULL,  -- FK added after tables exist
    target_asset_id UUID NOT NULL,   -- FK added after tables exist
    
    -- Relationship types
    relationship_type TEXT NOT NULL,
    -- 'reference' - This asset references the other
    -- 'continuity' - Exit frame continuity link
    -- 'derivative' - This asset was created from the other
    -- 'backup' - Backup of the other
    -- 'thumbnail' - Thumbnail for the other
    
    -- Additional info
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Add FK constraints
ALTER TABLE asset_relationships ADD CONSTRAINT fk_asset_rel_source
    FOREIGN KEY (source_asset_id) REFERENCES assets(id) ON DELETE CASCADE;
ALTER TABLE asset_relationships ADD CONSTRAINT fk_asset_rel_target
    FOREIGN KEY (target_asset_id) REFERENCES assets(id) ON DELETE CASCADE;
ALTER TABLE asset_relationships ADD CONSTRAINT unique_relationship
    UNIQUE (source_asset_id, target_asset_id, relationship_type);
ALTER TABLE asset_relationships ADD CONSTRAINT no_self_reference
    CHECK (source_asset_id != target_asset_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_asset_rel_source ON asset_relationships(source_asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_rel_target ON asset_relationships(target_asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_rel_type ON asset_relationships(relationship_type);


-- ══════════════════════════════════════════════════════════════════════════════
-- STORAGE USAGE TABLE - Track storage per story
-- ══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS storage_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    
    total_bytes BIGINT DEFAULT 0,
    video_bytes BIGINT DEFAULT 0,
    image_bytes BIGINT DEFAULT 0,
    audio_bytes BIGINT DEFAULT 0,
    other_bytes BIGINT DEFAULT 0,
    
    asset_count INT DEFAULT 0,
    video_count INT DEFAULT 0,
    image_count INT DEFAULT 0,
    audio_count INT DEFAULT 0,
    
    last_updated TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_storage_usage_story ON storage_usage(story_id);


-- ══════════════════════════════════════════════════════════════════════════════
-- HELPER VIEWS
-- ══════════════════════════════════════════════════════════════════════════════

-- View: Story assets with relationships
CREATE VIEW IF NOT EXISTS story_assets_view AS
SELECT 
    a.id,
    a.story_id,
    a.entity_type,
    a.entity_id,
    a.asset_type,
    a.storage_key,
    a.storage_url,
    a.mime_type,
    a.size_bytes,
    a.tags,
    a.metadata,
    a.version,
    a.created_at,
    r.relationship_type,
    r.target_asset_id as related_asset_id
FROM assets a
LEFT JOIN asset_relationships r ON a.id = r.source_asset_id;

-- View: Continuity chains (exit frame links)
CREATE VIEW IF NOT EXISTS continuity_chains AS
SELECT 
    source.id as scene_id,
    source.storage_url as source_video,
    target.id as next_scene_id,
    target.storage_url as next_video,
    source.metadata->'continuity_reference'->>'exit_frame_url' as exit_frame_url
FROM assets source
JOIN asset_relationships r ON source.id = r.source_asset_id AND r.relationship_type = 'continuity'
JOIN assets target ON r.target_asset_id = target.id
WHERE source.asset_type = 'video' AND target.asset_type = 'video';
