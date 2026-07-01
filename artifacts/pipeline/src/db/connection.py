import asyncpg
import os
import ssl
import re
from typing import Optional

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = os.environ["COCKROACHDB_URL"]
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        _pool = await asyncpg.create_pool(
            url,
            ssl=ssl_ctx,
            min_size=2,
            max_size=10,
            command_timeout=60,
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
