import os
import pytest
from unittest.mock import MagicMock, patch
from app.audit_agent.docker_runner import run_in_sandbox, run_and_monitor, RunResult

@pytest.fixture
def mock_docker_client():
    with patch("docker.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_docker_available():
    with patch("app.audit_agent.docker_runner.DOCKER_AVAILABLE", True):
        yield

def test_run_in_sandbox_success(mock_docker_client, mock_docker_available):
    # Setup
    mock_container = MagicMock()
    mock_container.decode.return_value = "Success output"
    mock_docker_client.containers.run.return_value = b"Success output"
    
    # Execute
    result = run_in_sandbox("/tmp/fake-repo", ["python", "app.py"])
    
    # Assert
    assert result["success"] is True
    assert "Success output" in result["stdout"]
    assert result["exit_code"] == 0

def test_run_and_monitor_port_collision(mock_docker_client, mock_docker_available):
    # Setup
    mock_container = MagicMock()
    mock_container.logs.return_value = b"Error: Address already in use"
    mock_container.status = "exited"
    mock_container.attrs = {'State': {'ExitCode': 1}}
    mock_docker_client.containers.run.return_value = mock_container
    
    # Execute
    result = run_and_monitor("/tmp/fake-repo", ["uvicorn", "main:app"], monitor_duration=0)
    
    # Assert
    assert result["success"] is False
    assert "port collision" in result["stderr"]
    assert "Address already in use" in result["stdout"]

def test_run_and_monitor_missing_dependency(mock_docker_client, mock_docker_available):
    # Setup
    mock_container = MagicMock()
    mock_container.logs.return_value = b"ModuleNotFoundError: No module named 'fastapi'"
    mock_container.status = "exited"
    mock_container.attrs = {'State': {'ExitCode': 1}}
    mock_docker_client.containers.run.return_value = mock_container
    
    # Execute
    result = run_and_monitor("/tmp/fake-repo", ["python", "main.py"], monitor_duration=0)
    
    # Assert
    assert result["success"] is False
    assert "missing dependency" in result["stderr"]
    assert "ModuleNotFoundError" in result["stdout"]

def test_fallback_when_docker_unavailable():
    with patch("app.audit_agent.docker_runner.DOCKER_AVAILABLE", False):
        result = run_in_sandbox("/tmp/fake-repo", ["python", "app.py"])
        assert result["success"] is False
        assert "Docker SDK not installed" in result["stderr"]
