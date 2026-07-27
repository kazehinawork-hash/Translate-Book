# 🚀 Quick Start cho người không chuyên tech

> **Chỉ cần 3 bước. Không cần biết lập trình.**

---

## Bước 1: Cài đặt 1 lần (10 phút)

### 1.1. Cài Python
- Tải **Python 3.10+** từ: https://www.python.org/downloads/
- **Quan trọng**: tick ✅ **"Add Python to PATH"** trong lúc cài
- Khởi động lại máy sau khi cài xong

### 1.2. Cài Git
- Tải từ: https://git-scm.com/download/win
- Chọn mặc định hết, cài xong khởi động lại

### 1.3. Khởi tạo dự án (1 lần duy nhất)

Mở **PowerShell** (gõ "powershell" vào Start menu), gõ lệnh sau rồi Enter:

```powershell
cd "F:\OneDrive\onyx\Translate Book"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r scripts\requirements.txt
```

> Nếu lỗi "running scripts is disabled", gõ:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
> rồi chạy lại lệnh trên.

### 1.4. Cài MinerU (chỉ cần nếu có sách PDF scan)

Trong cùng PowerShell:
```powershell
pip install -U mineru
mineru-models-download
```

> Tải model mất 5-10 phút. Bỏ qua nếu chỉ dịch EPUB/TXT.

---

## Bước 2: Bắt đầu dịch sách

### Cách 1: Dùng giao diện menu (KHUYẾN NGHỊ)

1. **Double-click** file `scripts\translate.bat`
2. Chọn **`1`** → Dịch sách mới
3. Chọn file trong danh sách (file phải có sẵn trong `input\`)
4. Đặt tên slug (hoặc Enter để dùng tên mặc định)
5. Chọn ngôn ngữ
6. Đợi tool trích xuất + chia chunk (~1-3 phút)

→ Tool sẽ tự mở chunk đầu tiên bằng Notepad/VS Code.

### Cách 2: Copy file vào input\ thủ công

Nếu tool không tìm thấy file, copy thủ công:

1. Mở thư mục `F:\OneDrive\onyx\Translate Book\input\`
2. Copy file sách (.pdf, .epub, .srt, .docx) vào đó
3. Quay lại tool, chọn lại **`1`**

---

## Bước 3: Dịch từng phần

Với mỗi chunk (phần văn bản), bạn làm theo 4 bước:

### 3.1. Mở chat AI
- Mở chat với tôi (hoặc ChatGPT, Claude, Gemini, Qwen...)

### 3.2. Copy chunk
- Mở file `working\chunks\<tên-sách>\chunk-XXX.md` bằng editor
- **Ctrl+A** (chọn tất cả) → **Ctrl+C** (copy)

### 3.3. Paste vào chat theo mẫu

```
Tôi muốn dịch tiếp cuốn "<Tên sách>" (EN/ZH → VI).

== GLOSSARY CUỐN SÁCH ==
[Open file glossary\<tên-sách>.md → Ctrl+A → Ctrl+C → Paste vào đây]

== YÊU CẦU ==
- Dịch sát nghĩa, tự nhiên
- Giữ tên riêng
- [Các yêu cầu riêng của bạn]

== TEXT GỐC (chunk XXX) ==
[Paste nội dung chunk vừa copy]
```

→ AI sẽ trả lời bằng bản dịch tiếng Việt.

### 3.4. Lưu bản dịch
- **Ctrl+A** (chọn hết bản dịch AI vừa trả) → **Ctrl+C**
- Mở file `output\<tên-sách>\chunk-XXX.md` bằng editor
- **Ctrl+V** (paste) → **Ctrl+S** (lưu)

### 3.5. Quay lại tool
- Quay lại cửa sổ tool, chọn:
  - **`3`** → Chạy QA tự động (kiểm tra lỗi)
  - **`4`** → Git commit (lưu phiên bản)
  - **`2`** → Tiếp tục chunk tiếp theo

---

## 💡 Mẹo

- **Mỗi chunk ~5-10 phút dịch** (bao gồm cả copy/paste)
- **Commit sau MỖI chunk** để không mất dữ liệu
- **Đọc lại glossary** ở đầu phiên chat - giúp AI dùng đúng thuật ngữ
- **File song ngữ**: sau khi dịch xong, chạy `python scripts\make_bilingual.py` để tạo file gốc + dịch xen kẽ (dùng cho review)
- **Gặp lỗi?** Mở chat với tôi, copy lỗi và dán vào - tôi sẽ hướng dẫn tiếp

---

## ❓ FAQ

**Hỏi: Tôi không tìm thấy file PDF khi chọn số 1?**
Đáp: Copy file vào thư mục `input\` trước (xem Bước 2 - Cách 2).

**Hỏi: Chunk là gì?**
Đáp: Mỗi chunk là 1 đoạn văn bản (~500-1500 từ) để dịch. Tool sẽ tự chia sách thành nhiều chunk.

**Hỏi: Tôi dịch tiếng Trung, có cần Pinyin không?**
Đáp: KHÔNG. Dịch thẳng Hán tự → Việt, không cần Pinyin.

**Hỏi: Glossary là gì?**
Đáp: Danh sách thuật ngữ + tên nhân vật + tên riêng, kèm bản dịch cố định. Giúp AI dịch nhất quán.

**Hỏi: Làm sao thêm thuật ngữ mới vào glossary?**
Đáp: Chọn `5` trong menu chính → chọn glossary → sửa file. **Nhớ sửa CẢ file .md và .csv** (cùng tên).

---

## 🆘 Cần trợ giúp?

1. Mở chat với tôi
2. Mô tả: bạn đang làm gì, lỗi gì
3. Copy lỗi (nếu có) → dán vào chat

Tôi sẽ hướng dẫn tiếp! 🙋
