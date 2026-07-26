from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode


def public_backend_url() -> str:
    return (os.getenv("PUBLIC_BACKEND_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000").rstrip("/")


def youtube_authorization_url(owner_id: str) -> tuple[str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise RuntimeError("GOOGLE_CLIENT_ID is required to connect YouTube")
    state = f"{owner_id}:{secrets.token_urlsafe(24)}"
    redirect_uri = f"{public_backend_url()}/pipeline/social/youtube/callback"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}", state


def tiktok_authorization_url(owner_id: str) -> tuple[str, str]:
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    if not client_key:
        raise RuntimeError("TIKTOK_CLIENT_KEY is required to connect TikTok")
    state = f"{owner_id}:{secrets.token_urlsafe(24)}"
    redirect_uri = f"{public_backend_url()}/pipeline/social/tiktok/callback"
    params = {
        "client_key": client_key,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "user.info.basic,video.upload,video.publish",
        "state": state,
    }
    return f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}", state

