from contextlib import asynccontextmanager
from contextvars import ContextVar

_job_context: ContextVar[dict | None] = ContextVar("job_context", default=None)


def get_job_context() -> dict | None:
    return _job_context.get()


@asynccontextmanager
async def job_context(**kwargs):
    token = _job_context.set(kwargs)
    try:
        yield kwargs
    finally:
        _job_context.reset(token)
