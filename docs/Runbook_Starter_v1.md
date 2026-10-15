# Runbook InsightHub Starter v1

## Preflight

```sh
docker version
docker compose version
git status --short
```

Không dùng cùng Compose project name cho lớp học và test. Không dùng `down -v` với namespace có dữ liệu cần giữ.

Mỗi Compose project mở PostgreSQL ra `127.0.0.1:${DB_PORT:-5433}`. Khi chạy song song nhiều project (starter, check, real, recovery), đặt `DB_PORT` riêng cho project thứ hai trở đi, ví dụ `DB_PORT=5434` cho `insighthub-c07-check`, `5435` cho `insighthub-c07-real`, `5436` cho `insighthub-c07-recovery`; nếu không, lệnh `up` báo cổng đã bị chiếm.

## Start và kiểm tra

```sh
docker compose --env-file .env -p insighthub-c07-starter up --build -d --wait
curl -fsS http://127.0.0.1:8107/readyz
curl -fsS http://127.0.0.1:8107/system/profile
python3 scripts/smoke.py --api-url http://127.0.0.1:8107 --web-url http://127.0.0.1:3107
```

`/system/profile` phải khớp file `.env` đang dùng. Endpoint này không trả credential.

## Regression

```sh
DB_PORT=5434 make COMPOSE="docker compose --env-file .env.example -p insighthub-c07-check" test
git diff --check
```

Fixture regression không gọi dịch vụ AI bên ngoài.

Thư mục `reports/` bị `.gitignore` để báo cáo nháp không vào Git. Evidence đã review (không chứa cookie, key, dữ liệu thật) đưa vào commit bằng `git add -f reports/<đường dẫn file>` và ghi đường dẫn trong PR hoặc hồ sơ milestone.

<a id="kiem-tra-sau-khi-bao-ve-endpoint"></a>

## Kiểm tra sau khi bảo vệ endpoint (từ M3.1)

Khi `/documents`, `/chat`, `/operations` đã yêu cầu phiên đăng nhập, smoke, eval adapter và AEV gửi kèm cookie phiên của tài khoản thử. Đặt `SEED_USER_PASSWORD` trong `.env` trước (bỏ dấu `#`, ít nhất 15 ký tự); `seed-users` và `session_cookie.py` cùng đọc biến này:

```sh
make COMPOSE="docker compose --env-file .env -p insighthub-c07-starter" seed-users
export INSIGHTHUB_SESSION_COOKIE="$(python3 scripts/session_cookie.py --web-url http://127.0.0.1:3107)"
python3 scripts/smoke.py --api-url http://127.0.0.1:8107 --web-url http://127.0.0.1:3107
unset INSIGHTHUB_SESSION_COOKIE
```

Thêm `--account B` để lấy phiên tài khoản B khi kiểm quyền A/B. Cookie là phiên thật: không in ra log, không dán vào công cụ AI, không đưa vào evidence; chỉ ghi lệnh đã chạy và kết quả. Script cũ `web/tests/e2e.mjs`, spec mẫu `web/e2e/smoke.spec.ts` và probe đọc qua API của backup drill viết cho endpoint công khai rc.3, học viên cập nhật cùng bài làm (đăng nhập trong E2E, `dependency_overrides[current_user]` trong `TestClient`).

## AEV với provider thật

```sh
python3 scripts/run_aev.py --api-url http://127.0.0.1:8107
```

Runner upload corpus riêng, chạy `evaluation/AEV-01.json`, kiểm Answered/NoEvidence, source scope, claim citation và prompt injection, rồi xóa đúng các tài liệu nó vừa tạo. Report được ghi vào `reports/evaluation/` và không chứa API key.

## Backup và restore drill

```sh
COMPOSE_PROJECT_NAME=insighthub-c07-starter ENV_FILE=.env make backup-restore-check
```

Script từ chối database rỗng. Nó hash mọi giá trị của tám bảng, gồm bytes gốc, segments, vectors, attempts và operations; so sánh trước/restore/sau để phát hiện thay đổi đồng thời. API trên database restore phải đọc đúng toàn văn/locator, đối soát chat và retrieve đúng phạm vi. Database tạm và dump tự xóa sau drill; report hash được giữ trong `reports/backup-restore/`.

**Thêm bảng của bài làm:** tám bảng trên là mặc định. Khi thêm bảng mới (ví dụ bảng Quiz của bạn, cùng `auth_user` và `ai_jobs` của scaffold), đưa chúng vào drill bằng `--extra-tables auth_user,ai_jobs,<bảng Quiz>` hoặc biến môi trường `BACKUP_EXTRA_TABLES=auth_user,ai_jobs,<bảng Quiz>` (dùng được với `make backup-restore-check`). Tên bảng chỉ gồm chữ thường, số, `_` và tùy chọn tiền tố schema; tên không hợp lệ bị từ chối. Điều kiện "database không rỗng" vẫn áp dụng cho các bảng nền; kiểm đọc qua API cho dữ liệu mới do học viên bổ sung.

Tạo corpus fixture cho drill trong namespace test riêng:

```sh
# .env.example để trống BETTER_AUTH_SECRET; namespace test dùng giá trị cố định, không phải secret.
export BETTER_AUTH_SECRET=test-only-not-a-secret-0123456789abcdef
API_PORT=8127 WEB_PORT=3127 DB_PORT=5436 docker compose --env-file .env.example -p insighthub-c07-recovery up --build -d --wait
python3 scripts/seed_recovery_fixture.py --api-url http://127.0.0.1:8127
python3 scripts/backup_restore_check.py --project insighthub-c07-recovery --env-file .env.example
docker compose --env-file .env.example -p insighthub-c07-recovery down
unset BETTER_AUTH_SECRET
```

Dừng mutation trong khi kiểm hash. Seed gồm TXT/MD/PDF, một failed attempt và chat, không dùng dữ liệu người thật. Cần giữ dump để diễn tập thủ công thì thêm `--keep-backup`: quyền file 600, thư mục riêng 700, chỉ instructor truy cập, không commit/gửi cùng starter. Đề xuất giữ tối đa 7 ngày trong sandbox rồi xóa sau khi đã kiểm restore; dữ liệu lớp thật áp dụng policy lớp đã xác nhận. Không dùng backup fixture làm evidence semantic của real embedding.

Backup production cần thêm retention, encryption, off-host storage, quyền truy cập và restore drill định kỳ. Starter chỉ cung cấp baseline có thể kiểm chứng tại local.

## Sự cố thường gặp

| Hiện tượng | Kiểm tra | Xử lý |
| --- | --- | --- |
| `/readyz` trả 503 | `docker compose logs api postgres` | Kiểm DB, migration và embedding identity |
| Upload 409 | Operation key hoặc file SHA-256 đã tồn tại | Đối soát operation, không đổi key để che lỗi |
| Chat `NoEvidence` | Threshold, source selection, corpus | Kiểm citation candidates và chạy AEV |
| Provider 429/502/504 | Log theo `X-Request-ID` | Chờ retry bounded, kiểm quota và policy |
| Local reranker không kết nối | `docker compose -f infra/reranker/docker-compose.yml ps` | Kiểm TEI health, model download và port 8187 |
| Index identity conflict | `/readyz`, config embedding | Dùng index/volume riêng hoặc migration có chủ đích |

## Stop

```sh
docker compose --env-file .env -p insighthub-c07-starter down
```

Lệnh này giữ volume. Chỉ xóa volume của namespace test khi đã kiểm đúng project name.
