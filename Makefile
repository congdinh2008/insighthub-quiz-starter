COMPOSE ?= docker compose
PYTHON ?= python3
API_URL ?= http://127.0.0.1:8107
WEB_URL ?= http://127.0.0.1:3107

.PHONY: seed-users mcp-role mcp-check trace-check trace-sample eval ai-bom delivery-report up down build test test-db test-backend test-web test-tools test-e2e test-pw mail-up mail-down smoke migrate sbom aev backup-restore-check reranker-local-up reranker-local-down
up:
	$(COMPOSE) up --build -d --wait

down:
	$(COMPOSE) --profile ollama --profile checks --profile mail down

# Optional local mail catcher (Mailpit): SMTP 127.0.0.1:1025, UI http://127.0.0.1:8025
mail-up:
	$(COMPOSE) --profile mail up -d mailpit

mail-down:
	$(COMPOSE) --profile mail stop mailpit

build:
	$(COMPOSE) build api web

# Auth scaffold: dịch vụ api bắt buộc BETTER_AUTH_SECRET. Test dùng giá trị cố định, không phải secret,
# để `--env-file .env.example` (giá trị trống) vẫn chạy được. Giá trị trong môi trường shell được ưu tiên.
test-db test-backend test-web: export BETTER_AUTH_SECRET ?= test-only-not-a-secret-0123456789abcdef

test-db:
	$(COMPOSE) up -d --wait postgres

test-backend: test-db
	$(COMPOSE) build api
	$(COMPOSE) run --rm --no-deps -e RUN_DB_TESTS=1 -e TEST_SCHEMA_PATH=/tmp/init.sql -v "$(CURDIR)/infra/db/init.sql:/tmp/init.sql:ro" api python -m unittest discover -s tests -v

test-web:
	$(COMPOSE) build web-check
	$(COMPOSE) --profile checks run --rm --no-deps web-check

test-tools:
	$(PYTHON) -m unittest discover -s scripts/tests -v

test-e2e:
	cd web && npm run test:e2e

# Playwright Test trong web/e2e (cần stack fixture đang chạy).
test-pw:
	cd web && npm run test:pw

test: test-backend test-web test-tools

smoke:
	$(PYTHON) scripts/smoke.py --api-url "$(API_URL)" --web-url "$(WEB_URL)"

migrate:
	$(COMPOSE) run --rm api python -c "from app.core.db import initialize_database,close_pool; initialize_database(); close_pool()"

sbom:
	$(PYTHON) scripts/generate_sbom.py

aev:
	$(PYTHON) scripts/run_aev.py --api-url "$(API_URL)"

backup-restore-check:
	$(PYTHON) scripts/backup_restore_check.py --project "$${COMPOSE_PROJECT_NAME:?Set COMPOSE_PROJECT_NAME}" --env-file "$${ENV_FILE:-$$([ -f .env ] && echo .env || echo .env.example)}"

# AI Engineering Kit (docs/ai/README.md)
trace-check:
	$(PYTHON) scripts/trace_check.py $(if $(GATE),--gate $(GATE),)

trace-sample:
	$(PYTHON) scripts/trace_sample.py --seed "$${SEED:?Set SEED, for example SEED=hv01-20261004}" --size "$${SIZE:-10}" --tier "$${TIER:-Core}"

eval:
	$(PYTHON) evaluation/harness/run_eval.py --api-url "$(API_URL)" $(if $(SUITE),--suite $(SUITE),) $(if $(K),--k $(K),)

ai-bom:
	$(PYTHON) scripts/generate_ai_bom.py

delivery-report:
	$(PYTHON) scripts/delivery_report.py

reranker-local-up:
	TEI_IMAGE=$$(if [ "$$(uname -m)" = "arm64" ] || [ "$$(uname -m)" = "aarch64" ]; then echo ghcr.io/huggingface/text-embeddings-inference:cpu-arm64-1.9; else echo ghcr.io/huggingface/text-embeddings-inference:cpu-1.9; fi) docker compose -f infra/reranker/docker-compose.yml up -d

reranker-local-down:
	docker compose -f infra/reranker/docker-compose.yml down

# MCP chỉ đọc (LR-05): bật đăng nhập cho role insighthub_readonly bằng mật khẩu trong .env.
# Không in mật khẩu. Chạy lại khi đổi mật khẩu.
mcp-role:
	@pw=$$(grep -E '^MCP_DB_READONLY_PASSWORD=' .env 2>/dev/null | cut -d= -f2-); \
	if [ -z "$$pw" ]; then echo "Thiếu MCP_DB_READONLY_PASSWORD trong .env"; exit 1; fi; \
	printf "ALTER ROLE insighthub_readonly LOGIN PASSWORD :'pw';\n" | \
	$(COMPOSE) exec -T postgres psql -q -v ON_ERROR_STOP=1 -v pw="$$pw" -U insighthub -d insighthub && echo "Đã bật đăng nhập cho insighthub_readonly"

mcp-check:
	uv run --no-project --python 3.12 --with mcp==2.2.0 --with "psycopg[binary]==3.3.5" tools/mcp/insighthub_db_readonly.py --check

# Auth scaffold: tạo tài khoản thử A và B đã xác minh (cần stack đang chạy).
seed-users:
	$(PYTHON) scripts/seed_auth_users.py --web-url "$(WEB_URL)" --compose "$(COMPOSE)"
