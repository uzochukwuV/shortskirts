import json
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import CharacterCreate, CharacterResponse, CharacterUpdate, GenerationJobResponse
from job_queue import enqueue_job, WORKLOAD_MEDIA
from pipeline.history import record_story_history
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/characters", tags=["characters"])


def _row_to_response(row) -> CharacterResponse:
    refs = row["ref_image_urls"]
    if isinstance(refs, str):
        refs = json.loads(refs)
    scene_ids = row.get("scene_ids") or []
    if isinstance(scene_ids, str):
        try:
            scene_ids = json.loads(scene_ids)
        except Exception:
            scene_ids = []
    return CharacterResponse(
        id=str(row["id"]),
        story_id=str(row["story_id"]),
        name=row["name"],
        description=row["description"],
        role=row["role"],
        personality=row["personality"],
        appearance=row["appearance"],
        ref_image_urls=refs or [],
        approval_status=row.get("approval_status", "pending"),
        locked=row.get("locked", False),
        scene_ids=[str(scene_id) for scene_id in scene_ids],
        created_at=row["created_at"],
    )


async def _get_character_for_owner(pool, character_id: str, owner_id: str):
    return await pool.fetchrow(
        """SELECT c.* FROM characters c
           JOIN stories s ON s.id = c.story_id
           WHERE c.id=$1 AND s.owner_id=$2""",
        character_id,
        owner_id,
    )


async def _load_character_scene_ids(pool, character_id: str) -> list[str]:
    rows = await pool.fetch(
        "SELECT scene_id FROM scene_characters WHERE character_id=$1 ORDER BY is_primary DESC, scene_id ASC",
        character_id,
    )
    return [str(r["scene_id"]) for r in rows]


async def _attach_scene_history(pool, story_id: str, character_row, event_type: str, payload: dict | None = None):
    story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
    if story:
        await record_story_history(
            pool,
            story=story,
            event_type=event_type,
            payload=payload or {},
        )


