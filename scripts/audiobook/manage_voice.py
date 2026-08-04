"""
Quản lý reference audio cho voice cloning (VieNeu-TTS).

Lưu reference 1 lần, tái sử dụng cho tất cả scripts audiobook.

Usage:
    # Extract + save reference từ MP3 (chỉ định thời điểm)
    python scripts/manage_voice.py extract --name van_tinh --source "core/file.mp3" --start 120 --duration 8

    # Tự động tìm đoạn giọng sạch nhất (energy VAD, không cần --start)
    python scripts/manage_voice.py extract --name van_tinh --source "core/file.mp3" --auto --duration 8

    # Chọn voice đang dùng (copy → active.wav)
    python scripts/manage_voice.py set-active van_tinh

    # Xem voice đang dùng
    python scripts/manage_voice.py active

    # List tất cả voices đã lưu
    python scripts/manage_voice.py list

    # Xem chi tiết 1 voice
    python scripts/manage_voice.py info van_tinh

    # Preview voice (tạo audio test 5s)
    python scripts/manage_voice.py preview van_tinh
    python scripts/manage_voice.py preview van_tinh --text "Xin chào, đây là giọng đọc test"
    python scripts/manage_voice.py preview active

    # Xóa voice
    python scripts/manage_voice.py delete van_tinh
"""
import sys
import os
import re
import json
import time
import argparse
import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES_DIR = os.path.join(PROJECT_ROOT, "core", "voices")
ACTIVE_WAV = os.path.join(VOICES_DIR, "active.wav")
ACTIVE_JSON = os.path.join(VOICES_DIR, "active.json")
os.makedirs(VOICES_DIR, exist_ok=True)

# TTS cache (lazy load)
_tts_instance = None


def _get_tts():
    """Get or create cached TTS instance."""
    global _tts_instance
    if _tts_instance is None:
        import vieneu
        _tts_instance = vieneu.Vieneu()
    return _tts_instance


