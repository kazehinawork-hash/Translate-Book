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
| `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` | ZH | 🔶 Đã dịch xong | Chưa merge/EPUB/audio. Tác giả Vi Dương |
| `zuo-yi-ge-you-feng-gu-de-nu-zi` | ZH | ✅ Hoàn tất | EPUB + audiobook (85 chương). Tác giả Vi Dương |
| `ban-co-nam-cho-ngoi` | VI | ✅ Hoàn tất | Audiobook (12 chương). Tác giả Nguyễn Nhật Ánh |

**Giai đoạn**: `⛁ Extract → 🔶 Dịch → ⚙️ QA/Merge → 📗 EPUB → 🎧 Audiobook → ✅ Hoàn tất`

---

## 🔨 Đang làm (hiện tại)

- *(trống — không có việc đang dở)*

---

## ⏳ Việc còn nợ / Đề xuất tiếp theo

- `zuo-yi-ge-gang-gang-hao-de-nu-zi-3`: deploy phần thân (merge → EPUB → audiobook) nếu người dùng muốn.
- (Thêm khi phát sinh.)

---

## 🧭 Quyết định gần đây

- Repo git **chỉ chứa CODE**; sản phẩm (bản dịch, glossary, audiobook, EPUB, progress) giữ local/Drive, không commit.
- Lịch sử git đã được rewrite (`filter-branch`) — repo giảm từ ~717MB → 0.4MB, không còn binary.
- Docs rút gọn: README là tài liệu duy nhất; đã xoá `QUICKSTART.md`, `USAGE.md`.
- Triển khai **Memory Bank** (STATE.md + session_log.md + AGENTS.md để agent tự đọc/ghi giữa phiên).

---

## 📝 Ghi chú chung

- Mọi script chạy bằng `.venv\Scripts\python.exe`; audiobook dùng `working\venv-vieneu\Scripts\python.exe`.
- Console Windows mặc định cp1252 → Python cần `sys.stdout.reconfigure(encoding='utf-8')`.
- Atom/pandoc tại `C:\Users\Admin\AppData\Local\Pandoc\pandoc.exe`.
- Lệnh dịch trọn sách: `/dich` (copy file vào `input\` rồi gõ lệnh).