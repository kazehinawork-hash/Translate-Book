"""
Pronunciation lexicon — map tên riêng/thuật ngữ → phiên âm đúng trước TTS.

Tham khảo VoiceStudio services/pronunciation.py.

Thứ tự applied (trước khi chunk):
  1. Glossary master (source→target) — chỉ dùng cho target == source (bản gốc)
  2. Per-book pronunciation JSON override (working/profile/<slug>-pronunciation.json)
  3. Inline overrides [[term|replacement]] trong text

Lưu ý: glossary master trong dự án này chứa source (Hán) → target (Việt).
Chỉ dùng glossary cho audiobook khi source == target (sách tiếng Việt nguyên bản)
hoặc khi có pronunciation.json override riêng.

Sử dụng:
    from pronunciation import apply_pronunciation
    text = apply_pronunciation(text, slug="ban-co-nam-cho-ngoi")
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Inline overrides: [[term|replacement]] / [[replacement]] ───────────────────
_INLINE_RE = re.compile(r"\[\[([^\]]{0,256})\]\]")


def apply_inline_overrides(text: str) -> str:
    """Resolve [[term|replacement]] → replacement, [[replacement]] → replacement."""
    if not text or "[[" not in text:
        return text or ""

    def _repl(m):
        inner = m.group(1)
        if "|" in inner:
            inner = inner.split("|", 1)[1]
        return inner

    return _INLINE_RE.sub(_repl, text)


# ── Lexicon matching (word-boundary aware, longest-first) ──────────────────────

def _boundary_prefix(key: str) -> str:
    return r"\b" if key[:1].isalnum() or key[:1] == "_" else ""


def _boundary_suffix(key: str) -> str:
    return r"\b" if key[-1:].isalnum() or key[-1:] == "_" else ""


def _compile(lexicon: dict[str, str]):
    """Build single alternation regex + casefold lookup. Keys sorted longest-first."""
    keys = sorted(lexicon.keys(), key=len, reverse=True)
    if not keys:
        return None, {}
    lookup = {k.casefold(): lexicon[k] for k in keys}
    alts = [f"{_boundary_prefix(k)}{re.escape(k)}{_boundary_suffix(k)}" for k in keys]
    pattern = re.compile("(?:" + "|".join(alts) + ")", re.IGNORECASE)
    return pattern, lookup


def apply_lexicon(text: str, lexicon: dict[str, str]) -> str:
    """Replace whole-word occurrences of each key with respelling.

    Case-insensitive, word-boundary aware, longest key first on overlap.
    Idempotent: applying twice gives the same result (no rescanning).
    """
    if not text or not lexicon:
        return text or ""
    pattern, lookup = _compile(lexicon)
    if pattern is None:
        return text

    def _repl(m):
        return lookup.get(m.group(0).casefold(), m.group(0))

    return pattern.sub(_repl, text)


# ── Load pronunciation dicts ───────────────────────────────────────────────────

def load_pronunciation_json(path: str) -> dict[str, str]:
    """Load {term: replacement} from a JSON file. {} on missing/empty."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k).strip(): str(v).strip()
                for k, v in data.items()
                if k and str(k).strip()}
    except Exception:
        return {}


def load_glossary_pronunciation(slug: str) -> dict[str, str]:
    """Load pronunciation from glossary master — chỉ dùng source→target
    khi source và target đều là phiên âm (không dùng translation mapping)."""
    # Glossary master dùng cho dịch, không dùng trực tiếp cho pronunciation.
    # Chỉ dùng khi có file pronunciation.json riêng.
    return {}


# ── Main API ───────────────────────────────────────────────────────────────────

def apply_pronunciation(text: str, slug: str = None,
                        extra_lexicon: dict[str, str] = None) -> str:
    """Apply pronunciation overrides to text trước khi TTS.

    Thứ tự:
      1. Per-book pronunciation JSON (working/profile/<slug>-pronunciation.json)
      2. Extra lexicon (nếu truyền thêm)
      3. Inline [[…]] overrides (cuối cùng — luôn thắng)

    Trả về text đã map, không raise.
    """
    if not text:
        return ""

    merged: dict[str, str] = {}

    # 1. Per-book pronunciation JSON
    if slug:
        pron_path = os.path.join(PROJECT_ROOT, "working", "profile",
                                 f"{slug}-pronunciation.json")
        book_dict = load_pronunciation_json(pron_path)
        if book_dict:
            merged.update(book_dict)

    # 2. Extra lexicon
    if extra_lexicon:
        merged.update({k: v for k, v in extra_lexicon.items() if k and v})

    # 3. Apply lexicon (longest-key-first)
    out = apply_lexicon(text, merged) if merged else text

    # 4. Inline [[…]] overrides — always last, always wins
    out = apply_inline_overrides(out)
    return out
