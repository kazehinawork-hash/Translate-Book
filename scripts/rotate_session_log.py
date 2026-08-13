"""
rotate_session_log.py — Giữ docs/session_log.md luôn gọn.

Khi file vượt quá ngưỡng (mặc định 100KB), các entry cũ hơn `--keep-months`
(số tháng giữ lại, mặc định 3) được dời sang:
    docs/session_log_archive/<YYYY-MM>.md
theo từng tháng (append vào file tháng tương ứng, giữ thứ tự cũ → mới).

Entry = khối bắt đầu bằng dòng `## YYYY-MM-DD` cho đến entry kế tiếp
(hoặc `## ` bất kỳ / cuối file). File chính giữ các entry GẦN NHẤT (mới).

Usage:
    python scripts/rotate_session_log.py               # xử lý nếu cần (in kết quả)
    python scripts/rotate_session_log.py --check       # chỉ báo cáo, không sửa
    python scripts/rotate_session_log.py --max-kb 200   # đổi ngưỡng
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "session_log.md"
ARCHIVE_DIR = ROOT / "docs" / "session_log_archive"
DEFAULT_MAX_KB = 100
DEFAULT_KEEP_MONTHS = 3

ENTRY_RE = re.compile(r"^## (\d{4})-(\d{2})-\d{2}")


def split_entries(text: str) -> list[tuple[str, str]]:
    """Chia nội dung thành list (date_key, block). date_key='' cho phần đầu (mào đầu)."""
    lines = text.splitlines(keepends=True)
    entries: list[tuple[str, str]] = []
    current_key = ""
    current = []
    for line in lines:
        m = ENTRY_RE.match(line.strip())
        if m:
            if current:
                entries.append((current_key, "".join(current)))
            current_key = f"{m.group(1)}-{m.group(2)}"
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append((current_key, "".join(current)))
    return entries


def main() -> None:
    check_only = "--check" in sys.argv
    max_kb = DEFAULT_MAX_KB
    keep_months = DEFAULT_KEEP_MONTHS
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--max-kb" and i + 1 < len(args):
            max_kb = int(args[i + 1])
        if a == "--keep-months" and i + 1 < len(args):
            keep_months = int(args[i + 1])

    if not LOG.exists():
        print(f"Không thấy {LOG}")
        return

    size_kb = LOG.stat().st_size / 1024
    text = LOG.read_text(encoding="utf-8")
    print(f"session_log.md: {size_kb:.0f} KB ({len(text.splitlines())} dòng)")

    if size_kb <= max_kb:
        print(f"✅ Dưới ngưỡng {max_kb} KB — không cần rotate.")
        return

    # Ngưỡng thời gian: giữ entry có tháng >= cutoff
    cutoff = datetime.now() - timedelta(days=30 * keep_months)
    cutoff_key = f"{cutoff.year}-{cutoff.month:02d}"

    entries = split_entries(text)
    keep = []
    archive: dict[str, list[str]] = {}
    for key, block in entries:
        if key == "":
            # Mào đầu (frontmatter/tiêu đề) luôn giữ
            keep.append((key, block))
        elif key >= cutoff_key:
            keep.append((key, block))
        else:
            archive.setdefault(key, []).append(block)

    if not archive:
        print(f"Không có entry cũ hơn {keep_months} tháng (cutoff {cutoff_key}) — không cần rotate.")
        return

    n_archived = sum(len(v) for v in archive.values())
    print(f"Sẽ dời {n_archived} entry cũ (> {keep_months} tháng) sang archive.")

    if check_only:
        for mkey in sorted(archive):
            print(f"  → {mkey}: {len(archive[mkey])} entry")
        print("(--check: chỉ báo cáo, không sửa)")
        return

    # Ghi archive (append theo tháng)
    ARCHIVE_DIR.mkdir(exist_ok=True)
    for mkey in sorted(archive):
        dest = ARCHIVE_DIR / f"{mkey}.md"
        header = f"# Session Log — tháng {mkey}\n\n" if not dest.exists() else ""
        with dest.open("a", encoding="utf-8") as f:
            f.write(header)
            for block in archive[mkey]:
                f.write(block)
        print(f"  → Đã thêm {len(archive[mkey])} entry vào {dest.name}")

    # Ghi lại file chính (giữ mào đầu + entry gần nhất)
    new_text = "".join(block for _, block in keep)
    tmp = LOG.with_suffix(".md.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(LOG)
    print(f"✅ session_log.md giờ còn {len(keep) - 1} entry, {LOG.stat().st_size / 1024:.0f} KB.")


if __name__ == "__main__":
    main()
