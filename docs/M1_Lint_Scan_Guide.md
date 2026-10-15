# Hướng dẫn lint và scan cho M1

Rubric M1 chấm "test và lint thực chạy" và "secret scan, dependency scan". Starter chỉ có sẵn test, smoke, E2E và `npm audit` trong [App CI](../.github/workflows/app-ci.yml). **Lint và scan là phần học viên tự thêm** vào fork. Cấu hình dưới đây là gợi ý, chưa bật trong Starter.

## Baseline Starter có finding sẵn

Đo trên Starter `learner-r1.3` ngày 06/10/2026:

| Công cụ | Kết quả baseline |
| --- | --- |
| `ruff check api scripts --select E4,E7,E9,F,I,B` (ruff 0.16.9, chưa có `api/pyproject.toml`) | 59 finding: 25 I001 (thứ tự import), 26 E701/E702 (nhiều lệnh một dòng), 3 B008, 2 B904, 2 B018, 1 E401 |
| `ruff format --check api` | 28 file cần format |
| ESLint với cấu hình gợi ý bên dưới | 6 finding: 4 `react-hooks/set-state-in-effect` (`ChatPanel.tsx`, `SourceView.tsx`, `UploadPanel.tsx`), 1 `no-explicit-any` (`lib/operations.ts`), 1 `no-empty` (`tests/e2e.mjs`) |
| `pip-audit -r api/requirements.txt` (2.10.1) | Không có lỗ hổng đã biết |
| `npm audit --omit=dev --audit-level=high --prefix web` | 0 lỗ hổng |
| gitleaks 8.30.1, toàn lịch sử | Không phát hiện |

Kết quả audit phụ thuộc thời điểm chạy: advisory mới có thể xuất hiện sau ngày đo. Finding mới là việc cần triage, không phải lỗi của công cụ.

Vì vậy **không bật gate toàn repo ngay**: khoanh phạm vi vào file học viên thay đổi (changed files), triage finding của baseline (sửa, ghi nhận có lý do hoặc để sau), ghi quyết định vào evidence M1. Không format lại toàn bộ Starter trong cùng PR với tính năng; nếu muốn, tách một PR `style:` riêng.

## Cấu hình gợi ý

### Python: ruff (thư mục `api/`)

Thêm vào `api/pyproject.toml` (tạo mới nếu chưa có):

```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B"]
```

Chạy: `ruff check <file thay đổi>`; `ruff format --check <file thay đổi>`.

### Web: ESLint (thư mục `web/`)

Next.js 16 không còn lệnh `next lint`; dùng ESLint CLI với flat config. Cài bằng `npm i -D -E --prefix web eslint @eslint/js typescript-eslint eslint-plugin-react-hooks globals` (lockfile ghi version), rồi tạo `web/eslint.config.mjs`:

```js
import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';

export default tseslint.config(
  { ignores: ['.next/**', 'node_modules/**', 'out/**', 'next-env.d.ts', 'playwright-report/**', 'test-results/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  { languageOptions: { globals: { ...globals.browser, ...globals.node } } },
  { plugins: { 'react-hooks': reactHooks }, rules: reactHooks.configs.recommended.rules },
);
```

Thiếu khối `globals`, ESLint báo `no-undef` cho `process`, `console` trong file `.js`, `.mjs` (khoảng 36 finding giả).

Thêm script `"lint": "eslint"` vào `web/package.json`; chạy `npx eslint <file thay đổi>` trong `web/`.

### Secret scan: gitleaks

Chạy toàn lịch sử Git (không cần cài, dùng Docker):

```sh
docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.30.1 git /repo --redact -v
```

Giá trị giả trong test (ví dụ `test-not-real`) có thể bị báo; allowlist có lý do trong `.gitleaks.toml`, không tắt cả rule. Không dán secret thật vào output hoặc chat.

### Dependency scan: pip-audit và npm audit

```sh
pip-audit -r api/requirements.txt
npm audit --omit=dev --audit-level=high --prefix web
```

### Kiểm package do AI đề xuất có tồn tại thật

Coding agent có thể đề xuất package không tồn tại hoặc gần tên package phổ biến (slopsquatting). Trước khi thêm dependency mới:

```sh
pip index versions <tên-package>          # Python: package có trên PyPI và các phiên bản
npm view <tên-package> name version repository.url maintainers   # Node
```

Đối chiếu tên, publisher, repository nguồn, số phiên bản và mức phổ biến; pin phiên bản trong `requirements.in`/`package.json`. Ghi lần kiểm vào mục AI usage của PR nếu package do AI đề xuất.

## Job CI mẫu

Thêm job này vào `.github/workflows/app-ci.yml` của fork. Pin action theo SHA như các bước hiện có.

```yaml
  lint-scan:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          fetch-depth: 0
      - name: Changed files
        run: |
          BASE="${{ github.event.pull_request.base.sha || github.event.before }}"
          git diff --name-only --diff-filter=ACMR "$BASE" HEAD > changed.txt || git ls-files > changed.txt
      - name: Ruff (changed Python files)
        run: |
          FILES=$(grep -E '\.py$' changed.txt || true)
          [ -z "$FILES" ] || pipx run --spec ruff==0.16.9 ruff check $FILES
      - name: pip-audit
        run: pipx run --spec pip-audit==2.10.1 pip-audit -r api/requirements.txt
      - name: gitleaks
        run: docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.30.1 git /repo --redact -v
```

ESLint chạy trong job có `npm ci --prefix web`, với danh sách `.ts`/`.tsx` từ `changed.txt` (bỏ tiền tố `web/`). Kiểm lại version công cụ mới nhất trước khi pin; ghi version vào evidence.

## Evidence M1 cần có

- Lệnh đã chạy, version công cụ, SHA commit và kết quả thực tế (link CI run hoặc log).
- Bảng triage finding baseline: sửa, chấp nhận có lý do, hoặc để sau kèm owner.
- Ít nhất một PR có lint/scan chạy trên changed files và đạt.
- PR có review theo [Review Workflow](ai/Review_Workflow.md): `/code-review --comment`, một finding được xác minh độc lập.
- Dòng đầu tiên trong `docs/ai/delivery-log.csv`.
