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
- **[docs/archive/PLAN.md](./docs/archive/PLAN.md)** — Kế hoạch tổng thể, pipeline, công cụ, lộ trình (lưu trữ)
- **[docs/archive/PROCESS.md](./docs/archive/PROCESS.md)** — Quy trình chi tiết từng bước, mẫu chat, xử lý sự cố (lưu trữ)

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

**Yêu cầu ngoài:** Cài [pandoc](https://pandoc.org/installing.html) (dùng để tạo EPUB tự động).
Không bắt buộc nếu bạn không cần EPUB — script vẫn chạy bình thường, file .md vẫn được tạo.

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
python scripts/run_pipeline.py --book "MyBook" --input "input/mybook.pdf" --lang en

# Agent dịch từng chunk:
python scripts/translate_helper.py --interactive --chunks-dir "working/chunks/mybook" --progress-dir "working/progress/mybook" --glossary "glossary/mybook.csv"

# QA và Merge tự động:
python scripts/run_pipeline.py --book "MyBook" --from-step 5
```

> Dùng `run_pipeline.py` cho trải nghiệm tốt nhất để tự động hóa toàn bộ quá trình.

**Chạy pipeline đầy đủ — tự động chọn định dạng theo ngôn ngữ:**

```bash
# Một lệnh duy nhất — không cần nhớ thêm flag nào
python scripts/run_pipeline.py --input "input/sach.pdf" --book "Ten Sach" --lang auto

# Kết quả:
#   - Sách ZH → output/ten-sach_trilingual.md (tam ngữ: gốc/pinyin/dịch)
#              → output/ten-sach_trilingual.epub (tự động, nếu có pandoc)
#   - Sách EN → output/ten-sach/ten-sach-vi.md (song ngữ EN+VI căn chỉnh đoạn)
#              → output/ten-sach/ten-sach-vi.epub (tự động, nếu có pandoc)
```

**Workflow tổng quan:**

```
Bước 1: Extract   → scripts/mineru_extract.py (PDF/DOCX/ảnh) hoặc scripts/epub_extract.py (EPUB)
Bước 2: Chunk     → scripts/chunk_text.py (smart chunking, JSON output)
Bước 3: Gen Glossary → scripts/generate_glossary.py (tạo prompt → Agent tạo CSV)
Bước 4: Translate → Agent đọc từng chunk + glossary → ghi vào working/progress/
Bước 5: QA        → scripts/glossary_qa.py (kiểm tra nhất quán thuật ngữ)
Bước 6: Merge     → scripts/merge_chunks.py (gộp → output/{book}/{book}-vi.md; sách ZH: output/{book}_trilingual.md)
Bước 7: EPUB      → scripts/make_epub.py (tự động, dùng pandoc → output/{book}/{book}-vi.epub; sách ZH: output/{book}_trilingual.epub)
```

Xem chi tiết trong **[USAGE.md](./USAGE.md)**.

---

## ✅ Thành tựu — 3 cuốn sách đã dịch hoàn thành

| STT | Slug | Tên sách (tạm dịch) | Ngôn ngữ gốc | Định dạng |
|-----|------|---------------------|:------------:|:---------:|
| 1 | `zuo-yi-ge-gang-gang-hao-de-nu-zi` | *Trở thành người phụ nữ vừa vặn* (做一个刚刚好的女子) — Khang Tĩnh Văn | ZH | EPUB |
| 2 | `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` | *Trở thành người phụ nữ vừa vặn — Tập 3* (做一个刚刚好的女子·第三卷) — Vi Dương | ZH | EPUB |
| 3 | `zuo-yi-ge-you-feng-gu-de-nu-zi` | *Trở thành người phụ nữ có phong thái* (做一个有风骨的女子) — Vi Dương | ZH | EPUB |

Mỗi cuốn đều có bản dịch Markdown + EPUB hoàn chỉnh trong [`output/`](./output/), kèm glossary riêng và báo cáo QA.

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
├── docs/
│   └── archive/
│       ├── PLAN.md
│       └── PROCESS.md
└── ...
```

---

## 📝 Ví dụ output tam ngữ

> Khi dịch sách tiếng Trung với `--trilingual`, Agent output 3-line blocks:

```
今天天气很好。
jīn tiān tiān qì hěn hǎo。
Hôm nay thời tiết rất đẹp。

我们去公园散步。
wǒ men qù gōng yuán sàn bù。
Chúng tôi đi dạo trong công viên。

我明天也要去。
wǒ míng tiān yě yào qù。
Ngày mai tôi cũng sẽ đi。
```

Dùng `scripts/merge_chunks.py --format trilingual` để gộp → `output/{book}_trilingual.md`.
Pipeline tự động chuyển sang `.epub` (có cấu trúc HTML + CSS riêng cho từng dòng) nếu có pandoc.

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
| **run_pipeline.py** | Orchestrator chính (--from-step/--to-step/--auto) | Script chạy toàn bộ pipeline tự động |
| **pandoc** | Chuyển .md → .epub với CSS tùy chỉnh | Cài từ https://pandoc.org/installing.html |
| **add_pinyin.py** | Sinh pinyin từ Hán tự (cấp câu) | JSON output, xử lý text pha Latin |
| **generate_trilingual.py** | Backfill pinyin vào chunk đã dịch | Thêm original+pinyin field, giữ translated |
| **git** | Version control | OneDrive không thay thế được |

---

## Dùng GPU (tùy chọn)

Mặc định `mineru_extract.py` và `ocr_paddle.py` tự động phát hiện GPU và dùng CPU nếu không có.
Nếu bạn có GPU NVIDIA và muốn chạy bằng GPU để tăng tốc:

- **MinerU** (`mineru_extract.py`): Cần cài **torch bản CUDA** (không phải bản CPU mặc định).
  Tra bảng lệnh cài tại: https://pytorch.org/get-started/locally/

- **PaddleOCR** (`ocr_paddle.py`): Cần cài **paddlepaddle-gpu** thay vì paddlepaddle CPU.
  Xem hướng dẫn tại: https://www.paddlepaddle.org.cn/en/install/quick

Sau khi cài đúng bản GPU, script `--device auto` sẽ tự dùng GPU. Có thể ép bằng
`--device cuda` (minerU) hoặc `--device gpu` (PaddleOCR).

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
