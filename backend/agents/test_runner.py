import subprocess
import os

def run_tests(repo_path: str):
    """
    Runs tests in the repository.
    Assumes pytest for python projects or looks for a logical test runner.
    For this specific problem, we'll try running pytest.
    """
    try:
        # Check for requirements.txt to install dependencies (optional but good)
        if os.path.exists(os.path.join(repo_path, "requirements.txt")):
            subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=repo_path, capture_output=True)

        result = subprocess.run(
            ["pytest"], 
            cwd=repo_path, 
            capture_output=True, 
            text=True
        )
        
        passed = result.returncode == 0
        output = result.stdout + "\n" + result.stderr
        
        return {
            "passed": passed,
            "output": output
        }
    except Exception as e:
        return {
            "passed": False,
            "output": str(e)
        }
