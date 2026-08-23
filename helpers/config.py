
import dotenv
import os

dotenv.load_dotenv()

    
class Config:
    gemini_api_key = os.getenv("GEMINI_API_KEY2") or ''

    worker_file = "data/workers.json"
    
    location = "boston"
    # Ollama config
    ollama_model_qwen = 'qwen3:0.6b'
    ollama_qwen_2_dot_5 = 'qwen2.5vl:7b'
    ollama_guard = "llama-guard3"
    
    # Gemini config
    gemini_model = 'gemini-2.5-flash'

if not Config.gemini_api_key:
    raise ValueError("An API key is NONE")
