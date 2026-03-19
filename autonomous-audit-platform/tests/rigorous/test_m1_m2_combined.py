import pytest
import asyncio
import uuid
import json
import os
import shutil
import tempfile
import base64
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

# App Imports
from app.db.models import UserDB, UserRole, APIKeyDB, APIUsageDB, AuditJobDB, EngineerJobDB, AuditStatus
from app.main import app
from app.utils.security import get_password_hash

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

# ─── MILESTONE 1: API MANAGER TESTS ──────────────────────────────────────────

@pytest.mark.anyio
async def test_api_manager_rotation_and_usage(db: AsyncSession):
    """
    M1: Verify that API keys are rotated when limits are hit and usage is tracked.
    """
    from app.api_manager.rotator import get_next_available_key, call_llm
    
    # 1. Add two OpenAI keys
    k1 = APIKeyDB(provider="openai", key_value="key-1", model="gpt-4", daily_limit=10)
    k2 = APIKeyDB(provider="openai", key_value="key-2", model="gpt-4", daily_limit=10)
    db.add_all([k1, k2])
    await db.commit()
    
    # 2. Simulate usage for k1 reaching limit
    usage = APIUsageDB(key_id=k1.id, tokens_used=100, prompt_tokens=50, completion_tokens=50, cost=0.01)
    db.add(usage)
    # Mark k1 as having 10 calls today (limit is 10)
    for _ in range(10):
        db.add(APIUsageDB(key_id=k1.id, tokens_used=1))
    await db.commit()
    
    # 3. Request key - should get k2
    selected_key = await get_next_available_key(db, "openai", "gpt-4")
    assert selected_key.key_value == "key-2"
    
    # 4. Verify call_llm tracks usage (Mock litellm)
    with patch("app.api_manager.rotator.completion") as mock_comp:
        mock_comp.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hello AI"))],
            usage=MagicMock(total_tokens=10, prompt_tokens=5, completion_tokens=5)
        )
        
        response = await call_llm(db, [{"role": "user", "content": "test"}], "openai", "gpt-4")
        assert response == "Hello AI"
        
        # Check DB for new usage record
        result = await db.execute(select(APIUsageDB).where(APIUsageDB.key_id == k2.id))
        usage_records = result.scalars().all()
        assert len(usage_records) > 0
        assert usage_records[0].tokens_used == 10

# ─── MILESTONE 1: AUDIT WORKFLOW TESTS ───────────────────────────────────────

@pytest.mark.anyio
async def test_audit_workflow_e2e(db: AsyncSession):
    """
    M1: Verify full audit pipeline: Clone -> Scan -> Docker -> Report.
    """
    from app.audit_agent.audit_runner import run_audit
    
    job_id = str(uuid.uuid4())
    repo_dir = tempfile.mkdtemp()
    with open(os.path.join(repo_dir, "app.py"), "w") as f: f.write("print('hello')")
    
    # Mock CrewAI and Docker
    mock_report = {
        "overall_health_score": 7,
        "findings": [{"severity": "HIGH", "title": "Insecure Port", "description": "Used port 80"}]
    }
    
    with patch("app.orchestrator.crew.AuditCrew.crew") as mock_crew_method, \
         patch("app.audit_agent.audit_runner.run_and_monitor", new_callable=AsyncMock) as mock_docker, \
         patch("app.audit_agent.audit_runner.storage_client.upload_bytes", new_callable=AsyncMock):
        
        # Mock Crew Kickoff
        mock_crew_inst = MagicMock()
        mock_crew_inst.kickoff.return_value = MagicMock(raw=json.dumps(mock_report))
        mock_crew_method.return_value = mock_crew_inst
        
        # Mock Docker Success
        mock_docker.return_value = MagicMock(success=True, stdout="Passed", stderr="", exit_code=0)
        
        report = await run_audit(db, job_id, repo_path=repo_dir, run_tests=True)
        
        assert report["overall_health_score"] == 7
        assert len(report["findings"]) > 0
        
        # Verify Job Status in DB
        result = await db.execute(select(AuditJobDB).where(AuditJobDB.job_id == job_id))
        job = result.scalar_one_or_none()
        assert job.status == AuditStatus.COMPLETED
        assert job.health_score == 7

    shutil.rmtree(repo_dir)

# ─── MILESTONE 2: ENGINEERING PIPELINE TESTS ─────────────────────────────────

