---
description: Tạo audiobook cho một cuốn sách ĐÃ DỊCH (có final/vi.md). Nhạc nền AI chọn theo cảm xúc từng chương (--music-auto đọc music_map.json). Chạy GPU batch 16 + volume 0.15. Chỉ AUDIO, không dịch — dùng /dich để dịch, /dich_audio để làm cả hai.
agent: build
---

Tự động tạo audiobook cho một cuốn sách **đã dịch xong** (có `output/books/<tên-sách-gốc>/final/vi.md`). Bạn chạy mọi thứ. `$ARGUMENTS` có thể là: (1) tên file trong `input/` (VD `ten-sach.epub`), (2) slug nội bộ (VD `qie-yi-qing-shen-gong-bai-tou`), hoặc để trống.

## A. Xác định sách
1. Nếu `$ARGUMENTS` là slug nội bộ → tìm thư mục sách qua `metadata.json` (slug → thư mục tên gốc).
2. Nếu `$ARGUMENTS` là tên file trong `input/` → tìm file ở 3 thư mục con, suy slug qua `scripts\manage_input.py` map thủ công (tên Trung) hoặc khớp chữ Latin.
3. Nếu trống → liệt kê các sách có `final/vi.md` (đã dịch), hỏi người dùng chọn.
4. Xác nhận `final/vi.md` tồn tại — nếu chưa có, báo người dùng chạy `/dich` trước.

## B. Nhạc nền AI theo nội dung (music_map) — TRƯỚC KHI TẠO
1. `--music-auto` đọc `working\progress_audio\music_map.json` (định dạng `{"<slug>": {"<chương>": "file.mp3"}}`).
2. Nếu slug **chưa có** trong music_map → **BẠN (agent) tự phân tích**: chạy `python -c` dùng `scripts\audiobook\audiobook_long.py` hàm `detect_chapters` để lấy danh sách chương + nội dung từ `final/vi.md`, **đọc từng chương** (đầu/miêu tả), chấm cảm xúc (buồn/vui/ngọt/trầm/hài hước/lãng mạn...), chọn 1 bài nhạc phù hợp trong `core/music/` cho mỗi chương → **ghi vào `music_map.json`** (giữ các cuốn cũ). Không cần API — bạn là AI.
3. Nếu slug đã có → dùng nguyên bản đồ.

## C. Tạo audiobook (GPU)
- Chạy:
  ```powershell
  working\venv-vieneu\Scripts\python.exe -u scripts\audiobook\audiobook_long.py --slug <slug> --gpu --batch-size 16 --music-auto --music-volume 0.15 --temperature 0.3 --top-k 10
  ```
- `--gpu` bắt buộc (RTX 3060); `--batch-size 16` chuẩn GPU (nhanh ~2x batch 8); `--music-auto` nhạc nền AI theo nội dung từng chương; `--music-volume 0.15` mức chốt; `--temperature 0.3 --top-k 10` giọng chậm rãi trầm ấm.
- **Resume tự động**: script checkpoint theo chương — dừng giữa chừng (khởi động lại máy...) thì chạy lại lệnh cũ, nó tự bỏ qua chương đã xong.
- Nếu `vi.md` đã đổi (sửa dịch): chạy lại `--chapter <số chương bị ảnh hưởng> --force` để tạo lại đúng phần.
- ⚠️ **Khi dịch LẠI toàn bộ sách (vi.md thay đổi hoàn toàn)** (kinh nghiệm 08-17): **phải xóa MP3 cũ + progress cũ + chunks cache cũ** trước khi chạy, nếu không `reconcile_existing_outputs` thấy file MP3 cũ → bỏ qua mọi chương và thoát ngay (exit 0, không tạo gì). Cụ thể:
  1. Xóa `output/books/<tên-sách-gốc>/audiobook/ch*.mp3` + `*.wav` (Python `os.remove` hoặc `cmd /c rd`).
  2. Xóa `working/progress_audio/<slug>.json` (+ `.bak`).
  3. Xóa `working/progress_audio/chunks/<slug>/` — nếu lỗi Access Denied do OneDrive đặt read-only: `cmd /c rd /s /q "<đường dẫn>"` (hoặc `attrib -R /s /d` trước).
  4. Rồi mới chạy lệnh tạo audio (không cần `--force`, progress đã sạch).
- ⚠️ Khi chạy nền: dùng `-u` (unbuffered) để log không bị nuốt; hoặc chạy trực tiếp terminal.

## D. QA audiobook
- Sau khi tạo:
  ```powershell
  python scripts\qa\audio_qa.py --slug <tên-thư-mục-gốc>
  ```
  ⚠️ **`audio_qa.py` resolve theo TÊN THƯ MỤC GỐC** (vd tên tiếng Trung `且以情深共白头：婚前看情感，婚后靠相处 (晚情)`), KHÔNG dùng slug nội bộ — truyền sai slug sẽ báo thiếu chapter. Báo cáo ghi tại `working/qa/<slug>/audio-report.json`; kiểm tra đủ chapter, file không rỗng, WAV 48 kHz, không clipping.

## E. Cập nhật metadata + input
1. **Cập nhật `metadata.json`**: `has_audio=true`, tự dò `has_epub`/`epub_file` từ thư mục. Ghi bằng Python UTF-8.
2. **Chuyển input → da-audio**: chạy `python scripts\manage_input.py`. Lưu ý: script chỉ quét file ở gốc `input/` — nếu file nằm trong thư mục con (`da-dich/`) thì chuyển thủ công qua Python (`shutil.move`).

## F. Tổng kết
- In đường dẫn: `output/books/<tên-sách-gốc>/audiobook/ch01.mp3...`, `final/vi.md`, `final/tamngu.md` (nếu ZH), `<tên-sách-input>.epub`.
- KHÔNG tự commit/push (theo AGENTS.md) trừ khi người dùng yêu cầu. Hỏi người dùng có muốn commit/push không.
