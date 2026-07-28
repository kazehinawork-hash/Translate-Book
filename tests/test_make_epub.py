import sys
sys.path.insert(0, 'scripts')

from pathlib import Path

TEST_DATA = Path(__file__).parent / 'test_epub_data'
TEST_INPUT = TEST_DATA / 'test_input.md'
TEST_OUTPUT = TEST_DATA / 'test_input.epub'


def test_epub_file_exists():
    assert TEST_OUTPUT.exists(), f'EPUB file not found: {TEST_OUTPUT}'


def test_epub_readable():
    from ebooklib import epub
    book = epub.read_epub(str(TEST_OUTPUT))
    titles = book.get_metadata('DC', 'title')
    assert any('Test Book' in str(t) for t in titles), f'Title not found: {titles}'


def test_epub_contains_html_classes():
    from ebooklib import epub
    book = epub.read_epub(str(TEST_OUTPUT))
    found_classes = False
    for item in book.get_items():
        if item.get_type() == 9:
            content = item.get_content().decode('utf-8')
            if 'tri-block' in content or 'bi-block' in content:
                found_classes = True
                break
    assert found_classes, 'No HTML block classes (tri-block/bi-block) found in any document'


def test_epub_has_vi_class():
    from ebooklib import epub
    book = epub.read_epub(str(TEST_OUTPUT))
    found_vi = False
    for item in book.get_items():
        if item.get_type() == 9:
            content = item.get_content().decode('utf-8')
            if 'class="vi"' in content:
                found_vi = True
                break
    assert found_vi, 'No HTML .vi class found in any document'


def test_epub_has_toc():
    from ebooklib import epub
    book = epub.read_epub(str(TEST_OUTPUT))
    has_nav = any(item.get_type() == 9 and 'nav' in item.get_name()
                  for item in book.get_items())
    assert has_nav, 'No table of contents (nav) found'
