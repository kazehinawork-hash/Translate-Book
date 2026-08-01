"""
local_translate.py - Dịch tự động bằng Local AI (LM Studio / OpenAI-compatible)

Thay vì copy/paste từng chunk vào chat AI, script này tự gọi Local AI
(LM Studio) dịch các chunk chưa dịch trong working/progress/<slug>/ và
ghi kết quả dòng-đối-dòng vào progress JSON (mode trilingual hoặc thường).

Yêu cầu:
    1. LM Studio đang chạy và đã bật Local Server (Dev tab -> Start Server)
       Mặc định: http://localhost:1234/v1
    2. Chunk JSON gốc đã có (working/chunks/<slug>/) và skeleton progress
       đã tạo (init_trilingual_skeleton.py) nếu muốn dịch tam ngữ.

Usage:
    # Dịch TẤT CẢ chunk chưa dịch của một cuốn sách
    .venv\\Scripts\\python.exe scripts\\local_translate.py --slug zuo-yi-ge-xxx

    # Dịch từ chunk 5 trở đi, giới hạn 10 chunk trong lượt này
    .venv\\Scripts\\python.exe scripts\\local_translate.py --slug zuo-yi-ge-xxx --from 5 --max-chunks 10

    # Dịch lại 1 chunk cụ thể (kể cả đã dịch)
    .venv\\Scripts\\python.exe scripts\\local_translate.py --slug zuo-yi-ge-xxx --chunk 3 --force

    # Chọn model khác / server khác
    .venv\\Scripts\\python.exe scripts\\local_translate.py --slug zuo-yi-ge-xxx --model qwen2.5-7b-instruct
    .venv\\Scripts\\python.exe scripts\\local_translate.py --slug zuo-yi-ge-xxx --base-url http://localhost:8080/v1

    # Xem trước prompt mà không gọi API
    .venv\\Scripts\\python.exe scripts\\local_translate.py --slug zuo-yi-ge-xxx --dry-run
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402

DEFAULT_BASE_URL = 'http://localhost:1234/v1'
DEFAULT_TIMEOUT = 900
DEFAULT_RETRIES = 3
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 8192


# ============== ĐỌC DỮ LIỆU ==============

def doc_json(file_path: Path):
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


def slug_from_path(progress_dir: Path) -> str:
    return progress_dir.name


# Ký tự Hán tự (CJK Unified Ideographs + mở rộng A)
_HAN_RE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')


def han_ratio(text: str) -> float:
    """Tỷ lệ ký tự Hán trong văn bản (0.0-1.0). Dùng để phát hiện bản dịch
    còn sót chữ Trung (model trả nguyên văn tiếng Trung)."""
    if not text:
        return 0.0
    total = len(text.strip())
    if total == 0:
        return 0.0
    return len(_HAN_RE.findall(text)) / total


def detect_ngao(text: str, original: str, sys_prompt: str) -> str:
    """Phát hiện dấu hiệu model 'ngáo': lặp prompt, lặp vô hạn, copy nguyên
    văn câu gốc. Trả về chuỗi mô tả nếu có vấn đề, ngược lại trả ''. """
    if not text.strip():
        return 'bản dịch rỗng'
    if original.strip():
        ratio = len(text) / max(len(original.strip()), 1)
        if ratio > 4:
            return f'đầu ra quá dài (gấp {ratio:.1f} lần đầu vào) — nghi lặp'
        if ratio < 0.15 and len(original.strip()) > 200:
            return f'đầu ra quá ngắn (chỉ {ratio * 100:.0f}% độ dài đầu vào) — nghi thiếu'
    if 'QUY TẮC BẮT BUỘC' in text:
        return 'đầu ra chứa lại nội dung prompt — nghi lặp'
    for line in original.splitlines():
        s = line.strip()
        if len(s) >= 30 and s in text:
            return 'đầu ra còn giữ nguyên câu gốc tiếng Trung — nghi copy'
    return ''


# ============== GỌI API LM STUDIO ==============

def fetch_models(base_url: str) -> list:
    req = urllib.request.Request(f"{base_url}/models", method='GET')
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return [m.get('id') for m in data.get('data', []) if m.get('id')]


def call_chat(base_url: str, model: str, messages: list,
              temperature: float, max_tokens: int, timeout: int) -> str:
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        method='POST',
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    choice = data['choices'][0]
    content = choice['message'].get('content')
    finish = choice.get('finish_reason', '?')
    if not content:
        raise RuntimeError(f"Model trả về rỗng (finish_reason={finish})")
    return content, finish


def detect_model(base_url: str, model: str | None) -> str:
    if model:
        return model
    models = fetch_models(base_url)
    if not models:
        raise RuntimeError(
            f"Không tìm thấy model nào tại {base_url}. "
            "Mở LM Studio, tải 1 model rồi bật Local Server."
        )
    return models[0]


# ============== PROMPT ==============

def build_system_prompt(source_lang: str, target_lang: str, glossary_text: str,
                        trilingual: bool, prev_ctx: str = '') -> str:
    if trilingual:
        rules = [
            "Đầu vào có N dòng -> đầu ra phải ĐÚNG N dòng. Tuyệt đối không gộp, không tách, không thêm, không bớt dòng.",
            "Dòng thứ i của đầu ra là bản dịch tiếng Việt của dòng thứ i đầu vào (giữ đúng thứ tự).",
            "Dòng heading (bắt đầu bằng #) giữ nguyên ký tự # nhưng dịch phần nội dung.",
            "Giữ NGUYÊN VẸN các dòng: ảnh (![...](...)), dòng trống, dòng chứa số/ISBN/URL/tên file.",
        ]
    else:
        rules = [
            "Đầu vào có N dòng -> đầu ra phải ĐÚNG N dòng. Tuyệt đối không gộp, không tách, không thêm, không bớt dòng.",
            "Dòng thứ i của đầu ra là bản dịch tiếng Việt của dòng thứ i đầu vào (giữ đúng thứ tự).",
            "Dòng heading (bắt đầu bằng #) giữ nguyên ký tự # nhưng dịch phần nội dung.",
            "Giữ NGUYÊN VẸN các dòng: ảnh (![...](...)), dòng trống, dòng chứa số/ISBN/URL/tên file.",
        ]

    if any(k in source_lang.lower() for k in ('trung', 'china', 'chinese')):
        rules.append(
            "Bản dịch phải 100% TIẾNG VIỆT: TUYỆT ĐỐI không được giữ lại bất kỳ "
            "ký tự Hán (Trung Quốc) nào — mọi chữ Hán phải được dịch hết sang tiếng Việt."
        )

    parts = [
        f"Bạn là dịch giả chuyên nghiệp. Dịch văn bản tiếng {source_lang} sang tiếng {target_lang} DÒNG-ĐỐI-DÒNG.",
        "",
        "QUY TẮC BẮT BUỘC:",
    ]
    parts.extend(f"{i}. {r}" for i, r in enumerate(rules, 1))
    parts.extend([
        "Không dịch nội dung bên trong code block, URL hoặc tag.",
        "Dùng ĐÚNG thuật ngữ trong GLOSSARY, không sai lệch.",
        "Không thêm lời dẫn, chú thích, giải thích hay lời bình.",
        "Đầu ra CHỈ gồm bản dịch từng dòng, không có gì khác.",
        "",
        "GLOSSARY (source,target,notes):",
        glossary_text if glossary_text else "(không có glossary)",
    ])
    if prev_ctx:
        parts.extend(["", "NGỮ CẢNH CHUNK TRƯỚC (chỉ để tham khảo, KHÔNG dịch):", prev_ctx])
    return '\n'.join(parts)


def build_user_message(text: str, trilingual: bool) -> str:
    if trilingual:
        return (
            "Dịch từng dòng văn bản dưới đây sang tiếng Việt, "
            "giữ nguyên số dòng (1 dòng gốc = 1 dòng dịch):\n\n" + text
        )
    return (
        "Dịch từng dòng văn bản dưới đây sang tiếng Việt, "
        "giữ nguyên số dòng (1 dòng gốc = 1 dòng dịch):\n\n" + text
    )


# ============== XỬ LÝ KẾT QUẢ ==============

def clean_output(content: str) -> str:
    content = content.strip()
    if content.startswith('```') and content.endswith('```'):
        content = content[3:-3].strip()
    return content


def strip_leading_prefix(text: str) -> str:
    """Bỏ các dòng mở đầu kiểu 'Dưới đây là bản dịch:' nếu model thêm vào."""
    lines = text.splitlines()
    while lines:
        stripped = lines[0].strip().lower()
        if not stripped:
            lines.pop(0)
            continue
        markers = ('dưới đây', 'đây là', 'bản dịch:', 'translation:', 'kết quả')
        if any(stripped.startswith(m) for m in markers):
            lines.pop(0)
            continue
        break
    return '\n'.join(lines)


def normalize_direction(text: str) -> str:
    """Đảm bảo văn bản in theo đúng thứ tự (chống lại hiện tượng trộn RTL của LM Studio)."""
    return text


# ============== LƯU KẾT QUẢ ==============

def save_progress(progress_file: Path, progress_data: dict, translated_text: str,
                  original_text: str, trilingual: bool, warning: str = '') -> None:
    translated_clean = translated_text.strip()
    progress_data['translated_text'] = translated_clean
    progress_data['translated_at'] = datetime.now().isoformat(timespec='seconds')
    progress_data['word_count_translated'] = len(translated_clean.split())
    if warning:
        progress_data['qa_warning'] = warning
    elif 'qa_warning' in progress_data:
        del progress_data['qa_warning']
    progress_file.write_text(json.dumps(progress_data, ensure_ascii=False, indent=2), encoding='utf-8')


# ============== MODE CHÍNH ==============

def collect_chunks(progress_dir: Path, chunks_dir: Path | None):
    import re
    files = sorted(progress_dir.glob('*.json'),
                   key=lambda x: int(re.search(r'\d+', x.name).group() if re.search(r'\d+', x.name) else 0))
    result = []
    chunk_map = {}
    if chunks_dir and chunks_dir.exists():
        for cf in chunks_dir.glob('*.json'):
            data = doc_json(cf)
            if data and 'chunk_id' in data:
                chunk_map[int(data['chunk_id'])] = data
    for f in files:
        data = doc_json(f)
        if data and 'chunk_id' in data:
            result.append((data, f, chunk_map.get(int(data.get('chunk_id')))))
    return result


def is_translated(data: dict) -> bool:
    return bool((data.get('translated_text') or '').strip())


def is_trilingual(data: dict, force_trilingual: str | None) -> bool:
    if force_trilingual == 'trilingual':
        return True
    if force_trilingual == 'bilingual':
        return False
    return data.get('mode') == 'trilingual' and bool((data.get('original_text') or '').strip())


def source_lines(data: dict, trilingual: bool) -> str:
    return data.get('original_text', '') if trilingual else data.get('source_text', '')


def run(args):
    setup_encoding()
    progress_dir = args.progress_dir
    if not progress_dir.exists():
        print(f"[LỖI] Không tìm thấy thư mục progress: {progress_dir}", file=sys.stderr)
        sys.exit(1)

    slug = slug_from_path(progress_dir)
    if args.chunks_dir is None:
        args.chunks_dir = PROJECT_ROOT / 'working' / 'chunks' / slug
    if args.glossary is None:
        args.glossary = PROJECT_ROOT / 'glossary' / f"{slug}.csv"
    glossary_text = doc_glossary(args.glossary)

    entries = collect_chunks(progress_dir, args.chunks_dir)
    if not entries:
        print(f"[LỖI] Không có progress JSON nào trong {progress_dir}", file=sys.stderr)
        sys.exit(1)

    all_ids = [int(d['chunk_id']) for d, _, _ in entries]

    to_translate = []
    for data, f, src in entries:
        cid = int(data['chunk_id'])
        if args.chunk is not None and cid != args.chunk:
            continue
        if cid < args.from_id:
            continue
        if args.force or not is_translated(data):
            to_translate.append((cid, data, f, src))
    to_translate.sort(key=lambda x: x[0])

    if args.max_chunks:
        to_translate = to_translate[:args.max_chunks]

    if not to_translate:
        print("Không có chunk nào cần dịch (tất cả đã xong — dùng --force để dịch lại).")
        return

    if args.dry_run:
        print(f"== DRY-RUN: {len(to_translate)} chunk sẽ được dịch ==")
        for cid, data, f, src in to_translate[:args.max_dry_run]:
            tril = is_trilingual(data, args.trilingual)
            prev_ctx = (src or {}).get('prev_context', '')
            sys_prompt = build_system_prompt(args.source_lang, args.target_lang, glossary_text, tril, prev_ctx)
            user_msg = build_user_message(source_lines(data, tril), tril)
            print(f"\n{'=' * 66}")
            print(f"CHUNK {cid} - {data.get('chapter', '')}")
            print(f"{'=' * 66}")
            print("[SYSTEM PROMPT]")
            print(sys_prompt)
            print("\n[USER MESSAGE]")
            print(user_msg)
        return

    print(f"Base URL : {args.base_url}")
    print(f"Slug     : {slug}")
    print(f"Chunks   : {len(to_translate)} chunk cần dịch")
    print(f"Glossary : {args.glossary} ({'có' if glossary_text else 'không'})")
    print()

    # Kiểm tra kết nối + model
    try:
        model = detect_model(args.base_url, args.model)
    except Exception as e:
        print(f"[LỖI] Không kết nối được LM Studio:\n  {e}\n\n"
              f"💡 Bật LM Studio → tab Dev → Start Server rồi chạy lại.", file=sys.stderr)
        sys.exit(1)
    print(f"Model    : {model}\n")

    n_ok = 0
    n_fail = 0
    for idx, (cid, data, f, src) in enumerate(to_translate, 1):
        tril = is_trilingual(data, args.trilingual)
        original = source_lines(data, tril)
        orig_lines = len(original.splitlines()) if original.strip() else 0
        prev_ctx = (src or {}).get('prev_context', '')
        chapter = (data.get('chapter') or '')[:50]
        print(f"[{idx}/{len(to_translate)}] Chunk {cid}/{data.get('total_chunks', '?')}"
              f" | {chapter} | {orig_lines} dòng")

        sys_prompt = build_system_prompt(args.source_lang, args.target_lang, glossary_text, tril, prev_ctx)

        result_text = ''
        warning = ''
        ok = False
        for attempt in range(1, args.retries + 1):
            warning = ''
            messages = [
                {'role': 'system', 'content': sys_prompt},
                {'role': 'user', 'content': build_user_message(original, tril)},
            ]
            try:
                raw, finish = call_chat(args.base_url, model, messages,
                                        args.temperature, args.max_tokens, args.timeout)
            except Exception as e:
                print(f"    ⚠️  Lần {attempt}/{args.retries} thất bại: {e}")
                if attempt < args.retries:
                    time.sleep(2)
                    continue
                n_fail += 1
                print(f"    ❌ Không dịch được chunk {cid}")
                break

            result_text = normalize_direction(strip_leading_prefix(clean_output(raw)))
            out_lines = len(result_text.splitlines())
            han = han_ratio(result_text)
            ngao = detect_ngao(result_text, original, sys_prompt)

            problems = []
            if orig_lines > 0 and out_lines != orig_lines:
                problems.append(f"số dòng lệch: {out_lines} (gốc {orig_lines})")
            if han > 0.05:
                problems.append(f"còn {han * 100:.0f}% ký tự Hán trong bản dịch")
            if finish == 'length':
                problems.append("bị cắt cụt (đạt max_tokens — model bật thinking/quá dài)")
            if ngao:
                problems.append(ngao)

            if problems:
                warning = "; ".join(problems)
                if attempt < args.retries:
                    print(f"    ⚠️  Lần {attempt}: {warning} — thử lại...")
                    extra_parts = ["\n\nLƯU Ý QUAN TRỌNG:"]
                    if 'số dòng' in warning:
                        extra_parts.append(f"Lần trước bạn trả {out_lines} dòng nhưng cần đúng {orig_lines} dòng. "
                                           f"Hãy trả ĐÚNG {orig_lines} dòng, mỗi dòng là bản dịch của 1 dòng đầu vào.")
                    if 'Hán' in warning:
                        extra_parts.append("Bản dịch phải 100% tiếng Việt, TUYỆT ĐỐI không giữ lại bất kỳ ký tự Hán nào.")
                    if 'quá dài' in warning or 'lặp' in warning or 'giữ nguyên câu gốc' in warning:
                        extra_parts.append("Đừng lặp lại hay copy văn bản. Dịch ngắn gọn từng dòng, đầu ra CHỈ gồm "
                                           "bản dịch tiếng Việt, độ dài tương đương đầu vào, không lặp lại prompt.")
                    if 'cắt cụt' in warning:
                        extra_parts.append("Phải TRẢ LỜI HOÀN CHỈNH đến hết, không dừng giữa chừng, không bỏ dở.")
                    if 'quá ngắn' in warning:
                        extra_parts.append("Bản dịch bị thiếu nhiều dòng — phải dịch ĐỦ toàn bộ văn bản đầu vào.")
                    sys_prompt += '\n'.join(extra_parts)
                    time.sleep(2)
                    continue
                print(f"    ⚠️  Lần {attempt}: {warning}")
                if any(k in warning for k in ('Hán', 'lặp', 'quá dài', 'giữ nguyên câu gốc', 'cắt cụt', 'rỗng', 'quá ngắn')):
                    print(f"    ❌ Bỏ qua chunk {cid} — bản dịch lỗi, không ghi đè bản cũ.")
                    n_fail += 1
                    ok = False
                    break
            ok = True
            break

        if not ok:
            continue

        save_progress(f, data, result_text, original, tril, warning=warning)
        if warning:
            n_fail += 1
            print(f"    ⚠️  Đã lưu (có cảnh báo): {warning} — {f.name}")
        else:
            n_ok += 1
            print(f"    ✅ Đã lưu: {f.name}")

    print(f"\nHoàn tất: {n_ok} chunk OK, {n_fail} chunk có vấn đề.")


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Dịch tự động bằng Local AI (LM Studio / OpenAI-compatible API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--slug', type=str, help='Tên cuốn sách (tự suy working/progress/<slug>/)')
    parser.add_argument('--progress-dir', type=Path,
                        help='Thư mục chứa progress JSON (ưu tiên hơn --slug)')
    parser.add_argument('--chunks-dir', type=Path,
                        help='Thư mục chunk gốc (để lấy prev/next context). Mặc định: working/chunks/<slug>/')
    parser.add_argument('--glossary', type=Path,
                        help='File glossary CSV. Mặc định: glossary/<slug>.csv')
    parser.add_argument('--base-url', type=str, default=DEFAULT_BASE_URL,
                        help=f'Base URL OpenAI-compatible (mặc định: {DEFAULT_BASE_URL})')
    parser.add_argument('--model', type=str, default=None,
                        help='Tên model trong LM Studio. Mặc định: model đầu tiên đang load')
    parser.add_argument('--chunk', type=int, default=None,
                        help='Chỉ dịch 1 chunk có id này')
    parser.add_argument('--from', type=int, dest='from_id', default=0,
                        help='Bắt đầu từ chunk_id (mặc định 0)')
    parser.add_argument('--max-chunks', type=int, default=None,
                        help='Giới hạn số chunk dịch trong 1 lượt chạy')
    parser.add_argument('--force', action='store_true',
                        help='Dịch lại cả chunk đã có bản dịch')
    parser.add_argument('--source-lang', type=str, default='Trung (Chinese)',
                        help='Ngôn ngữ nguồn (mặc định: Trung)')
    parser.add_argument('--target-lang', type=str, default='Việt (Vietnamese)',
                        help='Ngôn ngữ đích (mặc định: Việt)')
    parser.add_argument('--trilingual', type=str, choices=['trilingual', 'bilingual'], default=None,
                        help='Ép chế độ tam ngữ / song ngữ. Mặc định: tự nhận theo mode trong progress JSON')
    parser.add_argument('--temperature', type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument('--max-tokens', type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT,
                        help=f'Timeout mỗi request (giây, mặc định {DEFAULT_TIMEOUT})')
    parser.add_argument('--retries', type=int, default=DEFAULT_RETRIES,
                        help=f'Số lần thử lại khi lỗi (mặc định {DEFAULT_RETRIES})')
    parser.add_argument('--dry-run', action='store_true',
                        help='Chỉ in prompt, không gọi API')
    parser.add_argument('--max-dry-run', type=int, default=2,
                        help='Số chunk in trong --dry-run (mặc định 2)')

    args = parser.parse_args()

    if args.progress_dir is None:
        if not args.slug:
            parser.error("Cần cung cấp --slug hoặc --progress-dir")
        args.progress_dir = PROJECT_ROOT / 'working' / 'progress' / args.slug

    run(args)


if __name__ == '__main__':
    main()
