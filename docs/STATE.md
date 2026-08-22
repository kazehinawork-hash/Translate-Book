# 🧠 STATE — Trạng thái sống của dự án

> File này là **bộ nhớ trí nhớ chính** của agent (opencode). ĐƯỢC cập nhật mỗi phiên.
> **ĐẦU PHIÊN**: agent bắt buộc đọc file này + 2 entry cuối `session_log.md` trước khi làm việc.
> **CUỐI PHIÊN / XONG VIỆC**: cập nhật lại để phiên sau nối tiếp chính xác.
> (Có commit — thuộc phạm vi docs, không chứa sản phẩm.)

---

## 📚 Các cuốn sách

> Thư mục output đặt tên theo **tên sách gốc** (tên file input); mỗi thư mục có `metadata.json` ghi `slug` nội bộ. Slug vẫn dùng cho progress/chunks/glossary/audio.

| Slug (nội bộ) | Thư mục output (tên gốc) | Ngôn ngữ | Giai đoạn | Ghi chú / Bước tiếp theo |
|---|---|:--------:|-----------|--------------------------|
| `zuo-yi-ge-you-feng-gu-de-nu-zi` | `做一个有风骨的女子` | ZH | ✅ Hoàn tất | EPUB + audiobook (85 chương). Tác giả Vi Dương |
| `zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing` | `做一个有风骨的女子  不迎合, 不媚俗 (晚晴)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (66 chunks). **Dịch mới + audiobook 44/44 chương GPU + nhạc nền AI (08-18)**: input `.azw3` (Kindle) → calibre chuyển EPUB → extract 50 mục → 66 chunk → profile văn chương → dịch 66/66 (97K từ, khớp dòng 100%, QA Hán sót 0.0%) → đồng bộ TOC (46 mục = body) → 1 EPUB nhúng font. Audiobook: `--music-auto` đọc music_map.json (44 chương, mỗi chương 1 bài theo cảm xúc), volume 0.15, batch 16, temp 0.3, top_k 10. ~7.2 giờ audio (414MB). ⚠️ Slug khác cuốn cùng tên của Vi Dương (`zuo-yi-ge-you-feng-gu-de-nu-zi`) — đã dùng suffix `-wan-qing`. Tác giả Vãn Tình |
| `ban-co-nam-cho-ngoi` | `Ban Co Nam Cho Ngoi - Nguyen Nhat Anh` | VI | ✅ Hoàn tất | Audiobook 12/12 chương **GPU + nhạc nền (08-13)**: toàn bộ chương chạy lại bằng GPU batch 16, nhạc nền xoay `sach_ke_chuyen_10_lofi.mp3` / `sach_ke_chuyen_11_lofi.mp3`, **volume 0.15** (giảm từ 0.20), temp 0.3, top_k 10. ~3h09 audio. Tác giả Nguyễn Nhật Ánh |
| `dac-nhan-tam` | `Đắc Nhân Tâm - Dale Carnegie` | VI | ✅ Hoàn tất | Audiobook. Tác giả Dale Carnegie |
| `rung-na-uy` | `Rung Na-uy - Haruki Murakami` | VI | ✅ Hoàn tất | Audiobook. Tác giả Haruki Murakami |
| `eu-bim-task-group-handbook-v2-1` | `EU-BIM-Task-Group-Handbook-V2.1` | EN | 📗 Dịch xong | Handbook kỹ thuật BIM/Twin Transition (EU). Đã dịch 9/9 chunk, songngu.md + vi.md + vi.epub. Audiobook chưa làm (sách tài liệu kỹ thuật, tùy chọn) |
| `qie-yi-qing-shen-gong-bai-tou` | `且以情深共白头：婚前看情感，婚后靠相处 (晚情)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (58 chunks). **Dịch lại toàn bộ theo chuẩn văn chương mới + audiobook 75/75 chương GPU + nhạc nền AI (08-17)**: profile văn chương `working/profile/qie-yi-qing-shen-gong-bai-tou.md` → dịch 58/58 chunk (84K từ, 100% khớp dòng, QA Hán sót 0.0%) → merge tamngu.md + vi.md (đồng bộ mục lục với heading mới) → 1 EPUB nhúng font. Audiobook: `--music-auto` đọc `music_map.json` (75 chương, mỗi chương 1 bài theo cảm xúc), volume 0.15, batch 16, temp 0.3, top_k 10. ~6.4 giờ audio (369MB). Tác giả Vãn Tình |
| `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` | `做一个刚刚好的女子  不攀附, 不将就 (晚情)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (71 chunks). **Dịch lại toàn bộ theo chuẩn văn chương + audiobook mới GPU + nhạc nền AI (08-18)**: profile `working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing.md` → dịch 71/71 chunk (109K từ, khớp dòng 100%, QA Hán sót 0.0%) → merge tamngu.md + vi.md (đồng bộ mục lục titles.json) → 1 EPUB nhúng font Noto Serif SC (~15.5MB). Audiobook: music_map 50 chương, volume 0.15, batch 16, temp 0.3, top_k 10, ~7.4 giờ audio (405MB). Tác giả Vãn Tình |
| `zuo-yi-ge-you-jing-jie-de-nu-zi` | `做一个有境界的女子  不自轻,不自弃 (晚情)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình: "Làm một người phụ nữ có cảnh giới" (56 chunks). Audiobook chưa làm (tùy chọn) |
| `you-duo-xiang-jiu-you-duo-xing-fu` | `有多想要，就有多幸福 (晚情著)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (32 chunks). EPUB sách toàn ảnh 320 trang → OCR PaddleOCR (GPU) → raw.md 113KB. Dịch đủ 32/32 chunk, QA 0 lỗi, merge tamngu.md + vi.md + trilingual.epub. **Audiobook 71/71 chương GPU + nhạc nền AI (08-16)**: music_map theo cảm xúc từng chương, volume 0.15, batch 16. ~6h06 audio. Tác giả Vãn Tình |

**Giai đoạn**: `⛁ Extract → 🔶 Dịch → ⚙️ QA/Merge → 📗 EPUB → 🎧 Audiobook → ✅ Hoàn tất`

---

## 🔨 Đang làm (hiện tại)

- **Master glossary (08-13)**: gom toàn bộ glossary về **1 file `glossary/master.csv`** (346 thuật ngữ, cột `source,target,type,note,book,author,genre`) — bỏ mô hình nhiều file per-book. Tự tách `master_001.csv` khi >300 dòng. Script: `glossary_lib.py` (đọc/lọc theo book/author/genre), `merge_glossary.py` (gộp cuốn mới vào master — tự cập nhật thuật ngữ mới, tự đoán type, có `--check-dup`), `build_master.py` (gộp lần đầu). **Đã nâng cấp master (08-13)**: chuẩn hóa 3 từ trùng dịch (`修养`→Tu dưỡng, `尊严`→Nhân phẩm, `善良`→Tốt bụng), dịch 239 note Anh→Việt, thêm `infer_type()` tự phân loại character/place/phrase/term, thêm `--check-dup` chặn source trùng target khác. Đã sửa `run_pipeline.py`, `glossary_qa.py`, `translate_helper.py`, `translate.py` dùng master. **Fix root cause `_common.py`**: PROJECT_ROOT dùng `.resolve()` (fix bug merge_chunks ghi sai vị trí). **Thư mục `glossary/` tối giản**: chỉ `master.csv` + `_template.*`. Xem chi tiết session_log.

- **Prompt dịch văn chương "láng" (08-14)**: thêm phần `## LITERARY QUALITY` (8 quy tắc: dịch cả câu/đoạn, nhịp điệu, khẩu ngữ tự nhiên, xưng hô nhất quán, cảm xúc/hình ảnh, thuần Việt, tránh dịch máy) vào `translate_helper.py::build_prompt` (cả nhánh bilingual + trilingual) + `prompts/translate_prompt.md` + **ví dụ "cứng vs láng"** trước/sau. Sách mới dịch sẽ mượt hơn. Áp dụng từ 08-14.
- **Hồ sơ văn chương (book profile) — 08-14**: script `scripts/translate/create_book_profile.py` — in vài chunk đại diện + khung hồ sơ → agent viết `working/profile/<slug>.md` (tác giả/giọng văn, hệ xưng hô từng cặp nhân vật, hội thoại, thành ngữ, **đoạn dịch mẫu chuẩn "láng"**, lưu ý). Đã thêm bước **F2** vào `/dich` (cả `.commandcode` + `.opencode`): chạy trước khi dịch, mỗi batch dịch phải đọc profile. Nâng chất lượng dịch toàn diện.
- **QA văn chương mức A tối đa (08-14)**: nâng cấp `glossary_qa.py` thêm `qa_van_chuong()` — 4 kiểm tra miễn phí (0 token): (1) lặp từ liền kề trong câu (≥3 lần, bỏ từ dừng), (2) cụm "dịch máy" dùng nhiều ("một cách", "những điều", "mà còn", "đã được", "đối với"... ≥3 lần), (3) câu >90 chữ (dễ cứng), (4) tỷ lệ từ Hán-Việt >30% (nghi dịch sát chữ). Chạy tự động trong QA pipeline, báo cáo mục "Chất lượng văn chương". Test trên `ban-co-nam-cho-ngoi/vi.md`: bắt được 31× "một cách", 15× "đối với", 82 chỗ lặp từ — chứng minh giá trị cho sách tương lai.

