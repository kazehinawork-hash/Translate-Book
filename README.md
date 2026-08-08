# Translate Book — Dự án dịch tài liệu EN/ZH → VI

> Hệ thống dịch tài liệu tiếng Anh và tiếng Trung sang tiếng Việt, tích hợp AI (qua chat) làm engine dịch chính.

---

## 🚀 Cách nhanh nhất cho người mới

1. **Cài đặt 1 lần**: Cài [Python](https://www.python.org/downloads/) (tick ✅ *Add to PATH*) và [Git](https://git-scm.com/download/win), rồi chạy `.git\setup.bat` — chờ script tự tạo venv + cài packages.
2. **Copy file PDF/EPUB vào `input\`**.
3. **Mở Command Code (hoặc opencode), gõ `/dich`** và chọn file → pipeline (extract → QC → detect ngôn ngữ → chunk → glossary → dịch → QA → merge → EPUB) tự chạy hoàn toàn, kết quả ở `output/books/<slug>/`. Sách dịch dở thì chạy lại `/dich` để dịch tiếp phần còn thiếu.

Không cần nhớ lệnh, không cần biết PowerShell. (*Sách scan cần thêm `pip install -U mineru; mineru-models-download`.*)

---

## 📚 Tài liệu

- **[AGENTS.md](./AGENTS.md)** — Quy tắc làm việc cho AI (pipeline đầy đủ, quy tắc git, **bộ nhớ phiên**, cấu trúc thư mục, bước audiobook)
- **[docs/STATE.md](./docs/STATE.md)** — Trạng thái sống của dự án (cuốn sách, việc đang làm, còn nợ, quyết định) — agent đọc/ghi mỗi phiên
- **[docs/session_log.md](./docs/session_log.md)** — Nhật ký phiên (append-only) — xem việc gần nhất đã làm/còn dở

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
python scripts/translate/translate_helper.py --interactive \
    --chunks-dir "working/chunks/mybook" \
    --progress-dir "working/progress/mybook" \
    --glossary "glossary/mybook.csv" \
    --source-lang English --target-lang Vietnamese \
    --auto-commit
```

### Hoặc dùng pipeline scripts riêng:

```bash
# Pipeline đầy đủ (tự động extract → chunk → glossary prompt)
python scripts/pipeline/run_pipeline.py --book "MyBook" --input "input/mybook.pdf" --lang en

# Agent dịch từng chunk:
python scripts/translate/translate_helper.py --interactive --chunks-dir "working/chunks/mybook" --progress-dir "working/progress/mybook" --glossary "glossary/mybook.csv"

# QA và Merge tự động:
python scripts/pipeline/run_pipeline.py --book "MyBook" --from-step 5
```

> Dùng `run_pipeline.py` cho trải nghiệm tốt nhất để tự động hóa toàn bộ quá trình.

**Chạy pipeline đầy đủ — tự động chọn định dạng theo ngôn ngữ:**

```bash
# Một lệnh duy nhất — không cần nhớ thêm flag nào
python scripts/pipeline/run_pipeline.py --input "input/sach.pdf" --book "Ten Sach" --lang auto

# Kết quả:
#   - Sách ZH → output/books/ten-sach/final/tamngu.md (tam ngữ ZH/Pinyin/VI)
#              → output/books/ten-sach/trilingual.epub (tự động, nếu có pandoc)
#   - Sách EN → output/books/ten-sach/final/vi.md (thuần Việt)
#              → output/books/ten-sach/final/vi.epub (tự động, nếu có pandoc)
```

**Workflow tổng quan:**

```
Bước 1: Extract   → scripts/extract/mineru_extract.py (PDF/DOCX/ảnh) hoặc scripts/extract/epub_extract.py (EPUB)
Bước 2: Chunk     → scripts/process/chunk_text.py (smart chunking, JSON output)
Bước 3: Gen Glossary → scripts/process/generate_glossary.py (tạo prompt → Agent tạo CSV)
Bước 4: Translate → Agent đọc batch manifest + glossary → ghi từng chunk vào working/progress/
Bước 5: QA        → scripts/qa/glossary_qa.py (kiểm tra nhất quán thuật ngữ và alignment)
Bước 6: Merge     → scripts/output/merge_chunks.py (gộp → output/books/<slug>/final/)
Bước 7: EPUB      → scripts/output/make_epub.py (tự động, dùng pandoc → output/books/<slug>/trilingual.epub)
Bước 8: Audiobook → scripts/audiobook/manage_voice.py (clone giọng) + scripts/audiobook/audiobook_long.py (→ MP3)

Khi dịch bằng AI Agent, `batch_manifest.py` tạo batch 2–4 chunk theo chương tại `working/progress/<slug>/batches/`. Agent claim batch riêng, chạy `batch_qa.py`, rồi ghi từng progress JSON trước khi đánh dấu hoàn tất. Audiobook lưu checkpoint nguyên tử, fingerprint cả `vi.md` và chỉ dùng lại cache WAV khi fingerprint text/voice/tham số khớp. Sau khi tạo audio, chạy `audio_qa.py` để kiểm tra đủ chapter và chất lượng file.
```

---

## 🎧 Tạo Audiobook (VieNeu-TTS v3 Turbo)

Sau khi có bản dịch thuần Việt `output/books/<slug>/final/vi.md`, có thể tạo audiobook bằng giọng clone:

```bash
# 1. Clone giọng từ audiobook mẫu (cần 3-8s reference audio sạch)
python scripts/audiobook/manage_voice.py extract --name my_voice --source "<file.mp3>" --auto
python scripts/audiobook/manage_voice.py list                    # xem các giọng đã có
python scripts/audiobook/manage_voice.py set-active --name my_voice

# 2. Tạo audio toàn cuốn (auto-detect chương, resume dở chừng, tự động ra MP3)
python scripts/audiobook/audiobook_long.py --slug <slug> --first   # thử 1 chương
python scripts/audiobook/audiobook_long.py --slug <slug>          # toàn cuốn
```

**Yêu cầu**: venv riêng `working/venv-vieneu/` (Python 3.11, `pip install vieneu`).

**Quy trình**: Đọc `final/vi.md` → `detect_chapters` theo heading → làm sạch markdown → smart chunk ≤240 chữ (giữ câu, paragraph-aware) → `tts.infer(chunk, voice, style="doc_truyen")` từng đoạn → checkpoint/resume theo chương + chunk → join + silence + normalize → WAV 48kHz → tự chuyển MP3 128kbps (kèm metadata title/album).

**Tham số**: chạy CPU/ONNX, RTF ~0.4 (nhanh hơn real-time 2.5x), không cần GPU; 14 giọng preset + voice cloning.

Xem chi tiết trong **[AGENTS.md](./AGENTS.md)** (Bước 11).

---

## 🖥 App desktop (C# WPF)

Thư mục `desktop/` chứa app Windows (C# WPF, .NET 8, giao diện **WPF-UI Fluent**) để duyệt/xem bản dịch:

- `Views/MainWindow.xaml` — cửa sổ chính: NavigationView trái (Sách / Audio / Cài đặt), **Realtime Log** dock bên phải (RichTextBox màu theo level, ô lọc, nút `</>` thu/mở)
- `Views/BooksPage.xaml` — danh sách sách tab Input (chưa dịch) / Output (đã dịch): card sách có avatar, stat tiles, progress; tab Output chỉ còn nút **Đọc thử**
- `Views/EpubPreviewWindow.xaml` — xem trước EPUB qua WebView2 (đọc tam ngữ / thuần Việt, kèm audio player nếu có audiobook), nút Đọc thử tự tìm file: `trilingual.epub` (ZH) → `final/vi.epub` (EN)
- `Views/AudioPage.xaml` — quản lý giọng VieNeu + tạo audiobook
- `Views/ApiPage.xaml` — cấu hình API dịch (provider/key/model)

Theme theo hệ thống (Dark/Light) qua WPF-UI `ThemesDictionary`. Chạy bằng Visual Studio / `dotnet run` từ `desktop/` (xem `desktop/TranslateBook.csproj`).

---

## ✅ Thành tựu — các cuốn sách đã hoàn thành

| STT | Slug | Tên sách | Ngôn ngữ gốc | Định dạng |
|-----|------|----------|:------------:|:---------:|
| 1 | `zuo-yi-ge-gang-gang-hao-de-nu-zi` | *Trở thành người phụ nữ vừa vặn* (做一个刚刚好的女子) — Khang Tĩnh Văn | ZH | EPUB + audiobook |
| 2 | `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` | *Trở thành người phụ nữ vừa vặn — Tập 3* (做一个刚刚好的女子·第三卷) — Vi Dương | ZH | EPUB + audiobook |
| 3 | `zuo-yi-ge-you-feng-gu-de-nu-zi` | *Trở thành người phụ nữ có phong thái* (做一个有风骨的女子) — Vi Dương | ZH | EPUB + audiobook |
| 4 | `ban-co-nam-cho-ngoi` | *Bạn Có Năm Chỗ Ngồi* — Nguyễn Nhật Ánh | VI | audiobook |
| 5 | `la-nam-trong-la` | *Lá Nằm Trong Lá* — Nguyễn Nhật Ánh | VI | audiobook |
| 6 | `eu-bim-task-group-handbook-v2-1` | *EU BIM Task Group Handbook* (BIM/Twin Transition) — EU | EN | vi.md + vi.epub (audiobook tùy chọn) |

Mỗi cuốn gồm bản dịch Markdown (`output/books/<slug>/final/`), EPUB (tam ngữ sách ZH / thuần Việt sách EN), ảnh và audiobook MP3 — **giữ local/Drive, không đẩy lên git**.

---

## 🗂 Cấu trúc thư mục

```
Translate Book\
├── input\              # File gốc PDF/EPUB (KHÔNG commit - bản quyền)
├── output\             # Sản phẩm dịch + audiobook (KHÔNG commit - giữ local/Drive)
│   └── books\<slug>\   # final\ (vi.md, tamngu.md), trilingual.epub, images\, audiobook\
├── working\
│   ├── extracted\      # Markdown gốc sau extract (KHÔNG commit)
│   ├── chunks\         # Chunk JSON (KHÔNG commit)
│   ├── progress\       # Chunk đã dịch (KHÔNG commit - sản phẩm)
│   ├── progress_audio\ # Tiến độ + cache audiobook (KHÔNG commit)
│   ├── qa\             # Báo cáo QA (KHÔNG commit)
│   └── venv-vieneu\    # venv VieNeu-TTS (KHÔNG commit)
├── glossary\           # Glossary cuốn + thể loại (KHÔNG commit - sản phẩm)
├── core\               # Audio mẫu + reference voices (KHÔNG commit - bản quyền)
├── desktop\            # App desktop C# WPF (CÓ commit - code)
├── scripts\            # Python scripts (CÓ commit - code)
├── prompts\            # Prompt mẫu cho Agent dịch
├── docs\               # Trí nhớ phiên (CÓ commit)
│   ├── STATE.md        # Trạng thái sống — agent đọc/ghi mỗi phiên
│   └── session_log.md  # Nhật ký phiên (append-only)
├── .commandcode\        # Cấu hình Command Code (agent, command, taste, permissions) (CÓ commit)
├── .opencode\           # Cấu hình opencode cũ (command, agent) (CÓ commit)
├── .gitignore
├── README.md
└── AGENTS.md
```

> **Chính sách git**: repo chỉ chứa **code** (`scripts/`, `desktop/`, `.opencode/`, config, docs). Toàn bộ sản phẩm (bản dịch, glossary, audiobook, EPUB, progress) **không commit** — giữ local/OneDrive/Drive.

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

Dùng `scripts/output/merge_chunks.py --format trilingual` để gộp → `output/{book}_trilingual.md`.
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
| **batch_manifest.py** | Điều phối batch Agent, claim/complete/fail/verify chunk | Ngăn trùng/sót khi dịch theo batch |
| **merge_chunks.py** | Gộp chunk đã dịch → file hoàn chỉnh | Có validation thiếu/trùng/tổng chunk |
| **run_pipeline.py** | Orchestrator chính (--from-step/--to-step/--auto) | Script chạy toàn bộ pipeline tự động |
| **pandoc** | Chuyển .md → .epub với CSS tùy chỉnh | Cài từ https://pandoc.org/installing.html |
| **VieNeu-TTS v3 Turbo** | Tạo audiobook — clone giọng từ reference audio | CPU/ONNX, 48kHz, 14 giọng preset, voice cloning 3-8s |
| **manage_voice.py** | Quản lý reference voice: extract (VAD auto), list/info/delete/set-active | `scripts/audiobook/` |
| **audiobook_long.py** | Tạo audiobook toàn cuốn từ `final/vi.md`: detect chương, smart chunk, resume, cache fingerprint, auto MP3 | `scripts/audiobook/` |
| **batch_qa.py** | QA nhanh progress theo batch: rỗng, marker lỗi, alignment tam ngữ | `scripts/qa/` |
| **audio_qa.py** | QA coverage audiobook, WAV/MP3, duration, sample rate và clipping | Báo cáo `working/qa/<slug>/audio-report.json` |
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
- **Git chỉ giữ code** — sản phẩm (bản dịch, audiobook, EPUB, glossary, progress) để local/Drive, không đẩy binary nặng lên GitHub

---

## 🩹 Troubleshooting nhanh

| Lỗi | Fix |
|-----|-----|
| `ModuleNotFoundError: No module named 'X'` | `pip install -r requirements.txt` (chạy lại `setup.bat`) |
| PowerShell in ra `?\u1ebf?` | Thêm UTF-8 vào `$PROFILE`: `[Console]::OutputEncoding=[System.Text.Encoding]::UTF8` |
| EPUB lỗi "không tìm thấy ebooklib" | `pip install ebooklib beautifulsoup4 markdownify` |
| QA báo nhiều Hán tự sót | Dịch chưa xong / glossary thiếu → bổ sung glossary |
| `pandoc: command not found` | Cài pandoc: https://pandoc.org/installing.html |
| Audiobook không tìm thấy giọng | `manage_voice.py set-active --name <giọng>` (giọng nằm `core\voices\`) |

> Merge báo thiếu/empty chunk → dịch hết hoặc dùng `--allow-partial`/`--skip-missing`.

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
