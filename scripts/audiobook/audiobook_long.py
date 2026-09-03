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

    # Tạo 1 sample ngắn (~30s) để test giọng
    python scripts/audiobook_long.py --sample
    python scripts/audiobook_long.py --sample --sample-chars 500

    # Chạy lại từ đầu (bỏ qua progress)
    python scripts/audiobook_long.py --force
"""
import sys, os, re, time, argparse, json, shutil, hashlib, subprocess
import numpy as np
import soundfile as sf

# Text preprocessing trước TTS (text_normalize + pronunciation)
from text_normalize import normalize_for_tts
from pronunciation import apply_pronunciation

# scipy dùng cho fftconvolve (làm mượt envelope nhạc nền nhanh hơn np.convolve)
try:
    from scipy.signal import fftconvolve
except ImportError:
    fftconvolve = None

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Config
MAX_CHARS = 280          # chars per chunk (chunk dài hơn → model có ngữ cảnh, bớt nuốt phụ âm đầu câu/đoạn)
TTS_MAX_CHARS = 320      # giới hạn char của vieneu (phải >= MAX_CHARS để thư viện KHÔNG cắt lại → không vỡ câu)
SILENCE_BETWEEN = 0.4    # seconds silence between chunks
SILENCE_PARA = 0.8       # seconds silence between paragraphs
SILENCE_CHAPTER_END = 1.5 # seconds silence cuối chapter (trước khi chapter mới bắt đầu)
SAMPLE_RATE = 48000
MAX_RETRIES = 3          # retries per chunk on TTS failure
FADE_MS = 10             # fade in/out ở đầu/cuối chapter (tránh click khi start/stop)
CROSSFADE_MS = 15        # fade out/in nhẹ ở 2 đầu mỗi chunk trước khi chèn silence (chống click tại chỗ nối)
NORM_MASTER = 0.92       # normalize toàn chapter

# Nhạc nền (music bed) — trộn DƯỚI giọng đọc
MUSIC_DIR = os.path.join(PROJECT_ROOT, "core", "music")
MUSIC_VOLUME_DEFAULT = 0.12      # volume nhạc nền trung bình (tỷ lệ với giọng full-scale)
MUSIC_MIN_RATIO = 0.50           # khi giọng đọc: nhạc = volume * 0.5 (vd volume 0.2 → 10%)
MUSIC_MAX_RATIO = 1.0            # khi giọng nghỉ: nhạc = volume * 1.0 (vd volume 0.2 → 20%)
MUSIC_ENV_MS = 150               # làm mượt envelope (ms) — phản hồi nhanh, tự nhiên
MUSIC_CROSSFADE_MS = 6000        # crossfade tại điểm nối loop nhạc (tránh "click")
MUSIC_RISE_CAP_S = 1.2           # giới hạn thời gian nhạc "thở" lên khi giọng nghỉ (tránh nổi lâu)
MUSIC_TARGET_RMS = 0.18          # loudness chuẩn của nhạc nền sau normalize (mọi bài về cùng mức)


def _normalize(audio, target=NORM_MASTER):
    """Normalize audio về target peak. Không sửa mảng gốc."""
    peak = np.max(np.abs(audio))
    if peak <= 0:
        return audio
    return audio / peak * target


def _apply_fade(audio, fade_ms=FADE_MS):
    """Fade in/out ở đầu/cuối chapter để tránh click khi start/stop."""
    n = int(SAMPLE_RATE * fade_ms / 1000)
    if n <= 0 or len(audio) <= 2 * n:
        return audio
    audio = audio.copy()
    fade_in = np.linspace(0, 1, n, dtype=np.float32)
    fade_out = np.linspace(1, 0, n, dtype=np.float32)
    audio[:n] *= fade_in
    audio[-n:] *= fade_out
    return audio


def _edge_fade(audio, fade_ms=CROSSFADE_MS):
    """Fade ngắn (micro) ở 2 đầu chunk để chống click tại chỗ nối khi ghép.

    Khác ``_apply_fade`` (fade toàn chapter): chỉ nhún 2-3ms đầu/cuối về 0,
    không tạo cảm giác nghỉ — đủ để biên độ tại điểm nối = 0.
    """
    n = int(SAMPLE_RATE * fade_ms / 1000)
    if n <= 0 or len(audio) <= 2 * n:
        return audio
    audio = audio.copy()
    fade_in = np.linspace(0, 1, n, dtype=np.float32)
    fade_out = np.linspace(1, 0, n, dtype=np.float32)
    audio[:n] *= fade_in
    audio[-n:] *= fade_out
    return audio


def list_music_files():
    """Liệt kê file nhạc nền (mp3/wav) trong core/music/, sắp theo tên."""
    if not os.path.isdir(MUSIC_DIR):
        return []
    exts = (".mp3", ".wav", ".m4a", ".flac", ".ogg")
    files = [f for f in os.listdir(MUSIC_DIR)
             if os.path.splitext(f)[1].lower() in exts]
    return sorted(files)


def _resample(x, src_sr, dst_sr=SAMPLE_RATE):
    """Resample 1D float array về dst_sr bằng nội suy tuyến tính (đủ tốt cho nhạc nền)."""
    if src_sr == dst_sr or len(x) == 0:
        return x
    n = int(len(x) * dst_sr / src_sr)
    if n <= 1:
        return x[:1]
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def _loop_with_crossfade(music, total_samples):
    """Lặp nhạc cho đủ total_samples với crossfade mềm tại điểm nối.

    Tránh tiếng "click"/nhảy nhịp khi file nhạc ngắn hơn chapter và phải loop.
    """
    n = len(music)
    if n <= 0:
        return np.zeros(total_samples, dtype=np.float32)
    if total_samples <= n:
        return music[:total_samples]

    fade = int(SAMPLE_RATE * MUSIC_CROSSFADE_MS / 1000)
    fade = min(fade, n // 4)

    # Phần đầu/cuối dùng để crossfade: fade-out cuối + fade-in đầu
    tail = music[-fade:].copy()
    head = music[:fade].copy()
    ramp = np.linspace(0, 1, fade, dtype=np.float32)
    tail *= (1 - ramp)          # giảm dần về 0
    head *= ramp                # tăng dần từ 0

    # Chuẩn bị "vòng" nhạc: [tail (giảm) + head (tăng)] là phần nối mượt
    # Đơn giản hoá: nối chuỗi music liên tục, chèn crossfade ở ranh giới.
    out = np.zeros(total_samples, dtype=np.float32)
    pos = 0
    # Luôn phát trọn lần đầu từ đầu file (intro tự nhiên)
    while pos < total_samples:
        take = min(n, total_samples - pos)
        out[pos:pos + take] = music[:take]
        pos += take
        if pos >= total_samples:
            break
        # Tại điểm nối: áp crossfade — dùng bản music có tail/head đã chuẩn bị
        # Thay vì nối cứng, ta dùng phương pháp: phần fade-out cuối + fade-in đầu
        # đã được nhân sẵn → ghép vào là hết click.
        take = min(fade, total_samples - pos)
        if take > 0:
            out[pos:pos + take] = tail[:take]
        pos += take
        take = min(fade, total_samples - pos)
        if take > 0:
            out[pos:pos + take] = head[:take]
        pos += take
    return out


def mix_music_bed(voice, music_path, volume=MUSIC_VOLUME_DEFAULT,
                  min_ratio=MUSIC_MIN_RATIO, max_ratio=MUSIC_MAX_RATIO,
                  chapter_num=None, music_list=None):
    """Trộn nhạc nền DƯỚI giọng đọc (music bed) với ducking theo độ to giọng.

    - Nhạc tự "thở": dịu xuống khi giọng đọc, lên nhẹ khi giọng nghỉ.
    - Loop nhạc (nếu ngắn hơn chapter) bằng crossfade mềm — không click.
    - Giới hạn thời gian nhạc nổi lên (MUSIC_RISE_CAP_S) tránh nổi lâu khó chịu.
    - Trả về (mixed_audio, music_file_used).
    """
    if not music_path or not os.path.exists(music_path):
        return voice, None
    if len(voice) == 0:
        return voice, None

    sr = SAMPLE_RATE
    dur = len(voice)

    # 1. Load nhạc
    try:
        if music_path.lower().endswith(".mp3"):
            # Decode MP3 → WAV qua ffmpeg (tránh phụ thuộc thư viện decode MP3)
            import tempfile
            ffmpeg = None
            for cand in [shutil.which("ffmpeg"),
                         os.path.join(PROJECT_ROOT, "tools", "ffmpeg", "ffmpeg.exe"),
                         os.path.join(PROJECT_ROOT, "tools", "ffmpeg", "bin", "ffmpeg.exe")]:
                if cand and os.path.exists(cand):
                    ffmpeg = cand
                    break
            if not ffmpeg:
                print("   ⚠️  Không tìm thấy ffmpeg để đọc MP3 nhạc nền — bỏ qua nhạc.")
                return voice, None
            tmp_wav = os.path.join(tempfile.gettempdir(), f"bgm_{os.getpid()}.wav")
            proc = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", music_path,
                 "-ar", str(sr), "-ac", "1", tmp_wav],
                capture_output=True, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if proc.returncode != 0 or not os.path.exists(tmp_wav):
                print("   ⚠️  ffmpeg không decode được nhạc nền — bỏ qua nhạc.")
                return voice, None
            music, msr = sf.read(tmp_wav, dtype="float32")
            try:
                os.remove(tmp_wav)
            except OSError:
                pass
        else:
            music, msr = sf.read(music_path, dtype="float32")
        if music.ndim > 1:
            music = music.mean(axis=1)
        if len(music) == 0:
            return voice, None
        music = _resample(music, msr)
    except Exception as e:
        print(f"   ⚠️  Lỗi load nhạc nền ({e}) — bỏ qua nhạc.")
        return voice, None

    # 2. Loudness normalization: đo RMS cả bài rồi scale về mức chuẩn.
    #    Các file nhạc master to/nhỏ khác nhau → đưa về cùng độ to để volume
    #    10%/20% nghe đồng đều giữa các chương (bài nào cũng như bài nào).
    cur_rms = float(np.sqrt(np.mean(music.astype(np.float64) ** 2) + 1e-12))
    if cur_rms > 1e-6:
        gain = MUSIC_TARGET_RMS / cur_rms
        # Giới hạn gain để không khuếch đại bài quá nhỏ thành méo/vỡ
        gain = min(gain, 4.0)
        music = (music * gain).astype(np.float32)

    # 3. Loop nhạc cho đủ dài chapter (crossfade mềm tại nối)
    music_loop = _loop_with_crossfade(music, dur)

    # 4. Envelope ducking: RMS khung 40ms của giọng → volume nhạc
    win = int(0.04 * sr)
    hop = int(0.02 * sr)
    n_frames = max(1, (dur - win) // hop + 1)
    idx = np.arange(n_frames)[:, None] * hop + np.arange(win)
    idx = np.minimum(idx, dur - 1)
    frames = voice[idx].astype(np.float64)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    thr = np.percentile(rms, 15)
    peak = np.percentile(rms, 99)
    v = np.clip((rms - thr) / (peak - thr + 1e-9), 0, 1)

    # duck: 1 khi giọng nghỉ, 0 khi giọng đọc
    duck = 1.0 - v
    # làm phẳng: nhạc dao động nhẹ nhàng (không tắt hẳn)
    duck_smooth = 0.25 * duck + 0.75
    # Biên độ NHẠC NỀN thực tế = volume * tỷ lệ (volume là mức trung bình, tỷ lệ là dao động)
    amp_ratio = min_ratio + (max_ratio - min_ratio) * duck_smooth * duck
    amp = volume * amp_ratio

    # 4. Giới hạn thời gian nhạc "thở" lên: sau khi nghỉ quá lâu thì tự dịu lại
    #    (tránh nhạc nổi liên tục ở chương ít lời)
    rise_cap = int(MUSIC_RISE_CAP_S / (hop / sr))
    rise = np.where(duck > 0.5, 1.0, 0.0).astype(np.float32)
    # Chỉ cho phép "nổi" tối đa rise_cap frame liên tiếp
    counter = np.zeros_like(rise)
    cnt = 0
    for i in range(len(rise)):
        if rise[i] == 1.0:
            cnt += 1
            if cnt > rise_cap:
                rise[i] = 0.0
        else:
            cnt = 0
    # Nhạc chỉ nổi ở đoạn đầu của khoảng nghỉ
    amp_rise = np.where(rise > 0.5, 1.0, 0.0)
    amp = volume * (min_ratio + (max_ratio - min_ratio) * duck_smooth * amp_rise)

    # 5. Up-sample envelope về sample rate + làm mượt (fftconvolve nhanh)
    amp_up = np.interp(np.arange(dur), np.arange(len(amp)) * hop, amp).astype(np.float32)
    k = max(1, int(sr * MUSIC_ENV_MS / 1000))
    kernel = np.ones(k, dtype=np.float32) / k
    if fftconvolve is not None:
        amp_smooth = fftconvolve(amp_up, kernel, mode="same").astype(np.float32)
    else:
        amp_smooth = np.convolve(amp_up, kernel, mode="same").astype(np.float32)

    # 6. Trộn: nhạc * envelope + giọng, chống clip, giữ độ to giọng
    music_bed = music_loop * amp_smooth
    mixed = voice + music_bed
    voice_peak = np.max(np.abs(voice)) + 1e-9
    mix_peak = np.max(np.abs(mixed)) + 1e-9
    if mix_peak > voice_peak:
        mixed = mixed / mix_peak * voice_peak * 0.97

    return mixed, os.path.basename(music_path)


def find_book_dir(slug: str = None) -> str | None:
    """Tìm thư mục sách trong output/books/ theo slug.

    Thư mục output/books/ được đặt tên theo tên sách gốc (tên file input),
    mỗi thư mục có metadata.json ghi {'slug': 'tên-slug-cũ', ...}.
    - Nếu slug truyền vào: tìm thư mục có metadata.slug == slug.
    - Nếu không truyền: trả về thư mục duy nhất có final/vi.md (nếu có đúng 1).
    Trả về đường dẫn thư mục hoặc None.
    """
    books_dir = os.path.join(PROJECT_ROOT, "output", "books")
    if not os.path.isdir(books_dir):
        return None
    found = []
    for d in sorted(os.listdir(books_dir)):
        dpath = os.path.join(books_dir, d)
        if not os.path.isdir(dpath):
            continue
        # Đọc metadata.json nếu có
        meta_slug = None
        meta_path = os.path.join(dpath, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_slug = json.load(f).get("slug")
            except Exception:
                meta_slug = None
        if slug:
            if meta_slug == slug or d == slug:
                return dpath
        else:
            # Không truyền slug: xét thư mục có final/vi.md
            if os.path.exists(os.path.join(dpath, "final", "vi.md")):
                found.append(dpath)
    if slug is None and len(found) == 1:
        return found[0]
    return None


def find_vi_md(slug: str = None) -> tuple:
    """Tìm file -vi.md. Trả về (path, slug).

    Tìm theo thứ tự:
    1. output/books/<thư mục theo tên gốc>/final/vi.md (cấu trúc mới, map qua metadata.json)
    2. output/<slug>/<slug>-vi.md (cấu trúc cũ, backward compat)
    """
    books_dir = os.path.join(PROJECT_ROOT, "output", "books")
    output_dir = os.path.join(PROJECT_ROOT, "output")

    if slug:
        # Cấu trúc mới: map slug -> thư mục (tên gốc)
        book_dir = find_book_dir(slug)
        if book_dir:
            new_path = os.path.join(book_dir, "final", "vi.md")
            if os.path.exists(new_path):
                return new_path, slug
        # Fallback: tên thư mục = slug
        new_path = os.path.join(books_dir, slug, "final", "vi.md")
        if os.path.exists(new_path):
            return new_path, slug
        # Fallback cấu trúc cũ
        old_path = os.path.join(output_dir, slug, f"{slug}-vi.md")
        if os.path.exists(old_path):
            return old_path, slug
        raise FileNotFoundError(f"File not found: {new_path}")

    # Auto-detect: tìm -vi.md trong books/ và output/
    candidates = []
    # Cấu trúc mới: output/books/<tên gốc>/final/vi.md
    if os.path.isdir(books_dir):
        for d in sorted(os.listdir(books_dir)):
            vi_path = os.path.join(books_dir, d, "final", "vi.md")
            if os.path.exists(vi_path):
                candidates.append((vi_path, d))
    # Cấu trúc cũ: output/<slug>/<slug>-vi.md
    for d in sorted(os.listdir(output_dir)):
        vi_path = os.path.join(output_dir, d, f"{d}-vi.md")
        if os.path.exists(vi_path) and (vi_path, d) not in candidates:
            candidates.append((vi_path, d))

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        book_list = ", ".join(f"'{slug}'" for _, slug in candidates)
        raise FileNotFoundError(
            f"Có {len(candidates)} sách ({book_list}). "
            "Hãy chỉ định --slug để tránh chọn nhầm."
        )

    raise FileNotFoundError(f"No *-vi.md found in output/")


def detect_chapters(md_path: str) -> list:
    """Phát hiện tất cả chapters trong file -vi.md.
    Trả về list of (chapter_num, title, line_start, line_end).
    """
    chapters = []
    chapter_re = re.compile(
        r"^#\s*(?:"
        r"[（(](\d+)[）)]"                          # （01）Title hoặc (01) Title
        r"|(\d+)[.:：]\s+"                           # 01: Title hoặc 01. Title
        r"|Chapter\s+(\d+)[.:：]?\s*"                # Chapter 1: Title
        r"|Ch(?:ương|ƯƠNG)\s+(\d+)[.:：]?\s*"       # Chương 1: Title / CHƯƠNG 1 Title
        r"|Quy(?:ển|YỂN)\s+(\d+)[.:：]?\s*"         # Quyển 1: Title
        r"|Ph(?:ần|ẦN)\s+(\d+)[.:：]?\s*"            # Phần 1: Title
        r"|(\d+)\s+"                                  # 01 Title (bare number)
        r")"
    )
    all_lines = []

    with open(md_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            all_lines.append(line.rstrip())

    for i, line in enumerate(all_lines):
        m = chapter_re.match(line)
        if m:
            # Find which group matched
            num = next((g for g in m.groups() if g is not None), None)
            if num:
                num = int(num)
                # Extract title (everything after the matched pattern)
                title = line[m.end():].strip()
                chapters.append({
                    "num": num,
                    "title": title,
                    "line_start": i,
                })

    # Fallback: nếu không có chương đánh số (sách essay không số hiệu) →
    # dùng heading # / ## làm ranh giới chương (bỏ mục con đánh số + TOC).
    if not chapters:
        for i, line in enumerate(all_lines):
            m = re.match(r"^#{1,2}\s+(.*)$", line)
            if not m:
                continue
            title = m.group(1).strip()
            if re.match(r"^[0-9()（）]", title):
                continue
            if "CONTENTS" in title.upper() or "Mục Lục" in title or "目录" in title:
                continue
            # Bỏ qua EPUB item markers: ## [1] titlepage.xhtml, ## [2] text/...
            if re.match(r"^\[\d+\]\s+", title):
                continue
            chapters.append({
                "num": len(chapters) + 1,
                "title": title,
                "line_start": i,
            })

    # Set line_end for each chapter
    for idx in range(len(chapters) - 1):
        chapters[idx]["line_end"] = chapters[idx + 1]["line_start"]
    if chapters:
        chapters[-1]["line_end"] = len(all_lines)

    return chapters, all_lines


def cleanup_markdown(text: str) -> str:
    """Làm sạch markdown: bỏ bảng, link, chú thích, emphasis, bullet, blockquote."""
    import html
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)     # ảnh (trước link!)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)          # **bold**
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"\1", text)  # *italic*
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [text](url) → text
    text = re.sub(r"\[\^?\d+\]", "", text)                # footnote [1], [^1]
    text = re.sub(r"`([^`]*)`", r"\1", text)              # inline code → text
    text = re.sub(r"^>\s?", "", text)                     # blockquote >
    text = re.sub(r"\\\s*$", "", text)                    # soft line break \
    text = re.sub(r"^\s*[-*+]\s+", "", text)              # bullet list
    text = re.sub(r"^\s*\d+[.)]\s+", "", text)            # numbered list
    text = re.sub(r"^\s*\|.*\|\s*$", "", text)            # dòng bảng
    text = re.sub(r"[|]", "", text)                       # pipe rác còn sót
    # Full-width punctuation → ASCII (tránh TTS đọc ký tự Trung/Nhật)
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("【", "[").replace("】", "]")
    text = text.replace("《", "").replace("》", "")
    text = text.replace("：", ": ").replace("；", "; ")
    text = text.replace("，", ", ").replace("。", ". ")
    text = text.replace("！", "! ").replace("？", "? ")
    text = text.replace("、", ", ")
    # Normalize: ba dấu chấm → dấu ba chấm Unicode (…)
    text = re.sub(r"\.{3,}", "…", text)
    # Normalize: nhiều dấu chấm liên tiếp → dấu ba chấm
    text = re.sub(r"…{2,}", "…", text)
    text = html.unescape(text)                            # HTML entities (&nbsp; &mdash; …)
    return text.strip()


# Cache VietNormalizer instance
_viet_normalizer = None

# Cache sea_g2p.Normalizer (đã có sẵn trong venv vieneu) để normalize số/ngày/
# tiền/viết tắt TRƯỚC khi tách câu & chunk — tránh cắt nhầm "3.5"/"1.200.000".
_sea_g2p_normalizer = None


def normalize_by_sea_g2p(text: str) -> str:
    """Chuẩn hóa số/ngày/tiền/viết tắt bằng sea_g2p (giống tầng normalize của vieneu).

    Chỉ chạy khi có sẵn sea_g2p (venv vieneu); nếu không thì trả nguyên text.
    Không ép punc_norm để giữ dấu câu gốc (tránh biến "3." thành hết câu giả).
    """
    global _sea_g2p_normalizer
    try:
        if _sea_g2p_normalizer is None:
            from sea_g2p import Normalizer
            _sea_g2p_normalizer = Normalizer()
        return _sea_g2p_normalizer.normalize(text, punc_norm=False)
    except Exception as e:
        # sea_g2p không có / lỗi → bỏ qua (vieneu vẫn tự normalize khi phonemize)
        if _sea_g2p_normalizer is None:
            print(f"   ⚠️  sea_g2p chưa có — bỏ qua normalize số trước chunk: {e}")
        return text

# ── Từ điển phát âm ngoại lệ (từ mượn/tiếng Anh đọc theo cách Việt hoá) ──
# Thứ tự: từ DÀI trước (tránh khớp nhầm tiền tố của từ ghép), tất cả lowercase.
DEFAULT_PRONOUNCE = {
    "ok": "ô kê",
    "oke": "ô kê",
    "okay": "ô kê",
    "AI": "ê a i",  # chỉ viết HOA (viết tắt AI), không đụng "ai" (đại từ tiếng Việt)
    "wifi": "uy phai",
    "wi-fi": "uy phai",
    "tv": "tê vi",
    "tivi": "ti vi",
    "sms": "ét em mờ ét",
    "email": "i meo",
    "e-mail": "i meo",
    "website": "uép sao",
    "web": "uép",
    "app": "ép",
    "apps": "ép",
    "iphone": "ai phôn",
    "android": "an đroi",
    "windows": "uin đâu",
    "software": "phần mềm",
    "hardware": "phần cứng",
    "bim": "bim",
    "data": "đa ta",
    "file": "phai",
    "files": "phai",
    "server": "xơ vơ",
    "cloud": "clao",
    "online": "on lai",
    "offline": "óp phai",
    "internet": "in tơ nét",
    "google": "gồ gồ",
    "youtube": "iu túp",
    "facebook": "phây búc",
    "chat": "chát",
    "video": "vi đê ô",
    "audio": "au đi ô",
    "photo": "phô tô",
    "robot": "rô bốt",
    "computer": "côm piu tơ",
    "laptop": "láp tốp",
    "phone": "phôn",
    "tablet": "táp lét",
    "camera": "ca mê ra",
    "gps": "gi pi ét",
    "bluetooth": "bơ lu tút",
    "html": "hát tê em mờ en",
    "css": "xê ét ét",
    "pdf": "pi đi ép",
    "docx": "đóc x",
    "xlsx": "éc xen x",
    "api": "ê pi ai",
    "url": "iu a en",
    "www": "u u u",
    "https": "hát tê tê ép x",
    "http": "hát tê tê pi",
    "vpn": "vi pi en",
}

_pronounce_map = dict(DEFAULT_PRONOUNCE)  # copy mặc định; có thể bị ghi đè bằng --pronounce-json
_pronounce_sorted = sorted(DEFAULT_PRONOUNCE.keys(), key=len, reverse=True)


def _apply_pronounce(text: str) -> str:
    """Thay từ mượn/ngoại lệ trong text bằng cách đọc Việt hoá.

    - Key viết HOA (vd "AI") → chỉ khớp khi viết HOA (tránh đụng "ai" thường).
    - Key viết thường → khớp không phân biệt hoa/thường.
    """
    if not _pronounce_sorted:
        return text
    for word in _pronounce_sorted:
        if word != word.lower():
            # Key có ký tự HOA → match chính xác (case-sensitive)
            pattern = r"(?<![\w])" + re.escape(word) + r"(?![\w])"
            text = re.sub(pattern, _pronounce_map[word], text)
        else:
            pattern = r"(?<![\w])" + re.escape(word) + r"(?![\w])"
            text = re.sub(pattern, _pronounce_map[word], text, flags=re.IGNORECASE)
    return text


def load_pronounce_dict(path: str) -> None:
    """Nạp từ điển phát âm ngoại lệ từ JSON (ghi đè/merge lên mặc định)."""
    global _pronounce_sorted, _pronounce_map
    if not path or not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        print(f"   ⚠️  --pronounce-json phải là object {{'từ': 'cách đọc'}}")
        return
    _pronounce_map.update({str(k).lower(): str(v) for k, v in data.items()})
    _pronounce_sorted = sorted(_pronounce_map.keys(), key=len, reverse=True)
    print(f"   📖 Đã nạp từ điển phát âm: {len(data)} từ bổ sung (tổng {len(_pronounce_map)})")


def normalize_vietnamese_text(text: str) -> str:
    """Chuẩn hóa văn bản tiếng Việt cho TTS sử dụng VietNormalizer.

    Chuyển đổi số thành chữ, chuẩn hóa ngày tháng, tiền tệ,
    từ viết tắt, từ mượn.
    """
    global _viet_normalizer
    # 1. Từ điển phát âm ngoại lệ (từ mượn) — chạy trước normalizer
    text = _apply_pronounce(text)
    try:
        if _viet_normalizer is None:
            from vietnormalizer import VietnameseNormalizer
            _viet_normalizer = VietnameseNormalizer()
        return _viet_normalizer.normalize(text)
    except ImportError:
        # VietNormalizer chưa được cài đặt, bỏ qua chuẩn hóa
        return text
    except Exception as e:
        # Lỗi khi chuẩn hóa, trả về text gốc
        print(f"   ⚠️  VietNormalizer error: {e}")
        return text


def extract_chapter_text(lines: list, start: int, end: int, include_title: bool = True) -> list:
    """Trích xuất text Việt thành các đoạn văn (paragraphs).

    Trả về list of (paragraph_text, ends_paragraph).
    ends_paragraph=True nếu paragraph kế tiếp là heading hoặc end of chapter.
    """
    paragraphs = []
    current = []
    for line in lines[start:end]:
        stripped = line.strip()
        # Skip separator, html, image
        if stripped == "---":
            continue
        if re.match(r"^</?[a-zA-Z]", stripped):
            continue
        if not stripped:
            # Dòng trống → kết thúc 1 paragraph
            if current:
                paragraphs.append((" ".join(current), False))
                current = []
            continue
        if stripped.startswith("#"):
            # Heading: kết thúc paragraph hiện tại, đánh dấu section end
            if current:
                paragraphs.append((" ".join(current), True))
                current = []
            heading = re.sub(r"^#+\s*", "", stripped)
            # Chuyển full-width parentheses → ASCII trước khi kiểm tra
            heading = heading.replace("（", "(").replace("）", ")")
            heading = re.sub(r"^\(\d+\)\s*", "", heading)  # bỏ (01) prefix
            # Bỏ qua EPUB item markers: ## [1] titlepage.xhtml, ## [2] text/...
            if re.match(r"^\[\d+\]\s+", heading):
                continue
            if include_title and heading and len(heading) > 2:
                # Thêm "Chương" trước số thứ tự: "1. Title" → "Chương 1: Title"
                m_num = re.match(r"^(\d+)\s*[.:：]\s*(.+)$", heading)
                if m_num:
                    heading = f"Chương {m_num.group(1)}: {m_num.group(2)}"
                paragraphs.append((heading, False))
            continue
        # Cleanup markdown
        text = cleanup_markdown(stripped)
        if not text or len(text) <= 2:
            continue
        # Bỏ qua dòng chỉ có dấu câu hoặc ký tự vô nghĩa cho TTS
        if re.match(r'^[\s"\'""\'\'!,.?…—–\-*~()（）\-–—\[\]【】{}]+$', text):
            continue
        # Normalize số/ngày/tiền/viết tắt TRƯỚC khi tách câu/chunk
        # (tránh cắt nhầm "3.5", "1.200.000", "v.v." thành hết câu giả)
        text = normalize_by_sea_g2p(text)
        # Chuẩn hóa văn bản tiếng Việt cho TTS (từ mượn + vietnormalizer nếu có)
        text = normalize_vietnamese_text(text)
        current.append(text)
    # Paragraph cuối cùng → section end
    if current:
        paragraphs.append((" ".join(current), True))

    # Gộp paragraph ngắn (< 50 ký tự, thường là câu hội thoại đứng riêng) vào
    # paragraph liền TRƯỚC để model TTS có đủ ngữ cảnh — chunk 1 câu ngắn đứng
    # riêng khiến model hallucinate (bịa thêm nội dung dài / đọc lặp câu).
    # Không gộp vào heading (heading không phải câu đọc).
    merged_paras = []
    for p_text, p_end in paragraphs:
        if merged_paras and len(p_text) < 50 and len(merged_paras[-1][0]) > 2 \
                and not merged_paras[-1][0].startswith("Chương"):
            prev_text, prev_end = merged_paras[-1]
            merged_paras[-1] = (prev_text + " " + p_text, p_end or prev_end)
        else:
            merged_paras.append((p_text, p_end))
    paragraphs = merged_paras

    return paragraphs


_ABBREVIATIONS = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "ave", "blvd",
    "inc", "ltd", "corp", "dept", "est", "approx", "vs", "etc",
    "e.g", "i.e", "a.m", "p.m", "u.s", "u.s.a", "u.k",
    "vd", "ks", "ts", "pgs", "pgs", "ths", "cv", "bs", "ds",
})

# CJK sentence-ending punctuation (。！？；) — treated same as Latin .!?
_CJK_SENTENCE_ENDERS = "\u3002\uff01\uff1f\uff1b"  # 。！？；


def _split_sentences(text: str) -> list:
    """Tách text thành danh sách câu hoàn chỉnh.

    Tách tại: . ! ? … ; 。！？； theo sau bởi space hoặc cuối chuỗi.
    KHÔNG tách khi dấu chấm thuộc viết tắt (multi-language: Mr., Dr., ks., ts.,
    vs., etc., vd., Pgs., Ths., Cv., Bs., Ds.) hoặc viết tắt 1 chữ hoa + dấu
    chấm (TP., HCM.) trước chữ.
    Xử lý quote đóng: ". "? "! "? → giữ nguyên trong cùng câu.
    Xử lý CJK full-width: 。！？ → treated same as .!?
    """
    text = text.strip()
    if not text:
        return []

    protected = text
    # Viết tắt multi-language — giữ nguyên dấu chấm
    protected = re.sub(
        r"\b(mr|mrs|ms|dr|prof|sr|jr|st|vs|etc|vd|e\.g|i\.e|no|"
        r"ks|ts|ths|cv|bs|ds|vân vân|pgs)\.(?=\s+\S)",
        r"\1<PROTECT>", protected, flags=re.IGNORECASE)
    # "thành phố." từ "TP." trước tên địa danh chữ thường
    protected = re.sub(r"\bthành phố\.(?=\s+[a-zà-ỹ])", "thành phố<PROTECT>", protected)
    # Viết tắt 1 chữ hoa + dấu chấm trước chữ hoa
    protected = re.sub(r"\b([A-ZÀ-Ỹ])\.(?=\s+[A-ZÀ-Ỹ])", r"\1<PROTECT>", protected)

    # Tách tại: Latin sentence-enders + CJK sentence-enders + … + ;
    # Latin: require space/whitespace after (vd ". " nhưng không tách "3.14")
    # CJK: tách ngay sau dấu câu (không cần space — CJK không dùng space giữa câu)
    _LATIN_ENDERS = ".!?\u2026"
    _CJK_ENDERS = _CJK_SENTENCE_ENDERS  # 。！？；
    parts = []
    # Split Latin enders (need space after)
    latin_pat = r'(?<=[' + re.escape(_LATIN_ENDERS) + r'])\s+'
    parts = re.split(latin_pat, protected)
    # Further split each part by CJK enders (no space needed)
    final = []
    for part in parts:
        cjk_pat = r'(?<=[' + re.escape(_CJK_ENDERS) + r'])'
        cjk_parts = re.split(cjk_pat, part)
        final.extend(cjk_parts)
    parts = [p.replace("<PROTECT>", ".") for p in final]
    return [p.strip() for p in parts if p.strip()]


def _ensure_sentence_ending(text: str) -> str:
    """Đảm bảo text kết thúc bằng dấu câu để TTS ngắt nghỉ đúng cách.

    Nếu text không kết thúc bằng dấu câu, thêm dấu phẩy hoặc dấu chấm.
    """
    text = text.strip()
    if not text:
        return text
    # Nếu đã kết thúc bằng dấu câu, giữ nguyên
    if text[-1] in ".!?…;:":
        return text
    # Nếu kết thúc bằng dấu phẩy, giữ nguyên
    if text[-1] == ",":
        return text
    # Nếu kết thúc bằng dấu ngoặc đóng, giữ nguyên
    if text[-1] in ")]}":
        return text
    # Nếu kết thúc bằng dấu ngoặc mở, thêm dấu chấm
    if text[-1] in "([{":
        return text + "."
    # Nếu kết thúc bằng dấu gạch ngang, giữ nguyên
    if text[-1] in "—–":
        return text
    # Mặc định: thêm dấu phẩy để TTS ngắt nghỉ
    return text + ","


def smart_chunk(paragraphs: list, max_chars: int = MAX_CHARS) -> list:
    """Chunk paragraphs thành các đoạn <= max_chars, ưu tiên giữ nguyên câu.

    paragraphs: list of (text, ends_paragraph) từ extract_chapter_text.
    Chiến lược: tách paragraph thành câu → gộp câu liền kề vào chunk
    cho đến khi vượt max_chars → bắt chunk mới.

    Trả về list of (text, ends_paragraph).
    """
    chunks = []

    for para_idx, (para_text, para_section_end) in enumerate(paragraphs):
        para = re.sub(r"\s+", " ", para_text).strip()
        if not para:
            continue

        sentences = _split_sentences(para)
        if not sentences:
            sentences = [para]

        current = ""
        prev_sent_first = None  # 2 từ đầu của câu TRƯỚC trong cùng paragraph (phát hiện song song)

        for sent_idx, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue

            is_last_sent = (sent_idx == len(sentences) - 1)

            # Phát hiện câu SONG SONG (lặp cụm đầu câu, vd "một số đứa ở lại..." /
            # "một số đứa chuyển..."): model TTS dễ kẹt lặp nếu 2 câu cạnh nhau
            # trong cùng chunk → ép tách chunk trước khi gộp câu này.
            sent_first = tuple(sent.split()[:2])
            is_parallel = (
                prev_sent_first is not None
                and len(prev_sent_first) == 2 and len(sent_first) == 2
                and prev_sent_first[0] == sent_first[0]
                and prev_sent_first[1] == sent_first[1]
            )
            if is_parallel and current:
                chunks.append((_ensure_sentence_ending(current.strip()), False))
                current = ""
            prev_sent_first = sent_first

            # Nếu thêm câu này vào chunk hiện tại mà vẫn <= max_chars → gộp
            candidate = (current + " " + sent).strip() if current else sent
            if len(candidate) <= max_chars:
                current = candidate
                continue

            # Chunk hiện tại đã có nội dung → lưu lại, bắt chunk mới
            if current:
                # Đảm bảo chunk kết thúc bằng dấu câu
                chunks.append((_ensure_sentence_ending(current.strip()), False))
                current = ""

            # Câu mới quá dài → phải split
            if len(sent) > max_chars:
                remaining = sent
                while len(remaining) > max_chars:
                    split_pos = -1
                    # Ưu tiên tách tại dấu câu kết thúc câu (. ! ? … 。！？)
                    for sep in [". ", "! ", "? ", "… ", "\u3002 ", "\uff01 ", "\uff1f ", "…"]:
                        pos = remaining.rfind(sep, 0, max_chars)
                        if pos > split_pos:
                            split_pos = pos + len(sep)
                    # Nếu không tìm thấy dấu câu kết thúc, tách tại dấu chấm phẩy
                    if split_pos <= 0:
                        for sep in ["; ", ";"]:
                            pos = remaining.rfind(sep, 0, max_chars)
                            if pos > split_pos:
                                split_pos = pos + len(sep)
                    # Nếu không tìm thấy dấu chấm phẩy, tách tại dấu hai chấm
                    if split_pos <= 0:
                        for sep in [": ", ":"]:
                            pos = remaining.rfind(sep, 0, max_chars)
                            if pos > split_pos:
                                split_pos = pos + len(sep)
                    # Nếu không tìm thấy dấu hai chấm, tách tại dấu phẩy
                    if split_pos <= 0:
                        for sep in [", ", ","]:
                            pos = remaining.rfind(sep, 0, max_chars)
                            if pos > split_pos:
                                split_pos = pos + len(sep)
                    # Nếu không tìm thấy dấu phẩy, tách tại dấu gạch ngang
                    if split_pos <= 0:
                        for sep in [" — ", " – ", "—", "–"]:
                            pos = remaining.rfind(sep, 0, max_chars)
                            if pos > split_pos:
                                split_pos = pos + len(sep)
                    # Nếu không tìm thấy dấu gạch ngang, tách tại dấu cách
                    if split_pos <= 0:
                        space_pos = remaining.rfind(" ", 0, max_chars)
                        if space_pos > max_chars // 3:
                            split_pos = space_pos
                        else:
                            split_pos = max_chars
                    # Đảm bảo chunk kết thúc bằng dấu câu
                    chunks.append((_ensure_sentence_ending(remaining[:split_pos].strip()), False))
                    remaining = remaining[split_pos:].strip()
                current = remaining
            else:
                current = sent

        # Lưu chunk cuối cùng của paragraph → đánh dấu section end nếu paragraph là section end
        if current.strip():
            # Đảm bảo chunk kết thúc bằng dấu câu
            chunks.append((_ensure_sentence_ending(current.strip()), para_section_end))

    # Gộp các chunk NHỎ liền kề (nhất là câu hội thoại ngắn đứng riêng) để model
    # có đủ ngữ cảnh, tránh sinh lặp/hallucinate khi chunk quá ngắn. Duyệt từ đầu:
    # nếu chunk i + chunk i+1 <= max_chars → gộp (giữ flag para_end của chunk sau).
    # NGOẠI LỆ 1: không gộp nếu câu ĐẦU của chunk sau lặp cụm từ đầu của câu CUỐI
    # chunk trước (vd "một số đứa ở lại..." / "một số đứa chuyển...") — 2 câu song
    # song cạnh nhau khiến model TTS dễ kẹt lặp; tách riêng sẽ hết.
    # NGOẠI LỆ 2 (ưu tiên hơn): chunk cực ngắn (< 50 ký tự) LUÔN được gộp dù có
    # song song — vì chunk 1 câu ngắn đứng riêng khiến model hallucinate (bịa thêm
    # nội dung dài) nghiêm trọng hơn nhiều so với nguy cơ lặp do 2 câu song song.
    def _first_words(s, n=3):
        return tuple(s.split()[:n])

    def _is_parallel(prev, cur):
        prev_last = prev.rstrip().rsplit(".", 1)[-1] if "." in prev else prev
        prev_sents = [s for s in prev.split(". ") if s]
        cur_sents = [s for s in cur.split(". ") if s]
        if not prev_sents or not cur_sents:
            return False
        p = _first_words(prev_sents[-1])
        c = _first_words(cur_sents[0])
        return len(p) >= 2 and len(c) >= 2 and p[0] == c[0] and (p[1] == c[1] or p[1] in c)

    def _should_merge(prev, cur):
        """Quyết định có gộp chunk cur vào prev không."""
        total = len(prev) + len(cur) + 1
        # Chunk cực ngắn → gộp kể cả khi hơi vượt max_chars (tối đa TTS_MAX_CHARS,
        # giới hạn an toàn của model) — 1 câu ngắn đứng riêng nguy hiểm hơn nhiều
        # so với chunk hơi dài.
        if len(cur) < 50 or len(prev) < 50:
            return total <= TTS_MAX_CHARS
        if total > max_chars:
            return False
        return not _is_parallel(prev, cur)

    merged = []
    for text, para_end in chunks:
        if merged and _should_merge(merged[-1][0], text):
            prev_text, prev_para = merged[-1]
            merged[-1] = (prev_text + " " + text, para_end or prev_para)
        else:
            merged.append((text, para_end))

    # Lượt 2: chunk ngắn còn sót (chưa gộp được vào trước vì chunk trước đầy) →
    # gộp vào chunk SAU nếu còn chỗ. Duyệt ngược để gộp an toàn.
    merged2 = []
    i = 0
    while i < len(merged):
        text, para_end = merged[i]
        if (len(text) < 50 and i + 1 < len(merged)
                and _should_merge(text, merged[i + 1][0])):
            # Gộp text vào đầu chunk sau
            next_text, next_end = merged[i + 1]
            merged2.append((text + " " + next_text, para_end or next_end))
            i += 2
        else:
            merged2.append((text, para_end))
            i += 1
    chunks = merged2

    # Lượt 3: gộp chunk "unspeakable" (chỉ chứa dấu câu/ký tự không đọc được)
    # vào chunk liền kề — tránh TTS đọc nhảm hoặc trả về rỗng (#1330 pattern).
    _SPEAKABLE_RE = re.compile(r"[^\W_]", re.UNICODE)
    final = []
    for text, para_end in chunks:
        if not _SPEAKABLE_RE.search(text) and final:
            # Chunk toàn dấu câu — gộp vào chunk trước
            prev_text, prev_para = final[-1]
            merged_text = (prev_text + " " + text).strip()
            if len(merged_text) <= TTS_MAX_CHARS:
                final[-1] = (merged_text, para_end or prev_para)
            else:
                final.append((text, para_end))
        elif not _SPEAKABLE_RE.search(text) and not final:
            # Chunk đầu tiên toàn dấu câu — gộp vào chunk sau nếu có
            continue
        else:
            final.append((text, para_end))
    # Nếu chunk đầu là unspeakable và đã bị skip, đảm bảo có ít nhất 1 chunk
    if not final and chunks:
        final = [chunks[0]]

    return final


def find_nice_passage(paragraphs, min_chars=200, max_chars=800):
    """Tìm đoạn văn hay, liền mạch trong text Việt.

    paragraphs: list of (text, ends_paragraph) từ extract_chapter_text.
    Ưu tiên paragraph vừa đủ (min-max). Nếu không có, cắt paragraph dài
    tại biên câu gần max_chars.
    """
    # 1. Tìm paragraph có độ dài vừa phải
    for p_text, _ in paragraphs:
        p = re.sub(r"\s+", " ", p_text).strip()
        if min_chars <= len(p) <= max_chars:
            return p

    # 2. Không có đoạn vừa → cắt paragraph dài đầu tiên >= min_chars
    for p_text, _ in paragraphs:
        p = re.sub(r"\s+", " ", p_text).strip()
        if len(p) >= min_chars:
            separators = ["... ", "! ", "? ", ". ", "; "]
            cut_pos = -1
            for sep in separators:
                pos = p.rfind(sep, 0, max_chars)
                if pos > cut_pos:
                    cut_pos = pos + len(sep)
            if cut_pos > min_chars // 2:
                return p[:cut_pos].strip()
            return p[:max_chars].strip()

    # 3. Nối các paragraph ngắn
    passage = ""
    for p_text, _ in paragraphs:
        p = re.sub(r"\s+", " ", p_text).strip()
        if not p:
            continue
        if len(passage) + len(p) + 1 > max_chars:
            break
        passage += " " + p if passage else p

    return passage.strip()[:max_chars]


def make_silence(duration, sr=SAMPLE_RATE):
    return np.zeros(int(duration * sr), dtype=np.float32)


def _get_voice_gender(ref_path: str) -> str:
    """Đọc gender từ metadata JSON của voice. Mặc định 'female' nếu không tìm thấy."""
    json_path = ref_path.rsplit(".", 1)[0] + ".json"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("gender", "female")
    return "female"


def generate_chunk_audio(tts, voice_name, chunk, chunk_idx, total_chunks,
                         temperature=0.7, top_k=20, repetition_penalty=1.5,
                         top_p=0.95):
    """Generate audio cho 1 chunk với retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            t0 = time.time()
            audio = tts.infer(
                chunk,
                voice=voice_name,
                style="doc_truyen",
                max_chars=TTS_MAX_CHARS,
                temperature=temperature,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                top_p=top_p,
                apply_watermark=False,
            )
            elapsed = time.time() - t0
            audio = audio.squeeze()
            dur = len(audio) / SAMPLE_RATE

            pct = (chunk_idx + 1) / total_chunks * 100
            print(f"      [{chunk_idx+1:3d}/{total_chunks}] {pct:5.1f}% | {dur:.1f}s | {elapsed:.1f}s | \"{chunk[:40]}...\"")
            return audio, elapsed

        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"      [{chunk_idx+1}] Lần {attempt} thất bại: {e}. Thử lại...")
                time.sleep(2 * attempt)
            else:
                print(f"      [{chunk_idx+1}] ❌ Thất bại sau {MAX_RETRIES} lần: {e}")
                raise


