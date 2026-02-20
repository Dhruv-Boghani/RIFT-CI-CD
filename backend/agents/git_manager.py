import git
import os

def commit_and_push(repo_path: str, message: str, branch_name: str, token: str = None):
    try:
        repo = git.Repo(repo_path)
        
        # Configure user if not set
        try:
            repo.config_reader().get_value("user", "email")
        except:
             repo.config_writer().set_value("user", "name", "AI Agent").release()
             repo.config_writer().set_value("user", "email", "ai-agent@example.com").release()

        # Add all changes
        repo.git.add('.')
        
        # Commit
        try:
            repo.git.commit('-m', message)
        except git.exc.GitCommandError as e:
            if "nothing to commit" in str(e):
                 return {"status": "success", "message": "Nothing to commit"}
            raise e
            
        # Push
        if token:
            # We need to construct the remote URL with token
            origin = repo.remotes.origin
            original_url = origin.url
            
            # If original URL already has token, great. If not, inject.
            # Assuming original_url is https://github.com/user/repo.git or similar
            if "@" not in original_url and "https://" in original_url:
                 clean_url = original_url.replace("https://", "")
                 auth_url = f"https://{token}@{clean_url}"
                 # We don't want to change the remote config permanently to avoid leaking token on disk?
                 # git push https://token@github.com/user/repo.git HEAD:branch
                 repo.git.push(auth_url, f"HEAD:{branch_name}")
            else:
                 # Just try pushing
                 repo.git.push('origin', branch_name)
        else:
             # Try pushing without token (ssh or existing creds)
             repo.git.push('origin', branch_name)
            
        return {"status": "success"}
    except Exception as e:
        # Mask token
        msg = str(e)
        if token:
             msg = msg.replace(token, "***TOKEN***")
        return {"status": "error", "message": msg}
