import sys
sys.path.insert(0, 'scripts')

from post_extract_qc import kiem_tra_mojibake, MOJIBAKE_PATTERNS, HAS_FTFY


def test_mojibake_empty_text():
    """Text rỗng → không có mojibake."""
    assert kiem_tra_mojibake("") == []


def test_mojibake_clean_text():
    """Text sạch (ASCII + UTF-8 hợp lệ) → không có mojibake."""
    text = "The quick brown fox jumps over the lazy dog.\nHello world!"
    assert kiem_tra_mojibake(text) == []


def test_mojibake_clean_chinese():
    """Text tiếng Trung sạch → không có mojibake."""
    text = "今天天气很好。\n我们去公园散步。"
    assert kiem_tra_mojibake(text) == []


def test_mojibake_latin1_utf8():
    """UTF-8 bytes đọc sai thành Latin-1 → phát hiện mojibake."""
    text = "VoilÃ  lÃ  mÃ©chant"  # "Voilà le méchant" bị mojibake
    results = kiem_tra_mojibake(text)
    assert len(results) >= 1
    line, preview, desc = results[0]
    assert "Mojibake" in desc or "mojibake" in desc or "UTF-8" in desc or "ftfy" in desc


def test_mojibake_smart_quotes():
    """Smart quote bị hỏng → phát hiện mojibake."""
    text = "He said â€œhelloâ€"  # smart quotes broken
    results = kiem_tra_mojibake(text)
    assert len(results) >= 1
    line, preview, desc = results[0]
    assert "Mojibake" in desc or "Smart quote" in desc or "broken" in desc or "ftfy" in desc


def test_mojibake_bom():
    """BOM ở đầu dòng → phát hiện."""
    text = "\ufeffHello world"
    results = kiem_tra_mojibake(text)
    assert len(results) >= 1


def test_mojibake_replacement_char():
    """Ký tự thay thế U+FFFD → phát hiện."""
    text = "Bad \ufffd encoding here"
    results = kiem_tra_mojibake(text)
    assert len(results) >= 1


def test_mojibake_mixed_clean_and_dirty():
    """Text có cả dòng sạch và dòng mojibake → chỉ phát hiện dòng bẩn."""
    text = "Clean line.\nVoilÃ  lÃ  mÃ©chant\nAnother clean."
    results = kiem_tra_mojibake(text)
    assert len(results) == 1
    line, preview, desc = results[0]
    assert line == 2


def test_mojibake_only_blank_lines():
    """Chỉ dòng trống → không có mojibake (bỏ qua dòng trống)."""
    text = "\n\n\n\n"
    assert kiem_tra_mojibake(text) == []
