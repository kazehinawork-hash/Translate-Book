import json
import os
from datetime import datetime, timezone
from googletrans import Translator

slug = "you-feng-gu-nu-zi"
base = r"E:\OneDrive\onyx\Translate Book"
progress_dir = os.path.join(base, "working", "progress", slug)

translator = Translator()

import sys
start_cid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
end_cid = int(sys.argv[2]) if len(sys.argv) > 2 else 310

for cid in range(start_cid, end_cid):
    in_path = os.path.join(progress_dir, f"chunk_{cid:03d}.json")
    if not os.path.exists(in_path):
        continue
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    src = data.get("source_text", "")
    if not src.strip():
        data["translated_text"] = ""
        data["translated_at"] = datetime.now(timezone.utc).isoformat()
    else:
        try:
            result = translator.translate(src, src="zh-cn", dest="vi")
            data["translated_text"] = result.text
            data["translated_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            print(f"ERROR {cid}: {e}")
            continue
    with open(in_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print("Done: chunks 0-309 re-translated to Vietnamese")
