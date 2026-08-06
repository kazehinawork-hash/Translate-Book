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

**Giai đoạn**: `⛁ Extract → 🔶 Dịch → ⚙️ QA/Merge → 📗 EPUB → 🎧 Audiobook → ✅ Hoàn tất`

---

## 🔨 Đang làm (hiện tại)

- Sửa lỗi app desktop: núi "Bắt đầu dịch" không dịch, "Tạo audio" dùng sai Python + temperature/top_k không truyền, CancelCommand thiếu, log không dấu, LogText vô hạn, WebView2 user-data-folder, CSS tối cứng — **HOÀN THIỆN** (build 0 lỗi 0 cảnh báo).

---

## ⏳ Việc còn nợ / Đề xuất tiếp theo

- *(trống — cả 4 cuốn đã hoàn tất)*

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
- Audiobook venv `working\venv-vieneu\Scripts\python.exe` (3.11) cũng hỏng → **tạo lại từ Python 3.14.5**: `pip install vieneu==3.2.4` + `torch 2.13.0+cpu` + `torchaudio 2.11.0+cpu` (bắt buộc đủ torch/torchaudio nếu không speaker encoder lỗi).
- Console Windows mặc định cp1252 → Python cần `sys.stdout.reconfigure(encoding='utf-8')`.
- pandoc tại `C:\Users\RiverWind\AppData\Local\Pandoc\pandoc.exe` (có trong PATH).
- Lệnh dịch trọn sách: `/dich` (copy file vào `input\` rồi gõ lệnh).