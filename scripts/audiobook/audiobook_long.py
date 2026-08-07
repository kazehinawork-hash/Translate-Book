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
import sys, os, re, time, argparse, json, shutil, hashlib
import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Config
MAX_CHARS = 180          # chars per chunk (giảm từ 240 để tránh líu lưỡi)
SILENCE_BETWEEN = 0.4    # seconds silence between chunks
SILENCE_PARA = 0.8       # seconds silence between paragraphs
SILENCE_CHAPTER_END = 1.5 # seconds silence cuối chapter (trước khi chapter mới bắt đầu)
SAMPLE_RATE = 48000
MAX_RETRIES = 3          # retries per chunk on TTS failure
FADE_MS = 10             # fade in/out ở đầu/cuối chapter (tránh click khi start/stop)
NORM_MASTER = 0.92       # normalize toàn chapter


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


def find_vi_md(slug: str = None) -> tuple:
    """Tìm file -vi.md. Trả về (path, slug).

    Tìm theo thứ tự:
    1. output/books/<slug>/final/vi.md (cấu trúc mới)
    2. output/<slug>/<slug>-vi.md (cấu trúc cũ, backward compat)
    """
    books_dir = os.path.join(PROJECT_ROOT, "output", "books")
    output_dir = os.path.join(PROJECT_ROOT, "output")

    if slug:
        # Thử cấu trúc mới trước
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
    # Cấu trúc mới: output/books/<slug>/final/vi.md
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


def normalize_vietnamese_text(text: str) -> str:
    """Chuẩn hóa văn bản tiếng Việt cho TTS sử dụng VietNormalizer.

    Chuyển đổi số thành chữ, chuẩn hóa ngày tháng, tiền tệ,
    từ viết tắt, từ mượn.
    """
    global _viet_normalizer
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
            if include_title and heading and len(heading) > 2:
                paragraphs.append((heading, False))
            continue
        # Cleanup markdown
        text = cleanup_markdown(stripped)
        if not text or len(text) <= 2:
            continue
        # Bỏ qua dòng chỉ có dấu câu hoặc ký tự vô nghĩa cho TTS
        if re.match(r'^[\s"\'""\'\'!,.?…—–\-*~()（）\-–—\[\]【】{}]+$', text):
            continue
        # Chuẩn hóa văn bản tiếng Việt cho TTS
        text = normalize_vietnamese_text(text)
        current.append(text)
    # Paragraph cuối cùng → section end
    if current:
        paragraphs.append((" ".join(current), True))
    return paragraphs


