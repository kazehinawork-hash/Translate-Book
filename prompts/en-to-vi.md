# Prompt: Dịch tiếng Anh → Tiếng Việt

> **Đối tác**: dùng với AI (Qwen, GPT-4, Claude, Gemini đều ổn)
> **Dùng cho**: sách, tài liệu kỹ thuật EN → VI
> **File liên quan**: `../glossary/<slug>.md` (glossary cuốn sách), `../glossary/genres/<genre>.md` (glossary thể loại)

## Hướng dẫn gửi

Mở chat với AI, paste theo mẫu dưới (thay nội dung trong ngoặc vuông):

```
Bạn dịch giúp tôi đoạn tiếng Anh sau sang tiếng Việt.

== BỐI CẢNH ==
<Thể loại sách: kỹ thuật IT | tiểu thuyết | học thuật | ...>
<Văn phong mong muốn: trang trọng | thân mật | kỹ thuật>
<Xưng hô: tôi-bạn | ta-ngươi | ...>
<Đối tượng độc giả: ...>

== GLOSSARY BẮT BUỘC DÙNG ==
[paste toàn bộ glossary/<slug>.md + glossary/genres/<genre>.md]

== THUẬT NGỮ MỚI ==
Nếu gặp thuật ngữ chưa có trong glossary, đánh dấu:
[TERM-NEW: từ_gốc → đề_xuất_dịch] cho tôi duyệt.

== TEXT GỐC ==
<paste đoạn EN cần dịch>
```

## Quy tắc dịch

1. **GIỮ TÊN RIÊNG**: nhân vật, địa danh, tên công ty, tên sản phẩm — phiên âm hoặc giữ nguyên
2. **GLOSSARY LÀ MỆNH LỆNH**: nếu glossary đã có, dùng đúng bản dịch đó, KHÔNG tự ý đổi
3. **Thuật ngữ kỹ thuật IT**: giữ nguyên EN kèm giải thích ngắn lần đầu
   - Ví dụ: "API (giao diện lập trình ứng dụng)"
4. **Đoạn thoại**: giữ sắc thái (hài hước, nghiêm túc, giận dữ...)
5. **Format Markdown**: giữ nguyên heading, list, table, code block
6. **Văn phong nhất quán**: paste 1-2 đoạn đã dịch gần nhất để AI bám sát
7. **Đừng dịch từng từ một**: dịch cả câu, cả đoạn cho tự nhiên
8. **GIỮ CẤU TRÚC ĐOẠN VĂN**: mỗi đoạn gốc (paragraph) tạo đúng 1 đoạn dịch — KHÔNG gộp nhiều đoạn thành 1, KHÔNG tách 1 đoạn thành nhiều. Tỷ lệ 1:1 đoạn để đảm bảo bản dịch có thể ghép song song với bản gốc

## Sau khi dịch

- Lưu bản dịch vào `output/<slug>/chunk-XXX.md`
- Chạy QA: `python scripts/glossary_qa.py` (xem PROCESS.md mục 3.6)
- Cập nhật glossary nếu có `[TERM-NEW]` được duyệt
- Git commit

## Lưu ý

- **Không cần Pinyin** (đây là EN, không phải ZH)
- **Không qua API tự động** ở giai đoạn này (xem PLAN.md mục 13 cho lộ trình API)
- Nếu gặp từ đa nghĩa → hỏi tôi trước khi chốt
