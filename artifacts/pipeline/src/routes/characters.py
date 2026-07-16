import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from db.connection import get_pool
from models.story import CharacterCreate, CharacterResponse, GenerationJobResponse
from pipeline.character_gen import generate_character_references, get_character_embedding
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/characters", tags=["characters"])


def _row_to_response(row) -> CharacterResponse:
    refs = row["ref_image_urls"]
    if isinstance(refs, str):
        refs = json.loads(refs)
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


@router.post("", response_model=CharacterResponse)
async def create_character(
    body: CharacterCreate,
    background_tasks: BackgroundTasks,
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
    char_dict = {
        "name": body.name,
        "description": body.description,
        "role": body.role,
        "personality": body.personality,
        "appearance": body.appearance,
    }
    background_tasks.add_task(_generate_refs_bg, body.story_id, character_id, char_dict, story["style"])
    return _row_to_response(row)


async def _generate_refs_bg(story_id: str, character_id: str, character: dict, style: str):
    pool = await get_pool()
    try:
        urls = await generate_character_references(story_id, character_id, character, style)
        embedding = get_character_embedding(character)
        await pool.execute(
            """UPDATE characters SET ref_image_urls=$1::jsonb, embedding=$2::jsonb, updated_at=now()
               WHERE id=$3""",
            json.dumps(urls),
            json.dumps(embedding),
            character_id,
        )
    except Exception as e:
        print(f"[characters] Ref generation failed: {e}")


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
    return _row_to_response(row)


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


@router.post("/{character_id}/regenerate-refs", response_model=GenerationJobResponse)
async def regenerate_character_refs(
    character_id: str,
    background_tasks: BackgroundTasks,
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

    char_dict = {
        "name": char["name"],
        "description": char["description"],
        "role": char["role"],
        "personality": char["personality"],
        "appearance": char["appearance"],
    }
    background_tasks.add_task(
        _regen_refs_bg,
        character_id,
        str(char["story_id"]),
        char_dict,
        story["style"],
        job_id,
    )

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


async def _regen_refs_bg(character_id: str, story_id: str, char_dict: dict, style: str, job_id: str):
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
        await _upd(status="running", started_at=datetime.utcnow(), current_step="Generating new ref images")
        urls = await generate_character_references(story_id, character_id, char_dict, style)
        embedding = get_character_embedding(char_dict)
        await pool.execute(
            """UPDATE characters
               SET ref_image_urls=$1::jsonb, embedding=$2::jsonb,
                   approval_status='pending', updated_at=now()
               WHERE id=$3""",
            json.dumps(urls),
            json.dumps(embedding),
            character_id,
        )
        await _upd(
            status="completed",
            progress=1,
            current_step="Done",
            completed_at=datetime.utcnow(),
            result={"character_id": character_id, "ref_count": len(urls)},
        )
    except Exception as e:
        print(f"[characters] Regen refs failed: {e}")
        await _upd(
            status="failed",
            current_step=f"Failed: {str(e)[:200]}",
            completed_at=datetime.utcnow(),
        )
