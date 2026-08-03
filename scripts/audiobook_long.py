"""
Tạo audiobook từ file -vi.md (thuần Việt) — clone giọng VieNeu-TTS.

Auto-detect chapters, chunk + generate + join.

Usage:
    # Tạo audio toàn cuốn sách (auto-detect slug từ filename)
    python scripts/audiobook_long.py

    # Chỉ tạo 1 chapter cụ thể
    python scripts/audiobook_long.py --chapter 1

    # Tạo nhiều chapters
    python scripts/audiobook_long.py --chapter 1 2 3

    # Chỉ tạo chapter đầu tiên (nhanh, test)
    python scripts/audiobook_long.py --first
"""
import sys, os, re, time, argparse
import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Config
MAX_CHARS = 240          # chars per chunk (VieNeu limit ~256)
SILENCE_BETWEEN = 0.4    # seconds silence between chunks
SILENCE_PARA = 0.8       # seconds silence between paragraphs
SAMPLE_RATE = 48000


def find_vi_md(slug: str = None) -> tuple:
    """Tìm file -vi.md. Trả về (path, slug)."""
    output_dir = os.path.join(PROJECT_ROOT, "output")
    if slug:
        path = os.path.join(output_dir, slug, f"{slug}-vi.md")
        if os.path.exists(path):
            return path, slug
        raise FileNotFoundError(f"File not found: {path}")

    # Auto-detect: find first -vi.md in output/
    for d in os.listdir(output_dir):
        vi_path = os.path.join(output_dir, d, f"{d}-vi.md")
        if os.path.exists(vi_path):
            return vi_path, d

    raise FileNotFoundError(f"No *-vi.md found in {output_dir}")


