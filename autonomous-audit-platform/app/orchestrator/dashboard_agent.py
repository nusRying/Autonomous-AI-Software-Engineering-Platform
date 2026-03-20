from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings
import requests
import json

class DashboardAgent(Agent):
    def __init__(self, **kwargs):
        llm = ChatOpenAI(
            model=settings.default_llm_model,
            api_key=settings.openai_api_key
        )
        super().__init__(
            role="Dashboard & Control Panel Engineer",
            goal="Connect to Appsmith and similar low-code platforms to build 'on-the-fly' interactive data views and control panels.",
            backstory="You are a low-code/no-code expert who rapidly prototypes operational dashboards using Appsmith.",
            allow_delegation=False,
            verbose=True,
            llm=llm,
            **kwargs
        )

    def build_dashboard(self, requirements: dict):
        """Simulate the generation of an Appsmith dashboard configuration."""
        dashboard_config = {
            "pageName": "Agent Operational View",
            "widgets": [
                {"type": "CHART_WIDGET", "label": "Task Progress"},
                {"type": "TABLE_WIDGET", "label": "Audit Findings"},
                {"type": "JSON_FORM_WIDGET", "label": "Agent Parameters"}
            ],
            "appsmith_api_status": "mock_connected"
        }
        return {
            "status": "success",
            "message": "Dashboard prototype generated for Appsmith",
            "config": dashboard_config
        }
