"""
chunk_text.py - Chia file Markdown thành các chunk theo ranh giới logic

Hỗ trợ 4 strategy:
  - smart (default): chapter → paragraph → sentence, never mid-sentence
  - paragraph: chia tại ranh giới đoạn
  - line: chia theo dòng (cho phụ đề/thơ)
  - fixed: giữ nguyên logic cũ (2000 từ, 200 overlap) — backward compatible

Output:
  - smart/paragraph/line → JSON files trong output-dir
  - fixed → Markdown files (như cũ)

Ví dụ:
    python scripts/chunk_text.py ^
        --input "working\extracted\$slug\raw.md" ^
        --output-dir "working\chunks\$slug" ^
        --strategy smart ^
        --max-chars 2000 ^
        --lang en
"""

import os
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding  # noqa: E402

# Heading Markdown (rank 1-6)
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# Markdown table: line starting with |
TABLE_LINE_RE = re.compile(r'^\|', re.MULTILINE)

# Manual marker
MANUAL_BREAK = '<!-- CHUNK_BREAK -->'

# Ký tự Hán
HAN_REGEX = re.compile(r'[㐀-鿿豈-﫿]')

# Sentence boundary regex - Cải tiến cho hội thoại (tiểu thuyết)
# Hỗ trợ bắt dấu câu kết thúc kèm theo ngoặc kép/ngoặc đơn
SENTENCE_BOUNDARY = re.compile(
    r'([.?!][\"\'”’)]?\s+(?=[A-ZÀ-Ỹ])|[\u3002\uff01\uff1f][\"\'”’)]?\s*)'
)

# Context window size (chars)
CONTEXT_CHARS = 200

def get_safe_context(text: str, is_prev: bool, chars: int = 200) -> str:
    """Lấy ngữ cảnh an toàn, không cắt ngang chữ ở hai đầu."""
    if len(text) <= chars:
        return text
    if is_prev:
        ctx = text[-chars:]
        # Tìm khoảng trắng đầu tiên để bỏ phần chữ bị đứt khúc
        first_space = ctx.find(' ')
        if first_space != -1 and first_space < 50:
            return ctx[first_space:].lstrip()
        return ctx
    else:
        ctx = text[:chars]
        # Tìm khoảng trắng cuối cùng để bỏ phần chữ bị đứt khúc
        last_space = ctx.rfind(' ')
        if last_space != -1 and (chars - last_space) < 50:
            return ctx[:last_space].rstrip()
        return ctx


STRATEGIES = ['smart', 'paragraph', 'line', 'fixed']


def dem_so_luong(text: str, lang: str) -> int:
    if lang == 'zh':
        return len(HAN_REGEX.findall(text))
    return len(re.findall(r'\b\w+\b', text))


def tach_theo_marker(text: str) -> list[str]:
    if MANUAL_BREAK not in text:
        return [text]
    parts = text.split(MANUAL_BREAK)
    return [p.strip() for p in parts if p.strip()]


def phat_hien_bang(text: str) -> list[tuple[int, int]]:
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if TABLE_LINE_RE.match(line):
            start = i
            while i < len(lines) and TABLE_LINE_RE.match(lines[i].strip()):
                i += 1
            end = i
            if end - start >= 2:
                blocks.append((start, end))
        else:
            i += 1
    return blocks


def tach_theo_heading(text: str) -> list[tuple[str, str]]:
    """Tách theo heading. Trả về [(heading, body)]."""
    result = []
    current_heading = ''
    current_body = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            if current_body or current_heading:
                result.append((current_heading, '\n'.join(current_body).strip()))
            current_heading = line
            current_body = []
        else:
            current_body.append(line)
    if current_body or current_heading:
        result.append((current_heading, '\n'.join(current_body).strip()))
    return [(h, b) for h, b in result if h or b]


