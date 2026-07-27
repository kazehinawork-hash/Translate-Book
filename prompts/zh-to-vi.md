# Prompt: Dịch Hán tự → Tiếng Việt (trực tiếp, không qua Pinyin)

> Phiên bản: v2.0 — 2026-07-19
> Thay thế cho 2 file cũ: `zh-to-pinyin.md` và `pinyin-to-vi.md` (đã bỏ Pinyin trung gian)

---

## Mục đích

Dịch văn bản **Hán tự (中文)** trực tiếp sang **Tiếng Việt** trong 1 bước, có áp dụng glossary để đảm bảo nhất quán thuật ngữ và tên riêng.

## Tại sao KHÔNG qua Pinyin

- Pinyin là phiên âm, **mất hoàn toàn ngữ nghĩa**
- Một âm tiết (vd: `shi`) ứng với hàng chục ký tự Hán: 是/事/时/市/诗/十/石/使/史/识/世/室/视/试/式/...
- LLM dịch từ Pinyin phải **đoán lại ký tự gốc** → tỷ lệ sai cao
- LLM hiện đại (GPT-4/Claude/Gemini/Qwen) hiểu Hán tự rất tốt, dịch trực tiếp chính xác hơn
- OpenCC xử lý Phồn/Giản thể deterministic (nếu cần), không liên quan Pinyin
- Không có dự án dịch thực tế nào trên GitHub dùng Pinyin làm bước trung gian

## Khi nào dùng prompt này

- Dịch sách tiếng Trung (Giản thể hoặc Phồn thể) sang tiếng Việt
- Dịch phụ đề SRT tiếng Trung
- Dịch tài liệu kỹ thuật, hướng dẫn, bài báo tiếng Trung

## Khi nào KHÔNG dùng prompt này

- Dịch tiếng Anh → dùng `en-to-vi.md`
- Dịch ngôn ngữ khác → hỏi tôi
- Tài liệu chứa Hán Việt cổ, Kanji Nhật, văn bản cổ phức tạp → cần xử lý riêng, hỏi tôi trước

---

## Mẫu prompt đầy đủ

Sao chép và điền thông tin:

```
Bạn là dịch giả chuyên nghiệp dịch Hán tự (中文) sang Tiếng Việt.

== NGÔN NGỮ NGUỒN ==
Hán tự (Giản thể / Phồn thể) — đã được chuẩn hóa về Giản thể bằng OpenCC (nếu cần)

== NGÔN NGỮ ĐÍCH ==
Tiếng Việt

== GLOSSARY CUỐN SÁCH ==
[PASTE TOÀN BỘ NỘI DUNG glossary/<slug>.md Ở ĐÂY]

== GLOSSARY THỂ LOẠI ==
[PASTE glossary/genres/<genre>.md Ở ĐÂY]

== TÓM TẮT BỐI CẢNH ==
[PASTE working/summary/<slug>/summary.md Ở ĐÂY]

== PHONG CÁCH DỊCH ==
- Văn phong: [cổ trang / hiện đại / kỹ thuật / báo chí / v.v.]
- Xưng hô: [ta-ngươi / tôi-bạn / anh-em / v.v.]
- Giọng văn: [trang trọng / thân mật / hài hước / v.v.]
- Giữ nguyên: [thuật ngữ IT, tên riêng nước ngoài, v.v.]

== ĐOẠN ĐÃ DỊCH GẦN NHẤT (làm mẫu phong cách) ==
[PASTE 100-300 chữ từ chunk trước để giữ phong cách nhất quán]

== YÊU CẦU ĐẶC BIỆT ==
- [Các yêu cầu riêng cho cuốn này, vd: "giữ nguyên thuật ngữ tu tiên trong glossary", "dịch thoại tự nhiên như người Việt nói", v.v.]

== QUY TẮC BẮT BUỘC ==
1. Dịch TRỰC TIẾP Hán tự → Tiếng Việt, KHÔNG tạo Pinyin trung gian
2. Tuyệt đối tuân thủ glossary — thuật ngữ/tên riêng phải dùng đúng bản dịch đã thống nhất
3. Gặp thuật ngữ nghi là mới, chưa có trong glossary: đánh dấu [TERM-NEW: <chữ Hán>] ngay trong bản dịch
4. Không dịch: tên riêng nước ngoài đã quen thuộc (vd: New York, Einstein), thuật ngữ IT phổ biến (API, backend)
5. Giữ format Markdown gốc (heading, bold, list, code block)
6. **CODE BLOCK KHÔNG DỊCH**: phần bên trong ``` (code fence) phải giữ NGUYÊN, không dịch, không giải thích. Chỉ dịch text ngoài code block
7. **TABLE giữ nguyên cấu trúc**: hàng cột, delimiter `|`, header separator `|---|` — giữ nguyên, chỉ dịch nội dung ô. KHÔNG gộp hàng, KHÔNG thêm/xóa cột
8. **FORMULA giữ nguyên**: LaTeX inline `$...$` và display `$$...$$` giữ nguyên, không dịch, không chuyển đổi. Chỉ dịch text xung quanh
6. Giữ cấu trúc đoạn văn, không gộp/tách câu tùy tiện
7. Với đoạn thoại: dịch tự nhiên như người Việt nói, không dịch sát từng chữ
8. **GIỮ CẤU TRÚC ĐOẠN VĂN**: mỗi đoạn gốc (paragraph) tạo đúng 1 đoạn dịch — KHÔNG gộp nhiều đoạn thành 1, KHÔNG tách 1 đoạn thành nhiều. Tỷ lệ 1:1 đoạn để đảm bảo bản dịch có thể ghép song song với bản gốc
9. Cuối bản dịch, liệt kê:
   - Tất cả [TERM-NEW] đã đánh dấu
   - Ghi chú thuật ngữ mới gặp (nếu có)
   - Đoạn nào cảm thấy khó dịch, cần người xem lại

