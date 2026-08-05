---
description: Commit mọi thay đổi hiện tại, gộp nhánh đang làm việc vào main và push source lên GitHub.
agent: build
---

Thực hiện lần lượt để push toàn bộ source của dự án này lên nhánh `main` của GitHub (origin, repo `kazehinawork-hash/Translate-Book`):

1. Chạy `git status --short` và `git branch --show-current` để xem trạng thái và nhánh hiện tại.
2. Nếu có file thay đổi chưa commit:
   - `git add -A`
   - **Tạo commit message dễ đọc, có cấu trúc:**
     - Chạy `git status --short` và `git diff --stat` (hoặc `git diff --cached --stat`) để biết file nào thay đổi.
     - Tự phân loại + chọn emoji theo đúng kiểu thay đổi:
       - `✨ feat:` — tính năng/script mới
       - `🐛 fix:` — sửa lỗi
        - `📝 docs:` — tài liệu (README, AGENTS...)
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
   - Bỏ qua nếu không có gì để commit.
3. Xác định nhánh hiện tại (đặt là `CUR`):
   - Nếu `CUR` đã là `main`: chạy `git pull --rebase origin main` (nếu fail vì conflict thì dừng và báo), rồi `git push origin main` và kết thúc.
   - Nếu `CUR` khác `main`:
     a. `git fetch origin`
     b. `git checkout main` rồi `git pull --rebase origin main`
     c. `git merge <CUR>` — ưu tiên merge không fast-forward (`--no-ff`). Nếu có conflict: `git status` để xem, GIẢI QUYẾT xung đột bằng cách giữ cả hai hoặc theo logic hợp lý, `git add` các file đã xử lý, rồi `git commit`. Nếu không tự quyết được, dừng và báo người dùng.
     d. `git push origin main`
     e. Quay lại nhánh `CUR` bằng `git checkout <CUR>` (giữ nhánh feature cho lần làm việc sau).
4. In kết quả cuối: `git log --oneline -5` và xác nhận đã push thành công (hoặc báo lỗi + cách xử lý).
