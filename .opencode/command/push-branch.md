---
description: Commit toàn bộ thay đổi và push lên một nhánh — hiển thị danh sách nhánh và yêu cầu người dùng xác nhận trước khi push để tránh push nhầm.
agent: build
---

Push toàn bộ thay đổi hiện tại lên **một nhánh do người dùng chọn** trên GitHub (không đụng tới `main` trừ khi người dùng chọn `main`):

1. Chạy `git branch --show-current` để biết nhánh hiện tại, và `git status --short` để xem thay đổi.
2. Nếu có file chưa commit:
   - `git add -A`
   - **Tạo commit message dễ đọc, có cấu trúc:**
     - Chạy `git status --short` và `git diff --stat` (hoặc `git diff --cached --stat`) để biết file nào thay đổi.
     - Tự phân loại + chọn emoji theo đúng kiểu thay đổi:
       - `✨ feat:` — tính năng/script mới
       - `🐛 fix:` — sửa lỗi
       - `📝 docs:` — tài liệu (README, USAGE...)
       - `🔧 config:` — cấu hình (opencode, env...)
       - `♻️ refactor:` — tái cấu trúc
       - `✅ test:` — test
       - `🗑️ chore:` — việc lặt vặt khác
     - Nếu `$ARGUMENTS` có nội dung, dùng làm phần mô tả; ngược lại tự tóm tắt ngắn gọn từ các file thay đổi.
     - Định dạng message (nhiều dòng, nhìn là hiểu):
       ```
       ✨ feat(scope): tóm tắt ngắn về thay đổi

       - scripts/ten-file.py: mô tả ngắn đã đổi gì
       - glossary/ten-sach.csv: mô tả ngắn
       - ...

       📌 N file thay đổi: +X dòng thêm, -Y dòng xóa
       ```
     - In message ra cho người dùng **duyệt/xác nhận** trước khi commit (gõ y/s hoặc sửa lại). Chỉ commit sau khi đồng ý.
   - Nếu không có gì để commit, bỏ qua bước này.
3. **BƯỚC XÁC NHẬN NHÁNH (bắt buộc):**
   - Chạy `git branch --list` (hoặc `git branch -vv`) để liệt kê tất cả nhánh local, đánh dấu `*` nhánh đang đứng.
   - In danh sách nhánh ra cho người dùng, kèm nhánh hiện tại, và **hỏi người dùng chọn chính xác nhánh muốn push** (gõ tên nhánh hoặc số).
   - KHÔNG tự ý push vào nhánh hiện tại hay bất kỳ nhánh nào nếu chưa được người dùng xác nhận rõ ràng.
   - Nếu người dùng nhập tên nhánh không tồn tại: báo lỗi, liệt kê lại danh sách và dừng.
4. Push vào nhánh đã chọn (`TARGET`):
   - Nếu `TARGET` khác nhánh đang đứng: `git checkout <TARGET>` trước, rồi mới push.
   - Nếu nhánh đã có remote tracking (`git rev-parse --abbrev-ref @{u}` thành công): `git push`.
   - Nếu chưa: `git push -u origin <TARGET>` để đặt tracking.
   - Nếu `TARGET` là `main`: cảnh báo rõ ràng "đây là nhánh chính" trước khi push.
5. In kết quả: nhánh đã push, `git log --oneline -3`, hoặc báo lỗi + cách xử lý.
