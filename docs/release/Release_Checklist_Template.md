# Checklist phát hành InsightHub <R1 | R1.1>

Dùng cho LR-25 (R1, M4) và LR-27 (R1.1, M5). Sao chép file này thành `docs/release/Release_Checklist_<R1|R1.1>.md`, điền từng dòng theo **đúng commit phát hành**. Dòng chưa kiểm, bị chặn hoặc bỏ qua ghi rõ lý do, không đánh dấu đạt.

Tag: <tag> | Commit: <SHA> | Ngày: <ngày> | Người kiểm: <tên>

## 1. Phạm vi và truy vết

| Mục kiểm | Lệnh hoặc cách kiểm | Kết quả | Evidence |
| --- | --- | --- | --- |
| Trace đủ 153 AC áp dụng, 12 ngoài phạm vi | R1: `python3 scripts/trace_check.py --gate M4`; R1.1: `--gate M5` | | |
| AC Core R1 có `test_ids` và evidence trực tiếp | Lọc `tier=Core`, `risk=R1` trong `trace/ac-trace.csv` | | |
| Phần chưa đạt và AC Extended đã làm được ghi trong ghi chú phát hành | Đối chiếu [Release Notes](Release_Notes_Template.md) | | |
| Test report đạt exit criteria của test plan | Đối chiếu [Test Plan](Test_Plan_Template.md) mục 5, 6 trên commit phát hành | | |

## 2. Kiểm tự động trên đúng commit

| Mục kiểm | Lệnh | Kết quả | Evidence |
| --- | --- | --- | --- |
| Backend, Web, công cụ | `DB_PORT=5434 make COMPOSE="docker compose --env-file .env.example -p insighthub-c07-check" test` | | |
| App CI xanh trên commit phát hành | Liên kết lần chạy GitHub Actions | | |
| Eval fixture đạt trên đúng commit phát hành | Bước `eval-fixture` của App CI hoặc `make eval` với suite của bài làm | | |
| Smoke có phiên đăng nhập | `INSIGHTHUB_SESSION_COOKIE` từ `scripts/session_cookie.py`, rồi `make smoke` | | |
| E2E hành trình Quiz | `make test-pw` | | |
| Dependency và secret scan | Cấu hình CI của M1 | | |
| SBOM và AI-BOM sinh trong CI | Bước `make sbom`, `make ai-bom` của CI trên commit phát hành | | |

## 3. Gói phát hành và cài sạch

| Mục kiểm | Cách kiểm | Kết quả | Evidence |
| --- | --- | --- | --- |
| Git tag annotated trỏ đúng commit | `git show <tag> --no-patch` | | |
| Gói có checksum, `.env.example`, hướng dẫn cài, chạy, xử lý lỗi | `git archive --format=tar.gz -o insighthub-<tag>.tar.gz <tag>`, rồi `sha256sum insighthub-<tag>.tar.gz` | | |
| Gói không chứa `.env`, khóa, dữ liệu thật, cookie | Kiểm danh sách file trong gói | | |
| Cài sạch trên thư mục hoặc máy khác theo hướng dẫn | Clone hoặc giải nén mới, `docker compose up --build -d --wait` | | |
| Luồng chính sau cài sạch: đăng nhập, chọn tài liệu, tạo đề, làm bài, nộp, xem kết quả, Chat | Thực hiện qua UI, chạy E2E hành trình Quiz | | |

## 4. Dữ liệu, khôi phục (LR-26) và nâng cấp (LR-27)

| Mục kiểm | Cách kiểm | Kết quả | Evidence |
| --- | --- | --- | --- |
| Migration nâng cấp chạy trên bản sao dữ liệu R1, có backup trước (chỉ R1.1) | `make migrate` trên bản sao dữ liệu, theo expand và contract | | |
| Backup và restore gồm bảng Auth, `ai_jobs` và bảng bài làm | `--extra-tables auth_user,auth_session,auth_account,auth_verification,ai_jobs,<bảng bài làm>` | | |
| Quyền A/B sau restore | Đăng nhập A và B, thử đọc chéo bằng ID | | |
| Rollback R1.1 về R1 không mất dữ liệu (chỉ R1.1) | Theo kế hoạch rollback của CR | | |

## 5. Tính năng AI và ghi chú phát hành

| Mục kiểm | Cách kiểm | Kết quả | Evidence |
| --- | --- | --- | --- |
| Nhãn "nội dung do AI tạo" trên Chat, Quiz | Ảnh chụp UI | | |
| Provider, model, phiên bản prompt và schema khớp AI-BOM | `make ai-bom` | | |
| Giới hạn đã biết, kênh báo sự cố | Ghi chú phát hành | | |
| Lỗi còn mở có mức độ và hướng xử lý | Danh sách issue | | |

## 6. Vận hành (chỉ R1)

| Mục kiểm | Cách kiểm | Kết quả | Evidence |
| --- | --- | --- | --- |
| 3 SLI, 1 SLO, incident diễn tập, postmortem | [Operations Template](Operations_Template.md) | | |
| Lệnh phá dữ liệu bị chặn ở hai lớp | Log của rule `deny`, hook hoặc role database | | |

## 7. Quyết định go/no-go

AI được tổng hợp evidence cho checklist; quyết định do người ký.

- Quyết định: <Go | No-go>
- Căn cứ theo exit criteria và các mục trên: <ghi rõ>
- Waiver (nếu có): <mục, lý do, người chấp thuận, hạn xử lý>
- Điều kiện còn thiếu khi no-go và thời điểm đánh giá lại: <ghi rõ>
- Người quyết định và thời điểm: <tên, ngày giờ>