def _audio_cache_signature(chunk: str, voice_name: str, temperature: float, top_k: int,
                           repetition_penalty: float = 1.5, top_p: float = 0.95) -> str:
    payload = json.dumps({
        "chunk": chunk,
        "voice": voice_name,
        "temperature": temperature,
        "top_k": top_k,
        "repetition_penalty": repetition_penalty,
        "top_p": top_p,
        "max_chars": TTS_MAX_CHARS,
        "sample_rate": SAMPLE_RATE,
    }, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_cached_audio(path: str, signature_path: str, signature: str):
    if not os.path.exists(path) or not os.path.exists(signature_path):
        return None
    try:
        if open(signature_path, "r", encoding="utf-8").read().strip() != signature:
            return None
        info = sf.info(path)
        if info.samplerate != SAMPLE_RATE or info.frames <= 0:
            return None
        audio, _ = sf.read(path, dtype="float32")
        if audio.size == 0 or not np.isfinite(audio).all():
            return None
        return audio
    except Exception:
        return None


def _save_audio_cache(path: str, audio, signature: str) -> None:
    temp_wav = path + ".tmp.wav"
    temp_sig = path + ".tmp.sig"
    sf.write(temp_wav, audio, SAMPLE_RATE)
    os.replace(temp_wav, path)
    with open(temp_sig, "w", encoding="utf-8") as f:
        f.write(signature)
    os.replace(temp_sig, path + ".sig")


def _preprocess_chunk_text(text: str, slug: str = None) -> str:
    """Chuẩn hoá text trước TTS: normalize + pronunciation.

    Thứ tự:
      1. normalize_for_tts — xóa ký tự xấu, decode entities, limit repeats
      2. apply_pronunciation — per-book overrides từ pronunciation.json
         (chạy SAU _apply_pronounce để per-book luôn thắng DEFAULT_PRONOUNCE)
    """
    out = normalize_for_tts(text)
    out = apply_pronunciation(out, slug=slug)
    return out


def _load_book_pronunciation(slug: str) -> None:
    """Load per-book pronunciation overrides vào _pronounce_map.

    Gọi TRƯỚC khi extract_chapter_text xử lý text để _apply_pronounce
    dùng được per-book overrides.
    """
    if not slug:
        return
    from pronunciation import load_pronunciation_json
    pron_path = os.path.join(PROJECT_ROOT, "working", "profile",
                             f"{slug}-pronunciation.json")
    book_dict = load_pronunciation_json(pron_path)
    if book_dict:
        _pronounce_map.update({k.lower(): v for k, v in book_dict.items()})
        global _pronounce_sorted
        _pronounce_sorted = sorted(_pronounce_map.keys(), key=len, reverse=True)
        print(f"   📖 Đã nạp pronunciation per-book: {len(book_dict)} từ")


def generate_chapter_audio(tts, voice_name, chunks, chapter_num, temperature=0.7,
                           top_k=20, chunk_dir=None, force=False,
                           repetition_penalty=1.5, top_p=0.95,
                           use_batch=False, batch_size=8, slug=None):
    """Generate audio cho 1 chapter với cache kiểm tra được tham số.

    - use_batch=True (GPU): gom các chunk chưa cache thành nhóm, gọi infer_batch
      (static batching) — nhanh hơn nhiều lần so với infer từng chunk.
    - use_batch=False (CPU): generate từng chunk như cũ.
    - slug: tên slug sách để load pronunciation overrides.
    """
    # Preprocess: normalize + pronunciation cho mỗi chunk trước khi TTS
    chunks = [(_preprocess_chunk_text(t, slug=slug), ep) for t, ep in chunks]

    raw_audio = [None] * len(chunks)
    total_gen_time = 0

    # 1. Xác định chunk đã có cache (dùng lại) và chunk cần generate
    to_gen = []  # list of (idx, chunk_text)
    for i, (chunk, ends_para) in enumerate(chunks):
        if chunk_dir and not force:
            chunk_wav = os.path.join(chunk_dir, f"{i:04d}.wav")
            signature = _audio_cache_signature(chunk, voice_name, temperature, top_k,
                                               repetition_penalty, top_p)
            audio = _load_cached_audio(chunk_wav, chunk_wav + ".sig", signature)
            if audio is not None:
                print(f"      [{i+1:3d}/{len(chunks)}] ⏭  dùng lại cache")
                raw_audio[i] = audio
                continue
        to_gen.append((i, chunk))

    # 2. Generate phần chưa có — batch theo NHÓM (GPU) hoặc từng chunk (CPU)
    #    Chia to_gen thành các nhóm batch_size, mỗi nhóm infer xong in ngay
    #    (progress nhảy dần 1/60, 2/60... chứ không đợi hết chapter mới in).
    if use_batch and len(to_gen) > 1:
        for g in range(0, len(to_gen), batch_size):
            group = to_gen[g:g + batch_size]
            texts = [c for _, c in group]
            g_idxs = [i for i, _ in group]
            t0 = time.time()
            try:
                wavs = tts.infer_batch(
                    texts, voice=voice_name, style="doc_truyen",
                    temperature=temperature, top_k=top_k,
                    repetition_penalty=repetition_penalty, top_p=top_p,
                    apply_watermark=False, batch_size=len(texts))
            except Exception as e:
                print(f"   ⚠️  infer_batch lỗi ({e}) — fallback về infer từng chunk.")
                wavs = None
            if wavs is None:
                # Fallback: từng chunk trong nhóm
                for idx, chunk in group:
                    audio, elapsed = generate_chunk_audio(
                        tts, voice_name, chunk, idx, len(chunks), temperature, top_k,
                        repetition_penalty, top_p)
                    total_gen_time += elapsed
                    if chunk_dir:
                        _save_audio_cache(
                            os.path.join(chunk_dir, f"{idx:04d}.wav"), audio,
                            _audio_cache_signature(chunk, voice_name, temperature,
                                                   top_k, repetition_penalty, top_p))
                    raw_audio[idx] = audio
                continue
            elapsed = time.time() - t0
            total_gen_time += elapsed
            for idx, audio in zip(g_idxs, wavs):
                audio = audio.squeeze()
                dur = len(audio) / SAMPLE_RATE
                print(f"      [batch {idx+1:3d}/{len(chunks)}] {dur:.1f}s | \"{chunks[idx][0][:40]}...\"")
                if chunk_dir:
                    _save_audio_cache(
                        os.path.join(chunk_dir, f"{idx:04d}.wav"), audio,
                        _audio_cache_signature(chunks[idx][0], voice_name, temperature,
                                               top_k, repetition_penalty, top_p))
                raw_audio[idx] = audio
            to_gen = [t for t in to_gen if raw_audio[t[0]] is None]
    for idx, chunk in to_gen:
        audio, elapsed = generate_chunk_audio(
            tts, voice_name, chunk, idx, len(chunks), temperature, top_k,
            repetition_penalty, top_p)
        total_gen_time += elapsed
        if chunk_dir:
            _save_audio_cache(
                os.path.join(chunk_dir, f"{idx:04d}.wav"), audio,
                _audio_cache_signature(chunk, voice_name, temperature, top_k,
                                       repetition_penalty, top_p))
        raw_audio[idx] = audio

    # 3. Ghép: fade ngắn ở 2 đầu mỗi chunk (chống click), chèn silence theo loại
    #    ranh giới thật: hết câu/ngắt đoạn (dài) > cắt giữa câu (ngắn, gần như liền).
    combined = []
    for i, audio in enumerate(raw_audio):
        # Fade out 2-3ms cuối + fade in 2-3ms đầu của chunk → âm kết thúc về 0
        # trước khi gặp silence → hết "click"/"pop" tại chỗ nối (không ảnh hưởng cảm nhận).
        audio = _edge_fade(audio, CROSSFADE_MS)
        combined.append(audio)
        if i < len(raw_audio) - 1:
            chunk_text = chunks[i][0]
            ends_para = chunks[i][1]
            # Ngắt đoạn (heading/end) hoặc hết câu → nghỉ dài; cắt giữa câu → nghỉ ngắn
            is_sentence_end = ends_para or chunk_text.rstrip().endswith((".", "!", "?", '"', "…"))
            silence_dur = SILENCE_PARA if is_sentence_end else SILENCE_BETWEEN
            combined.append(make_silence(silence_dur))
    # Silence cuối chapter (tránh chuyển chapter đột ngột)
    combined.append(make_silence(SILENCE_CHAPTER_END))

    final = np.concatenate(combined)
    # 4. Normalize toàn chapter (giữ nguyên dynamic range)
    final = _normalize(final, NORM_MASTER)
    # 5. Fade in/out ở đầu/cuối chapter (áp dụng lên audio samples, không phải silence)
    final = _apply_fade(final)

    return final, total_gen_time


def _find_ffmpeg() -> str | None:
    """Tìm ffmpeg: PATH → tools/ffmpeg/ffmpeg.exe → tools/ffmpeg/bin/ffmpeg.exe."""
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    for rel in ["tools/ffmpeg/ffmpeg.exe", "tools/ffmpeg/bin/ffmpeg.exe"]:
        cand = os.path.join(PROJECT_ROOT, rel)
        if os.path.exists(cand):
            return cand
    return None


def _subprocess_kwargs() -> dict:
    """Kwargs cho subprocess: ẩn cửa sổ console trên Windows (tránh bật PowerShell khi chạy ffmpeg)."""
    kwargs = {"capture_output": True, "text": True}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return kwargs


def convert_to_mp3(wav_path: str, keep_wav: bool = False, bitrate: str = "128k",
                   title: str = None, album: str = None, artist: str = None,
                   track: int = None, cover_path: str = None) -> str | None:
    """Convert WAV → MP3 bằng ffmpeg nếu có, tự động nhúng Metadata ID3 & Cover Art. Trả về mp3 path hoặc None."""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        print("   ⚠️  Không tìm thấy ffmpeg — giữ file WAV (dung lượng lớn)")
        return None

    mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"
    try:
        # Nếu chưa truyền cover_path, tự động tìm cover trong thư mục sách
        if not cover_path:
            parent_dir = os.path.dirname(wav_path)
            book_dir = os.path.dirname(parent_dir) if os.path.basename(parent_dir) == "audiobook" else parent_dir
            for c_name in ["cover.jpg", "cover.png", "cover.jpeg", "images/cover.jpg", "images/cover.png"]:
                cand = os.path.join(book_dir, c_name)
                if os.path.exists(cand):
                    cover_path = cand
                    break

        cmd = [ffmpeg, "-y", "-i", wav_path]
        has_cover = cover_path and os.path.exists(cover_path)
        if has_cover:
            cmd += ["-i", cover_path, "-map", "0:a", "-map", "1:v"]

        cmd += ["-codec:a", "libmp3lame", "-b:a", bitrate]

        if has_cover:
            cmd += ["-codec:v", "mjpeg", "-disposition:v", "attached_pic"]

        if title:
            cmd += ["-metadata", f"title={title}"]
        if album:
            cmd += ["-metadata", f"album={album}"]
        if artist:
            cmd += ["-metadata", f"artist={artist}"]
        if track:
            cmd += ["-metadata", f"track={track}"]

        cmd.append(mp3_path)
        result = subprocess.run(cmd, timeout=300, encoding="utf-8", errors="replace",
                                **_subprocess_kwargs())
        if result.returncode != 0:
            print(f"   ⚠️  ffmpeg lỗi (exit {result.returncode}): {result.stderr[:200]}")
            return None
        if not os.path.exists(mp3_path):
            print("   ⚠️  ffmpeg không tạo file MP3 output")
            return None
        mp3_size = os.path.getsize(mp3_path)
        if mp3_size < 1000:
            print(f"   ⚠️  MP3 quá nhỏ ({mp3_size} bytes) — có thể lỗi")
            return None
        if not keep_wav:
            os.remove(wav_path)
        return mp3_path
    except subprocess.TimeoutExpired:
        print("   ⚠️  ffmpeg timeout (>300s)")
        return None
    except Exception as e:
        print(f"   ⚠️  ffmpeg exception: {e}")
        return None


# --- Progress / Checkpoint ---

def _progress_path(slug: str) -> str:
    """Path to progress JSON file."""
    progress_dir = os.path.join(PROJECT_ROOT, "working", "progress_audio")
    os.makedirs(progress_dir, exist_ok=True)
    return os.path.join(progress_dir, f"{slug}.json")


def load_progress(slug: str) -> dict:
    """Load progress từ JSON. Trả về dict với completed chapters."""
    path = _progress_path(slug)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"slug": slug, "completed_chapters": [], "total_gen_time": 0, "total_audio_time": 0}


