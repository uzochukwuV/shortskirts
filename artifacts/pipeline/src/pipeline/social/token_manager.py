"""
Token Manager - Secure token storage and refresh

Handles:
- Encrypted token storage in DB
- Automatic token refresh for YouTube/TikTok
- Token retrieval with automatic refresh if expired
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from db.connection import get_pool
from pipeline.social.token_store import encrypt_token, decrypt_token


def public_backend_url() -> str:
    import os
    return (os.getenv("PUBLIC_BACKEND_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000").rstrip("/")


async def get_youtube_token(account_id: str) -> tuple[str, bool]:
    """
    Get YouTube access token, refreshing if expired.
    
    Returns (access_token, was_refreshed).
    """
    pool = await get_pool()
    account = await pool.fetchrow(
        "SELECT * FROM social_accounts WHERE id=$1 AND platform='youtube'",
        account_id,
    )
    
    if not account:
        raise ValueError(f"Social account {account_id} not found")
    
    # Check if token is expired
    expires_at = account.get("token_expires_at")
    if expires_at and expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        # Token still valid
        access_token = decrypt_token(account.get("token_encrypted"))
        return access_token, False
    
    # Token expired - refresh it
    refresh_token = decrypt_token(account.get("refresh_token_encrypted"))
    if not refresh_token:
        raise ValueError("No refresh token available for YouTube")
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured")
    
    redirect_uri = f"{public_backend_url()}/pipeline/social/youtube/callback"
    
    async with httpx.AsyncClient(timeout=60) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    
    new_access_token = token_data.get("access_token")
    new_expires_in = int(token_data.get("expires_in") or 3600)
    new_refresh_token = token_data.get("refresh_token") or refresh_token
    
    # Update in DB
    await pool.execute(
        """UPDATE social_accounts
           SET token_encrypted=$2, refresh_token_encrypted=$3,
               token_expires_at=$4, updated_at=now()
           WHERE id=$1""",
        account_id,
        encrypt_token(new_access_token),
        encrypt_token(new_refresh_token),
        datetime.now(timezone.utc) + timedelta(seconds=new_expires_in),
    )
    
    return new_access_token, True


async def get_tiktok_token(account_id: str) -> tuple[str, bool]:
    """
    Get TikTok access token, refreshing if expired.
    
    Returns (access_token, was_refreshed).
    """
    pool = await get_pool()
    account = await pool.fetchrow(
        "SELECT * FROM social_accounts WHERE id=$1 AND platform='tiktok'",
        account_id,
    )
    
    if not account:
        raise ValueError(f"Social account {account_id} not found")
    
    # Check if token is expired
    expires_at = account.get("token_expires_at")
    if expires_at and expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        access_token = decrypt_token(account.get("token_encrypted"))
        return access_token, False
    
    # Token expired - refresh it
    refresh_token = decrypt_token(account.get("refresh_token_encrypted"))
    if not refresh_token:
        raise ValueError("No refresh token available for TikTok")
    
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
    if not client_key or not client_secret:
        raise ValueError("TikTok OAuth credentials not configured")
    
    async with httpx.AsyncClient(timeout=60) as client:
        token_resp = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    
    new_access_token = token_data.get("access_token")
    new_expires_in = int(token_data.get("expires_in") or 86400)
    new_refresh_token = token_data.get("refresh_token") or refresh_token
    
    # Update in DB
    await pool.execute(
        """UPDATE social_accounts
           SET token_encrypted=$2, refresh_token_encrypted=$3,
               token_expires_at=$4, updated_at=now()
           WHERE id=$1""",
        account_id,
        encrypt_token(new_access_token),
        encrypt_token(new_refresh_token),
        datetime.now(timezone.utc) + timedelta(seconds=new_expires_in),
    )
    
    return new_access_token, True


async def get_social_token(account_id: str) -> str:
    """
    Get access token for any platform, refreshing if needed.
    
    Returns the access token.
    """
    pool = await get_pool()
    account = await pool.fetchrow("SELECT * FROM social_accounts WHERE id=$1", account_id)
    
    if not account:
        raise ValueError(f"Social account {account_id} not found")
    
    platform = account["platform"]
    
    if platform == "youtube":
        token, _ = await get_youtube_token(account_id)
        return token
    elif platform == "tiktok":
        token, _ = await get_tiktok_token(account_id)
        return token
    elif platform == "mock":
        return decrypt_token(account.get("token_encrypted")) or "mock-token"
    else:
        raise ValueError(f"Unsupported platform: {platform}")


async def store_social_token(
    owner_id: str,
    platform: str,
    platform_user_id: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_in: int,
    scopes: list[str],
    display_name: str = "",
    metadata: Optional[dict] = None,
) -> str:
    """
    Store a new social account token in the database.
    
    Returns the account ID.
    """
    pool = await get_pool()
    metadata = metadata or {}
    
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    row = await pool.fetchrow(
        """INSERT INTO social_accounts
           (owner_id, platform, platform_user_id, display_name, scopes,
            token_encrypted, refresh_token_encrypted, token_expires_at, status, metadata)
           VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,'connected',$9::jsonb)
           ON CONFLICT (owner_id, platform, platform_user_id)
           DO UPDATE SET display_name=excluded.display_name, scopes=excluded.scopes,
                         token_encrypted=excluded.token_encrypted,
                         refresh_token_encrypted=COALESCE(excluded.refresh_token_encrypted, social_accounts.refresh_token_encrypted),
                         token_expires_at=excluded.token_expires_at, status='connected',
                         metadata=excluded.metadata, updated_at=now()
           RETURNING id""",
        owner_id,
        platform,
        platform_user_id,
        display_name or f"{platform.title()} account",
        __import__("json").dumps(scopes),
        encrypt_token(access_token),
        encrypt_token(refresh_token),
        expires_at,
        __import__("json").dumps(metadata),
    )
    
    return str(row["id"])


async def is_token_valid(account_id: str) -> bool:
    """Check if a token is still valid (not expired)."""
    pool = await get_pool()
    account = await pool.fetchrow(
        "SELECT token_expires_at FROM social_accounts WHERE id=$1 AND status='connected'",
        account_id,
    )
    
    if not account:
        return False
    
    expires_at = account.get("token_expires_at")
    if not expires_at:
        return True  # No expiry info, assume valid
    
    return expires_at > datetime.now(timezone.utc)


async def disconnect_account(account_id: str, owner_id: str) -> bool:
    """Disconnect a social account."""
    pool = await get_pool()
    result = await pool.execute(
        """UPDATE social_accounts
           SET status='disconnected', updated_at=now()
           WHERE id=$1 AND owner_id=$2""",
        account_id,
        owner_id,
    )
    return "UPDATE 1" in result
