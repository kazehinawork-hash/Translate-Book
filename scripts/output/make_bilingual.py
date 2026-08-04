"""
make_bilingual.py - Ghép file gốc + bản dịch thành file song ngữ

Ghép từng đoạn: gốc (đậm, có Pinyin nếu ZH) xen kẽ với bản dịch Việt.

Input:
  --source: working/extracted/<slug>/raw.md (hoặc raw-hans.md)
            Hoặc chunk cụ thể: working/chunks/<slug>/chunk-XXX.md
  --translation: output/<slug>/<slug>-vi.md
                 Hoặc chunk cụ thể: output/<slug>/chunk-XXX.md
  --output: output/<slug>/<slug>-songngu.md
  --lang: en|zh
  --report: working/qa/<slug>/bilingual-align.md

Ví dụ:
    python scripts/make_bilingual.py ^
        --source "working\\extracted\\nu-zi\\raw.md" ^
        --translation "output\\nu-zi\\nu-zi-vi.md" ^
        --output "output\\nu-zi\\nu-zi-songngu.md" ^
        --lang zh ^
        --report "working\\qa\\nu-zi\\bilingual-align.md"

    # Kiểm tra trước (chỉ xuất report, không ghi file):
    python scripts/make_bilingual.py --check ^
        --source "working\\extracted\\nu-zi\\raw.md" ^
        --translation "output\\nu-zi\\nu-zi-vi.md" ^
        --lang zh

    # Xem trước 1 chunk:
    python scripts/make_bilingual.py ^
        --source "working\\chunks\\nu-zi\\chunk-001.md" ^
        --translation "output\\nu-zi\\chunk-001.md" ^
        --lang zh
"""

import os
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None

from pinyin_utils import text_to_pinyin, has_han

# ─── Regex ───────────────────────────────────────────────────────────────

HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# Code block / table fences
FENCE_RE = re.compile(r'^(```|~~~|<?\|)', re.MULTILINE)


# ─── Tách đoạn ───────────────────────────────────────────────────────────

def is_heading(line: str) -> bool:
    return bool(HEADING_RE.match(line.strip()))


def split_paragraphs(text: str) -> list[str]:
    """Tách text thành các đoạn theo \\n\\s*\\n (giống chunk_text.py)."""
    parts = re.split(r'\n\s*\n', text)
    return [p.strip() for p in parts if p.strip()]


def classify_paragraph(para: str) -> str:
    """Phân loại đoạn: 'heading', 'code', 'table', 'image', 'text'."""
    lines = para.split('\n')
    first_line = lines[0].strip()

    # Heading
    if is_heading(first_line):
        return 'heading'

    # Code block (fenced)
    if first_line.startswith('```') or first_line.startswith('~~~'):
        return 'code'

    # Table
    if first_line.startswith('|'):
        return 'table'

    # Image
    if first_line.startswith('![') and len(lines) <= 3:
        return 'image'

    return 'text'


def extract_heading_level(para: str) -> int:
    """Trích xuất cấp heading (1-6). Trả về 0 nếu không phải heading."""
    m = HEADING_RE.match(para.split('\n')[0].strip())
    if m:
        return len(m.group(1))
    return 0


# ─── Căn chỉnh đoạn ─────────────────────────────────────────────────────

def align_paragraphs(
    src_paras: list[str],
    vi_paras: list[str],
    lang: str = 'en',
) -> list[tuple]:
    """
    Căn chỉnh 2 danh sách đoạn.

    Trả về list tuple: (src_chunk, vi_chunk, status)
    status: 'ok', 'check', 'src-only', 'vi-only'

    Thuật toán:
    1. Headings là neo cứng — tìm vị trí tương ứng.
    2. giữa 2 neo liên tiếp, dùng DP để ghép đoạn.
    3. DP cho phép: 1:1, 2:1, 1:2 (theo tỉ lệ độ dài).
    """
    result = []

    # Phân loại
    src_types = [classify_paragraph(p) for p in src_paras]
    vi_paras_split = _split_vi_heading_paragraphs(vi_paras)
    vi_types = [classify_paragraph(p) for p in vi_paras_split]

    # Tìm vị trí headings trong cả 2
    src_headings = [(i, src_types[i]) for i in range(len(src_types)) if src_types[i] == 'heading']
    vi_headings = [(i, vi_types[i]) for i in range(len(vi_types)) if vi_types[i] == 'heading']

    # Tạo danh sách "segments" — mỗi segment gồm heading + body paragraphs
    # Sau đó align segments
    src_segments = _build_segments(src_paras, src_types)
    vi_segments = _build_segments(vi_paras_split, vi_types)

    # Align segments
    aligned = _align_segments(src_segments, vi_segments, lang)

    return aligned