- **Text preprocessing audiobook (08-22)**: tích hợp 3 tính năng từ VoiceStudio repo:
  - `scripts/audiobook/text_normalize.py`: chuẩn hoá text trước TTS — xóa ký tự Unicode nguy hiểm (zero-width, bidi, BOM), decode HTML entities (`&amp;→&`), giới hạn ký tự lặp (`!!!!!→!!!`), gộp whitespace. Pure function, idempotent.
  - `scripts/audiobook/pronunciation.py`: pronunciation lexicon — word-boundary-aware replacement (longest-key-first), inline overrides `[[term|replacement]]`, load per-book JSON từ `working/profile/<slug>-pronunciation.json`. Merge với DEFAULT_PRONOUNCE + --pronounce-json.
  - Nâng cấp `_split_sentences`: multi-language abbreviation (ks., ts., ths., cv., bs., ds., pgs.), CJK full-width punctuation (。！？) tách đúng dù không có space.
  - Nâng cấp `smart_chunk`: thêm unspeakable-merge — gộp chunk chỉ chứa dấu câu vào chunk liền kề (tránh TTS đọc nhảm).
  - `_preprocess_chunk_text` chạy cho MỖI chunk trước khi TTS: `normalize_for_tts()` → `apply_pronunciation()`.
  - `_load_book_pronunciation()` load per-book pronunciation JSON vào _pronounce_map TRƯỚC khi extract_chapter_text xử lý.
  - Test OK: sample 12s từ `ban-co-nam-cho-ngoi` chạy thành công, preprocessing hoạt động đúng.

