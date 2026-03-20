from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings

class UXOptimizerAgent(Agent):
    def __init__(self, **kwargs):
        llm = ChatOpenAI(
            model=settings.default_llm_model,
            api_key=settings.openai_api_key
        )
        super().__init__(
            role="Frontend & UX Optimizer",
            goal="Analyze frontend layouts, calculate UX scores, and propose UI improvements to ensure maximum usability and aesthetics.",
            backstory="You are a leading UX/UI designer and frontend expert. You use tools like Playwright and Lighthouse to assess web layouts.",
            allow_delegation=False,
            verbose=True,
            llm=llm,
            **kwargs
        )

    def optimize_ux(self, frontend_path: str):
        """Analyze frontend code and provide UX optimization recommendations."""
        # Mock analysis results based on project defaults
        return {
            "ux_score": 85,
            "accessibility_score": 92,
            "performance_score": 78,
            "recommendations": [
                "Reduce bundle size by lazy loading agent modules",
                "Improve color contrast on the dashboard status indicators",
                "Add ARIA labels to the dynamic flow visualization components",
                "Implement skeleton screens for long-running agent tasks"
            ]
        }
