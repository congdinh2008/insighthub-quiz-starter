# Specs: Specify -> Plan -> Tasks -> Implement

Chuỗi spec (đặc tả) dùng làm đầu vào cho coding agent (Kit K8). Bắt buộc cho **Quiz**; tính năng khác dùng lại template nếu muốn.

| Bước | File | Milestone | Đầu vào | Người chốt |
| --- | --- | --- | --- | --- |
| Specify | `specs/<feature>/spec.md` | M2.1 LR-08 | SRS, trace đã `Human-verified` | Học viên |
| Plan | `specs/<feature>/plan.md` | M2 LR-11 | spec, OpenAPI, ERD, ADR | Học viên |
| Tasks | `specs/<feature>/tasks.md` | M2 LR-11 | plan | Học viên |
| Implement | PR theo từng task | M3 LR-16..18 | task + agent task brief | Học viên review diff |

Quy tắc:

- spec mô tả **cái gì và vì sao** theo SRS, không chép lại toàn bộ SRS; dẫn mã AC.
- Mỗi task nhỏ đủ review trong một PR (khoảng 400 dòng diff trở xuống), có AC, lệnh kiểm và stop condition (điều kiện dừng).
- Khi code khác plan, cập nhật plan/tasks trong cùng PR và ghi lý do. Thay đổi hành vi phải quay lại spec.

## Hai cổng duyệt

| Cổng | Duyệt trước khi | Tiêu chí đạt |
| --- | --- | --- |
| 1. Duyệt spec | Lập plan | Mỗi mục trỏ mã AC hoặc yêu cầu SRS. Không chứa cách cài đặt (bảng, endpoint, thư viện). Có nhánh lỗi và sai quyền cho yêu cầu rủi ro cao. NFR có điều kiện và số đo. Điểm chưa rõ nằm ở câu hỏi mở, không thành yêu cầu |
| 2. Duyệt plan, tasks | Giao agent code | Mỗi task trỏ mã AC, vừa một PR, có lệnh kiểm và stop condition. Task theo thứ tự phụ thuộc. Không có task ngoài spec |

Ghi kết quả duyệt (đạt, sửa gì, phần AI đề xuất bị bác) trong PR hoặc AI Delivery Log.

Template: [spec](_template/spec.md), [plan](_template/plan.md), [tasks](_template/tasks.md).
