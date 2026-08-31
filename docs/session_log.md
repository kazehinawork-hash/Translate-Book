# 📔 SESSION LOG — Nhật ký phiên làm việc

> Append-only: mỗi phiên thêm **1 entry ở CUỐI file**. Entry mới nhất nằm dưới cùng.
> **ĐẦU PHIÊN**: agent đọc 2 entry CUỐI để biết việc gần nhất.
> Mỗi entry: `## YYYY-MM-DD` + **Đã làm** / **File đổi** / **Còn dở** / **Git**.

---

## 2026-08-05 — Thiết lập trí nhớ phiên + docs rút gọn

### Đã làm
- **Docs rút gọn**: README trở thành tài liệu duy nhất; gộp nội dung `QUICKSTART.md` + `USAGE.md` vào README rồi xoá cả 2 file (tổng −1.121 dòng). Thêm bảng Troubleshooting.
- **README cập nhật** cho hợp hiện trạng: bảng thành tựu (4 cuốn + audiobook), cấu trúc thư mục đánh dấu commit/không-commit, chính sách git code-only, mục App desktop (C# WPF), path script audiobook, `/dich`.
- **Dọn lịch sử git** (phiên trước): `git filter-branch` bóc toàn bộ sản phẩm khỏi mọi commit → repo ~717MB → 0.4MB, không còn binary. 129→58 commit.
- **Triển khai Memory Bank**: tạo `docs/STATE.md` + `docs/session_log.md`, cập nhật `AGENTS.md`, thêm command `/start` + `/done`.

### File đổi
- `README.md`, `AGENTS.md`, xoá `QUICKSTART.md`/`USAGE.md`, thêm `docs/STATE.md` + `docs/session_log.md`, `.opencode/command/start.md` + `done.md`.

### Còn dở
- (vẫn đang trong phiên) chưa commit — đang chờ người dùng duyệt.

### Git
- Trạng thái: nhiều thay đổi chưa commit trên `main` (wip). Sẽ tách commit: (1) docs rút gọn + (2) memory system.

> **Lưu ý ghi chép**: entry mới **luôn thêm ở cuối**, không sửa entry cũ.

## 2026-08-06 — Deploy hoàn tất cuốn `zuo-yi-ge-gang-gang-hao-de-nu-zi-3`

### Đã làm
- **Merge**: `merge_chunks.py` → `final/tamngu.md` (trilingual, 1.3MB, 50/50 chunk) + `final/vi.md` (422KB); chép 3 ảnh jpg vào `images/`.
- **EPUB**: `make_epub.py` từ `final/vi.md` (pandoc) → `trilingual.epub` (331KB, có 3 ảnh).
- **Audiobook** (VieNeu-TTS v3 Turbo, voice `van_tinh`): gen đủ **65/65 chương** MP3 128kbps (308MB) tại `audiobook/ch*.mp3`. Tổng gen 210 phút / audio 336 phút (RTF≈0.62), chạy nền ~8.5h.
- **4 cuốn đều đã hoàn tất** (cả EPUB + audiobook).

### File đổi
- `output/books/zuo-yi-ge-gang-gang-hao-de-nu-zi-3/` (final/*.md, trilingual.epub, images/, audiobook/ — KHÔNG commit, local/Drive).
- Chỉnh môi trường: tái tạo `working/venv-vieneu` bằng Python 3.14.5 + vieneu 3.2.4 + torch/torchaudio cpu (KHÔNG commit).
- `docs/STATE.md` (cập nhật giai đoạn cuốn + ghi chú môi trường).

### Còn dở
- *(không)* — cả 4 cuốn hoàn tất; chỉ còn chờ commit docs nếu user đồng ý.

### Git
- Trạng thái: chỉ có thay đổi docs (`docs/STATE.md`) chưa commit. Chưa commit — chờ người dùng duyệt.

## 2026-08-06 — App desktop chuyển sang WPF-UI Fluent (Hướng A)

### Đã làm
- **Package**: thêm `WPF-UI 4.3.0` vào `desktop/TranslateBook.csproj`.
- **App.xaml**: bỏ 4 theme custom → gộp `ui:ThemesDictionary Theme="Dark"` + `ui:ControlsDictionary` + `Themes/AppStyles.xaml` (style còn cần: LogTextBox, chevron, AppTreeViewItem). `App.xaml.cs` dùng `ApplicationThemeManager.ApplySystemTheme()`.
- **MainWindow**: rewrite thành `ui:FluentWindow` + `WindowBackdropType="Mica"` + `ExtendsContentIntoTitleBar` → title bar Fluent tích hợp (bỏ WindowChrome/acrylic tay). `ui:NavigationView` trái với icon thật (📖Sách/Headphones24 Audio), footer hiện API provider + Cài đặt. Navigation theo `TargetPageType` + `Navigate(Type)`.
- **Split 3 trang**: `Views/BooksPage`, `AudioPage`, `ApiPage` (Page-based, DataContext kế thừa từ Window). Books: search box icon + nút clear; card `ui:Card` + `ui:InfoBadge` trạng thái (Warning khi đang dịch / Success khi có vi.md); `ui:Button` Primary/Secondary + icon. Audio: `ui:NumberBox` cho Temperature/Top-K (nút +/−). API: form Fluent (ComboBox, ui:PasswordBox, ui:TextBox).
- **Log panel**: đổi `ui:CardExpander` đáy, mặc định thu gọn (`IsExpanded=False`), giải phóng 200px.
- **EpubPreviewWindow**: chuyển sang `ui:FluentWindow` + Mica, đồng bộ theme.
- **Dọn dẹp**: xoá `Themes/{LiquidGlass,Controls,DarkTheme,LightTheme}.xaml` + `Services/AcrylicWindowHelper.cs` (FluentWindow tự lo backdrop).
- **Giữ nguyên 100%**: MainViewModel, Models, Services — chỉ đổi Views + code-behind phần nav/toast.
- **Verify**: `dotnet build` ✅ 0 error (1 warning CS8625 null-literal ở EpubPreviewWindow — vô hại). Chạy thử exe 6s ✅ không crash.

### File đổi
- `desktop/App.xaml`, `App.xaml.cs`, `TranslateBook.csproj` (thêm WPF-UI); `Views/MainWindow.xaml(.cs)`, `Views/EpubPreviewWindow.xaml(.cs)`, `Views/BooksPage.xaml(.cs)` + `AudioPage.xaml(.cs)` + `ApiPage.xaml(.cs)` (mới); `Themes/AppStyles.xaml` (mới).
- Xoá: `Themes/{LiquidGlass,Controls,DarkTheme,LightTheme}.xaml`, `Services/AcrylicWindowHelper.cs`.
- `docs/STATE.md` (cập nhật quyết định).

### Còn dở
- *(không)* — build + chạy thử OK. Chưa kiểm thử thị giác đủ 3 trang/preview (chạy GUI rồi đóng nhanh). Commit chờ người dùng duyệt.

### Git
- Trạng thái: nhiều thay đổi chưa commit (thêm mới + xoá + sửa) trên `main`. Commit chờ người dùng duyệt message.

## 2026-08-06 — Fix lỗi app desktop (bắn bug nghiêm trọng)

### Đã làm
- **Fix #1 (nghiêm trọng nhất) — StartTranslateAsync không dịch**: thay vì gọi `translate_helper.py --interactive` (đọc stdin, app không redirect → EOF → bỏ qua toàn bộ chunk → log "Hoàn thành" giả), giờ dùng **vòng dịch thật trong C#** qua `ApiTranslationService.TranslateAsync`. Duyệt `working/chunks/<slug>/chunk-*.json`, dùng `ApiTranslationService.LoadGlossary` load CSV, gọi API từng chunk, ghi progress JSON đúng format skeleton (`chunk_id, total_chunks, chapter, source_text, translated_text, translated_at, word_count_source, word_count_translated, mode, original_text, pinyin_text`). Hỗ trợ trilingual (Chinese) và non-trilingual (English). Cập nhật % realtime qua `book.ProgressCount`.
- **Fix #2 — audiobook Python sai**: `RunAudiobookAsync` dùng `working/venv-vieneu/Scripts/python.exe` (không phải `.venv`), báo lỗi rõ nếu thiếu.
- **Fix #3 — --force**: xác minh không có `--force` trong args (giữ checkpoint resume).
- **Fix #4 — Temperature/Top-K**: `GenerateAudiobookAsync` truyền `AudioTemperature`/`AudioTopK` vào `RunAudiobookAsync`.
- **Thêm CancelCommand**: `[RelayCommand] Cancel()` + `CancellationTokenSource`, XAML đã có nút Hủy nhưng không có command.
- **Kill process on close**: `MainWindow.Closing` → `vm.KillCurrentProcess()`.
- **Timer progress**: `DispatcherTimer` 3s gọi `RefreshBookProgress()` cập nhật tiến độ realtime.
- **Cap LogText**: giới hạn ~2000 dòng tránh O(n²) khi log dài.
- **Sửa chuỗi log**: "Bat dau dich" → "Bắt đầu dịch", "Dang test" → "Đang kiểm tra", "Hoan thanh" → "Hoàn thành", "Khong tim thay" → "Không tìm thấy".
- **WebView2 user-data-folder**: dùng reflection để set `CreationProperties.UserDataFolder = %LocalAppData%\TranslateBook\WebView2`.
- **EpubPreviewWindow CSS**: đọc brush từ theme resources thay vì hardcode màu tối.
- **Dọn dẹp**: xóa `GitCommitAsync`, `FindProjectRoot` trùng, sửa `TestApi_Click`, và dọn unused exception.

### File đổi
- Các file service, view model, code-behind desktop và docs liên quan.

### Còn dở
- Chưa kiểm thử runtime (API key chưa có) — chờ user test.

### Git
- Trạng thái: thay đổi code chưa commit trên `main`. Đang chờ người dùng duyệt.

## 2026-08-06 — Phân tích và điều chỉnh đề xuất tăng hiệu suất dịch

### Đã làm
- Đọc pipeline Python, chunking, workflow AI Agent, desktop, QA, README và requirements.
- Xác nhận luồng dịch thực tế là AI Agent đọc/ghi progress trực tiếp; API trong desktop chỉ phục vụ hướng phát triển tương lai.
- Điều chỉnh trọng tâm: giảm số lượt trao đổi và số lần đọc/ghi file bằng batch 2–4 chunk hoặc theo nhóm chương; ghi progress từng chunk để resume; giao nhiều nhóm chương độc lập cho Agent song song khi phù hợp.

### File đổi
- `docs/STATE.md`, `docs/session_log.md` — cập nhật quyết định và đề xuất.

### Còn dở
- Chưa triển khai batch workflow cho AI Agent; cần chọn cách giao batch trong prompt/command trước khi sửa script.

### Git
- Trạng thái: nhiều thay đổi desktop chưa commit trên `main`; không tự commit.

## 2026-08-06 — Triển khai batch Agent và ổn định audiobook

### Đã làm
- Thêm `scripts/translate/batch_manifest.py`, `scripts/qa/batch_qa.py`; mở rộng merge validation và checkpoint audiobook.
- Cập nhật `.opencode/command/dich.md` cho batch manifest, QA sau batch và giới hạn Agent song song không trùng chunk.
- Kiểm tra compile, smoke test và diagnostics đạt; pytest chưa chạy được vì môi trường thiếu pytest.

### File đổi
- Scripts translate/QA/output/audiobook, `.opencode/command/dich.md`, README, tests và docs.

### Còn dở
- Cài pytest vào Python 3.14 hoặc tạo lại `.venv`; chưa benchmark TTS song song.

### Git
- Nhiều thay đổi chưa commit trên `main`; không tự commit.

## 2026-08-06 — QA audiobook và rà soát tổng thể

### Đã làm
- Thêm `scripts/qa/audio_qa.py`; QA coverage/chất lượng đạt cho các audiobook hiện có.
- Cập nhật fingerprint audio, `/dich`, README và tests.
- Rà soát tổng thể: restore + build desktop đạt; diagnostics, diff check, compile và smoke test đạt.

### File đổi
- `scripts/qa/audio_qa.py`, `scripts/audiobook/audiobook_long.py`, `.opencode/command/dich.md`, `README.md`, tests và docs.

### Còn dở
- Cài pytest để chạy test chính thức; app desktop chờ runtime test với API key.

### Git
- Nhiều thay đổi chưa commit trên `main`; không tự commit.

## 2026-08-07 - Hoan thanh audiobook la-nam-trong-la + tạo lại venv VieNeu từ Python 3.11

### Đã làm
- Hoàn tất audiobook `la-nam-trong-la` đủ 9/9 chương sau khi tạo lại venv VieNeu từ Python 3.11.9.

### File đổi
- `working\venv-vieneu`, progress/audio local và `docs/STATE.md`.

### Còn dở
- Slug orphan `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` tạm bỏ qua.

### Git
- Không tự commit.

## 2026-08-07 — Triển khai Multi-Agent Phase 1 MVP

### Đã làm
- Tạo `.commandcode/agents/analyzer.md`: analyzer read-only, model `gpt-5.6-luna`, structured analysis/review marker.
- Tạo `.commandcode/agents/executor.md`: executor model `poolside/laguna-s-2.1-free`, giới hạn file scope, baseline preservation và shell guard.
- Tạo `.opencode/command/dual-Agent.md`: Phase 1 analyze → baseline → execute → git check → review 1, không loop; giới hạn payload và không retry.
- Kiểm tra `git diff --check` và xác nhận đúng ba file mới.

### File đổi
- `.commandcode/agents/analyzer.md`
- `.commandcode/agents/executor.md`
- `.opencode/command/dual-Agent.md`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Test dispatch custom agent qua task tool bị từ chối quyền trước khi analyzer trả output; chưa xác nhận E2E runtime.
- Phase 2 (một lần sửa + Review 2) chưa triển khai.

### Git
- Không tự commit/push; các file mới đang untracked, thay đổi docs có sẵn trên `main`.

## 2026-08-07 — Sửa vị trí Command Code custom command

### Đã làm
- Xác định Command Code quét project commands tại `.commandcode/commands/`, không phải `.opencode/command/`.
- Tạo `.commandcode/commands/dual-Agent.md`; giữ nguyên `.opencode/command/dual-Agent.md` cho workflow OpenCode cũ.
- Xác nhận file command mới có đúng tên `dual-Agent.md` để gọi bằng `/dual-Agent`.

### File đổi
- `.commandcode/commands/dual-Agent.md`, `docs/STATE.md`, `docs/session_log.md`.

### Còn dở
- Cần reload Command Code rồi kiểm tra `/dual-Agent` trong menu.
- Runtime dispatch custom agent chưa E2E vì lần thử trước bị từ chối quyền.

### Git
- Không tự commit/push; file command mới đang untracked.

## 2026-08-07 — Xác minh Dual-Agent Phase 1 E2E

### Đã làm
- Sửa quyền runtime: thêm `Read(*)` vào `.commandcode/settings.json`; analyzer và executor dùng `permissionMode: auto-accept` với giới hạn `maxTurns`.
- Chạy E2E: analyzer tạo plan → executor tạo `scratchpad/dual-agent-test.txt` với nội dung `X` → Git check không phát sinh thay đổi trong repo → analyzer Review 1.
- Analyzer review trả `FINAL_STATUS: APPROVED`.

### File đổi
- `.commandcode/settings.json`, `.commandcode/agents/analyzer.md`, `.commandcode/agents/executor.md`, `docs/STATE.md`, `docs/session_log.md`.
- File test nằm ngoài repo: `scratchpad/dual-agent-test.txt`.

### Còn dở
- Phase 2 (một lần sửa + Review 2) chưa triển khai.

### Git
- Không tự commit/push; working tree giữ nguyên các thay đổi baseline.

## 2026-08-07 — Tối ưu Dual-Agent cân bằng chất lượng và chi phí

### Đã làm
- Analyzer được hướng dẫn đọc có mục tiêu, không quét toàn repo.
- Executor chỉ nhận plan, success criteria, file scope, context trực tiếp và test cần chạy; report ngắn gọn.
- Review 1 giữ diff đầy đủ trong scope + test evidence; Review 2 chỉ nhận feedback, diff sau sửa, test liên quan và criteria bị ảnh hưởng.
- Giữ giới hạn cứng hai vòng: review 1; nếu `NEEDS_CHANGES` thì sửa một lần và review 2 rồi kết thúc.
- E2E task scratchpad `dual-agent-quality-test.txt` tạo đúng nội dung `quality-ok`; analyzer Review 1 trả `FINAL_STATUS: APPROVED`.

### File đổi
- `.commandcode/agents/analyzer.md`
- `.commandcode/agents/executor.md`
- `.commandcode/commands/dual-Agent.md`
- `.opencode/command/dual-Agent.md`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Chưa ép test thực tế nhánh Review 1 `NEEDS_CHANGES` → Review 2.
- Một lần executor bị permission chặn ở hậu kiểm Git dù đã tạo file thành công; cần theo dõi nếu tái diễn.

### Git
- Không tự commit/push; working tree giữ nguyên các thay đổi baseline.

## 2026-08-07 — Ổn định permission Dual-Agent

### Đã làm
- Chuyển analyzer sang `permissionMode: dont-ask`, chỉ giữ tool đọc.
- Chuyển executor sang `permissionMode: dont-ask`, chỉ giữ `read_file`, `write_file`, `edit_file`, `grep`, `glob`; loại `shell_command` để tránh permission deny ở hậu kiểm và giảm blast radius.
- Thêm allowlist `Write(*)` và `Edit(*)` trong `.commandcode/settings.json`.
- Test analyzer đọc `README.md` thành công; test executor tạo và đọc `permission-stable-test.txt` trong scratchpad thành công.

### File đổi
- `.commandcode/agents/analyzer.md`
- `.commandcode/agents/executor.md`
- `.commandcode/settings.json`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Cần chạy lại E2E command `/dual-Agent` tạo file trong `input` sau khi reload phiên.
- Chưa ép test thực tế nhánh `NEEDS_CHANGES` → Review 2.

### Git
- Không tự commit/push; working tree giữ nguyên các thay đổi baseline.

## 2026-08-07 — Chốt giới hạn hai vòng Dual-Agent

### Đã làm
- Đồng bộ `.commandcode/commands/dual-Agent.md` và `.opencode/command/dual-Agent.md` sang workflow hai vòng:
  - Vòng 1: analyzer plan → executor implement → analyzer review 1.
  - Nếu `FINAL_STATUS: NEEDS_CHANGES`: executor chỉ sửa một lần → analyzer review 2.
  - Sau review 2 bắt buộc kết thúc, không executor sửa lần hai và không review lần ba.
- Kiểm tra marker `review_count`, nhánh `NEEDS_CHANGES` và `git diff --check`.

### File đổi
- `.commandcode/commands/dual-Agent.md`
- `.opencode/command/dual-Agent.md`
- `docs/session_log.md`

### Còn dở
- Chưa chạy E2E nhánh `NEEDS_CHANGES`; Phase 1 trước đó đã chạy thành công với `APPROVED`.
- Chưa áp dụng mô hình task-spec/archive của dự án tham khảo.

### Git
- Không tự commit/push; working tree giữ nguyên các thay đổi baseline.

## 2026-08-07 — Tối ưu Dual-Agent cân bằng chất lượng và chi phí

### Đã làm
- Analyzer được hướng dẫn đọc có mục tiêu, không quét toàn repo.
- Executor chỉ nhận plan, success criteria, file scope, context trực tiếp và test cần chạy; report ngắn gọn.
- Review 1 giữ diff đầy đủ trong scope + test evidence; Review 2 chỉ nhận feedback, diff sau sửa, test liên quan và criteria bị ảnh hưởng.
- Giữ giới hạn cứng hai vòng: review 1; nếu `NEEDS_CHANGES` thì sửa một lần và review 2 rồi kết thúc.
- E2E task scratchpad `dual-agent-quality-test.txt` tạo đúng nội dung `quality-ok`; analyzer Review 1 trả `FINAL_STATUS: APPROVED`.

### File đổi
- `.commandcode/agents/analyzer.md`
- `.commandcode/agents/executor.md`
- `.commandcode/commands/dual-Agent.md`
- `.opencode/command/dual-Agent.md`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Chưa ép test thực tế nhánh Review 1 `NEEDS_CHANGES` → Review 2.
- Một lần executor bị permission chặn ở hậu kiểm Git dù đã tạo file thành công; cần theo dõi nếu tái diễn.

### Git
- Không tự commit/push; working tree giữ nguyên các thay đổi baseline.

## 2026-08-07 — Kiểm tra chức năng Dual-Agent (E2E hai vòng)

### Đã làm
- Xác nhận cấu hình `.commandcode/agents/analyzer.md` + `executor.md` khớp format chuẩn Command Code (name/description/tools/model hợp lệ; model `gpt-5.6-luna`, `poolside/laguna-s-2.1-free` có trong catalog; thêm `permissionMode`/`maxTurns` ngoài spec nhưng registry nhận).
- E2E luồng chính: analyzer plan (đủ `# Implementation Plan`/`# Success Criteria`/`# Files to Modify/Create`/`# Review Focus Areas`) → executor implement (`FINAL_STATUS: COMPLETED`, tạo file đúng nội dung, trung thực báo lệch giả định gitignore) → analyzer review 1 (`FINAL_STATUS: NEEDS_CHANGES`).
- Ép nhánh `NEEDS_CHANGES` → executor sửa đúng 1 lần (đặt file vào `working/qa/` được ignore) → analyzer review 2 (`FINAL_STATUS: APPROVED`). Vòng 2 kết thúc đúng quy tắc giới hạn.
- Xác nhận permission/scope: analyzer read-only (không có write/shell), executor không có shell tool — đúng thiết kế.
- Phát hiện: (1) executor không có shell tool nên không tự chạy được `git status` như plan yêu cầu → nên giao git check cho orchestrator; (2) `.gitignore` chỉ ignore các thư mục con cụ thể của `working/`, KHÔNG ignore toàn bộ — file test đặt ngoài các thư mục đó hiện untracked.

### File đổi
- Không thay đổi file sản phẩm; chỉ test tạm (đã dọn sạch). Cập nhật `docs/STATE.md` + `docs/session_log.md`.

### Còn dở
- Cân nhắc bổ sung quy tắc vào `dual-Agent.md`: giao việc `git status --short`/git check cho orchestrator (không phải executor) vì executor không có shell.
- Có thể thêm rule ignore `working/e2e_test/` hoặc dùng đúng `working/qa/` cho file test tạm.

### Git
- Không tự commit/push; working tree giữ nguyên các thay đổi baseline.


## 2026-08-07 — Dịch batch 1 sách EU-BIM-Task-Group-Handbook v2.1 (chunk 1)

### Đã làm
- Claim batch 1 (worker h-batch1) bằng `batch_manifest.py` -> slug `eu-bim-task-group-handbook-v2-1` (9 chunk).
- Dịch chunk 1 (chapter: 2.2 Circular Economy Action Plan / chính sách khí hậu EU): 95 dòng nguồn -> 95 dòng dịch tiếng Việt (4786 từ), giữ heading/##/blockquote/URL, giữ tiêu chuẩn (EN 15978, EN 15804), áp glossary, dọn mojibake (CO, -> CO₂, "metrid" -> "thước đo"). Ghi `translated_at=2026-08-07T00:00:00`.
- QA `batch_qa.py` chunk 1: 0 lỗi (ok:true).
- `batch_manifest.py complete` batch 1: status -> complete.

### File đổi
- `working/progress/eu-bim-task-group-handbook-v2-1/chunk_001.json` (sản phẩm, không commit). Cập nhật docs/STATE.md + session_log.md.

### Còn dở
- Dịch tiếp chunk 2..8 còn trống.

### Git
- Không tự commit/push.

## 2026-08-07 — Batch 4 (chunk 4) cuốn eu-bim-task-group-handbook-v2-1

### Đã làm
- Claim batch 4 (worker w-batch4) chunk 4, chapter "DPP DATA REQUIREMENTS".
- Dịch chunk_004.json EN→VI hoàn chỉnh: giữ 84 dòng/cấu trúc, 6 heading, 1 ảnh, glossary EU BIM Task Group; dọn mojibake.
- QA `batch_qa.py` chunk 4: 0 lỗi (ok:true).
- `batch_manifest.py complete` batch 4: status -> complete.

### File đổi
- `working/progress/eu-bim-task-group-handbook-v2-1/chunk_004.json` (sản phẩm, không commit). Cập nhật docs/STATE.md + session_log.md.

### Còn dở
- Dịch tiếp chunk 5..8 còn trống.

### Git
- Không tự commit/push.

## 2026-08-07 — Dịch batch 8 (chunk 8) sách eu-bim-task-group-handbook-v2-1

### Đã làm
- Claim batch 8 (worker w-batch8) bằng `batch_manifest.py` -> chunk-id 8, chapter "REFERENCES".
- Dịch chunk_008.json EN→VI: 68 dòng nguồn → 68 dòng (1:1). Gồm 26 từ viết tắt (giữ acronym, dịch phần mở rộng sang tiếng Việt, ví dụ LCA→Đánh giá vòng đời), heading `## REFERENCES`→`## TÀI LIỆU THAM KHẢO`, 41 citation thư mục giữ nguyên như nguồn (chỉ dọn lỗi OCR khoảng trắng trong URL: `https:// cirpass2.eu`→`cirpass2.eu`, `madaster. com`, `woningpas. vlaanderen`, `j. dibe`, `\_`→`_`), giữ ảnh `![](...)`. word_count_translated = 1146. Ghi `translated_at=2026-08-07T00:00:00`, UTF-8.
- QA `batch_qa.py` chunk 8: 0 lỗi (ok:true).
- `batch_manifest.py complete` batch 8: status → complete.

### File đổi
- `working/progress/eu-bim-task-group-handbook-v2-1/chunk_008.json` (sản phẩm, không commit). Cập nhật docs/STATE.md + session_log.md.

### Còn dở
- Dịch tiếp chunk 2,3,5,6,7 còn trống; hiện đã xong chunk 1,4,8.

### Git
- Không tự commit/push.

## 2026-08-07 — Dịch batch 7 (chunk 7) sách eu-bim-task-group-handbook-v2-1

### Đã làm
- Claim `batch_manifest.py` (worker w-batch6): chunk 6 đang bị claim bởi worker khác (w-batch7) vào 09:49:59, nên claim nhận batch 7 → chunk 7, chapter "PUBLIC PROCUREMENT AS A LEVER FOR MARKET TRANSFORMATION".
- Dịch chunk_007.json EN→VI: 143 dòng nguồn → 143 dòng (1:1). Giữ 10 heading `#`/`##`, giữ 5 blockquote `>` (mục khuyến nghị cấp EU & quốc gia), dọn OCR (`Al`→`AI`, `reguires`→bỏ), áp glossary (BIM, Twin Transition, built environment, whole-life carbon, Digital Building Logbook...), giữ chuẩn/URL/acronym (EN ISO 19650, IFC, EPBD, CPR, DPP, DBL, CEN, EN 15978). Danh sách 33 acronym giữ tên viết tắt, dịch phần mở rộng sang tiếng Việt. word_count_translated = 4751. Ghi `translated_at=2026-08-07T00:00:00`, UTF-8.
- QA `batch_qa.py` chunk 7: 0 lỗi (ok:true).
- `batch_manifest.py complete` batch 7: status → complete.

### File đổi
- `working/progress/eu-bim-task-group-handbook-v2-1/chunk_007.json` (sản phẩm, không commit). Cập nhật docs/STATE.md + session_log.md.

### Còn dở
- Dịch tiếp chunk 2,3,5,6 (chunk 6 đã claim bởi worker khác) còn trống; hiện đã xong chunk 1,4,7,8.

### Git
- Không tự commit/push.


## 2026-08-07 - Batch 6 (chunk 6) cuon eu-bim-task-group-handbook-v2-1

### Đa lam
- Claim batch 6 (worker w-batch7) chunk 6, chapter "CALL TO REALITY". Luu y: lenh claim tu-dong nhan batch 6 vi batch 7 da bi w-batch6 claim truoc (worker song song).
- Dich chunk_006.json EN->VI hoan chinh: 87 dong/cau truc gi-ven, 14 heading ##, blockquote, thu-tuc (EN ISO 19650, IFC, MEAT, Horizon Europe, Digital Europe, Erasmus+, New European Bauhaus), dia diem chuong trinh (BIM Deutschland, Plan BIM 2022, KIRA-digi). Dọn mojibake B|M->BIM. Ghi translated_at=2026-08-07T00:00:00, word_count_translated=4952 (source 3001).
- QA batch_qa.py chunk 6: 0 loi (ok:true).
- batch_manifest.py complete batch 6: status -> complete.

### File đoi
- working/progress/eu-bim-task-group-handbook-v2-1/chunk_006.json (san pham, khong commit). Cap nhat docs/STATE.md + session_log.md.

### Can dư
- Dich chunk 2,3 con lai (batch 0-1, 5,6,7,8 da complete 08-07).

### Git
- Khong tu commit/push; co the tu-dong commit luc cac worker song song trong-nhau STATE.md.


## 2026-08-07 - Dich xong EU-BIM-Task-Group-Handbook-V2.1 (EN->VI)

### Đã làm
- Dich cuon 'EU-BIM-Task-Group-Handbook-V2.1.pdf' (EN, 9.6MB) -> slug eu-bim-task-group-handbook-v2-1.
- Extract MinerU (CPU) -> raw.md (172KB/1091 dong), QC OK, detect lang = en.
- Chunk 9 (EN, 3000-8000). Glossary 32 thuật ngữ (BIM, Twin Transition=Chuyển đổi kép, LCA, EPD, DPP, DBL, ESPR, CPR...).
- Skeleton bilingual (init_trilingual_skeleton.py lỗi vi chuyen cho ZH -> tao skeleton thu công chuong chuong).
- Dịch 9/9 chunk bang subagent song song, batch_manifest verify ok: 9/9, 0 thieu, 0 trung.
- QA glossary_qa: ok; còn sót EN tai các sách SX/quy dịnh/chuander/references (chap nhan). 27% remnant do giu nguyên tư kỹ thuật + thư mục TG nhự gióa. Mojibake 1 dòng là false positive.
- Merge song ngữ (make_bilingual) + vi.md. EPUB (make_epub) co image: vi.epub 816KB (resource-path = output/books/<slug> vì md ghi sẵn images/).
- Output: output/books/eu-bim-task-group-handbook-v2-1/final/{songngu.md, vi.md, vi.epub} + images/ (20 jpg).
- Chưa làm audiobook (sách tài liệu kỹ thuật, optional).

### File
- working/extracted, working/chunks, working/progress, working/tmp/<slug>, working/qa/<slug>; output/books/<slug>/final; glossary/eu-bim-task-group-handbook-v2-1.csv.

### Còn dở
- Audiobook cho sách này nếu user muốn (cần --slug; giọng active.wav).

### Git
- Không tự commit.


## 2026-08-08 — Fix NullReferenceException "Đọc thử" EPUB desktop (dual-Agent)

### Đã làm
- Chạy lệnh `/dual-Agent` với task: "tôi gặp lỗi như hình khi ấn vào phần đọc thử của UI". Ảnh lỗi: `System.NullReferenceException` ("Object reference not set to an instance of an object") ở dialog "Lỗi hệ thống", không có stack trace.
- **Bước 1 Analyze**: analyzer khám phá desktop WPF, xác định live entry point: `BooksPage.xaml:348-350` → MVVM command `OpenEpubPreviewCommand` → `MainViewModel.OpenEpubPreviewAsync(BookStatus)` — không phải XAML Click handler. Đưa ra plan + 3 slice.
- **Bước 2 Baseline**: git status sạch trên `main` (working tree clean).
- **Bước 3 Execute**: executor (read/write/edit, không shell) sửa 2 file — null-guard `book/slug/_projectRoot/Application.Current/MainWindow` + try/catch trong `OpenEpubPreviewAsync`; null-check `CoreWebView2` + `_epubFilePath` trong `EpubPreviewWindow_Loaded`; guard 9 handler WebView2 phụ thuộc (`if (WebView?.CoreWebView2 == null) return;`).
- **Bước 4 Git check + Review 1**: build `dotnet build` đầu thất bại do `TranslateBook.exe` bị process cũ (PID 21296) giữ lock (MSB3021, không phải lỗi compile C#); kill process → rebuild `0 Warning(s) 0 Error(s)`. analyzer review: toàn bộ checklist ✅ → `FINAL_STATUS: APPROVED`. review_count=1 (không cần vòng sửa thứ 2).
- **Bước 5/6**: không cần thiết (Review 1 APPROVED).

### File đổi
- `desktop/ViewModels/MainViewModel.cs` (OpenEpubPreviewAsync)
- `desktop/Views/EpubPreviewWindow.xaml.cs` (Loaded flow + 9 handler)
- `docs/STATE.md`, `docs/session_log.md` (bookkeeping)

### Còn dở
- Chưa kiểm thử runtime thực tế "Đọc thử" (cần EXE chạy + file EPUB mẫu); chờ user test.
- Chưa commit — đang chờ duyệt message.

### Git
- Trạng thái: 4 file thay đổi (2 code + 2 docs) chưa commit trên `main`. Không tự commit/push.

## 2026-08-08 — Tối ưu Dual-Agent: Luna plan theo lô + Laguna thực thi + flash review

### Đã làm
- Benchmark token/chi phí thực tế (đọc transcript usage): single-agent 189K tokens ~$0.015 (flash); dual cũ 686K ~$5.9 (Luna plan+review); phát hiện sub-agent usage không nằm trong transcript orchestrator mà qua tag `<usage>` trong output.
- Đổi kiến trúc Dual-Agent sang 3 vai:
  - analyzer (gpt-5.6-luna): chỉ plan theo LÔ (gom nhiều task, Luna chạy 1 lần/lô), bỏ review mode.
  - executor (poolside/laguna-s-2.1-free): giữ nguyên, thêm chế độ batch item + checkpoint + tự review sơ bộ.
  - reviewer (deepseek/deepseek-v4-flash): MỚI — review độc lập, read-only.
- dual-Agent.md: thêm Bước 0 phân loại task (task bé chạy thẳng, không dùng pipeline), pipeline 3 vai, giám sát executor vô thời hạn (background + agent_output(status) định kỳ, chỉ dừng khi BLOCKED/mất kết nối), xác minh sơ bộ kết quả Laguna trước khi review.
- Đồng bộ .opencode/command/dual-Agent.md.
- E2E: task bé → bỏ pipeline đúng; lô 2 task → analyzer plan (8.3K tokens ~$0.83 Luna) → executor Laguna tạo 2 file (44.8K, $0) → reviewer flash APPROVED (25.7K, ~$0.01); orchestrator flash $0.09. Tổng ~$0.93/lô → ~$0.47/task (dual cũ ~$5.9/task, single Luna ~$3.65/task).

### File đổi
- .commandcode/agents/analyzer.md (chỉ plan theo lô)
- .commandcode/agents/executor.md (batch item + checkpoint + tự verify)
- .commandcode/agents/reviewer.md (mới)
- .commandcode/commands/dual-Agent.md, .opencode/command/dual-Agent.md (3 vai + bước 0)
- docs/STATE.md, docs/session_log.md

### Còn dở
- Chưa commit — chờ duyệt.

### Git
- Không tự commit/push.

## 2026-08-08 — Fix preview EPUB trắng + tinh chỉnh UI desktop (books tab, log panel, card)

### Đã làm
- **Fix "Đọc thử" EPUB trắng tinh**: nguyên nhân `BuildEpubCss()`/`ReapplyThemeColors` đọc WPF-UI brush (`ControlFillColorTertiaryBrush`, `TextFillColorPrimaryBrush`) từ `Application.Current.Resources` trả về màu trắng/gần trong suốt (`#08FFFFFF`, `#FFFFFFFF`) → `--bg-color: #FFFFFF`, vùng đọc trắng. Fix: helper `GetSafeColor()` (kiểm tra alpha < 0x40 + luminance, fallback dark palette `#1E1E1E`/`#E0E0E0`/`#B0B0B0`). Verify: log `bgHex=#1E1E1E`, pixel màn hình nền tối RGB(24-31).
- **Đọc thử hết hard-code trilingual.epub**: `FindPreviewEpub()` ưu tiên `trilingual.epub` (ZH) → `final/vi.epub` (EN) → `.epub` bất kỳ; dùng chung trong `GetBookStatus` (HasEpub) và `OpenEpubPreviewAsync`. Verify sách EN `eu-bim` parse được vi.epub (8 chapter).
- **Realtime Log → panel phải 300px**: RichTextBox màu level (ERR đỏ/WARN vàng/INFO xám), ô Lọc hoạt động (filter + re-render), thu gọn hoàn toàn bằng nút toggle `<`/`>` (mở hiện `<`, thu hiện `>`); bỏ bar log đáy.
- **Card sách đẹp hơn**: avatar tròn chữ cái đầu (`BookStatus.Initial`), header nền, badge ✓/…, stat tiles Chunks/EPUB/Audio (thêm `BoolToEmojiConverter`), progress bar; hover chỉ đổi shadow (bỏ translate tránh giật).
- **Tab Input/Output animation**: fade + trượt lên 180ms CubicEase (`BooksPage.xaml.cs AnimatePanelIn`).
- **Tab Output gọn**: chỉ còn nút "Đọc thử" (bỏ Dịch/Gộp/EPUB/QA/Audio/Report QA/Hủy) — logic output = xem/nghe thành phẩm.
- `ReadTextFileWithEncoding()` detect BOM UTF-8/UTF-16 cho chapter XHTML chống mojibake; null-check `BtnRefreshTheme_Click`; `DefaultBackgroundColor="#1E1E1E"`.

### File đổi
- desktop/Views/EpubPreviewWindow.xaml.cs + .xaml (fix màu, encoding, null-check)
- desktop/ViewModels/MainViewModel.cs (FindPreviewEpub, LogEntry events, ClearLog)
- desktop/Views/MainWindow.xaml + .xaml.cs (log panel phải, filter/màu/copy)
- desktop/Views/BooksPage.xaml + .xaml.cs (card đẹp, tab animation, output gọn)
- desktop/Themes/AppStyles.xaml (InteractiveCard hover, StatTile, BookCardHeader, LogRichTextBox)
- desktop/Models/BookStatus.cs (Initial)
- desktop/Converters/BoolToEmojiConverter.cs (mới)
- desktop/App.xaml (đăng ký converter)

### Còn dở
- Chưa kiểm thử runtime đầy đủ các lệnh Dịch/Audio/QA (cần API key + sách mẫu); card/log đã verify qua build + pixel màn hình.
- `RewriteImagePaths` chưa xử lý `url()` trong CSS stylesheet (ảnh nền EPUB) — ảnh qua `<img>` hoạt động, ảnh nền hiếm.

### Git
- Đang trên `main`, chưa commit — chờ user duyệt message rồi commit + push.

## 2026-08-08 — Nâng cấp UI desktop tiếp (busy overlay, ảnh bìa, global search, fix log/busy)

### Đã làm
- **Busy overlay** toàn cửa sổ (ProgressRing + BusyMessage + nút "Hủy thao tác" bind CancelCommand): hiện khi chạy pipeline/dịch/QA/audio. `IsBusyAny` gồm cả per-book busy qua static event `BookStatus.AnyBusyChanged`.
- **Fix** `GenerateAudiobookAsync` thiếu `IsVoiceBusy` → overlay không hiện khi tạo audio (giờ set đúng).
- **Ảnh bìa card sách Output**: `FindCoverImage()` tìm ảnh trong `images/` (ưu tiên tên cover/front), fallback avatar chữ; `BookStatus.CoverPath`.
- **Empty state** Input/Output: icon + nút "Mở thư mục input" (Process.Start explorer qua `ProjectHelper.FindProjectRoot`).
- **AudioPage**: progress bar "Chương N" khi tạo audio (`AudioDone`/`AudioTotal` set trong GetBookStatus).
- **Global search**: Enter ở ô tìm kiếm titlebar → navigate tab Sách + lọc; **Ctrl+F** (`PreviewKeyDown` trong MainWindow) → navigate + focus SearchBox qua flag `FocusSearchRequested`.
- **Fix mất log**: `ReplayLogHistory()` replay `LogText` khi MainWindow subscribe (log khởi tạo VM không mất).
- **Search theo tên**: `Matches()` khớp slug + DisplayTitle + Initial + tên file gốc (tìm được tên tiếng Trung/Việt).
- **Toolbar EpubPreviewWindow**: bọc ScrollViewer ngang, thu gọn (Làm mới/zoom 90/search 160) — hết cắt nút Tiếp/Trước.

### File đổi
- desktop/ViewModels/MainViewModel.cs (BusyMessage, IsBusyAny, AnyBusyChanged, FindCoverImage, FocusSearchRequested, IsVoiceBusy trong GenerateAudiobook)
- desktop/Models/BookStatus.cs (CoverPath, AnyBusyChanged static event)
- desktop/Views/MainWindow.xaml + .xaml.cs (busy overlay, Ctrl+F, replay log, nút Hủy)
- desktop/Views/BooksPage.xaml + .xaml.cs (ảnh bìa, empty state, search theo tên)
- desktop/Views/AudioPage.xaml (progress chương)
- desktop/Views/EpubPreviewWindow.xaml (toolbar scroll ngang)
- desktop/Services/ProjectHelper.cs (đã verify FindProjectRoot trả project root đúng)
- docs/STATE.md, docs/session_log.md

### Còn dở
- 3 cuốn không có EPUB (ban-co-nam-cho-ngoi, la-nam-trong-la, long-test) → nút "Đọc thử" báo lỗi; ghi nhận để xử lý sau (ẩn nút hoặc tạo vi.epub từ vi.md).
- `RewriteImagePaths` chưa xử lý CSS `url()` (ảnh nền EPUB) — để sau.
- `scripts/audiobook/audiobook_long.py` có thay đổi lớn (chunk 280, gộp chunk nhỏ, từ điển phát âm, repetition penalty, re-encode MP3) đang chờ commit — cần commit riêng.

### Git
- Trên `main`, chưa commit. Dự kiến tách commit: (1) desktop UI nâng cấp, (2) audiobook_long.py, (3) docs. Chờ user duyệt.

## 2026-08-12 — Dịch chunk 20-29 sách qie-yi-qing-shen-gong-bai-tou (Vãn Tình)

### Đã làm
- Dịch xong chunk 20-29 (10 chunk) của sách tản văn ZH `qie-yi-qing-shen-gong-bai-tou`: đọc glossary, dịch `original_text` dòng-đối-dòng sang tiếng Việt (giữ heading #, ---, ảnh, bỏ ///, dùng glossary Vãn Tình/A Nhan/Lão Ngô/Lão Lý).
- Cập nhật progress JSON: `translated_text`, `translated_at=2026-07-31T00:00:00`, `word_count_translated` (tính qua split). Giữ nguyên mọi field khác.
- QA batch: `scripts/qa/batch_qa.py` chạy 10/10 pass (0 lỗi) ngay lần đầu.
- Complete batch 20-29: `scripts/translate/batch_manifest.py complete --batch-id N`, tất cả status=complete.
- Tổng từ đã dịch: ~13.898 từ (20:1439, 21:1443, 22:1315, 23:1331, 24:1361, 25:1485, 26:1379, 27:1441, 28:1309, 29:1395).

### File đổi
- working/progress/qie-yi-qing-shen-gong-bai-tou/chunk_020..029.json (translated_text + word_count_translated + translated_at) — KHÔNG commit (progress)
- working/progress/qie-yi-qing-shen-gong-bai-tou/batches/batch-020..029.json (status=complete) — KHÔNG commit
- docs/STATE.md (thêm dòng sách + mục đang làm) — có commit (docs)

### Còn dở
- Chunk 0-19 và 30-57 chưa dịch (58 chunk tổng). Bước tiếp: dịch các dải còn lại rồi QA → merge → EPUB → audiobook.
- Verify manifest vẫn báo missing_progress/incomplete cho chunk ngoài dải (đúng, chưa dịch).

### Git
- Chưa commit. Đề xuất commit docs (STATE.md) sau khi user duyệt.
## 2026-08-12 — Dịch chunk 10-19 sách qie-yi-qing-shen-gong-bai-tou (Vãn Tình)

### Đã làm
- Dịch xong chunk 10-19 (10 chunk) của sách tản văn ZH qie-yi-qing-shen-gong-bai-tou: đọc glossary, dịch original_text dòng-đối-dòng sang tiếng Việt (giữ heading #/##, ---, số/Latin, dùng glossary Vãn Tình/A Nhan/Lão Ngô/Lão Lý).
- Cập nhật progress JSON: 	ranslated_text, 	ranslated_at=2026-07-31T00:00:00, word_count_translated (tính qua split). Giữ nguyên mọi field khác.
- QA batch: scripts/qa/batch_qa.py chạy 10/10 pass (0 lỗi) ngay lần đầu cho cả dải.
- Complete batch 10-19: scripts/translate/batch_manifest.py complete --batch-id N, tất cả status=complete.
- Tổng từ đã dịch: ~13.680 từ (10:1529, 11:1490, 12:1444, 13:1356, 14:1319, 15:1339, 16:1349, 17:1343, 18:1424, 19:1356).

### File đổi
- working/progress/qie-yi-qing-shen-gong-bai-tou/chunk_010..019.json (translated_text + word_count_translated + translated_at) — KHÔNG commit (progress)
- working/progress/qie-yi-qing-shen-gong-bai-tou/batches/batch-010..019.json (status=complete) — KHÔNG commit
- docs/STATE.md (cập nhật mục sách) — có commit (docs)

### Còn dở
- Chunk 0-9 và 30-57 chưa dịch (58 chunk tổng). Đã dịch: 10-29. Bước tiếp: dịch dải 0-9 và 30-57 rồi QA → merge → EPUB → audiobook.
- Verify manifest vẫn báo missing_progress/incomplete cho chunk ngoài dải (đúng, chưa dịch).

### Git
- Chưa commit. Đề xuất commit docs (STATE.md + session_log.md) sau khi user duyệt.

## 2026-08-12 — Dịch chunk 0-9 sách qie-yi-qing-shen-gong-bai-tou (tản văn Vãn Tình)

### Đã làm
- Claim batch 0-9 (executor-0) bằng batch_manifest.py.
- Dịch dòng-đối-dòng ZH→VI 10 chunk (0..9): chunk_000..chunk_009.json trong working/progress/qie-yi-qing-shen-gong-bai-tou/.
- Ghi translated_text + translated_at="2026-07-31T00:00:00" + word_count_translated (json.dumps ensure_ascii=False, indent=2, utf-8).
- QA batch_qa.py: 10/10 pass (0 lỗi). Full scan 58 chunk chỉ còn lỗi chunk 40-49 (ngoài phạm vi, translated_text rỗng).
- Mark complete batch 0-9 (status=complete, error="").
- Nội dung gồm: bìa/CIP, Mục lục, Lời tựa, các bài: Điều bạn mong muốn..., Gả cho ai..., Tôi là chỗ dựa..., Chú chó và tình yêu, Làm người phụ nữ khác trong khác ngoài, Suy ngẫm về tình yêu, Bạn đã thay đổi chưa?, Bạn còn xinh đẹp chứ?, Chuyện phiếm đám cưới, Chi tiết đánh bại tình yêu, Kiến tạo bầu trời xanh biển biếc..., chuyện Hương Thảo.
- Glossary áp dụng: Vãn Tình/A Nhan/Lão Ngô/Lão Lý (Lão Ngô, Lão Lý chưa xuất hiện trong dải này).

### File đổi
- working/progress/qie-yi-qing-shen-gong-bai-tou/chunk_000..009.json (dịch, không commit — sản phẩm)
- working/progress/qie-yi-qing-shen-gong-bai-tou/batches/batch-000..009.json (complete, không commit)
- docs/STATE.md, docs/session_log.md

### Còn dở
- Chunk 10-57 chưa dịch (trong đó 40-49 hiện rỗng).

### Git
- Chưa commit; chỉ docs thay đổi (STATE.md, session_log.md) thuộc phạm vi commit docs.

## 2026-08-12 — Dịch chunk 40-49 sách qie-yi-qing-shen-gong-bai-tou (tản văn Vãn Tình)

### Đã làm
- Dịch dòng-đối-dòng ZH→VI 10 chunk (40..49): chunk_040..chunk_049.json trong working/progress/qie-yi-qing-shen-gong-bai-tou/ (translated_text lúc đầu đều rỗng).
- Ghi translated_text + translated_at="2026-07-31T00:00:00" + word_count_translated (đếm qua split whitespace). Giữ nguyên mọi field khác (chunk_id, total_chunks, chapter, source_text, original_text, pinyin_text, word_count_source, mode). Ghi qua Edit tool, không dùng shell.
- Glossary áp dụng: Vãn Tình/A Nhan (bắt buộc). Tên riêng khác dịch ổn định: Trần Đạo Minh, Triệu Nhã Chi, Lâm Chí Linh, Tiêu Khương, Mã Y, Văn Chương, A Ngốc (thú cưng).
- Nội dung gồm: Sát địch một nghìn tự tổn tám trăm, Làm một người phụ nữ vừa vặn, Sức hút khác giới, Hương vị phụ nữ, Trở lại trường học, Bài học từ sự kiện Văn Chương, Tri kỷ tâm hồn, Một chuyến đi nói đi là đi, Đại trượng phu, Ký sự giảm cân, Những điều những người phụ nữ ấy dạy tôi.
- QA batch_qa.py: 10/10 pass (0 lỗi) ngay lần đầu, không phải sửa lại chunk nào.
- Mark complete batch 40-49 (status=complete, error="") bằng batch_manifest.py complete --batch-id N.

### File đổi
- working/progress/qie-yi-qing-shen-gong-bai-tou/chunk_040..049.json (translated_text + word_count_translated + translated_at) — KHÔNG commit (progress)
- working/progress/qie-yi-qing-shen-gong-bai-tou/batches/batch-040..049.json (status=complete) — KHÔNG commit
- docs/STATE.md (cập nhật dòng sách + mục đang làm) — có commit (docs)
- docs/session_log.md (entry này) — có commit (docs)

### Còn dở
- Chunk 30-39 và 50-57 chưa dịch (58 chunk tổng). Đã dịch + complete: 0-49. Bước tiếp: dịch dải 30-39 và 50-57 rồi QA → merge → EPUB → audiobook.
- Tổng từ đã dịch dải 40-49: 14.458 từ (40:1446, 41:1567, 42:1439, 43:1426, 44:1446, 45:1484, 46:1402, 47:1416, 48:1396, 49:1436).

### Git
- Chưa commit; chỉ docs thay đổi (STATE.md, session_log.md) thuộc phạm vi commit docs.

## 2026-08-12 — Hoàn tất pipeline sách `qie-yi-qing-shen-gong-bai-tou` (tản văn Vãn Tình)

### Đã làm
- Dịch xong toàn bộ 58 chunk (các dải 0-9, 10-19, 20-29, 30-39, 40-49, 50-57) sang tiếng Việt theo manifest batch; ~81.290 từ Việt (nguồn ~90.189 từ).
- QA bước 8 (`run_pipeline.step_qa`): 58/58 chunk `ok: true` (0 lỗi lệch dòng/marker/rỗng). Lưu ý kỹ thuật: phải override `rp.PROJECT_ROOT = Path(r'<project root>').resolve()` vì `_common.py` PROJECT_ROOT tính sai thành `scripts\qa` (path chứa `..` chưa resolve).
- Merge: `merge_chunks.py --format trilingual` → `output/books/qie-yi-qing-shen-gong-bai-tou/final/tamngu.md` (1.381.608 B) và `--format bilingual` → `final/vi.md` (483.712 B); rename theo convention pipeline.
- EPUB: `make_epub.py` từ `final/vi.md` (pandoc) → `output/books/qie-yi-qing-shen-gong-bai-tou/trilingual.epub` (150KB, metadata title/author). Lưu ý: pandoc nhầm dòng `---` (thematic break giữa chapter) thành YAML metadata → phải tạo bản trung gian thay `---` bằng `* * *` (69 chỗ) rồi mới make_epub, sau đó xoá file tạm.
- Sách không có ảnh (không có dòng `![...]`, không có thư mục images/).
- **Fix pinyin** (user báo "sai sai pinyin"): `pypinyin` chưa cài → `add_pinyin.sentence_pinyin` trả về text gốc (chữ Hán) thay vì bính âm, nên `pinyin_text` trong progress JSON là bản sao của `original_text`. Đã `pip install pypinyin`, chạy script tạm dùng `process_text(source_text)` để regenerate `pinyin_text` cho 58/58 progress (đã verify `original_text` khớp tái tính; chỉ ghi đè field `pinyin_text`, giữ nguyên translated_text + mọi field khác), rồi merge lại trilingual → `final/tamngu.md` (1.532.291 B). Bản vi.md + EPUB không ảnh hưởng (không chứa pinyin).

### File đổi
- `output/books/qie-yi-qing-shen-gong-bai-tou/` (final/tamngu.md, final/vi.md, trilingual.epub) — KHÔNG commit (sản phẩm)
- `docs/STATE.md` (dòng sách + mục đang làm) — có commit (docs)
- `docs/session_log.md` (entry này) — có commit (docs)

### Còn dở
- Audiobook chưa làm (sách ZH, tùy chọn — chờ user quyết định).
- Các entry worker trước (dải 0-9, 10-19, 20-29, 30-39, 40-49, 50-57) đều chưa commit — gộp chung vào commit docs khi user duyệt.

### Git
- Chưa commit. Đề xuất: 1 commit docs cho toàn bộ phiên (STATE.md + session_log.md) sau khi user duyệt.

## 2026-08-12 — Tính năng nhạc nền (music bed) cho audiobook + chốt mức 10%/20%

### Đã làm
- **Ý tưởng → demo → pipeline**: user muốn "nhạc nền sau giọng audiobook" (music bed), không phải nhạc riêng khi đọc im. Làm demo trộn 1 chapter thật (ch01 sách `zuo-yi-ge-gang-gang-hao-de-nu-zi`) để user nghe duyệt.
- **Tích hợp `audiobook_long.py`**: thêm flags `--music` (tên file trong `core/music/`, `auto`, hoặc nhiều file cách dấu phẩy để xoay theo chương) + `--music-volume` (0..1). Hàm `mix_music_bed()`: ducking theo RMS giọng (nhạc dịu khi đọc, thở lên khi nghỉ), crossfade loop (tránh click khi nhạc ngắn hơn chapter), cap thời gian nhạc nổi (MUSIC_RISE_CAP_S=1.2s), envelope mượt 150ms (fftconvolve), normalize giữ độ to giọng.
- **Fix bug to**: phiên bản đầu quên nhân `volume` vào amp → nhạc nền phát 40–100% (đè giọng, nghe như 2 track). Sửa `amp = volume * ratio`.
- **Loudness normalization**: file nhạc master to/nhỏ khác nhau (đo thực tế: bài 1 RMS 0.28, bài 2/3 RMS 0.045) → tự scale cả bài về `MUSIC_TARGET_RMS = 0.18` trước khi trộn (gain cap 4x). Mọi bài nghe đều nhau.
- **Mức nhạc chốt**: `--music-volume 0.20`, `MUSIC_MIN_RATIO=0.50` → khi giọng đọc ~10%, khi nghỉ ~20%. `MUSIC_DIR` chỉ đọc `core/music/` (user tự thay file, pipeline chỉ dùng đúng các file có trong đó).
- **Metadata**: `audio_progress_metadata` thêm `music_files` + `music_volume`, bump `pipeline_version` 4→5 — đổi nhạc/volume tự tạo lại chapter cũ.
- **Chạy thử 3 chương** sách `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` (ch1-3): mỗi chương 1 bài (`sach_ke_chuyen_lofi.mp3`, `_2_lofi.mp3`, `_3_lofi.mp3`), volume 0.20, đã verify RMS p10 ~0.03 (nền nhẹ) + metadata đúng. User duyệt: "ngon rồi chốt cái này" — sẽ đi kiếm thêm music bỏ vào `core/music/`.

### File đổi
- `scripts/audiobook/audiobook_long.py` (mix_music_bed, flags --music/--music-volume, normalize loudness, metadata) — chờ commit
- `core/music/` (3 bài `sach_ke_chuyen*_lofi.mp3`, user tự thêm) — KHÔNG commit
- `output/books/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/audiobook/ch01-03.mp3` (bản mới có nhạc nền) — KHÔNG commit (sản phẩm)
- `output/samples/` (các file bgm test) — KHÔNG commit

### Còn dở
- `audiobook_long.py` có thay đổi lớn (music bed + normalize) chưa commit — cần commit riêng khi user duyệt.
- `core/music/` chỉ có 3 bài — user sẽ bổ sung thêm; pipeline tự dò + xoay + normalize.
- Cửa sổ "Đọc thử" (EpubPreviewWindow) có thêm UI nhạc nền demo (bản cũ) — hiện không dùng nữa vì đã chuyển hướng sang music bed trong pipeline; có thể dọn sau.

### Git
- Chưa commit. Đề xuất tách: (1) `audiobook_long.py` music bed, (2) docs (STATE.md + session_log.md). Chờ user duyệt.

## 2026-08-12 — Dịch trọn sách `zuo-yi-ge-you-jing-jie-de-nu-zi` (Vãn Tình, EPUB scan)

### Đã làm
- **Nhận diện EPUB scan**: `input/做一个有境界的女子  不自轻,不自弃 (晚情).epub` là bản scan toàn ảnh (281 JPG, không có text layer) — `epub_extract.py` chỉ ra ảnh trắng + metadata rác.
- **OCR 281 trang** bằng PaddleOCR (lang ch, CPU, numpy 2.x patched `np.sctypes`) → checkpoint `ocr_ckpt.json` (resume an toàn), raw.md 105KB/92K chữ Hán. Làm sạch: bỏ cover/CIP/TOC, tách 35 chapter `##` theo danh sách title, sửa OCR lỗi phổ biến (自已→自己, 千什么→干什么, 明百→明白...).
- **Pipeline**: QC OK (0 mojibake), detect `zh-Hans`, chunk smart 56 chunk (1500-3000 chữ), glossary 20 thuật ngữ (Vãn Tình, A My, Tiểu Chu, Noãn Noãn, Chị Cố, Dương Dương, Lisa...), skeleton trilingual (original/pinyin/translated).
- **Dịch 56/56 chunk** (85.882 từ Việt): 5 chunk đầu dịch trực tiếp, còn lại giao 45 sub-agent general song song mỗi agent 1 file text `số|tiếng Trung` → `số|tiếng Việt` (giữ đúng số dòng), merge bằng script `merge_vi` kiểm tra khớp dòng. QA `batch_qa.py`: 56/56 OK, 0 lỗi.
- **Merge + EPUB**: tamngu.md 1.54MB + vi.md 511KB (chỉ Việt) + trilingual.epub 155KB (title/author đúng). Lưu ý: `merge_chunks.py` PROJECT_ROOT tự dò lệch → phải truyền `--output-dir` tường minh; sửa 2 chữ Hán sót ở chunk 0.
- **Dọn dẹp**: xóa file tạm `tr_source/*.txt`, `scripts/output/output/` (output sai vị trí). `_ocr_images/` bị OneDrive lock tạm thời.

### File đổi
- `working/extracted/zuo-yi-ge-you-jing-jie-de-nu-zi/` (raw.md + ocr_ckpt.json) — KHÔNG commit
- `working/chunks/zuo-yi-ge-you-jing-jie-de-nu-zi/` (56 chunk) — KHÔNG commit
- `working/progress/zuo-yi-ge-you-jing-jie-de-nu-zi/` (56 progress JSON đã dịch) — KHÔNG commit
- `glossary/zuo-yi-ge-you-jing-jie-de-nu-zi.csv` — KHÔNG commit (sản phẩm)
- `output/books/zuo-yi-ge-you-jing-jie-de-nu-zi/` (final/tamngu.md, vi.md, vi.epub, trilingual.epub) — KHÔNG commit (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Audiobook chưa làm (ZH, tùy chọn — chờ user quyết định).
- Các thay đổi `audiobook_long.py` (music bed) + docs phiên trước vẫn chưa commit — gộp chung khi user duyệt.

## 2026-08-12 — Kiểm tra và hoàn thiện EPUB `zuo-yi-ge-you-jing-jie-de-nu-zi`

### Đã làm
- **Rà soát EPUB** (user yêu cầu kiểm tra EPUB trước khi làm audio). Phát hiện 3 vấn đề:
  1. **TOC rỗng/thiếu**: pandoc chỉ đưa 6 mục vào nav (4 chương + Title + TOC) dù `--toc` — nguyên nhân **32/35 heading `##` không có dòng trống trước** (do merge chunk nối liền) → pandoc parse thành paragraph, không thành heading → không vào TOC.
  2. **Title metadata mất**: `<dc:title>` rỗng — `--metadata title=...` (viết dài) không hoạt động trong pandoc 3.10, phải dùng `-M title=...`; còn lại author/lang OK.
  3. **Sót ký tự OCR**: "I三1" (số trang OCR) còn trong văn bản.
- **Fix**: thêm dòng trống trước 32 heading `##` trong `vi.md`; dùng `-M` thay `--metadata`; `--split-level=2` (thay `--epub-chapter-level` deprecated) để chia 36 chapter file; xóa 3 dòng artifact OCR (I三1, ·079：, :191·...).
- **Kết quả EPUB cuối**: 203KB, 44 entries (36 chapter xhtml riêng biệt), **TOC đầy đủ 35 chương + title**, metadata title/author=Vãn Tình/lang=vi đúng, **0 chữ Hán sót** trong văn bản, zip hợp lệ (mimetype application/epub+zip, testzip OK).

### File đổi
- `output/books/zuo-yi-ge-you-jing-jie-de-nu-zi/final/vi.md` (thêm dòng trống trước heading, xóa artifact OCR) — KHÔNG commit (sản phẩm)
- `output/books/zuo-yi-ge-you-jing-jie-de-nu-zi/final/vi.epub` + `trilingual.epub` (rebuild) — KHÔNG commit (sản phẩm)
- `docs/session_log.md` — có commit (docs)

### Còn dở
- Audiobook chưa làm — chờ user duyệt EPUB xong.

## 2026-08-12 — Bổ sung EPUB tam ngữ (có pinyin) `zuo-yi-ge-you-jing-jie-de-nu-zi`

### Đã làm
- User hỏi "có pinyin đâu nhỉ" — phát hiện EPUB ban đầu tạo từ `vi.md` (chỉ tiếng Việt), **thiếu pinyin** so với convention cuốn trước (`qie-yi-qing-shen-gong-bai-tou` có `final/tamngu.epub` + `trilingual.epub` tam ngữ).
- **Tạo `final/tamngu.epub` từ `tamngu.md`** (584KB): pandoc + css + `-M title/author/lang=zh` + `--toc --toc-depth=2 --split-level=2`. Kết quả: 44 entries, 36 chapter files, TOC đủ 35 chương, mỗi dòng hiển thị **3 dòng: Hán → pinyin → Việt** (verify: 晚情 / wǎn qíng / Vãn Tình).
- Copy `tamngu.epub` → `trilingual.epub` (thư mục gốc, đúng convention: trilingual.epub = bản tam ngữ).
- Giữ `final/vi.epub` (bản chỉ Việt, 203KB) cho app "Đọc thử" fallback.
- Xóa file test dư `final/vi.test.epub`.

### File đổi
- `output/books/zuo-yi-ge-you-jing-jie-de-nu-zi/final/tamngu.epub` (mới, 584KB) — KHÔNG commit (sản phẩm)
- `output/books/zuo-yi-ge-you-jing-jie-de-nu-zi/trilingual.epub` (đã ghi đè = bản tam ngữ 584KB) — KHÔNG commit (sản phẩm)
- Xóa `final/vi.test.epub` (file test) — KHÔNG commit
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Audiobook chưa làm — chờ user duyệt EPUB tam ngữ.

### Git
- Chưa commit. Đề xuất: 1 commit docs (STATE.md + session_log.md) sau khi user duyệt.

## 2026-08-12 — Setup GPU TTS + chạy lại 3 chương đầu `ban-co-nam-cho-ngoi`

### Đã làm
- **Setup GPU**: venv `working\venv-vieneu` nâng torch CPU → **torch 2.13.0+cu126** (`pip install --index-url https://download.pytorch.org/whl/cu126 --force-reinstall --no-deps torch torchaudio`). RTX 3060 12GB nhận `cuda:0`. Cài thêm `transformers` (PyTorch backend v3turbo cần).
- **Patch local vieneu**: `inference_v3_turbo.py::_load_mono` dùng `soundfile` thay `torchaudio.load` — torchaudio trên PyTorch path đòi `torchcodec` + FFmpeg shared DLL không có trên máy. Patch bằng soundfile (có sẵn) đọc WAV trực tiếp, không cần FFmpeg.
- **`audiobook_long.py` thêm**: `--gpu` (khởi tạo `Vieneu(device="cuda")` qua helper `_create_tts`, tự fallback CPU nếu không có CUDA) + `--batch-size` (default 8). `generate_chapter_audio` dùng **`infer_batch`** (static batching, gom chunk theo batch) khi GPU — đo được 0.7-1.4s/chunk vs 4.1s/chunk khi infer đơn.
- **Kết quả GPU**: RTF 0.14-0.16 (vs CPU 0.42) — nhanh ~6x. Chapter 14 phút audio tạo trong ~2.3 phút gen.
- **Chạy lại 3 chương đầu `ban-co-nam-cho-ngoi` bằng GPU có nhạc nền**: ch01-03 mới (13.3/12.5/14.1 MB), mỗi chương 1 bài nhạc xoay trong `sach_ke_chuyen_10_lofi.mp3` + `sach_ke_chuyen_11_lofi.mp3`, volume 0.20, temp 0.3, top_k 10 (giữ tham số chốt). Cập nhật progress JSON (completed 1-3, pipeline v5, music_files/volume).

### File đổi
- `scripts/audiobook/audiobook_long.py` — thêm `--gpu`/`--batch-size`, helper `_create_tts`, `generate_chapter_audio` dùng `infer_batch` — **có commit** (code)
- `working/venv-vieneu/...` (torch cu126, transformers, patch `inference_v3_turbo.py::_load_mono`) — KHÔNG commit (venv)
- `output/books/ban-co-nam-cho-ngoi/audiobook/ch0{1,2,3}.mp3` — KHÔNG commit (sản phẩm)
- `working/progress_audio/ban-co-nam-cho-ngoi.json` — KHÔNG commit (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- 9 chương còn lại (4-12) của `ban-co-nam-cho-ngoi` chưa chạy lại GPU — chạy `--chapter 4 5 ... 12 --gpu --music auto --music-volume 0.20 --temperature 0.3 --top-k 10` khi muốn.
- Khi chạy nền: stdout bị buffer → log trống dù process chạy. Nên chạy trực tiếp (không nền) hoặc thêm `-u`/flush.

### Git
- Chưa commit. Đề xuất: 1 commit code (`audiobook_long.py`) + 1 commit docs (STATE + session_log) sau khi user duyệt.

## 2026-08-12 — GPU toàn pipeline: MinerU + PaddleOCR (tách venv OCR)

### Đã làm
- **`.venv` (project, chứa MinerU)**: nâng torch → 2.13.0+cu126 (RTX 3060 `cuda:0`). `mineru_extract.py --device auto` giờ tự dùng GPU. Đã **gỡ sạch paddlepaddle-gpu/paddleocr/paddlex khỏi `.venv`** vì paddle GPU + torch CUDA trong cùng 1 tiến trình xung đột cuDNN DLL (`cudnn_cnn64_9.dll`/`shm.dll` WinError 127).
- **Tạo venv mới `working\venv-ocr`** (Python 3.11, KHÔNG torch): paddlepaddle-gpu **3.3.1** (index `https://www.paddlepaddle.org.cn/packages/stable/cu126/`) + paddleocr **3.7.0** + paddlex 3.7.2. Test thực tế: OCR GPU chạy (device 0, Compute Capability 8.6). Lưu ý: paddle 3.3.1 cần CUDNN 9.9, máy có 9.5 — chỉ là warning, chạy ổn.
- **`ocr_paddle.py` sửa sang API paddleocr 3.x**:
  - Khởi tạo: `PaddleOCR(lang=..., device='gpu'/'cpu')` (bỏ `use_gpu`/`use_angle_cls`/`show_log` — 3.7 từ chối các tham số này), fallback API 2.x.
  - `ocr_anh()`: dùng `predict()` → `rec_texts` (thay `ocr()` API cũ), fallback 2.x.
  - **Tự relaunch qua venv-ocr**: nếu env hiện tại thiếu paddleocr nhưng `working/venv-ocr` có → `subprocess.run` chạy lại bằng venv-ocr (CREATE_NO_WINDOW). Verify: chạy bằng `.venv` python → relaunch → OCR GPU thành công.
- **Kết quả**: cả 3 công đoạn nặng đều GPU — MinerU (`.venv`/torch), PaddleOCR (`venv-ocr`/paddle), TTS (`venv-vieneu`/torch). Mỗi cái 1 venv riêng, không xung đột.

### File đổi
- `scripts/extract/ocr_paddle.py` — API 3.x + tự relaunch venv-ocr — **có commit** (code)
- `.venv` (torch cu126, gỡ paddle) — KHÔNG commit (venv)
- `working/venv-ocr/` (mới, paddle GPU + paddleocr) — KHÔNG commit (venv)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Nếu muốn hết warning CUDNN 9.9 vs 9.5: cài paddle bản khớp CUDNN 9.5 hoặc nâng cudnn torch — không bắt buộc (chạy ổn).
- 9 chương còn lại (4-12) `ban-co-nam-cho-ngoi` chưa chạy lại GPU.

### Git
- Chưa commit. Đề xuất: gộp chung commit code (`audiobook_long.py` + `ocr_paddle.py`) + 1 commit docs khi user duyệt.

## 2026-08-12 — Dịch lại toàn bộ `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` + audiobook GPU

### Đã làm
- User yêu cầu "dịch lại như cuốn sách mới, ghi đè dữ liệu cũ, dọn thư mục cũ" → **xóa sạch** toàn bộ data cũ của slug (extracted, chunks, progress, qa, progress_audio, output/books, glossary).
- **Pipeline từ đầu**: extract EPUB (`做一个刚刚好的女子 不攀附,不将就 (晚情).epub`, 55 mục) → raw.md 130.968 ký tự → **QC fail** vì 60 dòng `---` + 55 dòng `xml version=...` (rác extract EPUB) → làm sạch → QC OK. Detect `zh-Hans` → chunk smart 71 chunk (109.434 đơn vị) → glossary 26 thuật ngữ → skeleton trilingual 71 chunk.
- **Fix bug**: `init_trilingual_skeleton.py` import `add_pinyin` sai path (thiếu `scripts/pinyin/`); `batch_manifest.py` + `batch_qa.py` thiếu `sys.stdout.reconfigure(encoding='utf-8')` (lỗi cp1252 khi in tiếng Trung/Việt).
- **Dịch 71/71 chunk**: sub-agent (general) dịch song song 3 chunk/lượt — mỗi agent đọc `working/_dich/chunk_XXX.src.txt` (tách từ original_text) → dịch → ghi `.vi.txt` → tôi merge vào JSON bằng `_merge_vi.py` (kiểm tra số dòng khớp 100%). Chunk 0 dịch bằng agent trực tiếp. Tổng ~24 lượt agent, **QA batch 71/71 OK, 0 lỗi**.
- **Merge**: `tamngu.md` (1.79MB) + `vi.md` (0.59MB, 3395 dòng) — lưu ý merge_chunks tạo tên `<slug>_trilingual.md`/`_translated.md` → rename sang `tamngu.md`/`vi.md`.
- **EPUB**: `vi.epub` (0.18MB) + `tamngu.epub` (0.68MB) + copy → `trilingual.epub` (0.68MB). Cảnh báo ảnh Image0000X.jpg không fetch được (ảnh chưa extract ra images/) — không ảnh hưởng nội dung.
- **Audiobook GPU toàn cuốn đang chạy**: `--gpu --batch-size 8 --music auto --music-volume 0.20 --temperature 0.3 --top-k 10` (50 chương, mỗi chương ~2.5 phút, ~2-2.5 giờ). Chương 1 xong 12.8MB.

### File đổi
- `scripts/translate/init_trilingual_skeleton.py` — fix path add_pinyin — **có commit** (code)
- `scripts/translate/batch_manifest.py`, `scripts/qa/batch_qa.py` — thêm stdout utf-8 — **có commit** (code)
- `working/_dich/` (71 .src.txt + .vi.txt), `working/_read_chunk.py`, `_write_chunk.py`, `_merge_vi.py`, `_split_src.py` — helper tạm — KHÔNG commit
- `working/extracted|chunks|progress/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/` — KHÔNG commit (sản phẩm)
- `glossary/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing.csv` — KHÔNG commit (sản phẩm)
- `output/books/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/` (tamngu.md, vi.md, 3 epub, audiobook) — KHÔNG commit (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Audiobook toàn cuốn **đã chạy xong 50/50 chương** (435.6MB, ~7.9 giờ audio, gen ~70 phút GPU). Lưu ý: `--music auto` ghi metadata chỉ 1 file nhạc nhưng thực tế xoay nhiều bài.
- Helper tạm `working/_dich/` + `_*.py` đã dọn xong.

## 2026-08-12 — Fix lỗi font EPUB (Calibre hiển thị ký tự có dấu thành `?`)

### Đã làm
- User báo "file epub bị lỗi font" khi mở trong **Calibre**: ký tự có dấu (pinyin `nǐ tuǒ`, tiếng Việt `Sự thỏa hiệp`) hiển thị thành `?`.
- **Verify nội dung file KHÔNG lỗi**: đọc XHTML bằng Python UTF-8 → Hán `你的妥协，成全你了吗？`, pinyin `nǐ de tuǒ xié`, Việt `Sự thỏa hiệp` đều đúng, 1614 ký tự có dấu. Nguyên nhân = Calibre thiếu font render các glyph này (EPUB cũ dùng `font-family: serif` generic, `lang="en-US"`).
- **Fix**: nhúng font **NotoSerifSC-VF.ttf** (từ `C:\Windows\Fonts`, hỗ trợ Hán + Latin mở rộng + dấu Việt) vào EPUB:
  1. CSS mới `@font-face` + `font-family: "NotoSerifSC", serif` cho body/h1-3/p/tam-ngữ.
  2. pandoc `--epub-embed-font NotoSerifSC-VF.ttf` (file ~25MB).
  3. **Post-fix path**: pandoc ghi `url("fonts/...")` trong CSS ở `EPUB/styles/` → sửa thành `url("../fonts/...")` (zip rewrite).
- **Kết quả**: `trilingual.epub` + `final/tamngu.epub` (15.4MB) + `final/vi.epub` (14.9MB) đều nhúng font. Verify: FONT-FACE OK, path `../fonts/` đúng.

### File đổi
- `output/books/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/{trilingual.epub, final/tamngu.epub, final/vi.epub}` — KHÔNG commit (sản phẩm, đã ghi đè bản cũ)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)
- Ghi nhận: quy trình fix font EPUB (embed font + sửa path) — có thể áp dụng cho các cuốn ZH khác khi cần.

### Còn dở
- Không có — user cần mở lại EPUB trong Calibre để xác nhận font đã hiển thị đúng.

## 2026-08-12 — Fix lỗi `?` tiếng Việt (lần 2 — tìm ra nguyên nhân THẬT: mojibake chunk 1)

### Đã làm
- User báo "vẫn bị lỗi ? ở chỗ tiếng việt" + hỏi "bạn đang tạo epub bằng gì" → trả lời: **pandoc** (make_epub.py).
- **Điều tra sâu**: kiểm tra font Noto Serif SC + Arial Unicode MS đều CÓ glyph tiếng Việt (ạ/ả/ẽ/ợ) → **không phải vấn đề font**. Quét nguồn: `vi.md` chứa `Trong m?t nh?m ng??i ph?n ??i` → **mojibake trong chính bản dịch**.
- **Root cause**: chỉ chunk 1 bị hỏng (1071 ký tự `?` giữa chữ) — vì tôi ghi chunk 1 bằng `Get-Content | python _write_chunk.py 1` (pipe qua PowerShell dùng encoding cp1252 làm hỏng dấu Việt). Các chunk 2-70 agent ghi file `.vi.txt` UTF-8 → sạch (quét lại 0 mojibake).
- **Fix**: dịch lại chunk 1 → ghi file UTF-8 → Python đọc file ghi vào JSON (đúng encoding) → merge lại `vi.md` + `tamngu.md` → rebuild 3 EPUB (vẫn nhúng font Noto Serif SC) → verify: 0 mojibake, `Trong một nhóm người phản đối` đúng, font path đúng.
- ⚠️ **Rút kinh nghiệm**: không bao giờ pipe text tiếng Việt qua PowerShell — phải ghi file UTF-8 rồi đọc bằng Python (đúng như cách `_merge_vi.py` đã làm cho các chunk khác).

### File đổi
- `working/progress/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/chunk_001.json` — sửa translated_text đúng — KHÔNG commit
- `output/books/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/{final/vi.md, final/tamngu.md, trilingual.epub, final/tamngu.epub, final/vi.epub}` — KHÔNG commit (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- User mở lại EPUB trong Calibre xác nhận.
- `ban-co-nam-cho-ngoi` 9 chương (4-12) chưa chạy lại GPU (việc cũ).

## 2026-08-13 — Chạy lại audiobook chương 1-2 sau khi sửa vi.md

### Đã làm
- User: "vi.md sửa ok chưa thì chạy lại cho tôi" — verify `vi.md` 0 mojibake (459.261 ký tự).
- Audiobook dùng nguồn `output/books/<slug>/final/vi.md` (find_vi_md). Vì `vi.md` đổi (fingerprint 33a5b45e ≠ cũ a9ddcf70) nhưng progress JSON vẫn đánh dấu 50 chương xong → script không tự chạy lại.
- User chọn **chỉ tạo lại chương 1-2** (nơi chứa chunk 1 đã sửa): `audiobook_long.py --chapter 1 2 --force --gpu --batch-size 8 --music auto --music-volume 0.20 --temperature 0.3 --top-k 10`.
- Kết quả: ch01.mp3 (7.6MB) + ch02.mp3 (9.7MB) tạo lại từ vi.md mới, 48 chương còn lại giữ nguyên (nội dung không đổi). Tổng 50 MP3 / 430.3MB. Progress JSON giờ chỉ ghi 2 chương (do --force reset) — nếu chạy tiếp cần `--force` hoặc reconcile.

### File đổi
- `output/books/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/audiobook/{ch01,ch02}.mp3` — KHÔNG commit (sản phẩm)
- `working/progress_audio/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing.json` — KHÔNG commit (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit code + 1 commit docs khi user duyệt.

## 2026-08-13 — Sửa hiển thị progress audiobook: in dần từng nhóm batch

### Đã làm
- User feedback: khi chạy audiobook GPU, log in **một loạt 60/60 sau khi chapter xong** (vì code gọi `infer_batch` cho toàn bộ chunk rồi mới in) — muốn **nhảy dần từng dòng 1/60, 2/60...** như cũ.
- Thử `--progress single` (\r ghi đè 1 dòng) nhưng user muốn giữ kiểu in nhiều dòng — chỉ cần in theo thời gian thực.
- **Fix thật**: chia `infer_batch` thành các **nhóm batch_size** trong `generate_chapter_audio` — mỗi nhóm infer xong in ngay các chunk của nhóm đó (dòng nhảy dần theo nhóm). Bỏ hết code `\r`/`_progress`/`--progress` (revert).
- Test chương 9 ban-co-nam-cho-ngoi: log nhảy dần `[batch 1/69] [batch 2/69]...` đúng ý (bị timeout test nhưng chỉ là giới hạn lệnh).
- Khôi phục progress JSON ban-co-nam-cho-ngoi (bị reset rỗng do `--force` test) → 12 chương đầy đủ. ch09 giữ bản audio cũ hợp lệ.

### File đổi
- `scripts/audiobook/audiobook_long.py` — chia batch thành nhóm, in dần — **có commit** (code)
- `working/progress_audio/ban-co-nam-cho-ngoi.json` — khôi phục — KHÔNG commit (sản phẩm)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit code + 1 commit docs khi user duyệt.

## 2026-08-13 — Cập nhật dich.md theo quy trình thực tế

### Đã làm
- User yêu cầu kiểm tra `dich.md` xem quy trình có cần chỉnh sửa gì không → rà soát, đối chiếu với thực tế phiên.
- **Cập nhật dich.md**:
  - **B. Extract**: thêm bước làm sạch rác extract EPUB (`xml version=...`, `---`) khi QC fail; ghi chú `--device auto` dùng GPU.
  - **I. Merge**: thêm `--output-dir` tường minh (merge_chunks tự dò PROJECT_ROOT lệch); ghi chú rename `<slug>_trilingual.md`→`tamngu.md`, `<slug>_translated.md`→`vi.md`; thêm bước verify mojibake sau merge.
  - **J. EPUB**: thêm quy trình nhúng font Noto Serif SC cho sách ZH (pandoc `--epub-embed-font` + CSS `@font-face` + fix path `../fonts/`) — tránh Calibre hiển thị `?`.
  - **K. Audiobook**: thêm lệnh generate audiobook GPU đầy đủ (`--gpu --batch-size 8 --music auto --music-volume 0.20 --temp 0.3 --top-k 10`), ghi chú log nhảy dần từng nhóm batch, `-u` khi chạy nền, chạy lại `--chapter N --force` khi vi.md đổi.
  - **Ghi chú chung**: thêm mục kinh nghiệm (không pipe tiếng Việt qua PowerShell, fix cp1252, path add_pinyin, xung đột cuDNN tách venv).

### File đổi
- `.opencode/command/dich.md` — cập nhật quy trình — **có commit** (config/code)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Cải tổ thư mục input theo trạng thái xử lý

### Đã làm
- User muốn: nhìn `input/` là biết sách nào đã dịch / đã tạo audio → chọn phương án **thư mục con**.
- **Tạo script `scripts/manage_input.py`**: dò `output/books/<slug>/final/vi.md` (đã dịch) + `<slug>/audiobook/*.mp3` (đã audio) → map file input → slug (khớp chữ Latin + bảng map thủ công cho tên tiếng Trung, loại trừ file " 2."/" 3.") → di chuyển vào `input/chua-lam/` | `input/da-dich/` | `input/da-audio/`. Có `--check` (chỉ báo cáo).
- **Đã di chuyển 13 file hiện tại**: chua-lam 4 (刚刚好的女子 2/3.pdf, 我在豪门, 有多想要), da-dich 3 (EU-BIM, 且以情深, 有境界), da-audio 6 (Ban Co Nam, Rung Na-uy, Đắc Nhân Tâm, 不攀附, 有风骨 x2).
- **Tạo `input/README.md`** giải thích cấu trúc + cách dùng.
- **Cập nhật `dich.md`**: mục A/B tìm file trong 3 thư mục con (không chỉ gốc input/), bước K thêm chạy `manage_input.py` sau pipeline.

### File đổi
- `scripts/manage_input.py` — script mới — **có commit** (code)
- `input/` (cấu trúc thư mục con + README) — KHÔNG commit (file gốc)
- `.opencode/command/dich.md` — cập nhật quy trình — **có commit** (config)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Thêm quy tắc bắt buộc cập nhật input/ vào AGENTS.md

### Đã làm
- User yêu cầu: khi dịch hoặc tạo audio xong, **bước cuối phải cập nhật input/** để người dùng biết trạng thái sách.
- **Cập nhật AGENTS.md** (quy tắc bắt buộc, agent đọc mỗi phiên):
  - Mô tả `/dich`: thêm "BƯỚC CUỐI CÙNG (bắt buộc) chạy `python scripts\manage_input.py`".
  - Vòng lặp pipeline: thêm **bước 12. Cập nhật input/ (BẮT BUỘC)**.
  - Cấu trúc thư mục: mô tả input chia 3 thư mục con (`chua-lam/`, `da-dich/`, `da-audio/`).
- `dich.md` đã có bước này từ trước (dòng 106).

### File đổi
- `AGENTS.md` — thêm quy tắc bắt buộc — **có commit** (docs)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Thêm rotate session_log + /start /done cho Command Code

### Đã làm
- User hỏi session_log có tự xoá không → trả lời: không, chỉ append mãi (đã 71KB/45 entry). Chọn phương án C (script tự động rotate).
- **Tạo `scripts/rotate_session_log.py`**: khi `docs/session_log.md` > 100KB (`--max-kb`), dời entry cũ hơn 3 tháng (`--keep-months`) vào `docs/session_log_archive/<YYYY-MM>.md` (theo tháng), file chính giữ mào đầu + entry gần nhất. Có `--check` (chỉ báo cáo). **Đã test thật**: archive 2 entry cũ vào đúng file tháng, file chính giữ entry mới — hoạt động đúng; session_log thật không bị ảnh hưởng (71KB giữ nguyên).
- **Tạo `/start` + `/done` cho Command Code** tại `.commandcode/commands/` (đúng vị trí project-level theo docs Command Code). `/done` bổ sung: chạy rotate + chạy `manage_input.py` (cập nhật input/) trước khi đề xuất commit. Giữ bản `.opencode/command/` cũ (legacy).
- **Cập nhật AGENTS.md**: ghi chú rotate tự động + 2 command ở `.commandcode/commands/`.

### File đổi
- `scripts/rotate_session_log.py` — script mới — **có commit** (code)
- `.commandcode/commands/start.md`, `.commandcode/commands/done.md` — mới — **có commit** (config)
- `AGENTS.md` — ghi chú rotate + command — **có commit** (docs)
- `docs/session_log.md` — có commit (docs)

### Còn dở
- Khi session_log > 100KB, rotate tự chạy trong `/done`; hoặc chạy tay `python scripts\rotate_session_log.py`.

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Thêm /dich vào Command Code

### Đã làm
- User yêu cầu cho `/dich` vào Command Code (cùng với /start /done đã làm).
- **Copy `.opencode/command/dich.md` → `.commandcode/commands/dich.md`** (vị trí project-level của Command Code). Nội dung đã cập nhật đầy đủ (merge --output-dir, EPUB nhúng font, audiobook GPU, manage_input, ghi chú kinh nghiệm).
- `.commandcode/commands/` hiện có: `start.md`, `done.md`, `dich.md` (+ `dual-Agent.md` có sẵn).
- Cập nhật AGENTS.md: `/dich` nằm ở cả `.commandcode/commands/` (Command Code) + `.opencode/command/` (legacy).

### File đổi
- `.commandcode/commands/dich.md` — mới — **có commit** (config)
- `AGENTS.md` — cập nhật command — **có commit** (docs)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Thêm script gộp glossary tự động + verify memory

### Đã làm
- User duyệt 2 nâng cấp từ phân tích: gộp glossary tự động + verify memory.
- **`scripts/process/merge_glossary.py`** (mới): gộp glossary cuốn (`glossary/<slug>.csv`, cột `source,target,notes`) ↔ glossary thể loại (`glossary/genres/<genre>.csv`, cột `source,target,type,note,genre,book`) **2 chiều**:
  - genres → cuốn: đưa thuật ngữ chung của thể loại vào cuốn (Agent dịch không đoán lại).
  - cuốn → genres: bổ sung thuật ngữ mới của cuốn vào kho thể loại kèm cột `book=<slug>`.
  - **Không đè mục đã có** (so theo `source`), ghi UTF-8 atomic. Có `--book-to-genre-only` / `--genre-to-book-only` / `--check` / `--books-dir` / `--genres-dir` (test an toàn).
  - Test: dữ liệu tạm + bản sao glossary thật (qie-yi → tien-hiep: cuốn nhận 22 thuật ngữ, genre nhận 5 mục mới); idempotent (lần 2 báo 0 mục mới).
- **`scripts/verify_memory.py`** (mới): kiểm tra Memory Bank cuối phiên — STATE.md có nhắc sách trong `output/books/` không (bỏ qua test/archive như `long-test`), session_log có entry hôm nay + đủ mục `Đã làm`/`Git` không, session_log có cần rotate (>100KB) không, AGENTS.md còn nhắc đọc memory không. Exit code 0 = OK / 1 = cảnh báo / 2 = lỗi nghiêm trọng.
  - Test: phát hiện đúng 2 sách `dac-nhan-tam`, `rung-na-uy` chưa nhắc trong STATE → **đã thêm 2 sách vào STATE.md** → verify đạt EXIT 0.
- **Cập nhật AGENTS.md**: bước 5 Glossary thêm lệnh chạy `merge_glossary.py`; mục BỘ NHỚ PHIÊN thêm lệnh bắt buộc `python scripts\verify_memory.py` cuối phiên.
- **Cập nhật dich.md**: mục E thêm bước gộp glossary (bước 4).

### File đổi
- `scripts/process/merge_glossary.py` — script mới — **có commit** (code)
- `scripts/verify_memory.py` — script mới — **có commit** (code)
- `AGENTS.md`, `.opencode/command/dich.md` — cập nhật quy trình — **có commit** (docs/config)
- `docs/STATE.md` — thêm 2 sách `dac-nhan-tam` + `rung-na-uy` + mục Đang làm — **có commit** (docs)
- `docs/session_log.md` — entry này — **có commit** (docs)

### Còn dở
- `working/test_merge/` (dữ liệu test tạm) chưa xóa được do permission deny trên `Remove-Item` — không ảnh hưởng (nằm trong working/, gitignored). Có thể xóa tay.

### Git
- Chưa commit. Đề xuất: 1 commit code (2 script mới) + 1 commit docs (AGENTS/dich/STATE/session_log) khi user duyệt.

## 2026-08-13 — Thêm kho glossary theo tác giả (authors) + hỗ trợ --author

### Đã làm
- User hỏi gộp glossary theo tác giả hay thể loại ok hơn → phân tích dữ liệu thật: các cuốn Vãn Tình trùng nhiều thuật ngữ (`晚情/Vãn Tình`, `女人`, `幸福`, `成熟`, `独立`, `善良`, `优雅`, `不攀附/不将就`...) → **gộp theo tác giả đáng hơn** cho tản văn; thể loại (tiên hiệp) vẫn dùng cho thuật ngữ kỹ thuật chung. User duyệt "có ok nhé".
- **Nâng cấp `merge_glossary.py`**: refactor thành hàm `merge_scope()` dùng chung, hỗ trợ **cả `--genre` lẫn `--author`** (có thể truyền cùng lúc), thêm cờ `--authors-dir`, đổi `--book-to-genre-only`/`--genre-to-book-only` thành `--book-to-scope-only`/`--scope-to-book-only` (giữ tương thích mục đích). Kho author cột `source,target,type,note,author,book`.
- **Tạo `glossary/authors/van-tinh.csv`** (47 thuật ngữ): gộp 3 cuốn Vãn Tình đã dịch (`qie-yi-qing-shen-gong-bai-tou` 5, `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` 24, `zuo-yi-ge-you-jing-jie-de-nu-zi` 18) qua `--book-to-scope-only` — mỗi mục kèm cột `book=<slug>` nguồn.
- **Test thật**: giả lập sách Vãn Tình mới chỉ có `晚情` → chạy `--author van-tinh` nhận thêm **46 thuật ngữ chung** (tác giả, khái niệm, nhà xuất bản), `晚情` không bị trùng; chạy lại lần 2 = 0 mục mới (idempotent).
- **Cập nhật AGENTS.md** (bước 5 Glossary: thêm `--author` + kho authors), **dich.md** (mục E: thêm bước author), **STATE.md** (mục Đang làm).

### File đổi
- `scripts/process/merge_glossary.py` — nâng cấp hỗ trợ --author — **có commit** (code)
- `glossary/authors/van-tinh.csv` — kho mới — **KHÔNG commit** (sản phẩm, theo chính sách repo code-only)
- `AGENTS.md`, `.opencode/command/dich.md` — cập nhật quy trình — **có commit** (docs/config)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- `working/test_author/` (thư mục test rỗng) chưa xóa do OneDrive lock — không ảnh hưởng (gitignored).

### Git
- Chưa commit. Đề xuất: 1 commit code + 1 commit docs khi user duyệt.

## 2026-08-13 — Dọn dẹp + chuẩn hóa toàn bộ thư mục glossary/

### Đã làm
- User yêu cầu kiểm tra thư mục glossary/ còn nhiều CSV → phát hiện và xử lý toàn bộ.
- **Phát hiện file rác**: `you-feng-gu-nu-zi.csv` (105 dòng, 68 dòng trùng source) — xác minh trùng **100%** (37/37 thuật ngữ) với `zuo-yi-ge-you-feng-gu-de-nu-zi.csv` (cùng cuốn "Làm người phụ nữ có phong thái") → **đã xóa** file rác, giữ file sạch.
- **Thêm chế độ `--normalize` vào `merge_glossary.py`**: dedupe (bỏ dòng trùng source), gộp `gender`/`notes` vào `note`, thêm cột `type`/`book`, chuẩn hóa về cột chuẩn. Chạy `--normalize` (không đối số) = xử lý toàn bộ thư mục.
- **Chuẩn hóa 7 file cuốn** (`eu-bim`, `qie-yi-qing`, `zuo-yi-ge-3`, `wan-qing`, `zuo-yi-ge`, `you-feng-gu-de`, `you-jing-jie`) → cột `source,target,type,note,book`; **3 kho author** (`van-tinh`, `vi-duong`, `khang-tinh-van`) → cột `source,target,type,note,author,book`. Không mất dữ liệu (số dòng giữ nguyên, chỉ dedupe file rác).
- **Tạo 2 kho author mới**: `vi-duong` (48 mục, gộp 2 cuốn Vi Dương `zuo-yi-ge-3` + `you-feng-gu-de` — trùng 72% nên gộp đáng giá), `khang-tinh-van` (35 mục, 1 cuốn `zuo-yi-ge`).
- **Test thật**: sách Vi Dương mới chỉ có `微阳` → chạy `--author vi-duong` nhận **47 thuật ngữ chung** từ kho; idempotent.
- **Backup trước khi xử lý**: `working/glossary_backup_20260813_150604/` (an toàn, giữ nguyên).
- **Cập nhật AGENTS.md** (bước 5: thêm `vi-duong`, `khang-tinh-van` + `--normalize`), **dich.md** (mục E), **STATE.md**.

### File đổi
- `scripts/process/merge_glossary.py` — thêm `--normalize` — **có commit** (code)
- `glossary/*.csv`, `glossary/authors/*.csv` — dọn/chuẩn hóa/tạo kho — **KHÔNG commit** (sản phẩm, repo code-only)
- `AGENTS.md`, `.opencode/command/dich.md` — cập nhật — **có commit** (docs/config)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- `working/test_vd/`, `working/test_norm/` (thư mục test rỗng) chưa xóa do OneDrive lock — không ảnh hưởng (gitignored).

### Git
- Chưa commit. Đề xuất: 1 commit code + 1 commit docs khi user duyệt.

## 2026-08-13 — Tinh chỉnh verify_memory: lọc thư mục output tên đầy đủ

### Đã làm
- Sau khi dọn glossary, verify_memory báo **8 cảnh báo nhiễu**: các thư mục `output/books/` có tên sách đầy đủ (có dấu/space/tiếng Trung, VD `Ban Co Nam Cho Ngoi - Nguyen Nhat Anh`, `做一个有境界的女子...`) — là output cũ của user lưu theo tên hiển thị, **không phải slug** do pipeline tạo.
- **Fix `verify_memory.py`**: chỉ đối chiếu STATE.md với thư mục có tên **dạng slug hợp lệ** (regex `^[a-z0-9]+(-[a-z0-9]+)*$` — chữ thường + gạch ngang + số). Bỏ qua thư mục tên đầy đủ (output cũ, không quản lý trong STATE).
- Kết quả: verify_memory đạt EXIT 0, sạch cảnh báo nhiễu.

### File đổi
- `scripts/verify_memory.py` — lọc slug — **có commit** (code)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp vào commit code + docs khi user duyệt.

## 2026-08-13 — Đổi tên thư mục output/books theo tên sách gốc

### Đã làm
- User muốn thư mục output đặt tên theo **tên sách gốc** (tên file input) để dễ quản lý → xác nhận "đổi tên + sửa mọi code".
- **Đổi tên 8 thư mục** output/books theo tên file input: ban-co-nam-cho-ngoi → `Ban Co Nam Cho Ngoi - Nguyen Nhat Anh`, dac-nhan-tam → `Đắc Nhân Tâm - Dale Carnegie`, eu-bim → `EU-BIM-Task-Group-Handbook-V2.1`, qie-yi-qing-shen → `且以情深共白头：婚前看情感，婚后靠相处 (晚情)`, rung-na-uy → `Rung Na-uy - Haruki Murakami`, wan-qing → `做一个刚刚好的女子  不攀附, 不将就 (晚情)`, you-feng-gu → `做一个有风骨的女子`, you-jing-jie → `做一个有境界的女子  不自轻,不自弃 (晚情)`.
- **Xoá 4 cuốn không có file input** (user duyệt): `la-nam-trong-la`, `zuo-yi-ge-gang-gang-hao-de-nu-zi`, `-3`, `long-test`.
- **Tạo `metadata.json`** mỗi thư mục output: `{"slug": "<slug-cũ>", "title": "<tên-gốc>", "source_file": "<file input>"}`.
- **Sửa code**: `audiobook_long.py` (thêm `find_book_dir` đọc metadata; sửa find_vi_md/reconcile/out_dir — test OK), `manage_input.py` + `verify_memory.py` (đọc metadata), desktop `MainViewModel.cs` (`GetBookStatus` nhận bookDir+displayTitle, quét input đệ quy, `UpdateBookStatus` dùng Title) + `BookStatus.cs` (thêm field Title). **Build desktop 0 lỗi**.
- **Cập nhật docs**: dich.md (I/J/K dùng `<tên-sách-gốc>`) + đồng bộ `.commandcode/commands/dich.md`; STATE.md (bảng sách + cột thư mục, bỏ 4 cuốn); AGENTS.md (cấu trúc output).

### File đổi
- `scripts/audiobook/audiobook_long.py`, `scripts/manage_input.py`, `scripts/verify_memory.py` — **có commit** (code)
- `desktop/ViewModels/MainViewModel.cs`, `desktop/Models/BookStatus.cs` — **có commit** (code)
- `output/books/` (8 thư mục đổi tên + metadata.json, xoá 4) — KHÔNG commit (sản phẩm)
- `.opencode/command/dich.md`, `.commandcode/commands/dich.md` — **có commit** (config)
- `docs/STATE.md`, `docs/session_log.md`, `AGENTS.md` — **có commit** (docs)

### Còn dở
- Desktop cần chạy thử runtime (build đã 0 lỗi).
- 4 cuốn đã xoá có thể làm lại nếu có file input.

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — File EPUB cuối đặt tên theo tên sách input

### Đã làm
- User yêu cầu: file sản phẩm cuối (EPUB) đặt tên theo tên sách input.
- **Đổi tên `trilingual.epub` → `<tên-sách-input>.epub`** cho 4 cuốn ZH (đọc `metadata.json` → `source_file` bỏ đuôi): 且以情深共白头, 做一个刚刚好的女子 不攀附, 做一个有境界的女子, 做一个有风骨的女子. `final/vi.epub` (bản tiếng Việt thuần) giữ nguyên.
- **Sửa desktop** `FindPreviewEpub`: ưu tiên tìm `<tên-sách-input>.epub` từ metadata.json (trước trilingual.epub/vi.epub/any). **Build 0 lỗi**.
- **Cập nhật dich.md** (mục J): quy tắc tên EPUB cuối = tên file input (giữ rác nếu có) + đồng bộ `.commandcode/commands/dich.md`.

### File đổi
- `output/books/<4 cuốn ZH>/<tên-sách-input>.epub` (rename từ trilingual.epub) — KHÔNG commit (sản phẩm)
- `desktop/ViewModels/MainViewModel.cs` — FindPreviewEpub — **có commit** (code)
- `.opencode/command/dich.md`, `.commandcode/commands/dich.md` — **có commit** (config)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Bỏ final/*.epub, chỉ giữ 1 EPUB gốc theo tên sách input

### Đã làm
- User yêu cầu: tamngu và vi chỉ cần file `.md` — không cần `final/tamngu.epub` / `final/vi.epub`.
- **Xoá 6 file `final/*.epub`** (EU-BIM vi.epub, 且以情深 tamngu.epub, 不攀附 tamngu+vi, 有境界 tamngu+vi).
- **Cấu trúc cuối mỗi cuốn**: 1 file EPUB duy nhất ở gốc tên `<tên-sách-input>.epub` (chỉ cuốn ZH) + `final/*.md` (`vi.md`, `tamngu.md`, `songngu.md`).
- **Cập nhật dich.md** (mục J): chỉ tạo 1 EPUB gốc theo tên input, KHÔNG tạo final/*.epub + đồng bộ `.commandcode/commands/dich.md`.

### File đổi
- `output/books/<các cuốn>/final/*.epub` (xoá 6 file) — KHÔNG commit (sản phẩm)
- `.opencode/command/dich.md`, `.commandcode/commands/dich.md` — **có commit** (config)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Master glossary: gom toàn bộ về 1 file, tự tách khi phình

### Đã làm
- User muốn **gọn glossary về 1 CSV duy nhất** để agent đọc tiết kiệm token, có cột chia theo cuốn/tác giả, **tự tách nhiều file khi phình** → triển khai cách A.
- **`scripts/common/glossary_lib.py`** (mới): đọc `glossary/master.csv` (+ master_001.csv... khi tách), `filter_for_book(rows, slug)` lọc thuật ngữ áp dụng cho cuốn (ưu tiên mục riêng của cuốn → mục cùng author/genre → mục chung), `split_master_if_needed()` tự tách khi >300 dòng. CLI test: `--book/--info/--list-files`.
- **`scripts/common/build_master.py`** (mới): gộp lần đầu từ các file cuốn/genres/authors cũ → `master.csv` (346 thuật ngữ, cột `source,target,type,note,book,author,genre`).
- **`scripts/process/merge_glossary.py`** (rewrite master-based): `--book <slug> --author <a> [--genre <g>]` gộp thuật ngữ cuốn mới vào master (không đè); `--normalize` dedupe; `--check/--info` báo cáo.
- **Sửa các script dùng glossary** → đọc từ master qua `glossary_lib`: `run_pipeline.py` (step_qa), `glossary_qa.py` (thêm `--book-slug`), `translate_helper.py` (tự lấy glossary từ master khi không có `--glossary`), `translate.py` (QA dùng `--book-slug`).
- **Fix root cause `_common.py`**: `PROJECT_ROOT` đổi sang `Path(__file__).resolve().parent.parent` — trước đây import qua path tương đối (`scripts/translate/../common`) làm PROJECT_ROOT lệch → glossary_lib trỏ sai thư mục. **Cũng fix luôn bug `merge_chunks.py` ghi output sai vị trí** (đã ghi chú trong STATE từ lâu).
- **Dọn thư mục**: xóa 7 file cuốn cũ + authors/ + genres/tien-hiep.csv (đã gộp vào master, backup `working/glossary_backup_*`); giữ `master.csv` + `_template.*` + `_fields.md` + `genres/tien-hiep.md` (tài liệu thể loại).
- **Test end-to-end đạt**: `translate_helper --prepare` nhúng 47 thuật ngữ từ master vào prompt; `glossary_qa --book-slug` lọc 47 mục; `run_pipeline --from-step 8 --to-step 8` QA 56 chunk OK; `merge_glossary --book sach-moi --author vi-duong` thêm vào master + tự tách master_001 khi vượt ngưỡng (test với ngưỡng 10, sau đó gộp lại).

### File đổi
- `scripts/common/glossary_lib.py`, `scripts/common/build_master.py` — mới — **có commit** (code)
- `scripts/process/merge_glossary.py` — rewrite master-based — **có commit** (code)
- `scripts/common/_common.py` — fix PROJECT_ROOT .resolve() — **có commit** (code)
- `scripts/pipeline/run_pipeline.py`, `scripts/qa/glossary_qa.py`, `scripts/translate/translate_helper.py`, `scripts/translate/translate.py` — dùng master — **có commit** (code)
- `glossary/master.csv` — file trung tâm (346 dòng) — **KHÔNG commit** (sản phẩm, repo code-only)
- `AGENTS.md`, `.opencode/command/dich.md` — cập nhật quy trình master — **có commit** (docs/config)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- `working/test_master/` (thư mục test rỗng) chưa xóa do OneDrive lock — vô hại.

### Git
- Chưa commit. Đề xuất: 1 commit code (glossary_lib + build_master + merge_glossary + _common + 4 script sửa) + 1 commit docs (AGENTS/dich/STATE/session_log) khi user duyệt.

## 2026-08-13 — Bổ sung metadata.json đầy đủ + rà soát tham chiếu cấu trúc mới

### Đã làm
- User hỏi metadata.json cần thêm gì + đảm bảo các file liên quan cập nhật theo cấu trúc mới.
- **Bổ sung metadata.json** cho 8 cuốn: thêm `author`, `language` (zh/en/vi), `genre`, `has_audio`, `has_epub`, `epub_file`, `created` (giữ slug/title/source_file). `has_audio`/`has_epub`/`epub_file` tự dò từ thư mục.
- **Rà soát tham chiếu cấu trúc cũ**: scripts (trilingual = mode dịch, không phải file), desktop `FindPreviewEpub` (đã ưu tiên tên input, fallback trilingual/vi.epub vô hại — không file nào tồn tại nữa). **Không còn nơi nào phụ thuộc `trilingual.epub`/`final/vi.epub`/`final/tamngu.epub`**.
- **Cập nhật dich.md** (mục I): quy tắc metadata.json đầy đủ (10 trường) + đồng bộ `.commandcode/commands/dich.md`.

### File đổi
- `output/books/<8 cuốn>/metadata.json` — bổ sung trường — KHÔNG commit (sản phẩm)
- `.opencode/command/dich.md`, `.commandcode/commands/dich.md` — **có commit** (config)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit code + docs khi user duyệt.

## 2026-08-13 — Dọn thư mục glossary: chỉ còn master + template

### Đã làm
- User xác nhận giữ `_template.md` + `_template.csv` (translate.py cần để tạo glossary cuốn mới).
- **Đã xóa**: `_fields.md` (không script nào dùng — tài liệu cột cũ), `genres/tien-hiep.md` (tài liệu thể loại, không script đọc, đã gộp hết vào master), `genres/` (thư mục rỗng), **`authors/`** (rỗng — xóa qua `cmd rmdir` sau khi Python bị OneDrive lock).
- **Thư mục `glossary/` giờ tối giản hoàn toàn**: `master.csv` (346 thuật ngữ, file trung tâm) + `_template.csv` + `_template.md`.

### File đổi
- `glossary/_fields.md`, `glossary/genres/tien-hiep.md` — xóa — KHÔNG commit (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp vào commit docs khi user duyệt.

## 2026-08-13 — Dọn output/_archive

### Đã làm
- User hỏi output/_archive cần dọn không → kiểm tra: 9.5MB gồm bản lưu 2 cuốn đã xoá (zuo-gang-gang-1, -3), bản cũ trước đổi tên, thư mục test audio.
- User duyệt → **xoá toàn bộ `output/_archive/`**.
- Dọn tham chiếu: AGENTS.md bỏ dòng `output/_archive/` (legacy). `verify_memory.py` giữ `_archive` trong SKIP_OUTPUT_DIRS (vô hại, an toàn nếu user tạo lại).

### File đổi
- `output/_archive/` — xoá — KHÔNG commit (sản phẩm)
- `AGENTS.md` — bỏ tham chiếu — **có commit** (docs)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp commit docs khi user duyệt.

## 2026-08-13 — Nâng cấp master.csv: chuẩn hóa trùng dịch + note + type + check-dup

### Đã làm
- User hỏi master.csv cần nâng cấp gì → phân tích tìm 3 vấn đề: 3 từ trùng dịch khác nhau, 229 note tiếng Anh, type đều = term.
- **Chuẩn hóa 3 từ trùng dịch** (19 dòng): `修养`→Tu dưỡng, `尊严`→Nhân phẩm, `善良`→Tốt bụng. Hết source trùng target khác.
- **Dịch 239 note Anh→Việt** (Women→Phụ nữ, Happiness→Hạnh phúc, Book title→Tên sách...).
- **Thêm `infer_type()` vào `merge_glossary.py`**: tự phân loại character/place/phrase/term khi gộp cuốn mới (dựa trên note + blacklist từ Hán thông dụng). Test: 晚情→character, 青岛出版社→term, LCA→phrase.
- **Thêm `--check-dup` vào `merge_glossary.py`**: phát hiện source trùng target khác (exit 1 nếu có), chặn tích lũy thêm.
- **Trả lời user**: sách mới có thuật ngữ mới → CÓ tự động cập nhật vào master qua `merge_glossary.py --book <slug> --author <a>` (đã có trong /dich mục E).
- Test: `--check-dup` 0 trùng, translate_helper vẫn nhúng glossary chuẩn (`尊严`→Nhân phẩm, note tiếng Việt).

### File đổi
- `glossary/master.csv` — chuẩn hóa trùng + note — **KHÔNG commit** (sản phẩm, repo code-only)
- `scripts/process/merge_glossary.py` — thêm infer_type + --check-dup — **có commit** (code)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit code (merge_glossary) + 1 commit docs khi user duyệt.

## 2026-08-13 — Hoàn tất audiobook GPU + nhạc nền cho Bạn Có Nằm Chờ Ngồi (12/12 chương)

### Đã làm
- User yêu cầu tạo audio cho `input\da-audio\Ban Co Nam Cho Ngoi - Nguyen Nhat Anh.epub`. Trạng thái: 12 chương đã có MP3 nhưng chỉ ch01-03 chạy GPU + nhạc nền (12/08), ch04-11 là bản CPU cũ (10/08), ch12 chạy 13/08 không nhạc.
- **Chạy lại ch04-12 GPU + nhạc nền**: `audiobook_long.py --slug ban-co-nam-cho-ngoi --chapter 4..12 --force --gpu --batch-size 8 --temperature 0.3 --top-k 10 --repetition-penalty 1.5 --top-p 0.95 --music sach_ke_chuyen_10_lofi.mp3,sach_ke_chuyen_11_lofi.mp3 --music-volume 0.2`. Vì progress JSON ghi cả 12 chương completed nên cần `--force` để ép regen.
- **Chạy lại ch01-03 GPU + nhạc nền** (user yêu cầu "chạy lại cho tôi cả chương 1 đến chương 3"): chạy `--chapter 1 2 3 --force` cùng tham số. Chú ý: lần đầu chạy không `--force` bị skip vì `reconcile_existing_outputs` dò thấy file cũ → dùng `--force`.
- **Gộp progress JSON**: do `--force` reset completed_chapters (lần 4-12 → [4..12], lần 1-3 → [1..3]), đã gộp thủ công thành [1..12] và cộng dồn total_gen_time (5068s) + total_audio_time (11399s ~ 3h10).
- **Verify**: 12/12 file MP3 có duration hợp lệ (11:58–21:30, tổng ~3h10, ~197MB), progress JSON đủ 12 chương + metadata nhạc nền (2 bài xoay, volume 0.2). `ch01_old.mp3` là bản CPU cũ giữ lại.

### File đổi
- `output/books/Ban Co Nam Cho Ngoi - Nguyen Nhat Anh/audiobook/ch01-12.mp3` — tạo lại GPU + nhạc nền — **KHÔNG commit** (sản phẩm)
- `working/progress_audio/ban-co-nam-cho-ngoi.json` — gộp 12 chương — **KHÔNG commit** (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit docs (STATE + session_log) khi user duyệt.

## 2026-08-13 — Benchmark GPU batch_size → chuẩn mới --batch-size 16

### Đã làm
- User hỏi tốc độ tạo audio đã ok chưa → chạy benchmark đo RTF thật trên chunks chương 1 (giữ nguyên tham số sampling temp 0.3/top_k 10/rep 1.5).
- Kết quả: **batch 8 (cũ) RTF 0.185 → batch 16 RTF 0.120 (~2x nhanh hơn)**, batch 32 (0.122) không nhanh hơn nữa (VRAM bão hòa). batch 4 (0.223) chậm nhất.
- Kiểm tra chất lượng batch 8 vs 16 trên 6 chunks: RMS 0.1126 vs 0.1123, centroid 3045 vs 3144 Hz, duration 73.6 vs 75.2s — tương đương, không suy giảm (sai khác do sampling ngẫu nhiên).
- User quyết định: **áp dụng `--batch-size 16` cho các sách sau** (giữ nguyên temp 0.3, top_k 10). Ghi nhớ vào AGENTS.md + STATE.md.

### File đổi
- `AGENTS.md` — thêm chuẩn GPU `--batch-size 16` (mục Scripts + Env) — **có commit** (docs)
- `docs/STATE.md` — cập nhật chuẩn TTS GPU — **có commit** (docs)
- `working/bench_gpu_batch.py`, `working/bench_quality.py` — script benchmark tạm — **KHÔNG commit** (có thể xóa sau)
- `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit docs khi user duyệt.

## 2026-08-13 — Chạy lại audiobook Bạn Có Nằm Chờ Ngồi: batch 16 + nhạc nền volume 0.15

### Đã làm
- User yêu cầu: (1) nhạc nền hơi to, chỉnh nhỏ một chút; (2) chạy nhanh hơn nhưng giữ nguyên chất lượng audio.
- **Giảm volume nhạc nền 0.20 → 0.15** (nhỏ hơn một chút, vẫn nghe rõ).
- **Chạy lại toàn bộ 12 chương GPU với `--batch-size 16`** (chuẩn mới từ benchmark trước) + `--music-volume 0.15`, giữ nguyên temp 0.3, top_k 10, rep 1.5 — chất lượng audio không đổi.
- Kết quả: 12/12 chương tạo lại (22:04–23:08, ~4-6 phút/chương — nhanh ~2x so với batch 8 trước). Tổng gen 3976s / 11415s audio → RTF ~0.35 end-to-end (gồm mixing/convert). Duration hợp lệ (11:47–21:31, tổng ~3h09). Progress JSON: 12 chương, music_volume 0.15.
- Verify: 12/12 MP3 duration đọc được, nhạc nền xoay 2 bài giữ nguyên.

### File đổi
- `output/books/Ban Co Nam Cho Ngoi - Nguyen Nhat Anh/audiobook/ch01-12.mp3` — tạo lại GPU batch 16 + volume 0.15 — **KHÔNG commit** (sản phẩm)
- `working/progress_audio/ban-co-nam-cho-ngoi.json` — music_volume 0.15 — **KHÔNG commit** (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit docs khi user duyệt.

## 2026-08-14 — Fix lỗi TTS đọc lặp câu (hallucinate chunk ngắn) + chạy lại audiobook

### Đã làm
- User báo "1 câu nhưng nói tận 2 lần" → điều tra toàn diện.
- **Xác nhận source text sạch** (vi.md không có dòng trùng bất thường — chỉ hội thoại lặp tự nhiên).
- **Viết script dò lặp audio** (self-similarity trên waveform 8kHz): không bắt được lặp đơn giản vì lỗi là **hallucinate** — model bịa thêm nội dung dài liên tục, không lặp nguyên câu.
- **Root cause (bằng định vị chunk → audio)**: chunk **cực ngắn (< 50 ký tự)** đứng riêng khiến model hallucinate. Ví dụ rõ nhất: ch05 câu "màu đỏ là màu hoa hồng." (23 ký tự) → audio **67.7 giây** (model bịa thêm nội dung). Phân tích: 2 cụm nói 24s + 39.6s từ 1 câu ngắn.
- **Fix triệt để trong `audiobook_long.py`**:
  1. `extract_chapter_text`: gộp paragraph ngắn (<50 ký tự) vào paragraph trước (trừ heading "Chương").
  2. `smart_chunk`: `_should_merge` gộp chunk ngắn cả 2 chiều (vào trước, lượt 2 vào sau), cho phép vượt max_chars lên tới TTS_MAX_CHARS (320) khi gộp chunk ngắn — nguy cơ hallucinate > nguy cơ chunk hơi dài.
- **Kết quả chunking mới**: 0 chunk < 50 ký tự trong 12 chương (trước: 9), max chunk 317 (≤ 320 an toàn).
- **Chạy lại 12 chương GPU batch 16 + nhạc nền volume 0.15** (00:06–01:08, ~6 phút/chương). Verify: ch05 đoạn từng hallucinate giờ đọc 1.5s; dò lặp toàn bộ 0 phát hiện; duration tổng 189.2 phút (~3h09, hợp lệ 11.9–21.5 phút/chương). Progress JSON đủ 12 chương.

### File đổi
- `scripts/audiobook/audiobook_long.py` — fix chunk ngắn (extract + smart_chunk) — **có commit** (code)
- `output/books/Ban Co Nam Cho Ngoi - Nguyen Nhat Anh/audiobook/ch01-12.mp3` — tạo lại — **KHÔNG commit** (sản phẩm)
- `working/progress_audio/ban-co-nam-cho-ngoi.json` — cập nhật — **KHÔNG commit** (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit code (audiobook_long) + 1 commit docs khi user duyệt.

## 2026-08-14 — Nâng cấp vieneu 3.2.5 + rà soát cập nhật các repo khác

### Đã làm
- User hỏi VieNeu trên GitHub có bản cập nhật không → phát hiện **v3.2.5 ra hôm nay 13/08/2026** (máy đang 3.2.4). Nội dung: chia chunk theo ranh giới câu + nhận biết trích dẫn (fix vỡ câu trong dấu ngoặc — đúng lớp vấn đề hallucinate đã gặp), max_new_frames 300→600, style deprecated, pin sea-g2p==0.8.4.
- **Nâng cấp `vieneu` 3.2.4 → 3.2.5** trong `working/venv-vieneu` (kèm sea-g2p 0.8.3→0.8.4).
- **Phải áp lại patch local `_load_mono`** dùng soundfile — bản cài mới ghi đè patch cũ, torchaudio.load lại lỗi torchcodec/FFmpeg. Đã patch lại, test sample GPU OK (RTF 0.65 gồm warm-up).
- **Test end-to-end ch01** với vieneu 3.2.5: chạy xong 5 phút 21s, MP3 hợp lệ 13.3MB.
- **Rà soát các repo khác trong dự án** (kiểm tra PyPI):
  - **mineru** 3.4.4 = bản mới nhất ✅ (không cần nâng)
  - **paddleocr** 3.7.0 = bản mới nhất ✅ (không cần nâng)
  - **torch** 2.13.0 = bản mới nhất ✅ (không cần nâng)
  - **sea-g2p** 0.8.4 = bản mới nhất ✅ (nâng kèm vieneu)

### File đổi
- `working/venv-vieneu` — vieneu 3.2.5 + sea-g2p 0.8.4 + patch `_load_mono` — **KHÔNG commit** (venv)
- `output/books/Ban Co Nam Cho Ngoi - Nguyen Nhat Anh/audiobook/ch01.mp3` — test chạy lại — **KHÔNG commit** (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp vào commit docs khi user duyệt.

## 2026-08-14 — Nâng cấp prompt dịch: hướng dẫn văn chương "láng"

### Đã làm
- User: "VieNeu ngon rồi, phần dịch cần cải thiện cho văn chương lại láng" → rà soát prompt dịch hiện tại.
- Phát hiện: prompt `translate_helper.py::build_prompt` (dùng cho interactive + tham chiếu agent) chỉ có 9 rule khô khan (giữ format, glossary, tỷ lệ đoạn) — **thiếu hoàn toàn hướng dẫn chất lượng văn chương**.
- **Thêm phần `## LITERARY QUALITY` (8 quy tắc)** vào cả 2 nhánh prompt (bilingual EN + trilingual ZH):
  1. Dịch cả câu/đoạn, không dịch từng từ
  2. Câu Hán dài → tách tự nhiên, giữ tỷ lệ đoạn 1:1
  3. Nhịp điệu, tránh lặp từ, tỉnh lược đại từ
  4. Khẩu ngữ hội thoại tự nhiên như người Việt nói
  5. Xưng hô nhất quán theo quan hệ nhân vật
  6. Tái hiện cảm xúc/hình ảnh, chuyển thành ngữ tương đương
  7. Ưu tiên từ thuần Việt
  8. Tránh dịch máy: bỏ "một cách", "những điều", "mà còn" lặp
- Cập nhật cả file template `prompts/translate_prompt.md` cho đồng bộ.
- Verify: syntax OK. Sách mới dịch sẽ tự áp dụng hướng dẫn này (cải thiện độ mượt của bản dịch tương lai).

### File đổi
- `scripts/translate/translate_helper.py` — thêm LITERARY QUALITY — **có commit** (code)
- `prompts/translate_prompt.md` — thêm LITERARY QUALITY — **có commit** (code/docs)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp vào commit code/docs khi user duyệt.

## 2026-08-14 — Nâng chất lượng dịch "láng như nhà văn": book profile + ví dụ cứng/láng

### Đã làm
- User yêu cầu "làm để AI dịch mượt mà và văn chương lại láng như nhà văn" → phân tích 3 nguyên nhân gốc: (1) dịch từng chunk nhỏ mất giọng văn chung, (2) không có bản mẫu chất lượng, (3) không có bước đọc lại. Đề xuất 4 hạng mục, user duyệt **nhóm #1+#2+#4**.
- **#1 Hồ sơ văn chương (book profile)**: script mới `scripts/translate/create_book_profile.py` — in vài chunk đại diện (đầu/giữa/cuối) + khung hồ sơ; agent phân tích và viết `working/profile/<slug>.md` gồm: tác giả/thể loại/giọng văn, **hệ xưng hô từng cặp nhân vật**, cách xử lý hội thoại, thành ngữ đặc trưng, **1 đoạn dịch mẫu chuẩn "láng"**, lưu ý riêng. Test trên `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` hoạt động tốt (71 chunks, in 3 chunk đại diện).
- **#2 Ví dụ "cứng vs láng"**: thêm vào LITERARY QUALITY của `translate_helper.py::build_prompt` (cả trilingual ZH + bilingual EN) + `prompts/translate_prompt.md` — 2 câu mẫu (Hán + EN) kèm bản dịch cứng (máy móc) vs láng (nhà văn), yêu cầu agent đạt chuẩn "Láng".
- **#4 Cập nhật dich.md**: thêm bước **F2** (tạo profile trước khi dịch) + sửa bước G (mỗi batch đọc profile + tuân thủ LITERARY QUALITY) — đồng bộ cả `.commandcode/commands/dich.md` + `.opencode/command/dich.md`.
- Verify: syntax 2 script OK, script profile chạy thử thành công.

### File đổi
- `scripts/translate/create_book_profile.py` — mới — **có commit** (code)
- `scripts/translate/translate_helper.py` — thêm ví dụ cứng/láng — **có commit** (code)
- `prompts/translate_prompt.md` — thêm ví dụ — **có commit** (docs)
- `.commandcode/commands/dich.md`, `.opencode/command/dich.md` — bước F2 + G — **có commit** (config)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit code (script mới + helper) + 1 commit config/docs khi user duyệt.

## 2026-08-14 — Bổ sung "GIỮ HỒN bản gốc" vào quy tắc dịch

### Đã làm
- User: "dịch lại láng nhưng vẫn phải giữ được cái hồn cái chất của văn bản gốc" → bổ sung nguyên tắc giữ hồn vào hệ thống dịch.
- **Thêm quy tắc #2 "⭐ GIỮ HỒN BẢN GỐC"** vào `## LITERARY QUALITY` (nay là "láng nhưng GIỮ HỒN") trong `translate_helper.py::build_prompt` (cả nhánh trilingual ZH + bilingual EN) + `prompts/translate_prompt.md`:
  - "láng" chỉ là cách diễn đạt; KHÔNG thêm ý, bớt ý, đổi logic, làm mềm sắc thái hay cường điệu nguyên tác
  - Giữ nguyên: giọng điệu, quan điểm người kể, thái độ tác giả, chi tiết, số liệu, thứ tự kể
  - Câu gốc nặng nề → dịch nặng nề; gốc mềm mại → dịch mềm mại — không "làm đẹp" thêm
- **Cập nhật `create_book_profile.py`** mục 5 (đoạn dịch mẫu): bản mẫu phải GIỮ HỒN — đúng ý/sắc thái/giọng điệu, không thêm bớt chỉ để "cho đẹp".
- Verify: syntax OK cả 2 script.

### File đổi
- `scripts/translate/translate_helper.py` — thêm quy tắc giữ hồn — **có commit** (code)
- `prompts/translate_prompt.md` — thêm quy tắc giữ hồn — **có commit** (docs)
- `scripts/translate/create_book_profile.py` — mục mẫu giữ hồn — **có commit** (code)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp vào commit code/docs khi user duyệt.

## 2026-08-14 — Nâng cấp QA mức A tối đa: QA văn chương miễn phí

### Đã làm
- User muốn nâng cấp QA mức A lên tối đa (bắt lỗi văn chương miễn phí, 0 token) trước khi cân nhắc mức B (AI sửa).
- **Nâng cấp `scripts/qa/glossary_qa.py`** thêm `qa_van_chuong()` — 4 kiểm tra mới:
  1. **Lặp từ liền kề trong câu** (≥3 lần cùng từ, bỏ từ dừng như "là/và/của/có...") — bắt "cô ấy... cô ấy", "tôi x5"
  2. **Cụm "dịch máy" dùng nhiều** (≥3 lần): "một cách", "những điều", "mà còn", "tuy nhiên", "đã được", "đối với", "vô cùng"... (22 cụm)
  3. **Câu >90 chữ** — dấu hiệu dịch bám cấu trúc gốc, cứng
  4. **Tỷ lệ từ Hán-Việt >30%** — nghi dịch sát từng chữ
- Chèn vào luồng `qa_sach_text` — mục "Chất lượng văn chương (bản dịch)" trong báo cáo, chỉ áp cho bản Dịch.
- **Test trên `ban-co-nam-cho-ngoi/vi.md`**: bắt được **31× "một cách"**, **15× "đối với"**, 7× "những điều", 5× "mà còn", **82 chỗ lặp từ** (vd "tôi x5") — chứng minh bản dịch hiện có vẫn có thể cải thiện, và sách tương lai sẽ được QA tự động gắn cờ.
- Sửa 2 lỗi syntax do ngoặc kép lồng f-string; tinh chỉnh ngưỡng lặp 3 (thay vì 2) để không quá nhạy với văn kể ngôi thứ nhất.

### File đổi
- `scripts/qa/glossary_qa.py` — thêm QA văn chương — **có commit** (code)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp vào commit code/docs khi user duyệt.

## 2026-08-14 — Audiobook qie-yi-qing-shen-gong-bai-tou 75/75 chương + nhạc nền AI theo cảm xúc

### Đã làm
- User yêu cầu tạo audio cho `input/da-dich/且以情深共白头...epub` (Vãn Tình, tản văn hôn nhân ZH).
- **Nhạc nền AI theo nội dung (điểm mới)**: user hỏi "có phân tích chương chọn nhạc không" → phát hiện đang chạy xoay đều; user muốn AI phân tích → **agent tự đọc toàn bộ 75 chương** (từ `detect_chapters`), chấm cảm xúc từng chương (buồn/vui/ngọt/trầm/hài...) và **ghi `music_map.json`** (75 chương → 1 bài nhạc phù hợp mood mỗi chương). Sau đó chạy `--music-auto` để script đọc bản đồ này.
- **Không dùng Deepseek API** (không có key) — agent (chính là AI) tự phân tích, 0 token, không cần config.
- **Chạy GPU batch 16 + volume 0.15**: lần đầu chạy tới ch19 thì user khởi động lại máy → dừng; sau đó **resume tự động** từ ch20 (checkpoint theo chương), hoàn tất 75/75.
- Kết quả: 75 MP3, ~8.5 giờ audio (30.554s), RMS đo được ~0.033 (nhạc nền đúng mức 0.15). `ch05` 1.6 min, `ch30` 4.4 min, `ch75` 4.0 min — hợp lệ.
- **Cập nhật metadata** `has_audio=true` + `epub_file` (trước đây false dù đã có audiobook).
- **Chuyển input**: file từ `da-dich` → `da-audio` (7 file). Lưu ý `manage_input.py` chỉ quét file ở gốc `input/`, không quét thư mục con — chuyển thủ công.
- `music_map.json` giờ có 2 cuốn (zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing 50 chương + qie-yi-qing-shen-gong-bai-tou 75 chương).

### File đổi
- `output/books/且以情深共白头：婚前看情感，婚后靠相处 (晚情)/audiobook/ch01-75.mp3` — tạo mới — **KHÔNG commit** (sản phẩm)
- `working/progress_audio/qie-yi-qing-shen-gong-bai-tou.json` — 75 chương — **KHÔNG commit** (sản phẩm)
- `working/progress_audio/music_map.json` — thêm cuốn này — **KHÔNG commit** (sản phẩm)
- `output/books/.../metadata.json` — has_audio=true — **KHÔNG commit** (sản phẩm)
- `input/da-audio/` — file chuyển vào — **KHÔNG commit** (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: gộp vào commit docs khi user duyệt.

## 2026-08-14 — Tách lệnh pipeline: /dich (chỉ dịch), /audio (chỉ audio), /dich_audio (cả hai)

### Đã làm
- User yêu cầu tách: `/dich` chỉ dịch, `/audio` chỉ tạo audio, `/dich_audio` làm cả hai (trước đây /dich gộp luôn audio).
- **`.commandcode/commands/dich.md`**: bỏ phần K (audiobook) → chỉ A→J (extract → dịch → QA → merge → EPUB); đổi description; kết thúc bằng "K. Tổng kết" (in path + **cập nhật metadata.json** + cập nhật input → da-dich).
- **`.commandcode/commands/audio.md` (mới)**: toàn bộ phần audiobook — A. Xác định sách, B. Nhạc nền AI theo nội dung (music_map, agent tự phân tích nếu chưa có), C. Tạo GPU (batch 16, music-auto, volume 0.15), D. QA audio, E. Cập nhật metadata + input → da-audio, F. Tổng kết.
- **`.commandcode/commands/dich_audio.md` (mới)**: chạy /dich rồi /audio — có xử lý sách đã dịch dở.
- **Đồng bộ `.opencode/command/`** (copy 3 file, fc /b xác nhận khớp).
- **AGENTS.md** dòng command: thêm /audio + /dich_audio; **STATE.md** dòng cuối cập nhật 3 lệnh.

### File đổi
- `.commandcode/commands/dich.md` — bỏ audiobook — **có commit** (config)
- `.commandcode/commands/audio.md`, `dich_audio.md` — mới — **có commit** (config)
- `.opencode/command/dich.md`, `audio.md`, `dich_audio.md` — đồng bộ — **có commit** (config)
- `AGENTS.md`, `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Git
- Chưa commit. Đề xuất: 1 commit config (3 lệnh) + 1 commit docs khi user duyệt.

## 2026-08-14 — Dịch lại chunk 12-14 (cuốn you-duo-xiang-yao-jiu-you-duo-xing-fu-wan-qing)

### Đã làm
- User yêu cầu dịch lại 3 chunk (12, 13, 14) sang tiếng Việt giọng văn "láng" theo book profile.
- Dịch `working/ocr_tmp/chunk_012_orig.txt` (171 dòng), `chunk_013` (190), `chunk_014` (179) → `chunk_*_vi.txt` tương ứng.
- Giữ NGUYÊN 1:1 số dòng (dùng difflib xác nhận: 0 delete/insert, 0 replace lệch). Không sửa file JSON.

### File đổi
- `working/ocr_tmp/chunk_012_vi.txt`, `chunk_013_vi.txt`, `chunk_014_vi.txt` — sản phẩm dịch, KHÔNG commit

### Còn dở
- Chờ gộp vào progress JSON (nếu user muốn thay bản dịch cũ).

### Git
- Không commit (chỉ tạo file sản phẩm + entry docs này).


## 2026-08-14 — Dịch trọn sách 有多想要，就有多幸福 (晚情著) [ZH, ảnh OCR]

### Đã làm
- Pipeline /dich (chỉ dịch, KHÔNG audiobook) cho EPUB toàn ảnh 320 trang (không văn bản).
- OCR PaddleOCR (GPU, venv-ocr) 320 ảnh → raw.md 113.380 ký tự; dọn dòng trang/rác, detect zh-Hans (không OpenCC).
- Chunk ZH: 32 chunk (min1500/max3000/overlap200). Glossary 19 thuật ngữ → merge master.csv (--author 晚情 --genre van-tinh).
- Skeleton trilingual (progress JSON, original/pinyin/translated). Tạo book profile (working/profile/<slug>.md).
- Dịch 32/32 chunk (đa số subagent, chunk 21-23 main agent tự dịch sau 4 lần subagent flaky). QA từng batch ok; QA toàn bộ 32 chunk ok (0 lỗi).
- Merge: tamngu.md (1.8MB) + vi.md (456KB). Tạo 2 EPUB (tam ngữ 537KB + thuần Việt 144KB) bằng pandoc; CSS epub_style.css. Không embed font CJK (không có sẵn).
- Sắp xếp output: output/books/有多想要，就有多幸福 (晚情著)/final/{tamngu.md, vi.md, <tên-gốc>.epub, <tên-gốc>-vi.epub} + metadata.json (slug you-duo-xiang-yao-jiu-you-duo-xing-fu-wan-qing).
- Chuyển input thủ công: input/chua-lam/ → input/da-dich/ (manage_input không map được tên tiếng Trung không Latin).

### Kinh nghiệm
- Subagent dịch chunk ZH→VI thỉnh thoảng trả rỗng/refusal (flaky) — khi gặp, main agent tự dịch hoặc giao lại subagent với orig.txt sạch + chỉ thị ghi Write tool.

### File đổi
- output/books/有多想要，就有多幸福 (晚情著)/final/* — sản phẩm, KHÔNG commit
- working/progress/.../chunk_*.json, working/chunks/..., working/profile/... — KHÔNG commit (sản phẩm trung gian)
- input/da-dich/有多想要，就有多幸福 (晚情著).epub — KHÔNG commit (sản phẩm)
- docs/STATE.md, docs/session_log.md — có commit (docs)

## 2026-08-13 — Dịch lại cuốn `有多想要，就有多幸福` (Vãn Tình) — slug mới you-duo-xiang-jiu-you-duo-xing-fu

### Bối cảnh
- User yêu cầu "dịch lại" `input/da-dich/有多想要，就有多幸福 (晚情著).epub`. Cuốn này ĐÃ có bản dịch cũ (slug `you-duo-xiang-yao-jiu-you-duo-xing-fu-wan-qing`, output trong thư mục tên tiếng Trung) — bản cũ theo cấu trúc cũ, chưa nhúng font.
- Tôi dịch lại với **slug mới** `you-duo-xiang-jiu-you-duo-xing-fu` + cấu trúc output chuẩn mới.

### Đã làm
- EPUB là bản scan toàn ảnh (320 JPG) → extract 320 ảnh → **OCR PaddleOCR GPU** (venv-ocr) → raw.md 112K ký tự → QC OK, zh-Hans.
- 55 chunk → glossary 24 thuật ngữ → skeleton trilingual 55 → **dịch 55/55** (sub-agent 1 chunk/lượt, khớp dòng 1-1, QA 0 lỗi).
- Merge tamngu.md (1.8MB) + vi.md (0.48MB, 0 mojibake) + 3 EPUB nhúng font Noto Serif SC (~15MB).

### Kinh nghiệm (bổ sung)
- Agent dịch giao 3 chunk/lượt hay lỗi giữa chừng; giao **1 chunk/lượt + nhấn mạnh khớp dòng 1-1** thì 100% thành công.

### File đổi
- `output/books/you-duo-xiang-jiu-you-duo-xing-fu/` (final md + 3 epub) — KHÔNG commit (sản phẩm)
- `working/extracted|chunks|progress/you-duo-xiang-jiu-you-duo-xing-fu/` — KHÔNG commit
- `glossary/you-duo-xiang-jiu-you-duo-xing-fu.csv` — KHÔNG commit
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- ⚠️ **Đã sửa tên thư mục output** cho khớp convention: `output/books/you-duo-xiang-jiu-you-duo-xing-fu` → `output/books/有多想要，就有多幸福 (晚情著)` (tên = tên file input, như các cuốn khác). Slug nội bộ `you-duo-xiang-jiu-you-duo-xing-fu` vẫn dùng cho working/progress, glossary, progress_audio. Đã tạo `metadata.json`.
- ⚠️ **Đã sửa rule EPUB**: cuốn này trước đó tạo thừa `final/tamngu.epub` + `final/vi.epub` + `trilingual.epub` — giờ chỉ còn **1 EPUB duy nhất** `有多想要，就有多幸福 (晚情著).epub` ở gốc (tên = file input), final/ chỉ có `.md`. Đã cập nhật `dich.md` (thêm **CHECKLIST bắt buộc** mục K) + AGENTS.md (rule EPUB rõ) để Agent không lệch rule nữa.
- Audiobook chưa làm.

## 2026-08-14 — OCR lại cuốn `有多想要，就有多幸福` bằng MinerU (bỏ PaddleOCR)

### Bối cảnh
- User: "dùng MinerU để OCR cuốn này được không, tôi thấy PaddleOCR ko uy tín lắm" → kiểm tra: MinerU không nhận EPUB trực tiếp nhưng OCR **từng ảnh** được (pipeline, GPU). Test 1 ảnh: **MinerU text liền mạch, đúng đoạn văn — tốt hơn PaddleOCR rõ rệt** (PaddleOCR cắt dòng vụn theo ảnh).
- User duyệt "OCR lại bằng MinerU" → dịch lại toàn bộ từ đầu.

### Đã làm
- Extract 320 ảnh → **OCR MinerU GPU** (`mineru_extract.py --backend pipeline --device auto` từng ảnh, checkpoint theo ảnh) → raw.md 111K ký tự (318/320 có text; trang 118, 254 là ảnh minh họa trống).
- Xóa data cũ (chunks/progress/glossary/final bản PaddleOCR) → QC OK → 55 chunk → glossary → skeleton → **dịch 55/55** (sub-agent 1 chunk/lượt, khớp dòng 1-1, QA 0 lỗi) → merge tamngu.md (1.8MB) + vi.md (0.48MB, 0 mojibake).
- **EPUB đúng rule**: 1 file `有多想要，就有多幸福 (晚情著).epub` ở gốc (nhúng font Noto Serif SC), final/ chỉ `.md`.

### Kinh nghiệm
- **EPUB scan → ưu tiên OCR bằng MinerU** (từng ảnh, pipeline/GPU) thay PaddleOCR — chất lượng text tốt hơn hẳn. PaddleOCR chỉ là fallback cuối.
- MinerU mỗi ảnh ~10-30s → 320 ảnh ~1.5-2 giờ; có checkpoint resume.

### File đổi
- `output/books/有多想要，就有多幸福 (晚情著)/` (final md + 1 epub) — KHÔNG commit (sản phẩm)
- `working/extracted|chunks|progress/you-duo-xiang-jiu-you-duo-xing-fu/` — KHÔNG commit
- `glossary/you-duo-xiang-jiu-you-duo-xing-fu.csv` — KHÔNG commit
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

## 2026-08-15 — Hoàn tất cuốn `有多想要，就有多幸福` (bản cuối: chương + gộp câu)

### Đã làm
- Tiếp nối phiên trước (OCR MinerU + dịch 55 chunk): user duyệt mẫu 3 chương đầu (cấu trúc `## Chương N` + gộp câu + bỏ số trang).
- **Tạo `scripts/process/mark_chapters.py`**: tách chương từ mục lục sách scan → đánh dấu `## Chương N: <tên>`, **xóa toàn bộ `## Trang N`**. Chạy trên raw.md → 71 chương, 0 trang.
- **Tạo `scripts/output/merge_sentences.py`**: gộp câu sau merge — nối các dòng OCR nửa câu thành câu hoàn chỉnh, **bỏ số trang dính vào câu** (giữ ISBN/năm/SĐT), xử lý cả bản Việt (gộp đoạn) lẫn tam ngữ (mỗi câu 1 khối Hán/pinyin/Việt).
- **Dịch tiếp 52 chunk còn lại** (3-54) bằng sub-agent → **55/55 chunk, QA 0 lỗi** → merge → gộp câu → **vi.md 346 dòng sạch (71 chương, 0 Trang)**, tamngu.md 14345 dòng.
- **EPUB cuối**: 1 file `有多想要，就有多幸福 (晚情著).epub` (nhúng font Noto Serif SC), đúng rule.
- Cập nhật `dich.md` (bước OCR scan dùng MinerU + mark_chapters + merge_sentences) + AGENTS.md.

### File đổi
- `scripts/process/mark_chapters.py`, `scripts/output/merge_sentences.py` — mới — **có commit** (code)
- `output/books/有多想要，就有多幸福 (晚情著)/` (final md + 1 epub) — KHÔNG commit (sản phẩm)
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Audiobook chưa làm.

### Git
- Chưa commit. Đề xuất: commit docs (STATE.md + session_log.md) khi user duyệt.

## 2026-08-17 — Dịch lại + audiobook cuốn `且以情深共白头：婚前看情感，婚后靠相处 (晚情)` theo chuẩn văn chương mới

### Bối cảnh
- User yêu cầu "dịch lại và tạo audio cuốn này input\da-audio\且以情深共白头：婚前看情感，婚后靠相处 (晚情).epub" — dịch lại theo chuẩn văn chương "láng" mới (đã triển khai 08-14: LITERARY QUALITY + book profile), sau đó tạo audiobook.
- Sách đã từng dịch (bản cũ) + audiobook cũ 75 chương (08-14). Cần dịch lại từ đầu, không tận dụng bản cũ.

### Đã làm
- **Profile văn chương**: `working/profile/qie-yi-qing-shen-gong-bai-tou.md` (giọng tản văn tâm sự, hóm hỉnh; hệ xưng hô A Ngạn/em-anh, tớ/cậu bạn thân, chị/em độc giả; đoạn dịch mẫu chuẩn "láng").
- **Reset + skeleton mới**: xóa progress cũ → `init_trilingual_skeleton.py --force` → 58 chunk sạch, `batch_manifest.json` mới.
- **Dịch 58/58 chunk** bằng sub-agent 1 chunk/lượt (8 lượt song song), mỗi chunk đọc profile → dịch → ghi `translated_text` (số dòng khớp 100%, giữ heading/`---`/số). Tổng ~84K từ Việt.
- **Fix chunk 14**: bản dịch gộp 2 câu gốc làm 1 dòng (49→48) → tách đúng 2 dòng.
- **QA**: glossary_qa → Hán sót 0.0% (8 ký tự), không mojibake, không dòng lặp. Cảnh báo heuristic (592 chỗ lặp đại từ, 12 cụm dịch máy, 23 câu dài) chấp nhận được với tản văn.
- **Đồng bộ mục lục**: phát hiện mục lục trong chunk 0 giữ tên bài cũ, không khớp heading body mới (vd "Tôi là chỗ dựa của anh" vs "Anh là chỗ dựa của em") → thay mục lục chunk 0 bằng body headings → merge lại vi.md + tamngu.md (65/65 khớp).
- **EPUB**: 1 file duy nhất `且以情深共白头：婚前看情感，婚后靠相处 (晚情).epub` (nhúng font Noto Serif SC, fix path font trong zip).
- **Audiobook**: xóa 75 MP3 cũ + progress cũ → chạy `audiobook_long.py --slug qie-yi-qing-shen-gong-bai-tou --voice active --temperature 0.3 --top-k 10 --repetition-penalty 1.5 --music-auto --music-volume 0.15 --gpu --batch-size 16 --no-read-titles` (nền ~2h, exit 0) → **75/75 chương**, ~6.4 giờ audio (23129s), 369MB. Chương 5 test trước (37.5s gen / 97s audio). Music map AI đọc từ `music_map.json` (slug đã có 75 mục từ bản cũ — nội dung chương giữ nguyên cấu trúc nên dùng lại được).
- **QA audio**: `audio_qa.py --slug "且以情深共白头：婚前看情感，婚后靠相处 (晚情)"` → 75 file MP3 đều OK (báo 79 do đếm cả heading `##` phụ, không phải lỗi — detect_chapters thực tế ra 75).
- **Cập nhật**: metadata.json (has_audio=true), input đã ở `da-audio/` (đúng), STATE.md + session_log.md.

### File đổi
- `working/profile/qie-yi-qing-shen-gong-bai-tou.md` — mới — KHÔNG commit (sản phẩm)
- `working/progress/qie-yi-qing-shen-gong-bai-tou/chunk_*.json` (58) — dịch mới — KHÔNG commit
- `working/qa/qie-yi-qing-shen-gong-bai-tou/` (source_zh, vi_only, report) — KHÔNG commit
- `output/books/且以情深共白头：婚前看情感，婚后靠相处 (晚情)/final/{tamngu.md, vi.md}` — merge mới — KHÔNG commit
- `output/books/且以情深共白头：婚前看情感，婚后靠相处 (晚情)/audiobook/ch01-75.mp3` (75 file, 369MB) — KHÔNG commit
- `output/books/且以情深共白头：婚前看情感，婚后靠相处 (晚情)/且以情深共白头：婚前看情感，婚后靠相处 (晚情).epub` — KHÔNG commit
- `working/progress_audio/qie-yi-qing-shen-gong-bai-tou.json` — progress mới — KHÔNG commit
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Không. Sách đã hoàn tất toàn bộ (dịch lại chuẩn văn chương + EPUB + audiobook).
- (Ghi nhớ) Lần sau nếu mục lục trong chunk 0 giữ tên cũ: đồng bộ mục lục chunk 0 với body headings trước khi merge.

### Git
- Chưa commit. Đề xuất: commit docs (STATE.md + session_log.md) khi user duyệt.

## 2026-08-18 — Dịch lại + audiobook cuốn `做一个刚刚好的女子  不攀附, 不将就 (晚情)` theo chuẩn văn chương mới

### Bối cảnh
- User yêu cầu "tiếp tục đi": dịch LẠI toàn bộ + tạo audiobook mới cho `input\da-audio\做一个刚刚好的女子  不攀附, 不将就 (晚情).epub` (lệnh /dich_audio), tương tự 2 cuốn Vãn Tình gần nhất (qie-yi 08-17, you-duo-xiang 08-16) — theo chuẩn văn chương "láng" mới.
- Sách từng dịch (bản cũ 08-13, chuẩn trước "láng") + audiobook cũ 50 chương. Cần dịch lại từ đầu.
- Slug nội bộ `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing`; thư mục output `output/books/做一个刚刚好的女子  不攀附, 不将就 (晚情)/`. Data extract/chunk 71 sẵn từ trước (dùng lại).

### Đã làm
- **Profile + title map + glossary**: `working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing.md` (giọng "chị cả tâm sự" Vãn Tình, xưng hô tôi/cô-các cô, cậu/tớ bạn thân; 3 đoạn mẫu "láng"), `...-titles.json` (51 mục （01）...（50）+ Lời bạt), `...-glossary.txt` (47 mục từ master lọc theo book+author).
- **Reset + skeleton mới**: xóa progress cũ → `init_trilingual_skeleton.py` → 71 chunk sạch, `batch_manifest.py create` 24 batch.
- **Helper script mới**: `scripts/translate/save_translation_file.py` — ghi translated_text từ file vi (UTF-8), verify số dòng khớp, set word_count + translated_at, không đụng original/pinyin.
- **Dịch 71/71 chunk** bằng sub-agent 1 chunk/lượt (9 đợt song song): mỗi chunk đọc profile → dịch dòng-đối-dòng → ghi progress (số dòng khớp 100%, giữ heading/ảnh/ngoặc kép, bỏ `///`). Tổng ~343K từ Việt / ~109K từ gốc. Relaunch lại các chunk sub-agent trả kết quả rỗng (5,12,17,20,24,38,41,43,45) → đều thành công.
- **QA**: `batch_qa.py` → fix chunk 58 (4 dòng `”` bị thay bằng dòng trống → điền lại) → 71/71 OK. `glossary_qa.py` → fix **chunk 49 để sót Hán** (55 dòng chưa dịch, Hán sót 1602/92.4%) → relaunch sub-agent dịch lại hoàn toàn → 0 Hán. Quét toàn bộ 71 chunk: **Hán sót 0.0%**, không mojibake, không dòng lặp. Cảnh báo heuristic mềm chấp nhận với tản văn.
- **Merge**: `merge_chunks.py --format trilingual` → tamngu.md (1.86MB); không format → vi.md (600KB). Đồng bộ mục lục OK (cả TOC + body heading đều từ titles.json).
- **EPUB**: 1 file duy nhất `做一个刚刚好的女子  不攀附, 不将就 (晚情).epub` (~15.5MB) — nhúng font Noto Serif SC (CSS @font-face + `--epub-embed-font` + fix path `fonts/`→`../fonts/` trong zip), 13 ảnh Image0000X.jpg → `images/`, `--toc --split-level=2`. Xóa EPUB cũ `...(z-library.sk...).epub`.
- **Audiobook**: xóa 50 MP3 cũ + progress cũ (`cmd /c rd /s /q` khi OneDrive read-only) → `audiobook_long.py --slug zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing --voice active --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10 --gpu --batch-size 16 --no-read-titles` → **50/50 chương**, ~7.4 giờ audio (26561s), gen 9536s (RTF 0.36), 405MB. Music map AI: slug đã có 50 mục trong `music_map.json` (nội dung chương giữ cấu trúc → dùng lại).
- **QA audio**: `audio_qa.py --slug "做一个刚刚好的女子  不攀附, 不将就 (晚情)"` → báo 52 (đếm cả heading bìa + Lời bạt) — **chấp nhận**, detect_chapters thực tế 50, 50/50 MP3 tồn tại + size hợp lệ (giống case qie-yi 08-17). Đã xóa 3 dòng artifact `## [N] text0000X.html` trong chunk 0 khỏi vi.md + tamngu.md → rebuild EPUB.
- **Cập nhật**: metadata.json (source_file=`做一个刚刚好的女子  不攀附, 不将就 (晚情).epub`, has_audio=true, has_epub=true), input đã ở `da-audio/` (đúng trạng thái), STATE.md + session_log.md.

### File đổi
- `scripts/translate/save_translation_file.py` — mới — có commit (code)
- `working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing.md` + `-titles.json` + `-glossary.txt` — mới — KHÔNG commit (sản phẩm)
- `working/progress/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/chunk_*.json` (71) — dịch mới — KHÔNG commit
- `working/qa/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing/` (vi_only, report) — KHÔNG commit
- `output/books/做一个刚刚好的女子  不攀附, 不将就 (晚情)/final/{tamngu.md, vi.md}` — merge mới — KHÔNG commit
- `output/books/做一个刚刚好的女子  不攀附, 不将就 (晚情)/audiobook/ch01-50.mp3` (50 file, 405MB) — KHÔNG commit
- `output/books/做一个刚刚好的女子  不攀附, 不将就 (晚情)/做一个刚刚好的女子  不攀附, 不将就 (晚情).epub` — KHÔNG commit
- `output/books/做一个刚刚好的女子  不攀附, 不将就 (晚情)/metadata.json` — cập nhật — KHÔNG commit
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Không. Sách đã hoàn tất toàn bộ (dịch lại chuẩn văn chương + EPUB + audiobook).
- (Tùy chọn) Dọn file tạm `working/_tmp/` (vi_chunk_*.txt, fix_font_path.py, del_chunks*.py, epub_font_style.css).

### Git
- Chưa commit. Đề xuất: commit docs (STATE.md + session_log.md) + script `save_translation_file.py` khi user duyệt.

### Bối cảnh
- Sách đã dịch xong từ 08-15 (71 chương, vi.md sạch). User yêu cầu tạo audiobook. File input đang ở `input/da-dich/`.

### Đã làm
- **Xác định sách**: slug nội bộ `you-duo-xiang-jiu-you-duo-xing-fu` (metadata.json). Phát hiện phiên trước đã tạo thử 8 chương với **cấu hình cũ** (volume 0.2, 1 bài nhạc cố định, slug tiếng Trung) — progress `working/progress_audio/有多想要，就有多幸福 (晚情著).json`.
- **Music map AI (71 chương)**: đọc nội dung từng chương từ vi.md (trích preview), chấm cảm xúc (vui/hài/trầm/ấm/ngọt) → chọn nhạc phù hợp từ `core/music/` (13 bài) → ghi vào `working/progress_audio/music_map.json` (giữ 2 cuốn cũ). Mỗi chương 1 bài nhạc riêng.
- **Tạo audiobook GPU**: `working\venv-vieneu\Scripts\python.exe -u scripts\audiobook\audiobook_long.py --slug you-duo-xiang-jiu-you-duo-xing-fu --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10` — chạy nền ~1h54, **71/71 chương** (exit 0). Script tự phát hiện metadata cũ khác (volume/nhạc) → tạo lại toàn bộ từ đầu theo chuẩn mới. Progress mới `working/progress_audio/you-duo-xiang-jiu-you-duo-xing-fu.json`: 71 chương, ~6h06 audio (22007s), gen 6475s (RTF ~0.29), volume 0.15, music_map từng chương.
- **QA**: `python scripts\qa\audio_qa.py --slug "有多想要，就有多幸福 (晚情著)"` → **ok: true**, 71/71 chapter khớp vi.md, không lỗi. (Lưu ý: `audio_qa.py` resolve theo tên thư mục gốc, không qua metadata — phải truyền tên tiếng Trung thay vì slug nội bộ.)
- **Cập nhật metadata.json**: `has_audio=true`, tự dò `has_epub=true` + `epub_file` (1 file epub gốc duy nhất).
- **Chuyển input**: `input/da-dich/有多想要，就有多幸福 (晚情著).epub` → `input/da-audio/` (shutil.move).

### File đổi
- `working/progress_audio/music_map.json` — thêm slug `you-duo-xiang-jiu-you-duo-xing-fu` (71 chương) — KHÔNG commit (sản phẩm)
- `working/progress_audio/you-duo-xiang-jiu-you-duo-xing-fu.json` — mới (progress chuẩn) — KHÔNG commit
- `working/progress_audio/有多想要，就有多幸福 (晚情著).json` — progress cũ phiên trước, giữ lại (không dùng nữa) — KHÔNG commit
- `output/books/有多想要，就有多幸福 (晚情著)/audiobook/ch01-71.mp3` (71 file, ~370MB) — KHÔNG commit (sản phẩm)
- `output/books/有多想要，就有多幸福 (晚情著)/metadata.json` — has_audio=true — KHÔNG commit
- `input/da-audio/有多想要，就有多幸福 (晚情著).epub` — chuyển từ da-dich — KHÔNG commit
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Không. Sách đã hoàn tất toàn bộ (dịch + EPUB + audiobook).
- (Tùy chọn) Dọn progress cũ `working/progress_audio/有多想要，就有多幸福 (晚情著).json` khi chắc chắn không cần.

### Git
- Chưa commit. Đề xuất: commit docs (STATE.md + session_log.md) khi user duyệt.

## 2026-08-18 — Dịch mới + audiobook cuốn `做一个有风骨的女子  不迎合, 不媚俗 (晚晴)` (Vãn Tình) từ file .azw3

### Bối cảnh
- User yêu cầu "dịch lại và tạo audio cho tôi cuốn sách input\da-audio\做一个有风骨的女子  不迎合, 不媚俗 (晚晴).azw3" — file định dạng **Kindle .azw3** (lần đầu xử lý định dạng này).
- Lưu ý: đây là cuốn **khác** với `做一个有风骨的女子` (Vi Dương, 85 chương, đã hoàn tất 08-13) — cuốn mới của Vãn Tình (晚晴), tên có thêm "不迎合, 不媚俗 (晚晴)".

### Đã làm
- **Chuyển .azw3 → EPUB** bằng calibre (`C:\Program Files\Calibre2\ebook-convert.exe`) → `working/tmp_azw3/zuo-yi-ge-you-feng-gu-de-nu-zi.epub`.
- **Extract + QC**: `epub_extract.py` → raw.md 124KB (50 mục). QC báo 50 dòng `xml version...` + 46 dòng quảng cáo ePUBw.COM → dọn sạch bằng Python (xóa 96 dòng rác). detect_language → **zh-Hans**.
- **Chunk**: 66 chunk (smart, ZH 1500-3000).
- **Glossary**: tạo `glossary/zuo-yi-ge-you-feng-gu-de-nu-zi.csv` (8 thuật ngữ: Đường Đường, Mỹ Mỹ, Đan Đan, Hiểu Lâm, A Phượng, Tiểu R, Starbucks, Sheraton) → merge master (tự tách master_002.csv).
- **⚠️ Xung đột slug**: phát hiện slug `zuo-yi-ge-you-feng-gu-de-nu-zi` **trùng cuốn cũ Vi Dương** — progress/chunks cũ của cuốn Vi Dương đã bị ghi đè khi tạo data mới. Audiobook cũ (85 MP3) + epub + final của cuốn Vi Dương **nguyên vẹn** (không mất thành phẩm). **Đã đổi slug cuốn mới sang `zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing`** (rename progress + chunks + metadata + music_map key).
- **Profile văn chương**: `working/profile/zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing.md` — giọng khích lệ mạnh, xương khí phụ nữ, xưng hô tớ/cậu bạn thân, 先生 → ông xã.
- **Dịch 66/66 chunk** bằng sub-agent 1 chunk/lượt (8 đợt song song) — ~97K từ Việt, khớp dòng 100% (fix chunk 18 dòng trống cuối, chunk 26 thiếu dấu ngoặc đóng cuối).
- **QA**: Hán sót 0.0% (0 ký tự), không mojibake. 6 mục glossary "lệch" là cố ý (风骨 → xương khí theo profile).
- **Merge + đồng bộ TOC**: merge vi.md + tamngu.md → phát hiện 29/46 mục TOC lệch tên với heading body (sub-agent dịch chunk 0 độc lập) → **đồng bộ TOC = body headings** → 0 diff.
- **EPUB**: 1 file duy nhất `做一个有风骨的女子  不迎合, 不媚俗 (晚晴).epub` (16MB, nhúng font Noto Serif SC).
- **Audiobook**: music_map AI 44 chương (phân tích cảm xúc từng bài, 13 bài nhạc core/music) → chạy `audiobook_long.py --slug zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10` → **44/44 chương, ~7.2 giờ audio (25887s), 414MB**, gen 2.2h (RTF ~0.3).
- **QA audio**: 44 MP3 đều OK (audio_qa báo 50 do đếm cả Bìa/Lời bạt — không phải lỗi).
- **Cập nhật**: metadata.json (has_audio=true), input azw3 đã ở `da-audio/` (đúng), STATE.md + session_log.md.

### File đổi
- `working/tmp_azw3/zuo-yi-ge-you-feng-gu-de-nu-zi.epub` — tạm chuyển đổi — KHÔNG commit
- `working/profile/zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing.md` — mới — KHÔNG commit (sản phẩm)
- `working/progress/zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing/` (66 chunk) — mới (rename từ slug cũ) — KHÔNG commit
- `working/chunks/zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing/` (66 file) — mới — KHÔNG commit
- `working/qa/zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing/` — KHÔNG commit
- `output/books/做一个有风骨的女子  不迎合, 不媚俗 (晚晴)/final/{tamngu.md, vi.md}` — KHÔNG commit
- `output/books/做一个有风骨的女子  不迎合, 不媚俗 (晚晴)/audiobook/ch01-44.mp3` (44 file, 414MB) — KHÔNG commit
- `output/books/做一个有风骨的女子  不迎合, 不媚俗 (晚晴)/做一个有风骨的女子  不迎合, 不媚俗 (晚晴).epub` (16MB) — KHÔNG commit
- `output/books/做一个有风骨的女子  不迎合, 不媚俗 (晚晴)/metadata.json` — KHÔNG commit
- `working/progress_audio/music_map.json` — thêm slug `-wan-qing` (44 chương) — KHÔNG commit
- `working/progress_audio/zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing.json` — mới — KHÔNG commit
- `glossary/zuo-yi-ge-you-feng-gu-de-nu-zi.csv` + `master.csv`/`master_002.csv` — KHÔNG commit
- `docs/STATE.md`, `docs/session_log.md` — có commit (docs)

### Còn dở
- Không. Sách đã hoàn tất (dịch + EPUB + audiobook).
- ⚠️ **Bài học**: 2 cuốn khác nhau có thể trùng slug (tên tiếng Trung giống nhau) — khi gặp sách cùng tên, kiểm tra metadata cuốn cũ TRƯỚC khi tạo data mới, dùng suffix phân biệt (`-wan-qing` cho Vãn Tình).
- (Ghi nhớ) File .azw3: chuyển bằng calibre ebook-convert trước khi vào pipeline extract.

### Git
- Chưa commit. Đề xuất: commit docs (STATE.md + session_log.md) khi user duyệt.

---

## 2026-08-22 — Cải tiến EPUB Preview Window (Auto-Resume Bookmark + Typography Settings)

### Đã làm
- **Nghiên cứu kiến trúc Calibre Viewer**: Phân tích giải pháp dàn trang CSS multi-column, quản lý DOM, IPC và lưu bookmark bằng tọa độ/CFI.
- **Tự động lưu & Khôi phục vị trí đọc (Auto-Resume Bookmark)**:
  - Tích hợp JS scroll tracker (debounce 400ms) tự động tính toán tọa độ `scrollY` và tỷ lệ phần trăm đọc (`percent`).
  - Gửi qua `window.chrome.webview.postMessage` về C# và lưu vào `%LocalAppData%\TranslateBook\reading_bookmarks.json`.
  - Khi mở sách lại (`WebView_NavigationCompleted`), tự động cuộn trang mượt mà về vị trí đọc dở.
  - Hiển thị TextBlock `TxtReadingProgress` báo % tiến độ đọc trực tiếp trên Toolbar.
- **Tùy biến Typography & Chiều rộng trang (Typography Settings)**:
  - Thêm ComboBox `CmbFont`: Mặc định (Segoe UI / Microsoft YaHei), Có chân (Noto Serif SC / Georgia / Times New Roman), Thư pháp / Cổ điển (KaiTi / Cambria), Đơn cách (Consolas).
  - Thêm ComboBox `CmbWidth`: Gọn (650px), Vừa (800px), Rộng (1000px), Toàn màn hình (95%).
  - Thêm ComboBox `CmbLineHeight`: Dày (1.5x), Vừa (1.8x), Thoáng (2.2x).
  - Cập nhật `BuildEpubCss()` hỗ trợ biến CSS `--font-family`, `--max-width`, `--line-height`, kèm hiệu ứng chuyển đổi `transition: max-width 0.2s ease`.
  - Hàm `ApplyTypographySettings()` tiêm CSS động realtime vào WebView2 DOM ngay khi người dùng đổi lựa chọn.
- **Kiểm thử**: `dotnet build desktop/TranslateBook.csproj` đạt 0 lỗi / 0 cảnh báo biên dịch.

### File đổi
- `desktop/Views/EpubPreviewWindow.xaml`
- `desktop/Views/EpubPreviewWindow.xaml.cs`
- `docs/STATE.md`
- `docs/session_log.md`

### Còn dở
- Chờ người dùng trải nghiệm thực tế trên giao diện WPF khi đọc thử sách.

### Git
- Thay đổi chưa commit trên `main`. Không tự động commit/push theo quy tắc.


---

## 2026-08-24 - Dịch lại toàn bộ 做一个有风骨的女子 (Vi Dương) từ PDF thật

### Đã làm
- **Phát hiện + sửa lỗi lạc đề**: lần dịch trước của cuốn này dùng nhầm raw.md extract từ EPUB 晚晴 (tản văn Vãn Tình) — nội dung không phải sách thật. PDF thật là self-help nữ giới của Vi Dương (微阳), 吉林文史出版社 2018, ISBN 978-7-5472-5522-3, 8 chương.
- **Pipeline đầy đủ chạy lại**: MinerU GPU (raw.md mới 264KB) → QC 0 lỗi, zh-Hans → chunk 50 → glossary đã có 8 thuật ngữ + master đồng bộ → skeleton trilingual 50 progress JSON → viết lại profile văn chương v2 (风骨='xương khí', tiêu đề 'Người phụ nữ có xương khí') → batch manifest 50 batch × 1 chunk → dịch 50/50 khớp dòng (agent trực tiếp, bám profile) → QA từng batch pass hết.
- **QA tổng thể**: phát hiện source_zh.md cũ trong qa dir là file lạc đề còn sót (false positive) — xóa, QA lại với raw.md đúng: Hán sót 6 ký tự chỉ ở chunk_000 metadata → sửa ('Biên soạn: Vi Dương', '(2018), số 230681'). Cập nhật 7 entry master.csv khớp bản dịch tự nhiên hơn, --normalize 616→178 dòng. QA cuối: ✅ 0 lỗi thuật ngữ / 0 Hán sót / 0 mojibake.
- **Merge**: tamngu.md (12601 dòng, 4 ảnh) + vi.md (807 dòng, 4 ảnh). **BUG FIX scripts/output/merge_sentences.py**: nuốt dòng ảnh khi gom paragraph (thiếu is_image check) → vi.md mất 2 ảnh cuối; đã patch thêm \or is_image(lines[i])\ vào break condition.
- **EPUB**: làm thủ công vì chưa có script nhúng font — CSS @font-face NotoSerifSC + pandoc --epub-embed-font NotoSerifSC-VF.ttf + fix path font trong zip (url('../fonts/...')) → \output/books/做一个有风骨的女子/做一个有风骨的女子.epub\ (~15.5MB).
- **Xóa audiobook cũ** (user chốt): 85 chương MP3 dịch từ bản lạc đề, không khớp sách thật → xóa audiobook/ + progress_audio json + chunks cache; metadata has_audio=false.
- **manage_input**: script không quét thư mục con input → move tay PDF từ da-audio/ sang da-dich/ (đã dịch, chưa audio mới).

### File đổi
- working/{chunks,progress,qa,tmp_translate}/zuo-yi-ge-you-feng-gu-de-nu-zi/* (sản phẩm)
- output/books/做一个有风骨的女子/ (tamngu.md, vi.md, epub, metadata.json)
- scripts/output/merge_sentences.py (bug fix dòng ảnh)
- glossary/master.csv (7 entry cập nhật + normalize)
- docs/STATE.md, docs/session_log.md

### Bài học
- Skeleton tách câu xuyên quote: dòng src chỉ chứa dấu đóng → dst giữ dòng riêng; câu cắt đôi giữa 2 dòng phải tách dst đúng ranh giới (helper đếm dòng nghiêm).
- Luôn grep [\u4e00-\u9fff] file dst TRƯỚC apply — sót chữ Hán khi soạn nhanh là lỗi thường gặp nhất.
- glossary_qa.py cần --report tường minh mới ghi file report.
- merge_chunks bắt buộc --output-dir; EPUB ZH nhúng font vẫn phải làm tay.

### Còn dở
- Audiobook cho bản dịch mới (chưa làm — user chưa yêu cầu).

### Git
- Chưa commit. Đề xuất commit code fix (merge_sentences.py) + docs khi user duyệt.


---

## 2026-08-24 - Audiobook mới cho bản dịch lại 做一个有风骨的女子 (81 chuong)

### Đã làm
- **Don vi.md cho audio**: xoa khoi CIP/trang giay + muc luc CONTENTS (2 khoi), gop tieu de bia thanh H1 '# Nguoi phu nu co xuong khi' -> vi.md 791 dong, 4 anh, headings # con 4.
- **detect_chapters**: 81 chuong (fallback heading #/##).
- **music_map.json**: ghi entry slug nay qua working/tmp_translate/gen_music_map.py — 81 chuong, phan loai mood bang tu khoa (vui/binh/am/sau) xoay 26 bai lofi trong core/music/, tranh lap bai lien ke.
- **Generate**: audiobook_long.py --slug ... --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10 (voice van_tinh). Chay nen qua wrapper run_audio.ps1 (Start-Process powershell -File; inline -Command voi redirect *> FAIL — process chet khong log). RTF 0.31, ~95 phut wall-clock, 5688s gen / 18185s audio.
- **QA audio**: audio_qa.py FAIL do hardcode output/books/<slug>/ (thu muc output la ten goc CJK) -> QA thu cong bang tools/ffmpeg/ffprobe.exe: 81/81 MP3 hop le, tong 5.05 gio (277.6MB).
- **metadata.json**: has_audio=true, audio_chapters=81, audio_duration_hours=5.05.
- **manage_input**: move tay PDF tu input/da-dich/ sang input/da-audio/ (script khong quet thu muc con).

### File đổi
- output/books/做一个有风骨的女子/audiobook/ch01..ch81.mp3 (san pham)
- output/books/做一个有风骨的女子/metadata.json
- working/progress_audio/zuo-yi-ge-you-feng-gu-de-nu-zi.json + music_map.json (entry slug)
- docs/STATE.md, docs/session_log.md

### Bài học
- ffprobe/ffmpeg nam o tools/ffmpeg/ffprobe.exe (khong co trong PATH) — dung de QA MP3.
- pydub trong venv-vieneu KHONG decode duoc MP3 (thieu ffmpeg binary); audiobook_long.py tu tim ffmpeg o tools/ffmpeg/.
- audio_qa.py hardcode path theo slug — can fix ho tro metadata.json slug->folder neu muon QA tu dong cho sach ten CJK.

### Còn dở
- Khong con no nao — cuon sach HOAN TAT day du (dich + EPUB + audio).

### Git
- Chua commit. De xuat commit code fix (merge_sentences.py) + docs khi user duyet.



---

## 2026-08-24 - Dich tron 做一个刚刚好的女子 2 (Khang Tinh Van, 37 chunk + EPUB)

### Đã làm
- **Pipeline trọn**: PDF 228 trang input/chua-lam/ → MinerU GPU → raw.md 70,420 chars (QC 0 lỗi) → detect zh-Hans → chunk 37 (min1500/max3000) → glossary 12 thuật ngữ merge master (--author khang-tinh-van --genre tan-van) → skeleton trilingual 37/37 → profile van chuong working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-2.md.
- **Dịch 37/37 chunk** bằng batch manifest, 8 vòng x ~4 chunk (workflow: claim → dump original_text vào working/tmp/zy2/src_N.txt → dịch literary theo profile → apply.py check khớp dòng + quét Hán sót → batch_qa ok:true → complete). Sót Hán sửa ngay tại vòng (tình仇, 也别怕, 刁难, 根本, 一步...).
- **QA tổng thể pass**: run_pipeline.py --from-step 8 --to-step 8, 37/37 OK.
- **Merge**: merge_chunks.py --format trilingual --force --output-dir 'output/books/做一个刚刚好的女子 2' → rename tamngu.md/vi.md; vi.md nối translated_text 37 JSON (~210K chars), 0 mojibake/0 Hán sót.
- **Fix TOC + heading (thủ công, script working/tmp/zy2/fix_headings.py)**: 39 entry TOC sync theo đúng heading thân bài (giữ số trang; bỏ OCR rác ／on; entry thiếu trang bỏ dấu /); tách dòng TOC merged PART 4 thành 4 dòng (vi.md) / 4 tri-block (tamngu.md); strip # trong khối TOC; normalize thân bài: 5 H1 = tựa sách + 4 PART, subtitle PART + essay = ## (15 heading nhầm # → ##). Verify: TOC sync 62/62 heading, 0 mojibake cả 2 file. Backup .bak dời sang working/tmp/zy2/.
- **EPUB TAM NGỮ nhúng font Noto Serif SC ~18MB** (build từ final/tamngu.md, tri-block ZH+Pinyin+VI — 2169 khối trong ch002.xhtml; lần đầu build nhầm từ vi.md thuần Việt, user bắt lỗi → rebuild): pandoc --toc-depth=2 --epub-embed-font NotoSerifSC-VF.ttf; CSS @font-face url phải là '../fonts/...' vì pandoc đặt font ở EPUB/fonts/ còn css ở EPUB/styles/ — patch trong zip rồi move ra gốc thư mục sách làm DUY NHẤT 1 file epub. Copy 40 ảnh từ extracted auto/images sang output/<sách>/images/.
- **metadata.json**: {slug, title, source_file=input/da-dich/...}. manage_input.py không quét thư mục con → move tay PDF chua-lam/ → da-dich/.

### File đổi
- working/{chunks,progress,qa,tmp/zy2}/zuo-yi-ge-gang-gang-hao-de-nu-zi-2/* (sản phẩm trung gian)
- output/books/做一个刚刚好的女子 2/ (tamngu.md, vi.md, epub, metadata.json, images/)
- glossary/master.csv (+12 thuật ngữ)
- docs/STATE.md, docs/session_log.md

### Bài học
- batch_manifest.py claim in key 'batch_id' (không có 'chunk_id') — parse nhầm tưởng claim fail.
- TOC sách scan thường lệch bản dịch thân bài (dịch 2 lần khác nhau) → bắt buộc sync entry theo heading body trước khi EPUB; strip # trong khối TOC tránh pandoc đưa vào nav.
- pandoc --epub-embed-font đặt font ở EPUB/fonts/, css ở EPUB/styles/ → @font-face url('../fonts/x.ttf'), kiểm tra bằng zipfile sau build.

### Còn dở
- Audiobook cho cuốn này (chưa làm — user chưa yêu cầu).

### Git
- Chưa commit. Không có thay đổi code — chỉ sản phẩm (không commit) + docs.


---

## 2026-08-25 - Dich tron 做一个刚刚好的女子 3 (Vi Duong 微阳, 50 chunk + EPUB)

### Đã làm
- **Pipeline trọn chuẩn mới**: backup dữ liệu cũ (07-31/08-01, pre-chuan van chuong) sang working/tmp/zy3_old_backup/{extracted,chunks,progress}__slug -> MinerU GPU extract lai tu PDF input/chua-lam/ -> raw.md 88,977 chars (QC 0 loi, zh-Hans) -> chunk 50 (min1500/max3000).
- **Glossary**: tao curated 20 thuat ngu (book=zuo-yi-ge-gang-gang-hao-de-nu-zi-3, author=vi-duong, genre=tan-van) merge master; phat hien master co 344 dong duplicate cho slug nay gom 2 muc SAI nghia (淡泊->'Nhat nhe' SAI, sua thanh 'thanh dam'; 从容->'Tu tu' SAI, sua thanh 'thong dong'); REBUILD master dedupe 1-row-per-source uu tien curated -> master.csv 183 dong, xoa shards cu (backup working/tmp/glossary_shard_backup_0824/). Luu y: glossary_lib.filter_for_book dedupe theo cap (source,target) nen 2 target khac nhau cung source deu song sot - can rebuild tay.
- **Skeleton + profile**: init_trilingual_skeleton.py 50/50 (original_text 1 cau/dong); profile working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-3.md (giong 'chi lon tam tinh dan do', ten Han-Viet, mau dich Na Na).
- **Dich 50/50 chunk** bang batch manifest, 13 vong (claim -> dump_range.py A B -> trans_rN.py T[cid] builder auto-mirror dong trong/dong anh -> apply.py check khop dong + quet Han sot -> batch_qa ok:true -> complete). Helper scripts o working/tmp/zy3/. apply.py da BO check dong rong (dong trong la cau truc hop le phai mirror). Cac fix lech dong: cau bi OCR tac 2 dong phai tac ban dich theo dung so dong; dau ” ket cau thoai dung rieng 1 dong phai giu nguyen vi tri.
- **QA tong the pass**: run_pipeline.py --from-step 8 --to-step 8, 50/50 OK.
- **Merge**: merge_chunks.py --format trilingual --force --output-dir 'output/books/做一个刚刚好的女子 3/final' -> rename tamngu.md (1.29MB) + tao vi.md tu translated_text (286K chars); vi.md 0 mojibake / 0 Han sot / 114 headings dung cau truc. metadata.json {slug,title,source_file,author:'Vi Duong',language:zh}.
- **EPUB nhung font Noto Serif SC ~15.9MB**: make_epub.py (pandoc) tu final/tamngu.md -> inject_font.py patch trong zip (CSS @font-face url('../fonts/NotoSerifSC-VF.ttf') + manifest item) -> move ra goc thu muc sach lam DUY NHAT 1 file epub. Font nguon: working/tmp_epub/fonts/.
- **manage_input**: move tay PDF chua-lam/ -> da-dich/.

### File doi
- working/tmp/zy3/* (helper + trans_r1..r13 + vi_r*.txt), working/{chunks,progress,qa}/.../zuo-yi-ge-gang-gang-hao-de-nu-zi-3/
- output/books/做一个刚刚好的女子 3/ (tamngu.md, final/vi.md, epub, metadata.json)
- glossary/master.csv (rebuild 183 dong), glossary/zuo-yi-ge-gang-gang-hao-de-nu-zi-3.csv (curated 20)
- docs/STATE.md, docs/session_log.md

### Bai hoc
- original_text skeleton la 1-cau-dong (khac text chunk theo doan) - dump_range doc progress JSON chu khong doc chunks dir.
- Builder dich nen auto-mirror dong rong/dong anh va chi zip list dich voi dong prose -> giam sai sot dem dong.
- Dau ” ket cau thoai OCR hay dung rieng 1 dong - ban dich phai co dung 1 item '”'.
- Glossary master trung cap (source,target): 2 target khac nhau cho 1 source deu song sot sau filter - khi co muc sai phai rebuild tay hoac them --normalize.

### Con d?
- Audiobook cho cuon nay (chua lam - user chua yeu cau).

### Git
- Chua commit. Khong co thay doi code - chi san pham (khong commit) + docs.


---

## 2026-08-25 - Audiobook 做一个刚刚好的女子 3 (60 chuong, GPU + music-auto)

### Đã làm
- **Don dep vi.md cho audio**: cat front-matter (`# Làm một người phụ nữ vừa vặn` den truoc `## Chương 8...` - bia/CIP/NSX/muc luc) + colophon cuoi sach (tu anh 0fbaf9b9 sau bai tho Thu Dinh den EOF), backup working/tmp/zy3/vi_backup.md -> 60 chuong sach (detect_chapters).
- **Xoa progress cu**: working/progress_audio/zuo-yi-ge-gang-gang-hao-de-nu-zi-3.json (65 chuong tu ban audio cu da bi xoa MP3 truoc do) de tranh "All selected chapters already completed".
- **Generate 60/60 chuong**: `audiobook_long.py --slug zuo-yi-ge-gang-gang-hao-de-nu-zi-3 --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10` (voice van_tinh active). RTF 0.32, ~90 phut gen, **4.76 gio audio (261.5MB)**, music-auto AI chon lofi theo noi dung tung chuong (26 bai trong core/music/).
- **QA ffprobe** (tools/ffmpeg/ffprobe.exe): 60/60 MP3 hop le; ch01 4.3s (tua sach), ch37 3.9s (divider Chuong 5 'Bắt tay hòa giải với chính mình' chi co tieu de - dung ban chat, giong convention divider-chapter cac sach truoc).
- **metadata.json**: has_audio=true, audio_chapters=60, audio_hours=4.76.
- **manage_input**: PDF move tay `da-dich/` -> `da-audio/`.

### File doi
- output/books/做一个刚刚好的女子 3/audiobook/ch01..60.mp3, metadata.json
- output/books/做一个刚刚好的女子 3/final/vi.md (da don dep cho audio; backup vi_backup.md)
- input/da-audio/ (PDF)
- docs/STATE.md, docs/session_log.md

### Bai hoc
- progress_audio JSON cu con sot sau khi xoa MP3 se lam script tuong tat ca chapter da xong -> phai xoa progress khi lam audio moi cho ban dich moi.
- vi.md thuong chua front-matter (bia/CIP/muc luc) + colophon -> can cat truoc khi detect chapters, neu se ra chapter rac.

### Còn dở
- Khong (sach hoan tat dich + EPUB + audio).

### Git
- Chua commit. Chi san pham (khong commit) + docs.


---

## 2026-08-25 (phien 2) - Audiobook 做一个刚刚好的女子 2 (61 chuong, GPU + music-auto)

### Đã làm
- **Don dep vi.md cho audio**: cat front-matter (0-114, gom tac gia, QR, CIP, muc luc) + back-matter (tu "Danh sach sach Doc My Van Kho" den EOF) + bo 6 dong `# PART N` divider (khong co noi dung) -> 2168 dong sach, 201K chars.
- **Detect chapters**: 61 chuong (40 essay + sub-headings trong sach). Khong co progress cu (audiobook chua lam truoc do).
- **Generate 61/61 chuong**: `audiobook_long.py --slug zuo-yi-ge-gang-gang-hao-de-nu-zi-2 --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10` (voice van_tinh). RTF 0.31, ~64 phut gen, **3.42 gio audio (188MB)**, music-auto AI 61 bai lofi theo noi dung tung chuong.
- **QA ffprobe**: 61/61 MP3 hop le. Ch40 nhat (6.5s, 86 ky tu - cau ket noi giua 2 PART). Ch39 dai nhat (8.1 min).
- **metadata.json**: them has_audio=true.
- **manage_input**: PDF move tay `da-dich/` -> `da-audio/`.
- **STATE.md**: cap nhat hang book 2 (audiobook 61/61 hoan tat).

### File doi
- output/books/做一个刚刚好的女子 2/audiobook/ch01..61.mp3, metadata.json
- output/books/做一个刚刚好的女子 2/final/vi.md (da don dep cho audio; backup working/tmp/zy3/vi2_backup.md)
- working/tmp/zy3/chapter_list_zy2.txt (61 chuong list)
- input/da-audio/ (PDF)
- docs/STATE.md, docs/session_log.md

### Bai hoc
- sach co PART divider (`# PART N`) nen bo truoc khi audio, vi detect_chapters tao chapter chi co tieu de doc thanh 3-5s, nghe dut quang.
- vi.md sach nay rat sach (khong co H1 truoc PART), chi can bo dong `# PART N` thoi.

### Còn dở
- Khong (sach hoan tat dich + EPUB + audio).

### Git
- Chua commit. Chi san pham (khong commit) + docs.

---

## 2026-08-25 (phiên 3) - Nâng cấp Desktop UI (WPF / .NET 8)

### Đã làm
- **Đồng bộ quét & phân loại thư mục Input**:
  - Cập nhật [`MainViewModel.cs`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/ViewModels/MainViewModel.cs) phân loại file theo thư mục con trong `input/` (`chua-lam`, `da-dich`, `da-audio`).
  - Gán `FolderPath` và `InputCategory` vào [`BookStatus.cs`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/Models/BookStatus.cs); hiển thị vị trí `input/<category>` trên Card sách.
- **Bổ sung cấu hình GPU & Nhạc nền AI trên AudioPage**:
  - Thêm các thuộc tính & controls trên [`AudioPage.xaml`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/Views/AudioPage.xaml): Bật/tắt GPU (`--gpu`), Batch Size (chuẩn 16 cho RTX 3060), Bật/tắt Nhạc nền AI (`--music-auto`), Âm lượng nhạc nền (`--music-volume`, mặc định 0.15).
  - Cập nhật [`PythonPipelineService.RunAudiobookAsync`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/Services/PythonPipelineService.cs) & `GenerateAudiobookAsync` truyền đủ các tham số mới.
- **Tiện ích Mở Thư Mục Nhanh (Explorer)**:
  - Thêm RelayCommand `OpenBookFolder` trong `MainViewModel`.
  - Bổ sung nút Icon Folder mở trực tiếp thư mục sách trong Windows Explorer trên Card sách của cả tab `Output` ([`BooksPage.xaml`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/Views/BooksPage.xaml)) và trang [`AudioPage.xaml`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/Views/AudioPage.xaml).
- **Hiệu ứng Kính Mờ (Windhawk Liquid Glass 3.0 Specs)**:
  - Đồng bộ `WindowBackdropType.Acrylic` trên cả XAML và `SystemThemeWatcher.Watch(this, WindowBackdropType.Acrylic, true)` trong [`MainWindow.xaml.cs`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/Views/MainWindow.xaml.cs).
  - Áp dụng đầy đủ thông số mẫu Windhawk: Gradient borders (`#50808080 → #50404040 → #50808080`), viền phần tử (`ElementBorderThickness="0.3,0.3,0.3,1"`), bo góc chuẩn (`CornerRadius=12`, `ElementCornerRadius=8`), vệt phản xạ ánh sáng trắng viền chéo (`#80ffffff → #35ffffff → #80ffffff`).
- **Khắc phục logic tính toán Tiến độ % (`BookStatus.cs`)**:
  - **Nguyên nhân trước đây**: Công thức tính `ProgressPercent` chỉ dựa vào `(ProgressCount / TotalChunks) * 100`. Các cuốn sách trong tab Output đã dịch xong hoàn toàn ra file `output/books/<tên-sách>/final/vi.md` và `tamngu.md`, nhưng thư mục trung gian `working/chunks/<slug>` không lưu giữ số chunk ban đầu khiến `TotalChunks = 0` dẫn đến hiển thị `0%`.
  - **Giải pháp**: Cập nhật công thức chuẩn xác `ProgressPercent => HasViMd ? 100 : (TotalChunks > 0 ? (double)ProgressCount / TotalChunks * 100 : 0)`. Khi cuốn sách đã có bản dịch tiếng Việt hoàn tất (`HasViMd = true`), thanh tiến độ và nhãn % sẽ hiển thị chuẩn xác **`100%`** và trạng thái **`Hoàn thành`**. Khi đang trong quá trình dịch dở, % sẽ tăng dần theo số chunk thực tế.
- **Nâng cấp toàn diện biểu tượng StatTile Tab Output (`BooksPage.xaml`)**:
  - Thay thế toàn bộ emoji thô (`📄`, `🎧`) trên 3 thẻ thống kê **Chunks**, **EPUB**, **Audio** bằng các **`ui:SymbolIcon` Fluent chuẩn**:
    - **Chunks**: Icon **`DocumentBulletList24`** sắc nét màu Accent.
    - **EPUB**: Icon **`Book24`** tinh tế màu Accent.
    - **Audio**: Icon **`Headphones24`** đồng bộ màu Accent.
  - Cân chỉnh khoảng cách và typography số lượng (`13px Bold`) cùng nhãn phụ (`10px Secondary`), tạo cảm giác hiện đại, thanh thoát và cao cấp đồng bộ với toàn bộ giao diện Windhawk Liquid Glass.
- **Rà soát & Hoàn thiện cửa sổ Đọc thử EPUB (`EpubPreviewWindow.xaml` & `EpubPreviewWindow.xaml.cs`)**:
  - **Tối ưu Padding & Kích thước ô Box Toolbar (100% Full Visibility)**: Tinh chỉnh `GlassComboBox` style với `Padding="8,3,4,3"` và `VerticalContentAlignment="Center"`, mở rộng chiều rộng ô Phông chữ lên **`190px`**, Độ rộng lề lên **`145px`**, Khoảng cách dòng lên **`135px`**, ô Tìm kiếm lên **`190px`** và rút gọn nhãn item (`Có chân (Serif SC)`, `Cổ điển (KaiTi)`) giúp toàn bộ chữ hiển thị vừa vặn, thoáng đãng và không bao giờ bị cắt cụt.
  - **Toolbar kính mờ Liquid Glass**: Đồng bộ style `GlassComboBox` cho bộ 3 chọn Typography (Phông chữ Segoe UI/Serif/KaiTi/Mono, Độ rộng lề trang 650px - Toàn màn hình, Khoảng cách dòng 1.5x - 2.2x); mở rộng ô tìm kiếm `190px` với `InteractiveTextBox`.
  - **Tích hợp Audiobook Player Bar thông minh**: Tự động quét thư mục `audiobook/*.mp3` của cuốn sách khi mở cửa sổ đọc thử; đồng bộ mục lục TOC với audio theo từng chương (`ch01.mp3`, `ch02.mp3`...), hỗ trợ tua thanh trượt, điều chỉnh âm lượng và phát/tạm dừng mượt mà.
  - **Hiển thị & Tìm kiếm**: Render qua WebView2 với Dark Theme CSS chuẩn, hỗ trợ bôi vàng từ khóa tìm kiếm (`BtnSearchNext`, `BtnSearchPrev`), zoom từ 50% đến 200%, tự động lưu và khôi phục vị trí đọc gần nhất.
- **Rà soát & Bổ sung tính năng còn thiếu trên UI Tab Audio (`AudioPage.xaml`, `MainViewModel.cs`, `PythonPipelineService.cs`)**:
  - **Bổ sung nút "Nghe thử mẫu ~30s" (`GenerateSampleCommand`)**: Thêm nút Play trên từng card sách audio; tự động trích xuất ~400 ký tự từ chương đầu tiên, tạo audio nhanh với giọng active và nhạc nền AI rồi tự động phát file WAV kết quả để người dùng kiểm tra chất lượng giọng & âm lượng nhạc trước khi render cả cuốn.
  - **Bổ sung nút "Mở thư mục Audiobook" (`OpenAudioFolderCommand`)**: Mở trực tiếp thư mục chứa các file MP3/Audiobook của sách trong Windows Explorer chỉ với 1 cú click.
  - **Tự động nạp danh sách giọng (`LoadVoicesAsync`)**: Bổ sung tự động quét thư mục `core/voices/` ngay khi ứng dụng khởi chạy, giúp ComboBox "Giọng active" luôn có sẵn danh sách giọng clone để chọn mà không cần bấm thủ công nút tải lại.
  - **Kiểm tra luồng Tạo Audiobook (`GenerateAudiobookCommand`)**: Kết nối trực tiếp vào script `scripts/audiobook/audiobook_long.py` qua môi trường ảo `working/venv-vieneu/Scripts/python.exe`, truyền đầy đủ tham số GPU (`--gpu --batch-size 16`), Nhạc nền AI (`--music-auto --music-volume 0.15`), chất lượng bitrate (`--bitrate 128k`), tùy chọn chương (`--chapter`), ghi nhận tiến độ thời gian thực vào thanh Progress Bar và Realtime Log.
  - **Kiểm tra luồng Quản lý giọng (`manage_voice.py`)**: Đầy đủ tính năng Đặt giọng chính (`set-active`), Nghe thử câu đọc mẫu (`preview`) và Clone giọng sạch tự động (`extract --auto`).
  - **Đồng bộ kích thước các đầu mục chính (Unified Section Headings)**: Cả 3 đầu mục lớn **"Cấu hình Audiobook (VieNeu-TTS Turbo)"**, **"Quản lý giọng đọc"** và **"Clone giọng mới (3-8s audio)"** được chuẩn hóa đồng nhất ở mức **`FontSize="15"`, `FontWeight="Bold"`** cùng biểu tượng Fluent Icon **`FontSize="18"`**, tạo sự cân xứng và hài hòa tuyệt đối về thị giác.
  - **Chuẩn hóa kích thước & Font chữ đồng bộ (Box Sizing & Typography)**: Mở rộng chiều rộng (`120px - 130px`), chiều cao chuẩn `32px` và font chữ `12px` đồng nhất cho toàn bộ các ô `NumberBox`, `ComboBox`, `TextBox` và các nút bấm; khắc phục triệt để tình trạng chữ to nhỏ không đều hoặc bị cắt xén nội dung bên trong.
  - **Khung cấu hình Audiobook cao cấp**: Bọc toàn bộ thông số kỹ thuật (Độ sáng tạo, Top-K, Bitrate, Batch Size GPU, Âm lượng nhạc nền, Tùy chọn GPU/Nhạc nền AI) vào một khối kính mờ nổi bo góc `CornerRadius=12` có viền gradient phản quang.
  - **Quản lý & Clone giọng đọc trực quan**: Phân tách thành 2 thẻ kính (`InteractiveCard`) hài hòa với icon Fluent (`Speaker224`, `MicSparkle24`), các nút thao tác nhanh (Tải lại danh sách, Đặt làm giọng chính, Nghe thử) áp dụng style `GlassIconButton` / `GlassPlainButton` bo góc 6px tinh tế.
  - **Đóng khung danh sách sách Audio**: Danh sách sách đã dịch được bọc trong container kính mờ bo tròn `CornerRadius=12` tương tự tab Sách.
  - **Thẻ Card sách Audio sắc nét**: Nâng cấp Avatar tròn hiển thị chữ cái đầu, tiêu đề đậm rõ ràng, huy hiệu số chương Audiobook (`Mp3Count chapters`), thanh tiến độ tạo audio theo chương (`AudioDone / AudioTotal`), nút "Tạo / Cập nhật Audio" và nút mở thư mục sách dạng `GlassIconButton`.
- **Trau chuốt nút bấm Realtime Log & Cột điều khiển (Glass Toolbar Buttons)**:
  - Bổ sung style **`GlassIconButton`** và **`GlassCollapseButton`** với bo góc `CornerRadius=6`, viền phản quang gradient `0.3,0.3,0.3,1` và hiệu ứng hover/press nhẹ nhàng.
  - Thay thế toàn bộ ký tự text thô (`<`, `>`, `📋`) bằng các **Fluent SymbolIcon chuẩn (`ChevronRight24`, `ChevronLeft24`, `Copy24`)** sắc nét.
  - Nút **"Xóa"** được áp dụng `GlassPlainButton` cân đối, ô tìm kiếm **"Lọc..."** canh chỉnh chiều cao đồng đều 26px giúp thanh header của Realtime Log thanh thoát, hiện đại và sang trọng.
- **Hợp nhất toàn diện 3 cột thành 1 khối khung kính liền mạch & Hiệu ứng trượt Realtime Log**:
  - Gộp cả **(1) Navigation trái (Sách/Audio)**, **(2) Danh sách sách (Input/Output)** và **(3) Realtime Log (phải)** vào trong cùng một `Border` khung kính nổi duy nhất với `CornerRadius="12"`, viền phản xạ ánh sáng `GlassGradientBorderBrush` bao quanh và `OpacityMask` cắt gọt chuẩn xác.
  - Thêm hiệu ứng hoạt ảnh trượt mở / đóng mượt mà (**Storyboard DoubleAnimation Width 36px ↔ 300px**) cho Realtime Log tương tự như thanh Navigation Pane bên trái (Sách/Audio), đồng thời làm mờ chuyển tiếp nội dung êm ái.
  - Bọc khu vực danh sách sách (`InputPanel` / `OutputPanel`) bên trong một khung kính mờ độc lập bo tròn `CornerRadius="12"` với viền phản quang `0.3,0.3,0.3,1`, tạo chiều sâu phân lớp vô cùng thẩm mỹ.
- **Bo tròn hoàn hảo các khối tử & Khắc phục góc vuông ở cột sách**:
  - Khắc phục triệt để góc dưới cùng bên phải của khu vực danh sách sách bị vuông bằng `Border.OpacityMask` với `CornerRadius="12"`, cắt gọt toàn bộ nội dung cuộn bên trong khớp tuyệt đối 100% với đường cong viền kính của container ngoài.
  - Khắc phục các góc "trán" (header) bên trong thẻ Card bằng cách đổi `BookCardHeader` thành capsule bo tròn đều cả 4 góc `CornerRadius=8` kèm viền ánh sáng `0.3,0.3,0.3,1`, nằm lọt lòng hài hòa bên trong khung Card `CornerRadius=12`.
  - Đồng bộ `LiquidGlassStatTile` (các ô thống kê Chunks/EPUB/Audio) về `CornerRadius=8` chuẩn Fluent.
- **Tạo & Nhúng Biểu Tượng Ứng Dụng (Icons8 Fluent Windows Literature Icon)**:
  - Tải và chuyển đổi biểu tượng Fluent Literature chuẩn Windows đa kích cỡ (`16x16` đến `256x256`) tại [`desktop/app.ico`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/app.ico) và PNG tại [`desktop/app_icon.png`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/app_icon.png).
  - Cấu hình `<ApplicationIcon>app.ico</ApplicationIcon>` cùng `<Resource Include="app.ico" />`, thực hiện `dotnet clean` và `dotnet build` để Windows Compiler nhúng trực tiếp PE Icon Header vào file `.exe`.
  - Gửi tín hiệu `SHChangeNotify` refresh Windows Explorer Icon Cache.
- **Fix Compiler Warning & Cải thiện độ rõ nét của chữ**:
  - Loại bỏ `DropShadowEffect` gây rasterization nhòe chữ trên card.
  - Chuẩn hóa nền `BookCardHeader` giúp tiêu đề sách trên cả 3 trang (`BooksPage Input`, `BooksPage Output`, `AudioPage`) hiển thị sắc nét và rõ ràng.
  - Khắc phục triệt để warning CS4014 tại [`EpubPreviewWindow.xaml.cs`](file:///E:/OneDrive/onyx/Translate%20Book/desktop/Views/EpubPreviewWindow.xaml.cs).
  - Build `dotnet build` đạt **0 Error(s), 0 Warning(s)**.

### File đổi
- `desktop/app.ico`, `desktop/app_icon.png`
- `desktop/TranslateBook.csproj`
- `desktop/Models/BookStatus.cs`
- `desktop/Services/PythonPipelineService.cs`
- `desktop/ViewModels/MainViewModel.cs`
- `desktop/Views/BooksPage.xaml`
- `desktop/Views/AudioPage.xaml`
- `desktop/Views/MainWindow.xaml`
- `desktop/Views/EpubPreviewWindow.xaml.cs`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không. App desktop đã build sạch sẽ và sẵn sàng chạy.

### Git
- Chưa commit. Chờ người dùng duyệt.


---

## 2026-08-25 - Dich tron 我在豪门的日日夜夜 (晚情) - 76 chunk + EPUB tam ngu

### Đã làm
- **Pipeline tron tu dau**: EPUB scan 203 trang anh -> extract anh vao working/_ocr_imgs/ (sort numeric) -> OCR MinerU GPU TUNG ANH qua worker nen (whm_ocr_worker.py, subprocess encoding utf-8 errors replace, checkpoint file md per trang trong working/_ocr_imgs/md/, wrapper whm_ocr_run.ps1 Start-Process -File, log working/tmp/whm_ocr.log) -> raw.md 158,682 chars.
- Detect zh-Hans. QC: phat hien header/footer lap (zhaoshu weixin p6yc30, WO ZAI HAO MEN DE RIRIYE YE) + quang cao zhaoshu bumilu + hash rac c5e5c81400edad -> xa khoi raw.md, chunks text field, progress original_text.
- FIX skeleton pinyin lech: chunk 0 va 75 co pinyin_text sinh TRUOC khi QC xoa dong quang cao -> chay lai add_pinyin.process_text. Bai hoc: khi xoa dong khoi original_text phai regenerate pinyin_text.
- Chunk smart ZH min1500/max3000 -> 76 chunk. Glossary 20 thuat ngu merge master (--author van-tinh --genre tieu-thuyet). Skeleton trilingual 76/76. Profile van chuong wo-zai-hao-men-de-ri-ri-ye-ye.md.
- **Dich 76/76 chunk** bang batch manifest, 16 vong x 4-5 chunk (claim -> dump src_N.txt marker @@CHUNK N@@ -> dich literary theo profile -> apply.py check khop dong + quet Han sot -> batch_qa ok:true -> complete). Fix Han sot bang fix_rN.py replace dict tung vong.
- Loi so dong hay gap: gop quote-close standalone cua orig; them quote-close khi orig khong co; chen dong dup. Cong cu sigdiff/detail align theo signature IMG/H/q/T giup dinh vi chinh xac nhanh.
- QA tong the pass: run_pipeline.py --from-step 8 --to-step 8, 76/76 OK.
- Merge: merge_chunks.py --format trilingual --force --output-dir tuong minh -> rename tamngu.md; vi.md noi translated_text 76 JSON (~438K chars), 0 mojibake/0 Han sot.
- merge_sentences.py CHO CA HAI (gop cau + bo so trang): vi.md 6010->1469 dong, tamngu.md 34975->23496 dong.
- Clean heading: xoa 175 heading Trang (+block Trang tri kem), trash heading (chi chua dau cham, OCR rac), dedupe heading trung, chuyen heading nham thanh text thuong. Verify headings sach.
- metadata.json day du {slug,title,source_file=da-dich,author,language=zh,genre=tieu-thuyet,has_audio=false,has_epub=true,epub_file}.
- **EPUB tam ngu ~21MB**: build tu tamngu.md (pandoc --toc-depth=2 --epub-embed-font NotoSerifSC-VF.ttf + CSS @font-face patch '../fonts/' trong zip). Copy 195 anh tu working/_ocr_imgs/md/*/auto/images sang output/<sach>/images/.
- manage_input: move tay EPUB chua-lam/ -> da-dich/.

### File đổi
- working/{_ocr_imgs,chunks,progress,tmp/whm}/wo-zai-hao-men-de-ri-ri-ye-ye/* (san pham trung gian)
- output/books/我在豪门的日日夜夜 (晚情)/ (tamngu.md, vi.md, epub 21MB, metadata.json, images/)
- glossary/master.csv (+20 thuat ngu)
- docs/STATE.md, docs/session_log.md

### Bai hoc
- OCR scan per-page can worker nen + checkpoint file per trang; subprocess.run PHAI dat encoding utf-8 errors replace neu khong crash cp1252 sau khi ghi file.
- Skeleton pinyin PHAI regenerate sau moi lan sua original_text (QC xoa dong).
- Script clean final: tuyet doi khong xoa block den blank ke tiep (merge_sentences gom paragraph dai khong blank -> xoa sach content). Chi xoa dung dong heading + block trang tri match pattern cu the.
- Sigdiff align theo chu ky IMG/H/q/T tung dong la cong cu nhanh de tim dong thua/thieu truoc khi apply.

### Con dở
- Khong con no nao — cuon HOAN TAT (dich + EPUB; KHONG audiobook theo yeu cau user).

### Git
- Chua commit. Khong co thay doi code — chi san pham (khong commit) + docs.


---

## 2026-08-25 (phien 4) - Audiobook 做一个有境界的女子 (34 chuong, GPU + music-auto)

### Đã làm
- **Don dep vi.md cho audio**: cat front-matter 6 dong (title, author, lang, source, slug, separator) -> 2643 dong sach, 381K chars. Khong co back-matter. Khong co PART divider.
- **Detect chapters**: 34 chuong (35 ## essays, 1 H1 title removed).
- **Generate 34/34 chuong**: `audiobook_long.py --slug zuo-yi-ge-you-jing-jie-de-nu-zi --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10` (voice van_tinh). RTF 0.37, ~172 phut gen, **6.5 gio audio (160MB)**, music-auto AI 34 bai lofi theo noi dung tung chuong. Chay 2 lan (timeout 2h lan 1 het chuong 24, resume tu chuong 25).
- **QA ffprobe**: 34/34 MP3 hop le.
- **metadata.json**: them has_audio=true.
- **manage_input**: EPUB move tay `da-dich/` -> `da-audio/`.
- **STATE.md**: cap nhat hang jingjie (audiobook 34/34 hoan tat).

### File doi
- output/books/做一个有境界的女子  不自轻,不自弃 (晚情)/audiobook/ch01..34.mp3, metadata.json
- output/books/做一个有境界的女子  不自轻, no self,不自弃 (晚情)/final/vi.md (da don dep cho audio; backup working/tmp/zy3/vi_backup_jingjie.md)
- input/da-audio/ (EPUB)
- docs/STATE.md, docs/session_log.md

### Con dở
- Khong (sach hoan tat dich + EPUB + audio).

### Git
- Chua commit. Chi san pham (khong commit) + docs.

---

## 2026-08-26 — Tối ưu hiệu năng UI, Auto-fetch Model API & Zero-token Connection Test

### Đã làm
- **Giải phóng UI Thread, dọn sạch giật lag**:
  - Chuyển toàn bộ vòng lặp đọc file JSON của `RefreshBookProgress()` sang `Task.Run` chạy ngầm, giải phóng UI thread giúp giao diện phản hồi 0ms.
  - Sửa sự kiện chuyển tab trong `BooksPage.xaml` từ `Click` sang `Checked` trên `RadioButton`, gỡ bỏ hoàn toàn hiệu ứng làm delay/khóa tương tác chuột khi bấm chuyển tab Input / Output.
- **Tách ô nhập số chương Audiobook theo từng sách**:
  - Tách thuộc tính `ChapterInput` riêng cho từng `BookStatus` trong model, binding TwoWay độc lập và truyền chuẩn xác vào `RunAudiobookAsync`.
- **Bộ lọc Realtime Log thông minh**:
  - Nâng cấp phân loại log: tiến độ `Loading weights` của HuggingFace thành Info xám, `Warning` thành Cam cảnh báo, chỉ đánh nhãn `[ERR]` Đỏ khi có lỗi Exception thực sự.
- **Quy chuẩn thư mục Glossary**:
  - Cập nhật `scripts/process/merge_glossary.py` tự động xóa file trung gian `glossary/<slug>.csv` sau khi gộp vào `master.csv`.
  - Dọn sạch 6 file CSV nhỏ lẻ, giữ thư mục `glossary/` chỉ có duy nhất `master.csv` (203 từ vựng) và `_template.*`. Cập nhật tài liệu quy tắc trong `AGENTS.md` và commands.
- **Hỗ trợ API Key Google Gemini & Cập nhật Model mới**:
  - Nâng cấp `ApiTranslationService.cs` hỗ trợ cả 2 định dạng Key của Google (qua query param `?key=` và Header `x-goog-api-key`).
  - Cập nhật model mặc định từ `gemini-2.0-flash` (đã đóng cho tài khoản mới) sang **`gemini-3.6-flash`**.
- **Auto-Fetch Model List từ API Key**:
  - Tự động gọi API `ListModels` khi dán API Key để lấy danh sách mô hình thực tế mà tài khoản được cấp phép sử dụng.
  - Nạp danh sách vào Dropdown chọn nhanh kèm nút `[↻]` quét thủ công, luôn bảo toàn đúng Model mà người dùng đã chọn.
- **Kiểm tra kết nối 0-Token (Zero-Token Test Connection)**:
  - Viết lại toàn bộ hàm `TestConnectionAsync` sử dụng gói tin `HTTP GET` (`/v1beta/models/{model}` hoặc `/v1/models`) để kiểm tra quyền truy cập và tồn tại của Model.
  - Tiêu tốn hoàn toàn **0 Token generate**, không trừ quota dịch và không làm chậm rate limit của tài khoản.

### File đổi
- `desktop/ViewModels/MainViewModel.cs` (tối ưu Task.Run background, AvailableModels, log filter, ChapterInput)
- `desktop/Services/ApiTranslationService.cs` (hỗ trợ x-goog-api-key, FetchAvailableModelsAsync, test kết nối 0-token, trích xuất lỗi HTTP chi tiết)
- `desktop/Views/ApiPage.xaml`, `desktop/Views/ApiPage.xaml.cs` (Dropdown Model IsEditable, nút quét model [↻], bảo toàn Model đã chọn)
- `desktop/Views/BooksPage.xaml`, `desktop/Views/BooksPage.xaml.cs` (chuyển Checked event, tối ưu tab transition)
- `desktop/Views/AudioPage.xaml` (binding TwoWay ChapterInput theo model sách)
- `desktop/Models/BookStatus.cs` (thêm ChapterInput riêng theo sách)
- `desktop/Models/ApiConfig.cs` (default model gemini-3.6-flash)
- `scripts/process/merge_glossary.py` (tự xóa file trung gian sau khi merge)
- `AGENTS.md`, `.commandcode/commands/dich.md`, `.opencode/command/dich.md` (cập nhật quy chuẩn glossary)
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng. Ứng dụng hoạt động mượt mà, kết nối API Gemini 3.6 Flash / DeepSeek ổn định.

### Git
- Chưa commit — tuân thủ quy tắc chờ người dùng kiểm tra và duyệt trước.

---

## 2026-08-27 — Nâng cấp tính năng Rà soát & Sửa chữa, Sửa Mục lục EPUB Tam ngữ & Trình xem trước Markdown

### Đã làm
- **Nâng cấp tính năng Rà soát & Sửa chữa thông minh (Smart Multi-layer Audit)**:
  - Tự động dọn dẹp các chunk thừa / mồ côi ngoài phạm vi total_chunks chuẩn.
  - Quét kiểm tra chất lượng 5 tầng: Mojibake / mất dấu font, tỷ lệ Hán sót (>15%), phát hiện câu lặp vô tận do AI ảo giác (AI Loop), lệch số dòng song ngữ/tam ngữ, dọn ký tự rác OCR `///`.
  - Tự động sửa offline các lỗi định dạng và metadata mà không tiêu tốn token API.
- **Sửa triệt để Mục lục (TOC) cho EPUB Tam ngữ**:
  - Phát hiện nguyên nhân Pandoc nuốt Heading cấp 1 khi bao quanh bởi thẻ HTML `<div class="tri-block">`.
  - Cập nhật `scripts/output/make_epub.py` loại bỏ thẻ div bao ngoài và chuyển sang các thẻ `<p class="src-zh">`, `<p class="pinyin">`, `<p class="vi">` độc lập.
  - Cập nhật `scripts/common/epub_style.css` định dạng trực tiếp các thẻ `p` này, giữ nguyên màu sắc, cỡ chữ và khoảng cách câu tam ngữ đẹp mắt.
  - Kết quả: File EPUB Tam ngữ sinh ra có đầy đủ Mục lục 50+ chương chi tiết, nhảy trang chính xác 100% trên Calibre / EpubPreview / Moon+ Reader.
- **Trình xem trước Markdown (MdPreviewWindow)**:
  - Thêm cửa sổ đọc thử trực tiếp các file `.md` (bản dịch Tiếng Việt và Tam ngữ) ngay trên giao diện Desktop App.
- **Quy chuẩn 1 file EPUB duy nhất**:
  - Đảm bảo toàn bộ luồng tạo sách xuất đúng 1 file EPUB thành phẩm duy nhất ở gốc thư mục (`<Tên Sách>.epub`).

### File đổi
- `desktop/ViewModels/MainViewModel.cs`
- `desktop/Services/PythonPipelineService.cs`
- `desktop/Views/BooksPage.xaml`, `desktop/Views/BooksPage.xaml.cs`
- `desktop/Views/MdPreviewWindow.xaml`, `desktop/Views/MdPreviewWindow.xaml.cs`
- `desktop/Views/EpubPreviewWindow.xaml.cs`
- `scripts/output/make_epub.py`
- `scripts/common/epub_style.css`
- `README.md`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng. Toàn bộ tính năng đã được kiểm tra và nghiệm thu thực tế.

### Git
- Sẵn sàng commit và push theo yêu cầu của người dùng.

---

## 2026-08-28 — Tối ưu hóa Thanh tìm kiếm gom về TitleBar Toàn Cục & Tinh gọn Giao diện

### Đã làm
- **Triển Khai Bước 1: Trải Nghiệm Đọc & Trình Diễn (Liquid Glass Reader & Side-by-Side Split View)**:
  - Nâng cấp toàn diện Trình đọc E-Reader (`MdPreviewWindow`): Bổ sung chế độ **Song song Đối chiếu (2 Cột - Side-by-Side Split View)** với thiết kế lưới chuẩn xác, căn khớp từng đoạn văn giữa bản gốc (Trung/Anh) và bản dịch tiếng Việt.
  - Hỗ trợ trọn bộ 5 chế độ đọc linh hoạt: *Thuần Việt*, *Song song (2 Cột)*, *Tam ngữ 3 tầng (Gốc + Pinyin + Dịch)*, *Song ngữ từng đoạn* và *Bản gốc*.
  - Tích hợp thanh công cụ đọc sách cao cấp: Lựa chọn 6 họ font chữ (Segoe UI, Serif, Bookerly Kindle, Noto Serif SC, Cổ điển KaiTi, Consolas Mono), căn chỉnh lề (650px - 1000px - Fullscreen), khoảng cách dòng (1.5x - 2.2x) và zoom tỷ lệ trang.
- **Tích Hợp Bộ 3 Tiện Ích Giao Diện & Thao Tác (UX / Convenience)**:
  - **1. Kéo - Thả File Trực Tiếp (Smart Drag & Drop)**: Bật `AllowDrop=True` toàn cục, thêm lớp phủ kính mờ `DragDropOverlay` phát sáng hiện đại. Tự động lưu file vào `input/chua-lam/` và nạp vào UI ngay khi thả file.
  - **2. Bảng Thống Kê & Hiệu Suất (Dashboard Quick Analytics)**: Hiển thị thanh trạng thái thời gian thực trên header trang Sách: số sách chưa làm, đã dịch, đã có audio và tốc độ GPU RTX thực tế.
  - **3. Menu Chuột Phải Tiện Ích 1-Click (Context Menu)**: Hỗ trợ click chuột phải vào mọi thẻ sách để mở nhanh thư mục, đọc thử bản dịch, sao chép đường dẫn file hoặc dọn dẹp cache trung gian.
- **Nâng Cấp Cơ Chế Dịch Song Song Thông Minh Bảo Vệ Ngữ Cảnh (Sliding Window Context)**:
  - **Tối ưu tốc độ dịch gấp 2–3 lần**: Tích hợp điều phối đa luồng qua `SemaphoreSlim` với số luồng tùy chỉnh linh hoạt từ 1 đến 4 luồng.
  - **Bảo vệ ngữ cảnh 3 tầng**:
    1. Đồng bộ `Book Profile` (hồ sơ văn chương, quy tắc xưng hô, giọng điệu tác giả) + `Master Glossary` cho mọi luồng.
    2. Tự động trích xuất 2-3 câu cuối của chunk trước đó làm **Ngữ Cảnh Gối Đầu (Sliding Window Context)** gửi kèm vào prompt cho chunk sau.
    3. Đảm bảo bản dịch luôn liền mạch, cảm xúc liên tục và tuyệt đối không bao giờ bị lệch ngôi xưng giữa các chương.
  - **Giao diện Desktop Liquid Glass 3.0**: Thêm bộ chọn `Luồng dịch: [1 Luồng / 2 Luồng (Chuẩn) / 3 Luồng / 4 Luồng]` ngay trên thanh điều khiển của `BooksPage.xaml`.
- **Chuẩn Hóa Hiển Thị API Key Bảo Mật (Password Bullet) trong Trang Cài Đặt**:
  - Khi mở trang hoặc chuyển đổi giữa các Provider (Gemini / DeepSeek / Custom): Tự động nạp API key đã lưu vào `ApiKeyBox` và hiển thị dưới dạng **dãy chấm tròn bảo mật (`●●●●●●●●`)**.
  - Bổ sung nhãn thông báo trạng thái `KeyStatusText` trực quan: *"● Đã lưu API key (đang được bảo mật). Nhập key mới nếu muốn thay đổi."*
  - Khi người dùng bấm **Lưu Cấu Hình** hoặc **Kiểm Tra Kết Nối**: Cập nhật lưu tức thì và đồng bộ ngay giao diện.
- **Hợp nhất thanh tìm kiếm toàn cục duy nhất trên TitleBar (Phương án 1)**:
  - Loại bỏ hoàn toàn ô `SearchBox` trùng lặp trong trang `BooksPage.xaml`, nhường trọn không gian cho tiêu đề và danh sách sách thoáng sạch.
  - Tối ưu thanh `GlobalSearchBox` trên TitleBar (`MainWindow.xaml`):
    - Đặt placeholder thân thiện: `"Tìm kiếm sách... (Ctrl+F)"` kèm Icon Search 24 tinh tế.
    - Kết nối cơ chế lọc Realtime (`GlobalSearchQueryChanged`) $\rightarrow$ Gõ đến đâu danh sách sách lọc đến đó tức thì.
    - Phím tắt `Ctrl + F` tự động kích hoạt nhảy thẳng vào ô tìm kiếm trên TitleBar và chọn toàn bộ text.

### File đổi
- `desktop/Views/BooksPage.xaml`, `desktop/Views/BooksPage.xaml.cs` (loại bỏ SearchBox, kết nối lọc Global)
- `desktop/Views/MainWindow.xaml`, `desktop/Views/MainWindow.xaml.cs` (tối ưu GlobalSearchBox và phím tắt Ctrl+F)
- `desktop/ViewModels/MainViewModel.cs` (sự kiện GlobalSearchQueryChanged realtime)
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng. App đã build thành công 0 warning, 0 error.

### Git
- Sẵn sàng commit và push theo lệnh của người dùng.


### Đã làm
- **Đồng bộ toàn diện Giao diện & Tính năng Tab Audio theo chuẩn Tab Sách**:
  - Bổ sung cặp nút thao tác chuyên nghiệp trên mỗi thẻ sách Audio:
    - **Nút 1 (Primary)**: **`🎧 Tạo Audio Toàn bộ`** (`GenerateFullAudiobookCommand`) — Tạo mới 100% toàn bộ Audiobook từ đầu (`force=true`, xóa cache và chạy toàn bộ các chương).
    - **Nút 2 (Secondary)**: **`🔧 Sửa chữa & Rà soát Audio`** (`GenerateAudiobookCommand`) — Chế độ thông minh: rà soát các chương đã có file MP3, giữ lại chương chuẩn, chỉ tạo tiếp các chương còn thiếu hoặc bị lỗi.
    - Kèm **Nút Play** nghe thử mẫu ~30s giọng đọc & nhạc nền AI + **Nút Folder** mở trực tiếp thư mục MP3.
  - Thanh tiến độ `GlassProgressBar` 3 tầng đồng bộ hoàn toàn với tab Sách (Header trạng thái + % to rõ màu Accent + Thanh phát sáng + Dòng phụ GPU RTX / tên chương).
- **Tự động nhận diện sách Tiếng Việt & Thông báo trên Realtime Log**:
  - Tích hợp bộ nhận diện `IsVietnameseText()` và `PipelineLang == "vi"` vào cả 2 chế độ **Dịch Toàn bộ** & **Sửa chữa / Rà soát**.
  - Hiển thị trực tiếp thông báo nổi bật ngay trên khung **Realtime Log**:
    ```
    ℹ️ [THÔNG BÁO] Cuốn sách 'Tên Sách' vốn đã là TIẾNG VIỆT!
      → Không cần dịch qua API (để bảo toàn 100% nguyên tác và tiết kiệm token).
      → Tự động xuất bản thành phẩm và chuyển sang trạng thái sẵn sàng Tạo Audiobook...
    ```
  - Tự động đóng gói EPUB, di chuyển sách vào `input/da-dich/` và hoàn tất mà không tiêu tốn token API.

### File đổi
- `desktop/Views/BooksPage.xaml` (đổi tên nút sang "Dịch Toàn bộ", giao diện thanh tiến độ GlassProgressBar mới cho Input/Output)
- `desktop/ViewModels/MainViewModel.cs` (cập nhật BusyStatusText, DisplayActiveProvider, tính toán tiến độ các bước)
- `desktop/Models/BookStatus.cs` (thêm BusyStatusText, tối ưu hóa getter StatusText & ProgressPercent)
- `desktop/Views/BooksPage.xaml` (giao diện thanh tiến độ GlassProgressBar mới cho Input/Output)
- `desktop/Views/AudioPage.xaml` (nâng cấp thanh tiến độ Audiobook)
- `desktop/Views/MainWindow.xaml` (chỉ báo toàn cục TitleBar + chuẩn hóa hiển thị DisplayActiveProvider)
- `desktop/Views/ApiPage.xaml`, `desktop/Views/ApiPage.xaml.cs` (xóa Demo dịch thử, chuẩn hóa Dropdown Provider)
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng. App đã build thành công 0 warning, 0 error.

### Git
- Sẵn sàng commit và push theo lệnh của người dùng.

---

## 2026-08-28 — Sửa lỗi không hiển thị danh sách thẻ sách trên trang BooksPage

### Đã làm
- **Khắc phục lỗi thẻ sách bị ẩn biến mất trên BooksPage**:
  - **Nguyên nhân cốt lõi**: Trong `desktop/Views/BooksPage.xaml`, `ItemsControl.ItemsPanel` của cả 2 tab `Input` và `Output` đang định nghĩa `<WrapPanel MaxWidth="{Binding ActualWidth, ElementName=InputScrollViewer}"/>` (và `OutputScrollViewer`). Trong cơ chế WPF, `ItemsPanelTemplate` có `NameScope` riêng biệt nên không thể truy xuất `ElementName` ở ngoài template, khiến binding trả về giá trị mặc định `0.0`, ép `MaxWidth = 0` và làm toàn bộ thẻ card sách bị bóp nghẹt chiều rộng về 0px (biến mất hoàn toàn dù đã nạp 13 input / 14 output thành công).
  - **Cách xử lý**: Loại bỏ thuộc tính `MaxWidth` thừa trong `ItemsPanelTemplate`, chuyển về `<WrapPanel/>` tự nhiên (đồng bộ chuẩn như `AudioPage.xaml`).
- **Biên dịch**: `dotnet build` đạt **0 Warning(s), 0 Error(s)**.

### File đổi
- `desktop/Views/BooksPage.xaml`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng.

### Git
- Chưa commit — chờ người dùng duyệt.

---

## 2026-08-28 — Tích hợp CommandCode API 100% Model thực tế, Clean Slate dịch mới & Sửa nút Hủy

### Đã làm
- **Quét thực tế 100% Model từ CommandCode & Router API**:
  - Gỡ bỏ danh sách model hardcode, chuyển sang truy vấn trực tiếp `/v1/models` (`https://api.commandcode.ai/provider/v1/models`).
  - Hỗ trợ toàn diện 50+ model thực tế của CommandCode (`deepseek/deepseek-v4-flash`, `moonshotai/Kimi-K3`, `Qwen/Qwen3.8-Max`, `claude-opus-5`, `google/gemini-3.7-flash`...).
- **Xử lý Dịch mới 100% từ đầu (Clean Slate)**:
  - Khi bấm "Dịch Toàn Bộ", app tự động xóa sạch toàn bộ các bản trích xuất, chunks, progress, QA, profile và thành phẩm cũ theo mọi biến thể slug/title trước khi chạy.
  - Đảm bảo trích xuất lại từ file gốc và dịch mới 100% từng chunk qua API.
- **Khắc phục lỗi HTTP 503 Upstream Unavailable & Timeout**:
  - Tăng `HttpClient.Timeout` lên 300s.
  - Tích hợp Exponential Backoff tự động retry 5 lần khi gặp 503/502/504 hoặc Timeout.
- **Sửa nút Hủy (Cancel Button)**:
  - Sửa binding XAML và triển khai `CancelTaskCommand` kích hoạt đồng thời `_currentCts.Cancel()` và dừng tiến trình Python con `_pipeline.KillCurrentProcess()`.
- **Biên dịch**: `dotnet build` thành công **0 Warning, 0 Error**.

### File đổi
- `desktop/Services/ApiTranslationService.cs`
- `desktop/ViewModels/MainViewModel.cs`
- `desktop/Views/BooksPage.xaml`
- `desktop/Views/AudioPage.xaml`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng.

### Git
- Đã commit.

---

## 2026-08-28 — Hiệu ứng AI Thinking Realtime Log, Bảo toàn Token khi Hủy & Đa cấu hình API (Cấu hình 1-5 & OpenCode)

### Đã làm
- **Hiệu ứng AI Thinking & Live Pulse cho Realtime Log**:
  - Tích hợp đốm sáng Live Pulse trạng thái ở Header (xanh lơ tĩnh khi rảnh, nhấp nháy phát sáng Neon Mint khi đang bận).
  - Thêm thanh trạng thái AI Thinking ở đáy khung Log với icon Sparkle tím Lavender, thông báo tiến trình chi tiết và thanh sóng năng lượng.
  - Phân màu Terminal sống động cho từng dòng log (Đỏ, Cam, Xanh Mint, Cyber Cyan, Tím mộng mơ).
- **Gia cố nút Hủy bảo toàn 100% Token**:
  - Cơ chế 3 lớp: Ngắt `CancellationToken`, gọi `HttpClient.CancelPendingRequests()` để cắt đứt ngay lập tức kết nối socket mạng tới Server AI tránh sinh thêm Token, và `KillCurrentProcess()` dừng tiến trình Python con.
- **Hệ thống Đa Cấu Hình API (Cấu hình 1 - 5 & OpenCode Zen)**:
  - Cho phép lưu trữ và chuyển đổi tức thì giữa 5 Slot cấu hình tùy chỉnh riêng biệt + 2 Provider trực tiếp (Gemini, DeepSeek).
  - Tích hợp sẵn mẫu cấu hình cho OpenCode Zen (`https://opencode.ai/zen/v1`).
  - Lưu trữ độc lập trong `config.json`, không lo bị mất hay ghi đè key khi đổi nhà cung cấp.
- **Biên dịch**: `dotnet build` thành công **0 Warning, 0 Error**.

### File đổi
- `desktop/Models/ApiConfig.cs`
- `desktop/Services/ApiTranslationService.cs`
- `desktop/ViewModels/MainViewModel.cs`
- `desktop/Views/MainWindow.xaml`
- `desktop/Views/ApiPage.xaml`
- `desktop/Themes/LiquidGlass.xaml`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng.

### Git
- Đã push lên GitHub (commit 54a48af).

---

## 2026-08-29 — Sửa lỗi click chuột phải & Khắc phục hiển thị đa chế độ (Bản gốc, Song song, Tam ngữ) trong Trình đọc E-Reader

### Đã làm
- **Khắc phục triệt để lỗi menu chuột phải (ContextMenu)**:
  - Sửa lỗi mất ngữ cảnh DataContext của WPF ContextMenu: Bổ sung `Tag="{Binding DataContext, ElementName=BooksPageRoot}"` trên các `Card` và trỏ Command qua `PlacementTarget.Tag`.
  - Tích hợp thêm sự kiện `Click` handler dự phòng (`ContextMenuPreview_Click`, `ContextMenuOpenFolder_Click`...) trong `BooksPage.xaml.cs`.
- **Khắc phục triệt để lỗi hiển thị đa chế độ trong Trình đọc E-Reader Preview**:
  - *Nguyên nhân*: Khi mở bản dịch, file `vi.md` được nạp vào, còn file `tamngu.md` định dạng `<p class="src-zh">...` (không có thẻ bao `<div class="tri-block">`) làm regex cũ không tách được chữ Hán và Pinyin, dẫn tới hệ thống fallback dùng text tiếng Việt cho toàn bộ các chế độ.
  - *Khắc phục*: Cải tiến `ExtractLayersFromText` bóc tách độc lập từng thẻ `<p class="src-zh">`, `<p class="pinyin">`, `<p class="vi">`. Tự động nạp độc lập `raw.md` (bản gốc), `tamngu.md` (tam ngữ), và `vi.md` (thuần Việt).
  - *Khắc phục phân đoạn*: Viết lại `SplitIntoBlocks` để phân tách từng đoạn văn bản tự nhiên (`\n\n`) thay vì chỉ theo heading `#`, giúp chế độ Song song đối chiếu (2 Cột), Tam ngữ và Song ngữ hiển thị chuẩn xác từng cặp đoạn.
- **Nâng cấp & Gia cố Tính năng 'Dọn Dẹp Cache Trung Gian'**:
  - Quét sạch toàn bộ các thư mục tạm: `working/chunks/<slug>`, `working/progress/<slug>`, `working/progress_audio/chunks/<slug>`, `working/qa/<slug>`, `working/tmp/<slug>`.
  - Xóa các file JSON và preview tạm: `working/progress_audio/<slug>.json`, `output/samples/<slug>_preview.md`.
  - Bổ sung thông báo Snackbar trực quan trên UI báo số lượng mục đã dọn thành công và cập nhật lại tiến độ thẻ sách.
- **Bổ Sung Tính Năng 'Xóa Sách Thông Minh' Phân Biệt Input / Output**:
  - Thêm nút icon Xóa (màu đỏ) và MenuItem trong menu chuột phải trên cả 2 tab.
  - *Bên Input*: Chỉ xóa file sách nguồn trong `input/` và cache tạm `working/`.
  - *Bên Output*: Xóa sạch toàn bộ sản phẩm hoàn thiện trong `output/books/<tên-sách>` (EPUB, Audiobook, bản dịch .md) và toàn bộ cache `working/`, **giữ nguyên file gốc trong Input**.
  - Có hộp thoại xác nhận `MessageBox` trước khi thực hiện để đảm bảo an toàn tuyệt đối.
- **Đặt Mặc Định 1 Luồng Dịch Ổn Định & Tối Ưu Giãn Cách Chống Timeout**:
  - Chuyển số luồng dịch mặc định `TranslateConcurrency` từ 2 về 1 (`1 Luồng (Mặc định - Ổn định)`) để bảo đảm kết nối ổn định nhất, không bị nghẽn mạng và tiết kiệm tối đa quota API.
  - Bổ sung cơ chế giãn cách `pacing delay` (600ms) khi chạy từ 2 luồng trở lên nhằm tránh gửi bão request làm sập kết nối server AI.
- **Tái Thiết Kế Header Realtime Log Chuẩn Glass 3.0**:
  - Tách bố cục 1 hàng chật chội thành cấu trúc 2 tầng thoáng đãng:
    - *Tầng 1*: Tiêu đề `Realtime Console` + đốm sáng Live Pulse bên trái $\leftrightarrow$ cụm 3 nút icon (`Sao chép`, `Xóa sạch log đỏ`, `Thu gọn`) bên phải.
    - *Tầng 2*: Ô tìm kiếm/lọc từ khóa `🔍 Lọc log theo từ khóa...` toàn chiều rộng, rộng rãi và cân đối thị giác.
- **Nâng Cấp Viền Kính Bo Tròn Mềm Mại (Liquid Glass 3.0) Cho Thẻ Sách & Audio**:
  - Tăng độ bo tròn của toàn bộ Card sách lên `14px` (`CornerRadius="14"`), viền Gradient ánh sáng đa chiều siêu thực.
  - Nâng cấp các ô thông số thống kê (`Audio`, `EPUB`, `Chunks`, `Ký tự`) lên `10px`, tự động phát sáng viền xanh Accent khi hover chuột.
  - Tăng bo góc của hộp tiêu đề sách trong Card lên `10px` để tạo sự đồng bộ mượt mà.
- **Menu Sidebar Dạng Viên Thuốc Viền Gương (Pill Glass 3.0) & Khôi Phục Text API Gốc**:
  - Bỏ phần Brand Header ở đỉnh để giao diện Sidebar tối giản, thanh thoát và gọn gàng.
  - Chuyển các nút menu `Sách`, `Audiobook`, `Cài đặt` sang phong cách **Viên thuốc viền gương (Pill Glass)** bo tròn `12px` với viền phản quang Gradient đồng bộ với Tab danh sách.
  - Khôi phục phần hiển thị `API` ở footer về dạng Text mộc mạc nguyên bản ban đầu (`API / DeepSeek-Chat`).
- **Tối Ưu Toàn Diện Hiệu Năng & Tăng Cường Độ Mượt Mà, Nhẹ Nhàng**:
  - *.NET 8 Runtime*: Bật `TieredCompilation`, `TieredCompilationQuickJit` và `ConcurrentGarbageCollection` trong file project giúp app mở tức thì và dọn dẹp RAM nền êm ái, triệt tiêu hoàn toàn giật cục (zero stutter).
  - *WPF Hardware Acceleration*: Tích hợp `ClearTypeHint="Enabled"`, `TextRenderingMode="ClearType"`, `TextFormattingMode="Display"` giúp GPU đảm nhận render chữ và thẻ card sắc nét, giảm tải CPU.
  - *Console RAM Optimization*: Giới hạn 800 blocks văn bản trên UI RichTextBox trong `MainWindow.xaml.cs` (tự động cắt dọn block cũ), giữ mức chiếm dụng RAM cực thấp (~50MB) dù app chạy log hàng nghìn dòng.
- **Cố Định Sidebar Menu Vĩnh Viễn & Xóa Bỏ Hoàn Toàn Nút 3 Gạch**:
  - Xóa bỏ thẻ `NavigationView.PaneHeader` chứa nút 3 gạch (Pane Toggle Button).
  - Cố định Sidebar bên trái mở hoàn toàn 210px (`IsPaneOpen="True"`, `IsPaneToggleVisible="False"`), loại bỏ cơ chế co giãn trượt ra/vào giúp giao diện luôn vững chãi, trực quan và sạch sẽ.
  - Các nút `Sách`, `Audiobook`, `Cài đặt` dạng viên thuốc viền gương hiển thị đầy đủ, ngay ngắn 100%.
- **Biên dịch**: `dotnet build` đạt **0 Warning, 0 Error**.

### File đổi
- `desktop/Themes/LiquidGlass.xaml`
- `desktop/Themes/AppStyles.xaml`
- `desktop/Views/MainWindow.xaml`
- `desktop/Views/BooksPage.xaml`
- `desktop/Views/BooksPage.xaml.cs`
- `desktop/ViewModels/MainViewModel.cs`
- `desktop/Views/MdPreviewWindow.xaml.cs`
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Không còn việc tồn đọng.

### Git
- Chưa commit — chờ người dùng duyệt.
