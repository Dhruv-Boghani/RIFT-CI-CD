import re
import json
import os
from typing import List, Dict

def generate_branch_name(team_name: str, leader_name: str) -> str:
    """
    Generates branch name in format: TEAM_NAME_LEADER_NAME_AI_Fix
    Rules: All uppercase, spaces to underscores, no special chars
    """
    def clean(s):
        return re.sub(r'[^A-Z0-9]', '', s.upper().replace(' ', '_')) # Remove non-alphanumeric after upper/underscore
    
    # Better cleaning:
    # 1. Upper case
    # 2. Replace spaces with underscores
    # 3. Remove any non-alphanumeric except underscores
    t_clean = re.sub(r'[^A-Z0-9_]', '', team_name.upper().replace(' ', '_'))
    l_clean = re.sub(r'[^A-Z0-9_]', '', leader_name.upper().replace(' ', '_'))
    
    return f"{t_clean}_{l_clean}_AI_Fix"

def save_results(results: Dict):
    from backend.config import Config
    with open(Config.RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

def read_file_content(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def write_file_content(file_path: str, content: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