- **Cải tổ thư mục `input/` theo trạng thái (08-13)**: chia thành `input/chua-lam/` (chưa làm), `input/da-dich/` (đã dịch, chưa audio), `input/da-audio/` (đã dịch + audio). Script `scripts/manage_input.py` tự dò `output/books/` → di chuyển file input vào đúng thư mục; chạy sau mỗi pipeline (đã thêm vào `dich.md` bước K). Hiện trạng: chua-lam 4 file (2 PDF + 2 EPUB), da-dich 3, da-audio 6. Có `input/README.md` giải thích. `dich.md` mục A/B đã cập nhật tìm file trong thư mục con.

- **GPU toàn pipeline đã setup (08-12)**: RTX 3060 12GB được dùng cho cả 3 công đoạn nặng:
  - **TTS (venv `working\venv-vieneu`)**: vieneu **3.2.5** (nâng 08-14, fix chunk theo câu + trích dẫn + max_new_frames 600) + torch 2.13.0+cu126 → `audiobook_long.py --gpu --batch-size 16` dùng `infer_batch` static batching, RTF 0.12 (nhanh ~2x so với batch-size 8 cũ, benchmark 08-13). **Chuẩn GPU cho mọi sách sau: `--batch-size 16`**. Patch local `inference_v3_turbo.py::_load_mono` dùng soundfile (torchaudio cần torchcodec + FFmpeg shared không có) — **phải áp lại mỗi lần cài lại vieneu**.
  - **MinerU (`.venv`)**: nâng torch 2.13.0+cu126 → `mineru_extract.py --device auto` tự nhận GPU. Đã gỡ sạch paddle/paddleocr/paddlex khỏi `.venv` (chúng xung đột cuDNN DLL với torch CUDA).
  - **PaddleOCR (venv mới `working\venv-ocr`)**: paddlepaddle-gpu 3.3.1 (cu126) + paddleocr 3.7.0, **không có torch** → chạy GPU sạch (GPU Compute Capability 8.6, RTX 3060). `ocr_paddle.py` đã sửa sang API 3.x (`device='gpu'/'cpu'`, `predict()` → `rec_texts`) + cơ chế **tự relaunch qua venv-ocr** khi env hiện tại thiếu paddleocr. Lưu ý: cảnh báo CUDNN 9.9 (paddle) vs 9.5 (torch) — chạy ổn, chỉ là cảnh báo.
  - ⚠️ **Không import torch + paddle trong cùng 1 tiến trình** (xung đột cuDNN DLL trên Windows) — các script đã tách venv riêng nên không gặp.
