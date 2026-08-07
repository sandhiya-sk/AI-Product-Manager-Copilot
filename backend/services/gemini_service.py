import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

print("Gemini Key Loaded:", bool(os.getenv("GEMINI_API_KEY")))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize the Gemini model globally
model = genai.GenerativeModel("gemini-1.5-flash")

def ask_gemini(prompt, system_instruction=None, json_mode=False):
    """
    Query Gemini AI with the given prompt.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY missing")
    
    generation_config = {}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
        
    if system_instruction or json_mode:
        local_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction,
            generation_config=genai.GenerationConfig(**generation_config) if generation_config else None
        )
        response = local_model.generate_content(prompt)
    else:
        response = model.generate_content(prompt)
        
    return response.text
