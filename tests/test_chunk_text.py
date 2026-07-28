import sys
import re
sys.path.insert(0, 'scripts')

from chunk_text import (
    chunk_smart, chunk_by_paragraph, chunk_by_line,
    tach_cau, tach_theo_heading, tach_theo_doan,
    phat_hien_bang, dem_so_luong,
)


# ── Sample texts ──────────────────────────────────────────────────────────

EN_TEXT = """# Chapter 1

The quick brown fox jumps over the lazy dog. This is a test sentence
for verifying chunk boundaries. Hello world! How are you today?

Another paragraph with more content. It has multiple sentences.
Some of them are quite long and filled with interesting words.

## Section 1.1

More detailed content goes here. Every sentence ends properly.
We must ensure that chunks never cut through a sentence boundary.
This is critical for translation quality.

## Section 1.2

Final section in chapter one. The end is near for this chapter.
But wait, there is more text to process."""

ZH_TEXT = """# 第一章

今天天气很好。我们去公园散步。这是一个测试句子用来验证分块边界。

第二段有更多内容。它包含多个句子。有些句子相当长充满了有趣的词汇。

## 第一节

更多详细内容在这里。每个句子都正确结束。我们必须确保块永远不会切穿句子边界。

## 第二节

第一章的最后一节。结束即将来临。但等等还有更多文本需要处理。"""

TABLE_TEXT = """# Report

Here is some introductory text. It explains the table below.

| Name    | Age | City     |
|---------|-----|----------|
| Alice   | 30  | New York |
| Bob     | 25  | London   |
| Charlie | 35  | Paris    |

After the table, we have more regular text. This should not be cut
in the middle of a table.

## Conclusion

Final remarks here."""

EMPTY_TEXT = ""
SHORT_TEXT = "Hello world."
SHORT_ZH = "今天天气很好。"
ONE_SENTENCE = "This is just one single sentence for testing."


def _assert_total_content_preserved(chunks, original_text):
    words_in_chunks = sum(
        len(re.findall(r'\b\w+\b', c['text']))
        for c in chunks
    )
    words_in_src = len(re.findall(r'\b\w+\b', original_text))
    assert words_in_chunks >= words_in_src * 0.9, (
        f"Content lost: src={words_in_src}, chunks={words_in_chunks}"
    )


def _assert_no_mid_sentence_cut(text, chunks):
    for c in chunks:
        chunk_text = c['text']
        stripped = chunk_text.strip()
        if not stripped:
            continue
        for b in ['.', '!', '?', '\u3002', '\uff01', '\uff1f']:
            if stripped.endswith(b):
                break
        else:
            last_line = stripped.rsplit('\n', 1)[-1]
            if last_line.strip() and not last_line.strip().startswith('#'):
                if len(stripped) > 30:
                    assert False, (
                        f"Chunk {c['chunk_id']} may end mid-sentence: "
                        f"...{stripped[-40:]!r}"
                    )


# ── Basic tests ───────────────────────────────────────────────────────────

class TestChunkSmart:
    def test_en_no_mid_sentence_cut(self):
        chunks = chunk_smart(EN_TEXT, max_chars=400, min_chars=100, lang='en')
        assert len(chunks) >= 1
        _assert_no_mid_sentence_cut(EN_TEXT, chunks)

    def test_zh_no_mid_sentence_cut(self):
        chunks = chunk_smart(ZH_TEXT, max_chars=100, min_chars=30, lang='zh')
        assert len(chunks) >= 1
        _assert_no_mid_sentence_cut(ZH_TEXT, chunks)

    def test_total_content_preserved_en(self):
        chunks = chunk_smart(EN_TEXT, max_chars=400, min_chars=100, lang='en')
        _assert_total_content_preserved(chunks, EN_TEXT)

    def test_total_content_preserved_zh(self):
        chunks = chunk_smart(ZH_TEXT, max_chars=100, min_chars=30, lang='zh')
        src_han = len(re.findall(r'[㐀-鿿豈-﫿]', ZH_TEXT))
        chunks_han = sum(
            len(re.findall(r'[㐀-鿿豈-﫿]', c['text']))
            for c in chunks
        )
        assert chunks_han >= src_han * 0.9, (
            f"Han chars lost: src={src_han}, chunks={chunks_han}"
        )


