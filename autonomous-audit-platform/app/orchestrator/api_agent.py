from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings
import os

class APIAgent(Agent):
    def __init__(self, **kwargs):
        llm = ChatOpenAI(
            model=settings.default_llm_model,
            api_key=settings.openai_api_key
        )
        super().__init__(
            role="API Development & Integration Specialist",
            goal="Generate, test, and integrate real REST/GraphQL APIs. Manage API keys and fallback logic.",
            backstory="You are a backend wizard focused on building enterprise-grade APIs. You generate FastAPI/Python code following best practices.",
            allow_delegation=False,
            verbose=True,
            llm=llm,
            **kwargs
        )

    def generate_api(self, specification: dict):
        """Generate FastAPI code for an endpoint based on specification."""
        # Simulated code generation based on spec
        endpoint_name = specification.get("name", "new_endpoint")
        method = specification.get("method", "GET")
        path = specification.get("path", f"/{endpoint_name}")
        
        generated_code = f"""
from fastapi import APIRouter, Depends
from app.utils.security import get_current_user

router = APIRouter()

@router.{method.lower()}("{path}")
async def {endpoint_name}(current_user = Depends(get_current_user)):
    \"\"\"Generated API endpoint for {endpoint_name}\"\"\"
    return {{"message": "Success", "data": "Real-time generated logic for {endpoint_name}"}}
"""
        # In a full run, this would be written to a dynamic routes file
        return {
            "status": "success",
            "endpoint": endpoint_name,
            "code_snippet": generated_code,
            "integration_path": f"app/api/routes/generated_{endpoint_name}.py"
        }
