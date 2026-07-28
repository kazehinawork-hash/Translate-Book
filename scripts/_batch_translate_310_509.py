import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from googletrans import Translator

slug = "you-feng-gu-nu-zi"
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
progress_dir = os.path.join(base, "working", "progress", slug)

translator = Translator()

batch_start = int(sys.argv[1]) if len(sys.argv) > 1 else 310
batch_end = int(sys.argv[2]) if len(sys.argv) > 2 else 510

for cid in range(batch_start, batch_end):
    in_path = os.path.join(progress_dir, f"chunk_{cid:03d}.json")
    if not os.path.exists(in_path):
        print(f"SKIP {cid}: file not found")
        continue

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    src = data.get("source_text", "")
    if data.get("translated_text", ""):
        print(f"SKIP {cid}: already translated")
        continue

    if not src.strip():
        data["translated_text"] = src
        data["translated_at"] = datetime.now(timezone.utc).isoformat()
        with open(in_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{cid}: empty text, saved as-is")
        continue

    try:
        result = translator.translate(src, src="zh-cn", dest="vi")
        vi = result.text
        data["translated_text"] = vi
        data["translated_at"] = datetime.now(timezone.utc).isoformat()
        with open(in_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{cid}: {len(src)}ch -> {len(vi)}ch")
    except Exception as e:
        print(f"ERROR {cid}: {e}")

print("Done: chunks 310-509 translated")