def save_progress(slug: str, progress: dict):
    """Save progress atomically so an interrupted run cannot truncate JSON."""
    path = _progress_path(slug)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    os.replace(temp, path)


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audio_progress_metadata(voice: str, temperature: float, top_k: int,
                            bitrate: str, source_fingerprint: str,
                            repetition_penalty: float = 1.5, top_p: float = 0.95,
                            music_files: list = None, music_volume: float = None) -> dict:
    return {
        "voice": voice,
        "temperature": temperature,
        "top_k": top_k,
        "repetition_penalty": repetition_penalty,
        "top_p": top_p,
        "bitrate": bitrate,
        "source_fingerprint": source_fingerprint,
        "max_chars": MAX_CHARS,
        "sample_rate": SAMPLE_RATE,
        "pipeline_version": 5,
        "music_files": music_files or [],
        "music_volume": music_volume,
    }


def reconcile_existing_outputs(slug: str) -> list:
    """Quét output tìm file chương đã tồn tại.

    Tìm trong output/books/<thư mục theo tên gốc>/audiobook/ (mới, map qua
    metadata.json) và output/<slug>/ (cũ). Trả về list chapter number đã có audio.
    """
    found = []
    # Cấu trúc mới: thư mục theo tên gốc (map slug qua find_book_dir)
    book_dir = find_book_dir(slug)
    new_dir = os.path.join(book_dir, "audiobook") if book_dir else None
    # Cấu trúc cũ
    old_dir = os.path.join(PROJECT_ROOT, "output", slug)
    for out_dir in [new_dir, old_dir]:
        if out_dir and os.path.isdir(out_dir):
            pattern = re.compile(rf"^(?:{re.escape(slug)}-)?ch(\d+)\.(?:mp3|wav)$")
            for fn in os.listdir(out_dir):
                m = pattern.match(fn)
                if m:
                    found.append(int(m.group(1)))
    return sorted(set(found))


