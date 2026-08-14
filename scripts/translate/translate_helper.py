"""
translate_helper.py - Script hỗ trợ Agent dịch

Script này KHÔNG gọi API. Nó chuẩn bị dữ liệu để Agent dịch dễ dàng hơn.

Modes:
  --prepare {chunk_id}        : Đọc chunk JSON + glossary -> in ra prompt
  --prepare-batch {start} {end}: Chuẩn bị nhiều chunk cùng lúc
  --save {chunk_id}            : Nhận input từ stdin -> lưu vào progress
  --interactive                : Lặp tự động: prompt -> đợi dịch -> save -> commit -> next
  --status                     : Hiển thị tiến trình
  --next                       : Hiển thị chunk tiếp theo chưa dịch

Interactive mode commands:
  ---END---    Kết thúc nhập bản dịch và lưu
  ---SKIP---   Bỏ qua chunk này
  ---BACK---   Quay lại chunk trước
  ---EXIT---   Thoát interactive mode

Ví dụ:
    python scripts/translate_helper.py --interactive
    python scripts/translate_helper.py --interactive --skip 5
    python scripts/translate_helper.py --interactive --from 10 --auto-commit
    python scripts/translate_helper.py --save 0 --auto-commit
"""

import os
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402
from glossary_lib import load_all, filter_for_book  # noqa: E402


# Optional pyperclip for clipboard support
try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

TERMINAL_WIDTH = 66


def doc_json(file_path: Path) -> dict | None:
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            return json.loads(file_path.read_text(encoding=enc))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return None


def doc_glossary(csv_path: Path) -> str:
    if not csv_path.exists():
        return ''
    for enc in ('utf-8-sig', 'utf-8', 'gbk'):
        try:
            return csv_path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return ''


