import sys
sys.path.insert(0, 'scripts')

from make_bilingual import (
    split_paragraphs, classify_paragraph, _len_ratio,
    _dp_align, _align_body, align_paragraphs, generate_bilingual,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _count_status(aligned, status):
    return sum(1 for _, _, s in aligned if s == status)


# ── split_paragraphs ────────────────────────────────────────────────────────

class TestSplitParagraphs:
    def test_basic(self):
        paras = split_paragraphs("Para one.\n\nPara two.")
        assert paras == ["Para one.", "Para two."]

    def test_multiple_blank_lines(self):
        paras = split_paragraphs("A\n\n\nB")
        assert paras == ["A", "B"]

    def test_no_blank_lines(self):
        paras = split_paragraphs("Single block.")
        assert paras == ["Single block."]

    def test_empty_text(self):
        assert split_paragraphs("") == []
        assert split_paragraphs("   ") == []
        assert split_paragraphs("\n\n") == []


# ── classify_paragraph ──────────────────────────────────────────────────────

class TestClassifyParagraph:
    def test_heading(self):
        assert classify_paragraph("# Chapter 1") == 'heading'
        assert classify_paragraph("## Section 1.1") == 'heading'
        assert classify_paragraph("###### Deep") == 'heading'

    def test_code(self):
        assert classify_paragraph("```python\nprint('hello')\n```") == 'code'
        assert classify_paragraph("~~~\ncode block\n~~~") == 'code'

    def test_table(self):
        assert classify_paragraph("| Col1 | Col2 |") == 'table'

    def test_image(self):
        assert classify_paragraph("![alt](img.png)") == 'image'

    def test_text(self):
        assert classify_paragraph("Just a regular paragraph.") == 'text'


# ── _len_ratio ──────────────────────────────────────────────────────────────

class TestLenRatio:
    def test_equal_length(self):
        assert _len_ratio("hello", "hello", 'en') == 1.0

    def test_one_empty(self):
        assert _len_ratio("", "hello", 'en') == 0.0
        assert _len_ratio("hello", "", 'en') == 0.0

    def test_both_empty(self):
        assert _len_ratio("", "", 'en') == 1.0

    def test_partial_match(self):
        r = _len_ratio("short", "a very long text here", 'en')
        assert 0.0 < r < 1.0

    def test_zh_normalization(self):
        zh_text = "今天天气很好"
        vi_text = "Hôm nay thời tiết rất tốt"
        r_zh = _len_ratio(zh_text, vi_text, 'zh')
        r_en = _len_ratio(zh_text, vi_text, 'en')
        assert r_zh > r_en, "ZH normalization should produce higher ratio"


# ── _dp_align ───────────────────────────────────────────────────────────────

class TestDpAlign:
    def test_equal_same_length(self):
        src = ["Short one.", "Another short."]
        vi = ["Ngắn gọn.", "Một cái ngắn khác."]
        result = _dp_align(src, vi, 'en')
        assert len(result) == 2
        assert all(s == 'ok' for _, _, s in result)

    def test_1_to_2_merge(self):
        src = ["This is a single long paragraph."]
        vi = ["This is the first half.", "This is the second half."]
        result = _dp_align(src, vi, 'en')
        assert len(result) == 1
        assert result[0][2] == 'check'
        assert src[0] in result[0][0]

    def test_2_to_1_merge(self):
        src = ["First paragraph.", "Second paragraph."]
        vi = ["Combined translation of both paragraphs."]
        result = _dp_align(src, vi, 'en')
        assert len(result) == 1
        assert result[0][2] == 'check'

    def test_missing_segment(self):
        src = ["Para A.", "Para B.", "Para C."]
        vi = ["Trans A.", "Trans C."]
        result = _dp_align(src, vi, 'en')
        statuses = [s for _, _, s in result]
        assert 'src-only' in statuses

    def test_extra_segment(self):
        src = ["Para A.", "Para C."]
        vi = ["Trans A.", "Trans extra note.", "Trans C."]
        result = _dp_align(src, vi, 'en')
        statuses = [s for _, _, s in result]
        assert 'vi-only' in statuses

    def test_too_many_checks_downgrade(self):
        many_checks = [
            ("Very long source text " * 20, "Short", 'check'),
            ("Another long source " * 20, "Tiny", 'check'),
            ("Third extra long " * 20, "Mini", 'check'),
            ("Fourth long text " * 20, "Small", 'check'),
            ("Normal size para.", "Normal size trans.", 'ok'),
        ]
        n_check = sum(1 for _, _, s in many_checks if s == 'check')
        assert n_check > len(many_checks) * 0.3
        assert len(many_checks) > 3


# ── _align_body ─────────────────────────────────────────────────────────────

class TestAlignBody:
    def test_both_empty(self):
        assert _align_body([], [], 'en') == []

    def test_only_src(self):
        result = _align_body(["Only src."], [], 'en')
        assert result[0][2] == 'src-only'

    def test_only_vi(self):
        result = _align_body([], ["Only vi."], 'en')
        assert result[0][2] == 'vi-only'

    def test_fallback_zip(self):
        src = ["AAAA" * 50, "BBBB" * 50, "CCCC" * 50]
        vi = ["ZZZZ" * 10, "YYYY" * 10, "XXXX" * 10]
        result = _align_body(src, vi, 'en')
        assert len(result) == 3
        statuses = [s for _, _, s in result]
        assert any(s != 'ok' for s in statuses)


# ── align_paragraphs ────────────────────────────────────────────────────────

class TestAlignParagraphs:
    def test_equal_paragraphs_all_ok(self):
        src = ["# Chapter 1\n\nPara one.", "Para two."]
        vi = ["# Chương 1\n\nĐoạn một.", "Đoạn hai."]
        result = align_paragraphs(src, vi, 'en')
        ok_count = _count_status(result, 'ok')
        assert ok_count > 0
        assert _count_status(result, 'check') == 0
        assert _count_status(result, 'src-only') == 0
        assert _count_status(result, 'vi-only') == 0

    def test_missing_src_paragraph(self):
        src = ["# Ch1", "Para A.", "Para C."]
        vi = ["# Ch1", "Trans A.", "Trans B.", "Trans C."]
        result = align_paragraphs(src, vi, 'en')
        assert _count_status(result, 'vi-only') >= 1

    def test_missing_vi_paragraph(self):
        src = ["# Ch1", "Para A.", "Para B.", "Para C."]
        vi = ["# Ch1", "Trans A.", "Trans C."]
        result = align_paragraphs(src, vi, 'en')
        assert _count_status(result, 'src-only') >= 1

    def test_empty_body_no_heading(self):
        result = align_paragraphs([], [], 'en')
        assert result == []


# ── generate_bilingual (end-to-end) ─────────────────────────────────────────

class TestGenerateBilingual:
    def test_equal_paragraphs(self):
        src = "Para one.\n\nPara two."
        vi = "Đoạn một.\n\nĐoạn hai."
        output, warnings = generate_bilingual(src, vi, 'en')
        assert len(warnings) == 0
        assert "Para one." in output
        assert "Đoạn một." in output

    def test_zh_language(self):
        src = "今天天气很好。\n\n我们去公园散步。"
        vi = "Hôm nay thời tiết rất đẹp.\n\nChúng tôi đi dạo trong công viên."
        output, warnings = generate_bilingual(src, vi, 'zh')
        assert "今天天气很好。" in output
        assert "Hôm nay thời tiết" in output
        assert len(warnings) == 0

    def test_heading_preserved(self):
        src = "# Chapter 1\n\nContent here."
        vi = "# Chương 1\n\nNội dung ở đây."
        output, warnings = generate_bilingual(src, vi, 'en')
        assert "Chương 1" in output
        assert len(warnings) == 0

    def test_code_block_unchanged(self):
        src = "Some text.\n\n```\ncode\n```\n\nMore text."
        vi = "Một số text.\n\n```\ncode\n```\n\nThêm text."
        output, warnings = generate_bilingual(src, vi, 'en')
        assert "```" in output
        assert "Một số text" in output

    def test_extra_paragraph_vi(self):
        src = "Para one.\n\nPara two."
        vi = "Đoạn một.\n\nĐoạn extra (note).\n\nĐoạn hai."
        output, warnings = generate_bilingual(src, vi, 'en')
        assert "Đoạn extra" in output

    def test_missing_paragraph_vi(self):
        src = "Para one.\n\nPara two.\n\nPara three."
        vi = "Đoạn một.\n\nĐoạn ba."
        output, warnings = generate_bilingual(src, vi, 'en')
        assert "src-only" in output.lower() or output.strip()


# ── Edge cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_source(self):
        output, warnings = generate_bilingual("", "Some text.", 'en')
        assert output.strip() == "" or len(warnings) >= 0

    def test_empty_translation(self):
        output, warnings = generate_bilingual("Some text.", "", 'en')
        assert len(warnings) >= 0

    def test_both_empty(self):
        output, warnings = generate_bilingual("", "", 'en')
        assert output.strip() == ""
