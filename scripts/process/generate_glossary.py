"""
generate_glossary.py - Tạo prompt cho Agent để sinh glossary CSV

Đọc source text từ working/extracted/ hoặc working/chunks/,
tạo prompt file tại working/glossary_prompt.txt.
Agent đọc prompt này và tự tạo glossary CSV -> lưu vào glossary/{book_name}.csv.

Ví dụ:
    python scripts/generate_glossary.py ^
        --source "working\extracted\mybook\raw.md" ^
        --book-name "mybook"

    python scripts/generate_glossary.py ^
        --source-dir "working\chunks\mybook" ^
        --book-name "mybook" ^
        --max-chars 8000

    python scripts/generate_glossary.py ^
        --source "working\extracted\mybook\raw.md" ^
        --book-name "mybook" ^
        --merge-genre "tien-hiep"
"""

import os
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT


def _read_profile(profile_dir: Path, slug: str) -> str | None:
    """Đọc profile văn chương của cuốn, trả về các section hữu ích cho glossary."""
    p = profile_dir / f"{slug}.md"
    if not p.exists():
        return None
    raw = ''
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            raw = p.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if not raw.strip():
        return None

    lines = raw.splitlines()
    ctx_parts = []

    # Trích section quan trọng: xưng hô, thành ngữ, đặc trưng ngôn ngữ
    section_titles = {
        'Hệ xưng hô': [],
        'Thành ngữ': [],
        'Đặc trưng ngôn ngữ': [],
        'Cách xử lý hội thoại': [],
        'Lưu ý riêng': [],
    }
    current_title = None
    for line in lines:
        stripped = line.strip()
        # Detect H2 headers
        if stripped.startswith('## '):
            header = stripped[3:].strip().lower()
            for key in section_titles:
                if key.lower() in header:
                    current_title = key
                    break
            else:
                current_title = None
        elif current_title and stripped.startswith('- ') and len(stripped) < 120:
            section_titles[current_title].append(stripped)

    # Chỉ bao gồm section có content thực sự
    for title, items in section_titles.items():
        if items:
            ctx_parts.append(f"\n**{title}:**")
            ctx_parts.extend(f"- {item}" for item in items[:8])  # max 8 items/section

    if not ctx_parts:
        return None

    return '\n'.join(ctx_parts)


PROFILE_CONTEXT_INJECTION = r"""
--- BỐI CẢNH VĂN CHƯƠNG CỦA CUỐN SÁCH ---
{profile_context}
--- KẾT THÚC BỐI CẢNH ---

Khi trích thuật ngữ, áp dụng các quy tắc sau:
- KHÔNG đưa vào glossary những từ phổ thông xuất hiện trong phần bối cảnh trên
  (ví dụ: "女人" nếu sách này dùng nó như từ bình thường, không phải tên riêng/khái niệm cốt lõi).
- Ưu tiên các nhân vật, địa danh, tổ chức, khái niệm được nhắc đến trong bối cảnh.
- Với tên Hán: chú ý cách sách này xử lý (theo phần hệ xưng hô / lưu ý riêng).
- Nếu profile có gợi ý phong cách dịch cụ thể, bám theo đó khi chọn target.
"""


