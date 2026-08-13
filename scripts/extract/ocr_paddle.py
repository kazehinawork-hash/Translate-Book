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

import os
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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding  # noqa: E402


# === NEW: Tự dùng venv OCR riêng (working/venv-ocr) ===
# PaddleOCR 3.x + paddle GPU yêu cầu venv riêng (không có torch — tránh xung đột
# cuDNN DLL với torch CUDA trong .venv chính dùng cho MinerU).
# Nếu env hiện tại thiếu paddleocr nhưng venv-ocr có sẵn → relaunch bằng nó.
def _relaunch_via_ocr_venv() -> None:
    """Nếu đang chạy bằng python khác (thiếu paddleocr) nhưng có venv-ocr → chạy lại bằng venv-ocr."""
    if HAS_PADDLEOCR:
        return
    project_root = Path(__file__).resolve().parents[2]
    ocr_venv_py = project_root / 'working' / 'venv-ocr' / 'Scripts' / 'python.exe'
    if not ocr_venv_py.exists():
        return  # không có venv-ocr → để main() báo lỗi thiếu paddleocr
    try:
        from paddleocr import PaddleOCR  # noqa: F401
        return  # env hiện tại thực ra có paddleocr (import muộn thành công)
    except ImportError:
        pass
    print(f"Info: chay lai bang venv OCR: {ocr_venv_py}")
    cmd = [str(ocr_venv_py), str(Path(__file__).resolve())] + sys.argv[1:]
    try:
        import subprocess
        proc = subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        sys.exit(proc.returncode)
    except Exception as e:
        print(f"[WARN] Khong chay lai bang venv-ocr duoc ({e}) - tiep tuc bang env hien tai.", file=sys.stderr)


_relaunch_via_ocr_venv()


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


def detect_paddle_gpu() -> tuple[bool, str]:
    """Kiểm tra PaddlePaddle có hỗ trợ GPU không.
    
    Returns:
        tuple: (has_gpu, reason)
    """
    try:
        import paddle
        cuda_compiled = paddle.device.is_compiled_with_cuda()
        device_count = paddle.device.cuda.device_count()
        if cuda_compiled and device_count > 0:
            return True, ""
        elif cuda_compiled and device_count == 0:
            return False, "paddle được build với CUDA nhưng không có GPU khả dụng"
        else:
            return False, "paddle bản CPU-only (không compiled với CUDA)"
    except ImportError:
        return False, "chưa cài paddlepaddle"
    except Exception as e:
        return False, f"lỗi khi kiểm tra paddle GPU: {e}"


def ocr_anh(ocr_engine, image_path: Path, lang: str) -> str:
    """OCR 1 ảnh, trả về text Markdown.

    API PaddleOCR 3.x: ``ocr_engine.predict(path)`` trả list dict,
    mỗi dict có key ``rec_texts`` (list các dòng chữ nhận diện).
    """
    try:
        result = ocr_engine.predict(str(image_path))
    except AttributeError:
        # Fallback API 2.x cũ (use_gpu, result[0] là list line)
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
    if not result:
        return ''
    lines = []
    for page in result:
        if not isinstance(page, dict):
            continue
        for text in page.get('rec_texts') or []:
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
    # === NEW: --device flag thay thế --use-gpu ===
    parser.add_argument('--device', type=str, default='auto', choices=['auto', 'gpu', 'cpu'],
                        help='Thiết bị chạy: auto (tự phát hiện), gpu, cpu (mặc định: auto)')

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

    # === NEW: Xác định device (GPU/CPU) cho PaddleOCR ===
    if args.device == 'auto':
        has_gpu, reason = detect_paddle_gpu()
        use_gpu = has_gpu
        if not has_gpu:
            print(f"Dùng CPU ({reason})")
        else:
            print("Dùng GPU (CUDA)")
    elif args.device == 'gpu':
        has_gpu, reason = detect_paddle_gpu()
        if not has_gpu:
            print(f"[CẢNH BÁO] Bạn ép --device gpu nhưng {reason}.", file=sys.stderr)
            print("        Tự động rơi về CPU.", file=sys.stderr)
            use_gpu = False
        else:
            use_gpu = True
            print("Dùng GPU (CUDA)")
    else:
        use_gpu = False
        has_gpu, reason = detect_paddle_gpu()
        if has_gpu:
            print("Dùng CPU (GPU khả dụng nhưng bị ép dùng CPU)")
        else:
            print(f"Dùng CPU ({reason})")

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

    # Khởi tạo PaddleOCR (API 3.x: dùng device='gpu'/'cpu'; không có use_angle_cls/show_log)
    device_str = 'gpu' if use_gpu else 'cpu'
    try:
        ocr_engine = PaddleOCR(
            lang=paddle_lang,
            device=device_str,
        )
    except (TypeError, ValueError):
        # Fallback API 2.x cũ (use_gpu=)
        ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang=paddle_lang,
            use_gpu=use_gpu,
            show_log=False,
        )
    print(f"✓ PaddleOCR đã khởi tạo (device: {device_str})")

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
        elif args.input.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}:
            noi_dung = ocr_anh(ocr_engine, args.input, args.lang)
        elif args.input.suffix.lower() in {'.docx', '.doc'}:
            print("[CẢNH BÁO] DOCX: PaddleOCR chỉ OCR ảnh, không trích text. Dùng python-docx trước.")
            sys.exit(1)
        else:
            print(f"[LỖI] Định dạng không hỗ trợ: {args.input.suffix}", file=sys.stderr)
            sys.exit(1)
    finally:
        # LUÔN LUÔN cleanup temp dir, kể cả khi crash
        shutil.rmtree(temp_dir, ignore_errors=True)

    args.output.write_text(noi_dung, encoding='utf-8')
    print(f"\n✓ Đã ghi: {args.output}")
    print(f"  Kích thước: {len(noi_dung):,} ký tự")


if __name__ == '__main__':
    main()
