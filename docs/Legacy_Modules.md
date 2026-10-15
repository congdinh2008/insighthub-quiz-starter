# Module legacy chỉ định cho bài Legacy Modernization

Dùng cho phần legacy của ASG01 ở M5 (buổi 9, C02-U07-T02, T05, T06): module map, characterization tests, refactor từng bước qua agent có rollback và review PR do agent tạo. Starter **không** refactor sẵn các module này; chúng được giữ nguyên để học viên thực hành. **Không sửa các module này trước M5**; khi làm M3.1, M3 mà cần sửa phần nền khác, viết regression test trước diff.

## Module chỉ định

| Module | Hàm | Cyclomatic complexity (radon) | Vì sao chọn | Test hiện có |
| --- | --- | --- | --- | --- |
| [`api/app/core/config.py`](../api/app/core/config.py) | `Settings.validate_configuration` | E (40) | Một hàm gom mọi quy tắc cấu hình: chunk/retrieval, fixture vs real, key theo provider, kiểm URL, reranker local, model embedding. Nhiều nhánh lồng nhau, lặp logic kiểm URL, lỗi là chuỗi tự do | Một phần trong `api/tests/test_unit_config.py`; nhiều nhánh chưa có test riêng |
| [`api/app/services/ingestion.py`](../api/app/services/ingestion.py) | `extract_source` | C (19) | Rẽ nhánh theo đuôi file và magic bytes (TXT/MD/PDF), giới hạn ký tự/trang, deadline, gói lỗi `InvalidDocument`. Được gọi từ luồng ingestion chính nên thay đổi có tác động lớn | Chưa có unit test trực tiếp; chỉ được phủ gián tiếp qua integration test cần PostgreSQL |

Số liệu đo bằng `radon cc -s` trên Starter `v1.0.0-rc.3` ngày 27/09/2026. Học viên đo lại trên fork của mình trước khi bắt đầu.

## Cách làm gợi ý

1. Đọc hàm, vẽ các nhánh hành vi và liệt kê input biên (file rỗng, sai magic bytes, PDF mã hóa, vượt giới hạn; thiếu key, URL có credential, cổng sai).
2. Viết characterization tests ghi lại hành vi **hiện tại**, kể cả hành vi có vẻ lạ, trước lần sửa đầu tiên. Test phải chạy offline, không cần PostgreSQL cho `extract_source`.
3. Refactor từng bước nhỏ (extract function, bảng quy tắc, early return), chạy lại test sau mỗi bước, commit riêng để rollback được.
4. Không đổi thông điệp lỗi công khai, giới hạn mặc định, embedding identity hoặc quy tắc "provider thật không fallback sang fixture" nếu không có ADR.

## Chứng minh test bắt lỗi (mutation testing)

Ở M3 (ASG01 phần kiểm thử), mutation chạy trên một file code học viên tự viết, không chạy trên module legacy. Ở M5, mutation trên module legacy là tùy chọn khi còn timebox. Cách gọn: chạy mutation testing trên đúng file đã chọn, ví dụ `mutmut` cho Python, giới hạn phạm vi file để thời gian chạy ngắn. Ghi số mutant sống, phân tích ít nhất một mutant sống (test thiếu assertion hay mutant tương đương), bổ sung test rồi chạy lại. Không đặt mục tiêu phần trăm mutation score cố định; giá trị nằm ở phân tích.

## Module không dùng cho bài Assignment

Các module dưới đây đã được dùng làm ví dụ phân tích và refactor trong học liệu. Không chọn chúng cho ASG01 để bài làm thể hiện phân tích của chính học viên.

| Module | Hàm hoặc phạm vi |
| --- | --- |
| `api/app/services/reranking.py` | Toàn module |
| `api/app/services/chunking.py` | Toàn module |
| `api/app/services/retrieval.py` | `_pack_contexts` |
| `api/app/services/embeddings.py` | `_real_embed` |

## Chọn module khác

Học viên được chọn module khác (ví dụ `api/app/services/llm.py::_parse_result`, D (22)) nếu nêu lý do trong hồ sơ milestone: độ phức tạp đo được, mức rủi ro, test hiện có và phạm vi ảnh hưởng. Module chọn phải thuộc mã nền của Starter, không phải phần học viên vừa viết, không thuộc danh sách ở mục trên và không thuộc phần scaffold Auth, AI Job hoặc nền UI cấp từ `learner-r1.3`.
