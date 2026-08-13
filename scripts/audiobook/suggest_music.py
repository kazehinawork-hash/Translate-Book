"""
Gợi ý nhạc nền phù hợp với nội dung từng chương (mức B — dùng AI).

- Đọc tóm tắt chapter (text đầu) từ file vi.md.
- Gửi cho Deepseek (config từ ~/.translate_book/config.json) để chấm:
  - mood: nhãn cảm xúc chính (vui/buồn/căng/thư giãn/hồi hộp/ấm áp...)
  - energy: mức năng lượng 0..1 (hội thoại nhiều/hành động nhanh → cao)
  - suggest: tên file nhạc phù hợp nhất trong core/music/ (kèm lý do ngắn)
- Cache kết quả theo (slug, chapter_num, danh sách nhạc) để không gọi lại khi chạy lại.

Dùng: python suggest_music.py --slug <slug> --chapter N [--preview]
"""
import sys, os, re, json, time, urllib.request, hashlib

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".translate_book", "config.json")
CACHE_FILE = os.path.join(PROJECT_ROOT, "working", "progress_audio", "music_suggest_cache.json")
MUSIC_DIR = os.path.join(PROJECT_ROOT, "core", "music")

MAX_SAMPLE_CHARS = 800  # tóm tắt text gửi AI (đủ ngữ cảnh, không tốn token)
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE = "https://api.deepseek.com/v1"


def load_deepseek_config():
    """Đọc API key + model Deepseek từ config.json của desktop, fallback env var."""
    # 1. Config file (như desktop app dùng)
    if os.path.exists(CONFIG_FILE):
        try:
            cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
            provider = cfg.get("ActiveProvider") or "deepseek"
            p = cfg.get("Providers", {}).get(provider) or cfg.get("Providers", {}).get("deepseek")
            if p and p.get("ApiKey"):
                return p["ApiKey"], p.get("Model") or DEFAULT_MODEL, (p.get("BaseUrl") or DEFAULT_BASE).rstrip("/")
        except Exception:
            pass
    # 2. Env var fallback
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"], DEFAULT_MODEL, DEFAULT_BASE
    return None, None, None


def list_music():
    if not os.path.isdir(MUSIC_DIR):
        return []
    exts = (".mp3", ".wav", ".m4a", ".flac", ".ogg")
    return sorted(f for f in os.listdir(MUSIC_DIR) if os.path.splitext(f)[1].lower() in exts)


def extract_chapter_text(vi_md, chapter_num):
    """Trích text chapter theo heading '# ' từ vi.md."""
    lines = open(vi_md, encoding="utf-8").read().splitlines()
    # Tìm các heading chương (dạng '# (01)' hoặc '# Chương 1' hoặc '# xxx')
    heads = [(i, l) for i, l in enumerate(lines) if re.match(r"^#\s+", l)]
    # Chọn heading chứa số chapter (đề phòng heading mở đầu như tiêu đề sách)
    idx = -1
    for i, l in heads:
        if re.search(rf"[（(]0?{chapter_num}[）)]|\b0?{chapter_num}\b", l):
            idx = i
            break
    if idx < 0 and heads:
        # fallback: heading thứ N (bỏ heading đầu tiên nếu là tiêu đề sách)
        h = [x for x in heads if "Mục lục" not in x[1]]
        if len(h) >= chapter_num:
            idx = h[chapter_num - 1][0]
    if idx < 0:
        return ""
    # Lấy đến heading tiếp theo
    end = len(lines)
    for i, l in heads:
        if i > idx:
            end = i
            break
    text = "\n".join(lines[idx:end])
    # Làm sạch markdown
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # ảnh
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # link
    text = re.sub(r"[#*_>`~]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def call_deepseek(api_key, model, base, system, user):
    url = f"{base}/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def suggest_chapter(api_key, model, base, chapter_num, text, music_list, cache_key):
    """Gợi ý nhạc cho 1 chapter (có cache)."""
    # Kiểm tra cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE, encoding="utf-8"))
        except Exception:
            cache = {}
    if cache_key in cache:
        return cache[cache_key]

    if not api_key:
        return {"mood": "trung tính", "energy": 0.5, "suggest": None, "reason": "Không có API key"}

    system = ("Bạn là chuyên gia âm nhạc phim/audiobook. Đọc nội dung một chương sách tiếng Việt "
              "rồi chấm điểm tâm trạng và đề xuất bản nhạc nền phù hợp nhất. "
              "CHỈ trả về JSON dạng {\"mood\": \"tên cảm xúc (vui/buồn/căng/thư giãn/hồi hộp/ấm áp...)\", "
              "\"energy\": số 0..1 (hành động nhanh/hội thoại nhiều → cao), "
              "\"suggest\": tên file nhạc đúng trong danh sách, \"reason\": lý do 1 câu tiếng Việt}.")
    user = (f"Danh sách nhạc có sẵn (kèm đặc trưng):\n{json.dumps(music_list, ensure_ascii=False)}\n\n"
            f"Nội dung chương {chapter_num} (trích):\n{text[:MAX_SAMPLE_CHARS]}")

    try:
        raw = call_deepseek(api_key, model, base, system, user)
        # Parse JSON (có thể kèm ```json ... ```)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.S).strip()
        data = json.loads(raw)
        data["suggest"] = data.get("suggest")
        # Validate suggest nằm trong danh sách
        if data.get("suggest") not in music_list:
            data["suggest"] = None
    except Exception as e:
        data = {"mood": "trung tính", "energy": 0.5, "suggest": None, "reason": f"Lỗi AI: {e}"}

    # Cache
    cache[cache_key] = data
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return data


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gợi ý nhạc nền theo nội dung chương (mức B)")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--chapter", type=int, required=True, help="Số chương")
    parser.add_argument("--preview", action="store_true", help="Chỉ in kết quả, không ghi cache")
    args = parser.parse_args()

    vi_md = os.path.join(PROJECT_ROOT, "output", "books", args.slug, "final", "vi.md")
    if not os.path.exists(vi_md):
        print(f"❌ Không tìm thấy {vi_md}")
        return

    text = extract_chapter_text(vi_md, args.chapter)
    if not text:
        print(f"❌ Không trích được text chương {args.chapter}")
        return

    music_list = list_music()
    if not music_list:
        print("❌ core/music/ trống")
        return

    api_key, model, base = load_deepseek_config()
    cache_key = hashlib.sha256(
        json.dumps({"slug": args.slug, "ch": args.chapter, "music": music_list}, sort_keys=True,
                   ensure_ascii=False).encode()).hexdigest()

    if args.preview:
        # preview: không cache
        cache = {}
        result = suggest_chapter(api_key, model, base, args.chapter, text, music_list, cache_key)
    else:
        result = suggest_chapter(api_key, model, base, args.chapter, text, music_list, cache_key)

    print(f"Chương {args.chapter}: mood={result.get('mood')} | energy={result.get('energy')} | "
          f"suggest={result.get('suggest')} | ({result.get('reason','')})")


if __name__ == "__main__":
    main()
