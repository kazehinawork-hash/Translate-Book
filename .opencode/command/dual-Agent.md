---
description: Dual-Agent tối ưu chi phí: Luna plan theo lô → Laguna thực thi (free, giám sát vô thời hạn) → flash review độc lập
agent: build
---

Điều phối nhiệm vụ `$ARGUMENTS` theo workflow đồng bộ tối ưu chi phí-chất lượng:

```text
Bước 0: Phân loại task
- Task bé (1 file, sửa nhỏ, ít rủi ro) → chạy trực tiếp (không dùng pipeline) — kết thúc.
- Task ≥ trung bình → pipeline 3 vai:
  Bước 1: analyzer (Luna) plan theo LÔ → Bước 2: baseline → Bước 3: executor (Laguna) thực thi từng item
  Bước 4: reviewer (flash) review → tối đa 1 vòng sửa → Bước 5: reviewer review lần cuối
```

`PLAN`, `RESULT`, `REVIEW_1`, `REVIEW_2`, `BASE_STATUS`, `BASE_DIFF`, `NEW_CHANGED_FILES` chỉ là ký hiệu mô tả trong context, không phải runtime variables.

## Bước 0 — Phân loại task (BẮT BUỘC)

Trước khi gọi bất kỳ agent nào, đánh giá `$ARGUMENTS`:

- **Task bé**: sửa 1 file, thay đổi nhỏ, rủi ro thấp, không đụng logic nhiều file → **không dùng pipeline**. Làm trực tiếp như single-agent (đọc → sửa → test → xong). Báo người dùng đã bỏ qua pipeline vì task nhỏ.
- **Task ≥ trung bình**: nhiều file, refactor, thay đổi logic lan rộng, hoặc người dùng yêu cầu review → vào pipeline 3 vai bên dưới.

Tiêu chí "trung bình" nghiêng về chạy pipeline khi nghi ngờ — Luna plan $2.7 chỉ đáng khi task thực sự đáng.

## Bước 1 — Analyze theo LÔ (Luna)

Gọi `analyzer` qua task tool với `subagent_type="analyzer"`, prompt là toàn bộ `$ARGUMENTS` (nếu là lô nhiều task, gom tất cả vào 1 prompt duy nhất để Luna plan 1 lần cho cả lô).

- Chờ kết quả.
- Lưu output làm `PLAN`.
- Nếu lỗi, timeout hoặc thiếu `# Implementation Plan`: trả `FINAL_STATUS: BLOCKED` và kết thúc.

**Nguyên tắc gom lô**: nếu `$ARGUMENTS` chứa nhiều task nhỏ liên quan (vd: "sửa 3 lỗi UI"), gom vào 1 lần plan — Luna chỉ trả tiền 1 lần, chi phí chia đều cho cả lô.

## Bước 2 — Baseline Snapshot

Tại project root, trước executor:

1. Chạy `git status --short` → `BASE_STATUS`.
2. Chạy diff working tree/staged khi phù hợp → `BASE_DIFF`.
3. Ghi danh sách untracked → `BASE_UNTRACKED`.
4. Lưu hash/nội dung baseline của file trong `# Files to Modify/Create`.
5. Nếu không phải Git repository, ghi `Not a git repository`.

Không dùng `git diff --stat` làm nguồn duy nhất vì không thấy untracked files.

## Bước 3 — Execute theo item (Laguna, free)

Nếu plan có `# Batch Items` hoặc `# Slices`: giao executor **từng item/slice** theo thứ tự. Mỗi lần giao chỉ kèm item đó + ngữ cảnh chung của master plan. Chờ xong rồi mới giao item tiếp theo.

Nếu plan nhỏ: giao executor toàn bộ plan một lần.

Prompt cho executor chứa:
- `# Implementation Plan` (hoặc phần item/slice tương ứng).
- `# Success Criteria` (hoặc criteria con của item).
- `# Files to Modify/Create` (hoặc file scope con).
- Các pattern/code context liên quan trực tiếp.
- `BASE_STATUS` và baseline cần thiết.
- Test/build/lint cần chạy.

### Giám sát executor — BẮT BUỘC (Laguna chậm/yếu)

