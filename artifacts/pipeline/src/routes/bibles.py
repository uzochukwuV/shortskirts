"""
Bible routes — persistent brand/character/world/campaign memory.

Each bible is attached to a story and injected into the LLM prompt at plan-generation time,
ensuring every scene respects the brand's rules, character designs, and visual motifs.
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from db.connection import get_pool
from models.story import BibleCreate, BibleResponse

router = APIRouter(prefix="/pipeline/bibles", tags=["bibles"])


def _row_to_response(row) -> BibleResponse:
    content = row["content"]
    if isinstance(content, str):
        content = json.loads(content)
    return BibleResponse(
        id=str(row["id"]),
        story_id=str(row["story_id"]) if row["story_id"] else None,
        bible_type=row["bible_type"],
        name=row["name"],
        content=content or {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=BibleResponse)
async def create_bible(body: BibleCreate):
    pool = await get_pool()

    if body.story_id:
        story = await pool.fetchrow("SELECT id FROM stories WHERE id=$1", body.story_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

    row = await pool.fetchrow(
        """INSERT INTO bibles (story_id, bible_type, name, content)
           VALUES ($1, $2, $3, $4::jsonb)
           RETURNING *""",
        body.story_id, body.bible_type.value, body.name, json.dumps(body.content),
    )
    return _row_to_response(row)


@router.get("/story/{story_id}", response_model=list[BibleResponse])
async def list_story_bibles(story_id: str):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM bibles WHERE story_id=$1 ORDER BY created_at ASC", story_id
    )
    return [_row_to_response(r) for r in rows]


@router.get("/{bible_id}", response_model=BibleResponse)
async def get_bible(bible_id: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM bibles WHERE id=$1", bible_id)
    if not row:
        raise HTTPException(status_code=404, detail="Bible not found")
    return _row_to_response(row)


@router.put("/{bible_id}", response_model=BibleResponse)
async def update_bible(bible_id: str, body: BibleCreate):
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE bibles
           SET name=$1, content=$2::jsonb, bible_type=$3, updated_at=now()
           WHERE id=$4 RETURNING *""",
        body.name, json.dumps(body.content), body.bible_type.value, bible_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Bible not found")
    return _row_to_response(row)


@router.delete("/{bible_id}")
async def delete_bible(bible_id: str):
    pool = await get_pool()
    result = await pool.execute("DELETE FROM bibles WHERE id=$1", bible_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Bible not found")
    return {"deleted": bible_id}
