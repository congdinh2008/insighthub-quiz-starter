<!-- Tiêu đề: <Milestone> - <kết quả chính>, ví dụ "M3.1 - Hành trình Notebook có kiểm quyền A/B" -->

## Thay đổi

- Milestone / LR:
- AC liên quan (mã trong `trace/ac-trace.csv`):
- Issue "Task giao agent" hoặc task trong `specs/<feature>/tasks.md` (nếu có):
- PR milestone: link các PR task đã merge vào nhánh milestone (từ M3.1, Requirements mục 4.3):
- Kích thước diff: ~___ dòng (không tính file sinh tự động). PR vượt khoảng 400 dòng cần tách hoặc ghi lý do.

## Kiểm tra đã chạy

| Lệnh hoặc phép kiểm | Kỳ vọng | Thực tế | Log hoặc link |
| --- | --- | --- | --- |
| | | | |

Commit đã kiểm: <SHA>

## AI usage

- Công cụ và chế độ (Claude Code, Claude.ai, Codex; plan mode, agent chạy nền):
- Agent đã làm gì; file và lệnh nằm trong phạm vi task brief không:
- Agent có chạm vào test đã duyệt không (xem `git diff --stat -- '*test*'`): Có / Không
- Phần học viên tự kiểm độc lập (test, nguồn SRS, log):
- Đề xuất AI đã giữ, sửa hoặc bác bỏ và lý do (1-3 dòng tiêu biểu):
- Đã ghi một dòng vào `docs/ai/delivery-log.csv`: Có / Không

## Review

- [ ] Tự review 4 góc: Correctness, Security, Convention, Design (trước khi chạy AI reviewer)
- [ ] `/code-review --comment <số PR>` chạy trong session mới; finding đã phân loại Fix / Reject / Defer
- [ ] `/security-review` nếu PR chạm Auth, quyền, upload, prompt, log hoặc dữ liệu cá nhân
- [ ] Ít nhất một finding AI được xác minh bằng phép kiểm độc lập

## Definition of Done

- [ ] Test liên quan đạt; test mới thất bại đúng nguyên nhân trước khi triển khai (nếu TDD)
- [ ] Lint, secret scan, dependency scan đạt hoặc finding đã triage
- [ ] Kiểm quyền A/B cho tài nguyên bị ảnh hưởng
- [ ] Migration forward, không yêu cầu xóa volume
- [ ] `trace/ac-trace.csv` cập nhật; AC trong PR đã `Human-verified` trước khi giao agent
- [ ] Không có `.env`, API key, token hoặc dữ liệu thật trong diff, log hay ảnh chụp

## Còn mở hoặc cần hỗ trợ

