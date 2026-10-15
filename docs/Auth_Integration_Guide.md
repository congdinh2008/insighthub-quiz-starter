# Hướng dẫn tích hợp Auth và Email

Dùng khi làm phần **Extended** về tài khoản và email (đăng ký, xác minh email, khôi phục mật khẩu, Google). Feature Slice Quiz chỉ dùng Auth scaffold với tài khoản seed và không bắt buộc tài liệu này. Tài liệu nêu **quyết định mặc định, fit-gap và điểm kiểm**, không phải lời giải. Hành vi phải đạt vẫn theo [SRS](learner/02_SRS_InsightHub_v1.1.md#req-ih-auth-001) và [Requirements mục 16.2](learner/01_Requirements_InsightHub.md#auth-email).

## 0. Auth scaffold trong Starter (từ `learner-r1.3`, giữ nguyên ở `learner-r2.0`)

Starter cấp sẵn phần **plumbing** cho phương án mặc định (Better Auth, email và mật khẩu). Scaffold không chứa chính sách SRS và không làm AC nào tự đạt.

| Thành phần | Vị trí | Đã có |
| --- | --- | --- |
| Cấu hình Better Auth 1.7.6 | `web/lib/auth/config.ts`, `server.ts`, `client.ts` | Email và mật khẩu, cookie `insighthub.session_token` ký HMAC, ID dạng UUID, bảng `auth_*` tên snake_case. `disabledPaths` tắt endpoint Extended của thư viện (`/request-password-reset`, `/reset-password`, `/change-password`, `/verify-password`, `/update-user` trả 404); test `web/tests/auth-config.test.mjs` |
| Route Better Auth | `web/app/api/auth/[...all]/route.ts` | Đăng ký, đăng nhập, đăng xuất, đọc phiên theo endpoint của thư viện |
| Bảng Auth | `api/migrations/004_auth_scaffold.sql` | `auth_user`, `auth_session`, `auth_account`, `auth_verification`, sinh bằng `getMigrations` rồi review như migration do công cụ sinh |
| API xác định người dùng | `api/app/core/auth.py`, `GET /auth/me` | Dependency `current_user` tra `auth_session` trong cùng PostgreSQL theo mỗi request (phương án (a) ở mục 2), kiểm chữ ký cookie, phiên hết hạn hoặc bị xóa trả 401 `not_authenticated` |
| Chuyển phiên web sang API | `web/lib/forward.ts` | Route handler chỉ chuyển cookie phiên InsightHub, không chuyển toàn bộ cookie |
| Trạng thái client | `web/lib/client-state.ts` | Khóa `sessionStorage` gắn người dùng; đăng xuất xóa mọi khóa `insighthub.*` |
| Giao diện | `web/app/login/`, `web/components/app/app-header.tsx`, `requireSession()` | Trang `/login` tối thiểu, menu người dùng và đăng xuất, helper chuyển về `/login` cho Server Component |
| Email | `web/lib/auth/email.ts`, `mailer.ts` | Adapter SMTP (Mailpit hoặc dịch vụ thật). Hook EML-001, EML-002 là stub báo chưa triển khai (EML-002 chỉ cần khi làm Extended) |
| Dữ liệu thử | `make seed-users`, `scripts/session_cookie.py` | Hai tài khoản A, B đã xác minh, chỉ cho môi trường local; helper in cookie phiên để smoke, eval, AEV gọi endpoint đã bảo vệ |

**Việc của học viên trên scaffold** (đối chiếu mục 3):

| Nhóm | Việc phải làm |
| --- | --- |
| Chính sách tài khoản | Bật bắt buộc xác minh email, chặn dữ liệu nghiệp vụ khi `PendingVerification`; độ dài mật khẩu LIM-01; thời hạn phiên LIM-07 (idle 2 giờ, tuyệt đối 24 giờ); thu hồi phiên khi đăng xuất. Thu hồi phiên khi đổi hoặc đặt lại mật khẩu thuộc phần Extended |
| Email | Trigger, nội dung, liên kết, thời hạn, dùng một lần và trạng thái gửi EML-001 (Core); EML-002 khi làm khôi phục mật khẩu (Extended) |
| Màn hình | Đăng ký, xác minh theo prototype M2; trang `/login` của Starter thay theo prototype. Quên, đặt lại, đổi mật khẩu và hồ sơ khi làm Extended |
| Quyền | Bảo vệ endpoint và trang demo kế thừa (đang công khai) bằng `current_user`; ownership Notebook và mọi tài nguyên con; không tin `owner_id` do client gửi |
| Kiểm chứng | Test AC Auth và quyền A/B trên bài làm; scaffold có test mẫu cho `current_user` nhưng không thay evidence AC |
| Mở rộng | Khôi phục, đặt lại, đổi mật khẩu, hồ sơ, Google, liên kết danh tính, rate limit, phiên chờ xác minh hạn chế là Extended. Khi làm, bỏ đường dẫn tương ứng khỏi `extendedAuthPaths` trong `config.ts`, ghi vào fit-gap và kiểm lại endpoint còn tắt |

Muốn thay scaffold bằng phương án khác (mục 1), ghi ADR so sánh với scaffold và giữ hợp đồng `current_user` hoặc thay đồng bộ các điểm dùng.

## 1. Thư viện mặc định

| Phương án | Khi nào dùng | Ghi chú |
| --- | --- | --- |
| **Better Auth** (TypeScript, chạy trong Next.js, lưu bảng ở PostgreSQL của app) | Mặc định của lớp | Có email/password, xác minh email, reset mật khẩu, Google, account linking, session trong DB. Starter đã cấu hình phần nền (mục 0). Học viên tập trung vào phần SRS khác mặc định thư viện |
| Authlib + pwdlib (Argon2) + session tự xây trong FastAPI | Muốn giữ Auth trong Python | Nhiều code và rủi ro bảo mật hơn; bắt buộc ADR so sánh với phương án mặc định |
| Firebase Auth | Không khuyến nghị | Email theo template dịch vụ, user nằm ngoài DB ứng dụng nên backup/restore (LR-26) phức tạp, thêm luồng dữ liệu ra nước ngoài |

Pin phiên bản thư viện trong `package-lock.json`. Giá trị mặc định có thể đổi theo phiên bản: kiểm lại bằng spike LR-09, không dựa vào tài liệu này hoặc câu trả lời của AI.

## 2. Kiến trúc cần quyết định ở M2 (fit-gap, ADR khi thay scaffold)

| Câu hỏi | Lựa chọn thường gặp | Điểm kiểm |
| --- | --- | --- |
| FastAPI xác định người dùng thế nào? | (a) Tra bảng session của Better Auth trong cùng PostgreSQL (scaffold đã chọn). (b) JWT/JWKS | LIM-07 yêu cầu thu hồi phiên trong tối đa 60 giây và IH-AUTH-008-AC02 từ chối request sau logout. JWT không tra DB chỉ đạt khi TTL rất ngắn; ghi trade-off |
| Cookie đi từ trình duyệt tới API ra sao? | Next.js route/proxy chuyển tiếp cookie hoặc session token; API không nhận định danh người dùng từ header do client tự đặt | Tài khoản B gọi thẳng API `:8107` bằng ID của A phải bị từ chối |
| Email gửi từ đâu? | (a) Callback Better Auth trong Next.js gửi SMTP tới Mailpit. (b) Gọi mailer `api/app/core/mailer.py` qua endpoint nội bộ có xác thực | IH-MSG-003-AC02: lỗi gửi được ghi nhận, không đổi kết quả nghiệp vụ, không lộ tài khoản |
| Bảng Auth được quản lý thế nào? | Sinh SQL từ CLI của thư viện, **review như migration do AI/tool sinh**, đưa vào `api/migrations/` dạng forward | Chạy trên DB đã có dữ liệu; thêm bảng vào `--extra-tables` khi kiểm restore (LR-26) |

## 3. Fit-gap: mặc định thư viện so với SRS

SRS ghi rõ không coi giá trị mặc định của thư viện là đã đáp ứng chính sách sản phẩm. Bảng dưới là điểm khởi đầu cho LR-09; học viên xác nhận bằng spike.

| Chính sách SRS | Hành vi mặc định cần kiểm | Việc học viên làm |
| --- | --- | --- |
| BR-03: không tự liên kết Google khi trùng email | Account linking bật sẵn và có thể liên kết ngầm khi email trùng | Tắt liên kết ngầm (tùy chọn `disableImplicitLinking` hoặc tương đương); kiểm IH-AUTH-005-AC02 |
| LIM-01: mật khẩu 15-128 ký tự, không cắt khoảng trắng | Có tùy chọn độ dài tối thiểu/tối đa với mặc định khác SRS | Cấu hình 15/128; test mật khẩu có khoảng trắng đầu/cuối |
| LIM-07: hết hạn sau 2 giờ không hoạt động hoặc tối đa 24 giờ; thu hồi trong 60 giây | Thời hạn session và chu kỳ làm mới theo mặc định thư viện | Cấu hình idle; tự kiểm giới hạn tuyệt đối 24 giờ; API tra trạng thái session |
| Tài khoản `PendingVerification` không truy cập dữ liệu nghiệp vụ | Scaffold để `requireEmailVerification: false` (mặc định thư viện). Chế độ bắt buộc xác minh email thường chặn đăng nhập, không có phiên hạn chế | Core: chặn dữ liệu nghiệp vụ (IH-AUTH-001-AC01). Phiên hạn chế là Extended (IH-AUTH-002-AC02) |
| LIM-09: đếm sai theo tài khoản và IP, sliding window | Rate limit của thư viện theo cửa sổ và đường dẫn | Extended (IH-AUTH-003-AC02, IH-AUTH-006-AC02): tự xây bộ đếm |
| LIM-19: bằng chứng mật khẩu dùng một lần, tối đa 5 phút | Đổi mật khẩu nhận mật khẩu hiện tại trong cùng request | Extended (IH-AUTH-010, IH-NFR-001-AC04, nhánh tái xác thực của IH-NFR-011-AC02): ghi trong fit-gap cách đáp ứng khi làm |
| EML-001..005 | Có callback cho xác minh và reset (scaffold nối sẵn tới stub); không có sẵn thông báo đổi mật khẩu, hướng dẫn tài khoản chỉ dùng Google | EML-001 là Core; EML-002 (đi cùng khôi phục mật khẩu), EML-003, EML-004 (đi cùng Google) và EML-005 thuộc Extended |

## 4. Phạm vi chấm AUTH

Theo Requirements 1.0, toàn bộ AC nhóm AUTH và MSG là **Extended**: làm thêm khi 18 AC Core của Feature Slice Quiz đã đạt, không trừ điểm khi chưa làm. Khi làm, ưu tiên hành trình email và mật khẩu (IH-AUTH-001 đến 003, IH-MSG-003 với EML-001). Nếu làm đăng nhập Google mà chưa làm liên kết, đăng nhập Google bằng email trùng tài khoản mật khẩu phải **bị từ chối an toàn**, không tự liên kết và không cấp phiên. Chức năng chưa làm thì giao diện không hiển thị. Nguồn đầy đủ: cột `tier` trong [trace/ac-trace.csv](../trace/ac-trace.csv).

## 5. Chuẩn bị và dữ liệu

- Email **test riêng** cho khóa học. Khi làm Google (Extended): tài khoản Google test riêng, OAuth client ở chế độ testing với danh sách test user, callback trên `localhost`.
- Mailpit cho kiểm local (`make mail-up`); thư nhận trên Mailpit qua SMTP của ứng dụng được chấp nhận làm evidence EML-001 (Requirements mục 16.2, mã D5). Gửi thư thật là tùy chọn: Gmail riêng cho khóa học qua App Password và biến `WEB_SMTP_*` ([GETTING_STARTED](../GETTING_STARTED.md#gửi-thư-thật-bằng-gmail-tùy-chọn)).
- Client secret chỉ nằm trong `.env`; không dán vào Claude, log, issue hoặc ảnh chụp.

## 6. Điểm kiểm tối thiểu trước khi báo Auth đạt

- Tài khoản B không đọc, sửa, xóa được tài nguyên của A khi gọi thẳng API bằng ID của A.
- Logout làm request dùng phiên cũ bị từ chối trong giới hạn LIM-07 (đổi, reset mật khẩu cũng vậy nếu đã làm Extended).
- Phản hồi đăng nhập (và quên mật khẩu nếu đã làm) không tiết lộ tài khoản tồn tại (IH-NFR-001-AC05).
- Log, lỗi và report không chứa mật khẩu, token, link reset (IH-NFR-008-AC02).
- `/security-review` đã chạy trên PR Auth; finding đã phân loại theo [Review Workflow](ai/Review_Workflow.md).
