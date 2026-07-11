import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from db.connection import get_pool
from models.story import CharacterCreate, CharacterResponse, GenerationJobResponse
from pipeline.character_gen import generate_character_references, get_character_embedding

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


# ── Create character + trigger ref generation in background ──────────────────

@router.post("", response_model=CharacterResponse)
async def create_character(body: CharacterCreate, background_tasks: BackgroundTasks):
    pool = await get_pool()
    story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", body.story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    row = await pool.fetchrow(
        """INSERT INTO characters
           (story_id, name, description, role, personality, appearance)
           VALUES ($1,$2,$3,$4,$5,$6) RETURNING *""",
        body.story_id, body.name, body.description, body.role,
        body.personality, body.appearance,
    )
    character_id = str(row["id"])
    char_dict = {"name": body.name, "description": body.description, "role": body.role,
                 "personality": body.personality, "appearance": body.appearance}

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
            json.dumps(urls), json.dumps(embedding), character_id,
        )
    except Exception as e:
        print(f"[characters] Ref generation failed: {e}")


# ── List characters ───────────────────────────────────────────────────────────

@router.get("/story/{story_id}", response_model=list[CharacterResponse])
async def list_characters(story_id: str):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM characters WHERE story_id=$1 ORDER BY created_at ASC", story_id
    )
    return [_row_to_response(r) for r in rows]


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM characters WHERE id=$1", character_id)
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
    return _row_to_response(row)


# ── Approve character (approve ref images before scene generation) ────────────

@router.put("/{character_id}/approve", response_model=CharacterResponse)
async def approve_character(character_id: str):
    """Human gate: approve character reference images."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE characters
           SET approval_status='approved', approved_at=now(), updated_at=now()
           WHERE id=$1 RETURNING *""",
        character_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
    return _row_to_response(row)


# ── Lock character (prevent further ref regeneration) ────────────────────────

@router.put("/{character_id}/lock", response_model=CharacterResponse)
async def lock_character(character_id: str):
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE characters SET locked=true, updated_at=now() WHERE id=$1 RETURNING *",
        character_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
    return _row_to_response(row)


# ── Regenerate character ref images ──────────────────────────────────────────

@router.post("/{character_id}/regenerate-refs", response_model=GenerationJobResponse)
async def regenerate_character_refs(character_id: str, background_tasks: BackgroundTasks):
    """Regenerate reference images for a single character without rerunning the pipeline."""
    pool = await get_pool()

    char = await pool.fetchrow("SELECT * FROM characters WHERE id=$1", character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    if char.get("locked"):
        raise HTTPException(status_code=409, detail="Character is locked — unlock before regenerating")

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
        "name": char["name"], "description": char["description"],
        "role": char["role"], "personality": char["personality"],
        "appearance": char["appearance"],
    }
    background_tasks.add_task(
        _regen_refs_bg, character_id, str(char["story_id"]), char_dict,
        story["style"], job_id,
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


async def _regen_refs_bg(
    character_id: str, story_id: str,
    char_dict: dict, style: str, job_id: str,
):
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
            f"UPDATE generation_jobs SET {','.join(fields)} WHERE id=${len(vals)}", *vals,
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
            json.dumps(urls), json.dumps(embedding), character_id,
        )

        await _upd(
            status="completed", progress=1, current_step="Done",
            completed_at=datetime.utcnow(),
            result={"character_id": character_id, "ref_count": len(urls)},
        )

    except Exception as e:
        print(f"[characters] Regen refs failed: {e}")
        await _upd(
            status="failed", current_step=f"Failed: {str(e)[:200]}",
            completed_at=datetime.utcnow(),
        )
