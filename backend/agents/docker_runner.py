import docker
import os
import tarfile
import io
import time

class DockerTestRunner:
    def __init__(self, repo_path: str, image: str = "python:3.11-slim"):
        import urllib3
        print(f"DEBUG: urllib3 version: {urllib3.__version__}")
        try:
            self.client = docker.from_env()
            self.client.ping() # Verify connection immediately
        except Exception as e:
            print(f"Standard connection failed: {e}")
            if os.name == 'nt':
                print("Fallback: connecting to npipe:////./pipe/docker_engine")
                try:
                    self.client = docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
                except Exception:
                     print("Docker unavailable (Windows).")
                     self.client = None
            else:
                print("Docker unavailable (Linux/Cloud). Continuing with client=None.")
                self.client = None
        self.repo_path = os.path.abspath(repo_path)
        self.image = image
        self.container = None

    def build_image(self, tag: str) -> dict:
        """
        Builds the Docker image from the repo path.
        Returns a dictionary with status and logs.
        """
        """
        if not self.client:
            return {"status": "error", "logs": "Docker unavailable on this system."}
            
        try:
            print(f"Building image for {self.repo_path} with tag {tag}...")
            # Use low-level API to capture logs if needed, but high-level is easier for status
            image, build_logs = self.client.images.build(
                path=self.repo_path,
                tag=tag,
                rm=True,
                forcerm=True
            )
            
            # Format logs from generator if possible, but high-level returns list of dicts or logs
            # Actually client.images.build returns (Image, generator) if quiet=False (default)
            # wait, client.images.build signature depends on SDK version. 
            # In standard docker-py:
            # - if quiet=False (default), returns tuple (Image, logs_generator) NOT TRUE for recent versions?
            # Let's check documentation or assume standard behavior. 
            # Actually, standard behavior for 'build' path based is often just the image object or it raises BuildError.
            # Let's wrap in try-except BuildError.
            
            return {
                "status": "success",
                "logs": "Image built successfully",
                "image": image
            }
            
        except docker.errors.BuildError as e:
            # Capture build logs from the exception
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
        Mounts the repo path to /app.
        """
        if not self.client:
             return {
                "status": "error",
                "logs": "Docker unavailable. Cannot run tests in container.",
                "exit_code": -1
            }

        try:
            # Pull image if not present (optional, takes time)
            # self.client.images.pull(self.image)

            print(f"Starting test container for {self.repo_path}...")
            
            # Using volumes to mount the code
            # Note: On Windows, paths might need converting if using WSL/Docker Desktop
            # Assuming standard Windows path or Git Bash path works with Docker Desktop
            
            self.container = self.client.containers.run(
                self.image,
                command=f"bash -c 'pip install pytest && {command}'", # Simple setup
                volumes={self.repo_path: {'bind': '/app', 'mode': 'rw'}},
                working_dir='/app',
                detach=True,
                remove=False # Keep it to inspect logs
            )
            
            # Wait for container to finish
            result = self.container.wait()
            logs = self.container.logs().decode("utf-8")
            exit_code = result['StatusCode']
            
            # Cleanup
            self.container.remove()
            
            return {
                "status": "success" if exit_code == 0 else "failed",
                "logs": logs,
                "exit_code": exit_code
            }

        except docker.errors.DockerException as e:
            return {
                "status": "error",
                "logs": str(e),
                "exit_code": -1
            }
        except Exception as e:
            return {
                "status": "error",
                "logs": f"Unexpected error: {str(e)}",
                "exit_code": -1
            }

def run_tests_in_docker(repo_path: str) -> dict:
    runner = DockerTestRunner(repo_path)
    # Assume requirements.txt is in the repo, might need installation
    # For speed, using just pytest here, but in a real scenario we'd do:
    # pip install -r requirements.txt && pytest
    return runner.run_tests(command="pip install -r requirements.txt && pytest")
