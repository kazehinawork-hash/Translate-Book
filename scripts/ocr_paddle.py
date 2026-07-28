"""
ocr_paddle.py - OCR bằng PaddleOCR (backup cho MinerU)

Dùng khi MinerU xử lý kém. PaddleOCR có thể cho kết quả tốt hơn với
một số loại scan cụ thể.

Hỗ trợ:
- PDF scan
- Ảnh (PNG, JPG, ...)
- DOCX có ảnh

Ví dụ:
    python scripts/ocr_paddle.py ^
        --input "input\file-scan.pdf" ^
        --output "working\extracted\$slug\raw-paddle.md" ^
        --lang ch_sim+en
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from paddleocr import PaddleOCR
    HAS_PADDLEOCR = True
except ImportError:
    HAS_PADDLEOCR = False

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402


# Mapping ngôn ngữ phổ biến
LANG_MAP = {
    'ch_sim': 'Chinese (Simplified)',
    'ch_tra': 'Chinese (Traditional)',
    'en': 'English',
    'vi': 'Vietnamese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'fr': 'French',
    'de': 'German',
}


def ocr_anh(ocr_engine, image_path: Path, lang: str) -> str:
    """OCR 1 ảnh, trả về text Markdown."""
    result = ocr_engine.ocr(str(image_path), cls=True)
    if not result or not result[0]:
        return ''
    lines = []
    for line in result[0]:
        if line and len(line) >= 2:
            text = line[1][0]  # (text, confidence)
            if text:
                lines.append(text)
    return '\n\n'.join(lines)


# === NEW: Dùng pdf2image + tempfile để quản lý ảnh tạm an toàn ===
def chuyen_pdf_thanh_anh(pdf_path: Path, dpi: int = 200, output_dir: Path | None = None) -> list[Path]:
    """Chuyển PDF thành ảnh PNG để OCR.
    
    Args:
        pdf_path: Đường dẫn file PDF
        dpi: Độ phân giải (mặc định 200)
        output_dir: Thư mục lưu ảnh tạm (None = tạo temp dir mới)
    
    Returns:
        list[Path]: Danh sách đường dẫn ảnh
    """
    from pdf2image import convert_from_path
    
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix='ocr_pdf_'))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    images = convert_from_path(str(pdf_path), dpi=dpi)
    image_paths = []
    
    for i, img in enumerate(images, 1):
        img_path = output_dir / f"{pdf_path.stem}_page_{i:03d}.png"
        img.save(str(img_path), 'PNG')
        image_paths.append(img_path)
    
    return image_paths


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="OCR bằng PaddleOCR (backup cho MinerU)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File PDF scan / DOCX / ảnh')
    parser.add_argument('--output', type=Path, required=True, help='File Markdown đầu ra')
    parser.add_argument('--lang', type=str, default='ch_sim+en',
                        help='Ngôn ngữ (vd: ch_sim+en, en, ch_sim, vi). Mặc định: ch_sim+en')
    parser.add_argument('--dpi', type=int, default=200, help='DPI khi convert PDF sang ảnh (mặc định 200)')
    parser.add_argument('--use-gpu', dest='use_gpu', action='store_true', help='Dùng GPU (mặc định: CPU)')

    args = parser.parse_args()

    if not HAS_PADDLEOCR:
        print("[LỖI] Chưa cài paddleocr + paddlepaddle.", file=sys.stderr)
        print("        Cài bằng:", file=sys.stderr)
        print("        pip install paddleocr paddlepaddle", file=sys.stderr)
        sys.exit(1)

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Đọc: {args.input}")
    print(f"Ngôn ngữ: {args.lang}")
    print(f"Sử dụng {'GPU' if args.use_gpu else 'CPU'}")

    # Map ngôn ngữ user-friendly → code PaddleOCR chấp nhận
    PADDLE_LANG_MAP = {
        'ch_sim': 'ch',
        'ch_tra': 'chinese_cht',
        'chinese_cht': 'chinese_cht',
        'ch': 'ch',
        'en': 'en',
        'vi': 'vi',
        'ja': 'japan',
        'ko': 'korean',
        'fr': 'fr',
        'de': 'german',
    }

    # PaddleOCR không hỗ trợ 'ch_sim+en' (đa ngôn ngữ) - lấy phần đầu
    raw_lang = args.lang.split('+')[0] if '+' in args.lang else args.lang
    paddle_lang = PADDLE_LANG_MAP.get(raw_lang, raw_lang)
    print(f"  PaddleOCR lang: {paddle_lang} (từ '{args.lang}')")

    # Khởi tạo PaddleOCR
    use_angle_cls = True
    ocr_engine = PaddleOCR(
        use_angle_cls=use_angle_cls,
        lang=paddle_lang,
        use_gpu=args.use_gpu,
        show_log=False,
    )
    print("✓ PaddleOCR đã khởi tạo")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    import shutil

    # === NEW: Tạo temp dir an toàn + try/finally cleanup ===
    temp_dir = tempfile.mkdtemp(prefix='ocr_paddle_')
    temp_path = Path(temp_dir)

    try:
        # Xử lý theo loại file
        if args.input.suffix.lower() == '.pdf':
            print("Chuyển PDF sang ảnh...")
            image_paths = chuyen_pdf_thanh_anh(args.input, dpi=args.dpi, output_dir=temp_path)
            print(f"  {len(image_paths)} trang")

            all_text = []
            for i, img_path in enumerate(image_paths, 1):
                if console:
                    console.print(f"  [dim]OCR trang {i}/{len(image_paths)}...[/dim]")
                else:
                    print(f"  OCR trang {i}/{len(image_paths)}...")
                text = ocr_anh(ocr_engine, img_path, args.lang)
                all_text.append(f"\n## Trang {i}\n\n{text}\n")

            noi_dung = '\n---\n'.join(all_text)
    finally:
        # LUÔN LUÔN cleanup temp dir, kể cả khi crash
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
    elif args.input.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}:
        noi_dung = ocr_anh(ocr_engine, args.input, args.lang)
    elif args.input.suffix.lower() in {'.docx', '.doc'}:
        print("[CẢNH BÁO] DOCX: PaddleOCR chỉ OCR ảnh, không trích text. Dùng python-docx trước.")
        sys.exit(1)
    else:
        print(f"[LỖI] Định dạng không hỗ trợ: {args.input.suffix}", file=sys.stderr)
        sys.exit(1)

    args.output.write_text(noi_dung, encoding='utf-8')
    print(f"\n✓ Đã ghi: {args.output}")
    print(f"  Kích thước: {len(noi_dung):,} ký tự")


if __name__ == '__main__':
    main()
