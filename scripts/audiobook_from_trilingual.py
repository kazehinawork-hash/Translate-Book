"""
Tạo audiobook từ file bản dịch -vi.md (thuần Việt) — giọng clone + style doc_truyen.

Input: output/<slug>/<slug>-vi.md  (được tạo ở bước 9 Merge)
Output: audio WAV/MP3 dùng VieNeu-TTS clone giọng
"""
import sys, os, re
import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", "voice_clone_test")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VI_MD = os.path.join(
    PROJECT_ROOT, "output",
    "zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing",
    "zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing-vi.md"
)


def extract_vi_text(md_path):
    """Đọc text tiếng Việt từ file -vi.md, bỏ qua metadata/ảnh/separator."""
    vi_lines = []
    in_metadata = True  # Skip block metadata ở đầu file
    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            stripped = line.strip()
            # Skip heading标记, separator, ảnh, html
            if stripped.startswith("#") or stripped == "---":
                in_metadata = False
                continue
            if re.match(r'^!\[.*\]\(.*\)$', stripped) or stripped.startswith("![]"):
                continue
            if re.match(r'^</?[a-zA-Z]', stripped):
                continue
            # Skip metadata bold lines ở đầu (Tác giả, Ngôn ngữ, Số chương)
            if in_metadata and re.match(r'^\*\*.*\*\*', stripped):
                continue
            # Strip markdown emphasis
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', stripped)
            text = re.sub(r'\*(.*?)\*', r'\1', text)
            if not text.strip():
                continue
            vi_lines.append(text.strip())
    return vi_lines


def find_nice_passage(vi_lines, min_chars=200, max_chars=800):
    """Tìm đoạn văn hay, liền mạch."""
    # Skip first ~50 lines (metadata, CIP, etc.)
    content_lines = vi_lines[50:]
    
    # Build paragraphs by joining consecutive short lines
    paragraphs = []
    current = []
    for line in content_lines:
        # Skip lines that look like metadata
        if re.match(r'^[\d\.\s\-:\/]+$', line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)
        # If line ends with period/comma/newline, it might be end of sentence
        if len(" ".join(current)) > 100:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    
    # Find a passage with nice length
    for p in paragraphs:
        # Clean up
        p = re.sub(r'\s+', ' ', p).strip()
        if min_chars <= len(p) <= max_chars:
            return p
    
    # If no perfect match, concatenate short paragraphs
    passage = ""
    for p in paragraphs:
        p = re.sub(r'\s+', ' ', p).strip()
        if not p:
            continue
        if len(passage) + len(p) + 1 > max_chars:
            break
        passage += " " + p if passage else p
    
    return passage.strip()[:max_chars]


if __name__ == "__main__":
    print("=" * 60)
    print("AUDIOBOOK — Clone Voice + Doc Truyen Style")
    print("=" * 60)

    # Extract Vietnamese text from -vi.md
    print(f"\n📖 Đang đọc text từ: {VI_MD}")
    vi_lines = extract_vi_text(VI_MD)
    print(f"   Found {len(vi_lines)} dòng text")

    # Find a nice passage
    passage = find_nice_passage(vi_lines)
    print(f"\n📝 Đoạn văn ({len(passage)} chars):")
    print(f"   \"{passage[:200]}...\"")

    # Save passage to text file
    passage_path = os.path.join(OUTPUT_DIR, "passage.txt")
    with open(passage_path, "w", encoding="utf-8") as f:
        f.write(passage)
    print(f"\n💾 Passage saved: {passage_path}")

    # Load VieNeu-TTS and clone voice
    print("\n🎙️ Đang load VieNeu-TTS v3 Turbo...")
    import vieneu
    tts = vieneu.Vieneu()

    # Auto-select voice: active → pick from list
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
    from manage_voice import resolve_voice
    ref_path = resolve_voice()
    if not ref_path:
        sys.exit(1)
    voice_name = "active_voice"

    print(f"🔊 Clone giọng từ: {ref_path}")
    tts.add_voice(voice_name, ref_path,
                  description="Active voice",
                  gender="female")

    # Generate audio with doc_truyen style
    print(f"\n🎵 Generating audio (style=doc_truyen)...")
    import time
    t0 = time.time()
    audio = tts.infer(
        passage,
        voice=voice_name,
        style="doc_truyen",
        max_chars=256,
        temperature=0.7,
        top_k=20,
    )
    elapsed = time.time() - t0

    # Save
    out_path = os.path.join(OUTPUT_DIR, "audiobook_sample.wav")
    sf.write(out_path, audio, 48000)
    info = sf.info(out_path)

    print(f"\n✅ Output: {out_path}")
    print(f"   Duration: {info.duration:.1f}s")
    print(f"   Generation time: {elapsed:.1f}s")
    print(f"   RTF: {elapsed/info.duration:.2f}")

    mp3_path = os.path.join(OUTPUT_DIR, "audiobook_sample.mp3")
    try:
        sf.write(mp3_path, audio, 48000)
        print(f"   MP3: {mp3_path}")
    except:
        pass

    print(f"\n{'='*60}")
    print(f"🎧 Nghe tại: {OUTPUT_DIR}")
    print(f"{'='*60}")
