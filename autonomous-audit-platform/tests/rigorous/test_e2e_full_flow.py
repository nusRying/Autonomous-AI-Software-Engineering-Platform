"""
Rigorous E2E tests for the full audit flow.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import AuditJobDB, UserDB, UserRole
from app.models.audit import AuditStatus
from app.main import app
from app.utils.security import get_password_hash

@pytest.mark.anyio
async def test_full_audit_flow_success(db: AsyncSession):
    """
    Verify the complete Golden Path:
    1. Login as Admin/Developer
    2. Submit Audit
    3. Mock background task execution (_run_audit_logic)
    4. Verify DB state and results via API
    """
    # Setup: Create User
    admin_user = UserDB(username="e2e_admin", email="e2e@t.com", hashed_password=get_password_hash("p"), role=UserRole.ADMIN)
    db.add(admin_user)
    await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login
        login_resp = await client.post("/api/auth/login", data={"username": "e2e_admin", "password": "p"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Submit Audit
        with patch("app.api.routes.audit.settings.use_temporal", False), \
             patch("app.api.routes.audit.CELERY_AVAILABLE", False), \
             patch("app.api.routes.audit.settings.debug", True):
            
            resp = await client.post("/audit/", json={"repo_path": "./"}, headers=headers)
            assert resp.status_code == 202
            job_id = resp.json()["job_id"]

        # 3. Simulate background execution
        mock_report = {
            "overall_health_score": 9,
            "executive_summary": "Excellent codebase.",
            "findings": [{"title": "Test Finding", "severity": "LOW", "description": "None"}],
            "total_files_scanned": 10,
            "total_lines_scanned": 1000,
            "minio_json_url": "http://minio/report.json"
        }
        
        # Patch run_audit properly
        with patch("app.api.routes.audit.AUDIT_RUNNER_AVAILABLE", True), \
             patch("app.api.routes.audit.run_audit", new_callable=AsyncMock) as mock_run:
            
            mock_run.return_value = mock_report
            from app.api.routes.audit import _run_audit_logic
            await _run_audit_logic(db, job_id, "./", None, False, admin_user.id)

        # 4. Verify Final State
        resp = await client.get(f"/audit/{job_id}", headers=headers)
        data = resp.json()
        assert data["status"] == "completed"
        assert data["report"]["overall_health_score"] == 9

@pytest.mark.anyio
async def test_audit_visibility_rbac(db: AsyncSession):
    """Verify that users can only see their own audits."""
    from app.utils.security import get_password_hash
    
    # Create two users
    u1 = UserDB(username="user1", email="u1@t.com", hashed_password=get_password_hash("p"), role=UserRole.DEVELOPER)
    u2 = UserDB(username="user2", email="u2@t.com", hashed_password=get_password_hash("p"), role=UserRole.DEVELOPER)
    db.add_all([u1, u2])
    await db.commit()
    await db.refresh(u1)
    await db.refresh(u2)

    # Create a job owned by u1
    job = AuditJobDB(job_id="job-u1", owner_id=u1.id, status="completed", repo_path="./")
    db.add(job)
    await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login as u2
        login_resp = await client.post("/api/auth/login", data={"username": "user2", "password": "p"})
        token2 = login_resp.json()["access_token"]
        
        # Try to view u1's job
        resp = await client.get("/audit/job-u1", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403
