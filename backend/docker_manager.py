
import docker
import os
import shutil
import time
import json
import base64
import subprocess
from typing import Dict
from backend.config import Config

class DockerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Docker Error: {e}")
            self.client = None

    def build_sandbox_image(self):
        """
        Builds the universal sandbox image if not present.
        """
        if not self.client: return False
        
        try:
            print("Building Universal Sandbox Image (this may take time)...")
            # Point to backend/sandbox.Dockerfile
            dockerfile_path = os.path.join(os.path.dirname(__file__), "sandbox.Dockerfile")
            self.client.images.build(
                path=os.path.dirname(__file__),
                dockerfile="sandbox.Dockerfile",
                tag="rift-sandbox:latest"
            )
            print("Sandbox Image Built Successfully.")
            return True
        except Exception as e:
            print(f"Build Failed: {e}")
            return False

    def run_tests_in_sandbox(self, repo_url: str, branch_name: str, token: str, auth_mode: str = "https", private_key: str = None, image_tag: str = "rift-sandbox:latest", mount_path: str = None) -> Dict:
        """
        Runs tests in a Docker container using Universal Runner.
        If mount_path is provided, mounts that local path instead of cloning.
        """
        if not self.client:
            if Config.AI_AGENT_ALLOW_LOCAL_RUN:
                print("⚠️ Docker not available. Falling back to LOCAL SUBPROCESS execution (AI_AGENT_ALLOW_LOCAL_RUN=True).")
                return self.run_tests_locally(repo_url, branch_name, token, auth_mode, private_key)
            return {"status": "ERROR", "logs": "Docker not available and AI_AGENT_ALLOW_LOCAL_RUN is False."}

        # Check for image
        try:
            self.client.images.get(image_tag)
        except docker.errors.ImageNotFound:
            if image_tag == "rift-sandbox:latest":
                if not self.build_sandbox_image():
                    return {"status": "ERROR", "logs": "Failed to build sandbox image."}
            else:
                 return {"status": "ERROR", "logs": f"Custom image {image_tag} not found."}

        container = None
        try:
            clean_url = repo_url.replace("https://", "")
            
            # 1. Prepare Clone Command (Skip if mounting)
            clone_cmd = ""
            pre_config = ""
            volumes = {}

            if mount_path:
                print(f"Mounting local path {mount_path} instead of cloning.")
                # Mount to /app/repo
                volumes = {mount_path: {'bind': '/app/repo', 'mode': 'rw'}}
                # No clone command needed
            else:
                if auth_mode == "https":
                    if token:
                        auth_url = f"https://{token}@{clean_url}"
                    else:
                        auth_url = repo_url
                    clone_cmd = f"git clone {auth_url} /app/repo"
                    
                elif auth_mode == "ssh":
                    if not private_key:
                        return {"status": "ERROR", "logs": "Private Key missing for SSH mode."}
                        
                    b64_key = base64.b64encode(private_key.encode('utf-8')).decode('utf-8')
                    
                    pre_config = f"""
                    mkdir -p /root/.ssh && \
                    echo '{b64_key}' | base64 -d > /root/.ssh/id_rsa && \
                    chmod 600 /root/.ssh/id_rsa && \
                    ssh-keyscan github.com >> /root/.ssh/known_hosts && \
                    """
                    
                    ssh_url = repo_url
                    if "https://" in repo_url:
                        ssh_url = repo_url.replace("https://github.com/", "git@github.com:")
                    
                    clone_cmd = f"git clone {ssh_url} /app/repo"

            # 2. Inject Universal Runner Script
            # Read script content
            runner_path = os.path.join(os.path.dirname(__file__), "scripts", "universal_runner.py")
            with open(runner_path, "r") as f:
                runner_content = f.read()
            
            b64_runner = base64.b64encode(runner_content.encode('utf-8')).decode('utf-8')

            # 3. Execution Script
            if mount_path:
                # If mounted, we are already in the repo dir effectively, but mapped to /app/repo
                # We just need to ensure dependency install? universal_runner handles that.
                # We do NOT checkout branch if mounted, because we assume local state is what we want.
                script = f"""
                mkdir -p /app/repo && \
                cd /app/repo && \
                echo '{b64_runner}' | base64 -d > /app/universal_runner.py && \
                python3 /app/universal_runner.py
                """
            else:
                script = f"""
                {pre_config}
                {clone_cmd} && \
                cd /app/repo && \
                git checkout {branch_name} || git checkout -b {branch_name} && \
                echo '{b64_runner}' | base64 -d > /app/universal_runner.py && \
                python3 /app/universal_runner.py && \
                rm -rf /root/.ssh/id_rsa
                """
            
            container = self.client.containers.run(
                image_tag,
                command=f"bash -c '{script}'",
                detach=True,
                remove=False,
                volumes=volumes
            )
            
            exit_code = container.wait()
            logs = container.logs().decode("utf-8")
            container.remove()

            # 4. Parse JSON Output
            # The runner outputs JSON at the end, but logs might contain other stuff.
            # Look for the last line or JSON block.
            try:
                # Find start of JSON
                json_start = logs.rfind('{')
                if json_start != -1:
                    json_str = logs[json_start:]
                    result = json.loads(json_str)
                    
                    # Add raw logs if missing or just keep full logs
                    if "raw_logs" not in result or not result["raw_logs"]:
                         result["raw_logs"] = logs
                    
                    # Mask Token
                    if token:
                        result["raw_logs"] = result["raw_logs"].replace(token, "***TOKEN***")
                        
                    return result
            except:
                pass
            
            return {"status": "ERROR", "logs": logs}
            
        except Exception as e:
            if container:
                try: container.kill(); container.remove()
                except: pass
            return {"status": "ERROR", "logs": str(e)}

    def run_tests_locally(self, repo_url: str, branch_name: str, token: str, auth_mode: str = "https", private_key: str = None) -> Dict:
        """
        Fallback: Runs tests locally using subprocess and universal_runner.py.
        """
        import uuid
        run_id = str(uuid.uuid4())[:8]
        local_workspace = os.path.join(Config.WORKSPACE_DIR, f"run_{run_id}")
        repo_dir = os.path.join(local_workspace, "repo")
        
        os.makedirs(repo_dir, exist_ok=True)
        
        try:
            print(f"Starting Local Run: {run_id}")
            
            # 1. Clone
            clean_url = repo_url.replace("https://", "")
            if auth_mode == "https":
                auth_url = f"https://{token}@{clean_url}" if token else repo_url
                subprocess.run(f"git clone {auth_url} {repo_dir}", shell=True, check=True)
            else:
                # SSH fallback tricky locally without setup, assuming check has passed or skipping
                # For now, simple clone
                subprocess.run(f"git clone {repo_url} {repo_dir}", shell=True, check=True)
                
            # 2. Checkout
            subprocess.run(f"cd {repo_dir} && git checkout {branch_name} || git checkout -b {branch_name}", shell=True, check=True)
            
            # 3. Copy Universal Runner
            runner_src = os.path.join(os.path.dirname(__file__), "scripts", "universal_runner.py")
            runner_dest = os.path.join(repo_dir, "universal_runner.py")
            shutil.copy(runner_src, runner_dest)
            
            # 4. Run Runner
            # We run it with the CURRENT python environment (which has deps installed) or a new one?
            # Ideally universal_runner installs its own deps.
            cmd = f"cd {repo_dir} && python3 universal_runner.py"
            
            # Run with timeout
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            logs = process.stdout + "\n" + process.stderr
            
            # 5. Parse JSON
            try:
                json_start = logs.rfind('{')
                if json_start != -1:
                    json_str = logs[json_start:]
                    result = json.loads(json_str)
                    if "raw_logs" not in result or not result["raw_logs"]:
                        result["raw_logs"] = logs
                    return result
            except:
                pass
                
            return {"status": "ERROR", "logs": logs}
            
        except Exception as e:
            return {"status": "ERROR", "logs": f"Local Run Failed: {e}"}
        finally:
            # Cleanup ? Maybe keep for debugging if failed
            # shutil.rmtree(local_workspace, ignore_errors=True)
            pass
