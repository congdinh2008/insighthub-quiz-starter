---
name: Task giao agent
about: Agent task brief đủ để giao cho coding agent hoặc agent chạy nền
labels: agent-task
---

**Mục tiêu và tiêu chí hoàn thành:**

**Đầu vào:** spec/plan/tasks, AC (`Human-verified`), thiết kế, test đã duyệt

**Phạm vi được phép:** thư mục/file được sửa; lệnh được chạy; dữ liệu được dùng
**Ngoài phạm vi:** không sửa test đã duyệt, migration cũ, cấu hình CI, `.env`

**Lệnh kiểm và expected result (kết quả kỳ vọng):**

**Stop condition (điều kiện dừng):** dừng và hỏi khi cần đổi ngoài phạm vi, test đã duyệt thất bại vì spec hoặc cần quyền mới

**Người review và hạn:**
