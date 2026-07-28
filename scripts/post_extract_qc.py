"""
post_extract_qc.py - QC sau khi trích xuất (MinerU/EPUB)

Phát hiện:
- Mojibake (UTF-8 đọc thành Latin-1 hoặc ngược lại)
- Dòng trống quá nhiều (≥ 5 liên tiếp)
- Dòng lặp (OCR dính header)
- Encoding không phải UTF-8

Ví dụ:
    python scripts/post_extract_qc.py ^
        --input "working\extracted\$slug\raw.md" ^
        --report "working\qa\$slug\extract-qc.md" ^
        --lang zh
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None


# === NEW: ftfy integration (ưu tiên) cho mojibake detection ===
try:
    import ftfy
    HAS_FTFY = True
except ImportError:
    HAS_FTFY = False
    print("[CẢNH BÁO] Không có ftfy, dùng regex cũ để detect mojibake", file=sys.stderr)

# Mẫu mojibake phổ biến (fallback khi không có ftfy)
MOJIBAKE_PATTERNS = [
    (re.compile(r'Ã©|Ã¨|Ã¢|Ã |Â©|Â®'), 'UTF-8 → Latin-1 lỗi'),
    (re.compile(r'ä¸­æ|ä¸æ|æ–‡|è‹±|è‹±æ–‡'), 'UTF-8 → Latin-1 (Hán tự)'),
    (re.compile(r'â€™|â€œ|â€|Â '), 'Smart quote broken'),
    (re.compile(r'^\ufeff', re.MULTILINE), 'BOM ở đầu dòng'),
    (re.compile(r'\ufffd'), 'Ký tự thay thế U+FFFD (encoding không khớp)'),
]


def doc_file(file_path: Path) -> tuple[str, str]:
    """Đọc file, trả về (nội dung, encoding đã dùng)."""
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1']
    for enc in encodings:
        try:
            text = file_path.read_text(encoding=enc)
            return text, enc
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"Không đọc được {file_path}")


def kiem_tra_mojibake(text: str) -> list[tuple[int, str, str]]:
    """Phát hiện mojibake trong text.
    
    Ưu tiên dùng ftfy nếu có, fallback về regex MOJIBAKE_PATTERNS.
    
    Returns:
        list: [(line_number, line_preview, description), ...]
    """
    ket_qua = []
    dong_list = text.splitlines()
    
    for i, dong in enumerate(dong_list, 1):
        if not dong.strip():
            continue
            
        detected = False
        
        # Ưu tiên ftfy
        if HAS_FTFY:
            try:
                fixed = ftfy.fix_encoding(dong)
                if fixed != dong:
                    # Kiểm tra xem fix có thực sự cải thiện không
                    if len(fixed) > 0 and len(fixed) < len(dong) * 1.5:
                        preview = dong[:60] + ('...' if len(dong) > 60 else '')
                        fixed_preview = fixed[:40] + ('...' if len(fixed) > 40 else '')
                        ket_qua.append((i, preview, f"Mojibake (ftfy fix: {fixed_preview})"))
                        detected = True
            except Exception:
                pass
        
        # Fallback: regex
        if not detected:
            for pattern, mo_ta in MOJIBAKE_PATTERNS:
                if pattern.search(dong):
                    preview = dong[:60] + ('...' if len(dong) > 60 else '')
                    ket_qua.append((i, preview, mo_ta))
                    break
    
    return ket_qua


def kiem_tra_dong_lap(text: str, nguong: int = 3) -> list[tuple[int, str]]:
    """Phát hiện dòng lặp lại liên tiếp ≥ nguong lần."""
    ket_qua = []
    dong_truoc = None
    dem = 0
    for i, dong in enumerate(text.splitlines(), 1):
        dong = dong.strip()
        if not dong:
            continue
        if dong == dong_truoc:
            dem += 1
            if dem == nguong:
                ket_qua.append((i - nguong + 1, dong[:100]))
        else:
            dong_truoc = dong
            dem = 1
    return ket_qua


def kiem_tra_dong_lap_khong_lien_tuc(text: str, nguong: int = 5) -> list[tuple[str, int]]:
    """Phát hiện dòng lặp NHIỀU LẦN trong toàn bộ document (không cần liên tiếp).

    Dùng để bắt header/footer OCR theo trang: "Trang 1", "Chapter 1", v.v.
    xuất hiện ở mỗi trang nhưng cách nhau bởi nội dung.
    """
    from collections import Counter
    dem = Counter()
    for dong in text.splitlines():
        dong = dong.strip()
        # Chỉ đếm dòng "có nghĩa" (không quá ngắn, không phải heading markdown)
        if not dong or len(dong) < 3 or dong.startswith('#'):
            continue
        dem[dong] += 1
    # Trả về các dòng lặp ≥ nguong lần
    return [(dong, so_lan) for dong, so_lan in dem.most_common() if so_lan >= nguong]


def kiem_tra_dong_trong(text: str, nguong: int = 5) -> list[int]:
    """Phát hiện chỗ có ≥ nguong dòng trống liên tiếp."""
    ket_qua = []
    dem = 0
    for i, dong in enumerate(text.splitlines(), 1):
        if not dong.strip():
            dem += 1
            if dem == nguong:
                ket_qua.append(i - nguong + 1)
        else:
            dem = 0
    return ket_qua


def thong_ke(text: str) -> dict:
    """Thống kê cơ bản."""
    lines = text.splitlines()
    return {
        'tong_dong': len(lines),
        'dong_rong': sum(1 for l in lines if not l.strip()),
        'ky_tu': len(text),
    }


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="QC sau khi trích xuất Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File Markdown cần QC')
    parser.add_argument('--report', type=Path, help='File báo cáo đầu ra')
    parser.add_argument('--lang', choices=['en', 'zh'], default='en', help='Ngôn ngữ (chỉ để ghi nhận)')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    text, encoding = doc_file(args.input)
    stats = thong_ke(text)
    mojibake = kiem_tra_mojibake(text)
    lap = kiem_tra_dong_lap(text)
    lap_ko_lien_tuc = kiem_tra_dong_lap_khong_lien_tuc(text, nguong=5)
    trong = kiem_tra_dong_trong(text)

    # Tạo báo cáo
    bao_cao = []
    bao_cao.append(f"# Báo cáo QC trích xuất: {args.input.name}\n")
    bao_cao.append(f"- **File**: `{args.input}`")
    bao_cao.append(f"- **Encoding**: `{encoding}`")
    bao_cao.append(f"- **Ngôn ngữ**: {args.lang}")
    bao_cao.append("")

    bao_cao.append("## Thống kê")
    bao_cao.append(f"- Tổng dòng: {stats['tong_dong']}")
    bao_cao.append(f"- Dòng trống: {stats['dong_rong']}")
    bao_cao.append(f"- Ký tự: {stats['ky_tu']:,}".replace(',', '.'))
    bao_cao.append("")

    # Mojibake
    bao_cao.append("## Mojibake")
    if mojibake:
        bao_cao.append(f"❌ Phát hiện **{len(mojibake)}** dòng có mojibake:")
        bao_cao.append("")
        bao_cao.append("| Dòng | Nội dung | Loại lỗi |")
        bao_cao.append("|------|----------|----------|")
        for dong, nd, loai in mojibake[:20]:
            nd_clean = nd.replace('|', '\\|')
            bao_cao.append(f"| {dong} | `{nd_clean}` | {loai} |")
        if len(mojibake) > 20:
            bao_cao.append(f"| ... | ... | (còn {len(mojibake) - 20} dòng) |")
    else:
        bao_cao.append("✅ Không phát hiện mojibake")
    bao_cao.append("")

    # Dòng lặp
    bao_cao.append("## Dòng lặp (OCR dính header)")
    if lap:
        bao_cao.append(f"❌ Phát hiện **{len(lap)}** dòng lặp ≥ 3 lần liên tiếp:")
        for dong, nd in lap[:10]:
            nd_clean = nd.replace('|', '\\|')
            bao_cao.append(f"- Dòng {dong}: `{nd_clean}`")
    else:
        bao_cao.append("✅ Không phát hiện dòng lặp liên tiếp")

    # Dòng lặp không liên tiếp (header/footer OCR theo trang)
    if lap_ko_lien_tuc:
        bao_cao.append("")
        bao_cao.append("## Dòng lặp không liên tiếp (header/footer OCR theo trang)")
        bao_cao.append(f"⚠️ Phát hiện **{len(lap_ko_lien_tuc)}** dòng xuất hiện ≥ 5 lần trong toàn file:")
        bao_cao.append("")
        bao_cao.append("| Số lần | Dòng |")
        bao_cao.append("|--------|------|")
        for nd, so_lan in lap_ko_lien_tuc[:20]:
            nd_clean = nd.replace('|', '\\|')[:100]
            bao_cao.append(f"| {so_lan} | `{nd_clean}` |")
        if len(lap_ko_lien_tuc) > 20:
            bao_cao.append(f"| ... | (còn {len(lap_ko_lien_tuc) - 20} dòng) |")
        bao_cao.append("")
        bao_cao.append("> Nếu đây là header/footer OCR, cần xóa khỏi output. Có thể dùng sed/PowerShell hoặc dùng MinerU với option tắt header/footer.")
    else:
        bao_cao.append("✅ Không phát hiện dòng lặp không liên tiếp")
    bao_cao.append("")

    # Dòng trống
    bao_cao.append("## Dòng trống liên tiếp")
    if trong:
        bao_cao.append(f"⚠️ Có **{len(trong)}** chỗ có ≥ 5 dòng trống liên tiếp:")
        bao_cao.append(f"  Vị trí: dòng {', '.join(map(str, trong[:10]))}")
        if len(trong) > 10:
            bao_cao.append(f"  ... và {len(trong) - 10} chỗ khác")
    else:
        bao_cao.append("✅ Không có dòng trống quá nhiều")
    bao_cao.append("")

    # Encoding warning
    if encoding != 'utf-8' and encoding != 'utf-8-sig':
        bao_cao.append(f"## ⚠️ Cảnh báo encoding")
        bao_cao.append(f"File đọc được với encoding **{encoding}** (không phải UTF-8).")
        bao_cao.append("Khi lưu lại,hãy chuyển sang UTF-8 để tránh mojibake trên Windows.")
        bao_cao.append("")

    # Tổng kết
    co_loi = bool(mojibake or lap or lap_ko_lien_tuc or (encoding not in ('utf-8', 'utf-8-sig')))
    if co_loi:
        bao_cao.append("## ❌ Tổng kết: CÓ LỖI - cần sửa trước khi dịch")
    else:
        bao_cao.append("## ✅ Tổng kết: OK")

    nd_bao_cao = '\n'.join(bao_cao)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(nd_bao_cao, encoding='utf-8')
        if console:
            console.print(f"[bold green]Báo cáo QC:[/bold green] {args.report}")
        else:
            print(f"Báo cáo QC: {args.report}")

    # In tóm tắt
    if console:
        if co_loi:
            console.print(f"[bold red]❌ CÓ LỖI[/bold red] - xem chi tiết trong báo cáo")
        else:
            console.print(f"[bold green]✅ OK[/bold green]")
    else:
        print("\n=== TÓM TẮT ===")
        print(f"Mojibake: {len(mojibake)} chỗ")
        print(f"Dòng lặp liên tiếp: {len(lap)} chỗ")
        print(f"Dòng lặp không liên tiếp: {len(lap_ko_lien_tuc)} dòng")
        print(f"Dòng trống ≥ 5: {len(trong)} chỗ")
        print(f"Encoding: {encoding}")
        print("CÓ LỖI" if co_loi else "OK")


if __name__ == '__main__':
    main()
