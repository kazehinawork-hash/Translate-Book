import sys

sys.path.insert(0, "scripts")

from qa.batch_qa import check_chunk


def test_trilingual_alignment():
    errors = check_chunk({
        "mode": "trilingual",
        "original_text": "原文一\n原文二",
        "pinyin_text": "yuan wen yi\nyuan wen er",
        "translated_text": "Bản một\nBản hai",
    })
    assert errors == []


def test_trilingual_mismatch_and_marker():
    errors = check_chunk({
        "mode": "trilingual",
        "original_text": "原文一\n原文二",
        "pinyin_text": "yuan wen yi",
        "translated_text": "---SKIP---",
    })
    assert len(errors) == 2
