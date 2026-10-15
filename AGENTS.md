# InsightHub Starter - Quy tắc làm việc

Đọc `README.md`, `GETTING_STARTED.md`, `docs/Architecture_Starter_v1.md` và `docs/API_Contract_Starter_v1.md` trước khi sửa.

- Bộ tài liệu trong `docs/learner/`: [Requirements](docs/learner/01_Requirements_InsightHub.md) là đề bài (phần Core phải làm, điều chỉnh phạm vi bài tập, lộ trình, rubric). [SRS v1.1](docs/learner/02_SRS_InsightHub_v1.1.md) là đặc tả sản phẩm, không sửa. ZIP API/Schema là hợp đồng tham khảo để đối chiếu; không tự thay giao tiếp runtime. Manifest của gói mã nguồn chỉ xác nhận đúng phiên bản gói được kiểm.
- **Đọc tài liệu có phạm vi (tiết kiệm token):** không đọc toàn bộ `02_SRS_InsightHub_v1.1.md` hay `01_Requirements_InsightHub.md`. Mở đúng mục người dùng chỉ định, theo bảng Requirements mục 1.4, hoặc tìm bằng mã yêu cầu (ví dụ `IH-QUIZ-002`). Khi SRS và Requirements mục 1.3 khác nhau ở phạm vi bài tập, theo Requirements. Chạy test có phạm vi khi đang sửa, chạy toàn bộ trước khi báo xong.
- Giữ kiến trúc đồng bộ Web/API/PostgreSQL và HTTP 201 sau ingestion thành công, trừ khi có quyết định mới được ghi bằng ADR.
- Không làm yếu checksum, embedding identity, idempotency, deadline, citation validation, locks hoặc transaction để test pass.
- Mọi thay đổi schema dùng forward migration. Không yêu cầu xóa volume như cách nâng cấp.
- Giữ fixture hoàn toàn offline. Không gọi provider trả phí, tải model hoặc gửi tài liệu ra ngoài khi chưa có hướng dẫn phù hợp.
- Nghiệp vụ Auth (trên Auth scaffold) và Notebook là extension của học viên. Policy ownership phải do server xác lập; không tin owner do client gửi và không tự nhận dữ liệu nền cho user đầu tiên.
- AI Job scaffold mặc định từ chối (`DenyAllPolicy`). Không đăng ký policy cho phép tất cả, không nới quota, deadline hoặc publish fence để test đạt; policy phải kiểm chủ sở hữu, nguồn và quyền hiện hành (thêm Notebook khi làm Extended).
- Không log credentials, toàn văn tài liệu, prompt có nội dung nguồn hoặc provider body thô.
- Dùng Compose namespace riêng. Không thao tác container hoặc volume của project khác.
- Trước khi báo xong: chạy backend, web và smoke tests phù hợp (`make test`, `make smoke`) và ghi lệnh, kết quả, SHA commit vào evidence của milestone. Không báo pass khi chưa thực chạy.
- Không đọc, in hoặc gửi `.env`, API key, token; chỉ tham chiếu tên biến trong `README.md`.
- Fixture xác nhận behavior của phần mềm, không phải semantic evaluation của AI thật.

## Glossary và invariant nghiệp vụ

Học viên bổ sung ở M2 (LR-11). Mỗi invariant có nơi enforce chính và cách kiểm; lời nhắc trong prompt không phải enforcement point.

| Mã | Invariant | Enforcement point | Cách kiểm |
| --- | --- | --- | --- |

## AI Engineering Kit

Bản đồ Kit theo milestone: [docs/ai/README.md](docs/ai/README.md).

- **Truy vết:** `trace/ac-trace.csv` là traceability matrix duy nhất. Chỉ triển khai AC đã `Human-verified`; bản nháp AI ghi `draft_by=AI`. Không ghi `Passed` khi thiếu commit và evidence. Chạy `python3 scripts/trace_check.py` trước khi báo xong.
- **Test-as-spec:** không sửa test liệt kê trong `.claude/approved-tests.txt`. Test đã duyệt chỉ được học viên sửa trong commit riêng có trailer `Test-Change-Approved: <lý do>`; CI kiểm bằng `scripts/check_approved_tests.py`.
- **Spec chain:** task lấy từ `specs/<feature>/tasks.md`; code khác plan thì cập nhật plan/tasks trong cùng PR và ghi lý do.
- **PR:** dùng `.github/pull_request_template.md`, giữ diff khoảng 400 dòng trở xuống (không tính file sinh tự động) hoặc ghi lý do; điền mục AI usage và một dòng `docs/ai/delivery-log.csv` với số đo thật.
- **Package mới:** kiểm package tồn tại trên registry chính thức, đúng tên và publisher, pin phiên bản trước khi thêm; không cài package chỉ vì AI đề xuất.
- **Instructions lồng nhau:** `web/AGENTS.md` và `web/CLAUDE.md` do `next dev` của Next.js 16 sinh và tự thêm lại; giữ nguyên khối `nextjs-agent-rules`. Khi làm trong `web/`, đọc tài liệu Next.js đúng phiên bản tại `web/node_modules/next/dist/docs/` trước khi viết code.
- **Migration và CI do agent sinh:** review theo [checklist](docs/ai/templates/Review_Checklist_Migration_CI.md) trước khi merge.
