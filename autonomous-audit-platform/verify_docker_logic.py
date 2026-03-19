import os
import sys
from unittest.mock import MagicMock, patch

# Mock Docker available before importing
with patch("app.audit_agent.docker_runner.DOCKER_AVAILABLE", True):
    from app.audit_agent.docker_runner import run_in_sandbox, run_and_monitor

def test_logic():
    print("Testing docker_runner logic with mocks...")
    
    with patch("docker.from_env") as mock_from_env, \
         patch("os.path.abspath", side_effect=lambda x: x), \
         patch("os.path.isdir", return_value=True):
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        
        # Test 1: Successful run
        mock_docker_client = mock_client
        mock_container = MagicMock()
        mock_docker_client.containers.run.return_value = b"Success output"
        
        print("Checking run_in_sandbox success...")
        result = run_in_sandbox("/tmp/fake-repo", ["python", "app.py"])
        assert result["success"] is True
        assert "Success output" in result["stdout"]
        print("✅ SUCCESS: run_in_sandbox correctly captures output.")

        # Test 2: Port collision detection
        print("Checking run_and_monitor port collision...")
        mock_container = MagicMock()
        mock_container.logs.side_effect = lambda stdout, stderr: b"Error: Address already in use" if stdout else b""
        mock_container.status = "exited"
        mock_container.attrs = {'State': {'ExitCode': 1}}
        mock_docker_client.containers.run.return_value = mock_container
        
        # We need to mock time.sleep so it doesn't actually wait
        with patch("time.sleep", return_value=None):
            result = run_and_monitor("/tmp/fake-repo", ["uvicorn", "main:app"], monitor_duration=1)
            
        assert result["success"] is False
        assert "port collision" in result["stderr"].lower()
        print("✅ SUCCESS: run_and_monitor detects port collisions.")

        # Test 3: Missing dependency detection
        print("Checking run_and_monitor missing dependency...")
        mock_container.logs.side_effect = lambda stdout, stderr: b"ModuleNotFoundError: No module named 'fastapi'" if stdout else b""
        
        with patch("time.sleep", return_value=None):
            result = run_and_monitor("/tmp/fake-repo", ["python", "main.py"], monitor_duration=1)
            
        assert result["success"] is False
        assert "missing dependency" in result["stderr"].lower()
        print("✅ SUCCESS: run_and_monitor detects missing dependencies.")

if __name__ == "__main__":
    try:
        test_logic()
        print("\nAll core logic verified successfully.")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
