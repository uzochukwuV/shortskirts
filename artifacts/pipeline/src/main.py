import os
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from the pipeline root (parent of src/)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

from db.connection import init_db, close_pool
from routes.stories    import router as stories_router
from routes.characters import router as characters_router
from routes.episodes   import router as episodes_router
from routes.scenes     import router as scenes_router
from routes.gallery    import router as gallery_router
from routes.checkpoints import router as checkpoints_router, narration_router
from routes.providers  import router as providers_router
from routes.bibles     import router as bibles_router
from routes.uploads    import router as uploads_router
from routes.jobs       import router as jobs_router
from routes.admin      import router as admin_router
from routes.pipeline_runs import router as pipeline_runs_router
from routes.publish    import router as publish_router
from routes.schedules  import router as schedules_router
from routes.social     import router as social_router
from routes.stream     import router as stream_router
from routes.chat       import router as chat_router
from routes.agent      import router as agent_router
from auth              import router as auth_router
from pipeline.media_tools import ffmpeg_available, ffmpeg_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database with timeout to prevent hanging
    try:
        await asyncio.wait_for(init_db(), timeout=30.0)
        print("[startup] Database initialized successfully")
    except asyncio.TimeoutError:
        print("[startup] WARNING: Database initialization timed out, continuing anyway")
    except Exception as e:
        print(f"[startup] WARNING: Database initialization failed: {e}, continuing anyway")
    yield
    await close_pool()


app = FastAPI(
    title="StoryForge Anime API",
    description="AI Showrunner for branded short-form video series",
    version="2.0.0",
    lifespan=lifespan,
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$',
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(stories_router)
app.include_router(characters_router)
app.include_router(episodes_router)
app.include_router(scenes_router)
app.include_router(gallery_router)
app.include_router(checkpoints_router)
app.include_router(narration_router)
app.include_router(providers_router)
app.include_router(bibles_router)
app.include_router(uploads_router)
app.include_router(jobs_router)
app.include_router(admin_router)
app.include_router(pipeline_runs_router)
app.include_router(social_router)
app.include_router(publish_router)
app.include_router(schedules_router)
app.include_router(stream_router)
app.include_router(chat_router)
app.include_router(agent_router)


@app.get("/pipeline/health")
async def health():
    return {
        "status": "ok",
        "service": "storyforge-anime-pipeline",
        "version": "2.0.0",
        "media": {
            "ffmpeg_available": ffmpeg_available(),
            "ffmpeg_path": ffmpeg_path(),
        },
    }
