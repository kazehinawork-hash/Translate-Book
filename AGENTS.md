# AGENTS.md — Quy tắc làm việc cho dự án "Translate Book"

Dự án dịch sách tiếng Anh/Trung → tiếng Việt. AI (chat) là engine dịch.

## Ngôn ngữ giao tiếp
- Trả lời bằng **tiếng Việt** (trừ khi người dùng dùng ngôn ngữ khác).

## 🧠 BỘ NHỚ PHIÊN (session memory) — BẮT BUỘC
- **ĐẦU PHIÊN** (trước khi làm bất kỳ việc gì khác): đọc và nắm bắt:
  - `docs/STATE.md` — trạng thái sống (cuốn sách, việc đang làm, còn nợ, quyết định gần đây).
  - 2 entry CUỐI của `docs/session_log.md` — việc gần nhất đã làm / còn dở.
- **CUỐI PHIÊN / KHI XONG MỘT NHIỆM VỤ QUAN TRỌNG**:
  - Cập nhật `docs/STATE.md` (giai đoạn sách, đang làm, còn nợ, quyết định).
  - Thêm 1 entry mới vào CUỐI `docs/session_log.md` (ngày, đã làm, file đổi, còn dở, git).
- Ràng buộc git: 2 file này **CÓ commit** (thuộc phạm vi docs — không chứa sản phẩm; không bỏ vào .gitignore).
- Command hỗ trợ: `/start` (đọc + tóm tắt trạng thái), `/done` (nhắc ghi bộ nhớ + rotate log + đề xuất commit), `/dich` (chỉ DỊCH sách — extract → dịch → merge → EPUB), `/audio` (chỉ tạo AUDIO cho sách đã dịch — nhạc nền AI theo nội dung), `/dich_audio` (dịch + audio trong 1 lệnh). Các lệnh nằm ở `.commandcode/commands/` (Command Code) + `.opencode/command/` (opencode legacy).
- **Rotate session log tự động**: `docs/session_log.md` không tự xoá — khi > 100KB, chạy `python scripts\rotate_session_log.py` (trong `/done`) để dời entry cũ > 3 tháng vào `docs/session_log_archive/<YYYY-MM>.md`, file chính giữ gần nhất.
- **CUỐI PHIÊN: chạy `python scripts\verify_memory.py`** để kiểm tra STATE.md + session_log đã đồng bộ chưa (báo nếu thiếu entry hôm nay / sách mới chưa nhắc / session_log cần rotate). Sửa các cảnh báo trước khi kết thúc.
- Nguyên tắc: agent PHẢI tự đọc bộ nhớ khi bắt đầu — KHÔNG chờ người dùng nhắc.

## GIT — QUY TẮC BẮT BUỘC
- **KHÔNG BAO GIỜ tự động push** lên GitHub (bất kỳ nhánh nào) **trừ khi người dùng ra lệnh rõ ràng**.
- **KHÔNG tự commit** trừ khi được người dùng yêu cầu hoặc đồng ý rõ ràng.
- Khi commit:
  - Kiểm tra `git status --short`, `git branch --show-current`, `git diff --stat` trước.
  - Tạo commit message có cấu trúc, nhiều dòng, phân loại theo emoji:
    - `✨ feat:` — tính năng/script mới
    - `🐛 fix:` — sửa lỗi
    - `📝 docs:` — tài liệu (README, AGENTS...)
    - `🔧 config:` — cấu hình (opencode, env...)
    - `♻️ refactor:` — tái cấu trúc
    - `✅ test:` — test
    - `🗑️ chore:` — việc lặt vặt khác
  - Định dạng message:
    ```
    ✨ feat(scope): tóm tắt ngắn về thay đổi

    - scripts/ten-file.py: mô tả ngắn
    - glossary/ten-sach.csv: mô tả ngắn

    📌 N file thay đổi: +X dòng thêm, -Y dòng xóa
    ```
  - **In message ra cho người dùng duyệt trước khi commit**; chỉ commit sau khi được đồng ý.
