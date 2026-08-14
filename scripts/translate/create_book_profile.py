"""
create_book_profile.py - Tạo hồ sơ văn chương (book profile) cho cuốn sách trước khi dịch.

Profile là "chân dung" văn chương của cuốn sách: giọng văn tác giả, hệ xưng hô
giữa từng cặp nhân vật, cách xử lý hội thoại, thành ngữ/đặc trưng + 1 đoạn dịch
mẫu chuẩn (bản gốc → bản Việt "láng"). Agent đọc profile này khi dịch từng chunk
→ bản dịch nhất quán về giọng văn, xưng hô, cảm xúc và mượt hơn.

Cách dùng (agent tự chạy trước khi dịch):
    python scripts/translate/create_book_profile.py --chunks-dir working/chunks/<slug> --progress-dir working/progress/<slug>

Script in ra hướng dẫn + vài chunk đại diện (đầu/giữa/cuối) để agent phân tích,
rồi agent tự viết `working/profile/<slug>.md` (UTF-8). Nếu file profile đã tồn tại,
script báo "đã có" và dừng (không ghi đè).
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402

setup_encoding()

PROFILE_DIR = PROJECT_ROOT / 'working' / 'profile'


def find_chunk_files(chunks_dir: Path):
    """Lấy danh sách chunk JSON đã sắp xếp theo số thứ tự."""
    files = []
    for f in sorted(chunks_dir.glob('*.json')):
        try:
            data = json.loads(f.read_text(encoding='utf-8-sig'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
            except Exception:
                continue
        files.append((f, data))
    return files


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Tạo hồ sơ văn chương (book profile) cho cuốn sách')
    parser.add_argument('--chunks-dir', type=Path, required=True,
                        help='Thư mục chunk JSON gốc (working/chunks/{book}/)')
    parser.add_argument('--progress-dir', type=Path, required=True,
                        help='Thư mục progress (working/progress/{book}/) — để suy ra slug')
    parser.add_argument('--samples', type=int, default=3,
                        help='Số chunk đại diện để phân tích (mặc định: 3 = đầu/giữa/cuối)')
    args = parser.parse_args()

    if not args.chunks_dir.exists():
        print(f"[LỖI] Không tìm thấy thư mục chunks: {args.chunks_dir}", file=sys.stderr)
        sys.exit(1)

    # Suy slug từ progress_dir (working/progress/<slug>)
    slug = None
    parts = args.progress_dir.parts
    if 'working' in parts:
        idx = parts.index('working')
        if idx + 1 < len(parts):
            slug = parts[idx + 1] if idx + 1 == len(parts) - 1 else parts[idx + 2]
    if not slug:
        slug = args.chunks_dir.name

    out_file = PROFILE_DIR / f'{slug}.md'
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    if out_file.exists():
        print(f"ℹ️  Profile đã tồn tại: {out_file} — giữ nguyên (không ghi đè).")
        print(f"   Nếu muốn tạo lại, xóa file này rồi chạy lại.")
        return

    chunks = find_chunk_files(args.chunks_dir)
    if not chunks:
        print(f"[LỖI] Không có chunk JSON nào trong {args.chunks_dir}", file=sys.stderr)
        sys.exit(1)

    # Chọn chunk đại diện: đầu / giữa / cuối
    n = len(chunks)
    n_sample = min(args.samples, n)
    if n_sample == 1:
        idxs = [0]
    else:
        idxs = sorted({0, n // 2, n - 1})[:n_sample]

    print("=" * 70)
    print("  TẠO HỒ SƠ VĂN CHƯƠNG (BOOK PROFILE) — hướng dẫn cho Agent")
    print("=" * 70)
    print(f"\n📖 Slug: {slug} | {n} chunks")
    print(f"   File profile sẽ ghi vào: {out_file}")
    print(f"""
──────────────────────────────────────────────────────────────────────
Bạn hãy phân tích các chunk đại diện bên dưới rồi viết `{out_file.name}`
(markdown, UTF-8) với cấu trúc sau:

# Hồ sơ văn chương — {slug}

## 1. Tác giả & thể loại
- Tác giả / thể loại / giọng văn chung (kể chuyện hóm hỉnh, tản mạn trữ tình,
  cổ trang trang nghiêm, hiện đại gấp gáp...)

## 2. Hệ xưng hô (theo từng cặp nhân vật)
- VD: A gọi B là "mày", B gọi A là "tao"; A gọi C là "anh"; người kể gọi các
  nhân vật khác thế nào... — liệt kê CỤ THỂ từng cặp, tránh dịch lệch giữa các chunk

## 3. Cách xử lý hội thoại
- Câu thoại dài/ngắn? Có dùng khẩu ngữ đặc trưng vùng miền? Nhân vật hay
  ngập ngừng/chen ngang? Giữ đặc trưng này khi dịch

## 4. Thành ngữ & đặc trưng ngôn ngữ
- Thành ngữ, điển cố, từ lặp có chủ ý, cách tác giả dùng ẩn dụ...

## 5. Đoạn dịch mẫu chuẩn (quan trọng nhất)
- Chọn 1 đoạn (3-6 câu) trong các chunk bên dưới, dịch theo chuẩn "láng như
  nhà văn": mượt, tự nhiên, đúng LITERARY QUALITY. Quan trọng: bản mẫu phải
  GIỮ HỒN bản gốc — đúng ý, đúng sắc thái, đúng giọng điệu, không thêm/bớt/đổi
  ý chỉ để "cho đẹp". Đây là mực thước để các chunk khác bám theo

## 6. Lưu ý riêng
- Bất cứ điều gì cần chú ý khi dịch cuốn này
──────────────────────────────────────────────────────────────────────
""")

    for idx in idxs:
        fpath, data = chunks[idx]
        text = data.get('text') or data.get('original_text') or data.get('source_text') or ''
        chapter = data.get('chapter', '')
        cid = data.get('chunk_id', '?')
        print(f"\n===== CHUNK {cid} ({fpath.name}) — {chapter} =====")
        print(text[:3000])
        if len(text) > 3000:
            print(f"... [cắt — chunk dài {len(text)} ký tự]")

    print(f"\n→ Sau khi phân tích, viết {out_file} (UTF-8) rồi tiếp tục dịch.")
    print("  Mỗi chunk dịch sau đó sẽ đọc profile này để bám giọng văn/xưng hô.")


if __name__ == '__main__':
    main()
