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

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
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

    text = args.input.read_text(encoding='utf-8')
    print(f"Đọc: {args.input} ({len(text)} ký tự)")
    print(f"Config: {args.config} ({CONFIG_DESCRIPTIONS[args.config]})")

    converter = opencc.OpenCC(args.config)
    text_da_chuyen = converter.convert(text)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text_da_chuyen, encoding='utf-8')
    print(f"✓ Đã ghi: {args.output}")

    # Thống kê
    ky_tu_goc = sum(1 for c in text if '一' <= c <= '鿿')
    ky_tu_moi = sum(1 for c in text_da_chuyen if '一' <= c <= '鿿')
    print(f"  Ký tự Hán: gốc {ky_tu_goc} → sau {ky_tu_moi}")


if __name__ == '__main__':
    main()
