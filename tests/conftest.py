import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope='module')
def epub_test_output():
    """Tạo file .epub từ test_input.md bằng make_epub.py.

    Skip toàn bộ module test_make_epub nếu pandoc chưa cài.
    Dọn .epub sau khi test xong.
    """
    if shutil.which('pandoc') is None:
        pytest.skip('pandoc chưa được cài đặt — bỏ qua test EPUB')

    test_data = Path(__file__).parent / 'test_epub_data'
    input_md = test_data / 'test_input.md'
    output_epub = test_data / 'test_input.epub'

    # Xoá file .epub cũ nếu còn sót
    if output_epub.exists():
        output_epub.unlink()

    make_epub = Path(__file__).parent.parent / 'scripts' / 'make_epub.py'
    result = subprocess.run(
        [sys.executable, str(make_epub),
         str(input_md), '--title', 'Test Book', '--author', 'Test Author'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        pytest.fail(f'make_epub.py thất bại (mã {result.returncode}): {stderr}')

    yield output_epub

    # Dọn dẹp
    if output_epub.exists():
        output_epub.unlink()
