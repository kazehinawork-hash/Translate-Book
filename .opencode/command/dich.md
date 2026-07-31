---
description: Tự động dịch trọn một cuốn sách — chỉ cần file PDF/EPUB trong input/, lệnh này chạy toàn bộ pipeline (extract → chunk → glossary → dịch → QA → merge → EPUB) và trả kết quả hoàn chỉnh.
agent: build
---

Tự động dịch trọn một cuốn sách từ đầu đến cuối. Người dùng KHÔNG làm bước thủ công nào — bạn chạy mọi thứ. `$ARGUMENTS` có thể là: (1) tên file trong `input/` (VD `ten-sach.pdf`), (2) slug sách đã có chunk (VD `zuo-yi-ge-gang-gang-hao-de-nu-zi`), hoặc để trống.

Luồng tổng quát:

## A. Xác định công việc
1. Nếu `$ARGUMENTS` có tên file `.pdf`/`.epub`/`.docx` tồn tại trong `input/` → **sách mới**: chạy đủ bước B→J.
2. Nếu `$ARGUMENTS` là slug đã có `working/chunks/<slug>/` hoặc `working/progress/<slug>/` → **sách đang dở**: bỏ qua B, chạy từ D (glossary) hoặc E (skeleton) trở đi.
3. Nếu trống: liệt kê `input/` và `working/chunks/` + `working/progress/`, hỏi người dùng chọn.
4. Slug mặc định = tên file bỏ đuôi, viết thường, thay khoảng trắng bằng `-`. Nếu người dùng cung cấp `--slug <x>` trong `$ARGUMENTS` thì dùng slug đó.

## B. Extract (chỉ sách mới)
- EPUB: `.venv\Scripts\python.exe scripts\epub_extract.py --input input\<file> --output working\extracted\<slug>\raw.md`
- PDF/DOCX/ảnh: `.venv\Scripts\python.exe scripts\mineru_extract.py --input input\<file> --output working\extracted\<slug>\raw.md --lang <en|zh> --backend pipeline --device auto` (thử `--lang en` trước; nếu raw.md ra toàn chữ Hán thì chạy lại với `--lang zh`)
- In kết quả trích xuất (số dòng/ký tự của raw.md).

## C. QC + Detect lang + OpenCC
1. `.venv\Scripts\python.exe scripts\post_extract_qc.py --input working\extracted\<slug>\raw.md --report working\qa\<slug>\extract-qc.md --lang <en|zh>`
2. `.venv\Scripts\python.exe scripts\detect_language.py working\extracted\<slug>\raw.md --quiet` → kết quả `en` / `zh-Hans` / `zh-Hant`.
3. Nếu `zh-Hant`: `.venv\Scripts\python.exe scripts\opencc_normalize.py --input working\extracted\<slug>\raw.md --output working\extracted\<slug>\raw-hans.md --config t2s` và các bước sau dùng `raw-hans.md`.
4. Ghi nhớ `LANG` (en/zh) và file gốc `RAW` (raw.md hoặc raw-hans.md) để dùng tiếp.

