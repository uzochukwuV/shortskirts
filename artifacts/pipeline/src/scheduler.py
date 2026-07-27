import asyncio
import os
from dotenv import load_dotenv

from db.connection import close_pool, init_db
from pipeline.scheduler import enqueue_due_schedules
from pipeline.metrics import record_pipeline_metric
# Load .env from pipeline root directory
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(env_path)

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
