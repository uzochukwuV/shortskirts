import json
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from db.connection import get_pool
from models.story import CharacterCreate, CharacterResponse, GenerationJobResponse
from pipeline.character_gen import generate_character_references, get_character_embedding
from datetime import datetime

router = APIRouter(prefix="/pipeline/characters", tags=["characters"])


async def _generate_refs_bg(story_id: str, character_id: str, character: dict, style: str):
    pool = await get_pool()
    try:
        urls = await generate_character_references(story_id, character_id, character, style)
        embedding = await get_character_embedding(character)

        await pool.execute(
            """UPDATE characters SET ref_image_urls=$1::jsonb, embedding=$2::jsonb
               WHERE id=$3""",
            json.dumps(urls),
            json.dumps(embedding),
            character_id,
        )
    except Exception as e:
        print(f"[characters] Background ref generation failed: {e}")


@router.post("", response_model=CharacterResponse)
async def create_character(body: CharacterCreate, background_tasks: BackgroundTasks):
    pool = await get_pool()

    story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", body.story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    row = await pool.fetchrow(
        """INSERT INTO characters (story_id, name, description, role, personality, appearance)
           VALUES ($1,$2,$3,$4,$5,$6) RETURNING *""",
        body.story_id, body.name, body.description, body.role,
        body.personality, body.appearance,
    )
    character_id = str(row["id"])

    char_dict = {
        "name": body.name,
        "description": body.description,
        "role": body.role,
        "personality": body.personality,
        "appearance": body.appearance,
    }

    background_tasks.add_task(
        _generate_refs_bg, body.story_id, character_id, char_dict, story["style"]
    )

    refs = row["ref_image_urls"]
    if isinstance(refs, str):
        refs = json.loads(refs)

    return CharacterResponse(
        id=character_id,
        story_id=str(row["story_id"]),
        name=row["name"],
        description=row["description"],
        role=row["role"],
        personality=row["personality"],
        appearance=row["appearance"],
        ref_image_urls=refs or [],
        created_at=row["created_at"],
    )


@router.get("/story/{story_id}", response_model=list[CharacterResponse])
async def list_characters(story_id: str):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM characters WHERE story_id=$1 ORDER BY created_at ASC", story_id
    )
    result = []
    for row in rows:
        refs = row["ref_image_urls"]
        if isinstance(refs, str):
            refs = json.loads(refs)
        result.append(CharacterResponse(
            id=str(row["id"]),
            story_id=str(row["story_id"]),
            name=row["name"],
            description=row["description"],
            role=row["role"],
            personality=row["personality"],
            appearance=row["appearance"],
            ref_image_urls=refs or [],
            created_at=row["created_at"],
        ))
    return result


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM characters WHERE id=$1", character_id)
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
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
        created_at=row["created_at"],
    )
