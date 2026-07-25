import json
from fastapi import APIRouter, HTTPException, Depends
from db.connection import get_pool
from models.story import (
    StoryAssistantRequest,
    StoryAssistantResponse,
    StoryCapabilitiesResponse,
    StoryCreate,
    StoryOperationsAgentRequest,
    StoryOperationsAgentResponse,
    StoryPipelineConfigUpdate,
    StoryResponse,
    StoryUpdate,
    GenerationJobResponse,
    HistoryEntryResponse,
)
from pipeline.story_agent import generate_episode_plan, suggest_scene_edit, suggest_story_edit
from job_queue import enqueue_job, WORKLOAD_MEDIA, WORKLOAD_STORY
from pipeline.runtime_context import job_context
from pipeline.history import record_story_history
from pipeline.pipeline_config import normalize_pipeline_config, workflow_state_with_pipeline_config
from pipeline.operations_agent import build_story_capabilities, plan_operation
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
    frame_ratio = workflow_state.get("frame_ratio", "16:9")
    requested_video_ratio = workflow_state.get("requested_video_ratio", frame_ratio)
    requested_media_kind = workflow_state.get("requested_media_kind", "auto")
    pipeline_config = normalize_pipeline_config(
        workflow_state=workflow_state,
        workflow_type=row.get("workflow_type", "creator_series"),
        requested_media_kind=requested_media_kind,
        frame_ratio=frame_ratio,
        requested_video_ratio=requested_video_ratio,
    )

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
        frame_ratio=frame_ratio,
        requested_video_ratio=requested_video_ratio,
        num_episodes=row["num_episodes"],
        num_scenes=row["num_scenes"],
        status=row["status"],
        workflow_type=row.get("workflow_type", "creator_series"),
        requested_media_kind=requested_media_kind,
        workflow_version=row.get("workflow_version", "v1"),
        generation_version=row.get("generation_version", "v1"),
        approval_status=row.get("approval_status", "pending_approval"),
        pipeline_config=pipeline_config,
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


async def _load_story_row(pool, story_id: str, owner_id: str):
    return await pool.fetchrow(
        "SELECT * FROM stories WHERE id=$1 AND owner_id=$2",
        story_id,
        owner_id,
    )


async def _load_story_scene(pool, story_id: str, owner_id: str, scene_id: str):
    return await pool.fetchrow(
        """SELECT sc.*
           FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           JOIN stories s ON s.id = e.story_id
           WHERE sc.id=$1 AND s.id=$2 AND s.owner_id=$3""",
        scene_id,
        story_id,
        owner_id,
    )


async def _load_story_checkpoint(pool, story_id: str, owner_id: str):
    return await pool.fetchrow(
        """SELECT c.*
           FROM story_generation_checkpoints c
           JOIN stories s ON s.id = c.story_id
           WHERE c.story_id=$1 AND s.owner_id=$2
           ORDER BY
             CASE c.status
               WHEN 'pending_review' THEN 0
               WHEN 'pending' THEN 1
               WHEN 'running' THEN 2
               ELSE 3
             END,
             c.created_at DESC
           LIMIT 1""",
        story_id,
        owner_id,
    )


async def _load_story_job(pool, story_id: str):
    return await pool.fetchrow(
        """SELECT *
           FROM generation_jobs
           WHERE entity_type='story' AND entity_id=$1
           ORDER BY
             CASE status
               WHEN 'running' THEN 0
               WHEN 'pending' THEN 1
               WHEN 'retrying' THEN 2
               WHEN 'failed' THEN 3
               ELSE 4
             END,
             created_at DESC
           LIMIT 1""",
        story_id,
    )


async def _load_story_bibles(pool, story_id: str) -> list[dict]:
    rows = await pool.fetch(
        """SELECT *
           FROM bibles
           WHERE story_id=$1
           ORDER BY created_at ASC""",
        story_id,
    )
    bibles: list[dict] = []
    for row in rows:
        content = row["content"]
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {}
        bibles.append(
            {
                "bible_type": row["bible_type"],
                "name": row["name"],
                "content": content or {},
            }
        )
    return bibles


def _story_payload(row, plan_data: dict | None) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "prompt": row["prompt"],
        "genre": row["genre"],
        "style": row["style"],
        "status": row["status"],
        "workflow_type": row.get("workflow_type", "creator_series"),
        "episode_plan": plan_data or {},
    }


