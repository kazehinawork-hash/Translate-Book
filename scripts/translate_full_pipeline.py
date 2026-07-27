"""
translate_full_pipeline.py - Orchestrator chạy toàn bộ pipeline (trừ bước dịch)

Pipeline:
  1. Extract:     ✅ Auto (chạy mineru_extract.py hoặc epub_extract.py)
  2. Chunk:       ✅ Auto (chạy chunk_text.py)
  3. Gen Glossary: ⚠️ Tạo prompt -> Agent cần review và tạo CSV
  4. Translate:    🤖 Agent dịch từng chunk (dùng translate_helper.py)
  5. QA:          ✅ Auto (chạy glossary_qa.py)
  6. Merge:       ✅ Auto (chạy merge_chunks.py)

Ví dụ:
    python scripts/translate_full_pipeline.py ^
        --book "MyBook" ^
        --source-lang English ^
        --target-lang Vietnamese

    python scripts/translate_full_pipeline.py ^
        --book "MyBook" ^
        --input "input/mybook.pdf" ^
        --slug "mybook"

    python scripts/translate_full_pipeline.py ^
        --book "MyBook" ^
        --from-step 3 ^
        --auto

    python scripts/translate_full_pipeline.py ^
        --book "MyBook" ^
        --from-step 6
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding, PROJECT_ROOT

SCRIPT_DIR = Path(__file__).parent


def run_script(script_name: str, args: list[str], step_label: str) -> bool:
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        print(f"  [L\u1ed6I] Kh\u00f4ng t\u00ecm th\u1ea5y script: {script_path}", file=sys.stderr)
        return False
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n{'='*60}")
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


def print_agent_step(step: int, label: str, description: str):
    print(f"\n{'='*60}")
    print(f"  B\u01b0\u1edbc {step}: {label}")
    print(f"  {'='*40}")
    print(f"  {description}")
    print(f"{'='*60}")


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(
        description="Ch\u1ea1y to\u00e0n b\u1ed9 pipeline d\u1ecbch (tr\u1eeb b\u01b0\u1edbc d\u1ecbch do Agent l\u00e0m)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--book', type=str, required=True,
                        help='T\u00ean s\u00e1ch (d\u00f9ng cho t\u00ean file output)')
    parser.add_argument('--slug', type=str,
                        help='Slug s\u00e1ch (m\u1eb7c \u0111\u1ecbnh: t\u1eeb --book, lowercase, thay space b\u1eb1ng -)')
    parser.add_argument('--input', type=Path,
                        help='File \u0111\u1ea7u v\u00e0o (PDF/EPUB)')
    parser.add_argument('--source-lang', type=str, default='English',
                        help='Ng\u00f4n ng\u1eef ngu\u1ed3n (m\u1eb7c \u0111\u1ecbnh: English)')
    parser.add_argument('--target-lang', type=str, default='Vietnamese',
                        help='Ng\u00f4n ng\u1eef \u0111\u00edch (m\u1eb7c \u0111\u1ecbnh: Vietnamese)')
    parser.add_argument('--from-step', type=int, default=1, choices=range(1, 7),
                        help='B\u1eaft \u0111\u1ea7u t\u1eeb b\u01b0\u1edbc n\u00e0o (1-6, m\u1eb7c \u0111\u1ecbnh: 1)')
    parser.add_argument('--auto', action='store_true',
                        help='Ch\u1ebf \u0111\u1ed9 auto: skip c\u00e1c b\u01b0\u1edbc c\u1ea7n Agent, ch\u1ec9 ch\u1ea1y script t\u1ef1 \u0111\u1ed9ng')
    parser.add_argument('--chunk-strategy', type=str, default='smart',
                        choices=['smart', 'paragraph', 'line', 'fixed'],
                        help='Chi\u1ebfn l\u01b0\u1ee3c chunking (m\u1eb7c \u0111\u1ecbnh: smart)')
    parser.add_argument('--force', action='store_true',
                        help='Ghi \u0111\u00e8 m\u00e0 kh\u00f4ng h\u1ecfi (cho merge)')

    args = parser.parse_args()

    slug = args.slug or args.book.lower().replace(' ', '-')
    lang_code = 'en' if args.source_lang.lower() in ('en', 'english') else 'zh'

    print(f"\n{'#'*60}")
    print(f"# PIPELINE: {args.book} ({slug})")
    print(f"# Ng\u00f4n ng\u1eef: {args.source_lang} \u2192 {args.target_lang}")
    print(f"# T\u1eeb b\u01b0\u1edbc: {args.from_step}" + (" (auto mode)" if args.auto else ""))
    print(f"{'#'*60}\n")

    extracted_dir = PROJECT_ROOT / 'working' / 'extracted' / slug
    chunks_dir = PROJECT_ROOT / 'working' / 'chunks' / slug
    progress_dir = PROJECT_ROOT / 'working' / 'progress' / slug
    output_dir = PROJECT_ROOT / 'output'
    glossary_file = PROJECT_ROOT / 'glossary' / f'{slug}.csv'

    # == STEP 1: EXTRACT ==
    if args.from_step <= 1:
        if args.auto:
            print_agent_step(1, 'Extract', '\u26a0\ufe0f Skip trong auto mode (c\u1ea7n input file)')
        elif not args.input:
            print_agent_step(1, 'Extract', '\u26a0\ufe0f B\u1ecf qua: kh\u00f4ng c\u00f3 --input')
        else:
            raw_md = extracted_dir / 'raw.md'
            if args.input.suffix.lower() == '.epub':
                ok = run_script('epub_extract.py', [
                    '--input', str(args.input),
                    '--output', str(raw_md),
                ], f'1. Extract EPUB \u2192 {raw_md}')
            else:
                ok = run_script('mineru_extract.py', [
                    '--input', str(args.input),
                    '--output', str(raw_md),
                    '--lang', lang_code,
                ], f'1. Extract PDF \u2192 {raw_md}')
            if not ok:
                print('\n  [L\u1ed6I] Extract th\u1ea5t b\u1ea1i. D\u1eebng pipeline.', file=sys.stderr)
                sys.exit(1)
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 1 (Extract)")

    # == STEP 2: CHUNK ==
    if args.from_step <= 2:
        print_agent_step(2, 'Chunk', f'Chia text th\u00e0nh c\u00e1c chunk (strategy: {args.chunk_strategy})')

        # Find input for chunking
        chunk_input = extracted_dir / 'raw.md'
        alt_input = extracted_dir / 'raw-hans.md'
        if alt_input.exists():
            chunk_input = alt_input
        if not chunk_input.exists():
            print(f"  \u26a0\ufe0f Kh\u00f4ng t\u00ecm th\u1ea5y file extracted. B\u1ecf qua chunk.")
        else:
            run_script('chunk_text.py', [
                '--input', str(chunk_input),
                '--output-dir', str(chunks_dir),
                '--strategy', args.chunk_strategy,
                '--lang', lang_code,
            ], f'2. Chunk text \u2192 {chunks_dir}')
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 2 (Chunk)")

    # == STEP 3: GEN GLOSSARY ==
    if args.from_step <= 3:
        if args.auto:
            print_agent_step(3, 'Gen Glossary', '\u26a0\ufe0f Skip (auto mode) - Agent c\u1ea7n review v\u00e0 t\u1ea1o CSV')
        else:
            print_agent_step(3, 'Gen Glossary',
                             'T\u1ea1o prompt \u2192 Agent \u0111\u1ecdc v\u00e0 t\u1ea1o glossary CSV\n'
                             f'  Ch\u1ea1y l\u1ec7nh: python scripts/generate_glossary.py --source-dir {chunks_dir} --book-name {slug}\n'
                             f'  Sau \u0111\u00f3 \u0111\u1ecdc file prompt v\u00e0 y\u00eau c\u1ea7u Agent t\u1ea1o {glossary_file}')

            chunk_input_gg = chunks_dir if chunks_dir.exists() else extracted_dir
            if chunk_input_gg.exists():
                if chunks_dir.exists():
                    run_script('generate_glossary.py', [
                        '--source-dir', str(chunks_dir),
                        '--book-name', slug,
                    ], '3. Generate glossary prompt')
                else:
                    run_script('generate_glossary.py', [
                        '--source', str(extracted_dir / 'raw.md'),
                        '--book-name', slug,
                    ], '3. Generate glossary prompt')
            else:
                print("  \u26a0\ufe0f Kh\u00f4ng t\u00ecm th\u1ea5y source text. B\u1ecf qua.")
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 3 (Gen Glossary)")

    # == STEP 4: TRANSLATE ==
    if args.from_step <= 4:
        if args.auto:
            print_agent_step(4, 'Translate (Agent)',
                             '\u26a0\ufe0f Skip (auto mode) - Agent c\u1ea7n d\u1ecbch t\u1eebng chunk\n'
                             '  D\u00f9ng translate_helper.py \u0111\u1ec3 h\u1ed7 tr\u1ee3:\n'
                             f'    python scripts/translate_helper.py --prepare 0 --chunks-dir {chunks_dir} --glossary {glossary_file}\n'
                             f'    python scripts/translate_helper.py --save 0 --progress-dir {progress_dir}\n'
                             f'    python scripts/translate_helper.py --status --progress-dir {progress_dir}\n'
                             f'    python scripts/translate_helper.py --next --chunks-dir {chunks_dir} --progress-dir {progress_dir}')
        else:
            print_agent_step(4, 'Translate (Agent)',
                             'D\u1ecbch t\u1eebng chunk b\u1eb1ng Agent!\n\n'
                             f'  C\u00e1ch d\u00f9ng translate_helper.py:\n\n'
                             f'  1. Xem ti\u1ebfn tr\u00ecnh:\n'
                             f'     python scripts/translate_helper.py --status --progress-dir {progress_dir}\n\n'
                             f'  2. Xem chunk ti\u1ebfp theo c\u1ea7n d\u1ecbch:\n'
                             f'     python scripts/translate_helper.py --next --chunks-dir {chunks_dir} --progress-dir {progress_dir}\n\n'
                             f'  3. Chu\u1ea9n b\u1ecb prompt cho chunk (in ra terminal):\n'
                             f'     python scripts/translate_helper.py --prepare 0 --chunks-dir {chunks_dir} --glossary {glossary_file}\n\n'
                             f'  4. L\u01b0u b\u1ea3n d\u1ecbch sau khi Agent tr\u1ea3 v\u1ec1:\n'
                             f'     python scripts/translate_helper.py --save 0 --progress-dir {progress_dir} --chunks-dir {chunks_dir}\n'
                             f'     (paste b\u1ea3n d\u1ecbch, Ctrl+Z, Enter)')
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 4 (Translate)")

    # == STEP 5: QA ==
    if args.from_step <= 5:
        if progress_dir.exists() and glossary_file.exists():
            print_agent_step(5, 'QA', f'Ki\u1ec3m tra ch\u1ea5t l\u01b0\u1ee3ng d\u1ecbch')
            qa_dir = PROJECT_ROOT / 'working' / 'qa' / slug
            qa_dir.mkdir(parents=True, exist_ok=True)

            # Run QA on each translated chunk
            chunk_files = sorted(progress_dir.glob('*.json'))
            qa_ok = True
            for cf in chunk_files:
                try:
                    import json
                    data = json.loads(cf.read_text(encoding='utf-8-sig'))
                    cid = data.get('chunk_id', '?')
                    translated = data.get('translated_text', '')
                    if not translated.strip():
                        print(f"  \u26a0\ufe0f Chunk {cid} ch\u01b0a d\u1ecbch, b\u1ecf qua QA")
                        continue
                    source_text = data.get('source_text', '')
                    if not source_text:
                        print(f"  \u26a0\ufe0f Chunk {cid} kh\u00f4ng c\u00f3 source_text, d\u00f9ng chunk g\u1ed1c")

                    # Create temp files for QA
                    src_tmp = qa_dir / f'_qa_src_{cid}.md'
                    tgt_tmp = qa_dir / f'_qa_tgt_{cid}.md'
                    src_tmp.write_text(source_text or '', encoding='utf-8')
                    tgt_tmp.write_text(translated, encoding='utf-8')
                    report_file = qa_dir / f'chunk-{cid}-qa.md'

                    ok = run_script('glossary_qa.py', [
                        '--source', str(src_tmp),
                        '--translation', str(tgt_tmp),
                        '--glossary', str(glossary_file),
                        '--lang', lang_code,
                        '--report', str(report_file),
                    ], f'5. QA chunk {cid}')
                    if not ok:
                        qa_ok = False
                except Exception as e:
                    print(f"  \u26a0\ufe0f L\u1ed7i QA chunk {cf.name}: {e}")
            if qa_ok:
                print(f"\n  \u2705 QA ho\u00e0n t\u1ea5t cho {len(chunk_files)} chunk")
            else:
                print(f"\n  \u26a0\ufe0f QA c\u00f3 m\u1ed9t s\u1ed1 l\u1ed7i, ki\u1ec3m tra b\u00e1o c\u00e1o trong {qa_dir}")
        else:
            print_agent_step(5, 'QA', '\u26a0\ufe0f B\u1ecf qua: thi\u1ebfu progress_dir ho\u1eb7c glossary')
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 5 (QA)")

    # == STEP 6: MERGE ==
    if args.from_step <= 6:
        if progress_dir.exists():
            print_agent_step(6, 'Merge', f'G\u1ed9p t\u1ea5t c\u1ea3 chunk \u0111\u00e3 d\u1ecbch th\u00e0nh file ho\u00e0n ch\u1ec9nh')
            merge_args = [
                '--progress-dir', str(progress_dir),
                '--book-name', slug,
            ]
            if args.force:
                merge_args.append('--force')
            run_script('merge_chunks.py', merge_args,
                       f'6. Merge chunks \u2192 {output_dir / f"{slug}_translated.md"}')
        else:
            print_agent_step(6, 'Merge', '\u26a0\ufe0f B\u1ecf qua: progress_dir ch\u01b0a t\u1ed3n t\u1ea1i')
    else:
        print(f"  \u23ed B\u1ecf qua b\u01b0\u1edbc 6 (Merge)")

    print(f"\n{'#'*60}")
    print(f"# PIPELINE HO\u00c0N TH\u00c0NH: {args.book}")
    print(f"{'#'*60}")


if __name__ == '__main__':
    main()