== HÁN TỰ CẦN DỊCH ==
<PASTE HÁN TỰ Ở ĐÂY>

== ĐẦU RA MONG MUỐN ==
1. Bản dịch tiếng Việt
2. Danh sách [TERM-NEW] ở cuối
3. Ghi chú khó dịch (nếu có)
```

---

## Ví dụ cụ thể

### Input
```
李明看着窗外的雨，轻轻叹了口气。
他想起三天前师傅说的话："修仙之路，漫漫而修远。你可准备好了？"
"弟子明白。"他低声回答。
```

### Output mẫu (có glossary: 李明 = Lý Minh, 修仙 = Tu tiên, 师傅 = sư phụ)
```
Lý Minh nhìn mưa ngoài cửa sổ, khẽ thở dài.
Anh nhớ lại lời sư phụ ba ngày trước: "Con đường tu tiên, dài đằng đẵng mà xa vời. Ngươi đã chuẩn bị chưa?"
"Đệ tử hiểu rồi." Anh khẽ đáp.

== THUẬT NGỮ MỚI ==
- (không có)

== GHI CHÚ ==
- "修仙之路" dịch "con đường tu tiên" thay vì "đạo tu tiên" để khớp với glossary
```

---

## Prompt rút gọn (khi đã quen)

```
Dịch tiếp chunk Z của cuốn "<Tên sách>" (ZH → VI trực tiếp).

Glossary: [paste]
Summary: [paste]
2 đoạn trước: [paste 100 chữ]

Hán tự:
<PASTE>
```

---

## Mẹo

1. **Luôn paste 1-2 đoạn đã dịch gần nhất** vào prompt — giúp tôi giữ phong cách nhất quán
2. **Glossary càng chi tiết càng tốt** — đầu tư 1-2 giờ glossary ban đầu sẽ tiết kiệm hàng giờ sau
3. **Cập nhật glossary liên tục** — gặp [TERM-NEW] → quyết định ngay → thêm vào CSV + MD → commit git
4. **Chia chunk theo ranh giới** (chương, scene) thay vì cắt cứng theo số chữ
5. **Sau khi tôi dịch xong, copy kết quả → QA script** (`glossary_qa.py`) → sửa lỗi nếu có
