"""
audit_runner.py — Orchestrates the full audit pipeline.

This is the "glue" layer between the FastAPI endpoint and all audit components.
It runs synchronously (in a background thread or Celery) because:
  - CrewAI is synchronous by design
  - Docker execution is synchronous

Call run_audit() inside asyncio.to_thread() from the async endpoint.

Pipeline:
  1. Clone repo (if URL given) or use local path
  2. Run code_scanner (synchronous AST scan)
  3. Run doc_analyzer (LlamaIndex or fallback)
  4. Run CrewAI crew (AI analysis with 3 agents)
  5. Run docker_runner if tests requested
  6. Generate + write report (JSON + Markdown)
  7. Return report dict
"""
import asyncio
import os
import shutil
import tempfile
from typing import Optional
from loguru import logger

from app.audit_agent.code_scanner import scan_code
from app.audit_agent.doc_analyzer  import analyze_docs
from app.audit_agent.report_generator import generate_report
from app.audit_agent.docker_runner import detect_entry_point, run_and_monitor
from app.config import settings
from app.db.models import AuditJobDB
from sqlalchemy import update


def _clone_repo(repo_url: str, target_dir: str) -> str:
    """
    Clone a git repository to target_dir using gitpython.
    Returns the path to the cloned directory.
    """
    try:
        from git import Repo
        logger.info(f"Cloning {repo_url} → {target_dir}")
        Repo.clone_from(repo_url, target_dir, depth=1)  # shallow clone for speed
        return target_dir
    except ImportError:
        raise RuntimeError(
            "gitpython is not installed. "
            "Run 'pip install gitpython' or provide a local repo_path instead of repo_url."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to clone {repo_url}: {e}")


from sqlalchemy.ext.asyncio import AsyncSession

async def run_audit(
    db: AsyncSession,
    job_id: str,
    repo_path: Optional[str] = None,
    repo_url: Optional[str] = None,
    run_tests: bool = False,
) -> dict:
    """
    Execute the complete audit pipeline for a single job.

    Args:
        db:        Async database session for token tracking
        job_id:    Unique identifier for this audit job
        repo_path: Absolute path to a local repository (use this OR repo_url)
        repo_url:  Git URL to clone (if no local path given)
        run_tests: Whether to run tests inside Docker sandbox

    Returns:
        Full report dict (also written to disk by report_generator)
    """
    if not repo_path and not repo_url:
        raise ValueError("Either repo_path or repo_url must be provided")

    tmp_dir = None

    try:
        # ── Step 1: Resolve repo path ──────────────────────────────────────────
        if repo_url and not repo_path:
            tmp_dir = tempfile.mkdtemp(prefix="audit_clone_")
            # Clone is blocking, run in thread
            repo_path = await asyncio.to_thread(_clone_repo, repo_url, tmp_dir)
        else:
            repo_path = os.path.abspath(repo_path)

        if not os.path.isdir(repo_path):
            raise ValueError(f"repo_path does not exist: {repo_path}")

        logger.info(f"[{job_id}] Starting audit of: {repo_path}")

        # ── Step 2: Run static code scanner ───────────────────────────────────
        logger.info(f"[{job_id}] Running code scan...")
        # Static scan is CPU bound but usually fast, can run in thread if needed
        scan_result = await asyncio.to_thread(scan_code, repo_path)
        logger.info(
            f"[{job_id}] Code scan complete: "
            f"{scan_result['total_python_files']} files, "
            f"{len(scan_result['findings'])} findings"
        )

        # ── Step 3: Run doc analyzer ───────────────────────────────────────────
        logger.info(f"[{job_id}] Analyzing documentation...")
        docs_summary = await analyze_docs(db, repo_path)
        logger.info(f"[{job_id}] Doc analysis complete: {len(docs_summary)} chars")

        # ── Step 4: Run CrewAI (AI agent analysis) ─────────────────────────────
        ai_report_raw = None
        try:
            logger.info(f"[{job_id}] Starting CrewAI audit crew...")
            from app.orchestrator.crew import AuditCrew
            # CrewAI kickoff is synchronous, but its LLM calls will trigger our rotator
            crew = AuditCrew(db=db)
            # Run the blocking crew in a thread
            crew_result = await asyncio.to_thread(crew.kickoff, inputs={"repo_path": repo_path})
            ai_report_raw = crew_result.raw if hasattr(crew_result, "raw") else str(crew_result)
            logger.info(f"[{job_id}] CrewAI complete: {len(ai_report_raw)} chars")
        except Exception as e:
            logger.warning(f"[{job_id}] CrewAI failed (continuing without AI report): {e}")

        # ── Step 5: Docker test run (optional) ────────────────────────────────
        docker_result = None
        if run_tests:
            try:
                logger.info(f"[{job_id}] Running tests in Docker sandbox...")
                from app.audit_agent.docker_runner import run_tests as docker_run_tests
                # Docker runs are blocking
                docker_result = await asyncio.to_thread(docker_run_tests, repo_path)
                logger.info(
                    f"[{job_id}] Docker tests done: "
                    f"exit_code={docker_result['exit_code']}, "
                    f"time={docker_result['duration_seconds']:.1f}s"
                )
            except Exception as e:
                logger.warning(f"[{job_id}] Docker test run failed: {e}")

        # ── Step 5.5: Runtime Analysis (Smart Run) ────────────────────────────
        runtime_result = None
        try:
            logger.info(f"[{job_id}] Attempting runtime analysis (smart detect)...")
            entry_cmd = await asyncio.to_thread(detect_entry_point, repo_path)
            if entry_cmd:
                logger.info(f"[{job_id}] Detected entry point: {' '.join(entry_cmd)}")
                runtime_result = await asyncio.to_thread(run_and_monitor, repo_path, entry_cmd)
                logger.info(
                    f"[{job_id}] Runtime analysis complete: "
                    f"success={runtime_result['success']}, "
                    f"duration={runtime_result['duration_seconds']:.1f}s"
                )
            else:
                logger.debug(f"[{job_id}] No clear entry point found for runtime analysis.")
        except Exception as e:
            logger.warning(f"[{job_id}] Runtime analysis failed: {e}")

        # ── Step 6: Generate final report ─────────────────────────────────────
        logger.info(f"[{job_id}] Generating report...")
        report = await generate_report(
            job_id=job_id,
            repo_path=repo_path,
            output_dir=settings.audit_output_dir,
            scan_result=scan_result,
            docs_summary=docs_summary,
            ai_report_raw=ai_report_raw,
            runtime_analysis=runtime_result,
        )

        # Attach docker results if available
        if docker_result:
            report["test_run"] = {
                "exit_code": docker_result["exit_code"],
                "success": docker_result["success"],
                "output": docker_result["stdout"][:2000],
            }

        logger.info(
            f"[{job_id}] Audit complete. "
            f"Health score: {report['overall_health_score']}/10, "
            f"Findings: {len(report['findings'])}"
        )

        return report

    except Exception as e:
        logger.error(f"[{job_id}] Audit failed: {e}")
        raise e

    finally:
        # Clean up temp clone dir
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.debug(f"[{job_id}] Cleaned up temp dir: {tmp_dir}")