@pytest.mark.anyio
async def test_engineering_pipeline_self_correction(db: AsyncSession):
    """
    M2: Verify project generation with the self-correction loop.
    """
    from app.engineering_agent.engineering_runner import run_engineering_pipeline
    
    job_id = str(uuid.uuid4())
    job = EngineerJobDB(job_id=job_id, project_prompt="Build an API", status="pending")
    db.add(job)
    await db.commit()
    
    mock_spec = {"project_name": "FixMeApp", "architecture": "MVC"}
    
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("app.engineering_agent.engineering_runner.ProjectPlanner.generate_spec", new_callable=AsyncMock) as mock_plan, \
         patch("app.engineering_agent.engineering_runner.EngineerCrew") as mock_crew_class, \
         patch("app.audit_agent.docker_runner.run_and_monitor", new_callable=AsyncMock) as mock_verify, \
         patch("app.engineering_agent.engineering_runner.storage_client.upload_bytes", new_callable=AsyncMock), \
         patch("app.engineering_agent.engineering_runner.storage_client.get_presigned_url", new_callable=AsyncMock) as mock_url, \
         patch("app.engineering_agent.engineering_runner.ProjectMemory", MagicMock()):
        
        mock_plan.return_value = mock_spec
        mock_url.return_value = "http://minio/app.zip"
        
        # 1. First attempt FAILS verification
        fail_res = MagicMock(success=False, stdout="SyntaxError: invalid syntax", stderr="Line 10")
        # 2. Second attempt SUCCEEDS verification
        pass_res = MagicMock(success=True, stdout="Tests Passed", stderr="")
        
        mock_verify.side_effect = [fail_res, pass_res]
        
        # Mock Crew
        mock_crew_inst = MagicMock()
        mock_crew_class.return_value = mock_crew_inst
        mock_actual_crew = MagicMock()
        mock_actual_crew.kickoff.return_value = "Code Generated"
        mock_crew_inst.crew.return_value = mock_actual_crew
        
        result = await run_engineering_pipeline(db, job_id, "Build an API")
        
        assert result["status"] == "completed"
        # Verify verify was called TWICE (Self-correction triggered)
        assert mock_verify.call_count == 2
        
        await db.refresh(job)
        assert job.status == "completed"

@pytest.mark.anyio
async def test_vision_integration_in_pipeline(db: AsyncSession):
    """
    M2: Verify that providing an image triggers the vision processor.
    """
    from app.engineering_agent.engineering_runner import run_engineering_pipeline
    
    job_id = str(uuid.uuid4())
    job = EngineerJobDB(job_id=job_id, project_prompt="Clone this UI", status="pending")
    db.add(job)
    await db.commit()
    
    mock_img = "data:image/png;base64," + base64.b64encode(b"fake-image").decode()
    
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("app.engineering_agent.engineering_runner.ProjectPlanner.generate_spec", new_callable=AsyncMock) as mock_plan, \
         patch("app.engineering_agent.engineering_runner.VisionEngineer.screenshot_to_code", new_callable=AsyncMock) as mock_vision, \
         patch("app.engineering_agent.engineering_runner.EngineerCrew") as mock_crew_class, \
         patch("app.audit_agent.docker_runner.run_and_monitor", new_callable=AsyncMock) as mock_verify, \
         patch("app.engineering_agent.engineering_runner.storage_client.upload_bytes", new_callable=AsyncMock), \
         patch("app.engineering_agent.engineering_runner.storage_client.get_presigned_url", new_callable=AsyncMock), \
         patch("app.engineering_agent.engineering_runner.ProjectMemory", MagicMock()):
        
        mock_plan.return_value = {"project_name": "VisionApp"}
        mock_vision.return_value = "<button>Mock UI</button>"
        mock_verify.return_value = MagicMock(success=True)
        
        # Mock Crew
        mock_crew_inst = MagicMock()
        mock_crew_class.return_value = mock_crew_inst
        mock_crew_inst.crew.return_value.kickoff.return_value = "Done"
        
        await run_engineering_pipeline(db, job_id, "Clone this UI", image_base64=mock_img)
        
        # Verify Vision was called
        mock_vision.assert_called_once()
        # Verify Vision context was passed to the planner (via enhanced_prompt)
        # enhanced_prompt is the first arg to generate_spec
        enhanced_prompt = mock_plan.call_args[0][0]
        assert "Visual UI Reconstruction" in enhanced_prompt
        assert "<button>Mock UI</button>" in enhanced_prompt
