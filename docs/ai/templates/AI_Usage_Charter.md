# AI Usage Charter - InsightHub

<!-- Template K3 (M0.2 LR-04). Sao chép thành docs/ai/AI_Usage_Charter.md. Nội dung đào tạo, không phải tư vấn pháp lý. -->

Repository: <link> | Phiên bản: <x.y> | Người chịu trách nhiệm: <tên>

## 1. Phân loại dữ liệu

| Mức | Ví dụ trong InsightHub | Được đưa vào công cụ AI phát triển (Claude) | Được gửi tới provider AI của sản phẩm |
| --- | --- | --- | --- |
| Public | | | |
| Internal | | | |
| Confidential | `.env`, API key, token, dữ liệu Samsung SDS/khách hàng | Không | Không |
| Personal/Sensitive | Email tài khoản test, dữ liệu cá nhân | | |

## 2. Công cụ, tài khoản và quyền

| Công cụ | Tài khoản | Thư mục được sửa | Lệnh được chạy | Cơ chế thực thi (deny, hook, CI) |
| --- | --- | --- | --- | --- |

## 3. Người quyết định và checkpoint

## 4. Cách dừng và khôi phục

## 5. Ghi chú pháp lý Việt Nam ở mức dự án

Luật Trí tuệ nhân tạo 134/2025/QH15; Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và Nghị định 356/2025/NĐ-CP. Ghi áp dụng cụ thể cho InsightHub (vai trò, luồng dữ liệu ra nước ngoài, nhãn nội dung AI).

## 6. Prompt injection

Control nào trong Charter hoặc quyền công cụ chặn được instruction (chỉ dẫn) độc hại trong `evaluation/corpus/04_injection_vi.md`.
