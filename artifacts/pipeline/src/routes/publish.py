from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, user_id
from db.connection import get_pool
from job_queue import WORKLOAD_PUBLISH, enqueue_job
from models.social import (
    PublishPostResponse,
    PublishTargetCreate,
    PublishTargetDetailResponse,
    PublishTargetResponse,
)
from pipeline.publishers.media import resolve_publish_media

router = APIRouter(prefix="/pipeline/publish-targets", tags=["publish"])


def _json_array(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = []
    return value if isinstance(value, list) else []


def _json_object(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = {}
    return value or {}


def _target_response(row) -> PublishTargetResponse:
    return PublishTargetResponse(
        id=str(row["id"]),
        platform=row["platform"],
        social_account_id=str(row["social_account_id"]) if row.get("social_account_id") else None,
        story_id=str(row["story_id"]) if row.get("story_id") else None,
        episode_id=str(row["episode_id"]) if row.get("episode_id") else None,
        scene_id=str(row["scene_id"]) if row.get("scene_id") else None,
        artifact_id=str(row["artifact_id"]) if row.get("artifact_id") else None,
        asset_kind=row["asset_kind"],
        media_url=row.get("media_url"),
        title=row["title"],
        description=row["description"],
        tags=_json_array(row.get("tags")),
        privacy_status=row["privacy_status"],
        publish_mode=row["publish_mode"],
        requires_approval=row["requires_approval"],
        approved_at=row.get("approved_at"),
        scheduled_for=row.get("scheduled_for"),
        status=row["status"],
        error=row.get("error"),
        metadata=_json_object(row.get("metadata")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _post_response(row) -> PublishPostResponse:
    return PublishPostResponse(
        id=str(row["id"]),
        publish_target_id=str(row["publish_target_id"]),
        platform=row["platform"],
        platform_post_id=row.get("platform_post_id"),
        public_url=row.get("public_url"),
        upload_session_id=row.get("upload_session_id"),
        status=row["status"],
        response=_json_object(row.get("response")),
        error=row.get("error"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def _assert_story_owner(pool, owner_id: str, story_id: str | None) -> None:
    if not story_id:
        return
    ok = await pool.fetchval("SELECT 1 FROM stories WHERE id=$1 AND owner_id=$2", story_id, owner_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Story not found")


async def _assert_publish_asset_owner(pool, owner_id: str, body: PublishTargetCreate) -> None:
    await _assert_story_owner(pool, owner_id, body.story_id)
    if body.episode_id:
        row = await pool.fetchrow(
            """SELECT e.story_id
               FROM episodes e
               JOIN stories s ON s.id = e.story_id
               WHERE e.id=$1 AND s.owner_id=$2""",
            body.episode_id,
            owner_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Episode not found")
        if body.story_id and str(row["story_id"]) != body.story_id:
            raise HTTPException(status_code=400, detail="episode_id does not belong to story_id")
    if body.scene_id:
        row = await pool.fetchrow(
            """SELECT e.story_id, sc.episode_id
               FROM scenes sc
               JOIN episodes e ON e.id = sc.episode_id
               JOIN stories s ON s.id = e.story_id
               WHERE sc.id=$1 AND s.owner_id=$2""",
            body.scene_id,
            owner_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Scene not found")
        if body.story_id and str(row["story_id"]) != body.story_id:
            raise HTTPException(status_code=400, detail="scene_id does not belong to story_id")
        if body.episode_id and str(row["episode_id"]) != body.episode_id:
            raise HTTPException(status_code=400, detail="scene_id does not belong to episode_id")
    if body.artifact_id:
        row = await pool.fetchrow(
            """SELECT pa.story_id, pa.episode_id, pa.scene_id
               FROM pipeline_artifacts pa
               LEFT JOIN stories s ON s.id = pa.story_id
               WHERE pa.id=$1 AND (pa.story_id IS NULL OR s.owner_id=$2)""",
            body.artifact_id,
            owner_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Artifact not found")


async def _assert_account_owner(pool, owner_id: str, account_id: str | None, platform: str) -> None:
    if platform == "mock" and not account_id:
        return
    if not account_id:
        raise HTTPException(status_code=400, detail=f"{platform} publishing requires social_account_id")
    ok = await pool.fetchval(
        "SELECT 1 FROM social_accounts WHERE id=$1 AND owner_id=$2 AND platform=$3 AND status='connected'",
        account_id,
        owner_id,
        platform,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Connected social account not found")


@router.post("", response_model=PublishTargetResponse)
async def create_publish_target(body: PublishTargetCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    owner_id = user_id(user)
    await _assert_publish_asset_owner(pool, owner_id, body)
    await _assert_account_owner(pool, owner_id, body.social_account_id, body.platform)
    status = "pending_approval" if body.requires_approval else "ready"
    row = await pool.fetchrow(
        """INSERT INTO publish_targets
           (owner_id, social_account_id, story_id, episode_id, scene_id, artifact_id, platform,
            asset_kind, media_url, title, description, tags, privacy_status, publish_mode,
            requires_approval, scheduled_for, status, metadata)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13,$14,$15,$16,$17,$18::jsonb)
           RETURNING *""",
        owner_id,
        body.social_account_id,
        body.story_id,
        body.episode_id,
        body.scene_id,
        body.artifact_id,
        body.platform,
        body.asset_kind,
        body.media_url,
        body.title,
        body.description,
        json.dumps(body.tags),
        body.privacy_status,
        body.publish_mode,
        body.requires_approval,
        body.scheduled_for,
        status,
        json.dumps(body.metadata),
    )
    return _target_response(row)


@router.get("", response_model=list[PublishTargetResponse])
async def list_publish_targets(user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM publish_targets WHERE owner_id=$1 ORDER BY created_at DESC LIMIT 100",
        user_id(user),
    )
    return [_target_response(row) for row in rows]


@router.get("/{target_id}", response_model=PublishTargetDetailResponse)
async def get_publish_target(target_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM publish_targets WHERE id=$1 AND owner_id=$2", target_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Publish target not found")
    posts = await pool.fetch(
        "SELECT * FROM publish_posts WHERE publish_target_id=$1 ORDER BY created_at DESC",
        target_id,
    )
    return PublishTargetDetailResponse(**_target_response(row).model_dump(), posts=[_post_response(post) for post in posts])


@router.post("/{target_id}/approve", response_model=PublishTargetResponse)
async def approve_publish_target(target_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE publish_targets
           SET approved_at=now(), status=CASE WHEN status='pending_approval' THEN 'ready' ELSE status END, updated_at=now()
           WHERE id=$1 AND owner_id=$2
           RETURNING *""",
        target_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Publish target not found")
    return _target_response(row)


@router.post("/{target_id}/publish-now")
async def publish_now(target_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM publish_targets WHERE id=$1 AND owner_id=$2", target_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Publish target not found")
    if row["requires_approval"] and not row.get("approved_at"):
        raise HTTPException(status_code=409, detail="Publish target needs approval first")

    media_url = await resolve_publish_media(pool, dict(row))
    await pool.execute(
        "UPDATE publish_targets SET status='queued', media_url=$2, error=NULL, updated_at=now() WHERE id=$1",
        target_id,
        media_url,
    )
    job_id = await pool.fetchval(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('publish',$1,'pending',1,'Queued for publishing','publish_target')
           RETURNING id""",
        target_id,
    )
    await enqueue_job(str(job_id), workload=WORKLOAD_PUBLISH)
    return {"job_id": str(job_id), "publish_target_id": target_id}


@router.post("/{target_id}/retry")
async def retry_publish_target(target_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM publish_targets WHERE id=$1 AND owner_id=$2", target_id, user_id(user))
    if not row:
        raise HTTPException(status_code=404, detail="Publish target not found")
    await pool.execute("UPDATE publish_targets SET status='queued', error=NULL, updated_at=now() WHERE id=$1", target_id)
    job_id = await pool.fetchval(
        """INSERT INTO generation_jobs
           (entity_type, entity_id, status, total_steps, current_step, job_type)
           VALUES ('publish',$1,'pending',1,'Retry queued','publish_target')
           RETURNING id""",
        target_id,
    )
    await enqueue_job(str(job_id), workload=WORKLOAD_PUBLISH)
    return {"job_id": str(job_id), "publish_target_id": target_id}


@router.post("/{target_id}/cancel", response_model=PublishTargetResponse)
async def cancel_publish_target(target_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE publish_targets
           SET status='canceled', error='Canceled by user', updated_at=now()
           WHERE id=$1 AND owner_id=$2 AND status NOT IN ('published','processing')
           RETURNING *""",
        target_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cancelable publish target not found")
    return _target_response(row)
