"""
ocr_easy.py - OCR using EasyOCR (fallback for scanned PDFs)

For PDFs with GlyphLessFont where text extraction fails.
Uses EasyOCR on CPU (GPU not available).

Usage:
    python scripts/ocr_easy.py ^
        --input "input\gang-gang-hao-2.pdf" ^
        --output "working\extracted\gang-gang-hao-2\raw.md"
"""

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent))
from _common import setup_encoding  # noqa: E402


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    doc = fitz.open(str(pdf_path))
    image_paths = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_path = output_dir / f"page_{i + 1:04d}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
    doc.close()
    return image_paths


def ocr_page(reader, img_path: Path) -> str:
    result = reader.readtext(str(img_path), paragraph=True)
    lines = []
    for entry in result:
        text = entry[1]
        if text.strip():
            lines.append(text.strip())
    return '\n\n'.join(lines)


def main():
    setup_encoding()
    parser = argparse.ArgumentParser(description='OCR using EasyOCR')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--langs', type=str, default='ch_sim,en',
                        help='Languages (comma-separated, default: ch_sim,en)')
    args = parser.parse_args()

    if not args.input.exists():
        print(f'[ERROR] File not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    langs = [l.strip() for l in args.langs.split(',')]
    print(f'PDF: {args.input}')
    print(f'Output: {args.output}')
    print(f'Languages: {langs}')
    print(f'DPI: {args.dpi}')

    # Read progress file if it exists (to support resume)
    progress_file = args.output.with_suffix('.progress.json')
    already_done = set()
    if progress_file.exists():
        try:
            data = json.loads(progress_file.read_text('utf-8'))
            already_done = set(data.get('done_pages', []))
            print(f'Resuming: {len(already_done)} pages already processed')
        except Exception:
            already_done = set()

    print('Loading EasyOCR...')
    import easyocr
    reader = easyocr.Reader(langs, gpu=False)
    print('EasyOCR loaded')

    # Convert PDF to images
    print('Converting PDF to images...')
    image_dir = Path(tempfile.mkdtemp(prefix='ocr_easy_'))
    try:
        image_paths = pdf_to_images(args.input, image_dir, dpi=args.dpi)
        total = len(image_paths)
        print(f'  {total} pages')

        args.output.parent.mkdir(parents=True, exist_ok=True)
        all_texts = {}
        start_time = time.time()

        for i, img_path in enumerate(image_paths, 1):
            page_key = str(i)
            if page_key in already_done:
                continue

            elapsed = time.time() - start_time
            print(f'  OCR page {i}/{total} [{elapsed:.0f}s elapsed]...', end='', flush=True)
            text = ocr_page(reader, img_path)
            all_texts[page_key] = text
            print(f' {len(text)} chars')

            # Save progress periodically
            if i % 5 == 0:
                progress = {'done_pages': sorted(already_done | set(iter(all_texts)))}
                progress_file.write_text(json.dumps(progress, ensure_ascii=False), 'utf-8')
                # Write partial output
                _write_output(args.output, image_paths, all_texts, already_done)

        # Final write
        for pk in already_done:
            if pk not in all_texts:
                all_texts[pk] = ''
        _write_output(args.output, image_paths, all_texts, already_done)

        # Clean up progress file
        if progress_file.exists():
            progress_file.unlink()

        total_chars = sum(len(t) for t in all_texts.values())
        total_time = time.time() - start_time
        print(f'\nDone. {total_chars:,} chars in {total_time:.0f}s')
        print(f'Output: {args.output}')
    finally:
        shutil.rmtree(image_dir, ignore_errors=True)


def _write_output(output_path: Path, image_paths: list[Path],
                  all_texts: dict, already_done: set):
    parts = []
    for i, img_path in enumerate(image_paths, 1):
        pk = str(i)
        text = all_texts.get(pk, '')
        if not text and pk in already_done:
            text = ''
        parts.append(f'\n## Page {i}\n\n{text}\n')
    content = '\n---\n'.join(parts)
    output_path.write_text(content, encoding='utf-8')
    print(f'  [saved {len(content):,} chars]')


if __name__ == '__main__':
    main()
