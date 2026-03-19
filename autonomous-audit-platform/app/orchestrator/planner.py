import json
from typing import Any, Dict, List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.api_manager.rotator import call_llm
from app.config import settings


class PlannerAgent:
    """
    Agent responsible for decomposing an audit request into specific tasks.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model = settings.default_llm_model
        self.provider = settings.default_llm_provider

    async def create_plan(self, repo_path: str, repo_summary: str) -> List[Dict[str, Any]]:
        """
        Generates an audit plan based on the repository content summary.
        """
        prompt = f"""
        You are the Lead Auditor for an autonomous software audit platform.
        Your goal is to decompose a software audit request into a set of discrete, actionable tasks.

        Repository Path: {repo_path}
        Repository Summary: {repo_summary}

        Create a plan that includes:
        1. Context discovery (Analyzing documentation, structure).
        2. Security scanning (Identifying vulnerabilities).
        3. Quality assessment (Code quality, patterns).
        4. Report synthesis.

        Output MUST be a JSON list of tasks, where each task has:
        - "id": unique string
        - "agent": which agent should handle it ("doc_agent", "code_agent", "report_agent")
        - "description": clear instructions for the agent
        - "priority": 1-5 (1 highest)

        JSON Output:
        """
        
        messages = [{"role": "system", "content": "You are a task planner for a software audit system. Output JSON only."},
                    {"role": "user", "content": prompt}]
        
        try:
            response_text = await call_llm(
                db=self.db,
                messages=messages,
                provider=self.provider,
                model=self.model
            )
            
            # Basic JSON extraction in case the LLM includes markdown backticks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            plan = json.loads(response_text)
            logger.info(f"Generated plan with {len(plan)} tasks.")
            return plan
        except Exception as e:
            logger.error(f"Failed to generate audit plan: {e}")
            # Fallback plan
            return [
                {"id": "initial_scan", "agent": "doc_agent", "description": "General repo structure scan", "priority": 1},
                {"id": "security_scan", "agent": "code_agent", "description": "Scan for vulnerabilities", "priority": 1},
                {"id": "final_report", "agent": "report_agent", "description": "Synthesize findings", "priority": 5}
            ]
