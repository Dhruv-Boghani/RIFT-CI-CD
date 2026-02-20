from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
import os
import json
from backend.config import Config
from backend.config import Config
from backend.utils.file_utils import FileUtils
from backend.utils import read_file_content, write_file_content
from backend.services.git_service import GitService
from backend.services.repo_scanner import RepoScanner
from backend.agents import error_analyzer, fix_generator, git_manager

# --- States ---
class AnalysisState(TypedDict):
    repo_url: str
    username: str
    token: str
    workspace: str
    repo_path: str
    scan_results: List[Dict] # From RepoScanner
    analysis_report: List[Dict] # From ErrorAnalyzer
    logs: List[str]

class HealingState(TypedDict):
    workspace: str
    repo_path: str
    branch_name: str
    token: str # Needed for push
    error_to_fix: Dict # The specific error we are fixing
    fix_status: str # "success", "failed"
    logs: List[str]

# --- Nodes for Analysis ---

def secure_clone_node(state: AnalysisState):
    # 1. Create Workspace
    if not state.get("workspace"):
        state["workspace"] = FileUtils.create_workspace()
    
    # 2. Secure Clone
    res = GitService.secure_clone_repo(
        state["repo_url"], 
        state["username"], 
        state["token"], 
        state["workspace"]
    )
    
    if res["status"] == "error":
        state["logs"].append(f"Clone failed: {res['message']}")
        return {"logs": state["logs"]} # End here? usage of interrupt would be better but simplified
        
    state["repo_path"] = res["repo_path"]
    state["logs"].append(f"Cloned securely to {state['repo_path']}")
    return state

def scan_node(state: AnalysisState):
    if not state.get("repo_path"):
        return state
        
    state["logs"].append("Scanning repository...")
    files = RepoScanner.scan_repository(state["repo_path"])
    state["scan_results"] = files
    state["logs"].append(f"Scanned {len(files)} python files.")
    return state

def analyze_node(state: AnalysisState):
    report = []
    # Identify files that passed scanning but might have issues, or just strictly files with syntax errors first?
    # The prompt says: "Detect: Syntax, Lint... Send to LLM".
    # We will send ALL files found by scanner to LLM to be thorough, 
    # OR just the ones with syntax errors if we want to be fast.
    # Let's send ALL for now, but limit to small number if many?
    # For safety, let's limit to top 20 files to avoid hitting limits in this demo.
    
    files_to_analyze = state["scan_results"][:20] 
    
    for file_info in files_to_analyze:
        # If syntax error, explicitly mark it
        if file_info.get("has_syntax_error"):
             analysis = {
                 "file": file_info["file"],
                 "line": 0, # We might parse from error_detail
                 "type": "SYNTAX",
                 "description": file_info["error_detail"],
                 "suggested_fix": "Fix syntax error"
             }
             report.append(analysis)
             continue

        # Else, ask LLM
        analysis = error_analyzer.analyze_code_file(file_info)
        if analysis and isinstance(analysis, dict):
            # Ensure keys exist
            if "type" in analysis:
                report.append(analysis)
    
    state["analysis_report"] = report
    state["logs"].append(f"Analysis complete. Found {len(report)} issues.")
    
    # Save results.json
    results = {
        "timestamp": "now", # Placeholder
        "total_files": len(state["scan_results"]),
        "total_errors": len(report),
        "errors": report
    }
    
    # We save this in the workspace usually, or a global results path?
    # The requirement says "Create results.json".
    # We can save it in the workspace root.
    results_path = os.path.join(state["workspace"], "results.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
        
    return state

# --- Nodes for Healing ---

def apply_fix_node(state: HealingState):
    error = state["error_to_fix"]
    file_path = os.path.join(state["repo_path"], error["file"])
    
    state["logs"].append(f"Attempting to fix {error['file']}...")
    
    if os.path.exists(file_path):
        content = read_file_content(file_path)
        fixed_content = fix_generator.generate_fix(content, error)
        
        if fixed_content != content:
            write_file_content(file_path, fixed_content)
            state["fix_status"] = "applied"
            state["logs"].append("Fix applied to file system.")
        else:
            state["fix_status"] = "failed"
            state["logs"].append("LLM returned same content.")
    else:
        state["fix_status"] = "failed"
        state["logs"].append("File not found.")
        
    return state

def commit_push_node(state: HealingState):
    if state["fix_status"] != "applied":
        return state
        
    msg = f"[AI-AGENT] Fix {state['error_to_fix'].get('type')} in {state['error_to_fix'].get('file')}"
    
    # Basic git add/commit/push via GitService or simple git commands
    # We need a git manager for this.
    # Reuse git_manager.commit_and_push?
    # But we need to use the token!
    # The repo was cloned with the token, so `git push` might verify it, 
    # BUT we stripped the token from remote in step 2 (Requirement: "Remove token from remote after cloning").
    # Wait, if we remove token, we can't push.
    # "3. Remove token from remote after cloning."
    # "Apply fix... 3. Push to AI branch."
    # If token is removed, we must RE-INJECT it for push, or configure credential helper.
    # Securest way: Inject token into URL just for the push command.
    
    res = git_manager.commit_and_push(state["repo_path"], msg, state["branch_name"], state.get("token"))
    state["logs"].append(f"Git operation: {res.get('status')}")
    
    if res.get("status") == "success":
        state["fix_status"] = "success"
    else:
        state["fix_status"] = "failed_push"
        
    return state

# --- Workflows ---

# Analysis Workflow
analysis_workflow = StateGraph(AnalysisState)
analysis_workflow.add_node("secure_clone", secure_clone_node)
analysis_workflow.add_node("scan", scan_node)
analysis_workflow.add_node("analyze", analyze_node)

analysis_workflow.set_entry_point("secure_clone")
analysis_workflow.add_edge("secure_clone", "scan")
analysis_workflow.add_edge("scan", "analyze")
analysis_workflow.add_edge("analyze", END)

analysis_app = analysis_workflow.compile()

# Healing Workflow
healing_workflow = StateGraph(HealingState)
healing_workflow.add_node("apply_fix", apply_fix_node)
healing_workflow.add_node("commit_push", commit_push_node)

healing_workflow.set_entry_point("apply_fix")
healing_workflow.add_edge("apply_fix", "commit_push")
healing_workflow.add_edge("commit_push", END)

healing_app = healing_workflow.compile()
