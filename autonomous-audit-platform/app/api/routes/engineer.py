"""
Engineer API routes.
"""
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from pydantic import BaseModel

from app.database import AsyncSessionLocal, get_db
from app.db.models import EngineerJobDB, UserDB, UserRole
from app.config import settings
from app.utils.security import get_current_user, dev_required

router = APIRouter(prefix="/engineer", tags=["Autonomous Engineer"])

# ── Celery Task (Fallback) ───────────────────────────────────────────────────

try:
    from app.celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available for Engineering.")

if CELERY_AVAILABLE:
    @celery_app.task(name="run_engineering_pipeline_task")
    def run_engineering_pipeline_task(job_id: str, project_prompt: str, image_base64: Optional[str] = None):
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def run_with_local_db():
            async with AsyncSessionLocal() as db:
                from app.engineering_agent.engineering_runner import run_engineering_pipeline
                await run_engineering_pipeline(db, job_id, project_prompt, image_base64)

        return loop.run_until_complete(run_with_local_db())

# ── Pydantic Models ──────────────────────────────────────────────────────────

class EngineerRequest(BaseModel):
    project_prompt: str
    image_base64: Optional[str] = None # For UI reconstruction

class EngineerJobResponse(BaseModel):
    job_id: str
    project_name: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", status_code=202)
async def create_project(
    payload: EngineerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(dev_required)
):
    """
    Trigger the autonomous creation of a new project.
    """
    job_id = str(uuid.uuid4())
    job = EngineerJobDB(
        job_id=job_id,
        project_prompt=payload.project_prompt,
        status="pending",
        owner_id=current_user.id
    )
    db.add(job)
    await db.commit()

    engine_started = False

    if settings.use_temporal:
        try:
            from app.temporal_client import get_temporal_client
            from app.temporal.engineering_workflow import EngineerProjectWorkflow
            
            client = await get_temporal_client()
            await client.start_workflow(
                EngineerProjectWorkflow.run,
                args=[job_id, payload.project_prompt, payload.image_base64],
                id=f"engineer-{job_id}",
                task_queue="software-audit-tasks", # Reusing same queue for now
            )
            logger.info(f"Engineering job {job_id} started via Temporal")
            engine_started = True
        except Exception as e:
            logger.error(f"Failed to start Temporal for Engineering: {e}")

    if not engine_started:
        if CELERY_AVAILABLE:
            run_engineering_pipeline_task.delay(job_id, payload.project_prompt, payload.image_base64)
            logger.info(f"Engineering job {job_id} started via Celery")
            engine_started = True
        elif settings.debug:
            # Simple asyncio fallback for local dev without workers
            asyncio.create_task(_run_engineer_task(job_id, payload.project_prompt, payload.image_base64))
            logger.warning(f"Engineering job {job_id} started via Asyncio (DEBUG mode).")
            engine_started = True

    if not engine_started:
        raise HTTPException(status_code=503, detail="No background engine available.")

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Engineering pipeline started."
    }

async def _run_engineer_task(job_id: str, project_prompt: str, image_base64: Optional[str] = None):
    """Async background task for the engineering pipeline (Debug Fallback)."""
    async with AsyncSessionLocal() as db:
        from app.engineering_agent.engineering_runner import run_engineering_pipeline
        try:
            await run_engineering_pipeline(db, job_id, project_prompt, image_base64)
        except Exception as e:
            logger.error(f"Background Engineering Task Failed: {e}")

@router.get("/{job_id}")
async def get_engineer_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """Get status and technical spec of an engineering job."""
    result = await db.execute(select(EngineerJobDB).where(EngineerJobDB.job_id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "job_id": job.job_id,
        "project_name": job.project_name,
        "status": job.status,
        "project_prompt": job.project_prompt,
        "technical_spec": job.technical_spec,
        "repo_url": job.minio_repo_zip_url,
        "error": job.error,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }

@router.get("/")
async def list_engineer_jobs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """List recent engineering jobs."""
    query = select(EngineerJobDB)
    if current_user.role != UserRole.ADMIN:
        query = query.where(EngineerJobDB.owner_id == current_user.id)
    
    query = query.order_by(desc(EngineerJobDB.created_at)).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "project_name": j.project_name,
                "status": j.status,
                "created_at": j.created_at,
                "completed_at": j.completed_at,
            } for j in jobs
        ],
        "total": len(jobs)
    }
