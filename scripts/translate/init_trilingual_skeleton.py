"""init_trilingual_skeleton.py - Tạo skeleton progress JSON cho bản dịch tam ngữ.

Đọc từng chunk JSON, dùng add_pinyin.process_text để tách câu,
ghi original_text + pinyin_text (1 câu = 1 dòng) vào progress JSON.
translated_text để trống để subagent dịch từng dòng cho khớp alignment.

Usage:
    python scripts/init_trilingual_skeleton.py ^
        --chunks-dir "working\chunks\zuo-yi-ge-you-feng-gu-de-nu-zi" ^
        --progress-dir "working\progress\zuo-yi-ge-you-feng-gu-de-nu-zi"
"""

import os
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding
from add_pinyin import process_text


def main():
    setup_encoding()
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunks-dir', type=Path, required=True)
    parser.add_argument('--progress-dir', type=Path, required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    args.progress_dir.mkdir(parents=True, exist_ok=True)
    chunk_files = sorted(args.chunks_dir.glob('*.json'))
    total = 0
    for cf in chunk_files:
        chunk_data = json.loads(cf.read_text(encoding='utf-8-sig'))
        cid = chunk_data.get('chunk_id')
        if cid is None:
            continue
        source_text = chunk_data.get('text', '')
        entries = process_text(source_text)
        original_lines = [e['original'] for e in entries]
        pinyin_lines = [e['pinyin'] for e in entries]

        out_file = args.progress_dir / f"chunk_{cid:03d}.json"
        if out_file.exists() and not args.force:
            print(f"  \u26a0 skip {out_file.name}: \u0111\u00e3 t\u1ed3n t\u1ea1i (d\u00f9ng --force \u0111\u1ec3 ghi \u0111\u00e8)")
            continue

        progress_data = {
            'chunk_id': cid,
            'total_chunks': chunk_data.get('total_chunks', 0),
            'chapter': chunk_data.get('chapter', ''),
            'source_text': source_text,
            'translated_text': '',
            'word_count_source': chunk_data.get('word_count', 0),
            'word_count_translated': 0,
            'mode': 'trilingual',
            'original_text': '\n'.join(original_lines),
            'pinyin_text': '\n'.join(pinyin_lines),
        }
        out_file.write_text(json.dumps(progress_data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  \u2705 chunk_{cid:03d}.json: {len(original_lines)} c\u00e2u")
        total += 1

    print(f"\nHo\u00e0n t\u1ea5t: {total} skeleton progress \u0111\u00e3 t\u1ea1o t\u1ea1i {args.progress_dir}")


if __name__ == '__main__':
    main()
