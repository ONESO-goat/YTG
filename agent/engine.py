"""Thin wrapper around the AI providers. Every call returns parsed JSON, or None when it fails."""

import base64
import json
import logging
from typing import Any

from helpers.config import Config

log = logging.getLogger(__name__)

# Seconds to wait for a model before treating the scan as unanalyzable
REQUEST_TIMEOUT = 60


def _mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def parse_json(text: str | None) -> dict[str, Any] | None:
    """Parse a model's JSON answer, tolerating markdown code fences around it."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        log.warning("Model returned invalid JSON: %.200s", text)
        return None
    return parsed if isinstance(parsed, dict) else None


class Engine:
    def __init__(self, ai_to_use: str = "ollama") -> None:
        if ai_to_use not in ("gemini", "ollama"):
            raise ValueError(f"'{ai_to_use}' is not a supported AI backend")

        if ai_to_use == "gemini" and not Config.gemini_api_key:
            log.warning("AI_BACKEND=gemini but no GEMINI_API_KEY is set; using Ollama instead")
            ai_to_use = "ollama"
        self.backend = ai_to_use

        if self.backend == "gemini":
            from google import genai

            self.gemini = genai.Client(api_key=Config.gemini_api_key)
            self.gemini_model = Config.gemini_model
        else:
            import ollama

            self.ollama = ollama.Client(host=Config.ollama_host, timeout=REQUEST_TIMEOUT)
            self.ollama_model = Config.ollama_qwen_2_dot_5
        log.info("AI engine: %s", self.backend)

    def describe_image(self, image_bytes: bytes, system_prompt: str) -> dict[str, Any] | None:
        """Ask a vision model to describe a screenshot as JSON."""
        if self.backend == "gemini":
            from google.genai import types

            content = types.Content(
                role="user",
                parts=[types.Part.from_bytes(data=image_bytes, mime_type=_mime_type(image_bytes))],
            )
            return self._gemini(content, system_prompt)
        return self._ollama(
            system_prompt,
            {
                "role": "user",
                "content": "Please analyze this image.",
                "images": [base64.b64encode(image_bytes).decode()],
            },
        )

    def judge(self, text: str, system_prompt: str) -> dict[str, Any] | None:
        """Ask a model for a JSON verdict about a text description."""
        # The description comes from screen content, so it is fenced off as data, never instructions
        fenced = f"<<<DATA>>>\n{text}\n<<<DATA>>>"
        if self.backend == "gemini":
            from google.genai import types

            return self._gemini(
                types.Content(role="user", parts=[types.Part.from_text(text=fenced)]), system_prompt
            )
        return self._ollama(system_prompt, {"role": "user", "content": fenced})

    def _gemini(self, content: Any, system_prompt: str) -> dict[str, Any] | None:
        from google.genai import types

        try:
            response = self.gemini.models.generate_content(
                model=self.gemini_model,
                contents=[content],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT * 1000),
                ),
            )
        except Exception:
            log.exception("Gemini request failed")
            return None
        return parse_json(response.text)

    def _ollama(self, system_prompt: str, message: dict[str, Any]) -> dict[str, Any] | None:
        try:
            response = self.ollama.chat(
                model=self.ollama_model,
                messages=[{"role": "system", "content": system_prompt}, message],
                format="json",
                options={"temperature": 0.2},
            )
        except Exception:
            log.exception("Ollama request failed (is it running at %s?)", Config.ollama_host)
            return None
        return parse_json(response["message"]["content"])
