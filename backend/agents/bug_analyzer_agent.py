from backend.agents.llm_client import HealingAgentLLM
import json
import re

class BugAnalyzerAgent:
    def __init__(self):
        self.llm = HealingAgentLLM()
        
    def analyze_logs(self, logs: str) -> dict:
        """
        Analyzes logs to find the first error.
        Returns:
            {
                "file": "path/to/file.py",
                "line": 10,
                "type": "LINTING | SYNTAX | LOGIC | TYPE_ERROR | IMPORT | INDENTATION",
                "description": "..."
            }
        """
        prompt = f"""
            You are an expert debugger. 
            Analyze the following test/runtime logs and identify the FIRST failure location.
            
            Logs:
            {logs[-8000:]}
            
            Task:
            Return a valid JSON object with:
            - "file": The file path where the error occurred (e.g., src/utils.py). Look for stack traces like "at ... (file:line:col)". If multiple files in stack, choose the one in the user's project (not node_modules).
            - "line": The line number (integer).
            - "type": One of [LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION, RUNTIME]
            - "description": A brief explanation of the bug.
            
            CRITICAL: Return ONLY the raw JSON string. Do not hallucinate files. 
            - If the error is "Missing script: test" or "no test specified", return "file": "package.json", "line": 0, "type": "CONFIG".
            - If absolutely no file is found in the logs, return "file": "main.py" (or index.js) as a best guess for project entry.
        """
        
        messages = [
            {"role": "system", "content": "You are a debugger. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm._chat_completion(messages)
            
            # Clean up response
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            
            # Additional cleanup for Llama 3 chatter
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
                
            return json.loads(content)
        except Exception as e:
            # Fallback
            return {"file": "unknown", "line": 0, "type": "LOGIC", "description": f"Analysis failed: {str(e)}"}
