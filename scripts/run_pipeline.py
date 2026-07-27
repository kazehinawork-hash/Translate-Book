"""
run_pipeline.py - Orchestrator chạy cả pipeline cho 1 cuốn sách

Pipeline tự động:
  1. Trích xuất (MinerU hoặc EPUB)
  2. QC sau trích xuất
  3. Phát hiện ngôn ngữ
  4. (ZH) OpenCC nếu cần
  5. Chia chunk
  → Trả về danh sách file chunk, người dùng paste từng cái vào AI để dịch
  6. (Sau khi dịch) QA từng chunk
  7. Ghép file hoàn chỉnh

KHÔNG tự động gọi API (giai đoạn hiện tại - xem PLAN.md mục 13 cho lộ trình).

Ví dụ:
    python scripts/run_pipeline.py ^
        --input "input\ten-sach.pdf" ^
        --slug "ten-sach" ^
        --lang auto
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402

# Đường dẫn gốc dự án (giả định script này nằm trong scripts/)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


def chay_script(name: str, args: list[str]) -> bool:
    """Chạy script con, trả về True nếu thành công."""
    script_path = SCRIPT_DIR / name
    if not script_path.exists():
        print(f"[LỖI] Không tìm thấy script: {script_path}", file=sys.stderr)
        return False
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n{'='*60}")
    print(f"Chạy: {name} {' '.join(args)}")
    print('='*60)
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[LỖI] {name} thất bại với exit code {e.returncode}", file=sys.stderr)
        return False


def buoc_trich_xuat(args) -> Path | None:
    """Bước 1: Trích xuất. Trả về đường dẫn file raw.md."""
    raw_md = PROJECT_ROOT / "working" / "extracted" / args.slug / "raw.md"
    raw_md.parent.mkdir(parents=True, exist_ok=True)

    if args.input.suffix.lower() == '.epub':
        return raw_md if chay_script('epub_extract.py', [
            '--input', str(args.input),
            '--output', str(raw_md),
        ]) else None
    else:
        return raw_md if chay_script('mineru_extract.py', [
            '--input', str(args.input),
            '--output', str(raw_md),
            '--lang', args.lang if args.lang != 'auto' else 'en',
        ]) else None


def buoc_qc_trich_xuat(raw_md: Path, lang: str, slug: str) -> bool:
    """Bước 2: QC sau trích xuất."""
    qa_report = raw_md.parent.parent.parent / "qa" / slug / "extract-qc.md"
    return chay_script('post_extract_qc.py', [
        '--input', str(raw_md),
        '--report', str(qa_report),
        '--lang', lang,
    ])


def buoc_phat_hien_ngon_ngu(raw_md: Path) -> str:
    """Bước 3: Phát hiện ngôn ngữ. Trả về mã ngôn ngữ (en/zh-Hans/zh-Hant)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / 'detect_language.py'), str(raw_md), '--quiet'],
        capture_output=True, text=True
    )
    lang = result.stdout.strip() if result.returncode == 0 else 'unknown'
    print(f"Ngôn ngữ phát hiện: {lang}")
    return lang


def buoc_opencc(raw_md: Path, ngon_ngu: str) -> Path:
    """Bước 4: OpenCC nếu là Phồn thể. Trả về file raw-hans.md hoặc raw.md."""
    if ngon_ngu == 'zh-Hant':
        raw_hans = raw_md.parent / 'raw-hans.md'
        if chay_script('opencc_normalize.py', [
            '--input', str(raw_md),
            '--output', str(raw_hans),
            '--config', 't2s',
        ]):
            return raw_hans
    return raw_md


def buoc_chia_chunk(input_md: Path, lang: str, slug: str) -> bool:
    """Bước 5: Chia chunk."""
    if lang.startswith('zh'):
        min_chars, max_chars = 1500, 3000
    else:
        min_chars, max_chars = 3000, 8000

    chunks_dir = PROJECT_ROOT / "working" / "chunks" / slug
    return chay_script('chunk_text.py', [
        '--input', str(input_md),
        '--output-dir', str(chunks_dir),
        '--lang', 'zh' if lang.startswith('zh') else 'en',
        '--min-chars', str(min_chars),
        '--max-chars', str(max_chars),
        '--overlap-chars', '200',
        '--respect-headings',
    ])


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Orchestrator chạy pipeline trích xuất + chia chunk cho 1 cuốn sách",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File đầu vào (PDF/EPUB/DOCX/ảnh)')
    parser.add_argument('--slug', type=str, required=True, help='Slug sách (a-z, 0-9, dấu gạch ngang)')
    parser.add_argument('--lang', type=str, default='auto', help='Ngôn ngữ (en/zh/auto)')
    parser.add_argument('--skip-qc', action='store_true', help='Bỏ qua QC sau trích xuất')
    parser.add_argument('--skip-chunk', action='store_true', help='Chỉ trích xuất, không chia chunk')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"# PIPELINE: {args.input.name} → {args.slug}")
    print(f"{'#'*60}\n")

    # Bước 1: Trích xuất
    raw_md = buoc_trich_xuat(args)
    if not raw_md or not raw_md.exists():
        print("[LỖI] Trích xuất thất bại. Dừng pipeline.", file=sys.stderr)
        sys.exit(1)

    # Bước 2: QC (tùy chọn)
    if not args.skip_qc:
        lang_for_qc = args.lang if args.lang != 'auto' else 'en'
        if not buoc_qc_trich_xuat(raw_md, lang_for_qc, args.slug):
            print("[CẢNH BÁO] QC có vấn đề nhưng tiếp tục...")

    # Bước 3: Phát hiện ngôn ngữ (nếu auto)
    ngon_ngu = args.lang
    if args.lang == 'auto':
        ngon_ngu = buoc_phat_hien_ngon_ngu(raw_md)

    # Bước 4: OpenCC nếu Phồn
    input_md = buoc_opencc(raw_md, ngon_ngu)

    # Bước 5: Chia chunk
    if not args.skip_chunk:
        if not buoc_chia_chunk(input_md, ngon_ngu, args.slug):
            print("[LỖI] Chia chunk thất bại.", file=sys.stderr)
            sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"# HOÀN THÀNH")
    print(f"{'#'*60}")
    print(f"  Raw: {raw_md}")
    if input_md != raw_md:
        print(f"  Chuẩn hóa: {input_md}")
    if not args.skip_chunk:
        chunks_dir = PROJECT_ROOT / "working" / "chunks" / args.slug
        print(f"  Chunks: {chunks_dir}")
    print(f"\nBước tiếp: paste từng chunk vào chat AI để dịch, sau đó lưu vào output/{args.slug}/")


if __name__ == '__main__':
    main()
