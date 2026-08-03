import os
import ssl
from typing import Optional

import asyncpg
from fastapi import HTTPException, status


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    possible_paths = [
        os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env")),
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "..", ".env"),
        ".env",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            load_dotenv(path, override=False)
            print(f"[db] Loaded env from {path}")
            return

    print(f"[db] Warning: Could not find .env file in any of: {possible_paths}")


_load_env()

_pool: Optional[asyncpg.Pool] = None


def _clean_url(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().strip('"').strip("'")
    return cleaned or None


def _resolve_db_url() -> str:
    for key in ("COCKROACHDB_URL", "DATABASE_URL", "NEW_DB"):
        url = _clean_url(os.environ.get(key))
        if url:
            return url
    raise RuntimeError("No database connection string found. Set COCKROACHDB_URL or DATABASE_URL.")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    url = _resolve_db_url()
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async def init_connection(conn):
        await conn.execute("SET multiple_active_portals_enabled = true")

    try:
        _pool = await asyncpg.create_pool(
            url,
            ssl=ssl_ctx,
            min_size=2,
            max_size=10,
            command_timeout=60,
            init=init_connection,
            statement_cache_size=0,
        )
        return _pool
    except Exception as exc:
        _pool = None
        print(f"[db] Failed to create pool: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _split_statements(sql: str) -> list[str]:
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        lines.append(line)
    text = "\n".join(lines)
    stmts = [s.strip() for s in text.split(";")]
    return [s for s in stmts if s]


async def init_db():
    pool = await get_pool()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        schema = f.read()

    statements = _split_statements(schema)
    async with pool.acquire() as conn:
        for stmt in statements:
            try:
                await conn.execute(stmt)
            except Exception as e:
                err = str(e).lower()
                if any(x in err for x in ["already exists", "duplicate", "relation already"]):
                    pass
                else:
                    print(f"[db] Warning on stmt: {e}\nStatement: {stmt[:120]}")

        repair_statements = [
            """
            UPDATE scenes
            SET image_url = COALESCE(image_url, generation_metadata->>'image_url', state_snapshot->>'media_url'),
                updated_at = COALESCE(updated_at, now())
            WHERE image_url IS NULL
              AND (generation_metadata->>'image_url' IS NOT NULL OR state_snapshot->>'media_url' IS NOT NULL)
            """,
        ]
        for stmt in repair_statements:
            try:
                await conn.execute(stmt)
            except Exception as e:
                print(f"[db] Warning on repair stmt: {e}\nStatement: {stmt[:120]}")
