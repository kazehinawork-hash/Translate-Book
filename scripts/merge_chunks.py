"""
merge_chunks.py - Gộp tất cả chunk đã dịch thành file hoàn chỉnh

Đọc file JSON từ working/progress/ (sắp xếp theo chunk_id),
ghép nội dung translated_text, xuất ra output/{book_name}_translated.md.

Ví dụ:
    python scripts/merge_chunks.py ^
        --progress-dir "working\progress\mybook" ^
        --book-name "mybook" ^
        --force

    python scripts/merge_chunks.py ^
        --progress-dir "working\progress\mybook" ^
        --book-name "mybook" ^
        --allow-partial

    python scripts/merge_chunks.py ^
        --progress-dir "working\progress\mybook" ^
        --book-name "mybook" ^
        --skip-missing
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT


TERMINAL_WIDTH = 66


def doc_chunk_json(file_path: Path) -> dict | None:
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            data = json.loads(file_path.read_text(encoding=enc))
            if 'chunk_id' not in data:
                return None
            return data
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return None


def lay_chunk_id(file_path: Path) -> int:
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            data = json.loads(file_path.read_text(encoding=enc))
            return int(data.get('chunk_id', 999999))
        except (json.JSONDecodeError, ValueError, KeyError):
            continue
    stem = file_path.stem
    nums = [int(s) for s in stem.split('_') if s.isdigit()] or [999999]
    return nums[0]


def print_header(title: str, char: str = '\u2550'):
    print(f"\n{char * TERMINAL_WIDTH}")
    print(f"  {title}")
    print(f"{char * TERMINAL_WIDTH}")


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
    parser.add_argument('--allow-partial', action='store_true',
                        help='Cho ph\u00e9p merge khi thi\u1ebfu chunk (ch\u00e8n placeholder [CH\u01afA D\u1ecaCH])')
    parser.add_argument('--skip-missing', action='store_true',
                        help='B\u1ecf qua chunk thi\u1ebfu (kh\u00f4ng ch\u00e8n placeholder)')

    args = parser.parse_args()

    if not args.progress_dir.exists():
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y th\u01b0 m\u1ee5c: {args.progress_dir}", file=sys.stderr)
        sys.exit(1)

    if args.allow_partial and args.skip_missing:
        print("[L\u1ed6I] Kh\u00f4ng th\u1ec3 d\u00f9ng c\u1ea3 --allow-partial v\u00e0 --skip-missing c\u00f9ng l\u00fac",
              file=sys.stderr)
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

    # Read all chunk files
    json_files = sorted(
        [f for f in args.progress_dir.glob('*.json') if f.is_file()],
        key=lay_chunk_id,
    )

    if not json_files:
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y file JSON n\u00e0o trong {args.progress_dir}", file=sys.stderr)
        sys.exit(1)

    # Parse all chunks
    chunk_map = {}
    invalid = []
    for fpath in json_files:
        data = doc_chunk_json(fpath)
        if data is None:
            invalid.append(fpath.name)
            continue
        cid = int(data.get('chunk_id', -1))
        if cid < 0:
            invalid.append(fpath.name)
            continue
        chunk_map[cid] = data

    # Determine total_chunks
    total_chunks = max(
        max((d.get('total_chunks', 0) for d in chunk_map.values()), default=0),
        max(chunk_map.keys(), default=0) + 1,
    )

    # Validate chunk coverage
    expected_ids = set(range(total_chunks))
    present_ids = set(chunk_map.keys())
    missing_ids = sorted(expected_ids - present_ids)

    # Check for empty translations
    empty_ids = []
    for cid in list(chunk_map.keys()):
        text = chunk_map[cid].get('translated_text', '').strip()
        if not text:
            empty_ids.append(cid)

    # Validation report
    print_header(f"MERGE VALIDATION")
    print(f"  Total expected chunks: {total_chunks}")
    print(f"  Chunks found: {len(chunk_map)}")
    if invalid:
        print(f"  Invalid files: {len(invalid)} ({', '.join(invalid[:5])}{'...' if len(invalid) > 5 else ''})")
    missing_all = sorted(set(missing_ids + empty_ids))

    if missing_all:
        print(f"  Missing/empty chunks: {len(missing_all)}")
        for cid in missing_ids:
            print(f"    \u274c Chunk {cid}: MISSING")
        for cid in empty_ids:
            if cid not in missing_ids:
                print(f"    \u274c Chunk {cid}: EMPTY translation")

        if args.skip_missing:
            print(f"\n  \u23ed --skip-missing: b\u1ecf qua {len(missing_all)} chunk thi\u1ebfu/r\u1ed7ng")
        elif args.allow_partial:
            print(f"\n  \u23ed --allow-partial: ch\u00e8n placeholder cho {len(missing_all)} chunk thi\u1ebfu/r\u1ed7ng")
        else:
            print(f"\n  [L\u1ed6I] Ph\u00e1t hi\u1ec7n chunk thi\u1ebfu/r\u1ed7ng.")
            print(f"  D\u00f9ng --allow-partial \u0111\u1ec3 ch\u00e8n placeholder, --skip-missing \u0111\u1ec3 b\u1ecf qua,")
            print(f"  ho\u1eb7c ho\u00e0n th\u00e0nh c\u00e1c chunk thi\u1ebfu tr\u01b0\u1edbc khi merge.")
            sys.exit(1)

    # Merge
    segments = []
    merged_count = 0
    total_words_source = 0
    total_words_translated = 0

    for cid in range(total_chunks):
        if cid in chunk_map and chunk_map[cid].get('translated_text', '').strip():
            data = chunk_map[cid]
            t = data['translated_text'].strip()
            segments.append(t)
            merged_count += 1
            total_words_source += data.get('word_count_source', 0) or len(data.get('source_text', '').split())
            total_words_translated += data.get('word_count_translated', 0) or len(t.split())
        elif args.allow_partial:
            segments.append(f"[CH\u01afA D\u1ecaCH - Chunk {cid}]")
        elif args.skip_missing:
            pass  # skip entirely

    merged = '\n\n'.join(segments)
    output_file.write_text(merged, encoding='utf-8')

    elapsed = time.time() - start_time

    # Final statistics
    print_header(f"MERGE COMPLETE")
    print(f"  Book: {args.book_name}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Merged: {merged_count}")
    if missing_all:
        print(f"  Missing: {len(missing_all)} (chunk {', '.join(str(x) for x in missing_all[:10])}"
              f"{'...' if len(missing_all) > 10 else ''})")
    print(f"  Total words (source): ~{total_words_source:,}")
    print(f"  Total words (translated): ~{total_words_translated:,}")
    print(f"  Output: {output_file}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"{chr(0x2550) * TERMINAL_WIDTH}")

    if missing_all and args.allow_partial:
        print(f"\n  \u26a0\ufe0f {len(missing_all)} placeholder(s) inserted for missing chunks.")
    elif missing_all and args.skip_missing:
        print(f"\n  \u26a0\ufe0f {len(missing_all)} missing chunk(s) silently skipped.")


if __name__ == '__main__':
    main()
