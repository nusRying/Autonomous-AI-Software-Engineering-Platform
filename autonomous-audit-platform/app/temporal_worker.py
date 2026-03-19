"""
Temporal Worker script to execute Software Audit workflows and activities.
"""
import asyncio
from temporalio.worker import Worker
from app.temporal_client import get_temporal_client
from app.temporal.workflows import AuditWorkflow, ModuleInstallationWorkflow
from app.temporal.activities import (
    run_audit_activity, 
    update_job_status_activity,
    run_ansible_provisioning_activity
)
from loguru import logger

async def main():
    logger.info("Starting Temporal Worker for Software Audit...")
    
    # Connect to temporal server
    client = await get_temporal_client()
    
    # Start the worker
    worker = Worker(
        client,
        task_queue="software-audit-tasks",
        workflows=[AuditWorkflow, ModuleInstallationWorkflow],
        activities=[
            run_audit_activity, 
            update_job_status_activity,
            run_ansible_provisioning_activity
        ],
    )
    
    logger.info("Worker is running and listening on 'software-audit-tasks' queue")
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Temporal Worker stopped.")
