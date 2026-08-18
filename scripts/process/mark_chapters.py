"""Tách chương từ raw.md OCR (sách scan) — đánh dấu ## Chương N và XÓA ## Trang N.

Dùng cho sách OCR (MinerU/PaddleOCR): raw.md có 320+ khối '## Trang N' rất rác khi đọc.
Script dùng MỤC LỤC trong sách (tên chương + số trang) làm danh sách tham chiếu:
1. Tìm trang mục lục (dòng '目录').
2. Trích tên chương: chỉ dòng có dạng '<tên Hán> + <số trang>' (vd '女人的小心思006', '佳肴和白米饭117').
3. Quét raw.md: khối '## Trang N' mà dòng đầu khớp CHÍNH XÁC tên chương → thay bằng '## Chương N: <tên>'.
4. XÓA toàn bộ '## Trang N' còn lại (không cần trang gốc khi đọc).

Usage: python scripts/process/mark_chapters.py --input <raw.md> [--output <raw.md>]
"""
import sys, re, os, argparse
sys.stdout.reconfigure(encoding="utf-8")


def extract_chapters(toc_region: str) -> list:
    """Trích tên chương từ vùng mục lục: dòng '<tên Hán> + số trang'."""
    chapters = []
    for line in toc_region.split("\n"):
        l = line.strip()
        if not l or l.startswith("## ") or l in ("目录", "前言/自序"):
            continue
        # Pattern: tên Hán kết thúc bằng số trang (có thể cách hoặc dính): 'name006', 'name 016', 'name117'
        m = re.match(r"^(.{2,}?)[\s]*(\d{1,4})\s*$", l)
        if m:
            name = m.group(1).strip()
            if re.search(r"[\u4e00-\u9fff]", name) and len(name) >= 2:
                chapters.append(name)
    # Dedupe giữ thứ tự
    seen = set()
    out = []
    for c in chapters:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def mark_chapters(text: str, chapters: list) -> tuple:
    """Thay '## Trang N' có dòng đầu khớp tên chương bằng '## Chương N: tên'; xóa '## Trang N' còn lại."""
    lines = text.split("\n")
    result = []
    chapter_idx = 0
    matched = 0
    removed = 0
    i = 0
    chapter_set = set(chapters)  # tra nhanh

    while i < len(lines):
        line = lines[i]
        m = re.match(r"^## Trang (\d+)$", line.strip())
        if m:
            # Tìm dòng đầu không trống trong khối
            j = i + 1
            first = None
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                first = lines[j].strip()
            if first and first in chapter_set:
                chapter_idx += 1
                result.append(f"## Chương {chapter_idx}: {first}")
                matched += 1
                # Bỏ dòng '## Trang N' + dòng trống theo sau + dòng tiêu đề (đã thành heading)
                i = j  # nhảy tới dòng tiêu đề
                # Bỏ dòng tiêu đề (first) + dòng trống sau nó
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                continue
            else:
                removed += 1
                # Xóa dòng '## Trang N' nhưng giữ dòng trống phân cách (nếu có)
                i += 1
                continue
        else:
            result.append(line)
        i += 1

    return "\n".join(result), matched, removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None, help="Mặc định ghi đè input")
    args = parser.parse_args()

    text = open(args.input, encoding="utf-8").read()

    # 1. Tìm mục lục
    toc_start = text.find("目录")
    if toc_start < 0:
        print("⚠️ Không tìm thấy mục lục — bỏ qua.")
        return
    # Vùng mục lục: từ '目录' đến '前言' (kết thúc mục lục, bắt đầu nội dung)
    toc_end_m = re.search(r"\n\n前言", text[toc_start:])
    toc_region = text[toc_start:toc_start + toc_end_m.start()] if toc_end_m else text[toc_start:toc_start + 6000]

    chapters = extract_chapters(toc_region)
    print(f"Trích {len(chapters)} tên chương từ mục lục")

    out_text, matched, removed = mark_chapters(text, chapters)
    print(f"Đánh dấu {matched} chương, xóa {removed} dòng '## Trang N'")

    dest = args.output or args.input
    open(dest, "w", encoding="utf-8").write(out_text)
    print(f"Đã ghi: {dest} ({len(out_text)} ký tự)")


if __name__ == "__main__":
    main()
