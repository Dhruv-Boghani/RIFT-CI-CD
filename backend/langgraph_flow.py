from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
import os
import shutil
import subprocess
from backend.config import Config
from backend.utils.file_utils import FileUtils, read_file_content
from backend.github_service import GithubService
from backend.agents.test_runner_agent import TestRunnerAgent
from backend.agents.bug_analyzer_agent import BugAnalyzerAgent
from backend.agents.fix_generator_agent import FixGeneratorAgent
from backend.agents.llm_client import HealingAgentLLM  # Your upgraded HuggingFace API client
from backend.agents.docker_runner import DockerTestRunner # Your Docker builder

# --- State Definition (Merged) ---
class AgentState(TypedDict):
    repo_url: str
    team_name: str
    leader_name: str
    token: str 
    auth_mode: str 
    private_key: str 
    workspace: str
    repo_path: str
    branch_name: str
    iteration: int
    max_iterations: int
    test_status: str 
    logs: List[str] 
    fixes_applied: List[Dict] 
    current_error: Dict 
    language_detected: str 
    # Docker Specific Fields
    docker_exists: bool
    docker_retry_count: int
    docker_build_logs: str
    docker_image_tag: str

# Agents
github_service = GithubService()
test_runner = TestRunnerAgent()
bug_analyzer = BugAnalyzerAgent()
fix_generator = FixGeneratorAgent()

# --- Nodes ---

def clone_node(state: AgentState):
    state["logs"].append("--- Cloning Repository ---")
    workspace = FileUtils.create_workspace()
    state["workspace"] = workspace
    
    res = github_service.secure_clone_repo(
        state["repo_url"], 
        "", 
        state.get("token"), 
        workspace,
        auth_mode=state.get("auth_mode", "https"),
        private_key=state.get("private_key")
    )
    
    if res["status"] == "error":
        state["logs"].append(f"Clone Failed: {res['message']}")
        state["test_status"] = "ERROR"
        return state
        
    state["repo_path"] = res["repo_path"]
    state["logs"].append(f"Cloned repository to {state['repo_path']}")
    
    branch = github_service.create_fix_branch(state["repo_path"], state["team_name"], state["leader_name"])
    state["branch_name"] = branch
    state["logs"].append(f"Created branch: {branch}")
    
    # Initialize Docker fields
    state["docker_retry_count"] = 0
    state["docker_build_logs"] = ""
    state["docker_image_tag"] = "rift-sandbox:latest" # Default
    return state

# --- INJECTED DOCKER NODES ---

