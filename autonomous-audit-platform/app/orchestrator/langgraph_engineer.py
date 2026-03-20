import os
from typing import Annotated, TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from loguru import logger

from app.orchestrator.engineer_crew import EngineerCrew
from app.audit_agent.docker_runner import run_and_monitor

class EngineeringState(TypedDict):
    """The state of an autonomous engineering job."""
    job_id: str
    prompt: str
    image_base64: str
    project_path: str
    status: str
    attempts: int
    last_error: str
    files_created: List[str]
    verification_result: Dict

def engineer_build_node(state: EngineeringState):
    """Initial build step using CrewAI agents."""
    logger.info(f"--- [Node: Build] Job {state['job_id']} (Attempt {state['attempts'] + 1}) ---")
    crew = EngineerCrew(state['job_id'])
    # We pass the state to kickoff the specialized agents
    result = crew.kickoff({
        "prompt": state['prompt'],
        "image_base64": state['image_base64'],
        "attempt": state['attempts'] + 1,
        "last_error": state['last_error']
    })
    
    # In a real implementation, we'd parse specific files created
    return {
        "status": "built",
        "attempts": state['attempts'] + 1,
        "files_created": ["app/main.py"] # Mocked for now
    }

async def verify_node(state: EngineeringState):
    """Sandboxed execution to verify if the code actually works."""
    logger.info(f"--- [Node: Verify] Checking code stability ---")
    
    # Run the project in Docker sandbox
    result = await run_and_monitor(
        image="python:3.11-slim",
        command=["python", "-m", "pytest"],
        repo_path=state['project_path']
    )
    
    if result.success:
        return {"status": "verified", "verification_result": result.__dict__}
    else:
        return {
            "status": "failed_verification", 
            "last_error": result.stderr,
            "verification_result": result.__dict__
        }

def router_logic(state: EngineeringState):
    """Decision logic for the autonomous loop."""
    if state["status"] == "verified":
        return "complete"
    if state["attempts"] >= 3:
        logger.warning("Max attempts reached. Stopping loop.")
        return "max_attempts"
    return "fix"

def create_engineering_graph():
    """Builds the LangGraph state machine."""
    workflow = StateGraph(EngineeringState)

    # Define Nodes
    workflow.add_node("build", engineer_build_node)
    workflow.add_node("verify", verify_node)
    
    # Define Edges
    workflow.set_entry_point("build")
    workflow.add_edge("build", "verify")
    
    workflow.add_conditional_edges(
        "verify",
        router_logic,
        {
            "complete": END,
            "fix": "build",
            "max_attempts": END
        }
    )

    return workflow.compile()

# Global graph instance
autonomous_engineer = create_engineering_graph()
