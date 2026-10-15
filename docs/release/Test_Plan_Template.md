# Test plan và test report InsightHub

Dùng cho LR-19 (kiểm thử đa tầng, ASG01 phần 1, M3) và dùng lại tại release gate (LR-20, M4). Sao chép file này thành `docs/release/Test_Plan.md`. Giữ trong 1 đến 2 trang; dẫn link tới test, lần chạy CI và report, không chép lại nội dung.

Phiên bản kiểm: <commit hoặc tag> | Ngày: <ngày> | Người lập: <tên>

## 1. Phạm vi

| Mục | Nội dung |
| --- | --- |
| Trong phạm vi | Hành trình Quiz: đăng nhập, chọn tài liệu, tạo đề, làm bài, nộp, xem kết quả, mở lại, tài khoản B bị từ chối. Code tự viết ở M3.1, M3 |
| Ngoài phạm vi | <phần chưa xây, AC Extended chưa làm, lý do> |
| Mục tiêu chất lượng | <rủi ro cần giảm, ví dụ lộ dữ liệu chéo, citation sai nguồn> |

## 2. Rủi ro ưu tiên

| Rủi ro | Likelihood | Impact | AC liên quan | Cách kiểm |
| --- | --- | --- | --- | --- |
| <ví dụ: tài khoản B đọc được tài liệu của A> | | | | |

## 3. Chiến lược theo tầng

| Tầng hoặc loại test | Công cụ | Phạm vi | Người hay AI sinh ca | Oracle |
| --- | --- | --- | --- | --- |
| Unit, integration | pytest, Vitest | | | |
| API và quyền | pytest với `TestClient` | | | |
| E2E | `@playwright/test` (`npm run test:pw`) | Hành trình M3.1 | | |
| Mutation | mutmut hoặc Stryker | Một file code tự viết | | |
| Eval AI | `make eval` với `K=2` | Golden set hỏi đáp 4 case | | Ý kỳ vọng đặt trước |

## 4. Môi trường

| Mục | Giá trị |
| --- | --- |
| Commit | |
| Chế độ | Fixture hoặc real; provider và model khi real |
| Dữ liệu thử | Corpus của Starter, tài khoản seed A và B |
| Trình duyệt | Tên và phiên bản |

## 5. Entry và exit criteria

| Loại | Tiêu chí | Ngưỡng đặt trước |
| --- | --- | --- |
| Entry | Build và CI xanh; AC R1 của hành trình `Human-verified` | |
| Exit | AC R1 của hành trình Pass | 100% |
| Exit | Lỗi mức chặn còn mở | 0 |
| Exit | pass^k của golden set hỏi đáp (k = 2) | <ghi trước khi chạy> |
| Exit | Mutation score của file đã chọn | <ghi trước khi chạy, kèm lý do> |

NotRun, Skipped và Blocked không phải Pass. Đổi ngưỡng sau khi đã chạy phải ghi lý do và tăng phiên bản test plan.

## 6. Test report

| Hạng mục | Tổng | Pass | Fail | NotRun | Evidence |
| --- | --- | --- | --- | --- | --- |
| Unit, integration | | | | | |
| API và quyền | | | | | |
| E2E | | | | | |
| Eval hỏi đáp (pass^k) | | | | | |
| Mutation (score trước, sau) | | | | | |

Ca do AI sinh: <số ca sinh ra>, giữ lại <số ca>, loại <số ca>; lý do loại chính: <lý do>.

| Defect còn mở | Mức | Bước tái hiện | Trạng thái |
| --- | --- | --- | --- |
| | | | |

Kết luận theo exit criteria: <Đạt | Chưa đạt>, điều kiện còn thiếu: <ghi rõ>.

## 7. Dùng lại tại release gate

Ở M4, chạy lại trên commit candidate, cập nhật mục 6 và dẫn kết quả vào [checklist release](Release_Checklist_Template.md). Exit criteria của mục 5 là căn cứ cho quyết định go/no-go.
