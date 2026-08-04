"""
add_pinyin.py - Generate pinyin from Chinese text, sentence by sentence

Reads Chinese text, splits by sentence boundaries (。/！？),
generates pinyin for each sentence, outputs JSON for trilingual translation.

Output format (JSON array):
[
  {
    "original": "Chinese sentence.",
    "pinyin": "zhōng wén jù zi.",
    "paragraph_index": 0
  },
  ...
]

Handles mixed CJK/Latin text: only generates pinyin for CJK characters,
leaves Latin letters, numbers, and punctuation as-is.

Ví dụ:
    python scripts/add_pinyin.py --input "working/extracted/mybook/raw.md" --output "working/pinyin/mybook.json"
    python scripts/add_pinyin.py --input "working/chunks/mybook/chunk-000.json" --output "working/pinyin/chunk-000.json"
"""

import os
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding

try:
    from pypinyin import pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False


CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
SENTENCE_SPLIT = re.compile(r'([^\u3002\uff01\uff1f]+[\u3002\uff01\uff1f])')
HAN_REGEX = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+')
PUNCTUATION = set('，。、；：？！""''（）【】《》——…·～.,;:?!\u3000 ')


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def sentence_pinyin(text: str) -> str:
    """Generate pinyin for a single sentence. Non-CJK parts are preserved as-is."""
    if not HAS_PYPINYIN:
        return text

    parts = re.split(r'([\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+)', text)
    result_parts = []
    prev_was_cjk = False
    for part in parts:
        if HAN_REGEX.fullmatch(part):
            py_list = pinyin(part, style=Style.TONE)
            pinyin_str = ' '.join(p[0] for p in py_list)
            if prev_was_cjk:
                pass
            elif result_parts and re.search(r'[a-zA-Z0-9]', result_parts[-1]):
                result_parts.append(' ')
            result_parts.append(pinyin_str)
            prev_was_cjk = True
        else:
            is_punct = part and all(c in PUNCTUATION for c in part.strip())
            if prev_was_cjk and part and not part.startswith(' ') and not is_punct:
                result_parts.append(' ')
            result_parts.append(part)
            prev_was_cjk = False

    return ''.join(result_parts)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences at Chinese punctuation boundaries."""
    sentences = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = SENTENCE_SPLIT.findall(line)
        consumed = 0
        if parts:
            for p in parts:
                if p.strip():
                    sentences.append(p.strip())
                consumed += len(p)
            tail = line[consumed:].strip()
            if tail:
                sentences.append(tail)
        else:
            sentences.append(line)
    return sentences


def process_text(text: str) -> list[dict]:
    """Process text and return list of {original, pinyin, paragraph_index}."""
    para_index = 0
    result = []

    paragraphs = re.split(r'\n\s*\n', text)
    for para in paragraphs:
        if not para.strip():
            continue
        sentences = split_sentences(para)
        for sent in sentences:
            result.append({
                'original': sent,
                'pinyin': sentence_pinyin(sent),
                'paragraph_index': para_index,
            })
        para_index += 1

    return result


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Generate pinyin from Chinese text, sentence by sentence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True,
                        help='Input file (Markdown or chunk JSON)')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output JSON file')
    parser.add_argument('--text-key', type=str, default='text',
                        help='JSON key to extract text (for chunk JSON input, default: "text")')

    args = parser.parse_args()

    if not HAS_PYPINYIN:
        print("[LỖI] Cần cài pypinyin: pip install pypinyin", file=sys.stderr)
        sys.exit(1)

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    raw = args.input.read_text(encoding='utf-8-sig')

    # Detect if input is JSON (chunk format) or plain text
    text = ''
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            text = data.get(args.text_key, '')
            if not text:
                text = data.get('text', '')
        elif isinstance(data, list):
            text = '\n\n'.join(d.get(args.text_key, '') for d in data)
    except (json.JSONDecodeError, ValueError):
        text = raw

    if not text.strip():
        print("[LỖI] Không tìm thấy text trong input", file=sys.stderr)
        sys.exit(1)

    print(f"Đọc: {args.input} ({len(text)} ký tự)")
    print(f"  Có CJK: {has_cjk(text)}")

    result = process_text(text)
    print(f"  Số câu: {len(result)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f"✓ Đã ghi: {args.output} ({len(result)} sentence entries)")


if __name__ == '__main__':
    main()
