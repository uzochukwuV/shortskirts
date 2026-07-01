import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.connection import init_db, close_pool
from routes.stories import router as stories_router
from routes.characters import router as characters_router
from routes.episodes import router as episodes_router
from routes.jobs import router as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_pool()


app = FastAPI(
    title="StoryForge Anime API",
    description="Agentic AI anime story generation pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stories_router)
app.include_router(characters_router)
app.include_router(episodes_router)
app.include_router(jobs_router)


@app.get("/pipeline/health")
async def health():
    return {"status": "ok", "service": "storyforge-anime-pipeline"}


@app.get("/pipeline")
async def root():
    return {
        "service": "StoryForge Anime Pipeline",
        "version": "1.0.0",
        "endpoints": [
            "POST /pipeline/stories",
            "GET  /pipeline/stories",
            "GET  /pipeline/stories/{id}",
            "POST /pipeline/stories/{id}/generate",
            "POST /pipeline/characters",
            "GET  /pipeline/characters/story/{story_id}",
            "GET  /pipeline/characters/{id}",
            "GET  /pipeline/episodes/story/{story_id}",
            "GET  /pipeline/episodes/{id}",
            "GET  /pipeline/jobs/{id}",
            "GET  /pipeline/jobs/entity/{type}/{entity_id}",
        ],
    }
