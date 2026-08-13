"""
glossary_qa.py - QA tự động: kiểm tra thuật ngữ, ký tự sót, tính nhất quán

Script RẺ NHẤT mà GIÁ TRỊ CAO NHẤT trong pipeline - bắt lỗi nhất quán trước
khi người duyệt.

Dùng cho:
- Sách EN/ZH Markdown: kiểm tra thuật ngữ còn sót
- SRT: kiểm tra số dòng, timestamp, index

Ví dụ:
    python scripts/glossary_qa.py ^
        --source "working\chunks\$slug\chunk-001.md" ^
        --translation "output\$slug\chunk-001.md" ^
        --glossary "glossary\$slug.csv" ^
        --genre-glossary "glossary\genres\tien-hiep.csv" ^
        --lang zh ^
        --report "working\qa\$slug\chunk-001-qa.md"
"""

import os
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding  # noqa: E402
from glossary_lib import load_all, filter_for_book, get_author_of_book  # noqa: E402

# Cố gắng dùng pandas cho CSV (đẹp hơn); fallback về csv module nếu chưa cài
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
except ImportError:
    console = None


# ========== HẰNG SỐ ==========

# Ký tự Hán tự (CJK Unified Ideographs)
HAN_REGEX = re.compile(r'[㐀-鿿豈-﫿]')

# Mẫu mojibake phổ biến (encoding sai trên Windows)
MOJIBAKE_PATTERNS = [
    re.compile(r'Ã©|Ã¨|Ã¢|Ã |Â©|Â®'),     # UTF-8 đọc thành Latin-1
    re.compile(r'ä¸­æ|ä¸æ|æ–‡|è‹±|è‹±æ–‡'),     # UTF-8 đọc thành Latin-1 cho Hán
    re.compile(r'â€™|â€œ|â€|Â '),  # Smart quote broken
    re.compile(r'^\ufeff', re.MULTILINE), # BOM ở đầu dòng
    re.compile(r'\ufffd'), # Ký tự thay thế U+FFFD
]

# Bỏ qua các thẻ Markdown khi đếm từ/ký tự
MARKDOWN_NOISE = re.compile(r'^#+\s+|^[*\-+]\s+|`[^`]+`|\[[^\]]+\]\([^\)]+\)')


# ========== HÀM TIỆN ÍCH ==========

def doc_du_lieu(file_path: Path) -> str:
    """Đọc file với auto-detect encoding."""
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1']
    for enc in encodings:
        try:
            return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"Không đọc được {file_path} với các encoding phổ biến")


def doc_glossary(csv_path: Path) -> list[dict]:
    """Đọc file CSV glossary, bỏ qua dòng lỗi."""
    if not csv_path.exists():
        return []
    rows = []
    if HAS_PANDAS:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8', dtype=str, keep_default_na=False)
            rows = df.to_dict('records')
        except Exception as e:
            print(f"[CẢNH BÁO] Lỗi đọc {csv_path} bằng pandas: {e}", file=sys.stderr)
    if not rows:
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                rows = [dict(r) for r in reader]
        except Exception as e:
            print(f"[CẢNH BÁO] Lỗi đọc {csv_path}: {e}", file=sys.stderr)
    return rows


def dem_tu_en(text: str) -> int:
    """Đếm từ tiếng Anh (bỏ qua markdown noise)."""
    text = MARKDOWN_NOISE.sub('', text)
    return len(re.findall(r'\b[A-Za-z]+\b', text))


def dem_ky_tu_zh(text: str) -> int:
    """Đếm ký tự Hán (bỏ qua markdown noise)."""
    text = MARKDOWN_NOISE.sub('', text)
    return len(HAN_REGEX.findall(text))


def kiem_tra_mojibake(text: str) -> list[tuple[int, str]]:
    """Tìm các dòng có dấu hiệu mojibake. Trả về [(số_dòng, đoạn_văn)]."""
    ket_qua = []
    for i, dong in enumerate(text.splitlines(), 1):
        for pattern in MOJIBAKE_PATTERNS:
            if pattern.search(dong):
                ket_qua.append((i, dong[:80]))
                break
    return ket_qua


