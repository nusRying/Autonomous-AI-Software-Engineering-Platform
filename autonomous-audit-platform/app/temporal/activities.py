"""
Temporal activities for the Software Audit process.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional
from temporalio import activity
from loguru import logger

from app.database import AsyncSessionLocal
from app.db.models import AuditJobDB, AuditStatus

@activity.defn
async def run_audit_activity(job_id: str, repo_path: Optional[str], repo_url: Optional[str], run_tests: bool) -> dict:
    """
    Executes the actual audit logic as a Temporal Activity.
    """
    logger.info(f"Temporal Activity: Starting audit for job {job_id}")
    
    async with AsyncSessionLocal() as db:
        from app.audit_agent.audit_runner import run_audit
        
        # This will call our existing runner which handles cloning, scanning, etc.
        report = await run_audit(
            db=db,
            job_id=job_id,
            repo_path=repo_path,
            repo_url=repo_url,
            run_tests=run_tests,
        )
        return report

@activity.defn
async def update_job_status_activity(job_id: str, status: str, report: Optional[dict] = None, error: Optional[str] = None):
    """
    Updates the database with the current job status and report data.
    """
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(AuditJobDB).where(AuditJobDB.job_id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise RuntimeError(f"Job {job_id} not found")

        job.status = status
        if status == AuditStatus.RUNNING:
            job.started_at = datetime.now(timezone.utc)
        elif status == AuditStatus.COMPLETED and report:
            job.report_json = json.dumps(report)
            job.report_data = report
            job.health_score = report.get("overall_health_score")
            job.report_path = report.get("report_path")
            job.completed_at = datetime.now(timezone.utc)
        elif status == AuditStatus.FAILED:
            job.error = error
            job.completed_at = datetime.now(timezone.utc)
        
        await db.commit()
        logger.info(f"Temporal Activity: Updated job {job_id} status to {status}")

@activity.defn
async def verify_generated_app_activity(job_id: str, repo_path: str) -> dict:
    """
    Attempts to run the newly generated project in Docker and check for startup errors.
    """
    from app.audit_agent.docker_runner import run_and_monitor
    logger.info(f"Temporal Activity: Verifying stability for generated project {job_id}")
    
    # We reuse our existing Docker sandbox runner
    # The runner looks for a Dockerfile or requirements.txt automatically
    result = await run_and_monitor(repo_path, command=["python", "-m", "pytest"])
    
    return {
        "stable": result.success,
        "logs": result.stdout + result.stderr,
        "exit_code": result.exit_code
    }

@activity.defn
async def run_engineering_pipeline_activity(job_id: str, project_prompt: str, image_base64: Optional[str] = None) -> dict:
    """
    Executes the full Milestone 2 engineering pipeline.
    """
    logger.info(f"Temporal Activity: Running engineering pipeline for job {job_id}")
    async with AsyncSessionLocal() as db:
        from app.engineering_agent.engineering_runner import run_engineering_pipeline
        result = await run_engineering_pipeline(db, job_id, project_prompt, image_base64)
        return result

@activity.defn
async def run_ansible_provisioning_activity(module_name: str, environment: str) -> dict:
    """
    Runs the Ansible playbook to provision a new module using subprocess.
    """
    import subprocess
    logger.info(f"Temporal Activity: Provisioning module '{module_name}' in '{environment}' via Ansible")
    
    playbook_path = os.path.join(os.getcwd(), "ansible", "provision_module.yml")
    
    # Run ansible-playbook command
    # Assuming ansible-playbook is installed and available in the environment
    try:
        process = subprocess.run(
            [
                "ansible-playbook", 
                playbook_path, 
                "-e", f"module_name={module_name}",
                "-e", f"target_dir=./reproduction_{environment}"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "status": "success",
            "module": module_name,
            "environment": environment,
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "logs": process.stdout
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Ansible failed: {e.stderr}")
        return {
            "status": "failed",
            "module": module_name,
            "environment": environment,
            "error": e.stderr,
            "logs": e.stdout
        }
    except Exception as e:
        logger.error(f"Failed to run Ansible: {e}")
        return {
            "status": "error",
            "module": module_name,
            "environment": environment,
            "error": str(e)
        }
