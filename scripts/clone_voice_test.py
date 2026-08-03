"""
Clone giọng nói từ file audiobook mẫu bằng VieNeu-TTS v3 Turbo.

Bước 1: Trích xuất 5-10s reference audio từ file MP3
Bước 2: Clone giọng + test đọc text Việt

Usage:
    python scripts/clone_voice_test.py
"""
import sys
import os
import time
import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", "voice_clone_test")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === CONFIG ===
AUDIOBOOK_PATH = os.path.join(
    PROJECT_ROOT, "core",
    "[SÁCH NÓI] Bạn Đắt Giá Bao Nhiêu _ _ Vãn Tình _ [FULL] - (320 Kbps).mp3"
)
REFERENCE_DURATION = 8  # seconds
# Start at 2:00 (120s) — typically past intro music, into clear narration
REFERENCE_START = 120

TEST_TEXTS = [
    "Chào bạn, đây là giọng nói đượcclone từ sách nói Bạn Đắt Giá Bao Nhiêu của tác giả Vãn Tình.",
    "Mỗi người phụ nữ đều có quyền được hạnh phúc, được yêu thương và được sống là chính mình.",
    "Đừng bao giờ để người khác quyết định giá trị của bạn. Bạn đáng giá hơn những gì họ nghĩ.",
    "Cuộc đời ngắn ngủi lắm, hãy sống thật trọn vẹn với những điều mình yêu thích.",
]


def extract_reference():
    """Trích xuất reference audio từ audiobook."""
    print(f"📂 Đang đọc file: {os.path.basename(AUDIOBOOK_PATH)}")
    data, sr = sf.read(AUDIOBOOK_PATH)
    print(f"   Sample rate: {sr} Hz, Channels: {data.shape[1] if len(data.shape) > 1 else 1}")
    print(f"   Duration: {data.shape[0]/sr:.0f}s ({data.shape[0]/sr/60:.1f} min)")

    # Convert to mono if stereo
    if len(data.shape) > 1:
        data = data.mean(axis=1)

    # Extract segment
    start_sample = int(REFERENCE_START * sr)
    end_sample = int((REFERENCE_START + REFERENCE_DURATION) * sr)
    ref_audio = data[start_sample:end_sample]

    # Normalize
    peak = np.max(np.abs(ref_audio))
    if peak > 0:
        ref_audio = ref_audio / peak * 0.95

    ref_path = os.path.join(OUTPUT_DIR, "reference.wav")
    sf.write(ref_path, ref_audio, sr)
    print(f"✅ Reference audio: {ref_path}")
    print(f"   Duration: {len(ref_audio)/sr:.1f}s, Sample rate: {sr} Hz")
    return ref_path


def clone_and_test(ref_path):
    """Clone giọng và test đọc text."""
    print("\n🎙️ Đang khởi tạo VieNeu-TTS v3 Turbo...")
    import vieneu

    tts = vieneu.Vieneu()
    print(f"   Model loaded: v3-turbo")

    # Register cloned voice
    voice_name = "van_tinh_clone"
    print(f"\n🔊 Đang clone giọng từ reference ({REFERENCE_DURATION}s)...")
    tts.add_voice(
        voice_name,
        ref_path,
        description="Clone từ sách nói Vãn Tình - Bạn Đắt Giá Bao Nhiêu",
        gender="female",
    )
    print(f"   ✅ Voice '{voice_name}' registered")

    def save_audio(audio_np, path, sr=48000):
        """Save numpy audio array to WAV."""
        if audio_np.ndim > 1:
            audio_np = audio_np.squeeze()
        sf.write(path, audio_np, sr)

    # Test each text
    for i, text in enumerate(TEST_TEXTS):
        print(f"\n📝 Test {i+1}/{len(TEST_TEXTS)}: {text[:50]}...")
        out_path = os.path.join(OUTPUT_DIR, f"clone_test_{i+1}.wav")
        t0 = time.time()
        audio = tts.infer(text, voice=voice_name)
        elapsed = time.time() - t0
        save_audio(audio, out_path)

        info = sf.info(out_path)
        print(f"   ✅ Output: {out_path}")
        print(f"   Duration: {info.duration:.1f}s, Time: {elapsed:.1f}s")

    # Also test with different styles
    print(f"\n🎨 Test style 'doc_truyen'...")
    text = "Ngày xưa, ở một ngôi làng nhỏ ven sông, có một cô gái tên là Lan. Cô có giọng hát hay nhất vùng."
    out_path = os.path.join(OUTPUT_DIR, "clone_test_style_doc_truyen.wav")
    t0 = time.time()
    audio = tts.infer(text, voice=voice_name, style="doc_truyen")
    elapsed = time.time() - t0
    save_audio(audio, out_path)
    info = sf.info(out_path)
    print(f"   ✅ Output: {out_path} ({info.duration:.1f}s, {elapsed:.1f}s)")

    # Test emotion
    print(f"\n😊 Test emotion [cười]...")
    text = "Hôm nay là một ngày thật đẹp [cười] Bạn có thấy bầu trời hôm nay tuyệt lắm không?"
    out_path = os.path.join(OUTPUT_DIR, "clone_test_emotion.wav")
    t0 = time.time()
    audio = tts.infer(text, voice=voice_name)
    elapsed = time.time() - t0
    save_audio(audio, out_path)
    info = sf.info(out_path)
    print(f"   ✅ Output: {out_path} ({info.duration:.1f}s, {elapsed:.1f}s)")


if __name__ == "__main__":
    print("=" * 60)
    print("VOICE CLONE TEST — VieNeu-TTS v3 Turbo")
    print("=" * 60)

    ref_path = extract_reference()
    clone_and_test(ref_path)

    print("\n" + "=" * 60)
    print(f"✅ All outputs in: {OUTPUT_DIR}")
    print("=" * 60)
