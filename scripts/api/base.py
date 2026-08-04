"""Abstract base class cho translation providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranslationResult:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0


class TranslationProvider(ABC):
    """Base class cho tất cả API translation providers."""

    @abstractmethod
    def translate(self, text: str, glossary: str = "", context: str = "",
                  system_prompt: str = "") -> TranslationResult:
        """Dịch text. Trả về TranslationResult."""
        ...

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test kết nối API. Trả về (success, message)."""
        ...

    @abstractmethod
    def get_info(self) -> dict:
        """Trả về info: provider name, model, etc."""
        ...

    def build_prompt(self, text: str, glossary: str = "", context: str = "") -> str:
        """Xây dựng prompt cho translation."""
        parts = []
        if glossary:
            parts.append(f"GLOSSARY:\n{glossary}")
        if context:
            parts.append(f"CONTEXT:\n{context}")
        parts.append(f"TEXT TO TRANSLATE:\n{text}")
        return "\n\n".join(parts)
