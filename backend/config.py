import os
from dotenv import load_dotenv

# Load relative to file, not CWD
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
    MAX_RETRIES = 5
    WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")
    RESULTS_FILE = "results.json"
    
    # Allow local run (subprocess) if Docker is unavailable. 
    # CRITICAL: Set to "true" on platforms like Render Free Tier.
    AI_AGENT_ALLOW_LOCAL_RUN = os.getenv("AI_AGENT_ALLOW_LOCAL_RUN", "false").lower() == "true"

    # Ensure workspace exists
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
