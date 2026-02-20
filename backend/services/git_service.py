import git
import requests
from git import GitCommandError
from backend.utils.file_utils import FileUtils

class GitService:
    @staticmethod
    def secure_clone_repo(repo_url: str, username: str, token: str, workspace_path: str) -> dict:
        """
        Clones a repository securely using an injected token.
        
        Args:
            repo_url: The URL of the repository (e.g., https://github.com/user/repo)
            username: GitHub username
            token: GitHub Fine-Grained Access Token
            workspace_path: The directory where the repo should be cloned
            
        Returns:
            dict: Status and details of the operation
        """
        try:
            # 1. Construct Secure URL
            # Ensure URL starts with https://
            if not repo_url.startswith("https://"):
                 return {
                    "status": "error",
                    "message": "Repository URL must start with https://"
                }
            
            # Strip https:// for token injection
            clean_url = repo_url.replace("https://", "")
            
            # Format: https://startToken:endToken@github.com/user/repo
            # We use the token as the username for PATs usually, or username:token
            if username and token:
                auth_url = f"https://{username}:{token}@{clean_url}"
            elif token:
                 auth_url = f"https://{token}@{clean_url}" # Sometimes token is used as user
            else:
                 auth_url = repo_url # Public repo
            
            # 2. Define Clone Path
            repo_name = clean_url.split("/")[-1].replace(".git", "")
            clone_path = os.path.join(workspace_path, repo_name)
            
            # 3. Clean up if exists (just in case, though workspace should be unique)
            FileUtils.safe_delete_folder(clone_path)
            
            # 4. Clone
            try:
                git.Repo.clone_from(auth_url, clone_path)
            except GitCommandError as e:
                # Mask token in error message
                error_msg = str(e).replace(token, "***TOKEN***")
                
                if "403" in error_msg:
                    return {
                        "status": "error",
                        "message": "Access Denied (403). Check your token permissions.",
                        "suggestion": "Ensure your token has 'Contents' Read/Write and 'Metadata' Read permissions."
                    }
                elif "401" in error_msg:
                    return {
                        "status": "error",
                        "message": "Authentication Failed (401). Check your token.",
                        "suggestion": "Verify your GitHub username and Personal Access Token."
                    }
                elif "404" in error_msg:
                     return {
                        "status": "error",
                        "message": "Repository not found (404).",
                        "suggestion": "Check the repository URL."
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Git Error: {error_msg}"
                    }
            except Exception as e:
                 return {
                    "status": "error",
                    "message": f"Unexpected error during clone: {str(e)}"
                }

            # 5. Validate Access (Optional: Check if we can write?)
            # For now, just confirming existence is enough for clone.
            # Writing would be tested when we try to push a branch.
            
            return {
                "status": "success",
                "message": "Repository cloned successfully",
                "repo_path": clone_path,
                "workspace": workspace_path
            }

        except Exception as e:
             return {
                "status": "error",
                "message": f"System error: {str(e)}"
            }

    @staticmethod
    def validate_repo_access(repo_path: str) -> bool:
        """
        Validates if the repo at path is a valid git repo.
        """
        try:
            _ = git.Repo(repo_path)
            return True
        except:
            return False

    @staticmethod
    def validate_token_permissions(token: str, username: str, repo_url: str) -> dict:
        """
        Validates the GitHub token against the repository to check for push permissions.
        """
        try:
            # Extract owner/repo
            clean_url = repo_url.replace("https://github.com/", "").replace(".git", "")
            parts = clean_url.split("/")
            if len(parts) < 2:
                return {"status": "error", "message": "Invalid repository URL format."}
            
            owner, repo = parts[0], parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                permissions = data.get("permissions", {})
                
                if permissions.get("push", False):
                    return {"status": "success", "message": "Token valid with write access."}
                else:
                    return {
                        "status": "error", 
                        "message": "Token lacks WRITE permissions.",
                        "suggestion": "Ensure 'Contents' permission is set to Read and Write."
                    }
            elif response.status_code == 404:
                return {"status": "error", "message": "Repository not found or token invalid."}
            elif response.status_code == 401:
                return {"status": "error", "message": "Invalid credentials (401)."}
            else:
                return {"status": "error", "message": f"GitHub API Error: {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "message": f"Validation Error: {str(e)}"}
