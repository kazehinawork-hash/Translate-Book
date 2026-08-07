# 🧠 STATE — Trạng thái sống của dự án

> File này là **bộ nhớ trí nhớ chính** của agent (opencode). ĐƯỢC cập nhật mỗi phiên.
> **ĐẦU PHIÊN**: agent bắt buộc đọc file này + 2 entry cuối `session_log.md` trước khi làm việc.
> **CUỐI PHIÊN / XONG VIỆC**: cập nhật lại để phiên sau nối tiếp chính xác.
> (Có commit — thuộc phạm vi docs, không chứa sản phẩm.)

---

## 📚 Các cuốn sách

| Slug | Ngôn ngữ | Giai đoạn | Ghi chú / Bước tiếp theo |
|------|:--------:|-----------|--------------------------|
| `zuo-yi-ge-gang-gang-hao-de-nu-zi` | ZH | ✅ Hoàn tất | EPUB + audiobook (67 chương). Tác giả Khang Tĩnh Văn |
| `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` | ZH | ✅ Hoàn tất | EPUB + audiobook (65 chương). Tác giả Vi Dương |
| `zuo-yi-ge-you-feng-gu-de-nu-zi` | ZH | ✅ Hoàn tất | EPUB + audiobook (85 chương). Tác giả Vi Dương |
| `ban-co-nam-cho-ngoi` | VI | ✅ Hoàn tất | Audiobook (12 chương). Tác giả Nguyễn Nhật Ánh |
| `la-nam-trong-la` | VI | ✅ Hoàn tất | Audiobook (9 chương). Tác giả Nguyễn Nhật Ánh |
| `eu-bim-task-group-handbook-v2-1` | EN | 📗 Dịch xong | Handbook kỹ thuật BIM/Twin Transition (EU). Đã dịch 9/9 chunk, songngu.md + vi.md + vi.epub. Audiobook chưa làm (sách tài liệu kỹ thuật, tùy chọn) |
| `eu-bim-task-group-handbook-v2-1` | EN | 🔶 Dịch | Handbook BIM/Twin Transition EU (9 chunks). Đã complete 1,4,5,6,7,8 (08-07, nhiều worker song song), còn chunk 2,3 |

**Giai đoạn**: `⛁ Extract → 🔶 Dịch → ⚙️ QA/Merge → 📗 EPUB → 🎧 Audiobook → ✅ Hoàn tất`

---

## 🔨 Đang làm (hiện tại)

