from fastapi import APIRouter, Depends

from auth import get_current_user, user_id
from db.connection import get_pool
from models.story import GalleryItemResponse

router = APIRouter(prefix="/pipeline/gallery", tags=["gallery"])


async def _fetch_gallery_items(pool, owner_id: str | None = None, public: bool = False):
    if public:
        owner_clause = ""
        params = []
        scene_status_clause = "AND sc.status IN ('completed', 'ready')"
        episode_status_clause = "AND e.status IN ('completed', 'ready')"
    else:
        owner_clause = "AND s.owner_id = $1"
        params = [owner_id]
        scene_status_clause = ""
        episode_status_clause = ""

    rows = await pool.fetch(
        f"""
        WITH scene_items AS (
            SELECT
                'scene'::text AS kind,
                sc.id,
                s.id AS story_id,
                s.title AS story_title,
                e.id AS episode_id,
                e.episode_number,
                sc.id AS scene_id,
                sc.scene_number,
                COALESCE(sc.generation_metadata->>'title', 'Scene ' || sc.scene_number::text) AS title,
                COALESCE(sc.generation_metadata->>'description', sc.prompt) AS summary,
                COALESCE(sc.image_url, sc.clip_url) AS media_url,
                COALESCE(sc.generation_metadata->>'media_kind', CASE WHEN sc.image_url IS NOT NULL THEN 'image' ELSE 'video' END) AS media_kind,
                sc.duration,
                COALESCE(sc.updated_at, sc.created_at) AS sort_at,
                sc.created_at
            FROM scenes sc
            JOIN episodes e ON e.id = sc.episode_id
            JOIN stories s ON s.id = e.story_id
            WHERE COALESCE(sc.image_url, sc.clip_url) IS NOT NULL {owner_clause} {scene_status_clause}
        ),
        episode_items AS (
            SELECT
                'episode'::text AS kind,
                e.id,
                s.id AS story_id,
                s.title AS story_title,
                e.id AS episode_id,
                e.episode_number,
                NULL::uuid AS scene_id,
                NULL::int AS scene_number,
                e.title AS title,
                e.summary AS summary,
                e.assembled_video_url AS media_url,
                'video'::text AS media_kind,
                NULL::float AS duration,
                COALESCE(e.updated_at, e.created_at) AS sort_at,
                e.created_at
            FROM episodes e
            JOIN stories s ON s.id = e.story_id
            WHERE e.assembled_video_url IS NOT NULL {owner_clause} {episode_status_clause}
        )
        SELECT * FROM (
            SELECT * FROM scene_items
            UNION ALL
            SELECT * FROM episode_items
        ) items
        ORDER BY sort_at DESC
        LIMIT 12
        """,
        *params,
    )
    return [
        GalleryItemResponse(
            id=str(row["id"]),
            kind=row["kind"],
            story_id=str(row["story_id"]),
            story_title=row["story_title"],
            episode_id=str(row["episode_id"]),
            episode_number=row["episode_number"],
            scene_id=str(row["scene_id"]) if row["scene_id"] else None,
            scene_number=row["scene_number"],
            title=row["title"],
            summary=row["summary"],
            media_url=row["media_url"],
            media_kind=row.get("media_kind"),
            duration=row["duration"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("", response_model=list[GalleryItemResponse])
async def list_gallery_items(user=Depends(get_current_user)):
    pool = await get_pool()
    return await _fetch_gallery_items(pool, owner_id=user_id(user), public=False)


@router.get("/public", response_model=list[GalleryItemResponse])
async def list_public_gallery_items():
    pool = await get_pool()
    return await _fetch_gallery_items(pool, public=True)
