# ADR-003 - Operation idempotency trong database

- Status: Accepted
- Date: 19/09/2026

Upload, retry, delete và chat dùng operation record giữ tối thiểu 24 giờ. Advisory transaction lock serialize cùng operation key; fingerprint phát hiện key tái dùng với payload khác. Processing record commit trước công việc để polling quan sát được; exception và deadline phải đi tới trạng thái terminal. Migration 002 lưu deadline; polling phục hồi quá hạn, startup phục hồi interrupted.

Response thành công hoặc thất bại được replay; replay chat kiểm lại nguồn và loại excerpt đã bị xóa. Browser lưu key trước POST trong sessionStorage, đối soát đến deadline và giữ key nếu mạng chưa rõ kết quả. Đây là nền cho phục hồi mất kết nối, sẽ được scope thêm theo owner khi tích hợp Auth.
