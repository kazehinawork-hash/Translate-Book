"""
generate_trilingual.py - Backfill pinyin into already-translated chunk JSONs

Reads source text from chunks_dir, generates pinyin via pypinyin,
adds original_text/pinyin_text fields to existing progress JSON
without overwriting translated_text.

Ví dụ:
    python scripts/generate_trilingual.py ^
        --chunks-dir "working\chunks\mybook" ^
        --progress-dir "working\progress\mybook"

    python scripts/generate_trilingual.py ^
        --chunks-dir "working\chunks\mybook" ^
        --progress-dir "working\progress\mybook" ^
        --dry-run

    python scripts/generate_trilingual.py ^
        --chunks-dir "working\chunks\mybook" ^
        --progress-dir "working\progress\mybook" ^
        --force
"""

import os
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT
from add_pinyin import process_text

HAS_PYPINYIN = True


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Backfill pinyin into already-translated chunk JSONs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--chunks-dir', type=Path, required=True,
                        help='Th\u01b0 m\u1ee5c ch\u1ee9a chunk JSON g\u1ed1c (working/chunks/{book}/)')
    parser.add_argument('--progress-dir', type=Path, required=True,
                        help='Th\u01b0 m\u1ee5c ch\u1ee9a chunk \u0111\u00e3 d\u1ecbch (working/progress/{book}/)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Ch\u1ec9 xem s\u1ebd update nh\u1eefng chunk n\u00e0o, kh\u00f4ng ghi')
    parser.add_argument('--force', action='store_true',
                        help='Ghi \u0111\u00e8 m\u00e0 kh\u00f4ng c\u1ea7n confirm')

    args = parser.parse_args()

    if not HAS_PYPINYIN:
        print("[L\u1ed6I] C\u1ea7n c\u00e0i pypinyin: pip install pypinyin", file=sys.stderr)
        sys.exit(1)

    if not args.chunks_dir.exists():
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y th\u01b0 m\u1ee5c chunks: {args.chunks_dir}", file=sys.stderr)
        sys.exit(1)
    if not args.progress_dir.exists():
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y th\u01b0 m\u1ee5c progress: {args.progress_dir}", file=sys.stderr)
        ans = input("T\u1ea1o th\u01b0 m\u1ee5c progress? (y/N): ").strip().lower()
        if ans == 'y':
            args.progress_dir.mkdir(parents=True, exist_ok=True)
        else:
            sys.exit(1)

    # Read all chunk files from chunks_dir
    chunk_files = sorted(args.chunks_dir.glob('*.json'))
    if not chunk_files:
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y file JSON n\u00e0o trong {args.chunks_dir}", file=sys.stderr)
        sys.exit(1)

    update_count = 0
    skip_count = 0
    error_count = 0

    for cf in chunk_files:
        enc = 'utf-8-sig'
        try:
            chunk_data = json.loads(cf.read_text(encoding=enc))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                chunk_data = json.loads(cf.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"  \u274c {cf.name}: l\u1ed7i \u0111\u1ecdc: {e}", file=sys.stderr)
                error_count += 1
                continue

        cid = chunk_data.get('chunk_id')
        if cid is None:
            print(f"  \u26a0\ufe0f {cf.name}: kh\u00f4ng c\u00f3 chunk_id, b\u1ecf qua")
            skip_count += 1
            continue

        source_text = chunk_data.get('text', '')
        if not source_text.strip():
            print(f"  \u26a0\ufe0f Chunk {cid}: text r\u1ed7ng, b\u1ecf qua")
            skip_count += 1
            continue

        # Generate pinyin
        pinyin_entries = process_text(source_text)
        original_lines = [e['original'] for e in pinyin_entries]
        pinyin_lines = [e['pinyin'] for e in pinyin_entries]
        original_text = '\n'.join(original_lines)
        pinyin_text = '\n'.join(pinyin_lines)

        # Find or create progress file
        progress_file = args.progress_dir / f"chunk_{cid:03d}.json"
        if progress_file.exists():
            try:
                progress_data = json.loads(progress_file.read_text(encoding='utf-8-sig'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                progress_data = {}
        else:
            progress_data = {}

        # Update fields (preserve translated_text)
        progress_data['chunk_id'] = cid
        progress_data['total_chunks'] = progress_data.get('total_chunks', chunk_data.get('total_chunks', 0))
        progress_data['chapter'] = progress_data.get('chapter', chunk_data.get('chapter', ''))
        progress_data['source_text'] = progress_data.get('source_text', source_text)
        progress_data['mode'] = 'trilingual'
        progress_data['original_text'] = original_text
        progress_data['pinyin_text'] = pinyin_text
        if 'translated_text' not in progress_data:
            progress_data['translated_text'] = ''

        if args.dry_run:
            has_translation = bool(progress_data.get('translated_text', '').strip())
            status = '\u2705' if has_translation else '\u274c'
            action_msg = 's\u1ebd \u0111\u01b0\u1ee3c th\u00eam' if not has_translation else '\u0111\u00e3 c\u00f3'
            print(f"  {status} Chunk {cid}: {len(original_lines)} c\u00e2u, original+pinyin {action_msg}")
        else:
            progress_file.write_text(json.dumps(progress_data, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"  \u2705 Chunk {cid}: {len(original_lines)} c\u00e2u, \u0111\u00e3 th\u00eam original_text + pinyin_text")
        update_count += 1

    print(f"\nK\u1ebft qu\u1ea3: {update_count} chunk x\u1eed l\u00fd, {skip_count} b\u1ecf qua, {error_count} l\u1ed7i")
    if args.dry_run:
        print("  (\u0110\u00e2y l\u00e0 dry-run, ch\u01b0a ghi file n\u00e0o)")


if __name__ == '__main__':
    main()
