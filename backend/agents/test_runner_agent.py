from typing import Dict
from backend.docker_manager import DockerManager
from backend.config import Config

class TestRunnerAgent:
    def __init__(self):
        self.docker_manager = DockerManager()

    def run_tests(self, repo_url: str, branch_name: str, token: str, auth_mode: str = "https", private_key: str = None, image_tag: str = "rift-sandbox:latest", mount_path: str = None) -> Dict[str, str]:
        """
        Orchestrates test execution in a sandbox.
        """
        print(f"TestRunner: Starting tests for {repo_url} on branch {branch_name} (Auth: {auth_mode}) using image {image_tag}")
        
        # We delegate the heavy lifting to DockerManager
        # Now passing auth_mode and private_key
        result = self.docker_manager.run_tests_in_sandbox(
            repo_url=repo_url,
            branch_name=branch_name,
            token=token,
            auth_mode=auth_mode,
            private_key=private_key,
            image_tag=image_tag,
            mount_path=mount_path
        )
        
        return result
