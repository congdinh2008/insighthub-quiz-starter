# Checklist review migration và cấu hình build/test do AI sinh

<!-- Dùng ở M4 (LR-24..25) và M5 (LR-27) cho mọi PR có migration SQL, workflow CI, Dockerfile, Makefile hoặc cấu hình test do agent tạo hoặc sửa. -->

| Nhóm | Câu hỏi kiểm | Kết quả và căn cứ |
| --- | --- | --- |
| Mất dữ liệu | Có `DROP`, `TRUNCATE`, đổi kiểu cột, `NOT NULL` không default, xóa ràng buộc? Chạy trên dữ liệu đã có chưa? | |
| Forward và rollback | Migration forward-only? Ứng dụng bản trước còn chạy với schema mới để rollback app không? | |
| Tương thích | Thứ tự migration, index lớn, khóa bảng, embedding identity | |
| Bỏ qua kiểm | Test bị skip, `continue-on-error`, `\|\| true`, giảm ngưỡng coverage, bỏ job scan? | |
| Secret | Secret in log, biến môi trường in ra, `env` dump, cache chứa `.env`? | |
| Quyền CI | `permissions` tối thiểu, action pin theo SHA, trigger `pull_request_target`? | |
| Package | Package mới tồn tại thật, đúng tên, đúng publisher, đã pin phiên bản? | |
| Backup/restore | Bảng mới đã thêm vào `scripts/backup_restore_check.py --extra-tables`? | |

Ghi finding, quyết định Fix / Reject / Defer và lần kiểm lại vào PR theo [Review Workflow](../Review_Workflow.md).
