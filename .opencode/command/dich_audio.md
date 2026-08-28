---
description: Dịch trọn sách + tạo audiobook trong 1 lệnh (toàn bộ pipeline: extract → dịch → merge → EPUB → audiobook). Gộp /dich + /audio.
agent: build
---

Tự động **dịch trọn một cuốn sách VÀ tạo audiobook** — toàn bộ pipeline từ file gốc đến audiobook hoàn chỉnh. Người dùng KHÔNG làm bước thủ công nào. `$ARGUMENTS` có thể là: (1) tên file trong `input/` (VD `ten-sach.pdf`), (2) slug sách đã có chunk (VD `zuo-yi-ge-gang-gang-hao-de-nu-zi`), hoặc để trống.

## Cách chạy
1. **Chạy toàn bộ quy trình `/dich`** (extract → chunk → glossary → profile → dịch → QA → merge → EPUB):
   - Đảm bảo xuất đầy đủ `output/books/<tên-sách>/final/`: `raw.md` (bản gốc), `vi.md` (thuần Việt), `tamngu.md` (hoặc `songngu.md`), và `<tên-sách-input>.epub`.
2. **Chạy toàn bộ quy trình `/audio`** (music_map AI → tạo audiobook GPU → QA → metadata → chuyển input sang `da-audio`) — làm đúng từng bước A→F của lệnh đó.

## Lưu ý
- Nếu sách đã dịch xong (đã có `final/vi.md` và `final/raw.md`): bỏ qua bước dịch, chạy thẳng phần audio (như `/audio`).
- Nếu sách đang dở (có chunk/progress): tiếp tục dịch phần còn thiếu, merge đầy đủ rồi chạy audio.
- Cuối cùng cập nhật `input/` (sách hoàn chỉnh → `da-audio`), in đầy đủ đường dẫn output.
- KHÔNG tự commit/push (theo AGENTS.md) trừ khi người dùng yêu cầu.
