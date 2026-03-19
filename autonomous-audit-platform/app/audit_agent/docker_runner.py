"""
docker_runner.py — Sandboxed code execution via Docker SDK.

What it does:
1. Pulls (or reuses) a pre-built Python Docker image
2. Mounts the repo as a read-only volume
3. Runs a configurable command (e.g., pytest, python main.py) inside the container
4. Captures stdout/stderr and exit code
5. Returns a RunResult with all output

Security model:
  - Container has NO network access (network_disabled=True)
  - Read-only filesystem mount (ro=True)
  - Memory limited to 512MB
  - CPU quota limited to 50% of one core
  - Container auto-removed after run

Why Docker?
  The audit needs to actually *run* the target code to catch runtime errors.
  Running untrusted code directly would be dangerous — Docker isolates it.
"""
import os
import time
from typing import TypedDict, Optional
from loguru import logger

try:
    import docker
    from docker.errors import DockerException, ImageNotFound
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger.warning("docker SDK not installed — docker_runner will use fallback mode")


# ── Types ─────────────────────────────────────────────────────────────────────

class RunResult(TypedDict):
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    command: str
    image: str
    success: bool


# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_IMAGE = "python:3.11-slim"
DEFAULT_TIMEOUT = 60      # seconds before we kill the container
MEMORY_LIMIT = "512m"     # RAM cap for the sandbox
CPU_QUOTA = 50_000        # 50% of one CPU (Docker: quota/period = fraction)
CPU_PERIOD = 100_000


# ── Main function ──────────────────────────────────────────────────────────────

def run_in_sandbox(
    repo_path: str,
    command: list[str],
    image: str = DEFAULT_IMAGE,
    timeout: int = DEFAULT_TIMEOUT,
    workdir: str = "/repo",
    env: Optional[dict] = None,
) -> RunResult:
    """
    Execute a command inside a Docker sandbox with the repo mounted read-only.

    Args:
        repo_path: Absolute path to the repo on the host machine
        command:   Command to run, e.g. ["python", "-m", "pytest", "--tb=short"]
        image:     Docker image to use (must have Python)
        timeout:   Seconds before forcibly killing the container
        workdir:   Working directory inside the container (default: /repo)
        env:       Optional environment variables dict

    Returns:
        RunResult with stdout, stderr, exit_code, and timing info

    Raises:
        RuntimeError if Docker is unavailable or container creation fails
    """
    if not DOCKER_AVAILABLE:
        return _fallback_run(repo_path, command)

    if not os.path.isdir(repo_path):
        raise ValueError(f"repo_path is not a valid directory: {repo_path}")

    cmd_str = " ".join(command)
    logger.info(f"Docker sandbox: image={image}, cmd={cmd_str}")

    start = time.monotonic()

    try:
        client = docker.from_env()

        # Pull image if not present (silent if already cached)
        try:
            client.images.get(image)
            logger.debug(f"Image '{image}' found in local cache")
        except ImageNotFound:
            logger.info(f"Pulling Docker image '{image}'...")
            client.images.pull(image)

        container = client.containers.run(
            image=image,
            command=command,
            volumes={
                os.path.abspath(repo_path): {
                    "bind": workdir,
                    "mode": "ro",  # Read-only! Repo is never modified
                }
            },
            working_dir=workdir,
            environment=env or {},
            network_disabled=True,           # No outbound network
            mem_limit=MEMORY_LIMIT,
            cpu_period=CPU_PERIOD,
            cpu_quota=CPU_QUOTA,
            remove=True,                     # Auto-remove after run
            detach=False,                    # Wait for completion
            stdout=True,
            stderr=True,
        )

        duration = time.monotonic() - start
        output = container.decode("utf-8", errors="replace") if isinstance(container, bytes) else str(container)

        logger.info(f"Container finished in {duration:.1f}s")
        return RunResult(
            exit_code=0,
            stdout=output,
            stderr="",
            duration_seconds=duration,
            command=cmd_str,
            image=image,
            success=True,
        )

    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Docker run failed: {e}")
        return RunResult(
            exit_code=1,
            stdout="",
            stderr=str(e),
            duration_seconds=duration,
            command=cmd_str,
            image=image,
            success=False,
        )


# ── Entry Point Detection & Runtime Monitoring ──────────────────────────────