def tach_theo_doan(text: str) -> list[str]:
    """Tách theo đoạn văn, bảo vệ block table markdown."""
    table_blocks = phat_hien_bang(text)
    table_lines = set()
    for start, end in table_blocks:
        for i in range(start, end):
            table_lines.add(i)
    paragraphs = re.split(r'\n\s*\n', text)
    result = []
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i].strip()
        p_lines = p.splitlines()
        has_table_start = any(TABLE_LINE_RE.match(l.strip()) for l in p_lines)
        has_table_end = any(TABLE_LINE_RE.match(l.strip()) for l in p_lines)
        if has_table_start or has_table_end:
            merged = p
            while i + 1 < len(paragraphs):
                next_p = paragraphs[i + 1].strip()
                next_lines = next_p.splitlines()
                next_starts_table = any(TABLE_LINE_RE.match(l.strip()) for l in next_lines)
                if next_starts_table:
                    merged += '\n\n' + next_p
                    i += 1
                else:
                    break
            result.append(merged)
        else:
            result.append(p)
        i += 1
    return [p for p in result if p]


def cat_overlap_an_toan(text: str, target_chars: int, lang: str = 'en') -> str:
    """Cắt overlap an toàn - tìm biên giới câu/từ gần vị trí target."""
    if target_chars <= 0 or len(text) <= target_chars:
        return text
    cut_pos = len(text) - target_chars
    candidate = text[cut_pos:]
    boundary_patterns = [
        r'\n\n',
        r'\.\s*\n',
        r'\.[\s\"]',
        r'[\u3002\uff01\uff1f]\s*',
        r'\s',
    ]
    for pat in boundary_patterns:
        m = re.search(pat, candidate[:300])
        if m:
            return text[cut_pos + m.end():]
    return candidate


def gop_thanh_chunk(
    sections: list[tuple[str, str]],
    min_size: int,
    max_size: int,
    overlap_size: int,
    lang: str,
) -> list[str]:
    """Gộp các đoạn thành chunk theo kích thước min/max (logic cũ)."""
    chunks = []
    chunk_hien_tai = ''
    kich_thuoc_hien_tai = 0
    overlap_text = ''

    for heading, body in sections:
        doan_text = (heading + '\n' + body).strip() if heading else body
        if not doan_text:
            continue
        doan_size = dem_so_luong(doan_text, lang)

        if doan_size > max_size:
            if chunk_hien_tai:
                chunks.append(chunk_hien_tai.strip())
                overlap_text = cat_overlap_an_toan(chunk_hien_tai, overlap_size * 2, lang) if overlap_size > 0 else ''
                chunk_hien_tai = ''
                kich_thuoc_hien_tai = 0

            cac_doan_nho = tach_theo_doan(body)
            for doan in cac_doan_nho:
                doan_full = doan
                doan_size_full = dem_so_luong(doan_full, lang)
                if kich_thuoc_hien_tai + doan_size_full > max_size and chunk_hien_tai:
                    chunks.append(chunk_hien_tai.strip())
                    overlap_text = cat_overlap_an_toan(chunk_hien_tai, overlap_size * 2, lang) if overlap_size > 0 else ''
                    chunk_hien_tai = overlap_text
                    kich_thuoc_hien_tai = dem_so_luong(overlap_text, lang)
                if kich_thuoc_hien_tai == 0:
                    chunk_hien_tai = (heading + '\n' + doan_full).strip() if heading else doan_full
                else:
                    chunk_hien_tai += '\n\n' + doan_full
                kich_thuoc_hien_tai = dem_so_luong(chunk_hien_tai, lang)
            continue

        if kich_thuoc_hien_tai + doan_size <= max_size:
            if kich_thuoc_hien_tai == 0:
                chunk_hien_tai = doan_text
            else:
                chunk_hien_tai += '\n\n' + doan_text
            kich_thuoc_hien_tai += doan_size
        else:
            if chunk_hien_tai:
                chunks.append(chunk_hien_tai.strip())
                overlap_text = cat_overlap_an_toan(chunk_hien_tai, overlap_size * 2, lang) if overlap_size > 0 else ''
                chunk_hien_tai = overlap_text
                kich_thuoc_hien_tai = dem_so_luong(overlap_text, lang)
            chunk_hien_tai += '\n\n' + doan_text if chunk_hien_tai else doan_text
            kich_thuoc_hien_tai += doan_size

    if chunk_hien_tai:
        chunks.append(chunk_hien_tai.strip())

    return chunks


def canh_bao_chunk_cuoi_nho(chunks: list[str], min_size: int, lang: str) -> None:
    if not chunks:
        return
    last = chunks[-1]
    last_size = dem_so_luong(last, lang)
    if last_size < min_size * 0.5 and len(chunks) > 1:
        print(f"  \u26a0\ufe0f Chunk cu\u1ed1i ({last_size} \u0111\u01a1n v\u1ecb) < 50% min_size ({min_size}). C\u00f3 th\u1ec3 do input ng\u1eafn ho\u1eb7c ranh gi\u1edbi kh\u00f4ng \u0111\u1ec1u.")


