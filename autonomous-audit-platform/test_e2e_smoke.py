"""
Rigorous E2E Smoke Test for Milestone 1 & 2 Combined.
This script performs a LIVE test against the running server.
Requirements: 
1. Backend server running at http://localhost:8000
2. Database initialized with admin/admin123
"""

import httpx
import time
import sys
import json
from loguru import logger

BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def test_full_cycle():
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Login
        logger.info("Step 1: Authenticating...")
        resp = client.post("/api/auth/login", data={"username": ADMIN_USER, "password": ADMIN_PASS})
        if resp.status_code != 200:
            logger.error(f"Login failed: {resp.text}")
            sys.exit(1)
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        logger.success("Authenticated successfully.")

        # 2. Trigger Milestone 2: Autonomous Engineer
        logger.info("Step 2: Triggering Engineering Job (M2)...")
        engineer_payload = {
            "project_prompt": "Create a simple Python utility that calculates Fibonacci numbers and include a README.md."
        }
        resp = client.post("/engineer/", json=engineer_payload, headers=headers)
        if resp.status_code != 202:
            logger.error(f"Engineer trigger failed: {resp.text}")
            sys.exit(1)
        
        engineer_job_id = resp.json()["job_id"]
        logger.info(f"Engineer Job ID: {engineer_job_id}")

        # 3. Poll Engineer Job (Wait for Completion)
        logger.info("Step 3: Polling Engineer Job status...")
        project_path = None
        max_retries = 30
        for i in range(max_retries):
            status_resp = client.get(f"/engineer/{engineer_job_id}", headers=headers)
            job_data = status_resp.json()
            status = job_data["status"]
            logger.info(f"  Attempt {i+1}: Status = {status}")
            
            if status == "completed":
                project_path = job_data.get("generated_repo_path")
                logger.success(f"Engineering project completed. Path: {project_path}")
                break
            elif status == "failed":
                logger.error(f"Engineering project failed: {job_data.get('error')}")
                # For smoke test, we might proceed if it's a mock environment or fail
                sys.exit(1)
            
            time.sleep(5)
        else:
            logger.error("Engineer job timed out.")
            sys.exit(1)

        # 4. Trigger Milestone 1: Software Audit on the generated project
        logger.info("Step 4: Triggering Audit Job (M1) on generated project...")
        audit_payload = {
            "repo_path": project_path,
            "run_tests": True
        }
        resp = client.post("/audit/", json=audit_payload, headers=headers)
        if resp.status_code != 202:
            logger.error(f"Audit trigger failed: {resp.text}")
            sys.exit(1)
        
        audit_job_id = resp.json()["job_id"]
        logger.info(f"Audit Job ID: {audit_job_id}")

        # 5. Poll Audit Job
        logger.info("Step 5: Polling Audit Job status...")
        for i in range(max_retries):
            status_resp = client.get(f"/audit/{audit_job_id}", headers=headers)
            job_data = status_resp.json()
            status = job_data["status"]
            logger.info(f"  Attempt {i+1}: Status = {status}")
            
            if status == "completed":
                logger.success(f"Audit completed! Health Score: {job_data.get('health_score')}")
                logger.info(f"Report Summary: {job_data.get('report_data', {}).get('summary', 'No summary')}")
                break
            elif status == "failed":
                logger.error(f"Audit failed: {job_data.get('error')}")
                sys.exit(1)
            
            time.sleep(5)
        else:
            logger.error("Audit job timed out.")
            sys.exit(1)

        logger.success("Full Milestone 1 & 2 E2E Cycle Verified.")

if __name__ == "__main__":
    test_full_cycle()
