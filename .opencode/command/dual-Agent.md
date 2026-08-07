---
description: Dual-Agent: analyzer plan → executor implement → tối đa 2 vòng review/sửa, cân bằng chất lượng và chi phí
agent: build
---

Điều phối nhiệm vụ `$ARGUMENTS` theo workflow đồng bộ:

```text
Vòng 1: analyzer plan → executor implement → analyzer review 1
Nếu review 1 NEEDS_CHANGES:
Vòng 2: executor sửa → analyzer review 2 → kết thúc
```

`PLAN`, `RESULT`, `REVIEW_1`, `REVIEW_2`, `BASE_STATUS`, `BASE_DIFF`, `NEW_CHANGED_FILES` chỉ là ký hiệu mô tả trong context, không phải runtime variables.

## Quy tắc giới hạn vòng — BẮT BUỘC

- `review_count` bắt đầu bằng `0`.
- Sau review đầu tiên, đặt `review_count = 1`.
- Chỉ khi output review 1 có dòng chính xác `FINAL_STATUS: NEEDS_CHANGES` mới gọi executor sửa một lần.
- Sau khi executor sửa, gọi analyzer review cuối và đặt `review_count = 2`.
- Khi `review_count = 2`, bắt buộc kết thúc dù review 2 là `APPROVED`, `NEEDS_CHANGES`, lỗi hoặc timeout.
- Không gọi executor lần sửa thứ hai.
- Không gọi analyzer review lần thứ ba.

## Quy tắc chờ executor — BẮT BUỘC

- **Chờ executor hoàn tất KHÔNG giới hạn thời gian**: gọi executor và đợi đến khi nó trả kết quả, dù chậm bao lâu. Không đặt timeout cắt ngang.
- Không hủy executor giữa chừng vì "chạy lâu" — chỉ dừng khi executor tự trả `FINAL_STATUS: BLOCKED` hoặc kết thúc công việc.
- Nếu executor chậm nhưng vẫn đang hoạt động, tiếp tục đợi; không retry thêm một executor khác trong khi executor hiện tại chưa xong.
- Giới hạn vòng review (2 vòng) là giới hạn về **số vòng**, không phải giới hạn thời gian chờ.

## Quy tắc giám sát executor — BẮT BUỘC

- **Phân biệt "đang chạy" với "đã chết"**: không được ngầm coi executor chậm là đã lỗi. Chỉ xem executor thực sự ngừng hoạt động khi cơ chế giám sát xác nhận nó kết thúc/mất kết nối, không phải chỉ vì nó lâu.
- **Chạy executor ở chế độ nền (background) và theo dõi trạng thái định kỳ**: gọi `agent_output(status)` để kiểm tra còn sống hay không. Trạng thái hợp lệ là "đang chạy" (chờ tiếp) hoặc "đã trả kết quả cuối" (`COMPLETED`/`BLOCKED`).
- **Khi executor mất kết nối hoặc kết thúc bất thường** (không tự trả `COMPLETED`/`BLOCKED`, hoặc hệ thống báo agent lỗi/dừng): **ngay lập tức dừng workflow và trả `FINAL_STATUS: BLOCKED`** kèm nguyên nhân (mất kết nối / lỗi hệ thống / kết thúc bất thường). Không retry, không gọi analyzer review.
- **Không hủy executor chỉ vì chờ lâu**: chỉ dừng khi có bằng chứng executor đã ngừng hoạt động (lỗi kết nối, kết thúc bất thường). Nếu chỉ chậm, tiếp tục chờ.
- Nếu task dài và quan trọng, có thể yêu cầu executor ghi checkpoint tiến độ vào file sau mỗi bước lớn; nếu lâu không có checkpoint mới, đối chiếu với trạng thái agent để xác định "đứng im" hay "đã chết" rồi xử lý theo quy tắc trên.

## Chế độ Slice — tự động chia plan nhỏ giao từng phần (BẮT BUỘC khi plan dài)

Khi plan tổng dài hoặc nhiều bước, **không giao nguyên cục cho executor**. Thay vào đó chia plan thành nhiều slice giao từng phần, cuối cùng gộp lại vẫn đúng như một plan to.

### Nguyên tắc

