"""
srt_translate.py - Tách batch SRT ra text + Ghép bản dịch vào SRT (KHÔNG dùng API)

Giai đoạn hiện tại: workflow chat thủ công, KHÔNG tích hợp API.
Script chỉ làm 2 việc:
1. Tách batch: pysrt → text files (để paste vào chat AI)
2. Ghép: text files đã dịch → SRT hoàn chỉnh (giữ timestamp/index)

Ví dụ workflow:
    # Bước 1: tách
    python scripts/srt_translate.py ^
        --input "working\extracted\$slug\raw.srt" ^
        --extract-batches ^
        --batch-dir "working\chunks\$slug\srt-batches" ^
        --batch-size 30

    # (Paste từng batch vào chat, lưu bản dịch vào working\chunks\$slug\srt-batches\batch-001.vi.md)

    # Bước 2: ghép
    python scripts/srt_translate.py ^
        --input "working\extracted\$slug\raw.srt" ^
        --output "output\$slug\translated.srt" ^
        --batch-dir "working\chunks\$slug\srt-batches" ^
        --merge
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402

try:
    import pysrt
    HAS_PYSRT = True
except ImportError:
    HAS_PYSRT = False

try:
    from rich.console import Console
    from rich.progress import Progress
    console = Console()
except ImportError:
    console = None


def extract_batches(args):
    """Tách SRT thành các batch text files."""
    if not HAS_PYSRT:
        print("[LỖI] Cần cài pysrt: pip install pysrt", file=sys.stderr)
        sys.exit(1)

    if not args.input.exists():
        print(f"[LỖI] File không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    subs = pysrt.open(str(args.input), encoding='utf-8')
    print(f"Đọc: {args.input} ({len(subs)} phụ đề)")

    args.batch_dir.mkdir(parents=True, exist_ok=True)
    batch_size = args.batch_size
    tong_so_batch = (len(subs) + batch_size - 1) // batch_size

    for i in range(tong_so_batch):
        start = i * batch_size
        end = min((i + 1) * batch_size, len(subs))
        batch = subs[start:end]

        # Ghi text file: chỉ phần text, mỗi dòng 1 phụ đề (giữ index để trao đổi)
        # Phụ đề 2 dòng (sub.text có \n) → chuẩn hóa thành ' / ' để tránh vỡ round-trip
        lines = [f"[{sub.index}] {sub.text.replace(chr(10), ' / ')}" for sub in batch]
        noi_dung = '\n'.join(lines)

        ten_file = args.batch_dir / f"batch-{i+1:03d}.md"
        ten_file.write_text(noi_dung, encoding='utf-8')

        # Tạo file placeholder cho bản dịch
        vi_file = args.batch_dir / f"batch-{i+1:03d}.vi.md"
        if not vi_file.exists():
            vi_template = f"# Bản dịch batch {i+1}\n# Dòng {start+1}-{end} / {len(subs)}\n# Format: giữ nguyên `[index]` phía trước, chỉ dịch phần sau\n\n"
            for sub in batch:
                vi_template += f"[{sub.index}] <dịch phần này>\n"
            vi_file.write_text(vi_template, encoding='utf-8')

        print(f"  ✓ batch-{i+1:03d}.md + batch-{i+1:03d}.vi.md (dòng {start+1}-{end})")

    print(f"\nHoàn thành: {tong_so_batch} batch trong {args.batch_dir}")
    print(f"\nBước tiếp:")
    print(f"  1. Paste nội dung batch-XXX.md vào chat AI để dịch")
    print(f"  2. Lưu bản dịch vào batch-XXX.vi.md (giữ nguyên `[index]`)")
    print(f"  3. Chạy lệnh với --merge để ghép lại thành SRT hoàn chỉnh")


def merge_batches(args):
    """Ghép các bản dịch vào SRT gốc."""
    if not HAS_PYSRT:
        print("[LỖI] Cần cài pysrt: pip install pysrt", file=sys.stderr)
        sys.exit(1)

    if not args.input.exists():
        print(f"[LỖI] File SRT gốc không tồn tại: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.batch_dir.exists():
        print(f"[LỖI] Thư mục batch không tồn tại: {args.batch_dir}", file=sys.stderr)
        sys.exit(1)

    subs = pysrt.open(str(args.input), encoding='utf-8')
    print(f"Đọc SRT gốc: {args.input} ({len(subs)} phụ đề)")

    # Đọc tất cả file *.vi.md vào dict {index: text_dịch}
    ban_dich = {}
    vi_files = sorted(args.batch_dir.glob("batch-*.vi.md"))
    if not vi_files:
        print(f"[LỖI] Không tìm thấy file batch-*.vi.md trong {args.batch_dir}", file=sys.stderr)
        sys.exit(1)

    for vi_file in vi_files:
        content = vi_file.read_text(encoding='utf-8')
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('<'):
                continue
            # Parse [index] text_dịch
            if line.startswith('[') and ']' in line:
                try:
                    idx_str, text = line[1:].split(']', 1)
                    idx = int(idx_str.strip())
                    text_clean = text.strip()
                    if text_clean and not text_clean.startswith('<'):
                        ban_dich[idx] = text_clean
                except (ValueError, IndexError):
                    continue

    print(f"Đọc {len(ban_dich)} dòng đã dịch từ {len(vi_files)} file")

    # Thay thế text trong SRT
    # Khôi phục ' / ' (chuẩn hóa khi extract) → '\n' (chuẩn SRT multi-line)
    da_thay = 0
    chua_thay = []
    for sub in subs:
        if sub.index in ban_dich:
            sub.text = ban_dich[sub.index].replace(' / ', '\n')
            da_thay += 1
        else:
            chua_thay.append(sub.index)

    # Ghi SRT output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(args.output), encoding='utf-8')
    print(f"\n✓ Đã ghép: {args.output}")
    print(f"  Đã thay: {da_thay}/{len(subs)} dòng")
    if chua_thay:
        print(f"  ⚠️ Chưa dịch: {len(chua_thay)} dòng (index: {', '.join(map(str, chua_thay[:10]))}{'...' if len(chua_thay) > 10 else ''})")
        print(f"  → Có thể do batch-XXX.vi.md bị thiếu hoặc chưa paste đủ")
    else:
        print(f"  ✅ Đầy đủ tất cả dòng")


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Tách/ghép SRT (hỗ trợ dịch thủ công qua chat)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, required=True, help='File SRT đầu vào (gốc)')
    parser.add_argument('--output', type=Path, help='File SRT đầu ra (chỉ dùng với --merge)')
    parser.add_argument('--extract-batches', action='store_true', help='Tách SRT thành các batch text')
    parser.add_argument('--merge', action='store_true', help='Ghép các batch đã dịch thành SRT')
    parser.add_argument('--batch-dir', type=Path, help='Thư mục chứa các batch (input/output)')
    parser.add_argument('--batch-size', type=int, default=30, help='Số dòng/batch (mặc định 30)')

    args = parser.parse_args()

    if args.extract_batches and args.merge:
        print("[LỖI] Chỉ chọn 1 trong 2: --extract-batches hoặc --merge", file=sys.stderr)
        sys.exit(1)
    if not args.extract_batches and not args.merge:
        print("[LỖI] Phải chọn --extract-batches hoặc --merge", file=sys.stderr)
        sys.exit(1)
    if not args.batch_dir:
        print("[LỖI] Thiếu --batch-dir", file=sys.stderr)
        sys.exit(1)

    if args.extract_batches:
        extract_batches(args)
    else:  # merge
        if not args.output:
            print("[LỖI] --merge cần --output", file=sys.stderr)
            sys.exit(1)
        merge_batches(args)


if __name__ == '__main__':
    main()
