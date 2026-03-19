import os
import subprocess
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

env = os.environ.copy()
env["DATABASE_URL"] = "sqlite+aiosqlite:///./audit_platform.db"
env["REDIS_URL"] = "redis://localhost:6379/0"
env["MINIO_ENDPOINT"] = "http://localhost:9000"

log_file = os.path.join(base_dir, "worker_persistent.log")

with open(log_file, "w") as f:
    subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--concurrency=2"],
        stdout=f,
        stderr=subprocess.STDOUT,
        env=env
    )
print(f"Worker started and logging to {log_file}")