@router.post("", response_model=CharacterResponse)
async def create_character(
    body: CharacterCreate,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    owner_id = user_id(user)
    story = await pool.fetchrow(
        "SELECT * FROM stories WHERE id=$1 AND owner_id=$2",
        body.story_id,
        owner_id,
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    row = await pool.fetchrow(
        """INSERT INTO characters
           (story_id, name, description, role, personality, appearance)
           VALUES ($1,$2,$3,$4,$5,$6)
           ON CONFLICT (story_id, name) DO UPDATE SET
             description=excluded.description,
             role=excluded.role,
             personality=excluded.personality,
             appearance=excluded.appearance,
             updated_at=now()
           RETURNING *""",
        body.story_id,
        body.name,
        body.description,
        body.role,
        body.personality,
        body.appearance,
    )
    character_id = str(row["id"])
    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('character', $1, 'pending', 1, 'Queued', 'char_refs')
           RETURNING *""",
        character_id,
    )
    await enqueue_job(str(job_row["id"]), workload=WORKLOAD_MEDIA)
    return _row_to_response(row)


@router.get("/story/{story_id}", response_model=list[CharacterResponse])
async def list_characters(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT c.* FROM characters c
           JOIN stories s ON s.id = c.story_id
           WHERE c.story_id=$1 AND s.owner_id=$2
           ORDER BY c.created_at ASC""",
        story_id,
        user_id(user),
    )
    return [_row_to_response(r) for r in rows]


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await _get_character_for_owner(pool, character_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
    row = dict(row)
    row["scene_ids"] = await _load_character_scene_ids(pool, character_id)
    return _row_to_response(row)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    body: CharacterUpdate,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    char = await _get_character_for_owner(pool, character_id, user_id(user))
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")

    updated = await pool.fetchrow(
        """
        UPDATE characters
           SET name=COALESCE($2, name),
               description=COALESCE($3, description),
               role=COALESCE($4, role),
               personality=COALESCE($5, personality),
               appearance=COALESCE($6, appearance),
               ref_image_urls=CASE WHEN $7::jsonb IS NULL THEN ref_image_urls ELSE $7::jsonb END,
               approval_status=COALESCE($8, approval_status),
               locked=COALESCE($9, locked),
               updated_at=now()
         WHERE id=$1
         RETURNING *
        """,
        character_id,
        body.name,
        body.description,
        body.role,
        body.personality,
        body.appearance,
        json.dumps([u for u in body.ref_image_urls if u]) if body.ref_image_urls else None,
        body.approval_status,
        body.locked,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Character not found")
    await _attach_scene_history(pool, str(updated["story_id"]), updated, "character_updated", {
        "character_id": character_id,
    })
    updated = dict(updated)
    updated["scene_ids"] = await _load_character_scene_ids(pool, character_id)
    return _row_to_response(updated)


@router.put("/{character_id}/reject", response_model=CharacterResponse)
async def reject_character(character_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _get_character_for_owner(pool, character_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Character not found")
    row = await pool.fetchrow(
        """UPDATE characters
           SET approval_status='rejected', approved_at=NULL, locked=false, updated_at=now()
           WHERE id=$1 RETURNING *""",
        character_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
    await _attach_scene_history(pool, str(row["story_id"]), row, "character_rejected", {
        "character_id": character_id,
    })
    row = dict(row)
    row["scene_ids"] = await _load_character_scene_ids(pool, character_id)
    return _row_to_response(row)


@router.put("/{character_id}/references", response_model=CharacterResponse)
async def update_character_references(
    character_id: str,
    body: CharacterUpdate,
    user=Depends(get_current_user),
):
    return await update_character(character_id, body, user)


@router.put("/{character_id}/approve", response_model=CharacterResponse)
async def approve_character(character_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _get_character_for_owner(pool, character_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Character not found")
    row = await pool.fetchrow(
        """UPDATE characters
           SET approval_status='approved', approved_at=now(), updated_at=now()
           WHERE id=$1 RETURNING *""",
        character_id,
    )
    return _row_to_response(row)


@router.put("/{character_id}/lock", response_model=CharacterResponse)
async def lock_character(character_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _get_character_for_owner(pool, character_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Character not found")
    row = await pool.fetchrow(
        "UPDATE characters SET locked=true, updated_at=now() WHERE id=$1 RETURNING *",
        character_id,
    )
    return _row_to_response(row)


@router.put("/{character_id}/unlock", response_model=CharacterResponse)
async def unlock_character(character_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await _get_character_for_owner(pool, character_id, user_id(user)):
        raise HTTPException(status_code=404, detail="Character not found")
    row = await pool.fetchrow(
        "UPDATE characters SET locked=false, updated_at=now() WHERE id=$1 RETURNING *",
        character_id,
    )
    return _row_to_response(row)


@router.delete("/{character_id}", status_code=204)
async def delete_character(character_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    char = await _get_character_for_owner(pool, character_id, user_id(user))
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    if char.get("locked"):
        raise HTTPException(status_code=409, detail="Character is locked and cannot be deleted")
    await pool.execute("DELETE FROM characters WHERE id=$1", character_id)
    return None


@router.post("/{character_id}/regenerate-refs", response_model=GenerationJobResponse)
async def regenerate_character_refs(
    character_id: str,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    char = await _get_character_for_owner(pool, character_id, user_id(user))
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    if char.get("locked"):
        raise HTTPException(status_code=409, detail="Character is locked; unlock before regenerating")

    story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", str(char["story_id"]))
    if not story:
        raise HTTPException(status_code=404, detail="Parent story not found")

    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('character',$1,'pending',1,'Queued','char_refs')
           RETURNING *""",
        character_id,
    )
    job_id = str(job_row["id"])
    await enqueue_job(job_id, workload=WORKLOAD_MEDIA)

    return GenerationJobResponse(
        id=job_id,
        entity_type="character",
        entity_id=character_id,
        status="pending",
        progress=0,
        total_steps=1,
        current_step="Queued",
        job_type="char_refs",
        created_at=job_row["created_at"],
    )
