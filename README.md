# Translate Book — Dự án dịch tài liệu EN/ZH → VI

> Hệ thống dịch tài liệu tiếng Anh và tiếng Trung sang tiếng Việt, tích hợp AI (qua chat) làm engine dịch chính.

---

## 🚀 Cách nhanh nhất cho người mới

**Double-click `scripts\translate.bat`** → menu hiện ra → chọn số → làm theo hướng dẫn.

Không cần nhớ lệnh, không cần biết PowerShell. Đọc **[QUICKSTART.md](./QUICKSTART.md)** để bắt đầu trong 10 phút.

---

## 📚 Tài liệu

- **[QUICKSTART.md](./QUICKSTART.md)** — Hướng dẫn 1 trang cho non-tech (3 bước)
- **[USAGE.md](./USAGE.md)** — Hướng dẫn sử dụng thực hành (copy-paste commands, 4 workflow: PDF EN, EPUB ZH, SRT, scan)
- **[PLAN.md](./PLAN.md)** — Kế hoạch tổng thể, pipeline, công cụ, lộ trình
- **[PROCESS.md](./PROCESS.md)** — Quy trình chi tiết từng bước, mẫu chat, xử lý sự cố

---

## 🛠 Cách dùng cho người quen tech

Nếu bạn quen command line, dùng trực tiếp các script:

```powershell
# 1. Setup
cd "F:\OneDrive\onyx\Translate Book"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r scripts\requirements.txt
git init && git add PLAN.md PROCESS.md README.md USAGE.md QUICKSTART.md .gitignore glossary\ prompts\ scripts\requirements.txt && git commit -m "Initial commit"

# 2. Trích xuất (PDF EN)
python scripts\mineru_extract.py --input input\<file>.pdf --output working\extracted\<slug>\raw.md --lang en

# 3. Chia chunk
python scripts\chunk_text.py --input working\extracted\<slug>\raw.md --output-dir working\chunks\<slug> --lang en --min-chars 3000 --max-chars 8000 --overlap-chars 200 --respect-headings

# 4. Dịch từng chunk (paste vào chat AI, save vào output\<slug>\)
# 5. QA
python scripts\glossary_qa.py --source working\chunks\<slug>\chunk-001.md --translation output\<slug>\chunk-001.md --glossary glossary\<slug>.csv --lang en --report working\qa\<slug>\chunk-001-qa.md

# 6. Git commit
git add output/<slug>/chunk-001.md glossary/<slug>.* && git commit -m "feat(<slug>): chunk 001"
```

Xem chi tiết trong **[USAGE.md](./USAGE.md)**.

## 📚 Tài liệu

- **[USAGE.md](./USAGE.md)** — Hướng dẫn sử dụng thực hành (copy-paste commands, 4 workflow: PDF EN, EPUB ZH, SRT, scan)
- **[PLAN.md](./PLAN.md)** — Kế hoạch tổng thể, pipeline, công cụ, lộ trình
- **[PROCESS.md](./PROCESS.md)** — Quy trình chi tiết từng bước, mẫu chat, xử lý sự cố

---

## 🗂 Cấu trúc thư mục (rút gọn)

```
Translate Book\
├── input\          # File gốc (không commit git)
├── output\         # Bản dịch Markdown hoàn chỉnh
├── working\        # File trung gian (xem policy git bên dưới)
│   ├── extracted\  # Markdown sạch từ MinerU (KHÔNG commit)
│   ├── chunks\     # Văn bản đã chia chunk (KHÔNG commit)
│   ├── progress\   # Theo dõi tiến độ (CÓ commit - tài sản tích lũy)
│   ├── summary\    # Tóm tắt nội dung (CÓ commit - tài sản tích lũy)
│   └── qa\         # Báo cáo QA (KHÔNG commit)
├── glossary\       # Thuật ngữ (Markdown + CSV, có cả theo thể loại)
├── prompts\        # Prompt mẫu cho AI
├── scripts\        # Script Python hỗ trợ
└── .venv\          # Virtual environment (không commit git)
```

---

## 🛠 Công cụ chính

| Công cụ | Vai trò | Ghi chú |
|---------|---------|---------|
| **AI (chat)** | Engine dịch chính | Hỗ trợ EN→VI và ZH→VI trực tiếp |
| **MinerU** | Trích xuất/OCR PDF, DOCX, ảnh → Markdown | Tự loại header/footer, xử lý layout (KHÔNG hỗ trợ EPUB - dùng `epub_extract.py`) |
| **OpenCC** | Chuẩn hóa Phồn ↔ Giản thể | Deterministic, chính xác |
| **pysrt** | Xử lý SRT giữ timestamp/index | |
| **PaddleOCR** | OCR backup | Khi MinerU không đủ |
| **git** | Version control | OneDrive không thay thế được |

---

## 🔑 Nguyên tắc quan trọng

- **Dịch trực tiếp ZH → VI** (KHÔNG qua Pinyin) — Pinyin mất ngữ nghĩa
- **Glossary có 2 dạng**: Markdown (người đọc) + CSV (script QA)
- **Glossary theo thể loại** (`glossary\genres\`) — tích lũy giữa các cuốn
- **Chunk theo ranh giới** (chương, scene) — không cắt cứng theo số từ
- **UTF-8 cho mọi file text** — tránh mojibake trên Windows
- **Slug cho tên sách** — không dấu, không khoảng trắng
- **QA tự động sau mỗi chunk** — bắt lỗi nhất quán glossary
- **Git commit thường xuyên** — an toàn, dễ rollback

---

## ❓ FAQ

**Hỏi: Tôi có cần cài hết tất cả tools không?**
Đáp: Không. Bắt buộc chỉ có Python + git. MinerU chỉ cần khi có sách scan/PDF. OpenCC chỉ cần khi có sách tiếng Trung Phồn thể. Bạn có thể bắt đầu với việc paste text vào chat cho tôi dịch trước, cài tool dần khi cần.

**Hỏi: Sách của tôi là PDF scan, bắt đầu từ đâu?**
Đáp: Cài MinerU → chạy `python scripts\mineru_extract.py` → file Markdown → chia chunk → dịch. Hoặc upload ảnh từng trang cho tôi qua chat.

**Hỏi: Tôi dịch tiếng Trung, có cần Pinyin không?**
Đáp: Không. Pinyin không phải bước dịch. Chỉ dùng làm phụ chú nếu muốn (vd: bảng 3 cột cho SRT).

**Hỏi: Glossary CSV dùng để làm gì?**
Đáp: Script `glossary_qa.py` đọc CSV để tự động phát hiện thuật ngữ bị dịch sai, ký tự Hán/EN còn sót, v.v. Markdown cho người, CSV cho máy.

**Hỏi: Tại sao dùng OneDrive + git mà không chỉ OneDrive?**
Đáp: OneDrive sync tốt nhưng không hiểu version control, dễ conflict khi nhiều máy, khó diff/xem lịch sử. Git giải quyết các vấn đề đó.

---

## 📞 Khi cần hỗ trợ

Mở chat với tôi, mô tả:
- Bạn muốn làm gì
- Lỗi gặp phải (nếu có)
- Paste error message nếu có

Tôi sẽ hướng dẫn tiếp.
