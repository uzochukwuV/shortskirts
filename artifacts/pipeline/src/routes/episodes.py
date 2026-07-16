import json
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import EpisodeResponse, SceneResponse
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/episodes", tags=["episodes"])


async def _get_scenes(episode_id: str) -> list[SceneResponse]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM scenes WHERE episode_id=$1 ORDER BY scene_number ASC",
        episode_id,
    )
    result = []
    for r in rows:
        metadata = r["generation_metadata"]
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        metadata = metadata or {}
        result.append(SceneResponse(
            id=str(r["id"]),
            episode_id=str(r["episode_id"]),
            scene_number=r["scene_number"],
            prompt=r["prompt"],
            clip_url=r["clip_url"],
            exit_frame_url=r["exit_frame_url"],
            duration=r["duration"],
            status=r["status"],
            approval_status=r.get("approval_status", "pending"),
            locked=r.get("locked", False),
            regeneration_count=r.get("regeneration_count", 0),
            created_at=r["created_at"],
            title=metadata.get("title") or f"Scene {r['scene_number']}",
            description=metadata.get("description", ""),
            visual_prompt=metadata.get("visual_prompt") or r["prompt"],
            mood=metadata.get("mood", ""),
            location=metadata.get("location", ""),
        ))
    return result


@router.get("/story/{story_id}", response_model=list[EpisodeResponse])
async def list_episodes(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    story_row = await pool.fetchrow(
        "SELECT episode_plan FROM stories WHERE id=$1 AND owner_id=$2",
        story_id,
        user_id(user),
    )
    if not story_row:
        raise HTTPException(status_code=404, detail="Story not found")

    ep_plan_map: dict = {}
    plan = story_row["episode_plan"]
    if isinstance(plan, str):
        plan = json.loads(plan)
    if plan:
        for ep in plan.get("episodes", []):
            ep_plan_map[ep["episode_number"]] = ep

    rows = await pool.fetch(
        "SELECT * FROM episodes WHERE story_id=$1 ORDER BY episode_number ASC",
        story_id,
    )
    result = []
    for row in rows:
        scenes = await _get_scenes(str(row["id"]))
        ep_num = row["episode_number"]
        result.append(EpisodeResponse(
            id=str(row["id"]),
            story_id=str(row["story_id"]),
            episode_number=ep_num,
            title=row["title"],
            summary=ep_plan_map.get(ep_num, {}).get("summary", ""),
            assembled_video_url=row["assembled_video_url"],
            manifest_url=row["manifest_url"],
            status=row["status"],
            scenes=scenes,
            created_at=row["created_at"],
        ))
    return result


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT e.* FROM episodes e
           JOIN stories s ON s.id = e.story_id
           WHERE e.id=$1 AND s.owner_id=$2""",
        episode_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Episode not found")
    scenes = await _get_scenes(episode_id)
    return EpisodeResponse(
        id=str(row["id"]),
        story_id=str(row["story_id"]),
        episode_number=row["episode_number"],
        title=row["title"],
        assembled_video_url=row["assembled_video_url"],
        manifest_url=row["manifest_url"],
        status=row["status"],
        scenes=scenes,
        created_at=row["created_at"],
    )
