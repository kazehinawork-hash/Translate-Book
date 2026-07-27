"""
translate_helper.py - Script hỗ trợ Agent dịch

Script này KHÔNG gọi API. Nó chuẩn bị dữ liệu để Agent dịch dễ dàng hơn.

Modes:
  --prepare {chunk_id}      : Đọc chunk JSON + glossary -> in ra prompt đã điền sẵn
  --prepare-batch {start} {end}: Chuẩn bị nhiều chunk cùng lúc
  --save {chunk_id}          : Nhận input từ stdin -> lưu vào working/progress/chunk_{id}.json
  --status                   : Hiển thị tiến trình (chunk nào đã dịch, chunk nào chưa)
  --next                     : Hiển thị chunk_id tiếp theo chưa dịch

Ví dụ:
    python scripts/translate_helper.py ^
        --prepare 0 ^
        --chunks-dir "working\chunks\mybook" ^
        --glossary "glossary\mybook.csv" ^
        --source-lang English ^
        --target-lang Vietnamese

    python scripts/translate_helper.py --save 0 --progress-dir "working\progress\mybook"

    python scripts/translate_helper.py --status --progress-dir "working\progress\mybook"

    python scripts/translate_helper.py --next --progress-dir "working\progress\mybook"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT


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
    try:
        for enc in ('utf-8-sig', 'utf-8', 'gbk'):
            try:
                return csv_path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
    except Exception:
        return ''
    return ''


def build_prompt(chunk_data: dict, glossary_text: str, source_lang: str, target_lang: str) -> str:
    """Build the full prompt from template and data."""
    chunk_id = chunk_data.get('chunk_id', '?')
    total = chunk_data.get('total_chunks', '?')
    chapter = chunk_data.get('chapter', '')
    text = chunk_data.get('text', '')
    prev_ctx = chunk_data.get('prev_context', '')
    next_ctx = chunk_data.get('next_context', '')

    prompt = f"""# TRANSLATION INSTRUCTIONS

You are a professional translator. Your task is to translate the chunk below from {source_lang} to {target_lang}.

## RULES
1. Preserve ALL formatting: paragraphs, headings, lists, emphasis, line breaks
2. Keep proper nouns, brand names in original unless they have widely accepted Vietnamese translations
3. Use the GLOSSARY below — NEVER deviate from these translations
4. Do NOT add explanations, notes, or translator comments
5. Do NOT translate content inside code blocks, URLs, or placeholder tags
6. Maintain the original tone and style
7. Output ONLY the translated text

## GLOSSARY
{glossary_text if glossary_text else '(No glossary provided)'}

## PREVIOUS CHUNK CONTEXT (for reference only, do not re-translate)
{prev_ctx if prev_ctx else '(First chunk - no previous context)'}

## CHUNK TO TRANSLATE (Chunk {chunk_id}/{total}, {chapter})
{text}

