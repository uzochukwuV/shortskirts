import uuid
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from db.connection import get_pool
from models.story import StoryCreate, StoryResponse, GenerationJobResponse
from pipeline.story_agent import generate_episode_plan
from pipeline.orchestrator import run_story_generation

router = APIRouter(prefix="/pipeline/stories", tags=["stories"])


@router.post("", response_model=StoryResponse)
async def create_story(body: StoryCreate):
    pool = await get_pool()

    plan = await generate_episode_plan(
        prompt=body.prompt,
        genre=body.genre,
        style=body.style,
        num_episodes=body.num_episodes,
        num_scenes=body.num_scenes,
    )

    row = await pool.fetchrow(
        """INSERT INTO stories (title, prompt, genre, style, num_episodes, num_scenes, status, episode_plan)
           VALUES ($1, $2, $3, $4, $5, $6, 'draft', $7::jsonb)
           RETURNING *""",
        body.title, body.prompt, body.genre, body.style,
        body.num_episodes, body.num_scenes, json.dumps(plan),
    )

    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)

    return StoryResponse(
        id=str(row["id"]),
        title=row["title"],
        prompt=row["prompt"],
        genre=row["genre"],
        style=row["style"],
        num_episodes=row["num_episodes"],
        num_scenes=row["num_scenes"],
        status=row["status"],
        episode_plan=plan_data,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=list[StoryResponse])
async def list_stories():
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM stories ORDER BY created_at DESC LIMIT 50")
    result = []
    for row in rows:
        plan_data = row["episode_plan"]
        if isinstance(plan_data, str):
            plan_data = json.loads(plan_data)
        result.append(StoryResponse(
            id=str(row["id"]),
            title=row["title"],
            prompt=row["prompt"],
            genre=row["genre"],
            style=row["style"],
            num_episodes=row["num_episodes"],
            num_scenes=row["num_scenes"],
            status=row["status"],
            episode_plan=plan_data,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        ))
    return result


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
    if not row:
        raise HTTPException(status_code=404, detail="Story not found")
    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    return StoryResponse(
        id=str(row["id"]),
        title=row["title"],
        prompt=row["prompt"],
        genre=row["genre"],
        style=row["style"],
        num_episodes=row["num_episodes"],
        num_scenes=row["num_scenes"],
        status=row["status"],
        episode_plan=plan_data,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/{story_id}/generate", response_model=GenerationJobResponse)
async def generate_story(story_id: str, background_tasks: BackgroundTasks):
    pool = await get_pool()
    story = await pool.fetchrow("SELECT * FROM stories WHERE id = $1", story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story["status"] == "generating":
        raise HTTPException(status_code=409, detail="Generation already in progress")

    job_row = await pool.fetchrow(
        """INSERT INTO generation_jobs (entity_type, entity_id, status, total_steps, current_step)
           VALUES ('story', $1, 'pending', 0, 'Queued')
           RETURNING *""",
        story_id,
    )
    job_id = str(job_row["id"])

    await pool.execute("UPDATE stories SET status='generating' WHERE id=$1", story_id)

    background_tasks.add_task(run_story_generation, story_id, job_id)

    return GenerationJobResponse(
        id=job_id,
        entity_type="story",
        entity_id=story_id,
        status="pending",
        progress=0,
        total_steps=0,
        current_step="Queued",
        created_at=job_row["created_at"],
    )
