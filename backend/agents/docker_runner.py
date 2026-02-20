import docker
import os
import subprocess
import sys

class DockerTestRunner:
    def __init__(self, repo_path: str, image: str = "python:3.11-slim"):
        try:
            import urllib3
            print(f"DEBUG: urllib3 version: {urllib3.__version__}")
        except ImportError:
            pass

        self.client = None
        try:
            # Try to connect to Docker
            self.client = docker.from_env()
            self.client.ping() # Verify connection immediately
            print("Docker connection successful. Running in Docker mode.")
        except Exception as e:
            print(f"Standard Docker connection failed: {e}")
            if os.name == 'nt':
                print("Fallback: connecting to npipe:////./pipe/docker_engine")
                try:
                    self.client = docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
                    print("Docker connection successful via npipe.")
                except Exception:
                    print("Docker unavailable (Windows). Falling back to local execution.")
                    self.client = None
            else:
                print("Docker unavailable (Linux/Cloud). Falling back to local execution.")
                self.client = None
                
        self.repo_path = os.path.abspath(repo_path)
        self.image = image
        self.container = None

    def build_image(self, tag: str) -> dict:
        """
        Builds the Docker image from the repo path.
        If Docker is unavailable (e.g., on Render), skips the build.
        """
        if not self.client:
            print("Skipping Docker build: Docker is unavailable on this system (Render/Cloud mode).")
            return {
                "status": "success", 
                "logs": "Skipped build because Docker is unavailable. Proceeding with local execution.",
                "image": None
            }
            
        try:
            print(f"Building image for {self.repo_path} with tag {tag}...")
            image, build_logs = self.client.images.build(
                path=self.repo_path,
                tag=tag,
                rm=True,
                forcerm=True
            )
            
            return {
                "status": "success",
                "logs": "Image built successfully",
                "image": image
            }
            
        except docker.errors.BuildError as e:
            build_logs = ""
            for line in e.build_log:
                if 'stream' in line:
                    build_logs += line['stream']
            
            return {
                "status": "error",
                "logs": build_logs or str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "logs": f"Unexpected build error: {str(e)}"
            }

    def run_tests(self, command: str = "pytest"):
        """
        Runs tests inside a Docker container.
        If Docker is unavailable, runs the tests locally via subprocess.
        """
        if not self.client:
            print(f"Docker unavailable. Running command locally on host: {command}")
            return self._run_tests_locally(command)

        try:
            print(f"Starting test container for {self.repo_path}...")
            self.container = self.client.containers.run(
                self.image,
                command=f"bash -c '{command}'", 
                volumes={self.repo_path: {'bind': '/app', 'mode': 'rw'}},
                working_dir='/app',
                detach=True,
                remove=False 
            )
            
            result = self.container.wait()
            logs = self.container.logs().decode("utf-8")
            exit_code = result['StatusCode']
            
            self.container.remove()
            
            return {
                "status": "success" if exit_code == 0 else "failed",
                "logs": logs,
                "exit_code": exit_code
            }

        except docker.errors.DockerException as e:
            return {"status": "error", "logs": str(e), "exit_code": -1}
        except Exception as e:
            return {"status": "error", "logs": f"Unexpected error: {str(e)}", "exit_code": -1}

    def _run_tests_locally(self, command: str) -> dict:
        """
        Fallback method to run tests directly on the host machine using subprocess.
        """
        try:
            # Run the command directly in the repository directory
            process = subprocess.run(
                command,
                shell=True,            
                cwd=self.repo_path,    
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True              
            ) # <--- Make sure this closing parenthesis is here!
            
            return {
                "status": "success" if process.returncode == 0 else "failed",
                "logs": process.stdout,
                "exit_code": process.returncode
            }
            
        except Exception as e:
            return {
                "status": "error",
                "logs": f"Local execution failed: {str(e)}",
                "exit_code": -1
            }