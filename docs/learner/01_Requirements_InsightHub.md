# Requirements: Dự án cá nhân InsightHub

| Thông tin | Giá trị |
| --- | --- |
| Chương trình | B2B C07 SDLC with AI |
| Phiên bản | 1.0, ngày 15/10/2026 |
| Hình thức | Học trực tuyến, dự án cá nhân |
| Thời lượng | 10 buổi, 25 giờ trên lớp, khoảng 46 giờ tự học (2 đến 2,5 giờ mỗi ngày, trần 3 giờ) |
| Baseline | SRS InsightHub v1.1, Starter `learner-r2.0` |
| Thay đổi đề bài | Theo [chính sách thay đổi](#chinh-sach-thay-doi) |

Tài liệu này là đề bài duy nhất của Running Project. Bạn xây **một Feature Slice Quiz** trên Starter InsightHub và đưa nó đi qua đủ các pha SDLC: lập kế hoạch, phân tích yêu cầu, thiết kế, triển khai với coding agent, kiểm thử, phát hành, bảo trì. Đọc mục 1 đến 5 trước, sau đó đọc milestone của buổi đang học.

**Thứ tự ưu tiên tài liệu:** khi Knowledge Content, slide hoặc tài liệu khác nói khác tài liệu này về phạm vi bài làm, việc cần nộp hoặc cách chấm, tài liệu này quyết định.

Tài liệu đính kèm:

| Tài liệu | Vai trò |
| --- | --- |
| [SRS InsightHub v1.1](02_SRS_InsightHub_v1.1.md) | Đặc tả sản phẩm InsightHub: sản phẩm phải làm gì. Bài tập chỉ làm một phần, xác định ở mục 1. Đọc theo [hướng dẫn mục 1.4](#doc-srs), không đọc toàn bộ |
| Tài liệu này | Đề bài: bạn làm phần nào của sản phẩm, làm thế nào, nộp gì, chấm thế nào |
| [API và Schema Reference](03_API_Schema_Reference_v1.1.zip) | Từ M2: OpenAPI, JSON Schema tham khảo để thiết kế phần chênh |

## Mục lục

| Nội dung | Vị trí |
| --- | --- |
| Phạm vi bài làm, Starter có gì | [1. Phạm vi bài làm](#san-pham) |
| Track Build, Track Verify, checkpoint branch | [2. Hai track theo vai trò](#track) |
| Công cụ, provider AI miễn phí, tiết kiệm token, dữ liệu | [3. Công cụ, chi phí và dữ liệu](#cong-cu) |
| Lộ trình, timebox, nhịp học, cách nộp bài | [4. Lộ trình và cách nộp bài](#bat-dau) |
| Cơ cấu điểm, bài chuẩn bị, chính sách thay đổi | [5. Điểm và đánh giá](#danh-gia) |
| Buổi 1, 2 | [6. M0.1](#m01), [7. M0.2](#m02) |
| Buổi 3 đến 5 | [8. M1](#m1), [9. M2.1](#m21), [10. M2](#m2) |
| Buổi 6, 7 | [11. M3.1](#m31), [12. M3](#m3) |
| Buổi 8 đến 10 | [13. M4](#m4), [14. M5 và ASG01](#m5), [15. Capstone](#capstone) |
| Thiết kế và tích hợp với Starter | [16. Tích hợp với Starter](#data-api) |
| Traceability matrix, evidence, danh mục AC | [17. Truy vết và evidence](#evidence) |
| Thuật ngữ | [18. Glossary](#glossary) |

<a id="san-pham"></a>

## 1. Phạm vi bài làm

Bạn xây **Feature Slice Quiz** của InsightHub: người dùng tạo đề trắc nghiệm từ tài liệu, làm bài, máy chủ chấm điểm, người dùng xem lại kết quả. Hành vi sản phẩm theo [SRS](02_SRS_InsightHub_v1.1.md#sec-3-4-10). Sản phẩm đi qua đủ các pha SDLC, từ kế hoạch đến phát hành R1 và thay đổi thành R1.1.

### 1.1. Starter đã có gì, bạn xây gì

| Phần | Starter có sẵn | Việc của bạn |
| --- | --- | --- |
| Đăng nhập email và mật khẩu (Auth scaffold), tài khoản seed A và B (`make seed-users`), đăng xuất trên header | Có. API lấy người dùng bằng dependency `current_user` | Dùng `current_user` cho mọi endpoint Quiz. Không xây đăng ký, xác minh email (Extended) |
| Upload tài liệu, ingestion, embedding, trạng thái `Ready`, xem nguồn | Có. **Kho tài liệu dùng chung**: không gắn người dùng, không cần đăng nhập | Dùng làm nguồn tạo đề. Không phải cách ly tài liệu theo người dùng (điều chỉnh P2) |
| Chat hỏi đáp có citation | Có | Dùng làm đối tượng golden set ở M3 |
| AI Job scaffold: quota, rate limit, idempotency, deadline, publish fence, `record_usage`, `fail_job`, `DenyAllPolicy` | Có cơ chế, chưa có loại tác vụ nào | Viết policy, executor, schema, endpoint tạo đề ([AI Job Framework](../AI_Job_Framework.md), có ví dụ `echo`) |
| Gọi model trả JSON (`llm.generate_json`), retry khi nhà cung cấp lỗi, giả lập lỗi `AI_FIXTURE_FAULTS` | Có (hàm `generate_json` từ Starter `learner-r2.0.1`, trước buổi 6) | Viết prompt, schema, parser của đề và nhánh fixture |
| Web: theo dõi tác vụ (`useJobStatus`), thông tin nhà cung cấp AI (`ProfileDisclosure`), proxy API mẫu | Có. Proxy hiện chỉ đọc tác vụ | Thêm route tạo đề và làm bài theo mẫu proxy `documents` |
| Nền UI (token, component, app shell, `/dev/ui-kit`) | Có ([UI Foundation](../UI_Foundation.md)) | Dựng 3 màn Quiz |
| Eval harness: grader cấu trúc Quiz, pass^k, `ChatAdapter`, `QuizAdapter` dạng khung | Có | Viết `QuizAdapter`, thêm case golden set |
| Backup và restore (`make backup-restore-check`), SBOM, AI-BOM, `/metrics` | Có | Thêm bảng của bạn vào kiểm khôi phục, đưa SBOM và AI-BOM vào CI |
| **Quiz** | Chưa có | **Xây trọn từ spec đến phát hành** |

Các scaffold chỉ là cơ chế dùng chung, không làm AC nào tự đạt. Starter được cấp trước buổi 1. Trong khóa chỉ có hotfix cho lỗi chặn theo [mục 5.6](#chinh-sach-thay-doi).

<a id="core-extended"></a>

### 1.2. Phạm vi chấm: 18 AC Core

Nội dung AC đọc tại SRS theo link. Cột Điều chỉnh dẫn tới quyết định ở mục 1.3. Mức rủi ro R1 cần evidence trực tiếp riêng (mục 4.5).

| # | AC | Rủi ro | Điều chỉnh | Công việc | Hoàn thiện, kiểm tổng hợp |
| --- | --- | --- | --- | --- | --- |
| 1 | [IH-QUIZ-001-AC01](02_SRS_InsightHub_v1.1.md#req-ih-quiz-001) | R2 | P3 | LR-12 | M3.1 → M4 |
| 2 | [IH-QUIZ-001-AC02](02_SRS_InsightHub_v1.1.md#req-ih-quiz-001) | R1 | P3 | LR-12 | M3.1 → M4 |
| 3 | [IH-QUIZ-002-AC01](02_SRS_InsightHub_v1.1.md#req-ih-quiz-002) | R1 |  | LR-13, LR-14 | M3 → M4 |
| 4 | [IH-QUIZ-002-AC02](02_SRS_InsightHub_v1.1.md#req-ih-quiz-002) | R2 | P4 | LR-15, LR-27 | M3 → M5 |
| 5 | [IH-DATA-002-AC01](02_SRS_InsightHub_v1.1.md#req-ih-data-002) | R1 |  | LR-13 | M3.1 → M4 |
| 6 | [IH-DATA-002-AC03](02_SRS_InsightHub_v1.1.md#req-ih-data-002) | R1 | P4 | LR-14, LR-27 | M3 → M5 |
| 7 | [IH-OUT-001-AC02](02_SRS_InsightHub_v1.1.md#req-ih-out-001) | R1 | P1 | LR-15 | M3 → M4 |
| 8 | [IH-NFR-002-AC01](02_SRS_InsightHub_v1.1.md#req-ih-nfr-002) | R1 | P1, P2 | LR-16, LR-22 | M3 → M4 |
| 9 | [IH-NFR-003-AC02](02_SRS_InsightHub_v1.1.md#req-ih-nfr-003) | R1 |  | LR-23, LR-24 | M4 |
| 10 | [IH-INT-002-AC03](02_SRS_InsightHub_v1.1.md#req-ih-int-002) | R1 | P2 | LR-16 | M3 → M4 |
| 11 | [IH-AI-003-AC01](02_SRS_InsightHub_v1.1.md#req-ih-ai-003) | R2 |  | LR-12 | M3.1 → M4 |
| 12 | [IH-AI-005-AC01](02_SRS_InsightHub_v1.1.md#req-ih-ai-005) | R2 | P5 | LR-18, LR-22 | M3 → M4 |
| 13 | [IH-AI-005-AC02](02_SRS_InsightHub_v1.1.md#req-ih-ai-005) | R2 |  | LR-18 | M3 → M4 |
| 14 | [IH-UX-003-AC01](02_SRS_InsightHub_v1.1.md#req-ih-ux-003) | R2 | P6 | LR-10, LR-17 | M3 → M4 |
| 15 | [IH-NFR-009-AC02](02_SRS_InsightHub_v1.1.md#req-ih-nfr-009) | R1 |  | LR-26 | M4 |
| 16 | [IH-REL-001-AC02](02_SRS_InsightHub_v1.1.md#req-ih-rel-001) | R1 |  | LR-25 | M4 |
| 17 | [IH-REL-003-AC01](02_SRS_InsightHub_v1.1.md#req-ih-rel-003) | R2 |  | LR-27 | M5 |
| 18 | [IH-REL-003-AC02](02_SRS_InsightHub_v1.1.md#req-ih-rel-003) | R2 |  | LR-27 | M5 |

**Extended:** mọi AC áp dụng khác của SRS, làm thêm khi Core đã đạt, không trừ điểm khi chưa làm. Nếu làm, ghi evidence như Core. Nếu chưa làm, traceability matrix ghi `Extended-NotDone`. Danh mục đủ 165 AC theo tầng tại [Phụ lục A](#pham-vi-truy-vet). Không yêu cầu hạ tầng cloud hay Kubernetes.

<a id="dieu-chinh"></a>

### 1.3. Điều chỉnh phạm vi bài tập

SRS mô tả sản phẩm đầy đủ. Bài tập chỉ làm Feature Slice Quiz trên Starter, nên áp dụng các điều chỉnh dưới đây. Đây là quyết định của đề bài, không thay yêu cầu sản phẩm.

| Mã | Điều chỉnh | Áp dụng cho |
| --- | --- | --- |
| P1 | Starter chưa có Notebook. Chỗ SRS ghi "cùng Notebook" hoặc "chủ sở hữu Notebook" được hiểu là **người dùng đang đăng nhập**: chủ sở hữu đề, lần làm và tác vụ AI là người tạo. Notebook là Extended | IH-OUT-001-AC02, IH-NFR-002-AC01, LIM-05 |
| P2 | **Kho tài liệu dùng chung** trong môi trường cá nhân: tài liệu của Starter không gắn người dùng. Kiểm quyền IH-NFR-002-AC01 áp dụng cho đề Quiz, lần làm, tác vụ AI và kết quả AI. Cách ly tài liệu theo người dùng là Extended | IH-NFR-002-AC01, IH-INT-002-AC03 |
| P3 | Quiz làm bản **5 câu**. Bản 10 câu và nhánh trả `NoEvidence` khi tài liệu không đủ nội dung là Extended | IH-QUIZ-001-AC01, IH-QUIZ-001-AC02, LIM-17 |
| P4 | Nhánh **làm lại** Quiz (lần làm mới, giữ điểm lần trước) làm ở M5 qua CR-01, thuộc bản R1.1. R1 chỉ cần lưu và mở lại lần đã nộp, nộp lặp đúng | IH-QUIZ-002-AC02, IH-DATA-002-AC03 |
| P5 | Retry trong giới hạn rồi `Failed` đúng nguyên nhân là Core. Nhánh chuyển sang nhà cung cấp dự phòng là Extended | IH-AI-005-AC01 |
| P6 | Yêu cầu bàn phím và focus áp dụng cho màn làm Quiz. Các màn khác kiểm khi làm Extended | IH-UX-003-AC01 |
| P7 | Chỉ một công cụ AI là Quiz. Chỗ SRS nói năm công cụ, lọc theo loại công cụ, Mindmap, Slide, Báo cáo, Tóm tắt không áp dụng cho Core | IH-AI-003-AC01, IH-OUT-001 |

<a id="doc-srs"></a>

### 1.4. Hướng dẫn đọc SRS

SRS dài khoảng 70 nghìn từ. Chỉ đọc các mục dưới đây cho phần Core, mở mục khác khi làm Extended. Khi giao việc cho agent, chỉ định đúng mục hoặc mã yêu cầu, không cho agent đọc cả file.

| Cần | Mục SRS |
| --- | --- |
| Quy tắc chấm Quiz BR-14 | [3.1 Quy tắc nghiệp vụ](02_SRS_InsightHub_v1.1.md#sec-3-1) |
| Giới hạn LIM-05, LIM-10, LIM-11, LIM-17 | [3.2 Giới hạn](02_SRS_InsightHub_v1.1.md#sec-3-2) |
| Tạo đề, làm bài, chấm | [IH-QUIZ-001, IH-QUIZ-002](02_SRS_InsightHub_v1.1.md#sec-3-4-10) |
| Tác vụ AI, lưu kết quả, lỗi nhà cung cấp, usage | [IH-AI-003](02_SRS_InsightHub_v1.1.md#req-ih-ai-003), [IH-AI-005](02_SRS_InsightHub_v1.1.md#req-ih-ai-005) |
| Danh sách và mở lại kết quả | [IH-OUT-001](02_SRS_InsightHub_v1.1.md#req-ih-out-001) |
| Bảo toàn kết quả Quiz | [IH-DATA-002](02_SRS_InsightHub_v1.1.md#req-ih-data-002), [3.7.5](02_SRS_InsightHub_v1.1.md#sec-3-7-5) |
| Từ điển dữ liệu tác vụ, kết quả AI, `QuizAttempt` | [3.7.7](02_SRS_InsightHub_v1.1.md#sec-3-7-7) |
| Thông tin xử lý dữ liệu khi gọi AI | [IH-INT-002](02_SRS_InsightHub_v1.1.md#req-ih-int-002) |
| Bàn phím và focus | [IH-UX-003](02_SRS_InsightHub_v1.1.md#req-ih-ux-003) |
| Quyền, nội dung nguồn, khôi phục | [IH-NFR-002](02_SRS_InsightHub_v1.1.md#req-ih-nfr-002), [IH-NFR-003](02_SRS_InsightHub_v1.1.md#req-ih-nfr-003), [IH-NFR-009](02_SRS_InsightHub_v1.1.md#req-ih-nfr-009) |
| Phát hành và thay đổi | [IH-REL-001](02_SRS_InsightHub_v1.1.md#req-ih-rel-001), [IH-REL-003](02_SRS_InsightHub_v1.1.md#req-ih-rel-003) |

<a id="track"></a>

## 2. Hai track theo vai trò

Chọn track trong bản nộp M1 (dòng `Track: Build` hoặc `Track: Verify`). Được chuyển từ Verify sang Build bất cứ lúc nào. Hai track cùng sản phẩm, cùng milestone, cùng rubric.

| | Track Build (khuyến nghị cho Dev) | Track Verify (khuyến nghị cho BA, Tester, PM) |
| --- | --- | --- |
| M0.1 đến M2 | Như nhau | Như nhau |
| M3.1, M3 | Tự xây Quiz qua agent | Tự giao agent làm **ít nhất 1 task** của `tasks.md` (gợi ý: API làm bài không lộ đáp án, hoặc hàm chấm BR-14). Phần còn lại được merge checkpoint branch |
| Trọng tâm chấm phần triển khai | Brief, TDD, review diff của agent, chất lượng PR | Brief của task tự làm, TDD trên task đó, **review PR checkpoint có ít nhất 2 finding đã xác minh**, test và evidence |
| M4, M5, Capstone | Như nhau | Như nhau |

### 2.1. Checkpoint branch

Mentor phát hành nhánh tham chiếu trên Starter: `checkpoint/m3.1` trước buổi 6 và `checkpoint/m3` trước buổi 7. Cách dùng:

1. Làm thử trước. Ghi trong bản chuẩn bị phần đã thử, lỗi gặp và thời gian thực tế.
2. Merge qua một PR riêng `chore/checkpoint-m3.1` (hoặc `chore/checkpoint-m3`) vào nhánh milestone. Mô tả PR ghi lý do dùng checkpoint.
3. Review PR checkpoint như review PR của một agent: chạy test, đối chiếu AC, ghi finding Fix, Reject hoặc Defer.
4. Phần merge từ checkpoint không tính điểm triển khai. Phần review, test, evidence trên phần đó vẫn được tính.

Track Build cũng được dùng checkpoint khi bị chặn, cùng quy tắc trên.

### 2.2. Buddy

Mentor ghép mỗi bạn Track Verify với một bạn Track Build để hỗ trợ lỗi môi trường (Docker, WSL2, migration, test fail). Buddy giúp chẩn đoán, không làm hộ bài.

<a id="cong-cu"></a>

## 3. Công cụ, chi phí và dữ liệu

### 3.1. Công cụ phát triển

Công ty cấp tài khoản Claude Pro/Max cho học viên, chỉ dùng cho học tập. Claude App for Desktop và Claude Code trên máy cá nhân là công cụ AI chính. ChatGPT/Codex là phương án bổ sung nếu học viên có tài khoản, không bắt buộc. Mỗi Tool Guideline viết theo Claude và có mục Mapping ChatGPT/Codex. MCP bắt buộc từ M0.2 với role cơ sở dữ liệu chỉ đọc của Starter. Học trên máy cá nhân, tự chuẩn bị Docker theo [GETTING_STARTED](../../GETTING_STARTED.md). Máy Windows dùng WSL2.

### 3.2. Provider AI của sản phẩm

Đây là AI mà **ứng dụng InsightHub** gọi để sinh đề, khác với tài khoản Claude dùng để phát triển.

| Tầng | Cấu hình | Chi phí | Khi dùng |
| --- | --- | --- | --- |
| 0. Mặc định | `RAG_MODE=fixture` | 0 | Toàn bộ phát triển, test, CI. Executor Quiz bắt buộc có nhánh fixture chạy offline |
| 1A. Miễn phí, chạy trên máy | Ollama cho cả sinh nội dung và embedding ([Model Profiles](../Model_Profiles_And_Reranking.md), phương án D và ghi chú chạy offline) | 0 | Máy có RAM từ 16 GB |
| 1B. Miễn phí, cloud | Gemini free tier cho cả hai ([Model Profiles](../Model_Profiles_And_Reranking.md), phương án A) | 0 | Máy yếu. Giới hạn request thấp. Dữ liệu free tier có thể được nhà cung cấp dùng để cải thiện sản phẩm, nên **chỉ dùng corpus giả của Starter** |
| 2. Tùy chọn | DeepSeek hoặc provider trả phí khác | Thấp | Không bắt buộc. Tự chịu chi phí và đặt spending limit |

**AI thật chỉ bắt buộc ở hai điểm:** spike AI ở M2.1 (LR-09) và eval nội dung Quiz ở M4 (LR-23). Mọi điểm khác dùng fixture. Fixture kiểm hành vi phần mềm, không chứng minh chất lượng nội dung của model thật. Key chỉ giữ trong `.env`, không commit, không dán vào Claude hay công cụ AI khác.

### 3.3. Dùng Claude tiết kiệm token

Tài khoản Claude có hạn mức. Vượt hạn mức thì học viên tự nạp thêm. Phần lớn token bị đốt vì agent đọc tài liệu dài hoặc làm task quá lớn.

| Quy tắc | Vì sao |
| --- | --- |
| **Chỉ định đúng mục cần dùng** của tài liệu này hoặc của SRS theo [mục 1.4](#doc-srs). Không cho agent đọc cả SRS | SRS dài khoảng 70 nghìn từ, đọc một lần chiếm phần lớn context window |
| Mặc định dùng Sonnet. Chỉ chuyển Opus khi lập plan khó | Opus tốn hạn mức nhiều hơn |
| Mỗi task một session. Dùng `/clear` khi đổi task, `/compact` khi session dài | Context cũ bị gửi lại ở mỗi lượt |
| Dùng plan mode, duyệt plan trước khi cho agent sửa code | Tránh làm lại cả task |
| Chạy test có phạm vi (một file, một test) khi đang sửa. Chạy toàn bộ trước khi mở PR | Log test dài cũng là token |
| Chạy task dài sớm trong ngày, không dồn sát hạn nộp | Tránh chạm giới hạn sử dụng đúng lúc cần nộp |

### 3.4. Tài khoản và dữ liệu khi dùng AI

- Trước buổi 1, mở `claude.ai/settings/data-privacy-controls` và **tắt** thiết lập cho phép dùng dữ liệu để cải thiện model. Ghi xác nhận trong checklist setup buổi 1.
- Chỉ đưa vào Claude: Starter, corpus giả và bài làm của chính mình. Không đưa mã nguồn, tài liệu, dữ liệu hoặc credential của Samsung SDS hay khách hàng. Không đưa `.env`, API key, token. Giữ các rule `deny` trong `.claude/settings.json` của Starter.
- Không dùng `/feedback` hoặc chia sẻ transcript khi có nội dung bài làm chưa công khai.
- Dùng tài khoản Google và email test riêng cho khóa học. Không dùng tài khoản công ty.
- Starter là repository public nên fork của bạn cũng public: không commit dữ liệu thật, thông tin cá nhân, `.env` hoặc API key.
- Khi áp dụng vào dự án thật sau khóa học, chỉ dùng công cụ AI và dữ liệu được Samsung SDS phê duyệt.

### 3.5. Cách làm với AI

Được dùng AI Agent xuyên quá trình đọc nguồn, phân tích, lập kế hoạch, thiết kế, code, test, review và soạn hồ sơ. Bạn đối chiếu và chốt expected result theo nguồn, kiểm thay đổi và giải thích quyết định. Với bước nền, tự giải thích được mục tiêu, input, expected và cách kiểm trước khi giao agent. Lưu một vài quyết định tiêu biểu đã giữ, sửa hoặc bác bỏ đề xuất AI cùng lý do. Không cần nộp toàn bộ hội thoại. Quiz của khóa vẫn tự làm, không dùng AI.

<a id="bat-dau"></a>

## 4. Lộ trình và cách nộp bài

<a id="timebox"></a>

### 4.1. Lộ trình và timebox

| Buổi | Mốc | Milestone | Kết quả chính | Đọc KC/TG | Quiz, chuẩn bị | Timebox LR (phút) | Tự học |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Mốc 0 | M0.1 | Starter chạy upload, hỏi đáp, citation. Một phân tích yêu cầu bằng AI đã được kiểm | 120 phút | 35 phút | LR-01: 45<br>LR-02: 35<br>LR-03: 20<br>sửa theo phản hồi: 5 | 4,3 giờ |
| 2 | Mốc 0 | M0.2 | Workflow agent có giới hạn quyền, xử lý lỗi, chạy lại được | 125 phút | 35 phút | LR-04: 45<br>LR-05: 80<br>sửa theo phản hồi: 10 | 4,9 giờ |
| 3 | Mốc 1 | M1 | Backlog Quiz, Lifecycle Board, Charter có 2 stop condition enforced, Git/CI, AI Delivery Log | 95 phút | 35 phút | LR-06: 35<br>LR-07: 30 | 3,3 giờ |
| 4 | Mốc 2 | M2.1 | Trace 18 AC, lấy mẫu bản nháp AI, `spec.md` Quiz, spike AI | 130 phút | 35 phút | LR-08: 75<br>LR-09: 30 | 4,5 giờ |
| 5 | Mốc 3 | M2 | Prototype HTML 3 màn, API và schema, sơ đồ C4, sequence, state machine, ADR, threat model, `plan.md`/`tasks.md`, AI design review, review chéo | 150 phút | 35 phút | LR-10: 45<br>LR-11: 85<br>review bất đồng bộ: 20 | 5,6 giờ |
| 6 | Mốc 4 | M3.1 | Tạo đề qua AI Job (fixture), API làm bài không lộ đáp án, TDD | 110 phút | 35 phút | LR-12: 90<br>LR-13: 60 | 4,9 giờ |
| 7 | Mốc 5 | M3 | Chấm, lưu, mở lại, quyền A/B. Kiểm thử đa tầng có kỹ thuật thiết kế test (ASG01 phần 1) | 130 phút | 35 phút | LR-14: 35<br>LR-15: 25<br>LR-16: 20<br>LR-17: 20<br>LR-18: 20<br>LR-19: 70 | 5,9 giờ |
| 8 | Mốc 6 | M4 | Release gate, UAT, R1, restore, SBOM, eval 6 lượt, SLI/SLO, diễn tập incident | 150 phút | 35 phút | LR-20: 15<br>LR-21: 10<br>LR-22: 10<br>LR-23: 25<br>LR-24: 20<br>LR-25: 35<br>LR-26: 65 | 6,1 giờ |
| 9 | Mốc 7 | M5 | CR-01 thành R1.1, xử lý một lỗ hổng, refactor legacy (ASG01 phần 2) | 100 phút | 35 phút | LR-27: 130 (CR 45, lỗ hổng 20, refactor 65) | 4,4 giờ |
| 10 | Capstone | Capstone | Hồ sơ Capstone, lộ trình 30/60/90 | 55 phút | 25 phút (Quiz) | LR-28: 40<br>LR-29: 20 | 2,3 giờ |
| **Tổng** | | | | | | | **khoảng 46 giờ** |

Hạn hoàn thiện mỗi milestone: trước buổi kế tiếp ít nhất 12 giờ. Capstone: bản nháp trước buổi 10 ít nhất 2 giờ, bản cuối trong 3 ngày sau buổi 10. Từ buổi 3 trở đi, timebox LR đã gồm phần sửa theo phản hồi sau buổi học. Cột Mốc là tên dùng trong Knowledge Content và slide.

Timebox là mốc tự kiểm tiến độ, không thay hạn nộp hay rubric. Vượt khoảng 50% mà chưa có hướng xử lý thì dừng, ghi phần đã làm, phần bị chặn, thời gian thực tế vào bản chuẩn bị. Track Verify cân nhắc checkpoint branch ở bước này. Ghi thời gian thực tế vào `docs/ai/delivery-log.csv`. Số phút được điều chỉnh theo số đo thực tế của lớp theo [mục 5.6](#chinh-sach-thay-doi).

Học liệu phát hành theo bốn đợt: trước buổi 1 (Starter, tài liệu này, KC/TG/Quiz buổi 1, 2), buổi 3 đến 5, buổi 6 đến 8, buổi 9, 10. Ngày phát hành công bố trên kênh lớp.

<a id="nhip-tuan-mau"></a>

### 4.2. Nhịp học "đi trước một buổi"

- **Trước buổi n:** đọc KC/TG buổi n, làm Quiz, làm phần milestone n trong khả năng và gửi bản chuẩn bị (phần đã làm và câu hỏi cần hỗ trợ) trước giờ học ít nhất 2 giờ.
- **Trên lớp:** trao đổi điểm khó của dự án gắn với nội dung buổi, thực hành trên tiến độ của chính bạn.
- **Sau buổi n:** sửa theo phản hồi, hoàn thiện milestone n trước hạn, đọc và làm trước phần buổi kế tiếp.
- **Ngân sách gợi ý:** 2 giờ vào ngày có lớp, 2,5 giờ vào ngày không có lớp, trần 3 giờ chỉ dùng khi cần bù. Buổi 5, 7 và 8 nặng nhất. Bắt đầu M3.1 trước buổi 6, chuẩn bị kịch bản UAT từ cuối M3.

<a id="pr-theo-task"></a>

### 4.3. Repository cá nhân và cách nộp bài

1. **Fork** Starter vào tài khoản cá nhân (hoặc tổ chức lớp chỉ định), clone về máy, thiết lập remote `upstream` trỏ tới Starter để nhận hotfix.
2. Mỗi milestone tạo một nhánh `milestone/<mã>` (ví dụ `milestone/m1`). Commit mã nguồn, tài liệu, test của phần đã làm và push lên repository cá nhân.
3. Tạo **Pull Request** từ nhánh milestone vào `main` của **chính repository cá nhân**. Không gửi PR vào Starter.
4. Gửi **link PR và link bản ghi nộp bài** qua kênh nộp bài của lớp. Chỉ push lên Git chưa được coi là đã nộp.
5. Sau buổi học, push bản sửa lên cùng nhánh, gửi lại link kèm trạng thái "Bản hoàn thiện". Không force-push hoặc xóa PR để thay bài.
6. Tự rà soát xong và kiểm tra đạt thì merge PR vào `main`. Milestone tiếp theo tạo nhánh từ `main` đã cập nhật.

**PR theo task (từ M3.1).** Mỗi task giao agent dùng nhánh ngắn `task/<số issue>-<tên ngắn>` tạo từ nhánh milestone và mở một PR nhỏ vào nhánh milestone. PR task khoảng 400 dòng diff (không tính file sinh tự động), có task brief, checklist DoD, CI trên commit cuối, review 4 góc (tính đúng, bảo mật, quy ước mã nguồn, thiết kế). PR milestone vào `main` là bài nộp, mô tả liệt kê link các PR task. Không dùng squash merge để giữ thứ tự test fail trước khi pass.

**Commit:** mỗi commit một thay đổi có ý nghĩa, dạng `type(scope): mô tả`, ví dụ `feat(quiz): hide answers before submit`, `test(quiz): grade blank answers as wrong`. Tránh `update`, `fix all`. Không chấm theo số commit. Tag chỉ bắt buộc cho R1 (M4) và R1.1 (M5).

**Bài luyện trên lớp.** Lab dùng tính năng ví dụ (như Tóm tắt) đặt output trong thư mục `practice/<buổi>/` của repo cá nhân, không đặt vào `specs/`, `design/`, `docs/adr/` của bài làm. Thư mục `practice/` không chấm và không tính vào trace. Lượt luyện không ghi vào `docs/ai/delivery-log.csv` (file này chỉ chứa số đo thật của bài làm), muốn ghi lại thì dùng `practice/<buổi>/notes.md`.

**Bản ghi nộp bài** đặt tại `evidence/<milestone>/submission.md`:

```text
Milestone: M1
Track: Build | Verify
Link Pull Request:
Phiên bản mã nguồn đã kiểm tra: <link commit>
Đã hoàn thành: <việc và đường dẫn file/prototype/kết quả>
Output milestone: <đạt/chưa đạt, phạm vi đến hạn và lý do>
Đã kiểm tra: <lệnh hoặc bước chạy, kỳ vọng, thực tế, link log>
Quyết định với AI: <đề xuất đã giữ/sửa/bác bỏ và lý do>
AI Delivery Log: <các dòng đã ghi cho PR của milestone>
Còn thiếu hoặc cần hỗ trợ:
```

Lấy link commit từ mục Commits của PR và kiểm đúng phiên bản đó. Log phải lọc thông tin nhạy cảm, ghi rõ chạy fixture hay dịch vụ thật.

<a id="ai-kit"></a>

### 4.4. AI Engineering Kit xuyên milestone

Repository ghi lại cách dự án làm việc với AI: quy tắc agent, quyền, skill, hook, quy trình review, spec, eval và số đo. Mỗi thành phần gắn vào output LR của milestone, không tạo bài nộp riêng. Bản đồ theo milestone tại [docs/ai/README.md](../ai/README.md). Số đo trong `docs/ai/delivery-log.csv` là số thật. Không đo được thì để trống và ghi lý do.

<a id="kiem-chung-rui-ro"></a>

### 4.5. Kiểm chứng theo rủi ro

| Mức | Nhóm AC | Evidence ở M4 |
| --- | --- | --- |
| R1 | Quyền truy cập, lộ đáp án, mất dữ liệu, grounding, secret, phát hành | Evidence trực tiếp riêng, có `test_ids` |
| R2 | Vòng đời tác vụ, trạng thái, usage, bàn phím, CR | Dùng chung evidence được nếu mapping rõ |
| R3 | Thông báo, tài liệu | Checklist hoặc lấy mẫu |

- Expected của AC phải `Human-verified` **trước** khi giao agent triển khai AC đó.
- AI viết nháp nhanh hơn khả năng người kiểm từng dòng. Bản nháp AI phải ghi `draft_by=AI` và được bạn kiểm lại. Hạ mức rủi ro phải ghi lý do.

<a id="danh-gia"></a>

## 5. Điểm và đánh giá

### 5.1. Cách đọc rubric

Mỗi milestone có **rubric 100 điểm để phản hồi tiến độ**. Phần có kết quả và minh chứng đúng thì nhận điểm phần đó. Phần chưa làm, chưa đúng hoặc chưa kiểm được nhận 0. Rubric milestone dùng để phản hồi, không cộng vào điểm khóa. Prototype do bạn tạo ở M2 dùng tiếp cho triển khai và test. Module legacy chỉ định giữ nguyên đến M5.

### 5.2. Cơ cấu điểm khóa

| Thành phần | Trọng số | Cách xác định |
| --- | --- | --- |
| Quiz | 10% | Trung bình 10 Quiz. Mỗi Quiz 15 câu, 25 phút, làm một lần trước buổi học, tự làm, không dùng AI. Đạt từ 70% cho thấy đã đọc KC/TG. Dưới 70% thì đọc lại phần liên quan trước buổi học |
| Chuẩn bị trước buổi học | 15% | Trung bình 10 bản chuẩn bị, chấm theo mục 5.3 |
| ASG01 Legacy và kiểm thử đa tầng | 25% | Phần kiểm thử làm sau buổi 7 (LR-19), phần legacy làm sau buổi 9 (LR-27). Bản cuối nộp cùng Capstone. Rubric tại [mục 14.4](#asg01) |
| Capstone | 35% | Rubric 6 nhóm tại [mục 15.3](#capstone). Top 4 đến 5 học viên Q&A trên lớp |
| Chuyên cần và review | 15% | Tham dự và một lần review bất đồng bộ tại M2 |

Quy các điểm thành phần về thang 10. Điểm khóa = `0,10 × Quiz + 0,15 × Chuẩn bị + 0,25 × ASG01 + 0,35 × Capstone + 0,15 × Chuyên cần/review`.

**Điều kiện hoàn thành:** tổng điểm và Capstone từ 6/10, không thành phần nào bằng 0, tham dự ít nhất 8/10 buổi.

### 5.3. Bài chuẩn bị trước buổi học

Mỗi tiêu chí tối đa 25 điểm. Chọn mức cao nhất đáp ứng đầy đủ mô tả, nhân điểm tối đa với 0/40/70/100%, cộng bốn dòng rồi chia 10.

| Tiêu chí | Chưa có (0%) | Một phần (40%) | Đạt cốt lõi (70%) | Đầy đủ (100%) |
| --- | --- | --- | --- | --- |
| Phần tự thực hiện và câu hỏi | Chưa có bài | Chưa xác định phần đã tự làm | Có kết quả tự học/thực hành phù hợp buổi và phần cần hỗ trợ | Kết quả mở được, xác định rõ phụ thuộc và cách đã thử xử lý |
| Tính đúng | Không kiểm được nội dung | Có lỗi cơ bản chưa nhận diện | Phần đã làm đúng với tài liệu và phạm vi | Kiểm thêm tình huống biên và sửa sai có căn cứ |
| Giải thích cách làm và sử dụng AI | Chỉ chép đầu ra | Có kết luận thiếu lý do | Nêu cách tự phân tích, phần AI hỗ trợ và quyết định | So sánh phương án, nêu giới hạn và câu hỏi cụ thể |
| Minh chứng | Không có căn cứ | Chỉ khẳng định hoặc ảnh thiếu ngữ cảnh | Có đầu vào, kỳ vọng và kết quả thực tế | Người khác kiểm lại được, đúng phiên bản, rõ phần chưa kiểm |

Bản chuẩn bị không cần hoàn tất milestone. Dẫn tới PR và bản ghi nộp bài đang làm, ghi phần đã làm, phần bị chặn và câu hỏi. Không soạn tài liệu riêng. Bản chuẩn bị buổi 10 là bản nháp Capstone.

### 5.4. Chuyên cần và review

- Điểm tham dự trên thang 10 bằng số buổi tham dự hợp lệ.
- Review tại M2 chấm 0/4/7/10: không nộp / nhận xét chung / nhận xét gắn yêu cầu và minh chứng, có đề xuất kiểm / nhận xét đã đối chiếu, giải thích tác động và có kết quả theo dõi.
- Điểm chuyên cần và review = `(2 × điểm tham dự + điểm review) / 3`.
- Không buộc tìm lỗi nếu sản phẩm đúng. Chưa có bài bạn học thì dùng mẫu mentor cấp.

### 5.5. Nguyên tắc phản hồi

- Ghi tên tiêu chí, điểm, căn cứ và việc cần sửa. Không chấm bằng số commit, số dòng code, số prompt hay số công cụ AI.
- Điểm học tập và trạng thái sản phẩm là hai kết quả riêng. Điểm đạt không biến AC chưa kiểm thành đạt.
- Lỗi chặn phát hành phải sửa và kiểm lại trước khi kết luận bàn giao. Dịch vụ mô phỏng không thay kết quả tích hợp thật.
- Thời điểm nhận bài dựa trên kênh nộp của lớp, áp dụng chính sách lớp đã công bố.

<a id="chinh-sach-thay-doi"></a>

### 5.6. Chính sách thay đổi đề bài

Tài liệu này, SRS InsightHub v1.1 và Starter `learner-r2.0` là baseline của lớp. Thay đổi sau đó được xử lý như một change request, đúng cách bạn làm ở M5:

| Loại thay đổi | Cách công bố | Ảnh hưởng tới bài làm |
| --- | --- | --- |
| Hiệu chỉnh timebox, phạm vi AC hoặc rubric | Thông báo trên kênh lớp kèm phân tích tác động và ngày hiệu lực | Áp dụng từ milestone chưa đến hạn. Không chấm lại milestone đã nộp theo quy tắc mới bất lợi cho học viên |
| Hotfix Starter cho lỗi chặn | Tag hotfix trên Starter kèm ghi chú phát hành | Merge qua một PR `chore/sync-starter`, chạy lại test. Xung đột ở `AGENTS.md` thì giữ cả rule của bạn và rule mới |
| Sửa lỗi văn bản không đổi yêu cầu | Ghi trong nhật ký phiên bản | Không phải làm gì thêm |

Phát hiện mâu thuẫn hoặc thiếu trong đề bài thì ghi vào bản chuẩn bị kèm căn cứ. Không tự đổi yêu cầu.

<a id="m01"></a>

## 6. M0.1 (buổi 1): Chạy Starter và kiểm chứng một phân tích yêu cầu bằng AI

**Trọng tâm SDLC:** khảo sát baseline, kiểm chứng đầu ra AI.

### 6.1. Việc cần làm

<a id="lr-01"></a>

1. **LR-01 Khởi động Starter.** Fork, clone, thiết lập `upstream`, ghi link commit nền, chạy chế độ fixture theo [GETTING_STARTED](../../GETTING_STARTED.md). Tạo hai tài khoản thử bằng `make seed-users`, đăng nhập A và B tại `/login` rồi đăng xuất. Tải một file hợp lệ và một file lỗi, hỏi đáp và mở nguồn. Ghi lệnh, kết quả và lỗi. Giải thích vì sao fixture chưa chứng minh chất lượng AI thật. Kiểm thiết lập privacy theo mục 3.4 trước khi dùng Claude.

<a id="lr-02"></a>

2. **LR-02 Tạo đầu ra có cấu trúc.** Chọn một AC trong SRS, tự xác định điều kiện ban đầu, hành vi và expected result. Ghi ngữ cảnh đưa cho Claude vào `docs/ai/context-pack.md` theo [template](../ai/templates/context-pack.md). Chạy một lượt A/B có và không có một quy tắc ngữ cảnh, ghi số token. Tự viết JSON Schema cho đầu ra, yêu cầu Claude trả JSON gồm tình huống thành công và lỗi, kiểm bằng validator (`jsonschema` hoặc `ajv`), rồi đối chiếu nội dung với AC gốc. JSON hợp lệ chưa chứng minh phân tích đúng.

<a id="lr-03"></a>

3. **LR-03 Phát hiện và sửa một lỗi AI.** Dùng một đề xuất sai thực tế hoặc lỗi có chủ đích do lớp cung cấp. Chỉ ra sai ở đâu bằng tài liệu, mã nguồn hoặc phép thử độc lập, sửa và kiểm lại. Biến bài học thành một rule trong `AGENTS.md` kèm cách kiểm (lệnh, test hoặc cơ chế chặn).

### 6.2. Output nộp

Link PR `milestone/m0.1`, bản ghi nộp bài: kết quả setup, context pack, prompt, JSON và schema, trường hợp AI sai, kết quả kiểm lại, rule đã thêm vào `AGENTS.md`.

### 6.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Môi trường và thao tác nền | 30 | Khởi động được ứng dụng: 10. Tải file hợp lệ và hỏi đáp có nguồn: 10. Nhận diện đúng file lỗi: 10 |
| Prompt và đầu ra JSON | 25 | Context pack và lượt A/B có token: 5. Kiểm schema: 10. Đối chiếu nội dung với yêu cầu gốc: 10 |
| Kiểm chứng và sửa lỗi AI | 30 | Tái hiện lỗi: 10. Căn cứ độc lập: 10. Sửa và kiểm lại: 5. Rule `AGENTS.md` có cách kiểm: 5 |
| Bài nộp và giải thích | 15 | PR truy cập được: 5. Kết quả kiểm có phiên bản: 5. Giải thích giới hạn của fixture: 5 |

<a id="m02"></a>

## 7. M0.2 (buổi 2): Xây workflow AI Agent có giới hạn quyền

**Trọng tâm SDLC:** thiết lập cách làm việc với agent dùng xuyên dự án.

Trước buổi 2, cấu hình **MCP PostgreSQL chỉ đọc** theo [GETTING_STARTED](../../GETTING_STARTED.md): role `insighthub_readonly`, server `tools/mcp/insighthub_db_readonly.py`, file `.mcp.json` tạo từ `.mcp.json.example` và không commit. Máy không chạy được MCP thì dùng Claude Code gọi `psql` bằng chính role chỉ đọc, evidence vẫn phải có lỗi do database trả về.

### 7.1. Việc cần làm

<a id="lr-04"></a>

1. **LR-04 AI Usage Charter.** Lập `docs/ai/AI_Usage_Charter.md` theo [template](../ai/templates/AI_Usage_Charter.md): phân loại dữ liệu 4 mức (Public, Internal, Confidential, Personal/Sensitive) và mức nào được đưa vào AI, thư mục và lệnh được phép, người quyết định, cách dừng và khôi phục, ghi chú pháp lý Việt Nam ở mức áp dụng (Luật Trí tuệ nhân tạo 134/2025/QH15, Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15). Thử một thao tác ngoài quyền bằng dữ liệu giả và chứng minh công cụ hoặc môi trường đã từ chối. Lời "không được phép" của mô hình chưa chứng minh giới hạn quyền.

<a id="lr-05"></a>

2. **LR-05 Quy trình agent có dùng công cụ và MCP.** Chọn một công việc nhỏ (đọc API, chạy một nhóm test, đối chiếu dữ liệu qua MCP). Ghi mục tiêu, phạm vi, kế hoạch, checkpoint, expected trước khi chạy. Evidence MCP gồm ba lượt: gọi tool hợp lệ, một lỗi tool, một lệnh ghi bị database từ chối. Đóng gói quy trình thành skill `.claude/skills/<tên>/SKILL.md` theo [template](../ai/templates/SKILL.template.md) để chạy lại được.

### 7.2. Output nộp

Link PR `milestone/m0.2`, Charter, skill, log thực hành, ba lượt evidence MCP, kết quả kiểm giới hạn quyền. Không commit `.mcp.json` hoặc mật khẩu role.

### 7.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| AI Usage Charter và quyền | 25 | Charter gắn đúng repository: 10. Phân loại dữ liệu và quyền rõ: 10. Cách dừng và khôi phục: 5 |
| Quy trình agent thực chạy | 30 | Kế hoạch rõ: 10. Thao tác công cụ và MCP có log: 10. Đối chiếu kết quả với mục tiêu: 10 |
| Xử lý lỗi và giới hạn | 25 | Thử yêu cầu vượt phạm vi: 10. Xử lý lỗi công cụ: 10. Khôi phục từ checkpoint: 5 |
| Tái sử dụng và nộp bài | 20 | Skill chạy lại được: 10. PR và minh chứng đủ để giải thích: 10 |

<a id="m1"></a>

## 8. M1 (buổi 3): Lập kế hoạch Quiz và thiết lập Git/CI

**Trọng tâm SDLC:** khởi tạo, lập kế hoạch, kiểm soát thay đổi.

### 8.1. Việc cần làm

<a id="lr-06"></a>

1. **LR-06 Hồ sơ, backlog và Lifecycle Board.**
   - Ghi người dùng, hành trình Quiz và fit-gap với Starter (bảng mục 1.1: Fit, Partial hay phải xây).
   - Lập **5 đến 8 issue** theo kết quả chức năng, ví dụ: schema và migration Quiz, AI Job tạo đề, API làm bài, chấm và lưu lần làm, 3 màn UI, kiểm thử, phát hành R1. Mỗi issue có AC liên quan (mục 1.3), phụ thuộc, ước lượng T-shirt (S, M, L) và cách kiểm. Không tạo mỗi AC một issue.
   - Hoàn thiện Lifecycle Board từ lab buổi 3: bảng gate 6 pha (entry, exit criteria kiểm được, evidence, người duyệt), bản đồ AI theo pha (việc AI làm, Mức AI, sensor, người duyệt).
   - Cập nhật Charter: RACI (mỗi quyết định đúng một người chịu trách nhiệm cuối, agent không giữ vai này) và **2 stop condition enforced** (`deny`, hook hoặc CI). Được dùng 1 cơ chế Starter có sẵn (ví dụ hook bảo vệ test đã duyệt), ít nhất 1 do bạn tự cấu hình. Thử chạy lệnh bị chặn và ghi kết quả.

<a id="lr-07"></a>

2. **LR-07 Git và CI.** Issue theo [template](../../.github/ISSUE_TEMPLATE/feature.md), PR theo [PR template](../../.github/pull_request_template.md) có tự review, sau đó `/code-review --comment <số PR>` trong session Claude Code mới ([Review Workflow](../ai/Review_Workflow.md)). Phân loại finding Fix, Reject hoặc Defer, tự xác minh một finding. CI của Starter chạy pass trên fork, thêm lint và secret scan theo [hướng dẫn M1](../M1_Lint_Scan_Guide.md). Dependency scan là tùy chọn. Ghi dòng đầu tiên của `docs/ai/delivery-log.csv` làm baseline.

### 8.2. Output nộp

Link PR `milestone/m1`, bản ghi nộp bài có dòng `Track:`, hồ sơ và backlog, Lifecycle Board, Charter, link lần chạy CI. Có thể gộp tài liệu trong một file Markdown.

### 8.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Phạm vi và fit-gap | 20 | Hành trình Quiz rõ: 10. Phân biệt đúng phần Starter có sẵn và phần phải xây: 10 |
| Backlog | 20 | Issue gắn AC và kết quả: 10. Phụ thuộc và thứ tự đúng, có ước lượng: 10 |
| Lifecycle Board và Charter | 25 | Gate 6 pha có tiêu chí kiểm được: 10. Bản đồ AI có Mức AI và sensor: 5. RACI đúng một người chịu trách nhiệm cuối, 2 stop condition enforced và ít nhất 1 tự cấu hình: 10 |
| Git và CI | 25 | PR theo template có `/code-review` và finding đã xác minh: 15. CI có test và lint thực chạy: 10 |
| Quyết định với AI | 10 | Một điều chỉnh có căn cứ sau khi phản biện đề xuất AI: 5. Delivery Log có baseline: 5 |

<a id="m21"></a>

## 9. M2.1 (buổi 4): Phân tích yêu cầu Quiz và spike AI

**Trọng tâm SDLC:** phân tích yêu cầu, thiết kế test, giảm rủi ro kỹ thuật.

### 9.1. Việc cần làm

<a id="lr-08"></a>

1. **LR-08 Trace, spec và ước lượng.**
   - Trên `trace/ac-trace.csv`, dùng AI viết nháp nhánh, input, expected cho 18 AC Core (`draft_by=AI`), sau đó **tự kiểm 100%** và chuyển `Human-verified`. Chạy `python3 scripts/trace_check.py`. Bao phủ luồng chính, lỗi, sai quyền, nộp lặp. Cách ghi tại [mục 17](#bang-ket-qua).
   - Lập `specs/quiz/spec.md` theo [template](../../specs/_template/spec.md): yêu cầu viết theo EARS kèm nguồn SRS, AC 3 nhánh (thành công, lỗi, sai quyền) cho AC R1, NFR có số đo (ví dụ thời hạn LIM-11), clarification log. Viết 1 kịch bản Gherkin cho một AC R1, dùng lại làm E2E ở M3.
   - **Lấy mẫu bản nháp AI.** Dùng AI viết nháp `branches`, `expected` cho 12 AC Extended nhóm AI và OUT (`draft_by=AI`, giữ `Unverified`). Chạy `make trace-sample SEED=<mã học viên> SIZE=5 TIER=Extended`, tự kiểm 5 dòng được chọn với SRS, ghi `result` OK hoặc Error vào `trace/sampling-log.csv`, chạy `python3 scripts/trace_sample.py --evaluate`. Ghi một câu kết luận: giữ phần bản nháp còn lại hay phải sửa prompt và sinh lại. Không kiểm 7 dòng còn lại.
   - Ước lượng lại các issue bằng three-point hoặc story point, đối chiếu timebox mục 4.1, ghi phần chênh.

<a id="lr-09"></a>

2. **LR-09 Spike AI.** Chọn tầng provider (mục 3.2). Trước khi thử, ghi giả thuyết, phép thử, expected. Chạy một lần sinh đề 5 câu trên 1 tài liệu mẫu bằng AI thật, ghi provider, model, token, thời gian và output có đúng cấu trúc hay không. Giả lập lỗi provider bằng `AI_FIXTURE_FAULTS` ([AI Job Framework](../AI_Job_Framework.md)). Kết luận chọn provider nào cho M4 và vì sao.

### 9.2. Output nộp

Link PR `milestone/m2.1`, `trace/ac-trace.csv`, `trace/sampling-log.csv` và kết quả `--evaluate`, `specs/quiz/spec.md`, kết quả spike có giới hạn, ước lượng đã cập nhật.

### 9.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Trace và kiểm bản nháp AI | 30 | 18 AC `Human-verified`, nguồn gốc bản nháp ghi đúng: 10. Lấy mẫu 5 dòng có seed, có `result` và kết luận: 5. `trace_check.py` pass: 5. Chỉ ra ít nhất một lỗi của bản nháp AI đã sửa: 10 |
| Spec và test design | 30 | EARS có nguồn, AC 3 nhánh cho R1: 15. Expected cụ thể, có sai quyền và nộp lặp: 10. Gherkin: 5 |
| Spike AI | 25 | Giả thuyết, expected và actual rõ, phân biệt thật và giả lập: 15. Quyết định provider có căn cứ: 10 |
| Ước lượng | 15 | Có căn cứ: 10. Đối chiếu timebox, ghi chênh lệch: 5 |

<a id="m2"></a>

## 10. M2 (buổi 5): Thiết kế Quiz

**Trọng tâm SDLC:** thiết kế giải pháp, quyết định kiến trúc, threat modeling.

### 10.1. Việc cần làm

<a id="lr-10"></a>

1. **LR-10 Prototype HTML 3 màn** (tạo đề, làm bài, kết quả) trong `design/prototype/`, nhúng `design/prototype/_base/` theo [UI Foundation](../UI_Foundation.md). Được dùng AI dựng nháp, sau đó tự đối chiếu từng màn với AC. Thể hiện trạng thái đang xử lý, chưa có dữ liệu, lỗi, hết phiên. Màn làm bài thể hiện ở 2 kích thước: desktop 1440x900 và mobile 390x844. Ghi hành vi bàn phím và thứ tự focus của màn làm bài. Prototype không gọi API thật, không chứa secret. Figma là tùy chọn.

<a id="lr-11"></a>

2. **LR-11 API, dữ liệu, ADR, threat model và spec chain.**
   - OpenAPI và ERD dạng phần chênh so với [API/Schema Reference](03_API_Schema_Reference_v1.1.zip) cho Quiz: đề, câu hỏi, lần làm (`QuizAttempt`), dữ liệu trước và sau khi nộp, quyền đọc theo chủ sở hữu, kế hoạch migration. Một bảng khớp prototype, API, dữ liệu và AC cho hành trình tạo đề đến xem kết quả. Quy tắc tại [mục 16](#data-api).
   - Một ADR theo [template](../adr/ADR-000-Template.md) so sánh hai phương án (gợi ý: lưu đáp án cùng đề hay tách bảng, chấm đồng bộ hay qua job), có điều kiện xem lại.
   - Threat model 1 trang theo [template](../security/Threat_Model_Template.md): trust boundary, STRIDE cho API Quiz, luồng dữ liệu ra provider AI, prompt injection từ tài liệu.
   - `specs/quiz/plan.md` và `tasks.md`. Mỗi task vừa một PR, có AC, lệnh kiểm, stop condition. Track Verify đánh dấu task định tự làm.
   - **Review chéo:** review bất đồng bộ thiết kế của một bạn hoặc mẫu mentor cấp, ghi ít nhất 2 nhận xét có căn cứ (phần review 5% điểm khóa).
   - **Sơ đồ dạng code (Mermaid):** C4 Context và Container, 1 sequence "tạo đề qua AI Job" (web, API, worker, provider, database), 1 state machine của lần làm bài. Sơ đồ nằm trong hồ sơ thiết kế, nhất quán với API và dữ liệu.
   - **AI design review ở phiên độc lập:** mở session Claude Code mới hoặc dùng subagent `design-reviewer`, review hồ sơ thiết kế theo AC và threat model. Ghi ít nhất 2 finding, tự xác minh 1, mỗi finding có quyết định Fix, Reject hoặc Defer.
   - Glossary trong `AGENTS.md` là tùy chọn.

### 10.2. Output nộp

Link PR `milestone/m2`, đường dẫn prototype kèm commit, hồ sơ thiết kế có sơ đồ Mermaid (có thể một file), ADR, threat model, `plan.md`, `tasks.md`, bảng finding của AI design review, link bài review chéo.

### 10.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Prototype | 25 | Đủ 3 màn và trạng thái chính: 10. Màn làm bài ở 2 kích thước: 5. Bàn phím và focus màn làm bài: 10 |
| API, dữ liệu và sơ đồ | 30 | C4, sequence, state machine nhất quán với prototype, API và AC: 10. Tách dữ liệu trước và sau khi nộp, không lộ đáp án: 10. Quyền theo chủ sở hữu và migration rõ: 10 |
| ADR và threat model | 25 | ADR hai phương án có căn cứ và điều kiện xem lại: 10. Threat model có trust boundary, STRIDE, prompt injection: 15 |
| Spec chain và review | 20 | `tasks.md` đủ nhỏ, có lệnh kiểm và stop condition: 10. AI design review có finding đã xác minh và quyết định: 5. Review chéo có căn cứ: 5 |

<a id="m31"></a>

## 11. M3.1 (buổi 6): Tạo đề và API làm bài bằng TDD

**Trọng tâm SDLC:** triển khai với coding agent, TDD, kiểm soát thay đổi.

Mỗi task giao agent dùng issue template [Task giao agent](../../.github/ISSUE_TEMPLATE/agent-task.md), lấy AC đã `Human-verified` và phần thiết kế M2 liên quan. Mỗi task một PR theo [mục 4.3](#pr-theo-task).

### 11.1. Việc cần làm

<a id="lr-12"></a>

1. **LR-12 Tạo đề qua AI Job.** Migration cho đề Quiz. Policy, executor và endpoint tạo đề `quiz` trên AI Job scaffold, gọi model bằng `llm.generate_json`. Nhánh fixture chạy offline sinh đề 5 câu hợp lệ từ đoạn trích tài liệu. Kiểm schema trước khi lưu `Succeeded`. Web thêm route tạo đề theo mẫu proxy `documents`, theo dõi trạng thái bằng `useJobStatus`.

<a id="lr-13"></a>

2. **LR-13 API làm bài và TDD.** Endpoint lấy đề cho người làm bài chỉ trả câu hỏi và lựa chọn, chỉ chủ sở hữu đọc được. Ít nhất một task theo red, green, regression: commit test fail trước, commit code làm test pass sau. Thêm test đã duyệt vào `.claude/approved-tests.txt` để hook và CI bảo vệ.

Track Verify: tự làm ít nhất một task (gợi ý LR-13). Phần còn lại được dùng `checkpoint/m3.1` theo [mục 2.1](#track).

### 11.2. Output nộp

Link PR `milestone/m3.1` kèm danh sách PR task. Evidence: tạo đề fixture, gọi API làm bài bằng tài khoản A (không có đáp án) và tài khoản B (bị từ chối), lịch sử commit TDD.

### 11.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Chức năng chạy được | 30 | Tạo đề fixture qua AI Job, đề hợp lệ: 15. API làm bài không lộ đáp án, B bị từ chối: 15 |
| TDD và test đã duyệt | 25 | Lịch sử red, green, regression: 15. Test đã duyệt được hook và CI bảo vệ: 10 |
| Làm việc với agent | 30 | Brief có AC, lệnh kiểm, stop condition: 10. Review diff hoặc review PR checkpoint có finding đã xác minh: 20 |
| Evidence | 15 | Input, expected, actual, commit đúng phiên bản: 15 |

<a id="m3"></a>

## 12. M3 (buổi 7): Hoàn thiện Quiz và kiểm thử đa tầng

**Trọng tâm SDLC:** hoàn thiện chức năng, kiểm thử đa tầng (ASG01 phần 1).

### 12.1. Việc cần làm

<a id="lr-14"></a>

1. **LR-14 Nộp và chấm.** Máy chủ chấm theo BR-14, câu bỏ trống tính sai, lưu lần làm, nộp lặp cùng lần làm trả cùng kết quả. Không nhận điểm hay đáp án từ client.

<a id="lr-15"></a>

2. **LR-15 Kết quả và mở lại.** Màn kết quả có đáp án, giải thích, nguồn. Danh sách Quiz của tôi (mới nhất trước), mở lại lần đã nộp sau reload hoặc đăng nhập lại.

<a id="lr-16"></a>

3. **LR-16 Quyền và thông tin xử lý dữ liệu.** Tài khoản B bị từ chối ở mọi endpoint đề, lần làm và tác vụ của A, phản hồi không lộ nội dung. Tài liệu nguồn là kho dùng chung, không thuộc phạm vi kiểm này. Dùng lại `ProfileDisclosure` để hiển thị nhà cung cấp và dữ liệu gửi đi trước khi tạo đề.

<a id="lr-17"></a>

4. **LR-17 Màn làm bài.** Làm được hoàn toàn bằng bàn phím, focus rõ, thông báo lựa chọn chưa nộp có thể mất khi tải lại.

<a id="lr-18"></a>

5. **LR-18 Hoàn thiện AI Job.** Ghi usage của mỗi lời gọi model. Provider lỗi giả lập (`AI_FIXTURE_FAULTS`) kết thúc `Failed` đúng nguyên nhân trong thời hạn.

<a id="lr-19"></a>

6. **LR-19 Kiểm thử đa tầng.**
   - Test plan và test report theo [template](../release/Test_Plan_Template.md): phạm vi, rủi ro, entry và exit criteria có số. Report ghi Pass, Fail, NotRun có lý do.
   - Thiết kế test case bằng kỹ thuật: EP và BVA cho một quy tắc có biên (ví dụ số câu, thời hạn LIM-11), decision table cho quy tắc chấm BR-14. Ghi bảng test case trong test plan.
   - E2E bằng `@playwright/test` cho hành trình tạo đề, làm bài, nộp, xem kết quả, chạy trong CI (`npm run test:pw`). Dùng AI sinh nháp E2E từ kịch bản Gherkin của M2.1, tự review oracle và assertion trước khi commit, ghi trong PR ít nhất một chỗ đã sửa.
   - Golden set hỏi đáp trên Chat của Starter: suite `example-chat` có sẵn 2 case, bạn thêm 2 case để đủ 4 câu hỏi có ý kỳ vọng đặt trước, chạy k = 2 bằng eval harness (`make eval SUITE=... K=2`, fixture được chấp nhận ở mốc này).
   - Mutation test trên hàm chấm điểm: cài `mutmut` vào môi trường Python của API (Windows chạy trong WSL2), giới hạn đúng file. Phân tích ít nhất một mutant sống, bổ sung test, chạy lại.
   - Tự động hóa một việc lặp bằng hook hoặc skill là tùy chọn.

Track Verify được dùng `checkpoint/m3` cho LR-14 đến LR-18 theo [mục 2.1](#track). LR-19 là bài của bạn.

### 12.2. Output nộp

Link PR `milestone/m3`, test plan có bảng test case theo kỹ thuật, test report, link lần chạy CI có E2E, kết quả golden set, kết quả mutation trước và sau.

### 12.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Chức năng Quiz | 30 | Chấm đúng BR-14, nộp lặp đúng: 15. Mở lại sau reload, B không truy cập được: 15 |
| Test plan và report | 20 | Exit criteria có số, test case theo EP, BVA, decision table: 10. Report có NotRun và lý do: 10 |
| E2E và golden set | 30 | E2E sinh từ Gherkin, đã review, chạy trong CI: 15. Golden set 4 case, k = 2, có phân tích lượt lỗi: 15 |
| Mutation | 20 | Có mutation score: 10. Phân tích mutant sống và bổ sung test: 10 |

<a id="m4"></a>

## 13. M4 (buổi 8): Release gate và phát hành R1

**Trọng tâm SDLC:** release gate, phát hành, vận hành local.

### 13.1. Việc cần làm

<a id="lr-20"></a>

1. **LR-20 Kết luận AC.** Verdict cho 14 AC Core đến hạn M4, chạy `python3 scripts/trace_check.py --gate M4`.

<a id="lr-21"></a>

2. **LR-21 Hồi quy trên bản ứng viên.** Chạy lại E2E và test trên commit sẽ gắn tag, ghi kết quả.

<a id="lr-22"></a>

3. **LR-22 Kiểm quyền và lỗi provider qua API.** Tái chạy kiểm tài khoản B bị từ chối và ca provider lỗi trên bản ứng viên.

<a id="lr-23"></a>

4. **LR-23 Eval nội dung Quiz.** Viết `QuizAdapter` trong `evaluation/harness/adapters.py` (gọi API tạo đề, chờ tác vụ kết thúc, trả đề theo shape của grader) và suite 3 case với `question_count` 5. Chạy 6 lượt bằng AI thật đã chọn ở LR-09 (3 tài liệu, k = 2): kiểm cấu trúc bằng grader `quiz_structure`, tự kiểm đúng một đáp án và giải thích có trong nguồn. Ghi lượt lỗi và lý do. Thêm 1 case tài liệu chứa prompt injection. Chuyển bước `eval-fixture` của CI thành bắt buộc.

<a id="lr-24"></a>

5. **LR-24 Bảo mật và chuỗi cung ứng.** Chạy `/security-review` và xử lý finding. Sinh SBOM và AI-BOM trong CI (`make sbom`, `make ai-bom`). Cập nhật threat model.

<a id="lr-25"></a>

6. **LR-25 Go/no-go và phát hành R1.** Checklist theo [template](../release/Release_Checklist_Template.md), kết luận theo exit criteria của test plan. Trước khi kết luận, chạy **3 kịch bản UAT** cho hành trình Quiz của R1 (tạo đề, làm và nộp bài, xem lại và quyền A/B), ghi Pass hoặc Fail theo mã UAT ở [Phụ lục A](#pham-vi-truy-vet). Tag `r1.0`, gói bằng `git archive` của tag kèm SHA-256, release note có nhãn phần AI sinh.

<a id="lr-26"></a>

7. **LR-26 Khôi phục và vận hành.** Sao lưu và khôi phục vào database riêng bằng `make backup-restore-check` với `BACKUP_EXTRA_TABLES=auth_user,ai_jobs,<bảng Quiz của bạn>` để đối chiếu cả dữ liệu tài khoản, tác vụ và Quiz. Trên database khôi phục, kiểm bằng SQL mỗi đề và lần làm vẫn đúng chủ sở hữu A, không có dòng nào gán cho B. Theo [Operations Template](../release/Operations_Template.md):
   - **3 SLI và 1 SLO**, mỗi SLI có truy vấn hoặc nguồn số đo: tỷ lệ tác vụ `quiz` kết thúc `Succeeded` (bảng `ai_jobs`), thời gian xử lý p95 của tác vụ `quiz` (bảng `ai_jobs`), tỷ lệ phản hồi 5xx (`insighthub_http_requests_total` tại `/metrics`). SLO ví dụ: 95% tác vụ `quiz` `Succeeded` trong 120 giây. Thêm counter riêng vào `/metrics` là tùy chọn.
   - **Diễn tập incident dạng tabletop:** bật `AI_FIXTURE_FAULTS` cho tác vụ `quiz`, quan sát SLI vượt ngưỡng, chẩn đoán và khôi phục. Viết postmortem blameless 1 trang. AI được đề xuất giả thuyết, kết luận nguyên nhân do bạn đưa ra sau khi tái hiện.
   - **Chặn lệnh phá dữ liệu 2 lớp:** thêm rule `deny` vào `.claude/settings.json` và hook PreToolUse chặn cùng mẫu lệnh (ví dụ `docker compose down -v`, `DROP TABLE`), dùng lại `.claude/hooks/_common.py`. Tự thử một lệnh bị chặn, ghi kết quả.

### 13.2. Output nộp

Link PR `milestone/m4`, kết quả `trace_check --gate M4`, kết quả eval, kết quả 3 kịch bản UAT, checklist go/no-go, tag `r1.0` và checksum, evidence restore, Operations Template có SLI, SLO, diễn tập incident và postmortem, evidence lệnh bị chặn.

### 13.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Verdict AC và eval | 30 | Gate M4 pass, verdict có evidence: 15. 6 lượt eval và case injection có phân tích: 15 |
| Bảo mật | 20 | `/security-review` có xử lý: 5. SBOM, AI-BOM trong CI, threat model cập nhật: 10. Chặn lệnh phá dữ liệu 2 lớp đã thử: 5 |
| Go/no-go và R1 | 25 | Quyết định theo exit criteria và kết quả UAT, hồi quy trên bản ứng viên: 10. Tag, gói, checksum, release note: 15 |
| Restore và vận hành | 25 | Restore có đối chiếu bảng và chủ sở hữu A/B: 15. 3 SLI, 1 SLO đo được có truy vấn: 5. Diễn tập incident và postmortem: 5 |

<a id="m5"></a>

## 14. M5 (buổi 9): Change request R1.1 và refactor legacy

**Trọng tâm SDLC:** bảo trì và tiến hóa (ASG01 phần 2).

### 14.1. Việc cần làm

<a id="lr-27"></a>

**LR-27** gồm ba phần.

1. **CR-01: Làm lại Quiz.** Người dùng làm lại một đề đã nộp, mỗi lần làm có số thứ tự, điểm các lần trước giữ nguyên (nhánh làm lại của IH-QUIZ-002-AC02 và IH-DATA-002-AC03).
   - Impact analysis: AC, API, dữ liệu, UI, test bị ảnh hưởng. Cập nhật trace.
   - Tái hiện hành vi hiện tại bằng test trước khi sửa.
   - Migration theo expand và contract: thêm cột số thứ tự lần làm, backfill cho lần làm đã có, sau đó thêm ràng buộc. Sao lưu trước khi nâng cấp. Rollback giữ nguyên dữ liệu.
   - Regression, số đo usage trước và sau. Tag `r1.1`.
2. **Xử lý một lỗ hổng.** Chọn một finding từ dependency scan (`pip-audit`, `npm audit` theo [hướng dẫn M1](../M1_Lint_Scan_Guide.md)) hoặc `/security-review` của LR-24. Xử lý qua 5 bước: triage mức độ, kiểm khả năng bị khai thác trong InsightHub, sửa hoặc giảm thiểu, chạy regression, ghi vào release note R1.1. Nếu scan không còn finding, dùng finding mẫu mentor cấp trên kênh lớp.
3. **Refactor legacy** module `api/app/services/ingestion.py::extract_source` theo [Module legacy](../Legacy_Modules.md): module map, characterization test commit trước lần sửa đầu, agent refactor trong worktree, ít nhất hai bước có commit riêng, review PR do agent tạo theo [checklist](../ai/templates/Review_Checklist_Migration_CI.md), complexity trước và sau. Module `config.py` là tùy chọn.

### 14.2. Output nộp

Link PR `milestone/m5`, hồ sơ CR-01, migration và evidence rollback, tag `r1.1`, hồ sơ xử lý lỗ hổng, hồ sơ refactor legacy.

### 14.3. Rubric (100)

| Tiêu chí | Điểm | Cách chấm |
| --- | --- | --- |
| Hồ sơ CR và lỗ hổng | 20 | Impact analysis đủ và trace cập nhật: 15. Lỗ hổng xử lý đủ 5 bước, có regression: 5 |
| Migration và R1.1 | 35 | Expand và contract có backfill: 15. Rollback bảo toàn dữ liệu đã thử: 10. Regression và tag `r1.1`: 10 |
| Refactor legacy | 45 | Characterization test trước sửa: 15. Agent trong worktree, bước nhỏ có commit, PR được review: 15. Complexity trước và sau, CI pass: 15 |

<a id="asg01"></a>

### 14.4. Rubric ASG01 Legacy và kiểm thử đa tầng

**100 điểm, chiếm 25% điểm khóa.** Phần kiểm thử làm sau buổi 7 (LR-19), phần legacy làm sau buổi 9 (LR-27). Bản cuối nộp cùng Capstone. Mỗi dòng chấm 0% (chưa có minh chứng), 40% (một phần), 70% (đạt cốt lõi), 100% (đạt cả cốt lõi và đầy đủ).

| Phần | Tiêu chí | Điểm | Đạt cốt lõi (70%) | Đầy đủ (100%) |
| --- | --- | --- | --- | --- |
| Kiểm thử | Test plan và test report | 15 | Exit criteria có số, test case theo kỹ thuật thiết kế. Report có Pass, Fail, NotRun và lý do | Kết luận theo exit criteria, defect có bước tái hiện |
| Kiểm thử | Test nhiều tầng | 20 | E2E hành trình Quiz trong CI. Golden set Chat 4 case, k = 2 | E2E kiểm cả trạng thái dữ liệu. Lượt lỗi được giữ và giải thích |
| Kiểm thử | Chứng minh test bắt lỗi | 15 | Mutation trên hàm chấm điểm, có mutation score | Phân tích mutant sống, bổ sung test, chạy lại |
| Legacy | Bảo toàn hành vi | 20 | Module map `extract_source`, characterization test trước sửa | Edge case trước và sau, giải thích hành vi nghi lỗi |
| Legacy | Refactor qua agent có kiểm soát | 15 | Brief có stop condition, worktree, hai bước có commit, PR được review | Rollback một bước đã thử, tỷ lệ phải sửa ghi trong Delivery Log |
| Legacy | Cải thiện có số đo | 15 | Complexity trước và sau, CI pass | Giải thích đánh đổi, phản biện được đề xuất AI không phù hợp |

Phần kiểm thử chấm trên Quiz và Chat của Starter. Phần legacy chấm trên `extract_source`. Một evidence không dùng cho cả hai phần.

<a id="capstone"></a>

## 15. Capstone (buổi 10): Nghiệm thu, giải thích quyết định, lộ trình áp dụng

### 15.1. Việc cần làm

<a id="lr-28"></a>

1. **LR-28 Hồ sơ Capstone.** `docs/capstone/README.md` là mục lục evidence (dẫn link, không viết lại):
   - Bảng một trang: 6 pha, artifact, gate, phần AI làm, metric.
   - Truy một nhu cầu của Quiz xuyên vòng đời: AC, prototype, API, dữ liệu, code, test, `r1.0` và thay đổi ở `r1.1`.
   - Hướng dẫn chạy lại bản phát hành và evidence hành trình chính.
   - Ít nhất hai thay đổi quan trọng do AI sinh: đề xuất, phép kiểm, quyết định giữ, sửa hoặc bác bỏ.
   - Báo cáo metric so với baseline M1 từ `make delivery-report`. Ghi rõ đây là số đo proxy theo PR của dự án cá nhân, không phải DORA metrics của production.
   - Kết luận nghiệm thu theo 18 AC Core và các AC Extended đã làm.

<a id="lr-29"></a>

2. **LR-29 Lộ trình áp dụng AI 30/60/90 ngày.** Chọn một quy trình công việc thực tế của đội. Ghi owner, baseline hiện trạng, mục tiêu và các mốc 30, 60, 90 ngày (AI làm gì, ở mức nào, ai duyệt, evidence gì). KPI dùng DORA metrics (change lead time, deployment frequency, change fail rate, failed deployment recovery time, deployment rework rate) cùng review load và cost per accepted change, không dùng số dòng code hay số prompt làm KPI chính. Nêu cách thu dữ liệu, điều kiện tiếp tục hoặc dừng, rủi ro và mục **Công cụ và dữ liệu được phép** theo phê duyệt của Samsung SDS.

### 15.2. Output nộp

**Bản nháp** trước buổi 10 ít nhất 2 giờ (là bản chuẩn bị buổi 10). **Bản cuối** trong 3 ngày sau buổi 10, nộp cùng bản cuối ASG01. Mentor chọn 4 đến 5 học viên theo kết quả M4, M5 đã chấm, ưu tiên có cả Track Build và Track Verify, báo trước buổi 10 ít nhất 48 giờ. Học viên được chọn trình bày 8 phút và Q&A trên lớp: một nhu cầu xuyên vòng đời, R1 và R1.1, một đề xuất AI đã bác bỏ, metric so với baseline.

### 15.3. Rubric Capstone (100, chiếm 35% điểm khóa)

Mỗi dòng chấm 0%, 40%, 70% hoặc 100% như mục 14.4.

| Nhóm | Điểm | Đạt cốt lõi (70%) | Đầy đủ (100%) |
| --- | --- | --- | --- |
| Requirements và Planning | 15 | Backlog, trace 18 AC, spec Quiz truy được nguồn. CR-01 đúng quy trình | Truy hai chiều yêu cầu và test. Kế hoạch cập nhật theo số đo thực tế |
| Architecture và Design | 15 | Prototype, API, ERD, ADR, threat model nhất quán | Triển khai khớp thiết kế hoặc giải thích khác biệt |
| Implementation với coding agent | 20 | Quiz chạy đủ hành trình. Có task tự giao agent với TDD và PR có CI. Review diff của agent hoặc PR checkpoint có quyết định | Người khác chạy lại được. Dữ liệu còn sau khởi động lại, nộp lặp đúng |
| Verification và Validation | 15 | Test plan có kỹ thuật thiết kế, report, E2E, mutation, 6 lượt eval, UAT, security review có verdict | Phân tích lượt lỗi và test không ổn định. Không dùng AI tự chấm làm căn cứ duy nhất |
| Release, Operations, Maintenance | 15 | `r1.0`, `r1.1` có tag, gói, release note. Restore và migration có kiểm quyền. SLI, SLO, postmortem. Legacy refactor giữ hành vi | Rollback bảo toàn dữ liệu đã thử. Người khác tái cài được |
| Giải thích quyết định và hiệu quả AI | 20 | Giải thích quyết định qua các pha và hai thay đổi do AI sinh. Metric so với baseline. Lộ trình 30/60/90 có owner, KPI, điều kiện dừng | Đề xuất AI đã bác bỏ có căn cứ. Nêu giới hạn của proxy |

Lỗi lộ đáp án trước khi nộp hoặc lộ dữ liệu chéo tài khoản chưa sửa khiến nhóm Verification và Validation nhận 0.

<a id="data-api"></a>

## 16. Thiết kế và tích hợp với Starter

<a id="tich-hop-starter"></a>

### 16.1. Quy tắc tích hợp

| Quy tắc | Cách làm |
| --- | --- |
| Thiết kế dạng phần chênh | OpenAPI và ERD chỉ ghi bảng, endpoint, trường mới hoặc khác so với [API/Schema Reference](03_API_Schema_Reference_v1.1.zip) và Starter, kèm lý do. Sao chép Reference không kèm giải thích không được tính |
| Quyền do server quyết định | Người dùng lấy từ session (Auth scaffold). Không dùng `owner_id` do client gửi để cấp quyền |
| Dữ liệu trước và sau khi nộp | Tách schema công khai (câu hỏi, lựa chọn) và nội bộ (đáp án, giải thích). Đáp án chỉ trả sau khi nộp |
| Migration | Mọi thay đổi schema là forward migration. Không yêu cầu xóa volume để nâng cấp |
| AI Job | Mở rộng bảng `ai_jobs` của scaffold, không đăng ký policy cho phép tất cả, không nới quota, deadline hay publish fence để test pass ([ADR-004](../adr/ADR-004-AI-Job-Framework.md)) |
| Module legacy | Không sửa [module legacy chỉ định](../Legacy_Modules.md) trước M5. Cần sửa phần nền khác thì viết regression test trước diff |
| Kiến trúc Starter | Đối chiếu [Architecture](../Architecture_Starter_v1.md) và [API Contract](../API_Contract_Starter_v1.md) trước khi thiết kế |

<a id="auth-email"></a>

### 16.2. Auth, email và Google (Extended)

Quiz dùng nguyên Auth scaffold với tài khoản seed. Đăng ký, xác minh email, khôi phục mật khẩu, đăng nhập Google là Extended. Khi làm, theo [Auth Integration Guide](../Auth_Integration_Guide.md) và kiểm thư trên Mailpit của Starter. Không nới cấu hình cookie của Auth scaffold.

<a id="evidence"></a>

## 17. Truy vết và evidence

<a id="bang-ket-qua"></a>

### 17.1. Cách ghi traceability matrix

`trace/ac-trace.csv` là traceability matrix duy nhất của dự án. Cột bên trái do mentor cấp, không sửa. Bạn điền cột bên phải dần từ M2.1 đến M5. Ý nghĩa từng cột tại [trace/README](../../trace/README.md).

- Expected phải `Human-verified` trước khi giao agent triển khai AC đó. Bản nháp AI ghi `draft_by=AI` và chưa được có verdict khi chưa kiểm.
- `Passed` cần commit SHA, kết quả thực tế, evidence. AC R1 `Passed` cần thêm `test_ids`. `Blocked` ghi nguyên nhân trong `notes`. `Extended-NotDone` chỉ dùng cho Extended.
- Chỉ kết luận AC đạt khi mọi nhánh trong phiên bản đều đạt.
- Chạy `python3 scripts/trace_check.py` trước khi nộp. Từ M4 chạy thêm `--gate M4`, M5 chạy `--gate M5`.

### 17.2. Ghi evidence

| Loại công việc | Cần ghi |
| --- | --- |
| Phân tích với AI | Ngữ cảnh đưa vào, đề xuất của AI, phần đã giữ, sửa, bác bỏ và căn cứ |
| Agent làm task | Task brief, plan đã duyệt, diff đã review, finding và quyết định, kết quả CI |
| TDD | Commit test fail, commit code pass, test đã duyệt |
| Đánh giá nội dung AI | Provider, model, prompt version, input, kết quả từng lượt, lượt lỗi và lý do |
| Phát hành và thay đổi | Tag, checksum, release note, backup, restore, migration, rollback, regression |

Một evidence ghi một lần và được dẫn link ở nơi khác, không chép lại nhiều bảng.

<a id="pham-vi-truy-vet"></a>

### 17.3. Phụ lục A: danh mục AC theo tầng

Toàn bộ 165 AC của SRS v1.1. **Core** là 18 AC của bài tập (mục 1.2). **Extended** làm thêm khi Core đã đạt. **Ngoài phạm vi** không áp dụng cho bài tập. Cột Phạm vi giữ mã của SRS: A là áp dụng đầy đủ, D1 đến D9 là áp dụng có điều chỉnh, N là ngoài phạm vi. Cột Công việc và Mốc của AC Extended ghi "Mở rộng". `trace/ac-trace.csv` sinh từ bảng này.

| Mã yêu cầu | AC | Phạm vi | Tầng | Công việc | Mốc hoàn thiện, kiểm tổng hợp | Nghiệm thu liên quan |
| --- | --- | --- | --- | --- | --- | --- |
| IH-AUTH-001 | IH-AUTH-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-01 |
| IH-AUTH-001 | IH-AUTH-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-01 |
| IH-AUTH-002 | IH-AUTH-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-03 |
| IH-AUTH-002 | IH-AUTH-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-03 |
| IH-AUTH-003 | IH-AUTH-003-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-01 |
| IH-AUTH-003 | IH-AUTH-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-01 |
| IH-AUTH-004 | IH-AUTH-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-02 |
| IH-AUTH-004 | IH-AUTH-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-02 |
| IH-AUTH-005 | IH-AUTH-005-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-02, UAT-03 |
| IH-AUTH-005 | IH-AUTH-005-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-02, UAT-03 |
| IH-AUTH-005 | IH-AUTH-005-AC03 | A | Extended | Mở rộng | Mở rộng | UAT-02, UAT-03 |
| IH-AUTH-005 | IH-AUTH-005-AC04 | A | Extended | Mở rộng | Mở rộng | UAT-02, UAT-03 |
| IH-AUTH-006 | IH-AUTH-006-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-03 |
| IH-AUTH-006 | IH-AUTH-006-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-03 |
| IH-AUTH-007 | IH-AUTH-007-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-03 |
| IH-AUTH-007 | IH-AUTH-007-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-03 |
| IH-AUTH-007 | IH-AUTH-007-AC03 | A | Extended | Mở rộng | Mở rộng | UAT-03 |
| IH-AUTH-008 | IH-AUTH-008-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-04 |
| IH-AUTH-008 | IH-AUTH-008-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-04 |
| IH-AUTH-009 | IH-AUTH-009-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-04 |
| IH-AUTH-009 | IH-AUTH-009-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-04 |
| IH-AUTH-010 | IH-AUTH-010-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-03 |
| IH-AUTH-010 | IH-AUTH-010-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-03 |
| IH-NB-001 | IH-NB-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-05 |
| IH-NB-001 | IH-NB-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-05 |
| IH-NB-002 | IH-NB-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-05 |
| IH-NB-002 | IH-NB-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-05 |
| IH-NB-003 | IH-NB-003-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-12 |
| IH-NB-003 | IH-NB-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-12 |
| IH-NB-004 | IH-NB-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-13 |
| IH-NB-004 | IH-NB-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-13 |
| IH-DOC-001 | IH-DOC-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-06 |
| IH-DOC-001 | IH-DOC-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-06 |
| IH-DOC-002 | IH-DOC-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-06 |
| IH-DOC-002 | IH-DOC-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-06 |
| IH-DOC-003 | IH-DOC-003-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-07 |
| IH-DOC-003 | IH-DOC-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-07 |
| IH-DOC-004 | IH-DOC-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-07 |
| IH-DOC-004 | IH-DOC-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-07 |
| IH-DOC-005 | IH-DOC-005-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-06, UAT-08, UAT-12 |
| IH-DOC-005 | IH-DOC-005-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-06, UAT-08, UAT-12 |
| IH-DOC-006 | IH-DOC-006-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-12 |
| IH-DOC-006 | IH-DOC-006-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-12 |
| IH-CHAT-001 | IH-CHAT-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-08 |
| IH-CHAT-001 | IH-CHAT-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-08 |
| IH-CHAT-002 | IH-CHAT-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-08 |
| IH-CHAT-002 | IH-CHAT-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-08 |
| IH-CHAT-003 | IH-CHAT-003-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-09 |
| IH-CHAT-003 | IH-CHAT-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-09 |
| IH-CHAT-004 | IH-CHAT-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-08, UAT-12 |
| IH-CHAT-004 | IH-CHAT-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-08, UAT-12 |
| IH-CHAT-004 | IH-CHAT-004-AC03 | A | Extended | Mở rộng | Mở rộng | UAT-08, UAT-12 |
| IH-CHAT-004 | IH-CHAT-004-AC04 | A | Extended | Mở rộng | Mở rộng | UAT-08, UAT-12 |
| IH-CHAT-004 | IH-CHAT-004-AC05 | A | Extended | Mở rộng | Mở rộng | UAT-08, UAT-12 |
| IH-CHAT-005 | IH-CHAT-005-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-09, UAT-12 |
| IH-CHAT-005 | IH-CHAT-005-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-09, UAT-12 |
| IH-NOTE-001 | IH-NOTE-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-10 |
| IH-NOTE-001 | IH-NOTE-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-10 |
| IH-NOTE-001 | IH-NOTE-001-AC03 | A | Extended | Mở rộng | Mở rộng | UAT-10 |
| IH-NOTE-001 | IH-NOTE-001-AC04 | A | Extended | Mở rộng | Mở rộng | UAT-10 |
| IH-NOTE-002 | IH-NOTE-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-10, UAT-12 |
| IH-NOTE-002 | IH-NOTE-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-10, UAT-12 |
| IH-AI-001 | IH-AI-001-AC01 | D1 | Extended | Mở rộng | Mở rộng | UAT-11 |
| IH-AI-001 | IH-AI-001-AC02 | D1 | Extended | Mở rộng | Mở rộng | UAT-11 |
| IH-AI-002 | IH-AI-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-11 |
| IH-AI-002 | IH-AI-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-11 |
| IH-AI-003 | IH-AI-003-AC01 | D1 | Core | LR-12 | M3.1 → M4 | UAT-11, UAT-14 |
| IH-AI-003 | IH-AI-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-11, UAT-14 |
| IH-AI-004 | IH-AI-004-AC01 | D1 | Extended | Mở rộng | Mở rộng | UAT-11, UAT-12 |
| IH-AI-004 | IH-AI-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-11, UAT-12 |
| IH-AI-005 | IH-AI-005-AC01 | A | Core | LR-18, LR-22 | M3 → M4 | UAT-14 |
| IH-AI-005 | IH-AI-005-AC02 | A | Core | LR-18 | M3 → M4 | UAT-14 |
| IH-MM-001 | IH-MM-001-AC01 | N | Ngoài phạm vi | - | Mở rộng | UAT-11 |
| IH-MM-001 | IH-MM-001-AC02 | N | Ngoài phạm vi | - | Mở rộng | UAT-11 |
| IH-MM-002 | IH-MM-002-AC01 | N | Ngoài phạm vi | - | Mở rộng | UAT-11, UAT-15 |
| IH-MM-002 | IH-MM-002-AC02 | N | Ngoài phạm vi | - | Mở rộng | UAT-11, UAT-15 |
| IH-SUM-001 | IH-SUM-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-11 |
| IH-SUM-001 | IH-SUM-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-11 |
| IH-SUM-002 | IH-SUM-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-10, UAT-11 |
| IH-SUM-002 | IH-SUM-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-10, UAT-11 |
| IH-SLD-001 | IH-SLD-001-AC01 | N | Ngoài phạm vi | - | Mở rộng | UAT-11 |
| IH-SLD-001 | IH-SLD-001-AC02 | N | Ngoài phạm vi | - | Mở rộng | UAT-11 |
| IH-SLD-002 | IH-SLD-002-AC01 | N | Ngoài phạm vi | - | Mở rộng | UAT-11, UAT-15 |
| IH-SLD-002 | IH-SLD-002-AC02 | N | Ngoài phạm vi | - | Mở rộng | UAT-11, UAT-15 |
| IH-QUIZ-001 | IH-QUIZ-001-AC01 | A | Core | LR-12 | M3.1 → M4 | UAT-11 |
| IH-QUIZ-001 | IH-QUIZ-001-AC02 | A | Core | LR-12 | M3.1 → M4 | UAT-11 |
| IH-QUIZ-002 | IH-QUIZ-002-AC01 | A | Core | LR-13, LR-14 | M3 → M4 | UAT-11 |
| IH-QUIZ-002 | IH-QUIZ-002-AC02 | A | Core | LR-15, LR-27 | M3 → M5 | UAT-11 |
| IH-RPT-001 | IH-RPT-001-AC01 | N | Ngoài phạm vi | - | Mở rộng | UAT-11 |
| IH-RPT-001 | IH-RPT-001-AC02 | N | Ngoài phạm vi | - | Mở rộng | UAT-11 |
| IH-RPT-002 | IH-RPT-002-AC01 | N | Ngoài phạm vi | - | Mở rộng | UAT-11, UAT-13 |
| IH-RPT-002 | IH-RPT-002-AC02 | N | Ngoài phạm vi | - | Mở rộng | UAT-11, UAT-13 |
| IH-OUT-001 | IH-OUT-001-AC01 | D1 | Extended | Mở rộng | Mở rộng | UAT-11, UAT-13 |
| IH-OUT-001 | IH-OUT-001-AC02 | A | Core | LR-15 | M3 → M4 | UAT-11, UAT-13 |
| IH-OUT-002 | IH-OUT-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-11, UAT-12 |
| IH-OUT-002 | IH-OUT-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-11, UAT-12 |
| IH-OUT-003 | IH-OUT-003-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-12 |
| IH-OUT-003 | IH-OUT-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-12 |
| IH-DATA-001 | IH-DATA-001-AC01 | D1 | Extended | Mở rộng | Mở rộng | UAT-05, UAT-06, UAT-08, UAT-10, UAT-11, UAT-20 |
| IH-DATA-001 | IH-DATA-001-AC02 | D1 | Extended | Mở rộng | Mở rộng | UAT-05, UAT-06, UAT-08, UAT-10, UAT-11, UAT-20 |
| IH-DATA-001 | IH-DATA-001-AC03 | D1 | Extended | Mở rộng | Mở rộng | UAT-05, UAT-06, UAT-08, UAT-10, UAT-11, UAT-20 |
| IH-DATA-001 | IH-DATA-001-AC04 | A | Extended | Mở rộng | Mở rộng | UAT-05, UAT-06, UAT-08, UAT-10, UAT-11, UAT-20 |
| IH-DATA-001 | IH-DATA-001-AC05 | A | Extended | Mở rộng | Mở rộng | UAT-05, UAT-06, UAT-08, UAT-10, UAT-11, UAT-20 |
| IH-DATA-001 | IH-DATA-001-AC06 | A | Extended | Mở rộng | Mở rộng | UAT-05, UAT-06, UAT-08, UAT-10, UAT-11, UAT-20 |
| IH-DATA-002 | IH-DATA-002-AC01 | A | Core | LR-13 | M3.1 → M4 | UAT-10, UAT-11, UAT-12, UAT-20 |
| IH-DATA-002 | IH-DATA-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-10, UAT-11, UAT-12, UAT-20 |
| IH-DATA-002 | IH-DATA-002-AC03 | A | Core | LR-14, LR-27 | M3 → M5 | UAT-10, UAT-11, UAT-12, UAT-20 |
| IH-DATA-002 | IH-DATA-002-AC04 | D9 | Extended | Mở rộng | Mở rộng | UAT-10, UAT-11, UAT-12, UAT-20 |
| IH-UX-001 | IH-UX-001-AC01 | D2 | Extended | Mở rộng | Mở rộng | UAT-15 |
| IH-UX-001 | IH-UX-001-AC02 | D2 | Extended | Mở rộng | Mở rộng | UAT-15 |
| IH-UX-002 | IH-UX-002-AC01 | D2 | Extended | Mở rộng | Mở rộng | UAT-15 |
| IH-UX-002 | IH-UX-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-15 |
| IH-UX-003 | IH-UX-003-AC01 | D6 | Core | LR-10, LR-17 | M3 → M4 | UAT-15 |
| IH-UX-003 | IH-UX-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-15 |
| IH-UX-004 | IH-UX-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-14, UAT-15 |
| IH-UX-004 | IH-UX-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-14, UAT-15 |
| IH-MSG-001 | IH-MSG-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-18 |
| IH-MSG-001 | IH-MSG-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-18 |
| IH-MSG-002 | IH-MSG-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-15, UAT-18 |
| IH-MSG-002 | IH-MSG-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-15, UAT-18 |
| IH-MSG-003 | IH-MSG-003-AC01 | D5 | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-19 |
| IH-MSG-003 | IH-MSG-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-19 |
| IH-MSG-003 | IH-MSG-003-AC03 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-19 |
| IH-MSG-004 | IH-MSG-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-14, UAT-18 |
| IH-MSG-004 | IH-MSG-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-14, UAT-18 |
| IH-INT-001 | IH-INT-001-AC01 | D1 | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-INT-001 | IH-INT-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-INT-002 | IH-INT-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-06, UAT-11, UAT-15, UAT-16 |
| IH-INT-002 | IH-INT-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-06, UAT-11, UAT-15, UAT-16 |
| IH-INT-002 | IH-INT-002-AC03 | A | Core | LR-16 | M3 → M4 | UAT-06, UAT-11, UAT-15, UAT-16 |
| IH-INT-003 | IH-INT-003-AC01 | D3 | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-11, UAT-16 |
| IH-INT-003 | IH-INT-003-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-11, UAT-16 |
| IH-INT-004 | IH-INT-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-12, UAT-16, UAT-17, UAT-20 |
| IH-INT-004 | IH-INT-004-AC02 | D8 | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-12, UAT-16, UAT-17, UAT-20 |
| IH-NFR-001 | IH-NFR-001-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-04 |
| IH-NFR-001 | IH-NFR-001-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-04 |
| IH-NFR-001 | IH-NFR-001-AC03 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-04 |
| IH-NFR-001 | IH-NFR-001-AC04 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-04 |
| IH-NFR-001 | IH-NFR-001-AC05 | A | Extended | Mở rộng | Mở rộng | UAT-01, UAT-02, UAT-03, UAT-04 |
| IH-NFR-002 | IH-NFR-002-AC01 | A | Core | LR-16, LR-22 | M3 → M4 | UAT-12, UAT-13 |
| IH-NFR-002 | IH-NFR-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-12, UAT-13 |
| IH-NFR-003 | IH-NFR-003-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-13, UAT-14 |
| IH-NFR-003 | IH-NFR-003-AC02 | A | Core | LR-23, LR-24 | M4 | UAT-13, UAT-14 |
| IH-NFR-004 | IH-NFR-004-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-12, UAT-16 |
| IH-NFR-004 | IH-NFR-004-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-12, UAT-16 |
| IH-NFR-005 | IH-NFR-005-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-14, UAT-16 |
| IH-NFR-005 | IH-NFR-005-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-07, UAT-09, UAT-14, UAT-16 |
| IH-NFR-006 | IH-NFR-006-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-17 |
| IH-NFR-006 | IH-NFR-006-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-17 |
| IH-NFR-007 | IH-NFR-007-AC01 | D3 | Extended | Mở rộng | Mở rộng | UAT-17 |
| IH-NFR-007 | IH-NFR-007-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-17 |
| IH-NFR-008 | IH-NFR-008-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-NFR-008 | IH-NFR-008-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-NFR-009 | IH-NFR-009-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-NFR-009 | IH-NFR-009-AC02 | A | Core | LR-26 | M4 | UAT-16 |
| IH-NFR-010 | IH-NFR-010-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-NFR-010 | IH-NFR-010-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-NFR-011 | IH-NFR-011-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-04, UAT-13, UAT-21 |
| IH-NFR-011 | IH-NFR-011-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-04, UAT-13, UAT-21 |
| IH-REL-001 | IH-REL-001-AC01 | D4 | Extended | Mở rộng | Mở rộng | UAT-01, UAT-21 |
| IH-REL-001 | IH-REL-001-AC02 | A | Core | LR-25 | M4 | UAT-01, UAT-21 |
| IH-REL-002 | IH-REL-002-AC01 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-REL-002 | IH-REL-002-AC02 | A | Extended | Mở rộng | Mở rộng | UAT-16 |
| IH-REL-003 | IH-REL-003-AC01 | A | Core | LR-27 | M5 | UAT-16 |
| IH-REL-003 | IH-REL-003-AC02 | A | Core | LR-27 | M5 | UAT-16 |

<a id="glossary"></a>

## 18. Glossary

| Thuật ngữ | Nghĩa trong dự án |
| --- | --- |
| AC (acceptance criteria) | Tiêu chí chấp nhận trong SRS, mã dạng `IH-QUIZ-002-AC01`. Một AC chỉ đạt khi mọi nhánh áp dụng đều đạt. Thuật ngữ sản phẩm tra trong SRS |
| Core, Extended | Core là 18 AC được chấm. Extended là phần làm thêm, không trừ điểm khi chưa làm |
| R1, R2, R3 | Mức rủi ro của AC, quyết định mức evidence (mục 4.5) |
| Feature Slice | Một chức năng hoàn chỉnh đi qua đủ các pha SDLC, từ yêu cầu đến phát hành và thay đổi |
| Fixture | Chế độ chạy offline với kết quả AI giả lập, kiểm hành vi phần mềm, không đo chất lượng nội dung |
| AI Job | Cơ chế tác vụ AI của Starter: nhận yêu cầu, quota, idempotency, deadline, công bố kết quả |
| Policy, executor | Policy quyết định tác vụ được nhận hay không. Executor thực hiện tác vụ (gọi model, kiểm schema, lưu kết quả) |
| `Human-verified` | Expected của AC đã được người kiểm đối chiếu với nguồn |
| Test scenario, test case | Scenario mô tả tình huống cần kiểm ở mức nghiệp vụ. Test case có dữ liệu, bước, expected cụ thể để chạy được |
| Schema, migration | Schema là cấu trúc dữ liệu. Migration là thay đổi schema có kiểm soát, chạy theo thứ tự, có cách rollback |
| Expand và contract | Cách migration không phá dữ liệu: thêm cấu trúc mới, chuyển dữ liệu, sau đó mới siết ràng buộc hoặc bỏ cấu trúc cũ |
| Golden set | Bộ câu hỏi có ý kỳ vọng đặt trước để đánh giá câu trả lời AI. k = 2 nghĩa là mỗi case chạy 2 lần |
| Mutation test | Cố ý tạo lỗi nhỏ trong code (mutant) để kiểm bộ test có bắt được không |
| Characterization test | Test ghi lại hành vi hiện tại của code cũ trước khi refactor |
| Checkpoint branch | Nhánh tham chiếu do mentor phát hành để học viên tiếp tục khi bị chặn (mục 2.1) |
| Stop condition enforced | Điều kiện dừng agent được công cụ chặn thật (`deny`, hook, CI), không chỉ là lời dặn trong prompt |
| Go/no-go | Quyết định phát hành hay không dựa trên exit criteria đã đặt trước |
