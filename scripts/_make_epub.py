import sys
import re
from pathlib import Path
from datetime import datetime

from ebooklib import epub

def md_to_epub(md_path: Path, output_path: Path, title: str, author: str = "微阳"):
    book = epub.EpubBook()
    book.set_identifier(str(hash(md_path.read_text(encoding='utf-8'))))
    book.set_title(title)
    book.set_language('vi')
    book.add_author(author)
    book.add_metadata('DC', 'description', f'Bilingual translation of {title}')

    css = '''
body { font-family: serif; line-height: 1.8; margin: 1em; }
h1 { text-align: center; font-size: 1.6em; margin-top: 1.5em; }
h2 { font-size: 1.3em; margin-top: 1.2em; }
h3 { font-size: 1.1em; margin-top: 1em; }
p { text-indent: 0; margin: 0.5em 0; }
.source { color: #666; font-style: italic; }
.translation { color: #000; }
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
'''

    css_item = epub.EpubItem(uid="style", file_name="style/default.css", media_type="text/css", content=css)
    book.add_item(css_item)

    text = md_path.read_text(encoding='utf-8')
    lines = text.split('\n')

    chapters = []
    current_chapter = []
    current_title = "Mở đầu"
    chapter_index = 1

    def flush_chapter():
        nonlocal chapter_index
        content = '\n'.join(current_chapter)
        if not content.strip():
            return
        body_html = f'<body>{content}</body>' if content else '<body><br/></body>'
        ep_ch = epub.EpubHtml(
            title=current_title,
            file_name=f'chap_{chapter_index:03d}.xhtml',
            lang='vi'
        )
        ep_ch.add_item(css_item)
        page_content = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml">\n'
        page_content += f'<head><meta charset="utf-8"/><title>{current_title}</title></head>\n'
        page_content += body_html + '\n</html>'
        ep_ch.content = page_content.encode('utf-8')
        book.add_item(ep_ch)
        chapters.append(ep_ch)
        chapter_index += 1

    for line in lines:
        if line.startswith('# '):
            flush_chapter()
            current_title = line[2:].strip()
            current_chapter = [f'<h1>{current_title}</h1>']
        elif line.startswith('## '):
            current_chapter.append(f'<h2>{line[3:].strip()}</h2>')
        elif line.startswith('### '):
            current_chapter.append(f'<h3>{line[4:].strip()}</h3>')
        elif line.startswith('!['):
            alt = re.search(r'\[(.*?)\]', line)
            src = re.search(r'\((.*?)\)', line)
            if src:
                img_path = src.group(1)
                alt_text = alt.group(1) if alt else ''
                current_chapter.append(f'<p><img src="{img_path}" alt="{alt_text}"/></p>')
        elif line.strip() == '---':
            current_chapter.append('<hr/>')
        elif line.strip() == '':
            current_chapter.append('<br/>')
        else:
            current_chapter.append(f'<p>{line}</p>')

    flush_chapter()

    book.toc = [(epub.Section('Nội dung'), chapters)]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    book.spine = ['nav'] + chapters

    epub.write_epub(str(output_path), book, {})
    print(f"EPUB created: {output_path}")
    print(f"  Chapters: {len(chapters)}")
    print(f"  Size: {output_path.stat().st_size / 1024:.0f} KB")

if __name__ == '__main__':
    args = sys.argv[1:]
    input_md = args[0] if args else r"E:\OneDrive\onyx\Translate Book\output\you-feng-gu-nu-zi_translated_vi.md"
    output_epub = args[1] if len(args) > 1 else r"E:\OneDrive\onyx\Translate Book\output\you-feng-gu-nu-zi_translated_vi.epub"
    title = args[2] if len(args) > 2 else "做一个有风骨的女子: A Woman of Integrity"
    md_to_epub(
        md_path=Path(input_md),
        output_path=Path(output_epub),
        title=title
    )
