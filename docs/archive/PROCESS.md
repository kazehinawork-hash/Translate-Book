# PROCESS — Quy trình thực hiện chi tiết

> Phiên bản: v2.1 — Cập nhật 2026-07-19
> Đồng bộ với PLAN.md v2.1: sửa mâu thuẫn working/ git, tách EPUB, fix MinerU install, thêm CSV escape, fix pseudo-code.
> Tài liệu hướng dẫn từng bước để dịch 1 cuốn sách từ đầu đến cuối

---

## Mục lục
1. [Quy trình tổng quan](#1-quy-trình-tổng-quan)
2. [Chuẩn bị trước khi dịch](#2-chuẩn-bị-trước-khi-dịch)
3. [Quy trình sách tiếng Anh](#3-quy-trình-sách-tiếng-anh)
4. [Quy trình sách tiếng Trung](#4-quy-trình-sách-tiếng-trung)
5. [Quy trình sách scan](#5-quy-trình-sách-scan)
6. [Quy trình phụ đề SRT](#6-quy-trình-phụ-đề-srt)
7. [Quản lý glossary](#7-quản-lý-glossary)
8. [Theo dõi tiến độ](#8-theo-dõi-tiến-độ)
9. [Mẫu mở đầu phiên chat](#9-mẫu-mở-đầu-phiên-chat)
10. [Checklist chất lượng](#10-checklist-chất-lượng)
11. [Xử lý sự cố thường gặp](#11-xử-lý-sự-cố-thường-gặp)
12. [Mẹo tăng chất lượng dịch](#12-mẹo-tăng-chất-lượng-dịch)
13. [Git workflow](#13-git-workflow)

---

## 1. Quy trình tổng quan

```
┌────────────────────────────────────────────────┐
│ Bước 0: Chuẩn bị                              │
│  • Tạo thư mục dự án (slug)                    │
│  • Khởi tạo glossary từ thể loại               │
│  • Tóm tắt nội dung                            │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 1: Trích xuất                            │
│  • PDF/DOCX/ảnh/scan: MinerU                   │
│  • EPUB: scripts/epub_extract.py               │
│  • → Markdown sạch                             │
│  • Đã loại header/footer/số trang              │
│  • Xử lý layout nhiều cột, bảng biểu           │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 1.5: QC sau trích xuất                    │
│  • Phát hiện mojibake, dòng trống, lặp dòng   │
│  • Sửa trước khi dịch                          │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 2: Phát hiện ngôn ngữ + Chuẩn hóa         │
│  • Detect EN / ZH                              │
│  • ZH: OpenCC Phồn → Giản (nếu cần)            │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 3: Chia chunk                              │
│  • Ưu tiên ranh giới (chương, scene, đoạn)     │
│  • EN: 500-1500 từ/chunk                        │
│  • ZH: 1500-3000 chữ Hán/chunk                  │
│  • Overlap 1-2 câu từ chunk trước               │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 4: Dịch (nhiều phiên)                     │
│  • Mỗi phiên: 1-3 chunks                       │
│  • EN → VI: trực tiếp                           │
│  • ZH → VI: trực tiếp (KHÔNG qua Pinyin)       │
│  • Áp glossary                                  │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 4.5: QA tự động                            │
│  • Thuật ngữ glossary bị sót                   │
│  • Ký tự Hán/EN còn sót                        │
│  • (SRT: số dòng, timestamp khớp gốc)          │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 5: Người duyệt                            │
│  • Đọc + sửa nếu cần                          │
│  • Cập nhật glossary + git commit               │
└─────────────────────┬──────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ Bước 6: Ghép & hoàn thiện                      │
│  • Ghép tất cả chunks → file hoàn chỉnh        │
│  • Đọc lại 1 lần cuối                          │
│  • Sửa chỗ không nhất quán                     │
└────────────────────────────────────────────────┘
```

---

## 2. Chuẩn bị trước khi dịch

### 2.1 Tạo cấu trúc thư mục cho 1 dự án mới

**Quan trọng: Tất cả lệnh dưới đây dùng PowerShell 5.1 (Windows), không phải bash.**

```powershell
# Đặt biến để dễ dùng lại
$root = "F:\OneDrive\onyx\Translate Book"
$slug = "ten-sach-slug"  # TODO: thay bằng slug thật

# Tạo thư mục dự án (chỉ tạo working/, output/ chưa có slug thì thôi)
$dirs = @(
    "$root\output\$slug",
    "$root\working\extracted\$slug",
    "$root\working\chunks\$slug",
    "$root\working\progress\$slug",
    "$root\working\summary\$slug",
    "$root\working\qa\$slug"
)
foreach ($d in $dirs) {
    if (-not (Test-Path -LiteralPath $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "Created: $d"
    }
}

# Đảm bảo console UTF-8 (tránh mojibake khi echo tiếng Trung)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
```

### 2.2 Quy ước slug tên sách

**Slug phải**: không dấu, không khoảng trắng, không ký tự đặc biệt, chỉ dùng `a-z`, `0-9`, dấu gạch ngang.

| Tên sách | Slug |
|----------|------|
| Tu Tiên Trúc | `tu-tien-truc` |
| The Pragmatic Programmer | `the-pragmatic-programmer` |
| 三体 (Ba Thể) | `san-ti` |
| 凡人修仙传 | `fan-ren-xiu-xian-zhuan` |

Lý do:
- Tránh lỗi đồng bộ OneDrive với dấu
- Tránh lỗi path trong script Python
- Git-friendly (commit log dễ đọc)

### 2.3 Tạo file glossary mới

Copy từ template:

```powershell
Copy-Item "$root\glossary\_template.md" "$root\glossary\$slug.md"
Copy-Item "$root\glossary\_template.csv" "$root\glossary\$slug.csv"
```

Sau đó mở 2 file, điền thông tin cơ bản.

**Cả 2 file (Markdown + CSV) phải đồng bộ** — CSV dùng cho QA script, Markdown cho người đọc.

### 2.4 Kế thừa glossary thể loại

Nếu sách thuộc thể loại đã có glossary (vd: `tien-hiep`):

```powershell
# Xem các thuật ngữ đã có
Get-Content "$root\glossary\genres\tien-hiep.csv"
```

Khi bắt đầu dịch, paste cả glossary thể loại + glossary sách vào đầu phiên chat với tôi. Khi gặp thuật ngữ thể loại, tôi sẽ dùng bản dịch đã thống nhất.

### 2.5 Tạo file tóm tắt

Tạo `working\summary\$slug\summary.md`:

```markdown
# Tóm tắt: <Tên sách>

## Thông tin
- Tác giả: ...
- Thể loại: tien-hiep / ky-nghiep / ky-thuat-it
- Ngôn ngữ gốc: ZH / EN
- Số chương: ...
- Số trang: ...

## Bối cảnh
- Thời đại: ...
- Địa điểm: ...
- Hệ thống sức mạnh: ... (nếu có)

## Tóm tắt cốt truyện
(2-3 đoạn)

## Phong cách dịch
- Văn phong: cổ trang / hiện đại / kỹ thuật
- Xưng hô chính: ta-ngươi / tôi-bạn / ...
- Giọng văn: trang trọng / thân mật / hài hước
```

### 2.6 Tạo file theo dõi tiến độ

Tạo `working\progress\$slug\progress.md`:

```markdown
# Tiến độ: <Tên sách>

## Tổng quan
- Slug: <slug>
- Tổng chunks ước tính: Y
- Đã xong: Z/Y
- Ngày bắt đầu: YYYY-MM-DD
- Dự kiến xong: YYYY-MM-DD

## Chi tiết chunks
- [ ] chunk-001 (chương 1, ~800 từ): chưa dịch
- [ ] chunk-002 (chương 1, ~900 từ): chưa dịch
- [ ] chunk-003 (chương 2, ~700 từ): chưa dịch
- ...

## Vấn đề phát sinh
- ...
```

### 2.7 Ghi nhận glossary mới vào git

> Quy ước hiện tại: **1 repo duy nhất** cho cả thư mục dự án (xem mục 13). Không tạo repo riêng cho từng cuốn.

```powershell
cd $root
git add glossary/$slug.* working/summary/$slug/
git commit -m "feat(glossary): khoi tao glossary cho $slug"
```

Xem chi tiết ở mục 13.

---

## 3. Quy trình sách tiếng Anh

### Bước 3.1 — Trích text bằng MinerU

```powershell
cd "F:\OneDrive\onyx\Translate Book"
.\.venv\Scripts\Activate.ps1
python scripts/mineru_extract.py `
    --input "input\<file>.pdf" `
    --output "working\extracted\$slug\raw.md" `
    --lang en
```

> **EPUB**: dùng `python scripts/epub_extract.py` thay cho MinerU (xem mục 4.1E bên dưới).
>
> **DOCX/ảnh**: MinerU 3.4 cũng hỗ trợ, dùng cùng script với `--lang en`.

### Bước 3.1b — Phát hiện ngôn ngữ (tùy chọn)

Nếu không chắc file EN hay ZH (vd: sách có thể có 2 ngôn ngữ):

```powershell
python scripts/detect_language.py "working\extracted\$slug\raw.md"
# Output: "en" / "zh" / "zh-Hant" / "mixed"
```

Nếu đã biết chắc ngôn ngữ (EN hoặc ZH), bỏ qua bước này.

MinerU tự xử lý:
- PDF có text layer → lấy text
- PDF scan → tự OCR
- Loại header/footer/số trang
- Sắp xếp thứ tự đọc (multi-column)
- Nhận diện bảng biểu → Markdown table

### Bước 3.2 — QC sau trích xuất

```powershell
python scripts/post_extract_qc.py `
    --input "working\extracted\$slug\raw.md" `
    --report "working\qa\$slug\extract-qc.md" `
    --lang en
```

Script kiểm tra:
- Tỷ lệ ký tự lạ / mojibake
- Đoạn trống bất thường (>5 dòng trống liên tiếp)
- Lặp dòng (OCR dính header)
- Encoding có đúng UTF-8 không

Đọc báo cáo QC, sửa nếu có vấn đề. Nếu nhiều lỗi → xem mục 11 (sự cố 1).

### Bước 3.3 — Chia chunk theo ranh giới

**Nguyên tắc chính: Chunk theo ranh giới logic, không cắt cứng theo số từ.**

```powershell
python scripts/chunk_text.py `
    --input "working\extracted\$slug\raw.md" `
    --output-dir "working\chunks\$slug" `
    --min-chars 3000 `
    --max-chars 8000 `
    --overlap-chars 200 `
    --respect-headings
```

Tham số quan trọng:
- `--min-chars 3000`, `--max-chars 8000`: EN ~500-1500 từ/chunk
- `--overlap-chars 200`: ~2 câu overlap
- `--respect-headings`: KHÔNG cắt giữa chương/heading, ưu tiên ranh giới

Nếu script không tự chia đẹp (ví dụ: 1 chương quá dài), chia tay:
- Đọc file Markdown
- Chèn dấu phân cách `<!-- CHUNK_BREAK -->` tại ranh giới đoạn/scene
- Chạy lại script với `--manual-markers`

### Bước 3.4 — Dịch từng chunk

Mở chat với tôi, paste theo mẫu ở mục 9.1.

### Bước 3.5 — Lưu bản dịch

Lưu bản dịch vào `output\$slug\chunk-001.md`, `chunk-002.md`, ...

### Bước 3.6 — QA tự động

```powershell
python scripts/glossary_qa.py `
    --source "working\chunks\$slug\chunk-001.md" `
    --translation "output\$slug\chunk-001.md" `
    --glossary "glossary\$slug.csv" `
    --genre-glossary "glossary\genres\ky-thuat-it.csv" `
    --lang en `
    --report "working\qa\$slug\chunk-001-qa.md"
```

Script phát hiện:
- Thuật ngữ glossary còn sót chưa dịch đúng
- Từ tiếng Anh còn sót (ngoại trừ trong danh sách "giữ nguyên" của glossary)

Đọc báo cáo QA, sửa nếu cần.

### Bước 3.7 — Ghi nhận & commit

- Cập nhật `working\progress\$slug\progress.md` (tick chunk đã xong)
- Nếu có thuật ngữ mới → cập nhật cả `glossary\$slug.md` và `glossary\$slug.csv`
- Git commit:
  ```powershell
  git add output/$slug/chunk-001.md glossary/$slug.* working/progress/$slug/
  git commit -m "feat($slug): chunk 001 - <ten chuong>"
  ```

### Bước 3.8 — Lặp lại cho đến hết

### Bước 3.9 — Tạo file song ngữ (tùy chọn)

Khi đã dịch xong tất cả chunks, có thể tạo file song ngữ (gốc + dịch xen kẽ):

```powershell
python scripts/make_bilingual.py ^
    --source "working\extracted\$slug\raw.md" ^
    --translation "output\$slug\$slug-vi.md" ^
    --output "output\$slug\$slug-songngu.md" ^
    --lang en
```

Kết quả: mỗi đoạn có bản gốc (đậm) + bản dịch Việt Nam xen kẽ. Heading: Việt Nam + gốc đậm. Useful cho review song song.

---

## 4. Quy trình sách tiếng Trung

### Bước 4.1 — Trích text

**Nếu input là PDF/DOCX/ảnh:**
```powershell
python scripts/mineru_extract.py `
    --input "input\<file>.pdf" `
    --output "working\extracted\$slug\raw.md" `
    --lang ch
```

**Nếu input là EPUB** (MinerU không hỗ trợ):
```powershell
python scripts/epub_extract.py `
    --input "input\<file>.epub" `
    --output "working\extracted\$slug\raw.md"
```

Sau đó tiếp tục bước 4.2 (QC).

### Bước 4.2 — QC sau trích xuất

```powershell
python scripts/post_extract_qc.py `
    --input "working\extracted\$slug\raw.md" `
    --report "working\qa\$slug\extract-qc.md" `
    --lang zh
```

### Bước 4.3 — Phát hiện & chuẩn hóa Phồn thể (nếu có)

```powershell
# Detect ngôn ngữ
python scripts/detect_language.py "working\extracted\$slug\raw.md"
# Output: "zh-Hant" (Phồn) hoặc "zh-Hans" (Giản)

# Nếu là Phồn thể → chuẩn hóa sang Giản thể
python scripts/opencc_normalize.py `
    --input "working\extracted\$slug\raw.md" `
    --output "working\extracted\$slug\raw-hans.md" `
    --config t2s
```

Sau đó dùng file `raw-hans.md` cho các bước tiếp theo.

**Lưu ý**: Nếu cuốn sách cụ thể dùng Hán tự khác với chuẩn Phồn/Giản (vd: Hán Việt cổ, Nhật Kanji), cần xử lý riêng — xem mục 11 sự cố 4.

### Bước 4.4 — Chia chunk

```powershell
python scripts/chunk_text.py `
    --input "working\extracted\$slug\raw-hans.md" `
    --output-dir "working\chunks\$slug" `
    --min-chars 1500 `
    --max-chars 3000 `
    --overlap-chars 100 `
    --lang zh `
    --respect-headings
```

> **Lưu ý**: Nếu sách gốc đã là **Giản thể** (bước 4.3 phát hiện `zh-Hans` và bỏ qua OpenCC), thay `raw-hans.md` bằng `raw.md` ở `--input` — file này là output trực tiếp từ MinerU/EPUB.

Tham số cho ZH (khác EN):
- `--min-chars 1500`, `--max-chars 3000`: 1500-3000 chữ Hán/chunk (vì tiếng Trung không có khoảng trắng từ)
- `--overlap-chars 100`: ~1-2 câu overlap
- `--lang zh`: cần thiết để đếm ký tự đúng (không đếm space)

### Bước 4.5 — Dịch trực tiếp ZH → VI (KHÔNG qua Pinyin)

**Quan trọng**: Dịch thẳng Hán tự → Tiếng Việt, không cần bước Pinyin trung gian.

Mở chat với tôi, paste theo mẫu ở mục 9.2.

**Lý do** (xem chi tiết PLAN.md mục 2):
- Pinyin mất ngữ nghĩa: 1 âm tiết (shi, jing, yi...) ứng với hàng chục ký tự Hán
- LLM dịch từ Pinyin phải đoán lại ký tự gốc → tỷ lệ sai cao
- LLM hiện đại dịch ZH→VI trực tiếp rất tốt

### Bước 4.6 — Pinyin chỉ dùng làm phụ chú (tùy chọn)

Nếu muốn thêm Pinyin cho mục đích học phát âm (không bắt buộc):

```powershell
# Stub có sẵn trong scripts/add_pinyin_annotation.py
# Triển khai thật khi cần dùng (xem file đó để biết tham số)
python scripts/add_pinyin_annotation.py `
    --input "output\$slug\full.md" `
    --output "output\$slug\full-pinyin.md" `
    --mode brackets
```

**Không dùng** Pinyin làm bước trung gian trong dịch.

### Bước 4.7 — QA tự động

```powershell
python scripts/glossary_qa.py `
    --source "working\chunks\$slug\chunk-001.md" `
    --translation "output\$slug\chunk-001.md" `
    --glossary "glossary\$slug.csv" `
    --genre-glossary "glossary\genres\tien-hiep.csv" `
    --lang zh `
    --report "working\qa\$slug\chunk-001-qa.md"
```

Script phát hiện:
- Thuật ngữ glossary bị dịch sai/lệch
- Ký tự Hán tự còn sót (ngoại trừ tên riêng đã đánh dấu "giữ nguyên")
- Số lượng ký tự Hán còn lại > ngưỡng → cảnh báo

### Bước 4.8 — Ghi nhận & commit
Giống bước 3.7.

### Bước 4.9 — Tạo file song ngữ (tùy chọn)

```powershell
python scripts/make_bilingual.py ^
    --source "working\extracted\$slug\raw.md" ^
    --translation "output\$slug\$slug-vi.md" ^
    --output "output\$slug\$slug-songngu.md" ^
    --lang zh
```

With `--lang zh`, pinyin is added for each Chinese paragraph: original bold + pinyin italic, then Vietnamese.

---

## 5. Quy trình sách scan

MinerU đã hỗ trợ scan natively, nên quy trình gần giống quy trình thường.

### Bước 5.1 — Chạy MinerU

```powershell
python scripts/mineru_extract.py `
    --input "input\<file-scan>.pdf" `
    --output "working\extracted\$slug\raw.md" `
    --lang ch+en `
    --ocr pp-ocrv6
```

MinerU tự detect scan và chạy OCR với PP-OCRv6.

> **Ghi chú tham số MinerU**: `scripts/mineru_extract.py` là wrapper tự viết, có thể định nghĩa lại tham số cho phù hợp. Tham số CLI thật của MinerU 3.4 cần kiểm chứng bằng `mineru --help` sau khi cài — các tham số `--lang`, `--ocr`, `--dpi` ở trên là giao diện dự kiến, có thể đã thay đổi. Nếu wrapper báo "unknown option", chạy `mineru --help` để đối chiếu.

### Bước 5.2 — QC & đánh dấu trang lỗi

Đọc lướt file Markdown, đánh dấu các phần có vấn đề:
- Chữ bị lỗi nhiều
- Thiếu đoạn
- Sai thứ tự
- Header/footer còn sót (hiếm khi MinerU để sót, nhưng có thể)

Ghi vào `working\progress\$slug\progress.md`:
```markdown
## Trang OCR lỗi
- Trang 15-17: chữ mờ, cần re-OCR
- Trang 23: thiếu 1 đoạn cuối
- ...
```

### Bước 5.3 — Re-OCR trang lỗi bằng AI vision

Trong chat với tôi, upload ảnh trang lỗi:

```
Sách "<Tên sách>" trang 15 bị OCR lỗi, 
bạn đọc lại giúp tôi và trả text chính xác.

[Upload ảnh trang 15]
```

→ Tôi đọc ảnh → trả text chính xác → bạn thay thế vào file Markdown.

### Bước 5.4 — Khi MinerU xử lý quá kém

Nếu nhiều trang bị lỗi (OCR ra text lung tung):

**Phương án 1**: Thử PaddleOCR trực tiếp
```powershell
python scripts/ocr_paddle.py `
    --input "input\<file-scan>.pdf" `
    --output "working\extracted\$slug\raw-paddle.md" `
    --lang ch_sim+en
```

So sánh `raw.md` (MinerU) vs `raw-paddle.md` → chọn bản tốt hơn.

**Phương án 2**: Tăng DPI
```powershell
python scripts/mineru_extract.py `
    --input "input\<file-scan>.pdf" `
    --output "working\extracted\$slug\raw.md" `
    --dpi 400
```

> Tham số `--dpi` là do wrapper tự định nghĩa (MinerU CLI gốc không có). Kiểm chứng tham số bằng `mineru --help` nếu lệnh báo lỗi.

**Phương án 3**: Tiền xử lý ảnh trước
- Mở PDF từng trang trong trình đọc
- Crop vùng text, contrast cao
- Lưu ảnh mới → chạy lại OCR

**Phương án 4 (cuối cùng)**: Tìm bản text khác của sách
- Project Gutenberg (sách cũ hết bản quyền)
- GitHub repos số hóa sách
- Library Genesis (cân nhắc vấn đề bản quyền)

### Bước 5.5 — Tiếp tục pipeline EN hoặc ZH
Sau khi có text sạch → quay lại bước 3 hoặc 4.

---

## 6. Quy trình phụ đề SRT

### Bước 6.1 — Sao chép file

```powershell
Copy-Item "input\<file>.srt" "working\extracted\$slug\raw.srt"
```

### Bước 6.2 — Kiểm tra ngôn ngữ & encoding

Mở file SRT bằng editor hỗ trợ UTF-8 (VS Code, Notepad++):
- Encoding UTF-8? (không phải ANSI/GBK)
- Phụ đề ZH hay EN? (nếu song ngữ → tách 2 phần)

Nếu encoding sai, convert sang UTF-8 bằng VS Code: `File > Save with Encoding > UTF-8`.

### Bước 6.3 — Tách batch và ghép bản dịch (KHÔNG dùng API)

Phụ đề SRT có thể có hàng trăm dòng → dịch theo batch ~20-50 dòng/lần.

**Không copy text từ SRT thủ công** — dùng pysrt để giữ timestamp/index.

Script `srt_translate.py` chỉ làm **2 việc**:
1. **Tách batch**: đọc SRT bằng pysrt, xuất từng batch ra file text riêng để paste vào chat
2. **Ghép**: paste bản dịch trả về vào file text tương ứng, script sẽ ghép vào SRT cuối (giữ timestamp, index)

```powershell
# Bước 1: tách batch từ SRT gốc → file text để paste vào chat
python scripts/srt_translate.py `
    --input "working\extracted\$slug\raw.srt" `
    --extract-batches `
    --batch-dir "working\chunks\$slug\srt-batches" `
    --batch-size 30

# (Paste từng file batch vào chat, nhận bản dịch, lưu vào working\chunks\$slug\srt-batches\batch-001.vi.md ...)

# Bước 2: ghép các bản dịch vào SRT gốc
python scripts/srt_translate.py `
    --input "working\extracted\$slug\raw.srt" `
    --output "output\$slug\translated.srt" `
    --batch-dir "working\chunks\$slug\srt-batches" `
    --merge
```

**Lưu ý**: Giai đoạn hiện tại **KHÔNG tích hợp API** (xem PLAN.md mục 2 - nguyên tắc giai đoạn hiện tại). Lộ trình tích hợp API (bilingual_book_maker, Qwen-MT) xem PLAN.md mục 13.

**Nếu làm thủ công qua chat** (không dùng script):
1. Paste batch SRT vào chat (chỉ text, không timestamp)
2. Tôi dịch
3. Copy text dịch vào file SRT đúng dòng

### Bước 6.4 — Xuất file SRT tiếng Việt

Sau khi dịch xong:
- File `.srt` chuẩn: `output\$slug\translated.srt` (giữ timestamp gốc)
- Hoặc bảng Markdown 3 cột (nếu muốn học phát âm): `output\$slug\translated-bilingual.md`

```markdown
| # | Tiếng Trung | Pinyin | Tiếng Việt |
|---|-------------|--------|------------|
| 1 | 你好 | Nǐ hǎo | Xin chào |
| 2 | ... | ... | ... |
```

### Bước 6.5 — QA cho SRT

```powershell
python scripts/glossary_qa.py `
    --source "working\extracted\$slug\raw.srt" `
    --translation "output\$slug\translated.srt" `
    --glossary "glossary\$slug.csv" `
    --lang zh `
    --mode srt `
    --report "working\qa\$slug\srt-qa.md"
```

Script kiểm tra:
- Số dòng khớp gốc (không mất/thừa dòng)
- Timestamp không bị thay đổi
- Index liên tục (1, 2, 3, ...)
- Ký tự Hán còn sót
- Thuật ngữ glossary nhất quán

---

## 7. Quản lý glossary

### 7.1 Cấu trúc 2 lớp

**Lớp 1: Thể loại** (`glossary/genres/<genre>.csv`)
- Tích lũy giữa nhiều sách cùng thể loại
- Có sẵn: `tien-hiep.csv`, `ky-nghiep.csv`, `ky-thuat-it.csv`
- Bạn có thể tạo thêm khi cần

**Lớp 2: Cuốn sách** (`glossary/<slug>.csv`)
- Riêng cho từng cuốn
- Kế thừa từ thể loại + bổ sung riêng

### 7.2 Khi nào cập nhật glossary

- Gặp nhân vật mới → thêm vào mục Nhân vật (cả .md và .csv)
- Gặp địa danh mới → thêm vào mục Địa danh
- Gặp thuật ngữ chuyên ngành mới → thêm (cân nhắc: cuốn này hay cả thể loại?)
- Đổi phong cách dịch → cập nhật mục Quy tắc

### 7.3 Cách tôi đề xuất thuật ngữ mới

Trong bản dịch, tôi sẽ đánh dấu:
```
...và linh khí [TERM-NEW: 灵气] trong không gian...
```

Bạn trả lời:
- "Linh khí" → tôi dùng, thêm vào glossary
- "Khí linh" → tôi cập nhật
- "Giữ nguyên 灵气" → giữ Hán tự trong bản dịch, thêm vào CSV với `target = 灵气`

### 7.4 Đồng bộ Markdown ↔ CSV

Khi thêm/sửa thuật ngữ, cập nhật CẢ HAI file:
- `glossary/<slug>.md` cho người đọc
- `glossary/<slug>.csv` cho script QA

Quy ước cột CSV (xem `glossary/_fields.md`):
```
source,target,type,note,genre,book
张伟,Trương Vĩ,character,nhân vật chính,tien-hiep,ten-sach
修仙,Tu tiên,term,"thuật ngữ tu chân, phổ biến",tien-hiep,ten-sach
API,API,term,giữ nguyên EN,ky-thuat-it,
```

**Quan trọng**: Nếu `note` (hoặc bất kỳ trường nào) chứa **dấu phẩy**, **bắt buộc bọc trong nháy kép `"..."`** — nếu không sẽ vỡ cột. File CSV phải là **UTF-8 (không BOM)**.

### 7.5 Quy tắc ưu tiên khi dịch

1. **Glossary cuốn sách** (ưu tiên cao nhất)
2. **Glossary thể loại**
3. **Phong cách dịch** đã thống nhất trong glossary
4. **Quy tắc chung** trong `_template.md`
5. **Phán đoán của tôi** (sẽ hỏi bạn nếu không chắc)

---

## 8. Theo dõi tiến độ

### 8.1 File `working\progress\$slug\progress.md`

Cập nhật liên tục:

```markdown
# Tiến độ: <Tên sách>

## Tổng quan
- Slug: ten-sach
- Tổng chunks: 45
- Đã xong: 23/45 (51%)
- Bắt đầu: 2026-07-20
- Dự kiến xong: 2026-07-27

## Chi tiết
- [x] chunk-001 (chương 1): 2026-07-20
- [x] chunk-002 (chương 1): 2026-07-20
- [x] chunk-003 (chương 2): 2026-07-21
- ...
- [ ] chunk-024 (chương 8): đang làm

## Vấn đề phát sinh
- Trang 45: glossary thiếu tên "Lão Vương" → đã thêm
- chunk-015: cần xem lại cách dịch "灵气"
- chunk-022: MinerU OCR sai tên riêng "Lâm Phong" → đã sửa
```

### 8.2 Khi nào ghép file hoàn chỉnh

Khi đã dịch xong tất cả chunks:
1. Tạo file `output\$slug\full.md`
2. Ghép tất cả chunks theo thứ tự
3. Thêm mục lục nếu cần
4. Đọc lại 1 lần cuối → sửa chỗ không nhất quán
5. Tạo file song ngữ (tùy chọn): `python scripts/make_bilingual.py` (xem mục 3.9 / 4.9)
6. Đánh dấu "Hoàn thành" trong progress
7. Git commit cuối:
   ```powershell
   git add output/$slug/full.md working/progress/$slug/
   git commit -m "feat($slug): hoàn thành bản dịch"
   ```

---

## 9. Mẫu mở đầu phiên chat

### 9.1 Cho sách tiếng Anh

```
Tôi muốn dịch tiếp cuốn "<Tên sách>" (EN → VI).

== GLOSSARY CUỐN SÁCH ==
[paste toàn bộ glossary/<slug>.md]

== GLOSSARY THỂ LOẠI ==
[paste toàn bộ glossary/genres/<genre>.md]

== TÓM TẮT ==
[paste working/summary/<slug>/summary.md]

== TIẾN ĐỘ ==
Đã xong: chunks 1-5
Giờ làm: chunk 6

== 2 ĐOẠN ĐÃ DỊCH GẦN NHẤT (làm mẫu phong cách) ==
[paste 100-200 từ từ chunk 5]

== YÊU CẦU ĐẶC BIỆT ==
- Giữ format đoạn thoại
- Không dịch tên riêng
- ...

== TEXT GỐC (chunk 6) ==
<paste text>
```

### 9.2 Cho sách tiếng Trung

```
Tôi muốn dịch tiếp cuốn "<Tên sách>" (ZH → VI trực tiếp).

== GLOSSARY CUỐN SÁCH ==
[paste glossary/<slug>.md]

== GLOSSARY THỂ LOẠI ==
[paste glossary/genres/<genre>.md]

== TÓM TẮT ==
[paste working/summary/<slug>/summary.md]

== TIẾN ĐỘ ==
Đã xong: chunks 1-5 (đã có bản dịch)
Giờ làm: chunk 6

== 2 ĐOẠN ĐÃ DỊCH GẦN NHẤT (làm mẫu phong cách) ==
[paste 100-200 chữ từ chunk 5]

== YÊU CẦU ==
- Dịch thẳng Hán tự → VI, KHÔNG qua Pinyin
- Gặp thuật ngữ nghi mới → đánh dấu [TERM-NEW: ...]
- ...

== HÁN TỰ GỐC (chunk 6) ==
<paste Hán tự>
```

### 9.3 Cho sách scan trang lỗi

```
Sách "<Tên sách>" trang X bị OCR lỗi, bạn đọc lại giúp tôi.

[Upload ảnh trang]

Bối cảnh: <vài dòng ngữ cảnh xung quanh nếu cần>
```

### 9.4 Cho phụ đề SRT

```
Dịch tiếp SRT "<Tên phim>" tập X (dòng Y+1 đến Z).

== GLOSSARY PHIM ==
[paste glossary phim]

== THỂ LOẠI/SERIES ==
[paste nếu có]

== YÊU CẦU ==
- Dòng Z+1 trở đi chưa dịch
- Format đầu ra: bảng Markdown | # | Gốc | Pinyin | Việt |
  (chỉ thêm cột Pinyin nếu muốn dùng làm phụ chú)
- Giữ nguyên timestamp, index

== SRT GỐC (dòng Y+1 đến Z) ==
<paste SRT>
```

> **Các mẫu prompt có sẵn trong `prompts/`** (dùng làm tham khảo hoặc gửi trực tiếp cho AI):
> - `prompts/en-to-vi.md` — mẫu đầy đủ cho sách EN (kèm glossary template)
> - `prompts/zh-to-vi.md` — mẫu đầy đủ cho sách ZH
> - `prompts/ocr-fallback.md` — khi MinerU/OCR lỗi, upload ảnh trang
> - `prompts/review-checklist.md` — checklist + prompt để AI hỗ trợ duyệt

---

## 10. Checklist chất lượng

> Checklist chi tiết có sẵn trong `prompts/review-checklist.md` (kèm prompt gửi AI hỗ trợ duyệt từng chunk).


### Trước mỗi phiên dịch
- [ ] Đã đọc lại glossary chưa?
- [ ] Đã paste summary vào đầu phiên chưa?
- [ ] Đã paste 2 đoạn dịch gần nhất làm mẫu phong cách?
- [ ] Đã ghi rõ chunk nào đang làm?
- [ ] Git pull (nếu làm việc nhiều máy)?

### Trong mỗi phiên dịch
- [ ] Bản dịch có giữ đúng phong cách đã thống nhất?
- [ ] Tên riêng nhân vật đã nhất quán với glossary?
- [ ] Thuật ngữ chuyên ngành đã dùng đúng bản glossary?
- [ ] Có thuật ngữ mới nào cần hỏi ý kiến không?
- [ ] Đoạn thoại có giữ được sắc thái không?
- [ ] Có ký tự Hán/tiếng Anh nào sót không?

### Sau mỗi chunk dịch
- [ ] Đã chạy QA script (`glossary_qa.py`)?
- [ ] Đã sửa hết lỗi QA phát hiện?
- [ ] Đã cập nhật progress.md?
- [ ] Đã git commit?

### Trước khi ghép file hoàn chỉnh
- [ ] Tất cả chunks đã được dịch và duyệt?
- [ ] Glossary đã được cập nhật đầy đủ (cả .md và .csv)?
- [ ] Đã đọc lại 1 lần toàn bộ?
- [ ] Đã sửa chỗ không nhất quán?
- [ ] Mục lục đúng chưa?
- [ ] Format Markdown render đúng chưa?

---

## 11. Xử lý sự cố thường gặp

### Sự cố 1: MinerU không cài được hoặc xử lý quá kém
- **Triệu chứng**: Script lỗi, hoặc OCR ra text lung tung
- **Giải pháp**:
  - Thử PaddleOCR: `python scripts/ocr_paddle.py`
  - Tăng DPI: `--dpi 400` hoặc `--dpi 600`
  - Thử bản web zero-install [mineru.net](https://mineru.net)
  - Upload ảnh từng trang cho tôi qua chat
  - Cloud OCR (Google Cloud Vision) — tốn phí nhưng chất lượng cao

### Sự cố 2: Glossary chưa có → dịch sai tên
- **Triệu chứng**: Tên nhân vật bị dịch khác nhau giữa các chunk
- **Giải pháp**:
  - Dừng dịch
  - Đọc lại toàn bộ → thống nhất tên → cập nhật `glossary/<slug>.csv` và `.md`
  - Dùng Find & Replace để sửa các chunk đã dịch
  - Cập nhật QA script để phát hiện tự động lần sau

### Sự cố 3: Tôi quên ngữ cảnh giữa các phiên
- **Triệu chứng**: Bản dịch có vẻ không khớp với các phần trước
- **Giải pháp**:
  - Luôn paste summary + glossary ở đầu phiên
  - **Quan trọng**: paste 1-2 đoạn đã dịch gần nhất làm ví dụ phong cách
  - Nếu cần, paste cả chunk trước để tôi nắm bối cảnh

### Sự cố 4: Hán tự đặc biệt (Hán Việt cổ, Nhật Kanji, văn bản cổ)
- **Triệu chứng**: OpenCC chuẩn hóa sai
- **Giải pháp**:
  - Xác định loại Hán tự trước khi xử lý
  - Có thể cần custom config cho OpenCC
  - Hỏi tôi qua chat để được hỗ trợ từng trường hợp

### Sự cố 5: SRT bị lệch timestamp/index
- **Triệu chứng**: Phụ đề hiển thị sai thời gian hoặc dòng
- **Nguyên nhân**: Thường do copy/paste thủ công thay vì dùng pysrt
- **Giải pháp**:
  - Dùng `scripts/srt_translate.py` thay vì thủ công
  - Hoặc chạy QA mode SRT để phát hiện
  - Tái tạo lại từ file gốc

### Sự cố 6: Quá nhiều chunks → khó theo dõi
- **Triệu chứng**: Không biết đang ở đâu, đã làm gì
- **Giải pháp**:
  - Bắt buộc dùng file `working\progress\<slug>\progress.md`
  - Mỗi chunk xong → tick ngay
  - Cuối ngày review progress
  - Dùng git log để xem lịch sử

### Sự cố 7: Mojibake khi đọc file Markdown
- **Triệu chứng**: Chữ Trung hiển thị thành ký tự lạ (ä¸­æ–‡)
- **Nguyên nhân**: Encoding file không phải UTF-8
- **Giải pháp**:
  - Mở bằng VS Code → `File > Save with Encoding > UTF-8`
  - Khi tạo file PowerShell: thêm `$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'`
  - Khi tạo file Python: luôn `encoding='utf-8'`

### Sự cố 8: OneDrive sync conflict khi chạy script
- **Triệu chứng**: File bị lỗi, không sync được
- **Giải pháp**:
  - `working/extracted/`, `chunks/`, `qa/` không commit git → có thể xóa và tạo lại
  - **KHÔNG xóa** `working/summary/` và `working/progress/` — đó là tài sản tích lũy, có commit git
  - Tạm dừng OneDrive khi chạy batch lớn
  - Hoặc exclude các thư mục file to khỏi OneDrive sync (nếu cấu hình được)

### Sự cố 9: Tôi dịch một từ có nhiều nghĩa sai ngữ cảnh
- **Triệu chứng**: Cụm từ bị dịch sai nghĩa trong ngữ cảnh
- **Giải pháp**:
  - Sửa ngay trong bản dịch
  - Thêm vào glossary mục "Từ đa nghĩa" với nghĩa đúng trong ngữ cảnh này
  - Cảnh báo cho tôi ở đầu phiên sau

---

## 12. Mẹo tăng chất lượng dịch

1. **Glossary chi tiết từ đầu** — đầu tư 1-2 giờ glossary ban đầu sẽ tiết kiệm hàng giờ sau
2. **Paste 2 đoạn đã dịch gần nhất** vào đầu phiên — giúp tôi giữ phong cách nhất quán
3. **Đọc lại 1 chương trước khi dịch chương tiếp** — nắm bối cảnh
4. **Dịch theo ranh giới logic, không theo số từ** — 1 scene thoại hơn là 1000 từ rời rạc
5. **In bản dịch ra giấy** — bắt lỗi dễ hơn đọc trên màn hình
6. **Đọc to bản dịch** — phát hiện câu cụt, thiếu tự nhiên
7. **Lưu bản dịch thô và bản dịch sửa riêng** — có thể cần tham chiếu
8. **QA script sau mỗi chunk** — bắt lỗi nhất quán glossary ngay lập tức
9. **Commit git thường xuyên** — an toàn, dễ rollback

---

## 13. Git workflow

### 13.1 Khởi tạo

> **Điều kiện tiên quyết**: Đã chạy xong **Giai đoạn 0.4** (tạo file skeleton) trong PLAN.md mục 9. Nếu các file `README.md`, `glossary/`, `prompts/`, `scripts/requirements.txt` chưa tồn tại, lệnh `git add` bên dưới sẽ báo lỗi.

```powershell
cd "F:\OneDrive\onyx\Translate Book"
git init
git config user.name "Ten cua ban"
git config user.email "email@example.com"

# Commit đầu tiên
git add PLAN.md PROCESS.md README.md .gitignore glossary/ prompts/ scripts/requirements.txt
git commit -m "Initial commit: project structure"
```

### 13.2 Commit thường xuyên

Sau mỗi chunk dịch xong:
```powershell
git add output/$slug/chunk-001.md
git add glossary/$slug.*
git commit -m "feat($slug): chunk 001 - chuong 1"
```

Sau khi sửa glossary:
```powershell
git add glossary/$slug.csv glossary/$slug.md
git commit -m "glossary($slug): them 5 nhan vat moi"
```

### 13.3 Xem lịch sử

```powershell
git log --oneline
git log --stat  # chi tiết file thay đổi
```

### 13.4 So sánh phiên bản

```powershell
# Xem thay đổi trong file
git diff glossary/$slug.csv

# Xem thay đổi chunk đã sửa
git log -p output/$slug/chunk-001.md
```

### 13.5 Khi nào KHÔNG commit

- `input/` — file gốc có thể có bản quyền, không cần version control
- `working/extracted/`, `working/chunks/`, `working/qa/` — file to, tái tạo được từ input
- `working/summary/` và `working/progress/` — **CÓ commit** (tài sản tích lũy)
- `.venv/` — virtual environment, tái tạo được
- `__pycache__/`, `*.pyc` — Python cache

Cấu hình chi tiết trong `.gitignore`.

### 13.6 Lưu ý OneDrive + Git

- OneDrive sync tốt với text file (Markdown, CSV)
- Nhưng OneDrive KHÔNG hiểu git history → vẫn cần git
- Khi chạy script ghi nhiều file vào `working/`, có thể pause OneDrive tạm thời để tránh conflict

---

*Tài liệu này mô tả quy trình. Xem [PLAN.md](./PLAN.md) để hiểu bối cảnh tổng thể, lộ trình triển khai, và [README.md](./README.md) để bắt đầu nhanh.*
