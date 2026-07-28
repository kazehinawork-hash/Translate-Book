import re

md_path = r"E:\OneDrive\onyx\Translate Book\output\you-feng-gu-nu-zi_translated.md"
out_path = r"E:\OneDrive\onyx\Translate Book\output\you-feng-gu-nu-zi_translated_vi.md"

with open(md_path, "r", encoding="utf-8") as f:
    text = f.read()

lines = text.split("\n")
out_lines = []

for line in lines:
    if " /// " in line:
        parts = line.split(" /// ", 1)
        vi_part = parts[1].strip()
        if vi_part:
            out_lines.append(vi_part)
        else:
            out_lines.append("")
    elif "///" in line:
        parts = line.split("///", 1)
        vi_part = parts[1].strip()
        if vi_part:
            out_lines.append(vi_part)
        else:
            out_lines.append("")
    else:
        out_lines.append(line)

result = "\n".join(out_lines)

with open(out_path, "w", encoding="utf-8") as f:
    f.write(result)

# Stats
vi_count = sum(1 for c in result if '\u00e0' <= c <= '\u1ef9')
cn_count = sum(1 for c in result if '\u4e00' <= c <= '\u9fff')
print(f"Written: {out_path}")
print(f"Size: {len(result)} chars, {len(result.splitlines())} lines")
print(f"Chinese chars: {cn_count}")
print(f"Vietnamese chars: {vi_count}")
lines2 = result.splitlines()
has_cn = lambda l: any('\u4e00' <= c <= '\u9fff' for c in l)
cn_line_count = sum(1 for l in lines2 if has_cn(l))
print(f"Lines with Chinese: {cn_line_count}")
