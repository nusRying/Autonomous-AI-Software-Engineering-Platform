"""
AuditCrew — CrewAI orchestrator for the software audit workflow.

Architecture:
    - @CrewBase loads agents.yaml and tasks.yaml automatically
    - All 3 agents share the same custom LiteLLM-backed LLM
    - Tasks run SEQUENTIALLY: doc_analysis → code_scan → report_generation
    - The report_agent receives context from both previous tasks

Usage:
    from app.orchestrator.crew import AuditCrew

    # Blocking call (run in background thread or Celery):
    result = AuditCrew(db=db_session).kickoff(inputs={"repo_path": "/path/to/repo"})
    print(result.raw)  # JSON string of the audit report
"""
from typing import Any
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, task, crew
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


def _build_llm() -> LLM:
    """
    Build a CrewAI LLM object that talks to our LiteLLM proxy / any provider.

    LiteLLM handles all provider translation (OpenAI, Anthropic, Ollama, etc.).
    We use the model and provider from settings.

    In a full Milestone 1 implementation, this would be extended to
    dynamically fetch DB keys via the rotator — for now we use the env-provided key
    so CrewAI can work standalone without a running DB session.
    """
    model = settings.default_llm_model
    logger.debug(f"Building CrewAI LLM: model={model}")
    return LLM(model=model, temperature=0.2)


@CrewBase
class AuditCrew:
    """
    Orchestrates the 3-agent software audit pipeline.

    CrewAI's @CrewBase decorator automatically reads:
        - agents_config: app/orchestrator/agents.yaml
        - tasks_config:  app/orchestrator/tasks.yaml

    Each method decorated with @agent creates an Agent instance.
    Each method decorated with @task  creates a Task instance.
    The method decorated with @crew  assembles everything.
    """

    # Use absolute paths for config files
    import os
    from pathlib import Path
    BASE_DIR = Path(__file__).parent
    agents_config = str(BASE_DIR / "agents.yaml")
    tasks_config  = str(BASE_DIR / "tasks.yaml")

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── LLM shared across all agents ──────────────────────────────────────────
    @property
    def llm(self) -> Any:
        from app.api_manager.llm_adapters import CrewAIRotatorLLM
        return CrewAIRotatorLLM(
            db=self.db,
            provider=settings.default_llm_provider,
            model_name=settings.default_llm_model
        )

    # ── Agents ────────────────────────────────────────────────────────────────

    @agent
    def doc_agent(self) -> Agent:
        """Documentation & Architecture Analyst."""
        return Agent(
            config=self.agents_config["doc_agent"],
            llm=self.llm,
        )

    @agent
    def code_agent(self) -> Agent:
        """Code Quality & Security Inspector."""
        return Agent(
            config=self.agents_config["code_agent"],
            llm=self.llm,
        )

    @agent
    def report_agent(self) -> Agent:
        """Audit Report Synthesizer."""
        return Agent(
            config=self.agents_config["report_agent"],
            llm=self.llm,
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @task
    def doc_analysis_task(self) -> Task:
        """Analyze repository documentation."""
        return Task(
            config=self.tasks_config["doc_analysis_task"],
        )

    @task
    def code_scan_task(self) -> Task:
        """Scan source code for quality & security issues."""
        return Task(
            config=self.tasks_config["code_scan_task"],
        )

    @task
    def report_generation_task(self) -> Task:
        """Synthesize final JSON audit report."""
        return Task(
            config=self.tasks_config["report_generation_task"],
        )

    # ── Crew ──────────────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        """
        Assembles the full audit crew.

        Process.SEQUENTIAL ensures tasks run in the order defined above:
            1. doc_analysis_task
            2. code_scan_task
            3. report_generation_task (receives output of both as context)
        """
        logger.info("Assembling AuditCrew with sequential process")
        return Crew(
            agents=self.agents,   # auto-collected from @agent methods
            tasks=self.tasks,     # auto-collected from @task methods
            process=Process.sequential,
            verbose=True,
        )
