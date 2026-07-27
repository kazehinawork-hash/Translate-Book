"""
mineru_extract.py - Wrapper gọi MinerU CLI để trích xuất PDF/DOCX/ảnh

MinerU 2.x+ (đổi tên từ magic-pdf 1.x). CLI: `mineru` (không phải `magic-pdf`).
Cần verify tham số CLI bằng `mineru --help` sau khi cài - các tham số dưới
là giao diện dự kiến có thể đã thay đổi ở MinerU 3.4.

Ví dụ:
    python scripts/mineru_extract.py ^
        --input "input\ten-sach.pdf" ^
        --output "working\extracted\$slug\raw.md" ^
        --lang en
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None


def kiem_tra_mineru() -> str | None:
    """Kiểm tra MinerU CLI có sẵn không. Trả về đường dẫn hoặc None."""
    return shutil.which('mineru')


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Wrapper gọi MinerU CLI để trích xuất PDF/DOCX/ảnh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File đầu vào (PDF/DOCX/ảnh)')
    parser.add_argument('--output', type=Path, required=True, help='File Markdown đầu ra')
    parser.add_argument('--lang', type=str, default='en', help='Ngôn ngữ (en, ch, ch+en, ...)')
    parser.add_argument('--ocr', type=str, default='pp-ocrv6', help='Engine OCR')
    parser.add_argument('--dpi', type=int, default=200, help='DPI cho OCR (nếu áp dụng)')
    parser.add_argument('--method', type=str, default='auto', help='Method: auto, txt, ocr')
    parser.add_argument('--no-parse-equation', dest='parse_equation', action='store_false', help='Tắt parse công thức toán')
    parser.add_argument('--server', type=str, default=None, help='MinerU server URL (nếu dùng remote)')

    args = parser.parse_args()

    # Kiểm tra MinerU
    mineru_path = kiem_tra_mineru()
    if not mineru_path:
        print("[LỖI] Không tìm thấy MinerU CLI.", file=sys.stderr)
        print("        Cài bằng: pip install -U mineru", file=sys.stderr)
        print("        Sau đó: mineru-models-download (để tải model)", file=sys.stderr)
        sys.exit(1)

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Xây dựng lệnh
    # MinerU 3.4 CLI: mineru -p <path> -o <output_dir> -m <method> -b <backend>
    cmd = [
        mineru_path,
        '-p', str(args.input.absolute()),
        '-o', str(args.output.parent.absolute()),
        '-m', args.method,
    ]

    if args.server:
        cmd.extend(['--api-url', args.server])

    print(f"Chạy: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if console:
            console.print(f"[bold green]✓ MinerU hoàn thành[/bold green]")
        else:
            print("✓ MinerU hoàn thành")
        if result.stdout:
            print("STDOUT:", result.stdout[:500])
        if result.stderr:
            print("STDERR:", result.stderr[:500])
    except subprocess.CalledProcessError as e:
        print(f"[LỖI] MinerU thất bại (exit code {e.returncode})", file=sys.stderr)
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        print("\nGợi ý: chạy `mineru --help` để xem tham số CLI thật của phiên bản bạn đang cài.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"[LỖI] Không tìm thấy: {mineru_path}", file=sys.stderr)
        sys.exit(1)

    # Tìm file output thực tế của MinerU (thường nằm trong thư mục con)
    # Cấu trúc output MinerU 3.4: <output_dir>/<input_name>/auto/<input_name>.md
    possible_outputs = [
        args.output,
        args.output.parent / args.input.stem / args.input.suffix.lstrip('.') / f"{args.input.stem}.md",
        args.output.parent / args.input.stem / "auto" / f"{args.input.stem}.md",
    ]

    for p in possible_outputs:
        if p.exists() and p != args.output:
            shutil.move(str(p), str(args.output))
            print(f"✓ Đã di chuyển output: {args.output}")
            break
    else:
        if not args.output.exists():
            print(f"[CẢNH BÁO] Không tìm thấy file output. Kiểm tra thư mục {args.output.parent}", file=sys.stderr)


if __name__ == '__main__':
    main()
