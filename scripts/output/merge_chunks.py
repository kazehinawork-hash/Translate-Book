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

import os
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT


TERMINAL_WIDTH = 66

# ─── Public API ──────────────────────────────────────────────────────────────

MergeResult = dict  # {segments: list[str], merged_count: int, ...}


def validate_chunk_coverage(chunks: list[tuple[int, dict]]) -> dict:
    """Kiểm tra coverage và tính nhất quán trước khi merge."""
    invalid_ids = [cid for cid, _ in chunks if cid < 0]
    ids = [cid for cid, _ in chunks]
    duplicate_ids = sorted({cid for cid in ids if ids.count(cid) > 1})
    chunk_map = dict(chunks)
    total_values = {
        int(data.get('total_chunks', 0))
        for _, data in chunks
        if data.get('total_chunks') is not None
    }
    total_chunks = max(
        max(total_values, default=0),
        max(ids, default=-1) + 1,
    )
    missing_ids = sorted(set(range(total_chunks)) - set(ids))
    empty_ids = sorted(
        cid for cid, data in chunk_map.items()
        if not data.get('translated_text', '').strip()
    )
    return {
        'total_chunks': total_chunks,
        'present_ids': sorted(set(ids)),
        'missing_ids': missing_ids,
        'empty_ids': empty_ids,
        'duplicate_ids': duplicate_ids,
        'invalid_ids': invalid_ids,
        'inconsistent_totals': sorted(total_values - {0, total_chunks}),
        'missing_all': sorted(set(missing_ids + empty_ids)),
    }


