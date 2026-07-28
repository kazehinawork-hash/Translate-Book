"""
run_pipeline.py - Orchestrator chạy toàn bộ pipeline cho 1 cuốn sách

Pipeline:
   1. Extract     - Trích xuất (MinerU / EPUB)
   2. QC          - QC sau trích xuất
   3. Detect Lang - Phát hiện ngôn ngữ
   4. OpenCC      - (ZH) Phồn → Giản thể nếu cần
   5. Chunk       - Chia chunk
   6. Glossary    - Tạo prompt glossary → Agent review + tạo CSV
   7. Translate   - Dịch từng chunk (Agent + translate_helper.py)
   8. QA          - Kiểm tra chất lượng (glossary_qa.py)
   9. Merge       - Gộp chunk → file hoàn chỉnh

Dùng --from-step để chạy lại từ bước bất kỳ.
--auto bỏ qua các bước cần can thiệp thủ công (glossary, translate).

Ví dụ:
    # Chạy toàn bộ pipeline
    python scripts/run_pipeline.py ^
        --input "input\ten-sach.pdf" ^
        --book "Tên Sách" ^
        --lang auto

    # Chỉ extract + chunk
    python scripts/run_pipeline.py ^
        --input "input\ten-sach.pdf" ^
        --book "Tên Sách" ^
        --to-step 5

    # Gộp chunk đã dịch (bắt đầu từ bước 9)
    python scripts/run_pipeline.py ^
        --book "ten-sach" ^
        --from-step 9
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT  # noqa: E402

SCRIPT_DIR = Path(__file__).parent


def run_script(script_name: str, args: list[str], step_label: str = '') -> bool:
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        print(f"  [L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y script: {script_path}", file=sys.stderr)
        return False
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n{'='*60}")
    if step_label:
        print(f"  B\u01b0\u1edbc: {step_label}")
    print(f"  L\u1ec7nh: python {script_name} {' '.join(args)}")
    print('='*60)
    start = time.time()
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - start
        print(f"  \u2705 Ho\u00e0n th\u00e0nh ({elapsed:.1f}s)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [L\u1ed6I] Th\u1ea5t b\u1ea1i v\u1edbi exit code {e.returncode}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"  [L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y Python", file=sys.stderr)
        return False


def print_step(step: int, label: str, description: str):
    print(f"\n{'='*60}")
    print(f"  B\u01b0\u1edbc {step}: {label}")
    print(f"  {'='*40}")
    print(f"  {description}")
    print(f"{'='*60}")


# ─── Các bước ─────────────────────────────────────────────────────────────

def step_extract(args, slug: str) -> Path | None:
    raw_md = PROJECT_ROOT / "working" / "extracted" / slug / "raw.md"
    raw_md.parent.mkdir(parents=True, exist_ok=True)

    if not args.input:
        print("  \u26a0\ufe0f B\u1ecf qua: kh\u00f4ng c\u00f3 --input")
        return raw_md if raw_md.exists() else None

    if args.input.suffix.lower() == '.epub':
        ok = run_script('epub_extract.py', [
            '--input', str(args.input),
            '--output', str(raw_md),
        ], '1. Extract EPUB')
    else:
        ok = run_script('mineru_extract.py', [
            '--input', str(args.input),
            '--output', str(raw_md),
            '--lang', args.lang if args.lang != 'auto' else 'en',
        ], '1. Extract PDF')
    return raw_md if ok else None


def step_qc(slug: str, lang: str) -> bool:
    raw_md = PROJECT_ROOT / "working" / "extracted" / slug / "raw.md"
    if not raw_md.exists():
        print("  \u26a0\ufe0f Kh\u00f4ng t\u00ecm th\u1ea5y raw.md, b\u1ecf qua QC")
        return True
    qa_report = PROJECT_ROOT / "working" / "qa" / slug / "extract-qc.md"
    return run_script('post_extract_qc.py', [
        '--input', str(raw_md),
        '--report', str(qa_report),
        '--lang', lang,
    ], '2. QC sau trích xu\u1ea5t')


def step_detect_lang(slug: str, lang: str) -> str:
    if lang != 'auto':
        return lang
    raw_md = PROJECT_ROOT / "working" / "extracted" / slug / "raw.md"
    if not raw_md.exists():
        print("  \u26a0\ufe0f Kh\u00f4ng t\u00ecm th\u1ea5y raw.md, gi\u1eef nguy\u00ean ng\u00f4n ng\u1eef")
        return lang
    print_step(3, 'Detect Language', 'Ph\u00e1t hi\u1ec7n ng\u00f4n ng\u1eef t\u1ef1 \u0111\u1ed9ng')
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / 'detect_language.py'), str(raw_md), '--quiet'],
        capture_output=True, text=True
    )
    detected = result.stdout.strip() if result.returncode == 0 else 'unknown'
    print(f"  Ng\u00f4n ng\u1eef ph\u00e1t hi\u1ec7n: {detected}")
    return detected


def step_opencc(slug: str, ngon_ngu: str) -> Path:
    if ngon_ngu not in ('zh-Hant',):
        raw_md = PROJECT_ROOT / "working" / "extracted" / slug / "raw.md"
        return raw_md
    raw_md = PROJECT_ROOT / "working" / "extracted" / slug / "raw.md"
    raw_hans = raw_md.parent / 'raw-hans.md'
    print_step(4, 'OpenCC', 'Chuy\u1ec3n Ph\u1ed3n th\u1ec3 \u2192 Gi\u1ea3n th\u1ec3')
    if run_script('opencc_normalize.py', [
        '--input', str(raw_md),
        '--output', str(raw_hans),
        '--config', 't2s',
    ], '4. OpenCC'):
        return raw_hans
    return raw_md


def step_chunk(slug: str, lang: str, strategy: str = 'smart') -> bool:
    extracted_dir = PROJECT_ROOT / "working" / "extracted" / slug
    chunks_dir = PROJECT_ROOT / "working" / "chunks" / slug

    chunk_input = extracted_dir / 'raw.md'
    alt_input = extracted_dir / 'raw-hans.md'
    if alt_input.exists():
        chunk_input = alt_input
    if not chunk_input.exists():
        print(f"  \u26a0\ufe0f Kh\u00f4ng t\u00ecm th\u1ea5y file extracted. B\u1ecf qua chunk.")
        return False

    if lang.startswith('zh'):
        min_chars, max_chars = 1500, 3000
    else:
        min_chars, max_chars = 3000, 8000

    cmd_args = [
        '--input', str(chunk_input),
        '--output-dir', str(chunks_dir),
        '--lang', 'zh' if lang.startswith('zh') else 'en',
    ]
    if strategy != 'smart':
        cmd_args.extend(['--strategy', strategy])
    else:
        cmd_args.extend(['--min-chars', str(min_chars), '--max-chars', str(max_chars),
                         '--overlap-chars', '200', '--respect-headings'])

    return run_script('chunk_text.py', cmd_args, '5. Chia chunk')


def step_glossary(slug: str, auto: bool) -> bool:
    chunks_dir = PROJECT_ROOT / "working" / "chunks" / slug
    glossary_file = PROJECT_ROOT / 'glossary' / f'{slug}.csv'

    if auto:
        print_step(6, 'Gen Glossary', '\u26a0\ufe0f Auto mode: b\u1ecf qua (Agent c\u1ea7n review)')
        return True

    if not chunks_dir.exists():
        extracted_dir = PROJECT_ROOT / "working" / "extracted" / slug
        if not extracted_dir.exists():
            print("  \u26a0\ufe0f Kh\u00f4ng t\u00ecm th\u1ea5y source text. B\u1ecf qua.")
            return True
        run_script('generate_glossary.py', [
            '--source', str(extracted_dir / 'raw.md'),
            '--book-name', slug,
        ], '6. Generate glossary prompt')
    else:
        run_script('generate_glossary.py', [
            '--source-dir', str(chunks_dir),
            '--book-name', slug,
        ], '6. Generate glossary prompt')

    print(f"\n  {'='*40}")
    print(f"   Ti\u1ebfp theo: y\u00eau c\u1ea7u Agent t\u1ea1o {glossary_file}")
    print(f"   D\u1ef1a tr\u00ean prompt trong working/glossary/")
    print(f"  {'='*40}")
    return True


def step_translate_print(slug: str, auto: bool):
    chunks_dir = PROJECT_ROOT / "working" / "chunks" / slug
    progress_dir = PROJECT_ROOT / "working" / "progress" / slug
    glossary_file = PROJECT_ROOT / 'glossary' / f'{slug}.csv'

    if auto:
        print_step(7, 'Translate (Agent)', '\u26a0\ufe0f Auto mode: b\u1ecf qua')
        return

    print_step(7, 'Translate (Agent)',
               'D\u1ecbch t\u1eebng chunk b\u1eb1ng Agent!\n\n'
               f'  C\u00e1ch d\u00f9ng translate_helper.py:\n\n'
               f'  1. Xem ti\u1ebfn tr\u00ecnh:\n'
               f'     python scripts/translate_helper.py --status --progress-dir {progress_dir}\n\n'
               f'  2. Xem chunk ti\u1ebfp theo:\n'
               f'     python scripts/translate_helper.py --next --chunks-dir {chunks_dir} --progress-dir {progress_dir}\n\n'
               f'  3. Chu\u1ea9n b\u1ecb prompt:\n'
               f'     python scripts/translate_helper.py --prepare 0 --chunks-dir {chunks_dir} --glossary {glossary_file}\n\n'
               f'  4. L\u01b0u b\u1ea3n d\u1ecbch:\n'
               f'     python scripts/translate_helper.py --save 0 --progress-dir {progress_dir} --chunks-dir {chunks_dir}')


def step_qa(slug: str, lang: str, auto: bool) -> bool:
    progress_dir = PROJECT_ROOT / "working" / "progress" / slug
    glossary_file = PROJECT_ROOT / 'glossary' / f'{slug}.csv'

    if not progress_dir.exists() or not glossary_file.exists():
        print_step(8, 'QA', '\u26a0\ufe0f B\u1ecf qua: thi\u1ebfu progress_dir ho\u1eb7c glossary')
        return True

    print_step(8, 'QA', 'Ki\u1ec3m tra ch\u1ea5t l\u01b0\u1ee3ng d\u1ecbch')
    qa_dir = PROJECT_ROOT / 'working' / 'qa' / slug
    qa_dir.mkdir(parents=True, exist_ok=True)
    qa_ok = True

    chunk_files = sorted(progress_dir.glob('*.json'))
    for cf in chunk_files:
        try:
            data = json.loads(cf.read_text(encoding='utf-8-sig'))
            cid = data.get('chunk_id', '?')
            translated = data.get('translated_text', '')
            if not translated.strip():
                print(f"  \u26a0\ufe0f Chunk {cid} ch\u01b0a d\u1ecbch, b\u1ecf qua QA")
                continue
            source_text = data.get('source_text', '')
            src_tmp = qa_dir / f'_qa_src_{cid}.md'
            tgt_tmp = qa_dir / f'_qa_tgt_{cid}.md'
            src_tmp.write_text(source_text or '', encoding='utf-8')
            tgt_tmp.write_text(translated, encoding='utf-8')
            report_file = qa_dir / f'chunk-{cid}-qa.md'
            ok = run_script('glossary_qa.py', [
                '--source', str(src_tmp),
                '--translation', str(tgt_tmp),
                '--glossary', str(glossary_file),
                '--lang', lang,
                '--report', str(report_file),
            ], f'8. QA chunk {cid}')
            if not ok:
                qa_ok = False
        except Exception as e:
            print(f"  \u26a0\ufe0f L\u1ed7i QA chunk {cf.name}: {e}")

    if qa_ok:
        print(f"\n  \u2705 QA ho\u00e0n t\u1ea5t cho {len(chunk_files)} chunk")
    else:
        print(f"\n  \u26a0\ufe0f QA c\u00f3 l\u1ed7i, ki\u1ec3m tra b\u00e1o c\u00e1o trong {qa_dir}")
    return qa_ok


def step_merge(slug: str, force: bool, fmt: str = 'bilingual') -> bool:
    progress_dir = PROJECT_ROOT / "working" / "progress" / slug
    if not progress_dir.exists():
        print_step(9, 'Merge', '\u26a0\ufe0f B\u1ecf qua: progress_dir ch\u01b0a t\u1ed3n t\u1ea1i')
        return True

    print_step(9, 'Merge', 'G\u1ed9p t\u1ea5t c\u1ea3 chunk \u0111\u00e3 d\u1ecbch th\u00e0nh file ho\u00e0n ch\u1ec9nh')
    merge_args = [
        '--progress-dir', str(progress_dir),
        '--book-name', slug,
        '--format', fmt,
    ]
    if force:
        merge_args.append('--force')
    return run_script('merge_chunks.py', merge_args, '9. Merge chunks')


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Orchestrator ch\u1ea1y to\u00e0n b\u1ed9 pipeline d\u1ecbch s\u00e1ch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input', type=Path, help='File \u0111\u1ea7u v\u00e0o (PDF/EPUB/DOCX/\u1ea3nh)')
    parser.add_argument('--book', type=str, required=True,
                        help='T\u00ean s\u00e1ch (d\u00f9ng cho slug v\u00e0 output)')
    parser.add_argument('--slug', type=str, help='Slug (m\u1eb7c \u0111\u1ecbnh: t\u1eeb --book)')
    parser.add_argument('--lang', type=str, default='auto', help='Ng\u00f4n ng\u1eef (en/zh/auto)')
    parser.add_argument('--from-step', type=int, default=1, choices=range(1, 10),
                        help='B\u1eaft \u0111\u1ea7u t\u1eeb b\u01b0\u1edbc n\u00e0o (1-9, m\u1eb7c \u0111\u1ecbnh: 1)')
    parser.add_argument('--to-step', type=int, default=9, choices=range(1, 10),
                        help='K\u1ebft th\u00fac \u1edf b\u01b0\u1edbc n\u00e0o (1-9, m\u1eb7c \u0111\u1ecbnh: 9)')
    parser.add_argument('--auto', action='store_true',
                        help='Ch\u1ebf \u0111\u1ed9 auto: ch\u1ec9 ch\u1ea1y script t\u1ef1 \u0111\u1ed9ng, b\u1ecf qua b\u01b0\u1edbc c\u1ea7n Agent')
    parser.add_argument('--skip-qc', action='store_true', help='B\u1ecf qua QC sau tr\u00edch xu\u1ea5t')
    parser.add_argument('--force', action='store_true',
                        help='Ghi \u0111\u00e8 m\u00e0 kh\u00f4ng h\u1ecfi (cho merge)')
    parser.add_argument('--format', type=str, choices=['bilingual', 'trilingual'], default='bilingual',
                        help='\u0110\u1ecbnh d\u1ea1ng output merge (m\u1eb7c \u0111\u1ecbnh: bilingual)')

    args = parser.parse_args()
    slug = args.slug or args.book.lower().replace(' ', '-')
    lang_code = 'en' if args.lang == 'en' else 'zh'

    print(f"\n{'#'*60}")
    print(f"# PIPELINE: {args.book} ({slug})")
    print(f"# T\u1eeb b\u01b0\u1edbc {args.from_step} \u0111\u1ebfn b\u01b0\u1edbc {args.to_step}"
          + (" (auto mode)" if args.auto else ""))
    print(f"{'#'*60}\n")

    # Validate --input cho steps 1
    if args.from_step <= 1 and not args.input:
        parser.error("--input l\u00e0 b\u1eaft bu\u1ed9c khi b\u1eaft \u0111\u1ea7u t\u1eeb b\u01b0\u1edbc 1")

    # === STEP 1: EXTRACT ===
    raw_md = None
    if args.from_step <= 1 and args.to_step >= 1:
        raw_md = step_extract(args, slug)
        if not raw_md or not raw_md.exists():
            print("[L\u1ed6I] Tr\u00edch xu\u1ea5t th\u1ea5t b\u1ea1i. D\u1eebng pipeline.", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 1 (Extract)")

    # === STEP 2: QC ===
    if args.from_step <= 2 and args.to_step >= 2 and not args.skip_qc:
        lang_for_qc = args.lang if args.lang != 'auto' else 'en'
        if not step_qc(slug, lang_for_qc):
            print("[C\u1ea2NH B\u00c1O] QC c\u00f3 v\u1ea5n \u0111\u1ec1 nh\u01b0ng ti\u1ebfp t\u1ee5c...")
    elif args.from_step > 2 or args.to_step < 2:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 2 (QC)")

    # === STEP 3: DETECT LANGUAGE ===
    ngon_ngu = args.lang
    if args.from_step <= 3 and args.to_step >= 3:
        ngon_ngu = step_detect_lang(slug, args.lang)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 3 (Detect Lang)")

    # === STEP 4: OPENCC ===
    input_md = None
    if args.from_step <= 4 and args.to_step >= 4:
        input_md = step_opencc(slug, ngon_ngu)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 4 (OpenCC)")

    # === STEP 5: CHUNK ===
    if args.from_step <= 5 and args.to_step >= 5:
        if not step_chunk(slug, ngon_ngu):
            print("[L\u1ed6I] Chia chunk th\u1ea5t b\u1ea1i.", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 5 (Chunk)")

    # === STEP 6: GLOSSARY ===
    if args.from_step <= 6 and args.to_step >= 6:
        step_glossary(slug, args.auto)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 6 (Glossary)")

    # === STEP 7: TRANSLATE ===
    if args.from_step <= 7 and args.to_step >= 7:
        step_translate_print(slug, args.auto)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 7 (Translate)")

    # === STEP 8: QA ===
    if args.from_step <= 8 and args.to_step >= 8:
        step_qa(slug, lang_code, args.auto)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 8 (QA)")

    # === STEP 9: MERGE ===
    if args.from_step <= 9 and args.to_step >= 9:
        step_merge(slug, args.force, args.format)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 9 (Merge)")

    print(f"\n{'#'*60}")
    print(f"# PIPELINE HO\u00c0N TH\u00c0NH: {args.book}")
    print(f"{'#'*60}")
    if raw_md:
        print(f"  Raw: {raw_md}")
    if input_md and input_md != raw_md:
        print(f"  Chu\u1ea9n h\u00f3a: {input_md}")
    print(f"  Slug: {slug}")


if __name__ == '__main__':
    main()