- Kiểm tra nhánh hiện tại TRƯỚC khi commit — tránh commit nhầm vào `main` hoặc nhánh feature.
- Có sẵn các command trong `.opencode/command/`:
  - `new-branch` — tạo nhánh feature mới từ main
  - `push-branch` — push lên một nhánh do người dùng chọn (có bước xác nhận nhánh)
  - `push-main` — gộp nhánh hiện tại vào main rồi push (chỉ dùng khi được lệnh)
  - `dich` — tự động dịch trọn một cuốn sách: chỉ cần file PDF/EPUB trong `input/`, lệnh chạy toàn bộ pipeline (extract → QC → detect lang → chunk → glossary → skeleton → dịch bằng AI chat → QA → merge → EPUB → audiobook) rồi trả kết quả trong `output/<slug>/`. Nếu sách đã có chunk/progress thì dịch tiếp phần còn thiếu. Người dùng không phải làm bước thủ công nào. **BƯỚC CUỐI CÙNG (bắt buộc): chạy `python scripts\manage_input.py` để cập nhật `input/`** — file sách chuyển vào `input\chua-lam\` (chưa làm) / `input\da-dich\` (đã dịch) / `input\da-audio\` (đã dịch + audio), để người dùng nhìn input là biết sách xử lý đến đâu.

## VÒNG LẶP DỊCH SÁCH (pipeline)
1. **Extract**: `scripts/pipeline/run_pipeline.py` (MinerU cho PDF, epub_extract cho EPUB) → `working/extracted/<slug>/raw.md`
2. **QC**: `scripts/process/post_extract_qc.py`
3. **Detect lang** + **OpenCC t2s** (nếu zh-Hant)
4. **Chunk**: `scripts/process/chunk_text.py` strategy smart (ZH: min 1500/max 3000 chữ)
5. **Glossary**: `scripts/process/generate_glossary.py` → CSV `glossary/<slug>.csv` (bước trung gian). **Chạy `python scripts\process\merge_glossary.py --book <slug> --author <author> [--genre <genre>]`** để gộp vào **`glossary/master.csv`** (file trung tâm duy nhất, cột `source,target,type,note,book,author,genre`). Master **tự tách** thành `master_001.csv`, ... khi phình (>300 dòng) — `glossary_lib.py` tự gộp khi đọc. Mọi script (QA, translate, pipeline) tự lọc từ master theo slug qua `filter_for_book()` — **không cần file per-book**. Khi cần dọn: `--normalize` (dedupe) / `--check` / `--info`. Nếu master chưa có, gộp lần đầu bằng `python scripts\common\build_master.py`.
6. **Skeleton trilingual**: `scripts/translate/init_trilingual_skeleton.py --chunks-dir ... --progress-dir ...` → progress JSON `{chunk_id, total_chunks, chapter, source_text, translated_text, word_count_source, word_count_translated, mode:'trilingual', original_text, pinyin_text}`
7. **Dịch**: subagent dịch `original_text` dòng-đối-dòng sang `translated_text` (số dòng BẰNG nhau), giữ heading `#`/`##`, giữ nguyên dòng `![...]` ảnh, bỏ `///` OCR dư, dùng glossary, `translated_at="2026-07-31T00:00:00"`, ghi `json.dumps(ensure_ascii=False, indent=2)` utf-8. (KHÔNG dùng Local AI — chất lượng kém, đã bỏ.)
8. **QA**: tạo `working/qa/<slug>/vi_only.md` (nối `translated_text`) → `scripts/qa/glossary_qa.py` (kiểm tra Hán sót <5%, thuật ngữ, mojibake, dòng lặp)
9. **Merge**: `scripts/output/merge_chunks.py --format trilingual --force` → `output/books/<tên-sách-gốc>/final/tamngu.md` (thư mục output = tên file input, có `metadata.json`; chi tiết xem `.opencode/command/dich.md`)
10. **EPUB**: `scripts/output/make_epub.py` (cần pandoc) → **chỉ 1 file `<tên-sách-input>.epub` ở gốc** thư mục output; **KHÔNG tạo** `final/*.epub`/`trilingual.epub`. Sách ZH **bắt buộc nhúng font** Noto Serif SC (tránh Calibre hiện `?`). Chi tiết + checklist bắt buộc xem `.opencode/command/dich.md` mục J/K.
11. **Audiobook** (sách ZH): Clone giọng từ audiobook mẫu → VieNeu-TTS v3 Turbo → tạo audio từ `output/books/<tên-sách-gốc>/final/vi.md` (bản dịch thuần Việt)
12. **Cập nhật input/ (BẮT BUỘC)**: `python scripts\manage_input.py` — di chuyển file nguồn vào `input\da-dich\` (đã dịch) hoặc `input\da-audio\` (đã dịch + audio) để người dùng biết trạng thái.

## BƯỚC 11 — TẠO AUDIOBOOK (VieNeu-TTS v3 Turbo)

### Pipeline
1. **Trích reference audio**: `manage_voice.py extract` — lấy 5-10s giọng đọc sạch từ file audiobook mẫu, save WAV + metadata vào `core/voices/` (chỉ cần làm 1 lần). Dùng `--auto` để tự tìm đoạn giọng sạch bằng energy VAD (không cần chỉ `--start`)
2. **Clone giọng**: `tts.add_voice(name, ref_path)` — tự extract speaker embedding (192-d x-vector) + MOSS code tokens
3. **Đọc text Việt**: Đọc trực tiếp `<slug>-vi.md` (bản dịch thuần Việt từ bước 9 Merge). Text được làm sạch markdown (bảng/link/chú thích/ảnh), đọc cả tên chapter (tắt bằng `--no-read-titles`)
4. **Smart chunk**: Chia text ≤240 ký tự/đoạn (VieNeu limit ~256), giữ nguyên câu, giữ biên đoạn văn (paragraph-aware) → silence dài hơn giữa các đoạn
5. **Generate**: `tts.infer(chunk, voice=name, style="doc_truyen")` từng đoạn. Checkpoint theo chunk (resume nhanh giữa chừng), retry 3 lần
6. **Join**: `np.concatenate(all_audio)` + silence 0.4-0.8s giữa các đoạn → normalize từng chunk (0.95) + fade 10ms + master normalize (0.92) → WAV 48kHz
7. **MP3**: Tự động convert WAV → MP3 128kbps (xóa WAV trừ `--keep-wav`), kèm metadata title/album

### Scripts
- `scripts/audiobook/manage_voice.py` — Quản lý reference audio: extract (có `--auto` VAD), save WAV + metadata, list/info/delete/set-active/active, preview, validate chất lượng (duration/sample rate/peak)
- `scripts/audiobook/audiobook_long.py` — Tạo audio từ -vi.md: auto-detect chapters, `--first`/`--chapter N`/`--sample`/`--force`/`--voice NAME`/`--temperature`/`--top-k`/`--bitrate`/`--no-read-titles`/`--keep-wav`/`--merge`, resume checkpoint (theo chapter + theo chunk), retry, auto MP3. **Chuẩn GPU (08-13)**: `--gpu --batch-size 16` — benchmark RTF 0.12 (nhanh ~2x so với batch-size 8 cũ), chất lượng tương đương. Áp dụng cho mọi sách sau. **Nhạc nền chuẩn (08-13)**: `--music-volume 0.15` (user chốt mức này, nhạc nhỏ hơn 0.20 cũ).

### Env
- venv: `working/venv-vieneu/` (Python 3.11, `pip install vieneu`)
- Chạy GPU: `--gpu --batch-size 16` (RTF ~0.12, chuẩn từ 08-13 — benchmark nhanh ~2x batch 8 cũ, chất lượng tương đương). CPU (ONNX Runtime) RTF ~0.42, chỉ dùng khi không có GPU
- 14 preset voices, emotion tags ([cười]/[thở dài]/[hắng giọng]), 3 styles (tu_nhien/tin_tuc/doc_truyen)
- Voice clone cần 3-8s reference audio sạch

### Output
- `output/books/<slug>/audiobook/ch01.mp3` — audio chapter (MP3 128kbps, ~10MB/chapter, kèm metadata title/album)
- `output/books/<slug>/final/vi.md` — bản dịch thuần Việt (từ bước 9 Merge)
- `output/books/<slug>/final/tamngu.md` — bản tam ngữ
- `output/books/<slug>/<tên-sách-input>.epub` — **1 file EPUB duy nhất ở gốc** (tên theo file input, sách ZH nhúng font Noto Serif SC). KHÔNG tạo `final/*.epub` / `trilingual.epub`.
- `output/books/<slug>/images/` — ảnh từ EPUB
- Progress: `working/progress_audio/<slug>.json`
- Chunk cache để resume: `working/progress_audio/chunks/<slug>/` (tự xóa sau khi chapter xong)

## CẤU TRÚC THƯ MỤC QUAN TRỌNG
- `input/` — file gốc PDF/EPUB, **KHÔNG commit**. Chia 3 thư mục con theo trạng thái (tự động bởi `scripts/manage_input.py`): `chua-lam/` (chưa làm — **bỏ sách mới vào đây**), `da-dich/` (đã dịch, chưa audio), `da-audio/` (đã dịch + audio). Có `README.md` giải thích.
- `output/books/` — sản phẩm, **KHÔNG commit**. Thư mục đặt tên theo **tên sách gốc** (tên file input); mỗi thư mục có `metadata.json` ghi `{"slug": "<slug-nội-bộ>", "title": "...", "source_file": "..."}`. Slug nội bộ dùng cho `working/progress`, `working/chunks`, `glossary`, `progress_audio`. **Rule EPUB: mỗi cuốn CHỈ 1 file `.epub` ở gốc, tên = tên file input** (`<tên-sách-input>.epub`) — KHÔNG tạo `final/*.epub` hay `trilingual.epub` (tamngu/vi chỉ cần `.md` trong `final/`). Sách ZH phải nhúng font Noto Serif SC.
- `working/extracted/`, `working/chunks/`, `working/qa/` — **KHÔNG commit**
- `working/profile/<slug>.md` — hồ sơ văn chương per-book (giọng văn, xưng hô, đoạn mẫu "láng"), tạo ở bước F2 và ĐỌC khi dịch mỗi chunk — **KHÔNG commit** (sản phẩm)
- `working/progress/<slug>/` — chunk đã dịch, **KHÔNG commit** (sản phẩm trung gian)
- `working/progress_audio/` — progress + cache audiobook, **KHÔNG commit** (sản phẩm)
- `working/venv-vieneu/` — venv VieNeu-TTS, **KHÔNG commit**
- `glossary/` — glossary cuốn, **KHÔNG commit** (sản phẩm)
- `output/` — toàn bộ sản phẩm (final/*.md, ảnh, audiobook, epub), **KHÔNG commit**; giữ local/Drive
- `output/samples/` — test samples, **KHÔNG commit**
- `core/` — audio mẫu + reference voices dùng chung, **KHÔNG commit**
- `core/voices/` — reference audio đã extract (WAV + JSON metadata), **KHÔNG commit**
- Scripts chạy bằng `.venv\Scripts\python.exe` (Python 3.11)
- Audiobook scripts chạy bằng `working/venv-vieneu\Scripts\python.exe`

## MÔI TRƯỜNG
- Windows / PowerShell 5.1. Không dùng `&&`; dùng `;` và `if ($?)`.
- Console mặc định cp1252 — khi in ký tự không-ASCII từ Python cần `sys.stdout.reconfigure(encoding='utf-8')`.
- pandoc tại `C:\Users\Admin\AppData\Local\Pandoc\pandoc.exe`.
