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
cd "<PROJECT_ROOT>"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
> Thay `<PROJECT_ROOT>` bằng đường dẫn thực tế (VD: `F:\OneDrive\onyx\Translate Book`).

> Nếu lỗi "running scripts is disabled", gõ:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
> rồi chạy lại lệnh trên.

### 1.4. Cài MinerU (chỉ cần nếu có sách PDF scan)

Trong cùng PowerShell:
```powershell
pip install -U mineru
mineru-models-download
```

> Tải model mất 5-10 phút. Bỏ qua nếu chỉ dịch EPUB.

---

## Bước 2: Bắt đầu dịch sách

### Cách 1: Double-click `scripts\translate.bat` (KHUYẾN NGHỊ)

1. **Double-click** file `scripts\translate.bat`
2. Menu hiện ra, chọn **`1`** → Dịch sách MỚI
3. Chọn file trong danh sách (file phải có sẵn trong `input\`)
4. Đặt tên slug (hoặc Enter để dùng tên mặc định)
5. Chọn ngôn ngữ: `1` Tiếng Anh, `2` Tiếng Trung, `3` Tự phát hiện
6. Đợi tool tự trích xuất + phát hiện ngôn ngữ + chia chunk (1-3 phút)

→ Dự án đã sẵn sàng, bạn thấy tổng số chunk.

### Cách 2: Mở opencode và gõ lệnh `dich` (tự động hoàn toàn)

Trong opencode (chat), gõ:

```
/dich
```

Rồi chọn file PDF/EPUB trong `input\`. Tool sẽ tự chạy **toàn bộ** pipeline:
trích xuất → QC → phát hiện ngôn ngữ → chia chunk → glossary → **dịch** → QA → merge → EPUB.
Bạn chỉ cần chờ kết quả trong `output\<slug>\`.

---

## Bước 3: Dịch từng phần

Nếu dùng `dich`, bạn không cần làm bước này — bản dịch tự hoàn thành.

Nếu dùng `translate.bat`, sau khi dự án sẵn sàng:

1. Quay lại menu, chọn **`2`** → Tiếp tục sách ĐANG dịch
2. Chọn dự án → tool chỉ ra chunk tiếp theo
3. Dịch tự động bằng **AI chat (opencode)**: mở opencode nói `"dịch tiếp sách <slug>"` — AI tự
   đọc progress, dịch dòng-đối-dòng từng chunk chưa xong và lưu lại (không cần copy/paste)

→ Bản dịch được lưu vào `working\progress\<slug>\` (dạng JSON, có tiến độ).

Sau khi dịch xong:
- Chọn **`3`** → Chạy QA tự động (kiểm tra Hán sót, thuật ngữ)
- Chọn **`4`** → Git commit (lưu phiên bản)

> Ghép thành file hoàn chỉnh + tạo EPUB: mở opencode gõ `/dich` lần nữa (tool tự ghép tiếp
> phần đã dịch) hoặc chạy `python scripts\run_pipeline.py --book "<Ten>" --input input\<file> --lang auto`.

---

## 💡 Mẹo

- **Glossary = file CSV** (`glossary\<slug>.csv`): danh sách thuật ngữ + tên nhân vật với bản dịch cố định, giúp AI dịch nhất quán
- **Sách tiếng Trung** được dịch theo định dạng **tam ngữ**: dòng Hán tự + dòng Pinyin (phụ chú) + dòng dịch tiếng Việt
- **Commit sau MỖI chunk** để không mất dữ liệu
- **Gặp lỗi?** Mở chat với tôi, copy lỗi và dán vào - tôi sẽ hướng dẫn tiếp

---

## ❓ FAQ

**Hỏi: Tôi không tìm thấy file PDF khi chọn số 1?**
Đáp: Copy file vào thư mục `input\` trước (xem Bước 2 - Cách 1).

**Hỏi: Chunk là gì?**
Đáp: Mỗi chunk là 1 đoạn văn bản (~1500-3000 chữ Hán hoặc 3000-8000 từ tiếng Anh) để dịch. Tool sẽ tự chia sách thành nhiều chunk.

**Hỏi: Tôi dịch tiếng Trung, có cần Pinyin không?**
Đáp: Không. Bản dịch tam ngữ gồm 3 dòng: Hán tự gốc → Pinyin (phụ chú) → tiếng Việt. Bạn chỉ cần dịch thẳng Hán tự → Việt; Pinyin được sinh tự động.

**Hỏi: Glossary là gì?**
Đáp: Danh sách thuật ngữ + tên nhân vật + tên riêng, kèm bản dịch cố định, lưu dạng CSV. Giúp AI dịch nhất quán.

**Hỏi: Làm sao thêm thuật ngữ mới vào glossary?**
Đáp: Chọn `5` trong menu translate.bat → chọn glossary → sửa file CSV. Hoặc nhờ tôi (opencode) tạo/sửa giúp.

---

## 🆘 Cần trợ giúp?

1. Mở chat với tôi
2. Mô tả: bạn đang làm gì, lỗi gì
3. Copy lỗi (nếu có) → dán vào chat

Tôi sẽ hướng dẫn tiếp! 🙋
