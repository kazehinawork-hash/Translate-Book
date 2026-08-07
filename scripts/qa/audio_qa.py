"""Kiểm tra chất lượng và coverage audiobook đã tạo."""

from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import wave
from pathlib import Path


def wav_info(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        raw = wav.readframes(frames)
    peak = 0
    if sample_width == 2 and raw:
        values = struct.unpack(f"<{len(raw) // 2}h", raw)
        peak = max(abs(value) for value in values)
    return {
        "frames": frames,
        "duration": frames / sample_rate if sample_rate else 0,
        "sample_rate": sample_rate,
        "channels": channels,
        "peak": peak / 32767 if sample_width == 2 else None,
        "silent": not any(raw),
    }


CHAPTER_RE = re.compile(
    r"^\s*(?:#+\s*)?(?:Ch(?:ương|ƯƠNG)|Chapter|Quy(?:ển|YỂN)|Ph(?:ần|ẦN))\s+\d+",
    re.IGNORECASE | re.MULTILINE,
)
FALLBACK_HEADING_RE = re.compile(r"^#{1,2}\s+(.+)$", re.MULTILINE)


def find_vi_file(project_root: Path, slug: str) -> Path | None:
    candidates = [
        project_root / "output" / "books" / slug / "final" / "vi.md",
        project_root / "output" / "books" / slug / f"{slug}-vi.md",
        project_root / "output" / slug / f"{slug}-vi.md",
    ]
    return next((path for path in candidates if path.exists()), None)


def source_chapter_count(vi_file: Path) -> int:
    text = vi_file.read_text(encoding="utf-8-sig")
    numeric = len(CHAPTER_RE.findall(text))
    if numeric:
        return numeric
    fallback = [m.group(1) for m in FALLBACK_HEADING_RE.finditer(text)
                if "mục lục" not in m.group(1).lower()]
    return len(fallback)


def audio_chapter_numbers(audio_dir: Path) -> list[int]:
    return sorted(
        int(match.group(1))
        for path in audio_dir.glob("ch*.mp3")
        if (match := re.match(r"ch(\d+)\.mp3", path.name))
    )


def mp3_duration(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=False,
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, TypeError):
        return None


def inspect_audio(path: Path) -> dict:
    result = {"path": str(path), "exists": path.exists(), "size": 0, "ok": False, "errors": []}
    if not path.exists():
        result["errors"].append("không tìm thấy file")
        return result
    result["size"] = path.stat().st_size
    if result["size"] < 1000:
        result["errors"].append("file quá nhỏ hoặc rỗng")
    if path.suffix.lower() == ".wav":
        try:
            info = wav_info(path)
            result.update({"duration": info["duration"], "sample_rate": info["sample_rate"], "channels": info["channels"]})
            if info["frames"] <= 0 or info["duration"] <= 0:
                result["errors"].append("duration không hợp lệ")
            if info["sample_rate"] != 48000:
                result["errors"].append(f"sample rate {info['sample_rate']}, cần 48000")
            if info["silent"]:
                result["errors"].append("audio im lặng hoàn toàn")
            elif info["peak"] is not None and info["peak"] >= 1.0:
                result["errors"].append("có nguy cơ clipping")
        except Exception as exc:
            result["errors"].append(f"không đọc được WAV: {exc}")
    else:
        duration = mp3_duration(path)
        if duration is not None:
            result["duration"] = duration
            if duration <= 0:
                result["errors"].append("duration không hợp lệ")
    result["ok"] = not result["errors"]
    return result


def qa_audiobook(project_root: Path, slug: str) -> dict:
    vi_file = find_vi_file(project_root, slug)
    if vi_file is None:
        return {"slug": slug, "ok": False, "errors": ["không tìm thấy vi.md"], "chapters": []}
    source_count = source_chapter_count(vi_file)
    audio_dir = project_root / "output" / "books" / slug / "audiobook"
    actual = audio_chapter_numbers(audio_dir) if audio_dir.exists() else []
    expected = list(range(1, max(source_count, max(actual, default=0)) + 1))
    chapters = []
    for number in expected:
        mp3 = audio_dir / f"ch{number:02d}.mp3"
        wav = audio_dir / f"ch{number:02d}.wav"
        chapters.append({"chapter": number, "audio": inspect_audio(mp3 if mp3.exists() else wav)})
    errors = []
    if not audio_dir.exists():
        errors.append("không tìm thấy thư mục audiobook")
    if source_count and len(actual) < source_count:
        errors.append(f"thiếu chapter audio: có {len(actual)}, nguồn ước tính {source_count}")
    if actual and actual != list(range(1, max(actual) + 1)):
        errors.append(f"số chapter audio không liên tục: {actual}")
    errors.extend(f"chương {item['chapter']}: {err}" for item in chapters for err in item["audio"]["errors"])
    return {"slug": slug, "source": str(vi_file), "source_chapter_count": source_count,
            "audio_chapters": actual, "chapters": chapters, "errors": errors, "ok": not errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="QA audiobook theo vi.md")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = qa_audiobook(args.project_root, args.slug)
    report = args.report or args.project_root / "working" / "qa" / args.slug / "audio-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
