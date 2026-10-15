# Database migrations

Migration là forward-only, chạy theo thứ tự tên file dưới PostgreSQL advisory lock. Mỗi file phải idempotent cho lần retry sau crash và được ghi vào `schema_migrations`.

Không sửa migration đã phát hành. Tạo file số tiếp theo, thêm integration test cho fresh schema và upgrade schema hiện hữu. Không dùng xóa volume làm migration.

Migration 002 bổ sung deadline cho operation. Starter rc.3 dùng pipeline `extract-segment-chunk-v3`, đưa heading Markdown vào segment/chunk; không tự gọi provider để reindex corpus cũ. Corpus mới luôn dùng pipeline mới. Với corpus cũ cần áp dụng cách trích xuất mới, sao lưu và upload file gốc vào namespace/index mới, kiểm nguồn/AEV rồi mới chuyển runtime; giữ volume cũ để đối soát. Failed document có cùng bytes có thể retry bằng pipeline mới. Không suy rằng migration schema đã cập nhật vectors của tài liệu ready từ rc.2.
