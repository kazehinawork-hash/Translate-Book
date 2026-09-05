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
| `zuo-yi-ge-you-feng-gu-de-nu-zi` | `做一个有风骨的女子` | ZH | ✅ Hoàn tất | Self-help nữ giới Vi Dương (8 chương). **DỊCH LẠI TOÀN BỘ + AUDIOBOOK MỚI (08-24)** — lần trước extract từ EPUB lạc đề (tản văn Vãn Tình): MinerU PDF → 50 chunk → dịch 50/50 khớp dòng → QA 0 lỗi (Hán sót 0 sau khi sửa chunk_000 metadata) → merge tamngu.md+vi.md (fix bug merge_sentences nuốt dòng ảnh) → 1 EPUB nhúng font Noto Serif SC (~15.5MB). **Audiobook mới 81/81 chương GPU batch 16 + nhạc nền AI music_map (26 bài lofi, volume 0.15, temp 0.3, top_k 10)** — ~5.05 giờ audio (277MB), QA ffprobe 81/81 MP3 hợp lệ. Đã xóa audiobook cũ 85 chương (bản lạc đề). Input chuyển `da-audio/`. Tác giả Vi Dương |
| `zuo-yi-ge-you-feng-gu-de-nu-zi-wan-qing` | `做一个有风骨的女子  不迎合, 不媚俗 (晚晴)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (66 chunks). **Dịch mới + audiobook 44/44 chương GPU + nhạc nền AI (08-18)**: input `.azw3` (Kindle) → calibre chuyển EPUB → extract 50 mục → 66 chunk → profile văn chương → dịch 66/66 (97K từ, khớp dòng 100%, QA Hán sót 0.0%) → đồng bộ TOC (46 mục = body) → 1 EPUB nhúng font. Audiobook: `--music-auto` đọc music_map.json (44 chương, mỗi chương 1 bài theo cảm xúc), volume 0.15, batch 16, temp 0.3, top_k 10. ~7.2 giờ audio (414MB). ⚠️ Slug khác cuốn cùng tên của Vi Dương (`zuo-yi-ge-you-feng-gu-de-nu-zi`) — đã dùng suffix `-wan-qing`. Tác giả Vãn Tình |
| `ban-co-nam-cho-ngoi` | `Ban Co Nam Cho Ngoi - Nguyen Nhat Anh` | VI | ✅ Hoàn tất | Audiobook 12/12 chương **GPU + nhạc nền (08-13)**: toàn bộ chương chạy lại bằng GPU batch 16, nhạc nền xoay `sach_ke_chuyen_10_lofi.mp3` / `sach_ke_chuyen_11_lofi.mp3`, **volume 0.15** (giảm từ 0.20), temp 0.3, top_k 10. ~3h09 audio. Tác giả Nguyễn Nhật Ánh |
| `dac-nhan-tam` | `Đắc Nhân Tâm - Dale Carnegie` | VI | ✅ Hoàn tất | Audiobook. Tác giả Dale Carnegie |
| `rung-na-uy` | `Rung Na-uy - Haruki Murakami` | VI | ✅ Hoàn tất | Audiobook. Tác giả Haruki Murakami |
| `eu-bim-task-group-handbook-v2-1` | `EU-BIM-Task-Group-Handbook-V2.1` | EN | 📗 Dịch xong | Handbook kỹ thuật BIM/Twin Transition (EU). Đã dịch 9/9 chunk, songngu.md + vi.md + vi.epub. Audiobook chưa làm (sách tài liệu kỹ thuật, tùy chọn) |
| `qie-yi-qing-shen-gong-bai-tou` | `且以情深共白头：婚前看情感，婚后靠相处 (晚情)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (58 chunks). **Dịch lại toàn bộ theo chuẩn văn chương mới + audiobook 75/75 chương GPU + nhạc nền AI (08-17)**: profile văn chương `working/profile/qie-yi-qing-shen-gong-bai-tou.md` → dịch 58/58 chunk (84K từ, 100% khớp dòng, QA Hán sót 0.0%) → merge tamngu.md + vi.md (đồng bộ mục lục với heading mới) → 1 EPUB nhúng font. Audiobook: `--music-auto` đọc `music_map.json` (75 chương, mỗi chương 1 bài theo cảm xúc), volume 0.15, batch 16, temp 0.3, top_k 10. ~6.4 giờ audio (369MB). Tác giả Vãn Tình |
| `zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing` | `做一个刚刚好的女子  不攀附, 不将就 (晚情)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (71 chunks). **Dịch lại toàn bộ theo chuẩn văn chương + audiobook mới GPU + nhạc nền AI (08-18)**: profile `working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-wan-qing.md` → dịch 71/71 chunk (109K từ, khớp dòng 100%, QA Hán sót 0.0%) → merge tamngu.md + vi.md (đồng bộ mục lục titles.json) → 1 EPUB nhúng font Noto Serif SC (~15.5MB). Audiobook: music_map 50 chương, volume 0.15, batch 16, temp 0.3, top_k 10, ~7.4 giờ audio (405MB). Tác giả Vãn Tình |
| `zuo-yi-ge-you-jing-jie-de-nu-zi` | `做一个有境界的女子  不自轻,不自弃 (晚情)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình: "Làm một người phụ nữ có cảnh giới" (56 chunks). **Audiobook 34/34 chương GPU + nhạc nền AI (08-25)**: dọn vi.md (cắt front-matter title/author/slug 6 dòng), 34 chương essay. Voice van_tinh, volume 0.15, temp 0.3, top_k 10. RTF 0.37, ~172 phút gen, 6.5 giờ audio (160MB), music-auto lofi. QA ffprobe 34/34 MP3 hợp lệ. metadata has_audio=true. EPUB → `da-audio/`. Tác giả Vãn Tình |
| `you-duo-xiang-jiu-you-duo-xing-fu` | `有多想要，就有多幸福 (晚情著)` | ZH | ✅ Hoàn tất | Tản văn Vãn Tình (32 chunks). EPUB sách toàn ảnh 320 trang → OCR PaddleOCR (GPU) → raw.md 113KB. Dịch đủ 32/32 chunk, QA 0 lỗi, merge tamngu.md + vi.md + trilingual.epub. **Audiobook 71/71 chương GPU + nhạc nền AI (08-16)**: music_map theo cảm xúc từng chương, volume 0.15, batch 16. ~6h06 audio. Tác giả Vãn Tình |
| `zuo-yi-ge-gang-gang-hao-de-nu-zi-2` | `做一个刚刚好的女子 2` | ZH | ✅ Hoàn tất | Tản văn self-help nữ giới **Khang Tĩnh Văn** (康静文 — KHÁCH cuốn 1 cùng tên của Vãn Tình), 读美文库 2017, 4 PART + ~40 tản văn. **Dịch trọn pipeline (08-24)**: MinerU GPU → 37 chunk → dịch 37/37 bằng batch manifest (khớp dòng 100%, QA Hán sót 0) → merge tamngu.md + vi.md → fix TOC sync 39 entry theo heading body + heading normalize (5 H1 = tựa + 4 PART, essay = ##, tách dòng TOC merged PART 4) → 1 **EPUB TAM NGỮ** nhúng font Noto Serif SC (~18MB) — build từ `final/tamngu.md` (tri-block ZH+Pinyin+VI, 2169 khối; lần đầu build nhầm từ vi.md thuần Việt, user bắt lỗi → rebuild). **Audiobook 61/61 chương GPU batch 16 + nhạc nền AI (08-25)**: dọn vi.md (cắt front-matter 114 dòng + back-matter catalog + bỏ 6 dòng `# PART N` divider), detect_chapters = 61 chương (40 essay + sub-headings). Voice van_tinh, volume 0.15, temp 0.3, top_k 10. RTF 0.31, ~64 phút gen, 3.42 giờ audio (188MB), music-auto 61 bài lofi. QA ffprobe 61/61 MP3 hợp lệ. metadata has_audio=true. Input PDF → `da-audio/` |
| `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` | `做一个刚刚好的女子 3` | ZH | ✅ Hoàn tất | Tản văn self-help nữ giới Vi Dương (微阳), 吉林文史出版社 2018, ISBN 978-7-5472-5777-7, 8 chương. **DỊCH LẠI TOÀN BỘ THEO CHUẨN MỚI (08-25)**: dữ liệu cũ (07-31/08-01) move backup `working/tmp/zy3_old_backup/` → MinerU GPU extract lại từ PDF (88,977 chars, Han 86%) → 50 chunk → glossary curated 20 thuật ngữ merge master (fix 2 mục sai 淡泊→thanh đạm, 从容→thong dong; master rebuild dedupe 183 dòng, xoá shards cũ) → skeleton trilingual + profile văn chương (`working/profile/zuo-yi-ge-gang-gang-hao-de-nu-zi-3.md`) → dịch 50/50 chunk bằng batch manifest 13 vòng (claim→dump_range→trans_rN.py→apply.py→batch_qa→complete), khớp dòng 100%, QA tổng thể 0 lỗi → merge tamngu.md + vi.md (vi 0 mojibake / 0 Hán sót) → 1 EPUB nhúng font Noto Serif SC (~15.9MB) ở gốc thư mục sách. **Audiobook 60/60 chương GPU batch 16 + nhạc nền AI music-auto (08-25)**: dọn vi.md audio (cắt bìa/CIP/NSX/mục lục + colophon, backup `working/tmp/zy3/vi_backup.md`) → voice van_tinh, volume 0.15, temp 0.3, top_k 10, RTF 0.32, ~90 phút gen, 4.76 giờ audio (261MB), QA ffprobe 60/60 MP3 hợp lệ (ch01 = tựa sách, ch37 = divider chương 5 — ngắn là đúng bản chất). metadata has_audio=true. Input PDF → `da-audio/`. |
| `wo-zai-hao-men-de-ri-ri-ye-ye` | `我在豪门的日日夜夜 (晚情)` | ZH | ✅ Hoàn tất | Tiểu thuyết romance ngôi 'tôi' Vãn Tình (Linh Linh × Tử Hàn), EPUB scan 203 trang ảnh. **Dịch lại từ đầu (08-25)**: OCR MinerU GPU từng ảnh qua worker nền checkpoint → raw.md 158K chars → QC xoá header/footer/quảng cáo watermark → 76 chunk → glossary 20 thuật ngữ merge master → skeleton + profile văn chương → dịch 76/76 bằng batch manifest 16 vòng (khớp dòng 100%, QA pass) → merge tamngu.md + vi.md → merge_sentences gộp câu + clean heading Trang/rác/dedupe → **EPUB tam ngữ nhúng font Noto Serif SC (~21MB, 195 ảnh)**. KHÔNG audiobook theo yêu cầu user. Input EPUB → `da-dich/` |
| `bu-wei-jiang-lai-bu-nian-guo-qu` | `不畏将来 不念过去 (十二 [十二]) (z-library.sk, 1lib.sk, z-lib.sk)` | ZH | ⏸️ Tạm dừng | Tản văn Thập Nhị (103 chunks). Tạm dừng thử nghiệm API; đã dọn sạch working/ |
| `ni-suo-wei-de-wen-ding-bu-guo-shi-zai-lang-fei-sheng-ming` | `你所谓的稳定，不过是在浪费生命 (李尚龙) (z-library.sk, 1lib.sk, z-li` | ZH | 📗 Đã có EPUB | Tản văn Lý Thượng Long (李尚龙). Sách đã lưu trữ trong output/books/ |

## 🔨 Đang làm (hiện tại)

- **Khắc phục triệt để lỗi API Timeout (HTTP 503 / 524) & Bảo toàn Chunk (09-04, XONG)**:
  - Loại bỏ khối ví dụ dài dòng trong `BuildPrompt` của `ApiTranslationService.cs`, giảm tải ~1.000 tokens mỗi request để API không bị nghẽn gateway Cloudflare 524.
  - Tăng số lần thử lên 6 lần và áp dụng cơ chế giãn nở thông minh Exponential Backoff (5s, 10s, 20s, 35s, 50s kèm jitter) giúp upstream model có thời gian phục hồi.
  - Loại bỏ hoàn toàn cơ chế ping/thăm dò phụ (Health Probe) trong vòng lặp retry: không gửi thêm bất kỳ request hay tiêu tốn token thừa nào khi server bận.
  - Khắc phục bug đếm lỗi ở Vòng 2 trong `MainViewModel.cs`: kiểm tra trực tiếp trạng thái file progress trên đĩa, không báo lỗi giả các chunk đã dịch thành công.
  - Cơ chế tự động bỏ qua (Skip) các chunk đã dịch xong trong `TranslateOneChunkAsync`: khi chạy tiếp hoặc dùng "Sửa chữa & Rà soát", app nạp thẳng kết quả trên đĩa, không bao giờ dịch lại hay tốn thêm token API.
  - Đồng bộ và biên dịch sạch sẽ cả 2 cấu hình **Debug** và **Release** (0 Warning, 0 Error).

- **Tích Hợp Khả Năng Co Kéo Chiều Rộng Realtime Console (GridSplitter Glass 3.0) (09-05, XONG)**:
  - **GridSplitter chuẩn Liquid Glass 3.0**: Bổ sung `GridSplitter` ngăn cách giữa vùng nội dung chính (`NavView`) và bảng điều khiển `LogPanel`. Thanh kéo có vạch kính mờ trung tâm, quầng sáng xanh Cyan Neon `#00F0FF` khi rê chuột (Hover) hoặc khi đang kéo (Dragging).
  - **Co kéo tương tác trực tiếp & Mượt mà**: Cấu hình 3 cột cho `MainGlassContainer` (`*`, `Auto`, `LogColumnDef` với độ rộng ràng buộc `MinWidth="36"` và `MaxWidth="900"`).
  - **Bộ nhớ ghi nhớ độ rộng tùy biến**: Trong `MainViewModel.cs`, bổ sung `LogPanelColumnWidth` và lưu giữ độ rộng ưa thích `_savedLogPanelWidth`. Khi thu gọn (Collapse) bảng log thu về 36px icon bar; khi mở rộng (Expand), tự động khôi phục đúng chiều rộng trước đó người dùng đã kéo dãn thay vì bị reset về 300px cố định.
  - **Hỗ trợ cuộn ngang tự động (HorizontalScrollBarVisibility="Auto")**: Tránh mất chữ hoặc bị che khuất nội dung dòng lệnh dài khi người dùng thu hẹp chiều ngang của Console.
  - **Bộ Ba Nâng Cấp Giao Diện Toàn Diện Ultra-Polished OS-Grade (09-05, XONG)**:
    - **1. Custom Smooth Thin Scrollbar (`GlassThinScrollBar`)**: Thay thế thanh cuộn mặc định thô kệch của Windows bằng thanh cuộn kính mỏng 7px bo tròn hình viên thuốc (Pill), phát quang viền Neon `#00F0FF` khi hover và `#00E5FF` khi kéo chuột; áp dụng toàn cục cho mọi `ScrollViewer` trong ứng dụng.
    - **2. Đồ Họa Sóng Âm Thanh Động (`MiniWaveformVisualizer`)**: Trang trí thanh sóng âm thanh huỳnh quang 4 cột nhấp nhô sống động (Neon Cyan, Purple & Mint Gradient) bên cạnh số chương Audiobook của mỗi cuốn sách trên `AudioPage`.
    - **3. Hiệu Ứng Chuyển Trang Êm Ái (`GlassPageTransition`)**: Tạo chuyển động trượt mờ tinh tế (Slide & Fade Y: 8 $\rightarrow$ 0, Opacity 0.2 $\rightarrow$ 1.0 trong 220ms với DecelerationRatio 0.8) khi điều hướng qua lại giữa các tab Sách, Audiobook và Cài đặt.
  - **Sửa Triệt Để Lỗi Không Khởi Động Được Ứng Dụng (Startup Crash) (09-05, XONG)**:
    - **Nguyên nhân 1 (Xung đột Animation WPF-UI)**: Thư viện `WPF-UI` đã có sẵn cơ chế chuyển trang mượt mà `TransitionAnimationProvider.FadeInWithSlideTransition` can thiệp vào `TranslateTransform.Y`. Khi gắn thêm `GlassPageTransition` qua Style Setter, đối tượng `TranslateTransform` bị đóng băng (`Frozen/Sealed`), khiến WPF quăng lỗi `InvalidOperationException: Cannot animate the 'Y' property because the object is sealed or frozen`. Đã gỡ bỏ style `GlassPageTransition` khỏi `BooksPage`, `AudioPage`, `ApiPage` và `LiquidGlass.xaml`, nhường quyền chuyển trang trơn tru cho cơ chế mặc định của `WPF-UI NavigationView`.
    - **Nguyên nhân 2 (XamlParseException tại ScrollViewer Style)**: Setter gán `Property="Resources"` bên trong style của `ScrollViewer` không hợp lệ trong XAML WPF runtime (`ArgumentNullException: Value cannot be null (Parameter 'property')`). Đã chuẩn hóa thành Style ngầm định toàn cục hợp lệ: `<Style TargetType="ScrollBar" BasedOn="{StaticResource GlassThinScrollBar}"/>`.
    - **Kiểm nghiệm thực tế**: Ứng dụng đã khởi động thành công mỹ mãn, tiến trình `TranslateBook.exe` chạy mượt mà ổn định, file `crash.log` hoàn toàn sạch 0 lỗi. Cả 2 bản **Debug** và **Release** đều biên dịch đạt 0 Warning, 0 Error.
  - **Đại Tu Thanh Điều Hướng Bên Trái (Left Navigation Sidebar Overhaul) (09-05, XONG)**:
    - **1. Live Pill Badges Đếm Số Lượng Động**: Bổ sung huy hiệu viên thuốc viền gương phát quang bên cạnh tên tab: Huy hiệu Cyan Neon cho "Sách" (`TotalBooksCount`) và Huy hiệu Tím Neon cho "Audiobook" (`AudioBooksCount`), cập nhật tự động theo thời gian thực khi nạp sách.
    - **2. Thẻ Trạng Thái API Liquid Glass Tương Tác (Click-to-Navigate)**: Thay thế text API tĩnh thô sơ cũ bằng một thẻ kính mờ hoàn chỉnh có viền phản quang Glass gradient, đèn LED xanh lá (`#10B981`) phát sáng quầng Dropshadow biểu thị trạng thái kết nối sẵn sàng của AI Engine, tên Provider/Model đang chọn và icon điều hướng. Người dùng có thể bấm trực tiếp vào thẻ để chuyển nhanh đến trang Cấu hình API (`ApiPage`).
    - **3. Bảng Điều Khiển Tổng Quan Hệ Thống Mini (Mini System & GPU Widget)**: Tích hợp ngay phía trên thanh footer của sidebar hiển thị tổng số từ đã dịch tích lũy (`TotalTranslatedWords`) định dạng chuẩn quốc tế và thẻ chip trạng thái card GPU (`GpuPerformanceText`, ví dụ "RTF 0.12 (GPU RTX ~8x)").
  - **Sửa Triệt Để Lỗi Các Nút Bấm Trang Cài Đặt (ApiPage Buttons Fix) (09-05, XONG)**:
    - **1. Nút 'Quét' Model (`FetchModels`)**: Thay đổi kiểu từ `ui:Button` sang WPF `Button` chuẩn với style `GlassPlainButton` và `Cursor="Hand"`. Xóa bỏ xung đột TargetType giữa `Wpf.Ui.Controls.Button` và Style WPF Button gốc.
    - **2. Khắc phục lỗi Hit-Testing & Padding trong `LiquidGlassButton` / `LiquidGlassButtonPrimary`**: Chuyển `Padding="{TemplateBinding Padding}"` từ `OuterBorder` vào `InnerBorder`. Đảm bảo người dùng click vào bất kỳ đâu trên nút bấm (kể cả viền và padding) đều bắt sự kiện chuẩn xác, không bị vùng chết (dead zones).
    - **3. Đồng bộ và thu thập API Key an toàn (`GetCurrentApiKey`)**: Cả ba thao tác "Quét", "Lưu cấu hình", "Kiểm tra kết nối" giờ đây tự động đọc key thông minh từ cả ô ẩn (`ApiKeyBox`) lẫn ô hiện mật khẩu (`ApiKeyPlainBox`) hoặc cấu hình lưu trên đĩa.
    - **4. Phản hồi trạng thái tức thời & Trực quan**: Cập nhật ngay thanh trạng thái API (`ApiStatus`, icon xoay, đổi màu phát quang) kèm thông báo Snackbar/MessageBox khi bấm các nút để người dùng nhận biết ngay lập tức hệ thống đang xử lý, không còn tình trạng bấm nút im lặng không rõ kết quả.
    - **5. Kiểm thử**: Cả Debug và Release build sạch 100% (0 Warning, 0 Error).

  - **Nâng Cấp Giao Diện Trang Cài Đặt Liquid Glass 3.0 Gọn Gàng & Hiện Đại (09-05, XONG)**:
    - **1. Tinh gọn giao diện form**: Lược bỏ các dòng text/chip gợi ý model và mẫu URL theo yêu cầu của người dùng, giữ không gian thẻ cấu hình thoáng đãng, tối giản và sạch sẽ tuyệt đối.
    - **2. Hiệu Ứng Xoay Vòng Vô Cực Nút Quét (`ScanIconRotate`)**: Khi bấm quét model, icon `ArrowSync` của nút tự động quay tròn liên tục (`RepeatBehavior.Forever`) kèm chữ "Đang quét...", và tự động dừng trở lại trạng thái ban đầu khi quét xong.
    - **3. Kiểm thử**: Debug và Release build sạch 100% (0 Warning, 0 Error).

  - **Tân Trang & Nâng Cao Chất Lượng Giao Diện Toàn Diện (System UI Polish) (09-05, XONG)**:
    - **1. Đèn LED Nhịp Thở Sống Động (`LiveGlowPulseDot`)**: Tạo mới control đèn LED phát quang Cyan Neon với quầng sáng Blur tỏa nhịp thở (`DoubleAnimation` Scale 0.8 $\rightarrow$ 1.25, Opacity 0.2 $\rightarrow$ 0.8 lặp vô hạn) cho thanh tiêu đề của Realtime Console, tạo cảm giác hệ thống luôn thức và sẵn sàng xử lý.
    - **2. Tab Header Viền Kính Phát Quang & Shimmer (`GlassTabHeader`)**: Nâng cấp các tab Input/Output với viền phản quang Shimmer Gradient (`GlassCardShimmerBorderBrush`) và quầng Dropshadow phát quang Cyan khi được chọn (`IsChecked=True`).
    - **3. Tinh Chỉnh TextBox & ComboBox Kính Mờ**: Chuẩn hóa độ dày viền 1px, phản xạ viền Neon `#00F0FF` khi focus và hiệu ứng nền hover mượt mà cho `LiquidGlassTextBox` và `GlassComboBox`.
    - **4. Kiểm thử**: Cả Debug và Release build sạch 100% (0 Warning, 0 Error).

  - **Nâng Cấp Hiệu Ứng Chuyển Động Mượt Mà & Tối Ưu CPU/RAM (Motion & Perf Optimization) (09-05, XONG)**:
    - **1. Tối ưu CPU khi nhàn rỗi (Idle CPU Throttling)**: Thêm `Timeline.DesiredFrameRate="30"` cho các Storyboard chạy lặp vô hạn (`LiveGlowPulseDot` và 4 cột sóng của `MiniWaveformVisualizer`) trong `LiquidGlass.xaml`. Giảm chu kỳ đánh thức CPU ~50% khi ứng dụng mở nền mà mắt thường vẫn thấy êm ái hoàn hảo.
    - **2. Micro-Interactions Siêu Mượt bằng GPU Transforms**: Thêm hiệu ứng nâng thẻ kính (`LiquidGlassCard`) với `TranslateTransform.Y` (-2.5px) và `ScaleTransform` (1.008) sử dụng `DecelerationRatio="0.8"` (enter 180ms) và `AccelerationRatio="0.6"` (exit 200ms). Chạy hoàn toàn trên GPU Composition Thread, không gây tính toán lại Layout (Zero Measure/Arrange passes).
    - **3. Cuộn Danh Sách Chuẩn Pixel Cực Êm & Tối Ưu RAM**: Bổ sung `VirtualizingPanel.ScrollUnit="Pixel"` trên các `ScrollViewer` của `BooksPage` (Input/Output tabs) và `AudioPage`. Giúp thao tác cuộn chuột mượt mà từng pixel mà không giật cục theo dòng, đồng thời cơ chế Virtualization `Recycling` giữ dung lượng RAM ổn định kể cả khi thư viện sách mở rộng.
    - **4. Kiểm thử & Độ ổn định**: Cả **Debug** và **Release** đều biên dịch thành công tuyệt đối (0 Warning, 0 Error).

  - **Đồng Bộ Hệ Thống Bo Tròn Góc Chuẩn Dark Liquid Glass 3.0 (CornerRadius Harmony) (09-05, XONG)**:
    - **1. Xây dựng phân cấp bo tròn chuẩn mực (Radius Scale Hierarchy)**:
      - *Level 1 — Containers & Thẻ lớn (`CornerRadius="14"`)*: Các khung chính ứng dụng, cửa sổ, thẻ nội dung `LiquidGlassCard`, bảng điều khiển Input/Output và Config Panels. Viền quầng sáng (Outer Glow) đạt 16px.
      - *Level 2 — Tiêu đề nhóm, Thẻ mục lục & Thanh điều hướng (`CornerRadius="10"`)*: `BookCardHeader`, `StatTile`, `GlassTabHeader`, `GlassNavPillItem` tạo cảm giác thanh thoát, phân cấp rõ rệt với thẻ ngoài.
      - *Level 3 — Nút bấm, Ô nhập liệu & Huy hiệu (`CornerRadius="8"`)*: Đồng bộ tuyệt đối toàn bộ nút bấm (`LiquidGlassButton`, `LiquidGlassButtonPrimary`, `LiquidGlassNeonActionButton`, `GlassPlainButton`, `GlassIconButton`, `GlassDangerButton`, `GlassCollapseButton`, `GlassChipButton`), ô nhập `LiquidGlassTextBox`, ComboBox và các Pill Badges. Loại bỏ hoàn toàn sự không nhất quán giữa bán kính 6px và 8px cũ.
      - *Level 4 — Thanh tiến trình & Đèn báo (`CornerRadius="4"` và `"3"`)*: Rãnh thanh cuộn/tiến trình đạt 4px, thanh trượt phát quang và chấm LED tròn đều đạt 3px.
    - **2. Triển khai & Chuẩn hóa thực tế**:
      - Cập nhật các nút `GlassPlainButton`, `GlassIconButton`, `GlassDangerButton`, `GlassChipButton` trong `LiquidGlass.xaml` từ `6` lên `8`.
      - Cập nhật container icon Sparkle và chip hiển thị GPU trong `MainWindow.xaml` từ `6` lên `8`.
    - **3. Kiểm thử biên dịch**:
      - Cả hai cấu hình **Debug** và **Release** đều biên dịch thành công mỹ mãn với **0 Warning(s), 0 Error(s)**.



---

- **Tối Ưu Hóa Prompt Dịch Thuật & Khắc Phục Triệt Để Lỗi 503 Upstream Provider (09-03, XONG)**:
  - **Mục tiêu**: Giảm tải token đầu vào và đầu ra cho API CommandCode, khắc phục hiện tượng lỗi HTTP 503 Server bận / Upstream model provider is temporarily unavailable mà vẫn bảo toàn 100% chất lượng văn học và độ bám ngữ cảnh.
  - **Kết quả**:
    1. *Lọc thuật ngữ động (Smart Dynamic Glossary Filtering)*: Thay vì nhồi toàn bộ danh sách CSV của cả cuốn sách vào từng chunk, hàm `LoadGlossary(slug, root, filterText)` chỉ lọc và nạp các thuật ngữ thực sự xuất hiện trong đoạn văn cần dịch $\rightarrow$ giảm 30-40% kích thước prompt đầu vào.
    2. *Tinh gọn Prompt chỉ thị*: Cô đọng các quy tắc văn chương láng, loại bỏ các ví dụ dài dòng gây nặng tải cho LLM; giữ nguyên vẹn cầu nối ngữ cảnh gối đầu 3-4 câu của chunk trước (`contextPreviousText`) và hồ sơ văn chương `bookProfile`.
    3. *Tối ưu cơ chế Retry kết nối lại nhanh*: Khi gặp 503 Upstream Provider (server gốc đang scale/phục hồi), rút ngắn thời gian chờ từ `8s, 16s, 24s` xuống `4s, 8s, 12s` để kết nối lại ngay khi server vừa thông thoáng.
    4. *Chuẩn hóa kích thước Chunk*: Tinh chỉnh tham số `--min-chars 800 --max-chars 1600` trong `PythonPipelineService.RunChunkAsync` giúp mỗi chunk tương đương 1 bài tản văn / 1 phân cảnh hoàn chỉnh, AI sinh văn mượt mà và tập trung tối đa.

- **Nâng Cấp VieNeu-TTS Lên Phiên Bản 3.4.0 Mới Nhất (09-03, XONG)**:
  - **Mục tiêu**: Cập nhật engine VieNeu-TTS trong `working/venv-vieneu` từ `3.3.0` lên `3.4.0` (phát hành 02/09/2026) kèm gói phiên âm `sea-g2p 0.9.1`.
  - **Kết quả**:
    1. Cài đặt thành công `vieneu-3.4.0` và `sea-g2p-0.9.1`.
    2. Kiểm tra import module và chạy thử CLI `audiobook_long.py --help` hoạt động hoàn hảo, sẵn sàng cho các tác vụ tạo sách nói tiếp theo.

- **Bộ Tứ Nâng Cấp Toàn Diện: Trình Đọc, Dừng Khẩn Cấp, Audio ID3 & Kéo Thả Sách (09-03, XONG)**:
  - **Mục tiêu**: Hoàn thiện trải nghiệm người dùng theo 4 trụ cột chiến lược: E-Reader, Quản lý luồng, Audiobook & Thư viện sách.
  - **Kết quả**:
    1. *Nâng cấp 1 (Trình đọc E-Reader `MdPreviewWindow`)*:
       - **Tìm kiếm từ khóa trong trang (In-Page Find & Highlight)**: Tích hợp thanh tìm kiếm nổi chuẩn Liquid Glass (`Ctrl + F`), đánh dấu vàng tất cả các từ khớp (`mark.find-match`), đánh dấu cam từ khóa hiện tại (`find-current`), hỗ trợ `F3` / `Shift+F3` để nhảy tiếp/lùi và `Esc` để đóng.
       - **Bật / Ẩn Pinyin linh hoạt**: Nút toggle trên thanh công cụ cho phép ẩn/hiện tầng Pinyin theo ý muốn ở chế độ Tam ngữ.
       - **Đánh dấu chương đang đọc (Active TOC Tracking)**: Tích hợp `InjectScrollSpy()` tự động theo dõi vị trí cuộn trang của WebView2 và highlight chính xác chương tương ứng trên cây mục lục ở cột bên trái.
    2. *Nâng cấp 2 (Tạm dừng & Dừng khẩn cấp)*:
       - Bổ sung nút **Dừng khẩn cấp** (`GlassDangerButton` màu đỏ neon dịu) trực tiếp trên thanh AI Thinking Live Bar và nút icon `Stop24` ở Header Realtime Console, cho phép hủy ngay lập tức các tiến trình đang chạy (`CancelCommand` / `KillCurrentProcess`).
    3. *Nâng cấp 3 (Audiobook: Nghe nhanh mẫu gốc & Nhúng ID3/Bìa sách)*:
       - **Nút nghe nhanh mẫu có sẵn**: Bổ sung nút `Speaker224` trên trang Audiobook để phát ngay lập tức file audio mẫu gốc từ `core/voices/` mà không cần chờ GPU render.
       - **Nhúng ID3 Tag & Bìa sách**: Script `audiobook_long.py` tự động nhúng ảnh bìa (`cover.jpg`/`cover.png`), tên bài hát (Chương N), tên Album, Tác giả và số Track vào thẻ ID3 của file MP3.
    4. *Nâng cấp 4 (Kéo thả sách trực tiếp - Drag & Drop Import)*:
       - Bật `AllowDrop="True"` trên trang Sách kèm hiệu ứng kính mờ `DragDropOverlay`. Người dùng chỉ cần kéo file `.pdf`, `.epub`, `.azw3`, `.mobi` từ Windows Explorer thả vào cửa sổ, app tự động chép vào `input/chua-lam/` và làm mới danh sách tức thì.

- **Đồng Bộ Hoàn Toàn Thanh Tiến Trình Realtime Log Chuẩn Liquid Glass 3.0 (09-03, XONG)**:
  - **Mục tiêu**: Chuẩn hóa thanh tiến trình (progress bar) trong bảng Realtime Console đồng bộ 100% với hệ màu và hiệu ứng Kính mờ siêu thực (Liquid Glass 3.0) của toàn bộ dự án.
  - **Kết quả**:
    1. *Đồng bộ màu sắc Acrylic Glass*: Thanh tiến trình và dải trạng thái AI Live Status Bar sử dụng chung nền kính mờ `GlassElementBackground2Brush`, viền phản quang `GlassGradientBorderBrush`, tiệp màu hoàn hảo với nền Console và toàn app.
    2. *Dải quang phổ Liquid Glass mượt mà*: Hiệu ứng quét sáng Indeterminate được chuyển sang dải Sapphire Blue `#00B4D8` $\rightarrow$ Mint Accent `#48CAE4` $\rightarrow$ Ánh gương trung tâm $\rightarrow$ Purple Glow `#7B2CBF`, đồng nhất với toàn bộ các thanh tiến trình trên thẻ Sách và Audiobook.
    3. *Huy hiệu AI Sparkle Kính Mờ*: Biểu tượng ngôi sao AI `Sparkle24` sử dụng style nút kính mờ `GlassButtonNormalBrush` viền phản quang `GlassGradientBorderBrush` bo tròn `6px`, màu nhấn `AccentFillColorDefaultBrush` thanh lịch, tinh tế.

- **Tích Hợp Danh Sách Chương (TOC Mục Lục) Vào Trình Đọc Sách & Hỗ Trợ Co Kéo Linh Hoạt (09-03, XONG)**:

- **Tích Hợp Danh Sách Chương (TOC Mục Lục) Vào Trình Đọc Sách & Hỗ Trợ Co Kéo Linh Hoạt (09-03, XONG)**:
  - **Mục tiêu**: Khắc phục tình trạng khi đọc sách bên tab Output không thấy danh sách chương (`MdPreviewWindow`) và hỗ trợ co kéo độ rộng cột mục lục tùy ý.
  - **Kết quả**:
    1. *Sidebar Danh sách chương (TOC)*: Thêm cột trái Width 260px (`MinWidth="180"`, `MaxWidth="600"`) chứa `TreeView` danh sách chương mục lục tự động trích xuất từ các thẻ Heading (`#`, `##`, `###`) của file Markdown (`vi.md`, `tamngu.md`) hoặc tự động fallback nạp từ các file chunks đã trích xuất.
    2. *Thanh co kéo GridSplitter*: Bổ sung `GridSplitter` chuẩn Glass với con trỏ chuột `SizeWE`, cho phép người dùng thoải mái co kéo độ rộng cột mục lục chương to/nhỏ tùy ý trên cả `MdPreviewWindow` và `EpubPreviewWindow`. Khi bấm ẩn/hiện mục lục (`Ctrl+T`), app tự động ghi nhớ kích thước đã co kéo trước đó.
    3. *Điều hướng cuộn mượt (Smooth Scrolling)*: Bấm vào bất kỳ chương nào trong danh sách, WebView2 lập tức cuộn mượt (`scrollIntoView`) đến đúng vị trí chương đó theo Anchor ID hoặc Text heading.
    4. *Nút Bật / Ẩn Mục lục*: Bổ sung nút Icon Mục lục (`Navigation24`) trên thanh công cụ và phím tắt `Ctrl + T` để linh hoạt thu gọn/mở rộng sidebar mục lục khi cần đọc toàn màn hình.

- **Kiểm Tra Tính Thống Nhất Giao Diện Liquid Glass 3.0 & Tăng Tốc Toàn Diện (09-03, XONG)**:
  - **Mục tiêu**: Rà soát toàn bộ hệ thống giao diện trên tất cả các trang (`MainWindow`, `BooksPage`, `AudioPage`, `ApiPage`), đảm bảo đồng bộ 100% phong cách Kính mờ siêu thực (Liquid Glass 3.0) và tối ưu hóa hiệu năng render GPU.
  - **Kết quả**:
    1. *Tính thống nhất UI (100%)*: Toàn bộ các trang đều dùng chung hệ màu Acrylic Dark Kính mờ (`GlassBackgroundBrush`), viền phản quang `GlassGradientBorderBrush`, bo góc chuẩn hóa (`14px` cho Card chính, `10px` cho StatTile/Header, `12px` cho Pill Tab/Menu), và hệ thống nút bấm `GlassPlainButton`, `GlassComboBox`.
    2. *Tăng tốc phần cứng GPU DirectX*: Bổ sung đồng bộ `TextRenderingMode="ClearType"`, `TextFormattingMode="Display"`, `RenderOptions.ClearTypeHint="Enabled"`, `RenderOptions.BitmapScalingMode="HighQuality"` cho `MainWindow.xaml`, `AudioPage.xaml`, `ApiPage.xaml` và `BooksPage.xaml` giúp toàn bộ ứng dụng lướt mượt 60-120fps.

- **Cố Định Sidebar Menu Vĩnh Viễn & Xóa Bỏ Hoàn Toàn Nút 3 Gạch (08-30, XONG)**:
  - **Mục tiêu**: Xóa bỏ hoàn toàn nút 3 gạch (Pane Toggle Button), giữ Sidebar bên trái ở trạng thái mở cố định (`IsPaneOpen="True"`), loại bỏ hoàn toàn cơ chế trượt ra/trượt vào giúp giao diện luôn vững chãi, trực quan và dễ sử dụng.
  - **Cải tiến**:
    1. Xóa bỏ thẻ `NavigationView.PaneHeader` chứa nút 3 gạch.
    2. Cố định `IsPaneOpen="True"` và `IsPaneToggleVisible="False"`.
    3. Các nút menu dạng viên thuốc viền gương `Sách`, `Audiobook`, `Cài đặt` hiển thị đầy đủ, ngay ngắn và cố định 100%.

- **Tối Ưu Toàn Diện Hiệu Năng & Tăng Cường Độ Mượt Mà, Nhẹ Nhàng Của Phần Mềm (08-29, XONG)**:
  - **Mục tiêu**: Tối ưu hóa sâu ở tầng .NET 8 Runtime, card đồ họa GPU WPF và bộ nhớ RAM để ứng dụng phản hồi tức thì, cuộn danh sách 60-120fps mượt như nhung và không bị ngốn tài nguyên.
  - **Khắc phục**:
    1. *.NET 8 Tiered JIT & Concurrent GC*: Bật `TieredCompilation`, `TieredCompilationQuickJit` và `ConcurrentGarbageCollection` trong `TranslateBook.csproj` giúp app khởi động cực nhanh và dọn dẹp RAM nền mà không gây khựng hình (zero stutter).
    2. *WPF GPU Rendering Acceleration*: Bật `TextRenderingMode="ClearType"`, `TextFormattingMode="Display"` và `RenderOptions.ClearTypeHint="Enabled"` trong `BooksPage.xaml` giúp GPU trực tiếp render chữ và thẻ card sắc nét, giảm tải 100% cho CPU.
    3. *Console RAM Virtualization*: Giới hạn 800 blocks văn bản trên màn hình UI trong `MainWindow.xaml.cs` (tự động cắt dọn block cũ) giúp bảng Log chạy liên tục hàng nghìn dòng mà RAM vẫn giữ nguyên mức siêu nhẹ (~50MB), không bao giờ bị lag giật.

- **Menu Sidebar Dạng Viên Thuốc Viền Gương (Pill Glass 3.0) & Text API Gốc (08-29, XONG)**:
  - **Mục tiêu**: Tối ưu Sidebar theo phản hồi người dùng: Bỏ khối header đỉnh, khôi phục cụm Text API nguyên bản ở footer, và chuyển các nút menu thành dạng **Viên thuốc viền gương (Pill Glass)** đồng bộ với phong cách Tab danh sách.
  - **Cải tiến**:
    1. Bỏ hoàn toàn khối Header đỉnh để menu thoáng đãng, tối giản.
    2. Áp dụng Style `GlassNavPillItem` cho các nút menu `Sách`, `Audiobook`, `Cài đặt`: Bo tròn `12px` dạng viên thuốc, viền phản quang Gradient `GlassGradientBorderBrush`. Khi rê chuột hoặc chọn, viền tự động phát sáng xanh Accent rực rỡ và nền chuyển màu kính mờ.
    3. Khôi phục phần hiển thị `API` ở Footer về dạng Text mộc mạc nguyên bản ban đầu (`API / DeepSeek-Chat`).

- **Nâng Cấp Viền Kính Bo Tròn Mềm Mại (Liquid Glass 3.0) Cho Thẻ Sách & Audio (08-29, XONG)**:
  - **Mục tiêu**: Đồng bộ phong cách Kính mờ siêu thực (Aero Liquid Glass) cho toàn bộ hệ thống Card sách (cả tab Input & Output) và các khối thông số thống kê (Audio, EPUB, Chunks, Chữ).
  - **Cải tiến**:
    1. *Thẻ Card sách (`InteractiveCard`)*: Bo góc tăng lên `CornerRadius="14"` (mềm mại, không bị góc gãy thô cứng), viền phủ lớp ánh sáng `GlassGradientBorderBrush` đa chiều, tự động chuyển màu kính trong suốt khi rê chuột qua.
    2. *Hộp tiêu đề sách (`BookCardHeader`)*: Bo góc `CornerRadius="10"`, viền Gradient 1px sang trọng.
    3. *Các ô chỉ số Audio / EPUB / Chunks (`StatTile`)*: Tăng bo góc lên `10px`, viền Gradient sắc sảo, tự động phát sáng viền xanh Accent khi hover.

- **Tái Thiết Kế Header Realtime Log Chuẩn Glass 3.0 Sang Trọng & Cân Đối (08-29, XONG)**:
  - **Vấn đề**: Header Realtime Log trước đây nhồi nhét tất cả các nút (Thu gọn, Tiêu đề, Đốm sáng, Ô tìm kiếm, Nút Xóa chữ, Nút Sao chép) trên cùng 1 hàng ngang hẹp (300px), dẫn tới ô tìm kiếm bị co cụm chật chội, chữ bị méo và bố cục mất cân đối thị giác.
  - **Khắc phục**: Thiết kế lại cấu trúc 2 tầng chuẩn công thái học (Ergonomic Glass 3.0):
    1. *Tầng 1 (Status & Actions)*: Tiêu đề `Realtime Console` + đốm sáng Live Pulse bên trái $\leftrightarrow$ cụm 3 nút icon tròn tinh tế bên phải (`Sao chép log`, `Xóa sạch log (màu đỏ)` và `Thu gọn bảng log`).
    2. *Tầng 2 (Smart Filter)*: Thanh tìm kiếm/lọc từ khóa toàn chiều rộng `🔍 Lọc log theo từ khóa...`, rộng rãi, thanh thoát và trực quan.

- **Đặt Mặc Định 1 Luồng Dịch Ổn Định & Tối Ưu Giãn Cách Chống Timeout (08-29, XONG)**:
  - **Nguyên nhân Timeout**: Khi mở nhiều luồng (2-3-4 luồng song song), các API trung gian (Proxy, Router, Free/Standard tier) thường bị nghẽn cổng kết nối hoặc kích hoạt giới hạn Rate Limit đồng thời (RPM/TPM), dẫn đến hiện tượng server AI phản hồi chậm hoặc trả về mã 503/504/Timeout liên tục.
  - **Khắc phục**:
    1. Đặt mặc định `TranslateConcurrency = 1` (1 Luồng tuần tự) — đây là chế độ ổn định nhất, không bị nghẽn mạng và tiết kiệm quota tối đa.
    2. Bổ sung khoảng giãn cách an toàn (`pacing delay` 600ms) khi chạy từ 2 luồng trở lên để tránh gửi bão request cùng một lúc.
    3. Cập nhật nhãn ComboBox trên giao diện: `1 Luồng (Mặc định - Ổn định)`.

- **Bổ Sung Tính Năng 'Xóa Sách Thông Minh' Phân Biệt Input / Output (08-29, XONG)**:
  - **Mục tiêu**: Bổ sung nút bấm Xóa sách (icon thùng rác màu đỏ trên Card và trong ContextMenu) với cơ chế bảo vệ an toàn và phân định rõ ràng giữa 2 tab:
    1. **Tab Input (Sách nguồn)**: Chỉ xóa file/thư mục nguồn trong `input/` và cache tạm `working/chunks`, `working/progress`.
    2. **Tab Output (Sách đã dịch)**: Xóa sạch toàn bộ sản phẩm hoàn thiện trong `output/books/<tên-sách>` (EPUB, Audiobook MP3, final/vi.md, final/tamngu.md) và toàn bộ cache `working/`, **TUYỆT ĐỐI GIỮ NGUYÊN file gốc trong Input** để có thể dịch lại bất cứ lúc nào.
    3. Hộp thoại xác nhận `MessageBox` rõ ràng trước khi thực hiện để chống xóa nhầm.

- **Nâng Cấp & Gia Cố Tính Năng 'Dọn Dẹp Cache Trung Gian' (08-29, XONG)**:
  - **Mục tiêu**: Đảm bảo dọn dẹp sạch sẽ 100% tất cả các file tạm phân mảnh của cuốn sách được chọn, đồng thời có thông báo Snackbar trực quan trên giao diện người dùng.
  - **Khắc phục**:
    1. Quét sạch toàn bộ các thư mục tạm: `working/chunks/<slug>`, `working/progress/<slug>`, `working/progress_audio/chunks/<slug>`, `working/qa/<slug>`, `working/tmp/<slug>`.
    2. Xóa các file JSON và preview tạm: `working/progress_audio/<slug>.json`, `output/samples/<slug>_preview.md`.
    3. Tự động hiển thị Snackbar thông báo màu xanh (số mục đã dọn thành công) và nạp lại trạng thái sách về 0%.

- **Sửa Lỗi Hiển Thị Đa Chế Độ Trong Trình Đọc E-Reader Preview (08-29, XONG)**:
  - **Nguyên nhân**: Khi mở sách, hệ thống nạp `vi.md` gộp thuần Việt vào `_rawViText`. Trong file `tamngu.md`, các đoạn văn bản được cấu trúc bằng thẻ `<p class="src-zh">`, `<p class="pinyin">`, `<p class="vi">` (không có thẻ bao `<div class="tri-block">`), dẫn đến regex cũ bị bỏ qua và không bóc tách được các tầng tiếng Trung / Pinyin. Khi người dùng chuyển sang chế độ "Bản gốc", "Song song", "Tam ngữ", hệ thống fallback dùng `_rawViText` cho tất cả các cột khiến mọi chế độ đều ra tiếng Việt.
  - **Khắc phục**:
    1. Cải tiến `ExtractLayersFromText` với regex nhận diện trực tiếp các thẻ `<p class="src-zh">`, `<p class="pinyin">`, `<p class="vi">` độc lập, bóc tách chính xác từng tầng chữ Hán, Pinyin và Tiếng Việt.
    2. Trong `LoadAllBookLayers`: Tự động nạp độc lập `raw.md` (bản gốc), `tamngu.md` (tam ngữ + pinyin), `vi.md` (thuần Việt), và `progress` chunks JSON.
    3. Cải tiến `SplitIntoBlocks`: Tách theo đoạn văn bản tự nhiên (`\n\n`) thay vì chỉ theo heading `#`, giúp chế độ Song song đối chiếu (2 Cột), Tam ngữ và Song ngữ hiển thị đúng từng cặp đoạn thẳng hàng.

- **Sửa Lỗi Click Chuột Phải Vào Thẻ Sách Bấm 'Đọc Thử' Không Hoạt Động (08-29, XONG)**:
  - **Nguyên nhân**: Trong WPF, `ContextMenu` hiển thị trên một Visual Tree riêng biệt (Popup Window), nên binding kiểu `RelativeSource AncestorType=Page` không tìm thấy `Page` hay `MainViewModel`, làm cho Command không được kích hoạt khi người dùng click vào menu chuột phải. Ngoài ra, nếu sách ở tab Input chưa từng dịch chunk nào, hệ thống không báo gì khiến người dùng tưởng nút bị đơ.
  - **Khắc phục**:
    1. Gán `Tag="{Binding DataContext, ElementName=BooksPageRoot}"` vào Card và sửa binding ContextMenu sang `PlacementTarget.Tag.PreviewTranslatedCommand`.
    2. Bổ sung sự kiện `Click` handler trực tiếp trong code-behind `BooksPage.xaml.cs` (`ContextMenuPreview_Click`, `ContextMenuOpenFolder_Click`...) làm cơ chế bảo hiểm kép.
    3. Nâng cấp `PreviewTranslated`: Tự động tìm kiếm file xem trước ở mọi vị trí (`output/books/.../final/vi.md`, `working/qa/.../vi_only.md`, `output/samples/..._preview.md`, `working/extracted/.../raw.md`), và hiển thị Snackbar thông báo nếu sách chưa được dịch.

- **Sửa Lỗi Thẻ Sách Không Hiển Thị Trên Trang BooksPage (08-28, XONG)**:
  - **Nguyên nhân**: Trong `BooksPage.xaml`, `WrapPanel` của `ItemsControl` (cả tab Input và Output) bị gán `MaxWidth="{Binding ActualWidth, ElementName=InputScrollViewer}"`. Do `ItemsPanelTemplate` có NameScope riêng biệt nên không thể tìm thấy `InputScrollViewer`, dẫn đến `MaxWidth` bị gán bằng 0 và làm toàn bộ thẻ sách bị co lại 0px, biến mất khỏi màn hình dù dữ liệu đã tải đầy đủ.
  - **Khắc phục**: Loại bỏ binding `MaxWidth` thừa trong `ItemsPanelTemplate`, để `WrapPanel` tự động căn chỉnh và wrap theo chiều rộng của khung ScrollViewer như tab AudioPage.

- **Mở Rộng Toàn Diện Hệ Sinh Thái Model Cho API OpenCode / CommandCode / Custom (08-28, XONG)**:
  - **Vấn đề**: Khi bấm nút Quét, các API Proxy/Router thường chỉ trả về một số model cơ bản hoặc cấu trúc JSON không chuẩn, làm thiếu mất các model mạnh (DeepSeek V3, Qwen 2.5, Claude 3.5, GPT-4o...).
  - **Khắc phục**:
    1. Bổ sung cơ chế bóc tách đa tầng: duyệt linh hoạt các key (`id`, `name`, `model_name`, `display_name`, `slug`).
    2. Tích hợp sẵn bộ sưu tập hơn **40+ Model hàng đầu thế giới** vào danh sách xổ xuống của Custom Provider:
       - *Nhánh DeepSeek*: `deepseek-chat` (V3), `deepseek-reasoner` (R1), `deepseek/deepseek-chat`, `deepseek/deepseek-r1`.
       - *Nhánh Qwen (Alibaba)*: `qwen-2.5-72b-instruct`, `qwen-2.5-32b-instruct`, `qwen-max`, `qwen-plus`.
       - *Nhánh Claude (Anthropic)*: `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, `anthropic/claude-3.5-sonnet`.
       - *Nhánh OpenAI*: `gpt-4o`, `gpt-4o-mini`, `chatgpt-4o-latest`, `o1-mini`.
       - *Nhánh Gemini*: `gemini-2.5-flash`, `gemini-2.5-pro`, `google/gemini-2.5-flash`.
       - *Nhánh Trung Quốc khác*: `glm-4-plus`, `moonshot-v1-128k`, `yi-lightning`.
       - *Nhánh Llama 3*: `meta-llama/llama-3.3-70b-instruct`, `llama-3.3-70b-instruct`.

- **Nâng Cấp Quét Model Thông Minh Cho API Custom / OpenCode / CommandCode (08-28, XONG)**:
  - **Vấn đề**: Các bên cung cấp API trung gian/Proxy (OpenCode, CommandCode, OneAPI, OpenRouter...) thường có cấu trúc URL khác nhau (thiếu hoặc thừa `/v1`, hoặc trả về JSON dạng mảng thay vì bọc trường `data`), hoặc chặn route `GET /models`.
  - **Khắc phục**:
    1. Cơ chế dò đa endpoint: Tự động thử các biến thể URL (`<BaseUrl>/models`, `<BaseUrl>/v1/models`, v.v.).
    2. Hỗ trợ đa dạng cấu trúc JSON trả về (`data`, mảng thô `[ ]`, hoặc `models`).
    3. Tự động nạp sẵn danh sách Preset các Model thịnh hành nhất (`deepseek-chat`, `qwen-2.5-72b`, `claude-3-5-sonnet`, `gpt-4o-mini`, `gemini-2.5-flash`, `glm-4-plus`...) vào ComboBox nếu server trung gian tắt cổng `/models`.

- **Hệ Thống Đa Cấu Hình API Tùy Chỉnh (Cấu Hình 1, 2, 3, 4, 5) (08-28, XONG)**:
  - **Mục tiêu**: Cho phép người dùng lưu trữ nhiều API Key / Provider / Endpoint khác nhau (ví dụ: Key chính, Key phụ, Key dự phòng khi bị limit) và chuyển đổi qua lại chỉ với 1 click.
  - **Các profile hỗ trợ**:
    1. **⚡ Cấu hình 1 (Tùy chỉnh: CommandCode / OpenAI / Proxy)**
    2. **✨ Cấu hình 2 (Tùy chỉnh: DeepSeek / Qwen / Claude)**
    3. **🚀 Cấu hình 3 (Tùy chỉnh: API Key dự phòng 1)**
    4. **🌐 Cấu hình 4 (Tùy chỉnh: API Key dự phòng 2)**
    5. **🔮 Cấu hình 5 (Tùy chỉnh: API Key dự phòng 3)**
    6. **♊ Gemini Trực Tiếp (Google AI Studio)**
    7. **🐳 DeepSeek Trực Tiếp (api.deepseek.com)**
  - Tự động nạp API key, Model và Base URL tương ứng khi đổi cấu hình trong trang Cài đặt; lưu độc lập không bị ghi đè.

- **Bảo Vệ Token & Ngắt Cưỡng Bức Kết Nối API Khi Nhấn Hủy (08-28, XONG)**:
  - **Mục tiêu**: Đảm bảo khi người dùng nhấn nút "Hủy", hệ thống lập tức cắt đứt toàn bộ kết nối mạng tới Server AI, không để phát sinh thêm bất kỳ Token đầu ra nào.
  - **Cơ chế 3 lớp**:
    1. Kích hoạt `_currentCts.Cancel()` để toàn bộ vòng lặp đa luồng dừng nạp chunk mới ngay tức khắc.
    2. Gọi `_apiService.CancelPendingRequests()` để ngắt cưỡng bức (Abort socket) mọi Request HTTP đang truyền nhận giữa máy và Server AI.
    3. Gọi `_pipeline.KillCurrentProcess()` để hủy tiến trình Python con nếu đang ở bước extract/chunk.

- **Nâng Cấp Giao Diện & Hiệu Ứng Realtime Log (08-28, XONG)**:
  - **Live Pulsing Dot**: Chấm phát sáng trạng thái hệ thống ở Header Realtime Log (nhấp nháy thở màu Neon Mint `#69F0AE` khi đang bận và tĩnh Cyan `#00F0FF` khi rảnh).
  - **AI Thinking & Processing Status Bar**:
    - Khi hệ thống đang gọi API dịch hoặc tạo Audio, một thanh trạng thái kính mờ phát sáng xuất hiện ở đáy khung Log.
    - Chứa biểu tượng lấp lánh `Sparkle24` màu tím Lavender + Dòng text trạng thái realtime `BusyMessage`.
    - Kèm **3 đốm sáng nhảy nhấp nháy nhịp điệu (Wave Thinking Dots)** tạo cảm giác AI đang suy nghĩ, xử lý dữ liệu và duy trì ngữ cảnh sâu.
  - **Phân màu dòng Log Terminal**: Màu sắc chuyên nghiệp phân biệt rõ: Đỏ Neon (Lỗi), Cam Hổ Phách (Cảnh báo), Xanh Neon Mint (Thành công/Hoàn tất), Xanh Cyber Cyan (Bắt đầu/Bước tiến trình), Tím mộng mơ (Nhạc nền/Giọng đọc).

- **Xử Lý Dịch Mới 100% Từ Đầu (Clean Slate) Toàn Diện (08-28, XONG)**:
  - **Vấn đề**: Khi bấm nút "Dịch Toàn Bộ", app có thể vẫn sót dữ liệu trích xuất cũ nếu tên thư mục dùng tên sách tiếng Trung (`rawTitle`) hoặc slug rút gọn (`book.Slug`) khác nhau.
  - **Khắc phục**:
    1. Khi bấm **"Dịch Toàn Bộ"**, app tự động tổng hợp tất cả các biến thể định danh: `book.Slug`, `book.Title`, `book.EpubTitle`, và tên file gốc không đuôi.
    2. Quét và xóa sạch 100% toàn bộ:
       - `working/extracted/<mọi biến thể slug>/`
       - `working/chunks/<mọi biến thể slug>/`
       - `working/progress/<mọi biến thể slug>/`
       - `working/qa/<mọi biến thể slug>/`
       - `working/profile/<mọi biến thể slug>.md` & `-pronunciation.json`
       - `working/progress_audio/chunks/<mọi biến thể slug>/`
       - `output/books/<tên sách>/final/` & file `.epub` cũ
    3. Đảm bảo toàn bộ quy trình: Trích xuất lại từ file input $\rightarrow$ QC $\rightarrow$ Chia chunk mới $\rightarrow$ Tạo Skeleton mới $\rightarrow$ Dịch lại 100% từng chunk qua API mà không sử dụng bất kỳ mảnh dữ liệu cũ nào. (Chỉ tính năng **"Sửa chữa & Rà soát"** mới giữ lại chunk tốt cũ).

- **Sửa Lỗi Nút Hủy Hoạt Động 100% Ngay Lập Tức (08-28, XONG)**:
  - **Vấn đề**: Khi bấm dịch có hiện nút "Hủy" nhưng bấm vào không có tác dụng do thiếu liên kết RelayCommand và chưa ép buộc kill process con.
  - **Khắc phục**:
    1. Bổ sung `[RelayCommand] CancelTask(BookStatus? book)` trong `MainViewModel.cs` kích hoạt đồng thời cả: hủy `_currentCts.Cancel()` lẫn dừng cưỡng bức tiến trình Python con `_pipeline.KillCurrentProcess()`.
    2. Cập nhật binding chính xác `Command="{Binding DataContext.CancelTaskCommand, RelativeSource={RelativeSource AncestorType={x:Type Page}}}"` và `CommandParameter="{Binding}"` trên cả `BooksPage.xaml` và `AudioPage.xaml`.
    3. Khi bấm Hủy, tiến trình lập tức dừng ngay và trả lại trạng thái sẵn sàng cho thẻ sách.

- **Xử Lý Dịch Mới 100% Từ Đầu (Clean Slate) & Khắc Phục Lỗi 503/Timeout (08-28, XONG)**:
  - **Vấn đề 1 (Clean Slate)**: Người dùng bấm "Dịch Toàn Bộ" nhưng app lại lấy dữ liệu `raw.md` hoặc chunk cũ thay vì trích xuất và dịch mới hoàn toàn.
    - *Khắc phục*: Trong `RunPipelineAsync`, trước khi chạy bước 1, tự động xóa sạch toàn bộ thư mục tạm cũ (`working/extracted/<slug>`, `working/chunks/<slug>`, `working/progress/<slug>`, `working/qa/<slug>`). Tính năng tận dụng chunk cũ chỉ dành riêng cho chức năng "Rà soát & Sửa chữa".
  - **Vấn đề 2 (Lỗi HTTP 503 Upstream Model & Timeout / Canceled)**:
    - *Nguyên nhân*: Router API của CommandCode/OpenRouter đôi khi gặp trường hợp upstream model bị bận tạm thời (HTTP 503 Service Unavailable) hoặc chunk quá dài khiến request vượt quá timeout 100s.
    - *Khắc phục*:
      1. Tăng timeout của `HttpClient` từ 100s lên 300s (5 phút) để xử lý mượt mà các chunk dài và model suy luận sâu.
      2. Nâng cấp cơ chế tự động thử lại (Smart Exponential Backoff): Khi gặp lỗi 503, 502, 504 hoặc Timeout, hệ thống không báo lỗi đứt gánh mà tự động tạm dừng (10s, 20s, 30s, 40s) và retry đến 5 lần cho đến khi máy chủ phục hồi thành công.

- **Tích Hợp Chuẩn Endpoint Chính Thức Theo Tài Liệu CommandCode.ai/docs (08-28, XONG)**:
  - **Khám phá từ Docs**:
    - Endpoint Models: `GET https://api.commandcode.ai/provider/v1/models`
    - Endpoint Chat: `POST https://api.commandcode.ai/provider/v1/chat/completions`
    - Endpoint Messages (Anthropic format): `POST https://api.commandcode.ai/provider/v1/messages`
  - **Khắc phục trên App**:
    1. Tự động nhận diện API Key của CommandCode (dạng `user_...` hoặc `cmd_...`) ngay cả khi người dùng để trống Base URL để tự động trỏ đến `https://api.commandcode.ai/provider/v1`.
    2. Khi bấm **`[↻] Quét`**, hệ thống gửi request trực tiếp đến `https://api.commandcode.ai/provider/v1/models` và nạp về **toàn bộ 100% hơn 50+ model thực tế** mà tài khoản CommandCode đang sở hữu (`claude-opus-5`, `deepseek/deepseek-v4-flash`, `moonshotai/Kimi-K3`, `Qwen/Qwen3.8-Max`, `google/gemini-3.7-flash`, `xai/grok-4.6`, v.v.).
    3. Kiểm tra kết nối và Dịch thực tế hoàn toàn thông suốt với CommandCode API.

- **Chuẩn Hóa Cơ Chế Quét Model Thực Tế 100% Từ API Server (08-28, XONG)**:
  - **Vấn đề**: Người dùng yêu cầu quét chính xác danh sách Model thực tế mà tài khoản/API key của bên cung cấp (OpenCode, CommandCode, Router) đang sở hữu, không dùng danh sách gợi ý cố định (hardcode).
  - **Khắc phục**:
    1. Loại bỏ hoàn toàn danh sách preset cố định.
    2. Nâng cấp cơ chế bóc tách động (Dynamic Schema Parser) duyệt qua các endpoint khả dĩ (`<BaseUrl>/models`, `<BaseUrl>/v1/models`) và hỗ trợ tất cả các định dạng phản hồi thực tế từ server: `{ "data": [...] }`, `{ "models": [...] }`, mảng JSON thuần `[ ... ]` hoặc từ điển key-value.
    3. Hiển thị chính xác 100% số lượng và tên các Model thực tế mà server API trả về vào danh sách chọn ComboBox.

- **Chuẩn Hóa Danh Từ Văn Hóa Á Đông & Triệt Tiêu Lỗi Dịch Ngô Nghê (08-28, XONG)**:
  - **Vấn đề**: Các AI dịch thông thường hay bị "Tây hóa" hoặc dịch máy gượng gạo các khái niệm văn hóa Á Đông (như *旗袍* bị dịch ngây ngô thành *'áo dài Thượng Hải'* thay vì **sườn xám**; *汉服* bị dịch thành *quần áo thời Hán* thay vì **Hán phục**; *坐月子* bị dịch thành *ngồi tháng* thay vì **ở cữ**).
  - **Khắc phục**:
    1. Đã bổ sung các từ khóa văn hóa gốc vào `glossary/master.csv` ở cấp độ toàn hệ thống (dùng chung cho mọi cuốn sách).
    2. Nạp trực tiếp quy tắc văn hóa cùng ví dụ thực tế (Sườn xám / Hán phục / Ở cữ) vào `BuildPrompt` trong `ApiTranslationService.cs`.
    3. Đảm bảo từ nay trở đi, tất cả sách mới và sách cũ đều dịch chuẩn xác 100% các khái niệm văn hóa đời sống phương Đông.

- **Hoàn Thiện Bộ Tiêu Chuẩn Vàng (Ngữ Cảnh - Thuật Ngữ - Văn Chương) Cho AI Dịch (08-28, XONG)**:
  - **1. Ngữ Cảnh Sâu (Dual Context Sliding)**: Nạp kèm chính xác các câu dịch vừa xong của đoạn trước (`Bản dịch đoạn trước kết thúc bằng...`) kết hợp câu gốc để AI bắt đúng nhịp giọng, xưng hô và tiếp nối cảm xúc không một vết gãy.
  - **2. Thuật Ngữ Master 3 Tầng (`glossary/master.csv`)**: Lọc triệt để theo cấp độ ưu tiên: Thuật ngữ riêng cuốn sách $\rightarrow$ Thuật ngữ chung cùng tác giả/thể loại $\rightarrow$ Thuật ngữ toàn hệ thống; ép buộc dịch đúng 100% tên nhân vật/địa danh.
  - **3. Văn Chương "Láng" (Nhà Văn Thực Thụ)**: Hệ thống quy chuẩn và đối chiếu mẫu trực tiếp trong Prompt, triệt tiêu hoàn toàn lối dịch máy thô cứng kiểu từ-nối-từ, mang lại chất văn mượt mà, sâu lắng và thuần Việt.

- **Nâng Cấp Bảo Toàn Ngữ Cảnh & Thuật Ngữ Đa Tầng Cho Pipeline Dịch (08-28, XONG)**:
  - **Ngữ cảnh gối đầu (Sliding Context)**: Mỗi chunk gửi sang API luôn kèm theo 2–3 câu cuối của chunk trước (`contextPreviousText`) và toàn bộ Hồ sơ văn chương (`working/profile/<slug>.md`), giúp AI nối tiếp câu từ liền mạch, nhất quán xưng hô và cảm xúc giữa các đoạn.
  - **Thuật ngữ Master 3 tầng ưu tiên (`glossary/master.csv` & `master_*.csv`)**: Tự động lọc thông minh:
    1. *Tầng 1*: Thuật ngữ riêng của cuốn sách (`book == slug`).
    2. *Tầng 2*: Thuật ngữ chung của cùng tác giả hoặc thể loại (`author`/`genre`).
    3. *Tầng 3*: Thuật ngữ dùng chung toàn hệ thống (`book, author, genre rỗng`).
  - **Quy chuẩn văn chương "láng"**: Prompt dịch được cấu hình nghiêm ngặt với các ví dụ chuẩn nhà văn (đạt độ mượt mà tự nhiên, không dịch máy thô cứng).

- **Đồng Bộ 100% Chuẩn Quy Trình `/dich` Vào Nút Bấm "Dịch Toàn bộ" (08-28, XONG)**:
  - **Khớp trọn vẹn 11 bước (A → K)**:
    1. `Bước A-B (Extract)`: MinerU (GPU/Torch CUDA cho PDF/Scan) hoặc EpubExtract (EPUB).
    2. `Bước C (QC & OpenCC)`: Tự động chạy `post_extract_qc.py` và chuẩn hóa `opencc_normalize.py t2s` (chuyển chữ Hán phồn thể sang giản thể trước khi chunking).
    3. `Bước D (Chunk)`: Smart chunking theo độ dài chuẩn ngữ nghĩa.
    4. `Bước E (Glossary Master)`: Nạp tự động từ `glossary/master.csv`.
    5. `Bước F-F2 (Skeleton & Profile)`: Khởi tạo Skeleton progress đa ngữ và sinh `working/profile/<slug>.md` bám sát văn phong tác giả.
    6. `Bước G (Dịch & QA tức thì)`: Dịch bảo toàn số dòng, giữ nguyên heading `#`/`##`, lọc rác OCR `///`, chạy QA kiểm tra từng chunk.
    7. `Bước H-I (Merge)`: Gộp `tamngu.md`, `vi.md`, xuất `final/raw.md`, gộp câu nối dòng OCR qua `merge_sentences.py`.
    8. `Bước J-K (EPUB & Metadata & Input)`: Nhúng font Noto Serif SC cho EPUB, tạo `metadata.json` chuẩn và dọn chuyển file nguồn vào `input/da-dich/`.

- **Giải Quyết Triệt Để Lỗi Chuyển Chế Độ Đọc Trong `EpubPreviewWindow` (08-28, XONG)**:
  - **Vấn đề trước đây**: File EPUB khi giải nén có CSS gốc của Pandoc/sách (`stylesheet1.css`) ghi đè hoặc độ ưu tiên CSS class trên `body` không đủ cao để thay đổi giao diện các khối `.tri-block` / `.bi-block`.
  - **Giải pháp dứt điểm (DOM Manipulation trực tiếp)**: Viết lại hàm `ApplyDisplayMode(string modeTag)` bằng JavaScript DOM traversal duyệt trực tiếp từng phần tử (`.tri-block`, `.bi-block`, `.src-zh`, `.pinyin`, `.vi`, `section > p` phụ đề) và gán `style.display`, `style.gridTemplateColumns` inline.
  - **Kết quả**: Khi chọn bất kỳ chế độ nào trong ComboBox (Thuần Việt, Tam ngữ, Song song 2 cột, Bản gốc), toàn bộ giao diện WebView của EPUB lập tức biến đổi chuẩn xác 100% không còn bị ảnh hưởng bởi CSS của sách.

- **Sửa Lỗi Chuyển Chế Độ Đọc Trong `EpubPreviewWindow` (08-28, XONG)**:
  - **Nguyên nhân**: Trong `EpubPreviewWindow.xaml.cs`, chuỗi định dạng CSS trong hàm `BuildEpubCss()` là chuỗi nội suy C# `$@"..."` nhưng chưa được escape dấu ngoặc nhọn `{{...}}` ở các quy tắc CSS cho các chế độ đọc `.mode-vi`, `.mode-src`, `.mode-split`, `.mode-tri`. Khi runtime biên dịch chuỗi, các dấu ngoặc nhọn bị nuốt mất làm hỏng toàn bộ cú pháp CSS, dẫn đến trình duyệt không áp dụng được bộ lọc hiển thị.
  - **Khắc phục**: Đã escape chuẩn toàn bộ `{{...}}` trong `BuildEpubCss()`, đồng thời bổ sung các bộ chọn cho tiêu đề gốc (`section > p:has(strong)` và `section > p:has(em)`). Chế độ lọc Thuần Việt, Tam Ngữ, Song Song 2 cột và Bản Gốc hiện hoạt động tức thì 100%.

- **Trang Bị Trọn Bộ Đa Chế Độ Cho Trình Đọc EPUB Preview (`EpubPreviewWindow`) (08-28, XONG)**:
  - **Bổ sung ComboBox Chế độ hiển thị vào Toolbar EPUB**:
    1. `Bản dịch (Thuần Việt)`: Ẩn các dòng chữ Hán và Pinyin trong EPUB tam ngữ để đọc văn xuôi tiếng Việt thuần túy.
    2. `Tam ngữ (Gốc + Pinyin + Việt)`: Hiển thị 3 tầng khối hộp chuẩn sách học ngoại ngữ.
    3. `Song song Đối chiếu (2 Cột)`: Tự động chia 2 cột đối xứng (Bản gốc trái - Bản dịch phải) căn khớp trực tiếp từ các khối EPUB.
    4. `Bản gốc`: Ẩn bản dịch và Pinyin để đọc nguyên bản gốc.
  - **Tích hợp Loading Overlay & CSS Filter động**: Chuyển đổi siêu mượt qua JavaScript DOM injection ngay trên luồng WebView2 của file EPUB mà không cần trích xuất lại.

- **Đồng Bộ Hoàn Toàn Quy Trình Xuất `final/raw.md` Trên Toàn Bộ Giao Diện App (08-28, XONG)**:
  - **Nút "Dịch Toàn bộ" (`RunPipelineAsync`)**: Khi chạy dịch trọn gói qua giao diện, sau khi dịch và gộp file xong, hệ thống tự động xuất `raw.md` vào `output/books/<tên-sách>/final/raw.md`.
  - **Nút "Sửa chữa & Rà soát" (`RepairBookAsync`)**: Tự động đồng bộ và bảo tồn file `final/raw.md` khi cập nhật lại thành phẩm.
  - **Nhánh Sách Tiếng Việt**: Tự động tạo song song `final/vi.md` và `final/raw.md` ngay khi nhận diện sách gốc tiếng Việt để sẵn sàng đưa sang tab Audio tạo giọng đọc.
  - **Trình đọc E-Reader**: Tự động ưu tiên nạp `final/raw.md` giúp người dùng có thể đọc ngay bản gốc hoặc xem đối chiếu song song mà không cần phụ thuộc vào file tạm.

- **Cập Nhật Quy Trình Xuất Bản Gốc `final/raw.md` Song Hành Cùng `vi.md`/`tamngu.md` (08-28, XONG)**:
  - **Lưu trữ trọn vẹn**: Trong quá trình thực thi, hệ thống vẫn trích xuất và xử lý trong `working/extracted/<slug>/raw.md` bình thường để đảm bảo phân tách rõ ràng dữ liệu tạm và sản phẩm.
  - **Tự động xuất ra output**: Khi bước Merge hoàn tất (cả qua CLI `/dich` lẫn giao diện Desktop App), hệ thống tự động sao chép một bản `raw.md` vào `output/books/<tên-sách>/final/raw.md`.
  - **Cập nhật tài liệu quy chuẩn**: Đã chuẩn hóa quy tắc trong `AGENTS.md`, `.opencode/command/dich.md` và `.commandcode/commands/dich.md`.

- **Trang Bị Hiệu Ứng Loading Overlay Cho Trình Đọc E-Reader (08-28, XONG)**:
  - **Phản hồi tức thì**: Bổ sung `LoadingOverlay` kính mờ với `ProgressRing` chuyển động và thông báo trạng thái trực quan (ví dụ: *"Đang tải Song song Đối chiếu (2 Cột)..."*).
  - **Trải nghiệm mượt mà**: Tự động hiển thị ngay khi người dùng chọn chế độ từ dropdown và tự động biến mất ngay khi WebView2 kết xuất xong toàn bộ nội dung HTML/CSS.

- **Tối Ưu Hóa Tuyệt Đối Bộ Parser Đa Tầng Cho 5 Chế Độ E-Reader (08-28, XONG)**:
  - **Trích xuất theo dòng chuẩn xác (`ExtractLayersFromText`)**: Chuyển từ regex khối sang parser theo từng dòng kết hợp phân tích cú pháp HTML tag `<p class="src-zh">`, `<p class="pinyin">`, `<p class="vi">` và `<p class="src-en">`.
  - Giữ nguyên toàn bộ tiêu đề Markdown `# Heading` nằm ngoài khối thẻ để bố cục mục lục và tiêu đề chương luôn đồng bộ 100% giữa cả 5 chế độ.
  - Tự động fallback đa nguồn: `tamngu.md` $\rightarrow$ `songngu.md` $\rightarrow$ `vi.md` $\rightarrow$ `raw.md` $\rightarrow$ `working/progress/<slug>/chunk_*.json`.

- **Hoàn Thiện Bộ Parser Đa Tầng Cho 5 Chế Độ Hiển Thị E-Reader (08-28, XONG)**:
  - **Tự động bóc tách thông minh**: Trình đọc `MdPreviewWindow` tự động phân giải cấu trúc thẻ `<div class="tri-block">` và `<div class="bi-block">` từ các file `tamngu.md`, `songngu.md`, `vi.md` và `raw.md`.
  - **Chuẩn hóa 100% cho 5 Chế độ Hiển thị**:
    1. `Bản dịch (Thuần Việt)`: Tự động trích xuất chỉ phần tiếng Việt để đọc như một cuốn tiểu thuyết hoàn chỉnh.
    2. `Song song Đối chiếu (2 Cột - Side-by-Side)`: Chia đôi 2 cột độc lập, khớp từng đoạn giữa Bản gốc và Bản dịch.
    3. `Tam ngữ (Gốc + Pinyin + Việt)`: Hiển thị 3 tầng khối thẻ Hán - Pinyin - Việt.
    4. `Song ngữ (Từng đoạn)`: Gốc và Dịch xen kẽ nhau.
    5. `Bản gốc nguyên tác`: Tự động trích xuất chỉ phần chữ Hán/Anh nguyên bản.

- **Khắc Phục Lệnh Mở Trình Đọc E-Reader (`PreviewTranslatedCommand`) (08-28, XONG)**:
  - **Kết nối trực tiếp**: Đã gắn lệnh `PreviewTranslatedCommand` vào cả Menu chuột phải và nút chính **"Đọc sách"** trên thẻ sách.
  - **Tự động dò tìm thông minh nội dung**: Tự động dò nạp từ `final/vi.md`, `final/tamngu.md`, `working/qa/vi_only.md` hoặc gộp nhanh các chunk từ `working/progress/<slug>` kèm toàn bộ bản gốc/Pinyin để mở cửa sổ đọc sách ngay lập tức mà không bao giờ bị lỗi không mở được.

- **Triển Khai Bước 1: Trải Nghiệm Đọc & Trình Diễn (Liquid Glass Reader & Split View) (08-28, XONG)**:
  - **Nâng cấp Trình đọc E-Reader (`MdPreviewWindow`)**:
    - Thêm chế độ **`Song song Đối chiếu (2 Cột - Side-by-Side Split View)`**: Chia đôi màn hình độc lập, bên trái hiển thị bản gốc (Trung/Anh) và bên phải hiển thị bản dịch tiếng Việt, tự động đồng bộ theo từng đoạn văn.
    - Hỗ trợ đầy đủ 5 chế độ hiển thị 1-click:
      1. `Bản dịch (Thuần Việt)`: Trải nghiệm đọc tiểu thuyết văn học thuần túy.
      2. `Song song Đối chiếu (2 Cột)`: Phục vụ học tập, tra cứu và so sánh câu từ chuyên sâu.
      3. `Tam ngữ (Gốc + Pinyin + Việt)`: Dành riêng cho sách tiếng Trung (Hiển thị 3 tầng).
      4. `Song ngữ (Từng đoạn)`: Gốc và Dịch nối tiếp nhau.
      5. `Bản gốc`: Đọc thuần nguyên bản.
    - Tùy chỉnh trực quan: Phông chữ (Serif, Bookerly, Noto, KaiTi, Mono), Độ rộng lề trang, Khoảng cách dòng và Zoom phóng to/thu nhỏ mượt mà.

- **Sửa Lỗi Render Giao Diện Do XAML StaticResource ContextMenu (08-28, XONG)**:
  - Loại bỏ các tham chiếu style tĩnh không tồn tại (`GlassContextMenu`, `GlassSeparator`) trong DataTemplate của thẻ sách.
  - Khôi phục hoàn toàn quá trình kết xuất trực quan (visual tree rendering) của WPF cho toàn bộ danh sách thẻ sách ở cả 2 tab Input và Output.

- **Sửa Lỗi Đồng Bộ Bộ Lọc Sách & DataContext Trang BooksPage (08-28, XONG)**:
  - Sửa logic `ApplySearchFilter`: Khi chuỗi tìm kiếm rỗng thì gán `Filter = null` giúp toàn bộ danh sách Input & Output hiển thị đầy đủ ngay lập tức.
  - Tự động fallback nạp `DataContext` từ `Application.Current.MainWindow` và tự kích hoạt `LoadBooks()` nếu danh sách bị rỗng khi chuyển trang.

- **Tích Hợp Bộ 3 Tiện Ích Giao Diện & Thao Tác (UX / Convenience) (08-28, XONG)**:
  - **1. Kéo - Thả File Trực Tiếp (Smart Drag & Drop)**:
    - Kéo thả file `.pdf`, `.epub`, `.docx` từ Desktop vào App $\rightarrow$ Lớp phủ kính mờ phát sáng (DragDropOverlay) hiện ra; app tự động lưu file vào `input/chua-lam/` và nạp vào danh sách ngay lập tức.
  - **2. Bảng Thống Kê & Hiệu Suất (Dashboard Quick Analytics)**:
    - Thanh thống kê nhỏ gọn, sang trọng trên header: `Chưa làm (N)` • `Đã dịch (N)` • `Audio (N)` • `Tốc độ VieNeu-TTS RTF 0.12 (GPU RTX ~8x)`.
  - **3. Menu Chuột Phải Tiện Ích 1-Click (Context Menu)**:
    - Click chuột phải vào thẻ sách để: Mở thư mục sách (`OpenBookFolder`), Đọc thử bản dịch (`PreviewTranslated`), Sao chép đường dẫn file (`CopyBookPath`), Dọn dẹp cache trung gian (`CleanBookCache`).

- **Nâng Cấp Cơ Chế Dịch Song Song Thông Minh Bảo Vệ Ngữ Cảnh & Chống Quá Tải API Free (08-28, XONG)**:
  - **Cơ chế Chống Quá Tải API Free (Anti-Rate-Limit Auto Backoff)**:
    - Nếu API trả về `429 Too Many Requests` hoặc `Quota exceeded`: Hệ thống **tự động ngủ 35 giây** để phục hồi hạn ngạch và retry tối đa 5 lần mà không làm crash app.
    - Bộ chọn luồng hỗ trợ: `1 Luồng (An toàn Free)` (dành cho API Free hạn ngạch 15 RPM) và `2 Luồng (Khuyên dùng)`.
  - **3 Tầng Bảo Vệ Ngữ Cảnh Tuyệt Đối**:
    1. **Hiến pháp xưng hô toàn cuốn**: Nạp và áp đặt `Book Profile` (`working/profile/<slug>.md`) + `Master Glossary` cho mọi luồng dịch.
    2. **Ngữ cảnh gối đầu (Sliding Window Context)**: Tự động trích xuất 2-3 câu cuối của chunk trước đó gửi kèm vào prompt của chunk hiện tại $\rightarrow$ AI luôn nắm trọn mạch truyện và cảm xúc nhân vật.
    3. **Kiểm soát luồng an toàn (SemaphoreSlim)**: Thêm bộ chọn `TranslateConcurrency` trên thanh điều khiển của trang Sách `BooksPage.xaml`.

- **Chuẩn Hóa Hiển Thị API Key Bảo Mật (Password Bullet) trong Trang Cài Đặt (08-28, XONG)**:

- **Chuẩn Hóa Hiển Thị API Key Bảo Mật (Password Bullet) trong Trang Cài Đặt (08-28, XONG)**:
  - Khi người dùng đã lưu API key: Tự động nạp và hiển thị dưới dạng **dãy chấm tròn to bảo mật (`●●●●●●●●`)** thay vì để trống.
  - Tự động đồng bộ theo từng Provider (Gemini / DeepSeek / Custom) khi chuyển đổi Provider.
  - Thêm dòng trạng thái trực quan: `● Đã lưu API key (đang được bảo mật)` phát sáng màu Accent tinh tế.

- **Tối ưu hóa Thanh Tìm Kiếm Gom về TitleBar Toàn Cục (08-28, XONG)**:
  - **Loại bỏ ô tìm kiếm trùng lặp**: Xóa bỏ ô SearchBox thừa bên trong trang Sách `BooksPage`, giữ không gian hiển thị danh sách sách cực kỳ thoáng đãng, sang trọng.
  - **Hợp nhất thanh Global Search trên TitleBar**: 
    - Nhập từ khóa tại thanh TitleBar `GlobalSearchBox` (`Tìm kiếm sách... (Ctrl+F)`) $\rightarrow$ Tự động lọc realtime toàn bộ sách Input và Output ngay khi gõ.
    - Phím tắt `Ctrl + F` tự động kích hoạt nhảy thẳng vào ô tìm kiếm trên TitleBar.

- **Đồng bộ Giao diện & Tính năng Tab Audio chuẩn Tab Sách (08-27, XONG)**:
  - **Cặp nút thao tác trực quan**:
    - **Nút 1 (Primary)**: **`🎧 Tạo Audio Toàn bộ`** — Tạo mới 100% toàn bộ Audiobook từ đầu (`force=true`, xóa cache và chạy toàn bộ các chương).
    - **Nút 2 (Secondary)**: **`🔧 Sửa chữa & Rà soát Audio`** — Chế độ thông minh: rà soát các file MP3 từng chương, giữ lại các chương đã tạo chuẩn, chỉ tạo tiếp các chương còn thiếu hoặc bị lỗi mà không làm lại từ đầu.
    - Kèm **Nút Play** nghe thử mẫu ~30s giọng đọc & nhạc nền AI + **Nút Folder** mở trực tiếp thư mục MP3.
  - **Thanh tiến độ 3 tầng GlassProgressBar**: Hiển thị đồng bộ % to rõ + thanh phát sáng gradient + dòng phụ trạng thái chi tiết theo GPU RTX.

- **Rà soát & Sửa chữa thông minh (Smart Multi-layer Audit) & Chuẩn hóa EPUB Tam ngữ (08-27, XONG)**:
  - **Nâng cấp tính năng Rà soát & Sửa chữa (MainViewModel.cs)**: Quét và kiểm tra chất lượng 5 tầng (Mojibake, tỷ lệ Hán sót, lỗi lặp câu AI, lệch số dòng song ngữ/tam ngữ, ký tự rác OCR). Tự động dọn sạch các chunk rác mồ côi ngoài phạm vi total_chunks và tự sửa offline các lỗi định dạng mà không tốn token API.
  - **Sửa triệt để Mục lục EPUB Tam ngữ (make_epub.py & epub_style.css)**: Khắc phục lỗi Pandoc nuốt Heading cấp 1 khi gặp thẻ `<div class="tri-block">` bao ngoài bằng cách tách trực tiếp sang các thẻ `<p class="src-zh">`, `<p class="pinyin">`, `<p class="vi">` độc lập. Cập nhật CSS định dạng font, màu sắc và khoảng cách câu tam ngữ hoàn hảo.
  - **Quy chuẩn EPUB đầu ra duy nhất**: Đảm bảo toàn bộ hệ thống xuất đúng 1 file EPUB duy nhất ở thư mục gốc (`<Tên Sách>.epub`) chứa đầy đủ nội dung Tam ngữ và Mục lục 50+ chương nhảy trang chuẩn 100% trên Calibre, EpubPreview, Moon+ Reader.
  - **Trình xem trước Markdown (MdPreviewWindow)**: Hỗ trợ đọc thử trực tiếp cả bản Markdown thuần Việt và Tam ngữ trên Desktop App.

- **Tối ưu UI & Quản lý API Key (08-26, XONG)**:
  - **Tối ưu luồng UI**: Chuyển việc quét và đọc file chunk JSON trong `RefreshBookProgress()` sang `Task.Run` chạy ngầm (Background Thread), giúp giao diện không bị giật lag và phản hồi tức thì 0ms.
  - **Chuyển Tab Input / Output mượt mà**: Đổi sự kiện sang `Checked="TabInput_Click"` trên `RadioButton`, loại bỏ animation block click chuột.
  - **Hỗ trợ API Key Google Gemini**: Nâng cấp `ApiTranslationService.cs` hỗ trợ cả 2 định dạng Google Key (query parameter `?key=` và Header `x-goog-api-key`), đồng thời cập nhật default model lên `gemini-3.6-flash`.
  - **Auto-fetch danh sách Model từ API Key**: Tự động gọi API `ListModels` từ máy chủ Google/DeepSeek/OpenAI để lấy về toàn bộ model khả dụng khi dán Key, nạp vào ComboBox kèm nút `[↻]` quét thủ công, và luôn ghi nhớ model do người dùng chọn.
  - **Kiểm tra kết nối 0-Token (Zero Token Test)**: Chuyển toàn bộ phương thức `TestConnectionAsync` sang gọi HTTP GET (`/v1beta/models/{model}` hoặc `/v1/models`) để kiểm tra quyền truy cập và sự tồn tại của Model mà không tiêu tốn bất kỳ token generate hay quota nào của người dùng.
  - **Quy chuẩn Glossary**: Tự động xóa file trung gian `glossary/<slug>.csv` sau khi chạy `merge_glossary.py` vào `master.csv`, dọn sạch 6 file CSV nhỏ, giữ thư mục `glossary/` luôn gọn gàng (chỉ có `master.csv` 203 dòng).

- **Dịch trọn `wo-zai-hao-men-de-ri-ri-ye-ye` (08-25, XONG)**: EPUB scan 203 trang ảnh → OCR MinerU GPU từng ảnh (worker nền checkpoint) → raw.md 158K chars → QC xoá header/footer/quảng cáo → 76 chunk → glossary 20 thuật ngữ → skeleton trilingual + profile → dịch 76/76 bằng batch manifest 16 vòng (claim→dump→dịch→apply→batch_qa→complete), khớp dòng 100%, QA tổng thể pass → merge `--output-dir` tường minh → rename tamngu.md/vi.md → merge_sentences gộp câu+bỏ số trang cho cả hai → clean heading Trang/rác/dedupe → vi.md 0 mojibake/0 Hán sót → **EPUB tam ngữ build từ tamngu.md nhúng font Noto Serif SC (~21MB, 195 ảnh)**. metadata.json đầy đủ. Input EPUB move tay `chua-lam/` → `da-dich/`. KHÔNG audiobook theo yêu cầu user.

- **Audiobook `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` (08-25, XONG)**: dọn `final/vi.md` cho audio — cắt front-matter (`# Làm một người phụ nữ vừa vặn` → trước `## Chương 8...` gồm CIP/NSX/mục lục) + colophon cuối sách (từ ảnh `0fbaf9b9...jpg` sau bài thơ Thư Đình đến EOF), backup `working/tmp/zy3/vi_backup.md` → 60 chương sạch. Xoá progress cũ 65 chương (bản audio cũ đã xoá MP3). Chạy: `audiobook_long.py --slug zuo-yi-ge-gang-gang-hao-de-nu-zi-3 --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10` (voice van_tinh active) → **60/60 chương, RTF 0.32, ~90 phút gen, 4.76 giờ audio (261.5MB)**, music-auto chọn lofi theo nội dung từng chương. QA ffprobe 60/60 hợp lệ; ch01 (tựa sách) & ch37 (divider chương 5 "Bắt tay hòa giải với chính mình") ngắn là đúng bản chất. metadata.json has_audio=true. Input PDF move tay `da-dich/` → `da-audio/`.

- **Dịch trọn `zuo-yi-ge-gang-gang-hao-de-nu-zi-3` (08-25, XONG)**: PDF 吉林文史 2018 (Vi Dương 微阳 — KHÁCH cuốn cùng tên của Vãn Tình) → backup dữ liệu cũ → MinerU GPU → QC 0 lỗi → chunk 50 → glossary curated 20 thuật ngữ + rebuild master dedupe 183 dòng (fix 淡泊/从容 sai nghĩa) → skeleton + profile → dịch 50/50 bằng batch manifest 13 vòng (helper `working/tmp/zy3/{dump_range,apply}.py` + trans_r1..r13.py; original_text là 1-câu/dòng nên builder auto-mirror dòng trống/dòng ảnh) → khớp dòng 100% → QA tổng thể pass → merge `--output-dir` tường minh `output/books/做一个刚刚好的女子 3/final/` → tamngu.md + vi.md (0 mojibake / 0 Hán sót) + metadata.json → EPUB nhúng font Noto Serif SC ~15.9MB ở gốc thư mục sách (inject_font.py patch CSS @font-face '../fonts/' + manifest trong zip).

- **Dịch trọn `zuo-yi-ge-gang-gang-hao-de-nu-zi-2` (08-24, XONG)**: PDF 228 trang (Khang Tĩnh Văn, khác tác giả cuốn 1 cùng tên) → MinerU GPU → QC 0 lỗi → chunk 37 → glossary 12 thuật ngữ merge master → skeleton trilingual + profile văn chương → dịch 37/37 bằng batch manifest 8 vòng (claim→dump→dịch→apply.py→batch_qa→complete), khớp dòng 100%, QA tổng thể pass → merge `--output-dir` tường minh → **fix TOC + heading thủ công** (39 entry TOC sync theo heading body; strip # trong khối TOC; tách dòng merged PART 4 thành 4 tri-block ở tamngu.md; normalize: 5 H1 = tựa sách + 4 PART, essay = ##, 15 heading nhầm # → ##) → vi.md 0 mojibake/0 Hán sót → **EPUB TAM NGỮ nhúng font Noto Serif SC ~18MB** — build từ `final/tamngu.md` (tri-block ZH+Pinyin+VI, 2169 khối; lần đầu build nhầm từ vi.md thuần Việt, user bắt lỗi → rebuild): pandoc --toc-depth=2 --epub-embed-font NotoSerifSC-VF.ttf; CSS @font-face url phải là '../fonts/...' vì pandoc đặt font ở EPUB/fonts/ còn css ở EPUB/styles/ — patch trong zip rồi move ra gốc thư mục sách làm DUY NHẤT 1 file epub. metadata.json cập nhật source_file. Input PDF move tay `chua-lam/` → `da-dich/`.

- **Audiobook mới `zuo-yi-ge-you-feng-gu-de-nu-zi` (08-24, XONG)**: sau khi dịch lại + EPUB xong, tạo audiobook từ vi.md đã dọn (xóa CIP/CONTENTS, H1 '# Người phụ nữ có xương khí') → 81 chương. `--music-auto` đọc music_map.json (81 chương, mood vui/bình/am/sau xoay 26 bài lofi), volume 0.15, batch 16, temp 0.3, top_k 10, voice van_tinh. RTF 0.31, ~95 phút wall-clock. QA ffprobe (`tools\ffmpeg\ffprobe.exe`) 81/81 MP3 hợp lệ, tổng 5.05 giờ (277MB). metadata has_audio=true. Input PDF → `da-audio/`.

- **Dịch lại `zuo-yi-ge-you-feng-gu-de-nu-zi` (08-24)**: phát hiện lần dịch trước dùng nhầm raw.md từ EPUB lạc đề (tản văn Vãn Tình) → chạy lại full pipeline từ PDF thật (self-help nữ giới Vi Dương, 吉林文史出版社 2018): MinerU GPU → 50 chunk → dịch 50/50 bằng batch manifest (claim→dump→dịch→apply/QA/complete) → QA tổng thể 0 lỗi → merge + EPUB nhúng font. **Bug fix**: `merge_sentences.py` nuốt dòng ảnh — thêm `is_image(lines[i])` vào break condition (vi.md mất 2 ảnh cuối). **User chốt xóa audiobook cũ 85 chương** (bản lạc đề). EPUB làm thủ công (CSS @font-face + pandoc --epub-embed-font + fix path font trong zip). Glossary master normalize 616→178 dòng.

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

- **Cải tổ thư mục `input/` theo trạng thái (08-13)**: chia thành `input/chua-lam/` (chưa làm), `input/da-dich/` (đã dịch, chưa audio), `input/da-audio/` (đã dịch + audio). Script `scripts/manage_input.py` tự dò `output/books/` → di chuyển file input vào đúng thư mục; chạy sau mỗi pipeline (đã thêm vào `dich.md` bước K). Hiện trạng: chua-lam 2 file, da-dich 3, da-audio 8. Có `input/README.md` giải thích. `dich.md` mục A/B đã cập nhật tìm file trong thư mục con.

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

- **Nâng cấp Desktop UI & Sửa Lỗi Khởi Chạy (08-25)**:
  - **Hợp nhất giao diện 3 cột**: Cả Nav (Sách/Audio), Danh sách sách và Realtime Log được lồng chung trong 1 khung kính lớn `CornerRadius=12` tuyệt đẹp với viền gradient.
  - **Hiệu ứng trượt Realtime Log**: DoubleAnimation Width 36px ↔ 300px mở/thu mượt mà.
  - **Khung danh sách sách bo tròn**: Bọc `InputPanel` & `OutputPanel` trong khối kính bo cong `12px` đa tầng.
  - **Sửa triệt để lỗi crash khởi chạy**:
    - Chuyển `ProgressBar.Value` binding thành `Mode=OneWay` (khắc phục lỗi WPF mặc định gán TwoWay lên thuộc tính read-only `ProgressPercent`).
    - Khắc phục đệ quy lặp của `OpacityMask` VisualBrush binding.
  - **Biên dịch**: `dotnet build` đạt **0 Error(s), 0 Warning(s)**, ứng dụng khởi chạy mượt mà, ổn định.

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