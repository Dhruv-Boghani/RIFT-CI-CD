from backend.agents.llm_client import HealingAgentLLM
import os

class FixGeneratorAgent:
    def __init__(self):
        self.llm = HealingAgentLLM()

    def generate_fix(self, file_content: str, error_analysis: dict, language: str = "Unknown") -> str:
        """
        Generates a code fix using LLM with language context.
        """
        current_error = error_analysis.get('description', error_analysis.get('message', 'Unknown Error'))
        
        prompt = f"""
            You are an expert Autonomous Coding Agent specializing in {language}.
            
            Analyze the following code and the detected error.
            Generate a minimal, correct fix.
            
            Context:
            - Language: {language}
            - Error Type: {error_analysis.get('type')}
            - Location: Line {error_analysis.get('line')}
            - Message: {current_error}
            
            CODE CONTENT:
            ```
            {file_content}
            ```
            
            INSTRUCTIONS:
            1. Fix ONLY the reported error.
            2. Do not add comments or explanations.
            3. Return the COMPLETE file content with the fix applied.
            4. Ensure the syntax is correct for {language}.
            5. CRITICAL: output valid code only.
            
            OUTPUT FORMAT:
            Start with "FIX_DESCRIPTION: <short description of fix>" on the first line.
            Then provide the code block.
        """
        
        messages = [
            {"role": "system", "content": f"You are a coding expert in {language}. Return FIX_DESCRIPTION then Code."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm._chat_completion(messages)
            
            # Parse response
            lines = response.strip().split('\n')
            description = "Fixed error"
            code_lines = []
            
            for line in lines:
                if line.startswith("FIX_DESCRIPTION:"):
                    description = line.replace("FIX_DESCRIPTION:", "").strip()
                else:
                    code_lines.append(line)
            
            clean_code = "\n".join(code_lines).strip()
            
            # Aggressive cleanup
            if clean_code.startswith("```"):
                # Find first newline inside code block if mixed
                first_newline = clean_code.find("\n")
                if first_newline != -1:
                    clean_code = clean_code[first_newline+1:]
            
            if clean_code.endswith("```"):
                clean_code = clean_code[:-3]
                
            clean_code = clean_code.strip()
            
            # Fallback: if code is empty or seemingly invalid, return original
            if not clean_code or len(clean_code) < 10:
                print("Fix Gen: Result too short or empty.")
                return file_content, "No fix generated"

            return clean_code, description
            
        except Exception as e:
            print(f"Fix Gen Error: {e}")
            return file_content, "Error generating fix"

    def apply_fix_to_repo(self, repo_path: str, file_rel_path: str, new_content: str):
        full_path = os.path.join(repo_path, file_rel_path)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
