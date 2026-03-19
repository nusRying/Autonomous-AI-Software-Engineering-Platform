"""
Complete Rigorous E2E Testing Suite for Milestone 1 & 2.
Covers:
- M1: API Rotation, Audit Workflow, RBAC, Usage Monitoring.
- M2: Vision, Self-Correction (Retry Exhaustion), File Writing, Dashboard Integration.
- Edge Cases: Corrupted inputs, limit hits, failed tools.
"""

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
from datetime import datetime, timezone, timedelta

# App Imports
from app.db.models import UserDB, UserRole, APIKeyDB, APIUsageDB, AuditJobDB, EngineerJobDB
from app.main import app
from app.utils.security import get_password_hash
from app.api_manager.rotator import call_llm
from app.api_manager.usage_monitor import get_active_keys
from app.audit_agent.audit_runner import run_audit
from app.engineering_agent.engineering_runner import run_engineering_pipeline

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

# ─── M1: API MANAGER EDGE CASES ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_api_manager_all_keys_exhausted(db: AsyncSession):
    """
    EDGE CASE: Verify behavior when ALL keys for a provider are exhausted.
    """
    # 1. Add two exhausted keys
    k1 = APIKeyDB(provider="openai", api_key="sk-1", tokens_used=1000, token_limit=500, is_active=False)
    k2 = APIKeyDB(provider="openai", api_key="sk-2", tokens_used=1000, token_limit=500, is_active=False)
    db.add_all([k1, k2])
    await db.commit()
    
    # 2. Try to get active keys - should return empty list
    active_keys = await get_active_keys(db, "openai")
    assert len(active_keys) == 0
    
    # 3. call_llm should attempt env key if no DB keys
    with patch("app.api_manager.rotator.settings.openai_api_key", ""), \
         patch.dict("os.environ", {"OPENAI_API_KEY": ""}), \
         patch("app.api_manager.rotator.litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        
        # We expect it to reach litellm.acompletion with NO key, which we simulate here
        mock_acomp.side_effect = Exception("Env Key Triggered")
        
        with pytest.raises(Exception) as exc:
            await call_llm(db, [{"role": "user", "content": "test"}], provider="openai")
        assert "Env Key Triggered" in str(exc.value)

@pytest.mark.anyio
async def test_api_manager_auto_reactivation(db: AsyncSession):
    """
    EDGE CASE: Verify that keys are not used if disabled_until is in the future.
    """
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    k1 = APIKeyDB(provider="openai", api_key="sk-1", is_active=True, disabled_until=future_time)
    db.add(k1)
    await db.commit()
    
    active_keys = await get_active_keys(db, "openai")
    assert k1 not in active_keys

# ─── M1: AUDIT & RBAC EDGE CASES ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_audit_rbac_isolation(db: AsyncSession):
    """
    EDGE CASE: Verify that an Observer cannot start an audit.
    """
    import httpx
    # Setup: Create Observer
    username = f"obs_{uuid.uuid4().hex[:8]}"
    obs_user = UserDB(username=username, email=f"{username}@audit.com", hashed_password=get_password_hash("p"), role=UserRole.OBSERVER)
    db.add(obs_user)
    await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login_resp = await client.post("/api/auth/login", data={"username": username, "password": "p"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to trigger audit (M1)
        resp = await client.post("/audit/", json={"repo_path": "./"}, headers=headers)
        assert resp.status_code == 403 # Forbidden

@pytest.mark.anyio
async def test_audit_corrupted_doc_handling(db: AsyncSession):
    """
    EDGE CASE: Verify audit agent handles corrupted/unreadable project files gracefully.
    """
    job_id = str(uuid.uuid4())
    repo_dir = tempfile.mkdtemp()
    # Create a corrupted/binary file where text is expected
    with open(os.path.join(repo_dir, "README.md"), "wb") as f:
        f.write(os.urandom(1000))
    
    with patch("app.orchestrator.crew.AuditCrew", spec=True) as mock_crew_class, \
         patch("app.audit_agent.audit_runner.run_and_monitor", new_callable=AsyncMock) as mock_docker:
        
        mock_crew_inst = MagicMock()
        mock_crew_class.return_value = mock_crew_inst
        
        # Properly mock the nested kickoff result to return a STRING for .raw
        mock_kickoff_res = MagicMock()
        type(mock_kickoff_res).raw = json.dumps({"overall_health_score": 0, "findings": [{"title": "Analysis Error"}]})
        
        mock_crew_inst.crew.return_value.kickoff.return_value = mock_kickoff_res
        
        mock_docker.return_value = MagicMock(success=True)
        
        # Should not crash, should return report with findings
        report = await run_audit(db, job_id, repo_path=repo_dir)
        assert "findings" in report
        
    shutil.rmtree(repo_dir)

# ─── M2: ENGINEERING RETRY EXHAUSTION ────────────────────────────────────────

@pytest.mark.anyio
async def test_engineer_retry_exhaustion(db: AsyncSession):
    """
    EDGE CASE: Verify system behavior when self-correction fails 3 times in a row.
    """
    job_id = str(uuid.uuid4())
    job = EngineerJobDB(job_id=job_id, project_prompt="Impossible Code", status="pending")
    db.add(job)
    await db.commit()
    
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("app.engineering_agent.engineering_runner.ProjectPlanner.generate_spec", new_callable=AsyncMock) as mock_plan, \
         patch("app.engineering_agent.engineering_runner.EngineerCrew") as mock_crew_class, \
         patch("app.audit_agent.docker_runner.run_and_monitor", new_callable=AsyncMock) as mock_verify, \
         patch("app.engineering_agent.engineering_runner.storage_client.upload_bytes", new_callable=AsyncMock), \
         patch("app.engineering_agent.engineering_runner.storage_client.get_presigned_url", return_value="http://minio/fail.zip"), \
         patch("app.engineering_agent.engineering_runner.ProjectMemory") as mock_mem_class:
        
        mock_mem_inst = MagicMock()
        mock_mem_inst.query_context = AsyncMock(return_value="")
        mock_mem_inst.add_context = AsyncMock()
        mock_mem_class.return_value = mock_mem_inst

        mock_plan.return_value = {"project_name": "FailApp"}
        # Fail consistently
        mock_verify.return_value = MagicMock(success=False, stdout="Persistent Error", stderr="Death")
        
        mock_crew_inst = MagicMock()
        mock_crew_class.return_value = mock_crew_inst
        mock_crew_inst.crew.return_value.kickoff.return_value = "Broken Code"
        
        # We expect a RuntimeError from our new check
        with pytest.raises(RuntimeError) as exc:
            await run_engineering_pipeline(db, job_id, "Impossible Code")
        assert "Max retries reached" in str(exc.value)
        
        await db.refresh(job)
        assert job.status == "failed"
        assert "Max retries reached" in job.error

# ─── M2: VISION WITH CORRUPTED IMAGE ─────────────────────────────────────────

@pytest.mark.anyio
async def test_vision_corrupted_image(db: AsyncSession):
    """
    EDGE CASE: Verify vision processor handles garbage base64 strings gracefully.
    """
    job_id = str(uuid.uuid4())
    job = EngineerJobDB(job_id=job_id, project_prompt="UI Project", status="pending")
    db.add(job)
    await db.commit()
    
    garbage_img = "data:image/png;base64,THIS_IS_NOT_AN_IMAGE_!!!!"
    
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("app.engineering_agent.engineering_runner.ProjectPlanner.generate_spec", new_callable=AsyncMock) as mock_plan, \
         patch("app.engineering_agent.engineering_runner.VisionEngineer.screenshot_to_code", new_callable=AsyncMock) as mock_vision, \
         patch("app.engineering_agent.engineering_runner.EngineerCrew") as mock_crew_class, \
         patch("app.audit_agent.docker_runner.run_and_monitor", new_callable=AsyncMock) as mock_verify, \
         patch("app.engineering_agent.engineering_runner.storage_client.get_presigned_url", return_value="http://minio/vision.zip"), \
         patch("app.engineering_agent.engineering_runner.ProjectMemory") as mock_mem_class:
        
        mock_mem_inst = MagicMock()
        mock_mem_inst.query_context = AsyncMock(return_value="")
        mock_mem_inst.add_context = AsyncMock()
        mock_mem_class.return_value = mock_mem_inst

        # Mock vision to raise an error
        mock_vision.side_effect = Exception("Invalid image data")
        mock_plan.return_value = {"project_name": "VisionFail"}
        mock_verify.return_value = MagicMock(success=True)
        mock_crew_inst = MagicMock()
        mock_crew_class.return_value = mock_crew_inst
        mock_crew_inst.crew.return_value.kickoff.return_value = "Standard code without vision"
        
        # Pipeline should handle vision failure and still complete
        result = await run_engineering_pipeline(db, job_id, "UI Project", image_base64=garbage_img)
        
        assert result["status"] == "completed" 
        await db.refresh(job)
        assert job.status == "completed"

# ─── M1 + M2 INTEGRATION: FULL CYCLE ─────────────────────────────────────────

@pytest.mark.anyio
async def test_full_platform_cycle_m1_m2(db: AsyncSession):
    """
    INTEGRATION: 
    1. Engineer generates project (M2).
    2. Auditor audits generated project (M1).
    Verify artifacts flow correctly.
    """
    job_id_m2 = str(uuid.uuid4())
    job_id_m1 = str(uuid.uuid4())
    
    # Pre-create Engineer Job in DB
    job_m2 = EngineerJobDB(job_id=job_id_m2, project_prompt="Generate and audit me", status="pending")
    db.add(job_m2)
    # Pre-create Audit Job in DB
    job_m1 = AuditJobDB(job_id=job_id_m1, status="pending")
    db.add(job_m1)
    await db.commit()

    mock_spec = {"project_name": "IntegratedApp"}
    repo_dir = tempfile.mkdtemp()
    inner_repo = os.path.join(repo_dir, "integratedapp")
    os.makedirs(inner_repo, exist_ok=True)
    with open(os.path.join(inner_repo, "main.py"), "w") as f: f.write("print('Hello World')")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         patch("app.engineering_agent.engineering_runner.ProjectPlanner.generate_spec", new_callable=AsyncMock) as mock_plan, \
         patch("app.engineering_agent.engineering_runner.EngineerCrew") as mock_crew_class, \
         patch("app.audit_agent.docker_runner.run_and_monitor", new_callable=AsyncMock) as mock_verify, \
         patch("app.engineering_agent.engineering_runner.storage_client.upload_bytes", new_callable=AsyncMock), \
         patch("app.engineering_agent.engineering_runner.storage_client.get_presigned_url", return_value="http://minio/integrated.zip"), \
         patch("app.engineering_agent.engineering_runner.ProjectMemory") as mock_mem_class, \
         patch("app.orchestrator.crew.AuditCrew", spec=True) as mock_audit_crew_class:
        
        mock_mem_inst = MagicMock()
        mock_mem_inst.query_context = AsyncMock(return_value="")
        mock_mem_inst.add_context = AsyncMock()
        mock_mem_class.return_value = mock_mem_inst

        # 1. Setup Engineer Success
        mock_plan.return_value = mock_spec
        mock_verify.return_value = MagicMock(success=True)
        mock_crew_inst = MagicMock()
        mock_crew_class.return_value = mock_crew_inst
        mock_crew_inst.crew.return_value.kickoff.return_value = "Project Generated"
        
        # Patch tempfile.mkdtemp to return our controlled repo_dir
        with patch("app.engineering_agent.engineering_runner.tempfile.mkdtemp", return_value=repo_dir), \
             patch("app.engineering_agent.engineering_runner.open", MagicMock()):
            
            # 2. Setup Audit Success
            mock_audit_crew_inst = MagicMock()
            mock_kickoff_res = MagicMock()
            type(mock_kickoff_res).raw = json.dumps({"overall_health_score": 10, "findings": []})
            mock_audit_crew_inst.crew.return_value.kickoff.return_value = mock_kickoff_res
            mock_audit_crew_class.return_value = mock_audit_crew_inst

            # Trigger M2
            eng_res = await run_engineering_pipeline(db, job_id_m2, "Generate and audit me")
            assert eng_res["status"] == "completed"

            # Trigger M1 on same path
            aud_res = await run_audit(db, job_id_m1, repo_path=inner_repo)
            assert aud_res["overall_health_score"] == 10

    shutil.rmtree(repo_dir)