def get_glossary_text(args) -> str:
    """Lấy nội dung glossary cho prompt.

    Ưu tiên:
      1. `--glossary <file>` nếu được truyền (tương thích cũ).
      2. Ngược lại, đọc master.csv + lọc theo slug (từ --progress-dir hoặc --chunks-dir).
    """
    if args.glossary:
        return doc_glossary(args.glossary)

    # Tự đoán slug từ --progress-dir hoặc --chunks-dir
    # (thư mục có dạng working/<sub>/<slug> hoặc working/<slug>)
    slug = None
    for d in (getattr(args, 'progress_dir', None), getattr(args, 'chunks_dir', None)):
        if d is None or not d.name:
            continue
        parts = d.parts
        # working/progress/<slug> | working/chunks/<slug> | working/<slug>
        if 'working' in parts:
            idx = parts.index('working')
            if idx + 1 < len(parts):
                slug = parts[idx + 1] if idx + 1 == len(parts) - 1 else parts[idx + 2]
                break
    if slug:
        rows = filter_for_book(load_all(), slug)
        if rows:
            import csv as _csv
            import io
            buf = io.StringIO()
            writer = _csv.DictWriter(buf, fieldnames=['source', 'target', 'type', 'note', 'book', 'author', 'genre'],
                                     extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
            return buf.getvalue()
    return ''


def build_prompt(chunk_data: dict, glossary_text: str, source_lang: str, target_lang: str, trilingual: bool = False) -> str:
    chunk_id = chunk_data.get('chunk_id', '?')
    total = chunk_data.get('total_chunks', '?')
    chapter = chunk_data.get('chapter', '')
    text = chunk_data.get('text', '')
    prev_ctx = chunk_data.get('prev_context', '')
    next_ctx = chunk_data.get('next_context', '')

    if trilingual:
        return f"""# TRILINGUAL TRANSLATION INSTRUCTIONS ({source_lang} \u2192 Pinyin \u2192 {target_lang})

You are a professional translator. Your task is to produce a **trilingual output** for the chunk below.

## FORMAT
Output each sentence as a **3-line block**, with blocks separated by a blank line:

```
{source_lang} sentence 1.
pinyin of sentence 1.
{target_lang} translation of sentence 1.

{source_lang} sentence 2.
pinyin of sentence 2.
{target_lang} translation of sentence 2.
```

## EXAMPLE (Chinese \u2192 Pinyin \u2192 Vietnamese)
Input: "今天天气很好。我们去公园散步。"

Output:
```
今天天气很好。
jīn tiān tiān qì hěn hǎo。
Hôm nay thời tiết rất đẹp。

我们去公园散步。
wǒ men qù gōng yuán sàn bù。
Chúng tôi đi dạo trong công viên。
```

## RULES
1. Preserve ALL formatting: paragraphs, headings, lists, emphasis, line breaks
2. Keep proper nouns, brand names in original unless they have widely accepted Vietnamese translations
3. Use the GLOSSARY below \u2014 NEVER deviate from these translations
4. Do NOT add explanations, notes, or translator comments
5. Do NOT translate content inside code blocks, URLs, or placeholder tags
6. Maintain the original tone and style
7. Output ONLY the trilingual blocks \u2014 no extra text before or after
8. Preserve markdown tables and LaTeX formulas EXACTLY as they are.

## LITERARY QUALITY (v\u0103n ch\u01b0\u01a1ng l\u00e1ng nh\u01b0ng GI\u1eee H\u1ed2N \u2014 b\u1eaft bu\u1ed9c, \u00e1p d\u1ee5ng cho d\u00f2ng ti\u1ebfng Vi\u1ec7t)
1. D\u1ecbch C\u1ea2 C\u00c2U, C\u1ea2 \u0110O\u1ea0N, kh\u00f4ng d\u1ecbch t\u1eebng t\u1eeb m\u1ed9t \u2014 b\u1ea3n Vi\u1ec7t ph\u1ea3i \u0111\u1ecdc t\u1ef1 nhi\u00ean nh\u01b0 v\u0103n Vi\u1ec7t g\u1ed1c, kh\u00f4ng m\u00e1y m\u00f3c b\u00e1m c\u1ea5u tr\u00fac c\u00e2u H\u00e1n
2. \u2b50 GI\u1eee H\u1ed2N B\u1ea2N G\u1ed0C: \u201cl\u00e1ng\u201d ch\u1ec9 l\u00e0 c\u00e1ch di\u1ec5n \u0111\u1ea1t; tuy\u1ec7t \u0111\u1ed1i KH\u00d4NG th\u00eam \u00fd, b\u1edbt \u00fd, \u0111\u1ed5i logic, l\u00e0m m\u1ec1m s\u1eafc th\u00e1i hay c\u01b0\u1eddng \u0111i\u1ec7u c\u1ee7a nguy\u00ean t\u00e1c. Gi\u1eef nguy\u00ean: gi\u1ecdng \u0111i\u1ec7u (ch\u00e2m bi\u1ebfm/tr\u1eef t\u00ecnh/gay g\u1eaft), quan \u0111i\u1ec3m ng\u01b0\u1eddi k\u1ec3, th\u00e1i \u0111\u1ed9 t\u00e1c gi\u1ea3 v\u1edbi nh\u00e2n v\u1eadt/s\u1ef1 vi\u1ec7c, c\u00e1c chi ti\u1ebft c\u1ee5 th\u1ec3, s\u1ed1 li\u1ec7u, th\u1ee9 t\u1ef1 k\u1ec3. N\u1ebfu c\u00e2u g\u1ed1c \u00fd n\u1eb7ng n\u1ec1, b\u1ea3n d\u1ecbch ph\u1ea3i n\u1eb7ng n\u1ec1; n\u1ebfu g\u1ed1c m\u1ec1m m\u1ea1i, b\u1ea3n d\u1ecbch m\u1ec1m m\u1ea1i \u2014 kh\u00f4ng \u201cl\u00e0m \u0111\u1eb9p\u201d th\u00eam cho kh\u00e1c \u00fd
3. C\u00e2u H\u00e1n d\u00e0i: \u0111\u01b0\u1ee3c ph\u00e9p t\u00e1ch th\u00e0nh 2-3 c\u00e2u ng\u1eafn t\u1ef1 nhi\u00ean h\u01a1n cho ti\u1ebfng Vi\u1ec7t; c\u00e2u v\u1ee5n c\u00f3 th\u1ec3 n\u1ed1i l\u1ea1i \u2014 m\u1ed7i c\u00e2u H\u00e1n v\u1eabn gi\u1eef \u0111\u00fang 1 d\u00f2ng H\u00e1n + 1 d\u00f2ng pinyin + 1 d\u00f2ng Vi\u1ec7t
4. Nh\u1ecbp \u0111i\u1ec7u & \u00e2m thanh: \u01b0u ti\u00ean c\u00e2u c\u00f3 v\u1ea7n, c\u00f3 nh\u1ecbp, tr\u00e1nh l\u1eb7p t\u1eeb ng\u1eef li\u00ean ti\u1ebfp; thay \u0111\u1ea1i t\u1eeb tr\u00f9ng b\u1eb1ng c\u00e1ch t\u1ec9nh l\u01b0\u1ee3c ho\u1eb7c \u0111\u1ed5i c\u00e1ch di\u1ec5n \u0111\u1ea1t
5. Kh\u1ea9u ng\u1eef & h\u1ed9i tho\u1ea1i: d\u1ecbch nh\u01b0 ng\u01b0\u1eddi Vi\u1ec7t th\u1ef1c s\u1ef1 n\u00f3i chuy\u1ec7n, gi\u1eef s\u1eafc th\u00e1i; KH\u00d4NG d\u1ecbch s\u00e1t ch\u1eef l\u00e0m tho\u1ea1i c\u1ee9ng nh\u1eafc
6. X\u01b0ng h\u00f4: ch\u1ecdn v\u00e0 gi\u1eef NH\u1ea4T QU\u00c1N m\u1ed9t h\u1ec7 x\u01b0ng h\u00f4 ph\u00f9 h\u1ee3p theo m\u1ed1i quan h\u1ec7 nh\u00e2n v\u1eadt; kh\u00f4ng tr\u00e1o \u0111\u1ed5i gi\u1eefa ch\u1eebng
7. C\u1ea3m x\u00fac & h\u00ecnh \u1ea3nh: t\u00e1i hi\u1ec7n c\u1ea3m x\u00fac nguy\u00ean t\u00e1c b\u1eb1ng t\u1eeb ng\u1eef ti\u1ebfng Vi\u1ec7t gi\u00e0u h\u00ecnh \u1ea3nh; th\u00e0nh ng\u1eef H\u00e1n kh\u00f3 hi\u1ec3u khi d\u1ecbch s\u00e1t th\u00ec chuy\u1ec3n sang t\u01b0\u01a1ng \u0111\u01b0\u01a1ng ti\u1ebfng Vi\u1ec7t t\u1ef1 nhi\u00ean (t\u01b0\u01a1ng \u0111\u01b0\u01a1ng v\u1ec1 \u00fd v\u00e0 s\u1eafc th\u00e1i, kh\u00f4ng \u0111\u1ed5i \u00fd)
8. Thu\u1ea7n Vi\u1ec7t: \u01b0u ti\u00ean t\u1eeb thu\u1ea7n Vi\u1ec7t ho\u1eb7c H\u00e1n-Vi\u1ec7t \u0111\u00e3 th\u00f4ng d\u1ee5ng; tr\u00e1nh l\u1ea1m d\u1ee5ng t\u1eeb H\u00e1n-Vi\u1ec7t kh\u00f3 hi\u1ec3u khi c\u00f3 t\u1eeb Vi\u1ec7t thay th\u1ebf
9. Tr\u00e1nh d\u1ecbch m\u00e1y: kh\u00f4ng c\u00f3 c\u1ee5m "m\u1ed9t c\u00e1ch", "nh\u1eefng \u0111i\u1ec1u", "m\u00e0 c\u00f2n", "tuy nhi\u00ean" l\u1eb7p \u2014 \u0111\u1ecdc l\u1ea1i b\u1ea3n d\u1ecbch nh\u01b0 v\u0103n xu\u00f4i Vi\u1ec7t thu\u1ea7n

### V\u00cd D\u1ee4 CHU\u1ea8N (b\u1ea3n c\u1ee9ng vs b\u1ea3n l\u00e1ng)
C\u00e2u H\u00e1n: \u201c\u5979\u5fc3\u91cc\u5f88\u96be\u8fc7\uff0c\u4f46\u662f\u5979\u5f3a\u5fcd\u7740\u6ce1\u6ca1\u6709\u8ba9\u6cea\u6c34\u6d41\u4e0b\u6765\u3002\u201d
- \ud83d\udee1\ufe0f B\u1ea3n c\u1ee9ng (m\u00e1y m\u00f3c): \u201cTrong l\u00f2ng c\u00f4 \u1ea5y r\u1ea5t kh\u00f3 ch\u1ecbu, nh\u01b0ng c\u00f4 \u1ea5y c\u1ed1 n\u00ecn l\u1ea1i kh\u00f4ng \u0111\u1ec3 n\u01b0\u1edbc m\u1eaft ch\u1ea3y xu\u1ed1ng.\u201d (l\u1eb7p "c\u00f4 \u1ea5y", c\u1ee9ng)
- \u2705 B\u1ea3n l\u00e1ng (nh\u00e0 v\u0103n): \u201cL\u00f2ng c\u00f4 qu\u1ea9n qu\u1ea1i, nh\u01b0ng c\u00f4 n\u00e9n h\u1ebft v\u00e0o trong, kh\u00f4ng \u0111\u1ec3 m\u1ed9t gi\u1ecdt n\u01b0\u1edbc m\u1eaft r\u01a1i xu\u1ed1ng.\u201d (h\u00ecnh \u1ea3nh, t\u1ec9nh l\u01b0\u1ee3c \u0111\u1ea1i t\u1eeb, nh\u1ecbp t\u1ef1 nhi\u00ean)

C\u00e2u H\u00e1n: \u201c\u4ed6\u4e0d\u505c\u5730\u5de5\u4f5c\uff0c\u4e00\u76f4\u5de5\u4f5c\u5230\u5f88\u665a\u3002\u201d
- \ud83d\udee1\ufe0f C\u1ee9ng: \u201cAnh \u1ea5y kh\u00f4ng ng\u1eebng l\u00e0m vi\u1ec7c, m\u1ed9t m\u1ef1c l\u00e0m vi\u1ec7c \u0111\u1ebfn r\u1ea5t mu\u1ed9n.\u201d (l\u1eb7p "l\u00e0m vi\u1ec7c")
- \u2705 L\u00e1ng: \u201cAnh mi\u1ebft m\u00e0i l\u00e0m \u0111\u1ebfn khuya.\u201d (g\u1ecdn, t\u1ef1 nhi\u00ean, kh\u00f4ng l\u1eb7p)

B\u1ea3n d\u1ecbch c\u1ee7a b\u1ea1n ph\u1ea3i \u0111\u1ea1t chu\u1ea9n \u201cL\u00e1ng\u201d nh\u01b0 c\u00e1c v\u00ed d\u1ee5 tr\u00ean, kh\u00f4ng ph\u1ea3i chu\u1ea9n \u201cC\u1ee9ng\u201d.

## GLOSSARY
{glossary_text if glossary_text else '(No glossary provided)'}

## PREVIOUS CHUNK CONTEXT (for reference only, do not re-translate)
{prev_ctx if prev_ctx else '(First chunk - no previous context)'}

## CHUNK TO TRANSLATE (Chunk {chunk_id}/{total}, {chapter})
{text}

## NEXT CHUNK CONTEXT (for reference only, do not re-translate)
{next_ctx if next_ctx else '(Last chunk - no next context)'}"""

    return f"""# TRANSLATION INSTRUCTIONS

You are a professional translator. Your task is to translate the chunk below from {source_lang} to {target_lang}.

## RULES
1. Preserve ALL formatting: paragraphs, headings, lists, emphasis, line breaks
2. Keep proper nouns, brand names in original unless they have widely accepted Vietnamese translations
3. Use the GLOSSARY below — NEVER deviate from these translations
4. Do NOT add explanations, notes, or translator comments
5. Do NOT translate content inside code blocks, URLs, or placeholder tags
6. Maintain the original tone and style
7. Output ONLY the translated text
8. CRITICAL: Maintain a strictly 1:1 paragraph ratio! Do NOT merge multiple short paragraphs into one, and do NOT split one paragraph into many.
9. Preserve markdown tables and LaTeX formulas EXACTLY as they are.

## LITERARY QUALITY (văn chương láng nhưng GIỮ HỒN — bắt buộc)
1. Dịch CẢ CÂU, CẢ ĐOẠN, không dịch từng từ một — bản dịch phải đọc tự nhiên như văn Việt gốc, không máy móc bám cấu trúc câu gốc
2. ⭐ GIỮ HỒN BẢN GỐC: "láng" chỉ là cách diễn đạt; tuyệt đối KHÔNG thêm ý, bớt ý, đổi logic, làm mềm sắc thái hay cường điệu của nguyên tác. Giữ nguyên: giọng điệu (châm biếm/trữ tình/gay gắt), quan điểm người kể, thái độ tác giả với nhân vật/sự việc, chi tiết cụ thể, số liệu, thứ tự kể. Nếu câu gốc ý nặng nề, bản dịch phải nặng nề; nếu gốc mềm mại, bản dịch mềm mại — không "làm đẹp" thêm cho khác ý
3. Câu gốc dài (đặc biệt tiếng Trung): được phép tách thành 2-3 câu ngắn tự nhiên hơn cho tiếng Việt; câu vụn có thể nối lại — miễn GIỮ NGUYÊN số đoạn văn (paragraph ratio 1:1)
4. Nhịp điệu & âm thanh: ưu tiên câu có vần, có nhịp, tránh lặp từ ngữ liên tiếp (trừ khi cố ý nhấn mạnh); thay đại từ trùng lặp bằng cách tỉnh lược hoặc đổi cách diễn đạt
5. Khẩu ngữ & hội thoại: dịch như người Việt thực sự nói chuyện, giữ sắc thái (hài hước, giận dữ, ngập ngừng, mỉa mai); KHÔNG dịch sát chữ làm thoại cứng nhắc
6. Xưng hô: chọn và giữ NHẤT QUÁN một hệ xưng hô phù hợp (tôi/bạn, tôi/cậu, anh/em, mày/tao...) theo mối quan hệ nhân vật; không tráo đổi giữa chừng
7. Cảm xúc & hình ảnh: tái hiện cảm xúc của nguyên tác bằng từ ngữ tiếng Việt giàu hình ảnh; nếu thành ngữ gốc khó hiểu khi dịch sát, chuyển sang thành ngữ/tương đương tiếng Việt tự nhiên (tương đương về ý và sắc thái, không đổi ý)
8. Thuần Việt: ưu tiên từ thuần Việt hoặc từ Hán-Việt đã thông dụng; tránh dịch lạm dụng từ Hán-Việt khó hiểu khi có từ Việt thay thế
9. Tránh dịch máy: không có cụm "một cách" (thay bằng trạng từ/cụm tự nhiên), "những điều", "mà còn", "tuy nhiên" lặp — đọc lại bản dịch như văn xuôi Việt thuần

### VÍ DỤ CHUẨN (bản cứng vs bản láng)
Câu EN: "She felt very sad inside, but she held back and didn't let the tears fall."
- 🛡️ Bản cứng (máy móc): "Cô ấy cảm thấy rất buồn trong lòng, nhưng cô ấy kìm lại và không để những giọt nước mắt rơi xuống." (lặp "cô ấy", cứng)
- ✅ Bản láng (nhà văn): "Lòng cô quặn thắt, nhưng cô nén hết vào trong, không để một giọt nước mắt rơi xuống." (hình ảnh, tỉnh lược đại từ, nhịp tự nhiên)

Câu EN: "He worked nonstop, working until very late."
- 🛡️ Cứng: "Anh ấy làm việc không ngừng, làm việc đến rất muộn." (lặp "làm việc")
- ✅ Láng: "Anh miệt mài làm đến khuya." (gọn, tự nhiên, không lặp)

Bản dịch của bạn phải đạt chuẩn "Láng" như các ví dụ trên, không phải chuẩn "Cứng".

## GLOSSARY
{glossary_text if glossary_text else '(No glossary provided)'}

## PREVIOUS CHUNK CONTEXT (for reference only, do not re-translate)
{prev_ctx if prev_ctx else '(First chunk - no previous context)'}

## CHUNK TO TRANSLATE (Chunk {chunk_id}/{total}, {chapter})
{text}

## NEXT CHUNK CONTEXT (for reference only, do not re-translate)
{next_ctx if next_ctx else '(Last chunk - no next context)'}"""


def make_progress_bar(completed: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return ''
    filled = int(completed * width / total)
    bar = '\u2588' * filled + '\u2591' * (width - filled)
    pct = int(completed * 100 / total)
    return f"[{bar}] {pct}%"


def print_header(title: str, char: str = '\u2550'):
    print(f"\n{char * TERMINAL_WIDTH}")
    print(f"  {title}")
    print(f"{char * TERMINAL_WIDTH}")


def git_auto_commit(chunk_id, total_chunks, progress_dir, dry_run=False, no_verify=False):
    """Auto-commit a translated chunk to git."""
    chunk_file = progress_dir / f"chunk_{chunk_id:03d}.json"
    if not chunk_file.exists():
        return False
    try:
        subprocess.run(
            ['git', 'add', str(chunk_file)],
            capture_output=True, check=False, cwd=PROJECT_ROOT
        )
        msg = f"translate: chunk {chunk_id}/{total_chunks}"
        cmd = ['git', 'commit', '-m', msg]
        if no_verify:
            cmd.append('--no-verify')
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, check=False, cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            if not dry_run:
                print(f"  [AUTO-COMMIT] chunk {chunk_id}/{total_chunks} committed", file=sys.stderr)
            return True
        else:
            if 'nothing to commit' in result.stderr or 'nothing to commit' in result.stdout:
                return True
            print(result.stderr, file=sys.stderr)
            return False
    except FileNotFoundError:
        return False


def find_chunk_file(chunks_dir: Path, chunk_id: int) -> Path | None:
    for pattern in [f"chunk-{chunk_id:03d}.json", f"chunk_{chunk_id:03d}.json"]:
        cf = chunks_dir / pattern
        if cf.exists():
            return cf
    matches = list(chunks_dir.glob(f"*{chunk_id:03d}*.json"))
    if matches:
        return matches[0]
    matches = list(chunks_dir.glob(f"*{chunk_id}*.json"))
    if matches:
        return matches[0]
    return None


def get_translated_ids(progress_dir: Path) -> set:
    translated = set()
    if progress_dir.exists():
        for f in progress_dir.glob('*.json'):
            data = doc_json(f)
            if data and data.get('translated_text', '').strip():
                translated.add(int(data.get('chunk_id', -1)))
    return translated


def find_next_chunk(chunks_dir: Path, progress_dir: Path, from_id: int = 0, translated: set | None = None) -> int | None:
    if translated is None:
        translated = get_translated_ids(progress_dir)
    if not chunks_dir.exists():
        return None
    import re
    all_chunks = sorted(chunks_dir.glob('*.json'), key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
    for f in all_chunks:
        data = doc_json(f)
        if data is None:
            continue
        cid = int(data.get('chunk_id', -1))
        if cid >= from_id and cid not in translated:
            return cid
    return None


def load_chunk_data(chunks_dir: Path, chunk_id: int) -> dict | None:
    cf = find_chunk_file(chunks_dir, chunk_id)
    if cf is None:
        return None
    return doc_json(cf)


def mode_prepare(args):
    chunks_dir = args.chunks_dir
    if not chunks_dir.exists():
        print(f"[L\u1ed6I] Th\u01b0 m\u1ee5c chunks kh\u00f4ng t\u1ed3n t\u1ea1i: {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    data = load_chunk_data(chunks_dir, args.prepare)
    if data is None:
        print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y chunk {args.prepare} trong {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    glossary_text = get_glossary_text(args)
    prompt = build_prompt(data, glossary_text, args.source_lang, args.target_lang, args.trilingual)
    print(prompt)


def mode_prepare_batch(args):
    chunks_dir = args.chunks_dir
    if not chunks_dir.exists():
        print(f"[L\u1ed6I] Th\u01b0 m\u1ee5c chunks kh\u00f4ng t\u1ed3n t\u1ea1i: {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    start = args.prepare_batch[0]
    end = args.prepare_batch[1]
    glossary_text = get_glossary_text(args)

    for cid in range(start, end + 1):
        data = load_chunk_data(chunks_dir, cid)
        if data is None:
            print(f"\n{'=' * TERMINAL_WIDTH}")
            print(f"CHUNK {cid}: File not found, skipping")
            continue

        prompt = build_prompt(data, glossary_text, args.source_lang, args.target_lang, args.trilingual)
        print(f"\n{'=' * TERMINAL_WIDTH}")
        print(f"CHUNK {cid}/{data.get('total_chunks', '?')} - {data.get('chapter', '')}")
        print('=' * TERMINAL_WIDTH)
        print(prompt)


def parse_trilingual_output(text: str) -> dict:
    """Parse trilingual Agent output into {original_text, pinyin_text, translated_text}.

    Expected format:
        Chinese line 1.
        pinyin line 1.
        Vietnamese line 1.

        Chinese line 2.
        pinyin line 2.
        Vietnamese line 2.
    """
    lines = [l.rstrip('\n\r') for l in text.splitlines()]
    blocks = []
    current_block = []
    for line in lines:
        if line.strip() == '':
            if len(current_block) == 3:
                blocks.append(current_block)
            current_block = []
        else:
            current_block.append(line)
    if len(current_block) == 3:
        blocks.append(current_block)

    if not blocks:
        return {
            'original_text': '',
            'pinyin_text': '',
            'translated_text': text.strip(),
        }

    originals = []
    pinyins = []
    translateds = []
    for block in blocks:
        originals.append(block[0])
        pinyins.append(block[1])
        translateds.append(block[2])

    return {
        'original_text': '\n'.join(originals),
        'pinyin_text': '\n'.join(pinyins),
        'translated_text': '\n'.join(translateds),
    }


def save_translation(chunk_id: int, translated_text: str, args, source_data: dict | None = None) -> Path:
    """Save translation to progress dir. Returns the output path."""
    progress_dir = args.progress_dir
    if not progress_dir.exists():
        progress_dir.mkdir(parents=True, exist_ok=True)

    chunks_dir = args.chunks_dir
    src = source_data or {}
    if not src and chunks_dir and chunks_dir.exists():
        d = load_chunk_data(chunks_dir, chunk_id)
        if d:
            src = {
                'chunk_id': d.get('chunk_id', chunk_id),
                'total_chunks': d.get('total_chunks', 0),
                'chapter': d.get('chapter', ''),
                'source_text': d.get('text', ''),
                'word_count_source': d.get('word_count', 0),
            }

    now = datetime.now().isoformat(timespec='seconds')
    translated_clean = translated_text.strip()

    progress_data = {
        'chunk_id': src.get('chunk_id', chunk_id),
        'total_chunks': src.get('total_chunks', 0),
        'chapter': src.get('chapter', ''),
        'source_text': src.get('source_text', ''),
        'translated_text': translated_clean,
        'translated_at': now,
        'word_count_source': src.get('word_count_source', 0),
        'word_count_translated': len(translated_clean.split()),
    }

    if args.trilingual:
        parsed = parse_trilingual_output(translated_clean)
        progress_data['mode'] = 'trilingual'
        progress_data['original_text'] = parsed['original_text']
        progress_data['pinyin_text'] = parsed['pinyin_text']
        progress_data['translated_text'] = parsed['translated_text']

    out_file = progress_dir / f"chunk_{chunk_id:03d}.json"
    out_file.write_text(json.dumps(progress_data, ensure_ascii=False, indent=2), encoding='utf-8')
    return out_file


def do_auto_commit(chunk_id: int, total_chunks: int, args):
    if args.auto_commit:
        ok = git_auto_commit(chunk_id, total_chunks, args.progress_dir, no_verify=args.no_verify)
        if ok:
            print(f"  [AUTO-COMMIT] chunk {chunk_id}/{total_chunks} committed")
        else:
            print(f"  [AUTO-COMMIT] skipped (git not available or nothing to commit)")


def mode_save(args):
    progress_dir = args.progress_dir
    if not progress_dir.exists():
        progress_dir.mkdir(parents=True, exist_ok=True)

    chunk_id = args.save

    print("Paste translated text, then type ---END--- on a new line to finish:", file=sys.stderr)
    try:
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

    lines = []
    for line in sys.stdin:
        stripped = line.rstrip('\n\r')
        if stripped == '---END---':
            break
        lines.append(line)

    translated = ''.join(lines).strip()
    if not translated:
        print("[L\u1ed6I] Kh\u00f4ng c\u00f3 n\u1ed9i dung d\u1ecbch, b\u1ecf qua.", file=sys.stderr)
        sys.exit(1)

    out_file = save_translation(chunk_id, translated, args)
    total = 0
    src_data = doc_json(out_file)
    if src_data:
        total = src_data.get('total_chunks', 0)
    print(f"\n\u2705 \u0110\u00e3 l\u01b0u: {out_file}", file=sys.stderr)

    do_auto_commit(chunk_id, total, args)


def mode_status(args):
    progress_dir = args.progress_dir
    if not progress_dir.exists():
        print(f"Th\u01b0 m\u1ee5c progress ch\u01b0a t\u1ed3n t\u1ea1i: {progress_dir}")
        print(f"Ti\u1ebfn tr\u00ecnh: 0/0 (0%)")
        return

    import re
    json_files = sorted(progress_dir.glob('*.json'), key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
    if not json_files:
        print(f"Kh\u00f4ng c\u00f3 chunk n\u00e0o trong {progress_dir}")
        return

    chunks = []
    for f in json_files:
        data = doc_json(f)
        if data and 'chunk_id' in data:
            chunks.append(data)

    chunks.sort(key=lambda c: int(c.get('chunk_id', 999999)))
    if not chunks:
        return

    total = max(c.get('total_chunks', 0) for c in chunks) or len(chunks)
    translated = sum(1 for c in chunks if c.get('translated_text', '').strip())

    bar = make_progress_bar(translated, total)
    print(f"Ti\u1ebfn tr\u00ecnh: {translated}/{total} {bar}\n")

    for c in chunks:
        cid = c.get('chunk_id', '?')
        chapter = c.get('chapter', '')
        has_translation = bool(c.get('translated_text', '').strip())
        status = '\u2705' if has_translation else '\u274c'
        ts = c.get('translated_at', '')[:10] if has_translation else ''
        ch = f" - {chapter[:40]}" if chapter else ''
        print(f"  {status} Chunk {cid}{ch} {ts}")


def mode_next(args):
    progress_dir = args.progress_dir
    chunks_dir = args.chunks_dir

    translated = get_translated_ids(progress_dir)

    if not chunks_dir or not chunks_dir.exists():
        print("[L\u1ed6I] C\u1ea7n --chunks-dir \u0111\u1ec3 x\u00e1c \u0111\u1ecbnh t\u1ed5ng s\u1ed1 chunk", file=sys.stderr)
        sys.exit(1)

    import re
    all_chunks = sorted(chunks_dir.glob('*.json'), key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
    for f in all_chunks:
        data = doc_json(f)
        if data is None:
            continue
        cid = int(data.get('chunk_id', -1))
        if cid >= 0 and cid not in translated:
            print(f"{cid}")
            print(f"chapter: {data.get('chapter', '')}", file=sys.stderr)
            print(f"file: {f.name}", file=sys.stderr)
            return

    print("T\u1ea5t c\u1ea3 chunk \u0111\u00e3 d\u1ecbch xong!")
    sys.exit(0)


def mode_interactive(args):
    chunks_dir = args.chunks_dir
    progress_dir = args.progress_dir
    if not progress_dir.exists():
        progress_dir.mkdir(parents=True, exist_ok=True)

    if not chunks_dir or not chunks_dir.exists():
        print(f"[L\u1ed6I] C\u1ea7n --chunks-dir \u0111\u1ec3 d\u00f9ng interactive mode", file=sys.stderr)
        sys.exit(1)

    glossary_text = get_glossary_text(args)

    # Get total chunks
    import re
    all_chunk_files = sorted(chunks_dir.glob('*.json'), key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
    if not all_chunk_files:
        print(f"[L\u1ed6I] Kh\u00f4ng c\u00f3 chunk JSON n\u00e0o trong {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    last_data = doc_json(all_chunk_files[-1])
    total_chunks = (last_data.get('total_chunks', 0) or
                    max((doc_json(f).get('chunk_id', 0) for f in all_chunk_files if doc_json(f)), default=0) + 1)

    from_id = args.from_id
    translated = get_translated_ids(progress_dir)
    history = []
    history_pos = -1

    print_header(f"INTERACTIVE TRANSLATION MODE", '\u2550')
    print(f"  Source: {args.source_lang}  |  Target: {args.target_lang}")
    print(f"  Chunks dir: {chunks_dir}")
    print(f"  Progress dir: {progress_dir}")
    if args.glossary:
        print(f"  Glossary: {args.glossary}")
    print(f"  Auto-commit: {'ON' if args.auto_commit else 'OFF'}")
    if HAS_CLIPBOARD:
        print(f"  Clipboard: available")
    print(f"\n  Commands during translation:")
    print(f"    ---END---   Save and continue")
    print(f"    ---SKIP---  Skip this chunk")
    print(f"    ---BACK---  Go back to previous chunk")
    print(f"    ---EXIT---  Exit interactive mode")
    print(f"{chr(0x2550) * TERMINAL_WIDTH}")

    prompt_count = 0
    while True:
        cid = find_next_chunk(chunks_dir, progress_dir, from_id, translated)
        if cid is None:
            print_header(f"ALL DONE! All {total_chunks} chunks translated.")
            break

        prompt_count += 1
        if prompt_count > 1:
            history_pos = -1

        data = load_chunk_data(chunks_dir, cid)
        if data is None:
            print(f"\n  [L\u1ed6I] Kh\u00f4ng th\u1ec3 \u0111\u1ecdc chunk {cid}, b\u1ecf qua")
            from_id = cid + 1
            continue

        chapter = data.get('chapter', '')
        word_count = data.get('word_count', 0)
        completed = len(translated)

        # Display progress and header
        bar = make_progress_bar(completed, total_chunks)
        print()
        print(f"{chr(0x2550) * TERMINAL_WIDTH}")
        print(f"  CHUNK {cid}/{total_chunks}  |  {chapter[:50] if chapter else ''}  |  {word_count} words")
        print(f"  {bar}")
        print(f"{chr(0x2550) * TERMINAL_WIDTH}")

        # Build and display prompt
        prompt = build_prompt(data, glossary_text, args.source_lang, args.target_lang, args.trilingual)
        print(f"\n[TRANSLATION PROMPT - copy this into Agent]")
        print(f"{chr(0x2500) * TERMINAL_WIDTH}")
        print(prompt)
        print(f"{chr(0x2500) * TERMINAL_WIDTH}")

        # Copy to clipboard if available
        if HAS_CLIPBOARD:
            try:
                pyperclip.copy(prompt)
                print(f"[CLIPBOARD] Prompt copied to clipboard!")
            except Exception:
                pass

        # Read translation
        print(f"\nPaste translation below (type ---END--- on a new line to finish):")
        print(f"  Commands: ---END---  ---SKIP---  ---BACK---  ---EXIT---")

        try:
            sys.stdin.reconfigure(encoding='utf-8')
        except Exception:
            pass

        input_lines = []
        for line in sys.stdin:
            stripped = line.rstrip('\n\r')
            if stripped == '---END---':
                break
            if stripped == '---SKIP---':
                input_lines = None
                break
            if stripped == '---BACK---':
                input_lines = 'BACK'
                break
            if stripped == '---EXIT---':
                print("\nExiting interactive mode.")
                sys.exit(0)
            input_lines.append(line)

        if input_lines is None:
            print(f"  \u23ed Skipped chunk {cid}")
            history.append(('skip', cid))
            from_id = cid + 1
            continue

        if input_lines == 'BACK':
            print(f"  \u23ed Going back")
            # Find the chunk before this one
            from_id = max(0, cid - 1)
            continue

        translated_text = ''.join(input_lines).strip()
        if not translated_text:
            print(f"  \u26a0\ufe0f Empty translation, skipped")
            from_id = cid + 1
            continue

        out_file = save_translation(cid, translated_text, args, source_data={
            'chunk_id': cid,
            'total_chunks': total_chunks,
            'chapter': chapter,
            'source_text': data.get('text', ''),
            'word_count_source': word_count,
        })
        translated.add(cid)
        print(f"  \u2705 Saved chunk {cid} to {out_file.name}")

        do_auto_commit(cid, total_chunks, args)

        history.append(('done', cid))
        from_id = cid + 1


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="H\u1ed7 tr\u1ee3 Agent d\u1ecbch t\u1eebng chunk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Common args
    parser.add_argument('--chunks-dir', type=Path,
                        help='Th\u01b0 m\u1ee5c ch\u1ee9a chunk JSON g\u1ed1c (working/chunks/{book}/)')
    parser.add_argument('--progress-dir', type=Path,
                        help='Th\u01b0 m\u1ee5c ch\u1ee9a chunk \u0111\u00e3 d\u1ecbch (working/progress/{book}/)')
    parser.add_argument('--glossary', type=Path,
                        help='File glossary CSV')
    parser.add_argument('--source-lang', type=str, default='English',
                        help='Ng\u00f4n ng\u1eef ngu\u1ed3n (m\u1eb7c \u0111\u1ecbnh: English)')
    parser.add_argument('--target-lang', type=str, default='Vietnamese',
                        help='Ng\u00f4n ng\u1eef \u0111\u00edch (m\u1eb7c \u0111\u1ecbnh: Vietnamese)')
    parser.add_argument('--auto-commit', action='store_true',
                        help='T\u1ef1 \u0111\u1ed9ng git commit sau m\u1ed7i chunk')
    parser.add_argument('--trilingual', action='store_true',
                        help='Ch\u1ebf \u0111\u1ed9 tam ng\u1eef (Chinese/Pinyin/Vietnamese)')
    parser.add_argument('--no-verify', action='store_true',
                        help='B\u1ecf qua git hook khi auto-commit')

    # Modes
    parser.add_argument('--prepare', type=int,
                        help='Chu\u1ea9n b\u1ecb prompt cho chunk_id')
    parser.add_argument('--prepare-batch', type=int, nargs=2, metavar=('START', 'END'),
                        help='Chu\u1ea9n b\u1ecb prompt cho nhi\u1ec1u chunk')
    parser.add_argument('--save', type=int,
                        help='Nh\u1eadn b\u1ea3n d\u1ecbch t\u1eeb stdin v\u00e0 l\u01b0u v\u00e0o progress')
    parser.add_argument('--interactive', action='store_true',
                        help='Ch\u1ebf \u0111\u1ed9 t\u01b0\u01a1ng t\u00e1c: t\u1ef1 \u0111\u1ed9ng l\u1eb7p qua c\u00e1c chunk ch\u01b0a d\u1ecbch')
    parser.add_argument('--status', action='store_true',
                        help='Hi\u1ec3n th\u1ecb ti\u1ebfn tr\u00ecnh d\u1ecbch')
    parser.add_argument('--next', action='store_true',
                        help='Hi\u1ec3n th\u1ecb chunk_id ti\u1ebfp theo ch\u01b0a d\u1ecbch')
    parser.add_argument('--from', type=int, dest='from_id', default=0,
                        help='B\u1eaft \u0111\u1ea7u t\u1eeb chunk_id n\u00e0o (ch\u1ec9 d\u00f9ng v\u1edbi --interactive)')

    args = parser.parse_args()

    if args.progress_dir is None:
        args.progress_dir = PROJECT_ROOT / 'working' / 'progress'

    if args.prepare is not None:
        mode_prepare(args)
    elif args.prepare_batch is not None:
        mode_prepare_batch(args)
    elif args.save is not None:
        mode_save(args)
    elif args.interactive:
        mode_interactive(args)
    elif args.status:
        mode_status(args)
    elif args.next:
        mode_next(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
