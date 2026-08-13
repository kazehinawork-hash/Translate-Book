"""
manage_input.py — Tổ chức thư mục input/ theo trạng thái xử lý.

Chia input/ thành 3 thư mục con:
  input/chua-lam/  — file chưa dịch
  input/da-dich/   — đã dịch (có final/vi.md) nhưng chưa tạo audiobook
  input/da-audio/  — đã dịch + đã tạo audiobook (có audiobook/*.mp3)

Chạy sau mỗi pipeline (hoặc tay khi cần) để file input luôn phản ánh
trạng thái sách: nhìn input/ là biết ngay file nào xử lý đến đâu.

Usage:
    python scripts/manage_input.py           # dò output và sắp xếp file input
    python scripts/manage_input.py --check   # chỉ báo cáo, không di chuyển
"""
import os
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input"
BOOKS = ROOT / "output" / "books"
SUBDIRS = {"chua-lam": INPUT / "chua-lam",
           "da-dich": INPUT / "da-dich",
           "da-audio": INPUT / "da-audio"}

# Chuẩn hoá tên file -> slug (bỏ đuôi, viết thường, ký tự -> a-z0-9-)
def normalize(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", stem).strip("-")
    return stem.lower()


# Map thủ công cho file tiếng Trung / tên không khớp chữ Latin với slug.
# (phần đầu = chuỗi con trong tên file, phần sau = slug)
MANUAL_MAP = [
    ("Đắc Nhân Tâm", "dac-nhan-tam"),
    ("且以情深共白头", "qie-yi-qing-shen-gong-bai-tou"),
    ("做一个刚刚好的女子", "zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing"),
    ("做一个有境界的女子", "zuo-yi-ge-you-jing-jie-de-nu-zi"),
    ("做一个有风骨的女子", "zuo-yi-ge-you-feng-gu-de-nu-zi"),
]


def slug_from_file(fname: str, known: dict) -> str | None:
    """Map tên file input -> slug (ưu tiên map thủ công, rồi khớp chữ Latin)."""
    # 0. File có số tập (" 2.", " 3."...) không khớp với sách gốc — coi như chưa làm
    if re.search(r"\s\d+\.(pdf|epub|azw3)$", fname, re.IGNORECASE):
        return None
    # 1. Map thủ công (tên Trung/đặc biệt)
    for key, slug in MANUAL_MAP:
        if key in fname and slug in known:
            return slug
    # 2. Khớp slug theo chữ Latin trong tên file
    fname_lower = fname.lower()
    for slug in known:
        slug_latin = re.sub(r"[^a-z0-9]", "", slug)
        if slug_latin and slug_latin in re.sub(r"[^a-z0-9]", "", fname_lower):
            return slug
    return None


def main() -> None:
    check_only = "--check" in sys.argv

    # 1. Thu thập trạng thái từ output/books/
    #    Thư mục đặt tên theo tên sách gốc; metadata.json ghi {'slug': ...}
    states = {}  # slug -> 'audio' | 'dich' | 'none'
    if BOOKS.is_dir():
        for d in BOOKS.iterdir():
            if not d.is_dir():
                continue
            # slug gốc: từ metadata.json nếu có, fallback tên thư mục
            slug = d.name
            meta = d / "metadata.json"
            if meta.exists():
                try:
                    import json as _json
                    slug = _json.loads(meta.read_text(encoding="utf-8")).get("slug") or slug
                except Exception:
                    pass
            has_final = (d / "final" / "vi.md").exists() or (d / "final" / "tamngu.md").exists()
            audio_dir = d / "audiobook"
            has_audio = audio_dir.is_dir() and any(audio_dir.glob("*.mp3"))
            if has_audio:
                states[slug] = "audio"
            elif has_final:
                states[slug] = "dich"
            else:
                states[slug] = "none"

    # 2. Duyệt file input/
    for sub in SUBDIRS.values():
        sub.mkdir(exist_ok=True)

    moved = {"chua-lam": [], "da-dich": [], "da-audio": []}
    for f in sorted(INPUT.iterdir()):
        if not f.is_file() or f.name in ("README.md",):
            continue
        slug = slug_from_file(f.name, states)
        if slug and slug in states:
            target = "da-audio" if states[slug] == "audio" else "da-dich" if states[slug] == "dich" else "chua-lam"
        else:
            target = "chua-lam"
        dest = SUBDIRS[target] / f.name
        if f.parent == SUBDIRS[target]:
            moved[target].append(f.name)
            continue
        if check_only:
            print(f"  [{target}] {f.name}")
        else:
            shutil.move(str(f), str(dest))
            moved[target].append(f.name)
            print(f"  → {target}: {f.name}")

    # 3. Tóm tắt
    print("\n=== TRẠNG THÁI INPUT ===")
    for sub_name, sub_path in SUBDIRS.items():
        n = len([x for x in sub_path.iterdir() if x.is_file()])
        label = {"chua-lam": "🕒 Chưa làm", "da-dich": "📗 Đã dịch", "da-audio": "🎧 Đã dịch + audio"}[sub_name]
        print(f"  {label}: {n} file")
    if check_only:
        print("\n(--check: chỉ báo cáo, không di chuyển)")


if __name__ == "__main__":
    main()
