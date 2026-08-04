"""Google Gemini API provider."""
import os
from .base import TranslationProvider, TranslationResult
from .config import get_provider_config


class GeminiProvider(TranslationProvider):
    """Gemini API — google-generativeai."""

    def __init__(self):
        config = get_provider_config("gemini")
        if not config:
            raise ValueError("Chưa cấu hình Gemini API")
        self.api_key = config.get("api_key", "")
        self.model_name = config.get("model", "gemini-2.0-flash")

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        except ImportError:
            raise ImportError("Chưa cài: pip install google-generativeai")

    def translate(self, text: str, glossary: str = "", context: str = "",
                  system_prompt: str = "") -> TranslationResult:
        prompt = self.build_prompt(text, glossary, context)
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"

        response = self.model.generate_content(prompt)
        return TranslationResult(
            text=response.text,
            model=self.model_name,
            provider="gemini",
        )

    def test_connection(self) -> tuple[bool, str]:
        try:
            response = self.model.generate_content("Say 'OK' in one word.")
            return True, f"OK — Model: {self.model_name}"
        except Exception as e:
            return False, f"Lỗi: {e}"

    def get_info(self) -> dict:
        return {"provider": "gemini", "model": self.model_name}
