import os
import secrets

import dotenv

dotenv.load_dotenv()


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class Config:
    gemini_api_key = os.getenv("GEMINI_API_KEY2") or os.getenv("GEMINI_API_KEY") or ""

    # Which classifier to use: "stub" (no AI, for development), "ollama" or "gemini"
    ai_backend = os.getenv("AI_BACKEND", "stub").lower()

    # Ollama config
    ollama_host = os.getenv("OLLAMA_HOST", "http://172.26.144.1:11434")
    ollama_model_qwen = "qwen3:0.6b"
    ollama_qwen_2_dot_5 = "qwen2.5vl:7b"
    ollama_guard = "llama-guard3"

    # Gemini config
    gemini_model = "gemini-2.5-flash"

    # Database
    database_url = os.getenv("DATABASE_URL", "sqlite:///./database.db")
    database_echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"

    # Auth. Without JWT_SECRET a random one is generated, so tokens stop working on restart.
    jwt_secret = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
    jwt_secret_is_ephemeral = not os.getenv("JWT_SECRET")
    jwt_algorithm = "HS256"
    jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))

    # Admin-only endpoints (reward creation, manual point edits, daily settlement)
    # require this key in the X-Admin-Key header. Unset means they are disabled.
    admin_api_key = os.getenv("ADMIN_API_KEY", "")

    cors_origins = _env_list(
        "CORS_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173",
    )
