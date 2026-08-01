# AGENTS.md — Quy tắc làm việc cho dự án "Translate Book"

Dự án dịch sách tiếng Anh/Trung → tiếng Việt. AI (chat) là engine dịch.

## Ngôn ngữ giao tiếp
- Trả lời bằng **tiếng Việt** (trừ khi người dùng dùng ngôn ngữ khác).

## GIT — QUY TẮC BẮT BUỘC
- **KHÔNG BAO GIỜ tự động push** lên GitHub (bất kỳ nhánh nào) **trừ khi người dùng ra lệnh rõ ràng**.
- **KHÔNG tự commit** trừ khi được người dùng yêu cầu hoặc đồng ý rõ ràng.
- Khi commit:
  - Kiểm tra `git status --short`, `git branch --show-current`, `git diff --stat` trước.
  - Tạo commit message có cấu trúc, nhiều dòng, phân loại theo emoji:
    - `✨ feat:` — tính năng/script mới
    - `🐛 fix:` — sửa lỗi
    - `📝 docs:` — tài liệu (README, USAGE...)
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
  - `dich` — tự động dịch trọn một cuốn sách: chỉ cần file PDF/EPUB trong `input/`, lệnh chạy toàn bộ pipeline (extract → QC → detect lang → chunk → glossary → skeleton → dịch bằng AI chat → QA → merge → EPUB) rồi trả kết quả trong `output/<slug>/`. Nếu sách đã có chunk/progress thì dịch tiếp phần còn thiếu. Người dùng không phải làm bước thủ công nào.

## VÒNG LẶP DỊCH SÁCH (pipeline)
1. **Extract**: `run_pipeline.py` (MinerU cho PDF, epub_extract cho EPUB) → `working/extracted/<slug>/raw.md`
2. **QC**: `post_extract_qc.py`
3. **Detect lang** + **OpenCC t2s** (nếu zh-Hant)
4. **Chunk**: `chunk_text.py` strategy smart (ZH: min 1500/max 3000 chữ)
5. **Glossary**: `generate_glossary.py` → CSV `glossary/<slug>.csv` (cột `source,target` bắt buộc)
6. **Skeleton trilingual**: `scripts/init_trilingual_skeleton.py --chunks-dir ... --progress-dir ...` → progress JSON `{chunk_id, total_chunks, chapter, source_text, translated_text, word_count_source, word_count_translated, mode:'trilingual', original_text, pinyin_text}`
7. **Dịch**: subagent dịch `original_text` dòng-đối-dòng sang `translated_text` (số dòng BẰNG nhau), giữ heading `#`/`##`, giữ nguyên dòng `![...]` ảnh, bỏ `///` OCR dư, dùng glossary, `translated_at="2026-07-31T00:00:00"`, ghi `json.dumps(ensure_ascii=False, indent=2)` utf-8. (KHÔNG dùng Local AI — chất lượng kém, đã bỏ.)
8. **QA**: tạo `working/qa/<slug>/vi_only.md` (nối `translated_text`) → `glossary_qa.py` (kiểm tra Hán sót <5%, thuật ngữ, mojibake, dòng lặp)
9. **Merge**: `merge_chunks.py --format trilingual --force` → `output/<slug>_trilingual.md`
10. **EPUB**: `make_epub.py` (cần pandoc)

## CẤU TRÚC THƯ MỤC QUAN TRỌNG
- `input/` — file gốc PDF/EPUB, **KHÔNG commit**
- `working/extracted/`, `working/chunks/`, `working/qa/` — **KHÔNG commit**
- `working/progress/<slug>/` — chunk đã dịch, **CÓ commit**
- `glossary/` — glossary cuốn, **có commit**
- `output/` — bản dịch hoàn chỉnh (md + epub + images/), **có commit**
- Scripts chạy bằng `.venv\Scripts\python.exe` (Python 3.11)

## MÔI TRƯỜNG
- Windows / PowerShell 5.1. Không dùng `&&`; dùng `;` và `if ($?)`.
- Console mặc định cp1252 — khi in ký tự không-ASCII từ Python cần `sys.stdout.reconfigure(encoding='utf-8')`.
- pandoc tại `C:\Users\Admin\AppData\Local\Pandoc\pandoc.exe`.
