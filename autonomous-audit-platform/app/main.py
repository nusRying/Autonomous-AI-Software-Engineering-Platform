"""
FastAPI application entry point.

Startup flow:
1. App lifespan starts → creates DB tables, ensures output dir exists
2. Routers are included → /health, /api/auth, /api/api_keys, /audit
3. Uvicorn serves the app
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import init_db
from app.api.routes.health import router as health_router
from app.api.routes.api_keys import router as api_keys_router
from app.api.routes.audit import router as audit_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.engineer import router as engineer_router
from app.api.routes.dashboard import router as dashboard_router

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus instrumentator not available — metrics endpoint will be disabled.")

async def init_admin():
    """Create a default admin user if the database is empty."""
    from app.database import AsyncSessionLocal
    from app.db.models import UserDB, UserRole
    from app.utils.security import get_password_hash
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserDB).limit(1))
        if not result.scalar_one_or_none():
            logger.info("Initializing default admin user...")
            admin = UserDB(
                username="admin",
                email="admin@audit.platform",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
            )
            db.add(admin)
            await db.commit()
            logger.info("Default admin user created: admin / admin123")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    # ── Startup ──
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Create DB tables
    await init_db()
    logger.info("Database initialized")

    # Create default admin
    await init_admin()

    # Ensure audit report output directory exists
    os.makedirs(settings.audit_output_dir, exist_ok=True)
    logger.info(f"Audit output directory: {settings.audit_output_dir}")

    # Initialize MinIO
    if settings.use_minio:
        try:
            from app.utils.storage import storage_client
            await storage_client.ensure_bucket_exists()
            logger.info("MinIO bucket initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")

    yield  # App is now running

    # ── Shutdown ──
    logger.info("Shutting down...")


# ── Create FastAPI app ──
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Autonomous Software Engineering Platform — Milestone 1 MVP. "
        "Manages LLM API keys and runs automated software audits."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
 
# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development; adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Instrument app
if PROMETHEUS_AVAILABLE:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Observability"])

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")

# ── Include routers ──
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(audit_router)
app.include_router(analytics_router)
app.include_router(engineer_router)
app.include_router(dashboard_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
