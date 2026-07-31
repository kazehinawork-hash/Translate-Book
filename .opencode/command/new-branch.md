---
description: Tạo nhánh làm việc mới từ main (đã cập nhật) và chuyển sang nhánh đó, sẵn sàng cho một tính năng.
agent: build
---

Tạo một nhánh làm việc mới tách từ `main` (đã được cập nhật mới nhất từ GitHub) cho dự án này:

1. Chạy `git status --short` để kiểm tra. Nếu có thay đổi chưa commit: cảnh báo người dùng và hỏi xác nhận trước khi tiếp tục (không tự commit nếu chưa được đồng ý).
2. Tên nhánh mới:
   - Nếu người dùng đã nhập sau lệnh (`$ARGUMENTS`), dùng chính tên đó (chuẩn hóa: thay khoảng trắng bằng `-`, bỏ dấu tiếng Việt, viết thường).
   - Nếu trống: hỏi người dùng tên nhánh muốn dùng (gợi ý tiền tố `feature/`).
3. Cập nhật main mới nhất:
   - `git fetch origin`
   - `git checkout main`
   - `git pull --rebase origin main`
4. Tạo nhánh mới từ main:
   - `git checkout -b <tên-nhánh>`
5. Đẩy nhánh lên GitHub để backup: `git push -u origin <tên-nhánh>`.
6. In kết quả: tên nhánh mới, xác nhận đã tạo + push, và `git status` để người dùng bắt đầu làm việc.
