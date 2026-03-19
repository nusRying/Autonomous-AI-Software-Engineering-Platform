"""
ProjectPlanner — Logic for high-level architectural decomposition of new projects.
"""
import json
from typing import Any, Dict, List
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.api_manager.rotator import call_llm
from app.config import settings

class ProjectPlanner:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model = settings.default_llm_model
        self.provider = settings.default_llm_provider

    async def generate_spec(self, project_prompt: str) -> Dict[str, Any]:
        """
        Takes a user idea and turns it into a technical spec JSON.
        """
        prompt = f"""
        You are a Lead System Architect. Your goal is to take a high-level project idea
        and decompose it into a complete technical specification.

        Project Idea: {project_prompt}

        Your specification MUST be a valid JSON object with the following structure:
        {{
            "project_name": "string",
            "architecture_overview": "string",
            "tech_stack": {{
                "backend": "FastAPI",
                "frontend": "React + Tailwind",
                "database": "SQLite/PostgreSQL"
            }},
            "database_schema": [
                {{
                    "table": "string",
                    "columns": ["name:type", ...]
                }}
            ],
            "api_endpoints": [
                {{
                    "path": "string",
                    "method": "GET|POST|PUT|DELETE",
                    "description": "string"
                }}
            ],
            "frontend_components": ["string", "string"]
        }}

        Output ONLY the JSON object.
        """
        
        messages = [{"role": "system", "content": "You are a software architect. Output JSON only."},
                    {"role": "user", "content": prompt}]
        
        try:
            response_text = await call_llm(
                db=self.db,
                messages=messages,
                provider=self.provider,
                model=self.model
            )
            
            # Clean JSON extraction
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            spec = json.loads(response_text)
            logger.info(f"Generated tech spec for: {spec.get('project_name')}")
            return spec
        except Exception as e:
            logger.error(f"Failed to generate tech spec: {e}")
            return {"error": "Failed to plan project. Check prompt clarity."}
