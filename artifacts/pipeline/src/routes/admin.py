import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db.connection import get_pool
from models.admin import (
    AdminActivityItem,
    AdminAuthResponse,
    AdminLoginRequest,
    AdminOverviewResponse,
    AdminProfileResponse,
    AdminStorySummary,
    AdminUserDetailResponse,
    AdminUserSummary,
)

router = APIRouter(prefix="/pipeline/admin", tags=["admin"])
security = HTTPBearer(auto_error=False)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
ADMIN_SESSION_TTL_DAYS = int(os.getenv("ADMIN_SESSION_TTL_DAYS", "30"))


def _hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 210_000).hex()
    return f"pbkdf2_sha256$210000${salt}${digest}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _json_value(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value or {}


def _admin_password_matches(password: str) -> bool:
    if ADMIN_PASSWORD_HASH:
        return _verify_password(password, ADMIN_PASSWORD_HASH)
    if ADMIN_PASSWORD is not None:
        return hmac.compare_digest(password, ADMIN_PASSWORD)
    return False


async def _create_session() -> str:
    pool = await get_pool()
    token = secrets.token_urlsafe(40)
    expires_at = datetime.utcnow() + timedelta(days=ADMIN_SESSION_TTL_DAYS)
    await pool.execute(
        """INSERT INTO admin_sessions (token_hash, expires_at)
           VALUES ($1, $2)""",
        _token_hash(token),
        expires_at,
    )
    return token