def is_word_in_text(word: str, text: str, is_latin: bool = False) -> bool:
    """Kiểm tra từ có nằm trong văn bản không, dùng word boundary cho chữ Latin để tránh lỗi chuỗi con."""
    if not word or not text:
        return False
    if is_latin or not HAN_REGEX.search(word):
        try:
            pattern = r'\b' + re.escape(word) + r'\b'
            return bool(re.search(pattern, text, flags=re.IGNORECASE))
        except re.error:
            return word.lower() in text.lower()
    else:
        return word in text


def kiem_tra_dong_lap(text: str, nguong: int = 3) -> list[tuple[int, str]]:
    """Phát hiện dòng lặp lại liên tiếp ≥ nguong lần (OCR dính header)."""
    ket_qua = []
    dong_truoc = None
    dem = 0
    for i, dong in enumerate(text.splitlines(), 1):
        dong = dong.strip()
        if dong and dong == dong_truoc:
            dem += 1
            if dem == nguong:
                ket_qua.append((i - nguong + 1, dong[:80]))
        else:
            dong_truoc = dong
            dem = 1
    return ket_qua


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


# ========== HÀM CHÍNH: QA SÁCH (Markdown) ==========

def qa_sach_text(
    source_text: str,
    translated_text: str,
    glossary: list[dict],
    lang: str,
    genre_glossary: list[dict] | None = None,
    source_name: str = '',
    translation_name: str = '',
    threshold: float = 5.0,
) -> dict:
    """QA logic trên text string (không đọc file)."""
    bao_cao = []
    bao_cao.append(f"# Báo cáo QA: {translation_name}\n")
    if source_name:
        bao_cao.append(f"- **Nguồn**: `{source_name}`")
    if translation_name:
        bao_cao.append(f"- **Bản dịch**: `{translation_name}`")
    bao_cao.append(f"- **Ngôn ngữ**: {lang}")
    bao_cao.append("")

    text_goc = source_text
    text_dich = translated_text

    # Thống kê cơ bản
    if lang == 'zh':
        ky_tu_goc = dem_ky_tu_zh(text_goc)
        ky_tu_dich = dem_ky_tu_zh(text_dich)
        bao_cao.append("## Thống kê")
        bao_cao.append(f"- Ký tự Hán gốc: **{ky_tu_goc}**")
        bao_cao.append(f"- Ký tự Hán còn sót trong bản dịch: **{ky_tu_dich}**")
        bao_cao.append(f"- Tỷ lệ còn sót: {ky_tu_dich / max(ky_tu_goc, 1) * 100:.1f}%\n")
    else:
        tu_goc = dem_tu_en(text_goc)
        tu_dich = dem_tu_en(text_dich)
        bao_cao.append("## Thống kê")
        bao_cao.append(f"- Từ tiếng Anh gốc: **{tu_goc}**")
        bao_cao.append(f"- Từ tiếng Anh còn sót trong bản dịch: **{tu_dich}**")
        bao_cao.append(f"- Tỷ lệ còn sót: {tu_dich / max(tu_goc, 1) * 100:.1f}%\n")

    all_glossary = list(glossary)
    if genre_glossary:
        all_glossary += genre_glossary

    if not all_glossary:
        bao_cao.append("## ⚠️ Không có glossary - bỏ qua kiểm tra thuật ngữ")
    else:
        bao_cao.append(f"## Kiểm tra thuật ngữ ({len(all_glossary)} mục)")
        bao_cao.append("")

        loi_thuat_ngu = []
        loi_chua_dich = []
        loi_dich_sai = []
        cho_phep_giu_nguyen = []

        for entry in all_glossary:
            source = (entry.get('source') or '').strip()
            target = (entry.get('target') or '').strip()
            loai = (entry.get('type') or '').strip()
            note = (entry.get('note') or '').strip()

            if not source or not target:
                continue

            if source == target or 'giữ nguyên' in note.lower():
                cho_phep_giu_nguyen.append((source, target, loai))
                continue

            if is_word_in_text(source, text_dich, lang == 'en'):
                if HAN_REGEX.search(source) and lang == 'zh':
                    loi_chua_dich.append((source, target, 'tên riêng Hán còn sót'))
                elif re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$', source):
                    loi_chua_dich.append((source, target, 'tên riêng EN còn sót'))
                else:
                    loi_thuat_ngu.append((source, target, loai, 'source vẫn còn trong bản dịch'))
            
            if is_word_in_text(source, text_goc, lang == 'en') and source != target and 'giữ nguyên' not in note.lower():
                if not is_word_in_text(target, text_dich, True):
                    loi_dich_sai.append((source, target, loai, 'Không dùng target của glossary'))

        if loi_chua_dich:
            bao_cao.append("### ⚠️ Có thể còn sót (cần xem lại)")
            bao_cao.append("| Source | Target | Ghi chú |")
            bao_cao.append("|--------|--------|---------|")
            for s, t, note in loi_chua_dich:
                bao_cao.append(f"| `{s}` | {t} | {note} |")
            bao_cao.append("")

        if loi_thuat_ngu:
            bao_cao.append("### ❌ Lỗi thuật ngữ (source vẫn còn)")
            bao_cao.append("| Source | Target | Loại |")
            bao_cao.append("|--------|--------|------|")
            for s, t, loai, note in loi_thuat_ngu:
                bao_cao.append(f"| `{s}` | {t} | {loai} |")
            bao_cao.append("")

        if cho_phep_giu_nguyen:
            bao_cao.append(f"### ℹ️ Cho phép giữ nguyên: {len(cho_phep_giu_nguyen)} mục")
            bao_cao.append("")

        if loi_dich_sai:
            bao_cao.append("### ❌ Lỗi dịch sai (không bám sát glossary)")
            bao_cao.append("| Source | Target | Loại | Ghi chú |")
            bao_cao.append("|--------|--------|------|---------|")
            for s, t, loai, note in loi_dich_sai:
                bao_cao.append(f"| `{s}` | {t} | {loai} | {note} |")
            bao_cao.append("")

        if not loi_chua_dich and not loi_thuat_ngu and not loi_dich_sai:
            bao_cao.append("### ✅ Không phát hiện lỗi thuật ngữ")
            bao_cao.append("")

    bao_cao.append("## QC sau trích xuất")
    for ten, text in [("Gốc", text_goc), ("Dịch", text_dich)]:
        ds_mo = kiem_tra_mojibake(text)
        ds_lap = kiem_tra_dong_lap(text)
        ds_trong = kiem_tra_dong_trong(text)
        bao_cao.append(f"### File {ten}")
        if ds_mo:
            bao_cao.append(f"- ❌ Mojibake: {len(ds_mo)} chỗ")
            for dong, nd in ds_mo[:5]:
                bao_cao.append(f"  - Dòng {dong}: `{nd}`")
            if len(ds_mo) > 5:
                bao_cao.append(f"  - ... và {len(ds_mo) - 5} chỗ khác")
        else:
            bao_cao.append("- ✅ Không có mojibake")
        if ds_lap:
            bao_cao.append(f"- ❌ Dòng lặp: {len(ds_lap)} chỗ")
        else:
            bao_cao.append("- ✅ Không có dòng lặp")
        if ds_trong:
            bao_cao.append(f"- ⚠️ Dòng trống liên tiếp ≥ 5: {len(ds_trong)} chỗ (dòng {', '.join(map(str, ds_trong))})")
        else:
            bao_cao.append("- ✅ Không có dòng trống quá nhiều")
        bao_cao.append("")

    co_loi = False
    for line in bao_cao:
        if 'Tỷ lệ còn sót' in line:
            try:
                pct = float(line.split(':')[1].strip().rstrip('%'))
                if pct > threshold:
                    co_loi = True
            except (ValueError, IndexError):
                pass

    return {
        'source_name': source_name,
        'translation_name': translation_name,
        'text_goc': text_goc,
        'text_dich': text_dich,
        'report_lines': bao_cao,
        'co_loi': co_loi,
    }


