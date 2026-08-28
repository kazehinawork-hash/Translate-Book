---
description: Dịch trọn một cuốn sách (extract → chunk → glossary → dịch → QA → merge → EPUB). Chỉ DỊCH, không tạo audiobook — dùng /audio để tạo audio, /dich_audio để làm cả hai.
agent: build
---

Tự động dịch trọn một cuốn sách từ đầu đến cuối (KHÔNG tạo audiobook — dùng `/audio` hoặc `/dich_audio`). Người dùng KHÔNG làm bước thủ công nào — bạn chạy mọi thứ. `$ARGUMENTS` có thể là: (1) tên file trong `input/` (VD `ten-sach.pdf`), (2) slug sách đã có chunk (VD `zuo-yi-ge-gang-gang-hao-de-nu-zi`), hoặc để trống.

Luồng tổng quát:

## A. Xác định công việc
1. Nếu `$ARGUMENTS` có tên file `.pdf`/`.epub`/`.docx` tồn tại trong `input/` (tìm ở cả 3 thư mục con `input\chua-lam\`, `input\da-dich\`, `input\da-audio\` — **sách mới/đã làm đều có thể chạy lại**) → chạy đủ bước B→J. Lưu ý dùng đường dẫn đầy đủ `input\<thư-mục-con>\<file>`.
2. Nếu `$ARGUMENTS` là slug đã có `working/chunks/<slug>/` hoặc `working/progress/<slug>/` → **sách đang dở**: bỏ qua B, chạy từ D (glossary) hoặc E (skeleton) trở đi.
3. Nếu trống: liệt kê `input/chua-lam/` (chưa làm) + `working/chunks/` + `working/progress/`, hỏi người dùng chọn.
4. Slug mặc định = tên file bỏ đuôi, viết thường, thay khoảng trắng bằng `-`. Nếu người dùng cung cấp `--slug <x>` trong `$ARGUMENTS` thì dùng slug đó.

## B. Extract (chỉ sách mới)
- EPUB (có text layer): `python scripts\extract\epub_extract.py --input input\<file> --output working\extracted\<slug>\raw.md`
- PDF/DOCX/ảnh: `python scripts\extract\mineru_extract.py --input input\<file> --output working\extracted\<slug>\raw.md --lang <en|zh> --backend pipeline --device auto` (thử `--lang en` trước; nếu raw.md ra toàn chữ Hán thì chạy lại với `--lang zh`). `--device auto` tự dùng GPU (torch CUDA trong `.venv`).
- **EPUB scan (toàn ảnh, không text layer) — BẮT BUỘC dùng MinerU** (ưu tiên, chất lượng tốt hơn PaddleOCR rõ rệt — text liền mạch):
  1. Extract ảnh từ EPUB: `python -c "import zipfile,os,re; z=zipfile.ZipFile(r'input\<file>'); os.makedirs(r'working\_ocr_imgs',exist_ok=True); imgs=sorted([x for x in z.namelist() if x.lower().endswith(('.jpg','.jpeg','.png'))], key=lambda n: int(re.search(r'(\d+)',n).group(1)) if re.search(r'(\d+)',n) else 99999); [open(os.path.join(r'working\_ocr_imgs',f'{i+1:03d}{os.path.splitext(n)[1]}'),'wb').write(z.read(n)) for i,n in enumerate(imgs)]; z.close()"`
  2. OCR từng ảnh bằng MinerU (chạy nền, checkpoint theo ảnh): loop gọi `mineru_extract.py --input <ảnh> --output <tmp>.md --lang zh --backend pipeline --device auto`, ghi checkpoint, ghép thành `raw.md` với `## Trang N`.
  3. MinerU ~10-30s/ảnh (320 ảnh ~1.5-2 giờ) — chạy nền, có checkpoint resume.
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
4. **Gộp vào master**: chạy `python scripts\process\merge_glossary.py --book <slug> --author <author> [--genre <genre>]` — thêm thuật ngữ của cuốn vào `glossary\master.csv` (file trung tâm duy nhất, cột `source,target,type,note,book,author,genre`), **không đè mục đã có**. **Sau khi gộp xong, file trung gian `glossary/<slug>.csv` được tự động xóa** để giữ thư mục `glossary/` luôn gọn gàng (chỉ có `master.csv` và `_template.*`). Nếu cuốn thuộc tác giả/thể loại đã có trong master (`van-tinh`, `vi-duong`, `khang-tinh-van`, `tien-hiep`), các thuật ngữ chung đó sẽ **tự áp dụng** khi dịch/QA (không cần copy vào file cuốn). Master tự tách `master_001.csv` khi phình (>300 dòng) — không cần làm gì.
5. In tóm tắt số thuật ngữ cho người dùng xem.

## F. Skeleton progress
- ZH: `python scripts\translate\init_trilingual_skeleton.py --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug>` → tạo `working\progress\<slug>\chunk_<NNN>.json` (`mode=trilingual`, `original_text` 1 câu/dòng, `translated_text` rỗng).
- EN: chạy script tương tự (vẫn tạo được skeleton). Nếu script LỖI với EN: tự tạo `working\progress\<slug>\chunk_<NNN>.json` tối giản cho từng chunk gốc với fields: `chunk_id`, `total_chunks`, `chapter`, `source_text` (bằng `text` của chunk gốc), `translated_text` (`''`), `word_count_source`, `word_count_translated` (`0`), `mode` (`'bilingual'`), `translated_at` (`''`). Ghi bằng `json.dumps(ensure_ascii=False, indent=2)` UTF-8.

## F2. Hồ sơ văn chương (book profile) — TRƯỚC KHI DỊCH (08-14)
- Chạy `python scripts\translate\create_book_profile.py --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug>` — script in ra vài chunk đại diện (đầu/giữa/cuối) + khung hồ sơ.
- **Đọc các chunk đó, tự phân tích và viết `working\profile\<slug>.md`** (UTF-8) gồm: tác giả/thể loại/giọng văn, hệ xưng hô từng cặp nhân vật, cách xử lý hội thoại, thành ngữ đặc trưng, **1 đoạn dịch mẫu chuẩn "láng"**, lưu ý riêng.
- Nếu profile đã tồn tại → giữ nguyên, không tạo lại.
- **Khi dịch mỗi chunk (bước G): ĐỌC profile này** và bám giọng văn/xưng hô/chuẩn mẫu — đây là yêu cầu bắt buộc để bản dịch nhất quán và mượt.

## G. Dịch theo batch (bạn tự dịch — AI chat)
Tạo manifest một lần sau khi có skeleton:
```powershell
python scripts\translate\batch_manifest.py create --slug <slug> --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug> --batch-size 3
```

Mỗi lượt Agent chỉ nhận một batch:
```powershell
python scripts\translate\batch_manifest.py claim --slug <slug> --chunks-dir working\chunks\<slug> --progress-dir working\progress\<slug> --worker <agent-id>
```

1. Đọc JSON của đúng các `chunk_ids` trong batch đã claim; không quét hoặc tự nhận chunk ngoài manifest. Nguồn là `original_text` (trilingual) hoặc `source_text` (bilingual). **Đọc `working\profile\<slug>.md` (nếu có) trước khi dịch** để bám giọng văn/xưng hô/mẫu chuẩn.
2. Dịch theo thứ tự chunk, giữ glossary/ngữ cảnh chung. Trilingual phải giữ đúng số dòng; giữ heading `#`/`##`, dòng ảnh `![...]`, dòng trống, số/ISBN/URL; bỏ `///` OCR dư. Tuân thủ `## LITERARY QUALITY` trong prompt (dịch cả câu/đoạn, tránh lặp từ, hội thoại tự nhiên, xưng hô nhất quán, thuần Việt).
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
- ZH: `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --format trilingual --force --output-dir "output\books\<tên-sách-gốc>\final"` → tạo `<slug>_trilingual.md` → **rename thành `tamngu.md`**; rồi `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug> --force --output-dir "output\books\<tên-sách-gốc>\final"` → tạo `<slug>_translated.md` → **rename thành `vi.md`**. Đồng thời copy file `working\extracted\<slug>\raw.md` vào `"output\books\<tên-sách-gốc>\final\raw.md"`.
- ⚠️ **BẮT BUỘC truyền `--output-dir` tường minh** (merge_chunks tự dò PROJECT_ROOT bị lệch trên máy này — ghi ra sai vị trí nếu bỏ qua). Rename file sau merge vì script đặt tên `<slug>_trilingual.md`/`<slug>_translated.md` thay vì `tamngu.md`/`vi.md`.
- EN: `python scripts\output\merge_chunks.py --progress-dir working\progress\<slug> --book-name <slug>-tmp --output-dir working\tmp\<slug> --force`, rồi `python scripts\output\make_bilingual.py --source <RAW> --translation working\tmp\<slug>\<slug>-tmp_translated.md --output "output\books\<tên-sách-gốc>\final\songngu.md" --lang en`; copy sang `"output\books\<tên-sách-gốc>\final\vi.md"`. Đồng thời copy `working\extracted\<slug>\raw.md` vào `"output\books\<tên-sách-gốc>\final\raw.md"`.
- Sau merge, **verify nguồn dịch không mojibake**: quét ký tự `?` đứng giữa chữ (pattern `[a-zA-ZÀ-ỹ]\?(?=[a-zA-ZÀ-ỹ])`) trong vi.md — nếu > 0 thì chunk tương ứng bị hỏng dấu (thường do ghi qua pipe PowerShell), cần sửa lại chunk đúng UTF-8 rồi merge lại.
- ⚠️ **Đồng bộ mục lục với heading body** (kinh nghiệm 08-17): nếu sách dịch LẠI hoặc chunk 0 giữ nội dung cũ, mục lục (giữa `# Mục lục` và `---`) có thể mang tên bài CŨ không khớp heading thân sách MỚI (vd "Tôi là chỗ dựa của anh" vs "Anh là chỗ dựa của em"). Trước khi kết thúc merge: đọc các heading `#` sau `---` (bỏ `# Mục lục`), **thay toàn bộ khối mục lục bằng đúng danh sách heading body đó** (dùng script Python sửa `chunk_000.json` trước rồi merge lại, hoặc sửa trực tiếp vi.md/tamngu.md). Xác nhận số mục TOC = số heading body.
- **Sách OCR (scan) — BẮT BUỘC gộp câu + bỏ số trang** (sau merge, trước EPUB):
  ```powershell
  python scripts\output\merge_sentences.py --input "output\books\<tên-sách-gốc>\final\vi.md"
  python scripts\output\merge_sentences.py --input "output\books\<tên-sách-gốc>\final\tamngu.md"
  ```
  Script gộp các dòng OCR nửa câu thành câu hoàn chỉnh, **bỏ số trang** (002, 003...) dính vào câu (giữ ISBN/năm/số điện thoại), giữ nguyên `## Chương N` + mục lục. Bản Việt gộp mượt; bản tam ngữ mỗi câu 1 khối Hán/pinyin/Việt.

## J. EPUB
- Nếu người dùng muốn file EPUB (hoặc mặc định tạo): gọi pandoc tại `C:\Users\Admin\AppData\Local\Pandoc\pandoc.exe` qua `python scripts\output\make_epub.py "output\books\<tên-sách-gốc>\final\vi.md" --title "<Tên sách>" --author "<tác giả nếu biết>" --resource-path "output\books\<tên-sách-gốc>\images;working\extracted\<slug>"` (nếu pandoc không nằm trong PATH, thử thêm `C:\Users\Admin\AppData\Local\Pandoc` vào PATH tạm hoặc gọi pandoc.exe trực tiếp).
- **Tên file EPUB cuối = tên sách input** (theo yêu cầu user): chỉ giữ **1 file EPUB ở gốc thư mục** tên `<tên-sách-input>.epub` (vd `做一个刚刚好的女子  不攀附, 不将就 (晚情) (z-library.sk, 1lib.sk, z-lib.sk).epub` — đúng tên file trong input/, có thể giữ cả phần rác). **KHÔNG tạo `final/tamngu.epub` / `final/vi.epub`** — tamngu và vi chỉ cần file `.md` (`final/tamngu.md`, `final/vi.md`).
- **Sách ZH (tam ngữ/pinyin/tiếng Việt có dấu) — BẮT BUỘC nhúng font** nếu không muốn Calibre hiển thị ký tự có dấu thành `?`: dùng pandoc trực tiếp với `--epub-embed-font` + CSS `@font-face`:
  1. CSS tạm khai báo `@font-face { font-family: "NotoSerifSC"; src: url("fonts/NotoSerifSC-VF.ttf"); }` và set `font-family: "NotoSerifSC", serif` cho body/h1-3/p/tam-ngữ.
  2. `pandoc "output\books\<tên-sách-gốc>\final\tamngu.md" -o working\tmp_epub\tamngu.epub --css <css> --epub-embed-font C:\Windows\Fonts\NotoSerifSC-VF.ttf -M title="<Tên sách>" -M author="<tác giả>" --toc` (font lấy từ `C:\Windows\Fonts\NotoSerifSC-VF.ttf` — hỗ trợ Hán + Latin mở rộng + dấu Việt).
  3. **Fix path font**: pandoc ghi `url("fonts/...")` trong CSS (đặt tại `EPUB/styles/`) → dùng Python sửa trong zip thành `url("../fonts/...")`.
  4. Copy `tamngu.epub` → **`output/books/<tên-sách-gốc>/<tên-sách-input>.epub`** (file EPUB duy nhất, tên theo file input). **KHÔNG tạo `final/tamngu.epub` / `final/vi.epub`** — chỉ giữ `.md` trong final/.

## K. Tổng kết
- In đường dẫn đầy đủ các file output: `output/books/<tên-sách-gốc>/final/vi.md` (bản tiếng Việt), `output/books/<tên-sách-gốc>/final/tamngu.md` (tam ngữ, nếu ZH), `output/books/<tên-sách-gốc>/<tên-sách-input>.epub` (EPUB).
- **✅ CHECKLIST BẮT BUỘC trước khi báo xong** (kiểm tra từng mục, đảm bảo KHÔNG lệch rule):
  1. Thư mục output tên = **tên file input** (`output/books/<tên-sách-gốc>/`) — KHÔNG dùng slug Latin.
  2. Có `metadata.json` đầy đủ (slug nội bộ, title, source_file, author, language, genre, has_audio, has_epub, epub_file, created).
  3. **Chỉ 1 file `.epub`** ở gốc, tên `<tên-sách-input>.epub` — **KHÔNG có** `final/*.epub`, **KHÔNG có** `trilingual.epub`/`vi.epub` ở gốc.
  4. `final/` chỉ chứa `.md`: `tamngu.md` (ZH) + `vi.md` (+ `songngu.md` nếu EN).
  5. `vi.md` **0 mojibake** (quét pattern `[a-zA-ZÀ-ỹ]\?(?=[a-zA-ZÀ-ỹ])`).
  6. EPUB ZH **đã nhúng font** Noto Serif SC (nếu không, Calibre hiển thị `?`).
  7. `input/` đã cập nhật trạng thái (`manage_input.py` hoặc thủ công).
- **Cập nhật `metadata.json`** (nếu chưa đầy đủ): đảm bảo có `author`, `language`, `genre`, `has_audio=false`, `has_epub`/`epub_file` tự dò từ thư mục. Ghi bằng Python UTF-8.
- **Cập nhật input/ theo trạng thái (BẮT BUỘC)**: chạy `python scripts\manage_input.py` — file sách dịch xong sẽ vào **`input\da-dich\`** (đã dịch, chưa audio). Lưu ý: `manage_input.py` chỉ quét file ở gốc `input/`, không quét thư mục con — nếu file đã nằm trong thư mục con (vd `chua-lam/`) thì chuyển thủ công qua Python (`shutil.move` vào `da-dich/`).
- KHÔNG tự commit/push (theo AGENTS.md) trừ khi người dùng yêu cầu. Hỏi người dùng có muốn commit/push không.

## ⚠️ Ghi chú chung (kinh nghiệm từ các phiên)
- **KHÔNG bao giờ pipe text tiếng Việt qua PowerShell** (`Get-Content | python ...`) — encoding cp1252 làm hỏng dấu thành `?`. Luôn ghi file UTF-8 bằng Python rồi đọc lại.
- `batch_manifest.py` / `batch_qa.py` / script in tiếng Việt cần `sys.stdout.reconfigure(encoding="utf-8")` (đã fix) — nếu script mới in tiếng Việt lỗi cp1252, thêm dòng này.
- `init_trilingual_skeleton.py` import `add_pinyin` từ `scripts/pinyin/` (đã fix sys.path).
- Xung đột cuDNN DLL trên Windows: **không import torch + paddle trong cùng 1 tiến trình** — MinerU dùng `.venv` (torch), PaddleOCR dùng `working\venv-ocr` (paddle), TTS dùng `working\venv-vieneu` (torch). `ocr_paddle.py` tự relaunch qua venv-ocr khi env hiện tại thiếu paddleocr.
