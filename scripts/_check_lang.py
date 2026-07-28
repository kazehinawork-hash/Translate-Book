import json, os

progress_dir = r"E:\OneDrive\onyx\Translate Book\working\progress\you-feng-gu-nu-zi"
out_dir = r"C:\Users\Admin\AppData\Local\Temp\opencode"

for cid in [3, 4, 7, 12, 20, 30, 40, 60]:
    d = json.load(open(os.path.join(progress_dir, f"chunk_{cid:03d}.json"), "r", encoding="utf-8"))
    t = d.get("translated_text", "")
    has_vi = any(0x00E0 <= ord(c) <= 0x1EF9 for c in t)
    has_cn = any(0x4E00 <= ord(c) <= 0x9FFF for c in t)
    has_en = bool(t.strip()) and not has_vi and not has_cn
    with open(os.path.join(out_dir, "check_lang.txt"), "a", encoding="utf-8") as f:
        f.write(f"CHUNK {cid}: vi={has_vi} cn={has_cn} en={has_en}\n")
        f.write(f"  SRC: {d['source_text'][:120]}\n")
        f.write(f"  TR:  {t[:120]}\n\n")
