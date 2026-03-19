from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


class OrchestrationState:
    """
    Holds the shared state for a multi-agent audit run.
    """
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.findings: List[Dict[str, Any]] = []
        self.plan: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.status: str = "initialized"

    def add_finding(self, agent_name: str, finding: Dict[str, Any]):
        finding["agent"] = agent_name
        self.findings.append(finding)

    def set_plan(self, plan: List[Dict[str, Any]]):
        self.plan = plan


class BaseOrchestrator(ABC):
    """
    Base class for orchestrating multiple agents.
    Provides shared state, database access, and common utilities.
    """
    def __init__(self, db: AsyncSession, repo_path: str):
        self.db = db
        self.repo_path = repo_path
        self.state = OrchestrationState(repo_path)
        logger.info(f"Initialized Orchestrator for {repo_path}")

    @abstractmethod
    async def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start the orchestration process.
        """
        pass

    def get_context(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary representing the current orchestration state.
        """
        return {
            "repo_path": self.state.repo_path,
            "findings_count": len(self.state.findings),
            "status": self.state.status,
            "plan": self.state.plan
        }
