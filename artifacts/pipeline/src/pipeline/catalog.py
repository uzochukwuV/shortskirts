"""
Reference Catalog for continuity-aware asset retrieval.

Indexes existing uploads, character refs, scene refs, and exit frames.
Stores metadata: tags, source, approval status, usage history.
Provides catalog_search() function for filtered retrieval.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from db.connection import get_pool


# Catalog entry types
class AssetType:
    CHARACTER_REF = "character_ref"
    SCENE_REF = "scene_ref"
    EXIT_FRAME = "exit_frame"
    STYLE_REF = "style_ref"
    USER_UPLOAD = "user_upload"


# Approval status
class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


async def index_asset(
    *,
    story_id: str,
    asset_type: str,
    url: str,
    source: str,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    character_id: str | None = None,
    scene_id: str | None = None,
    episode_id: str | None = None,
) -> str:
    """
    Index a new asset in the reference catalog.
    Returns the catalog entry ID.
    """
    pool = await get_pool()
    
    row = await pool.fetchrow(
        """INSERT INTO reference_catalog
           (story_id, asset_type, url, source, tags, metadata, character_id, scene_id, episode_id, approval_status)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $9, 'pending')
           RETURNING id""",
        story_id,
        asset_type,
        url,
        source,
        json.dumps(tags or []),
        json.dumps(metadata or {}),
        character_id,
        scene_id,
        episode_id,
    )
    
    return str(row["id"])


async def update_asset_tags(
    *,
    catalog_id: str,
    tags: list[str],
) -> None:
    """Update tags for an existing catalog entry."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE reference_catalog SET tags=$2::jsonb, updated_at=now() WHERE id=$1",
        catalog_id,
        json.dumps(tags),
    )


