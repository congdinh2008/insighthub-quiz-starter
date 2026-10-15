@AGENTS.md

## Ghi chú riêng cho Claude Code

- Bắt đầu mỗi task bằng plan mode: trình bày plan, chờ học viên duyệt rồi mới sửa code. Task giao agent dùng issue template "Task giao agent" hoặc một dòng trong `specs/<feature>/tasks.md`.
- Không tắt permission prompt (không dùng `--dangerously-skip-permissions` hoặc `bypassPermissions`). Đọc kỹ từng lệnh trước khi duyệt.
- `.claude/settings.json` đặt chế độ quyền khởi đầu là Manual (`defaultMode: default`), chặn đọc `.env`, `.env.*` (kể cả `.env.example`), `secrets/`, file khóa; chặn `rm -rf`, `git push --force`, `git reset --hard`. Không tự chuyển sang `auto` hoặc `bypassPermissions` khi làm bài.
- Hai hook `PreToolUse` chạy bằng `python3`, ghi log tại `reports/hooks/events.jsonl`:
  - `block-secrets` chặn lệnh đọc, in hoặc dump `.env`, `secrets/`, file khóa (ví dụ `cat .env`, `printenv`, `docker compose config`, `grep -r` không có `--exclude`).
  - `protect-approved-tests` chặn sửa các test liệt kê trong `.claude/approved-tests.txt` (test-as-spec). Khi test đã duyệt thất bại, dừng lại và báo học viên; không sửa assertion, expected hoặc fixture để test đạt.
- Rule và hook là lưới an toàn, không phải ranh giới bảo mật: không vòng qua bằng script, `bash -c` hoặc công cụ khác. Cần biết tên biến cấu hình thì đọc mục "Cấu hình AI" trong `README.md`.
- Thiết lập cá nhân đặt trong `.claude/settings.local.json` (không commit); không nới rule `deny` hoặc gỡ hook của repo.
- Không dùng `/feedback` khi transcript chứa bài làm chưa công khai.

## Review và kiểm chứng

- Review PR theo [docs/ai/Review_Workflow.md](docs/ai/Review_Workflow.md): tự review 4 góc trước, sau đó `/code-review --comment <số PR>` trong **session mới**; thêm `/security-review` khi PR chạm Auth, quyền, upload, prompt, log.
- Khi review, ưu tiên finding có căn cứ (file:dòng, test, mục SRS). Không báo suy đoán như lỗi; ghi rõ phạm vi đã rà nếu không có finding.
- Trước khi triển khai AC nào, kiểm dòng của AC đó trong `trace/ac-trace.csv` đã `Human-verified`; nếu chưa, dừng và báo học viên.
- Không điền `verdict`, `actual`, `commit` trong bảng trace hoặc số đo trong `docs/ai/delivery-log.csv` khi chưa có kết quả chạy thật.
