from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings
import os

class FlowAgent(Agent):
    def __init__(self, **kwargs):
        llm = ChatOpenAI(
            model=settings.default_llm_model,
            api_key=settings.openai_api_key
        )
        super().__init__(
            role="Business Logic & Process Flow Analyst",
            goal="Map business logic and construct process visualizations using sequence diagrams, state machines, and flowcharts.",
            backstory="You are a master of process engineering. You translate complex business requirements into clear, visual workflows using Mermaid diagrams.",
            allow_delegation=False,
            verbose=True,
            llm=llm,
            **kwargs
        )

    def analyze_flow(self, project_path: str):
        """Analyze code to extract business logic and generate Mermaid diagrams."""
        # Simulated logic for MVP: In a real run, this would scan files for logic branches
        diagram = """
graph TD
    A[User Request] --> B{Auth Check}
    B -- Success --> C[Agent Orchestration]
    B -- Fail --> D[401 Unauthorized]
    C --> E[Execution Loop]
    E --> F[Verification]
    F -- Pass --> G[Success Response]
    F -- Fail --> E
        """
        return {
            "status": "success",
            "diagram_type": "mermaid",
            "diagram": diagram,
            "business_rules": [
                "Authentication required for all API access",
                "Cyclic self-correction loop for agent tasks",
                "Mandatory verification step before task finalization"
            ]
        }
