---
description: Tự động dịch trọn một cuốn sách — chỉ cần file PDF/EPUB trong input/, lệnh này chạy toàn bộ pipeline (extract → chunk → glossary → dịch → QA → merge → EPUB) và trả kết quả hoàn chỉnh.
agent: build
---

Tự động dịch trọn một cuốn sách từ đầu đến cuối. Người dùng KHÔNG làm bước thủ công nào — bạn chạy mọi thứ. `$ARGUMENTS` có thể là: (1) tên file trong `input/` (VD `ten-sach.pdf`), (2) slug sách đã có chunk (VD `zuo-yi-ge-gang-gang-hao-de-nu-zi`), hoặc để trống.

Luồng tổng quát:

## A. Xác định công việc
1. Nếu `$ARGUMENTS` có tên file `.pdf`/`.epub`/`.docx` tồn tại trong `input/` (tìm ở cả 3 thư mục con `input\chua-lam\`, `input\da-dich\`, `input\da-audio\` — **sách mới/đã làm đều có thể chạy lại**) → chạy đủ bước B→J. Lưu ý dùng đường dẫn đầy đủ `input\<thư-mục-con>\<file>`.
2. Nếu `$ARGUMENTS` là slug đã có `working/chunks/<slug>/` hoặc `working/progress/<slug>/` → **sách đang dở**: bỏ qua B, chạy từ D (glossary) hoặc E (skeleton) trở đi.
3. Nếu trống: liệt kê `input/chua-lam/` (chưa làm) + `working/chunks/` + `working/progress/`, hỏi người dùng chọn.
4. Slug mặc định = tên file bỏ đuôi, viết thường, thay khoảng trắng bằng `-`. Nếu người dùng cung cấp `--slug <x>` trong `$ARGUMENTS` thì dùng slug đó.

## B. Extract (chỉ sách mới)
- EPUB: `python scripts\extract\epub_extract.py --input input\<file> --output working\extracted\<slug>\raw.md`
- PDF/DOCX/ảnh: `python scripts\extract\mineru_extract.py --input input\<file> --output working\extracted\<slug>\raw.md --lang <en|zh> --backend pipeline --device auto` (thử `--lang en` trước; nếu raw.md ra toàn chữ Hán thì chạy lại với `--lang zh`). `--device auto` tự dùng GPU (torch CUDA trong `.venv`).
- **Làm sạch rác extract EPUB** (nếu QC bước C fail vì dòng lặp): xóa dòng `xml version='1.0' encoding='utf-8'?` và separator `---` thừa khỏi raw.md trước khi sang bước C (ví dụ dùng Python đọc/ghi UTF-8 — KHÔNG dùng pipe PowerShell vì hỏng dấu tiếng Việt).
- In kết quả trích xuất (số dòng/ký tự của raw.md).

## C. QC + Detect lang + OpenCC
1. `python scripts\process\post_extract_qc.py --input working\extracted\<slug>\raw.md --report working\qa\<slug>\extract-qc.md --lang <en|zh>`
2. `python scripts\process\detect_language.py working\extracted\<slug>\raw.md --quiet` → kết quả `en` / `zh-Hans` / `zh-Hant`.
3. Nếu `zh-Hant`: `python scripts\process\opencc_normalize.py --input working\extracted\<slug>\raw.md --output working\extracted\<slug>\raw-hans.md --config t2s` và các bước sau dùng `raw-hans.md`.
4. Ghi nhớ `LANG` (en/zh) và file gốc `RAW` (raw.md hoặc raw-hans.md) để dùng tiếp.

## D. Chunk
- EN: `python scripts\process\chunk_text.py --input <RAW> --output-dir working\chunks\<slug> --lang en --min-chars 3000 --max-chars 8000 --overlap-chars 200 --respect-headings`
- ZH: `python scripts\process\chunk_text.py --input <RAW> --output-dir working\chunks\<slug> --lang zh --min-chars 1500 --max-chars 3000 --overlap-chars 200 --respect-headings`
- Xác nhận số chunk JSON trong `working\chunks\<slug>\`.

## E. Glossary
1. `python scripts\process\generate_glossary.py --source-dir working\chunks\<slug> --book-name <slug>` → tạo `working\glossary_prompt_<slug>.txt`.
2. Đọc file prompt đó, rồi đọc vài chunk JSON đầu + giữa sách, tự trích danh sách thuật ngữ (tên nhân vật, địa điểm, thuật ngữ) và tạo `glossary\<slug>.csv` với header `source,target,notes`. Ghi UTF-8.
3. Nếu `glossary\<slug>.csv` đã tồn tại thì giữ nguyên (không tạo lại).
4. **Gộp vào master**: chạy `python scripts\process\merge_glossary.py --book <slug> --author <author> [--genre <genre>]` — thêm thuật ngữ của cuốn vào `glossary\master.csv` (file trung tâm duy nhất, cột `source,target,type,note,book,author,genre`), **không đè mục đã có**. Nếu cuốn thuộc tác giả/thể loại đã có trong master (`van-tinh`, `vi-duong`, `khang-tinh-van`, `tien-hiep`), các thuật ngữ chung đó sẽ **tự áp dụng** khi dịch/QA (không cần copy vào file cuốn). Master tự tách `master_001.csv` khi phình (>300 dòng) — không cần làm gì.
5. In tóm tắt số thuật ngữ cho người dùng xem.

## F. Skeleton progress
- ZH: `python scripts\translate\init_trilingual_skeleton.py --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug>` → tạo `working\progress\<slug>\chunk_<NNN>.json` (`mode=trilingual`, `original_text` 1 câu/dòng, `translated_text` rỗng).
- EN: chạy script tương tự (vẫn tạo được skeleton). Nếu script LỖI với EN: tự tạo `working\progress\<slug>\chunk_<NNN>.json` tối giản cho từng chunk gốc với fields: `chunk_id`, `total_chunks`, `chapter`, `source_text` (bằng `text` của chunk gốc), `translated_text` (`''`), `word_count_source`, `word_count_translated` (`0`), `mode` (`'bilingual'`), `translated_at` (`''`). Ghi bằng `json.dumps(ensure_ascii=False, indent=2)` UTF-8.

## G. Dịch theo batch (bạn tự dịch — AI chat)
Tạo manifest một lần sau khi có skeleton:
```powershell
python scripts\translate\batch_manifest.py create --slug <slug> --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug> --batch-size 3
```

Mỗi lượt Agent chỉ nhận một batch:
```powershell
python scripts\translate\batch_manifest.py claim --slug <slug> --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug> --worker <agent-id>
```

1. Đọc JSON của đúng các `chunk_ids` trong batch đã claim; không quét hoặc tự nhận chunk ngoài manifest. Nguồn là `original_text` (trilingual) hoặc `source_text` (bilingual).
2. Dịch theo thứ tự chunk, giữ glossary/ngữ cảnh chung. Trilingual phải giữ đúng số dòng; giữ heading `#`/`##`, dòng ảnh `![...]`, dòng trống, số/ISBN/URL; bỏ `///` OCR dư.
3. Sau khi kiểm tra từng chunk, cập nhật riêng `working/progress/<slug>/chunk_<NNN>.json` với `translated_text`, `translated_at`, `word_count_translated`; giữ nguyên field khác và dùng UTF-8/`ensure_ascii=False`.
4. Chạy QA nhanh đúng các chunk trong batch:
```powershell
python scripts\qa\batch_qa.py --progress-dir working\progress\<slug> --chunk-id <id-1> --chunk-id <id-2>
```
Nếu QA báo lỗi, sửa và kiểm tra lại; không đánh dấu batch hoàn tất khi lệch dòng, rỗng hoặc còn marker điều khiển.
5. Nếu mọi chunk trong batch đạt kiểm tra, đánh dấu batch hoàn tất:
```powershell
python scripts\translate\batch_manifest.py complete --slug <slug> --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug> --batch-id <id>
```
Nếu lỗi, dùng `fail --batch-id <id>` để batch được giao lại; không xóa progress đã tốt.
5. Có thể dùng nhiều Agent song song **chỉ khi mỗi Agent claim batch khác nhau**. Ưu tiên các batch thuộc chương khác nhau; tuyệt đối không để hai Agent ghi cùng `chunk_id`.
6. Kiểm tra trạng thái và coverage trước khi chuyển bước:
```powershell
python scripts\translate\batch_manifest.py verify --slug <slug> --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug>
```
Manifest chỉ điều phối; `progress JSON` từng chunk vẫn là dữ liệu dịch chính.

## H. QA
- Nếu có `glossary\<slug>.csv` + progress đầy đủ: `python scripts\pipeline\run_pipeline.py --book <book> --slug <slug> --from-step 8 --to-step 8` — BẮT BUỘC thêm `--to-step 8` để CHỈ chạy bước 8 (QA), tránh tự merge/EPUB luôn. In báo cáo cho người dùng; sửa các lỗi rõ ràng (Hán sót, mojibake) nếu dễ.

## I. Merge
- ⚠️ **Thư mục output dùng tên sách gốc** (tên file input): `output/books/<tên-sách-gốc>/`. Sau khi tạo thư mục, **BẮT BUỘC tạo `metadata.json`** đầy đủ:
  ```json
  {
    "slug": "<slug-nội-bộ>",
    "title": "<tên-sách-gốc>",
    "source_file": "<tên file input>",
    "author": "<tác giả>",
    "language": "zh" | "en" | "vi",
    "genre": "<thể loại>",
    "has_audio": true|false,
    "has_epub": true|false,
    "epub_file": "<tên file epub nếu có>",
    "created": "YYYY-MM-DD"
  }
  ```
  Các trường `has_audio`/`has_epub`/`epub_file` có thể tự dò từ thư mục khi cập nhật (chạy lại `scripts\manage_input.py` không ghi đè metadata). `<slug>` là định danh nội bộ (progress/chunks/glossary/audio).
- ZH: `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --format trilingual --force --output-dir "output\books\<tên-sách-gốc>\final"` → tạo `<slug>_trilingual.md` → **rename thành `tamngu.md`**; rồi `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --force --output-dir "output\books\<tên-sách-gốc>\final"` → tạo `<slug>_translated.md` → **rename thành `vi.md`**.
- ⚠️ **BẮT BUỘC truyền `--output-dir` tường minh** (merge_chunks tự dò PROJECT_ROOT bị lệch trên máy này — ghi ra sai vị trí nếu bỏ qua). Rename file sau merge vì script đặt tên `<slug>_trilingual.md`/`<slug>_translated.md` thay vì `tamngu.md`/`vi.md`.
- EN: `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug>-tmp --output-dir working\tmp\<slug> --force`, rồi `python scripts\output\make_bilingual.py --source <RAW> --translation working\tmp\<slug>\<slug>-tmp_translated.md --output "output\books\<tên-sách-gốc>\final\songngu.md" --lang en`; copy sang `"output\books\<tên-sách-gốc>\final\vi.md"`.
- Sau merge, **verify nguồn dịch không mojibake**: quét ký tự `?` đứng giữa chữ (pattern `[a-zA-ZÀ-ỹ]\?(?=[a-zA-ZÀ-ỹ])`) trong vi.md — nếu > 0 thì chunk tương ứng bị hỏng dấu (thường do ghi qua pipe PowerShell), cần sửa lại chunk đúng UTF-8 rồi merge lại.

## J. EPUB
- Nếu người dùng muốn file EPUB (hoặc mặc định tạo): gọi pandoc tại `C:\Users\Admin\AppData\Local\Pandoc\pandoc.exe` qua `python scripts\output\make_epub.py "output\books\<tên-sách-gốc>\final\vi.md" --title "<Tên sách>" --author "<tác giả nếu biết>" --resource-path "output\books\<tên-sách-gốc>\images;working\extracted\<slug>"` (nếu pandoc không nằm trong PATH, thử thêm `C:\Users\Admin\AppData\Local\Pandoc` vào PATH tạm hoặc gọi pandoc.exe trực tiếp).
- **Tên file EPUB cuối = tên sách input** (theo yêu cầu user): chỉ giữ **1 file EPUB ở gốc thư mục** tên `<tên-sách-input>.epub` (vd `做一个刚刚好的女子  不攀附, 不将就 (晚情) (z-library.sk, 1lib.sk, z-lib.sk).epub` — đúng tên file trong input/, có thể giữ cả phần rác). **KHÔNG tạo `final/tamngu.epub` / `final/vi.epub`** — tamngu và vi chỉ cần file `.md` (`final/tamngu.md`, `final/vi.md`).
- **Sách ZH (tam ngữ/pinyin/tiếng Việt có dấu) — BẮT BUỘC nhúng font** nếu không muốn Calibre hiển thị ký tự có dấu thành `?`: dùng pandoc trực tiếp với `--epub-embed-font` + CSS `@font-face`:
  1. CSS tạm khai báo `@font-face { font-family: "NotoSerifSC"; src: url("fonts/NotoSerifSC-VF.ttf"); }` và set `font-family: "NotoSerifSC", serif` cho body/h1-3/p/tam-ngữ.
  2. `pandoc "output\books\<tên-sách-gốc>\final\tamngu.md" -o working\tmp_epub\tamngu.epub --css <css> --epub-embed-font C:\Windows\Fonts\NotoSerifSC-VF.ttf -M title="<Tên sách>" -M author="<tác giả>" --toc` (font lấy từ `C:\Windows\Fonts\NotoSerifSC-VF.ttf` — hỗ trợ Hán + Latin mở rộng + dấu Việt).
  3. **Fix path font**: pandoc ghi `url("fonts/...")` trong CSS (đặt tại `EPUB/styles/`) → dùng Python sửa trong zip thành `url("../fonts/...")`.
  4. Copy `tamngu.epub` → **`output/books/<tên-sách-gốc>/<tên-sách-input>.epub`** (file EPUB duy nhất, tên theo file input). **KHÔNG tạo `final/tamngu.epub` / `final/vi.epub`** — chỉ giữ `.md` trong final/.

## K. Audiobook (tạo + QA) và tổng kết
- **Tạo audiobook GPU** (nếu người dùng muốn / mặc định làm cho sách VI + ZH đã dịch). `--slug` vẫn dùng slug nội bộ — script `find_book_dir()` tự map slug → thư mục tên gốc qua `metadata.json`:
  ```powershell
  working\venv-vieneu\Scripts\python.exe -u scripts\audiobook\audiobook_long.py --slug <slug> --gpu --batch-size 8 --music auto --music-volume 0.20 --temperature 0.3 --top-k 10
  ```
  - `--gpu` bắt buộc cho GPU (RTX 3060); `--batch-size 8` gom chunk mỗi forward; `--music auto` nhạc nền xoay (mỗi chương 1 bài trong `core/music/`); `--music-volume 0.20` mức đã chốt; `--temperature 0.3 --top-k 10` tham số chốt (giọng chậm rãi trầm ấm).
  - Log in **dần từng nhóm batch** (`[batch 1/60]`, `[batch 2/60]`...) — không đợi hết chapter mới in.
  - Nếu `vi.md` đã đổi (sửa dịch): chạy lại `--chapter <số chương bị ảnh hưởng> --force` để tạo lại đúng phần, giữ các chương khác.
  - ⚠️ Khi chạy nền: dùng `-u` (unbuffered) để log không bị nuốt; hoặc chạy trực tiếp terminal.
- **QA audiobook** sau khi tạo:
  ```powershell
  python scripts\qa\audio_qa.py --slug <slug>
  ```
- Báo cáo được ghi tại `working/qa/<slug>/audio-report.json`; phải kiểm tra đủ chapter, file không rỗng, WAV 48 kHz và không clipping. MP3 được đo duration nếu máy có `ffprobe`.
- In đường dẫn đầy đủ các file output: `output/books/<tên-sách-gốc>/final/vi.md` (bản tiếng Việt), `output/books/<tên-sách-gốc>/final/tamngu.md` (tam ngữ, nếu ZH), `output/books/<tên-sách-gốc>/trilingual.epub` (EPUB), `output/books/<tên-sách-gốc>/audiobook/` (ch01.mp3...) và báo cáo QA.
- **Sắp xếp input/ theo trạng thái** (tự động): chạy `python scripts\manage_input.py` để di chuyển file input vào `input\chua-lam\` (chưa làm) / `input\da-dich\` (đã dịch) / `input\da-audio\` (đã dịch + audio) — nhìn input là biết sách xử lý đến đâu.
- KHÔNG tự commit/push (theo AGENTS.md) trừ khi người dùng yêu cầu. Hỏi người dùng có muốn commit/push không.

## ⚠️ Ghi chú chung (kinh nghiệm từ các phiên)
- **KHÔNG bao giờ pipe text tiếng Việt qua PowerShell** (`Get-Content | python ...`) — encoding cp1252 làm hỏng dấu thành `?`. Luôn ghi file UTF-8 bằng Python rồi đọc lại.
- `batch_manifest.py` / `batch_qa.py` / script in tiếng Việt cần `sys.stdout.reconfigure(encoding="utf-8")` (đã fix) — nếu script mới in tiếng Việt lỗi cp1252, thêm dòng này.
- `init_trilingual_skeleton.py` import `add_pinyin` từ `scripts/pinyin/` (đã fix sys.path).
- Xung đột cuDNN DLL trên Windows: **không import torch + paddle trong cùng 1 tiến trình** — MinerU dùng `.venv` (torch), PaddleOCR dùng `working\venv-ocr` (paddle), TTS dùng `working\venv-vieneu` (torch). `ocr_paddle.py` tự relaunch qua venv-ocr khi env hiện tại thiếu paddleocr.
