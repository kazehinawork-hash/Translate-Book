---
description: Đọc bộ nhớ phiên và tóm tắt trạng thái hiện tại trước khi bắt đầu làm việc.
agent: build
---

Đọc bộ nhớ phiên rồi tóm tắt để người dùng biết "đang ở đâu, làm gì tiếp theo":

1. Đọc `docs/STATE.md` và 2 entry CUỐI của `docs/session_log.md`.
2. Tóm tắt ngắn gọn (tiếng Việt):
   - Cuốn sách đang xử lý + giai đoạn + bước tiếp theo.
   - Công việc đang dở / còn nợ.
   - Quyết định gần đây liên quan đến việc sắp làm.
   - Trạng thái git (có thay đổi chưa commit không).
3. Hỏi người dùng muốn làm gì tiếp trong phiên này.

KHÔNG sửa file — chỉ đọc và tóm tắt.