# Prompt: Checklist duyệt bản dịch

> **Dùng cho**: khi người dùng (bạn) duyệt bản dịch từng chunk, dùng prompt này để AI hỗ trợ review

## Prompt gửi AI

```
Bạn review giúp tôi bản dịch chunk <số> của cuốn "<Tên sách>".

== BẢN GỐC ==
<paste text gốc EN/ZH>

== BẢN DỊCH HIỆN TẠI ==
<paste bản dịch VI>

== GLOSSARY ==
<paste glossary áp dụng>

== KIỂM TRA ==
1. Tên riêng có khớp glossary không?
2. Thuật ngữ chuyên ngành có khớp không?
3. Có sót ký tự Hán/EN không?
4. Văn phong có nhất quán với 2 đoạn đã dịch trước không?
5. Đoạn thoại có giữ sắc thái không?
6. Có chỗ nào dịch quá máy móc / thiếu tự nhiên không?

== YÊU CẦU ==
- Liệt kê từng vấn đề kèm vị trí (dòng/câu)
- Đề xuất bản sửa
- Nếu có thuật ngữ mới → đánh dấu [TERM-NEW: ...]
```

## Checklist thủ công (bạn tự kiểm)

- [ ] Đọc lướt toàn bộ bản dịch
- [ ] Đối chiếu từng đoạn với gốc
- [ ] Kiểm tra tên riêng, địa danh khớp glossary
- [ ] Kiểm tra thuật ngữ nhất quán
- [ ] Đọc to 1-2 đoạn → bắt câu cụt
- [ ] Cập nhật glossary nếu có thuật ngữ mới (cả .md và .csv)
- [ ] Git commit
