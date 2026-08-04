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

import os
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT


PROMPT_TEMPLATE = """Read the following text and extract ALL:
1. Character names (nhân vật)
2. Place names (địa điểm)
3. Organization names (tổ chức)
4. Domain-specific terms (thuật ngữ chuyên ngành)
5. Skills / Magic items / Artifacts / Cultivation levels (Chiêu thức, pháp bảo, vật phẩm, cảnh giới)
6. Brand/product names (thương hiệu/sản phẩm)

Output as CSV format:
source,target,notes

Rules:
- "source" = original term (English/Chinese)
- "target" = suggested Vietnamese translation (leave blank if unsure)
- "notes" = brief context (e.g., "main character", "fictional city", "artifact", "martial art")
- Sort by frequency (most frequent first)
- Do NOT include common words, only proper nouns and specialized terms
- CRITICAL: OUTPUT ONLY THE RAW CSV TEXT. NO EXPLANATIONS, NO MARKDOWN BLOCKS (```), NO GREETINGS.

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
        # Sort numerically by extracting digits from filename to handle >999 chunks
        import re
        json_files = sorted(args.source_dir.glob('*.json'), key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
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

    # L\u1ea5y m\u1eabu tr\u1ea3i \u0111\u1ec1u (\u0110\u1ea7u, Gi\u1eefa, Cu\u1ed1i) n\u1ebfu v\u0103n b\u1ea3n qu\u00e1 d\u00e0i
    if len(text) > args.max_chars * 1.5:
        part_size = args.max_chars // 3
        
        start_text = text[:part_size]
        mid_idx = len(text) // 2 - part_size // 2
        mid_text = text[mid_idx:mid_idx + part_size]
        end_text = text[-part_size:]
        
        # C\u1ed1 g\u1eafng c\u1eaft g\u1ecdn g\u00e0ng t\u1ea1i c\u00e1c d\u00f2ng m\u1edbi
        def clean_chunk(chunk_text, is_start=False, is_end=False):
            start_cut = 0 if is_start else chunk_text.find('\n')
            if start_cut == -1: start_cut = 0
            end_cut = len(chunk_text) if is_end else chunk_text.rfind('\n')
            if end_cut <= 0: end_cut = len(chunk_text)
            return chunk_text[start_cut:end_cut].strip()

        start_text = clean_chunk(start_text, is_start=True)
        mid_text = clean_chunk(mid_text)
        end_text = clean_chunk(end_text, is_end=True)
        
        preview = (
            "--- PH\u1ea6N \u0110\u1ea6U TRUY\u1ec6N ---\n" + start_text + "\n\n" +
            "--- PH\u1ea6N GI\u1eeeA TRUY\u1ec6N ---\n" + mid_text + "\n\n" +
            "--- PH\u1ea6N CU\u1ed0I TRUY\u1ec6N ---\n" + end_text
        )
        print(f"  (L\u1ea5y m\u1eabu \u0110\u1ea7u-Gi\u1eefa-Cu\u1ed1i t\u1eeb {len(text)} k\u00fd t\u1ef1, xu\u1ed1ng c\u00f2n {len(preview)} k\u00fd t\u1ef1)")
    else:
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