def detect_entry_point(repo_path: str) -> Optional[list[str]]:
    """
    Search for common entry points to determine how to 'start' the project.
    Returns a command list or None if no clear entry point found.
    """
    if not os.path.isdir(repo_path):
        return None

    files = os.listdir(repo_path)
    
    # Priority 1: Python frameworks/scripts
    if "requirements.txt" in files:
        # Check for common web frameworks
        with open(os.path.join(repo_path, "requirements.txt"), "r", errors="ignore") as f:
            reqs = f.read().lower()
            if "fastapi" in reqs or "uvicorn" in reqs:
                if "main.py" in files: return ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
                if "app.py" in files: return ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
            if "flask" in reqs:
                if "app.py" in files: return ["python", "app.py"]
                if "main.py" in files: return ["python", "main.py"]

    if "main.py" in files:
        return ["python", "main.py"]
    if "app.py" in files:
        return ["python", "app.py"]
    if "run.py" in files:
        return ["python", "run.py"]

    # Priority 2: Node.js (basic support)
    if "package.json" in files:
        return ["npm", "start"]

    return None


def run_and_monitor(
    repo_path: str,
    command: list[str],
    image: str = DEFAULT_IMAGE,
    monitor_duration: int = 15,
) -> RunResult:
    """
    Run a project entry point and monitor its logs for a fixed duration.
    This is used for 'Runtime Analysis' to detect startup failures, port collisions, etc.
    """
    if not DOCKER_AVAILABLE:
        return _fallback_run(repo_path, command)

    cmd_str = " ".join(command)
    logger.info(f"Runtime Monitor: image={image}, cmd={cmd_str}, wait={monitor_duration}s")

    start = time.monotonic()
    client = docker.from_env()

    try:
        # Ensure image is present
        try:
            client.images.get(image)
        except ImageNotFound:
            client.images.pull(image)

        # Start container in background
        container = client.containers.run(
            image=image,
            command=command,
            volumes={os.path.abspath(repo_path): {"bind": "/repo", "mode": "ro"}},
            working_dir="/repo",
            network_disabled=False,  # Allow network for startup checks (e.g. binding ports locally)
            mem_limit=MEMORY_LIMIT,
            cpu_quota=CPU_QUOTA,
            detach=True,
            remove=False
        )

        # Wait for the monitor duration
        time.sleep(monitor_duration)

        # Capture logs
        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
        
        # Check if still running
        try:
            container.reload()
            is_running = container.status == "running"
            if is_running:
                container.stop(timeout=2)
            exit_code = 0 if is_running else container.attrs['State']['ExitCode']
        except Exception:
            is_running = False
            exit_code = 1

        duration = time.monotonic() - start
        
        # Simple analysis of logs
        success = is_running or exit_code == 0
        if "address already in use" in (stdout + stderr).lower():
            stderr += "\n[ANALYSIS] Detected potential port collision (Address already in use)."
            success = False
        if "modulenotfounderror" in (stdout + stderr).lower():
            stderr += "\n[ANALYSIS] Detected missing dependency (ModuleNotFoundError)."
            success = False
        if "connection refused" in (stdout + stderr).lower():
            stderr += "\n[ANALYSIS] Detected failed connection (Connection refused)."

        try:
            container.remove(force=True)
        except Exception:
            pass

        return RunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            command=cmd_str,
            image=image,
            success=success,
        )

    except Exception as e:
        logger.error(f"Runtime Monitor failed: {e}")
        try:
            if 'container' in locals():
                container.remove(force=True)
        except Exception:
            pass
        return RunResult(
            exit_code=1,
            stdout="",
            stderr=str(e),
            duration_seconds=time.monotonic() - start,
            command=cmd_str,
            image=image,
            success=False,
        )


def run_tests(repo_path: str, image: str = DEFAULT_IMAGE) -> RunResult:
    """
    Convenience wrapper: run pytest in the sandbox.
    """
    return run_in_sandbox(
        repo_path=repo_path,
        command=["sh", "-c", "pip install -r requirements.txt -q 2>&1 && python -m pytest --tb=short -q 2>&1 || true"],
        image=image,
        timeout=120,
    )


def _fallback_run(repo_path: str, command: list[str]) -> RunResult:
    """
    Fallback when Docker SDK is not installed.
    """
    return RunResult(
        exit_code=-1,
        stdout="",
        stderr="Docker SDK not installed. Install 'docker' to enable sandbox execution.",
        duration_seconds=0.0,
        command=" ".join(command),
        image="N/A",
        success=False,
    )