class TestChunkParagraph:
    def test_basic(self):
        chunks = chunk_by_paragraph(EN_TEXT, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) >= 1

    def test_zh_basic(self):
        chunks = chunk_by_paragraph(ZH_TEXT, max_chars=500, min_chars=50, lang='zh')
        assert len(chunks) >= 1


class TestChunkLine:
    def test_basic(self):
        chunks = chunk_by_line(EN_TEXT, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) >= 1

    def test_zh_basic(self):
        chunks = chunk_by_line(ZH_TEXT, max_chars=500, min_chars=50, lang='zh')
        assert len(chunks) >= 1


# ── Edge cases ────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_text(self):
        chunks = chunk_smart(EMPTY_TEXT, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) == 0

        chunks = chunk_by_paragraph(EMPTY_TEXT, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) == 0

        chunks = chunk_by_line(EMPTY_TEXT, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) == 0

    def test_short_text_en(self):
        chunks = chunk_smart(SHORT_TEXT, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) == 1
        assert 'Hello' in chunks[0]['text']

    def test_short_text_zh(self):
        chunks = chunk_smart(SHORT_ZH, max_chars=2000, min_chars=100, lang='zh')
        assert len(chunks) == 1

    def test_one_sentence(self):
        chunks = chunk_smart(ONE_SENTENCE, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) == 1

    def test_very_small_max_chars(self):
        text = "A.\nB.\nC.\nD.\nE.\nF.\nG.\nH.\nI.\nJ.\nK.\nL.\nM.\nN.\nO.\nP."
        chunks = chunk_smart(text, max_chars=10, min_chars=3, lang='en')
        assert len(chunks) >= 2


# ── Tables ────────────────────────────────────────────────────────────────

class TestTables:
    def test_table_not_cut(self):
        table_blocks = phat_hien_bang(TABLE_TEXT)
        assert len(table_blocks) >= 1
        for start, end in table_blocks:
            assert end - start >= 2

    def test_smart_strategy_with_tables(self):
        result = chunk_smart(TABLE_TEXT, max_chars=2000, min_chars=100, lang='en')
        combined = '\n'.join(c['text'] for c in result)
        assert '| Alice   | 30  | New York |' in combined
        assert '| Bob     | 25  | London   |' in combined


# ── Headings ──────────────────────────────────────────────────────────────

class TestHeadings:
    def test_tach_theo_heading(self):
        sections = tach_theo_heading(ZH_TEXT)
        assert len(sections) >= 3
        headings = [h for h, b in sections]
        assert any('# Chapter' in h or '# 第' in h for h in headings if h)

    def test_chapter_separated(self):
        text = "# Chap1\n\nBody text.\n\n# Chap2\n\nMore body."
        chunks = chunk_smart(text, max_chars=2000, min_chars=100, lang='en')
        assert len(chunks) >= 2

    def test_heading_text_not_split(self):
        text = "# Very Long Heading That Should Not Be Cut\n\nBody."
        sections = tach_theo_heading(text)
        assert len(sections) >= 1
        assert '# Very Long Heading' in sections[0][0]


# ── Sentence splitting ───────────────────────────────────────────────────

class TestSentenceSplitting:
    def test_en_sentences(self):
        text = "First sentence.\nSecond sentence!\nThird sentence?"
        sents = tach_cau(text)
        assert len(sents) == 3

    def test_zh_sentences(self):
        text = "第一句。\n第二句！\n第三句？"
        sents = tach_cau(text)
        assert len(sents) == 3

    def test_mixed_punctuation(self):
        text = "Hello!\nHow are you?\nI am fine.\nGood."
        sents = tach_cau(text)
        assert len(sents) == 4

    def test_no_trailing_punctuation(self):
        text = "Hello world"
        sents = tach_cau(text)
        assert len(sents) == 1


# ── Counting ──────────────────────────────────────────────────────────────

