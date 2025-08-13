"""
FastAPI application entrypoint for Auto-EDA MVP
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down shared resources once per process."""
    # Ensure storage directory exists
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)

    # --- DB init ---
    try:
        from app.core import db as core_db  # lazy import to avoid cycles
        engine, SessionLocal = core_db.init_engine_and_session(settings.DATABASE_URL)
        app.state.db_engine = engine
        app.state.SessionLocal = SessionLocal
        logger.info("db.initialized", url=settings.DATABASE_URL)
        # Optional: create tables for user model
        try:
            from app.models.user import ensure_tables
            ensure_tables(engine)
            logger.info("db.tables.ready")
        except Exception as te:
            logger.warning("db.tables.failed", error=str(te))
    except Exception as e:
        logger.warning("db.init_failed", error=str(e))
        app.state.db_engine = None
        app.state.SessionLocal = None

    # --- Queue init (guarded) ---
    if bool(getattr(settings, "USE_REDIS", False)):
        try:
            import redis  # type: ignore
            from rq import Queue  # type: ignore
            app.state.redis = redis.from_url(settings.REDIS_URL)
            app.state.rq_queue = Queue("default", connection=app.state.redis)
            logger.info("redis.queue.ready", url=settings.REDIS_URL)
        except Exception as e:
            logger.warning("redis.init_failed", error=str(e))
            app.state.redis = None
            app.state.rq_queue = None
    else:
        app.state.redis = None
        app.state.rq_queue = None
        logger.info("redis.disabled", reason="USE_REDIS is false (settings)")

    app.state.storage_dir = settings.STORAGE_DIR

    # ---- app runs ----
    yield

    # --- Teardown ---
    try:
        if getattr(app.state, "db_engine", None) is not None:
            app.state.db_engine.dispose()
            logger.info("db.engine.disposed")
    except Exception as e:
        logger.warning("db.dispose_failed", error=str(e))


# Create app AFTER lifespan is defined
app = FastAPI(title=settings.APP_NAME, version=settings.API_VERSION, lifespan=lifespan)

# ----- Compat alias: /job/run -> /jobs/run -----------------------------------
@app.post("/job/run", include_in_schema=False)
def jobs_alias(dataset_id: str):
    return RedirectResponse(url=f"/jobs/run?dataset_id={dataset_id}", status_code=307)


# ----- Static files / favicon -------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico", media_type="image/x-icon")


# ----- Middleware -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Error handlers ---------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.warning("request.validation_error", detail=str(exc))
    return JSONResponse(status_code=422, content={"error": "Validation failed", "details": exc.errors()})


# ----- Routers ----------------------------------------------------------------
try:
    from app.api import auth, datasets, jobs, reports
    app.include_router(auth.router,     prefix="/auth",     tags=["auth"])
    app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
    app.include_router(jobs.router,     prefix="/jobs",     tags=["jobs"])
    app.include_router(reports.router,  prefix="/reports",  tags=["reports"])
    logger.info("routers.registered")
except Exception as e:
    logger.warning("routers.register_failed", error=str(e))


# ----- Health -----------------------------------------------------------------
@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.API_VERSION, "env": settings.APP_ENV, "status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz():
    details = {
        "db": bool(getattr(app.state, "db_engine", None)),
        "queue": bool(getattr(app.state, "rq_queue", None)),
        "storage": os.path.isdir(settings.STORAGE_DIR),
    }
    ready = details["storage"] and details["db"] and (
        details["queue"] if bool(getattr(settings, "USE_REDIS", False)) else True
    )
    return {"ready": ready, "details": details}
