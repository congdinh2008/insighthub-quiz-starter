# AEV-01 - RAG evaluation corpus

> Golden set, grader bằng code và pass^k cho Summary/Quiz (LR-23) nằm ở [eval harness](harness/README.md) (`make eval`). Trang này mô tả bộ AEV-01 cho hỏi đáp RAG của Starter. Từ M3.1, đặt `INSIGHTHUB_SESSION_COOKIE` trước khi chạy AEV hoặc harness ([Runbook](../docs/Runbook_Starter_v1.md#kiem-tra-sau-khi-bao-ve-endpoint)).

Bộ nhỏ dùng để kiểm `Answered`, `NoEvidence`, citation và prompt injection trước release. Fixture không được tính là kết quả AEV.

1. Khởi động một real-provider profile trên database/index riêng.
2. Chạy `make aev`; runner upload đúng corpus, chọn `document_ids`, chấm từng case và dọn tài liệu do chính nó tạo.
3. Kết quả local nằm trong `reports/evaluation/`. Chỉ đưa evidence đã review vào release package.
4. Không ghi API key hoặc provider response thô. Fixture không được phép chạy AEV.

AEV-01 v3 có 3 grounded case, 2 NoEvidence case, 1 answerable prompt-injection case và lặp một grounded case. Thêm PDF supplement thành 8 lượt. Runner kiểm status, concept, forbidden term, source scope, claims không rỗng, citation reference, excerpt thực sự nằm trong source endpoint, đúng locator và required facts theo oracle. Ba regression test cố ý tạo claim rỗng/citation giả/locator sai để kiểm bộ chấm.

Bộ chấm tự động không kết luận quan hệ ngữ nghĩa giữa claim và nguồn. Report ban đầu có `semantic_review: pending`; reviewer phải đọc từng claim và nguồn, ghi verdict/lý do/tên reviewer trên bản đã review, giữ nguyên bản raw cùng hash. Không bỏ lượt lỗi hoặc nhầm review của Codex với xác nhận độc lập của instructor. Corpus là dữ liệu synthetic do Mochi AI tự tạo cho phép thử, không chứa thông tin khách hàng.

Các file do Mochi AI biên soạn cho chương trình B2B C07, phạm vi sử dụng nội bộ lớp học.

| File | SHA-256 |
| --- | --- |
| `01_quy_trinh_vi.md` | `164567376f9ca27d9f2d05d8e9001e628c87ab3aa2fa1810da302f9619e642d1` |
| `02_operations_en.txt` | `d4a586ce013f138804580532b4030fcf219d985aaa3558e9f33eedc103fa2b37` |
| `03_reference.pdf` | `50fab3673cd8e7ce894afb428c67dfb38129807f9a2c7d4964afbbefad73712a` |
| `04_injection_vi.md` | `d746cd194f816487a8a1459b7674754f5c9ca3e2364fd8264cc460f7136b5fb3` |