def _scene_payload(scene_row) -> dict:
    metadata = scene_row.get("generation_metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    metadata = metadata or {}
    return {
        "title": metadata.get("title") or f"Scene {scene_row['scene_number']}",
        "description": metadata.get("description", ""),
        "visual_prompt": metadata.get("visual_prompt") or scene_row["prompt"],
        "mood": metadata.get("mood", ""),
        "location": metadata.get("location", ""),
        "action": metadata.get("action", ""),
        "narration": metadata.get("narration", ""),
        "prompt": scene_row["prompt"],
    }


async def _regenerate_outline(pool, story_row, owner_id: str):
    story_status = (story_row["status"] or "").strip().lower()
    if story_status in {"generating", "checkpoint_review"}:
        raise HTTPException(status_code=409, detail="Cancel or finish the current run before regenerating the outline")

    scene_count = await pool.fetchval(
        """SELECT COUNT(*)
           FROM scenes sc
           JOIN episodes e ON e.id = sc.episode_id
           WHERE e.story_id=$1""",
        str(story_row["id"]),
    )
    if scene_count and int(scene_count) > 0:
        raise HTTPException(
            status_code=409,
            detail="Outline regeneration is only allowed before scene generation starts",
        )

    workflow_state = story_row.get("workflow_state")
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except Exception:
            workflow_state = {}
    workflow_state = workflow_state or {}
    bibles = await _load_story_bibles(pool, str(story_row["id"]))

    async with job_context(entity_type="story", workload=WORKLOAD_STORY):
        plan = await generate_episode_plan(
            prompt=story_row["prompt"],
            genre=story_row["genre"],
            style=story_row["style"],
            num_episodes=story_row["num_episodes"],
            num_scenes=story_row["num_scenes"],
            workflow_type=story_row.get("workflow_type", "creator_series"),
            bibles=bibles,
            reference_context=workflow_state,
        )

    updated = await pool.fetchrow(
        """UPDATE stories
           SET status='draft',
               approval_status='pending_approval',
               approved_at=NULL,
               episode_plan=$2::jsonb,
               updated_at=now()
           WHERE id=$1 AND owner_id=$3
           RETURNING *""",
        str(story_row["id"]),
        json.dumps(plan),
        owner_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Story not found")

    for ep in plan.get("episodes", []):
        await pool.execute(
            """INSERT INTO episodes (story_id, episode_number, title, status)
               VALUES ($1,$2,$3,'pending')
               ON CONFLICT (story_id, episode_number)
               DO UPDATE SET title=EXCLUDED.title, updated_at=now()""",
            str(updated["id"]),
            ep["episode_number"],
            ep.get("title", f"Episode {ep['episode_number']}"),
        )

    await record_story_history(
        pool,
        story=updated,
        event_type="outline_regenerated",
        payload={
            "status": updated["status"],
            "approval_status": updated.get("approval_status"),
        },
    )
    return updated, plan


@router.post("", response_model=StoryResponse)
async def create_story(body: StoryCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    owner_id = user_id(user)
    pipeline_config = normalize_pipeline_config(
        body.pipeline_config,
        workflow_type=body.workflow_type.value,
        requested_media_kind=body.requested_media_kind.value,
        frame_ratio=body.frame_ratio,
        requested_video_ratio=body.requested_video_ratio,
    )
    workflow_state = workflow_state_with_pipeline_config({
        "style_reference_urls": [u for u in body.style_reference_urls if u],
        "character_reference_urls": [u for u in body.character_reference_urls if u],
        "scene_reference_urls": [u for u in body.scene_reference_urls if u],
        "frame_ratio": body.frame_ratio,
        "requested_video_ratio": body.requested_video_ratio,
        "requested_media_kind": body.requested_media_kind.value,
    }, pipeline_config)

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


@router.put("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: str,
    body: StoryUpdate,
    user=Depends(get_current_user),
):
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
        try:
            plan_data = json.loads(plan_data)
        except Exception:
            plan_data = {}
    plan_data = dict(plan_data or {})
    if body.synopsis is not None:
        plan_data["synopsis"] = body.synopsis
    if body.setting is not None:
        plan_data["setting"] = body.setting
    if body.themes is not None:
        plan_data["themes"] = [theme for theme in body.themes if theme]

    updated = await pool.fetchrow(
        """UPDATE stories
           SET title=COALESCE($2, title),
               prompt=COALESCE($3, prompt),
               genre=COALESCE($4, genre),
               style=COALESCE($5, style),
               episode_plan=$6::jsonb,
               updated_at=now()
           WHERE id=$1 AND owner_id=$7
           RETURNING *""",
        story_id,
        body.title,
        body.prompt,
        body.genre,
        body.style,
        json.dumps(plan_data),
        user_id(user),
    )
    await record_story_history(
        pool,
        story=updated,
        event_type="story_updated",
        payload={
            "title": body.title,
            "prompt": body.prompt,
            "genre": body.genre,
            "style": body.style,
            "synopsis": body.synopsis,
            "setting": body.setting,
            "themes": body.themes,
        },
    )
    return _build_story_response(updated, plan_data)


@router.post("/{story_id}/assistant", response_model=StoryAssistantResponse)
async def story_assistant(
    story_id: str,
    body: StoryAssistantRequest,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    owner_id = user_id(user)
    row = await _load_story_row(pool, story_id, owner_id)
    if not row:
        raise HTTPException(status_code=404, detail="Story not found")

    plan_data = row["episode_plan"]
    if isinstance(plan_data, str):
        try:
            plan_data = json.loads(plan_data)
        except Exception:
            plan_data = {}
    story_payload = _story_payload(row, plan_data)

    target = (body.target or "story").lower()
    if target == "scene":
        if not body.scene_id:
            raise HTTPException(status_code=400, detail="scene_id is required for scene edits")
        scene_row = await _load_story_scene(pool, story_id, owner_id, body.scene_id)
        if not scene_row:
            raise HTTPException(status_code=404, detail="Scene not found")
        scene_payload = _scene_payload(scene_row)
        result = await suggest_scene_edit(story_payload, scene_payload, body.instruction)
        return StoryAssistantResponse(
            target="scene",
            message=result.get("message", "Drafted a scene revision."),
            story_patch={},
            scene_patch=result.get("scene_patch") or {},
        )

    result = await suggest_story_edit(story_payload, body.instruction)
    return StoryAssistantResponse(
        target="story",
        message=result.get("message", "Drafted a story revision."),
        story_patch=result.get("story_patch") or {},
        scene_patch={},
    )


@router.get("/{story_id}/capabilities", response_model=StoryCapabilitiesResponse)
async def get_story_capabilities(
    story_id: str,
    scene_id: str | None = None,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    owner_id = user_id(user)
    story_row = await _load_story_row(pool, story_id, owner_id)
    if not story_row:
        raise HTTPException(status_code=404, detail="Story not found")

    selected_scene = None
    if scene_id:
        selected_scene = await _load_story_scene(pool, story_id, owner_id, scene_id)
        if not selected_scene:
            raise HTTPException(status_code=404, detail="Scene not found")

    selected_checkpoint = await _load_story_checkpoint(pool, story_id, owner_id)
    active_job = await _load_story_job(pool, story_id)
    capabilities = build_story_capabilities(
        story=dict(story_row),
        selected_scene=dict(selected_scene) if selected_scene else None,
        selected_checkpoint=dict(selected_checkpoint) if selected_checkpoint else None,
        active_job=dict(active_job) if active_job else None,
    )
    return StoryCapabilitiesResponse(
        story_id=story_id,
        story_status=story_row["status"],
        selected_scene_id=str(selected_scene["id"]) if selected_scene else None,
        selected_checkpoint_id=str(selected_checkpoint["id"]) if selected_checkpoint else None,
        **capabilities,
    )


@router.post("/{story_id}/regenerate-outline", response_model=StoryResponse)
async def regenerate_outline(story_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    owner_id = user_id(user)
    story_row = await _load_story_row(pool, story_id, owner_id)
    if not story_row:
        raise HTTPException(status_code=404, detail="Story not found")
    updated, plan = await _regenerate_outline(pool, story_row, owner_id)
    return _build_story_response(updated, plan)


@router.post("/{story_id}/operations-agent", response_model=StoryOperationsAgentResponse)
async def story_operations_agent(
    story_id: str,
    body: StoryOperationsAgentRequest,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    owner_id = user_id(user)
    story_row = await _load_story_row(pool, story_id, owner_id)
    if not story_row:
        raise HTTPException(status_code=404, detail="Story not found")

    plan_data = story_row["episode_plan"]
    if isinstance(plan_data, str):
        try:
            plan_data = json.loads(plan_data)
        except Exception:
            plan_data = {}
    story_payload = _story_payload(story_row, plan_data or {})

    selected_scene = None
    if body.scene_id:
        selected_scene = await _load_story_scene(pool, story_id, owner_id, body.scene_id)
        if not selected_scene:
            raise HTTPException(status_code=404, detail="Scene not found")

    selected_checkpoint = await _load_story_checkpoint(pool, story_id, owner_id)
    active_job = await _load_story_job(pool, story_id)
    operation_plan = await plan_operation(
        story=story_payload,
        selected_scene=dict(selected_scene) if selected_scene else None,
        selected_checkpoint=dict(selected_checkpoint) if selected_checkpoint else None,
        active_job=dict(active_job) if active_job else None,
        instruction=body.instruction,
    )

    if not body.execute:
        return StoryOperationsAgentResponse(
            executed=False,
            reason=None if operation_plan["allowed"] else operation_plan["message"],
            **{k: v for k, v in operation_plan.items() if k != "capabilities"},
        )

    if not operation_plan["allowed"]:
        return StoryOperationsAgentResponse(
            executed=False,
            reason=operation_plan["message"],
            **{k: v for k, v in operation_plan.items() if k != "capabilities"},
        )

    operation = operation_plan["operation"]
    result: dict[str, str] = {}
    executed = False
    reason = None

    if operation == "edit_story":
        patch = operation_plan["story_patch"] or {}
        current_plan = dict(plan_data or {})
        if "synopsis" in patch:
            current_plan["synopsis"] = patch["synopsis"]
        if "setting" in patch:
            current_plan["setting"] = patch["setting"]
        if "themes" in patch:
            current_plan["themes"] = [theme for theme in (patch["themes"] or []) if theme]
        updated = await pool.fetchrow(
            """UPDATE stories
               SET title=COALESCE($2, title),
                   prompt=COALESCE($3, prompt),
                   genre=COALESCE($4, genre),
                   style=COALESCE($5, style),
                   episode_plan=$6::jsonb,
                   updated_at=now()
               WHERE id=$1 AND owner_id=$7
               RETURNING *""",
            story_id,
            patch.get("title"),
            patch.get("prompt"),
            patch.get("genre"),
            patch.get("style"),
            json.dumps(current_plan),
            owner_id,
        )
        if updated:
            await record_story_history(
                pool,
                story=updated,
                event_type="story_updated_by_operations_agent",
                payload={"instruction": body.instruction, "story_patch": patch},
            )
            executed = True
            result = {"story_id": story_id}
    elif operation == "edit_scene" and selected_scene:
        patch = operation_plan["scene_patch"] or {}
        metadata = selected_scene.get("generation_metadata")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        metadata = metadata or {}
        for key in ("title", "description", "visual_prompt", "mood", "location", "action", "narration"):
            if key in patch:
                metadata[key] = patch[key]
        updated_scene = await pool.fetchrow(
            """UPDATE scenes
               SET prompt=COALESCE($2, prompt),
                   generation_metadata=$3::jsonb,
                   updated_at=now()
               WHERE id=$1
               RETURNING *""",
            str(selected_scene["id"]),
            patch.get("prompt"),
            json.dumps(metadata),
        )
        if updated_scene:
            await record_story_history(
                pool,
                story=story_row,
                event_type="scene_updated_by_operations_agent",
                payload={"instruction": body.instruction, "scene_id": str(selected_scene["id"])},
            )
            executed = True
            result = {"scene_id": str(selected_scene["id"])}
    elif operation == "approve_outline":
        updated = await pool.fetchrow(
            """UPDATE stories
               SET status='approved', approval_status='approved', approved_at=now(), updated_at=now()
               WHERE id=$1 AND owner_id=$2 AND status='draft'
               RETURNING *""",
            story_id,
            owner_id,
        )
        if updated:
            await record_story_history(
                pool,
                story=updated,
                event_type="outline_approved_by_operations_agent",
                payload={"instruction": body.instruction},
            )
            executed = True
            result = {"story_id": story_id}
    elif operation == "regenerate_outline":
        updated, _ = await _regenerate_outline(pool, story_row, owner_id)
        executed = True
        result = {"story_id": str(updated["id"])}
    elif operation == "start_generation":
        if story_row["status"] in {"generating", "checkpoint_review"}:
            reason = "Generation already in progress"
        elif story_row["status"] == "draft":
            reason = "Outline must be approved before generation"
        else:
            job_row = await pool.fetchrow(
                """INSERT INTO generation_jobs
                   (entity_type, entity_id, status, total_steps, current_step, job_type)
                   VALUES ('story',$1,'pending',0,'Queued','full_episode')
                   RETURNING *""",
                story_id,
            )
            await enqueue_job(str(job_row["id"]), workload=WORKLOAD_STORY)
            await pool.execute(
                "UPDATE stories SET status='generating', updated_at=now() WHERE id=$1",
                story_id,
            )
            executed = True
            result = {"story_id": story_id, "job_id": str(job_row["id"])}
    elif operation == "regenerate_scene" and selected_scene:
        job_row = await pool.fetchrow(
            """INSERT INTO generation_jobs
               (entity_type, entity_id, status, total_steps, current_step, job_type)
               VALUES ('scene', $1, 'pending', 1, 'Queued', 'scene_regen')
               RETURNING *""",
            str(selected_scene["id"]),
        )
        await enqueue_job(str(job_row["id"]), workload=WORKLOAD_MEDIA)
        await pool.execute(
            "UPDATE scenes SET status='running', updated_at=now() WHERE id=$1",
            str(selected_scene["id"]),
        )
        executed = True
        result = {"scene_id": str(selected_scene["id"]), "job_id": str(job_row["id"])}
    elif operation == "approve_checkpoint" and selected_checkpoint:
        if selected_checkpoint.get("status") == "approved":
            executed = True
            result = {"checkpoint_id": str(selected_checkpoint["id"])}
        elif not selected_checkpoint.get("resume_job_id"):
            reason = "Checkpoint does not have a pending resume job"
        elif selected_checkpoint.get("audio_status") in {"pending", "running"}:
            reason = "Checkpoint narration audio is still processing"
        else:
            await pool.execute(
                """UPDATE story_generation_checkpoints
                   SET status='approved', approved_at=now(), reviewed_at=now(), updated_at=now()
                   WHERE id=$1""",
                str(selected_checkpoint["id"]),
            )
            await pool.execute(
                "UPDATE stories SET status='generating', updated_at=now() WHERE id=$1",
                story_id,
            )
            await enqueue_job(str(selected_checkpoint["resume_job_id"]), workload=WORKLOAD_STORY)
            executed = True
            result = {
                "checkpoint_id": str(selected_checkpoint["id"]),
                "job_id": str(selected_checkpoint["resume_job_id"]),
            }
    elif operation == "cancel_run" and active_job:
        updated_job = await pool.fetchrow(
            """UPDATE generation_jobs
               SET status='canceled',
                   error='Canceled by operations agent',
                   completed_at=COALESCE(completed_at, now()),
                   worker_id=NULL,
                   lease_expires_at=NULL,
                   updated_at=now()
               WHERE id=$1
               RETURNING *""",
            str(active_job["id"]),
        )
        if updated_job:
            executed = True
            result = {"job_id": str(updated_job["id"])}
    elif operation == "retry_failed_step" and active_job:
        updated_job = await pool.fetchrow(
            """UPDATE generation_jobs
               SET status='pending',
                   error=NULL,
                   completed_at=NULL,
                   worker_id=NULL,
                   leased_at=NULL,
                   lease_expires_at=NULL,
                   last_heartbeat_at=now(),
                   current_step='Retry queued',
                   updated_at=now()
               WHERE id=$1
               RETURNING *""",
            str(active_job["id"]),
        )
        if updated_job:
            await enqueue_job(str(updated_job["id"]), workload=WORKLOAD_STORY)
            executed = True
            result = {"job_id": str(updated_job["id"])}

    if not executed and reason is None:
        reason = "The selected operation could not be executed"

    return StoryOperationsAgentResponse(
        executed=executed,
        reason=reason,
        result=result,
        **{k: v for k, v in operation_plan.items() if k != "capabilities"},
    )


@router.put("/{story_id}/pipeline-config", response_model=StoryResponse)
async def update_story_pipeline_config(
    story_id: str,
    body: StoryPipelineConfigUpdate,
    user=Depends(get_current_user),
):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM stories WHERE id=$1 AND owner_id=$2",
        story_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Story not found")
    workflow_state = row.get("workflow_state")
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except Exception:
            workflow_state = {}
    pipeline_config = normalize_pipeline_config(
        body.pipeline_config,
        workflow_state=workflow_state,
        workflow_type=row.get("workflow_type", "creator_series"),
    )
    updated_state = workflow_state_with_pipeline_config(workflow_state, pipeline_config)
    updated = await pool.fetchrow(
        """UPDATE stories
           SET workflow_state=$1::jsonb, updated_at=now()
           WHERE id=$2 AND owner_id=$3
           RETURNING *""",
        json.dumps(updated_state),
        story_id,
        user_id(user),
    )
    await record_story_history(
        pool,
        story=updated,
        event_type="pipeline_config_updated",
        payload={"pipeline_config": pipeline_config},
    )
    plan_data = updated["episode_plan"]
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    return _build_story_response(updated, plan_data)


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
