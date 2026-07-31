import asyncpg
import os
import ssl
import re
from typing import Optional

# Load .env if not already loaded
def _load_env():
    if os.environ.get("COCKROACHDB_URL"):
        return  # Already loaded
    try:
        from dotenv import load_dotenv
        # Try multiple possible locations for .env
        # Use normpath to resolve .. in paths
        possible_paths = [
            os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env")),
            os.path.join(os.path.dirname(__file__), ".env"),
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.getcwd(), "..", ".env"),
            ".env",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                load_dotenv(path)
                print(f"[db] Loaded env from {path}")
                return
        print(f"[db] Warning: Could not find .env file in any of: {possible_paths}")
    except Exception as e:
        print(f"[db] Warning: Could not load .env file: {e}")

_load_env()

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = os.environ["COCKROACHDB_URL"]
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        async def init_connection(conn):
            # Enable multiple active portals for CockroachDB compatibility
            await conn.execute("SET multiple_active_portals_enabled = true")
        
        _pool = await asyncpg.create_pool(
            url,
            ssl=ssl_ctx,
            min_size=2,
            max_size=10,
            command_timeout=60,
            init=init_connection,
            statement_cache_size=0,  # Disable statement caching for CockroachDB compatibility
        )
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _split_statements(sql: str) -> list[str]:
    # Remove comment lines, split on semicolons
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

        # Backfill media URLs for older narrated-image scenes where the asset was
        # written into JSON metadata before the dedicated column existed.
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