def _build_segments(paras: list[str], types: list[str]) -> list[dict]:
    """Build segments: each segment = heading + following non-heading paragraphs."""
    segments = []
    current = {'heading': None, 'heading_idx': -1, 'body': [], 'body_indices': []}

    for i, (para, typ) in enumerate(zip(paras, types)):
        if typ == 'heading':
            if current['heading'] is not None or current['body']:
                segments.append(current)
            current = {'heading': para, 'heading_idx': i, 'body': [], 'body_indices': []}
        else:
            current['body'].append(para)
            current['body_indices'].append(i)

    if current['heading'] is not None or current['body']:
        segments.append(current)

    return segments


def _split_heading_body(para: str) -> tuple[str, str]:
    """Split a heading paragraph into (heading_line, body_text).
    Returns ('', para) if not a heading or no body after heading.
    """
    if not is_heading(para):
        return ('', para)
    lines = para.split('\n', 1)
    heading = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else ''
    return (heading, body)


def _split_vi_heading_paragraphs(vi_paras: list[str]) -> list[str]:
    """Split Vietnamese paragraphs that start with a heading into separate heading + body.

    Vietnamese translations sometimes merge heading + body into one paragraph,
    while the source has them separate. This function splits them for proper alignment.
    """
    result = []
    for para in vi_paras:
        first_line = para.split('\n')[0].strip()
        if is_heading(first_line):
            lines = para.split('\n', 1)
            heading = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ''
            result.append(heading)
            if body:
                result.append(body)
        else:
            result.append(para)
    return result


def _align_segments(
    src_segments: list[dict],
    vi_segments: list[dict],
    lang: str = 'en',
) -> list[tuple]:
    """Align segments between source and translation."""
    result = []
    si = 0  # source segment index
    ti = 0  # translation segment index

    while si < len(src_segments) and ti < len(vi_segments):
        src_seg = src_segments[si]
        vi_seg = vi_segments[ti]

        # Cả 2 đều có heading
        if src_seg['heading'] and vi_seg['heading']:
            # Check if source heading has body text embedded
            src_heading_line, src_heading_body = _split_heading_body(src_seg['heading'])

            # Ghép heading
            result.append((src_seg['heading'], vi_seg['heading'], 'ok'))

            # Combine source heading body + segment body for alignment
            src_body = list(src_seg['body'])
            if src_heading_body:
                src_body.insert(0, src_heading_body)

            # Align body paragraphs
            body_align = _align_body(src_body, vi_seg['body'], lang)
            result.extend(body_align)
            si += 1
            ti += 1

            # Chỉ source có heading → source ahead
        elif src_seg['heading'] and not vi_seg['heading']:
            # Có thể heading bị dịch trong đoạn body của vi
            # Thử match heading tiếp theo của vi
            found = False
            for lookahead in range(ti, min(ti + 3, len(vi_segments))):
                if vi_segments[lookahead]['heading']:
                    # Gap segments ở vi không có heading → ghép body
                    for j in range(ti, lookahead):
                        body_align = _align_body([], vi_segments[j]['body'], lang)
                        result.extend(body_align)
                    ti = lookahead
                    found = True
                    break
            if not found:
                # Heading không có pair → src-only
                result.append((src_seg['heading'], None, 'src-only'))
                body_align = _align_body(src_seg['body'], [], lang)
                result.extend(body_align)
                si += 1

        # Chỉ vi có heading
        elif not src_seg['heading'] and vi_seg['heading']:
            found = False
            for lookahead in range(si, min(si + 3, len(src_segments))):
                if src_segments[lookahead]['heading']:
                    for j in range(si, lookahead):
                        body_align = _align_body(src_segments[j]['body'], [], lang)
                        result.extend(body_align)
                    si = lookahead
                    found = True
                    break
            if not found:
                result.append((None, vi_seg['heading'], 'vi-only'))
                body_align = _align_body([], vi_seg['body'], lang)
                result.extend(body_align)
                ti += 1

        # Cả 2 không có heading
        else:
            body_align = _align_body(src_seg['body'], vi_seg['body'], lang)
            result.extend(body_align)
            si += 1
            ti += 1

    # Remaining source segments
    while si < len(src_segments):
        seg = src_segments[si]
        if seg['heading']:
            result.append((seg['heading'], None, 'src-only'))
        body_align = _align_body(seg['body'], [], lang)
        result.extend(body_align)
        si += 1

    # Remaining translation segments
    while ti < len(vi_segments):
        seg = vi_segments[ti]
        if seg['heading']:
            result.append((None, seg['heading'], 'vi-only'))
        body_align = _align_body([], seg['body'], lang)
        result.extend(body_align)
        ti += 1

    return result


