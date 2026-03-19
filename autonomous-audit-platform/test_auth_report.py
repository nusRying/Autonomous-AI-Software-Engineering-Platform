import requests

def test():
    base_url = "http://localhost:8000"
    job_id = "b29cb92b-2f45-4290-a0c5-a67c315d8b6f"
    
    # 1. Login
    login_res = requests.post(f"{base_url}/api/auth/login", data={"username": "admin", "password": "admin123"})
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.status_code} {login_res.text}")
        return
    
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful")

    # 2. Get Job Status
    job_res = requests.get(f"{base_url}/audit/{job_id}", headers=headers)
    print(f"Job Status: {job_res.status_code}")
    if job_res.status_code == 200:
        print("Job metadata found")
    
    # 3. Get Report Markdown
    report_res = requests.get(f"{base_url}/audit/{job_id}/report-markdown", headers=headers)
    print(f"Report Markdown Status: {report_res.status_code}")
    print(f"Report Markdown Body: {report_res.text[:200]}")

if __name__ == "__main__":
    test()
