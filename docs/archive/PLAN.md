# PLAN — Kế hoạch tổng thể dự án dịch tài liệu

> Phiên bản: v3.2 — Cập nhật 2026-07-29
> Thay đổi so với v2.1: Dọn dẹp sạch sẽ các script rác (translate_full_pipeline, ocr_easy, _make_epub, v.v.), hoàn thiện luồng Pandoc EPUB (TOC, CSS tối ưu E-ink).
> Trạng thái: Lưu trữ (Archive) nhưng đã được đồng bộ với mã nguồn mới nhất.

---

## Mục lục
1. [Tổng quan](#1-tổng-quan)
2. [Mục tiêu & phạm vi](#2-mục-tiêu--phạm-vi)
3. [Cấu trúc thư mục](#3-cấu-trúc-thư-mục)
4. [Pipeline tổng thể](#4-pipeline-tổng-thể)
5. [Công cụ & thư viện](#5-công-cụ--thư-viện)
6. [Hệ thống Glossary](#6-hệ-thống-glossary)
7. [Cài đặt môi trường (Windows)](#7-cài-đặt-môi-trường-windows)
8. [Quy ước đặt tên & encoding](#8-quy-ước-đặt-tên--encoding)
9. [Lộ trình triển khai](#9-lộ-trình-triển-khai)
10. [Vai trò & trách nhiệm](#10-vai-trò--trách-nhiệm)
11. [Ước lượng thời gian](#11-ước-lượng-thời-gian)
12. [Rủi ro & giải pháp](#12-rủi-ro--giải-pháp)
13. [Lộ trình tự động hóa dài hạn](#13-lộ-trình-tự-động-hóa-dài-hạn)
14. [Câu hỏi mở](#14-câu-hỏi-mở)
15. [Tài liệu tham khảo](#15-tài-liệu-tham-khảo)
16. [Lịch sử thay đổi](#16-lịch-sử-thay-đổi)

---

## 1. Tổng quan

Dự án hỗ trợ dịch tài liệu từ **tiếng Anh** và **tiếng Trung** sang **tiếng Việt** để đọc được. Hệ thống kết hợp:
- **AI (qua chat)** làm engine dịch chính và kiểm tra chất lượng
- **MinerU** (opendatalab) trích xuất text/OCR từ PDF/DOCX/ảnh/scan ra Markdown sạch
- **ebooklib + beautifulsoup4** trích xuất EPUB (MinerU không hỗ trợ EPUB)
- **OpenCC** chuẩn hóa Phồn thể → Giản thể (deterministic, chính xác)
- **Glossary** đảm bảo nhất quán thuật ngữ/tên riêng (2 lớp: thể loại + cuốn sách; 2 dạng: Markdown + CSV)
- **Git** quản lý phiên bản glossary + bản dịch (OneDrive không thay thế được git)
- **Script QA tự động** bắt lỗi nhất quán trước khi người duyệt

### Nguyên tắc thiết kế
- **Chất lượng dịch > số lượng**: dịch trực tiếp Hán tự → VI, không qua Pinyin trung gian (Pinyin mất ngữ nghĩa, LLM dịch từ Pinyin phải đoán lại chữ gốc → tỷ lệ sai cao)
- **Dùng công cụ có sẵn thay vì tự viết**: MinerU giải quyết trích xuất/OCR/layout/header-footer tốt hơn tự viết
- **Tự động hóa chỗ rẻ + giá trị cao**: QA script bắt lỗi glossary rẻ hơn nhiều so với duyệt thủ công

---

## 2. Mục tiêu & phạm vi

### Mục tiêu chính
- Dịch tài liệu EN/ZH → VI chất lượng đọc hiểu
- Hỗ trợ nhiều định dạng: PDF (text + scan), EPUB, DOCX, SRT, TXT, MD
- Giữ được ngữ cảnh và nhất quán thuật ngữ xuyên suốt cuốn sách
- Quy trình lặp lại được, dễ bảo trì

### Phạm vi
- **Đối tượng**: cá nhân, vài cuốn/tháng
- **Ngôn ngữ nguồn**: Tiếng Anh, Tiếng Trung (Giản thể + Phồn thể)
- **Ngôn ngữ đích**: Tiếng Việt
- **Định dạng đầu ra**: Markdown/Text có cấu trúc
- **Không bao gồm (giai đoạn hiện tại)**: tự động hóa toàn bộ, xuất bản thương mại, dịch thời gian thực
- **Có thể mở rộng (lộ trình dài hạn)**: tích hợp API dịch, translation memory

### Yêu cầu đã thống nhất với người dùng
| # | Yêu cầu | Quyết định |
|---|---------|------------|
| 1 | Loại tài liệu | Hỗn hợp nhiều định dạng (PDF, EPUB, DOCX, SRT...) |
| 2 | Quy trình dịch | AI dịch trước → người duyệt lại |
| 3 | Đầu ra | Markdown/Text |
| 4 | Pipeline tiếng Trung | Hán tự → (OpenCC chuẩn hóa) → VI trực tiếp (1 bước) |
| 5 | Quy mô | Cá nhân, vài cuốn/tháng |
| 6 | Glossary | Bắt buộc, theo từng dự án + theo thể loại |
| 7 | Sách scan | Có — dùng MinerU (chính) + PaddleOCR (backup) |

### Quyết định thiết kế quan trọng (cập nhật v2.0)
| Quyết định | Lý do |
|------------|-------|
| **KHÔNG dùng Pinyin làm bước trung gian** | Pinyin là phiên âm, mất ngữ nghĩa (shi = 是/事/时/十/石/使/史/诗/市/识...). LLM dịch từ Pinyin phải đoán lại ký tự gốc → tỷ lệ nhầm cao. LLM hiện đại dịch ZH→VI trực tiếp rất tốt. |
| **Dùng OpenCC chuẩn hóa Phồn/Giản thể** | OpenCC chuyển đổi deterministic, có từ điển cụm từ, chính xác tuyệt đối. Pinyin không giải quyết vấn đề này. |
| **Pinyin chỉ dùng làm phụ chú** | Trong bảng 3 cột cho SRT (Hán tự | Pinyin | VI) hoặc cho mục đích học phát âm. Không phải bước dịch. |
| **Dùng MinerU thay tự viết extract/OCR** | MinerU (75k⭐) giải quyết sẵn PDF/DOCX/ảnh → Markdown, loại header/footer/số trang, layout nhiều cột, bảng biểu. PP-OCRv6, chạy CPU Windows. Tiết kiệm ~3 scripts tự viết. |
| **Glossary có 2 dạng song song** | Markdown cho người đọc, CSV/JSON cho script QA. Bắt buộc dùng CSV/JSON cho tự động kiểm tra. |
| **Glossary theo thể loại** | Tích lũy thuật ngữ giữa các sách cùng thể loại (vd: tien-hiep, ky-nghiep, ky-thuat-it). |
| **Git quản lý phiên bản** | OneDrive không thay thế git: dễ conflict file batch, khó diff. Git init trong thư mục, commit theo ngày. |
| **Quy ước Windows cụ thể** | PowerShell chứ không phải bash, UTF-8 cho mọi file text, slug cho tên thư mục (no diacritics, no spaces). |

---

## 3. Cấu trúc thư mục

```
F:\OneDrive\onyx\Translate Book\
│
├── PLAN.md                  # File này
├── PROCESS.md               # Quy trình chi tiết
├── README.md                # Hướng dẫn nhanh
├── .gitignore               # Loại trừ working/{extracted,chunks,qa} + input/ khỏi git
│
├── input\                   # File gốc chờ xử lý (KHÔNG commit git)
│
├── output\                  # Bản dịch Markdown hoàn chỉnh
│
├── working\                 # File trung gian (xem mục 3.1 bên dưới về git)
│   ├── extracted\           # Markdown sạch từ MinerU (KHÔNG commit git, file to)
│   ├── chunks\              # Văn bản đã chia chunk (KHÔNG commit git, tái tạo được)
│   ├── progress\            # Theo dõi tiến độ từng cuốn (COMMIT - tài sản tích lũy)
│   ├── summary\             # Tóm tắt nội dung + bối cảnh (COMMIT - tài sản tích lũy)
│   └── qa\                  # Báo cáo QA tự động (KHÔNG commit git, file to)
│
├── glossary\                # Bộ nhớ thuật ngữ (commit git)
│   ├── _template.md         # Mẫu chung (Markdown)
│   ├── _template.csv        # Mẫu chung (CSV máy đọc được)
│   ├── _fields.md           # Quy ước các cột CSV (encoding, escape dấu phẩy)
│   ├── genres\              # Glossary theo thể loại (commit git)
│   │   ├── tien-hiep.md     # ✅ Có sẵn
│   │   ├── tien-hiep.csv    # ✅ Có sẵn
│   │   ├── ky-nghiep.md     # Tạo khi cần
│   │   ├── ky-nghiep.csv    # Tạo khi cần
│   │   ├── ky-thuat-it.md   # Tạo khi cần
│   │   └── ky-thuat-it.csv  # Tạo khi cần
│   ├── <ten-sach-slug>.md   # Glossary riêng từng cuốn (Markdown) - copy từ _template
│   └── <ten-sach-slug>.csv  # Glossary riêng từng cuốn (CSV) - copy từ _template
│
├── prompts\                 # Prompt mẫu cho AI
│   ├── en-to-vi.md
│   ├── zh-to-vi.md          # Hán tự → VI trực tiếp (không qua Pinyin)
│   ├── ocr-fallback.md      # Khi MinerU/AI cần re-OCR trang
│   └── review-checklist.md  # Checklist khi duyệt bản dịch
│
└── scripts\                 # Script Python hỗ trợ
    ├── requirements.txt
    ├── _common.py           # Helper: setup_encoding, PROJECT_ROOT
    ├── translate.py         # CLI menu tương tác (cho non-tech)
    ├── translate.bat        # 1-click launcher Windows
    ├── mineru_extract.py    # Wrapper gọi MinerU (PDF/DOCX/ảnh)
    ├── ocr_paddle.py        # OCR backup bằng PaddleOCR (khi MinerU kém)
    ├── epub_extract.py      # Trích xuất EPUB (ebooklib) - vì MinerU không hỗ trợ
    ├── opencc_normalize.py  # Chuẩn hóa Phồn → Giản (t2s)
    ├── chunk_text.py        # Chia chunk theo ranh giới
    ├── detect_language.py   # Phát hiện EN/ZH
    ├── glossary_qa.py       # QA tự động: kiểm tra thuật ngữ, ký tự sót
    ├── srt_translate.py     # SRT: tách batch ra text + ghép lại (KHÔNG dùng API)
    ├── post_extract_qc.py   # QC sau trích xuất: mojibake, dòng trống, lặp
    ├── add_pinyin_annotation.py  # (TÙY CHỌN) Thêm Pinyin làm phụ chú, không bắt buộc
    ├── make_bilingual.py         # Ghép bản gốc + dịch thành file song ngữ (xen kẽ)
    └── run_pipeline.py      # Orchestrator chạy cả pipeline
```

### Quy tắc commit git
- **Có commit**: `PLAN.md`, `PROCESS.md`, `README.md`, `glossary/`, `output/`, `prompts/`, **`working/summary/`**, **`working/progress/`** (tài sản tích lũy, file nhỏ, có giá trị lịch sử)
- **Không commit**: `input/` (file gốc có thể có bản quyền), `working/extracted/` (file to, tái tạo được), `working/chunks/` (tái tạo được), `working/qa/` (file to, tái tạo được)
- OneDrive vẫn sync toàn bộ để backup, nhưng git mới là source of truth cho phiên bản
- Xem chi tiết trong `.gitignore`

---

## 4. Pipeline tổng thể

```
┌─────────────────────────────────────────────┐
│ INPUT: File gốc                             │
│ (PDF text / PDF scan / EPUB / DOCX / SRT...) │
└──────────────────────┬──────────────────────┘
                       ↓
        ┌──────────────────────────┐
        │ B1. Trích xuất           │
        │  • PDF/DOCX/ảnh: MinerU  │
        │  • EPUB: epub_extract.py │
        │  • Scan: tự OCR          │
        │  → Markdown sạch          │
        │  (đã loại header/footer,  │
        │   sửa layout, số trang)   │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B1.5. QC sau trích xuất   │
        │  • Tỷ lệ ký tự lạ        │
        │  • Đoạn trống bất thường  │
        │  • Lặp dòng (OCR dính    │
        │    header)                │
        │  • Mojibake               │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B2. Phát hiện ngôn ngữ    │
        │  EN / ZH / mixed         │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B2.5. Chuẩn hóa ZH       │
        │  • OpenCC Phồn → Giản    │
        │  • (nếu phát hiện Phồn)  │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B3. Chia chunk            │
        │  • Ưu tiên ranh giới     │
        │    (chương, đoạn, scene)  │
        │  • EN: 500-1500 từ       │
        │  • ZH: 1500-3000 chữ     │
        │  • Overlap 1-2 câu       │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B4. Dịch                  │
        │  • EN → VI: 1 bước       │
        │  • ZH → VI: 1 bước       │
        │    (trực tiếp, không     │
        │     qua Pinyin)           │
        │  • Áp glossary            │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B4.5. QA tự động          │
        │  • Thuật ngữ glossary    │
        │    còn sót chưa dịch     │
        │  • Ký tự Hán/EN sót     │
        │  • (SRT: số dòng,        │
        │    timestamp khớp gốc)   │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B5. Xuất Markdown         │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B5.5. File song ngữ      │
        │  (tùy chọn)              │
        │  make_bilingual.py       │
        │  → file gốc + dịch xen  │
        │    kẽ để review song     │
        │    song                   │
        └────────────┬─────────────┘
                     ↓
        ┌──────────────────────────┐
        │ B6. Người duyệt           │
        │  • Đọc & sửa              │
        │  • Cập nhật glossary      │
        │  • git commit             │
        └──────────────────────────┘
```

### Pipeline tiếng Trung (chi tiết)

```
Hán tự (Phồn hoặc Giản)
    ↓ [OpenCC: t2s (Phồn → Giản)]
Hán tự chuẩn (Giản thể)
    ↓ [AI: dịch trực tiếp Hán tự → VI]
Tiếng Việt bản dịch
    ↓ [Áp glossary, ghi chú thuật ngữ mới]
Output Markdown
```

**Lý do KHÔNG qua Pinyin:**
- Pinyin mất ngữ nghĩa: 1 âm tiết (shi, jing, yi...) ứng với hàng chục ký tự Hán
- LLM dịch từ Pinyin phải đoán lại ký tự gốc → tỷ lệ nhầm cao
- LLM hiện đại (GPT-4/Claude/Gemini/Qwen) dịch ZH→VI trực tiếp rất tốt vì hiểu ngữ cảnh cả câu/đoạn
- OpenCC xử lý Phồn/Giản chính xác tuyệt đối (deterministic, có từ điển cụm từ)
- Không có dự án dịch thực tế nào trên GitHub dùng Pinyin làm bước trung gian

**Khi nào Pinyin vẫn hữu ích:**
- Phụ chú trong bảng SRT (Hán tự | Pinyin | VI) cho mục đích học phát âm
- Tài liệu dạy tiếng Trung (nếu có)
- **KHÔNG dùng** làm bước dịch trung gian

### Pipeline trích xuất với MinerU

```
File gốc (PDF/DOCX/ảnh)
    ↓ [scripts/mineru_extract.py]
MinerU xử lý:
  - Tự detect có text layer hay không
  - Scan → tự OCR (PP-OCRv6)
  - Loại header/footer/số trang
  - Xử lý layout nhiều cột
  - Nhận diện bảng biểu
    ↓
Markdown sạch → working/extracted/<slug>/raw.md
    ↓ [scripts/post_extract_qc.py]
QC: phát hiện mojibake, dòng trống, lặp
    ↓
Markdown sạch + báo cáo QC

Lưu ý: EPUB KHÔNG dùng MinerU. Dùng scripts/epub_extract.py (ebooklib).
```

**Tại sao MinerU thay vì tự viết:**
- 75k⭐, mature, community lớn
- Giải quyết sẵn 6 vấn đề phức tạp: text layer, OCR, header/footer, layout, bảng, thứ tự đọc
- Có bản web zero-install tại mineru.net để test trước khi cài local
- Chạy được CPU-only trên Windows
- Bản 3.4 (6/2026) nâng lên PP-OCRv6

**Khi nào dùng PaddleOCR thay thế:**
- MinerU không cài được
- File cụ thể MinerU xử lý kém (thử PaddleOCR xem có tốt hơn không)
- Trang cụ thể cần re-OCR bằng AI vision (upload ảnh cho tôi)

---

## 5. Công cụ & thư viện

### Công cụ chính
| Công cụ | Vai trò | Ghi chú |
|---------|---------|---------|
| **AI (chat với tôi)** | Engine dịch chính | Qwen, GPT-4, Claude, Gemini đều dịch ZH→VI trực tiếp tốt |
| **MinerU** | Trích xuất/OCR PDF/DOCX/ảnh → Markdown | [opendatalab/MinerU](https://github.com/opendatalab/MinerU) |
| **OpenCC** | Chuẩn hóa Phồn ↔ Giản thể | [BYVoid/OpenCC](https://github.com/BYVoid/OpenCC) |
| **pysrt** | SRT parser giữ timestamp/index | Thay thế xử lý thủ công |
| **PaddleOCR** | OCR backup | [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) |
| **git** | Version control | OneDrive không thay thế |

### Tham khảo cho tương lai
| Công cụ | Vai trò tiềm năng |
|---------|-------------------|
| [bilingual_book_maker](https://github.com/yihong0618/bilingual_book_maker) | Tự động hóa dịch sách bằng LLM, có `--use_context`, `--resume`, prompt tùy biến (nhét glossary vào system role) |
| [docling](https://github.com/docling-project/docling) | IBM, chuẩn hóa đa định dạng → Markdown, thay thế tương đương MinerU |
| [Ebook Translator Calibre Plugin](https://github.com/bookfere/Ebook-Translator-Calibre-Plugin) | Tham khảo workflow dịch ebook + glossary |
| **Qwen-MT** | Dịch model có terminology intervention + translation memory |

### Python packages (`scripts/requirements.txt`)

Xem file `scripts/requirements.txt` để biết danh sách đầy đủ. Quy tắc: **mỗi package 1 dòng** (pip không chấp nhận dấu phẩy phân tách).

Các package chính:
- `mineru` (2.x+; từ MinerU 1.x đổi tên, KHÔNG dùng `magic-pdf` cũ)
- `opencc-python-reimplemented`, `paddleocr`, `paddlepaddle`
- `ebooklib`, `beautifulsoup4` (EPUB — vì MinerU không hỗ trợ)
- `pypdf`, `pdfplumber`, `pymupdf` (PDF backup)
- `python-docx`, `pysrt`
- `pypinyin` (chỉ phụ chú, không dùng dịch), `langdetect`
- `pandas`, `chardet`

### Không cần cài
- AI vision (chính là tôi qua chat)
- OpenCC CLI (chỉ cần Python wrapper `opencc-python-reimplemented`)

---

## 6. Hệ thống Glossary

### 6.1 Cấu trúc 2 lớp

**Lớp 1: Theo thể loại** (`glossary/genres/`)
- Tích lũy giữa các cuốn sách cùng thể loại
- Ví dụ: `tien-hiep.csv` chứa tất cả thuật ngữ tu tiên đã gặp

**Lớp 2: Theo cuốn sách** (`glossary/<slug>.csv`)
- Riêng cho từng cuốn
- Kế thừa + bổ sung từ glossary thể loại
- Có thể override thuật ngữ thể loại nếu cuốn này dùng khác

### 6.2 Định dạng 2 dạng song song

**Markdown (cho người đọc):**
```markdown
# Glossary: <Tên sách>

## Thông tin chung
- Ngôn ngữ gốc: ZH
- Phong cách: cổ trang, trang trọng
- Xưng hô: ta-ngươi

## Nhân vật
| Tên gốc | Tên Việt | Ghi chú |
|---------|----------|---------|
| 张伟 | Trương Vĩ | Nhân vật chính |

## Thuật ngữ
| Tên gốc | Tên Việt | Ghi chú |
|---------|----------|---------|
| 修仙 | Tu tiên | |
| 灵气 | Linh khí | |
```

**CSV (cho script):**
```csv
source,target,type,note,genre,book
张伟,Trương Vĩ,character,nhân vật chính,tien-hiep,ten-sach
修仙,Tu tiên,term,"thuật ngữ tu chân, phổ biến",tien-hiep,ten-sach
灵气,Linh khí,term,,tien-hiep,ten-sach
API,API,term,giữ nguyên EN,ky-thuat-it,ten-sach
```

**Quy ước CSV (rất quan trọng):**
- **Mỗi dòng CSV** ứng với 1 thuật ngữ (không xuống dòng giữa chừng)
- Nếu `note` (hoặc bất kỳ trường nào) chứa **dấu phẩy**, phải bọc trong dấu nháy kép `"..."`
- Cột có giá trị rộng để trống 2 dấu phẩy liên tiếp (xem dòng 灵气 ở trên)
- File CSV phải là **UTF-8 (không BOM)** để tránh lỗi đọc trên Windows
- Dùng `pandas.read_csv(file, encoding='utf-8')` để đọc

> **Lưu ý requirements.txt** (xem mục 5): tương tự quy tắc "mỗi package 1 dòng", KHÔNG dùng dấu phẩy phân tách nhiều package trên 1 dòng.

**Các cột CSV:**
- `source`: từ/cụm gốc
- `target`: bản dịch
- `type`: character | term | place | phrase
- `note`: ghi chú (bọc trong `"..."` nếu có dấu phẩy)
- `genre`: thể loại (để lọc khi áp)
- `book`: cuốn sách cụ thể (rỗng = áp dụng cho cả thể loại)

### 6.3 QA tự động (`scripts/glossary_qa.py`)

Sau mỗi chunk dịch xong, chạy QA script để phát hiện:
- **Thuật ngữ glossary bị dịch sai/lệch**: tìm `source` trong bản dịch mà chưa được thay bằng `target`
- **Ký tự Hán còn sót chưa dịch** (cho sách ZH)
- **Tiếng Anh còn sót chưa dịch** (cho sách EN, trừ thuật ngữ IT đã đánh dấu giữ nguyên)
- **SRT**: số dòng khớp gốc, timestamp không bị xóa, index liên tục

Đây là script **rẻ nhất mà giá trị cao nhất** — bắt lỗi nhất quán trước khi người duyệt.

### 6.4 Quy tắc quản lý
- Tôi sẽ **hỏi trước** khi thêm thuật ngữ mới vào glossary
- Tôi đánh dấu `[TERM-NEW]` khi gặp thuật ngữ có thể mới
- Glossary dùng xuyên suốt cả cuốn — cập nhật liên tục, git commit thường xuyên

---

## 7. Cài đặt môi trường (Windows)

### 7.1 Cài Python
- Tải Python 3.10+ từ [python.org](https://www.python.org/downloads/)
- Tick "Add Python to PATH" khi cài

### 7.2 Cài dependencies
```powershell
# Tạo virtual env (PowerShell)
cd "F:\OneDrive\onyx\Translate Book"
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Cài packages
pip install -r scripts/requirements.txt
```

### 7.3 Cài MinerU
Theo hướng dẫn tại [github.com/opendatalab/MinerU](https://github.com/opendatalab/MinerU):
```powershell
pip install -U mineru
# Tải model weights
mineru-models-download
# Kiểm chứng tham số CLI (mỗi phiên bản có thể khác nhau)
mineru --help
```

**Lưu ý**: Từ MinerU 2.x, package đổi tên từ `magic-pdf` sang `mineru`. CLI là `mineru` (không phải `magic-pdf`). Khi viết `mineru_extract.py` cần `mineru --help` để xác nhận tham số thật (đặc biệt là `--lang`, `--ocr`, `--dpi` ở MinerU 3.4 có thể đã thay đổi).

### 7.4 Test thử MinerU
- Bản web zero-install: [mineru.net](https://mineru.net) — test với 1 file trước khi cài local
- Sau khi cài local, test với 1 ảnh đơn giản

### 7.5 Cài git
- Tải từ [git-scm.com](https://git-scm.com/download/win)
- Hoặc dùng qua VS Code

### 7.6 Khởi tạo git repo

**Quan trọng**: Chạy bước "Tạo file skeleton" (0.4) TRƯỚC bước này. Nếu các file chưa tồn tại, `git add` sẽ báo lỗi.

```powershell
cd "F:\OneDrive\onyx\Translate Book"
git init
git add PLAN.md PROCESS.md README.md .gitignore
git add glossary/ prompts/ scripts/requirements.txt
git commit -m "Initial commit: project structure and docs"
```

---

## 8. Quy ước đặt tên & encoding

### 8.1 Slug tên sách
- **Không dấu, không khoảng trắng, không ký tự đặc biệt**
- Chỉ dùng: a-z, 0-9, dấu gạch ngang
- Ví dụ:
  - "Tu Tiên Trúc" → `tu-tien-truc`
  - "The Pragmatic Programmer" → `the-pragmatic-programmer`
  - "三体" → `san-ti` (chuyển Hán tự sang Pinyin không dấu cho slug)

Script chuyển đổi slug sẽ có trong `scripts/` (nếu cần).

### 8.2 Encoding
- **Tất cả file text phải là UTF-8 (không BOM)**
- Lý do: tránh mojibake với tiếng Trung trên Windows
- Khi tạo file mới bằng Notepad: chọn "Save as" → Encoding: UTF-8
- Khi tạo file bằng PowerShell:
  ```powershell
  # Đảm bảo console output UTF-8
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  $PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
  ```
- Khi tạo file bằng Python: luôn khai báo `encoding='utf-8'`

### 8.3 Path
- Dùng đường dẫn tuyệt đối trong script để tránh lỗi working directory
- Tránh dấu cách trong tên file/thư mục (slug đã loại trừ)
- OneDrive path `F:\OneDrive\...` — lưu ý `\` trong Python string cần escape hoặc dùng raw string `r"F:\..."`

---

## 9. Lộ trình triển khai (4 giai đoạn)

### Giai đoạn 0: Khởi tạo (1 lần)
| Bước | Công việc | Thời gian |
|------|-----------|-----------|
| 0.1 | Cài Python 3.10+ | 5 phút |
| 0.2 | Tạo virtual env + cài requirements | 15-30 phút |
| 0.3 | Cài MinerU + tải model | 15 phút |
| 0.4 | **Tạo file skeleton**: README.md, .gitignore, glossary/_template.md, glossary/_template.csv, glossary/_fields.md, glossary/genres/ với tien-hiep.{md,csv} mẫu, prompts/zh-to-vi.md, **scripts/requirements.txt** (và các script có sẵn khác) | 15 phút |
| 0.5 | Khởi tạo git + commit đầu (xem mục 7.6) | 5 phút |
| 0.6 | Test MinerU với 1 ảnh đơn giản | 10 phút |

**Thứ tự quan trọng**: 0.4 (skeleton) phải xong trước 0.5 (git init), nếu không lệnh `git add` sẽ lỗi vì file chưa tồn tại.

### Giai đoạn 1: Test pipeline EN
- Chạy thử 1 sách tiếng Anh ngắn (~30-50 trang)
- Kiểm tra: MinerU trích text → chia chunk → dịch → QA → xuất MD
- Đánh giá chất lượng, tinh chỉnh prompt

### Giai đoạn 2: Test pipeline ZH
- Chạy thử 1 sách tiếng Trung ngắn
- Kiểm tra: MinerU → OpenCC → dịch trực tiếp → QA
- So sánh chất lượng với dịch qua Pinyin (nếu cần) để xác nhận quyết định

### Giai đoạn 3: Test OCR (sách scan)
- Chạy thử 1 sách scan vài chục trang
- So sánh chất lượng MinerU vs PaddleOCR
- Test quy trình re-OCR bằng AI cho trang lỗi

### Giai đoạn 4: Vận hành
- Xử lý sách thật
- Tích lũy glossary theo thể loại
- Tối ưu quy trình
- Cân nhắc lộ trình tự động hóa (xem mục 13)

---

## 10. Vai trò & trách nhiệm

### AI (tôi) — engine chính
- Dịch EN → VI, ZH → VI (trực tiếp)
- Áp dụng glossary
- Đề xuất thuật ngữ mới (đánh dấu `[TERM-NEW]`)
- Re-OCR trang lỗi (khi upload ảnh)
- Hỗ trợ giải quyết vấn đề kỹ thuật

### Scripts Python — tự động hóa
- MinerU: trích xuất/OCR
- OpenCC: chuẩn hóa Phồn/Giản
- chunk_text: chia chunk theo ranh giới
- glossary_qa: kiểm tra nhất quán
- srt_translate: xử lý SRT giữ timestamp
- post_extract_qc: QC sau trích xuất
- run_pipeline: orchestrator

### Người dùng (bạn) — duyệt & quyết định
- Duyệt bản dịch cuối cùng
- Cập nhật glossary
- Quyết định phong cách dịch
- Theo dõi tiến độ + git commit

---

## 11. Ước lượng thời gian cho 1 cuốn 200 trang

| Khâu | Thời gian | Ghi chú |
|------|-----------|---------|
| Chuẩn bị (glossary, summary) | 1-2 giờ | Làm 1 lần đầu, các chunk sau dùng lại |
| Trích text (MinerU/EPUB) | 5-15 phút | Tự động, có thể chạy batch |
| QC sau trích xuất | 10 phút | Tự động + 10 phút xem báo cáo |
| Chia chunk | 5 phút | Tự động + 15 phút review ranh giới |
| Dịch (~30-50 chunks) | 6-10 giờ thao tác | Chờ AI trả lời + copy/paste |
| QA sau dịch (tự động) | <1 phút/chunk | Script chạy gần như tức thì, 5 phút là duyệt báo cáo |
| Duyệt & sửa | 3-5 giờ | Người đọc + sửa, có QA hỗ trợ |
| Ghép file hoàn chỉnh | 1 giờ | Script ghép + kiểm tra |
| **Tổng** | **~12-20 giờ thao tác** | Ở nhịp 2-3 giờ/ngày ≈ **5-8 ngày** |

So với v1.0: giảm ~1-2 ngày nhờ:
- Bỏ bước dịch qua Pinyin (giảm 50% số lượt gọi AI cho ZH)
- QA tự động (giảm duyệt thủ công)
- MinerU tự xử lý layout/header/footer

---

## 12. Rủi ro & giải pháp

| Rủi ro | Giải pháp |
|--------|-----------|
| Glossary thiếu → dịch không nhất quán | Tạo glossary từ đầu, cập nhật liên tục, có QA script |
| Quên chunk đã dịch | Dùng file `working/progress/<slug>/progress.md` + git log |
| Mất ngữ cảnh giữa các phiên | File `working/summary/<slug>/summary.md` + paste 1-2 đoạn gần nhất |
| MinerU xử lý kém với 1 số file | Thử PaddleOCR; re-OCR trang lỗi bằng AI vision |
| Context window giới hạn | Chia chunk nhỏ, dùng overlap, paste summary |
| Thuật ngữ chuyên ngành sai | Tôi hỏi bạn khi gặp `[TERM-NEW]` + QA tự động |
| Mojibake khi mở file trên Windows | UTF-8 everywhere, quy ước trong mục 8 |
| OneDrive sync conflict khi script chạy | `working/extracted/`, `chunks/`, `qa/` không commit git, có thể pause OneDrive khi chạy batch. `working/summary/` và `progress/` thì OK để sync vì file nhỏ |
| Git conflict khi nhiều máy | Commit thường xuyên, pull trước khi sửa |

---

## 13. Lộ trình tự động hóa dài hạn

Giai đoạn hiện tại: workflow chat thủ công với AI (~6-10 giờ thao tác/cuốn).

Khi số lượng sách tăng hoặc muốn tăng tốc, cân nhắc:

### 13.1 Dùng bilingual_book_maker
- Repo: [yihong0618/bilingual_book_maker](https://github.com/yihong0618/bilingual_book_maker)
- Hỗ trợ: EPUB, TXT, MD, SRT, PDF
- Tính năng: `--use_context` (giữ ngữ cảnh), `--resume` (tiếp tục), `--retranslate`, prompt tùy biến có system role (nhét glossary vào)
- Chi phí: Gemini free tier / DeepSeek rất rẻ
- Giữ nguyên: glossary + duyệt thủ công

### 13.2 Dùng Qwen-MT (hoặc LLM API khác) với translation memory
- Dùng TM (translation memory) để tái sử dụng bản dịch cũ
- Có terminology intervention cho glossary
- Script tự động dịch → mình chỉ duyệt + sửa

### 13.3 Lợi ích
- Giảm thao tác tay từ 6-10 giờ xuống còn 1-2 giờ/cuốn (chủ yếu review)
- Glossary tích lũy được dùng xuyên suốt

**Lưu ý**: Chưa triển khai ở giai đoạn này. Workflow chat hiện tại đủ cho "vài cuốn/tháng". Chuyển sang tự động hóa khi cần.

---

## 14. Câu hỏi mở (chờ xác nhận khi bắt đầu)

1. Cấu trúc thư mục mục 3 — OK hay cần điều chỉnh?
2. Đã có Python trên máy chưa?
3. Đã có git chưa? Hay dùng qua VS Code?
4. Bắt đầu từ giai đoạn nào (0/1/2/3/4)?
5. Có muốn tôi tạo sẵn glossary thể loại mẫu (vd: tien-hiep) hay tự tạo khi cần?
6. Có OneDrive đang sync thư mục này không? (để biết có cần loại `working/` khỏi sync)

---

## 15. Tài liệu tham khảo

| Công cụ | Liên quan | URL |
|---------|-----------|-----|
| MinerU | Trích xuất/OCR PDF scan → Markdown, bỏ header/footer, PP-OCRv6, CPU Windows | https://github.com/opendatalab/MinerU |
| OpenCC | Chuyển Phồn ↔ Giản chính xác (deterministic, từ điển cụm từ) | https://github.com/BYVoid/OpenCC |
| PaddleOCR | OCR backup | https://github.com/PaddlePaddle/PaddleOCR |
| docling | Chuẩn hóa đa định dạng → Markdown (IBM) | https://github.com/docling-project/docling |
| bilingual_book_maker | Dịch sách EPUB/TXT/MD/SRT/PDF bằng LLM, có context, resume, prompt tùy biến | https://github.com/yihong0618/bilingual_book_maker |
| Ebook Translator Calibre Plugin | Workflow dịch ebook + glossary | https://github.com/bookfere/Ebook-Translator-Calibre-Plugin |

---

## 16. Lịch sử thay đổi

| Ngày | Phiên bản | Thay đổi |
|------|-----------|----------|
| 2026-07-19 | v1.0 | Khởi tạo kế hoạch |
| 2026-07-19 | v2.0 | Bỏ Pinyin trung gian pipeline; thêm OpenCC, MinerU; thêm glossary CSV/JSON, genre-based, QA script; thêm git; thêm lộ trình tự động hóa; sửa lỗi Windows (PowerShell, UTF-8, slug); đồng bộ PLAN↔PROCESS; thêm tài liệu tham khảo |
| 2026-07-19 | v2.1 | Sửa theo review lần 2: (A1) commit `working/summary/` + `progress/`, exclude `extracted/chunks/qa`; (A2) thống nhất `working/<slug>/raw.md`; (A3) `srt_translate.py` chỉ tách/ghép, không dùng API; (B1) tách EPUB ra `epub_extract.py` riêng; (B2) `requirements.txt` mỗi package 1 dòng; (B3) đổi `magic-pdf` → `mineru`; (B4) đổi `raw-giainen.md` → `raw-hans.md`; (B5) ghi chú kiểm chứng tham số MinerU; (B6) thêm bước 0.4 "tạo file skeleton" trước git init; (C1) sửa ước lượng thời gian; (C2) thêm `detect_language` cho pipeline EN; (C3) quy ước CSV escape dấu phẩy; (C4) `add_pinyin_annotation.py` thành file riêng; (C5) sửa ký tự cây thư mục; (C6) OpenCC pipeline dịch chỉ dùng t2s; (C7) xử lý `prompts/qa-check.md` |
| 2026-07-19 | v2.2 | Implement code theo PLAN/PROCESS: viết 12 file `.py` (10 scripts + 1 orchestrator + 1 helper); fix P0 blockers (4), P1 chất lượng (4), P2 tài liệu (4); thêm `USAGE.md` - hướng dẫn sử dụng thực hành với 4 workflow copy-paste (PDF EN, EPUB ZH, SRT, scan); update README link sang USAGE |
| 2026-07-19 | v2.3 | Thêm giao diện thân thiện cho non-tech: `scripts/translate.py` (CLI menu tương tác 8 lựa chọn, dùng rich), `scripts/translate.bat` (1-click launcher Windows set UTF-8 + activate venv), `QUICKSTART.md` (hướng dẫn 1 trang 3 bước). User chỉ cần double-click `.bat` → chọn số trong menu → làm theo hướng dẫn |
| 2026-07-20 | v2.4 | Thêm `scripts/make_bilingual.py` — ghép bản gốc + dịch thành file song ngữ xen kẽ (EN: gốc đậm + dịch; ZH: gốc đậm + pinyin nghiêng + dịch). Cập nhật prompts (thêm quy tắc 1:1 đoạn), PROCESS.md (bước 3.9/4.9), PLAN.md (directory tree, pipeline), USAGE.md (bước 8), QUICKSTART.md (mẹo), translate.py (menu option 7) |
| 2026-07-29 | v3.2 | Dọn dẹp dự án: xóa bỏ hoàn toàn `ocr_easy.py` và các file rác/cũ (`_make_epub.py`, `translate_full_pipeline.py`). Tối ưu hóa Pandoc EPUB: thêm TOC cho sách tam ngữ, chỉnh CSS thân thiện màn hình E-ink (không in nghiêng Hán tự). |

---

*Tài liệu này là bản kế hoạch tổng thể. Xem [PROCESS.md](./PROCESS.md) để biết quy trình thực hiện chi tiết từng bước, và [README.md](./README.md) để bắt đầu nhanh.*
