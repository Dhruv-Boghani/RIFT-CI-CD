import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure backend module is found
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.langgraph_flow import analyze_project_node, fix_node
from backend.agents.bug_analyzer_agent import BugAnalyzerAgent

class TestFileDetection(unittest.TestCase):
    def setUp(self):
        self.test_repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_repo"))
        os.makedirs(self.test_repo_path, exist_ok=True)
        
        # Create dummy file
        self.dummy_file = os.path.join(self.test_repo_path, "src", "real_utils.py")
        os.makedirs(os.path.dirname(self.dummy_file), exist_ok=True)
        with open(self.dummy_file, "w") as f:
            f.write("def foo(): pass")
            
    def tearDown(self):
        import shutil
        if os.path.exists(self.test_repo_path):
            shutil.rmtree(self.test_repo_path)

    def test_analyze_project_populates_file_list(self):
        state = {
            "repo_path": self.test_repo_path, 
            "logs": [],
            "file_list": []
        }
        
        # Mock LLM to avoid API calls
        with patch('backend.agents.llm_client.HealingAgentLLM') as MockLLM:
             MockLLM.return_value.get_relevant_files.return_value = []
             MockLLM.return_value.analyze_project_structure.return_value = "explanation"
             
             new_state = analyze_project_node(state)
             
             file_list = new_state.get("file_list", [])
             print(f"File List: {file_list}")
             
             # Check if file is in list (normalize paths)
             normalized_list = [f.replace("\\", "/") for f in file_list]
             self.assertIn("src/real_utils.py", normalized_list)

    def test_fix_node_fuzzy_search(self):
        state = {
            "repo_path": self.test_repo_path,
            "file_list": ["src/utils.py"], 
            "current_error": {"file": "utils.py"}, # Missing src/ prefix, should be found by fuzzy search
            "logs": [],
            "iteration": 0
        }
        
        # Mock FixGenerator to avoid API calls and file writes
        with patch('backend.agents.fix_generator_agent.FixGeneratorAgent') as MockFix:
            MockFix.return_value.generate_fix.return_value = ("fixed_content", "desc")
            MockFix.return_value.apply_fix_to_repo.return_value = None
            
            # Using read_file_content mock
            with patch('backend.langgraph_flow.read_file_content', return_value="content"):
                 new_state = fix_node(state)
                 
                 # Check logs for fuzzy match
                 logs = "\n".join(new_state["logs"])
                 print(f"Logs: {logs}")
                 self.assertIn("Fuzzy match found", logs)
                 self.assertIn("src/utils.py", logs)
    
    def test_bug_analyzer_prompt_includes_files(self):
        agent = BugAnalyzerAgent()
        file_list = ["main.py", "utils.py"]
        
        # Mock LLM chat completion to inspect prompt
        with patch.object(agent.llm, '_chat_completion', return_value='{}') as mock_chat:
            agent.analyze_logs("error logs", file_list)
            
            # Get the prompt sent to LLM
            call_args = mock_chat.call_args
            messages = call_args[0][0]
            user_content = messages[1]["content"]
            
            print(f"Prompt snippet: {user_content[:200]}...")
            self.assertIn("Valid Files in Repo: main.py, utils.py", user_content)

if __name__ == '__main__':
    unittest.main()
