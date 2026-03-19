"""
EngineerCrew — CrewAI orchestrator for autonomous project generation.
"""
from typing import Any
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

@CrewBase
class EngineerCrew:
    """
    Orchestrates the autonomous software engineering pipeline.
    Decomposes prompts, writes code, and verifies stability.
    """

    agents_config = "engineer_agents.yaml"
    tasks_config  = "engineer_tasks.yaml"

    def __init__(self, db: AsyncSession):
        self.db = db

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
    def architect_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["architect_agent"],
            llm=self.llm,
        )

    @agent
    def engineer_agent(self) -> Agent:
        from app.orchestrator.tools import FileWriterTool
        return Agent(
            config=self.agents_config["engineer_agent"],
            llm=self.llm,
            tools=[FileWriterTool()]
        )

    @agent
    def qa_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_agent"],
            llm=self.llm,
        )

    @agent
    def technical_writer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["technical_writer_agent"],
            llm=self.llm,
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @task
    def full_stack_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config["full_stack_generation_task"],
        )

    @task
    def stability_verification_task(self) -> Task:
        return Task(
            config=self.tasks_config["stability_verification_task"],
            context=[self.full_stack_generation_task()]
        )

    @task
    def documentation_task(self) -> Task:
        return Task(
            config=self.tasks_config["documentation_task"],
            context=[self.full_stack_generation_task()]
        )

    # ── Crew ──────────────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        logger.info("Assembling EngineerCrew for autonomous project generation")
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