async def get_current_admin(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required")
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT *
           FROM admin_sessions
           WHERE token_hash=$1 AND expires_at > now()""",
        _token_hash(credentials.credentials),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired admin session")
    await pool.execute("UPDATE admin_sessions SET last_seen_at=now() WHERE id=$1", row["id"])
    return row


def _row_to_story_summary(row) -> AdminStorySummary:
    return AdminStorySummary(
        id=str(row["id"]),
        title=row["title"],
        status=row["status"],
        approval_status=row.get("approval_status", "pending_approval"),
        workflow_type=row.get("workflow_type", "creator_series"),
        workflow_version=row.get("workflow_version"),
        generation_version=row.get("generation_version"),
        episode_count=row.get("episode_count", 0),
        completed_episode_count=row.get("completed_episode_count", 0),
        failed_episode_count=row.get("failed_episode_count", 0),
        job_count=row.get("job_count", 0),
        failed_job_count=row.get("failed_job_count", 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_user_summary(row) -> AdminUserSummary:
    return AdminUserSummary(
        id=str(row["id"]),
        email=row["email"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        story_count=row.get("story_count", 0),
        draft_story_count=row.get("draft_story_count", 0),
        approved_story_count=row.get("approved_story_count", 0),
        generating_story_count=row.get("generating_story_count", 0),
        checkpoint_story_count=row.get("checkpoint_story_count", 0),
        completed_story_count=row.get("completed_story_count", 0),
        failed_story_count=row.get("failed_story_count", 0),
        total_job_count=row.get("total_job_count", 0),
        completed_job_count=row.get("completed_job_count", 0),
        failed_job_count=row.get("failed_job_count", 0),
        last_activity_at=row.get("last_activity_at"),
        last_story_title=row.get("last_story_title"),
        last_story_status=row.get("last_story_status"),
    )


def _admin_profile() -> AdminProfileResponse:
    return AdminProfileResponse(email=ADMIN_EMAIL or "admin", role="admin")


@router.post("/login", response_model=AdminAuthResponse)
async def login(body: AdminLoginRequest):
    email = body.email.strip().lower()
    if not ADMIN_EMAIL or email != ADMIN_EMAIL or not _admin_password_matches(body.password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    token = await _create_session()
    return AdminAuthResponse(token=token, admin=_admin_profile())


@router.get("/me", response_model=AdminProfileResponse)
async def me(admin=Depends(get_current_admin)):
    return _admin_profile()


@router.post("/logout")
async def logout(admin=Depends(get_current_admin)):
    pool = await get_pool()
    await pool.execute("DELETE FROM admin_sessions WHERE id=$1", admin["id"])
    return {"ok": True}


@router.get("/overview", response_model=AdminOverviewResponse)
async def overview(admin=Depends(get_current_admin)):
    pool = await get_pool()
    totals = await pool.fetchrow(
        """
        SELECT
          (SELECT count(*) FROM users) AS total_users,
          (SELECT count(*) FROM stories) AS total_stories,
          (SELECT count(*) FROM episodes) AS total_episodes,
          (SELECT count(*) FROM scenes) AS total_scenes,
          (SELECT count(*) FROM generation_jobs) AS total_jobs,
          (SELECT count(*) FROM generation_jobs WHERE status='pending') AS queued_jobs,
          (SELECT count(*) FROM generation_jobs WHERE status='running') AS running_jobs,
          (SELECT count(*) FROM generation_jobs WHERE status='completed') AS completed_jobs,
          (SELECT count(*) FROM generation_jobs WHERE status='failed') AS failed_jobs,
          (SELECT count(*) FROM stories WHERE status='draft') AS draft_stories,
          (SELECT count(*) FROM stories WHERE status='approved') AS approved_stories,
          (SELECT count(*) FROM stories WHERE status='generating') AS generating_stories,
          (SELECT count(*) FROM stories WHERE status='checkpoint_review') AS checkpoint_stories,
          (SELECT count(*) FROM stories WHERE status='completed' OR status='ready') AS completed_stories,
          (SELECT count(*) FROM stories WHERE status='failed') AS failed_stories
        """
    )

    story_status_breakdown = await pool.fetch(
        "SELECT status, count(*)::int AS count FROM stories GROUP BY status ORDER BY count DESC"
    )
    job_status_breakdown = await pool.fetch(
        "SELECT status, count(*)::int AS count FROM generation_jobs GROUP BY status ORDER BY count DESC"
    )
    daily_activity = await pool.fetch(
        """
        SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day, count(*)::int AS count
        FROM stories
        WHERE created_at >= now() - interval '14 days'
        GROUP BY 1
        ORDER BY 1
        """
    )
    provider_cost = await pool.fetchrow(
        """
        SELECT
          COALESCE(sum(estimated_cost_usd), 0) AS total_cost,
          COALESCE(avg(provider_latency_ms), 0) AS avg_latency_ms,
          COALESCE(max(provider_latency_ms), 0) AS p95_latency_ms
        FROM pipeline_metrics
        """
    )
    top_failure_steps = await pool.fetch(
        """
        SELECT step_name, provider, count(*)::int AS failures
        FROM pipeline_metrics
        WHERE status='failed'
        GROUP BY step_name, provider
        ORDER BY failures DESC, step_name ASC
        LIMIT 8
        """
    )
    recent_failures = await pool.fetch(
        """
        SELECT metric_kind, step_name, provider, error, created_at, entity_type, entity_id
        FROM pipeline_metrics
        WHERE status='failed'
        ORDER BY created_at DESC
        LIMIT 12
        """
    )
    return AdminOverviewResponse(
        totals={
            "total_users": totals["total_users"],
            "total_stories": totals["total_stories"],
            "total_episodes": totals["total_episodes"],
            "total_scenes": totals["total_scenes"],
            "total_jobs": totals["total_jobs"],
            "queued_jobs": totals["queued_jobs"],
            "running_jobs": totals["running_jobs"],
            "completed_jobs": totals["completed_jobs"],
            "failed_jobs": totals["failed_jobs"],
            "draft_stories": totals["draft_stories"],
            "approved_stories": totals["approved_stories"],
            "generating_stories": totals["generating_stories"],
            "checkpoint_stories": totals["checkpoint_stories"],
            "completed_stories": totals["completed_stories"],
            "failed_stories": totals["failed_stories"],
        },
        story_status_breakdown=[{"status": row["status"], "count": row["count"]} for row in story_status_breakdown],
        job_status_breakdown=[{"status": row["status"], "count": row["count"]} for row in job_status_breakdown],
        daily_activity=[{"day": row["day"], "count": row["count"]} for row in daily_activity],
        provider_costs={
            "total_cost": float(provider_cost["total_cost"] or 0),
            "avg_latency_ms": int(provider_cost["avg_latency_ms"] or 0),
            "p95_latency_ms": int(provider_cost["p95_latency_ms"] or 0),
        },
        provider_latency={
            "avg_latency_ms": int(provider_cost["avg_latency_ms"] or 0),
            "p95_latency_ms": int(provider_cost["p95_latency_ms"] or 0),
        },
        top_failure_steps=[
            {"step_name": row["step_name"], "provider": row["provider"], "failures": row["failures"]}
            for row in top_failure_steps
        ],
        recent_failures=[
            {
                "metric_kind": row["metric_kind"],
                "step_name": row["step_name"],
                "provider": row["provider"],
                "error": row["error"],
                "created_at": row["created_at"],
                "entity_type": row["entity_type"],
                "entity_id": str(row["entity_id"]) if row["entity_id"] else None,
            }
            for row in recent_failures
        ],
    )


@router.get("/users", response_model=list[AdminUserSummary])
async def list_users(admin=Depends(get_current_admin)):
    pool = await get_pool()
    rows = await pool.fetch(
        """
        WITH story_stats AS (
          SELECT
            owner_id,
            count(*)::int AS story_count,
            count(*) FILTER (WHERE status='draft')::int AS draft_story_count,
            count(*) FILTER (WHERE status='approved')::int AS approved_story_count,
            count(*) FILTER (WHERE status='generating')::int AS generating_story_count,
            count(*) FILTER (WHERE status='checkpoint_review')::int AS checkpoint_story_count,
            count(*) FILTER (WHERE status IN ('completed', 'ready'))::int AS completed_story_count,
            count(*) FILTER (WHERE status='failed')::int AS failed_story_count,
            max(updated_at) AS last_story_at
          FROM stories
          GROUP BY owner_id
        ),
        job_stats AS (
          SELECT
            s.owner_id,
            count(*)::int AS total_job_count,
            count(*) FILTER (WHERE gj.status='completed')::int AS completed_job_count,
            count(*) FILTER (WHERE gj.status='failed')::int AS failed_job_count,
            max(gj.updated_at) AS last_job_at
          FROM generation_jobs gj
          JOIN stories s ON s.id = gj.entity_id
          WHERE gj.entity_type='story'
          GROUP BY s.owner_id
        )
        SELECT
          u.id, u.email, u.created_at, u.updated_at,
          COALESCE(ss.story_count, 0) AS story_count,
          COALESCE(ss.draft_story_count, 0) AS draft_story_count,
          COALESCE(ss.approved_story_count, 0) AS approved_story_count,
          COALESCE(ss.generating_story_count, 0) AS generating_story_count,
          COALESCE(ss.checkpoint_story_count, 0) AS checkpoint_story_count,
          COALESCE(ss.completed_story_count, 0) AS completed_story_count,
          COALESCE(ss.failed_story_count, 0) AS failed_story_count,
          COALESCE(js.total_job_count, 0) AS total_job_count,
          COALESCE(js.completed_job_count, 0) AS completed_job_count,
          COALESCE(js.failed_job_count, 0) AS failed_job_count,
          GREATEST(u.updated_at, COALESCE(ss.last_story_at, u.updated_at), COALESCE(js.last_job_at, u.updated_at)) AS last_activity_at,
          ls.title AS last_story_title,
          ls.status AS last_story_status
        FROM users u
        LEFT JOIN story_stats ss ON ss.owner_id = u.id
        LEFT JOIN job_stats js ON js.owner_id = u.id
        LEFT JOIN LATERAL (
          SELECT title, status
          FROM stories
          WHERE owner_id = u.id
          ORDER BY updated_at DESC
          LIMIT 1
        ) ls ON true
        ORDER BY last_activity_at DESC NULLS LAST, u.created_at DESC
        """
    )
    return [_row_to_user_summary(row) for row in rows]


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(user_id: str, admin=Depends(get_current_admin)):
    pool = await get_pool()
    user = await pool.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    summary_row = await pool.fetchrow(
        """
        WITH story_stats AS (
          SELECT
            owner_id,
            count(*)::int AS story_count,
            count(*) FILTER (WHERE status='draft')::int AS draft_story_count,
            count(*) FILTER (WHERE status='approved')::int AS approved_story_count,
            count(*) FILTER (WHERE status='generating')::int AS generating_story_count,
            count(*) FILTER (WHERE status='checkpoint_review')::int AS checkpoint_story_count,
            count(*) FILTER (WHERE status IN ('completed', 'ready'))::int AS completed_story_count,
            count(*) FILTER (WHERE status='failed')::int AS failed_story_count,
            max(updated_at) AS last_story_at
          FROM stories
          WHERE owner_id=$1
          GROUP BY owner_id
        ),
        job_stats AS (
          SELECT
            s.owner_id,
            count(*)::int AS total_job_count,
            count(*) FILTER (WHERE gj.status='completed')::int AS completed_job_count,
            count(*) FILTER (WHERE gj.status='failed')::int AS failed_job_count,
            max(gj.updated_at) AS last_job_at
          FROM generation_jobs gj
          JOIN stories s ON s.id = gj.entity_id
          WHERE gj.entity_type='story' AND s.owner_id=$1
          GROUP BY s.owner_id
        )
        SELECT
          u.id, u.email, u.created_at, u.updated_at,
          COALESCE(ss.story_count, 0) AS story_count,
          COALESCE(ss.draft_story_count, 0) AS draft_story_count,
          COALESCE(ss.approved_story_count, 0) AS approved_story_count,
          COALESCE(ss.generating_story_count, 0) AS generating_story_count,
          COALESCE(ss.checkpoint_story_count, 0) AS checkpoint_story_count,
          COALESCE(ss.completed_story_count, 0) AS completed_story_count,
          COALESCE(ss.failed_story_count, 0) AS failed_story_count,
          COALESCE(js.total_job_count, 0) AS total_job_count,
          COALESCE(js.completed_job_count, 0) AS completed_job_count,
          COALESCE(js.failed_job_count, 0) AS failed_job_count,
          GREATEST(u.updated_at, COALESCE(ss.last_story_at, u.updated_at), COALESCE(js.last_job_at, u.updated_at)) AS last_activity_at,
          ls.title AS last_story_title,
          ls.status AS last_story_status
        FROM users u
        LEFT JOIN story_stats ss ON ss.owner_id = u.id
        LEFT JOIN job_stats js ON js.owner_id = u.id
        LEFT JOIN LATERAL (
          SELECT title, status
          FROM stories
          WHERE owner_id = u.id
          ORDER BY updated_at DESC
          LIMIT 1
        ) ls ON true
        WHERE u.id=$1
        """,
        user_id,
    )
    stories = await pool.fetch(
        """
        SELECT
          s.id, s.title, s.status, s.approval_status, s.workflow_type, s.workflow_version,
          s.generation_version, s.created_at, s.updated_at,
          COUNT(DISTINCT e.id)::int AS episode_count,
          COUNT(DISTINCT e.id) FILTER (WHERE e.status IN ('completed', 'ready'))::int AS completed_episode_count,
          COUNT(DISTINCT e.id) FILTER (WHERE e.status='failed')::int AS failed_episode_count,
          COUNT(DISTINCT gj.id)::int AS job_count,
          COUNT(DISTINCT gj.id) FILTER (WHERE gj.status='failed')::int AS failed_job_count
        FROM stories s
        LEFT JOIN episodes e ON e.story_id = s.id
        LEFT JOIN generation_jobs gj ON gj.entity_id = s.id AND gj.entity_type='story'
        WHERE s.owner_id=$1
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT 100
        """,
        user_id,
    )
    jobs = await pool.fetch(
        """
        SELECT
          gj.id, gj.entity_type, gj.entity_id, gj.job_type, gj.status, gj.progress,
          gj.total_steps, gj.current_step, gj.error, gj.result, gj.created_at, gj.updated_at,
          s.title AS story_title
        FROM generation_jobs gj
        LEFT JOIN stories s ON s.id = gj.entity_id AND gj.entity_type='story'
        WHERE s.owner_id=$1
        ORDER BY gj.created_at DESC
        LIMIT 50
        """,
        user_id,
    )
    activity_rows = await pool.fetch(
        """
        SELECT * FROM (
          SELECT 'story'::text AS kind, s.id, s.title, s.status, s.created_at, s.updated_at,
                 jsonb_build_object('workflow_type', s.workflow_type, 'approval_status', s.approval_status) AS metadata
          FROM stories s
          WHERE s.owner_id=$1
          UNION ALL
          SELECT 'job'::text AS kind, gj.id, COALESCE(s.title, gj.entity_id::text), gj.status, gj.created_at, gj.updated_at,
                 jsonb_build_object('entity_type', gj.entity_type, 'job_type', gj.job_type, 'step_name', gj.current_step) AS metadata
          FROM generation_jobs gj
          LEFT JOIN stories s ON s.id = gj.entity_id AND gj.entity_type='story'
          WHERE s.owner_id=$1
        ) activity
        ORDER BY updated_at DESC NULLS LAST, created_at DESC
        LIMIT 20
        """,
        user_id,
    )
    if not summary_row:
        summary_row = user
        summary_row = {
            "id": user["id"],
            "email": user["email"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
            "story_count": 0,
            "draft_story_count": 0,
            "approved_story_count": 0,
            "generating_story_count": 0,
            "checkpoint_story_count": 0,
            "completed_story_count": 0,
            "failed_story_count": 0,
            "total_job_count": 0,
            "completed_job_count": 0,
            "failed_job_count": 0,
            "last_activity_at": user["updated_at"],
            "last_story_title": None,
            "last_story_status": None,
        }
    user_summary = _row_to_user_summary(summary_row)
    return AdminUserDetailResponse(
        user=user_summary,
        stories=[_row_to_story_summary(row) for row in stories],
        recent_jobs=[
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "entity_id": str(row["entity_id"]),
                "job_type": row["job_type"],
                "status": row["status"],
                "progress": row["progress"],
                "total_steps": row["total_steps"],
                "current_step": row["current_step"],
                "error": row["error"],
                "result": _json_value(row["result"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "story_title": row["story_title"],
            }
            for row in jobs
        ],
        recent_activity=[
            AdminActivityItem(
                kind=row["kind"],
                id=str(row["id"]),
                title=row["title"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=_json_value(row["metadata"]),
            )
            for row in activity_rows
        ],
    )


@router.get("/users/{user_id}/stories", response_model=list[AdminStorySummary])
async def get_user_stories(user_id: str, admin=Depends(get_current_admin)):
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT
          s.id, s.title, s.status, s.approval_status, s.workflow_type, s.workflow_version,
          s.generation_version, s.created_at, s.updated_at,
          COUNT(DISTINCT e.id)::int AS episode_count,
          COUNT(DISTINCT e.id) FILTER (WHERE e.status IN ('completed', 'ready'))::int AS completed_episode_count,
          COUNT(DISTINCT e.id) FILTER (WHERE e.status='failed')::int AS failed_episode_count,
          COUNT(DISTINCT gj.id)::int AS job_count,
          COUNT(DISTINCT gj.id) FILTER (WHERE gj.status='failed')::int AS failed_job_count
        FROM stories s
        LEFT JOIN episodes e ON e.story_id = s.id
        LEFT JOIN generation_jobs gj ON gj.entity_id = s.id AND gj.entity_type='story'
        WHERE s.owner_id=$1
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT 100
        """,
        user_id,
    )
    return [_row_to_story_summary(row) for row in rows]
