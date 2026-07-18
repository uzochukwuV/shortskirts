import json
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import StoryCreate, StoryResponse, GenerationJobResponse, HistoryEntryResponse
from pipeline.story_agent import generate_episode_plan
from job_queue import enqueue_job, WORKLOAD_STORY
from pipeline.runtime_context import job_context
from pipeline.history import record_story_history
from auth import get_current_user, user_id

router = APIRouter(prefix="/pipeline/stories", tags=["stories"])


def _build_story_response(row, plan_data) -> StoryResponse:
    workflow_state = row.get("workflow_state")
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except Exception:
            workflow_state = None
    if workflow_state is None:
        workflow_state = {}

    if isinstance(plan_data, str):
        try:
            plan_data = json.loads(plan_data)
        except Exception:
            plan_data = None

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
        workflow_version=row.get("workflow_version", "v1"),
        generation_version=row.get("generation_version", "v1"),
        approval_status=row.get("approval_status", "pending_approval"),
        workflow_state=workflow_state,
        episode_plan=plan_data,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _history_row_to_response(row, entity_type: str) -> HistoryEntryResponse:
    state_snapshot = row.get("state_snapshot")
    payload = row.get("payload")
    if isinstance(state_snapshot, str):
        try:
            state_snapshot = json.loads(state_snapshot)
        except Exception:
            state_snapshot = None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = None
    return HistoryEntryResponse(
        id=str(row["id"]),
        entity_type=entity_type,
        entity_id=str(row["story_id"]),
        revision=row["revision"],
        event_type=row["event_type"],
        workflow_version=row.get("workflow_version"),
        generation_version=row.get("generation_version", "v1"),
        source_job_id=str(row["source_job_id"]) if row.get("source_job_id") else None,
        state_snapshot=state_snapshot,
        payload=payload,
        created_at=row["created_at"],
    )