def _split_sentences(text: str) -> list:
    """Tách text thành danh sách câu hoàn chỉnh.

    Tách tại: . ! ? … ; theo sau bởi space hoặc cuối chuỗi.
    Xử lý quote đóng: ". "? "! "? → giữ nguyên trong cùng câu.
    """
    text = text.strip()
    if not text:
        return []
    # Tách tại dấu câu结束 (không tách nếu trước đó là quote mở)
    # Pattern: dấu câu + space hoặc cuối chuỗi, KHÔNG có quote mở ngay trước
    parts = re.split(r'(?<=[.!?…])\s+', text)
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

        for sent_idx, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue

            is_last_sent = (sent_idx == len(sentences) - 1)

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
                    # Ưu tiên tách tại dấu câu kết thúc câu (. ! ? …)
                    for sep in [". ", "! ", "? ", "… ", "…"]:
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

    # Gộp chunk cuối cùng vào chunk trước nếu cả 2 đều nhỏ
    if len(chunks) >= 2:
        last_text, last_para = chunks[-1]
        prev_text, prev_para = chunks[-2]
        if len(prev_text) + len(last_text) + 1 <= max_chars:
            chunks[-2] = (prev_text + " " + last_text, last_para or prev_para)
            chunks.pop()

    return chunks


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
                         temperature=0.7, top_k=20):
    """Generate audio cho 1 chunk với retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            t0 = time.time()
            audio = tts.infer(
                chunk,
                voice=voice_name,
                style="doc_truyen",
                max_chars=MAX_CHARS + 64,
                temperature=temperature,
                top_k=top_k,
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


def _audio_cache_signature(chunk: str, voice_name: str, temperature: float, top_k: int) -> str:
    payload = json.dumps({
        "chunk": chunk,
        "voice": voice_name,
        "temperature": temperature,
        "top_k": top_k,
        "max_chars": MAX_CHARS,
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


def generate_chapter_audio(tts, voice_name, chunks, chapter_num, temperature=0.7,
                           top_k=20, chunk_dir=None, force=False):
    """Generate audio cho 1 chapter với cache kiểm tra được tham số."""
    raw_chunks = []
    total_gen_time = 0

    # 1. Generate hoặc load cache — chỉ thu thập audio chunks, chưa chèn silence
    for i, (chunk, ends_para) in enumerate(chunks):
        if chunk_dir and not force:
            chunk_wav = os.path.join(chunk_dir, f"{i:04d}.wav")
            signature = _audio_cache_signature(chunk, voice_name, temperature, top_k)
            audio = _load_cached_audio(chunk_wav, chunk_wav + ".sig", signature)
            if audio is not None:
                print(f"      [{i+1:3d}/{len(chunks)}] ⏭  dùng lại cache")
                raw_chunks.append(audio)
                continue

        audio, elapsed = generate_chunk_audio(
            tts, voice_name, chunk, i, len(chunks), temperature, top_k)
        total_gen_time += elapsed

        if chunk_dir:
            _save_audio_cache(
                os.path.join(chunk_dir, f"{i:04d}.wav"), audio,
                _audio_cache_signature(chunk, voice_name, temperature, top_k))

        raw_chunks.append(audio)

    # 2. Ghép: chèn silence GIỮA các chunk, + silence cuối chapter
    combined = []
    for i, audio in enumerate(raw_chunks):
        combined.append(audio)
        if i < len(raw_chunks) - 1:
            chunk_text = chunks[i][0]
            ends_para = chunks[i][1]
            is_para_end = ends_para or chunk_text.rstrip().endswith((".", "!", "?", '"', "…"))
            silence_dur = SILENCE_PARA if is_para_end else SILENCE_BETWEEN
            combined.append(make_silence(silence_dur))
    # Silence cuối chapter (tránh chuyển chapter đột ngột)
    combined.append(make_silence(SILENCE_CHAPTER_END))

    final = np.concatenate(combined)
    # 3. Normalize toàn chapter (giữ nguyên dynamic range)
    final = _normalize(final, NORM_MASTER)
    # 4. Fade in/out ở đầu/cuối chapter (áp dụng lên audio samples, không phải silence)
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


def convert_to_mp3(wav_path: str, keep_wav: bool = False, bitrate: str = "128k",
                   title: str = None, album: str = None) -> str | None:
    """Convert WAV → MP3 bằng ffmpeg nếu có. Trả về mp3 path hoặc None."""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        print("   ⚠️  Không tìm thấy ffmpeg — giữ file WAV (dung lượng lớn)")
        return None

    mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"
    try:
        import subprocess
        cmd = [ffmpeg, "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", bitrate]
        if title:
            cmd += ["-metadata", f"title={title}"]
        if album:
            cmd += ["-metadata", f"album={album}"]
        cmd.append(mp3_path)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
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
                            bitrate: str, source_fingerprint: str) -> dict:
    return {
        "voice": voice,
        "temperature": temperature,
        "top_k": top_k,
        "bitrate": bitrate,
        "source_fingerprint": source_fingerprint,
        "max_chars": MAX_CHARS,
        "sample_rate": SAMPLE_RATE,
        "pipeline_version": 3,
    }


def reconcile_existing_outputs(slug: str) -> list:
    """Quét output寻找 file chương đã tồn tại.

    Tìm trong output/books/<slug>/audiobook/ (mới) và output/<slug>/ (cũ).
    Trả về list chapter number đã có file audio.
    """
    found = []
    # Cấu trúc mới
    new_dir = os.path.join(PROJECT_ROOT, "output", "books", slug, "audiobook")
    # Cấu trúc cũ
    old_dir = os.path.join(PROJECT_ROOT, "output", slug)
    for out_dir in [new_dir, old_dir]:
        if os.path.isdir(out_dir):
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


def merge_all_chapters(slug: str, out_dir: str, chapters: list):
    """Nối tất cả chapter MP3/WAV thành 1 file hoàn chỉnh.

    Ưu tiên dùng ffmpeg (nối MP3). Nếu không có ffmpeg, nối WAV bằng numpy.
    """
    import subprocess

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

    # Ưu tiên merge MP3 bằng ffmpeg
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
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
               "-codec:a", "copy", merged_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0 and os.path.exists(merged_path):
                size_mb = os.path.getsize(merged_path) / 1024 / 1024
                print(f"   ✅ Merge: {merged_path} ({size_mb:.1f} MB, {len(mp3_files)} chapters)")
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
    parser.add_argument("--bitrate", default="128k", help="Bitrate MP3 (default: 128k, có thể dùng 64k)")
    parser.add_argument("--read-titles", action="store_true", default=True,
                        help="Đọc tên chapter đầu mỗi chương (default: bật)")
    parser.add_argument("--no-read-titles", action="store_false", dest="read_titles",
                        help="Không đọc tên chapter")
    args = parser.parse_args()

    # 1. Find -vi.md
    vi_md, slug = find_vi_md(args.slug)
    print(f"📖 Book: {slug}")
    print(f"   File: {vi_md}")

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
        import vieneu
        tts = vieneu.Vieneu()

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
        audio = tts.infer(passage, voice=voice_name, style="doc_truyen", max_chars=MAX_CHARS + 64,
                          temperature=args.temperature, top_k=args.top_k,
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

    # Output dir: output/books/<slug>/audiobook/
    out_dir = os.path.join(PROJECT_ROOT, "output", "books", slug, "audiobook")
    os.makedirs(out_dir, exist_ok=True)

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
    import vieneu
    tts = vieneu.Vieneu()

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
        source_fingerprint)
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
                chunk_dir=chunk_dir, force=args.force)
        except Exception as e:
            print(f"   ❌ Failed at chapter {num}: {e}")
            print(f"   💾 Progress saved (chunk cache giữ lại để resume). Run again to resume.")
            save_progress(slug, progress)
            return

        # Save WAV
        wav_path = os.path.join(out_dir, f"ch{num:02d}.wav")
        sf.write(wav_path, audio, SAMPLE_RATE)

        # Lấy duration từ WAV trước khi convert (sf.info không hỗ trợ MP3 trên mọi hệ thống)
        wav_info = sf.info(wav_path)
        wav_duration = wav_info.duration

        # Convert to MP3 (có metadata title/album)
        mp3_title = f"Chương {num}" + (f": {title}" if title else "")
        mp3_path = convert_to_mp3(wav_path, keep_wav=args.keep_wav,
                                  bitrate=args.bitrate, title=mp3_title, album=slug)
        final_path = mp3_path if mp3_path else wav_path
        size_mb = os.path.getsize(final_path) / 1024 / 1024
        total_gen += gen_time
        total_audio += wav_duration
        total_size += size_mb
        gen_this_run += gen_time
        audio_this_run += wav_duration

        # Dọn chunk cache sau khi chapter hoàn thành
        if os.path.isdir(chunk_dir):
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
        merge_all_chapters(slug, out_dir, chapters)


if __name__ == "__main__":
    main()
