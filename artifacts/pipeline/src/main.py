import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.connection import init_db, close_pool
from routes.stories    import router as stories_router
from routes.characters import router as characters_router
from routes.episodes   import router as episodes_router
from routes.scenes     import router as scenes_router
from routes.gallery    import router as gallery_router
from routes.checkpoints import router as checkpoints_router
from routes.bibles     import router as bibles_router
from routes.uploads    import router as uploads_router
from routes.jobs       import router as jobs_router
from routes.admin      import router as admin_router
from auth              import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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
app.include_router(bibles_router)
app.include_router(uploads_router)
app.include_router(jobs_router)
app.include_router(admin_router)


@app.get("/pipeline/health")
async def health():
    return {"status": "ok", "service": "storyforge-anime-pipeline", "version": "2.0.0"}


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
                "PUT    /pipeline/stories/{id}/approve-outline",
                "POST   /pipeline/stories/{id}/generate",
                "GET    /pipeline/stories/{story_id}/checkpoints",
                "PUT    /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/approve",
                "GET    /pipeline/stories/{story_id}/history",
                "GET    /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/history",
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
            ],
        },
    }
