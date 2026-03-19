import os
import subprocess
import sys
import time
import requests

# Set absolute path to base dir
base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

env = os.environ.copy()
env["DATABASE_URL"] = "sqlite+aiosqlite:///./audit_platform.db"
env["REDIS_URL"] = "redis://localhost:6379/0"
env["MINIO_ENDPOINT"] = "http://localhost:9000"

log_file = os.path.join(base_dir, "diag_backend.log")

print(f"Starting backend diagnostic...")
with open(log_file, "w") as f:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=f,
        stderr=subprocess.STDOUT,
        env=env
    )

print(f"Process PID: {proc.pid}")
print("Waiting 10 seconds for startup...")
time.sleep(10)

if proc.poll() is not None:
    print("ERROR: Process terminated prematurely.")
    with open(log_file, "r") as f:
        print("--- LAST 20 LINES OF LOG ---")
        print("".join(f.readlines()[-20:]))
else:
    print("SUCCESS: Process is still running.")
    try:
        resp = requests.get("http://localhost:8000/health", timeout=2)
        print(f"Health Check: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Health Check FAILED: {e}")
    
    # We leave it running if it succeeded