- Sách `ban-co-nam-cho-ngoi` (Nguyễn Nhật Ánh): **✅ Hoàn tất 12/12 chương GPU batch 16 + nhạc nền (08-14)** — toàn bộ chương chạy lại trên GPU (RTF ~0.12 benchmark, batch 16 nhanh ~2x) với nhạc nền xoay 2 bài (`sach_ke_chuyen_10_lofi.mp3` ch1/3/5..., `sach_ke_chuyen_11_lofi.mp3` ch2/4/6...), **volume 0.15**. **Đã fix lỗi đọc lặp câu (08-14)**: root cause là chunk cực ngắn (<50 ký tự, câu hội thoại đứng riêng) khiến model hallucinate (bịa thêm nội dung dài, vd ch05 câu "màu đỏ là màu hoa hồng." đọc thành 67 giây). Fix ở `audiobook_long.py`: gộp paragraph ngắn vào paragraph trước (`extract_chapter_text`) + `smart_chunk` gộp chunk ngắn cả 2 chiều, cho phép vượt max_chars lên tới TTS_MAX_CHARS (320) khi cần. Kết quả: 0 chunk <50 ký tự trong 12 chương, max chunk 317, hết hallucinate. Tổng ~3h09 audio (~182MB). File `ch01_old.mp3` là bản CPU cũ giữ lại.

