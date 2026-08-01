# USAGE — Hướng dẫn sử dụng dự án (thực hành)

> Tài liệu thực hành - copy-paste commands. Đọc [README.md](./README.md) để hiểu tổng quan, [PROCESS.md](./docs/archive/PROCESS.md) để hiểu chi tiết từng bước.
> Phiên bản: v3.3 — Cập nhật 2026-07-31

---

## 📋 Mục lục

1. [Setup 1 lần (10-15 phút)](#1-setup-1-lần-10-15-phút)
2. [Dịch 1 cuốn sách PDF tiếng Anh](#2-dịch-1-cuốn-sách-pdf-tiếng-anh)
3. [Dịch 1 cuốn EPUB tiếng Trung](#3-dịch-1-cuốn-epub-tiếng-trung)
4. [Dịch 1 file SRT phụ đề](#4-dịch-1-file-srt-phụ-đề)
5. [Dịch sách scan (PDF ảnh)](#5-dịch-sách-scan-pdf-ảnh)
6. [Cập nhật glossary](#6-cập-nhật-glossary)
7. [Git workflow hàng ngày](#7-git-workflow-hàng-ngày)
8. [Troubleshooting nhanh](#8-troubleshooting-nhanh)
9. [Tam ngữ (Chinese → Pinyin → Vietnamese)](#9-tam-ngữ-chinese--pinyin--vietnamese)
10. [Workflow mới: Agent-first](#10-workflow-mới-agent-first-khuyến-nghị)
11. [Interactive mode chi tiết](#11-interactive-mode-chi-tiết)

---

## 1. Setup 1 lần (10-15 phút)

> Thực hiện 1 lần trên mỗi máy. Sau đó bỏ qua mục này.

### 1.1. PowerShell: bật UTF-8 mặc định

**Quan trọng** - chạy 1 lần để PowerShell in được tiếng Việt:

```powershell
# Mở PowerShell as Administrator, chạy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Thêm vào profile để tự động chạy mỗi session:
notepad $PROFILE
# Thêm 2 dòng này vào file:
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
# Lưu, đóng PowerShell, mở lại
```

### 1.2. Tạo virtual env + cài packages

```powershell
cd "<PROJECT_ROOT>"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

> **Lưu ý**: Thay `<PROJECT_ROOT>` bằng đường dẫn thực tế (VD: `F:\OneDrive\onyx\Translate Book`).
> Trên macOS/Linux: `cd /path/to/Translate Book && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

Sau này mỗi lần mở PowerShell mới:
```powershell
cd "F:\OneDrive\onyx\Translate Book"
.\.venv\Scripts\Activate.ps1
```

### 1.3. Cài MinerU (chỉ cần cho PDF/DOCX scan)

```powershell
pip install -U mineru
mineru-models-download
```

> Tải model mất ~5-10 phút (~2GB). Chỉ cần 1 lần.

### 1.4. Khởi tạo git (chỉ lần đầu)

```powershell
cd "F:\OneDrive\onyx\Translate Book"
git init
git config user.name "Tên của bạn"
git config user.email "email@example.com"

# Commit ban đầu
git add docs/archive/PLAN.md docs/archive/PROCESS.md README.md USAGE.md .gitignore
git add glossary\ prompts\ scripts\requirements.txt
git commit -m "Initial commit: project structure and docs"
```

---

## 2. Dịch 1 cuốn sách PDF tiếng Anh

> Ví dụ cuốn "The Pragmatic Programmer" PDF, slug=`pragmatic-programmer`.

> **Khuyến nghị**: dùng pipeline tự động (`run_pipeline.py`) — không cần tạo thư mục,
> copy glossary hay dịch từng chunk thủ công. Để dịch bằng AI chat trong opencode,
> chỉ cần gõ lệnh `/dich` và chọn file trong `input\` (xem AGENTS.md).

### Bước 1: Chuẩn bị (1 phút)

```powershell
cd "<PROJECT_ROOT>"
.\.venv\Scripts\Activate.ps1

$root = "<PROJECT_ROOT>"
$book = "The Pragmatic Programmer"
$slug = "pragmatic-programmer"

# Copy file gốc vào input\
Copy-Item "F:\Downloads\the-pragmatic-programmer.pdf" "$root\input\"
```

### Bước 2: Chạy pipeline tự động đến bước 6 (3-5 phút)

Pipeline lo hết: trích xuất → QC → detect ngôn ngữ → OpenCC (nếu Phồn) → chunk → tạo prompt glossary:

```powershell
python scripts\run_pipeline.py `
    --input "$root\input\the-pragmatic-programmer.pdf" `
    --book $book `
    --slug $slug `
    --lang en `
    --to-step 6
```

Sau khi xong, kiểm tra `working\extracted\$slug\raw.md` - mở bằng VS Code xem có ổn không.

### Bước 3: Tạo glossary CSV

```powershell
# Tạo prompt glossary (từ chunk đã chia)
python scripts\generate_glossary.py `
    --source-dir "working\chunks\$slug" `
    --book-name $slug
# → File prompt tại working/glossary_prompt_{slug}.txt
```

Yêu cầu Agent (opencode) đọc file prompt đó và tạo `glossary\$slug.csv`
(cột bắt buộc: `source,target`, xem `glossary\_fields.md`). Rà soát lại trước khi dịch.

### Bước 4: Dịch từng chunk

**Dịch bằng AI chat (opencode)** — mở opencode, gõ `/dich <slug>` (tự chạy nốt pipeline),
hoặc nói `"dịch tiếp sách <slug>"` để Agent dịch dòng-đối-dòng từng chunk chưa xong
trong `working\progress\$slug\` rồi tự lưu lại.

Bản dịch được lưu vào `working\progress\$slug\chunk_*.json` (có `translated_at`).

### Bước 5: QA

```powershell
# Tạo bản dịch thuần Việt để QA
python scripts\merge_chunks.py `
    --progress-dir "working\progress\$slug" `
    --book-name $slug `
    --format bilingual `
    --force

# Chạy QA (kiểm tra thuật ngữ, Hán sót, mojibake, dòng lặp)
python scripts\glossary_qa.py `
    --source "working\extracted\$slug\raw.md" `
    --translation "output\${slug}_translated.md" `
    --glossary "glossary\$slug.csv" `
    --lang en `
    --report "working\qa\$slug\qa-vi.md"
```

Nếu có lỗi (exit code 1), xem báo cáo → sửa bản dịch trong progress JSON
(chỉnh `translated_text`, hoặc nhờ AI dịch lại chunk đó bằng lệnh `/dich`).

### Bước 6: Merge + EPUB hoàn chỉnh

```powershell
python scripts\run_pipeline.py `
    --book $book `
    --slug $slug `
    --from-step 9 `
    --force
# Bước 9 (Merge) tự chọn định dạng theo ngôn ngữ:
#   - EN → song ngữ EN+VI + bản thuần Việt
#   - ZH → tam ngữ Hán/Pinyin/Việt
# Bước 10 (EPUB) chạy make_epub.py nếu có pandoc
```

Kết quả trong `output\$slug\`. Commit tiến trình trong `working\progress\$slug\`.

---

## 3. Dịch 1 cuốn EPUB tiếng Trung

> Ví dụ cuốn "三体" (Ba Thể), slug=`san-ti`, thể loại `tien-hiep`.
> Sách ZH được dịch theo định dạng **tam ngữ** (Hán tự + Pinyin + Việt).

### Bước 1: Chuẩn bị

```powershell
cd "F:\OneDrive\onyx\Translate Book"
.\.venv\Scripts\Activate.ps1

$root = "F:\OneDrive\onyx\Translate Book"
$book = "三体"
$slug = "san-ti"
$genre = "tien-hiep"

# Copy file
Copy-Item "F:\Downloads\santi.epub" "$root\input\"
```

### Bước 2: Chạy pipeline tự động đến bước 6

```powershell
python scripts\run_pipeline.py `
    --input "$root\input\santi.epub" `
    --book $book `
    --slug $slug `
    --lang zh `
    --to-step 6
# Tự lo: extract (epub_extract) → QC → detect lang → OpenCC (nếu Phồn) → chunk → glossary prompt
```

### Bước 3: Tạo glossary CSV

```powershell
python scripts\generate_glossary.py `
    --source-dir "working\chunks\$slug" `
    --book-name $slug `
    --merge-genre $genre
# Agent (opencode) đọc working/glossary_prompt_{slug}.txt → tạo glossary\$slug.csv
```

### Bước 4: Khởi tạo skeleton tam ngữ

```powershell
python scripts\init_trilingual_skeleton.py `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug"
# Tạo progress JSON trống cho từng chunk, gồm original_text + pinyin_text
```

### Bước 5: Dịch từng chunk

**Dịch bằng AI chat (opencode)**: gõ `/dich <slug>` để chạy trọn pipeline, hoặc yêu cầu
Agent dịch `original_text` dòng-đối-dòng sang `translated_text` (số dòng bằng nhau,
giữ heading `#`/`##` và dòng ảnh `![...]`).

### Bước 6: QA

```powershell
# Tạo bản dịch thuần Việt để QA
python scripts\merge_chunks.py `
    --progress-dir "working\progress\$slug" `
    --book-name $slug `
    --format trilingual `
    --force

# QA: kiểm tra Hán sót (<5%), thuật ngữ, mojibake, dòng lặp
python scripts\glossary_qa.py `
    --source "working\extracted\$slug\raw.md" `
    --translation "output\${slug}_translated.md" `
    --glossary "glossary\$slug.csv" `
    --lang zh `
    --report "working\qa\$slug\qa-vi.md"
```

> `merge_chunks.py --format trilingual` tạo `output\${slug}_trilingual.md` (tam ngữ)
> và `output\${slug}_translated.md` (thuần Việt) — dùng bản thuần Việt để QA.

### Bước 7: Merge + EPUB hoàn chỉnh

```powershell
python scripts\run_pipeline.py `
    --book $book `
    --slug $slug `
    --from-step 9 `
    --force
# → output/${slug}_trilingual.md + output/${slug}_trilingual.epub (nếu có pandoc)
```

Commit tiến trình trong `working\progress\$slug\`.

---

## 4. Dịch 1 file SRT phụ đề

> Ví dụ phim "Inception" tập 1, slug=`inception-s01e01`.

### Bước 1: Chuẩn bị

```powershell
cd "F:\OneDrive\onyx\Translate Book"
.\.venv\Scripts\Activate.ps1

$root = "F:\OneDrive\onyx\Translate Book"
$slug = "inception-s01e01"

# Copy file
Copy-Item "F:\Downloads\inception-s01e01.srt" "$root\input\"

# Tạo thư mục
$dirs = @("$root\output\$slug",
          "$root\working\extracted\$slug",
          "$root\working\chunks\$slug\srt-batches",
          "$root\working\qa\$slug")
foreach ($d in $dirs) {
    if (-not (Test-Path -LiteralPath $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}

# Copy + verify encoding
Copy-Item "$root\input\inception-s01e01.srt" "$root\working\extracted\$slug\raw.srt"
# Mở bằng VS Code: File > Save with Encoding > UTF-8 (nếu chưa phải)
code "$root\working\extracted\$slug\raw.srt"
```

### Bước 2: Tách batch

```powershell
python scripts\srt_translate.py `
    --input "$root\working\extracted\$slug\raw.srt" `
    --extract-batches `
    --batch-dir "$root\working\chunks\$slug\srt-batches" `
    --batch-size 30
```

Tạo ra N file `batch-001.md` (text gốc) + `batch-001.vi.md` (template bản dịch).

### Bước 3: Dịch từng batch

Paste nội dung `batch-001.md` vào chat AI, nhận bản dịch, lưu vào `batch-001.vi.md` (giữ nguyên `[index]` phía trước).

### Bước 4: Ghép lại thành SRT

```powershell
python scripts\srt_translate.py `
    --input "$root\working\extracted\$slug\raw.srt" `
    --output "$root\output\$slug\translated.srt" `
    --batch-dir "$root\working\chunks\$slug\srt-batches" `
    --merge
```

### Bước 5: QA

```powershell
python scripts\glossary_qa.py `
    --source "$root\working\extracted\$slug\raw.srt" `
    --translation "$root\output\$slug\translated.srt" `
    --glossary "$root\glossary\$slug.csv" `
    --lang en `
    --mode srt `
    --report "$root\working\qa\$slug\srt-qa.md"
```

### Bước 6: Commit

```powershell
git add output/$slug/translated.srt glossary/$slug.*
git commit -m "feat($slug): SRT translation"
```

---

## 5. Dịch sách scan (PDF ảnh)

> Giống PDF thường, nhưng thêm bước thử PaddleOCR nếu MinerU kém.

```powershell
# Chạy MinerU như bình thường
python scripts\mineru_extract.py `
    --input "$root\input\scan-book.pdf" `
    --output "$root\working\extracted\$slug\raw.md" `
    --lang ch+en

# QC
python scripts\post_extract_qc.py `
    --input "$root\working\extracted\$slug\raw.md" `
    --report "$root\working\qa\$slug\extract-qc.md" `
    --lang zh

# Nếu nhiều lỗi → thử PaddleOCR
python scripts\ocr_paddle.py `
    --input "$root\input\scan-book.pdf" `
    --output "$root\working\extracted\$slug\raw-paddle.md" `
    --lang ch_sim+en

# So sánh 2 file, chọn bản tốt hơn
code --diff "$root\working\extracted\$slug\raw.md" "$root\working\extracted\$slug\raw-paddle.md"
```

Tiếp tục như bước chia chunk + dịch + QA.

---

## 6. Cập nhật glossary

### Thêm thuật ngữ mới

**CSV** (bản nguồn duy nhất - cho cả script QA lẫn AI dịch):

```powershell
notepad "$root\glossary\$slug.csv"
# Thêm dòng: source,target,type,note,genre,book
# Vd: 张伟,Trương Vĩ,character,Nhân vật chính,tien-hiep,san-ti
```

> Quy tắc CSV: nếu `note` có dấu phẩy → bọc trong `"..."`. Xem `glossary\_fields.md`.

> Lưu ý: glossary **chỉ còn là CSV** (không còn dạng `.md` riêng cho người đọc).

### Commit

```powershell
git add glossary/$slug.csv
git commit -m "glossary($slug): them 5 nhan vat moi"
```

### Thêm vào glossary thể loại (khi từ phổ biến)

```powershell
notepad "$root\glossary\genres\tien-hiep.csv"
# Thêm dòng với genre=tien-hiep, book=rỗng (áp dụng cả thể loại)
```

---

## 7. Git workflow hàng ngày

```powershell
# Đầu ngày
cd "F:\OneDrive\onyx\Translate Book"
git pull  # nếu làm việc nhiều máy

# Trong ngày - commit mỗi chunk xong (bản dịch nằm trong progress JSON)
git add working/progress/$slug/ glossary/$slug.csv
git commit -m "feat($slug): chunk 006"

# Xem lịch sử
git log --oneline
git log --stat

# So sánh phiên bản
git diff glossary/$slug.csv
git log -p working/progress/$slug/chunk_006.json

# Cuối ngày - kiểm tra trạng thái
git status
```

---

## 8. Troubleshooting nhanh

| Lỗi | Nguyên nhân | Fix |
|-----|-------------|-----|
| `ModuleNotFoundError: No module named 'X'` | Chưa cài | `pip install -r scripts\requirements.txt` |
| PowerShell in ra `?\u1ebf?` | Chưa set UTF-8 | Xem §1.1, mở PowerShell mới |
| `git add` báo lỗi file không tồn tại | Chưa tạo file | Tạo file trước (xem §1.4 + GĐ0.4) |
| `MinerU thất bại` | MinerU 3.4 thay đổi tham số | Chạy `mineru --help` rồi sửa `mineru_extract.py` |
| EPUB lỗi "không tìm thấy ebooklib" | Chưa cài | `pip install ebooklib beautifulsoup4 markdownify` |
| QA báo "khoảng 50% Hán tự còn sót" | Dịch chưa xong / glossary thiếu | Bổ sung glossary, dịch lại |
| Số dòng SRT không khớp | Bỏ sót batch khi dịch | Dịch bổ sung batch thiếu |
| Chunk cuối quá nhỏ (cảnh báo) | Input ngắn hoặc ranh giới lệch | Có thể bỏ qua hoặc merge thủ công |

Chi tiết hơn → [PROCESS.md §11](./docs/archive/PROCESS.md#11-xử-lý-sự-cố-thường-gặp).

---

## 9. Tam ngữ (Chinese → Pinyin → Vietnamese)

> Workflow dành cho sách tiếng Trung, muốn output 3 dòng: Hán tự + Pinyin + Dịch.

### 9.1. Backfill pinyin cho chunk đã dịch

```powershell
# Đã dịch xong bản thường (bilingual), muốn thêm pinyin
python scripts\generate_trilingual.py `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug"

# Xem trước (không ghi)
python scripts\generate_trilingual.py `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug" `
    --dry-run
```

### 9.2. Dịch trực tiếp với tam ngữ (khuyến nghị)

**Bước 1 — Tạo skeleton trilingual** (progress JSON có sẵn `original_text` + `pinyin_text`):

```powershell
python scripts\init_trilingual_skeleton.py `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug"
```

**Bước 2 — Dịch bằng AI chat**: Agent (opencode) dịch `original_text` dòng-đối-dòng
sang `translated_text`, số dòng bằng nhau, giữ heading `#`/`##`, giữ dòng ảnh `![...]`,
bỏ dòng OCR dư `///`, dùng glossary, ghi `translated_at="2026-07-31T00:00:00"`.

**Bước 2b — Hoặc interactive mode** (`translate_helper.py --trilingual`):

```powershell
# Prepare prompt tam ngữ
python scripts\translate_helper.py `
    --prepare 0 `
    --chunks-dir "working\chunks\$slug" `
    --glossary "glossary\$slug.csv" `
    --trilingual

# Interactive mode tam ngữ
python scripts\translate_helper.py `
    --interactive `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug" `
    --glossary "glossary\$slug.csv" `
    --trilingual `
    --auto-commit
```

### 9.3. Merge tam ngữ

```powershell
python scripts\merge_chunks.py `
    --progress-dir "working\progress\$slug" `
    --book-name $slug `
    --format trilingual `
    --force
# → Output: output/{slug}_trilingual.md
```

> **Mẹo**: Nếu dùng `run_pipeline.py`, định dạng merge tự động chọn theo ngôn ngữ:
> - ZH → `--format trilingual` (3 dòng gốc/pinyin/dịch)
> - EN → `--format bilingual` + `make_bilingual.py` (song ngữ EN+VI căn chỉnh đoạn)

### 9.4. Sinh pinyin từ file gốc (standalone)

```powershell
python scripts\add_pinyin.py `
    --input "working\extracted\$slug\raw.md" `
    --output "working\pinyin\$slug.json"
# → JSON array: [{original, pinyin, paragraph_index}, ...]
```

---

## 10. Workflow mới: Agent-first (khuyến nghị)

> Workflow này dùng pipeline scripts mới, Agent tự đọc chunk JSON + glossary và dịch trực tiếp.
> Không cần copy-paste thủ công từng chunk, không cần tạo file Markdown riêng.
>
> **Cách đơn giản nhất**: mở opencode, gõ `/dich` → chọn file trong `input\` → chờ kết quả
> trong `output\<slug>\` (tool chạy toàn bộ pipeline, xem AGENTS.md).

### 10.1. Pipeline toàn bộ

```powershell
cd "F:\OneDrive\onyx\Translate Book"
.\.venv\Scripts\Activate.ps1

$book = "my-book"
$slug = "my-book"

# Bước 1-6: Extract + QC + Detect lang + Chunk + Glossary prompt
python scripts\run_pipeline.py `
    --book $book `
    --input "input\my-book.pdf" `
    --lang auto
# → Đọc file working/glossary_prompt_my-book.txt, yêu cầu Agent tạo glossary/my-book.csv

# Bước 7: Dịch bằng AI chat — mở opencode, gõ /dich <slug> hoặc nói "dịch tiếp sách <slug>"
# (Agent tự dịch dòng-đối-dòng từng chunk chưa xong và lưu vào progress JSON)

# Bước 8-10: QA + Merge + EPUB
python scripts\run_pipeline.py `
    --book $book `
    --from-step 8 `
    --force
```

> Lưu ý: run_pipeline không có flag `--source-lang` — dùng `--lang en|zh|auto`.

### 10.2. Dịch bằng AI chat (KHUYẾN NGHỊ)

> **Ít thao tác nhất**: mở opencode gõ `/dich <slug>` (hoặc nói `"dịch tiếp sách <slug>"`).
> Agent tự đọc `working\progress\$slug\`, dịch dòng-đối-dòng từng chunk chưa xong
> (giữ heading/ảnh, dùng glossary, ghi `translated_at` + số dòng khớp) và tự lưu lại.

```powershell
# Trong opencode, gõ:
/dich <slug>
# hoặc yêu cầu: "dịch tiếp sách <slug>"
```

### 10.3. Interactive mode (dịch bằng AI chat qua terminal)

> **Giảm thao tác**: một lệnh duy nhất, tự động prompt → đợi dịch → save → commit → next.

```powershell
# Bắt đầu interactive mode (tự động tìm chunk chưa dịch)
python scripts\translate_helper.py --interactive `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug" `
    --glossary "glossary\$slug.csv" `
    --source-lang English --target-lang Vietnamese `
    --auto-commit

# Bắt đầu từ chunk 10
python scripts\translate_helper.py --interactive --from 10 `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug" `
    --glossary "glossary\$slug.csv"

# Trong interactive mode, các lệnh sau dùng được khi paste:
#   ---END---    Lưu và sang chunk tiếp
#   ---SKIP---   Bỏ qua chunk này
#   ---BACK---   Quay lại chunk trước
#   ---EXIT---   Thoát
```

### 10.4. Dịch thủ công từng chunk (nếu không dùng interactive)

```powershell
# Xem chunk nào chưa dịch
python scripts\translate_helper.py `
    --next `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug"

# Chuẩn bị prompt cho chunk 0 (in ra terminal)
python scripts\translate_helper.py `
    --prepare 0 `
    --chunks-dir "working\chunks\$slug" `
    --glossary "glossary\$slug.csv" `
    --source-lang English `
    --target-lang Vietnamese

# Copy prompt từ terminal → paste cho Agent → Agent trả bản dịch
# Sau đó lưu bản dịch (dùng ---END--- để kết thúc):
python scripts\translate_helper.py `
    --save 0 --auto-commit `
    --progress-dir "working\progress\$slug" `
    --chunks-dir "working\chunks\$slug"

# Kiểm tra tiến trình
python scripts\translate_helper.py `
    --status `
    --progress-dir "working\progress\$slug"
```

### 10.7. QA và Merge

> **Tự động chọn định dạng**: `run_pipeline.py` tự động phát hiện ngôn ngữ ở bước 3,
> và chọn đúng định dạng merge (trilingual cho ZH, song ngữ EN+VI cho EN) mà không
> cần thêm flag `--format` hay `--trilingual`.

```powershell
# QA tất cả chunk đã dịch
python scripts\run_pipeline.py `
    --book $book `
    --from-step 5

# Merge thành file hoàn chỉnh (tự động chọn định dạng theo ngôn ngữ)
python scripts\run_pipeline.py `
    --book $book `
    --from-step 6 `
    --force

# Merge với validation (kiểm tra chunk thiếu trước khi gộp)
python scripts\merge_chunks.py `
    --progress-dir "working\progress\$slug" `
    --book-name $slug `
    --force

# Merge cho phép thiếu chunk (chèn placeholder [CHƯA DỊCH])
python scripts\merge_chunks.py `
    --progress-dir "working\progress\$slug" `
    --book-name $slug `
    --allow-partial

# Merge bỏ qua chunk thiếu
python scripts\merge_chunks.py `
    --progress-dir "working\progress\$slug" `
    --book-name $slug `
    --skip-missing
```

#### Validation & error handling

`merge_chunks.py` tự động kiểm tra trước khi gộp:

| Kiểm tra | Mô tả | Hành vi mặc định |
|----------|-------|-----------------|
| **Thiếu chunk** | Chunk_id không liên tục (vd: có 0,1,3 thiếu 2) | **Báo lỗi và dừng** — yêu cầu dịch hết hoặc dùng flag |
| **Dịch rỗng** | chunk tồn tại nhưng `translated_text` trống | **Báo lỗi và dừng** |
| **File lỗi** | JSON không parse được hoặc thiếu chunk_id | **Bỏ qua file**, báo danh sách file lỗi |

**Các flag xử lý:**

- `--allow-partial`: Thay chunk thiếu bằng `[CHƯA DỊCH - Chunk N]` placeholder
- `--skip-missing`: Bỏ qua chunk thiếu (file output ngắn hơn dự kiến)
- Không dùng flag nào: **exit code 1** nếu thiếu chunk

Nếu cả `--allow-partial` và `--skip-missing` đều không dùng, script **không ghi file** khi phát hiện thiếu chunk, tránh output không hoàn chỉnh.

### 10.5. Glossary flow hoàn chỉnh

> **Luồng xử lý glossary**: `generate_glossary.py` → Agent tạo CSV → user review → dùng trong translate → QA check.

#### Bước A: Tạo prompt cho Agent

```powershell
python scripts\generate_glossary.py `
    --source "working\extracted\$slug\raw.md" `
    --book-name $slug
```
→ File prompt tại `working/glossary_prompt_{slug}.txt`

#### Bước B: Agent đọc prompt → tạo CSV

```
Đọc file glossary_prompt_{slug}.txt, yêu cầu Agent tạo file CSV.
Lưu kết quả vào glossary/{slug}.csv
```

#### Bước C: Kiểm tra CSV format

Script `glossary_qa.py` và `translate_helper.py` expect CSV có cột:
```csv
source,target,type,note,genre,book
"张伟","Trương Vĩ","character","Nhân vật chính","tien-hiep","san-ti"
"阴剑","âm kiếm","term","thuật ngữ võ học","tien-hiep",""
```

- `source`: Thuật ngữ gốc (bắt buộc)
- `target`: Bản dịch (bỏ trống nếu chưa biết, Agent sẽ điền sau)
- `type`: `character` / `term` / `place` / `item`...
- `note`: Ngữ cảnh ngắn (tùy chọn)
- `genre` / `book`: thẻ gán thể loại / cuốn sách (rỗng = áp dụng chung)

> Xem quy ước đầy đủ tại `glossary\_fields.md`.

#### Bước D: Dùng glossary khi dịch

```powershell
# translate_helper tự động đọc glossary khi --glossary được cung cấp
python scripts\translate_helper.py --interactive --glossary "glossary\$slug.csv" ...
```

#### Bước E: QA kiểm tra glossary consistency

```powershell
# Sau khi dịch, QA tự động kiểm tra thuật ngữ
python scripts\glossary_qa.py `
    --source "working\chunks\$slug\chunk-000.json" `
    --translation "working\progress\$slug\chunk_000.json" `
    --glossary "glossary\$slug.csv" `
    --lang en
```

#### Bước F: Merge vào genre glossary (tùy chọn)

```powershell
# Khi thuật ngữ phổ biến, copy vào glossary/genres/{genre}.csv
# để dùng lại cho các cuốn sách cùng thể loại
```

---

### 10.6. Chunking riêng (nếu muốn tùy chỉnh)

```powershell
# Smart chunking (mặc định)
python scripts\chunk_text.py `
    --input "working\extracted\$slug\raw.md" `
    --output-dir "working\chunks\$slug" `
    --strategy smart `
    --lang en `
    --max-chars 2000 `
    --min-chars 500

# Paragraph chunking
python scripts\chunk_text.py `
    --input "working\extracted\$slug\raw.md" `
    --output-dir "working\chunks\$slug" `
    --strategy paragraph `
    --lang en

# Line chunking (cho phụ đề/thơ)
python scripts\chunk_text.py `
    --input "working\extracted\$slug\raw.md" `
    --output-dir "working\chunks\$slug" `
    --strategy line `
    --lang en

# Fixed chunking (giữ nguyên behavior cũ)
python scripts\chunk_text.py `
    --input "working\extracted\$slug\raw.md" `
    --output-dir "working\chunks\$slug" `
    --strategy fixed `
    --lang en `
    --min-chars 3000 `
    --max-chars 8000 `
    --overlap-chars 200 `
    --respect-headings
```

---

## 11. Interactive mode chi tiết

> **Một lệnh duy nhất** cho toàn bộ quá trình dịch: tự động tìm chunk, in prompt, đợi dịch, lưu, commit.

### 11.1. Cách dùng

```powershell
python scripts\translate_helper.py --interactive `
    --chunks-dir "working\chunks\$slug" `
    --progress-dir "working\progress\$slug" `
    --glossary "glossary\$slug.csv" `
    --source-lang English --target-lang Vietnamese `
    --auto-commit
```

### 11.2. Luồng hoạt động

```
1. Tìm chunk tiếp theo chưa dịch trong working/progress/{slug}/
2. Đọc chunk JSON + glossary CSV
3. In prompt ra terminal (và copy vào clipboard nếu có pyperclip)
4. Hiển thị tiến trình: [█████░░░░░░░] 33%
5. Đợi user paste bản dịch
6. Lưu vào working/progress/{slug}/chunk_{id}.json
7. Nếu --auto-commit: git add + git commit
8. Quay lại bước 1 cho chunk tiếp theo
```

### 11.3. Commands trong interactive mode

| Command | Hành động |
|---------|-----------|
| `---END---` (dòng mới) | Kết thúc nhập bản dịch, lưu và sang chunk tiếp |
| `---SKIP---` | Bỏ qua chunk hiện tại |
| `---BACK---` | Quay lại chunk trước |
| `---EXIT---` | Thoát interactive mode |

### 11.4. Flags

| Flag | Mô tả |
|------|-------|
| `--from {id}` | Bắt đầu từ chunk_id cụ thể |
| `--auto-commit` | Tự động git commit sau mỗi chunk |
| `--glossary {path}` | File glossary CSV (nếu có) |
| `--chunks-dir {path}` | Thư mục chunk gốc |
| `--progress-dir {path}` | Thư mục lưu tiến trình |

### 11.5. Yêu cầu

- Python 3.10+
- `pyperclip` (optional): `pip install pyperclip` để tự động copy prompt vào clipboard

---

## 💡 Mẹo tăng tốc

- **Glossary đầu tư 1-2h ban đầu** sẽ tiết kiệm hàng giờ sau
- **Paste 2 đoạn đã dịch gần nhất** vào đầu phiên chat - AI giữ phong cách nhất quán
- **Commit mỗi chunk** - rollback dễ khi cần
- **Đọc lại 1 chương trước khi dịch chương tiếp** - nắm bối cảnh
- **In ra giấy bản dịch** - bắt lỗi tốt hơn đọc màn hình

---

*Có câu hỏi? Mở chat với tôi, kèm error message (nếu có) và bước đang làm.*