def tach_cau(text: str) -> list[str]:
    """Tách text thành các câu, giữ delimiter và xử lý ngoặc kép hội thoại."""
    sentences = []
    # Sử dụng SENTENCE_BOUNDARY để cắt
    parts = re.split(SENTENCE_BOUNDARY, text)
    
    buf = ''
    for i in range(0, len(parts), 2):
        chunk = parts[i]
        delim = parts[i+1] if i+1 < len(parts) else ''
        buf += chunk + delim
        if delim:
            sentences.append(buf.strip())
            buf = ''
            
    if buf.strip():
        sentences.append(buf.strip())
    
    return [s for s in sentences if s.strip()]


def get_chapter_name(heading: str) -> str:
    """Extract chapter name from heading line, or return empty string."""
    if not heading:
        return ''
    m = HEADING_RE.match(heading)
    if m:
        return m.group(2).strip()
    return heading.strip()


def chunk_smart(text: str, max_chars: int, min_chars: int, lang: str) -> list[dict]:
    """Smart chunking: chapter → paragraph → sentence boundaries."""
    units = []
    current_chapter = ''
    sections = tach_theo_heading(text)

    for heading, body in sections:
        chapter = get_chapter_name(heading) if heading else current_chapter
        if heading:
            current_chapter = chapter
        # Split body into paragraphs
        paragraphs = tach_theo_doan(body)
        first = True
        for para in paragraphs:
            if not para.strip():
                continue
            text = (heading + '\n\n' + para) if first and heading else para
            units.append({
                'chapter': chapter,
                'heading': heading,
                'text': text,
                'size': dem_so_luong(text, lang),
            })
            first = False

    # Build chunks by combining units
    chunks_raw = []
    current_chunk = []
    current_size = 0
    current_chapter = ''

    for unit in units:
        u_size = unit['size']
        u_text = unit['text']
        u_chapter = unit['chapter']
        u_heading = unit['heading']

        # If this unit alone exceeds max, split by sentences
        if u_size > max_chars:
            if current_chunk:
                chunks_raw.append((current_chapter, current_chunk))
                current_chunk = []
                current_size = 0

            sentences = tach_cau(u_text)
            for sent in sentences:
                s_size = dem_so_luong(sent, lang)
                if current_size + s_size > max_chars and current_chunk:
                    chunks_raw.append((current_chapter, current_chunk))
                    current_chunk = []
                    current_size = 0
                current_chunk.append(sent)
                current_size += s_size
                if u_chapter:
                    current_chapter = u_chapter

            if current_chunk:
                chunks_raw.append((current_chapter, current_chunk))
                current_chunk = []
                current_size = 0
            continue

        # Normal unit
        if current_size + u_size > max_chars and current_chunk:
            # Check if still below min_chars — if so, keep going
            if current_size >= min_chars or current_size + u_size > max_chars * 1.5:
                chunks_raw.append((current_chapter, current_chunk))
                current_chunk = []
                current_size = 0

        if u_heading:
            current_chapter = u_chapter
            # Chỉ bẻ chunk mới tại Heading nếu chunk hiện tại đã đủ lớn (>= min_chars)
            if current_chunk and current_size >= min_chars:
                chunks_raw.append((current_chapter, current_chunk))
                current_chunk = []
                current_size = 0
                current_chunk.append(u_text)
                current_size = u_size
            else:
                current_chunk.append(u_text)
                current_size += u_size
        else:
            current_chunk.append(u_text)
            current_size += u_size

    if current_chunk:
        chunks_raw.append((current_chapter, current_chunk))

    # Convert to dict format with context
    full_texts = ['\n\n'.join(parts) for chapter, parts in chunks_raw]
    
    # Lọc bỏ các chunk hoàn toàn không có chữ (size = 0)
    valid_texts = [txt for txt in full_texts if dem_so_luong(txt, lang) > 0]
    
    result = []
    total = len(valid_texts)

    for i, text in enumerate(valid_texts):
        prev_ctx = ''
        next_ctx = ''

        if i > 0:
            prev_ctx = get_safe_context(valid_texts[i - 1], is_prev=True, chars=CONTEXT_CHARS)
        if i < total - 1:
            next_ctx = get_safe_context(valid_texts[i + 1], is_prev=False, chars=CONTEXT_CHARS)

        # Determine chapter from first heading in text
        chapter = ''
        for line in text.splitlines():
            m = HEADING_RE.match(line)
            if m:
                chapter = m.group(2).strip()
                break

        result.append({
            'chunk_id': i,
            'total_chunks': total,
            'chapter': chapter,
            'text': text,
            'prev_context': prev_ctx,
            'next_context': next_ctx,
            'word_count': dem_so_luong(text, lang),
        })

    return result


