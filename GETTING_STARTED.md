# Chạy InsightHub Starter

## Yêu cầu

- Máy cá nhân có Docker và Docker Compose v2 do học viên tự chuẩn bị: Docker Desktop (macOS/Windows), Docker Engine (Linux, WSL2), hoặc phương án thay thế như Colima, OrbStack (macOS) hay Podman nếu chạy được Docker Compose v2 của Starter. Học viên tự kiểm điều khoản sử dụng của công cụ đã chọn. Windows xem mục [Windows (WSL2)](#windows-wsl2).
- RAM trống khoảng 3 GiB: tổng `mem_limit` của postgres, api, web là khoảng 2,3 GiB (768 MiB + 1 GiB + 512 MiB), cộng thêm khi build image.
- Cổng 8107 và 3107 trống, hoặc đặt `API_PORT`/`WEB_PORT` khác.
- Git, Python 3.11+ và Make để dùng công cụ kiểm/đóng gói. Browser E2E cần Node 24.20.0 và Playwright trong lockfile; chạy ứng dụng chỉ cần Docker.

## Windows (WSL2)

WSL2 là đường chính thức trên Windows vì Makefile và script cần bash, GNU make và python3. Chạy trực tiếp trên PowerShell/CMD không được hỗ trợ.

1. Cài WSL2 và Ubuntu (PowerShell quyền Admin): `wsl --install -d Ubuntu-24.04`, khởi động lại máy, tạo user Linux. Kiểm `wsl -l -v` hiển thị `VERSION 2`.
2. Chọn một cách chạy Docker:
   - Docker Desktop for Windows, bật `Settings > Resources > WSL integration` cho distro Ubuntu.
   - Docker Engine cài trong Ubuntu WSL theo hướng dẫn Docker cho Ubuntu; bật `systemd=true` trong `/etc/wsl.conf`.

   Kiểm trong terminal Ubuntu: `docker compose version`. Chọn cách phù hợp với máy cá nhân và tự kiểm điều khoản sử dụng của công cụ; Docker Engine trong WSL là phương án không cần Docker Desktop.
3. Cài công cụ trong Ubuntu: `sudo apt update && sudo apt install -y git make python3 python3-venv curl`. Node.js 24.20.0 chỉ cần khi chạy browser E2E trên máy (cài qua nvm hoặc fnm).
4. Clone repository **trong filesystem của WSL** (ví dụ `~/work/insighthub`), không clone vào `/mnt/c/...` vì I/O chậm, lỗi quyền file và file watcher. Mở bằng VS Code extension WSL (`code .` trong thư mục repo).
5. Đặt `git config --global core.autocrlf input`. Repository có `.gitattributes` giữ LF và giữ nguyên byte của SRS, corpus, tài liệu mẫu.
6. Nếu mạng đang dùng cần proxy, cấu hình proxy cho Docker, apt và npm; báo mentor trước buổi B1 nếu build image bị chặn.

**Phương án dự phòng: devcontainer.** Khi không cài được công cụ trong WSL, mở repo bằng VS Code Dev Containers (`Reopen in Container`). [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json) cung cấp Python 3.12, Node 24.20.0, make và Docker-in-Docker; máy host vẫn cần Docker (Docker Desktop hoặc Docker Engine trong WSL). Cấu hình này chưa được pilot trên máy học viên; ghi lại lỗi gặp phải để mentor xử lý.

## Fork starter và khởi tạo bài làm

Học viên C07 bắt buộc fork repository starter theo URL và phiên bản giảng viên công bố. Trên dịch vụ Git, tạo fork cá nhân hoặc trong không gian lớp được cấp, sau đó thay các giá trị ví dụ dưới đây bằng URL thực.

**Fork là public** vì Starter public. Chỉ commit dữ liệu giả và tài liệu mẫu. Không commit `.env`, API key, mật khẩu, dữ liệu thật của công ty hoặc thông tin cá nhân. Lỡ commit secret thì thu hồi key trước, rồi báo mentor.


```sh
git clone 'URL_FORK_CA_NHAN' insighthub
cd insighthub
git remote add upstream 'URL_REPOSITORY_STARTER'
git remote -v
git rev-parse HEAD
git switch -c milestone/m0.1
```

`origin` phải trỏ tới fork cá nhân, `upstream` trỏ tới starter. Ghi commit nền và nguồn starter vào hồ sơ dự án; giữ nguyên lịch sử Git. Thiết lập `user.name` và `user.email` của học viên. Cách commit, tạo PR trong repository cá nhân, gửi bài cho giảng viên và thời hạn tại [Requirements](docs/learner/01_Requirements_InsightHub.md).

Bật workflow `.github/workflows/app-ci.yml` trên fork nếu dùng GitHub Actions. Workflow chạy trên push vào `main` và trên pull request, dùng fixture, không cần khóa AI. Xác nhận kết quả khi workflow thực chạy; không giả định quyền Actions hoặc secret của repository gốc được chuyển sang fork.

## Chuẩn bị Claude Code và GitHub CLI

1. Cài Claude Code theo phiên bản giảng viên công bố trong Tool Readiness; đăng nhập bằng tài khoản Claude Pro/Max học tập và kiểm thiết lập privacy (Requirements mục 3.4).
2. Hook của repo chạy bằng `python3` (cùng yêu cầu với Makefile). Mở `claude` tại thư mục repo, chạy `/hooks` để xác nhận hai hook `block_secrets.py` và `protect_approved_tests.py` đã nạp. Thử an toàn: yêu cầu Claude chạy `cat .env`; kết quả mong đợi là bị hook chặn và có dòng `deny` trong `reports/hooks/events.jsonl`.
3. Cài GitHub CLI và chạy `gh auth login` để dùng `/code-review --comment <số PR>` theo [Review Workflow](docs/ai/Review_Workflow.md).
4. Chạy `python3 scripts/trace_check.py` và `python3 -m unittest discover -s scripts/tests` để xác nhận công cụ Kit chạy được trên máy (không cần Docker).

Không đặt API key vào biến môi trường của shell đang chạy Claude Code; key chỉ nằm trong `.env` để Compose đọc.

## Khi nhận thêm gói ZIP

ZIP dùng để đối chiếu hoặc kiểm cài đặt sạch, không thay repository fork nộp bài. Giải nén vào thư mục riêng và kiểm SHA-256 trước khi chạy; không ghi đè bản fork đang phát triển. Nếu chưa có quyền fork, báo giảng viên cấp quyền và tiếp tục kiểm setup trên ZIP, ghi rõ phụ thuộc chưa hoàn tất. Không tạo lịch sử Git mới để giả lập nguồn starter.

[SRS](docs/learner/02_SRS_InsightHub_v1.1.md) (đặc tả sản phẩm) và hợp đồng API tham khảo nằm trong `docs/learner/`. Phần bài tập phải làm xác định trong Requirements mục 1. `PACKAGE_MANIFEST.json`, khi có trong gói Starter, là biên nhận của đúng gói mã nguồn đó; không thay bảng phạm vi hoặc kết quả kiểm của bài làm. Không đưa `.env` thật vào Git hoặc artifact. Đọc [Requirements](docs/learner/01_Requirements_InsightHub.md) mục 1 đến 5 trước khi phát triển.

## Khởi động offline fixture

```sh
cp .env.example .env
```

Mở `.env` bằng trình soạn thảo và điền `BETTER_AUTH_SECRET` (khóa ký cookie phiên của Auth scaffold, tối thiểu 32 ký tự). Tạo giá trị bằng `openssl rand -base64 32` rồi dán vào file; không in `.env` ra terminal hoặc gửi cho công cụ AI. Thiếu biến này thì Compose dừng với thông báo hướng dẫn.

### Chuẩn bị trước buổi 1: kéo image và build sẵn

Làm bước này ngay khi nhận Starter, trên mạng ổn định, để không phải chờ tải image hoặc build trong lúc làm M0.1 và trên lớp. Lần đầu có thể mất vài phút đến vài chục phút tùy tốc độ mạng.

```sh
docker compose --env-file .env -p insighthub-c07-starter pull postgres
docker compose --env-file .env -p insighthub-c07-starter build
```

Sau đó lệnh `up --build` bên dưới dùng lại image và cache build đã có nên chạy nhanh. Nếu build lỗi do mạng hoặc proxy, ghi lỗi vào checklist setup buổi 1 để mentor hỗ trợ. Lịch tự học gợi ý theo ngày nằm ở [nhịp tuần mẫu](docs/learner/01_Requirements_InsightHub.md#nhip-tuan-mau) của Requirements.

```sh
docker compose --env-file .env -p insighthub-c07-starter up --build -d --wait
```

- Web: http://localhost:3107
- API docs: http://localhost:8107/docs
- Readiness: http://localhost:8107/readyz

Upload riêng từng file trong `sample-docs/`. Fixture trả trích đoạn có nhãn để kiểm flow. Nó không chứng minh câu trả lời AI có chất lượng.

### Tài khoản thử A và B (Auth scaffold)

```sh
make COMPOSE="docker compose --env-file .env -p insighthub-c07-starter" seed-users
```

Lệnh tạo `a@insighthub.test` và `b@insighthub.test` qua endpoint đăng ký của Better Auth rồi đánh dấu đã xác minh (chỉ cho dữ liệu thử). Mật khẩu lấy từ `SEED_USER_PASSWORD` trong `.env`; để trống thì script sinh mật khẩu và in một lần. Đăng nhập tại http://localhost:3107/login, kiểm menu người dùng và đăng xuất. Trang demo `/` và các endpoint tài liệu, hỏi đáp kế thừa từ rc.3 vẫn công khai; bảo vệ chúng bằng phiên và quyền là việc của học viên ở M3.1 (xem [Auth Integration Guide](docs/Auth_Integration_Guide.md)).

Nền UI: trang `/dev/ui-kit` hiển thị component dùng chung; token và quy tắc tại [UI Foundation](docs/UI_Foundation.md). Prototype HTML ở M2 dùng `design/prototype/_base/`.

<a id="mcp-chi-doc"></a>

### MCP PostgreSQL chỉ đọc (M0.2, LR-05)

Ranh giới quyền nằm ở database: role `insighthub_readonly` (migration 003) chỉ có `SELECT` trên bảng tài liệu và vận hành, giao dịch mặc định chỉ đọc, `statement_timeout` 5 giây, không đọc bảng phiên Auth. Server MCP của Starter (`tools/mcp/insighthub_db_readonly.py`, SDK `mcp` 2.2.0) từ chối chạy nếu kết nối bằng role khác.

1. Cài [uv](https://docs.astral.sh/uv/) (dùng để chạy server với phiên bản đã pin).
2. Mở `.env`, bỏ dấu `#` của `MCP_DB_READONLY_PASSWORD=` và đặt mật khẩu riêng cho role. Cổng database trên máy mặc định `5433` (`DB_PORT`), chỉ mở trên `127.0.0.1`.
3. Bật đăng nhập cho role và kiểm kết nối:

   ```sh
   make COMPOSE="docker compose --env-file .env -p insighthub-c07-starter" mcp-role
   make mcp-check
   ```

4. Tạo cấu hình cho Claude Code: `cp .mcp.json.example .mcp.json` (file này bị `.gitignore`, không commit). Mở `claude` tại thư mục repo, chạy `/mcp` và duyệt server `insighthub-db`.
5. Evidence LR-05 gồm ba lượt: một truy vấn hợp lệ, một lỗi tool (ví dụ bảng không tồn tại) và một lệnh ghi bị database từ chối (`cannot execute INSERT in a read-only transaction` hoặc `permission denied`).

**Phương án dự phòng** khi máy không chạy được MCP: dùng tool Bash của Claude Code gọi `psql` bằng chính role chỉ đọc, ví dụ `psql "postgresql://insighthub_readonly@127.0.0.1:5433/insighthub" -c "SELECT count(*) FROM documents"`. Tool Bash của Claude Code không nhập được mật khẩu tương tác, nên lưu mật khẩu role vào `~/.pgpass` (dòng `127.0.0.1:5433:insighthub:insighthub_readonly:<mật khẩu>`, `chmod 600 ~/.pgpass`) trước khi mở `claude`; không đặt mật khẩu trong lệnh hoặc prompt. Máy chưa có `psql` thì chạy trong container với `-T` (không cần TTY) và tự nhập mật khẩu trong terminal riêng: `docker compose --env-file .env -p insighthub-c07-starter exec -T postgres psql -h 127.0.0.1 -U insighthub_readonly -d insighthub -c "SELECT 1"`, hoặc gán `PGPASSWORD` trong shell của học viên trước khi mở `claude` (không gõ vào chat). Evidence vẫn phải có lỗi do database trả về; lời từ chối của mô hình không thay kiểm soát thực tế.

Ghi SHA mã nguồn và hash file mẫu đã dùng trong hồ sơ milestone. Khi chạy lại trên dữ liệu còn tồn tại, cùng byte của tài liệu `Ready` được dedup; cùng byte của tài liệu `Failed` trả `409 document_conflict` theo [API Contract](docs/API_Contract_Starter_v1.md). Đổi `Idempotency-Key` không đổi danh tính nội dung. Với ca kiểm validation cho file mới, dùng nội dung thử riêng; với ca dedup/retry, giữ nguyên nội dung để kiểm đúng hành vi. Không xóa volume hoặc nới expected result để làm test đạt.

Nếu giảng viên cung cấp revision Starter mới, giữ commit nền cũ, review diff trước khi tích hợp vào fork và kiểm lại phần bị ảnh hưởng. Không reset mất bài làm; evidence của lần chạy trước vẫn thuộc SHA/corpus trước đó.

## Email local với Mailpit (tùy chọn)

Starter cấp hạ tầng tối thiểu cho phần Auth/Email của bài làm: mail catcher Mailpit (Compose profile `mail`), adapter SMTP [`api/app/core/mailer.py`](api/app/core/mailer.py) và adapter gửi thư của Auth scaffold (`web/lib/auth/mailer.ts`). Hook gửi EML-001, EML-002 (EML-002 khi làm Extended) của Better Auth mới là stub báo chưa triển khai; nội dung, trigger, thời hạn liên kết và chính sách xác minh là việc của học viên theo Requirements.

```sh
make COMPOSE="docker compose --env-file .env -p insighthub-c07-starter" mail-up
```

- SMTP: `127.0.0.1:1025` từ máy; `mailpit:1025` từ container API (mặc định của `SMTP_HOST`/`SMTP_PORT`).
- Giao diện xem thư: http://127.0.0.1:8025
- Đổi cổng khi bị chiếm: `MAIL_SMTP_PORT`, `MAIL_UI_PORT`. Đổi người gửi: `MAIL_FROM`.

Mailpit giữ thư trong máy, không gửi ra Internet. Chỉ dùng địa chỉ email test; không dùng email hoặc dữ liệu thật của công ty. Dừng bằng `make ... mail-down`.

## Gửi thư thật bằng Gmail (tùy chọn)

Thư nhận trên Mailpit đã đủ làm evidence EML-001 (Requirements mục 16.2). Chỉ làm phần này khi muốn kiểm thư tới hộp thư thật.

1. Dùng một Gmail riêng cho khóa học (tạo mới hoặc tài khoản cá nhân phụ). Không dùng tài khoản công ty hoặc Google Workspace của đơn vị. App Password cho phép gửi thư thay tài khoản, nên không dùng Gmail cá nhân chính.
2. Bật 2-Step Verification cho tài khoản, tạo App Password tại `myaccount.google.com/apppasswords`.
3. Thêm vào `.env` (không commit, không dán vào công cụ AI): `WEB_SMTP_HOST=smtp.gmail.com`, `WEB_SMTP_PORT=587`, `WEB_SMTP_USER=<địa chỉ Gmail>`, `WEB_SMTP_PASSWORD=<App Password>`, `MAIL_FROM=InsightHub <địa chỉ Gmail>`. Cổng 587 dùng STARTTLS, giữ `WEB_SMTP_SECURE` mặc định `false`.
4. Tạo lại container web: `make COMPOSE="docker compose --env-file .env -p insighthub-c07-starter" up`.
5. Đăng ký hai tài khoản A/B bằng plus-addressing của cùng hộp thư, ví dụ `ten+a@gmail.com` và `ten+b@gmail.com`; thư của cả hai về một inbox.

Gmail cá nhân giới hạn số thư gửi mỗi ngày (khoảng 500 người nhận), đủ cho bài tập. Che địa chỉ email và link xác minh còn hiệu lực trong ảnh hoặc log nộp bài. Xóa App Password sau khóa học.

## Kiểm tra

```sh
DB_PORT=5434 make COMPOSE="docker compose --env-file .env.example -p insighthub-c07-check" test
make API_URL=http://127.0.0.1:8107 WEB_URL=http://127.0.0.1:3107 smoke
git diff --check
```

Backend integration tests tạo PostgreSQL schema ngẫu nhiên và tự xóa. Smoke test chỉ xóa document do chính lần chạy tạo. `DB_PORT=5434` cho project check tránh trùng cổng `5433` của project starter đang chạy; project real dùng `5435`. Từ M3.1, smoke cần cookie phiên theo [Runbook](docs/Runbook_Starter_v1.md#kiem-tra-sau-khi-bao-ve-endpoint).

## Migration dữ liệu cũ

API tự chạy migration forward-only trong `api/migrations/` khi startup. Có thể chạy riêng:

```sh
make COMPOSE="docker compose --env-file .env -p insighthub-c07-starter" migrate
```

Không xóa volume để xử lý schema mismatch. Sao lưu trước khi thay embedding dimension hoặc identity; vector cũ không được diễn giải bằng model mới.

## Provider thật

Sửa ngay file `.env` đã tạo, không copy thêm profile:

```env
RAG_MODE=real
DEEPSEEK_API_KEY=<key DeepSeek>
GEMINI_API_KEY=<key Gemini>
```

Key do học viên tự mua và tự chịu chi phí; đặt spending limit trên tài khoản provider trước khi chạy. Muốn dùng provider khác thay DeepSeek (Gemini, Anthropic, gateway OpenAI-compatible, Ollama local), xem [Model Profiles](docs/Model_Profiles_And_Reranking.md#provider-tuy-chon). Đây là ba biến cần cấu hình. DeepSeek trả lời bằng `deepseek-flash`; Gemini tạo embedding bằng `gemini-embedding-2`, 1024 chiều. Không cần key OpenAI, Anthropic, Voyage hoặc Cohere cho cấu hình này. Reranker mặc định tắt.

Điền khóa vào `.env` tại máy, không sửa file `.example`, không gửi key trong chat hay dán vào công cụ AI, không commit credential. Chỉ gửi dữ liệu giả tới provider. Nếu chuyển từ env cũ, bỏ các dòng `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `LLM_MODEL`, `EMBEDDING_MODEL`, `RAG_PROFILE`, `AI_DATA_USAGE_NOTICE` và `AI_DATA_POLICY_URL` để dùng mặc định mới. Thay model khi cần bằng hai biến được chú thích trong `.env.example`.

Áp dụng lại cấu hình và kiểm profile:

```sh
API_PORT=8117 WEB_PORT=3117 DB_PORT=5435 docker compose --env-file .env -p insighthub-c07-real up --build -d --wait
curl -fsS http://127.0.0.1:8117/system/profile
python3 scripts/run_aev.py --api-url http://127.0.0.1:8117
```

Profile đúng là `classroom-deepseek-gemini`, generation `deepseek`, embedding `gemini`, reranker `none`. Thiếu key sẽ báo lỗi khi khởi động; provider lỗi không fallback sang fixture. Test real AEV gửi bộ tài liệu mẫu và câu hỏi tới hai provider.

Ví dụ trên giữ fixture ở 8107/3107 và real ở 8117/3117 với volume riêng. Upload lại tài liệu gốc vào real runtime; không dùng vector fixture cho real. Chỉ đổi model hỏi đáp không làm thay đổi embedding identity. Chi tiết về reranker và tuning tại [Model Profiles và Reranking](docs/Model_Profiles_And_Reranking.md).

## Backup và restore

```sh
COMPOSE_PROJECT_NAME=insighthub-c07-starter ENV_FILE=.env make backup-restore-check
```

Backup drill yêu cầu corpus có dữ liệu, một chat thành công và một failed attempt; xem lệnh seed riêng và cách thêm bảng mới của bài làm vào drill trong [Runbook](docs/Runbook_Starter_v1.md#backup-và-restore-drill).

## Dừng

```sh
docker compose --env-file .env -p insighthub-c07-starter down
```

Lệnh trên giữ volume. Chỉ dùng `down -v` với namespace test có thể hủy và sau khi đã kiểm đúng project.