def _chunks_root(slug: str) -> str:
    """Thư mục chứa audio chunk từng chapter (để resume giữa chừng)."""
    root = os.path.join(PROJECT_ROOT, "working", "progress_audio", "chunks", slug)
    os.makedirs(root, exist_ok=True)
    return root


def _chapter_chunk_dir(slug: str, chapter_num: int) -> str:
    d = os.path.join(_chunks_root(slug), f"ch{chapter_num:02d}")
    os.makedirs(d, exist_ok=True)
    return d


def merge_all_chapters(slug: str, out_dir: str, chapters: list, bitrate: str = "128k"):
    """Nối tất cả chapter MP3/WAV thành 1 file hoàn chỉnh.

    Ưu tiên dùng ffmpeg (nối MP3, RE-ENCODE để timestamp liên tục).
    Nếu không có ffmpeg, nối WAV bằng numpy.
    """

    # Tìm tất cả file chapter đã tạo, sắp xếp theo số thứ tự
    mp3_files = []
    wav_files = []
    for ch in sorted(chapters, key=lambda c: c["num"]):
        mp3 = os.path.join(out_dir, f"ch{ch['num']:02d}.mp3")
        wav = os.path.join(out_dir, f"ch{ch['num']:02d}.wav")
        # Fallback: cấu trúc cũ <slug>-chNN.mp3
        if not os.path.exists(mp3):
            mp3_old = os.path.join(out_dir, f"{slug}-ch{ch['num']:02d}.mp3")
            if os.path.exists(mp3_old):
                mp3 = mp3_old
        if not os.path.exists(wav):
            wav_old = os.path.join(out_dir, f"{slug}-ch{ch['num']:02d}.wav")
            if os.path.exists(wav_old):
                wav = wav_old
        if os.path.exists(mp3):
            mp3_files.append(mp3)
        elif os.path.exists(wav):
            wav_files.append(wav)

    if not mp3_files and not wav_files:
        print("   ⚠️  Không tìm thấy file chapter nào để merge")
        return

    # Ưu tiên merge MP3 bằng ffmpeg — RE-ENCODE (không -c copy) để chuẩn hoá
    # sample-rate/bitrate giữa các chapter → timestamp liên tục, player không
    # nhảy sai thời điểm; aresample=async=1 ép đúng tốc độ khi có chênh lệch.
    if mp3_files:
        ffmpeg = _find_ffmpeg()
        if not ffmpeg:
            print("   ⚠️  Cần ffmpeg để merge MP3. Giữ nguyên các file chapter riêng lẻ.")
            return
        merged_path = os.path.join(out_dir, f"{slug}.mp3")
        concat_list = os.path.join(out_dir, f"{slug}_concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for mp3 in mp3_files:
                # ffmpeg concat demuxer cần path escaped
                safe = mp3.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{safe}'\n")
        # Re-encode: -ar 48000 -ac 1 chuẩn hoá mọi chapter về cùng format
        # (tránh bitrate/sample-rate khác nhau làm ngắt quãng khi ghép).
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
               "-ar", "48000", "-ac", "1",
               "-af", "aresample=async=1:first_pts=0",
               "-codec:a", "libmp3lame", "-b:a", bitrate,
               "-metadata", f"title={slug}", "-metadata", f"album={slug}",
               merged_path]
        try:
            result = subprocess.run(cmd, timeout=600, **_subprocess_kwargs())
            if result.returncode == 0 and os.path.exists(merged_path):
                size_mb = os.path.getsize(merged_path) / 1024 / 1024
                print(f"   ✅ Merge: {merged_path} ({size_mb:.1f} MB, {len(mp3_files)} chapters, re-encoded {bitrate})")
            else:
                print(f"   ⚠️  ffmpeg merge lỗi: {result.stderr[:200]}")
        except Exception as e:
            print(f"   ⚠️  Merge exception: {e}")
        finally:
            if os.path.exists(concat_list):
                os.remove(concat_list)
        return

    # Fallback: nối WAV bằng numpy
    print(f"   🔗 Merging {len(wav_files)} WAV files...")
    all_audio = []
    for wav in wav_files:
        data, sr = sf.read(wav, dtype="float32")
        all_audio.append(data)
        all_audio.append(make_silence(1.0, sr))  # 1s silence giữa chapters
    merged = np.concatenate(all_audio)
    merged_wav = os.path.join(out_dir, f"{slug}.wav")
    sf.write(merged_wav, merged, sr)
    size_mb = os.path.getsize(merged_wav) / 1024 / 1024
    print(f"   ✅ Merge: {merged_wav} ({size_mb:.1f} MB)")
    # Thử convert sang MP3
    mp3 = convert_to_mp3(merged_wav, keep_wav=True, title=slug, album=slug)
    if mp3:
        print(f"   ✅ MP3: {mp3}")


