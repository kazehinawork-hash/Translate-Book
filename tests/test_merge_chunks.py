import sys
sys.path.insert(0, 'scripts')

from merge_chunks import merge_texts, validate_chunk_coverage


def _make_chunk(cid: int, text: str, chapter: str = '', total: int = 10,
                original_text: str | None = None,
                pinyin_text: str = '') -> tuple[int, dict]:
    return (cid, {
        'chunk_id': cid,
        'chapter': chapter,
        'total_chunks': total,
        'translated_text': text,
        'original_text': original_text if original_text is not None else text,
        'pinyin_text': pinyin_text,
        'word_count_source': len(text.split()),
        'word_count_translated': len(text.split()),
    })


class TestChunkCoverage:
    def test_duplicate_ids_and_inconsistent_totals(self):
        result = validate_chunk_coverage([
            (0, {"chunk_id": 0, "total_chunks": 2, "translated_text": "A"}),
            (0, {"chunk_id": 0, "total_chunks": 3, "translated_text": "B"}),
        ])
        assert result["duplicate_ids"] == [0]
        assert result["inconsistent_totals"] == [2]

    def test_missing_and_empty_ids(self):
        result = validate_chunk_coverage([
            (0, {"chunk_id": 0, "total_chunks": 3, "translated_text": "A"}),
            (2, {"chunk_id": 2, "total_chunks": 3, "translated_text": ""}),
        ])
        assert result["missing_ids"] == [1]
        assert result["empty_ids"] == [2]
        assert result["missing_all"] == [1, 2]


class TestChapterHeadings:
    def test_no_chapter_field(self):
        chunks = dict([
            _make_chunk(0, 'Content 0'),
            _make_chunk(1, 'Content 1'),
        ])
        result = merge_texts(2, chunks, 'bilingual', False, False)
        assert '## ' not in result['merged'], 'No headings expected when chapter field is empty'
        assert result['merged_count'] == 2

    def test_single_chapter(self):
        chunks = dict([
            _make_chunk(0, 'Content 0', chapter='Chuong 1'),
            _make_chunk(1, 'Content 1'),
        ])
        result = merge_texts(2, chunks, 'bilingual', False, False)
        assert '## Chuong 1' in result['merged']
        count = result['merged'].count('## ')
        assert count == 1, f'Expected 1 heading, got {count}'

    def test_two_chapters(self):
        chunks = dict([
            _make_chunk(0, 'Content 0', chapter='Chuong 1'),
            _make_chunk(1, 'Content 1'),
            _make_chunk(2, 'Content 2', chapter='Chuong 2'),
            _make_chunk(3, 'Content 3'),
        ])
        result = merge_texts(4, chunks, 'bilingual', False, False)
        assert '## Chuong 1' in result['merged']
        assert '## Chuong 2' in result['merged']
        count = result['merged'].count('## ')
        assert count == 2, f'Expected 2 headings, got {count}'

    def test_consecutive_same_chapter_no_repeat(self):
        chunks = dict([
            _make_chunk(0, 'Content 0', chapter='Chuong 1'),
            _make_chunk(1, 'Content 1', chapter='Chuong 1'),
            _make_chunk(2, 'Content 2', chapter='Chuong 2'),
        ])
        result = merge_texts(3, chunks, 'bilingual', False, False)
        count = result['merged'].count('## ')
        assert count == 2, f'Expected 2 headings (no repeat), got {count}'

    def test_heading_before_first_chunk(self):
        chunks = dict([
            _make_chunk(0, 'Mo dau'),
            _make_chunk(1, 'Chap 1 start', chapter='Chuong 1'),
            _make_chunk(2, 'More content'),
        ])
        result = merge_texts(3, chunks, 'bilingual', False, False)
        lines = result['merged'].split('\n')
        heading_idx = next(i for i, l in enumerate(lines) if '## Chuong 1' in l)
        assert heading_idx > 0, 'Heading should not be the very first line'
        assert any('Mo dau' in l for l in lines[:heading_idx]), 'Mo dau should appear before the heading'

    def test_page_break_before_second_chapter(self):
        chunks = dict([
            _make_chunk(0, 'Intro', chapter='Mo dau'),
            _make_chunk(1, 'Chap 1', chapter='Chuong 1'),
        ])
        result = merge_texts(2, chunks, 'bilingual', False, False)
        # Page break should appear before chapter 1 (second chapter), not before mo dau
        assert "page-break-before" in result['merged'], 'Expected page-break before second chapter'
        first_chapter_pos = result['merged'].find('## Mo dau')
        page_break_pos = result['merged'].find('page-break-before')
        second_chapter_pos = result['merged'].find('## Chuong 1')
        assert page_break_pos > first_chapter_pos, 'page-break should be after first chapter heading'
        assert page_break_pos < second_chapter_pos, 'page-break should be before second chapter heading'

    def test_trilingual_with_chapters(self):
        chunks = dict([
            _make_chunk(0, 'Line 1A\nLine 1B', chapter='Chuong 1',
                        original_text='Line 1A\nLine 1B', pinyin_text='L1A\nL1B'),
            _make_chunk(1, 'Line 2', chapter='Chuong 2',
                        original_text='Line 2', pinyin_text='L2'),
        ])
        result = merge_texts(2, chunks, 'trilingual', False, False)
        assert '## Chuong 1' in result['merged']
        assert '## Chuong 2' in result['merged']
        assert 'tri-block' in result['merged']
        assert 'page-break-before' in result['merged']
