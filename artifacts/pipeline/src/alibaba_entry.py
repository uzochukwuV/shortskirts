from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Import the main app with all API routes
from main import app as main_app, init_db, close_pool

# Create a new app with SPA fallback
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to init DB, but don't fail if it doesn't work
    try:
        await init_db()
    except Exception as e:
        print(f"Database init failed (will retry on first request): {e}")
    yield
    try:
        await close_pool()
    except:
        pass

app = FastAPI(lifespan=lifespan)

# Include all routes from main app
for route in main_app.routes:
    app.routes.append(route)

# Mount static files for assets
app.mount("/assets", StaticFiles(directory="/root/project/dist/public/assets"), name="assets")

# Catch-all route for SPA - must come last
@app.get("/{path:path}")
async def serve_spa(path: str):
    return FileResponse("/root/project/dist/public/index.html")

@app.get("/")
async def serve_root():
    return FileResponse("/root/project/dist/public/index.html")
