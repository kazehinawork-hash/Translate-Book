"""
epub_extract.py - Trích xuất EPUB sang Markdown

Dùng cho file EPUB (MinerU không hỗ trợ EPUB).
ebooklib đọc EPUB, beautifulsoup4 parse HTML, markdownify convert sang Markdown
(giữ heading, list, table, bold/italic - quan trọng cho chunk_text --respect-headings).

Ví dụ:
    python scripts/epub_extract.py ^
        --input "input\ten-sach.epub" ^
        --output "working\extracted\$slug\raw.md"
        --no-include-metadata
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    HAS_EPUBLIB = True
except ImportError:
    HAS_EPUBLIB = False

try:
    from markdownify import markdownify as md_convert
    HAS_MARKDOWNIFY = True
except ImportError:
    HAS_MARKDOWNIFY = False

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None


# NEW: Kiểm tra DRM trong file EPUB
def kiem_tra_drm(epub_path: Path) -> None:
    """Kiểm tra file EPUB có chứa DRM không."""
    drm_files = {'META-INF/encryption.xml', 'META-INF/rights.xml'}
    try:
        with zipfile.ZipFile(str(epub_path), 'r') as z:
            names = set(z.namelist())
            found = drm_files & names
            if found:
                print(f"[LỖI] File EPUB có DRM! Phát hiện: {', '.join(sorted(found))}", file=sys.stderr)
                print("        EPUB có DRM không thể trích xuất trực tiếp.", file=sys.stderr)
                print("        Gợi ý: Dùng DeDRM tools (https://github.com/apprenticeharper/DeDRM_tools)", file=sys.stderr)
                print("        để loại bỏ DRM trước.", file=sys.stderr)
                sys.exit(1)
    except (zipfile.BadZipFile, Exception) as e:
        print(f"[CẢNH BÁO] Không thể kiểm tra DRM: {e}", file=sys.stderr)


# Bỏ qua các thẻ không cần nội dung
SKIP_TAGS = {'script', 'style', 'nav', 'header', 'footer', 'aside', 'form'}


def html_to_markdown(html_content: str) -> str:
    """Convert HTML sang Markdown bằng markdownify (giữ heading, list, table)."""
    if not HAS_MARKDOWNIFY:
        raise ImportError(
            "Cần cài markdownify: pip install markdownify"
        )

    soup = BeautifulSoup(html_content, 'html.parser')

    # Bỏ các thẻ không cần nội dung
    for tag in soup.find_all(SKIP_TAGS):
        tag.decompose()

    # markdownify xử lý heading, list, table, bold/italic, blockquote chuẩn xác
    text = md_convert(
        str(soup),
        heading_style='ATX',          # #, ##, ### (giúp chunk_text --respect-headings hoạt động)
        bullets='-',                  # - thay vì *
        strip=['a'],                  # bỏ <a> tag nhưng giữ text
    )

    # Làm sạch: gộp nhiều dòng trống, strip trailing whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(line.rstrip() for line in text.splitlines())
    return text.strip()


def lay_text_sach(epub_path: Path) -> tuple[list[dict], dict]:
    """Đọc EPUB, trả về (list_chapter, metadata)."""
    if not HAS_EPUBLIB:
        print("[LỖI] Cần cài ebooklib + beautifulsoup4:", file=sys.stderr)
        print("        pip install ebooklib beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    book = epub.read_epub(str(epub_path))
    metadata = {
        'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown',
        'author': ', '.join(a[0] for a in book.get_metadata('DC', 'creator')) or 'Unknown',
        'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else 'Unknown',
    }

    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode('utf-8', errors='ignore')
        try:
            md_text = html_to_markdown(content)
        except ImportError as e:
            print(f"[LỖI] {e}", file=sys.stderr)
            sys.exit(1)
        if md_text:
            chapters.append({
                'id': item.get_id(),
                'name': item.get_name(),
                'content': md_text,
            })

    return chapters, metadata


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Trích xuất EPUB sang Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File EPUB đầu vào')
    parser.add_argument('--output', type=Path, required=True, help='File Markdown đầu ra')
    # P2 fix: dùng boolean pair để --no-include-metadata có tác dụng thật
    parser.add_argument('--include-metadata', dest='include_metadata', action='store_true',
                        help='Thêm metadata ở đầu file (mặc định: bật)')
    parser.add_argument('--no-include-metadata', dest='include_metadata', action='store_false',
                        help='Không thêm metadata ở đầu file')
    parser.set_defaults(include_metadata=True)

    args = parser.parse_args()

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    kiem_tra_drm(args.input)

    print(f"Đọc: {args.input}")
    chapters, metadata = lay_text_sach(args.input)
    print(f"  Tác giả: {metadata['author']}")
    print(f"  Tiêu đề: {metadata['title']}")
    print(f"  Số chương/mục: {len(chapters)}")

    # Ghép các chương
    parts = []
    if args.include_metadata:
        parts.append(f"# {metadata['title']}\n")
        parts.append(f"**Tác giả**: {metadata['author']}  ")
        parts.append(f"**Ngôn ngữ gốc**: {metadata['language']}  ")
        parts.append(f"**Số chương (EPUB items)**: {len(chapters)}\n")
        parts.append("---\n")

    for i, ch in enumerate(chapters, 1):
        parts.append(f"\n## [{i}] {ch['name']}\n")
        parts.append(ch['content'])
        parts.append("\n---\n")

    noi_dung = '\n'.join(parts)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(noi_dung, encoding='utf-8')
    print(f"✓ Đã ghi: {args.output}")
    print(f"  Kích thước: {len(noi_dung):,} ký tự")


if __name__ == '__main__':
    main()
