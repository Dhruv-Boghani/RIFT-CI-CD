from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from backend.config import Config
import os

def generate_fix(file_content: str, error_info: dict):
    if not Config.GEMINI_API_KEY:
        return "Error: No API Key"

    llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=Config.GEMINI_API_KEY)
   
    prompt = PromptTemplate.from_template(
        """
        You are an expert python developer. valid json output only.
        Fix the following error in the code.
        
        Error Type: {type}
        Error Description: {description}
        Line: {line}
        
        File Content:
        {content}
        
        Return ONLY the raw code of the fixed file. Do not use markdown blocks.
        """
    )
    
    try:
        res = prompt.invoke({
            "type": error_info.get('type'),
            "description": error_info.get('description'),
            "line": error_info.get('line'),
            "content": file_content
        })
        
        cleaned = res.content
        if cleaned.startswith("```python"):
            cleaned = cleaned[9:-3]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:-3]
            
        return cleaned.strip()
    except Exception as e:
        return file_content # Return original if fail
