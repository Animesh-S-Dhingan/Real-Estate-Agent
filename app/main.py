"""EstateAI FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.errors import APIError, api_error_handler, error_body
from app import models  # noqa: F401 — register models

settings = get_settings()


def _ensure_data_dir() -> None:
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_data_dir()
    Base.metadata.create_all(bind=engine)
    # Auto-seed if empty
    from app.seed import seed_if_empty

    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "EstateAI — AI-powered property discovery, neighbourhood intelligence, "
        "and investment analysis for Delhi NCR (FastAPI)."
    ),
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(APIError, api_error_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    body = error_body("INTERNAL_ERROR", "An unexpected error occurred.")
    if settings.debug:
        body["error"]["message"] = f"An unexpected error occurred: {exc}"
    return JSONResponse(status_code=500, content=body)


app.include_router(api_router, prefix=settings.api_prefix)

# Also expose legacy top-level aliases used by older frontend workers
from app.api.v1 import ai as ai_routes

app.include_router(ai_routes.router, tags=["legacy"])


@app.get("/")
def root():
    return {
        "status": "ok",
        "product": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": settings.api_prefix,
        "geography": "Delhi NCR",
    }


# Serve frontend statically when present
frontend_dir = Path(__file__).resolve().parents[1] / "Frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
