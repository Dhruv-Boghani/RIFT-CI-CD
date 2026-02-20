import os
import shutil
import git
import stat
import time
from backend.config import Config

def on_rm_error(func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clone_repository(repo_url: str, repo_path: str):
    if os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path, onerror=on_rm_error)
        except Exception as e:
            print(f"Error cleaning directory: {e}")
            # If permission error persists, maybe we should re-raise or handle it differently
            # But for now, let's assume the handler creates a clean slate or throws
            pass
    
    try:
        git.Repo.clone_from(repo_url, repo_path)
        return {"status": "success", "path": repo_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def checkout_branch(repo_path: str, branch_name: str):
    try:
        repo = git.Repo(repo_path)
        # Check if branch exists
        if branch_name in repo.heads:
            repo.heads[branch_name].checkout()
        else:
            repo.git.checkout('-b', branch_name)
        return {"status": "success", "branch": branch_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
