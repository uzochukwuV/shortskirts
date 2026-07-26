import asyncio
import os

from db.connection import close_pool, init_db
from pipeline.scheduler import enqueue_due_schedules


POLL_SECONDS = int(os.getenv("SCHEDULER_POLL_SECONDS", "60"))


async def main():
    await init_db()
    print(f"[scheduler] started poll={POLL_SECONDS}s")
    try:
        while True:
            queued = await enqueue_due_schedules()
            if queued:
                print(f"[scheduler] queued {len(queued)} schedule jobs")
            await asyncio.sleep(POLL_SECONDS)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())