async def update_asset_approval(
    *,
    catalog_id: str,
    approval_status: str,
) -> None:
    """Update approval status for a catalog entry."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE reference_catalog SET approval_status=$2, updated_at=now() WHERE id=$1",
        catalog_id,
        approval_status,
    )


async def record_asset_usage(
    *,
    catalog_id: str,
    used_in_scene_id: str,
    used_for_purpose: str | None = None,
) -> None:
    """Record that an asset was used in a scene generation."""
    pool = await get_pool()
    
    # Update usage count
    await pool.execute(
        """UPDATE reference_catalog 
           SET usage_count = usage_count + 1, 
               last_used_at = now(),
               updated_at = now()
           WHERE id=$1""",
        catalog_id,
    )
    
    # Record usage history
    await pool.execute(
        """INSERT INTO reference_catalog_usage (catalog_id, scene_id, purpose, used_at)
           VALUES ($1, $2, $3, now())""",
        catalog_id,
        used_in_scene_id,
        used_for_purpose,
    )


async def catalog_search(
    *,
    story_id: str,
    asset_types: list[str] | None = None,
    tags: list[str] | None = None,
    approval_status: str | None = None,
    source: str | None = None,
    character_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    include_usage_stats: bool = False,
) -> list[dict[str, Any]]:
    """
    Search the reference catalog with filtering.
    
    Args:
        story_id: Required - search within this story
        asset_types: Filter by asset types (e.g., ['character_ref', 'exit_frame'])
        tags: Filter by tags (AND logic - must have all specified tags)
        approval_status: Filter by approval status
        source: Filter by source ('user_upload', 'generated', 'catalog')
        character_id: Filter by character
        episode_id: Filter by episode
        scene_id: Filter by scene
        limit: Maximum results (default 50)
        offset: Pagination offset
        include_usage_stats: Include usage history in results
    
    Returns:
        List of matching catalog entries with metadata
    """
    pool = await get_pool()
    
    conditions = ["story_id = $1"]
    params = [story_id]
    param_idx = 2
    
    if asset_types:
        conditions.append(f"asset_type = ANY(${param_idx}::text[])")
        params.append(asset_types)
        param_idx += 1
    
    if tags:
        # Each tag must be present (AND logic)
        for tag in tags:
            conditions.append(f"${param_idx} = ANY(tags)")
            params.append(tag)
            param_idx += 1
    
    if approval_status:
        conditions.append(f"approval_status = ${param_idx}")
        params.append(approval_status)
        param_idx += 1
    
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1
    
    if character_id:
        conditions.append(f"character_id = ${param_idx}")
        params.append(character_id)
        param_idx += 1
    
    if episode_id:
        conditions.append(f"episode_id = ${param_idx}")
        params.append(episode_id)
        param_idx += 1
    
    if scene_id:
        conditions.append(f"scene_id = ${param_idx}")
        params.append(scene_id)
        param_idx += 1
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT * FROM reference_catalog
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])
    
    rows = await pool.fetch(query, *params)
    
    results = []
    for row in rows:
        entry = {
            "id": str(row["id"]),
            "story_id": str(row["story_id"]),
            "asset_type": row["asset_type"],
            "url": row["url"],
            "source": row["source"],
            "tags": row["tags"] or [],
            "metadata": row["metadata"] or {},
            "character_id": str(row["character_id"]) if row["character_id"] else None,
            "scene_id": str(row["scene_id"]) if row["scene_id"] else None,
            "episode_id": str(row["episode_id"]) if row["episode_id"] else None,
            "approval_status": row["approval_status"],
            "usage_count": row["usage_count"] or 0,
            "last_used_at": row["last_used_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        
        if include_usage_stats:
            usage_rows = await pool.fetch(
                """SELECT * FROM reference_catalog_usage 
                   WHERE catalog_id = $1 
                   ORDER BY used_at DESC 
                   LIMIT 10""",
                str(row["id"]),
            )
            entry["recent_usage"] = [
                {
                    "scene_id": str(u["scene_id"]),
                    "purpose": u["purpose"],
                    "used_at": u["used_at"],
                }
                for u in usage_rows
            ]
        
        results.append(entry)
    
    return results


async def get_character_references(
    *,
    story_id: str,
    character_id: str,
    approved_only: bool = True,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get character reference images from the catalog."""
    conditions = ["story_id = $1", "asset_type = $2"]
    params: list[Any] = [story_id, AssetType.CHARACTER_REF]
    
    if character_id:
        conditions.append("character_id = $3")
        params.append(character_id)
    
    if approved_only:
        conditions.append("approval_status = 'approved'")
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT * FROM reference_catalog
        WHERE {where_clause}
        ORDER BY usage_count DESC, created_at DESC
        LIMIT $3
    """
    
    rows = await pool.fetch(query, *params, limit)
    return [
        {
            "id": str(row["id"]),
            "url": row["url"],
            "character_id": str(row["character_id"]) if row["character_id"] else None,
            "tags": row["tags"] or [],
            "approval_status": row["approval_status"],
            "usage_count": row["usage_count"] or 0,
        }
        for row in rows
    ]


async def get_exit_frames(
    *,
    story_id: str,
    episode_id: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get exit frame images from the catalog."""
    conditions = ["story_id = $1", "asset_type = $2"]
    params: list[Any] = [story_id, AssetType.EXIT_FRAME]
    
    if episode_id:
        conditions.append("episode_id = $3")
        params.append(episode_id)
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT rc.*, s.scene_number
        FROM reference_catalog rc
        LEFT JOIN scenes s ON rc.scene_id = s.id
        WHERE {where_clause}
        ORDER BY s.scene_number DESC, rc.created_at DESC
        LIMIT $3
    """
    
    rows = await pool.fetch(query, *params, limit)
    return [
        {
            "id": str(row["id"]),
            "url": row["url"],
            "scene_id": str(row["scene_id"]) if row["scene_id"] else None,
            "scene_number": row["scene_number"],
            "tags": row["tags"] or [],
            "approval_status": row["approval_status"],
        }
        for row in rows
    ]


async def get_references_for_scene(
    *,
    story_id: str,
    scene_id: str,
    episode_id: str,
    character_ids: list[str] | None = None,
    previous_exit_frame: str | None = None,
    max_refs: int = 8,
) -> list[str]:
    """
    Get relevant reference URLs for scene generation.
    
    Prioritizes:
    1. Character references (first)
    2. Previous exit frame (if available and not already included)
    3. Scene references from same episode
    """
    pool = await get_pool()
    urls: list[str] = []
    
    # Get character references
    if character_ids:
        for char_id in character_ids[:4]:
            char_refs = await get_character_references(
                story_id=story_id,
                character_id=char_id,
                approved_only=True,
                limit=2,
            )
            for ref in char_refs:
                if ref["url"] and ref["url"] not in urls:
                    urls.append(ref["url"])
                    if len(urls) >= max_refs:
                        return urls
    
    # Add previous exit frame if available
    if previous_exit_frame and previous_exit_frame not in urls:
        urls.append(previous_exit_frame)
        if len(urls) >= max_refs:
            return urls
    
    # Get scene references from same episode
    if len(urls) < max_refs:
        scene_refs = await catalog_search(
            story_id=story_id,
            asset_types=[AssetType.SCENE_REF],
            episode_id=episode_id,
            approval_status=ApprovalStatus.APPROVED,
            limit=max_refs - len(urls),
        )
        for ref in scene_refs:
            if ref["url"] and ref["url"] not in urls:
                urls.append(ref["url"])
    
    return urls


async def bulk_index_scene_refs(
    *,
    story_id: str,
    episode_id: str,
    scene_id: str,
    scene_number: int,
    exit_frame_url: str,
    tags: list[str] | None = None,
) -> str:
    """Index a scene's exit frame as a reference for future scenes."""
    return await index_asset(
        story_id=story_id,
        asset_type=AssetType.EXIT_FRAME,
        url=exit_frame_url,
        source="generated",
        tags=tags or [f"episode_{episode_id}", f"scene_{scene_number}"],
        metadata={
            "scene_number": scene_number,
            "generated_at": datetime.utcnow().isoformat(),
        },
        scene_id=scene_id,
        episode_id=episode_id,
    )


