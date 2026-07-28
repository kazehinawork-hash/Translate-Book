"""
translate_full_pipeline.py - (DEPRECATED) Dùng run_pipeline.py thay thế.

Script này được gộp vào run_pipeline.py. Giữ lại tạm thời để tương thích
ngược. Vui lòng dùng run_pipeline.py cho pipeline mới.

Ví dụ thay thế:
    python scripts/run_pipeline.py --book "MyBook" --input "input/mybook.pdf"
    python scripts/run_pipeline.py --book "MyBook" --from-step 6
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

print("[DEPRECATED] translate_full_pipeline.py: dùng run_pipeline.py thay th\u1ebf.", file=sys.stderr)
print(f"  Chuy\u1ec3n l\u1ec7nh sang: python scripts/run_pipeline.py {' '.join(sys.argv[1:])}\n", file=sys.stderr)

cmd = [sys.executable, str(SCRIPT_DIR / 'run_pipeline.py')] + sys.argv[1:]
result = subprocess.run(cmd)
sys.exit(result.returncode)
