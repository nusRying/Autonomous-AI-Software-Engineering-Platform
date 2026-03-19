"""
Rigorous E2E tests for the Milestone 2 Autonomous Engineer flow.
"""
import pytest
import httpx
import uuid
import json
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import EngineerJobDB, UserDB, UserRole
from app.main import app
from app.utils.security import get_password_hash

@pytest.mark.anyio
async def test_engineer_create_project_success(db: AsyncSession):
    """
    Verify that a developer can trigger the engineering pipeline.
    """
    # Setup: Create Developer User
    dev_user = UserDB(username="engineer_dev", email="dev@engineer.com", hashed_password=get_password_hash("p"), role=UserRole.DEVELOPER)
    db.add(dev_user)
    await db.commit()
    await db.refresh(dev_user)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login
        login_resp = await client.post("/api/auth/login", data={"username": "engineer_dev", "password": "p"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Submit Project Prompt
        # Mock Temporal and Celery to avoid starting real workers
        # Also patch AsyncSessionLocal to use the test engine's session
        from app.api.routes.engineer import AsyncSessionLocal
        with patch("app.api.routes.engineer.settings.use_temporal", False), \
             patch("app.api.routes.engineer.CELERY_AVAILABLE", False), \
             patch("app.api.routes.engineer.settings.debug", True), \
             patch("app.api.routes.engineer.AsyncSessionLocal", return_value=db):
            
            payload = {"project_prompt": "Create a simple Task Manager API with FastAPI."}
            resp = await client.post("/engineer/", json=payload, headers=headers)
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]
            assert resp.json()["status"] == "pending"

        # 3. Verify Job in DB
        result = await db.execute(select(EngineerJobDB).where(EngineerJobDB.job_id == job_id))
        job = result.scalar_one_or_none()
        assert job is not None
        assert job.project_prompt == payload["project_prompt"]
        assert job.owner_id == dev_user.id

@pytest.mark.anyio
async def test_engineer_pipeline_execution_mocked(db: AsyncSession):
    """
    Verify the engineering runner logic (mocking the heavy agents).
    """
    job_id = str(uuid.uuid4())
    job = EngineerJobDB(job_id=job_id, project_prompt="Mock Project", status="pending")
    db.add(job)
    await db.commit()

    # Mock Planner and Crew
    mock_spec = {"project_name": "MockApp", "architecture": "Clean"}
    mock_crew_res = "Code generated successfully."

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-dummy"}), \
         patch("app.engineering_agent.engineering_runner.ProjectPlanner.generate_spec", new_callable=AsyncMock) as mock_plan, \
         patch("app.engineering_agent.engineering_runner.EngineerCrew") as mock_crew_class, \
         patch("app.engineering_agent.engineering_runner.ProjectMemory.query_context", new_callable=AsyncMock) as mock_mem_query, \
         patch("app.engineering_agent.engineering_runner.ProjectMemory.add_context", new_callable=AsyncMock) as mock_mem_add, \
         patch("app.engineering_agent.engineering_runner.storage_client.upload_bytes", new_callable=AsyncMock), \
         patch("app.engineering_agent.engineering_runner.storage_client.get_presigned_url", new_callable=AsyncMock) as mock_url, \
         patch("app.audit_agent.docker_runner.run_and_monitor", new_callable=AsyncMock) as mock_verify, \
         patch("app.engineering_agent.engineering_runner.VisionEngineer.screenshot_to_code", new_callable=AsyncMock) as mock_vision:
        
        mock_plan.return_value = mock_spec
        mock_vision.return_value = "/* Mock UI Code */"
        
        # Mock Verification Success
        mock_verify_res = MagicMock()
        mock_verify_res.success = True
        mock_verify.return_value = mock_verify_res
        
        # Mock Crew Instance and its crew().kickoff()
        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance
        
        mock_actual_crew = MagicMock()
        mock_actual_crew.kickoff.return_value = mock_crew_res
        mock_crew_instance.crew.return_value = mock_actual_crew
        mock_mem_query.return_value = ""
        mock_url.return_value = "http://minio/mock.zip"

        from app.engineering_agent.engineering_runner import run_engineering_pipeline
        result = await run_engineering_pipeline(db, job_id, "Mock Project", image_base64="data:image/png;base64,mock")

        assert result["status"] == "completed"
        assert result["project_name"] == "MockApp"
        
        # Verify DB final state
        await db.refresh(job)
        assert job.status == "completed"
        assert job.technical_spec == mock_spec
        assert job.minio_repo_zip_url == "http://minio/mock.zip"
