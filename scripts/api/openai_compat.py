"""OpenAI-compatible API provider (DeepSeek, OpenCode, CommandCode, custom)."""
from .base import TranslationProvider, TranslationResult
from .config import get_provider_config


class OpenAICompatProvider(TranslationProvider):
    """OpenAI-compatible API — dùng cho DeepSeek, OpenCode, CommandCode, custom."""

    def __init__(self, provider_name: str = "deepseek"):
        config = get_provider_config(provider_name)
        if not config:
            raise ValueError(f"Chưa cấu hình {provider_name} API")
        self.provider_name = provider_name
        self.api_key = config.get("api_key", "")
        self.model_name = config.get("model", "gpt-3.5-turbo")
        self.base_url = config.get("base_url")

        try:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)
        except ImportError:
            raise ImportError("Chưa cài: pip install openai")

    def translate(self, text: str, glossary: str = "", context: str = "",
                  system_prompt: str = "") -> TranslationResult:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content = self.build_prompt(text, glossary, context)
        messages.append({"role": "user", "content": user_content})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.7,
        )

        result_text = response.choices[0].message.content or ""
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0

        return TranslationResult(
            text=result_text,
            model=self.model_name,
            provider=self.provider_name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    def test_connection(self) -> tuple[bool, str]:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Say 'OK' in one word."}],
                max_tokens=10,
            )
            return True, f"OK — Model: {self.model_name}"
        except Exception as e:
            return False, f"Lỗi: {e}"

    def get_info(self) -> dict:
        return {"provider": self.provider_name, "model": self.model_name, "base_url": self.base_url}
