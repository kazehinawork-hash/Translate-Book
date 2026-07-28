import json
import os
import sys
from datetime import datetime, timezone
from googletrans import Translator

slug = "you-feng-gu-nu-zi"
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
progress_dir = os.path.join(base, "working", "progress", slug)

start = int(sys.argv[1]) if len(sys.argv) > 1 else 510
end = int(sys.argv[2]) if len(sys.argv) > 2 else 941

translator = Translator()
count = 0

for cid in range(start, end):
    in_path = os.path.join(progress_dir, f"chunk_{cid:03d}.json")
    if not os.path.exists(in_path):
        continue
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("translated_text", "").strip():
        continue
    src = data.get("source_text", "")
    if not src.strip():
        data["translated_text"] = src
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
    count += 1
    print(f"OK {cid}")

print(f"Done: {count} chunks translated ({start}-{end-1})")
