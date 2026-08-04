"""
detect_language.py - Phát hiện ngôn ngữ (EN/ZH/Phồn/Giản)

Bước 1: langdetect để phân biệt EN vs ZH vs ngôn ngữ khác
Bước 2: Nếu là ZH, kiểm tra ký tự Phồn-thể-specific để phân biệt Phồn vs Giản

Ví dụ:
    python scripts/detect_language.py "working\extracted\$slug\raw.md"
    # Output: zh-Hans
"""

import os
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding  # noqa: E402

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0  # Kết quả ổn định
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False


# Ký tự chỉ có trong Phồn thể (không có trong Giản thể)
# Lấy từ OpenCC standard char table
PHON_THE_DAC_TRUNG = set('萬與軋辭類麼麼葉齒鉅鉤錄陣爭隸隻雙雜雞靈黃黑默體麵麥黃龍龜龜')

# Ký tự chỉ có trong Giản thể
GIAN_THE_DAC_TRUNG = set('万与轧辞类么麽叶齿钜钩录阵争隶只双杂鸡灵黄黑默体面麦黄龙龟')


def doc_file_text(file_path: Path) -> str:
    """Đọc file với auto-detect encoding."""
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1']
    for enc in encodings:
        try:
            return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"Không đọc được {file_path}")


def phan_biet_phong_gian(text: str) -> str:
    """Phân biệt Phồn thể vs Giản thể bằng đếm ký tự đặc trưng."""
    dem_phong = sum(1 for c in text if c in PHON_THE_DAC_TRUNG)
    dem_gian = sum(1 for c in text if c in GIAN_THE_DAC_TRUNG)

    if dem_phong == 0 and dem_gian == 0:
        return 'zh-Hans'  # Không có ký tự đặc trưng nào, mặc định Giản
    if dem_phong > dem_gian * 1.5:
        return 'zh-Hant'
    if dem_gian > dem_phong * 1.5:
        return 'zh-Hans'
    # Không rõ ràng - mặc định theo nhiều hơn
    return 'zh-Hant' if dem_phong > dem_gian else 'zh-Hans'


def phat_hien(text: str) -> str:
    """Pipeline phát hiện ngôn ngữ."""
    if not HAS_LANGDETECT:
        print("[CẢNH BÁO] Chưa cài langdetect. Cài bằng: pip install langdetect", file=sys.stderr)
        return 'unknown'

    # Lấy mẫu 5000 ký tự đầu (langdetect hoạt động tốt hơn với text không quá dài)
    sample = text[:5000]
    try:
        lang = detect(sample)
    except Exception as e:
        return f'unknown (lỗi: {e})'

    if lang in ('zh-cn', 'zh-tw', 'zh'):
        return phan_biet_phong_gian(sample)
    return lang


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Phát hiện ngôn ngữ file (EN/ZH/Phồn/Giản)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('file', type=Path, help='File cần phát hiện ngôn ngữ')
    parser.add_argument('--quiet', '-q', action='store_true', help='Chỉ in kết quả, không giải thích')

    args = parser.parse_args()

    if not args.file.exists():
        print(f"[LỖI] File không tồn tại: {args.file}", file=sys.stderr)
        sys.exit(1)

    text = doc_file_text(args.file)
    ket_qua = phat_hien(text)

    if args.quiet:
        print(ket_qua)
    else:
        print(f"File: {args.file}")
        print(f"Ngôn ngữ phát hiện: {ket_qua}")
        # Gợi ý
        if ket_qua == 'zh-Hant':
            print("→ Gợi ý: chạy opencc_normalize.py với --config t2s")
        elif ket_qua == 'en':
            print("→ Gợi ý: tiếng Anh, dùng prompts/en-to-vi.md")
        elif ket_qua == 'zh-Hans':
            print("→ Gợi ý: đã là Giản thể, bỏ qua OpenCC")


if __name__ == '__main__':
    main()
