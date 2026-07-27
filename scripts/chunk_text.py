"""
chunk_text.py - Chia file Markdown thành các chunk theo ranh giới logic

Nguyên tắc:
- Ưu tiên ranh giới (heading #, ##, ###; ngắt cảnh; kết thúc chương)
- KHÔNG cắt giữa đoạn văn
- EN: 500-1500 từ/chunk
- ZH: 1500-3000 chữ Hán/chunk
- Hỗ trợ overlap giữa các chunk
- Hỗ trợ manual marker: <!-- CHUNK_BREAK -->

Ví dụ:
    python scripts/chunk_text.py ^
        --input "working\extracted\$slug\raw.md" ^
        --output-dir "working\chunks\$slug" ^
        --min-chars 3000 ^
        --max-chars 8000 ^
        --overlap-chars 200 ^
        --lang en ^
        --respect-headings
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402

# Heading Markdown (rank 1-6)
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# Manual marker
MANUAL_BREAK = '<!-- CHUNK_BREAK -->'

# Ký tự Hán
HAN_REGEX = re.compile(r'[㐀-鿿豈-﫿]')


def dem_so_luong(text: str, lang: str) -> int:
    """Đếm kích thước theo ngôn ngữ (từ cho EN, ký tự Hán cho ZH)."""
    if lang == 'zh':
        return len(HAN_REGEX.findall(text))
    return len(re.findall(r'\b\w+\b', text))


def tach_theo_marker(text: str) -> list[str]:
    """Tách text theo manual marker trước (ưu tiên cao nhất)."""
    if MANUAL_BREAK not in text:
        return [text]
    parts = text.split(MANUAL_BREAK)
    return [p.strip() for p in parts if p.strip()]


def tach_theo_heading(text: str) -> list[tuple[str, str]]:
    """Tách theo heading. Trả về [(heading, body)]."""
    result = []
    current_heading = ''
    current_body = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            if current_body or current_heading:
                result.append((current_heading, '\n'.join(current_body).strip()))
            current_heading = line
            current_body = []
        else:
            current_body.append(line)
    if current_body or current_heading:
        result.append((current_heading, '\n'.join(current_body).strip()))
    return [(h, b) for h, b in result if h or b]


def tach_theo_doan(text: str) -> list[str]:
    """Tách theo đoạn văn (1 hoặc nhiều dòng trống = ranh giới đoạn)."""
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def cat_overlap_an_toan(text: str, target_chars: int, lang: str = 'en') -> str:
    """Cắt overlap an toàn - tìm biên giới câu/từ gần vị trí target.

    Tránh cắt giữa câu (cắt ở '. ' hoặc '\\n\\n' gần nhất trước target).
    """
    if target_chars <= 0 or len(text) <= target_chars:
        return text

    # Cắt tại vị trí target
    cut_pos = len(text) - target_chars
    candidate = text[cut_pos:]

    # Tìm biên giới câu gần nhất SAU cut_pos (trong khoảng +200 ký tự)
    # Ưu tiên: \n\n > . \n > . " > .\n > . " > . 
    boundary_patterns = [
        r'\n\n',           # đoạn
        r'\.\s*\n',        # cuối câu + xuống dòng
        r'\.[\s\"]',       # cuối câu + space/quote
        r'[\u3002\uff01\uff1f]\s*',  # fullwidth 。！？ (cho tiếng Trung)
        r'\s',             # space (EN)
    ]

    for pat in boundary_patterns:
        m = re.search(pat, candidate[:300])
        if m:
            return text[cut_pos + m.end():]

    # Không tìm thấy biên giới → trả về nguyên (cắt tại cut_pos)
    return candidate


def gop_thanh_chunk(
    sections: list[tuple[str, str]],
    min_size: int,
    max_size: int,
    overlap_size: int,
    lang: str,
) -> list[str]:
    """Gộp các đoạn thành chunk theo kích thước min/max."""
    chunks = []
    chunk_hien_tai = ''
    kich_thuoc_hien_tai = 0
    overlap_text = ''

    for heading, body in sections:
        # Tính kích thước heading + body
        doan_text = (heading + '\n' + body).strip() if heading else body
        if not doan_text:
            continue
        doan_size = dem_so_luong(doan_text, lang)

        # Nếu đoạn đơn lẻ đã vượt max_size → tách tiếp theo đoạn nhỏ
        if doan_size > max_size:
            # Flush chunk hiện tại
            if chunk_hien_tai:
                chunks.append(chunk_hien_tai.strip())
                overlap_text = cat_overlap_an_toan(chunk_hien_tai, overlap_size * 2, lang) if overlap_size > 0 else ''
                chunk_hien_tai = ''
                kich_thuoc_hien_tai = 0

            # Tách đoạn lớn thành các đoạn nhỏ hơn
            cac_doan_nho = tach_theo_doan(body)
            for doan in cac_doan_nho:
                doan_full = doan
                doan_size_full = dem_so_luong(doan_full, lang)
                if kich_thuoc_hien_tai + doan_size_full > max_size and chunk_hien_tai:
                    chunks.append(chunk_hien_tai.strip())
                    overlap_text = cat_overlap_an_toan(chunk_hien_tai, overlap_size * 2, lang) if overlap_size > 0 else ''
                    chunk_hien_tai = overlap_text
                    kich_thuoc_hien_tai = dem_so_luong(overlap_text, lang)
                if kich_thuoc_hien_tai == 0:
                    chunk_hien_tai = (heading + '\n' + doan_full).strip() if heading else doan_full
                else:
                    chunk_hien_tai += '\n\n' + doan_full
                kich_thuoc_hien_tai = dem_so_luong(chunk_hien_tai, lang)
            continue

        # Đoạn vừa/không đủ min: thêm vào chunk hiện tại
        if kich_thuoc_hien_tai + doan_size <= max_size:
            if kich_thuoc_hien_tai == 0:
                chunk_hien_tai = doan_text
            else:
                chunk_hien_tai += '\n\n' + doan_text
            kich_thuoc_hien_tai += doan_size
        else:
            # Đoạn mới sẽ vượt max → flush chunk hiện tại
            if chunk_hien_tai:
                chunks.append(chunk_hien_tai.strip())
                overlap_text = cat_overlap_an_toan(chunk_hien_tai, overlap_size * 2, lang) if overlap_size > 0 else ''
                chunk_hien_tai = overlap_text
                kich_thuoc_hien_tai = dem_so_luong(overlap_text, lang)
            chunk_hien_tai += '\n\n' + doan_text if chunk_hien_tai else doan_text
            kich_thuoc_hien_tai += doan_size

    if chunk_hien_tai:
        chunks.append(chunk_hien_tai.strip())

    return chunks


def canh_bao_chunk_cuoi_nho(chunks: list[str], min_size: int, lang: str) -> None:
    """Cảnh báo nếu chunk cuối quá nhỏ (không merge để tránh context leak)."""
    if not chunks:
        return
    last = chunks[-1]
    last_size = dem_so_luong(last, lang)
    if last_size < min_size * 0.5 and len(chunks) > 1:
        print(f"  ⚠️ Chunk cuối ({last_size} đơn vị) < 50% min_size ({min_size}). Có thể do input ngắn hoặc ranh giới không đều.")


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Chia file Markdown thành chunk theo ranh giới logic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File Markdown đầu vào')
    parser.add_argument('--output-dir', type=Path, required=True, help='Thư mục chứa các chunk')
    parser.add_argument('--lang', choices=['en', 'zh'], default='en', help='Ngôn ngữ (en: đếm từ, zh: đếm chữ Hán)')
    parser.add_argument('--min-chars', type=int, default=3000, help='Kích thước tối thiểu/chunk (từ hoặc chữ Hán)')
    parser.add_argument('--max-chars', type=int, default=8000, help='Kích thước tối đa/chunk')
    parser.add_argument('--overlap-chars', type=int, default=200, help='Số ký tự overlap giữa các chunk')
    parser.add_argument('--respect-headings', dest='respect_headings', action='store_true', help='Ưu tiên ranh giới heading #, ##, ### (mặc định: bật)')
    parser.add_argument('--no-respect-headings', dest='respect_headings', action='store_false', help='Không ưu tiên ranh giới heading')
    parser.add_argument('--manual-markers', action='store_true', help='Tách theo manual marker <!-- CHUNK_BREAK --> trước')
    parser.add_argument('--prefix', type=str, default='chunk', help='Tiền tố tên file (mặc định: chunk)')

    parser.set_defaults(respect_headings=True)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    text = args.input.read_text(encoding='utf-8')
    print(f"Đọc: {args.input} ({dem_so_luong(text, args.lang)} đơn vị)")

    # Nếu KHÔNG dùng --manual-markers nhưng text chứa marker → strip (tránh marker rò vào output)
    if not args.manual_markers and MANUAL_BREAK in text:
        dem = text.count(MANUAL_BREAK)
        text = text.replace(MANUAL_BREAK, '')
        print(f"  ⚠️ Tìm thấy {dem} manual marker trong input nhưng KHÔNG dùng --manual-markers → đã strip khỏi text")

    # Bước 1: tách theo manual marker (nếu có)
    if args.manual_markers and MANUAL_BREAK in text:
        marker_parts = tach_theo_marker(text)
        print(f"Tách theo manual marker: {len(marker_parts)} phần")
    else:
        marker_parts = [text]

    # Bước 2: tách theo heading (nếu bật respect_headings)
    if args.respect_headings:
        all_sections = []
        for part in marker_parts:
            all_sections.extend(tach_theo_heading(part))
        print(f"Tách theo heading: {len(all_sections)} section")
    else:
        all_sections = [('', p) for p in marker_parts]

    # Bước 3: gộp thành chunk
    chunks = gop_thanh_chunk(
        all_sections,
        min_size=args.min_chars,
        max_size=args.max_chars,
        overlap_size=args.overlap_chars,
        lang=args.lang,
    )
    print(f"Tạo được {len(chunks)} chunk")

    # Cảnh báo nếu chunk cuối quá nhỏ
    canh_bao_chunk_cuoi_nho(chunks, args.min_chars, args.lang)

    # Bước 4: ghi file
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for i, chunk in enumerate(chunks, 1):
        ten_file = args.output_dir / f"{args.prefix}-{i:03d}.md"
        ten_file.write_text(chunk, encoding='utf-8')
        kich_thuoc = dem_so_luong(chunk, args.lang)
        print(f"  ✓ {ten_file.name} ({kich_thuoc} đơn vị)")

    print(f"\nHoàn thành: {len(chunks)} chunk trong {args.output_dir}")


if __name__ == '__main__':
    main()