- **Tính năng nhạc nền (music bed) audiobook — đã chốt (08-12, chỉnh 08-13)**: `audiobook_long.py` thêm `--music` (tên file trong `core/music/`, nhiều file cách dấu phẩy xoay theo chương) + `--music-volume`. Trộn nhạc DƯỚI giọng với ducking (khi đọc ~7%, khi nghỉ ~15% ở volume 0.15), crossfade loop, loudness normalize (mọi bài về RMS 0.18 — bài master to/nhỏ đều nghe đều), metadata bump pipeline v5 (đổi nhạc/volume tự tạo lại). **Mức chốt mới: volume 0.15, MIN_RATIO 0.50** (giảm từ 0.20 — user yêu cầu nhạc nhỏ hơn 08-13). User sẽ bổ sung thêm music vào `core/music/` — pipeline tự dò + xoay + normalize, chỉ dùng đúng file có trong đó.
- Sách `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` (tản văn Vãn Tình, ZH): **✅ Đã dịch lại toàn bộ theo chuẩn văn chương + audiobook mới (08-18)** — xem dòng bảng phía trên. Chi tiết: profile `working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing.md` + title map `...-titles.json` (51 mục) + glossary lọc `...-glossary.txt`; dịch 71/71 chunk bằng sub-agent (bám profile, khớp dòng 100%, fix chunk 49 để sót Hán → dịch lại), QA batch 0 lỗi + Hán sót 0.0%; merge tamngu.md (1.86MB) + vi.md (600KB); 1 EPUB nhúng font Noto Serif SC (~15.5MB, 13 ảnh images/). Audiobook 50/50 chương GPU batch 16 + nhạc nền AI music_map (volume 0.15, temp 0.3, top_k 10), ~7.4 giờ audio (405MB), đã xóa 3 dòng artifact `## [N] text0000X.html` khỏi vi.md + rebuild EPUB.
- Sách `有多想要，就有多幸福` (Có bao nhiêu khao khát, có bấy nhiêu hạnh phúc — Vãn Tình, ZH, 08-15): ✅ **Hoàn tất (bản cuối)** — EPUB scan 320 ảnh → **OCR MinerU GPU** → **`mark_chapters.py` tách chương** (mục lục → `## Chương N`, xóa `## Trang`) → 55 chunk → dịch 55/55 (QA 0 lỗi) → merge + **`merge_sentences.py` gộp câu + bỏ số trang** → **71 chương sạch, 0 dòng Trang** → 1 EPUB duy nhất `有多想要，就有多幸福 (晚情著).epub` (nhúng font). Output `output/books/有多想要，就有多幸福 (晚情著)/` (metadata.json + final/{tamngu.md, vi.md}). Audiobook chưa làm.
- Sách `qie-yi-qing-shen-gong-bai-tou` (tản văn Vãn Tình, ZH): **✅ Đã dịch lại toàn bộ theo chuẩn văn chương + audiobook mới (08-17)** — xem dòng bảng phía trên. Chi tiết: profile `working/profile/qie-yi-qing-shen-gong-bai-tou.md`, dịch 58/58 chunk bằng sub-agent 1 chunk/lượt (bám profile, khớp dòng 100%), fix chunk 14 (gộp 2 câu → tách), đồng bộ mục lục chunk 0 với heading body mới, QA Hán sót 0.0%, EPUB nhúng font, audiobook 75/75 chương GPU batch 16 + nhạc nền AI music_map (volume 0.15, temp 0.3, top_k 10), ~6.4 giờ audio.
- Sách `zuo-yi-ge-you-jing-jie-de-nu-zi` (tản văn của Vãn Tình, ZH, 08-12): ✅ Hoàn tất — EPUB scan 281 trang đã OCR (PaddleOCR) → raw.md 105KB, chunk 56, dịch đủ 56/56 chunk (85.882 từ), QA 0 lỗi, merge tamngu.md (1.54MB) + vi.md (511KB) + trilingual.epub (155KB). Audiobook chưa làm (ZH, tùy chọn).
- Sách `eu-bim-task-group-handbook-v2-1`: ✅ Hoàn tất (9/9 chunk, QA 0 lỗi) — đã merge + vi.md + vi.epub + images/. Audiobook optional (chưa làm). Còn chunk 2,3 đã hoàn tất hết theo log phiên 08-07.
- Sửa lỗi preview "Đọc thử" EPUB trắng tinh trên desktop app (WPF) — **đã hoàn tất**: nguyên nhân là `BuildEpubCss()`/`ReapplyThemeColors` đọc WPF-UI brush từ `Application.Current.Resources` trả về màu trắng/gần trong suốt (`#08FFFFFF`, `#FFFFFFFF`) → `--bg-color: #FFFFFF` làm vùng đọc trắng. Fix: thêm `GetSafeColor()` kiểm tra alpha + luminance, fallback palette dark theme (`#1E1E1E` nền/`#E0E0E0` chữ/`#B0B0B0` phụ). Verify thực tế: log `bgHex=#1E1E1E`, pixel màn hình nền tối RGB(24-31). Build 0 lỗi/0 cảnh báo.
- UI desktop tinh chỉnh phiên 08-08 (đã build 0 lỗi/0 cảnh báo, app chạy ổn):
  - **Fix preview trắng** (mô tả trên) + `ReadTextFileWithEncoding()` (detect BOM UTF-8/16 cho chapter XHTML chống mojibake) + null-check `BtnRefreshTheme_Click` + `DefaultBackgroundColor="#1E1E1E"`.
  - **FindPreviewEpub()**: nút "Đọc thử" hết hard-code `trilingual.epub` → tìm theo thứ tự `trilingual.epub` → `final/vi.epub` (sách EN) → `.epub` bất kỳ. Verify `eu-bim` (EN) mở được `final/vi.epub`.
  - **Realtime Log** chuyển từ đáy sang **panel dọc phải 300px**: RichTextBox màu theo level (ERR đỏ/WARN vàng/INFO xám), ô "Lọc" hoạt động (filter theo dòng), nút Xóa/📋; thu gọn hoàn toàn bằng nút `<`/`>` (toggle chuẩn: mở hiện `<`, thu hiện `>`).
  - **Card sách** Input/Output làm đẹp: avatar tròn chữ cái đầu, header nền, badge trạng thái, stat tiles (Chunks/EPUB/Audio), progress bar; hover chỉ đổi shadow (bỏ translate gây giật khi chuột gần mép).
  - **Tab Input/Output** có animation fade + trượt lên (180ms CubicEase).
  - Tab Output gọn: chỉ còn nút **Đọc thử** (bỏ Dịch/Gộp/EPUB/QA/Audio — tạo audiobook ở trang Audio, nghe trong cửa sổ Đọc thử).
