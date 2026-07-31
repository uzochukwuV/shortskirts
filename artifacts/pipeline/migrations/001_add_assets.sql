-- Assets table migration for unified agent system
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
    parent_asset_id UUID REFERENCES assets(id),  -- For derived assets
    
    -- Organization
    tags TEXT[] DEFAULT '{}',   -- Searchable tags
    metadata JSONB DEFAULT '{}', -- Additional metadata
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Constraints
    CONSTRAINT valid_asset_type CHECK (asset_type IN ('video', 'image', 'audio', 'document'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_assets_story_id ON assets(story_id);
CREATE INDEX IF NOT EXISTS idx_assets_entity ON assets(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_assets_parent ON assets(parent_asset_id);
CREATE INDEX IF NOT EXISTS idx_assets_created ON assets(created_at DESC);

-- Full-text search on metadata
CREATE INDEX IF NOT EXISTS idx_assets_metadata ON assets USING GIN(metadata);


-- ══════════════════════════════════════════════════════════════════════════════
-- ASSET RELATIONSHIPS TABLE - Track relationships between assets
-- ══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS asset_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source_asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    target_asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    
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
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Prevent duplicate relationships
    CONSTRAINT unique_relationship UNIQUE (source_asset_id, target_asset_id, relationship_type),
    CONSTRAINT no_self_reference CHECK (source_asset_id != target_asset_id)
);

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
    
    last_updated TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE (story_id)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_storage_usage_story ON storage_usage(story_id);


-- ══════════════════════════════════════════════════════════════════════════════
-- FUNCTIONS & TRIGGERS
-- ══════════════════════════════════════════════════════════════════════════════

-- Function to update storage usage when assets change
CREATE OR REPLACE FUNCTION update_storage_usage()
RETURNS TRIGGER AS $$
BEGIN
    -- Update on insert
    IF TG_OP = 'INSERT' THEN
        UPDATE storage_usage SET
            total_bytes = total_bytes + NEW.size_bytes,
            video_bytes = video_bytes + CASE WHEN NEW.asset_type = 'video' THEN NEW.size_bytes ELSE 0 END,
            image_bytes = image_bytes + CASE WHEN NEW.asset_type = 'image' THEN NEW.size_bytes ELSE 0 END,
            audio_bytes = audio_bytes + CASE WHEN NEW.asset_type = 'audio' THEN NEW.size_bytes ELSE 0 END,
            asset_count = asset_count + 1,
            video_count = video_count + CASE WHEN NEW.asset_type = 'video' THEN 1 ELSE 0 END,
            image_count = image_count + CASE WHEN NEW.asset_type = 'image' THEN 1 ELSE 0 END,
            last_updated = now()
        WHERE story_id = NEW.story_id;
        
        -- Insert if not exists
        IF NOT FOUND THEN
            INSERT INTO storage_usage (story_id, total_bytes, asset_count)
            VALUES (NEW.story_id, NEW.size_bytes, 1);
        END IF;
        
        RETURN NEW;
    
    -- Update on delete
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE storage_usage SET
            total_bytes = total_bytes - OLD.size_bytes,
            video_bytes = video_bytes - CASE WHEN OLD.asset_type = 'video' THEN OLD.size_bytes ELSE 0 END,
            image_bytes = image_bytes - CASE WHEN OLD.asset_type = 'image' THEN OLD.size_bytes ELSE 0 END,
            audio_bytes = audio_bytes - CASE WHEN OLD.asset_type = 'audio' THEN OLD.size_bytes ELSE 0 END,
            asset_count = asset_count - 1,
            video_count = video_count - CASE WHEN OLD.asset_type = 'video' THEN 1 ELSE 0 END,
            image_count = image_count - CASE WHEN OLD.asset_type = 'image' THEN 1 ELSE 0 END,
            last_updated = now()
        WHERE story_id = OLD.story_id;
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic storage updates
DROP TRIGGER IF EXISTS trigger_update_storage_usage ON assets;
CREATE TRIGGER trigger_update_storage_usage
AFTER INSERT OR DELETE ON assets
FOR EACH ROW EXECUTE FUNCTION update_storage_usage();


-- ══════════════════════════════════════════════════════════════════════════════
-- HELPER VIEWS
-- ══════════════════════════════════════════════════════════════════════════════

-- View: Story assets with relationships
CREATE OR REPLACE VIEW story_assets_view AS
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
CREATE OR REPLACE VIEW continuity_chains AS
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
