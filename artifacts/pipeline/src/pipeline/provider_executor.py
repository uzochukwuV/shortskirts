from __future__ import annotations

from typing import Any, Awaitable, Callable


class ProviderExecutionError(RuntimeError):
    def __init__(self, message: str, failures: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.failures = failures or []


async def execute_ordered_attempts(
    attempts: list[dict[str, Any]],
    operation: Callable[[dict[str, Any]], Awaitable[str | None]],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    for attempt in attempts:
        try:
            result = await operation(attempt)
            if result:
                return result, attempt, failures
            failures.append({**attempt, "error": "provider returned no result"})
        except Exception as exc:
            failures.append({**attempt, "error": str(exc)[:1000]})
    raise ProviderExecutionError("All provider attempts failed", failures)
