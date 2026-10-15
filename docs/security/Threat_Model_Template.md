# Threat model InsightHub

<!-- Lập sơ bộ ở M2 (LR-11), cập nhật theo bản triển khai ở M4 (LR-24). Chỉ dùng dữ liệu giả và tài khoản test. Nội dung đào tạo, không phải tư vấn pháp lý. -->

Phiên bản: <x.y> | Commit/thiết kế đối chiếu: <link> | Người lập: <tên>

## 1. Data flow và trust boundary

Vẽ sơ đồ (Mermaid hoặc ảnh) gồm: trình duyệt, Next.js, FastAPI, PostgreSQL, tài liệu upload, RAG/index, provider AI sinh nội dung và embedding, Auth provider, SMTP/Mailpit, coding agent (Claude Code), MCP. Đánh dấu trust boundary.

## 2. Luồng dữ liệu ra nước ngoài

| Luồng | Đích | Dữ liệu | Mức theo Charter | Được phép? | Control |
| --- | --- | --- | --- | --- | --- |
| Hỏi đáp, Summary, Quiz | Provider AI đã chọn | Đoạn tài liệu, câu hỏi | | | |
| Embedding | | | | | |
| Đăng nhập Google | Google | | | | |
| Phát triển với coding agent | Claude | Code, corpus giả | | | |

## 3. STRIDE trên endpoint và thực thể chính

| Endpoint / thực thể | S | T | R | I | D | E | Threat cụ thể | Control | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 4. Threat riêng của ứng dụng AI và coding agent

| Threat | Ví dụ trong InsightHub | Điều kiện lethal trifecta đã cắt | Control | Test |
| --- | --- | --- | --- | --- |
| Prompt injection gián tiếp qua tài liệu | `evaluation/corpus/04_injection_vi.md` | | | |
| Lộ dữ liệu qua citation, cache | | | | |
| Agent đọc secret hoặc vượt quyền | | | `.claude/settings.json`, hook | |

Lethal trifecta gồm ba điều kiện: truy cập dữ liệu riêng tư, tiếp xúc nội dung không tin cậy, có kênh gửi dữ liệu ra ngoài. Đủ cả ba thì prompt injection có thể lấy dữ liệu. Với mỗi threat AI, ghi điều kiện đã cắt và control tương ứng; guardrail của model không thay cho việc cắt điều kiện.

## 5. Tự phân loại rủi ro AI

Lập luận mức rủi ro của InsightHub theo Luật Trí tuệ nhân tạo 134/2025/QH15; ghi giả định và phần cần Legal/DPO xác nhận.

## 6. Lịch sử cập nhật

| Phiên bản | Milestone | Thay đổi | Lý do |
| --- | --- | --- | --- |
