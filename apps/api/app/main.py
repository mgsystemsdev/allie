from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import care, core, extras, feeds, settings

settings_env = get_settings()
Path(settings_env.upload_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Allie Care API", version="1.0.0")

origins = {
    settings_env.web_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core.router)
app.include_router(feeds.router)
app.include_router(care.router)
app.include_router(extras.router)
app.include_router(settings.router)

app.mount("/uploads", StaticFiles(directory=settings_env.upload_dir), name="uploads")