def analyze_project_node(state: AgentState):
    state["logs"].append("--- Analyzing Project Structure ---")
    repo_path = state["repo_path"]
    agent = HealingAgentLLM()
    
    # 1. Gather file structure (Ignore node_modules, etc)
    structure = ""
    ignored_dirs = {".git", "node_modules", "venv", "__pycache__", ".next", "dist", "build"}
    
    for root, dirs, files in os.walk(repo_path):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        
        level = root.replace(repo_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        structure += '{}{}/\n'.format(indent, os.path.basename(root))
        subindent = ' ' * 4 * (level + 1)
        
        # Limit files per folder to avoid huge trees
        if len(files) > 20: 
             structure += '{}({} files...)\n'.format(subindent, len(files))
        else:
            for f in files:
                structure += '{}{}\n'.format(subindent, f)
            
    # 2. Ask LLM which files are relevant
    state["logs"].append("Identifying critical files...")
    relevant_files = agent.get_relevant_files(structure)
    state["logs"].append(f"Selected files for analysis: {relevant_files}")
    
    # 3. Read content of those files
    file_content_map = {}
    for rel_path in relevant_files:
        full_path = os.path.join(repo_path, rel_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                # Limit size per file
                with open(full_path, "r", errors='ignore') as f:
                    file_content_map[rel_path] = f.read()[:3000] 
            except Exception:
                pass
            
    # Fallback if no files selected or found
    if not file_content_map:
        # Try common defaults
        for f in ["package.json", "requirements.txt", "pom.xml", "go.mod"]:
            p = os.path.join(repo_path, f)
            if os.path.exists(p):
                with open(p, "r") as fh:
                    file_content_map[f] = fh.read()[:2000]

    # 4. Generate Explain.txt
    explanation = agent.analyze_project_structure(file_content_map)
    
    explain_path = os.path.join(repo_path, "explain.txt")
    with open(explain_path, "w") as f:
        f.write(explanation)
        
    state["logs"].append("Project analysis saved to explain.txt")
    return state

def check_dockerfile_node(state: AgentState):
    state["logs"].append("--- Checking for Dockerfile ---")
    repo_path = state["repo_path"]
    dockerfile_path = os.path.join(repo_path, "Dockerfile")
    
    if os.path.exists(dockerfile_path):
        state["logs"].append("Dockerfile found.")
        return {"docker_exists": True}
    else:
        state["logs"].append("Dockerfile NOT found.")
        return {"docker_exists": False}

def generate_dockerfile_node(state: AgentState):
    state["logs"].append("--- Generating Dockerfile via HuggingFace API ---")
    repo_path = state["repo_path"]
    agent = HealingAgentLLM() 
    
    # Gather context
    structure = ""
    for root, dirs, files in os.walk(repo_path):
        level = root.replace(repo_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        structure += '{}{}/\n'.format(indent, os.path.basename(root))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            structure += '{}{}\n'.format(subindent, f)
            
    # Read project analysis context
    project_context = ""
    explain_path = os.path.join(repo_path, "explain.txt")
    if os.path.exists(explain_path):
        with open(explain_path, "r") as f:
            project_context = f.read()

    # Optimization: If explain.txt exists, use ONLY that to generate Dockerfile to save context.
    # The explain.txt was generated from smart analysis and should be sufficient.
    if project_context:
        state["logs"].append("Using explain.txt for Dockerfile generation (skipping raw files to save tokens).")
        structure = "" 
        sample_content = ""

    has_gpu = shutil.which('nvidia-smi') is not None
    
    dockerfile_content = agent.generate_dockerfile(structure, sample_content, project_context=project_context, has_gpu=has_gpu)
    
    with open(os.path.join(repo_path, "Dockerfile"), "w") as f:
        f.write(dockerfile_content)
        
    state["logs"].append("Dockerfile generated.")
    return {"docker_exists": True}

def validate_docker_node(state: AgentState):
    retry_count = state.get('docker_retry_count', 0)
    state["logs"].append(f"--- Validating Dockerfile (Retry {retry_count}) ---")
    repo_path = state["repo_path"]
    runner = DockerTestRunner(repo_path)
    
    tag = f"test-build-{state['team_name']}:latest".lower()
    result = runner.build_image(tag)
    
    if result["status"] == "success":
        state["logs"].append(f"Dockerfile validation SUCCESS. Image: {tag}")
        return {
            "docker_build_logs": "Image built successfully", 
            "docker_image_tag": tag
        }
    else:
        state["logs"].append(f"Dockerfile validation FAILED: {result['logs']}")
        return {
            "docker_build_logs": result["logs"],
            "docker_retry_count": retry_count
        }

def fix_dockerfile_node(state: AgentState):
    state["logs"].append("--- Fixing Dockerfile ---")
    repo_path = state["repo_path"]
    dockerfile_path = os.path.join(repo_path, "Dockerfile")
    build_logs = state.get("docker_build_logs", "")
    
    agent = HealingAgentLLM()
    
    if os.path.exists(dockerfile_path):
        with open(dockerfile_path, "r") as f:
            content = f.read()
            
        fixed_content = agent.fix_dockerfile(content, build_logs)
        
        with open(dockerfile_path, "w") as f:
            f.write(fixed_content)
            
        state["logs"].append("Dockerfile updated by AI.")
        
    return {"docker_retry_count": state.get("docker_retry_count", 0) + 1}

# --- END INJECTED DOCKER NODES ---

def test_node(state: AgentState):
    image_tag = state.get("docker_image_tag", "rift-sandbox:latest")
    repo_path = state.get("repo_path")
    
    state["logs"].append(f"Running Universal Tests (Iteration {state['iteration'] + 1}/{state['max_iterations']}) using {image_tag}...")
    
    # If we are using a custom built image, we likely want to mount the local code 
    # to test the changes we just made (including the Dockerfile itself if needed).
    # If using sandbox, we might still want to mount local code to test fixes?
    # Yes, always prefer local mounting if available to test applied fixes before commit.
    
    mount_path = repo_path if os.path.exists(repo_path) else None

    res = test_runner.run_tests(
        state["repo_url"], 
        state["branch_name"], 
        state.get("token"),
        auth_mode=state.get("auth_mode", "https"),
        private_key=state.get("private_key"),
        image_tag=image_tag,
        mount_path=mount_path
    )
    
    if "language" in res:
        state["language_detected"] = res["language"]
        state["logs"].append(f"Language Detected: {res['language']}")
    
    raw_status = res["status"].upper() # ensure uppercase
    if raw_status == "SUCCESS":
        state["test_status"] = "PASSED"
    elif raw_status == "FAILED":
        state["test_status"] = "FAILED"
    else:
        state["test_status"] = "ERROR" # Fallback
    
    state["logs"].append(f"Test Result: {state['test_status']}")
    
    if state["test_status"] in ["FAILED", "ERROR"]:
        if "errors" in res and res["errors"]:
            state["current_error"] = res["errors"][0]
            state["current_error"]["raw_logs"] = res.get("raw_logs", "")
        else:
            state["current_error"] = {"raw_logs": res.get("raw_logs", "")}
        
    return state

def analyze_node(state: AgentState):
    err = state.get("current_error", {})
    if err.get("type", "UNKNOWN") != "UNKNOWN" and err.get("file") and err.get("line"):
        state["logs"].append(f"Regex Detected {err.get('type')} error in {err.get('file')} line {err.get('line')}")
        return state

    state["logs"].append("Analyzing failure logs with LLM...")
    logs = err.get("raw_logs", "")

    # --- QUICK CHECK FOR MISSING SCRIPTS ---
    if "Missing script: \"test\"" in logs or "no test specified" in logs:
        state["logs"].append("⚠️ Detected missing test script. Targeting package.json.")
        analysis = {
            "file": "package.json",
            "line": 0,
            "type": "CONFIG",
            "description": "The 'test' script is missing or invalid in package.json. Please add a valid test script."
        }
        state["current_error"].update(analysis)
        return state

    analysis = bug_analyzer.analyze_logs(logs)
    
    # --- FALLBACK MECHANISM ---
    # If LLM returns unknown file, try to guess based on project structure
    if analysis.get("file") in [None, "unknown", ""] or not analysis.get("file"):
        repo_path = state["repo_path"]
        guessed_file = None
        
        # Check based on detected language
        lang = state.get("language_detected", "").lower()
        
        common_files = []
        if "node" in lang or os.path.exists(os.path.join(repo_path, "package.json")):
            common_files = ["index.js", "server.js", "app.js", "main.js", "src/index.js", "src/server.js"]
        elif "python" in lang or os.path.exists(os.path.join(repo_path, "requirements.txt")):
            common_files = ["main.py", "app.py", "run.py", "server.py", "manage.py"]
            
        for f in common_files:
            if os.path.exists(os.path.join(repo_path, f)):
                guessed_file = f
                break
                
        if guessed_file:
            analysis["file"] = guessed_file
            analysis["line"] = 1 # Start at top
            analysis["description"] += " (Auto-detected entry point due to missing file info in logs)"
            state["logs"].append(f"⚠️ verification fallback: targeting {guessed_file}")

    state["current_error"].update(analysis)
    state["logs"].append(f"LLM Detected {analysis.get('type')} error in {analysis.get('file')} line {analysis.get('line')}")
    return state

def fix_node(state: AgentState):
    err = state["current_error"]
    file_rel = err.get("file")
    
    if not file_rel:
        state["logs"].append("Could not identify file to fix.")
        state["iteration"] += 1
        return state

    full_path = os.path.join(state["repo_path"], file_rel)
    if not os.path.exists(full_path):
        state["logs"].append(f"File {file_rel} not found in workspace.")
        state["iteration"] += 1
        return state
         
    content = read_file_content(full_path)
    
    fixed_content, fix_desc = fix_generator.generate_fix(content, err) 
    
    if fixed_content == content:
        state["logs"].append("LLM could not generate a fix.")
    else:
        fix_generator.apply_fix_to_repo(state["repo_path"], file_rel, fixed_content)
        
        # User requested format: 
        # {Type} error in {file} line {line} -> Fix: {description}
        err_type = err.get("type", "General")
        line_num = err.get("line", 0)
        
        commit_msg = f"{err_type} error in {file_rel} line {line_num} -> Fix: {fix_desc}"
        
        fix_record = {
            "file": file_rel,
            "bug_type": err_type,
            "line_number": line_num,
            "commit_message": commit_msg,
            "status": "Applied" 
        }
        state["fixes_applied"].append(fix_record)
        state["logs"].append(f"Applied fix locally to {file_rel}")
        
    return state

def commit_node(state: AgentState):
    """Upgraded Commit Node using direct subprocess logic to guarantee token injection"""
    state["logs"].append("--- Committing and Pushing Fixes ---")
    
    if not state.get("fixes_applied"):
        state["iteration"] += 1
        return state
        
    last_fix = state["fixes_applied"][-1]
    
    # If fix wasn't actually applied (e.g. LLM failure), skip commit
    if last_fix.get("status") != "Applied":
        state["logs"].append("⚠️ Skipping commit: No fix was applied in the previous step.")
        state["iteration"] += 1
        return state
        
    msg = last_fix["commit_message"]
    repo_path = state["repo_path"]
    branch_name = state["branch_name"]
    repo_url = state["repo_url"]
    
    github_token = os.environ.get("GITHUB_TOKEN") or state.get("token")

    if github_token:
        # Secure URL injection
        auth_repo_url = repo_url.replace("https://", f"https://{github_token}@")
        try:
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", msg], cwd=repo_path, check=True, capture_output=True)
            # subprocess.run(["git", "push", "-u", auth_repo_url, branch_name], cwd=repo_path, check=True, capture_output=True)
            
            last_fix["status"] = "Fixed Locally" # Changed status
            state["logs"].append("✅ Committed changes locally.")
        except subprocess.CalledProcessError as e:
            last_fix["status"] = "Failed Commit"
            error_msg = e.stderr.decode() if e.stderr else str(e)
            state["logs"].append(f"❌ Git commit failed: {error_msg}")
    else:
        state["logs"].append("⚠️ Commit applied locally. No GITHUB_TOKEN provided.")
        last_fix["status"] = "Fixed Locally"
        
    state["iteration"] += 1
    return state

def pr_node(state: AgentState):
    state["logs"].append("Pushing changes and Creating Pull Request...")
    repo_path = state["repo_path"]
    branch_name = state["branch_name"]
    repo_url = state["repo_url"]
    github_token = os.environ.get("GITHUB_TOKEN") or state.get("token")
    
    # 1. PUSH CHANGES NOW
    if github_token:
        auth_repo_url = repo_url.replace("https://", f"https://{github_token}@")
        try:
            state["logs"].append("Pushing all local commits to remote...")
            subprocess.run(["git", "push", "-u", auth_repo_url, branch_name], cwd=repo_path, check=True, capture_output=True)
            state["logs"].append("✅ Push Successful.")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            state["logs"].append(f"❌ Final Push failed: {error_msg}")
            # Ensure we still try to PR if possible, or return?
            # If push fails, PR might fail or show old code. 
            pass

    # 2. CREATE PR
    title = f"AI Fixes for {state['team_name']}"
    body = f"Autonomous fixes generated by RIFT Agent.\n\nStats:\n- Language: {state.get('language_detected', 'Unknown')}\n- Iterations: {state['iteration']}\n- Fixes: {len(state['fixes_applied'])}"
    
    res = github_service.create_pr(state["repo_url"], state["branch_name"], state.get("token"), title, body)
    
    if res["status"] == "success":
        state["logs"].append(f"PR Created: {res['url']}")
    else:
        state["logs"].append(f"PR Creation Note: {res.get('message')}")
        
    return state

# --- Flow Logic & Graph Construction ---

def route_dockerfile(state: AgentState):
    if state.get("docker_exists"):
        return "validate_docker"
    else:
        return "generate_dockerfile"

def route_after_validation(state: AgentState):
    logs = state.get("docker_build_logs", "")
    retry_count = state.get("docker_retry_count", 0)
    
    if "Image built successfully" in logs:
        return "test"
    
    if retry_count >= 3:
        state["test_status"] = "ERROR"
        state["logs"].append("Docker build failed after 3 retries. Aborting.")
        return "create_pr" # Fails out to the PR node to log the attempt
    
    return "fix_dockerfile"

def check_retry(state: AgentState):
    if state["test_status"] == "PASSED": return "create_pr"
    # Treat ERROR same as FAILED for retry purposes
    if state["iteration"] >= state["max_iterations"]: return "create_pr"
    return "analyze"

workflow = StateGraph(AgentState)

# Add all nodes
workflow.add_node("clone", clone_node)
workflow.add_node("analyze_project", analyze_project_node)
workflow.add_node("check_dockerfile", check_dockerfile_node)
workflow.add_node("generate_dockerfile", generate_dockerfile_node)
workflow.add_node("validate_docker", validate_docker_node)
workflow.add_node("fix_dockerfile", fix_dockerfile_node)
workflow.add_node("test", test_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("fix", fix_node)
workflow.add_node("commit", commit_node)
workflow.add_node("create_pr", pr_node)

workflow.set_entry_point("clone")
workflow.add_edge("clone", "analyze_project")
workflow.add_edge("analyze_project", "check_dockerfile")

workflow.add_conditional_edges(
    "check_dockerfile",
    route_dockerfile,
    {
        "validate_docker": "validate_docker",
        "generate_dockerfile": "generate_dockerfile"
    }
)

workflow.add_edge("generate_dockerfile", "validate_docker")

workflow.add_conditional_edges(
    "validate_docker",
    route_after_validation,
    {
        "test": "test",
        "create_pr": "create_pr",
        "fix_dockerfile": "fix_dockerfile"
    }
)

workflow.add_edge("fix_dockerfile", "validate_docker")

workflow.add_conditional_edges(
    "test",
    check_retry,
    {
        "create_pr": "create_pr",
        "analyze": "analyze"
    }
)

workflow.add_edge("analyze", "fix")
workflow.add_edge("fix", "commit")
workflow.add_edge("commit", "test")
workflow.add_edge("create_pr", END)

app = workflow.compile()