def chunk_by_paragraph(text: str, max_chars: int, min_chars: int, lang: str) -> list[dict]:
    """Chunk by paragraph boundaries only."""
    paragraphs = tach_theo_doan(text)
    chunks_raw = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        if not para.strip():
            continue
        p_size = dem_so_luong(para, lang)

        if current_size + p_size > max_chars and current_chunk:
            chunks_raw.append('\n\n'.join(current_chunk))
            current_chunk = []
            current_size = 0

        current_chunk.append(para)
        current_size += p_size

    if current_chunk:
        chunks_raw.append('\n\n'.join(current_chunk))

    full_texts = chunks_raw
    result = []
    total = len(full_texts)

    for i, text in enumerate(full_texts):
        prev_ctx = ''
        next_ctx = ''
        if i > 0:
            prev_ctx = get_safe_context(full_texts[i - 1], is_prev=True, chars=CONTEXT_CHARS)
        if i < total - 1:
            next_ctx = get_safe_context(full_texts[i + 1], is_prev=False, chars=CONTEXT_CHARS)

        chapter = ''
        for line in text.splitlines():
            m = HEADING_RE.match(line)
            if m:
                chapter = m.group(2).strip()
                break

        result.append({
            'chunk_id': i,
            'total_chunks': total,
            'chapter': chapter,
            'text': text,
            'prev_context': prev_ctx,
            'next_context': next_ctx,
            'word_count': dem_so_luong(text, lang),
        })

    return result