def merge_texts(
    total_chunks: int,
    chunk_map: dict[int, dict],
    fmt: str,
    allow_partial: bool,
    skip_missing: bool,
) -> MergeResult:
    """Gộp chunks thành 1 string, tự động chèn heading ## chapter.

    Trả về dict với keys: segments, merged, merged_count, total_words_source,
    total_words_translated.
    """
    segments: list[str] = []
    merged_count = 0
    total_words_source = 0
    total_words_translated = 0
    last_chapter: str | None = None

    for cid in range(total_chunks):
        if cid in chunk_map and chunk_map[cid].get('translated_text', '').strip():
            data = chunk_map[cid]
            chapter = (data.get('chapter') or '').strip()

            # Chèn page break nếu chapter thay đổi
            heading = ''
            if chapter and chapter != last_chapter:
                if last_chapter is not None:
                    heading = '<div style="page-break-before: always;"></div>\n\n'
                last_chapter = chapter

            if fmt == 'trilingual':
                orig = data.get('original_text', '').strip()
                pin = data.get('pinyin_text', '').strip()
                trans = data['translated_text'].strip()

                orig_lines = [l for l in orig.splitlines() if l.strip()]
                pin_lines = [l for l in pin.splitlines() if l.strip()]
                trans_lines = [l for l in trans.splitlines() if l.strip()]

                max_lines = max(len(orig_lines), len(pin_lines), len(trans_lines))
                if len(orig_lines) != len(pin_lines) or len(orig_lines) != len(trans_lines):
                    print(f'  \u26a0\ufe0f Chunk {cid}: line count mismatch (orig={len(orig_lines)}, pinyin={len(pin_lines)}, vi={len(trans_lines)}), padding to {max_lines}')

                block_parts = []
                for i in range(max_lines):
                    o = orig_lines[i] if i < len(orig_lines) else ''
                    p = pin_lines[i] if i < len(pin_lines) else ''
                    v = trans_lines[i] if i < len(trans_lines) else ''

                    if o.startswith('#') or v.startswith('#'):
                        # Output heading natively for Pandoc TOC
                        raw_o = re.sub(r'^(#{1,6})\s+', '', o).strip()
                        raw_p = re.sub(r'^(#{1,6})\s*', '', p).strip()
                        block_parts.append(f"{v}\n\n**{raw_o}**\n\n*{raw_p}*")
                    elif o.startswith('![') or v.startswith('!['):
                        # Images should not be wrapped; avoid duplicating when
                        # the translation kept the same image line
                        if o == v:
                            block_parts.append(o)
                        else:
                            block_parts.append(f"{o}\n\n{v}")
                    else:
                        block_parts.append(
                            f'<div class="tri-block">\n'
                            f'<p class="src-zh">{o}</p>\n'
                            f'<p class="pinyin">{p}</p>\n'
                            f'<p class="vi">{v}</p>\n'
                            f'</div>'
                        )
                t = '\n\n'.join(block_parts)
                t = heading + t
            else:
                t = heading + data['translated_text'].strip()

            segments.append(t)
            merged_count += 1
            total_words_source += data.get('word_count_source', 0) or len(data.get('source_text', '').split())
            total_words_translated += data.get('word_count_translated', 0) or len(t.split())
        elif allow_partial:
            segments.append(f'[CHƯA DỊCH - Chunk {cid + 1}]')
        elif skip_missing:
            pass

    merged = '\n\n'.join(segments)
    return {
        'segments': segments,
        'merged': merged,
        'merged_count': merged_count,
        'total_words_source': total_words_source,
        'total_words_translated': total_words_translated,
    }


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
    parser.add_argument('--format', type=str, choices=['bilingual', 'trilingual'], default='bilingual',
                        help='\u0110\u1ecbnh d\u1ea1ng output: bilingual = ch\u1ec9 ti\u1ebfng Vi\u1ec7t (d\u00f9ng l\u00e0m input trung gian cho make_bilingual.py), trilingual = 3 d\u00f2ng g\u1ed1c/pinyin/d\u1ecbch')
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
    suffix = "_trilingual" if args.format == 'trilingual' else "_translated"
    output_file = output_dir / f"{args.book_name}{suffix}.md"

    if output_file.exists() and not args.force:
        print(f"File \u0111\u00e3 t\u1ed3n t\u1ea1i: {output_file}")
        ans = input("Ghi \u0111\u00e8? (y/N): ").strip().lower()
        if ans != 'y':
            print("H\u1ee7y b\u1ecf.")
            sys.exit(0)

    start_time = time.time()

    # Read all chunks once
    chunks = []
    invalid = []
    for f in args.progress_dir.glob('*.json'):
        if not f.is_file():
            continue
        data = doc_chunk_json(f)
        if data is None:
            invalid.append(f.name)
            continue
        cid = int(data.get('chunk_id', -1))
        if cid < 0:
            invalid.append(f.name)
            continue
        chunks.append((cid, data))

    if not chunks:
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y file JSON n\u00e0o trong {args.progress_dir}", file=sys.stderr)
        sys.exit(1)

    chunks.sort(key=lambda x: x[0])
    chunk_map = dict(chunks)
    validation = validate_chunk_coverage(chunks)
    total_chunks = validation['total_chunks']
    missing_ids = validation['missing_ids']
    empty_ids = validation['empty_ids']
    missing_all = validation['missing_all']

    # Validation report
    print_header(f"MERGE VALIDATION")
    print(f"  Total expected chunks: {total_chunks}")
    print(f"  Chunks found: {len(chunk_map)}")
    if invalid:
        print(f"  Invalid files: {len(invalid)} ({', '.join(invalid[:5])}{'...' if len(invalid) > 5 else ''})")
    if validation['duplicate_ids']:
        print(f"  Duplicate chunk IDs: {', '.join(map(str, validation['duplicate_ids']))}")
    if validation['inconsistent_totals']:
        print(f"  Inconsistent total_chunks values: {validation['inconsistent_totals']}")
    if validation['duplicate_ids'] or validation['inconsistent_totals']:
        print("\n  [LỖI] Manifest chunk không nhất quán; dừng merge để tránh mất hoặc đảo nội dung.", file=sys.stderr)
        sys.exit(1)

    if missing_all:
        print(f"  Missing/empty chunks: {len(missing_all)}")
        for cid in missing_ids:
            print(f"    ❌ Chunk {cid + 1}: MISSING (file chunk-{cid + 1:03d}.json)")
        for cid in empty_ids:
            if cid not in missing_ids:
                print(f"    ❌ Chunk {cid + 1}: EMPTY translation")

        if args.skip_missing:
            print(f"\n  ⏭ --skip-missing: bỏ qua {len(missing_all)} chunk thiếu/rỗng")
        elif args.allow_partial:
            print(f"\n  ⏭ --allow-partial: chèn placeholder cho {len(missing_all)} chunk thiếu/rỗng")
        else:
            print(f"\n  [LỖI] Phát hiện chunk thiếu/rỗng.")
            print(f"  Dùng --allow-partial để chèn placeholder, --skip-missing để bỏ qua,")
            print(f"  hoặc hoàn thành các chunk thiếu trước khi merge.")
            sys.exit(1)


    # Merge
    result = merge_texts(
        total_chunks, chunk_map, args.format,
        args.allow_partial, args.skip_missing,
    )
    output_file.write_text(result['merged'], encoding='utf-8')

    elapsed = time.time() - start_time

    # Final statistics
    print_header(f"MERGE COMPLETE")
    print(f"  Book: {args.book_name}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Merged: {result['merged_count']}")
    if missing_all:
        print(f"  Missing: {len(missing_all)} (chunk {', '.join(str(x + 1) for x in missing_all[:10])}"
              f"{'...' if len(missing_all) > 10 else ''})")
    print(f"  Total words (source): ~{result['total_words_source']:,}")
    print(f"  Total words (translated): ~{result['total_words_translated']:,}")
    print(f"  Output: {output_file}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"{chr(0x2550) * TERMINAL_WIDTH}")

    if missing_all and args.allow_partial:
        print(f"\n  \u26a0\ufe0f {len(missing_all)} placeholder(s) inserted for missing chunks.")
    elif missing_all and args.skip_missing:
        print(f"\n  \u26a0\ufe0f {len(missing_all)} missing chunk(s) silently skipped.")


if __name__ == '__main__':
    main()