- UI nâng cấp tiếp (08-08, build 0 lỗi/0 cảnh báo):
  - **Busy overlay** toàn cửa sổ: ProgressRing + BusyMessage + nút "Hủy thao tác" — hiện khi chạy pipeline/dịch/QA/audio; `IsBusyAny` gồm cả per-book busy (qua `BookStatus.AnyBusyChanged`).
  - **Ảnh bìa card sách** (Output): tìm ảnh trong `images/` (ưu tiên tên cover/front), fallback avatar chữ.
  - **Empty state** Input/Output có icon + nút "Mở thư mục input" (mở Explorer).
  - **AudioPage**: progress bar "Chương N" khi tạo audio (`AudioDone`/`AudioTotal` set trong GetBookStatus).
  - **Global search**: Enter ở ô tìm kiếm titlebar → nhảy tới tab Sách + lọc; **Ctrl+F** → focus ô tìm kiếm.
  - **Fix mất log**: replay `LogText` khi MainWindow subscribe (log khởi tạo không bị mất).
  - **Search theo tên**: filter khớp slug + DisplayTitle + tên file (tìm được tên tiếng Trung/Việt).
  - **Toolbar preview**: bọc ScrollViewer ngang + thu gọn nút (Làm mới, zoom 90, search 160) — hết bị cắt nút Tiếp/Trước.
  - **Fix**: `GenerateAudiobookAsync` set `IsVoiceBusy` (trước đây overlay không hiện khi tạo audio).

- **Nâng cấp EPUB Preview Window (08-22)**:
  - **Tự động lưu & Khôi phục vị trí đọc (Auto-Resume / Bookmark)**: JS theo dõi sự kiện cuộn trang với debounce 400ms, gửi tọa độ scrollY + phần trăm tiến độ về C#; lưu nguyên tử vào `%LocalAppData%\TranslateBook\reading_bookmarks.json`. Khi mở lại sách, tự động nhảy mượt về vị trí đọc dở. Hiển thị phần trăm đọc trên Toolbar.
  - **Tùy biến Typography & Chiều rộng trang (Typography Settings)**: Thêm bộ điều khiển trực quan trên Toolbar (chọn Phông chữ: Segoe UI, Serif, Cổ điển, Monospace; chọn Độ rộng lề: Gọn 650px, Vừa 800px, Rộng 1000px, Toàn màn hình 95%; chọn Khoảng cách dòng: 1.5x, 1.8x, 2.2x). Tiêm biến CSS trực tiếp vào WebView2 DOM mà không cần reload trang.
  - `dotnet build` đạt 0 lỗi.

