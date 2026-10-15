# ADR-001 - Ingestion đồng bộ

- Status: Accepted
- Date: 19/09/2026

Giữ FastAPI xử lý ingestion đồng bộ và trả HTTP 201 chỉ khi document `Ready`. Bổ sung durable attempt, deadline, idempotency và crash recovery thay vì thêm queue/worker vào starter. Quyết định giữ footprint nhỏ cho lớp học và tránh biến kiến trúc phân tán thành điều kiện đầu vào.
