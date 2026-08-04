"""
opencc_normalize.py - Chuẩn hóa Phồn thể → Giản thể bằng OpenCC

Dùng khi sách gốc là Phồn thể (zh-Hant). OpenCC xử lý deterministic, chính xác
với từ điển cụm từ - tốt hơn LLM dịch từ Phồn sang Giản.

Ví dụ:
    python scripts/opencc_normalize.py ^
        --input "working\extracted\$slug\raw.md" ^
        --output "working\extracted\$slug\raw-hans.md" ^
        --config t2s
"""

import os
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding  # noqa: E402

try:
    import opencc
    HAS_OPENCC = True
except ImportError:
    HAS_OPENCC = False


# Mapping config name → ý nghĩa
CONFIG_DESCRIPTIONS = {
    't2s': 'Phồn thể → Giản thể (Traditional → Simplified)',
    's2t': 'Giản thể → Phồn thể (Simplified → Traditional)',
    't2tw': 'Phồn thể → Đài Loan (Traditional → Taiwan)',
    'tw2t': 'Đài Loan → Phồn thể (Taiwan → Traditional)',
    's2tw': 'Giản thể → Đài Loan (Simplified → Taiwan)',
    'tw2s': 'Đài Loan → Giản thể (Taiwan → Simplified)',
    't2jp': 'Phồn thể → Nhật (Traditional → Japan Kanji)',
    'jp2t': 'Nhật → Phồn thể (Japan Kanji → Traditional)',
}


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Chuẩn hóa Hán tự bằng OpenCC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File đầu vào')
    parser.add_argument('--output', type=Path, required=True, help='File đầu ra')
    parser.add_argument('--config', type=str, default='t2s',
                        choices=list(CONFIG_DESCRIPTIONS.keys()),
                        help='Loại chuyển đổi (mặc định: t2s = Phồn → Giản)')

    args = parser.parse_args()

    if not HAS_OPENCC:
        print("[LỖI] Chưa cài opencc-python-reimplemented.", file=sys.stderr)
        print("        Cài bằng: pip install opencc-python-reimplemented", file=sys.stderr)
        sys.exit(1)

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    converter = opencc.OpenCC(args.config)

    # === NEW: Kiểm tra kích thước file - streaming cho file lớn ===
    file_size = args.input.stat().st_size
    FILE_SIZE_THRESHOLD = 50 * 1024 * 1024  # 50 MB

    print(f"Config: {args.config} ({CONFIG_DESCRIPTIONS[args.config]})")

    if file_size > FILE_SIZE_THRESHOLD:
        # ===== STREAMING MODE cho file lớn =====
        size_mb = file_size / (1024 * 1024)
        print(f"[INFO] File lớn ({size_mb:.1f} MB), xử lý từng dòng để tiết kiệm RAM...")
        
        so_dong = 0
        with open(args.input, 'r', encoding='utf-8') as fin, \
             open(args.output, 'w', encoding='utf-8') as fout:
            for line in fin:
                # Convert từng dòng
                converted_line = converter.convert(line)
                fout.write(converted_line)
                so_dong += 1
                
                # Progress mỗi 1000 dòng
                if so_dong % 1000 == 0:
                    print(f"  Đã xử lý {so_dong} dòng...", end='\r')
        
        print(f"\n[OK] Đã chuẩn hóa {so_dong} dòng")
    else:
        # ===== BATCH MODE cho file nhỏ (giữ nguyên cách cũ) =====
        text = args.input.read_text(encoding='utf-8')
        print(f"Đọc: {args.input} ({len(text)} ký tự)")
        
        text_da_chuyen = converter.convert(text)
        args.output.write_text(text_da_chuyen, encoding='utf-8')
        print(f"Ghi: {args.output}")


if __name__ == '__main__':
    main()
