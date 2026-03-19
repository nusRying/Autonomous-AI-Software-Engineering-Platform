"""
Rigorous Security & RBAC tests for Milestone 1.
"""
import pytest
import httpx
from fastapi import status
from app.main import app

@pytest.mark.anyio
async def test_unauthorized_access():
    """Verify that accessing endpoints without a token returns 401."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Audit list
        resp = await client.get("/audit/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        
        # API Keys list
        resp = await client.get("/api/api_keys/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.anyio
async def test_full_rbac_suite(db):
    """Integrated test for RBAC flow using the 'db' fixture."""
    from app.db.models import UserDB, UserRole
    from app.utils.security import get_password_hash
    
    # Setup: Create Admin, Developer, Observer
    admin_user = UserDB(username="admin_test", email="a@t.com", hashed_password=get_password_hash("p"), role=UserRole.ADMIN)
    dev_user = UserDB(username="dev_test", email="d@t.com", hashed_password=get_password_hash("p"), role=UserRole.DEVELOPER)
    obs_user = UserDB(username="obs_test", email="o@t.com", hashed_password=get_password_hash("p"), role=UserRole.OBSERVER)
    db.add_all([admin_user, dev_user, obs_user])
    await db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # ── Test Observer ──
        login_resp = await client.post("/api/auth/login", data={"username": "obs_test", "password": "p"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Should fail adding key
        resp = await client.post("/api/api_keys/", json={"provider": "openai", "api_key": "sk-valid-length-key"}, headers=headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        # ── Test Developer ──
        login_resp = await client.post("/api/auth/login", data={"username": "dev_test", "password": "p"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Should succeed triggering audit (returns 202)
        resp = await client.post("/audit/", json={"repo_path": "./"}, headers=headers)
        assert resp.status_code == status.HTTP_202_ACCEPTED

        # ── Test Admin ──
        login_resp = await client.post("/api/auth/login", data={"username": "admin_test", "password": "p"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Should succeed adding key
        resp = await client.post("/api/api_keys/", json={"provider": "openai", "api_key": "sk-valid-length-key", "label": "test"}, headers=headers)
        assert resp.status_code == 201
