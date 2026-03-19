"""
Audit API routes.

Endpoints:
    POST   /audit              — Submit a new audit job
    GET    /audit/{job_id}     — Poll job status
    GET    /audit              — List all jobs

Architecture:
    Audits are executed via Temporal (advanced) or Celery (fallback).
"""
import os
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import FileResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import AsyncSessionLocal, get_db
from app.db.models import AuditJobDB, UserDB, UserRole
from app.models.audit import AuditRequest, AuditStatus
from app.config import settings
from app.utils.security import get_current_user, dev_required

# Try to import heavy dependencies
try:
    from app.celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available.")

try:
    from app.audit_agent.audit_runner import run_audit
    AUDIT_RUNNER_AVAILABLE = True
except ImportError:
    AUDIT_RUNNER_AVAILABLE = False
    logger.warning("Audit runner dependencies (crewai/llama-index) not available.")

router = APIRouter(prefix="/audit", tags=["Audit"])


# ── Celery Task (Fallback) ───────────────────────────────────────────────────

if CELERY_AVAILABLE:
    @celery_app.task(name="run_full_audit_task", bind=True)
    def run_full_audit_task(self, job_id: str, repo_path: Optional[str], repo_url: Optional[str], run_tests: bool, user_id: Optional[int] = None):
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def run_with_local_db():
            async with AsyncSessionLocal() as db:
                await _run_audit_logic(db, job_id, repo_path, repo_url, run_tests, user_id)

        return loop.run_until_complete(run_with_local_db())
else:
    def run_full_audit_task(*args, **kwargs):
        logger.error("Celery not installed.")
        raise RuntimeError("Celery not installed.")


async def _run_audit_logic(db: AsyncSession, job_id: str, repo_path: Optional[str], repo_url: Optional[str], run_tests: bool, user_id: Optional[int]):
    """The core audit runner logic, now takes an active db session."""
    result = await db.execute(select(AuditJobDB).where(AuditJobDB.job_id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        logger.error(f"Job {job_id} not found in database")
        return

    job.status = AuditStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        if not AUDIT_RUNNER_AVAILABLE:
            raise RuntimeError("Audit runner dependencies missing.")

        report = await run_audit(db=db, job_id=job_id, repo_path=repo_path, repo_url=repo_url, run_tests=run_tests)
        
        # Pillar #2, #7, #10: Finalize via Unified Integration Manager
        try:
            from app.integrations.unified import UnifiedIntegrationManager
            unified = UnifiedIntegrationManager()
            unified_results = await unified.finalize_audit(job_id, json.dumps(report), repo_url or repo_path)
            report["unified_mvp_results"] = unified_results
            logger.info(f"Audit {job_id} finalized with unified integrations.")
        except Exception as ue:
            logger.error(f"Unified finalization failed for {job_id}: {ue}")

        job.status = AuditStatus.COMPLETED
        job.report_json = json.dumps(report)
        job.report_data = report
        job.health_score = report.get("overall_health_score")
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as e:
        job.status = AuditStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/", status_code=202)
async def submit_audit(
    payload: AuditRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(dev_required)
):
    """Submit a new audit job. Uses Temporal if available, otherwise Celery."""
    if not payload.repo_path and not payload.repo_url:
        raise HTTPException(status_code=422, detail="Provide repo_path or repo_url")

    job_id = str(uuid.uuid4())
    job = AuditJobDB(
        job_id=job_id,
        repo_path=payload.repo_path,
        repo_url=payload.repo_url,
        status=AuditStatus.PENDING,
        owner_id=current_user.id
    )
    db.add(job)
    await db.commit()

    engine_started = False

    if settings.use_temporal:
        try:
            from app.temporal_client import get_temporal_client
            from app.temporal.workflows import AuditWorkflow
            
            client = await get_temporal_client()
            await client.start_workflow(
                AuditWorkflow.run,
                args=[job_id, payload.repo_path, payload.repo_url, payload.run_tests],
                id=f"audit-{job_id}",
                task_queue="software-audit-tasks",
            )
            logger.info(f"Audit job {job_id} started via Temporal")
            engine_started = True
        except Exception as e:
            logger.error(f"Failed to start Temporal: {e}")

    if not engine_started:
        if CELERY_AVAILABLE:
            run_full_audit_task.delay(job_id, payload.repo_path, payload.repo_url, payload.run_tests, current_user.id)
            logger.info(f"Audit job {job_id} started via Celery")
            engine_started = True
        elif settings.debug:
            logger.warning(f"Audit job {job_id} submitted (No worker).")
            engine_started = True

    if not engine_started:
        raise HTTPException(status_code=503, detail="No background engine available.")

    return {
        "job_id": job_id,
        "status": AuditStatus.PENDING,
        "message": "Audit submitted successfully.",
    }


@router.get("/{job_id}")
async def get_audit_status(
    job_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """Get status and result of an audit job."""
    result = await db.execute(select(AuditJobDB).where(AuditJobDB.job_id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    report = json.loads(job.report_json) if job.report_json else None
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "repo_path": job.repo_path,
        "repo_url": job.repo_url,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error,
        "report": report,
    }


@router.get("/")
async def list_audits(
    limit: int = 20, 
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """List recent audit jobs."""
    query = select(AuditJobDB)
    if current_user.role != UserRole.ADMIN:
        query = query.where(AuditJobDB.owner_id == current_user.id)
    
    query = query.order_by(desc(AuditJobDB.created_at)).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "status": j.status,
                "repo_path": j.repo_path,
                "health_score": j.health_score,
                "created_at": j.created_at,
                "completed_at": j.completed_at,
            } for j in jobs
        ],
        "total": len(jobs)
    }

@router.get("/{job_id}/report-markdown")
async def get_report_markdown(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """Get the Markdown content of an audit report."""
    logger.info(f"Fetching report markdown for job {job_id}")
    result = await db.execute(select(AuditJobDB).where(AuditJobDB.job_id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for report markdown")
        raise HTTPException(status_code=404, detail="Job not found")

    logger.info(f"Job {job_id} found, status={job.status}, report_path={job.report_path}")

    if job.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        logger.warning(f"User {current_user.id} not authorized for job {job_id}")
        raise HTTPException(status_code=403, detail="Not authorized")

    if job.status != "completed":
        logger.warning(f"Report not ready for job {job_id} (status={job.status})")
        raise HTTPException(status_code=400, detail="Report not ready")

    # 1. Try MinIO
    if settings.use_minio:
        from app.utils.storage import storage_client
        try:
            md_key = f"{job_id}/report.md"
            logger.info(f"Attempting MinIO fetch: {md_key}")
            content = await storage_client.download_bytes(md_key)
            logger.info(f"Successfully fetched from MinIO: {len(content)} bytes")
            return Response(content=content, media_type="text/markdown")
        except Exception as e:
            logger.warning(f"MinIO fetch failed for {job_id}: {e}")

    # 2. Try Local Disk
    if job.report_path and os.path.exists(job.report_path):
        logger.info(f"Found report on local disk: {job.report_path}")
        return FileResponse(job.report_path, media_type="text/markdown")
    
    # 3. Try Fallback Path inside output_dir
    fallback_path = os.path.join(settings.audit_output_dir, job_id, "report.md")
    logger.info(f"Checking fallback path: {fallback_path}")
    if os.path.exists(fallback_path):
        logger.info(f"Found report at fallback path: {fallback_path}")
        return FileResponse(fallback_path, media_type="text/markdown")

    logger.error(f"Report file not found for job {job_id} anywhere.")
    raise HTTPException(status_code=404, detail="Markdown report file not found")
