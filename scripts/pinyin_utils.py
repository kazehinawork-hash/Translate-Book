"""
pinyin_utils.py - Hàm Pinyin dùng chung

Cung cấp text_to_pinyin() và has_han() dùng cho make_bilingual.py,
add_pinyin_annotation.py, và các module khác cần sinh Pinyin.

Import:
    from pinyin_utils import text_to_pinyin, has_han, HAS_PYPINYIN
"""

import functools
import re

try:
    from pypinyin import pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False


HAN_RE = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]+')
CJK_PUNCTUATION_RE = re.compile(r'\s+([。，、；：！？）》」』】\u3000-\u303f\uff00-\uffef])')


def has_han(text: str) -> bool:
    """Kiểm tra text có chứa ký tự Hán không."""
    return bool(HAN_RE.search(text))


@functools.lru_cache(maxsize=256)
def text_to_pinyin(text: str) -> str:
    """Hán tự → Pinyin có dấu thanh. Giữ nguyên ký tự không phải Hán (số, dấu câu).

    Trả về chuỗi Pinyin rỗng nếu text không có Hán tự hoặc pypinyin chưa cài.
    """
    if not HAS_PYPINYIN or not has_han(text):
        return ''
    py_list = pinyin(text, style=Style.TONE, errors='default')
    result = ' '.join(p[0] for p in py_list)
    result = CJK_PUNCTUATION_RE.sub(r'\1', result)
    return result
