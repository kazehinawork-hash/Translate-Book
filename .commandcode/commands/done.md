---
description: Ghi bộ nhớ phiên (STATE + session_log + rotate nếu dài) khi kết thúc công việc và đề xuất commit.
---

Kết thúc phiên/hoàn thành nhiệm vụ quan trọng — cập nhật bộ nhớ, rotate log nếu cần, rồi đề xuất commit:

1. **Cập nhật `docs/STATE.md`**: sửa giai đoạn sách (nếu thay đổi), cập nhật "Đang làm" / "Việc còn nợ" / "Quyết định gần đây".
2. **Thêm 1 entry mới** vào CUỐI `docs/session_log.md` (không sửa entry cũ) theo mẫu:
   - `## YYYY-MM-DD — tiêu đề ngắn`
   - `### Đã làm` — việc hoàn thành
   - `### File đổi` — danh sách file
   - `### Còn dở` — việc chưa xong (nếu có)
   - `### Git` — trạng thái commit/push
3. **Rotate session_log nếu dài** (tự động): chạy `python scripts\rotate_session_log.py` — nếu `docs/session_log.md` > 100KB, các entry cũ (> 3 tháng) được dời sang `docs/session_log_archive/<YYYY-MM>.md`, file chính giữ gần nhất.
4. **Cập nhật input/ nếu phiên có dịch/audio** (bắt buộc theo AGENTS.md): chạy `python scripts\manage_input.py` để file sách chuyển vào `input\chua-lam\` / `da-dich\` / `da-audio\`.
5. Đề xuất commit cho các file bộ nhớ (theo quy tắc commit trong AGENTS.md, phân loại `📝 docs:`), in message cho người dùng duyệt trước khi commit.
6. Nếu trong phiên còn thay đổi code/docs khác chưa commit, nêu chúng và hỏi người dùng có muốn commit gộp cùng không.
