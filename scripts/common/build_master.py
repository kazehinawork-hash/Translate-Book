"""
build_master.py — Gộp toàn bộ glossary (các file cuốn cũ + genres + authors) vào master.csv.

MỘT LẦN — dùng khi chuyển sang hệ thống master. Sau đó dùng merge_glossary.py để thêm mới.

Nguồn:
  - glossary/<slug>.csv            (cột source,target,notes[,gender]) → book=<slug>
  - glossary/genres/<name>.csv     (source,target,type,note,genre,book) → genre=<name>
  - glossary/authors/<name>.csv    (source,target,type,note,author,book) → author=<name>

Output: glossary/master.csv với cột source,target,type,note,book,author,genre
(giữ nguyên từng dòng gốc — nếu cùng source ở nhiều nơi, giữ cả để filter_for_book chọn đúng).

Usage:
    python scripts/common/build_master.py            # gộp + ghi master.csv (giữ file cũ)
    python scripts/common/build_master.py --info     # chỉ báo cáo, không ghi
    python scripts/common/build_master.py --delete-source   # gộp rồi xóa file cuốn/genres/authors cũ (có backup)
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402
import glossary_lib  # noqa: E402


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "gbk", "big5"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return [dict(r) for r in csv.DictReader(f)]
        except (UnicodeDecodeError, csv.Error):
            continue
    return []


def main() -> None:
    setup_encoding()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--info", action="store_true", help="Chỉ báo cáo số dòng từng nguồn")
    parser.add_argument("--delete-source", action="store_true",
                        help="Sau khi gộp, xóa các file cuốn/genres/authors cũ (KHÔNG xóa _template, backup riêng)")
    args = parser.parse_args()

    master_rows: list[dict] = []
    source_counts: list[tuple[str, int]] = []
    seen: set[tuple[str, str, str]] = set()  # (source, book, author/genre) để tránh trùng chính xác

    # 1. Các file cuốn ở glossary/*.csv (bỏ _template, master)
    for p in sorted(glossary_lib.GLOSSARY_DIR.glob("*.csv")):
        if p.name.startswith("_") or p.name.startswith("master"):
            continue
        rows = read_csv(p)
        source_counts.append((p.name, len(rows)))
        for r in rows:
            source = (r.get("source") or "").strip()
            target = (r.get("target") or "").strip()
            if not source or not target:
                continue
            note = " | ".join(x.strip() for x in [r.get("note", ""), r.get("notes", ""), r.get("gender", "")] if x and x.strip())
            key = (source, target, f"book:{p.stem}")
            if key in seen:
                continue
            seen.add(key)
            master_rows.append({
                "source": source,
                "target": target,
                "type": (r.get("type") or "").strip() or "term",
                "note": note,
                "book": p.stem,
                "author": "",
                "genre": "",
            })

    # 2. genres
    genres_dir = glossary_lib.GLOSSARY_DIR / "genres"
    if genres_dir.exists():
        for p in sorted(genres_dir.glob("*.csv")):
            rows = read_csv(p)
            source_counts.append((f"genres/{p.name}", len(rows)))
            for r in rows:
                source = (r.get("source") or "").strip()
                target = (r.get("target") or "").strip()
                if not source or not target:
                    continue
                key = (source, target, f"genre:{p.stem}")
                if key in seen:
                    continue
                seen.add(key)
                master_rows.append({
                    "source": source,
                    "target": target,
                    "type": (r.get("type") or "").strip() or "term",
                    "note": (r.get("note") or "").strip(),
                    "book": (r.get("book") or "").strip(),
                    "author": "",
                    "genre": p.stem,
                })

    # 3. authors
    authors_dir = glossary_lib.GLOSSARY_DIR / "authors"
    if authors_dir.exists():
        for p in sorted(authors_dir.glob("*.csv")):
            rows = read_csv(p)
            source_counts.append((f"authors/{p.name}", len(rows)))
            for r in rows:
                source = (r.get("source") or "").strip()
                target = (r.get("target") or "").strip()
                if not source or not target:
                    continue
                key = (source, target, f"author:{p.stem}")
                if key in seen:
                    continue
                seen.add(key)
                master_rows.append({
                    "source": source,
                    "target": target,
                    "type": (r.get("type") or "").strip() or "term",
                    "note": (r.get("note") or "").strip(),
                    "book": (r.get("book") or "").strip(),
                    "author": p.stem,
                    "genre": "",
                })

    if args.info:
        print(f"Tổng {len(master_rows)} thuật ngữ sẽ gộp vào master.csv:")
        for name, count in source_counts:
            print(f"  - {name}: {count} dòng")
        return

    # Ghi master.csv
    master_path = glossary_lib.GLOSSARY_DIR / "master.csv"
    master_path.parent.mkdir(parents=True, exist_ok=True)
    with master_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target", "type", "note", "book", "author", "genre"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(master_rows)
    print(f"✅ Đã ghi {len(master_rows)} dòng vào {master_path.name}")

    if args.delete_source:
        # Xóa file cuốn cũ + genres + authors (giữ _template, master)
        deleted = []
        for p in sorted(glossary_lib.GLOSSARY_DIR.glob("*.csv")):
            if p.name.startswith("_") or p.name.startswith("master"):
                continue
            p.unlink()
            deleted.append(p.name)
        for sub in ("genres", "authors"):
            sdir = glossary_lib.GLOSSARY_DIR / sub
            if sdir.exists():
                for p in sorted(sdir.glob("*.csv")):
                    p.unlink()
                    deleted.append(f"{sub}/{p.name}")
        print(f"🗑️ Đã xóa {len(deleted)} file nguồn cũ (backup ở working/glossary_backup_* nếu có):")
        for d in deleted:
            print(f"  - {d}")


if __name__ == "__main__":
    main()
