"""
Temporal workflow for autonomous project engineering.
"""
from datetime import timedelta
from typing import Optional, Dict, Any
from temporalio import workflow
from loguru import logger

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import run_engineering_pipeline_activity, verify_generated_app_activity

@workflow.defn
class EngineerProjectWorkflow:
    @workflow.run
    async def run(self, job_id: str, project_prompt: str, image_base64: Optional[str] = None) -> Dict[str, Any]:
        """
        Orchestrates:
        1. Implementation (Engineering Pipeline Activity)
        2. Stability Verification (Docker Activity)
        """
        logger.info(f"Temporal Workflow: Engineering Project {job_id}")

        # Execute Engineering Pipeline
        result = await workflow.execute_activity(
            run_engineering_pipeline_activity,
            args=[job_id, project_prompt, image_base64],
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=None
        )

        if result.get("status") == "completed" and result.get("repo_path"):
            # Verify Stability
            verification = await workflow.execute_activity(
                verify_generated_app_activity,
                args=[job_id, result.get("repo_path")],
                start_to_close_timeout=timedelta(minutes=5)
            )
            result["verification"] = verification

        return result
