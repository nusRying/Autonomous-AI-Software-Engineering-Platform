import requests

services = {
    "GitLab": "http://localhost:8080",
    "Appsmith": "http://localhost:8081",
    "Structurizr": "http://localhost:8082",
    "SonarQube": "http://localhost:9003",
    "App": "http://localhost:8000"
}

for name, url in services.items():
    try:
        resp = requests.get(url, timeout=3)
        print(f"{name}: {resp.status_code}")
    except Exception as e:
        print(f"{name}: Down ({type(e).__name__})")
