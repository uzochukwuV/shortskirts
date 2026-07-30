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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


@app.get("/pipeline")
async def root():
    return {
        "service": "StoryForge Anime Pipeline",
        "version": "2.0.0",
        "features": [
            "workflow_types: creator_series|brand_campaign|social_short|educational|game_lore|narrated_image_story",
            "approval_gates: outline, characters, scenes",
            "checkpoint_reviews: pause every 3 narrated-image scenes for human approval",
            "granular_regeneration: per-scene, per-character-refs",
            "brand_bibles: brand|character|world|campaign memory",
        ],
        "endpoints": {
            "stories": [
                "POST   /pipeline/stories",
                "GET    /pipeline/stories",
                "GET    /pipeline/stories/{id}",
                "GET    /pipeline/stories/{id}/capabilities",
                "POST   /pipeline/stories/{id}/operations-agent",
                "PUT    /pipeline/stories/{id}/approve-outline",
                "POST   /pipeline/stories/{id}/regenerate-outline",
                "POST   /pipeline/stories/{id}/generate",
                "GET    /pipeline/stories/{story_id}/checkpoints",
                "PUT    /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/approve",
                "POST   /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/audio/regenerate",
                "PUT    /pipeline/stories/{story_id}/pipeline-config",
                "GET    /pipeline/stories/{story_id}/history",
                "GET    /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/history",
            ],
            "narration": [
                "GET    /pipeline/narration/voices",
            ],
            "providers": [
                "GET    /pipeline/providers/status",
            ],
            "pipeline_runs": [
                "GET    /pipeline/runs/story/{story_id}",
                "GET    /pipeline/runs/{run_id}",
                "GET    /pipeline/runs/{run_id}/steps",
                "GET    /pipeline/runs/{run_id}/artifacts",
                "GET    /pipeline/runs/steps/{step_id}",
                "POST   /pipeline/runs/steps/{step_id}/retry",
                "POST   /pipeline/runs/{run_id}/cancel",
            ],
            "bibles": [
                "POST   /pipeline/bibles",
                "GET    /pipeline/bibles/story/{story_id}",
                "GET    /pipeline/bibles/{id}",
                "PUT    /pipeline/bibles/{id}",
                "DELETE /pipeline/bibles/{id}",
            ],
            "characters": [
                "POST   /pipeline/characters",
                "GET    /pipeline/characters/story/{story_id}",
                "GET    /pipeline/characters/{id}",
                "PUT    /pipeline/characters/{id}/approve",
                "PUT    /pipeline/characters/{id}/lock",
                "POST   /pipeline/characters/{id}/regenerate-refs",
            ],
            "scenes": [
                "GET    /pipeline/scenes/{id}",
                "PUT    /pipeline/scenes/{id}/approve",
                "PUT    /pipeline/scenes/{id}/reject",
                "PUT    /pipeline/scenes/{id}/lock",
                "POST   /pipeline/scenes/{id}/regenerate",
                "GET    /pipeline/scenes/{id}/history",
            ],
            "episodes": [
                "GET    /pipeline/episodes/story/{story_id}",
                "GET    /pipeline/episodes/{id}",
            ],
            "gallery": [
                "GET    /pipeline/gallery",
            ],
            "uploads": [
                "POST   /pipeline/uploads/image",
            ],
            "jobs": [
                "GET    /pipeline/jobs/{id}",
                "GET    /pipeline/jobs/entity/{type}/{entity_id}",
                "POST   /pipeline/jobs/{id}/cancel",
                "POST   /pipeline/jobs/{id}/retry",
            ],
            "social": [
                "GET    /pipeline/social/accounts",
                "POST   /pipeline/social/accounts/mock",
                "POST   /pipeline/social/{platform}/connect",
                "GET    /pipeline/social/{platform}/callback",
                "DELETE /pipeline/social/accounts/{account_id}",
            ],
            "publishing": [
                "POST   /pipeline/publish-targets",
                "GET    /pipeline/publish-targets",
                "GET    /pipeline/publish-targets/{target_id}",
                "POST   /pipeline/publish-targets/{target_id}/approve",
                "POST   /pipeline/publish-targets/{target_id}/publish-now",
                "POST   /pipeline/publish-targets/{target_id}/retry",
                "POST   /pipeline/publish-targets/{target_id}/cancel",
            ],
            "schedules": [
                "POST   /pipeline/schedules",
                "GET    /pipeline/schedules",
                "GET    /pipeline/schedules/{schedule_id}",
                "PATCH  /pipeline/schedules/{schedule_id}",
                "DELETE /pipeline/schedules/{schedule_id}",
                "POST   /pipeline/schedules/{schedule_id}/run-now",
                "POST   /pipeline/schedules/dispatch-due",
                "GET    /pipeline/schedules/{schedule_id}/runs",
            ],
        },
    }