PROMPT_TEMPLATE = """Bạn là một chuyên gia ngôn ngữ và biên tập viên dịch thuật sách cao cấp.
Nhiệm vụ của bạn là đọc kỹ văn bản mẫu của cuốn sách dưới đây và trích xuất TOÀN BỘ BẢNG THUẬT NGỮ & NGỮ CẢNH CỐT LÕI phục vụ cho dịch thuật.

HÃY TRÍCH XUẤT ĐẦY ĐỦ CÁC DANH MỤC SAU:
1. Nhân vật (Character names & Nicknames): Tên nhân vật, biệt danh, vai trò (nhân vật chính, phụ, mẹ, chồng, sếp...).
2. Hệ xưng hô & Quan hệ nhân vật (Pronouns & Relationship Context):
   - Quan trọng: Cách nhân vật xưng hô với nhau (VD: "林总" → Sếp Lâm; "小李" → Tiểu Lý; "阿姨" → Dì/Bác).
3. Địa danh & Không gian (Place names): Tên thành phố, công ty, trường học, địa điểm gắn liền với cốt truyện.
4. Thuật ngữ chuyên ngành / Văn hóa / Pháp bảo / Cảnh giới (Domain & Core concepts):
   - Từ ngữ chuyên môn (y học, tâm lý học, kinh tế học, tu tiên, chiêu thức...).
5. Cụm từ triết lý / Châm ngôn chủ đạo của cuốn sách (Core catchphrases / Theme phrases).

ĐỊNH DẠNG ĐẦU RA BẮT BUỘC (Đúng chuẩn CSV, KHÔNG giải thích thêm, KHÔNG dùng markdown block ```):
source,target,notes

QUY TẮC CHẤT LƯỢNG VĂN CHƯƠNG — BÁM SÁT NGỮ CẢNH:
- KHÔNG đưa các từ phổ thông hàng ngày không có nghĩa đặc thù (VD: 女人, 吃饭, 跑步, 很高兴).
- CHỈ GIỮ từ có sắc thái biểu cảm, phong cách hoặc vai trò cốt truyện.
- "notes" PHẢI ghi rõ vai trò/ngữ cảnh (VD: "nhân vật chính", "chồng cũ của nữ chính", "khái niệm triết lý sống", "chiêu thức").

MẪU VĂN BẢN TRÍCH XUẤT TỪ CUỐN SÁCH:
{text}
"""


