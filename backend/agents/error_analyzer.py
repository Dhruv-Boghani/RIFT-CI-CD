from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from backend.config import Config
import json

def analyze_error(test_output: str):
    if not Config.GEMINI_API_KEY:
        return {"error": "Missing API Key"}
        
    llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=Config.GEMINI_API_KEY)
    
    prompt = PromptTemplate.from_template(
        """
        Analyze the following pytest output and identify the FIRST failure.
        Return a JSON object (NO MARKDOWN) with:
        - "file": path to the file causing the error
        - "line": line number (integer)
        - "type": one of [LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION]
        - "description": brief description of error
        
        Test Output:
        {output}
        """
    )
    
    chain = prompt | llm
    try:
        response = chain.invoke({"output": test_output})
        content = response.content.strip()
        # Clean markdown if present
        if content.startswith("```json"):
            content = content[7:-3]
        return json.loads(content)
    except Exception as e:
        # Fallback if parsing fails
        return {"type": "LOGIC", "description": "Could not parse error", "file": "unknown", "line": 0}

def analyze_code_file(file_info: dict):
    if not Config.GEMINI_API_KEY:
        return {"error": "Missing API Key"}
        
    llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=Config.GEMINI_API_KEY)
    
    prompt = PromptTemplate.from_template(
        """
        You are a senior python developer.
        Analyze the following python file for errors.
        
        File: {filename}
        
        Potential Issues Detected:
        {error_detail}
        
        File Content:
        {content}
        
        Task:
        Identify the FIRST critical error (Syntax, Linting, Import, Logic).
        If no critical error exists, return INVALID_JSON.
        
        Return a valid JSON object (NO MARKDOWN) with:
        - "file": "{filename}"
        - "line": line number (integer)
        - "type": one of [LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION]
        - "description": brief description of error
        - "suggested_fix": brief fix suggestion
        """
    )
    
    chain = prompt | llm
    try:
        response = chain.invoke({
            "filename": file_info.get("file"),
            "error_detail": file_info.get("error_detail", "None"),
            "content": file_info.get("content")
        })
        
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return json.loads(content)
    except Exception as e:
        # Fallback or no error found
        return None