# SQL migrations for catalog tables (run once during setup)
CATALOG_SCHEMA = """
-- Reference catalog table for indexing assets
CREATE TABLE IF NOT EXISTS reference_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL,
    asset_type TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    character_id UUID,
    scene_id UUID,
    episode_id UUID,
    approval_status TEXT DEFAULT 'pending',
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT fk_character FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL,
    CONSTRAINT fk_scene FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE SET NULL,
    CONSTRAINT fk_episode FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE SET NULL
);

-- Usage history for catalog entries
CREATE TABLE IF NOT EXISTS reference_catalog_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_id UUID NOT NULL REFERENCES reference_catalog(id) ON DELETE CASCADE,
    scene_id UUID,
    purpose TEXT,
    used_at TIMESTAMP DEFAULT now()
);

-- Indexes for efficient catalog searches
CREATE INDEX IF NOT EXISTS idx_catalog_story ON reference_catalog(story_id);
CREATE INDEX IF NOT EXISTS idx_catalog_asset_type ON reference_catalog(asset_type);
CREATE INDEX IF NOT EXISTS idx_catalog_character ON reference_catalog(character_id);
CREATE INDEX IF NOT EXISTS idx_catalog_scene ON reference_catalog(scene_id);
CREATE INDEX IF NOT EXISTS idx_catalog_approval ON reference_catalog(approval_status);
CREATE INDEX IF NOT EXISTS idx_catalog_usage_catalog ON reference_catalog_usage(catalog_id);
"""


async def ensure_catalog_tables() -> None:
    """Create catalog tables if they don't exist."""
    pool = await get_pool()
    for statement in CATALOG_SCHEMA.strip().split(";"):
        statement = statement.strip()
        if statement:
            await pool.execute(statement)


# ─── Scene Continuity Tracking ─────────────────────────────────────────────────

"""
Continuity tracking for scene-to-scene consistency.
Stores exit frame metadata (lighting, palette, camera state) for
automatic injection into next scene's generation.
"""

import base64
import io
from dataclasses import asdict, dataclass, field
from typing import Optional

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from storage.b2 import upload_bytes, build_key
    HAS_B2 = True
except ImportError:
    HAS_B2 = False


@dataclass
class ContinuityState:
    """Visual state at end of scene for continuity."""
    
    story_id: str
    episode_id: str
    scene_number: int
    
    # Exit frame
    exit_frame_url: Optional[str] = None
    
    # Color palette
    dominant_colors: list[str] = field(default_factory=list)  # Hex colors
    
    # Lighting
    lighting_type: str = "natural"  # natural, golden_hour, dramatic, neon
    color_temperature: str = "neutral"  # warm, neutral, cool
    
    # Camera state
    camera_angle: str = "eye_level"
    camera_motion: str = "static"
    
    # Scene info
    mood: str = ""
    style: str = ""
    model: str = ""
    seed: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> ContinuityState:
        return cls(**data)


@dataclass  
class SceneContext:
    """Context for next scene generation with continuity."""
    
    previous_exit_frame_url: Optional[str] = None
    previous_lighting: str = "natural"
    previous_color_temp: str = "neutral"
    previous_camera_angle: str = "eye_level"
    previous_camera_motion: str = "static"
    previous_dominant_colors: list[str] = field(default_factory=list)
    previous_mood: str = ""
    
    # Generated continuity guidance for prompt
    continuity_note: str = ""