- **Chờ executor hoàn tất KHÔNG giới hạn thời gian**: gọi executor và đợi đến khi nó trả kết quả, dù chậm bao lâu. Không đặt timeout cắt ngang. Không hủy executor giữa chừng vì "chạy lâu" — chỉ dừng khi executor tự trả `FINAL_STATUS: BLOCKED` hoặc kết thúc công việc.
- **Chạy executor ở chế độ nền (background) và theo dõi trạng thái định kỳ**: gọi `agent_output(status)` kiểm tra còn sống hay không. Trạng thái hợp lệ: "đang chạy" (chờ tiếp) hoặc "đã trả kết quả cuối" (`COMPLETED`/`BLOCKED`).
- **Phân biệt "đang chạy" với "đã chết"**: không ngầm coi executor chậm là đã lỗi. Chỉ xem executor thực sự ngừng hoạt động khi cơ chế giám sát xác nhận nó kết thúc/mất kết nối — không phải chỉ vì nó lâu.
- **Khi executor mất kết nối hoặc kết thúc bất thường** (không tự trả `COMPLETED`/`BLOCKED`, hoặc hệ thống báo agent lỗi/dừng): **ngay lập tức dừng workflow và trả `FINAL_STATUS: BLOCKED`** kèm nguyên nhân. Không retry, không gọi reviewer.
- **Laguna là model giá rẻ — kiểm tra kỹ kết quả**: sau khi executor trả `COMPLETED`, xác minh sơ bộ trước khi gửi review: đọc lại file đã sửa (đặc biệt vùng thay đổi), chạy test/build nếu cần. Nếu phát hiện rõ ràng thiếu sót, giao lại executor sửa 1 lần trước khi vào review.
- **Không retry thêm executor khác** trong khi executor hiện tại chưa xong.
- Nếu task dài, yêu cầu executor ghi checkpoint tiến độ vào file sau mỗi bước lớn; nếu lâu không có checkpoint mới, đối chiếu trạng thái agent để xác định "đứng im" hay "đã chết" rồi xử lý theo quy tắc trên.

## Bước 4 — Git Check và Review 1 (flash)

1. Chạy lại `git status --short` và diff.
2. Tính `NEW_CHANGED_FILES` (tracked thay đổi + untracked mới) bằng so sánh với baseline.
3. Thu thập diff đầy đủ của các file trong scope và kết quả test/build/lint liên quan.
4. Gọi `reviewer` qua task tool với `subagent_type="reviewer"` review với:
   - task gốc dạng tóm tắt,
   - `# Success Criteria`,
   - `# Review Focus Areas`,
   - `RESULT` ngắn gọn,
   - `NEW_CHANGED_FILES`, diff đầy đủ trong scope,
   - test result và baseline summary.
5. Output review phải kết thúc bằng chính xác một marker:
   - `FINAL_STATUS: APPROVED`
   - `FINAL_STATUS: NEEDS_CHANGES`

Đặt `review_count = 1`.

- Nếu `APPROVED`: trả kết quả và kết thúc.
- Nếu lỗi, timeout hoặc thiếu marker: trả `FINAL_STATUS: BLOCKED` và kết thúc.
- Chỉ nếu là `NEEDS_CHANGES` mới sang Bước 5.

## Bước 5 — Executor sửa đúng một lần

Gọi `executor` đúng một lần với payload tối thiểu nhưng đủ bằng chứng:

- `# Files to Modify/Create` và success criteria liên quan.
- Feedback cụ thể từ `REVIEW_1`.
- Diff hiện tại của file cần sửa.
- Kết quả test liên quan.
- BASELINE warning nếu file có thay đổi từ trước.

Không truyền lại toàn bộ PLAN/RESULT nếu feedback đã đủ; chỉ bổ sung phần plan cần thiết.

- Yêu cầu executor chỉ sửa feedback được nêu, không mở rộng scope.
- Chờ executor hoàn tất không giới hạn thời gian (theo quy tắc giám sát Bước 3).
- Nếu executor trả `FINAL_STATUS: BLOCKED` hoặc hệ thống báo agent lỗi dừng: báo nguyên nhân và kết thúc.
- Không retry executor.

## Bước 6 — Git Check và Review 2 — REVIEW CUỐI (flash)

1. Chạy lại Git check và tính `NEW_CHANGED_FILES` so với baseline ban đầu.
2. Thu thập diff sau sửa của file liên quan và test result mới.
3. Gọi `reviewer` qua task tool với `subagent_type="reviewer"` lần cuối với feedback review 1, success criteria bị ảnh hưởng, diff sau sửa và test result.
4. Lưu output làm `REVIEW_2` và đặt `review_count = 2`.
5. Dù `REVIEW_2` là `APPROVED`, `NEEDS_CHANGES`, lỗi hoặc timeout, bắt buộc kết thúc ngay.
6. Không gọi thêm executor hoặc reviewer.

## Kết quả trả về

Trả cho người dùng:

1. Kết quả executor cuối cùng.
2. Review cuối cùng (`REVIEW_1` nếu review 1 APPROVED; `REVIEW_2` nếu có vòng sửa).
3. `review_count` là `1` hoặc `2`.
4. Nếu dừng do lỗi: `FINAL_STATUS: BLOCKED` và nguyên nhân.

Payload quá lớn chỉ được rút gọn log/output lặp hoặc diff ngoài scope; phải giữ success criteria, file scope, lỗi test, diff file đang review và feedback. Ghi rõ phần đã rút gọn. Giới hạn chính vẫn là số vòng review, không phải số ký tự.
