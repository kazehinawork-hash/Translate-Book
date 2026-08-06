# 📔 SESSION LOG — Nhật ký phiên làm việc

> Append-only: mỗi phiên thêm **1 entry ở CUỐI file**. Entry mới nhất nằm dưới cùng.
> **ĐẦU PHIÊN**: agent đọc 2 entry CUỐI để biết việc gần nhất.
> Mỗi entry: `## YYYY-MM-DD` + **Đã làm** / **File đổi** / **Còn dở** / **Git**.

---

## 2026-08-05 — Thiết lập trí nhớ phiên + docs rút gọn

### Đã làm
- **Docs rút gọn**: README trở thành tài liệu duy nhất; gộp nội dung `QUICKSTART.md` + `USAGE.md` vào README rồi xoá cả 2 file (tổng −1.121 dòng). Thêm bảng Troubleshooting.
- **README cập nhật** cho hợp hiện trạng: bảng thành tựu (4 cuốn + audiobook), cấu trúc thư mục đánh dấu commit/không-commit, chính sách git code-only, mục App desktop (C# WPF), path script audiobook, `/dich`.
- **Dọn lịch sử git** (phiên trước): `git filter-branch` bóc toàn bộ sản phẩm khỏi mọi commit → repo ~717MB → 0.4MB; force-push `main`. 129→58 commit.
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

---

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
- **WebView2 user-data-folder**: dùng reflection để set `CreationProperties.UserDataFolder = %LocalAppData%\TranslateBook\WebView2` (type `CoreWebView2CreationProperties` không resolve ở compile-time).
- **EpubPreviewWindow CSS**: đọc `TextFillColorPrimaryBrush`/`TextFillColorSecondaryBrush`/`AccentFillColorDefaultBrush` từ theme resources thay vì hardcode màu tối.
- **Dọn dẹp**: xóa `GitCommitAsync` (không UI gọi), `FindProjectRoot` duplikat → dùng `ProjectHelper.FindProjectRoot()`, sửa `TestApi_Click` dùng `ComboBoxItem.Content` thay `SelectedValue`, `ConfigService` đã có try/catch + backup.

### File đổi
- `desktop/Services/ApiTranslationService.cs` (thêm `LoadGlossary`, `sourceLang`/`targetLang`/`trilingual` params)
- `desktop/ViewModels/MainViewModel.cs` (rewrite StartTranslateAsync, GenerateAudiobookAsync, thêm Cancel, timer, cap log)
- `desktop/Services/PythonPipelineService.cs` (audiobook Python + error message)
- `desktop/Views/MainWindow.xaml.cs` (Closing → KillCurrentProcess)
- `desktop/Views/ApiPage.xaml.cs` (TestApi_Click fix)
- `desktop/Views/BooksPage.xaml.cs` (dùng ProjectHelper.FindProjectRoot)
- `desktop/Views/EpubPreviewWindow.xaml.cs` (CSS theme + WebView2 user-data-folder)
- `desktop/Services/ConfigService.cs` (bỏ unused `ex`)
- `docs/STATE.md`, `docs/session_log.md`

### Còn dở
- Chưa kiểm thử runtime (API key chưa có) — chờ user test.
- `translate_helper.py --interactive` vẫn còn trong PythonPipelineService nhưng không được gọi từ app.

### Git
- Trạng thái: thay đổi code chưa commit trên `main`. Đang chờ người dùng duyệt.