def _create_tts(args) -> "object":
    """Khởi tạo VieNeu-TTS v3 Turbo theo chế độ chạy (GPU/CPU).

    - GPU (--gpu): dùng PyTorch/CUDA (model gốc fp32/bf16 + static batching).
    - CPU (mặc định): dùng ONNX Runtime int8 (nhanh, torch-free).
    """
    import vieneu
    if args.gpu:
        import torch
        if not torch.cuda.is_available():
            print("   ⚠️  --gpu được chỉ định nhưng không tìm thấy CUDA — chạy CPU thay thế.")
            return vieneu.Vieneu()
        dev = f"cuda:{torch.cuda.current_device()}"
        print(f"   ⚡ GPU: {torch.cuda.get_device_name(torch.cuda.current_device())} ({dev})")
        return vieneu.Vieneu(device=dev)
    print("   💻 Backend: CPU (ONNX Runtime int8)")
    kwargs = {}
    if args.threads and args.threads > 0:
        kwargs["threads"] = args.threads
    return vieneu.Vieneu(**kwargs)


def main():
    parser = argparse.ArgumentParser(description="Tạo audiobook từ -vi.md")
    parser.add_argument("--slug", help="Book slug (auto-detect nếu bỏ trống)")
    parser.add_argument("--chapter", type=int, nargs="+", help="Chapter cụ thể (vd: --chapter 1 2 3)")
    parser.add_argument("--first", action="store_true", help="Chỉ tạo chapter đầu tiên (test nhanh)")
    parser.add_argument("--sample", action="store_true", help="Tạo 1 sample ngắn (~30s) để test giọng")
    parser.add_argument("--sample-chars", type=int, default=400, help="Số ký tự cho sample mode (default: 400)")
    parser.add_argument("--force", action="store_true", help="Chạy lại từ đầu, bỏ qua progress")
    parser.add_argument("--keep-wav", action="store_true", help="Giữ file WAV sau khi convert MP3")
    parser.add_argument("--merge", action="store_true",
                        help="Sau khi generate, nối tất cả chapter thành 1 file hoàn chỉnh")
    parser.add_argument("--voice", default=None, help="Tên voice đã lưu (vd: van_tinh). Mặc định dùng active")
    parser.add_argument("--temperature", type=float, default=0.7, help="Nhiệt độ TTS (default: 0.7)")
    parser.add_argument("--top-k", type=int, default=20, help="Top-k sampling (default: 20)")
    parser.add_argument("--repetition-penalty", type=float, default=1.5,
                        help="Repetition penalty (default: 1.5, cao hơn = ít lặp từ/câu hơn)")
    parser.add_argument("--top-p", type=float, default=0.95,
                        help="Top-p nucleus sampling (default: 0.95)")
    parser.add_argument("--bitrate", default="128k", help="Bitrate MP3 (default: 128k, có thể dùng 64k)")
    parser.add_argument("--read-titles", action="store_true", default=True,
                        help="Đọc tên chapter đầu mỗi chương (default: bật)")
    parser.add_argument("--no-read-titles", action="store_false", dest="read_titles",
                        help="Không đọc tên chapter")
    parser.add_argument("--pronounce-json", default=None,
                        help="JSON từ điển phát âm ngoại lệ {'từ': 'cách đọc'} (merge lên mặc định)")
    parser.add_argument("--keep-chunks", action="store_true",
                        help="Giữ cache WAV từng chunk sau khi chapter xong (phục vụ phân tích lặp)")
    parser.add_argument("--music", nargs="?", const="auto", default=None, metavar="FILE",
                        help="Trộn nhạc nền DƯỚI giọng đọc. Truyền tên file trong core/music/ "
                             "(vd: --music sach_ke_chuyen_lofi.mp3), 'auto' = chọn file có sẵn, "
                             "nhiều file cách dấu phẩy để xoay theo chương. Mặc định tắt.")
    parser.add_argument("--music-auto", action="store_true",
                        help="Tự chọn nhạc theo nội dung chương bằng AI (Deepseek) — thông minh hơn xoay đều")
    parser.add_argument("--music-volume", type=float, default=None,
                        help=f"Volume nhạc nền trung bình 0..1 (default: {MUSIC_VOLUME_DEFAULT})")
    parser.add_argument("--gpu", action="store_true",
                        help="Chạy TTS trên GPU (CUDA) — nhanh hơn nhiều nếu có NVIDIA. Mặc định: CPU/ONNX.")
    parser.add_argument("--batch-size", type=int, default=8,
                        help="Số chunk gộp mỗi forward khi chạy GPU (default: 8). Lớn hơn = nhanh hơn, tốn VRAM hơn.")
    parser.add_argument("--threads", type=int, default=0,
                        help="Số intra-op threads cho ONNX/CPU (0 = mặc định engine). Chỉ áp dụng khi chạy CPU.")
    args = parser.parse_args()

    if args.pronounce_json:
        load_pronounce_dict(args.pronounce_json)

    # 1. Find -vi.md
    vi_md, slug = find_vi_md(args.slug)
    print(f"📖 Book: {slug}")
    print(f"   File: {vi_md}")

    # Load per-book pronunciation overrides (nếu có)
    _load_book_pronunciation(slug)

    # 2. Detect chapters
    chapters, all_lines = detect_chapters(vi_md)
    print(f"📑 Found {len(chapters)} chapters")

    # Sample mode: chỉ tạo 1 đoạn ngắn để test giọng
    if args.sample:
        print(f"\n🎤 Sample mode — tạo {args.sample_chars} ký tự từ chapter đầu tiên")
        ch = chapters[0]
        paragraphs = extract_chapter_text(all_lines, ch["line_start"], ch["line_end"],
                                          include_title=args.read_titles)
        passage = find_nice_passage(paragraphs, min_chars=200, max_chars=args.sample_chars)
        if not passage:
            print("❌ Không tìm thấy đoạn văn phù hợp")
            return

        print(f"   Text ({len(passage)} chars): \"{passage[:80]}...\"")

        print("\n🎙️ Loading VieNeu-TTS v3 Turbo...")
        tts = _create_tts(args)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from manage_voice import resolve_voice, get_voice_path
        if args.voice:
            ref_path = get_voice_path(args.voice)
            if not ref_path:
                print(f"❌ Voice '{args.voice}' not found. Run 'manage_voice.py list'")
                return
        else:
            ref_path = resolve_voice(non_interactive=True)
            if not ref_path:
                return
        voice_name = "active_voice"
        tts.add_voice(voice_name, ref_path, description="Active voice for audiobook",
                      gender=_get_voice_gender(ref_path), denoise=False)

        print("🎵 Generating...")
        t0 = time.time()
        audio = tts.infer(passage, voice=voice_name, style="doc_truyen", max_chars=TTS_MAX_CHARS,
                          temperature=args.temperature, top_k=args.top_k,
                          repetition_penalty=args.repetition_penalty, top_p=args.top_p,
                          apply_watermark=False)
        elapsed = time.time() - t0
        audio = audio.squeeze()
        # Normalize + fade (giống chapter mode để nghe nhất quán)
        audio = _normalize(audio, NORM_MASTER)
        audio = _apply_fade(audio)

        out_dir = os.path.join(PROJECT_ROOT, "output", "samples")
        os.makedirs(out_dir, exist_ok=True)
        wav_path = os.path.join(out_dir, f"{slug}-sample.wav")
        sf.write(wav_path, audio, SAMPLE_RATE)

        info = sf.info(wav_path)
        print(f"\n✅ Sample: {wav_path}")
        print(f"   Duration: {info.duration:.1f}s | Gen: {elapsed:.1f}s | RTF: {elapsed/info.duration:.2f}")
        return

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

    # Output dir: output/books/<thư mục theo tên gốc>/audiobook/
    book_dir = find_book_dir(slug)
    if not book_dir:
        # Tạo mới nếu chưa có (sách mới): thư mục theo slug (sẽ được đặt tên gốc sau)
        book_dir = os.path.join(PROJECT_ROOT, "output", "books", slug)
    out_dir = os.path.join(book_dir, "audiobook")
    os.makedirs(out_dir, exist_ok=True)

    # Nhạc nền (music bed): resolve danh sách file dùng cho các chapter
    music_files = []
    music_volume = args.music_volume if args.music_volume is not None else MUSIC_VOLUME_DEFAULT
    if args.music:
        avail = list_music_files()
        if not avail:
            print("   ⚠️  core/music/ trống — tắt nhạc nền (đặt file .mp3/.wav vào core/music/)")
        else:
            if args.music == "auto":
                # auto: chọn file đầu tiên (hoặc xoay nếu dùng --music "auto,auto")
                music_files = [avail[0]]
            else:
                # Dùng tên file chỉ định, cho phép nhiều file cách dấu phẩy
                for name in [s.strip() for s in args.music.split(",") if s.strip()]:
                    if name == "auto":
                        pick = avail[len(music_files) % len(avail)]
                        music_files.append(pick)
                    elif name in avail:
                        music_files.append(name)
                    else:
                        print(f"   ⚠️  Không tìm thấy nhạc '{name}' trong core/music/ — bỏ qua")
            if music_files:
                print(f"🎵 Nhạc nền: {', '.join(music_files)} (volume {music_volume:.0%}, xoay theo chương)")
            else:
                print("   ⚠️  Không có nhạc nền hợp lệ — tắt")
    elif args.music_auto:
        # Chế độ AI: mỗi chương tự gợi ý nhạc theo nội dung (suggest_music.py, có cache)
        avail = list_music_files()
        if not avail:
            print("   ⚠️  core/music/ trống — tắt nhạc nền (đặt file .mp3/.wav vào core/music/)")
        else:
            print(f"🎵 Nhạc nền: TỰ ĐỘNG theo nội dung (AI) — {len(avail)} bài có trong core/music/ (volume {music_volume:.0%})")

    # 3. Load progress
    progress = load_progress(slug)
    completed = set(progress.get("completed_chapters", []))

    # Reconcile: dò file audio đã tồn tại trong output/ (resume cả khi mất progress JSON)
    # Bỏ qua reconcile khi --force (muốn tạo lại từ đầu)
    if not args.force:
        existing = reconcile_existing_outputs(slug)
        if existing:
            new_done = [n for n in existing if n not in completed]
            if new_done:
                completed.update(new_done)
                progress["completed_chapters"] = sorted(completed)
                print(f"🔎 Phát hiện {len(new_done)} chương đã có audio: {new_done} → đánh dấu hoàn thành")

    if completed and not args.force:
        print(f"📊 Progress: {len(completed)} chapters completed")
        not_done = [ch for ch in selected if ch["num"] not in completed]
        if not not_done:
            print("✅ All selected chapters already completed. Use --force to regenerate.")
            return
        selected = not_done
        print(f"   Remaining: {[ch['num'] for ch in selected]}")
    elif args.force:
        print("🔄 Force mode — regenerating all chapters")
        progress = {"slug": slug, "completed_chapters": [], "total_gen_time": 0, "total_audio_time": 0}
        completed = set()
        chunks_root = _chunks_root(slug)
        if os.path.isdir(chunks_root):
            shutil.rmtree(chunks_root, ignore_errors=True)

    # 4. Load TTS
    print("\n🎙️ Loading VieNeu-TTS v3 Turbo...")
    tts = _create_tts(args)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from manage_voice import resolve_voice, get_voice_path
    if args.voice:
        ref_path = get_voice_path(args.voice)
        if not ref_path:
            print(f"❌ Voice '{args.voice}' not found. Run 'manage_voice.py list'")
            return
    else:
        ref_path = resolve_voice(non_interactive=True)
        if not ref_path:
            return
    voice_name = "active_voice"
    tts.add_voice(voice_name, ref_path,
                  description="Active voice for audiobook",
                  gender=_get_voice_gender(ref_path),
                  denoise=False)

    source_fingerprint = _file_sha256(vi_md)
    current_metadata = audio_progress_metadata(
        args.voice or os.path.basename(ref_path),
        args.temperature, args.top_k, args.bitrate,
        source_fingerprint,
        args.repetition_penalty, args.top_p,
        music_files=music_files, music_volume=music_volume)
    old_metadata = progress.get("audio_metadata")
    metadata_changed = bool(completed and old_metadata != current_metadata)
    if metadata_changed:
        print("⚠️  Tham số/voice đã đổi; tạo lại các chapter đã hoàn tất.")
        completed = set()
        progress["completed_chapters"] = []
        if args.first:
            selected = [chapters[0]]
        elif args.chapter:
            selected = [ch for ch in chapters if ch["num"] in args.chapter]
        else:
            selected = chapters
    progress["audio_metadata"] = current_metadata
    save_progress(slug, progress)

    # 5. Generate audio for each selected chapter
    # Khởi tạo từ progress cũ (cộng dồn khi resume)
    total_gen = progress.get("total_gen_time", 0)
    total_audio = progress.get("total_audio_time", 0)
    total_size = 0
    gen_this_run = 0
    audio_this_run = 0
    start_time = time.time()
    chapters_done_this_run = 0

    for ch in selected:
        num = ch["num"]
        title = ch["title"]
        start = ch["line_start"]
        end = ch["line_end"]

        # Skip if already completed (double-check)
        if num in completed:
            print(f"   ⏭  Chapter {num:02d} already done, skipping")
            continue

        print(f"\n{'─'*50}")
        print(f"📑 Chapter {num:02d}: {title}")
        print(f"   Lines {start+1}-{end} ({end-start} lines)")

        # Extract text (paragraph-aware)
        paragraphs = extract_chapter_text(all_lines, start, end,
                                          include_title=args.read_titles)
        total_chars = sum(len(p[0]) for p in paragraphs)
        print(f"   {len(paragraphs)} đoạn văn, {total_chars} ký tự")

        if not paragraphs:
            print("   ⚠️  No text found, skipping")
            continue

        # Chunk
        chunks = smart_chunk(paragraphs)
        if not chunks:
            print("   ⚠️  No chunks generated, skipping")
            continue
        print(f"   {len(chunks)} chunks (max {MAX_CHARS} chars)")

        # Generate (có checkpoint từng chunk → resume nhanh khi bị gián đoạn)
        chunk_dir = _chapter_chunk_dir(slug, num)
        print(f"   🎵 Generating...")
        try:
            audio, gen_time = generate_chapter_audio(
                tts, voice_name, chunks, num,
                temperature=args.temperature, top_k=args.top_k,
                chunk_dir=chunk_dir, force=args.force,
                repetition_penalty=args.repetition_penalty, top_p=args.top_p,
                use_batch=args.gpu, batch_size=args.batch_size, slug=slug)
        except Exception as e:
            print(f"   ❌ Failed at chapter {num}: {e}")
            print(f"   💾 Progress saved (chunk cache giữ lại để resume). Run again to resume.")
            save_progress(slug, progress)
            return

        # Trộn nhạc nền DƯỚI giọng đọc (music bed) nếu có
        if args.music_auto:
            # Chế độ AI (agent): đọc bản đồ gợi ý nhạc theo nội dung chương từ file JSON
            # (do agent chấm cảm xúc từng chương và ghi vào working/progress_audio/music_map.json).
            music_name = None
            map_path = os.path.join(PROJECT_ROOT, "working", "progress_audio", "music_map.json")
            try:
                if os.path.exists(map_path):
                    music_map = json.load(open(map_path, encoding="utf-8"))
                    # Map lưu theo dạng {"slug": {chapter_num: "file.mp3"}}
                    per_book = music_map.get(slug, {})
                    music_name = per_book.get(str(num))
            except Exception as e:
                print(f"   ⚠️  Lỗi đọc bản đồ nhạc ({e}) — dùng xoay đều")
            if not music_name:
                avail = list_music_files()
                if avail:
                    music_name = avail[(num - 1) % len(avail)]
            if music_name:
                music_path = os.path.join(MUSIC_DIR, music_name)
                audio, used = mix_music_bed(audio, music_path, volume=music_volume,
                                            chapter_num=num, music_list=[music_name])
                if used:
                    print(f"   🎵 Nhạc nền (agent): {used} (chapter {num})")
        elif music_files:
            music_name = music_files[(num - 1) % len(music_files)]
            music_path = os.path.join(MUSIC_DIR, music_name)
            audio, used = mix_music_bed(audio, music_path, volume=music_volume,
                                        chapter_num=num, music_list=music_files)
            if used:
                print(f"   🎵 Nhạc nền: {used} (chapter {num})")

        # Save WAV
        wav_path = os.path.join(out_dir, f"ch{num:02d}.wav")
        sf.write(wav_path, audio, SAMPLE_RATE)

        # Lấy duration từ WAV trước khi convert (sf.info không hỗ trợ MP3 trên mọi hệ thống)
        wav_info = sf.info(wav_path)
        wav_duration = wav_info.duration

        # Convert to MP3 (có metadata title/album/artist/track/cover)
        mp3_title = f"Chương {num}" + (f": {title}" if title else "")
        album_name = os.path.basename(book_dir) if book_dir else slug
        mp3_path = convert_to_mp3(wav_path, keep_wav=args.keep_wav,
                                  bitrate=args.bitrate, title=mp3_title, album=album_name,
                                  track=num)
        final_path = mp3_path if mp3_path else wav_path
        size_mb = os.path.getsize(final_path) / 1024 / 1024
        total_gen += gen_time
        total_audio += wav_duration
        total_size += size_mb
        gen_this_run += gen_time
        audio_this_run += wav_duration

        # Dọn chunk cache sau khi chapter hoàn thành (trừ khi --keep-chunks để phân tích)
        if os.path.isdir(chunk_dir) and not args.keep_chunks:
            shutil.rmtree(chunk_dir, ignore_errors=True)

        # ETA dựa trên chapters đã xong TRONG lần chạy này (chính xác hơn)
        chapters_done_this_run += 1
        elapsed_total = time.time() - start_time
        if chapters_done_this_run > 0:
            avg_time_per_ch = elapsed_total / chapters_done_this_run
            remaining_chapters = len(selected) - chapters_done_this_run
            eta_seconds = avg_time_per_ch * remaining_chapters
            eta_str = f" | ETA: {eta_seconds/60:.0f}m"
        else:
            eta_str = ""

        print(f"   ✅ {final_path}")
        print(f"      Duration: {wav_duration:.1f}s ({wav_duration/60:.1f} min) | Gen: {gen_time:.1f}s | RTF: {gen_time/wav_duration:.2f} | {size_mb:.1f} MB{eta_str}")

        # Update progress
        completed.add(num)
        progress["completed_chapters"] = sorted(completed)
        progress["total_gen_time"] = total_gen
        progress["total_audio_time"] = total_audio
        save_progress(slug, progress)

    # 6. Summary
    elapsed_total = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"🎧 HOÀN THÀNH — {slug}")
    print(f"   Chapters: {len(completed)}/{len(chapters)}")
    print(f"   Audio tổng: {total_audio:.1f}s ({total_audio/60:.1f} min)")
    print(f"   Gen time tổng: {total_gen:.1f}s ({total_gen/60:.1f} min)")
    if audio_this_run > 0:
        print(f"   Lần này: {audio_this_run:.1f}s audio, {gen_this_run:.1f}s gen, RTF: {gen_this_run/audio_this_run:.2f}")
        print(f"   Tốc độ trung bình: {elapsed_total/60:.1f} phút wall-clock / {chapters_done_this_run} chapter")
    print(f"   Total size: {total_size:.1f} MB")
    print(f"   Output: {out_dir}")
    print(f"{'='*50}")

    # 7. Merge all chapters nếu --merge
    if args.merge:
        print(f"\n🔗 Merging chapters...")
        merge_all_chapters(slug, out_dir, chapters, bitrate=args.bitrate)


if __name__ == "__main__":
    main()
