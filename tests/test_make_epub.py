import pytest
from pathlib import Path


class TestEpub:
    @pytest.fixture(autouse=True)
    def _setup(self, epub_test_output: Path):
        self.epub_path = epub_test_output

    def test_epub_file_exists(self):
        assert self.epub_path.exists(), f'EPUB file not found: {self.epub_path}'

    def test_epub_readable(self):
        from ebooklib import epub
        book = epub.read_epub(str(self.epub_path))
        titles = book.get_metadata('DC', 'title')
        assert any('Test Book' in str(t) for t in titles), f'Title not found: {titles}'

    def test_epub_contains_html_classes(self):
        from ebooklib import epub
        book = epub.read_epub(str(self.epub_path))
        found_classes = False
        for item in book.get_items():
            if item.get_type() == 9:
                content = item.get_content().decode('utf-8')
                if 'tri-block' in content or 'bi-block' in content:
                    found_classes = True
                    break
        assert found_classes, 'No HTML block classes (tri-block/bi-block) found in any document'

    def test_epub_has_vi_class(self):
        from ebooklib import epub
        book = epub.read_epub(str(self.epub_path))
        found_vi = False
        for item in book.get_items():
            if item.get_type() == 9:
                content = item.get_content().decode('utf-8')
                if 'class="vi"' in content:
                    found_vi = True
                    break
        assert found_vi, 'No HTML .vi class found in any document'

    def test_epub_has_toc(self):
        from ebooklib import epub
        book = epub.read_epub(str(self.epub_path))
        has_nav = any(item.get_type() == 9 and 'nav' in item.get_name()
                      for item in book.get_items())
        assert has_nav, 'No table of contents (nav) found'
