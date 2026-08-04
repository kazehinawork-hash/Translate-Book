"""Service facade — chọn và tạo provider theo config."""
from .base import TranslationProvider
from .config import get_active_provider, get_provider_config


def get_provider(name: str = None) -> TranslationProvider:
    """Tạo và trả về TranslationProvider theo tên.

    Nếu name=None, dùng active provider từ config.
    """
    if name is None:
        name = get_active_provider()

    config = get_provider_config(name)
    if not config:
        raise ValueError(f"Provider '{name}' không tồn tại trong config")

    if name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider()
    elif name in ("deepseek", "custom"):
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(provider_name=name)
    else:
        raise ValueError(f"Provider '{name}' không hỗ trợ")
