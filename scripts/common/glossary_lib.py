"""
glossary_lib.py — Thư viện đọc glossary dùng chung cho các script.

Thay thế cách đọc `glossary/<slug>.csv` rời rạc bằng **master CSV**:
  - `glossary/master.csv`          : file gộp toàn bộ (mặc định)
  - `glossary/master_001.csv`, ... : khi master phình to → tự tách thành nhiều file
                                     (quy tắc: master, master_001, master_002, ...)

Mỗi dòng có cột:
  source,target,type,note,book,author,genre
  - `book`   : slug cuốn (rỗng = áp dụng chung)
  - `author` : slug tác giả (rỗng = không thuộc tác giả)
  - `genre`  : slug thể loại (rỗng = không thuộc thể loại)

API:
  - load_all() -> list[dict]                    : đọc toàn bộ master (gộp nhiều file)
  - filter_for_book(rows, slug) -> list[dict]   : lọc thuật ngữ áp dụng cho cuốn slug
      (ưu tiên: mục có book==slug, rồi author/genre khớp, rồi mục chung book rỗng)
  - get_author_of_book(rows, slug) -> str       : tìm author của cuốn (qua cột author của mục có book==slug)
  - get_genre_of_book(rows, slug) -> str        : tìm genre của cuốn
  - master_files() -> list[Path]                : danh sách file master hiện có
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PROJECT_ROOT, setup_encoding  # noqa: E402

GLOSSARY_DIR = PROJECT_ROOT / "glossary"
MASTER_PREFIX = "master"
MASTER_FIRST = GLOSSARY_DIR / "master.csv"
# Ngưỡng tự tách: khi 1 master > MASTER_SPLIT_ROWS dòng, tách phần thừa sang master_001.csv, ...
MASTER_SPLIT_ROWS = 300


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return [dict(r) for r in csv.DictReader(f)]
        except (UnicodeDecodeError, csv.Error):
            continue
    return []


def master_files() -> list[Path]:
    """Danh sách file master theo thứ tự: master.csv, master_001.csv, ..."""
    files = []
    first = MASTER_FIRST
    if first.exists():
        files.append(first)
    for p in sorted(GLOSSARY_DIR.glob(f"{MASTER_PREFIX}_*.csv")):
        files.append(p)
    return files


def load_all() -> list[dict]:
    """Đọc toàn bộ master (gộp nhiều file nếu đã tách)."""
    rows: list[dict] = []
    for f in master_files():
        rows.extend(_read_csv(f))
    return rows


def _normalize_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").strip().lower()).strip("-")


def filter_for_book(rows: list[dict], slug: str) -> list[dict]:
    """Lọc thuật ngữ áp dụng cho cuốn `slug`.

    Ưu tiên:
      1. Mục có book == slug (thuật ngữ riêng của cuốn)
      2. Mục có author/genre khớp với author/genre của cuốn (thuật ngữ chung tác giả/thể loại)
      3. Mục chung (book, author, genre đều rỗng)
    """
    slug_n = _normalize_slug(slug)
    author_of_book = get_author_of_book(rows, slug)
    genre_of_book = get_genre_of_book(rows, slug)

    result: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for r in rows:
        source = (r.get("source") or "").strip()
        target = (r.get("target") or "").strip()
        if not source or not target:
            continue
        book = _normalize_slug(r.get("book") or "")
        author = _normalize_slug(r.get("author") or "")
        genre = _normalize_slug(r.get("genre") or "")

        # Ưu tiên 1: mục riêng của cuốn (book == slug)
        if book == slug_n:
            key = (source, target)
            if key not in seen:
                seen.add(key)
                result.append(r)
            continue

        # Ưu tiên 2: mục cùng tác giả / cùng thể loại với cuốn (kể cả book khác — thuật ngữ chung tác giả/genre)
        if author and author == author_of_book:
            key = (source, target)
            if key not in seen:
                seen.add(key)
                result.append(r)
            continue
        if genre and genre == genre_of_book:
            key = (source, target)
            if key not in seen:
                seen.add(key)
                result.append(r)
            continue

        # Ưu tiên 3: mục chung hoàn toàn (book/author/genre đều rỗng)
        if book == "" and author == "" and genre == "":
            key = (source, target)
            if key not in seen:
                seen.add(key)
                result.append(r)
            continue

    return result


def get_author_of_book(rows: list[dict], slug: str) -> str:
    """Tìm author của cuốn slug — lấy từ cột author của mục có book==slug."""
    slug_n = _normalize_slug(slug)
    for r in rows:
        if _normalize_slug(r.get("book") or "") == slug_n and (r.get("author") or "").strip():
            return _normalize_slug(r.get("author") or "")
    return ""


def get_genre_of_book(rows: list[dict], slug: str) -> str:
    slug_n = _normalize_slug(slug)
    for r in rows:
        if _normalize_slug(r.get("book") or "") == slug_n and (r.get("genre") or "").strip():
            return _normalize_slug(r.get("genre") or "")
    return ""


def split_master_if_needed() -> None:
    """Nếu master.csv phình to (> MASTER_SPLIT_ROWS dòng), tự tách phần thừa sang master_001.csv.

    Chạy sau mỗi lần ghi master. Không mất dữ liệu — chỉ dời dòng.
    """
    if not MASTER_FIRST.exists():
        return
    rows = _read_csv(MASTER_FIRST)
    if len(rows) <= MASTER_SPLIT_ROWS:
        return

    # Dòng đầu (giữ nguyên) + phần thừa dời đi
    keep = rows[:MASTER_SPLIT_ROWS]
    excess = rows[MASTER_SPLIT_ROWS:]

    # Ghi lại master giữ phần đầu
    _write_csv(MASTER_FIRST, keep)

    # Gộp excess vào master_001.csv (hoặc master tiếp theo) — append nếu đã có
    next_idx = 1
    while True:
        target = GLOSSARY_DIR / f"{MASTER_PREFIX}_{next_idx:03d}.csv"
        if not target.exists():
            break
        existing = _read_csv(target)
        if len(existing) + len(excess) > MASTER_SPLIT_ROWS:
            next_idx += 1
            continue
        excess = existing + excess
        break
    _write_csv(target, excess)
    setup_encoding()
    print(f"  [glossary_lib] Tự tách master: giữ {len(keep)} dòng, dời {len(excess)} dòng sang {target.name}")


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


if __name__ == "__main__":
    # CLI nhỏ để test/kiểm tra
    import argparse
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Glossary library CLI (test)")
    parser.add_argument("--book", help="Slug cuốn để lọc")
    parser.add_argument("--list-files", action="store_true", help="Liệt kê file master")
    parser.add_argument("--info", action="store_true", help="Thông tin toàn master")
    args = parser.parse_args()

    if args.list_files:
        for f in master_files():
            print(f"{f.name}: {len(_read_csv(f))} dòng")
    elif args.info:
        rows = load_all()
        print(f"Tổng {len(rows)} thuật ngữ trong {len(master_files())} file master")
        books = sorted({r.get('book', '') for r in rows if r.get('book')})
        authors = sorted({r.get('author', '') for r in rows if r.get('author')})
        genres = sorted({r.get('genre', '') for r in rows if r.get('genre')})
        print(f"  Sách: {books}")
        print(f"  Tác giả: {authors}")
        print(f"  Thể loại: {genres}")
    elif args.book:
        rows = load_all()
        print(f"Book '{args.book}': author='{get_author_of_book(rows, args.book)}' genre='{get_genre_of_book(rows, args.book)}'")
        filtered = filter_for_book(rows, args.book)
        print(f"  {len(filtered)} thuật ngữ áp dụng:")
        for r in filtered[:20]:
            print(f"    {r.get('source')} → {r.get('target')} [{r.get('type')}] (book={r.get('book') or '-'}, author={r.get('author') or '-'}, genre={r.get('genre') or '-'})")
        if len(filtered) > 20:
            print(f"    ... và {len(filtered) - 20} mục nữa")
    else:
        parser.print_help()
