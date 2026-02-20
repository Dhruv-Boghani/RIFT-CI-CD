import os
import shutil
import stat
import time
import tempfile
from pathlib import Path
from datetime import datetime

class FileUtils:
    @staticmethod
    def create_workspace(base_dir: str = "workspace") -> str:
        """
        Creates a unique workspace directory using a timestamp.
        Returns the absolute path to the new workspace.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        workspace_path = os.path.join(base_dir, f"run_{timestamp}")
        
        # Ensure base directory exists
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        os.makedirs(workspace_path, exist_ok=True)
        return os.path.abspath(workspace_path)

    @staticmethod
    def on_rm_error(func, path, exc_info):
        """
        Error handler for shutil.rmtree to handle Windows read-only files.
        If the error is due to access denied, it attempts to change the file permission and retry.
        """
        # Check if the file is read-only
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWRITE)
            try:
                func(path)
            except Exception:
                # If it still fails, wait a tiny bit and try one more time
                time.sleep(0.1)
                try:
                    func(path)
                except Exception:
                    pass # Best effort
        else:
            # If it's not a permission issue, maybe it's a lock. Wait and retry.
            time.sleep(0.1)
            try:
                func(path)
            except Exception:
                pass


    @staticmethod
    def safe_delete_folder(folder_path: str):
        """
        Safely deletes a folder and its contents, handling Windows permission issues.
        """
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path, onerror=FileUtils.on_rm_error)
            except Exception as e:
                print(f"Error deleting folder {folder_path}: {e}")

def read_file_content(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def write_file_content(file_path: str, content: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