---

## ⏳ Việc còn nợ / Đề xuất tiếp theo

- Luồng chính dùng AI Agent trực tiếp, không dùng API; tối ưu bằng cách giảm số lượt trao đổi và số lần Agent phải đọc/ghi file.
- Thay vì dịch từng chunk một, cho Agent xử lý theo batch nhỏ (2–4 chunk hoặc một nhóm theo chương) trong cùng lượt, nhưng vẫn ghi từng progress JSON để resume an toàn.
- Có thể giao các nhóm chương độc lập cho nhiều Agent song song; không chia giữa một chương nếu cần giữ văn phong/ngữ cảnh.
- Tạo prompt/batch manifest cố định, cache glossary và ngữ cảnh chung; Agent chỉ đọc phần cần dịch thay vì quét lại toàn bộ thư mục.
- QA/kiểm tra số dòng và glossary chạy sau mỗi batch; chỉ giao lại các chunk lỗi, không dịch lại cả sách.
- API trong desktop chỉ là hướng tương lai, không dùng làm cơ sở ưu tiên hiệu suất hiện tại.
- **Dual-Agent tối ưu chi phí (08-08)**: cấu hình 3 vai — analyzer (Luna) plan theo LÔ → executor (Laguna free) thực thi từng item → reviewer (deepseek-v4-flash) review độc lập. Bước 0 phân loại task: task bé chạy thẳng (không dùng pipeline), task ≥ trung bình mới vào pipeline. Luna chỉ chạy 1 lần/1 lô (giảm chi phí đáng kể: dual cũ ~$5.9/task → mới ~$0.47/task theo benchmark lô 2 task). Giám sát Laguna vô thời hạn: chạy background, kiểm tra `agent_output(status)` định kỳ, chỉ dừng khi executor tự trả `BLOCKED` hoặc mất kết nối; kèm xác minh sơ bộ kết quả trước khi gửi review vì Laguna là model yếu.
- Multi-Agent đã có workflow tối đa 2 vòng review/sửa: vòng 1 plan → implement → review; chỉ khi `NEEDS_CHANGES` mới sửa một lần và review 2 rồi bắt buộc dừng. Prompt đã tối ưu theo hướng giảm context lặp nhưng giữ success criteria, file scope, diff và test evidence. Đã ổn định permission bằng `dont-ask`: analyzer chỉ đọc, executor chỉ read/write/edit không dùng shell; test analyzer đọc và executor ghi scratchpad đều đạt. **E2E hai vòng đã chạy thành công 08-07**: analyzer plan → executor implement → review 1 `NEEDS_CHANGES` → executor sửa 1 lần → review 2 `APPROVED`; kết thúc đúng quy tắc giới hạn vòng. Hai phát hiện: (1) executor không có shell nên không tự chạy `git status` — git check nên giao orchestrator; (2) `.gitignore` chỉ ignore thư mục con cụ thể của `working/`, không ignore toàn bộ — file test tạm nên đặt trong `working/qa/` hoặc thư mục được ignore khác.
- Đã triển khai workflow AI Agent theo batch: `scripts/translate/batch_manifest.py` tạo/claim/complete/fail/verify batch, `.opencode/command/dich.md` bắt buộc dùng manifest + QA batch.
- Đã thêm `scripts/qa/batch_qa.py` kiểm tra rỗng/marker/alignment tam ngữ; `merge_chunks.py` chặn duplicate và total_chunks không nhất quán.
- Audiobook checkpoint được ghi nguyên tử, lưu metadata và chỉ tái dùng WAV khi fingerprint text/voice/tham số khớp; không triển khai TTS song song.
- Compile, smoke test và diagnostics đạt; đã thêm `audio_qa.py` dùng thư viện chuẩn WAV, không phụ thuộc soundfile khi QA.
- QA thực tế đạt cho 3 audiobook ZH: `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` (65 chương), `zuo-yi-ge-you-feng-gu-de-nu-zi` (85 chương), `zuo-yi-ge-gang-gang-hao-de-nu-zi` (67 chương); đủ chapter liên tục, MP3 hợp lệ, duration đọc được.
- Desktop `dotnet restore` + `dotnet build --no-restore` đạt 0 lỗi/0 cảnh báo; diagnostics sạch.
- Pytest chưa chạy được vì `.venv` trỏ Python 3.11 đã gỡ và Python 3.14 chưa cài pytest; unit harness/compile/smoke test đã đạt.

