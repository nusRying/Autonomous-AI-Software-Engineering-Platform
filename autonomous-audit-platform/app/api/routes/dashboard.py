from fastapi import APIRouter, Header, HTTPException, Depends, UploadFile, File
from typing import Optional, List
import yaml
import os
from pydantic import BaseModel
from loguru import logger
from app.config import settings
from app.temporal_client import get_temporal_client
from app.temporal.workflows import ModuleInstallationWorkflow
from app.engineering_agent.vision_processor import VisionEngineer
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def verify_appsmith_secret(x_appsmith_secret: str = Header(...)):
    if x_appsmith_secret != settings.dashboard_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid Appsmith Secret")
    return x_appsmith_secret

@router.post("/optimize-ux")
async def optimize_ux(
    description: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    secret: str = Depends(verify_appsmith_secret)
):
    """
    Takes an uploaded screenshot and a description, and returns an "Improved UX" proposal.
    """
    try:
        image_bytes = await file.read()
        vision = VisionEngineer(db)
        
        # Perfect the UI
        optimized_code = await vision.screenshot_to_code(
            image_bytes=image_bytes,
            context_description=f"UX Optimization Request: {description}"
        )
        
        return {
            "status": "success",
            "optimized_code": optimized_code,
            "message": "UX Optimization proposal generated successfully."
        }
    except Exception as e:
        logger.error(f"UX Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class InstallModuleRequest(BaseModel):
    module_name: str
    environment: str = "staging"

@router.post("/install-module")
async def install_module(
    request: InstallModuleRequest,
    secret: str = Depends(verify_appsmith_secret)
):
    """
    Triggers the Temporal workflow to install/provision a new module.
    """
    try:
        client = await get_temporal_client()
        
        # Start the workflow
        handle = await client.start_workflow(
            ModuleInstallationWorkflow.run,
            args=[request.module_name, request.environment],
            id=f"install-{request.module_name}-{os.urandom(4).hex()}",
            task_queue="software-audit-tasks"
        )
        
        return {
            "status": "triggered",
            "workflow_id": handle.id,
            "message": f"Installation of '{request.module_name}' started in '{request.environment}'."
        }
    except Exception as e:
        logger.error(f"Failed to trigger installation workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class StateEntry(BaseModel):
    module_name: str
    status: str
    version: str
    last_audit: Optional[str] = None
    health_score: Optional[int] = None

class ProjectState(BaseModel):
    project_name: str
    last_updated: str
    modules: List[StateEntry]

@router.get("/appsmith-config")
async def get_appsmith_config():
    """
    Returns the JSON configuration for the Appsmith dashboard.
    Users can import this into their Appsmith instance.
    """
    config_path = os.path.join("app", "api", "templates", "appsmith_dashboard_v1.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Config not found")

@router.get("/state", response_model=ProjectState)
async def get_project_state(secret: str = Depends(verify_appsmith_secret)):
    """
    Returns the current high-level state of the project from STATE.yaml.
    This is consumed by the Appsmith interactive panel.
    """
    state_file = os.path.join(os.getcwd(), "STATE.yaml")
    if not os.path.exists(state_file):
        # Return default state if file doesn't exist
        return ProjectState(
            project_name=settings.app_name,
            last_updated="N/A",
            modules=[]
        )
    
    with open(state_file, "r") as f:
        data = yaml.safe_load(f)
        return ProjectState(**data)

@router.post("/propose-change")
async def propose_change(
    module_name: str, 
    proposal_description: str,
    secret: str = Depends(verify_appsmith_secret)
):
    """
    Triggers an Engineering Agent task to create a PR for a proposed change.
    In a real implementation, this would trigger a Temporal workflow.
    """
    # For now, we return a mock success message
    return {
        "status": "success",
        "message": f"Proposal for '{module_name}' submitted. An Engineering Agent will create a PR shortly.",
        "proposal_summary": proposal_description
    }
class ApplyAction(BaseModel):
    module_name: str
    action_type: str # e.g., "reproduce", "update", "rollback"
    parameters: Optional[dict] = {}

@router.post("/apply-change")
async def apply_change(
    action: ApplyAction,
    secret: str = Depends(verify_appsmith_secret)
):
    """
    Executes a direct action on the infrastructure (e.g., via Ansible/Temporal).
    This simulates the 'Safety Valve' where a human authorizes an agent's proposal.
    """
    # For now, we simulate the start of a deployment task
    return {
        "status": "in_progress",
        "task_id": f"task_{os.urandom(4).hex()}",
        "message": f"Action '{action.action_type}' initiated for '{action.module_name}'.",
        "details": f"Parameters: {action.parameters}"
    }
