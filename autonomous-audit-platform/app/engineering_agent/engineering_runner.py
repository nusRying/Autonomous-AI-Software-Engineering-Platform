"""
engineering_runner.py — Orchestrates the full autonomous engineering pipeline.
"""
import os
import uuid
import json
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import base64
from app.db.models import EngineerJobDB
from app.orchestrator.project_planner import ProjectPlanner
from app.orchestrator.engineer_crew import EngineerCrew
from app.engineering_agent.web_crawler import RequirementCrawler
from app.engineering_agent.vision_processor import VisionEngineer
from app.memory.vector_store import ProjectMemory
from app.utils.storage import storage_client
from app.config import settings

async def run_engineering_pipeline(
    db: AsyncSession,
    job_id: str,
    project_prompt: str,
    image_base64: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the full Milestone 2 engineering pipeline.
    """
    tmp_dir = None
    try:
        # Fetch Job
        result = await db.execute(select(EngineerJobDB).where(EngineerJobDB.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise RuntimeError(f"Engineer Job {job_id} not found")

        # ── Step 0: Context Retrieval, Web Crawling & Vision ────────────────
        logger.info(f"[{job_id}] Phase 0: Retrieving context...")
        
        # Memory
        memory = ProjectMemory("global_patterns")
        past_context = await memory.query_context(project_prompt)
        
        # Web Crawling if URL found
        web_context = ""
        if "http" in project_prompt:
            import re
            urls = re.findall(r'(https?://\S+)', project_prompt)
            if urls:
                crawler = RequirementCrawler()
                crawl_res = await crawler.analyze_url(urls[0])
                if crawl_res.get("status") == "success":
                    web_context = f"Reference Web App Content:\n{crawl_res['markdown_content']}"

        # Vision Analysis if image provided
        vision_context = ""
        if image_base64:
            try:
                logger.info(f"[{job_id}] Vision: Reconstructing UI from screenshot...")
                vision_engine = VisionEngineer(db)
                # Remove data URI prefix if present
                pure_base64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
                image_bytes = base64.b64decode(pure_base64)
                vision_code = await vision_engine.screenshot_to_code(image_bytes, context_description=project_prompt)
                vision_context = f"Visual UI Reconstruction (React/Tailwind Code):\n{vision_code}"
            except Exception as ve:
                logger.error(f"[{job_id}] Vision Analysis Failed: {ve}")
                # Fallback: continue without vision context

        enhanced_prompt = f"Idea: {project_prompt}\n"
        if past_context:
            enhanced_prompt += f"\nHistorical Patterns:\n{past_context}"
        if web_context:
            enhanced_prompt += f"\n{web_context}"
        if vision_context:
            enhanced_prompt += f"\n{vision_context}"

        # ── Step 1: Autonomous Planning ──────────────────────────────────────
        logger.info(f"[{job_id}] Phase 1: Generating technical spec...")
        job.status = "planning"
        await db.commit()

        planner = ProjectPlanner(db)
        spec = await planner.generate_spec(enhanced_prompt)
        
        job.technical_spec = spec
        job.project_name = spec.get("project_name", "Untitled Project")
        await db.commit()

        # ── Step 2: Implementation & Self-Correction ────────────────────────
        logger.info(f"[{job_id}] Phase 2: Generating code with self-correction loop...")
        
        # Create a workspace for the new project
        tmp_dir = tempfile.mkdtemp(prefix=f"engineer_{job_id}_")
        repo_path = os.path.join(tmp_dir, job.project_name.replace(" ", "_").lower())
        os.makedirs(repo_path, exist_ok=True)

        max_attempts = 3
        attempt = 1
        last_error = ""

        while attempt <= max_attempts:
            logger.info(f"[{job_id}] Implementation Attempt {attempt}/{max_attempts}")
            job.status = f"coding_attempt_{attempt}"
            await db.commit()

            # Initialize Crew
            crew_executor = EngineerCrew(db)
            
            # Prepare inputs - if it's a retry, add error context
            crew_inputs = {
                "project_prompt": enhanced_prompt,
                "tech_spec": json.dumps(spec),
                "repo_path": repo_path
            }
            if last_error:
                crew_inputs["project_prompt"] += f"\n\nPREVIOUS ATTEMPT FAILED WITH ERRORS:\n{last_error}\nPlease fix these issues in the new implementation."

            # Execute Implementation
            crew_result = crew_executor.crew().kickoff(inputs=crew_inputs)

            # Verification (Internal to runner for immediate loop)
            from app.audit_agent.docker_runner import run_and_monitor
            verify_res = await run_and_monitor(repo_path, command=["python", "-m", "pytest"])
            
            if verify_res.success:
                logger.info(f"[{job_id}] Verification SUCCESS on attempt {attempt}")
                break
            else:
                last_error = verify_res.stdout + verify_res.stderr
                logger.warning(f"[{job_id}] Verification FAILED on attempt {attempt}. Error: {last_error[:200]}...")
                attempt += 1

        if attempt > max_attempts:
            logger.error(f"[{job_id}] Failed to generate stable app after {max_attempts} attempts.")
            raise RuntimeError(f"Max retries reached ({max_attempts}) without passing verification.")

        # ── Step 3: Persistence & Learning ──────────────────────────────────
        logger.info(f"[{job_id}] Phase 3: Finalizing and learning...")
        job.status = "verifying"
        
        # Store successful patterns in memory
        await memory.add_context(
            text=f"Project: {job.project_name}. Prompt: {project_prompt}. Spec: {json.dumps(spec)}",
            metadata={"job_id": job_id, "type": "project_pattern", "source": "engineering_pipeline"}
        )

        # Zip and upload to MinIO
        zip_path = shutil.make_archive(repo_path, 'zip', repo_path)
        zip_filename = os.path.basename(zip_path)
        
        if settings.use_minio:
            with open(zip_path, "rb") as f:
                await storage_client.upload_bytes(
                    f"{job_id}/{zip_filename}",
                    f.read(),
                    "application/zip"
                )
                job.minio_repo_zip_url = await storage_client.get_presigned_url(f"{job_id}/{zip_filename}")

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.generated_repo_path = repo_path # Note: this is a temp path, in production would be a persistent volume
        await db.commit()

        return {
            "job_id": job_id,
            "project_name": job.project_name,
            "status": "completed",
            "repo_url": job.minio_repo_zip_url
        }

    except Exception as e:
        logger.error(f"Engineering Pipeline Failed: {e}")
        if 'job' in locals() and job:
            job.status = "failed"
            job.error = str(e)
            await db.commit()
        raise e
    # Note: We don't clean up tmp_dir yet so the user can inspect it if needed, 
    # but in a real system we would after backup.