def qa_sach(args) -> dict:
    """QA cho file dịch Markdown thường. Wrapper quanh qa_sach_text."""
    text_goc = doc_du_lieu(args.source)
    text_dich = doc_du_lieu(args.translation)

    glossary = []
    if args.glossary:
        glossary += doc_glossary(args.glossary)
    if args.genre_glossary:
        glossary += doc_glossary(args.genre_glossary)
    # Nếu không có file riêng nhưng có --book-slug → lọc từ master.csv
    if not glossary and args.book_slug:
        glossary += filter_for_book(load_all(), args.book_slug)

    return qa_sach_text(
        source_text=text_goc,
        translated_text=text_dich,
        glossary=glossary,
        lang=args.lang,
        source_name=str(args.source),
        translation_name=str(args.translation),
        threshold=args.threshold,
    )


# ========== CLI ==========

def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="QA tự động cho bản dịch (Markdown/SRT)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--source', type=Path, required=True, help='File gốc (chunk-X.md hoặc raw.srt)')
    parser.add_argument('--translation', type=Path, required=True, help='Bản dịch')
    parser.add_argument('--glossary', type=Path, help='Glossary cuốn sách (CSV) — nếu có sẽ dùng thay master')
    parser.add_argument('--genre-glossary', type=Path, help='Glossary thể loại (CSV)')
    parser.add_argument('--book-slug', help='Slug cuốn sách — tự lọc glossary từ master.csv khi không có --glossary')
    parser.add_argument('--lang', choices=['en', 'zh'], required=True, help='Ngôn ngữ gốc')
    parser.add_argument('--mode', choices=['md', 'srt'], default='md', help='Loại file: md hoặc srt')
    parser.add_argument('--report', type=Path, help='File báo cáo (Markdown)')
    parser.add_argument('--threshold', type=float, default=5.0,
                        help='Ngưỡng cảnh báo Hán tự còn sót (%%, mặc định 5.0). Mặc định áp cho cả md và srt mode.')

    args = parser.parse_args()

    # Kiểm tra file tồn tại
    for p in [args.source, args.translation]:
        if not p.exists():
            print(f"[LỖI] File không tồn tại: {p}", file=sys.stderr)
            sys.exit(1)

    co_loi = False  # Track có lỗi để exit code

    if args.mode == 'md':
        ket_qua = qa_sach(args)
        nd_bao_cao = '\n'.join(ket_qua['report_lines'])
        co_loi = ket_qua['co_loi']
    else:
        # SRT mode: kiểm tra đầy đủ (line/timestamp/index/Hán sót/glossary)
        try:
            import pysrt
        except ImportError:
            print("[LỖI] Cần cài pysrt: pip install pysrt", file=sys.stderr)
            sys.exit(1)
        sub_goc = pysrt.open(str(args.source))
        sub_dich = pysrt.open(str(args.translation))
        bao_cao = [f"# Báo cáo QA SRT: {args.translation.name}\n"]
        bao_cao.append(f"- Số dòng gốc: {len(sub_goc)}")
        bao_cao.append(f"- Số dòng dịch: {len(sub_dich)}")
        if len(sub_goc) != len(sub_dich):
            bao_cao.append(f"- ❌ **Số dòng KHÔNG khớp!** Chênh {abs(len(sub_goc) - len(sub_dich))}")
            co_loi = True
        else:
            bao_cao.append("- ✅ Số dòng khớp")
        # Kiểm tra timestamp
        timestamp_khop = all(
            str(g.start) == str(d.start) and str(g.end) == str(d.end)
            for g, d in zip(sub_goc, sub_dich)
        )
        if not timestamp_khop:
            bao_cao.append("- ❌ Timestamp KHÔNG khớp")
            co_loi = True
        else:
            bao_cao.append("- ✅ Timestamp khớp")
        # Kiểm tra index
        index_lien_tuc = all(g.index == d.index for g, d in zip(sub_goc, sub_dich))
        if not index_lien_tuc:
            bao_cao.append("- ❌ Index KHÔNG liên tục")
            co_loi = True
        else:
            bao_cao.append("- ✅ Index liên tục")

        # Check Hán tự còn sót (chỉ khi lang=zh)
        if args.lang == 'zh':
            text_goc_all = '\n'.join(s.text for s in sub_goc)
            text_dich_all = '\n'.join(s.text for s in sub_dich)
            ky_tu_goc = len(HAN_REGEX.findall(text_goc_all))
            ky_tu_dich = len(HAN_REGEX.findall(text_dich_all))
            pct_sot = (ky_tu_dich / ky_tu_goc * 100) if ky_tu_goc > 0 else 0
            bao_cao.append("")
            bao_cao.append("## Ký tự Hán")
            bao_cao.append(f"- Gốc: {ky_tu_goc} | Dịch còn sót: {ky_tu_dich} ({pct_sot:.1f}%)")
            if pct_sot > args.threshold:
                bao_cao.append(f"- ❌ Vượt ngưỡng {args.threshold}%")
                co_loi = True
            else:
                bao_cao.append(f"- ✅ Dưới ngưỡng {args.threshold}%")

        # Check glossary
        glossary = []
        if args.glossary:
            glossary += doc_glossary(args.glossary)
        if args.genre_glossary:
            glossary += doc_glossary(args.genre_glossary)
        if not glossary and args.book_slug:
            glossary += filter_for_book(load_all(), args.book_slug)
        if glossary:
            bao_cao.append("")
            bao_cao.append(f"## Glossary ({len(glossary)} mục)")
            text_dich_all = '\n'.join(s.text for s in sub_dich)
            loi_glossary = []
            loi_dich_sai = []
            for entry in glossary:
                source = (entry.get('source') or '').strip()
                target = (entry.get('target') or '').strip()
                if not source or not target or source == target:
                    continue
                if is_word_in_text(source, text_dich_all, args.lang == 'en'):
                    loi_glossary.append((source, target))
                if is_word_in_text(source, text_goc_all, args.lang == 'en') and not is_word_in_text(target, text_dich_all, True):
                    loi_dich_sai.append((source, target))
            if loi_glossary or loi_dich_sai:
                if loi_glossary:
                    bao_cao.append(f"- ❌ Có {len(loi_glossary)} thuật ngữ glossary còn sót (chưa dịch):")
                    for s, t in loi_glossary[:20]:
                        bao_cao.append(f"  - `{s}` → `{t}`")
                    if len(loi_glossary) > 20:
                        bao_cao.append(f"  - ... và {len(loi_glossary) - 20} mục")
                if loi_dich_sai:
                    bao_cao.append(f"- ❌ Có {len(loi_dich_sai)} thuật ngữ không dùng đúng target của glossary:")
                    for s, t in loi_dich_sai[:20]:
                        bao_cao.append(f"  - `{s}` đáng lẽ phải dịch là `{t}`")
                    if len(loi_dich_sai) > 20:
                        bao_cao.append(f"  - ... và {len(loi_dich_sai) - 20} mục")
                co_loi = True
            else:
                bao_cao.append("- ✅ Glossary OK")

        nd_bao_cao = '\n'.join(bao_cao)

    # In ra console (tóm tắt)
    if console:
        if co_loi:
            console.print(f"\n[bold red]❌ QA có lỗi:[/bold red] {args.translation}")
        else:
            console.print(f"\n[bold green]✅ QA hoàn thành:[/bold green] {args.translation}")
    else:
        prefix = "❌ QA có lỗi:" if co_loi else "✅ QA hoàn thành:"
        print(f"\n{prefix} {args.translation}")

    # Ghi báo cáo
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(nd_bao_cao, encoding='utf-8')
        if console:
            console.print(f"[dim]Báo cáo: {args.report}[/dim]")
        else:
            print(f"Báo cáo: {args.report}")

    # Exit code: 0 nếu OK, 1 nếu có lỗi (để CI/hook bắt được)
    sys.exit(1 if co_loi else 0)


if __name__ == '__main__':
    main()
