"""FastAPI entrypoint — Video Magic backend."""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import create_tables
from api.projects import router as projects_router
from api.stripe_routes import router as stripe_router

app = FastAPI(title="Video Magic API", version="1.0.0")

# CORS — allow Next.js dev server + production
origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(projects_router)
app.include_router(stripe_router)

# Serve generated videos as static files
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "./storage/projects"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")


@app.on_event("startup")
async def startup():
    create_tables()


@app.get("/health")
async def health():
    return {"status": "ok"}
