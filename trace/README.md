# Traceability matrix AC và kiểm chứng theo rủi ro

`ac-trace.csv` là **một traceability matrix (bảng truy vết) xuyên khóa** cho 165 AC (153 áp dụng, 12 ngoài phạm vi), thay cho việc tự dựng bảng ở LR-08. Cột bên trái do giảng viên cấp; cột bên phải học viên điền dần từ M2.1 đến M5. Cách ghi theo [Requirements mục 17.1](../docs/learner/01_Requirements_InsightHub.md#bang-ket-qua).

## Cột

| Nhóm | Cột | Ý nghĩa |
| --- | --- | --- |
| Giảng viên cấp | `ac_id`, `req_id`, `group`, `scope`, `lr`, `due`, `uat`, `srs_ref` | Lấy từ [Requirements Phụ lục A](../docs/learner/01_Requirements_InsightHub.md#pham-vi-truy-vet), không sửa. `scope` là mã A, D1 đến D9 (trừ D7), N của SRS. AC Extended có `lr`, `due` là `Mở rộng` |
| Giảng viên cấp | `tier` | `Core` (chấm, 18 AC của Feature Slice Quiz), `Extended` (làm thêm, 135 AC), `OutOfScope` (12 AC) theo [Requirements mục 1.2](../docs/learner/01_Requirements_InsightHub.md#core-extended). `Pending` chỉ dùng khi giảng viên chưa công bố tầng |
| Giảng viên cấp | `risk_suggested` | Mức rủi ro gợi ý R1/R2/R3 |
| Học viên | `risk`, `risk_reason` | Mức rủi ro áp dụng; hạ mức so với gợi ý phải ghi lý do |
| Học viên | `branches`, `expected` | Nhánh cần kiểm, input và expected result theo SRS |
| Học viên | `draft_by` | `AI` nếu AI viết nháp, `Human` nếu tự viết |
| Học viên | `verification`, `verified_by`, `verify_method` | `Unverified` hoặc `Human-verified`; người kiểm; `SRS-crosscheck`, `Test`, `Sample`, `Review` |
| Học viên | `design_ref`, `test_ids`, `actual`, `commit`, `evidence`, `verdict`, `notes` | Thiết kế, test, kết quả thực tế, commit đã kiểm, minh chứng, kết luận |

`verdict`: `NotRun`, `Passed`, `Failed`, `Blocked`, `Extended-NotDone`, `OutOfScope`.

## Mức rủi ro

| Mức | Tiêu chí | Cách kiểm |
| --- | --- | --- |
| R1 | Quyền truy cập, ownership, lộ hoặc mất dữ liệu, lộ đáp án Quiz, grounding, secret trong log, phát hành và khôi phục | Kiểm sâu 100%; `Passed` cần evidence trực tiếp có `test_ids` |
| R2 | Vòng đời, trạng thái, idempotency, CRUD, luồng UI chính, schema output | Kiểm đủ trước khi giao agent; evidence dùng chung được nếu có mapping |
| R3 | Nội dung thông báo, avatar, tài liệu API, hồ sơ bàn giao | Checklist hoặc lấy mẫu |

## Quy trình theo milestone

| Mốc | Việc | Lệnh |
| --- | --- | --- |
| M2.1 LR-08 | AI viết nháp `branches`/`expected` cho 18 AC Core, ghi `draft_by=AI`. Học viên kiểm 100% và chuyển `Human-verified`. Phân tích sâu 1 AC R1 kèm Gherkin | `python3 scripts/trace_check.py` |
| M2.1 LR-08 lấy mẫu | AI viết nháp 12 AC Extended nhóm AI và OUT (`draft_by=AI`). Lấy mẫu 5 dòng có seed, tự kiểm, ghi `result` OK/Error. Tỷ lệ lỗi từ 20% trở lên thì sửa prompt và sinh lại | `make trace-sample SEED=<mã> SIZE=5 TIER=Extended`, `python3 scripts/trace_sample.py --evaluate` |
| M3.1-M3 | Trước khi giao agent một task: chuyển AC R1/R2 của task sang `Human-verified` (mục DoD của PR) | `python3 scripts/trace_check.py` |
| M4 LR-20, LR-25, LR-26 | Kết luận 14 AC Core đến hạn M4, gồm phát hành và khôi phục R1 (IH-NFR-009-AC02, IH-REL-001-AC02) | `python3 scripts/trace_check.py --gate M4` |
| M5 LR-27 | CR-01 làm lại Quiz: kết luận IH-REL-003, nhánh làm lại của IH-QUIZ-002-AC02 và IH-DATA-002-AC03 ở R1.1 | `python3 scripts/trace_check.py --gate M5` |

`trace_check.py` chạy trong CI trên mọi PR. Script chỉ kiểm tính nhất quán; điểm và verdict vẫn dựa trên minh chứng thật. Không đổi tên cột hoặc xóa dòng; có thể thêm cột riêng ở cuối.
