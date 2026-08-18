"""Ghi bản dịch chunk vào progress JSON an toàn UTF-8 (tránh pipe PowerShell hỏng dấu).

Cách dùng:
  python scripts/translate/save_translation_file.py --chunk <id> --vi-file <path> \
      --progress-dir working/progress/<slug>
Đọc bản dịch từ vi-file (UTF-8), cập nhật translated_text, word_count_translated,
translated_at vào chunk_<id>.json mà KHÔNG đụng original_text/pinyin_text/heading/ảnh.
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, required=True)
    ap.add_argument("--vi-file", required=True)
    ap.add_argument("--progress-dir", required=True)
    ap.add_argument("--translated-at", default="2026-07-31T00:00:00")
    args = ap.parse_args()

    progress_dir = Path(args.progress_dir)
    pf = progress_dir / f"chunk_{args.chunk:03d}.json"
    if not pf.exists():
        print(f"ERROR: {pf} not found")
        sys.exit(1)

    vi_text = Path(args.vi_file).read_text(encoding="utf-8").strip("\n")

    data = json.loads(pf.read_text(encoding="utf-8"))
    orig_lines = data["original_text"].splitlines()
    vi_lines = vi_text.splitlines()

    if len(orig_lines) != len(vi_lines):
        print(f"ERROR: line mismatch orig={len(orig_lines)} vi={len(vi_lines)}")
        sys.exit(2)

    data["translated_text"] = vi_text
    data["word_count_translated"] = len(vi_text.replace(" ", "").replace("\n", ""))
    data["translated_at"] = args.translated_at

    pf.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OK chunk_{args.chunk:03d}.json updated: {len(vi_lines)} dòng, "
          f"{data['word_count_translated']} chữ")


if __name__ == "__main__":
    main()