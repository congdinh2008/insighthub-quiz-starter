# ADR-004: AI Job framework dùng chung, đồng bộ trong request, khóa theo người dùng

Trạng thái: Accepted | Ngày: 04/10/2026 | Người quyết định: người bảo trì Starter (learner-r1.3)

## Bối cảnh

Hỏi đáp và các công cụ AI cùng chịu một bộ quy tắc của SRS:

| Quy tắc | Nội dung |
| --- | --- |
| Mục 3.3.2 | Kiểm idempotency trước khi tính lượt mới. Cùng key cùng dữ liệu trả thao tác cũ, khác dữ liệu báo xung đột. Lưu snapshot đầu vào của lần tiếp nhận đầu |
| LIM-10 | Mỗi người dùng tối đa 1 tác vụ AI đang chạy và 10 yêu cầu mới trong 60 giây, tính chung hỏi đáp và công cụ. Request bị từ chối không tính lượt |
| LIM-11 | Hỏi đáp 60 giây, công cụ AI 120 giây. Retry nội bộ và restart không gia hạn |
| LIM-12 | Key giữ tối thiểu 24 giờ. TTL độc lập với dữ liệu nghiệp vụ |
| BR-08, BR-09 | Nguồn, Notebook hoặc hội thoại đích bị xóa trước khi lưu thì không công bố kết quả |
| IH-INT-004-AC02 | Kiểm hai request đồng thời, key trùng khác dữ liệu, hết phiên, xóa trong lúc chạy, quá hạn |

Starter rc.3 đã có mẫu `operation_records` (ADR-003) cho upload và chat, nhưng key là toàn cục, không có quota và không có điểm kiểm điều kiện trước khi công bố. Nếu mỗi học viên tự tổng quát hóa mẫu này, phần đồng thời dễ sai (replay chéo người dùng, vượt quota khi hai request đến cùng lúc) và lấy thời gian khỏi trọng tâm LLM feature.

## Phương án

| Tiêu chí | A: Bảng `ai_jobs`, đồng bộ trong request, advisory lock theo người dùng | B: Queue và worker nền | C: Mở rộng `operation_records` |
| --- | --- | --- | --- |
| Đáp ứng AC | Đủ LIM-10 đến LIM-12, BR-08 qua hook policy | Đủ, thêm khả năng chạy dài | Thiếu cột người dùng, quota, usage. Phải đổi constraint của bảng đang dùng |
| Bảo mật và quyền | Người dùng từ phiên, policy mặc định từ chối | Như A, thêm bề mặt broker | Phải đổi khóa duy nhất, dễ hồi quy upload |
| Độ phức tạp, testability | Một transaction, test bằng hai luồng và PostgreSQL thật | Thêm broker, worker, retry ngoài request | Thấp về số bảng nhưng trộn hai ngữ nghĩa |
| Vận hành, backup/restore | Không thêm dịch vụ | Thêm dịch vụ cần giám sát | Không thêm dịch vụ |

## Quyết định

Chọn A. Bảng `ai_jobs` (migration 005) và module `api/app/core/ai_jobs.py`:

- `accept_job` chạy trong một transaction có `pg_advisory_xact_lock` theo `user_id`, theo thứ tự: dọn job quá hạn, nhả key hết hạn, kiểm idempotency, kiểm job đang chạy, kiểm cửa sổ 60 giây, ghi job `Processing` cùng `deadline_at` tuyệt đối.
- `run_job` chạy executor trong deadline còn lại, lỗi chuyển `Failed` với mã ổn định.
- `publish` khóa dòng job, kiểm còn hạn, gọi `policy.can_publish` và `write_result` trong cùng transaction.
- `JobPolicy` mặc định `DenyAllPolicy`. Học viên đăng ký policy theo loại job.
- Đồng bộ trong request như ADR-001. Client mất kết nối đối soát bằng `GET /ai-jobs/{id}` hoặc theo key.
- Chat của Starter giữ trên `operation_records`. Trong R1 của bài tập, Chat không chuyển vào `ai_jobs` (mã D8, đính chính 04/10/2026 tại mục Nhật ký).

## Hệ quả

- Tích cực: một bản cơ chế đã test cho cả lớp. Học viên tập trung vào executor, schema đầu ra, policy và Output.
- Tiêu cực và rủi ro còn lại:
  - Request giữ kết nối tới 120 giây. Proxy web đặt timeout 125 giây (`web/lib/jobs-server.ts`).
  - Khóa theo người dùng tuần tự hóa các lần tiếp nhận của cùng người, không ảnh hưởng người khác.
  - Startup đánh dấu mọi job `Processing` là `interrupted`, giả định một tiến trình API. Chạy nhiều worker cần thiết kế lại (ADR mới).
  - Chat chưa nằm trong `ai_jobs` thì LIM-10 chưa tính chung hỏi đáp và công cụ. Trong bài tập R1, đây là phạm vi đã chốt (mã D8), không phải việc học viên phải tích hợp.
  - `notebook_id` chưa có khóa ngoại; học viên thêm khi tạo bảng Notebook.
- Test chứng minh: `api/tests/test_integration.py` các test `test_ai_job_*` (hai request đồng thời, key trùng khác dữ liệu, quota không tính request bị từ chối, quá hạn giải phóng suất và chặn công bố, fence rollback kết quả, endpoint kiểm phiên, chủ sở hữu và policy, restart). `api/tests/test_unit_ai_jobs.py` cho envelope lỗi và giả lập lỗi provider.

## Điều kiện xem lại

Mở lại quyết định và chuyển sang phương án B (queue và worker nền) khi có một trong các điều kiện:

| Điều kiện | Ngưỡng | Lý do |
| --- | --- | --- |
| Cần chạy hơn một tiến trình API | Bất kỳ | Startup đánh dấu `interrupted` giả định một tiến trình |
| Proxy hoặc hạ tầng phía trước không giữ được kết nối | Timeout dưới 125 giây | Request đồng bộ giữ kết nối tới deadline 120 giây |
| Thời gian chờ tác vụ AI tăng | p95 vượt 60 giây trong 7 ngày | Người dùng giữ kết nối lâu, tăng tỉ lệ mất phản hồi |
| SRS cho phép nhiều tác vụ AI đồng thời mỗi người dùng | Thay đổi LIM-10 | Khóa theo người dùng không còn phù hợp |

Contract phía client (gửi job, đối soát theo id hoặc key, polling trạng thái) giữ nguyên khi chuyển sang B.

## Nhật ký

- 04/10/2026 (Requirements 1.3): Chat ở lại `operation_records` trong R1 của bài tập để cân tải tự học; LIM-10 áp dụng cho Summary và Quiz (mã D8). Quyết định A không đổi; dòng về Chat ở mục Quyết định đã đính chính (trước đây yêu cầu học viên đưa Chat vào `ai_jobs` ở M3.1).

## Vai trò của AI

AI đề xuất cấu trúc module và bộ test. Người bảo trì giữ thứ tự kiểm theo mục 3.3.2, bác bỏ phương án queue (ngoài phạm vi ADR-001) và phương án tự sinh key ở server, kiểm độc lập bằng test đồng thời trên PostgreSQL.
