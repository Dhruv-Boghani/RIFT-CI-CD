from huggingface_hub import InferenceClient
import json
import re
import os

class HealingAgentLLM:
    _instance = None
    _client = None
    _model_id = None
    
    # Fallback model if the primary one fails authentication/availability
    FALLBACK_MODEL = "HuggingFaceH4/zephyr-7b-beta"

    # Using a reliable model like Zephyr-7b by default for consistent code-generation
    # But Qwen or Mistral are good too if they work. Zephyr is very forgiving.
    # User requested Llama 3 8B
    # Using the NousResearch version (ungated) to avoid permission errors
    def __new__(cls, model_id: str = "Qwen/Qwen2.5-Coder-32B-Instruct"):
        """Singleton pattern for the API client."""
        if cls._instance is None:
            instance = super(HealingAgentLLM, cls).__new__(cls)
            try:
                instance._initialize_model(model_id)
                cls._instance = instance
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to initialize LLM: {e}")
                # Don't raise here if you want to allow retry?
                # But better to fail fast if config is wrong.
                raise e
        return cls._instance

    def _initialize_model(self, model_id: str):
        print(f"Connecting to Hugging Face API (InferenceClient) for model: {model_id}...")
        
        hf_token = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        
        if not hf_token or hf_token == "your_hf_token_here":
            error_msg = (
                "HUGGINGFACE_API_KEY is missing or invalid! "
                "Please set it in your .env file."
            )
            print(f"ERROR: {error_msg}")
            
        try:
            # Use InferenceClient directly which supports chat_completion
            self._client = InferenceClient(token=hf_token)
            self._model_id = model_id
            print(f"Successfully initialized Hugging Face Client for {model_id}.")
            
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            raise e

    def _chat_completion(self, messages, temperature=0.1, max_tokens=1024):
        """Helper to call call chat completion API"""
        try:
            response = self._client.chat_completion(
                model=self._model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                seed=42
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Call Failed: {e}")
            return f"Error generating response: {e}"

    def analyze_error(self, test_logs: str) -> dict:
        """
        Analyzes the test logs.
        """
        prompt = f"""
            You are an expert software debugger.
            Analyze the following test logs and traceback.
            Identify:
            1. The file causing the error (path).
            2. The line number (if available).
            3. The type of bug (SYNTAX, LOGIC, LINTING, RUNTIME).
            4. A brief description of the error.

            Test Logs:
            {test_logs[:10000]} 

            Return your response in strictly VALID JSON format like this:
            {{
                "file": "path/to/file.py",
                "line": 10,
                "type": "LOGIC",
                "description": "IndexError due to off-by-one loop."
            }}
            Do not include any explanation outside the JSON.
        """
        
        messages = [
            {"role": "system", "content": "You are a helpful AI debugger that outputs JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._chat_completion(messages)
        
        try:
            # Clean response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response.strip()
                
            json_str = json_str.replace("```json", "").replace("```", "")
            return json.loads(json_str)
        except Exception as e:
            print(f"Error parsing analysis: {e} | Response: {response}")
            return {"file": "unknown", "type": "UNKNOWN", "description": "Failed to analyze logs."}

    def generate_fix(self, file_content: str, error_analysis: dict) -> str:
        """
        Generates the fixed code.
        """
        prompt = f"""
            You are an expert Python developer.
            Refactor the following code to fix the reported error.
            
            Error Details:
            Type: {error_analysis.get("type")}
            Description: {error_analysis.get("description")}
            Line: {error_analysis.get("line")}

            Current Code:
            {file_content}

            Return ONLY the full corrected code. Do not wrap it in markdown blocks directly, just raw code is preferred but wrapped is okay.
        """
        
        messages = [
            {"role": "system", "content": "You are an expert coder. Return only code."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._chat_completion(messages)
        
        # Cleanup
        fixed_code = response.strip()
        code_block = re.search(r'```python(.*?)```', fixed_code, re.DOTALL)
        if code_block:
            fixed_code = code_block.group(1)
        else:
            code_block = re.search(r'```(.*?)```', fixed_code, re.DOTALL)
            if code_block:
                fixed_code = code_block.group(1)
            
        return fixed_code.strip()

    def _clean_dockerfile_string(self, raw_string: str) -> str:
        content = raw_string.strip()
        
        code_block = re.search(r'```(?:dockerfile)?(.*?)```', content, re.DOTALL | re.IGNORECASE)
        if code_block:
            content = code_block.group(1).strip()
            
        lines = content.splitlines()
        clean_lines = []
        started = False
        
        for line in lines:
            if line.strip().upper().startswith("FROM"):
                started = True
            
            if started:
                clean_lines.append(line)
        
        if not clean_lines:
             return content

        return "\n".join(clean_lines).strip()

    def generate_dockerfile(self, file_structure: str, sample_content: str = "", project_context: str = "", has_gpu: bool = False) -> str:
        gpu_instruction = "Host has GPU available. Use a CUDA-enabled base image **IF** the project requires it (e.g. ML/AI). Otherwise use a standard runtime (e.g. node:18-alpine, python:3.9-slim)." if has_gpu else "Use a standard CPU base image (e.g. node:18-alpine, python:3.9-slim)."

        prompt = f"""
            You are a Principal DevOps Architect. 
            Write a flawless, production-ready Dockerfile for the following project.
            
            {gpu_instruction}
            
            Project Analysis (explain.txt):
            {project_context}
            
            Project Structure:
            {file_structure}
            
            Dependency Content:
            {sample_content}
            
            CRITICAL RULES:
            1. Return ONLY the raw Dockerfile code.
            2. The very first word of your response MUST be 'FROM'. Do NOT add any preamble like "Here is the Dockerfile".
            3. Use official, slim/alpine images where possible (e.g. node:18-alpine, python:3.9-slim).
            4. **Install dependencies from lockfiles/manifests** (package.json, requirements.txt) ONLY. Do NOT manually install packages unless strictly necessary for the build environment.
            5. Ensure the application is exposed on the correct port and starts with the correct command (e.g. `npm start`, `python app.py`).
            6. **Node.js Specifics:**
               - use `npm ci` or `npm install` with `package.json` ONLY.
               - Check the provided `package.json` content in 'Dependency Content'. **ONLY run `npm run build` if a "build" script is explicitly present in `scripts`.** If no build script exists, DO NOT include a build step.
        """
        
        messages = [
            {"role": "system", "content": "You are a DevOps expert. Output ONLY valid Dockerfile content."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._chat_completion(messages)
        
        return self._clean_dockerfile_string(response)

    def fix_dockerfile(self, dockerfile_content: str, build_logs: str) -> str:
        prompt = f"""
            You are a Principal DevOps Architect.
            Fix the error in this Dockerfile based on the build logs.
            
            Broken Dockerfile:
            {dockerfile_content}
            
            Docker Error Log:
            {build_logs[-2000:]}
            
            Analysis:
            - If the error is "Missing script: build" or similar, REMOVE the `RUN npm run build` line entirely.
            - If the error is "unknown instruction", remove the invalid line (e.g. if it's a comment or note that isn't a valid instruction).
            - Ensure all dependencies are installed.
            
            Return ONLY the fully corrected Dockerfile code.
        """
        
        messages = [
            {"role": "system", "content": "You are a DevOps expert. Output ONLY valid Dockerfile content. Fix the error."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._chat_completion(messages)
        return self._clean_dockerfile_string(response)

    def get_relevant_files(self, file_structure: str) -> list:
        """
        Asks the LLM which files are relevant to understand the project structure.
        """
        prompt = f"""
            You are a Senior Software Architect.
            Review the following project file structure.
            Identify the top 5-10 most critical files that would help you understand:
            1. The Tech Stack (Language/Framework).
            2. Dependencies.
            3. Entry Point.
            
            Project Structure:
            {file_structure[:8000]} 
            
            Return ONLY a JSON list of file paths. Example:
            ["package.json", "src/index.js", "docker-compose.yml"]
        """
        
        messages = [
            {"role": "system", "content": "You are a Software Architect. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._chat_completion(messages)
        
        try:
             # Extract list from potential markdown
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                return []
        except:
            return []

    def analyze_project_structure(self, file_content_map: dict) -> str:
        """
        Analyzes the specific file contents to determine tech stack.
        """
        context = ""
        for fname, content in file_content_map.items():
            context += f"\n--- File: {fname} ---\n{content}\n"
            
        prompt = f"""
            You are a Senior Software Architect.
            Analyze the following project files to determine the tech stack and requirements.
            
            Project Files:
            {context[:12000]}
            
            Provide a concise summary (max 200 words) called 'explain.txt' that includes:
            1. The primary programming language and framework.
            2. Key dependencies.
            3. The estimated entry point command.
            4. Any specific environment requirements.
            5. **CRITICAL:** The user cannot read the source files. You MUST EXTRACT and LIST any hardcoded testing credentials, default environment variables (e.g. PORT, DB_URI), and specific API routes/test links found in the code.
            
            Context: This explanation will be used to generate a production-ready Dockerfile later, so focus on build and runtime requirements.
            
            Do NOT write code. Just explain the project context clearly.
        """
        
        messages = [
            {"role": "system", "content": "You are a Software Architect. Provide a concise project technical summary."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._chat_completion(messages)
        return response.strip()
