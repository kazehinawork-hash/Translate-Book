# Prompt: Re-OCR trang lỗi bằng AI vision

> **Dùng cho**: khi MinerU/PaddleOCR trích xuất trang bị lỗi (chữ mờ, thiếu, sai thứ tự)

## Hướng dẫn gửi

Trong chat với AI, upload ảnh trang và paste:

```
Sách "<Tên sách>" trang <số trang> bị OCR lỗi, bạn đọc lại ảnh giúp tôi.

== BỐI CẢNH ==
- Trang trước: <tóm tắt 1-2 câu>
- Trang sau: <tóm tắt 1-2 câu>
- Ngôn ngữ gốc: <ZH | EN | song ngữ>
- Phong cách: <cổ trang | hiện đại | kỹ thuật>

== YÊU CẦU ==
- Đọc chính xác từng dòng
- Giữ nguyên cấu trúc đoạn
- Nếu có phương trình/ký hiệu đặc biệt → dùng LaTeX
- Nếu có bảng → Markdown table

== ẢNH TRANG ==
[Upload ảnh]
```

## Quy tắc

- **Upload ảnh gốc** (không crop trừ khi cần tập trung vùng text)
- Nếu ảnh mờ → báo AI, có thể cần ảnh nét hơn
- Nếu trang có 2 cột → báo AI đọc theo thứ tự trái→phải, trên→dưới
- Văn bản cổ/Hán Việt → có thể cần chú thích về biến thể chữ

## Khi nhận kết quả

- So sánh với trang xung quanh trong `working/extracted/<slug>/raw.md`
- Thay thế phần lỗi bằng text mới
- Đánh dấu trong `working/progress/<slug>/progress.md` mục "Trang OCR lỗi"
