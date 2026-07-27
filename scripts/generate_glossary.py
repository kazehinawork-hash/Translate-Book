"""
generate_glossary.py - Tạo prompt cho Agent để sinh glossary CSV

Đọc source text từ working/extracted/ hoặc working/chunks/,
tạo prompt file tại working/glossary_prompt.txt.
Agent đọc prompt này và tự tạo glossary CSV -> lưu vào glossary/{book_name}.csv.

Ví dụ:
    python scripts/generate_glossary.py ^
        --source "working\extracted\mybook\raw.md" ^
        --book-name "mybook"

    python scripts/generate_glossary.py ^
        --source-dir "working\chunks\mybook" ^
        --book-name "mybook" ^
        --max-chars 8000

    python scripts/generate_glossary.py ^
        --source "working\extracted\mybook\raw.md" ^
        --book-name "mybook" ^
        --merge-genre "tien-hiep"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT


PROMPT_TEMPLATE = """Read the following text and extract ALL:
1. Character names (nh\u00e2n v\u1eadt)
2. Place names (\u0111\u1ecba \u0111i\u1ec3m)
3. Organization names (t\u1ed5 ch\u1ee9c)
4. Domain-specific terms (thu\u1eadt ng\u1eef chuy\u00ean ng\u00e0nh)
5. Brand/product names (th\u01b0\u01a1ng hi\u1ec7u/s\u1ea3n ph\u1ea9m)

Output as CSV format:
source,target,notes

Rules:
- "source" = original term (English/Chinese)
- "target" = suggested Vietnamese translation (leave blank if unsure, Agent will fill later)
- "notes" = brief context (e.g., "main character", "fictional city", "ML term")
- Sort by frequency (most frequent first)
- Do NOT include common words, only proper nouns and specialized terms

TEXT:
{text}
"""


def doc_text(file_path: Path) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1'):
        try:
            return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"Kh\u00f4ng th\u1ec3 \u0111\u1ecdc {file_path}")


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="T\u1ea1o prompt cho Agent \u0111\u1ec3 sinh glossary CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source', type=Path,
                              help='File source text (\u01b0u ti\u00ean: working/extracted/{book}/raw.md)')
    source_group.add_argument('--source-dir', type=Path,
                              help='Th\u01b0 m\u1ee5c ch\u1ee9a c\u00e1c file chunk JSON (working/chunks/{book}/)')
    parser.add_argument('--book-name', type=str, required=True,
                        help='T\u00ean s\u00e1ch (\u0111\u1eb7t t\u00ean file prompt v\u00e0 glossary output)')
    parser.add_argument('--max-chars', type=int, default=10000,
                        help='S\u1ed1 k\u00fd t\u1ef1 t\u1ed1i \u0111a cho preview text (m\u1eb7c \u0111\u1ecbnh: 10000)')
    parser.add_argument('--merge-genre', type=str,
                        help='Merge glossary m\u1edbi v\u00e0o glossary/genres/{genre}.csv hi\u1ec7n c\u00f3 (VD: "tien-hiep")')
    parser.add_argument('--output', type=Path,
                        help='File output prompt (m\u1eb7c \u0111\u1ecbnh: working/glossary_prompt_{book_name}.txt)')

    args = parser.parse_args()

    # Đọc source text
    text = ''
    if args.source:
        if not args.source.exists():
            print(f"[L\u1ed6I] File kh\u00f4ng t\u1ed3n t\u1ea1i: {args.source}", file=sys.stderr)
            sys.exit(1)
        text = doc_text(args.source)
        print(f"\u0110\u1ecdc: {args.source} ({len(text)} k\u00fd t\u1ef1)")
    elif args.source_dir:
        if not args.source_dir.exists():
            print(f"[L\u1ed6I] Th\u01b0 m\u1ee5c kh\u00f4ng t\u1ed3n t\u1ea1i: {args.source_dir}", file=sys.stderr)
            sys.exit(1)
        json_files = sorted(args.source_dir.glob('*.json'))
        if not json_files:
            print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y file JSON n\u00e0o trong {args.source_dir}", file=sys.stderr)
            sys.exit(1)
        texts = []
        for f in json_files:
            try:
                import json as _json
                data = _json.loads(doc_text(f))
                texts.append(data.get('text', ''))
            except Exception:
                continue
        text = '\n\n'.join(texts)
        print(f"\u0110\u1ecdc {len(json_files)} file chunk t\u1eeb {args.source_dir} ({len(text)} k\u00fd t\u1ef1)")

    if not text.strip():
        print("[L\u1ed6I] Kh\u00f4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c n\u1ed9i dung", file=sys.stderr)
        sys.exit(1)

    # Truncate if needed
    preview = text[:args.max_chars]
    if len(text) > args.max_chars:
        last_period = preview.rfind('.')
        last_newline = preview.rfind('\n')
        cut = max(last_period, last_newline)
        if cut > args.max_chars * 0.5:
            preview = preview[:cut + 1]
        print(f"  (c\u1eaft t\u1eeb {len(text)} k\u00fd t\u1ef1 xu\u1ed1ng {len(preview)} k\u00fd t\u1ef1)")

    prompt_content = PROMPT_TEMPLATE.format(text=preview)

    output_path = args.output or (PROJECT_ROOT / 'working' / f'glossary_prompt_{args.book_name}.txt')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt_content, encoding='utf-8')

    print(f"\n\u2705 \u0110\u00e3 t\u1ea1o prompt file: {output_path}")
    print(f"  Dung l\u01b0\u1ee3ng: {len(prompt_content)} k\u00fd t\u1ef1")
    print(f"\n  B\u01b0\u1edbc ti\u1ebfp: \u0110\u1ecdc file prompt v\u00e0 y\u00eau c\u1ea7u Agent t\u1ea1o glossary CSV")
    print(f"  L\u01b0u glossary v\u00e0o: glossary/{args.book_name}.csv")

    if args.merge_genre:
        genre_file = PROJECT_ROOT / 'glossary' / 'genres' / f'{args.merge_genre}.csv'
        if genre_file.exists():
            print(f"\n  \u0110\u00e3 t\u00ecm th\u1ea5y glossary/genres/{args.merge_genre}.csv")
            print(f"  Sau khi Agent t\u1ea1o CSV, ch\u1ea1y merge th\u1ee7 c\u00f4ng ho\u1eb7c copy c\u00e1c m\u1ee5c m\u1edbi v\u00e0o file n\u00e0y.")
        else:
            print(f"\n  \u26a0\ufe0f Ch\u01b0a c\u00f3 glossary/genres/{args.merge_genre}.csv")
            print(f"  T\u1ea1o file m\u1edbi khi Agent tr\u1ea3 v\u1ec1 glossary.")


if __name__ == '__main__':
    main()