---

## ⏳ Việc còn nợ / Còn dở

- App desktop: đã fix lỗi NullReferenceException ở nút "Đọc thử" EPUB (Preview): guard `Application.Current`/`MainWindow`/slug/project-root trong `OpenEpubPreviewAsync` + null-check `CoreWebView2` và EPUB path trong `EpubPreviewWindow`, cùng guard 9 handler phụ thuộc. Chưa kiểm thử runtime do chưa có API key; chờ user test các lệnh Dịch/Audio/QA.

---

## 🧭 Quyết định gần đây

- App desktop (C# WPF) refactor hoàn tất (0 lỗi, 0 cảnh báo): fix StartTranslateAsync → dịch thật qua API, fix audiobook Python/temperature/--force/CancelCommand/WebView2/CSS/log dấu/LogText cap. Xem chi tiết phần trên.
- Repo git **chỉ chứa CODE**; sản phẩm (bản dịch, glossary, audiobook, EPUB, progress) giữ local/Drive, không commit.
- Lịch sử git đã được rewrite (`filter-branch`) — repo giảm từ ~717MB → 0.4MB, không còn binary.
- Docs rút gọn: README là tài liệu duy nhất; đã xoá `QUICKSTART.md`, `USAGE.md`.
- Triển khai **Memory Bank** (STATE.md + session_log.md + AGENTS.md để agent tự đọc/ghi giữa phiên).
- **Fix desktop "Đọc thử" EPUB**: `MainViewModel.OpenEpubPreviewAsync` + `EpubPreviewWindow` (WebView2 `CoreWebView2` + EPUB path) thêm null-guard đầy đủ; 9 handler WebView2 phụ thuộc cũng được guard. Build `dotnet build` 0 lỗi/0 cảnh báo. dual-Agent workflow: analyzer plan → executor implement → Review 1 `FINAL_STATUS: APPROVED` (review_count=1, không cần sửa lần 2).

---

## 📝 Ghi chú chung

- **Python 3.11 đã bị gỡ khỏi máy** → venv `.venv` (trỏ 3.11) HỎNG. Script chạy trực tiếp bằng `python` (3.14). Khi dùng `merge_chunks.py` phải luôn truyền `--output-dir` tường minh (PROJECT_ROOT tự dò bị lệch).
- Audiobook venv `working\venv-vieneu\Scripts\python.exe` (Python 3.11) — **đã tạo lại** từ Python 3.11.9 (`C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe`) sau khi base Python 3.14 bị gỡ gây hỏng venv; cài `pip install torch torchaudio` (CPU) + `vieneu==3.2.5` (nâng 08-14 từ 3.2.4, kèm sea-g2p 0.8.4). Chạy OK (torch 2.13.0+cpu, torchaudio 2.11.0+cpu). **Sau khi nâng cấp vieneu phải áp lại patch `_load_mono` soundfile.**
- Console Windows mặc định cp1252 → Python cần `sys.stdout.reconfigure(encoding='utf-8')`.
- pandoc tại `C:\Users\RiverWind\AppData\Local\Pandoc\pandoc.exe` (có trong PATH).
- Lệnh dịch trọn sách: `/dich` (chỉ dịch — copy file vào `input\` rồi gõ lệnh), `/audio` (tạo audiobook cho sách đã dịch — nhạc nền AI theo nội dung), `/dich_audio` (dịch + audio trong 1 lệnh).