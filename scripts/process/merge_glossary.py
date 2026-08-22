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
  python scripts/process/merge_glossary.py --check-source-conflicts               # phát hiện source conflict cross-book
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


# Từ khoá gợi ý type trong note
_CHAR_HINT = ("nhân vật", "nhân vật", "nhân vật chính", "tên nhân", "người kể", "tác giả", "chồng", "vợ", "bạn", "hàng xóm", "đồng nghiệp", "em", "chị", "anh", "mẹ", "bố", "con", "character", "main char", "author", "protagonist")
_PLACE_HINT = ("địa danh", "thành phố", "quốc gia", "nước", "ngôi làng", "thị trấn", "khu", "phố", "tỉnh", "place", "city", "country", "location")
# Từ Hán thông dụng (không phải tên riêng) — tránh đoán nhầm thành character
_COMMON_HAN = {"女人", "女子", "幸福", "成熟", "独立", "善良", "优雅", "温柔", "坚强", "勇敢", "真诚", "宽容", "感恩", "乐观", "坚韧", "淡定", "从容", "智慧", "自信", "魅力", "气质", "修养", "尊严", "岁月", "婚姻", "平等", "人性", "妥协", "后记", "小三", "法国", "青岛", "风骨", "内心", "蝴蝶效应", "不攀附", "不将就", "不迷茫", "不低头", "不迎合", "不媚俗", "面带微笑", "内心强大", "从容不迫"}
_HAN_NAME_RE = __import__("re").compile(r"^[\u4e00-\u9fff]{2,4}$")


def infer_type(source: str, note: str) -> str:
    """Tự đoán type: character / place / phrase / term dựa trên source + note."""
    src = (source or "").strip()
    note_l = (note or "").lower()
    if not src:
        return "term"
    # 1. Note gợi ý mạnh (nhân vật / địa điểm) — ưu tiên cao nhất
    if any(h in note_l for h in ("nhân vật", "nhân vật", "character", "main char", "protagonist", "tác giả", "author", "người kể", "chồng", "hàng xóm", "đồng nghiệp")):
        return "character"
    if any(h in note_l for h in ("địa danh", "thành phố", "quốc gia", "ngôi làng", "thị trấn", "place", "city", "country", "location", "nước ", "tỉnh")):
        return "place"
    # 2. Note "nhà xuất bản / publisher" → term
    if any(h in note_l for h in ("nhà xuất bản", "publisher", "book title", "tên sách", "publishing")):
        return "term"
    # 3. Tên riêng Hán: 3-4 ký tự (không thuộc từ thông dụng) → character; 2 ký tự chỉ khi có gợi ý bạn/em/chị...
    if _HAN_NAME_RE.match(src) and src not in _COMMON_HAN:
        if len(src) >= 3 or any(h in note_l for h in ("bạn", "em ", "chị", "anh ", "cô", "bà")):
            return "character"
    # 4. Cụm dài / có khoảng trắng → phrase
    if " " in src or len(src) > 12:
        return "phrase"
    return "term"


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
    parser.add_argument("--check-dup", action="store_true", help="Kiểm tra source trùng target khác nhau trong master")
    parser.add_argument("--check", action="store_true", help="Báo cáo master (số dòng, sách, tác giả, thể loại)")
    parser.add_argument("--info", action="store_true", help="Chi tiết master: từng file + số dòng")
    parser.add_argument("--check-source-conflicts", action="store_true",
                        help="Phát hiện cùng 1 source có nhiều target khác nhau cross-book (cần xác nhận bản dịch chuẩn)")
    args = parser.parse_args()

    # ---- --check-dup: phát hiện source trùng target khác nhau ----
    if args.check_dup:
        rows = glossary_lib.load_all()
        from collections import defaultdict
        src_map: dict[str, set[str]] = defaultdict(set)
        for r in rows:
            src = (r.get("source") or "").strip()
            tgt = (r.get("target") or "").strip()
            if src and tgt:
                src_map[src].add(tgt)
        dups = {k: v for k, v in src_map.items() if len(v) > 1}
        if dups:
            print(f"⚠️ Có {len(dups)} source trùng với >1 target (cần chốt bản dịch):")
            for k, v in sorted(dups.items()):
                print(f"  {k}: {sorted(v)}")
            sys.exit(1)
        print(f"✅ Không có source trùng target khác — {len(rows)} thuật ngữ, {len(src_map)} source duy nhất.")
        return

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

    # ---- --check-source-conflicts: phát hiện source conflict cross-book ----
    if args.check_source_conflicts:
        rows = glossary_lib.load_all()
        src_map = {}
        for r in rows:
            src = (r.get('source') or '').strip()
            tgt = (r.get('target') or '').strip()
            if not src or not tgt:
                continue
            key = src.lower()
            src_map.setdefault(key, []).append({
                'src': src,
                'tgt': tgt,
                'book': r.get('book', ''),
                'author': r.get('author', ''),
                'genre': r.get('genre', ''),
            })
        conflicts = {k: v for k, v in src_map.items() if len(set(e['tgt'] for e in v)) > 1}
        if conflicts:
            print(f"\n⚠️ FOUND {len(conflicts)} SOURCE CONFLICTS:")
            print("(Cùng một source nhưng khác target ở các cuốn sách khác nhau)\n")
            for norm_src, data in sorted(conflicts.items()):
                s = data[0]
                tgts = sorted(set(e['tgt'] for e in data))
                print(f"  Source: {s['src']} -> Targets: {', '.join(tgts)}")
                for e in data:
                    p = []
                    if e['book']:
                        p.append(f"book={e['book']}")
                    if e['author']:
                        p.append(f"author={e['author']}")
                    if e['genre']:
                        p.append(f"genre={e['genre']}")
                    meta = ', '.join(p) if p else 'shared'
                    print(f"    - {e['tgt']} [{meta}]")
                print()
            sys.exit(1)
        else:
            print(f"\n✅ OK: No source conflicts found ({len(src_map)} sources, all consistent).")
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
        parser.error("Cần --book (hoặc --check/--info/--normalize/--check-source-conflicts)")

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
            "type": (r.get("type") or "").strip() or infer_type(src, note),
            "note": note,
            "book": args.book,
            "author": args.author or "",
            "genre": args.genre or "",
        })
        existing.add((src, tgt))

    if args.dry_run:
        print(f"(dry-run) Sẽ thêm {len(new_entries)} thuật ngữ mới của cuốn '{args.book}' vào master"
              + (f" [author={args.author}]" if args.author else "") + (f" [genre={args.genre}]" if args.genre else ""))
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