## D. Chunk
- EN: `.venv\Scripts\python.exe scripts\chunk_text.py --input <RAW> --output-dir working\chunks\<slug> --lang en --min-chars 3000 --max-chars 8000 --overlap-chars 200 --respect-headings`
- ZH: `.venv\Scripts\python.exe scripts\chunk_text.py --input <RAW> --output-dir working\chunks\<slug> --lang zh --min-chars 1500 --max-chars 3000 --overlap-chars 200 --respect-headings`
- Xác nhận số chunk JSON trong `working\chunks\<slug>\`.

## E. Glossary
1. `.venv\Scripts\python.exe scripts\generate_glossary.py --source-dir working\chunks\<slug> --book-name <slug>` → tạo `working\glossary_prompt_<slug>.txt`.
2. Đọc file prompt đó, rồi đọc vài chunk JSON đầu + giữa sách, tự trích danh sách thuật ngữ (tên nhân vật, địa điểm, thuật ngữ) và tạo `glossary\<slug>.csv` với header `source,target,notes` (nếu cuốn đã có genre như tiên hiệp, tham khảo `glossary\genres\*.csv`). Ghi UTF-8.
3. Nếu `glossary\<slug>.csv` đã tồn tại thì giữ nguyên (không tạo lại).
4. In tóm tắt số thuật ngữ cho người dùng xem.

## F. Skeleton progress
- ZH: `.venv\Scripts\python.exe scripts\init_trilingual_skeleton.py --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug>`
- EN: bước này không bắt buộc nhưng nên tạo skeleton (script vẫn chạy được với EN, `mode=trilingual`; nếu script lỗi với EN thì bỏ qua và tiến hành dịch trực tiếp).

## G. Dịch (bạn tự dịch — AI chat)
Lặp qua từng file `working\progress\<slug>\chunk_<NNN>.json` có `translated_text` rỗng (theo thứ tự số):
1. Đọc JSON: dịch `original_text` dòng-đối-dòng sang `translated_text` — số dòng kết quả PHẢI bằng số dòng gốc; giữ heading `#`/`##`, dòng ảnh `![...]`, dòng trống, dòng số/ISBN/URL; bỏ `///` OCR dư; dùng glossary.
2. Cập nhật: `translated_text`, `translated_at` (giờ ISO hiện tại, VD `2026-07-31T00:00:00`), `word_count_translated`. Giữ nguyên field khác. Ghi bằng `json.dumps(data, ensure_ascii=False, indent=2)` UTF-8.
3. Chunk ngắn tự dịch; chunk dài dùng **subagent** dịch rồi đọc lại kiểm tra. Kiểm tra số dòng sau mỗi chunk, nếu lệch thì dịch lại.
4. In tiến độ mỗi 5 chunk: "Đã dịch x/n".

## H. QA
- Nếu có `glossary\<slug>.csv` + progress đầy đủ: chạy QA từng chunk hoặc gọi `.venv\Scripts\python.exe scripts\run_pipeline.py --book <book> --slug <slug> --from-step 8` (bước 8 = QA). In báo cáo cho người dùng; sửa các lỗi rõ ràng (Hán sót, mojibake) nếu dễ.

## I. Merge
- ZH: `.venv\Scripts\python.exe scripts\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --format trilingual --force` → `output\<slug>_trilingual.md`; rồi `.venv\Scripts\python.exe scripts\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --force` → `output\<slug>_translated.md`. Tạo `output\<slug>\` và di chuyển thành `output\<slug>\<slug>-tamngu.md` + `output\<slug>\<slug>-vi.md`.
- EN: `.venv\Scripts\python.exe scripts\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug>-tmp --output-dir working\tmp\<slug> --force`, rồi `.venv\Scripts\python.exe scripts\make_bilingual.py --source <RAW> --translation working\tmp\<slug>\<slug>-tmp_translated.md --output output\<slug>\<slug>-songngu.md --lang en`; copy sang `output\<slug>\<slug>-vi.md`.

## J. EPUB
- Nếu người dùng muốn file EPUB (hoặc mặc định tạo): gọi pandoc tại `C:\Users\Admin\AppData\Local\Pandoc\pandoc.exe` qua `.venv\Scripts\python.exe scripts\make_epub.py output\<slug>\<slug>-vi.md --title "<Tên sách>" --author "<tác giả nếu biết>" --resource-path "output\<slug>;working\extracted\<slug>"` (nếu pandoc không nằm trong PATH, thử thêm `C:\Users\Admin\AppData\Local\Pandoc` vào PATH tạm hoặc gọi pandoc.exe trực tiếp).

## K. Tổng kết
- In đường dẫn đầy đủ các file output: bản tiếng Việt, tam ngữ (nếu ZH), EPUB.
- KHÔNG tự commit/push (theo AGENTS.md) trừ khi người dùng yêu cầu. Hỏi người dùng có muốn commit/push không.