def _len_ratio(a: str, b: str, lang: str = 'en') -> float:
    """Tỉ lệ độ dài giữa 2 đoạn (0-1). 1 = bằng nhau.
    For ZH→VI, Vietnamese is ~1.5-1.8x longer, so normalize.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    # ZH→VI: Vietnamese text is typically 1.5-1.8x longer than Chinese
    if lang == 'zh':
        lb = lb * 0.6  # normalize Vietnamese length
    return min(la, lb) / max(la, lb)


def _dp_align(src_body: list[str], vi_body: list[str], lang: str = 'en') -> list[tuple]:
    """
    DP alignment cho body paragraphs giữa 2 segment.

    Cho phép: 1:1, 2:1 (2 src → 1 vi), 1:2 (1 src → 2 vi).
    Cost = 1 - len_ratio.
    """
    n = len(src_body)
    m = len(vi_body)

    if n == 0 and m == 0:
        return []

    if n == 0:
        return [(None, p, 'vi-only') for p in vi_body]
    if m == 0:
        return [(p, None, 'src-only') for p in src_body]

    INF = float('inf')
    # dp[i][j] = (min_cost, predecessor)
    dp = [[(INF, None)] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = (0, None)

    for i in range(n + 1):
        for j in range(m + 1):
            if dp[i][j][0] == INF:
                continue
            cost_so_far = dp[i][j][0]

            # 1:1
            if i < n and j < m:
                ratio = _len_ratio(src_body[i], vi_body[j], lang)
                cost = (1 - ratio) * 10  # penalty for mismatch
                new_cost = cost_so_far + cost
                if new_cost < dp[i + 1][j + 1][0]:
                    dp[i + 1][j + 1] = (new_cost, ('1:1', i, j))

            # 2:1 (2 src → 1 vi)
            if i + 1 < n and j < m:
                merged_src = src_body[i] + '\n\n' + src_body[i + 1]
                ratio = _len_ratio(merged_src, vi_body[j], lang)
                cost = (1 - ratio) * 10 + 2  # small extra penalty for merge
                new_cost = cost_so_far + cost
                if new_cost < dp[i + 2][j + 1][0]:
                    dp[i + 2][j + 1] = (new_cost, ('2:1', i, j))

            # 1:2 (1 src → 2 vi)
            if i < n and j + 1 < m:
                merged_vi = vi_body[j] + '\n\n' + vi_body[j + 1]
                ratio = _len_ratio(src_body[i], merged_vi, lang)
                cost = (1 - ratio) * 10 + 2
                new_cost = cost_so_far + cost
                if new_cost < dp[i + 1][j + 2][0]:
                    dp[i + 1][j + 2] = (new_cost, ('1:2', i, j))

            # Skip src (src-only)
            if i < n:
                new_cost = cost_so_far + 5  # penalty for skip
                if new_cost < dp[i + 1][j][0]:
                    dp[i + 1][j] = (new_cost, ('skip-src', i, j))

            # Skip vi (vi-only)
            if j < m:
                new_cost = cost_so_far + 5
                if new_cost < dp[i][j + 1][0]:
                    dp[i][j + 1] = (new_cost, ('skip-vi', i, j))

    # Backtrack
    result = []
    i, j = n, m
    while i > 0 or j > 0:
        _, pred = dp[i][j]
        if pred is None:
            break
        op, pi, pj = pred

        if op == '1:1':
            result.append((src_body[pi], vi_body[pj], 'ok'))
            i, j = pi, pj
        elif op == '2:1':
            merged = src_body[pi] + '\n\n' + src_body[pi + 1]
            result.append((merged, vi_body[pj], 'check'))
            i, j = pi, pj
        elif op == '1:2':
            merged = vi_body[pj] + '\n\n' + vi_body[pj + 1]
            result.append((src_body[pi], merged, 'check'))
            i, j = pi, pj
        elif op == 'skip-src':
            result.append((src_body[pi], None, 'src-only'))
            i, j = pi, pj
        elif op == 'skip-vi':
            result.append((None, vi_body[pj], 'vi-only'))
            i, j = pi, pj

    result.reverse()

    # Đánh giá tổng thể: nếu có quá nhiều check → downgrade
    n_check = sum(1 for _, _, s in result if s == 'check')
    if n_check > len(result) * 0.3 and len(result) > 3:
        # Quá nhiều chỗ không chắc → đánh dấu toàn bộ
        result = [(s, v, 'check' if st == 'ok' else st) for s, v, st in result]

    return result


def _align_body(src_body: list[str], vi_body: list[str], lang: str = 'en') -> list[tuple]:
    """Align body paragraphs, return list of (src, vi, status)."""
    if not src_body and not vi_body:
        return []
    if not src_body:
        return [(None, p, 'vi-only') for p in vi_body]
    if not vi_body:
        return [(p, None, 'src-only') for p in src_body]

    # Thử DP alignment
    aligned = _dp_align(src_body, vi_body, lang)

    # Kiểm tra chất lượng
    n_ok = sum(1 for _, _, s in aligned if s == 'ok')
    total = len(aligned)
    if total > 0 and n_ok / total >= 0.5:
        return aligned

    # Nếu DP cho kết quả tệ, fallback sang zip đơn giản + đánh dấu check
    result = []
    for i in range(max(len(src_body), len(vi_body))):
        s = src_body[i] if i < len(src_body) else None
        v = vi_body[i] if i < len(vi_body) else None
        if s and v:
            ratio = _len_ratio(s, v, lang)
            status = 'ok' if ratio > 0.3 else 'check'
        else:
            status = 'src-only' if s else 'vi-only'
        result.append((s, v, status))
    return result


# ─── Format output ────────────────────────────────────────────────────────

def format_bilingual_block(
    src: str | None,
    vi: str | None,
    lang: str,
    status: str,
) -> str:
    """Format 1 block song ngữ."""
    lines = []
    vi_handled = False

    if src is not None:
        typ = classify_paragraph(src)
        first_line = src.split('\n')[0].strip()

        if typ == 'heading':
            # Heading: Vietnamese heading = Markdown heading, original in bold + pinyin
            raw_heading = HEADING_RE.sub(r'\2', first_line).strip()

            if vi is not None:
                # Use Vietnamese heading as the Markdown heading
                lines.append(vi)
                lines.append("")
            # Original heading in bold
            lines.append(f"**{raw_heading}**")
            # Pinyin if ZH
            if lang == 'zh' and has_han(raw_heading):
                py = text_to_pinyin(raw_heading)
                if py:
                    lines.append(f"*{py}*")
            lines.append("")
            vi_handled = True
        elif typ == 'code':
            # Code block: keep unchanged, no Pinyin
            lines.append(src)
            lines.append("")
            vi_handled = (vi == src)
        elif typ == 'table':
            # Table: keep unchanged
            lines.append(src)
            lines.append("")
            vi_handled = (vi == src)
        elif typ == 'image':
            # Image: keep unchanged
            lines.append(src)
            lines.append("")
            vi_handled = True
        else:
            # Text paragraph: wrap in HTML for styled EPUB
            lines.append('<div class="bi-block">')
            if status == 'check':
                lines.append(f'<p class="src-en">[ALIGN-CHECK] {src}</p>')
            else:
                lines.append(f'<p class="src-en">{src}</p>')
            if lang == 'zh' and has_han(src):
                py = text_to_pinyin(src)
                if py:
                    lines.append(f'<p class="pinyin">{py}</p>')
            lines.append(f'<p class="vi">{vi if vi is not None else ""}</p>')
            lines.append('</div>')
            lines.append("")
            vi_handled = True

    if vi is not None and not vi_handled:
        lines.append(vi)
        lines.append("")

    return '\n'.join(lines)


def generate_bilingual(
    src_text: str,
    vi_text: str,
    lang: str,
) -> tuple[str, list[str]]:
    """
    Tạo nội dung song ngữ từ 2 file.

    Trả về: (output_text, warnings)
    """
    warnings = []

    # Tách đoạn
    src_paras = split_paragraphs(src_text)
    vi_paras = split_paragraphs(vi_text)

    print(f"  Gốc: {len(src_paras)} đoạn")
    print(f"  Dịch: {len(vi_paras)} đoạn")

    # Căn chỉnh
    aligned = align_paragraphs(src_paras, vi_paras, lang)

    # Tạo output
    blocks = []
    n_check = 0
    n_src_only = 0
    n_vi_only = 0

    for src, vi, status in aligned:
        block = format_bilingual_block(src, vi, lang, status)
        blocks.append(block)

        if status == 'check':
            n_check += 1
            if src:
                preview = src[:60].replace('\n', ' ')
            elif vi:
                preview = vi[:60].replace('\n', ' ')
            else:
                preview = "?"
            warnings.append(f"[ALIGN-CHECK] {preview}...")
        elif status == 'src-only':
            n_src_only += 1
        elif status == 'vi-only':
            n_vi_only += 1

    output = '\n---\n\n'.join(blocks)

    # Thống kê
    total = len(aligned)
    print(f"  Căn chỉnh: {total} blocks "
          f"(ok: {total - n_check - n_src_only - n_vi_only}, "
          f"check: {n_check}, "
          f"gốc-only: {n_src_only}, "
          f"dịch-only: {n_vi_only})")

    return output, warnings


# ─── Report ───────────────────────────────────────────────────────────────

def write_report(
    report_path: Path,
    src_path: Path,
    vi_path: Path,
    lang: str,
    warnings: list[str],
    src_paras: int,
    vi_paras: int,
) -> None:
    """Ghi báo cáo căn chỉnh."""
    lines = [
        f"# Bilingual Alignment Report",
        f"",
        f"- **Source**: `{src_path}`",
        f"- **Translation**: `{vi_path}`",
        f"- **Language**: {lang}",
        f"- **Source paragraphs**: {src_paras}",
        f"- **Translation paragraphs**: {vi_paras}",
        f"- **Difference**: {abs(src_paras - vi_paras)}",
        f"- **Alignment issues**: {len(warnings)}",
        f"",
    ]

    if warnings:
        lines.append("## Issues")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
    else:
        lines.append("## Status: OK")
        lines.append("")
        lines.append("No alignment issues detected.")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Báo cáo: {report_path}")


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Ghép file gốc + bản dịch thành file song ngữ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--source', type=Path, required=True,
                        help='File gốc (raw.md / raw-hans.md / chunk-XXX.md)')
    parser.add_argument('--translation', type=Path, required=True,
                        help='File dịch (<slug>-vi.md / chunk-XXX.md)')
    parser.add_argument('--output', type=Path, default=None,
                        help='File output song ngữ (bỏ qua trong --check mode)')
    parser.add_argument('--lang', choices=['en', 'zh'], required=True,
                        help='Ngôn ngữ gốc (en: không có Pinyin, zh: thêm Pinyin)')
    parser.add_argument('--report', type=Path, default=None,
                        help='Báo cáo căn chỉnh (working/qa/<slug>/bilingual-align.md)')
    parser.add_argument('--check', action='store_true',
                        help='Chỉ chạy căn chỉnh + xuất report (không ghi file output)')
    args = parser.parse_args()

    # Validate input
    if not args.source.exists():
        print(f"[LỖI] File gốc không tồn tại: {args.source}", file=sys.stderr)
        sys.exit(1)
    if not args.translation.exists():
        print(f"[LỖI] File dịch không tồn tại: {args.translation}", file=sys.stderr)
        sys.exit(1)
    if not args.check and not args.output:
        print(f"[LỖI] Cần --output hoặc --check", file=sys.stderr)
        sys.exit(1)

    # Đọc file
    src_text = args.source.read_text(encoding='utf-8')
    vi_text = args.translation.read_text(encoding='utf-8')

    print(f"Gốc:     {args.source}")
    print(f"Dịch:    {args.translation}")
    if args.output:
        print(f"Output:  {args.output}")
    print(f"Ngôn ngữ: {args.lang}")
    print()

    # Chạy
    output_text, warnings = generate_bilingual(src_text, vi_text, args.lang)

    # Đếm paragraphs
    src_paras = len(split_paragraphs(src_text))
    vi_paras = len(split_paragraphs(vi_text))

    # Ghi report
    if args.report:
        write_report(args.report, args.source, args.translation, args.lang,
                     warnings, src_paras, vi_paras)

    # Ghi output
    if not args.check and args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding='utf-8')
        print(f"\nĐã tạo: {args.output}")
    elif args.check:
        print(f"\n[CHECK MODE] Không ghi file output.")
        if warnings:
            print(f"Có {len(warnings)} vấn đề cần xem (xem report).")
        else:
            print(f"Không có vấn đề nào.")


if __name__ == '__main__':
    main()
