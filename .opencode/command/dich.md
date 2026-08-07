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
- EPUB: `python scripts\extract\epub_extract.py --input input\<file> --output working\extracted\<slug>\raw.md`
- PDF/DOCX/ảnh: `python scripts\extract\mineru_extract.py --input input\<file> --output working\extracted\<slug>\raw.md --lang <en|zh> --backend pipeline --device auto` (thử `--lang en` trước; nếu raw.md ra toàn chữ Hán thì chạy lại với `--lang zh`)
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
2. Đọc file prompt đó, rồi đọc vài chunk JSON đầu + giữa sách, tự trích danh sách thuật ngữ (tên nhân vật, địa điểm, thuật ngữ) và tạo `glossary\<slug>.csv` với header `source,target,notes` (nếu cuốn đã có genre như tiên hiệp, tham khảo `glossary\genres\*.csv`). Ghi UTF-8.
3. Nếu `glossary\<slug>.csv` đã tồn tại thì giữ nguyên (không tạo lại).
4. In tóm tắt số thuật ngữ cho người dùng xem.

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
- ZH: `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --format trilingual --force` → `output/books/<slug>/final/tamngu.md`; rồi `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --force` → `output/books/<slug>/final/vi.md`.
- EN: `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug>-tmp --output-dir working\tmp\<slug> --force`, rồi `python scripts\output\make_bilingual.py --source <RAW> --translation working\tmp\<slug>\<slug>-tmp_translated.md --output output/books/<slug>/final/songngu.md --lang en`; copy sang `output/books/<slug>/final/vi.md`.

## J. EPUB
- Nếu người dùng muốn file EPUB (hoặc mặc định tạo): gọi pandoc tại `C:\Users\Admin\AppData\Local\Pandoc\pandoc.exe` qua `python scripts\output\make_epub.py output/books/<slug>/final/vi.md --title "<Tên sách>" --author "<tác giả nếu biết>" --resource-path "output/books/<slug>/images;working\extracted\<slug>"` (nếu pandoc không nằm trong PATH, thử thêm `C:\Users\Admin\AppData\Local\Pandoc` vào PATH tạm hoặc gọi pandoc.exe trực tiếp). File EPUB output: `output/books/<slug>/trilingual.epub`.

## K. Audiobook QA và tổng kết
- Sau khi tạo audiobook, chạy QA coverage/chất lượng:
```powershell
python scripts\qa\audio_qa.py --slug <slug>
```
- Báo cáo được ghi tại `working/qa/<slug>/audio-report.json`; phải kiểm tra đủ chapter, file không rỗng, WAV 48 kHz và không clipping. MP3 được đo duration nếu máy có `ffprobe`.
- Nếu `vi.md` thay đổi hoặc đổi voice/tham số TTS, chạy lại audiobook để fingerprint tự buộc tạo lại chapter không tương thích.
- In đường dẫn đầy đủ các file output: `output/books/<slug>/final/vi.md` (bản tiếng Việt), `output/books/<slug>/final/tamngu.md` (tam ngữ, nếu ZH), `output/books/<slug>/trilingual.epub` (EPUB), `output/books/<slug>/audiobook/` và báo cáo QA.
- KHÔNG tự commit/push (theo AGENTS.md) trừ khi người dùng yêu cầu. Hỏi người dùng có muốn commit/push không.