def detect_chapters(md_path: str) -> list:
    """Phát hiện tất cả chapters trong file -vi.md.
    Trả về list of (chapter_num, title, line_start, line_end).
    """
    chapters = []
    chapter_re = re.compile(r"^#\s*[（(](\d+)[）)]\s*(.*)")
    all_lines = []

    with open(md_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            all_lines.append(line.rstrip())

    for i, line in enumerate(all_lines):
        m = chapter_re.match(line)
        if m:
            num = int(m.group(1))
            title = m.group(2).strip()
            chapters.append({
                "num": num,
                "title": title,
                "line_start": i,
            })

    # Set line_end for each chapter
    for idx in range(len(chapters) - 1):
        chapters[idx]["line_end"] = chapters[idx + 1]["line_start"]
    if chapters:
        chapters[-1]["line_end"] = len(all_lines)

    return chapters, all_lines


def extract_chapter_text(lines: list, start: int, end: int) -> list:
    """Trích xuất text Việt từ 1 chapter (line range)."""
    vi_lines = []
    for line in lines[start:end]:
        stripped = line.strip()
        # Skip separator, heading, html, image
        if stripped == "---":
            continue
        if stripped.startswith("#"):
            continue
        if re.match(r"^</?[a-zA-Z]", stripped):
            continue
        if re.match(r"^!\[.*\]\(.*\)$", stripped) or stripped.startswith("![]"):
            continue
        # Strip markdown emphasis
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
        text = re.sub(r"\*(.*?)\*", r"\1", text)
        if not text.strip() or len(text.strip()) <= 2:
            continue
        vi_lines.append(text.strip())
    return vi_lines


def smart_chunk(lines, max_chars=MAX_CHARS):
    """Chunk lines thành các đoạn <= max_chars, giữ nguyên câu."""
    chunks = []
    current = ""
    for line in lines:
        if current and len(current) + len(line) + 1 > max_chars:
            chunks.append(current.strip())
            current = line
        else:
            current = current + " " + line if current else line
    if current.strip():
        chunks.append(current.strip())
    return chunks


def make_silence(duration, sr=SAMPLE_RATE):
    return np.zeros(int(duration * sr), dtype=np.float32)


def generate_chapter_audio(tts, voice_name, chunks, chapter_num, verbose=True):
    """Generate audio cho 1 chapter. Returns (audio_array, gen_time)."""
    all_audio = []
    total_gen_time = 0

    for i, chunk in enumerate(chunks):
        t0 = time.time()
        audio = tts.infer(
            chunk,
            voice=voice_name,
            style="doc_truyen",
            max_chars=256,
            temperature=0.7,
            top_k=20,
        )
        elapsed = time.time() - t0
        total_gen_time += elapsed

        audio = audio.squeeze()
        all_audio.append(audio)

        # Add silence
        is_para_end = chunk.rstrip().endswith((".", "!", "?", '"'))
        silence_dur = SILENCE_PARA if is_para_end else SILENCE_BETWEEN
        all_audio.append(make_silence(silence_dur))

        if verbose:
            dur = len(audio) / SAMPLE_RATE
            pct = (i + 1) / len(chunks) * 100
            print(f"      [{i+1:3d}/{len(chunks)}] {pct:5.1f}% | {dur:.1f}s | {elapsed:.1f}s | \"{chunk[:40]}...\"")

    final = np.concatenate(all_audio)
    # Normalize
    peak = np.max(np.abs(final))
    if peak > 0:
        final = final / peak * 0.92

    return final, total_gen_time


def main():
    parser = argparse.ArgumentParser(description="Tạo audiobook từ -vi.md")
    parser.add_argument("--slug", help="Book slug (auto-detect nếu bỏ trống)")
    parser.add_argument("--chapter", type=int, nargs="+", help="Chapter cụ thể (vd: --chapter 1 2 3)")
    parser.add_argument("--first", action="store_true", help="Chỉ tạo chapter đầu tiên (test nhanh)")
    args = parser.parse_args()

    # 1. Find -vi.md
    vi_md, slug = find_vi_md(args.slug)
    print(f"📖 Book: {slug}")
    print(f"   File: {vi_md}")

    # 2. Detect chapters
    chapters, all_lines = detect_chapters(vi_md)
    print(f"📑 Found {len(chapters)} chapters")

    # Select which chapters to generate
    if args.first:
        selected = [chapters[0]]
    elif args.chapter:
        selected = [ch for ch in chapters if ch["num"] in args.chapter]
        if not selected:
            print(f"❌ Chapters {args.chapter} not found. Available: {[ch['num'] for ch in chapters]}")
            return
    else:
        selected = chapters

    # Output dir: output/<slug>/
    out_dir = os.path.join(PROJECT_ROOT, "output", slug)
    os.makedirs(out_dir, exist_ok=True)

    # 3. Load TTS
    print("\n🎙️ Loading VieNeu-TTS v3 Turbo...")
    import vieneu
    tts = vieneu.Vieneu()

    sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
    from manage_voice import resolve_voice
    ref_path = resolve_voice()
    if not ref_path:
        return
    voice_name = "active_voice"
    tts.add_voice(voice_name, ref_path,
                  description="Active voice for audiobook",
                  gender="female")

    # 4. Generate audio for each selected chapter
    total_gen = 0
    total_audio = 0
    total_size = 0

    for ch in selected:
        num = ch["num"]
        title = ch["title"]
        start = ch["line_start"]
        end = ch["line_end"]

        print(f"\n{'─'*50}")
        print(f"📑 Chapter {num:02d}: {title}")
        print(f"   Lines {start+1}-{end} ({end-start} lines)")

        # Extract text
        vi_lines = extract_chapter_text(all_lines, start, end)
        total_chars = sum(len(l) for l in vi_lines)
        print(f"   {len(vi_lines)} dòng, {total_chars} ký tự")

        if not vi_lines:
            print("   ⚠️  No text found, skipping")
            continue

        # Chunk
        chunks = smart_chunk(vi_lines)
        print(f"   {len(chunks)} chunks (max {MAX_CHARS} chars)")

        # Generate
        print(f"   🎵 Generating...")
        audio, gen_time = generate_chapter_audio(tts, voice_name, chunks, num)

        # Save
        wav_path = os.path.join(out_dir, f"{slug}-ch{num:02d}.wav")
        sf.write(wav_path, audio, SAMPLE_RATE)

        info = sf.info(wav_path)
        size_mb = os.path.getsize(wav_path) / 1024 / 1024
        total_gen += gen_time
        total_audio += info.duration
        total_size += size_mb

        print(f"   ✅ {wav_path}")
        print(f"      Duration: {info.duration:.1f}s ({info.duration/60:.1f} min) | Gen: {gen_time:.1f}s | RTF: {gen_time/info.duration:.2f} | {size_mb:.1f} MB")

    # 5. Summary
    print(f"\n{'='*50}")
    print(f"🎧 HOÀN THÀNH — {slug}")
    print(f"   Chapters: {len(selected)}/{len(chapters)}")
    print(f"   Total audio: {total_audio:.1f}s ({total_audio/60:.1f} min)")
    print(f"   Total gen time: {total_gen:.1f}s ({total_gen/60:.1f} min)")
    print(f"   RTF: {total_gen/total_audio:.2f}")
    print(f"   Total size: {total_size:.1f} MB")
    print(f"   Output: {out_dir}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
