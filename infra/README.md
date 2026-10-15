# Môi trường ứng dụng được cung cấp

`db/init.sql` khởi tạo PostgreSQL + pgvector cho một volume mới. Đây là tiện ích chạy ứng dụng tại máy học viên; không phải bài tập xây hạ tầng.

Giữ nguyên schema và identity của index đang có. Thay đổi schema trong dự án phải có migration và test giữ dữ liệu. Không xóa volume để thay cho migration. Tài khoản trong Compose chỉ dành cho lab local, không dùng trên môi trường chia sẻ hoặc production.
