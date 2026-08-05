---
description: Ghi bộ nhớ phiên (STATE + session_log) khi kết thúc công việc và đề xuất commit.
agent: build
---

Kết thúc phiên/hoàn thành nhiệm vụ quan trọng — cập nhật bộ nhớ rồi đề xuất commit:

1. **Cập nhật `docs/STATE.md`**: sửa giai đoạn sách (nếu thay đổi), cập nhật "Đang làm" / "Việc còn nợ" / "Quyết định gần đây".
2. **Thêm 1 entry mới** vào CUỐI `docs/session_log.md` (không sửa entry cũ) theo mẫu:
   - `## YYYY-MM-DD — tiêu đề ngắn`
   - `### Đã làm` — việc hoàn thành
   - `### File đổi` — danh sách file
   - `### Còn dở` — việc chưa xong (nếu có)
   - `### Git` — trạng thái commit/push
3. Đề xuất commit cho 2 file bộ nhớ (theo quy tắc commit trong AGENTS.md, phân loại `📝 docs:`), in message cho người dùng duyệt trước khi commit.
4. Nếu trong phiên còn thay đổi code/docs khác chưa commit, nêu chúng và hỏi người dùng có muốn commit gộp cùng không.