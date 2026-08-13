"""
verify_memory.py — Kiểm tra Memory Bank (docs/STATE.md + docs/session_log.md) đã được cập nhật đầy đủ chưa.

Bù cho điểm yếu "agent tự giác": thay vì tin lời agent, script này đối chiếu
trạng thái thực tế của repo với nội dung memory:

  1. STATE.md có mục "Các cuốn sách" và bảng cập nhật theo `output/books/` (sách mới hoàn tất mà STATE thiếu → cảnh báo).
  2. session_log.md có entry cùng ngày hôm nay? (nếu phiên đang làm việc mà chưa có entry → nhắc).
  3. session_log.md còn đủ gọn (không cần rotate)? (đọc scripts/rotate_session_log.py ngưỡng 100KB).
  4. AGENTS.md có nhắc đọc STATE.md/session_log.md đầu phiên không? (chống mất quy tắc).

Không sửa file — chỉ báo cáo + trả exit code:
  0 = OK, 1 = có cảnh báo (memory chưa đồng bộ / cần rotate), 2 = lỗi nghiêm trọng (thiếu file).

Usage:
    python scripts/verify_memory.py
    python scripts/verify_memory.py --strict     # coi cảnh báo nhỏ (session hôm nay chưa có entry) là fail
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from common._common import setup_encoding, PROJECT_ROOT

STATE = PROJECT_ROOT / "docs" / "STATE.md"
SESSION_LOG = PROJECT_ROOT / "docs" / "session_log.md"
AGENTS = PROJECT_ROOT / "AGENTS.md"
ROTATE_LIMIT_KB = 100
ENTRY_RE = re.compile(r"^##\s+(\d{4})-(\d{2})-(\d{2})", re.MULTILINE)
# Thư mục output không phải sách thật (test/archive) — bỏ qua khi đối chiếu STATE.md
SKIP_OUTPUT_DIRS = {"long-test", "_archive", "samples", "audio_test"}


def check_state(output_books: Path) -> list[str]:
    """STATE.md phải có mục Các cuốn sách + đề cập các slug trong output/books/."""
    warnings: list[str] = []
    if not STATE.exists():
        return [f"❌ Thiếu {STATE.relative_to(PROJECT_ROOT)}"]
    text = STATE.read_text(encoding="utf-8")
    if "Các cuốn sách" not in text:
        warnings.append("❌ STATE.md thiếu mục '📚 Các cuốn sách'")
    if "Đang làm" not in text:
        warnings.append("❌ STATE.md thiếu mục '🔨 Đang làm (hiện tại)'")
    if "Việc còn nợ" not in text and "Còn nợ" not in text:
        warnings.append("❌ STATE.md thiếu mục '⏳ Việc còn nợ / Đề xuất tiếp theo'")
    # Đối chiếu slug trong output/books/ với STATE.md.
    # Thư mục đặt tên theo tên sách gốc; slug gốc nằm trong metadata.json.
    if output_books.exists():
        for d in sorted(output_books.iterdir()):
            if d.is_dir() and d.name not in SKIP_OUTPUT_DIRS:
                slug = d.name
                meta = d / "metadata.json"
                if meta.exists():
                    try:
                        import json as _json
                        slug = _json.loads(meta.read_text(encoding="utf-8")).get("slug") or slug
                    except Exception:
                        pass
                if slug not in text:
                    warnings.append(f"⚠️ Sách '{slug}' có trong output/books/ nhưng STATE.md chưa nhắc tới")
    return warnings


def check_session_log() -> list[str]:
    warnings: list[str] = []
    if not SESSION_LOG.exists():
        return [f"❌ Thiếu {SESSION_LOG.relative_to(PROJECT_ROOT)}"]
    text = SESSION_LOG.read_text(encoding="utf-8")
    entries = ENTRY_RE.findall(text)
    if not entries:
        return ["❌ session_log.md không có entry nào (thiếu '## YYYY-MM-DD')"]
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in text:
        warnings.append(f"⚠️ session_log.md chưa có entry hôm nay ({today}) — nếu phiên đang làm, nhớ ghi cuối phiên")
    # Entry mới nhất phải đủ các mục con
    latest_block = ""
    for m in ENTRY_RE.finditer(text):
        latest_block = text[m.start():]
    if "Đã làm" not in latest_block or "Git" not in latest_block:
        warnings.append("⚠️ Entry mới nhất của session_log chưa đủ mục 'Đã làm'/'Git'")
    # Kiểm tra kích thước (rotate)
    size_kb = SESSION_LOG.stat().st_size / 1024
    if size_kb > ROTATE_LIMIT_KB:
        warnings.append(f"⚠️ session_log.md đã {size_kb:.0f} KB (> {ROTATE_LIMIT_KB} KB) — nên chạy scripts/rotate_session_log.py")
    return warnings


def check_agents() -> list[str]:
    warnings: list[str] = []
    if not AGENTS.exists():
        return [f"❌ Thiếu {AGENTS.relative_to(PROJECT_ROOT)}"]
    text = AGENTS.read_text(encoding="utf-8")
    if "STATE.md" not in text or "session_log" not in text:
        warnings.append("⚠️ AGENTS.md không nhắc đọc STATE.md/session_log đầu phiên")
    return warnings


def main() -> None:
    setup_encoding()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true", help="Coi cảnh báo nhỏ (chưa có entry hôm nay) là fail")
    args = parser.parse_args()

    output_books = PROJECT_ROOT / "output" / "books"
    all_warnings: list[str] = []
    all_warnings += check_state(output_books)
    all_warnings += check_session_log()
    all_warnings += check_agents()

    if all_warnings:
        print("📋 KIỂM TRA MEMORY BANK — phát hiện vấn đề:")
        for w in all_warnings:
            print(f"  {w}")
        severe = [w for w in all_warnings if w.startswith("❌")]
        minor = [w for w in all_warnings if w.startswith("⚠️")]
        if severe:
            print(f"\nKết luận: {len(severe)} lỗi nghiêm trọng + {len(minor)} cảnh báo. Cần sửa.")
            sys.exit(2)
        if args.strict and minor:
            print(f"\nKết luận (strict): {len(minor)} cảnh báo — coi là fail.")
            sys.exit(1)
        print(f"\nKết luận: {len(minor)} cảnh báo nhỏ (không chặn).")
        sys.exit(1)
    print("✅ Memory Bank đồng bộ: STATE.md + session_log.md + AGENTS.md đều ổn.")
    sys.exit(0)


if __name__ == "__main__":
    main()