def chunk_by_line(text: str, max_chars: int, min_chars: int, lang: str) -> list[dict]:
    """Chunk by line boundaries (for subtitles/poetry)."""
    lines = [l for l in text.splitlines() if l.strip()]
    chunks_raw = []
    current_chunk = []
    current_size = 0

    for line in lines:
        l_size = dem_so_luong(line, lang)
        if current_size + l_size > max_chars and current_chunk:
            chunks_raw.append('\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += l_size

    if current_chunk:
        chunks_raw.append('\n'.join(current_chunk))

    full_texts = chunks_raw
    result = []
    total = len(full_texts)

    for i, text in enumerate(full_texts):
        prev_ctx = ''
        next_ctx = ''
        if i > 0:
            prev_ctx = get_safe_context(full_texts[i - 1], is_prev=True, chars=CONTEXT_CHARS)
        if i < total - 1:
            next_ctx = get_safe_context(full_texts[i + 1], is_prev=False, chars=CONTEXT_CHARS)

        chapter = ''

        result.append({
            'chunk_id': i,
            'total_chunks': total,
            'chapter': chapter,
            'text': text,
            'prev_context': prev_ctx,
            'next_context': next_ctx,
            'word_count': dem_so_luong(text, lang),
        })

    return result


def write_json_chunks(chunks: list[dict], output_dir: Path, prefix: str = 'chunk') -> None:
    """Write chunks as JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for chunk in chunks:
        cid = chunk['chunk_id']
        fname = output_dir / f"{prefix}-{cid:03d}.json"
        fname.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  \u2713 {fname.name} ({chunk['word_count']} \u0111\u01a1n v\u1ecb)")


def write_markdown_chunks(chunks: list[str], output_dir: Path, prefix: str = 'chunk', lang: str = 'en') -> None:
    """Write chunks as Markdown files (backward compatible)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, chunk in enumerate(chunks, 1):
        ten_file = output_dir / f"{prefix}-{i:03d}.md"
        ten_file.write_text(chunk, encoding='utf-8')
        kich_thuoc = dem_so_luong(chunk, lang)
        print(f"  \u2713 {ten_file.name} ({kich_thuoc} \u0111\u01a1n v\u1ecb)")


def process_fixed(text: str, args) -> tuple[list[str], list[str]]:
    """Process with fixed strategy (old behavior). Returns markdown chunks list."""
    if not args.manual_markers and MANUAL_BREAK in text:
        dem = text.count(MANUAL_BREAK)
        text = text.replace(MANUAL_BREAK, '')
        print(f"  \u26a0\ufe0f T\u00ecm th\u1ea5y {dem} manual marker trong input nh\u01b0ng KH\u00d4NG d\u00f9ng --manual-markers \u2192 \u0111\u00e3 strip kh\u1ecfi text")

    if args.manual_markers and MANUAL_BREAK in text:
        marker_parts = tach_theo_marker(text)
        print(f"T\u00e1ch theo manual marker: {len(marker_parts)} ph\u1ea7n")
    else:
        marker_parts = [text]

    if args.respect_headings:
        all_sections = []
        for part in marker_parts:
            all_sections.extend(tach_theo_heading(part))
        print(f"T\u00e1ch theo heading: {len(all_sections)} section")
    else:
        all_sections = [('', p) for p in marker_parts]

    chunks = gop_thanh_chunk(
        all_sections,
        min_size=args.min_chars,
        max_size=args.max_chars,
        overlap_size=args.overlap_chars,
        lang=args.lang,
    )
    return chunks


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Chia file Markdown thành chunk theo ranh giới logic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File Markdown đầu vào')
    parser.add_argument('--output-dir', type=Path, required=True, help='Thư mục chứa các chunk')
    parser.add_argument('--lang', choices=['en', 'zh'], default='en', help='Ngôn ngữ (en: đếm từ, zh: đếm chữ Hán)')
    parser.add_argument('--strategy', choices=STRATEGIES, default='smart', help='Chiến lược chunking (mặc định: smart)')
    parser.add_argument('--min-chars', type=int, default=500, help='Kích thước tối thiểu/chunk (từ hoặc chữ Hán)')
    parser.add_argument('--max-chars', type=int, default=2000, help='Kích thước tối đa/chunk')
    parser.add_argument('--overlap-chars', type=int, default=200, help='Số ký tự overlap giữa các chunk (chỉ dùng cho strategy=fixed)')
    parser.add_argument('--respect-headings', dest='respect_headings', action='store_true', help='Ưu tiên ranh giới heading (chỉ dùng cho strategy=fixed)')
    parser.add_argument('--no-respect-headings', dest='respect_headings', action='store_false', help='Không ưu tiên ranh giới heading')
    parser.add_argument('--manual-markers', action='store_true', help='Tách theo manual marker <!-- CHUNK_BREAK --> trước (chỉ dùng cho strategy=fixed)')
    parser.add_argument('--prefix', type=str, default='chunk', help='Tiền tố tên file (mặc định: chunk)')

    parser.set_defaults(respect_headings=True)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"[L\u1ed6I] File kh\u00f4ng t\u1ed3n t\u1ea1i: {args.input}", file=sys.stderr)
        sys.exit(1)

    text = args.input.read_text(encoding='utf-8-sig')
    print(f"\u0110\u1ecdc: {args.input} ({dem_so_luong(text, args.lang)} \u0111\u01a1n v\u1ecb)")
    print(f"Strategy: {args.strategy}")

    if args.strategy == 'fixed':
        chunks_md = process_fixed(text, args)
        n_chunks = len(chunks_md)
        print(f"T\u1ea1o \u0111\u01b0\u1ee3c {n_chunks} chunk")
        canh_bao_chunk_cuoi_nho(chunks_md, args.min_chars, args.lang)
        write_markdown_chunks(chunks_md, args.output_dir, args.prefix, args.lang)
    else:
        strategy_map = {
            'smart': chunk_smart,
            'paragraph': chunk_by_paragraph,
            'line': chunk_by_line,
        }
        chunk_fn = strategy_map[args.strategy]
        chunks = chunk_fn(text, args.max_chars, args.min_chars, args.lang)
        n_chunks = len(chunks)
        print(f"T\u1ea1o \u0111\u01b0\u1ee3c {n_chunks} chunk")
        write_json_chunks(chunks, args.output_dir, args.prefix)

    print(f"\nHo\u00e0n th\u00e0nh: {n_chunks} chunk trong {args.output_dir}")


if __name__ == '__main__':
    main()
