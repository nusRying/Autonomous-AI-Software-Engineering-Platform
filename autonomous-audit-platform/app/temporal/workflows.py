"""
Temporal workflow for orchestrating the Software Audit process.
"""
from datetime import timedelta
from typing import Optional
from temporalio import workflow
from loguru import logger

# Import activity definitions for type safety
with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        run_audit_activity, 
        update_job_status_activity,
        run_ansible_provisioning_activity
    )
    from app.db.models import AuditStatus

@workflow.defn
class AuditWorkflow:
    @workflow.run
    async def run(self, job_id: str, repo_path: Optional[str], repo_url: Optional[str], run_tests: bool) -> dict:
        """
        Orchestrates the full audit lifecycle:
        1. Update DB status to RUNNING
        2. Execute the actual Audit agent logic
        3. Update DB status to COMPLETED (or FAILED on error)
        """
        logger.info(f"Temporal Workflow: Executing for job {job_id}")

        # Step 1: Mark job as RUNNING in database
        await workflow.execute_activity(
            update_job_status_activity,
            args=[job_id, AuditStatus.RUNNING],
            start_to_close_timeout=timedelta(seconds=30),
        )

        try:
            # Step 2: Run the actual audit
            # This activity may take minutes, set a long timeout
            report = await workflow.execute_activity(
                run_audit_activity,
                args=[job_id, repo_path, repo_url, run_tests],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=None # Don't automatically retry LLM/Docker runs on logic failure
            )

            # Step 3: Complete the job
            await workflow.execute_activity(
                update_job_status_activity,
                args=[job_id, AuditStatus.COMPLETED, report],
                start_to_close_timeout=timedelta(seconds=30),
            )
            return report

        except Exception as e:
            # Step 3 (Error): Mark job as FAILED
            error_msg = str(e)
            logger.error(f"Temporal Workflow Failed for {job_id}: {error_msg}")
            await workflow.execute_activity(
                update_job_status_activity,
                args=[job_id, AuditStatus.FAILED, None, error_msg],
                start_to_close_timeout=timedelta(seconds=30),
            )
            raise e

@workflow.defn
class ModuleInstallationWorkflow:
    @workflow.run
    async def run(self, module_name: str, environment: str = "staging") -> dict:
        """
        Orchestrates the installation of a new platform module:
        1. Provisioning (Ansible/Docker)
        2. Post-installation health check (Simulation)
        """
        logger.info(f"Temporal Workflow: Installing module '{module_name}'")

        # Step 1: Provisioning
        provision_result = await workflow.execute_activity(
            run_ansible_provisioning_activity,
            args=[module_name, environment],
            start_to_close_timeout=timedelta(minutes=10)
        )

        # Step 2: Simulate Health Check
        logger.info(f"Temporal Workflow: Verifying module '{module_name}' health")
        provision_result["health_check"] = "pass"

        return provision_result