- Analyzer vẫn tạo **master plan** (giữ nguyên success criteria tổng, file scope tổng, ngữ cảnh/pattern chung) — đây là thứ đảm bảo kết quả cuối nhất quán.
- Analyzer **cắt master plan thành `# Slices`**: danh sách slice có **thứ tự phụ thuộc** (slice sau chỉ được làm khi slice trước xong), mỗi slice có:
  - Tên + mục tiêu ngắn.
  - File scope con (file nào được đụng trong slice này).
  - Success criteria con (có thể kiểm tra độc lập).
- Mỗi slice nên độc lập nhất có thể (sửa file A trước, file B sau; hoặc nhóm theo module/chương).
- **Slice không chia đôi một file/quyết định chung**: nếu hai slice cùng đụng một file, tách theo giai đoạn (tạo → sửa) để tránh đè nhau.

### Quy trình giao slice

1. Sau khi có master plan + `# Slices`, điều phối lần lượt **từng slice** theo thứ tự.
2. Với mỗi slice: gọi `executor` với **chỉ slice đó** (plan con, file scope con, criteria con), giữ kèm ngữ cảnh chung của master plan (glossary, pattern, quyết định) để nhất quán.
3. Chờ executor slice đó xong (theo "Quy tắc chờ executor" và "Quy tắc giám sát executor").
4. **Xác minh slice**: kiểm tra nhanh criteria con của slice (không tính là vòng review). Nếu slice fail → **chỉ làm lại slice đó** (giao lại executor tối đa 1 lần), không làm lại cả plan.
5. Ghi checkpoint tiến độ (slice nào xong/chưa) — nếu dừng giữa chừng có thể resume từ slice còn thiếu.
6. Sau khi **tất cả slice xong**, mới sang Bước 4 (Git Check + Review 1) đối chiếu **master success criteria** — giới hạn 2 vòng review vẫn giữ nguyên cho review tổng cuối.

### Báo tiến độ cho người dùng

- Trong lúc chờ executor chạy (có thể rất lâu), điều phối **báo tiến độ định kỳ** cho người dùng: `Đang làm slice N/X: <tên slice>` khi bắt đầu mỗi slice, và `Slice N/X xong ✅` khi xác minh xong.
- Nếu dừng giữa chừng, báo rõ: `Đã xong slice N/X, còn lại: ...` kèm checkpoint — để người dùng biết resume từ đâu.
- Không được im lặng chờ executor vô hạn mà không thông báo gì.

### Giới hạn

- Số lần giao lại một slice: **tối đa 1 lần** (nếu lần 2 vẫn fail → dừng, báo `BLOCKED` slice nào hỏng).
- Việc xác minh slice KHÔNG tính vào `review_count` — `review_count` chỉ đếm review tổng (Review 1/Review 2).
- Giữ đủ ngữ cảnh chung giữa các slice; không cắt success criteria tổng, file scope tổng hoặc pattern chung khi tách slice.

### Vị trí manifest slice

- Checkpoint/manifest slice (dùng `scripts/translate/slice_manifest.py`) PHẢI đặt **ngoài thư mục chứa file của task**, ví dụ `working/slice_manifests/<slug>/`.
- Không được tạo manifest bên trong thư mục task (như `working/<task_dir>/manifest/`) — sẽ vi phạm master success criteria "chính xác N file" khi review tổng.
- Khi resume, đọc manifest từ vị trí chuẩn đó để biết slice nào pending/failed còn thiếu.



## Nguyên tắc tiết kiệm nhưng giữ chất lượng

- Analyzer đọc có mục tiêu: entry point, file trực tiếp liên quan, config/dependency và test liên quan; không quét toàn repo.
- Executor nhận đầy đủ plan, success criteria, file scope, pattern cần tuân thủ và test cần chạy; không nhận log/diff lặp lại không liên quan.
- Review 1 nhận diff đầy đủ của file trong scope, kết quả test và các success criteria; không cần chép toàn bộ source nếu diff đã có.
- Review 2 chỉ nhận feedback review 1, diff sau sửa, kết quả test liên quan và success criteria bị ảnh hưởng; không truyền lại toàn bộ lịch sử.
- Không cắt success criteria, file scope, lỗi test hoặc diff của file đang review để tiết kiệm token.

## Bước 1 — Analyze

Gọi `analyzer` qua task tool với `subagent_type="analyzer"` và prompt là toàn bộ `$ARGUMENTS`.

