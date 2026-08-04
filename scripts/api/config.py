"""Config system — quản lý API keys và provider settings."""
import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".translate_book"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "active_provider": "deepseek",
    "providers": {
        "gemini": {
            "api_key": "",
            "model": "gemini-2.0-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
        },
        "deepseek": {
            "api_key": "",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
        },
        "custom": {
            "api_key": "",
            "model": "",
            "base_url": "",
        },
    },
}


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_config_dir()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Merge với default để đảm bảo đủ keys
        for key in DEFAULT_CONFIG:
            if key not in config:
                config[key] = DEFAULT_CONFIG[key]
        for provider in DEFAULT_CONFIG["providers"]:
            if provider not in config.get("providers", {}):
                config.setdefault("providers", {})[provider] = DEFAULT_CONFIG["providers"][provider]
        return config
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_active_provider() -> str:
    return load_config().get("active_provider", "deepseek")


def set_active_provider(name: str):
    config = load_config()
    config["active_provider"] = name
    save_config(config)


def get_provider_config(name: str) -> Optional[dict]:
    config = load_config()
    return config.get("providers", {}).get(name)


def set_provider_config(name: str, api_key: str, model: str = None, base_url: str = None):
    config = load_config()
    provider = config.get("providers", {}).get(name, {})
    if api_key:
        provider["api_key"] = api_key
    if model:
        provider["model"] = model
    if base_url:
        provider["base_url"] = base_url
    config.setdefault("providers", {})[name] = provider
    save_config(config)


def test_provider_connection(name: str) -> tuple[bool, str]:
    """Test kết nối API. Trả về (success, message)."""
    config = get_provider_config(name)
    if not config or not config.get("api_key"):
        return False, "Chưa cấu hình API key"

    try:
        if name == "gemini":
            return _test_gemini(config)
        elif name == "deepseek":
            return _test_openai_compat(config)
        elif name == "custom":
            return _test_openai_compat(config)
        return False, f"Provider '{name}' không hỗ trợ"
    except Exception as e:
        return False, f"Lỗi: {e}"


def _test_gemini(config: dict) -> tuple[bool, str]:
    try:
        import google.generativeai as genai
        genai.configure(api_key=config["api_key"])
        model = genai.GenerativeModel(config.get("model", "gemini-2.0-flash"))
        response = model.generate_content("Say 'OK' in one word.")
        return True, f"OK — Model: {config.get('model')}"
    except ImportError:
        return False, "Chưa cài google-generativeai: pip install google-generativeai"
    except Exception as e:
        return False, f"Lỗi: {e}"


def _test_openai_compat(config: dict) -> tuple[bool, str]:
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url"),
        )
        response = client.chat.completions.create(
            model=config.get("model", "gpt-3.5-turbo"),
            messages=[{"role": "user", "content": "Say 'OK' in one word."}],
            max_tokens=10,
        )
        return True, f"OK — Model: {config.get('model')}"
    except ImportError:
        return False, "Chưa cài openai: pip install openai"
    except Exception as e:
        return False, f"Lỗi: {e}"
