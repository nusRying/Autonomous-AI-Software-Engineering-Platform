import os
import shutil
import tempfile
from app.audit_agent.docker_runner import run_and_monitor

def setup_dummy_project(path, code):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.py"), "w") as f:
        f.write(code)

def run_live_tests():
    print("--- LIVE DOCKER RUNTIME VERIFICATION ---")
    
    # Base temp directory for tests
    base_temp = tempfile.mkdtemp(prefix="audit_test_")
    
    try:
        # Test 1: ModuleNotFoundError
        print("\n[Test 1] Testing ModuleNotFoundError logic...")
        test1_path = os.path.join(base_temp, "dummy_missing_module")
        setup_dummy_project(test1_path, "import non_existent_module_12345")
        
        res1 = run_and_monitor(test1_path, ["python", "main.py"], monitor_duration=2)
        print(f"Success: {res1['success']}")
        print(f"Stdout: {res1['stdout']}")
        print(f"Stderr: {res1['stderr']}")
        if "modulenotfounderror" in (res1["stderr"] + res1["stdout"]).lower():
            print("[SUCCESS] Correctly detected ModuleNotFoundError in output.")
        else:
            print("[FAILED] to detect ModuleNotFoundError in output.")

        # Test 2: Address already in use
        print("\n[Test 2] Testing Port Collision ('Address already in use')...")
        port_collision_code = '''
import socket
import time

try:
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.bind(("0.0.0.0", 8000))

    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2.bind(("0.0.0.0", 8000))
except Exception as e:
    print(f"Error: {e}")
    
time.sleep(2)
'''
        test2_path = os.path.join(base_temp, "dummy_port_collision")
        setup_dummy_project(test2_path, port_collision_code)
        
        res2 = run_and_monitor(test2_path, ["python", "main.py"], monitor_duration=3)
        print(f"Success: {res2['success']}")
        print(f"Stdout: {res2['stdout']}")
        print(f"Stderr: {res2['stderr']}")
        if "address already in use" in (res2["stderr"] + res2["stdout"]).lower():
            print("[SUCCESS] Correctly detected 'Address already in use' in output.")
        else:
            print("[FAILED] to detect 'Address already in use' in output.")

    finally:
        # Cleanup
        shutil.rmtree(base_temp, ignore_errors=True)

if __name__ == "__main__":
    run_live_tests()