def extract_color_palette(image_bytes: bytes, num_colors: int = 5) -> list[str]:
    """Extract dominant colors from image as hex strings."""
    if not HAS_PIL:
        return []
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img = img.resize((100, 100))
        
        pixels = list(img.getdata())
        color_counts: dict[tuple, int] = {}
        
        for r, g, b in pixels:
            r_q = (r // 32) * 32
            g_q = (g // 32) * 32
            b_q = (b // 32) * 32
            color_counts[(r_q, g_q, b_q)] = color_counts.get((r_q, g_q, b_q), 0) + 1
        
        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        
        hex_colors = []
        for (r, g, b), _ in sorted_colors[:num_colors]:
            hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
        
        return hex_colors
        
    except Exception as e:
        print(f"[catalog] Color extraction failed: {e}")
        return []


def infer_lighting_from_colors(colors: list[str]) -> str:
    """Infer lighting type from dominant colors."""
    if not colors:
        return "natural"
    
    try:
        r_avg, g_avg, b_avg = 0, 0, 0
        count = 0
        
        for hex_color in colors:
            hex_color = hex_color.lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r_avg += r
            g_avg += g
            b_avg += b
            count += 1
        
        if count == 0:
            return "natural"
        
        r_avg //= count
        g_avg //= count
        b_avg //= count
        
        # Warm tones = golden hour
        if r_avg > g_avg > b_avg and r_avg - b_avg > 30:
            return "golden_hour"
        
        # Cool tones = dramatic/night
        if b_avg > r_avg and b_avg - r_avg > 30:
            return "dramatic"
        
        # High saturation = neon
        max_val = max(r_avg, g_avg, b_avg)
        min_val = min(r_avg, g_avg, b_avg)
        saturation = (max_val - min_val) / max_val if max_val > 0 else 0
        
        if saturation > 0.7 and max_val > 150:
            return "neon"
        
        return "natural"
        
    except Exception:
        return "natural"


async def create_continuity_state(
    story_id: str,
    episode_id: str,
    scene_number: int,
    exit_frame_bytes: bytes,
    prompt: str = "",
    model: str = "",
    seed: int = 0,
    mood: str = "",
    style: str = "",
    camera_motion: str = "static",
    camera_angle: str = "eye_level",
) -> ContinuityState:
    """Create continuity state from exit frame.
    
    Extracts color palette, infers lighting, uploads to B2.
    """
    # Extract color palette
    dominant_colors = extract_color_palette(exit_frame_bytes)
    
    # Infer lighting
    lighting_type = infer_lighting_from_colors(dominant_colors)
    
    # Upload exit frame to B2
    exit_frame_url = None
    if HAS_B2:
        try:
            key = build_key(story_id, "episodes", episode_id, "scenes", f"scene_{scene_number}_exit.png")
            exit_frame_url = upload_bytes(exit_frame_bytes, key, "image/png")
        except Exception as e:
            print(f"[catalog] B2 upload failed: {e}")
    
    return ContinuityState(
        story_id=story_id,
        episode_id=episode_id,
        scene_number=scene_number,
        exit_frame_url=exit_frame_url,
        dominant_colors=dominant_colors,
        lighting_type=lighting_type,
        color_temperature="warm" if "golden" in lighting_type else "neutral",
        camera_angle=camera_angle,
        camera_motion=camera_motion,
        mood=mood,
        style=style,
        model=model,
        seed=seed,
    )


def build_scene_context(
    previous: Optional[ContinuityState],
) -> SceneContext:
    """Build continuity context for next scene from previous state."""
    if not previous:
        return SceneContext()
    
    context = SceneContext(
        previous_exit_frame_url=previous.exit_frame_url,
        previous_lighting=previous.lighting_type,
        previous_color_temp=previous.color_temperature,
        previous_camera_angle=previous.camera_angle,
        previous_camera_motion=previous.camera_motion,
        previous_dominant_colors=previous.dominant_colors,
        previous_mood=previous.mood,
    )
    
    # Build continuity guidance
    continuity_parts = []
    
    if previous.exit_frame_url:
        continuity_parts.append("Maintain visual continuity from the previous scene.")
    
    if previous.lighting_type != "natural":
        continuity_parts.append(f"Continue the {previous.lighting_type} lighting style.")
    
    if previous.camera_motion != "static":
        continuity_parts.append(f"Camera continues with {previous.camera_motion} movement.")
    
    if previous.dominant_colors:
        colors_str = ", ".join(previous.dominant_colors[:3])
        continuity_parts.append(f"Color palette: {colors_str}.")
    
    context.continuity_note = " ".join(continuity_parts)
    
    return context


def inject_continuity_into_prompt(
    base_prompt: str,
    context: SceneContext,
) -> str:
    """Inject continuity guidance into scene prompt."""
    if not context.continuity_note:
        return base_prompt
    
    return base_prompt.strip() + f"\n\n{context.continuity_note}"
