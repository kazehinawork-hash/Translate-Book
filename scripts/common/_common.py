"""
_common.py - Helper chung cho các script (encoding, paths, output)

Import: from _common import setup_encoding, PROJECT_ROOT
"""

import sys
from pathlib import Path

# Đường dẫn gốc dự án (parent của scripts/)
# Dùng .resolve() để chuẩn hóa __file__ (tránh bị ".." trong path khi import
# qua đường dẫn tương đối → PROJECT_ROOT lệch, ghi file sai chỗ).
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # scripts/common/ → scripts/ → project root


def setup_encoding() -> None:
    """Thiết lập UTF-8 cho stdout/stderr trên Windows.

    Cần thiết vì PowerShell mặc định dùng cp1252, không in được tiếng Việt.
    Gọi đầu mỗi script trước khi in ra console.
    """
    if sys.platform == 'win32':
        for stream_name in ('stdout', 'stderr'):
            stream = getattr(sys, stream_name, None)
            if stream is None:
                continue
            # Python 3.7+
            reconfigure = getattr(stream, 'reconfigure', None)
            if callable(reconfigure):
                try:
                    reconfigure(encoding='utf-8', errors='replace')
                except Exception:
                    pass
        # Fallback cho Python cũ
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')
        except Exception:
            pass


def print_safe(*args, **kwargs):
    """Print an toàn (encode errors='replace')."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: thay ký tự lỗi
        text = ' '.join(str(a) for a in args)
        print(text.encode('ascii', errors='replace').decode('ascii'), **kwargs)
