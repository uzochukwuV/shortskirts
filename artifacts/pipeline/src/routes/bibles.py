import json
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import BibleCreate, BibleResponse
from auth import get_current_user, user_id

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
async def create_bible(body: BibleCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    owner_id = user_id(user)

    if body.story_id:
        story = await pool.fetchrow(
            "SELECT id FROM stories WHERE id=$1 AND owner_id=$2",
            body.story_id,
            owner_id,
        )
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

    row = await pool.fetchrow(
        """INSERT INTO bibles (owner_id, story_id, bible_type, name, content)
           VALUES ($1, $2, $3, $4, $5::jsonb)
           RETURNING *""",
        owner_id,
        body.story_id,
        body.bible_type.value,
        body.name,
        json.dumps(body.content),
    )
    return _row_to_response(row)


@router.get("/story/{story_id}", response_model=list[BibleResponse])
async def list_story_bibles(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT b.* FROM bibles b
           JOIN stories s ON s.id = b.story_id
           WHERE b.story_id=$1 AND s.owner_id=$2
           ORDER BY b.created_at ASC""",
        story_id,
        user_id(user),
    )
    return [_row_to_response(r) for r in rows]


@router.get("/{bible_id}", response_model=BibleResponse)
async def get_bible(bible_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM bibles WHERE id=$1 AND owner_id=$2",
        bible_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Bible not found")
    return _row_to_response(row)


@router.put("/{bible_id}", response_model=BibleResponse)
async def update_bible(bible_id: str, body: BibleCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    owner_id = user_id(user)
    if body.story_id:
        story = await pool.fetchrow(
            "SELECT id FROM stories WHERE id=$1 AND owner_id=$2",
            body.story_id,
            owner_id,
        )
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

    row = await pool.fetchrow(
        """UPDATE bibles
           SET story_id=$1, name=$2, content=$3::jsonb, bible_type=$4, updated_at=now()
           WHERE id=$5 AND owner_id=$6 RETURNING *""",
        body.story_id,
        body.name,
        json.dumps(body.content),
        body.bible_type.value,
        bible_id,
        owner_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Bible not found")
    return _row_to_response(row)


@router.delete("/{bible_id}")
async def delete_bible(bible_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    result = await pool.execute(
        "DELETE FROM bibles WHERE id=$1 AND owner_id=$2",
        bible_id,
        user_id(user),
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Bible not found")
    return {"deleted": bible_id}