def doc_text(file_path: Path) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1'):
        try:
            return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"Kh\u00f4ng th\u1ec3 \u0111\u1ecdc {file_path}")


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="T\u1ea1o prompt cho Agent \u0111\u1ec3 sinh glossary CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--source', type=Path,
                              help='File source text (\u01b0u ti\u00ean: working/extracted/{book}/raw.md)')
    source_group.add_argument('--source-dir', type=Path,
                              help='Th\u01b0 m\u1ee5c ch\u1ee9a c\u00e1c file chunk JSON (working/chunks/{book}/)')
    parser.add_argument('--book-name', type=str, required=True,
                        help='T\u00ean s\u00e1ch (\u0111\u1eb7t t\u00ean file prompt v\u00e0 glossary output)')
    parser.add_argument('--max-chars', type=int, default=10000,
                        help='S\u1ed1 k\u00fd t\u1ef1 t\u1ed1i \u0111a cho preview text (m\u1eb7c \u0111\u1ecbnh: 10000)')
    parser.add_argument('--merge-genre', type=str,
                        help='Merge glossary m\u1edbi v\u00e0o glossary/genres/{genre}.csv hi\u1ec7n c\u00f3 (VD: "tien-hiep")')
    parser.add_argument('--output', type=Path,
                        help='File output prompt (mặc định: working/glossary_prompt_{book_name}.txt)')

    args = parser.parse_args()

    PROFILE_DIR = PROJECT_ROOT / 'working' / 'profile'

    # --- Bước 0: Tự đọc profile văn chương nếu có (cung cấp bối cảnh cho AI) ---
    profile_ctx = _read_profile(PROFILE_DIR, args.book_name)
    if profile_ctx:
        print(f"\n\u0110\u00e3 tìm thấy profile văn chương: {PROFILE_DIR}/{args.book_name}.md")
        print("   Injecting vào prompt...")
    else:
        print(f"\n\u2139\ufe0f Không có profile ({PROFILE_DIR}/{args.book_name}.md) — chạy ở chế độ cơ bản.")

    # Đọc source text
    text = ''
    if args.source:
        if not args.source.exists():
            print(f"[L\u1ed6I] File kh\u00f4ng t\u1ed3n t\u1ea1i: {args.source}", file=sys.stderr)
            sys.exit(1)
        text = doc_text(args.source)
        print(f"\u0110\u1ecdc: {args.source} ({len(text)} k\u00fd t\u1ef1)")
    elif args.source_dir:
        if not args.source_dir.exists():
            print(f"[L\u1ed6I] Th\u01b0 m\u1ee5c kh\u00f4ng t\u1ed3n t\u1ea1i: {args.source_dir}", file=sys.stderr)
            sys.exit(1)
        # Sort numerically by extracting digits from filename to handle >999 chunks
        import re
        json_files = sorted(args.source_dir.glob('*.json'), key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
        if not json_files:
            print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y file JSON n\u00e0o trong {args.source_dir}", file=sys.stderr)
            sys.exit(1)
        texts = []
        for f in json_files:
            try:
                import json as _json
                data = _json.loads(doc_text(f))
                texts.append(data.get('text', ''))
            except Exception:
                continue
        text = '\n\n'.join(texts)
        print(f"\u0110\u1ecdc {len(json_files)} file chunk t\u1eeb {args.source_dir} ({len(text)} k\u00fd t\u1ef1)")

    if not text.strip():
        print("[L\u1ed6I] Kh\u00f4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c n\u1ed9i dung", file=sys.stderr)
        sys.exit(1)

    # Lấy mẫu trải đều (Đầu, Giữa, Cuối) nếu văn bản quá dài
    if len(text) > args.max_chars * 1.5:
        part_size = args.max_chars // 3
        
        start_text = text[:part_size]
        mid_idx = len(text) // 2 - part_size // 2
        mid_text = text[mid_idx:mid_idx + part_size]
        end_text = text[-part_size:]
        
        # Cố gắng cắt gọn gàng tại các dòng mới
        def clean_chunk(chunk_text, is_start=False, is_end=False):
            start_cut = 0 if is_start else chunk_text.find('\n')
            if start_cut == -1: start_cut = 0
            end_cut = len(chunk_text) if is_end else chunk_text.rfind('\n')
            if end_cut <= 0: end_cut = len(chunk_text)
            return chunk_text[start_cut:end_cut].strip()

        start_text = clean_chunk(start_text, is_start=True)
        mid_text = clean_chunk(mid_text)
        end_text = clean_chunk(end_text, is_end=True)
        
        preview = (
            "--- PH\u1ea6N \u0110\u1ea6U TRUY\u1ec6N ---\n" + start_text + "\n\n" +
            "--- PH\u1ea6N GI\u1eeeA TRUY\u1ec6N ---\n" + mid_text + "\n\n" +
            "--- PH\u1ea6N CU\u1ed0I TRUY\u1ec6N ---\n" + end_text
        )
        print(f"  (L\u1ea5y m\u1eabu \u0110\u1ea7u-Gi\u1eefa-Cu\u1ed1i t\u1eeb {len(text)} k\u00fd t\u1ef1, xu\u1ed1ng c\u00f2n {len(preview)} k\u00fd t\u1ef1)")
    else:
        preview = text[:args.max_chars]
        if len(text) > args.max_chars:
            last_period = preview.rfind('.')
            last_newline = preview.rfind('\n')
            cut = max(last_period, last_newline)
            if cut > args.max_chars * 0.5:
                preview = preview[:cut + 1]
            print(f"  (cắt từ {len(text)} ký tự xuống {len(preview)} ký tự)")

    # --- Bước cuối: Format prompt với profile context injection ---
    prompt_content = PROMPT_TEMPLATE.format(text=preview)

    # Inject profile context nếu có (cung cấp bối cảnh văn chương cho AI)
    if profile_ctx:
        final_prompt = PROFILE_CONTEXT_INJECTION.replace('{profile_context}', profile_ctx) + '\n\n' + prompt_content
    else:
        final_prompt = prompt_content

    output_path = args.output or (PROJECT_ROOT / 'working' / f'glossary_prompt_{args.book_name}.txt')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_prompt, encoding='utf-8')

    print(f"\n\u2705 \u0110\u00e3 t\u1ea1o prompt file: {output_path}")
    print(f"  Dung l\u01b0\u1ee3ng: {len(final_prompt)} k\u00fd t\u1ef1")
    print(f"\n  B\u01b0\u1edbc ti\u1ebfp: \u0110\u1ecdc file prompt và yêu cầu Agent tạo glossary CSV")
    print(f"  Lưu glossary vào: glossary/{args.book_name}.csv")

    if args.merge_genre:
        genre_file = PROJECT_ROOT / 'glossary' / 'genres' / f'{args.merge_genre}.csv'
        if genre_file.exists():
            print(f"\n  \u0110\u00e3 tìm thấy glossary/genres/{args.merge_genre}.csv")
            print(f"  Sau khi Agent tạo CSV, chạy merge thủ công hoặc copy các mục mới vào file này.")
        else:
            print(f"\n  \u26a0\ufe0f Chưa có glossary/genres/{args.merge_genre}.csv")
            print(f"  Tạo file mới khi Agent trả về glossary.")


if __name__ == '__main__':
    main()