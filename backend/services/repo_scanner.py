import os
import ast
from typing import List, Dict

class RepoScanner:
    @staticmethod
    def scan_repository(repo_path: str) -> List[Dict]:
        """
        Recursively scans the repository for Python files.
        Checks for syntax errors using ast.parse.
        Returns a list of file info objects.
        """
        results = []
        
        for root, _, files in os.walk(repo_path):
            if ".git" in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_path)
                    
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        # Check Syntax
                        try:
                            ast.parse(content)
                            is_syntax_error = False
                            error_detail = None
                        except SyntaxError as e:
                            is_syntax_error = True
                            error_detail = f"SyntaxError: {e.msg} at line {e.lineno}"
                            
                        results.append({
                            "file": rel_path,
                            "full_path": full_path,
                            "has_syntax_error": is_syntax_error,
                            "error_detail": error_detail,
                            "content": content
                        })
                        
                    except Exception as e:
                        print(f"Error scanning file {rel_path}: {e}")
                        
        return results