- Chờ kết quả.
- Lưu output làm `PLAN`.
- Nếu lỗi, timeout hoặc thiếu `# Implementation Plan`: trả `FINAL_STATUS: BLOCKED` và kết thúc.

## Bước 2 — Baseline Snapshot

Tại project root, trước executor:

1. Chạy `git status --short` → `BASE_STATUS`.
2. Chạy diff working tree/staged khi phù hợp → `BASE_DIFF`.
3. Ghi danh sách untracked → `BASE_UNTRACKED`.
4. Lưu hash/nội dung baseline của file trong `# Files to Modify/Create`.
5. Nếu không phải Git repository, ghi `Not a git repository`.

Không dùng `git diff --stat` làm nguồn duy nhất vì không thấy untracked files.

## Bước 3 — Execute lần đầu

Gọi `executor` qua task tool với `subagent_type="executor"`, prompt chứa:

- `# Implementation Plan`.
- `# Success Criteria`.
- `# Files to Modify/Create`.
- Các pattern/code context liên quan trực tiếp.
- `BASE_STATUS` và baseline cần thiết.
- Test/build/lint cần chạy.

Không truyền toàn bộ `BASE_DIFF` nếu không liên quan đến file scope.

- Executor chỉ được sửa file trong scope.
- Chờ executor hoàn tất không giới hạn thời gian (xem "Quy tắc chờ executor").
- Lưu output ngắn gọn làm `RESULT`.
- Nếu executor trả `FINAL_STATUS: BLOCKED` (lỗi logic/scope) hoặc hệ thống báo agent lỗi dừng: báo nguyên nhân và kết thúc, không review.

## Bước 4 — Git Check và Review 1

1. Chạy lại `git status --short` và diff.
2. Tính `NEW_CHANGED_FILES`, bao gồm file tracked thay đổi và file untracked mới, bằng so sánh với baseline.
3. Thu thập diff đầy đủ của các file trong scope và kết quả test/build/lint liên quan.
4. Gọi `analyzer` review với:
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
- Chỉ nếu là `NEEDS_CHANGES` mới được sang Bước 5.

## Bước 5 — Executor sửa đúng một lần

Gọi `executor` đúng một lần với payload tối thiểu nhưng đủ bằng chứng:

- `# Files to Modify/Create` và success criteria liên quan.
- Feedback cụ thể từ `REVIEW_1`.
- Diff hiện tại của file cần sửa.
- Kết quả test liên quan.
- BASELINE warning nếu file có thay đổi từ trước.

Không truyền lại toàn bộ PLAN/RESULT nếu feedback đã đủ; chỉ bổ sung phần plan cần thiết để tránh hiểu sai scope.

- Yêu cầu executor chỉ sửa feedback được nêu, không mở rộng scope.
- Chờ executor hoàn tất không giới hạn thời gian (xem "Quy tắc chờ executor").
- Nếu executor trả `FINAL_STATUS: BLOCKED` hoặc hệ thống báo agent lỗi dừng: báo nguyên nhân và kết thúc.
- Không retry executor.

## Bước 6 — Git Check và Review 2 — REVIEW CUỐI

1. Chạy lại Git check và tính `NEW_CHANGED_FILES` so với baseline ban đầu.
2. Thu thập diff sau sửa của file liên quan và test result mới.
3. Gọi analyzer review lần cuối với feedback review 1, success criteria bị ảnh hưởng, diff sau sửa và test result.
4. Lưu output làm `REVIEW_2` và đặt `review_count = 2`.
5. Dù `REVIEW_2` là `APPROVED`, `NEEDS_CHANGES`, lỗi hoặc timeout, bắt buộc kết thúc ngay.
6. Không gọi thêm executor hoặc analyzer.

## Kết quả trả về

Trả cho người dùng:

1. Kết quả executor cuối cùng.
2. Review cuối cùng (`REVIEW_1` nếu review 1 APPROVED; `REVIEW_2` nếu có vòng sửa).
3. `review_count` là `1` hoặc `2`.
4. Nếu dừng do lỗi: `FINAL_STATUS: BLOCKED` và nguyên nhân.

Payload quá lớn chỉ được rút gọn log/output lặp hoặc diff ngoài scope; phải giữ success criteria, file scope, lỗi test, diff file đang review và feedback. Ghi rõ phần đã rút gọn. Giới hạn chính vẫn là số vòng review, không phải số ký tự.
