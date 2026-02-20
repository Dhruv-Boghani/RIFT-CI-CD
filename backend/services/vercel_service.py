import requests
from typing import Optional, Dict, List

class VercelService:
    BASE_URL = "https://api.vercel.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token

    def get_latest_deployment(self, repo_url: str, token: str) -> Dict[str, str]:
        """
        Finds the latest deployment for a given GitHub repository.
        Requires Vercel Token.
        """
        if not token:
             return {"status": "error", "message": "Vercel Token required"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # extracting repo name from url
        # e.g., https://github.com/user/repo -> user/repo
        clean_url = repo_url.replace("https://github.com/", "").replace(".git", "")
        if "git@github.com:" in repo_url:
             clean_url = repo_url.replace("git@github.com:", "").replace(".git", "")
        
        # We search deployments. 
        # Vercel API doesn't have a direct "search by git repo" filter easily accessible across all projects 
        # without iterating, BUT we can try filtering by `repo` if we know the project?
        # Actually, `GET /v6/deployments` accepts `repo` parameter (e.g., `user/repo`)?
        # Documentation says: `repo` query param: "The name of the repository to filter deployments by." (e.g. `vercel/vercel`)
        
        params = {
            "repo": clean_url,
            "limit": 1,
            "state": "READY,ERROR,BUILDING,CANCELED" # We want to see even if it failed
        }

        try:
            response = requests.get(f"{self.BASE_URL}/v6/deployments", headers=headers, params=params)
             
            if response.status_code != 200:
                return {"status": "error", "message": f"Vercel API Error: {response.text}"}
            
            deployments = response.json().get("deployments", [])
            
            if not deployments:
                return {"status": "not_found", "message": "No Vercel deployment found for this repository."}
            
            latest = deployments[0]
            
            return {
                "status": "success",
                "deployment_id": latest["uid"],
                "project_name": latest["name"],
                "url": f"https://{latest['url']}",
                "state": latest["state"],
                "created": latest["created"]
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_build_logs(self, deployment_id: str, token: str) -> Dict[str, any]:
        """
        Fetches build logs (events) for a deployment.
        """
        if not token:
             return {"status": "error", "message": "Vercel Token required"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            # /v3/deployments/{idOrUrl}/events
            response = requests.get(f"{self.BASE_URL}/v3/deployments/{deployment_id}/events", headers=headers)
            
            if response.status_code != 200:
                 return {"status": "error", "message": f"Failed to fetch logs: {response.text}"}
            
            # The events endpoint returns a stream of JSON objects if not standard, 
            # but usually requests.get handles it if it closes. 
            # Actually, it might be a stream.
            # However, for a finished deployment, it returns all events.
            # The format is a list of objects.
            
            events = response.json() 
            
            # Parsing logs
            logs = []
            for event in events:
                text = event.get("text", "")
                if text:
                    logs.append(text)
            
            return {"status": "success", "logs": logs}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
