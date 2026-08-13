"""
merge_glossary.py — Gộp glossary cuốn sách vào master.csv (1 file trung tâm).

Thay thế mô hình nhiều file: giờ chỉ có `glossary/master.csv` (và master_001.csv, ... khi phình).
Mỗi dòng có cột: source,target,type,note,book,author,genre.

Cách dùng khi dịch sách mới:
  1. Agent tạo/tìm `glossary/<slug>.csv` (danh sách thuật ngữ cuốn mới).
  2. Chạy lệnh này để gộp vào master:
     python scripts/process/merge_glossary.py --book <slug> --author <author> [--genre <genre>]
     → các thuật ngữ của cuốn (chưa có trong master) được thêm vào master với cột book=<slug>, author=..., genre=...
     → KHÔNG đè mục đã có (so theo source+target+book).
  3. Nếu cuốn thuộc tác giả/thể loại đã có trong master, các thuật ngữ chung đó sẽ tự áp dụng
     khi QA/dịch (glossary_lib.filter_for_book).

Chế độ khác:
  python scripts/process/merge_glossary.py --book <slug> --author <a> --dry-run   # chỉ báo cáo
  python scripts/process/merge_glossary.py --normalize                            # dedupe toàn master
  python scripts/process/merge_glossary.py --check                                # báo cáo master
  python scripts/process/merge_glossary.py --info                                 # chi tiết master
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from common._common import setup_encoding, PROJECT_ROOT  # noqa: E402
from common import glossary_lib  # noqa: E402


def _write_master(rows: list[dict]) -> None:
    """Ghi toàn bộ vào master.csv (ghi file tạm rồi replace), rồi tự tách nếu phình."""
    path = glossary_lib.MASTER_FIRST
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    fields = ["source", "target", "type", "note", "book", "author", "genre"]
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)
    glossary_lib.split_master_if_needed()


def main() -> None:
    setup_encoding()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--book", help="Slug cuốn sách cần gộp glossary vào master")
    parser.add_argument("--author", help="Tác giả (VD: van-tinh) — gán cho các mục mới của cuốn")
    parser.add_argument("--genre", help="Thể loại (VD: tien-hiep) — gán cho các mục mới của cuốn")
    parser.add_argument("--books-dir", type=Path, default=PROJECT_ROOT / "glossary",
                        help="Thư mục chứa glossary cuốn tạm (mặc định: glossary/)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ báo cáo sẽ thêm gì, không ghi")
    parser.add_argument("--normalize", action="store_true", help="Dedupe toàn bộ master.csv")
    parser.add_argument("--check", action="store_true", help="Báo cáo master (số dòng, sách, tác giả, thể loại)")
    parser.add_argument("--info", action="store_true", help="Chi tiết master: từng file + số dòng")
    args = parser.parse_args()

    # ---- --check / --info: báo cáo master ----
    if args.check or args.info:
        rows = glossary_lib.load_all()
        files = glossary_lib.master_files()
        print(f"Master: {len(files)} file, tổng {len(rows)} thuật ngữ")
        books = sorted({r.get('book', '') for r in rows if r.get('book')})
        authors = sorted({r.get('author', '') for r in rows if r.get('author')})
        genres = sorted({r.get('genre', '') for r in rows if r.get('genre')})
        print(f"  Sách: {books}")
        print(f"  Tác giả: {authors}")
        print(f"  Thể loại: {genres}")
        if args.info:
            for f in files:
                print(f"  - {f.name}: {len(glossary_lib._read_csv(f))} dòng")
        return

    # ---- --normalize: dedupe toàn master ----
    if args.normalize:
        rows = glossary_lib.load_all()
        before = len(rows)
        seen: set[tuple[str, str]] = set()
        deduped: list[dict] = []
        for r in rows:
            src = (r.get("source") or "").strip()
            tgt = (r.get("target") or "").strip()
            if not src or not tgt:
                continue
            key = (src, tgt)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)
        _write_master(deduped)
        print(f"✅ Normalize master: {before} → {len(deduped)} dòng (bỏ {before - len(deduped)} trùng)")
        return

    # ---- Gộp cuốn vào master ----
    if not args.book:
        parser.error("Cần --book (hoặc --check/--info/--normalize)")

    book_path = args.books_dir / f"{args.book}.csv"
    if not book_path.exists():
        print(f"⚠️ Không tìm thấy glossary cuốn: {book_path}")
        print("   Tạo file này trước (generate_glossary.py) hoặc truyền --books-dir đúng.")
        return

    # Đọc glossary cuốn (nhiều encoding)
    book_rows = []
    for enc in ("utf-8-sig", "utf-8", "gbk", "big5"):
        try:
            with open(book_path, "r", encoding=enc, newline="") as f:
                book_rows = [dict(r) for r in csv.DictReader(f)]
            break
        except (UnicodeDecodeError, csv.Error):
            continue
    if not book_rows:
        print(f"⚠️ Không đọc được {book_path}")
        return

    master = glossary_lib.load_all()
    # Tập hợp (source, target) đã có trong master cho cuốn này
    existing = {(r.get("source", "").strip(), r.get("target", "").strip()) for r in master if r.get("book", "").strip() == args.book}

    new_entries = []
    for r in book_rows:
        src = (r.get("source") or "").strip()
        tgt = (r.get("target") or "").strip()
        if not src or not tgt:
            continue
        if (src, tgt) in existing:
            continue
        note = " | ".join(x.strip() for x in [r.get("note", ""), r.get("notes", ""), r.get("gender", "")] if x and x.strip())
        new_entries.append({
            "source": src,
            "target": tgt,
            "type": (r.get("type") or "").strip() or "term",
            "note": note,
            "book": args.book,
            "author": args.author or "",
            "genre": args.genre or "",
        })
        existing.add((src, tgt))

    if args.dry_run:
        print(f"(dry-run) Sẽ thêm {len(new_entries)} thuật ngữ mới của cuốn '{args.book}' vào master"
              + (f" [author={args.author}]" if args.author else "") + (f" [genre={args.genre}]" if args.genre else "") + ":")
        for e in new_entries[:20]:
            print(f"  - {e['source']} → {e['target']}")
        if len(new_entries) > 20:
            print(f"  ... và {len(new_entries) - 20} mục nữa")
        return

    if not new_entries:
        print(f"ℹ️ Không có thuật ngữ mới — cuốn '{args.book}' đã đồng bộ với master.")
        return

    _write_master(master + new_entries)
    print(f"✅ Đã thêm {len(new_entries)} thuật ngữ của cuốn '{args.book}' vào master.csv"
          + (f" [author={args.author}]" if args.author else "") + (f" [genre={args.genre}]" if args.genre else ""))


if __name__ == "__main__":
    main()
