import git
import requests
import re
import os
import tempfile
import stat
from git import GitCommandError
from backend.utils.file_utils import FileUtils

class GithubService:
    @staticmethod
    def _create_ssh_key_file(private_key: str) -> str:
        """
        Writes private key to a temporary file with secure permissions (0600).
        Returns the path to the key file.
        """
        # Create a temporary file
        fd, path = tempfile.mkstemp()
        
        # Write key
        with os.fdopen(fd, 'w') as f:
            f.write(private_key)
            if not private_key.endswith('\n'):
                f.write('\n')
        
        # chmod 600 is critical for SSH
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        
        return path

    @staticmethod
    def secure_clone_repo(repo_url: str, username: str, token: str, workspace_path: str, auth_mode: str = "https", private_key: str = None) -> dict:
        """
        Clones a repository securely using either HTTPS or SSH.
        """
        ssh_key_path = None
        try:
            auth_url = repo_url
            env = os.environ.copy()

            if auth_mode == "https":
                if not repo_url.startswith("https://"):
                     return {"status": "error", "message": "Repository URL must start with https:// for HTTPS mode"}
                
                clean_url = repo_url.replace("https://", "")
                if username and token:
                    auth_url = f"https://{username}:{token}@{clean_url}"
                elif token:
                     auth_url = f"https://{token}@{clean_url}"
                else:
                     auth_url = repo_url
                     
            elif auth_mode == "ssh":
                # Expecting git@github.com:user/repo.git
                if not private_key:
                    return {"status": "error", "message": "Private Key required for SSH mode"}
                
                ssh_key_path = GithubService._create_ssh_key_file(private_key)
                
                # Configure GIT_SSH_COMMAND
                # -o options to avoid known_hosts prompt issues in automation
                ssh_cmd = f"ssh -i {ssh_key_path} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
                env["GIT_SSH_COMMAND"] = ssh_cmd

            repo_name = repo_url.split("/")[-1].replace(".git", "")
            clone_path = os.path.join(workspace_path, repo_name)
            
            FileUtils.safe_delete_folder(clone_path)
            
            try:
                # Pass env for SSH and enable longpaths
                git.Repo.clone_from(auth_url, clone_path, env=env, config='core.longpaths=true', allow_unsafe_options=True)
            except GitCommandError as e:
                error_msg = str(e)
                if token:
                    error_msg = error_msg.replace(token, "***TOKEN***")
                return {"status": "error", "message": f"Git Error: {error_msg}"}
            except Exception as e:
                 return {"status": "error", "message": f"Unexpected error: {str(e)}"}

            return {
                "status": "success",
                "message": "Repository cloned successfully",
                "repo_path": clone_path,
                "workspace": workspace_path
            }

        except Exception as e:
             return {"status": "error", "message": f"System error: {str(e)}"}
        finally:
            # Cleanup SSH key
            if ssh_key_path and os.path.exists(ssh_key_path):
                try:
                    os.unlink(ssh_key_path)
                except:
                    pass

    @staticmethod
    def create_fix_branch(repo_path: str, team_name: str, leader_name: str) -> str:
        """
        Creates a new branch with strict format: TEAMNAME_LEADERNAME_AI_Fix
        """
        def clean(s):
            return re.sub(r'[^A-Z0-9_]', '', s.upper().replace(' ', '_'))
            
        t_clean = clean(team_name)
        l_clean = clean(leader_name)
        
        branch_name = f"{t_clean}_{l_clean}_AI_Fix"
        
        repo = git.Repo(repo_path)
        try:
            current = repo.active_branch
            if branch_name in repo.heads:
                repo.heads[branch_name].checkout()
            else:
                repo.create_head(branch_name).checkout()
                
            return branch_name
        except Exception as e:
            print(f"Branch error: {e}")
            return branch_name

    @staticmethod
    def commit_and_push(repo_path: str, message: str, branch_name: str, token: str, auth_mode: str = "https", private_key: str = None) -> dict:
        ssh_key_path = None
        try:
            repo = git.Repo(repo_path)
            env = os.environ.copy()
            
            # Configure user
            with repo.config_writer() as cw:
                cw.set_value("user", "name", "AI Agent")
                cw.set_value("user", "email", "ai-agent@hackathon.com")

            if message:
                repo.git.add('.')
                try:
                    repo.git.commit('-m', message)
                except git.exc.GitCommandError as e:
                    if "nothing to commit" in str(e):
                        pass 
                    else:
                        raise e
            
            # Prepare Push
            if auth_mode == "https":
                origin = repo.remotes.origin
                url = origin.url
                if "https://" in url and "@" not in url:
                    clean = url.replace("https://", "")
                    auth_url = f"https://{token}@{clean}"
                    repo.git.push(auth_url, f"HEAD:{branch_name}")
                else:
                    repo.git.push('origin', f"HEAD:{branch_name}")
                    
            elif auth_mode == "ssh":
                if not private_key:
                     return {"status": "error", "message": "Private Key required for SSH push"}
                
                ssh_key_path = GithubService._create_ssh_key_file(private_key)
                ssh_cmd = f"ssh -i {ssh_key_path} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
                
                # We need to ensure remote URL is SSH format if it wasn't already?
                # If we cloned via SSH, origin URL should be SSH.
                # Just use `repo.git.push` with the custom SSH command ENV.
                
                with repo.git.custom_environment(GIT_SSH_COMMAND=ssh_cmd):
                    repo.git.push('origin', f"HEAD:{branch_name}")
                
            return {"status": "success"}
            
        except Exception as e:
            msg = str(e)
            if token:
                msg = msg.replace(token, "***TOKEN***")
            return {"status": "error", "message": msg}
        finally:
            if ssh_key_path and os.path.exists(ssh_key_path):
                try:
                    os.unlink(ssh_key_path)
                except:
                    pass

    @staticmethod
    def create_pr(repo_url: str, branch_name: str, token: str, title: str, body: str) -> dict:
        """
        Creates a Pull Request using GitHub API.
        NOTE: Even with SSH for git ops, we still need a Token for API calls (PR creation).
        If auth_mode is SSH, we might not have a token.
        But requirement said: "SSH Mode ... Optional: Public Key".
        Wait, PR creation via SSH key is NOT possible with standard GitHub API (REST).
        GitHub CLI (gh) can do it, but we use REST.
        REST API requires a Token (PAT or OAuth).
        
        The prompt says:
        "If SSH selected... Show inputs: SSH Clone Command, Private SSH Key..."
        Does NOT explicitly ask for Token in SSH mode.
        
        However, "Create PR" step #11 implies we need it.
        If user provides ONLY SSH Key, we CANNOT create PR via API.
        We can push the branch, but creating PR requires API token.
        
        If token is missing, we should skip PR creation or warn user.
        Let's assume users using SSH might accept manual PR creation, 
        OR we ask for token anyway?
        
        Prompt: "If HTTPS selected: Show input: Token... If SSH selected: Show inputs: SSH Command, Private Key..."
        It seems Token is NOT provided in SSH mode.
        
        Resolution:
        If token is empty/None in `create_pr`, return warning "PR Creation requires GitHub Token (not provided in SSH mode)".
        The agent will still push the branch, which is the hard part.
        """
        if not token:
             return {"status": "skipped", "message": "PR creation skipped (No GitHub Token provided)"}
             
        try:
            # Logic remains same, needs Token
            clean_url = repo_url.replace("https://github.com/", "").replace(".git", "")
            # If SSH URL: git@github.com:user/repo.git
            if repo_url.startswith("git@"):
                clean_url = repo_url.replace("git@github.com:", "").replace(".git", "")
            
            owner, repo = clean_url.split("/")
            
            api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            data = {
                "title": title,
                "body": body,
                "head": branch_name,
                "base": "main" 
            }
            
            resp = requests.post(api_url, headers=headers, json=data)
            
            if resp.status_code == 201:
                return {"status": "success", "url": resp.json().get("html_url")}
            elif resp.status_code == 422:
                return {"status": "warning", "message": "PR might already exist"}
            else:
                return {"status": "error", "message": f"GitHub API {resp.status_code}: {resp.text}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
