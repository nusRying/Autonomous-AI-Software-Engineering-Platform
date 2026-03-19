import os
import subprocess
import sys

# Get absolute path to the directory where this script is located
base_dir = os.path.dirname(os.path.abspath(__file__))

env = os.environ.copy()
env["DATABASE_URL"] = "sqlite+aiosqlite:///./app/data/platform.db"
env["REDIS_URL"] = "redis://localhost:6379/0"
env["MINIO_ENDPOINT"] = "http://localhost:9000"

log_path = os.path.join(base_dir, "backend_output.log")

with open(log_path, "w") as f:
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd=base_dir,
        env=env
    )
print(f"Backend started via Popen. Logging to {log_path}")
