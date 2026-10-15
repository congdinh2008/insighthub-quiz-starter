# Hồ sơ vận hành InsightHub R1

Dùng cho LR-26 (M4). Sao chép file này thành `docs/release/Operations_R1.md`. Chỉ dùng dữ liệu giả; log đưa vào AI phải khử secret, cookie, token và dữ liệu cá nhân trước.

Tag: <R1> | Commit: <SHA> | Ngày: <ngày> | Người lập: <tên>

## 1. SLI và SLO

| SLI | Định nghĩa | Nguồn số đo | Giá trị đo |
| --- | --- | --- | --- |
| SLI-1 | <ví dụ: tỷ lệ request trả 5xx trên tổng request> | `insighthub_http_requests_total` tại `/metrics` (nhãn `status`) | |
| SLI-2 | <ví dụ: latency p95 của hỏi đáp> | `insighthub_rag_query_latency_seconds` | |
| SLI-3 | <ví dụ: tỷ lệ AI job `Failed` hoặc tỷ lệ fallback> | Bản ghi usage của IH-AI-005 | |

| SLO | Mục tiêu | Cửa sổ đo | Error budget | Hành động khi vượt |
| --- | --- | --- | --- | --- |
| | | | | |

Cách xem số đo: <lệnh hoặc truy vấn, bảng hoặc dashboard; Grafana là tùy chọn>.

## 2. Diễn tập incident

Giả lập lỗi provider: `inject_provider_faults` trong test, hoặc `AI_FIXTURE_FAULTS=<provider>:<lỗi>` khi chạy thủ công ở chế độ fixture ([AI Job Framework](../AI_Job_Framework.md)).

| Thời điểm | Sự kiện | Nguồn phát hiện | Người xử lý |
| --- | --- | --- | --- |
| | Bắt đầu giả lập lỗi | | |
| | Phát hiện qua SLI hoặc log | | |
| | Giảm thiểu | | |
| | Khôi phục bình thường | | |

| Giả thuyết nguyên nhân do AI đề xuất | Cách tái hiện hoặc bác bỏ | Kết quả |
| --- | --- | --- |
| | | Tái hiện được hoặc bác bỏ, kèm căn cứ |

## 3. Postmortem blameless

| Mục | Nội dung |
| --- | --- |
| Tóm tắt và tác động | |
| Nguyên nhân gốc | |
| Điều đã làm tốt | |
| Điều cần cải thiện | |
| Hành động phòng ngừa | Người phụ trách và hạn |

## 4. Chặn lệnh phá dữ liệu

| Lệnh thử (dữ liệu giả) | Lớp 1 và log | Lớp 2 và log | Kết quả |
| --- | --- | --- | --- |
| <ví dụ: `docker compose down -v`> | <rule `deny` trong `.claude/settings.json`> | <hook `PreToolUse` hoặc role database tối thiểu quyền> | Bị chặn ở cả hai lớp |

Lời từ chối của mô hình không được tính là một lớp chặn.

## 5. Khôi phục

Dẫn tới kết quả `scripts/backup_restore_check.py --extra-tables` và phép kiểm quyền A/B sau restore (mục 4 của [checklist release](Release_Checklist_Template.md)).