## NEXT CHUNK CONTEXT (for reference only, do not re-translate)
{next_ctx if next_ctx else '(Last chunk - no next context)'}"""
    return prompt


def mode_prepare(args):
    """Prepare a single chunk prompt and print to stdout."""
    chunks_dir = args.chunks_dir
    if not chunks_dir.exists():
        print(f"[L\u1ed6I] Th\u01b0 m\u1ee5c chunks kh\u00f4ng t\u1ed3n t\u1ea1i: {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    chunk_file = chunks_dir / f"chunk-{args.prepare:03d}.json"
    if not chunk_file.exists():
        chunk_file = chunks_dir / f"chunk_{args.prepare:03d}.json"
    if not chunk_file.exists():
        # Try glob
        matches = list(chunks_dir.glob(f"*{args.prepare}*.json"))
        if not matches:
            print(f"[L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y chunk {args.prepare} trong {chunks_dir}", file=sys.stderr)
            sys.exit(1)
        chunk_file = matches[0]

    data = doc_json(chunk_file)
    if data is None:
        print(f"[L\u1ed6I] Kh\u00f4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c {chunk_file}", file=sys.stderr)
        sys.exit(1)

    glossary_text = doc_glossary(args.glossary) if args.glossary else ''
    prompt = build_prompt(data, glossary_text, args.source_lang, args.target_lang)
    print(prompt)


def mode_prepare_batch(args):
    """Prepare multiple chunks in sequence."""
    chunks_dir = args.chunks_dir
    if not chunks_dir.exists():
        print(f"[L\u1ed6I] Th\u01b0 m\u1ee5c chunks kh\u00f4ng t\u1ed3n t\u1ea1i: {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    start = args.prepare_batch[0]
    end = args.prepare_batch[1]

    glossary_text = doc_glossary(args.glossary) if args.glossary else ''

    for cid in range(start, end + 1):
        chunk_file = chunks_dir / f"chunk-{cid:03d}.json"
        if not chunk_file.exists():
            chunk_file = chunks_dir / f"chunk_{cid:03d}.json"
        if not chunk_file.exists():
            print(f"\n{'='*60}")
            print(f"CHUNK {cid}: File not found, skipping")
            continue

        data = doc_json(chunk_file)
        if data is None:
            print(f"\n{'='*60}")
            print(f"CHUNK {cid}: Cannot read, skipping")
            continue

        prompt = build_prompt(data, glossary_text, args.source_lang, args.target_lang)
        print(f"\n{'='*60}")
        print(f"CHUNK {cid}/{data.get('total_chunks', '?')} - {data.get('chapter', '')}")
        print('=' * 60)
        print(prompt)


def mode_save(args):
    """Read translation from stdin and save to progress file."""
    progress_dir = args.progress_dir
    if not progress_dir.exists():
        progress_dir.mkdir(parents=True, exist_ok=True)

    chunk_id = args.save

    # Find the original chunk file to get metadata
    chunks_dir = args.chunks_dir
    source_data = {}
    if chunks_dir and chunks_dir.exists():
        for pattern in [f"chunk-{chunk_id:03d}.json", f"chunk_{chunk_id:03d}.json"]:
            cf = chunks_dir / pattern
            if cf.exists():
                d = doc_json(cf)
                if d:
                    source_data = {
                        'chunk_id': d.get('chunk_id', chunk_id),
                        'total_chunks': d.get('total_chunks', 0),
                        'chapter': d.get('chapter', ''),
                        'source_text': d.get('text', ''),
                        'word_count_source': d.get('word_count', 0),
                    }
                break

    # Read translated text from stdin
    print("Paste translated text, then press Ctrl+Z then Enter (Windows) or Ctrl+D (Unix):", file=sys.stderr)
    try:
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass
    translated_lines = sys.stdin.buffer.read().decode('utf-8', errors='replace')

    now = datetime.now().isoformat(timespec='seconds')

    progress_data = {
        'chunk_id': source_data.get('chunk_id', chunk_id),
        'total_chunks': source_data.get('total_chunks', 0),
        'chapter': source_data.get('chapter', ''),
        'source_text': source_data.get('source_text', ''),
        'translated_text': translated_lines.strip(),
        'translated_at': now,
        'word_count_source': source_data.get('word_count_source', 0),
        'word_count_translated': len(translated_lines.split()),
    }

    out_file = progress_dir / f"chunk_{chunk_id:03d}.json"
    out_file.write_text(json.dumps(progress_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n\u2705 \u0110\u00e3 l\u01b0u: {out_file} ({progress_data['word_count_translated']} t\u1eeb)", file=sys.stderr)


def mode_status(args):
    """Show translation progress."""
    progress_dir = args.progress_dir
    if not progress_dir.exists():
        print(f"Th\u01b0 m\u1ee5c progress ch\u01b0a t\u1ed3n t\u1ea1i: {progress_dir}")
        print(f"Ti\u1ebfn tr\u00ecnh: 0/0 (0%)")
        return

    json_files = sorted(progress_dir.glob('*.json'))
    if not json_files:
        print(f"Kh\u00f4ng c\u00f3 chunk n\u00e0o trong {progress_dir}")
        print(f"Ti\u1ebfn tr\u00ecnh: 0/0 (0%)")
        return

    chunks = []
    for f in json_files:
        data = doc_json(f)
        if data and 'chunk_id' in data:
            chunks.append(data)

    chunks.sort(key=lambda c: int(c.get('chunk_id', 999999)))

    if not chunks:
        print(f"Kh\u00f4ng c\u00f3 d\u1eef li\u1ec7u chunk h\u1ee3p l\u1ec7 trong {progress_dir}")
        return

    total = max(c.get('total_chunks', 0) for c in chunks) or len(chunks)
    translated = sum(1 for c in chunks if c.get('translated_text', '').strip())

    print(f"Ti\u1ebfn tr\u00ecnh: {translated}/{total} ({translated * 100 // max(total, 1)}%)\n")

    for c in chunks:
        cid = c.get('chunk_id', '?')
        chapter = c.get('chapter', '')
        has_translation = bool(c.get('translated_text', '').strip())
        status = '\u2705' if has_translation else '\u274c'
        ts = c.get('translated_at', '')[:10] if has_translation else ''
        ch = f" - {chapter[:40]}" if chapter else ''
        print(f"  {status} Chunk {cid}{ch} {ts}")


def mode_next(args):
    """Show next untranslated chunk."""
    progress_dir = args.progress_dir
    chunks_dir = args.chunks_dir

    translated_ids = set()
    if progress_dir.exists():
        for f in progress_dir.glob('*.json'):
            data = doc_json(f)
            if data and data.get('translated_text', '').strip():
                translated_ids.add(int(data.get('chunk_id', -1)))

    if not chunks_dir or not chunks_dir.exists():
        print("[L\u1ed6I] C\u1ea7n --chunks-dir \u0111\u1ec3 x\u00e1c \u0111\u1ecbnh t\u1ed5ng s\u1ed1 chunk", file=sys.stderr)
        sys.exit(1)

    all_chunks = sorted(chunks_dir.glob('*.json'))
    for f in all_chunks:
        data = doc_json(f)
        if data is None:
            continue
        cid = int(data.get('chunk_id', -1))
        if cid >= 0 and cid not in translated_ids:
            print(f"{cid}")
            print(f"chapter: {data.get('chapter', '')}", file=sys.stderr)
            print(f"file: {f.name}", file=sys.stderr)
            return

    print("T\u1ea5t c\u1ea3 chunk \u0111\u00e3 d\u1ecbch xong!")
    sys.exit(0)


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

    # Modes
    parser.add_argument('--prepare', type=int,
                        help='Chu\u1ea9n b\u1ecb prompt cho chunk_id')
    parser.add_argument('--prepare-batch', type=int, nargs=2, metavar=('START', 'END'),
                        help='Chu\u1ea9n b\u1ecb prompt cho nhi\u1ec1u chunk')
    parser.add_argument('--save', type=int,
                        help='Nh\u1eadn b\u1ea3n d\u1ecbch t\u1eeb stdin v\u00e0 l\u01b0u v\u00e0o progress')
    parser.add_argument('--status', action='store_true',
                        help='Hi\u1ec3n th\u1ecb ti\u1ebfn tr\u00ecnh d\u1ecbch')
    parser.add_argument('--next', action='store_true',
                        help='Hi\u1ec3n th\u1ecb chunk_id ti\u1ebfp theo ch\u01b0a d\u1ecbch')

    args = parser.parse_args()

    # Default progress dir
    if args.progress_dir is None:
        args.progress_dir = PROJECT_ROOT / 'working' / 'progress'

    if args.prepare is not None:
        mode_prepare(args)
    elif args.prepare_batch is not None:
        mode_prepare_batch(args)
    elif args.save is not None:
        mode_save(args)
    elif args.status:
        mode_status(args)
    elif args.next:
        mode_next(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
