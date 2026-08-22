"""
Text normalization cho audiobook TTS — chuẩn hoá text trước khi gửi đến engine.

Áp dụng TRƯỚC pronunciation.py và TRƯỚC chunking.

Tham khảo VoiceStudio services/text_normalization.py — áp dụng cho tiếng Việt.

Xử lý:
  1. Xóa ký tự Unicode nguy hiểm (zero-width, bidi controls, BOM, etc.)
  2. Decode HTML entities (&amp; → &, &nbsp; → space, ...)
  3. Giới hạn ký tự lặp ("!!!!" → "!!!", "......" → "...")
  4. Gộp khoảng trắng thừa (tab/multiple spaces → single space)
  5. Giữ nguyên dấu ngoặc vuông [...] (grammar markers: [pause], [voice], ...)
  6. KHÔNG chuyển số tự → chữ (VieNeu đọc số Việt chuẩn, không cần num2words)
"""
from __future__ import annotations

import re

# ── Ký tự Unicode nguy hiểm (xóa bỏ) ──────────────────────────────────────────

_UNSAFE_CONTROL_CODEPOINTS = frozenset(
    (
        *range(0x00, 0x09),      # C0 controls (trừ \t)
        0x0B, 0x0C,              # VT, FF
        *range(0x0E, 0x20),      # C0 controls (trừ \r)
        *range(0x7F, 0xA0),      # DEL, C1 controls
        *range(0x200B, 0x2010),  # Zero-width chars
        *range(0x202A, 0x202F),  # Bidi controls
        *range(0x2060, 0x2065),  # Word joiners, invisible operators
        0xFEFF,                  # BOM
        0xFFFD,                  # Replacement char
    )
)
_UNSAFE_TRANSLATION = dict.fromkeys(_UNSAFE_CONTROL_CODEPOINTS)

# ── HTML entities ──────────────────────────────────────────────────────────────

_ENTITIES = {
    "&nbsp;": " ",
    "&quot;": '"',
    "&#39;": "'",
    "&apos;": "'",
    "&hellip;": "…",
    "&mdash;": "—",
    "&ndash;": "–",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
}
_ENTITY_RE = re.compile(
    "(?:" + "|".join(re.escape(k) for k in _ENTITIES) + r"|&amp;(?![a-zA-Z#]))"
)

# ── Ký tự lặp ─────────────────────────────────────────────────────────────────

_REPEAT_RE = re.compile(r"([!?.,;:~_*#=-])\1{3,}")

# ── Whitespace ─────────────────────────────────────────────────────────────────

_HSPACE_RE = re.compile(r"[^\S\n]+")
_NEWLINE_RE = re.compile(r"\n{3,}")


def _strip_unsafe_controls(text: str) -> str:
    return text.translate(_UNSAFE_TRANSLATION)


def _safety_filters(text: str) -> str:
    """Xóa ký tự nguy hiểm, decode entities, giới hạn lặp, gộp whitespace."""
    out = _strip_unsafe_controls(text)
    out = _ENTITY_RE.sub(lambda m: _ENTITIES.get(m.group(0), "&"), out)
    out = _REPEAT_RE.sub(lambda m: m.group(1) * 3, out)
    out = _HSPACE_RE.sub(" ", out)
    out = _NEWLINE_RE.sub("\n\n", out)
    return out.strip()


def normalize_for_tts(text: str) -> str:
    """Chuẩn hoá text trước TTS. Idempotent.

    Thứ tự:
      1. Safety filters (xóa control chars, decode entities, limit repeats)
    """
    if not text:
        return ""
    return _safety_filters(text)
