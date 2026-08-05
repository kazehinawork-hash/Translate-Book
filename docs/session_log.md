# 📔 SESSION LOG — Nhật ký phiên làm việc

> Append-only: mỗi phiên thêm **1 entry ở CUỐI file**. Entry mới nhất nằm dưới cùng.
> **ĐẦU PHIÊN**: agent đọc 2 entry CUỐI để biết việc gần nhất.
> Mỗi entry: `## YYYY-MM-DD` + **Đã làm** / **File đổi** / **Còn dở** / **Git**.

---

## 2026-08-05 — Thiết lập trí nhớ phiên + docs rút gọn

### Đã làm
- **Docs rút gọn**: README trở thành tài liệu duy nhất; gộp nội dung `QUICKSTART.md` + `USAGE.md` vào README rồi xoá cả 2 file (tổng −1.121 dòng). Thêm bảng Troubleshooting.
- **README cập nhật** cho hợp hiện trạng: bảng thành tựu (4 cuốn + audiobook), cấu trúc thư mục đánh dấu commit/không-commit, chính sách git code-only, mục App desktop (C# WPF), path script audiobook, `/dich`.
- **Dọn lịch sử git** (phiên trước): `git filter-branch` bóc toàn bộ sản phẩm khỏi mọi commit → repo ~717MB → 0.4MB; force-push `main`. 129→58 commit.
- **Triển khai Memory Bank**: tạo `docs/STATE.md` + `docs/session_log.md`, cập nhật `AGENTS.md`, thêm command `/start` + `/done`.

### File đổi
- `README.md`, `AGENTS.md`, xoá `QUICKSTART.md`/`USAGE.md`, thêm `docs/STATE.md` + `docs/session_log.md`, `.opencode/command/start.md` + `done.md`.

### Còn dở
- (vẫn đang trong phiên) chưa commit — đang chờ người dùng duyệt.

### Git
- Trạng thái: nhiều thay đổi chưa commit trên `main` (wip). Sẽ tách commit: (1) docs rút gọn + (2) memory system.

> **Lưu ý ghi chép**: entry mới **luôn thêm ở cuối**, không sửa entry cũ.