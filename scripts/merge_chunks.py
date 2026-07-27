"""
merge_chunks.py - Gộp tất cả chunk đã dịch thành file hoàn chỉnh

Đọc file JSON từ working/progress/ (sắp xếp theo chunk_id),
ghép nội dung translated_text, xuất ra output/{book_name}_translated.md.

Ví dụ:
    python scripts/merge_chunks.py ^
        --progress-dir "working\progress\mybook" ^
        --book-name "mybook" ^
        --force
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT


def doc_chunk_json(file_path: Path) -> dict | None:
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            data = json.loads(file_path.read_text(encoding=enc))
            if 'chunk_id' not in data:
                print(f"  \u26a0\ufe0f B\u1ecf qua {file_path.name}: thi\u1ebfu chunk_id", file=sys.stderr)
                return None
            return data
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    print(f"  \u26a0\ufe0f Kh\u00f4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c {file_path.name}", file=sys.stderr)
    return None


def lay_chunk_id(file_path: Path) -> int:
    """Extract chunk_id from filename (chunk_001.json -> 1) or file content."""
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            data = json.loads(file_path.read_text(encoding=enc))
            return int(data.get('chunk_id', 999999))
        except (json.JSONDecodeError, ValueError, KeyError):
            continue
    # Fallback: extract from filename
    stem = file_path.stem
    nums = [int(s) for s in stem.split('_') if s.isdigit()] or [999999]
    return nums[0]


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="G\u1ed9p c\u00e1c chunk \u0111\u00e3 d\u1ecbch th\u00e0nh file ho\u00e0n ch\u1ec9nh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--progress-dir', type=Path, required=True,
                        help='Th\u01b0 m\u1ee5c ch\u1ee9a c\u00e1c file chunk JSON \u0111\u00e3 d\u1ecbch')
    parser.add_argument('--book-name', type=str, required=True,
                        help='T\u00ean s\u00e1ch (\u0111\u1eb7t t\u00ean file output)')
    parser.add_argument('--force', action='store_true',
                        help='Ghi \u0111\u00e8 m\u00e0 kh\u00f4ng h\u1ecfi confirm')
    parser.add_argument('--output-dir', type=Path,
                        help='Th\u01b0 m\u1ee5c output (m\u1eb7c \u0111\u1ecbnh: output/)')

    args = parser.parse_args()

    if not args.progress_dir.exists():
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y th\u01b0 m\u1ee5c: {args.progress_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output_dir or (PROJECT_ROOT / 'output')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.book_name}_translated.md"

    if output_file.exists() and not args.force:
        print(f"File \u0111\u00e3 t\u1ed3n t\u1ea1i: {output_file}")
        ans = input("Ghi \u0111\u00e8? (y/N): ").strip().lower()
        if ans != 'y':
            print("H\u1ee7y b\u1ecf.")
            sys.exit(0)

    start_time = time.time()

    json_files = sorted(
        [f for f in args.progress_dir.glob('*.json') if f.is_file()],
        key=lay_chunk_id,
    )

    if not json_files:
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y file JSON n\u00e0o trong {args.progress_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\u0110\u1ecdc {len(json_files)} file chunk t\u1eeb {args.progress_dir}")

    chunks = []
    skipped = 0
    for fpath in json_files:
        data = doc_chunk_json(fpath)
        if data is None:
            skipped += 1
            continue
        translated = data.get('translated_text', '').strip()
        if not translated:
            print(f"  \u26a0\ufe0f Chunk {data.get('chunk_id', '?')} ch\u01b0a c\u00f3 translated_text, b\u1ecf qua")
            skipped += 1
            continue
        chunks.append(data)

    if not chunks:
        print("[L\u1ed6I] Kh\u00f4ng c\u00f3 chunk n\u00e0o c\u00f3 d\u1eef li\u1ec7u d\u1ecbch", file=sys.stderr)
        sys.exit(1)

    chunks.sort(key=lambda c: int(c.get('chunk_id', 999999)))

    segments = []
    total_words = 0
    for c in chunks:
        t = c.get('translated_text', '').strip()
        segments.append(t)
        total_words += len(t.split())

    merged = '\n\n'.join(segments)
    output_file.write_text(merged, encoding='utf-8')

    elapsed = time.time() - start_time

    print(f"\n\u2705 Ho\u00e0n th\u00e0nh: {output_file}")
    print(f"  T\u1ed5ng s\u1ed1 chunk \u0111\u00e3 merge: {len(chunks)}" + (f" (b\u1ecf qua {skipped})" if skipped else ""))
    print(f"  T\u1ed5ng s\u1ed1 t\u1eeb: ~{total_words}")
    print(f"  Th\u1eddi gian: {elapsed:.2f}s")


if __name__ == '__main__':
    main()