- Dịch sách `eu-bim-task-group-handbook-v2-1` (EN→VI) theo batch: `working\progress\eu-bim-task-group-handbook-v2-1\` có 9 chunk. Batch 1 (chunk 1) complete 08-07 (95 dòng, 4787 từ, QA 0 lỗi). Batch 4 (chunk 4) complete 08-07 (84 dòng, 4611 từ, QA 0 lỗi). Batch 6 (chunk 6 CALL TO REALITY) complete 08-07 bởi w-batch7 (87 dòng, 4952 từ, QA 0 lỗi). Batch 8 (chunk 8 References) complete 08-07 (68 dòng, 1146 từ, QA 0 lỗi). Batch 7 (chunk 7 PUBLIC PROCUREMENT) complete 08-07 (143 dòng, 4751 từ, QA 0 lỗi). Batch 5 (chunk 5) complete. Còn chunk 2,3.

---

## ⏳ Việc còn nợ / Đề xuất tiếp theo

- Luồng chính dùng AI Agent trực tiếp, không dùng API; tối ưu bằng cách giảm số lượt trao đổi và số lần Agent phải đọc/ghi file.
- Thay vì dịch từng chunk một, cho Agent xử lý theo batch nhỏ (2–4 chunk hoặc một nhóm theo chương) trong cùng lượt, nhưng vẫn ghi từng progress JSON để resume an toàn.
- Có thể giao các nhóm chương độc lập cho nhiều Agent song song; không chia giữa một chương nếu cần giữ văn phong/ngữ cảnh.
- Tạo prompt/batch manifest cố định, cache glossary và ngữ cảnh chung; Agent chỉ đọc phần cần dịch thay vì quét lại toàn bộ thư mục.
- QA/kiểm tra số dòng và glossary chạy sau mỗi batch; chỉ giao lại các chunk lỗi, không dịch lại cả sách.
- API trong desktop chỉ là hướng tương lai, không dùng làm cơ sở ưu tiên hiệu suất hiện tại.
- Multi-Agent đã có workflow tối đa 2 vòng review/sửa: vòng 1 plan → implement → review; chỉ khi `NEEDS_CHANGES` mới sửa một lần và review 2 rồi bắt buộc dừng. Prompt đã tối ưu theo hướng giảm context lặp nhưng giữ success criteria, file scope, diff và test evidence. Đã ổn định permission bằng `dont-ask`: analyzer chỉ đọc, executor chỉ read/write/edit không dùng shell; test analyzer đọc và executor ghi scratchpad đều đạt. **E2E hai vòng đã chạy thành công 08-07**: analyzer plan → executor implement → review 1 `NEEDS_CHANGES` → executor sửa 1 lần → review 2 `APPROVED`; kết thúc đúng quy tắc giới hạn vòng. Hai phát hiện: (1) executor không có shell nên không tự chạy `git status` — git check nên giao orchestrator; (2) `.gitignore` chỉ ignore thư mục con cụ thể của `working/`, không ignore toàn bộ — file test tạm nên đặt trong `working/qa/` hoặc thư mục được ignore khác.
- Đã triển khai workflow AI Agent theo batch: `scripts/translate/batch_manifest.py` tạo/claim/complete/fail/verify batch, `.opencode/command/dich.md` bắt buộc dùng manifest + QA batch.
- Đã thêm `scripts/qa/batch_qa.py` kiểm tra rỗng/marker/alignment tam ngữ; `merge_chunks.py` chặn duplicate và total_chunks không nhất quán.
- Audiobook checkpoint được ghi nguyên tử, lưu metadata và chỉ tái dùng WAV khi fingerprint text/voice/tham số khớp; không triển khai TTS song song.
- Compile, smoke test và diagnostics đạt; đã thêm `audio_qa.py` dùng thư viện chuẩn WAV, không phụ thuộc soundfile khi QA.
- QA thực tế đạt cho 3 audiobook ZH: `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` (65 chương), `zuo-yi-ge-you-feng-gu-de-nu-zi` (85 chương), `zuo-yi-ge-gang-gang-hao-de-nu-zi` (67 chương); đủ chapter liên tục, MP3 hợp lệ, duration đọc được.
- Desktop `dotnet restore` + `dotnet build --no-restore` đạt 0 lỗi/0 cảnh báo; diagnostics sạch.
- Pytest chưa chạy được vì `.venv` trỏ Python 3.11 đã gỡ và Python 3.14 chưa cài pytest; unit harness/compile/smoke test đã đạt.

---

## ⏳ Việc còn nợ / Còn dở

- App desktop: chưa kiểm thử runtime vì chưa có API key. Chờ user test.

---

## 🧭 Quyết định gần đây

- App desktop (C# WPF) refactor hoàn tất (0 lỗi, 0 cảnh báo): fix StartTranslateAsync → dịch thật qua API, fix audiobook Python/temperature/--force/CancelCommand/WebView2/CSS/log dấu/LogText cap. Xem chi tiết phần trên.
- Repo git **chỉ chứa CODE**; sản phẩm (bản dịch, glossary, audiobook, EPUB, progress) giữ local/Drive, không commit.
- Lịch sử git đã được rewrite (`filter-branch`) — repo giảm từ ~717MB → 0.4MB, không còn binary.
- Docs rút gọn: README là tài liệu duy nhất; đã xoá `QUICKSTART.md`, `USAGE.md`.
- Triển khai **Memory Bank** (STATE.md + session_log.md + AGENTS.md để agent tự đọc/ghi giữa phiên).

---

## 📝 Ghi chú chung

- **Python 3.11 đã bị gỡ khỏi máy** → venv `.venv` (trỏ 3.11) HỎNG. Script chạy trực tiếp bằng `python` (3.14). Khi dùng `merge_chunks.py` phải luôn truyền `--output-dir` tường minh (PROJECT_ROOT tự dò bị lệch).
- Audiobook venv `working\venv-vieneu\Scripts\python.exe` (Python 3.11) — **đã tạo lại** từ Python 3.11.9 (`C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe`) sau khi base Python 3.14 bị gỡ gây hỏng venv; cài `pip install torch torchaudio` (CPU) + `vieneu==3.2.4`. Chạy OK (torch 2.13.0+cpu, torchaudio 2.11.0+cpu).
- Console Windows mặc định cp1252 → Python cần `sys.stdout.reconfigure(encoding='utf-8')`.
- pandoc tại `C:\Users\RiverWind\AppData\Local\Pandoc\pandoc.exe` (có trong PATH).
- Lệnh dịch trọn sách: `/dich` (copy file vào `input\` rồi gõ lệnh).