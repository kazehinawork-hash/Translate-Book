import sys
import wave

sys.path.insert(0, "scripts")

from qa.audio_qa import inspect_audio, qa_audiobook


def test_inspect_valid_wav(tmp_path):
    path = tmp_path / "ch01.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes((int(0.2 * 32767)).to_bytes(2, "little", signed=True) * 48000)
    result = inspect_audio(path)
    assert result["ok"]
    assert result["sample_rate"] == 48000
    assert result["duration"] == 1.0


def write_wav(path, sample_rate):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes((int(0.2 * 32767)).to_bytes(2, "little", signed=True) * sample_rate)


def test_inspect_invalid_sample_rate(tmp_path):
    path = tmp_path / "ch01.wav"
    write_wav(path, 16000)
    result = inspect_audio(path)
    assert not result["ok"]
    assert any("sample rate" in error for error in result["errors"])


def test_qa_detects_missing_chapter(tmp_path):
    vi = tmp_path / "vi.md"
    vi.write_text("# Chương 1\n\nNội dung.\n\n# Chương 2\n\nNội dung.", encoding="utf-8")
    audio_dir = tmp_path / "audiobook"
    audio_dir.mkdir()
    write_wav(audio_dir / "ch01.wav", 48000)
    root = tmp_path / "output" / "books" / "book" / "final"
    root.mkdir(parents=True)
    vi.rename(root / "vi.md")
    (tmp_path / "output" / "books" / "book" / "audiobook").mkdir()
    (tmp_path / "output" / "books" / "book" / "audiobook" / "ch01.wav").write_bytes(audio_dir.joinpath("ch01.wav").read_bytes())
    result = qa_audiobook(tmp_path, "book")
    assert not result["ok"]
    assert any("chương 2" in error for error in result["errors"])