def _sanitize_name(name: str) -> str:
    """Chname thành identifier an toàn: lowercase, bỏ ký tự đặc biệt."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9_-]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def _voice_path(name: str) -> tuple:
    """Trả về (wav_path, json_path) cho voice name."""
    return (
        os.path.join(VOICES_DIR, f"{name}.wav"),
        os.path.join(VOICES_DIR, f"{name}.json"),
    )


def get_voice_path(name: str) -> str | None:
    """Trả về path WAV của voice theo tên. None nếu không tồn tại."""
    name = _sanitize_name(name)
    wav_path, _ = _voice_path(name)
    if os.path.exists(wav_path):
        return wav_path
    return None


def _to_mono(data):
    """Convert stereo → mono, tránh triệt tiêu phase (downmix bằng mean)."""
    if len(data.shape) == 1:
        return data
    mean = data.mean(axis=1)
    peak_mean = np.max(np.abs(mean))
    peak_ch1 = np.max(np.abs(data[:, 0]))
    # Nếu mean bị triệt tiêu nặng (>50%), dùng channel 1 thay thế
    if peak_mean < 0.3 * peak_ch1:
        return data[:, 0]
    return mean


def _find_auto_segment(data, sr, duration=8.0):
    """Tìm đoạn 'giọng đọc sạch' nhất bằng energy VAD heuristic.

    Yêu cầu window có speech_ratio >= 0.5 (đa số frame hoạt động),
    rồi chọn window có động lực tốt nhất (speech biến thiên, nhạc nền
    đồng đều). Trả về start_time (giây).
    """
    hop = int(sr * 0.02)      # 20ms window
    window = int(sr * 0.05)   # 50ms window
    n = len(data)
    if n < window:
        return 0.0

    n_frames = (n - window) // hop
    rms = np.empty(n_frames, dtype=np.float32)
    for i in range(n_frames):
        seg = data[i * hop:i * hop + window]
        rms[i] = np.sqrt(np.mean(seg ** 2))

    # Ngưỡng: 5x noise floor (percentile 15) → tách sạch speech khỏi im lặng
    noise_floor = np.percentile(rms, 15)
    thr = max(noise_floor * 5.0, 1e-4)
    active = rms > thr

    frames_per_win = int(duration * sr / hop)
    if frames_per_win <= 0:
        return 0.0

    candidates = []
    for i in range(0, max(1, len(active) - frames_per_win), frames_per_win):
        seg_active = active[i:i + frames_per_win]
        seg_rms = rms[i:i + frames_per_win]
        speech_ratio = np.mean(seg_active)
        if speech_ratio < 0.5:
            continue
        # Động lực: speech có sự biến thiên lớn (lặng xen kẽ), nhạc nền đồng đều
        dynamics = np.std(seg_rms) / (np.mean(seg_rms) + 1e-9)
        clip_penalty = 1.0 if np.max(seg_rms) < 0.6 else 0.4
        candidates.append((min(dynamics, 1.2) * clip_penalty, i * hop / sr))

    if candidates:
        # Ưu tiên động lực cao (giọng đọc), tránh nhạc nền đều
        best_score, best_start = max(candidates, key=lambda c: c[0])
    else:
        # Không có window nào đạt chuẩn → fallback: chọn window nhiều speech nhất
        best_ratio, best_start = 0.0, 0.0
        for i in range(0, max(1, len(active) - frames_per_win), frames_per_win):
            ratio = np.mean(active[i:i + frames_per_win])
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i * hop / sr
    return best_start


def extract_voice(name: str, source: str, start: float, duration: float,
                  description: str = "", gender: str = "", auto: bool = False) -> str:
    """
    Trích xuất reference audio từ file MP3/WAV → save vào core/voices/.

    Nếu auto=True → tự tìm đoạn giọng sạch nhất (bỏ qua start).
    Returns: path to saved WAV file.
    """
    name = _sanitize_name(name)
    wav_path, json_path = _voice_path(name)

    # Resolve source path
    if not os.path.isabs(source):
        source = os.path.join(PROJECT_ROOT, source)
    if not os.path.exists(source):
        raise FileNotFoundError(f"Source audio not found: {source}")

    print(f"📂 Reading: {os.path.basename(source)}")
    data, sr = sf.read(source)
    total_duration = data.shape[0] / sr
    print(f"   {sr} Hz, {'stereo' if len(data.shape) > 1 else 'mono'}, {total_duration:.0f}s ({total_duration/60:.1f} min)")

    # Convert to mono (tránh triệt tiêu phase)
    data = _to_mono(data)

    # Auto-detect đoạn giọng sạch
    if auto:
        start = _find_auto_segment(data, sr, duration=duration)
        print(f"   🎯 Auto-detect: bắt đầu tại {start:.1f}s")

    # Extract segment
    start_sample = int(start * sr)
    end_sample = int((start + duration) * sr)
    if end_sample > len(data):
        end_sample = len(data)
        duration = (end_sample - start_sample) / sr
        print(f"   ⚠️  Adjusted duration to {duration:.1f}s (reached end of file)")

    ref_audio = data[start_sample:end_sample]

    # Normalize
    peak = np.max(np.abs(ref_audio))
    if peak > 0:
        ref_audio = ref_audio / peak * 0.95

    # Save WAV
    sf.write(wav_path, ref_audio, sr)

    # Save metadata
    metadata = {
        "name": name,
        "source_file": os.path.relpath(source, PROJECT_ROOT),
        "start_time": start,
        "duration": round(duration, 2),
        "sample_rate": sr,
        "description": description,
        "gender": gender,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved: {wav_path}")
    print(f"   Duration: {duration:.1f}s, {sr} Hz")
    print(f"   Metadata: {json_path}")

    # Validate
    warnings = validate_reference(wav_path)
    if warnings:
        print(f"   ⚠️  Warnings:")
        for w in warnings:
            print(f"      - {w}")

    return wav_path


def validate_reference(wav_path: str) -> list:
    """Kiểm tra chất lượng reference audio. Trả về list warnings."""
    warnings = []
    info = sf.info(wav_path)

    if info.duration < 3.0:
        warnings.append(f"Duration quá ngắn ({info.duration:.1f}s). Nên dùng >= 3s.")
    if info.duration > 15.0:
        warnings.append(f"Duration quá dài ({info.duration:.1f}s). Nên dùng 3-8s.")
    if info.samplerate < 16000:
        warnings.append(f"Sample rate thấp ({info.samplerate} Hz). Nên dùng >= 16000 Hz.")

    # Check peak level
    data, _ = sf.read(wav_path)
    peak = np.max(np.abs(data))
    if peak < 0.01:
        warnings.append(f"Âm lượng quá thấp (peak={peak:.4f}). Có thể là file im lặng.")
    elif peak < 0.1:
        warnings.append(f"Âm lượng thấp (peak={peak:.2f}). Nên normalize.")

    return warnings


def preview_voice(name: str, text: str = None):
    """Tạo audio test từ reference voice."""
    name = _sanitize_name(name)

    # Handle "active" special case
    if name == "active":
        wav_path = ACTIVE_WAV
        if not os.path.exists(wav_path):
            print("❌ No active voice set.")
            return
    else:
        wav_path, _ = _voice_path(name)
        if not os.path.exists(wav_path):
            print(f"❌ Voice '{name}' not found.")
            return

    if text is None:
        text = "Chào bạn, đây là giọng đọc test. Cuốn sách này nói về cuộc đời của một người phụ nữ."

    print(f"🔊 Preview voice: {name}")
    print(f"   Reference: {wav_path}")

    try:
        tts = _get_tts()
        tts.add_voice("preview_voice", wav_path, description="Preview", denoise=False)

        print(f"   Text: \"{text[:60]}...\"")
        t0 = time.time()
        audio = tts.infer(text, voice="preview_voice", style="doc_truyen", max_chars=256,
                          apply_watermark=False)
        elapsed = time.time() - t0

        # Save
        preview_dir = os.path.join(PROJECT_ROOT, "output", "voice_preview")
        os.makedirs(preview_dir, exist_ok=True)
        preview_path = os.path.join(preview_dir, f"preview_{name}.wav")
        sf.write(preview_path, audio, 48000)

        info = sf.info(preview_path)
        print(f"\n   ✅ Preview: {preview_path}")
        print(f"   Duration: {info.duration:.1f}s | Gen: {elapsed:.1f}s")
    except ImportError:
        print("❌ vieneu not installed. Run: pip install vieneu")
    except Exception as e:
        print(f"❌ Preview failed: {e}")


def list_voices():
    """Liệt kê tất cả voices đã lưu."""
    wavs = sorted([f for f in os.listdir(VOICES_DIR) if f.endswith(".wav")])
    if not wavs:
        print("📭 No voices saved yet.")
        print(f"   Extract with: python scripts/manage_voice.py extract --name <name> --source <mp3> --start <sec>")
        return

    print(f"{'Name':<20} {'Duration':>8} {'Gender':<8} {'Description'}")
    print("-" * 70)
    for wav_file in wavs:
        name = wav_file[:-4]
        _, json_path = _voice_path(name)
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            dur = meta.get("duration", "?")
            gender = meta.get("gender", "")
            desc = meta.get("description", "")[:40]
            print(f"{name:<20} {dur:>6.1f}s  {gender:<8} {desc}")
        else:
            info = sf.info(os.path.join(VOICES_DIR, wav_file))
            print(f"{name:<20} {info.duration:>6.1f}s  {'':8} (no metadata)")

    print(f"\n📁 {VOICES_DIR}")


def show_info(name: str):
    """Hiển thị chi tiết 1 voice."""
    name = _sanitize_name(name)
    wav_path, json_path = _voice_path(name)

    if not os.path.exists(wav_path):
        print(f"❌ Voice '{name}' not found.")
        return

    info = sf.info(wav_path)
    print(f"🔊 Voice: {name}")
    print(f"   File: {wav_path}")
    print(f"   Duration: {info.duration:.1f}s, {info.samplerate} Hz")

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        print(f"   Source: {meta.get('source_file', '?')}")
        print(f"   Start: {meta.get('start_time', '?')}s")
        print(f"   Gender: {meta.get('gender', '?')}")
        print(f"   Description: {meta.get('description', '?')}")
        print(f"   Created: {meta.get('created_at', '?')}")
    else:
        print("   ⚠️  No metadata file")


def delete_voice(name: str):
    """Xóa voice."""
    name = _sanitize_name(name)
    wav_path, json_path = _voice_path(name)

    if not os.path.exists(wav_path):
        print(f"❌ Voice '{name}' not found.")
        return

    os.remove(wav_path)
    print(f"🗑️  Deleted: {wav_path}")
    if os.path.exists(json_path):
        os.remove(json_path)
        print(f"🗑️  Deleted: {json_path}")


def set_active(name: str):
    """Chọn voice đang dùng: copy → active.wav + active.json."""
    name = _sanitize_name(name)
    wav_path, json_path = _voice_path(name)

    if not os.path.exists(wav_path):
        print(f"❌ Voice '{name}' not found. Use 'list' to see available voices.")
        return

    # Copy WAV
    import shutil
    shutil.copy2(wav_path, ACTIVE_WAV)

    # Copy JSON (or create minimal one)
    if os.path.exists(json_path):
        shutil.copy2(json_path, ACTIVE_JSON)
    else:
        meta = {"name": name, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(ACTIVE_JSON, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    info = sf.info(ACTIVE_WAV)
    print(f"✅ Active voice: {name}")
    print(f"   File: {ACTIVE_WAV}")
    print(f"   Duration: {info.duration:.1f}s, {info.samplerate} Hz")


def show_active():
    """Hiển thị voice đang dùng."""
    if not os.path.exists(ACTIVE_WAV):
        print("⚠️  No active voice set.")
        print(f"   Set with: python scripts/manage_voice.py set-active <name>")
        return

    info = sf.info(ACTIVE_WAV)
    print(f"🔊 Active voice: {info.duration:.1f}s, {info.samplerate} Hz")
    print(f"   File: {ACTIVE_WAV}")

    if os.path.exists(ACTIVE_JSON):
        with open(ACTIVE_JSON, "r", encoding="utf-8") as f:
            meta = json.load(f)
        print(f"   Name: {meta.get('name', '?')}")
        print(f"   Source: {meta.get('source_file', '?')}")
        print(f"   Description: {meta.get('description', '?')}")


def resolve_voice(auto_set: bool = True, non_interactive: bool = False) -> str | None:
    """
    Tự động chọn voice để dùng.
    1. Nếu active.wav tồn tại → dùng luôn
    2. Nếu có voices nhưng chưa set → hỏi user chọn
    3. Nếu không có voice nào → trả về None

    non_interactive=True: không gọi input(), tự động chọn voice đầu tiên.
    Returns: path to active.wav, hoặc None nếu không có voice.
    """
    # 1. Active voice đã có
    if os.path.exists(ACTIVE_WAV):
        meta = {}
        if os.path.exists(ACTIVE_JSON):
            with open(ACTIVE_JSON, "r", encoding="utf-8") as f:
                meta = json.load(f)
        name = meta.get("name", "active")
        print(f"🔊 Using active voice: {name}")
        return ACTIVE_WAV

    # 2. Có voices nhưng chưa set active
    voices = _list_voice_names()
    if not voices:
        print("❌ No voices found. Run:")
        print('   python scripts/manage_voice.py extract --name <name> --source <mp3> --start 120 --duration 8')
        return None

    if len(voices) == 1:
        # Only 1 voice → auto-select
        name = voices[0]
        print(f"🔊 Only 1 voice available, auto-selecting: {name}")
        if auto_set:
            set_active(name)
        return _voice_path(name)[0]

    # Multiple voices → ask user (hoặc auto-select nếu non-interactive)
    if non_interactive:
        name = voices[0]
        print(f"🔊 Non-interactive mode: tự động chọn voice đầu tiên: {name}")
        if auto_set:
            set_active(name)
        return _voice_path(name)[0]

    print("🔊 Available voices:")
    for i, name in enumerate(voices):
        _, json_path = _voice_path(name)
        desc = ""
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            desc = meta.get("description", "")[:50]
        print(f"   [{i+1}] {name} — {desc}")

    while True:
        try:
            choice = input(f"\nChọn voice [1-{len(voices)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(voices):
                name = voices[idx]
                if auto_set:
                    set_active(name)
                return _voice_path(name)[0]
            print(f"   Invalid choice. Enter 1-{len(voices)}.")
        except (ValueError, EOFError):
            print("   Invalid input.")
            return None


def _list_voice_names() -> list:
    """Liệt kê tên tất cả voices (trừ active.wav)."""
    if not os.path.exists(VOICES_DIR):
        return []
    return sorted([
        f[:-4] for f in os.listdir(VOICES_DIR)
        if f.endswith(".wav") and f != "active.wav"
    ])


def main():
    parser = argparse.ArgumentParser(description="Quản lý reference audio cho voice cloning")
    sub = parser.add_subparsers(dest="command")

    # extract
    p_ext = sub.add_parser("extract", help="Extract reference audio từ MP3/WAV")
    p_ext.add_argument("--name", required=True, help="Tên voice (vd: van_tinh)")
    p_ext.add_argument("--source", required=True, help="Path file MP3/WAV nguồn")
    p_ext.add_argument("--start", type=float, default=120.0, help="Thời gian bắt đầu (giây, default: 120)")
    p_ext.add_argument("--duration", type=float, default=8.0, help="Thời lượng (giây, default: 8)")
    p_ext.add_argument("--description", default="", help="Mô tả voice")
    p_ext.add_argument("--gender", default="", help="Giới tính (male/female)")
    p_ext.add_argument("--auto", action="store_true",
                       help="Tự động tìm đoạn giọng sạch nhất (energy VAD)")

    # list
    sub.add_parser("list", help="Liệt kê tất cả voices")

    # info
    p_info = sub.add_parser("info", help="Xem chi tiết voice")
    p_info.add_argument("name", help="Tên voice")

    # delete
    p_del = sub.add_parser("delete", help="Xóa voice")
    p_del.add_argument("name", help="Tên voice")

    # set-active
    p_act = sub.add_parser("set-active", help="Chọn voice đang dùng (copy → active.wav)")
    p_act.add_argument("name", help="Tên voice")

    # active
    sub.add_parser("active", help="Xem voice đang dùng")

    # preview
    p_prev = sub.add_parser("preview", help="Preview voice (tạo audio test)")
    p_prev.add_argument("name", help="Tên voice (hoặc 'active')")
    p_prev.add_argument("--text", default=None, help="Text để đọc (default: sample text)")

    args = parser.parse_args()

    if args.command == "extract":
        extract_voice(args.name, args.source, args.start, args.duration,
                      args.description, args.gender, auto=args.auto)
    elif args.command == "list":
        list_voices()
    elif args.command == "info":
        show_info(args.name)
    elif args.command == "delete":
        delete_voice(args.name)
    elif args.command == "set-active":
        set_active(args.name)
    elif args.command == "active":
        show_active()
    elif args.command == "preview":
        preview_voice(args.name, args.text)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
