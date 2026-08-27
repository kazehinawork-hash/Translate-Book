"""
make_epub.py - Chuyển file .md đã merge sang .epub dùng pandoc

Yêu cầu: pandoc (https://pandoc.org/installing.html)
"""

import os
import re
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Chuyển file .md đã merge sang .epub dùng pandoc'
    )
    parser.add_argument('input', type=Path, help='File .md đầu vào')
    parser.add_argument('--title', type=str, default='', help='Tên sách (metadata)')
    parser.add_argument('--author', type=str, default='', help='Tác giả (metadata)')
    parser.add_argument('--cover', type=Path, default=None, help='File ảnh bìa')
    parser.add_argument('--resource-path', type=str, default='', help='Đường dẫn tìm kiếm ảnh/tài nguyên')
    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.exists():
        print(f"[LỖI] Không tìm thấy file: {input_path}", file=sys.stderr)
        sys.exit(1)

    pandoc_path = shutil.which('pandoc')
    if pandoc_path is None:
        print(
            "[LỖI] pandoc chưa được cài đặt.\n"
            "  Tải và cài từ: https://pandoc.org/installing.html\n"
            "  Hoặc dùng package manager:\n"
            "    Windows: winget install pandoc\n"
            "    macOS:   brew install pandoc\n"
            "    Linux:   sudo apt install pandoc",
            file=sys.stderr,
        )
        sys.exit(1)

    # Làm sạch heading kỹ thuật dạng ## [N] text0000X.html, **[N]...**, *[N]...* và xml version trước khi đóng gói EPUB
    try:
        content = input_path.read_text(encoding='utf-8')
        # Xóa toàn bộ khối tri-block chứa xml version
        content = re.sub(r'<div class="tri-block">\s*<p class="src-zh">xml version=[^<]*</p>\s*<p class="pinyin">[^<]*</p>\s*<p class="vi">[^<]*</p>\s*</div>', '', content, flags=re.DOTALL)
        # Xóa các thẻ div rỗng
        content = re.sub(r'<div class="tri-block">\s*</div>', '', content)
        # Bỏ thẻ <div> và </div> bao ngoài để Pandoc không bị chặn nhận diện Heading TOC
        content = content.replace('<div class="tri-block">', '').replace('</div>', '')
        lines = content.splitlines()
        clean_lines = []
        for line in lines:
            s = line.strip()
            # Bỏ dòng rác xml version
            if "xml version=" in s:
                continue
            # Bỏ tiêu đề kỹ thuật bóc tách epub ## [1] text00000.html hoặc **[1] text...**
            if re.match(r'^(##|\*\*|\*)\s*\[\d+\]\s*text\d+\.html', s, re.IGNORECASE):
                continue
            clean_lines.append(line)
        cleaned_content = '\n'.join(clean_lines)
        if cleaned_content != content:
            input_path.write_text(cleaned_content, encoding='utf-8')
    except Exception:
        pass

    output_path = input_path.with_suffix('.epub')
    title = args.title or input_path.stem
    author = args.author or ''

    css_here = Path(__file__).parent / 'epub_style.css'
    css_common = Path(__file__).parent.parent / 'common' / 'epub_style.css'
    css_path = css_here if css_here.exists() else css_common

    cmd = [
        pandoc_path,
        str(input_path),
        '-o', str(output_path),
        '--css', str(css_path),
        '--metadata', f'title={title}',
        '--toc',
        '--split-level=1',
        '--epub-chapter-level=1',
    ]
    if author:
        cmd.extend(['--metadata', f'author={author}'])
    if args.cover and args.cover.exists():
        cmd.extend(['--epub-cover-image', str(args.cover)])
    if args.resource_path:
        cmd.extend(['--resource-path', args.resource_path])

    print(f"  Pandoc: {pandoc_path}")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Title:  {title}")
    if author:
        print(f"  Author: {author}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[LỖI] pandoc thất bại (mã {result.returncode})", file=sys.stderr)
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    if result.stderr:
        print(f"  pandoc stderr: {result.stderr.strip()}")

    print(f"  Dung lượng: {output_path.stat().st_size / 1024:.0f} KB")
    print(f"  ✅ Đã tạo EPUB: {output_path}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
