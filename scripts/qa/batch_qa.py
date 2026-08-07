"""Kiểm tra nhanh progress chunk trước khi hoàn tất batch Agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ERROR_MARKERS = ("---SKIP---", "---BACK---", "---EXIT---")


def check_chunk(data: dict) -> list[str]:
    errors = []
    translated = (data.get("translated_text") or "").strip()
    if not translated:
        return ["translated_text rỗng"]
    if any(marker in translated for marker in ERROR_MARKERS):
        errors.append("còn marker điều khiển Agent")
    if data.get("mode") == "trilingual":
        originals = [line for line in (data.get("original_text") or "").splitlines() if line.strip()]
        pinyin = [line for line in (data.get("pinyin_text") or "").splitlines() if line.strip()]
        translations = [line for line in translated.splitlines() if line.strip()]
        if len(originals) != len(pinyin) or len(originals) != len(translations):
            errors.append(
                f"lệch dòng gốc={len(originals)}, pinyin={len(pinyin)}, dịch={len(translations)}"
            )
    return errors


def check_progress(progress_dir: Path, chunk_ids: list[int] | None = None) -> dict:
    ids = chunk_ids or sorted(
        int(path.stem.split("_")[-1])
        for path in progress_dir.glob("chunk_*.json")
        if path.stem.split("_")[-1].isdigit()
    )
    errors = {}
    for cid in ids:
        path = progress_dir / f"chunk_{cid:03d}.json"
        if not path.exists():
            errors[str(cid)] = ["không tìm thấy progress JSON"]
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            chunk_errors = check_chunk(data)
            if chunk_errors:
                errors[str(cid)] = chunk_errors
        except (OSError, json.JSONDecodeError) as exc:
            errors[str(cid)] = [f"không đọc được JSON: {exc}"]
    return {"checked": len(ids), "errors": errors, "ok": not errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="QA nhanh progress batch dịch")
    parser.add_argument("--progress-dir", type=Path, required=True)
    parser.add_argument("--chunk-id", type=int, action="append")
    args = parser.parse_args()
    result = check_progress(args.progress_dir, args.chunk_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
