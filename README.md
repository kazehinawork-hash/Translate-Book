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

## 🛠 Cách dùng cho người quen tech (Workflow mới)

### Setup

```bash
cd <PROJECT_ROOT>
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Interactive mode (KHUYẾN NGHỊ) — tự động lặp

```bash
# Một lệnh duy nhất: prompt → đợi dịch → save → commit → next
python scripts/translate_helper.py --interactive \
    --chunks-dir "working/chunks/mybook" \
    --progress-dir "working/progress/mybook" \
    --glossary "glossary/mybook.csv" \
    --source-lang English --target-lang Vietnamese \
    --auto-commit
```

### Hoặc dùng pipeline scripts riêng:

```bash
# Pipeline đầy đủ (tự động extract → chunk → glossary prompt)
python scripts/translate_full_pipeline.py --book "MyBook" --input "input/mybook.pdf" --source-lang English

# Agent dịch từng chunk:
python scripts/translate_helper.py --interactive --chunks-dir "working/chunks/mybook" --progress-dir "working/progress/mybook" --glossary "glossary/mybook.csv"

# QA và Merge tự động:
python scripts/translate_full_pipeline.py --book "MyBook" --from-step 5
```

**Workflow tổng quan:**

```
Bước 1: Extract   → scripts/extract_pdf.py (hoặc extract_epub.py, extract_srt.py)
Bước 2: Chunk     → scripts/chunk_text.py (smart chunking, JSON output)
Bước 3: Gen Glossary → scripts/generate_glossary.py (tạo prompt → Agent tạo CSV)
Bước 4: Translate → Agent đọc từng chunk + glossary → working/progress/
Bước 5: QA        → scripts/glossary_qa.py (kiểm tra nhất quán thuật ngữ)
Bước 6: Merge     → scripts/merge_chunks.py (gộp → output/{book}_translated.md)
```

Xem chi tiết trong **[USAGE.md](./USAGE.md)**.

---

## ✅ Thành tựu — 4 cuốn sách đã dịch hoàn thành

| STT | Slug | Tên sách (tạm dịch) | Ngôn ngữ gốc | Định dạng |
|-----|------|---------------------|:------------:|:---------:|
| 1 | `the-alchemist` | *The Alchemist* (Nhà giả kim) — Paulo Coelho | EN | PDF |
| 2 | `nu-zi` | *Nữ tử* (女子) | ZH | EPUB |
| 3 | `wei-yang` | *Vi dương* (微阳) | ZH | EPUB |
| 4 | `you-feng-gu` | *Hữu phụng cốc* (有凤谷) | ZH | EPUB |

Mỗi cuốn đều có bản dịch Markdown + EPUB hoàn chỉnh trong [`output/`](./output/), kèm glossary riêng và báo cáo QA.

---

## 📚 Tài liệu

- **[USAGE.md](./USAGE.md)** — Hướng dẫn sử dụng thực hành (copy-paste commands, 4 workflow: PDF EN, EPUB ZH, SRT, scan)
- **[PLAN.md](./PLAN.md)** — Kế hoạch tổng thể, pipeline, công cụ, lộ trình
- **[PROCESS.md](./PROCESS.md)** — Quy trình chi tiết từng bước, mẫu chat, xử lý sự cố

---

## 🗂 Cấu trúc thư mục

```
Translate Book\
├── input\              # File gốc (KHÔNG commit)
├── output\             # Bản dịch hoàn chỉnh
├── working\
│   ├── extracted\      # Markdown gốc sau extract (KHÔNG commit)
│   ├── chunks\         # Chunk JSON (KHÔNG commit)
│   ├── progress\       # Chunk đã dịch (CÓ commit - tài sản tích lũy)
│   ├── summary\        # Tóm tắt (CÓ commit)
│   └── qa\             # Báo cáo QA (KHÔNG commit)
├── glossary\
│   └── genres\         # Glossary theo thể loại
├── prompts\            # Prompt mẫu cho Agent dịch
├── scripts\            # Python scripts
├── .gitignore
├── README.md
├── USAGE.md
├── QUICKSTART.md
├── PLAN.md
└── PROCESS.md
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
| **chunk_text.py** | Chunking với 4 strategy (smart/paragraph/line/fixed) | JSON output + neighbor context |
| **generate_glossary.py** | Tạo prompt để Agent sinh glossary CSV | Không gọi API |
| **translate_helper.py** | Hỗ trợ Agent dịch (interactive/prepare/save/status/next/auto-commit) | Interactive mode tự động lặp |
| **merge_chunks.py** | Gộp chunk đã dịch → file hoàn chỉnh | |
| **translate_full_pipeline.py** | Orchestrator chạy pipeline | Từng bước hoặc auto |
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
