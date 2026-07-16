import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from db.connection import get_pool

SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
PBKDF2_ITERATIONS = 210_000
security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/pipeline/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=256)


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


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


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _user_response(row) -> UserResponse:
    return UserResponse(
        id=str(row["id"]),
        email=row["email"],
        created_at=row["created_at"],
    )


async def _create_session(user_id: str) -> str:
    pool = await get_pool()
    token = secrets.token_urlsafe(40)
    expires_at = datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)
    await pool.execute(
        """INSERT INTO auth_sessions (user_id, token_hash, expires_at)
           VALUES ($1, $2, $3)""",
        user_id,
        _hash_token(token),
        expires_at,
    )
    return token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    pool = await get_pool()
    token_hash = _hash_token(credentials.credentials)
    row = await pool.fetchrow(
        """SELECT u.*
           FROM auth_sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.token_hash=$1 AND s.expires_at > now()""",
        token_hash,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return row


def user_id(user) -> str:
    return str(user["id"])


@router.post("/register", response_model=AuthResponse)
async def register(body: AuthRequest):
    pool = await get_pool()
    email = _normalize_email(body.email)
    password_hash = _hash_password(body.password)
    try:
        row = await pool.fetchrow(
            """INSERT INTO users (email, password_hash)
               VALUES ($1, $2)
               RETURNING *""",
            email,
            password_hash,
        )
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Email is already registered")
        raise
    token = await _create_session(str(row["id"]))
    return AuthResponse(token=token, user=_user_response(row))


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE email=$1",
        _normalize_email(body.email),
    )
    if not row or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = await _create_session(str(row["id"]))
    return AuthResponse(token=token, user=_user_response(row))


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return _user_response(user)


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if credentials:
        pool = await get_pool()
        await pool.execute(
            "DELETE FROM auth_sessions WHERE token_hash=$1",
            _hash_token(credentials.credentials),
        )
    return {"ok": True}
