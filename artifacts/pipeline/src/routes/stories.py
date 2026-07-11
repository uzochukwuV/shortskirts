import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from db.connection import get_pool
from models.story import StoryCreate, StoryResponse, GenerationJobResponse, StoryStatus
from pipeline.story_agent import generate_episode_plan
from pipeline.orchestrator import run_story_generation

router = APIRouter(prefix="/pipeline/stories", tags=["stories"])


def _build_story_response(row, plan_data) -> StoryResponse:
    return StoryResponse(
        id=str(row["id"]),
        title=row["title"],
        prompt=row["prompt"],
        genre=row["genre"],
        style=row["style"],
        num_episodes=row["num_episodes"],
        num_scenes=row["num_scenes"],
        status=row["status"],
        workflow_type=row.get("workflow_type", "creator_series"),
        approval_status=row.get("approval_status", "pending_approval"),
        episode_plan=plan_data,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=StoryResponse)
async def create_story(body: StoryCreate):
    pool = await get_pool()

    # Load bibles if provided — inject into LLM planning prompt
    bibles = []
    if body.bible_ids:
        rows = await pool.fetch(
            "SELECT * FROM bibles WHERE id = ANY($1::uuid[])", body.bible_ids
        )
        for r in rows:
            content = r["content"]
            if isinstance(content, str):
                content = json.loads(content)
            bibles.append({
                "bible_type": r["bible_type"],
                "name": r["name"],
                "content": content or {},
            })

    plan = await generate_episode_plan(
        prompt=body.prompt,
        genre=body.genre,
        style=body.style,
        num_episodes=body.num_episodes,
        num_scenes=body.num_scenes,
        workflow_type=body.workflow_type.value,
        bibles=bibles,
    )

    row = await pool.fetchrow(
        """INSERT INTO stories
           (title, prompt, genre, style, num_episodes, num_scenes, status,
            workflow_type, approval_status, episode_plan)
           VALUES ($1,$2,$3,$4,$5,$6,'draft',$7,'pending_approval',$8::jsonb)
           RETURNING *""",
        body.title, body.prompt, body.genre, body.style,
        body.num_episodes, body.num_scenes,
        body.workflow_type.value, json.dumps(plan),
    )
    story_id = str(row["id"])

    # Link bibles to this story
    if body.bible_ids:
        for bid in body.bible_ids:
            await pool.execute(
                "UPDATE bibles SET story_id=$1 WHERE id=$2 AND story_id IS NULL",
                story_id, bid,
            )

    # Auto-materialize characters from plan
    plan_characters = plan.get("characters", [])
    if plan_characters:
        await _insert_plan_characters(pool, story_id, plan_characters)

    # Pre-insert episode rows
    for ep in plan.get("episodes", []):
        await pool.execute(
            """INSERT INTO episodes (story_id, episode_number, title, status)
               VALUES ($1,$2,$3,'pending')
               ON CONFLICT (story_id, episode_number) DO NOTHING""",
            story_id, ep["episode_number"],
            ep.get("title", f"Episode {ep['episode_number']}"),
        )

    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)

    return _build_story_response(row, plan_data)


async def _insert_plan_characters(pool, story_id: str, characters: list[dict]):
    for char in characters:
        name = char.get("name", "").strip()
        if not name:
            continue
        exists = await pool.fetchval(
            "SELECT id FROM characters WHERE story_id=$1 AND name=$2", story_id, name
        )
        if exists:
            continue
        await pool.execute(
            """INSERT INTO characters
               (story_id, name, description, role, personality, appearance, ref_image_urls)
               VALUES ($1,$2,$3,$4,$5,$6,'[]'::jsonb)""",
            story_id, name,
            char.get("description", ""),
            char.get("role", "main"),
            char.get("personality", ""),
            char.get("appearance", ""),
        )
    print(f"[stories] Materialised {len(characters)} characters for story {story_id}")


@router.get("", response_model=list[StoryResponse])
async def list_stories():
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM stories ORDER BY created_at DESC LIMIT 50")
    result = []
    for row in rows:
        plan_data = row["episode_plan"]
        if isinstance(plan_data, str):
            plan_data = json.loads(plan_data)
        result.append(_build_story_response(row, plan_data))
    return result


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
    if not row:
        raise HTTPException(status_code=404, detail="Story not found")
    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    return _build_story_response(row, plan_data)


# ── Approval gate: approve the outline before any video renders ──────────────

@router.put("/{story_id}/approve-outline", response_model=StoryResponse)
async def approve_outline(story_id: str):
    """Human gate: approve the story outline. Required before generation can start."""
    pool = await get_pool()
    story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story["status"] not in ("draft",):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve outline in status '{story['status']}'"
        )

    row = await pool.fetchrow(
        """UPDATE stories
           SET status='approved', approval_status='approved', approved_at=now(), updated_at=now()
           WHERE id=$1 RETURNING *""",
        story_id,
    )
    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    return _build_story_response(row, plan_data)


# ── Start generation (requires approved outline) ─────────────────────────────

@router.post("/{story_id}/generate", response_model=GenerationJobResponse)
async def generate_story(story_id: str, background_tasks: BackgroundTasks):
    pool = await get_pool()
    story = await pool.fetchrow("SELECT * FROM stories WHERE id=$1", story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story["status"] == "generating":
        raise HTTPException(status_code=409, detail="Generation already in progress")

    # Enforce approval gate — outline must be approved first
    if story["status"] == "draft":
        raise HTTPException(
            status_code=400,
            detail="Outline must be approved before generation. Call PUT /approve-outline first."
        )

    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('story',$1,'pending',0,'Queued','full_episode')
           RETURNING *""",
        story_id,
    )
    job_id = str(job_row["id"])
    await pool.execute("UPDATE stories SET status='generating', updated_at=now() WHERE id=$1", story_id)
    background_tasks.add_task(run_story_generation, story_id, job_id)

    return GenerationJobResponse(
        id=job_id,
        entity_type="story",
        entity_id=story_id,
        status="pending",
        progress=0,
        total_steps=0,
        current_step="Queued",
        job_type="full_episode",
        created_at=job_row["created_at"],
    )
