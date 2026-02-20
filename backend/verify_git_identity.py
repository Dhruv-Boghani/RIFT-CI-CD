import unittest
import os
import shutil
import tempfile
from git import Repo
import sys

# Ensure backend module is found
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.github_service import GithubService

class TestGitIdentity(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for the test repo
        self.test_dir = tempfile.mkdtemp()
        self.repo = Repo.init(self.test_dir)
        
        # Create a dummy file
        self.file_path = os.path.join(self.test_dir, "test.txt")
        with open(self.file_path, "w") as f:
            f.write("test content")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except:
                pass

    def test_commit_with_config(self):
        # Attempt to commit using the service
        # This should fail if config is not set, or pass if our fix works
        # Note: We need to mock push or expect it to fail since we have no remote
        
        try:
            # We trap the push error, but check if commit succeeded
            GithubService.commit_and_push(
                self.test_dir, 
                "test commit", 
                "main", 
                "dummy_token"
            )
        except Exception as e:
            # Push will likely fail due to no remote/token, but we care if COMMIT happened
            print(f"Service returned: {e}")

        # Check if commit exists and has correct author
        try:
            commit = self.repo.head.commit
            print(f"Commit Author: {commit.author.name} <{commit.author.email}>")
            
            self.assertEqual(commit.author.name, "Dhruv")
            self.assertEqual(commit.author.email, "dhruvboghani624@gmail.com")
            self.assertEqual(commit.message.strip(), "test commit")
            
        except ValueError:
            self.fail("Commit was not created!")

if __name__ == '__main__':
    unittest.main()
