import gitlab
import os
import subprocess
import time
import requests

GITLAB_URL = "http://localhost:8080"
PRIVATE_TOKEN = "glpat-MVPTOKEN123456789012"

def run_command(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.stdout, result.stderr

def init_gitlab():
    print("Checking GitLab availability...")
    max_retries = 30
    for i in range(max_retries):
        try:
            resp = requests.get(GITLAB_URL)
            if resp.status_code == 200:
                print("GitLab is up!")
                break
        except:
            pass
        print(f"Waiting for GitLab... ({i+1}/{max_retries})")
        time.sleep(10)
    else:
        print("GitLab timed out.")
        return

    gl = gitlab.Gitlab(GITLAB_URL, private_token=PRIVATE_TOKEN)
    
    project_name = "autonomous-audit-platform"
    try:
        project = gl.projects.create({'name': project_name})
        print(f"Project {project_name} created.")
    except Exception as e:
        print(f"Project might already exist or error: {e}")
        try:
            project = gl.projects.get(f"root/{project_name}")
            print(f"Found existing project.")
        except:
            print("Could not find project.")
            return

    repo_path = "C:\\Users\\umair\\Videos\\Freelance\\Aoi Kei\\Project 1\\autonomous-audit-platform"
    
    # Push using PAT in URL
    remote_url = f"http://root:{PRIVATE_TOKEN}@localhost:8080/root/{project_name}.git"
    
    run_command(f"git remote remove origin", cwd=repo_path)
    run_command(f"git remote add origin {remote_url}", cwd=repo_path)
    
    print("Pushing to GitLab...")
    stdout, stderr = run_command("git push -u origin master", cwd=repo_path)
    print(stdout)
    print(stderr)

if __name__ == "__main__":
    init_gitlab()
