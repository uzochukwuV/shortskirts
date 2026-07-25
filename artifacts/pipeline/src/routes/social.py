from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_current_user, user_id
from db.connection import get_pool
from models.social import OAuthStartResponse, SocialAccountMockCreate, SocialAccountResponse
from pipeline.social.oauth import public_backend_url, tiktok_authorization_url, youtube_authorization_url
from pipeline.social.token_store import encrypt_token

router = APIRouter(prefix="/pipeline/social", tags=["social"])


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


def _account_response(row) -> SocialAccountResponse:
    return SocialAccountResponse(
        id=str(row["id"]),
        platform=row["platform"],
        platform_user_id=row.get("platform_user_id"),
        display_name=row.get("display_name"),
        scopes=_json_array(row.get("scopes")),
        status=row["status"],
        metadata=_json_object(row.get("metadata")),
        token_expires_at=row.get("token_expires_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/accounts", response_model=list[SocialAccountResponse])
async def list_social_accounts(user=Depends(get_current_user)):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM social_accounts WHERE owner_id=$1 ORDER BY created_at DESC",
        user_id(user),
    )
    return [_account_response(row) for row in rows]


@router.post("/accounts/mock", response_model=SocialAccountResponse)
async def create_mock_account(body: SocialAccountMockCreate, user=Depends(get_current_user)):
    pool = await get_pool()
    platform_user_id = body.platform_user_id or f"{body.platform}-{user_id(user)}"
    row = await pool.fetchrow(
        """INSERT INTO social_accounts
           (owner_id, platform, platform_user_id, display_name, scopes, status, metadata)
           VALUES ($1,$2,$3,$4,$5::jsonb,'connected',$6::jsonb)
           ON CONFLICT (owner_id, platform, platform_user_id)
           DO UPDATE SET display_name=excluded.display_name, scopes=excluded.scopes,
                         status='connected', metadata=excluded.metadata, updated_at=now()
           RETURNING *""",
        user_id(user),
        body.platform,
        platform_user_id,
        body.display_name or f"{body.platform.title()} test account",
        json.dumps(body.scopes or ["mock.publish"]),
        json.dumps(body.metadata),
    )
    return _account_response(row)


@router.post("/{platform}/connect", response_model=OAuthStartResponse)
async def start_social_connect(platform: str, user=Depends(get_current_user)):
    try:
        if platform == "youtube":
            url, state = youtube_authorization_url(user_id(user))
        elif platform == "tiktok":
            url, state = tiktok_authorization_url(user_id(user))
        else:
            raise HTTPException(status_code=400, detail="Unsupported platform")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OAuthStartResponse(authorization_url=url, state=state)


@router.get("/youtube/callback")
async def youtube_callback(code: str = Query(...), state: str = Query(...)):
    owner_id = state.split(":", 1)[0]
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Google OAuth credentials are not configured")
    redirect_uri = f"{public_backend_url()}/pipeline/social/youtube/callback"
    async with httpx.AsyncClient(timeout=60) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = int(token_data.get("expires_in") or 3600)
        profile_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()
    item = (profile.get("items") or [{}])[0]
    platform_user_id = item.get("id") or f"youtube-{owner_id}"
    display_name = ((item.get("snippet") or {}).get("title")) or "YouTube channel"
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO social_accounts
           (owner_id, platform, platform_user_id, display_name, scopes, token_encrypted,
            refresh_token_encrypted, token_expires_at, status, metadata)
           VALUES ($1,'youtube',$2,$3,$4::jsonb,$5,$6,$7,'connected',$8::jsonb)
           ON CONFLICT (owner_id, platform, platform_user_id)
           DO UPDATE SET display_name=excluded.display_name, scopes=excluded.scopes,
                         token_encrypted=excluded.token_encrypted,
                         refresh_token_encrypted=COALESCE(excluded.refresh_token_encrypted, social_accounts.refresh_token_encrypted),
                         token_expires_at=excluded.token_expires_at, status='connected',
                         metadata=excluded.metadata, updated_at=now()""",
        owner_id,
        platform_user_id,
        display_name,
        json.dumps(["youtube.upload"]),
        encrypt_token(access_token),
        encrypt_token(refresh_token),
        datetime.utcnow() + timedelta(seconds=expires_in),
        json.dumps({"profile": profile}),
    )
    return {"ok": True, "platform": "youtube", "display_name": display_name}


@router.get("/tiktok/callback")
async def tiktok_callback(code: str = Query(...), state: str = Query(...)):
    owner_id = state.split(":", 1)[0]
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
    if not client_key or not client_secret:
        raise HTTPException(status_code=400, detail="TikTok OAuth credentials are not configured")
    redirect_uri = f"{public_backend_url()}/pipeline/social/tiktok/callback"
    async with httpx.AsyncClient(timeout=60) as client:
        token_resp = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    open_id = token_data.get("open_id") or f"tiktok-{owner_id}"
    expires_in = int(token_data.get("expires_in") or 86400)
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO social_accounts
           (owner_id, platform, platform_user_id, display_name, scopes, token_encrypted,
            refresh_token_encrypted, token_expires_at, status, metadata)
           VALUES ($1,'tiktok',$2,$3,$4::jsonb,$5,$6,$7,'connected',$8::jsonb)
           ON CONFLICT (owner_id, platform, platform_user_id)
           DO UPDATE SET display_name=excluded.display_name, scopes=excluded.scopes,
                         token_encrypted=excluded.token_encrypted,
                         refresh_token_encrypted=COALESCE(excluded.refresh_token_encrypted, social_accounts.refresh_token_encrypted),
                         token_expires_at=excluded.token_expires_at, status='connected',
                         metadata=excluded.metadata, updated_at=now()""",
        owner_id,
        open_id,
        "TikTok account",
        json.dumps(["video.upload", "video.publish"]),
        encrypt_token(access_token),
        encrypt_token(refresh_token),
        datetime.utcnow() + timedelta(seconds=expires_in),
        json.dumps({"token_response": {k: v for k, v in token_data.items() if "token" not in k}}),
    )
    return {"ok": True, "platform": "tiktok"}


@router.delete("/accounts/{account_id}")
async def disconnect_social_account(account_id: str, user=Depends(get_current_user)):
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE social_accounts
           SET status='disconnected', updated_at=now()
           WHERE id=$1 AND owner_id=$2
           RETURNING *""",
        account_id,
        user_id(user),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Social account not found")
    return {"ok": True}

