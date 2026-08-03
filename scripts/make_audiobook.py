"""
make_audiobook.py - Chuyển file .md bản dịch sang sách nói (audiobook MP3)

Dùng edge-tts (Microsoft Edge neural voices, online) + ffmpeg (nối file).

Yêu cầu:
  - edge-tts: cài qua `pip install edge-tts` (hoặc có sẵn edge-tts.exe)
  - ffmpeg:   cài qua `winget install Gyan.FFmpeg`

Ví dụ:
  # Toàn bộ sách, giọng nữ mặc định
  python scripts/make_audiobook.py output\\<slug>-vi.md

  # Giọng nam, nhanh hơn 10%, chỉ 3 chương đầu (thử nhanh)
  python scripts/make_audiobook.py output\\<slug>-vi.md --voice vi-VN-NamMinhNeural --rate +10% --limit 3

  # Chỉ định edge-tts / ffmpeg nếu không có trong PATH
  python scripts/make_audiobook.py output\\<slug>-vi.md --edge-tts C:\\...\\edge-tts.exe --ffmpeg C:\\...\\ffmpeg.exe
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Danh sách đường dẫn edge-tts/ffmpeg thường gặp trên Windows (nếu không có trong PATH)
EDGE_TTS_FALLBACKS = [
    Path(r"C:\Users\RiverWind\AppData\Local\Programs\Python\Python310\Scripts\edge-tts.exe"),
    Path(r"C:\Users\Admin\AppData\Local\Programs\Python\Python311\Scripts\edge-tts.exe"),
]
FFMPEG_FALLBACKS = [
    Path(r"C:\Users\RiverWind\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"),
]


def find_tool(name: str, fallbacks: list[Path]) -> Path | None:
    found = shutil.which(name)
    if found:
        return Path(found)
    for p in fallbacks:
        if p.exists():
            return p
    return None


def strip_markdown(text: str) -> str:
    """Làm sạch văn bản trước khi TTS: bỏ markdown, html, ảnh, OCR dư."""
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Bỏ dòng hình ảnh
        if re.match(r'^!\[.*\]\(.*\)$', line) or line.startswith('!['):
            continue
        # Bỏ thẻ html (vd <div class=...>, </div>)
        if re.match(r'^</?[a-zA-Z][^>]*>$', line):
            continue
        # Bỏ /// OCR dư
        line = line.replace('///', ' ')
        # Bỏ markdown emphasis
        line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
        line = re.sub(r'\*([^*]+)\*', r'\1', line)
        line = re.sub(r'__([^_]+)__', r'\1', line)
        line = re.sub(r'`([^`]+)`', r'\1', line)
        # Bỏ link markdown [text](url) -> text
        line = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', line)
        line = line.strip()
        if not line:
            continue
        lines.append(line)
    return '\n'.join(lines)


def split_chapters(text: str) -> list[dict]:
    """Tách văn bản thành các chương. Nhận biết heading cấp 1 `# ...`.

    Chỉ `#` (cấp 1) mới là ranh giới chương. Các heading `## [n] textXXXX.html`
    (trang ảnh/trang lẻ trong EPUB) và `## Mục lục` bị bỏ qua.
    """
    chapters = []
    cur = None
    skip_toc = False
    for raw in text.splitlines():
        m = re.match(r'^(#{1,3})\s+(.*)$', raw)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # Ranh giới chương: chỉ heading cấp 1 không phải trang ảnh/trang lẻ
            if level == 1 and not re.match(r'^\[\d+\]', title):
                if cur is not None:
                    chapters.append(cur)
                if re.match(r'^Mục lục', title):
                    cur = {'title': title, 'body': [], 'skip': True}
                else:
                    cur = {'title': title, 'body': [], 'skip': False}
                continue
            # Heading phụ cấp 2/3 là trang ảnh `## [n] textXXXX.html` — bỏ
            if level >= 2 and re.match(r'^\[\d+\]', title):
                continue
        if cur is None:
            cur = {'title': '(Mở đầu)', 'body': [], 'skip': False}
        cur['body'].append(raw)
    if cur is not None:
        chapters.append(cur)
    return chapters


def split_segments(text: str, max_chars: int = 1500) -> list[str]:
    """Chia văn bản thành các đoạn <= max_chars, ưu tiên cắt ở dấu câu.

    Bỏ các đoạn không có ký tự chữ (toàn ký hiệu rác từ OCR như `?.??.`)
    và các đoạn toàn tiếng Trung (không nên đọc bằng giọng Việt).
    """
    segments = []
    paragraph = '\n'.join(
        p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()
    )
    # Cắt ở dấu chấm hết câu nếu có thể
    for part in re.split(r'(?<=[.!?…])\s+', paragraph):
        if len(part) <= max_chars:
            segments.append(part)
        else:
            # Cắt cứng theo ký tự nếu vẫn dài
            for i in range(0, len(part), max_chars):
                segments.append(part[i:i + max_chars])
    cleaned = []
    for s in segments:
        s = s.strip()
        if not s:
            continue
        # Phải có ít nhất 1 chữ cái Latin/Việt (có dấu) — bỏ chuỗi toàn ký hiệu
        if not re.search(r'[A-Za-zÀ-ỹà-ỹ]', s):
            continue
        # Nếu toàn tiếng Trung (Hán) thì bỏ — giọng Việt không đọc được
        han = len(re.findall(r'[\u3400-\u4DBF\u4E00-\u9FFF]', s))
        if han > 0 and han > len(s) * 0.4:
            continue
        cleaned.append(s)
    return cleaned


def build_concat_file(part_files: list[Path], list_path: Path) -> None:
    lines = []
    for p in part_files:
        # Dùng đường dẫn tuyệt đối vì concat demuxer resolve path tương đối
        # so với thư mục chứa file list.
        path = str(p.resolve()).replace('\\', '/')
        lines.append(f"file '{path}'")
    list_path.write_text('\n'.join(lines), encoding='utf-8')


def run_edge_tts(edge_tts: Path, text: str, out_mp3: Path, voice: str, rate: str) -> bool:
    # Dùng file tạm thay vì --text để tránh lỗi encoding ký tự Unicode trên Windows
    text_file = out_mp3.with_suffix('.txt')
    text_file.write_text(text, encoding='utf-8')
    cmd = [
        str(edge_tts),
        '--voice', voice,
        '--file', str(text_file),
        '--write-media', str(out_mp3),
    ]
    if rate:
        cmd.extend(['--rate', rate])
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0 or not out_mp3.exists() or out_mp3.stat().st_size == 0:
        print(f"      [LỖI] edge-tts thất bại:\n{result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def run_edge_tts_with_retry(edge_tts: Path, text: str, out_mp3: Path, voice: str, rate: str, retries: int = 3) -> bool:
    """Gọi edge-tts, thử lại nếu lỗi mạng tạm thời (NoAudioReceived)."""
    for attempt in range(1, retries + 1):
        ok = run_edge_tts(edge_tts, text, out_mp3, voice, rate)
        if ok:
            return True
        if attempt < retries:
            print(f"      ⏳ Thử lại lần {attempt + 1}/{retries}...")
            import time
            time.sleep(2 * attempt)
    return False


def run_ffmpeg_concat(ffmpeg: Path, list_path: Path, output: Path) -> bool:
    cmd = [
        str(ffmpeg), '-y', '-f', 'concat', '-safe', '0',
        '-i', str(list_path),
        '-c:a', 'libmp3lame', '-b:a', '128k',
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0 or not output.exists():
        print(f"      [LỖI] ffmpeg nối file thất bại:\n{result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Chuyển file .md bản dịch sang sách nói (audiobook MP3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('input', type=Path, help='File .md đầu vào (bản dịch tiếng Việt)')
    parser.add_argument('--output', type=Path, default=None, help='File MP3 đầu ra (mặc định: cùng tên .mp3)')
    parser.add_argument('--voice', type=str, default='vi-VN-HoaiMyNeural',
                        help='Giọng đọc. Nữ: vi-VN-HoaiMyNeural | Nam: vi-VN-NamMinhNeural')
    parser.add_argument('--rate', type=str, default='',
                        help='Tốc độ đọc, vd: +10%% (nhanh), -10%% (chậm)')
    parser.add_argument('--max-chars', type=int, default=1500,
                        help='Độ dài tối đa mỗi đoạn TTS (mặc định: 1500 ký tự)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Chỉ đọc N chương đầu (0 = tất cả). Dùng để thử nhanh.')
    parser.add_argument('--tmp-dir', type=Path, default=None,
                        help='Thư mục chứa file MP3 tạm từng đoạn (mặc định: thư mục tạm hệ thống)')
    parser.add_argument('--edge-tts', type=Path, default=None, help='Đường dẫn edge-tts (nếu không có trong PATH)')
    parser.add_argument('--ffmpeg', type=Path, default=None, help='Đường dẫn ffmpeg (nếu không có trong PATH)')
    parser.add_argument('--keep-parts', action='store_true',
                        help='Giữ lại các file MP3 tạm từng đoạn (không xoá)')
    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.exists():
        print(f"[LỖI] Không tìm thấy file: {input_path}", file=sys.stderr)
        sys.exit(1)

    edge_tts = args.edge_tts or find_tool('edge-tts', EDGE_TTS_FALLBACKS)
    if edge_tts is None:
        print("[LỖI] Không tìm thấy edge-tts.\n"
              "  Cài qua: pip install edge-tts\n"
              "  Hoặc truyền --edge-tts <đường dẫn>", file=sys.stderr)
        sys.exit(1)

    ffmpeg = args.ffmpeg or find_tool('ffmpeg', FFMPEG_FALLBACKS)
    if ffmpeg is None:
        print("[LỖI] Không tìm thấy ffmpeg.\n"
              "  Cài qua: winget install Gyan.FFmpeg\n"
              "  Hoặc truyền --ffmpeg <đường dẫn>", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or input_path.with_suffix('.mp3')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding='utf-8')
    chapters = split_chapters(text)
    if not chapters:
        chapters = [{'title': '(Toàn bộ)', 'body': text.splitlines()}]

    if args.limit > 0:
        chapters = chapters[:args.limit]

    print(f"  edge-tts : {edge_tts}")
    print(f"  ffmpeg   : {ffmpeg}")
    print(f"  Input    : {input_path}")
    print(f"  Output   : {output_path}")
    print(f"  Voice    : {args.voice}  Rate: {args.rate or '0%'}")
    print(f"  Chương   : {len(chapters)}")

    tmp_dir = args.tmp_dir or Path(tempfile.mkdtemp(prefix='audiobook_'))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    part_files: list[Path] = []
    seg_idx = 0
    total_chars = 0
    fail = False

    for ci, ch in enumerate(chapters, start=1):
        if ch.get('skip'):
            print(f"  ⏭  Chương {ci}: {ch['title'][:40]} — bỏ qua (Mục lục)")
            continue
        body = strip_markdown('\n'.join(ch['body']))
        if not body:
            print(f"  ⏭  Chương {ci}: {ch['title'][:40]} — trống, bỏ qua")
            continue
        segments = split_segments(body, args.max_chars)
        print(f"  Chương {ci}: {ch['title'][:50]} — {len(body)} ký tự / {len(segments)} đoạn")
        for si, seg in enumerate(segments, start=1):
            seg_idx += 1
            total_chars += len(seg)
            part = tmp_dir / f'part_{seg_idx:05d}.mp3'
            ok = run_edge_tts_with_retry(edge_tts, seg, part, args.voice, args.rate)
            if not ok:
                fail = True
                break
            part_files.append(part)
            print(f"      [{seg_idx}] {len(seg)} ký tự → {part.name}")
            if fail:
                break
        if fail:
            break

    if fail or not part_files:
        print(f"\n[LỖI] Không tạo được audiobook.", file=sys.stderr)
        if args.keep_parts:
            print(f"  File tạm giữ tại: {tmp_dir}")
        sys.exit(1)

    print(f"\n  Nối {len(part_files)} đoạn bằng ffmpeg...")
    list_path = tmp_dir / 'concat.txt'
    build_concat_file(part_files, list_path)
    if not run_ffmpeg_concat(ffmpeg, list_path, output_path):
        sys.exit(1)

    size_kb = output_path.stat().st_size / 1024
    dur_s = total_chars / 12  # ước lượng: ~12 ký tự/giây nói tiếng Việt
    print(f"\n  ✅ Đã tạo audiobook: {output_path}")
    print(f"     Dung lượng : {size_kb / 1024:.1f} MB")
    print(f"     Tổng chữ   : {total_chars:,}")
    print(f"     Ước thời lượng: {dur_s / 60:.1f} phút")

    if not args.keep_parts:
        import shutil as _sh
        _sh.rmtree(tmp_dir, ignore_errors=True)
    else:
        print(f"  File tạm giữ tại: {tmp_dir}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
