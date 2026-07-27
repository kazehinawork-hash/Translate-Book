"""
add_pinyin_annotation.py - (TÙY CHỌN) Thêm Pinyin làm phụ chú dưới cụm Hán tự

CHỈ dùng khi muốn thêm Pinyin vào output cuối cùng (cho mục đích học phát âm,
bảng SRT 3 cột, ...). KHÔNG dùng làm bước trung gian dịch - xem PLAN.md mục 2.

Mode:
  - all: thêm Pinyin cho MỌI cụm Hán tự liên tiếp ≥ 1 ký tự
  - brackets: chỉ thêm cho Hán tự trong ngoặc vuông [汉字]
  - select: dùng regex/keyword tùy biến (TODO)

Ví dụ:
    python scripts/add_pinyin_annotation.py ^
        --input "output\$slug\full.md" ^
        --output "output\$slug\full-pinyin.md" ^
        --mode all
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402

try:
    from pypinyin import pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None


HAN_REGEX = re.compile(r'[㐀-鿿豈-﫿]+')
BRACKET_HAN_REGEX = re.compile(r'\[([㐀-鿿豈-﫿]+)\]')


def text_to_pinyin(text: str) -> str:
    """Chuyển Hán tự → Pinyin có dấu."""
    if not HAS_PYPINYIN:
        return text
    py_list = pinyin(text, style=Style.TONE)
    return ' '.join([p[0] for p in py_list])


def add_pinyin_all(text: str) -> str:
    """Thêm Pinyin dưới mỗi cụm Hán tự."""
    def replace(match):
        han = match.group(0)
        py = text_to_pinyin(han)
        return f"{han}\n<small>({py})</small>"
    return HAN_REGEX.sub(replace, text)


def add_pinyin_brackets(text: str) -> str:
    """Chỉ thêm Pinyin cho Hán tự trong [ngoặc vuông]."""
    def replace(match):
        han = match.group(1)
        py = text_to_pinyin(han)
        return f"[{han}]\n<small>({py})</small>"
    return BRACKET_HAN_REGEX.sub(replace, text)


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="(TÙY CHỌN) Thêm Pinyin làm phụ chú",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File Markdown đầu vào')
    parser.add_argument('--output', type=Path, required=True, help='File Markdown đầu ra')
    parser.add_argument('--mode', choices=['all', 'brackets'], default='all',
                        help='Chế độ: all (mọi cụm Hán tự) | brackets (chỉ trong [])')

    args = parser.parse_args()

    if not HAS_PYPINYIN:
        print("[LỖI] Cần cài pypinyin: pip install pypinyin", file=sys.stderr)
        sys.exit(1)

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    text = args.input.read_text(encoding='utf-8')
    print(f"Đọc: {args.input} ({len(text)} ký tự)")

    if args.mode == 'all':
        text_moi = add_pinyin_all(text)
    else:
        text_moi = add_pinyin_brackets(text)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text_moi, encoding='utf-8')
    print(f"✓ Đã ghi: {args.output}")
    print(f"  Mode: {args.mode}")
    print(f"  Kích thước: {len(text)} → {len(text_moi)} ký tự (+{len(text_moi) - len(text)})")


if __name__ == '__main__':
    main()