@router.post("", response_model=StoryResponse)
async def create_story(body: StoryCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    owner_id = user_id(user)
    workflow_state = {
        "style_reference_urls": [u for u in body.style_reference_urls if u],
        "character_reference_urls": [u for u in body.character_reference_urls if u],
        "scene_reference_urls": [u for u in body.scene_reference_urls if u],
    }

    bibles = []
    if body.bible_ids:
        rows = await pool.fetch(
            "SELECT * FROM bibles WHERE id = ANY($1::uuid[]) AND owner_id=$2",
            body.bible_ids,
            owner_id,
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

    async with job_context(entity_type="story", workload=WORKLOAD_STORY):
        plan = await generate_episode_plan(
            prompt=body.prompt,
            genre=body.genre,
            style=body.style,
            num_episodes=body.num_episodes,
            num_scenes=body.num_scenes,
            workflow_type=body.workflow_type.value,
            bibles=bibles,
            reference_context=workflow_state,
        )

    row = await pool.fetchrow(
        """INSERT INTO stories
           (owner_id, title, prompt, genre, style, num_episodes, num_scenes, status,
            workflow_type, workflow_version, generation_version, workflow_state,
            approval_status, episode_plan)
           VALUES ($1,$2,$3,$4,$5,$6,$7,'draft',$8,'v1','v1',$9::jsonb,'pending_approval',$10::jsonb)
           RETURNING *""",
        owner_id,
        body.title,
        body.prompt,
        body.genre,
        body.style,
        body.num_episodes,
        body.num_scenes,
        body.workflow_type.value,
        json.dumps(workflow_state),
        json.dumps(plan),
    )
    story_id = str(row["id"])
    await record_story_history(
        pool,
        story=row,
        event_type="story_created",
        payload={
            "title": row["title"],
            "status": row["status"],
            "approval_status": row.get("approval_status"),
            "workflow_type": row.get("workflow_type"),
        },
    )

    if body.bible_ids:
        for bid in body.bible_ids:
            await pool.execute(
                """UPDATE bibles SET story_id=$1, updated_at=now()
                   WHERE id=$2 AND story_id IS NULL AND owner_id=$3""",
                story_id,
                bid,
                owner_id,
            )

    plan_characters = plan.get("characters", [])
    if plan_characters:
        await _insert_plan_characters(
            pool,
            story_id,
            plan_characters,
            seed_ref_urls=workflow_state["character_reference_urls"] or workflow_state["style_reference_urls"],
        )

    for ep in plan.get("episodes", []):
        await pool.execute(
            """INSERT INTO episodes (story_id, episode_number, title, status)
               VALUES ($1,$2,$3,'pending')
               ON CONFLICT (story_id, episode_number) DO NOTHING""",
            story_id,
            ep["episode_number"],
            ep.get("title", f"Episode {ep['episode_number']}"),
        )

    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    return _build_story_response(row, plan_data)


async def _insert_plan_characters(pool, story_id: str, characters: list[dict], seed_ref_urls: list[str] | None = None):
    inserted = 0
    skipped = 0
    refs = [u for u in (seed_ref_urls or []) if u]
    for char in characters:
        name = char.get("name", "").strip()
        if not name:
            skipped += 1
            continue
        row = await pool.fetchrow(
            """INSERT INTO characters
               (story_id, name, description, role, personality, appearance, ref_image_urls)
               VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)
               ON CONFLICT (story_id, name) DO NOTHING
               RETURNING id""",
            story_id,
            name,
            char.get("description", ""),
            char.get("role", "main"),
            char.get("personality", ""),
            char.get("appearance", ""),
            json.dumps(refs),
        )
        if row:
            inserted += 1
        else:
            skipped += 1
    print(f"[stories] Materialised {inserted} characters for story {story_id}; skipped {skipped}")


@router.get("", response_model=list[StoryResponse])
async def list_stories(user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM stories WHERE owner_id=$1 ORDER BY created_at DESC LIMIT 50",
        user_id(user),
    )
    result = []
    for row in rows:
        plan_data = row["episode_plan"]
        if isinstance(plan_data, str):
            plan_data = json.loads(plan_data)
        result.append(_build_story_response(row, plan_data))
    return result


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM stories WHERE id=$1 AND owner_id=$2",
        story_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Story not found")
    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    return _build_story_response(row, plan_data)


@router.put("/{story_id}/approve-outline", response_model=StoryResponse)
async def approve_outline(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE stories
           SET status='approved', approval_status='approved', approved_at=now(), updated_at=now()
           WHERE id=$1 AND owner_id=$2 AND status='draft'
           RETURNING *""",
        story_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Draft story not found")
    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    await record_story_history(
        pool,
        story=row,
        event_type="outline_approved",
        payload={
            "status": row["status"],
            "approval_status": row.get("approval_status"),
        },
    )
    return _build_story_response(row, plan_data)


@router.post("/{story_id}/generate", response_model=GenerationJobResponse)
async def generate_story(
    story_id: str,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    story = await pool.fetchrow(
        "SELECT * FROM stories WHERE id=$1 AND owner_id=$2",
        story_id,
        user_id(user),
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story["status"] in {"generating", "checkpoint_review"}:
        raise HTTPException(status_code=409, detail="Generation already in progress")
    if story["status"] == "draft":
        raise HTTPException(
            status_code=400,
            detail="Outline must be approved before generation. Call PUT /approve-outline first.",
        )

    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('story',$1,'pending',0,'Queued','full_episode')
           RETURNING *""",
        story_id,
    )
    job_id = str(job_row["id"])
    await enqueue_job(job_id, workload=WORKLOAD_STORY)
    await pool.execute(
        "UPDATE stories SET status='generating', updated_at=now() WHERE id=$1",
        story_id,
    )

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


@router.get("/{story_id}/history", response_model=list[HistoryEntryResponse])
async def get_story_history(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    if not await pool.fetchrow(
        "SELECT 1 FROM stories WHERE id=$1 AND owner_id=$2",
        story_id,
        user_id(user),
    ):
        raise HTTPException(status_code=404, detail="Story not found")
    rows = await pool.fetch(
        """SELECT * FROM story_history
           WHERE story_id=$1
           ORDER BY revision ASC, created_at ASC""",
        story_id,
    )
    return [_history_row_to_response(row, "story") for row in rows]
