# Quy trình review có AI trên Pull Request

Áp dụng từ M1 (LR-07) cho mọi PR tính năng; bắt buộc với PR bảo mật (M4 LR-24), PR cấu hình CI và phát hành (M4 LR-24..25), PR migration và PR do agent tạo (M5 LR-27). Tài khoản Claude Pro/Max dùng được toàn bộ quy trình mặc định; không cần GitHub App, secret hoặc phút GitHub Actions.

## Quy trình mặc định

1. **Tự review trước.** Tác giả rà 4 góc Correctness, Security, Convention, Design theo checklist trong PR template.
2. **Tách writer và reviewer.** Mở **session Claude Code mới** (không dùng session đã viết code), chạy:
   ```text
   /code-review --comment <số PR>
   ```
   Cờ `--comment` đứng trước số PR: phần sau mức và cờ được đọc là đích review. Lệnh review chạy như subagent có context riêng và đăng finding thành inline comment trên PR qua GitHub CLI (`gh auth login` trước). Review đọc `CLAUDE.md`/`AGENTS.md`, vì vậy quy tắc review của dự án đặt trong các file này.
3. **Review bảo mật khi cần.** PR chạm Auth, session, quyền, upload, prompt, log hoặc dữ liệu cá nhân: chạy thêm `/security-review` và đính kết quả vào PR.
4. **Phân loại từng finding.**

   | Quyết định | Điều kiện | Ghi |
   | --- | --- | --- |
   | Fix | Tái hiện được hoặc có căn cứ trong SRS, code, test | Commit sửa, test chứng minh |
   | Reject | Không tái hiện được, sai ngữ cảnh hoặc trái SRS | Căn cứ bác bỏ (file:dòng, test, mục SRS) |
   | Defer | Đúng nhưng ngoài phạm vi PR | Issue mới, mức ưu tiên |

   Xác minh ít nhất một finding bằng phép kiểm độc lập. Không cần tìm lỗi ở mọi góc; kết luận "không có vấn đề" phải có căn cứ.
5. **Ghi số đo.** Điền mục AI usage trong PR và một dòng `docs/ai/delivery-log.csv`: số finding, số finding đúng, số phút review. Tỷ lệ finding đúng là số đo "review load" dùng cho kế hoạch 30 ngày.

## Tùy chọn (Stretch B7)

Claude Code GitHub Actions với token subscription (`claude setup-token`, secret `CLAUDE_CODE_OAUTH_TOKEN`) chỉ dùng khi AI Usage Charter cho phép lưu token dài hạn của tài khoản học tập trong repository secret. Lưu ý:

- GitHub App của Claude xin quyền ghi rộng (Contents, Pull requests, Workflows). Chỉ cài cho repository bài làm.
- Mỗi lượt chạy tốn phút GitHub Actions (repository private có giới hạn) và quota subscription.
- Đặt `--max-turns`, timeout, concurrency; kích hoạt thủ công bằng `@claude`; xóa secret và thu hồi token khi kết thúc khóa.

## Không dùng trong khóa

Dịch vụ managed Code Review của Anthropic chỉ dành cho gói Team/Enterprise, tính phí theo mức sử dụng và không chặn merge. Học viên có thể nêu như phương án cấp tổ chức trong kế hoạch áp dụng 30 ngày.

## Dùng công cụ AI khác

Học viên dùng công cụ khác Claude (ví dụ Codex): chạy tính năng code review tương ứng của công cụ đó trên cùng PR, áp dụng nguyên các bước 1, 4, 5. Lệnh cụ thể theo Tool Profile của công cụ do giảng viên cung cấp.

Tên lệnh và tùy chọn có thể thay đổi theo phiên bản Claude Code; phiên bản được kiểm cho lớp ghi trong Tool Readiness do giảng viên cung cấp.
