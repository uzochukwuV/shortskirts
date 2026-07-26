from fastapi.staticfiles import StaticFiles

from main import app


app.mount("/", StaticFiles(directory="/root/project/dist/public", html=True), name="static")
