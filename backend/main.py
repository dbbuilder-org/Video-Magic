"""FastAPI entrypoint — Video Magic backend."""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import create_tables, reset_orphaned_projects
from model_config import resolve_models, _resolved
from api.projects import router as projects_router
from api.stripe_routes import router as stripe_router
from api.users import router as users_router
from api.proxy_guard import require_proxy_secret

app = FastAPI(title="Video Magic API", version="1.0.0")

# Proxy gate. Registered before CORS so that CORS remains the outermost
# middleware and preflight requests are still answered. This service is
# deployed as its own public web service (see render.yaml), so without this
# gate the X-User-Id and X-User-Email headers are self-asserted by whoever
# calls it.
app.middleware("http")(require_proxy_secret)

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
app.include_router(users_router)

# Serve generated videos as static files
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "./storage/projects"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")


@app.on_event("startup")
async def startup():
    create_tables()
    reset_orphaned_projects()
    resolve_models()


@app.get("/health")
async def health():
    import models as _models
    return {"status": "ok", "models": _resolved, "db": str(_models.DATABASE_PATH)}