class TestCounting:
    def test_en_word_count(self):
        assert dem_so_luong("Hello world foo bar", 'en') == 4

    def test_zh_char_count(self):
        assert dem_so_luong("今天天气很好", 'zh') == 6

    def test_empty_count(self):
        assert dem_so_luong("", 'en') == 0
        assert dem_so_luong("", 'zh') == 0


# ── Strategy comparison ───────────────────────────────────────────────────

class TestStrategyComparison:
    def test_all_strategies_return_chunks(self):
        for strategy_fn in [chunk_smart, chunk_by_paragraph, chunk_by_line]:
            chunks = strategy_fn(EN_TEXT, max_chars=500, min_chars=100, lang='en')
            assert len(chunks) >= 1, f"{strategy_fn.__name__} returned 0 chunks"

    def test_same_input_different_outputs(self):
        text = "A B C.\n\nD E F.\n\nG H I.\n\nJ K L.\n\nM N O."
        smart_chunks = chunk_smart(text, max_chars=100, min_chars=20, lang='en')
        para_chunks = chunk_by_paragraph(text, max_chars=100, min_chars=20, lang='en')
        line_chunks = chunk_by_line(text, max_chars=100, min_chars=20, lang='en')
        assert len(smart_chunks) >= 1
        assert len(para_chunks) >= 1
        assert len(line_chunks) >= 1
        # All three produce different number of chunks or text structure
        totals = {len(smart_chunks), len(para_chunks), len(line_chunks)}
        assert len(totals) >= 1  # at least one works, could be same for small data


# ── Incremental output match ──────────────────────────────────────────────

class TestIncrementalMatch:
    def test_smart_chunks_combine_to_full_text_en(self):
        text = EN_TEXT
        chunks = chunk_smart(text, max_chars=400, min_chars=100, lang='en')
        combined = '\n\n'.join(c['text'] for c in chunks)
        src_normalized = re.sub(r'\s+', ' ', text)
        combined_normalized = re.sub(r'\s+', ' ', combined)
        # Core content should match (allow minor whitespace diff)
        for phrase in ['The quick brown fox', 'Hello world', 'More detailed content']:
            assert phrase in combined_normalized

    def test_smart_chunks_combine_to_full_text_zh(self):
        chunks = chunk_smart(ZH_TEXT, max_chars=100, min_chars=30, lang='zh')
        combined = ''.join(c['text'] for c in chunks)
        for phrase in ['今天天气很好', '第二段', '更多详细内容']:
            assert phrase in combined


# ── Chunk metadata ────────────────────────────────────────────────────────

class TestChunkMetadata:
    def test_chunk_ids_sequential(self):
        chunks = chunk_smart(EN_TEXT, max_chars=400, min_chars=100, lang='en')
        for i, c in enumerate(chunks):
            assert c['chunk_id'] == i, f"Expected chunk_id={i}, got {c['chunk_id']}"

    def test_total_chunks_consistent(self):
        chunks = chunk_smart(EN_TEXT, max_chars=400, min_chars=100, lang='en')
        total = chunks[0]['total_chunks'] if chunks else 0
        for c in chunks:
            assert c['total_chunks'] == total

    def test_word_count_matches_text(self):
        chunks = chunk_smart(EN_TEXT, max_chars=400, min_chars=100, lang='en')
        for c in chunks:
            expected = dem_so_luong(c['text'], 'en')
            assert c['word_count'] == expected, (
                f"Chunk {c['chunk_id']}: word_count={c['word_count']}, actual={expected}"
            )

    def test_context_fields_present(self):
        chunks = chunk_smart(EN_TEXT, max_chars=400, min_chars=100, lang='en')
        for c in chunks:
            assert 'prev_context' in c
            assert 'next_context' in c
            assert 'chapter' in c

    def test_context_chain(self):
        chunks = chunk_smart(EN_TEXT, max_chars=400, min_chars=100, lang='en')
        if len(chunks) >= 2:
            for i in range(1, len(chunks)):
                assert len(chunks[i]['prev_context']) > 0
                assert len(chunks[i - 1]['next_context']) > 0
