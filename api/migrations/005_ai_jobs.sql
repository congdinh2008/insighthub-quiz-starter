-- AI Job scaffold (learner-r1.3, ADR-004): cơ chế dùng chung cho hỏi đáp và công cụ AI.
-- Chỉ chứa cơ chế (idempotency theo người dùng, LIM-10, LIM-11, publish fence, usage), không chứa nghiệp vụ:
-- không có bảng Output, Quiz attempt, prompt hay schema đầu ra. Xem docs/AI_Job_Framework.md.
CREATE TABLE IF NOT EXISTS ai_jobs (
    id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    -- Người dùng lấy từ phiên (app/core/auth.py), không nhận từ client (IH-DATA-001-AC04).
    user_id uuid NOT NULL REFERENCES auth_user (id) ON DELETE CASCADE,
    -- Chưa có khóa ngoại: học viên thêm FK tới bảng Notebook của mình bằng migration forward.
    notebook_id uuid,
    -- Loại tác vụ. Starter dùng chat, summary, quiz; học viên thêm loại khác mà không cần migration.
    job_type text NOT NULL CHECK (job_type ~ '^[a-z][a-z0-9_]{1,31}$'),
    -- NULL sau khi key hết hạn (LIM-12) để key được dùng lại; job và kết quả vẫn giữ nguyên (mục 3.3.2).
    idempotency_key text CHECK (idempotency_key IS NULL OR length(idempotency_key) BETWEEN 1 AND 128),
    request_fingerprint text NOT NULL,
    -- Snapshot đầu vào đã chuẩn hóa của lần tiếp nhận đầu tiên (mục 3.3.2).
    input_snapshot jsonb NOT NULL,
    status text NOT NULL DEFAULT 'Processing'
        CHECK (status IN ('Processing', 'Succeeded', 'NoEvidence', 'Failed')),
    error_code text,
    accepted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    deadline_at timestamptz NOT NULL,
    finished_at timestamptz,
    -- Con trỏ tới bản ghi kết quả do học viên tạo (ví dụ Output id).
    result_ref text,
    -- Mỗi phần tử là một lần gọi model: provider, model, token, latency, finish_reason, chi phí ước tính (IH-AI-005-AC02).
    usage jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(usage) = 'array'),
    -- Thử lại sau thất bại tạo job mới liên kết với job cũ (BR-10).
    retry_of uuid REFERENCES ai_jobs (id),
    idempotency_expires_at timestamptz NOT NULL,
    CONSTRAINT ai_jobs_deadline_after_accept CHECK (deadline_at > accepted_at),
    CONSTRAINT ai_jobs_terminal_has_finish CHECK ((status = 'Processing') = (finished_at IS NULL)),
    CONSTRAINT ai_jobs_failed_has_code CHECK (status <> 'Failed' OR error_code IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS ai_jobs_user_type_key
    ON ai_jobs (user_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL;
-- Đếm cửa sổ 60 giây và tìm job đang chạy theo người dùng (LIM-10).
CREATE INDEX IF NOT EXISTS ai_jobs_user_accepted ON ai_jobs (user_id, accepted_at DESC);
CREATE INDEX IF NOT EXISTS ai_jobs_processing ON ai_jobs (deadline_at) WHERE status = 'Processing';
CREATE INDEX IF NOT EXISTS ai_jobs_retry_of ON ai_jobs (retry_of) WHERE retry_of IS NOT NULL;
