"""
Scene routes — granular regeneration and approval gates.

Key endpoints:
  POST /pipeline/scenes/{id}/regenerate    — regenerate this scene's video clip in background
  PUT  /pipeline/scenes/{id}/approve       — approve this scene (human gate)
  PUT  /pipeline/scenes/{id}/reject        — reject / request redo (resets approval)
  PUT  /pipeline/scenes/{id}/lock          — lock scene so it cannot be regenerated
  GET  /pipeline/scenes/{id}               — get scene detail
"""
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from db.connection import get_pool
from models.story import SceneResponse, GenerationJobResponse
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/scenes", tags=["scenes"])
async def _scene_belongs_to_owner(pool, scene_id: str, owner_id: str) -> bool:
    return bool(await pool.fetchval(
        """SELECT 1 FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1 AND s.owner_id=$2""",
        scene_id,
        owner_id,
    ))


# ─── Helper ───────────────────────────────────────────────────────────────────

def _row_to_scene(r, metadata: dict | None = None) -> SceneResponse:
    if metadata is None:
        metadata = r.get("generation_metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

    return SceneResponse(
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
    )


# ─── Get scene ────────────────────────────────────────────────────────────────

@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    return _row_to_scene(row)


# ─── Approve scene ────────────────────────────────────────────────────────────

@router.put("/{scene_id}/approve", response_model=SceneResponse)
async def approve_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow(
        """UPDATE scenes
           SET approval_status='approved', approved_at=now(), updated_at=now()
           WHERE id=$1 RETURNING *""",
        scene_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    return _row_to_scene(row)


# ─── Reject scene ─────────────────────────────────────────────────────────────

@router.put("/{scene_id}/reject", response_model=SceneResponse)
async def reject_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow(
        """UPDATE scenes
           SET approval_status='rejected', approved_at=NULL, updated_at=now()
           WHERE id=$1 RETURNING *""",
        scene_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    return _row_to_scene(row)


# ─── Lock scene ───────────────────────────────────────────────────────────────

@router.put("/{scene_id}/lock", response_model=SceneResponse)
async def lock_scene(scene_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")
    row = await pool.fetchrow(
        "UPDATE scenes SET locked=true, updated_at=now() WHERE id=$1 RETURNING *",
        scene_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scene not found")
    return _row_to_scene(row)


# ─── Regenerate scene ────────────────────────────────────────────────────────

@router.post("/{scene_id}/regenerate", response_model=GenerationJobResponse)
async def regenerate_scene(scene_id: str, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _scene_belongs_to_owner(pool, scene_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Scene not found")

    scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    if scene.get("locked"):
        raise HTTPException(status_code=409, detail="Scene is locked and cannot be regenerated")

    if scene.get("status") == "running":
        raise HTTPException(status_code=409, detail="Scene generation already in progress")

    # Create a tracking job
    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('scene', $1, 'pending', 1, 'Queued for regeneration', 'scene_regen')
           RETURNING *""",
        scene_id,
    )
    job_id = str(job_row["id"])

    await pool.execute(
        "UPDATE scenes SET status='running', approval_status='pending', updated_at=now() WHERE id=$1",
        scene_id,
    )

    background_tasks.add_task(_regen_scene_bg, scene_id, job_id)

    return GenerationJobResponse(
        id=job_id,
        entity_type="scene",
        entity_id=scene_id,
        status="pending",
        progress=0,
        total_steps=1,
        current_step="Queued for regeneration",
        job_type="scene_regen",
        created_at=job_row["created_at"],
    )


async def _regen_scene_bg(scene_id: str, job_id: str):
    """Background task: re-generate a single scene clip."""
    from pipeline.scene_gen import generate_scene_clip
    from pipeline.story_agent import build_scene_prompt

    pool = await get_pool()

    async def _upd(**kw):
        fields, vals = [], []
        for i, (k, v) in enumerate(kw.items(), 1):
            if k == "result" and isinstance(v, dict):
                fields.append(f"{k}=${i}::jsonb")
                vals.append(json.dumps(v))
            else:
                fields.append(f"{k}=${i}")
                vals.append(v)
        vals.append(job_id)
        await pool.execute(
            f"UPDATE generation_jobs SET {','.join(fields)} WHERE id=${len(vals)}",
            *vals,
        )

    try:
        await _upd(status="running", started_at=datetime.utcnow(), current_step="Loading context")

        scene = await pool.fetchrow("SELECT * FROM scenes WHERE id=$1", scene_id)
        episode = await pool.fetchrow("SELECT * FROM episodes WHERE id=$1", scene["episode_id"])
        story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", episode["story_id"])

        plan = story["episode_plan"]
        if isinstance(plan, str):
            plan = json.loads(plan)

        # Find the scene plan in the episode plan
        ep_num = episode["episode_number"]
        scene_num = scene["scene_number"]
        scene_plan = {}
        for ep in plan.get("episodes", []):
            if ep["episode_number"] == ep_num:
                for sc in ep.get("scenes", []):
                    if sc["scene_number"] == scene_num:
                        scene_plan = sc
                        break
                break

        # Restore from generation_metadata if scene_plan not in episode plan
        if not scene_plan:
            meta = scene["generation_metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta) if meta else {}
            scene_plan = {
                "scene_number": scene_num,
                "title": (meta or {}).get("title", f"Scene {scene_num}"),
                "description": (meta or {}).get("description", ""),
                "visual_prompt": scene["prompt"],
                "mood": (meta or {}).get("mood", ""),
                "location": (meta or {}).get("location", ""),
                "action": (meta or {}).get("action", ""),
                "characters_present": (meta or {}).get("characters_present", []),
            }

        # Load character refs
        characters = await pool.fetch(
            "SELECT * FROM characters WHERE story_id=$1", str(story["id"])
        )
        char_map = {r["name"]: dict(r) for r in characters}
        char_refs = []
        for cname in scene_plan.get("characters_present", []):
            char = char_map.get(cname)
            if char:
                refs = char.get("ref_image_urls") or []
                if isinstance(refs, str):
                    refs = json.loads(refs)
                char_refs.extend(refs)
        char_refs = char_refs[:4]

        await _upd(current_step="Generating new video clip")

        result = await generate_scene_clip(
            story_id=str(story["id"]),
            episode_id=str(episode["id"]),
            scene=scene_plan,
            story_context=plan,
            character_refs=char_refs,
            previous_exit_frame_url=None,   # no bridging on regen
            previous_scene_summary="",
            style=story["style"],
        )

        # Preserve existing metadata and merge new result
        existing_meta = scene["generation_metadata"]
        if isinstance(existing_meta, str):
            existing_meta = json.loads(existing_meta) if existing_meta else {}
        merged = {**(existing_meta or {}), "visual_prompt": result["prompt"], "refs_used": result.get("refs_used", 0)}

        regen_count = (scene.get("regeneration_count") or 0) + 1
        await pool.execute(
            """UPDATE scenes SET clip_url=$1, exit_frame_url=$2, duration=$3,
               status='completed', approval_status='pending',
               generation_metadata=$4::jsonb, regeneration_count=$5, updated_at=now()
               WHERE id=$6""",
            result["clip_url"], result.get("exit_frame_url"),
            result.get("duration", 5.0), json.dumps(merged), regen_count, scene_id,
        )

        await _upd(
            status="completed", progress=1, current_step="Done",
            completed_at=datetime.utcnow(), result={"scene_id": scene_id, "clip_url": result["clip_url"]},
        )

    except Exception as e:
        print(f"[scenes] Regen failed for {scene_id}: {e}")
        await pool.execute("UPDATE scenes SET status='failed', updated_at=now() WHERE id=$1", scene_id)
        await _upd(status="failed", current_step=f"Failed: {str(e)[:200]}", completed_at=datetime.utcnow())
