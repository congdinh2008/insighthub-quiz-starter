"""AI Job scaffold (learner-r1.3, ADR-004): cơ chế dùng chung cho công cụ AI (Summary, Quiz).

Chat của bài tập R1 giữ `operation_records` của Starter (mã D8); nhánh `chat` (deadline 60 giây) được giữ
cho trường hợp tích hợp sau này.

Starter chỉ cấp **cơ chế**, không chứa nghiệp vụ. Vòng đời một tác vụ trong endpoint của học viên:

    user = current_user(request)                                  # Auth scaffold
    # Học viên: kiểm Notebook thuộc user, chuẩn hóa và kiểm đầu vào nghiệp vụ (IH-AI-002)
    job, replay = accept_job(user_id=user.id, job_type="summary", idempotency_key=key,
                             normalized_input=snapshot, notebook_id=notebook_id)
    if replay:
        return job.public()                                       # gửi lại: không tạo job, không tính lượt
    outcome = run_job(job, executor)                              # executor của học viên gọi model
    job = publish(job, outcome, write_result=save_output)         # fence BR-08, BR-09 bằng policy
    return job.public()

Quy tắc SRS được cơ chế bảo đảm: idempotency theo người dùng trước khi tính lượt (mục 3.3.2), 1 tác vụ
đang chạy và 10 yêu cầu trong 60 giây (LIM-10), deadline tuyệt đối 60 hoặc 120 giây không gia hạn khi retry
hoặc restart (LIM-11), key giữ 24 giờ (LIM-12), chỉ công bố khi còn hạn và policy cho phép (BR-08, BR-09).

Policy mặc định từ chối (DenyAllPolicy): job không đọc lại hay công bố được cho tới khi học viên đăng ký policy
của mình bằng `register_policy`. Chi tiết: docs/AI_Job_Framework.md.
"""

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Protocol

from psycopg.types.json import Jsonb

from app.core.db import get_conn
from app.core.deadline import check_deadline, operation_deadline
from app.core.errors import (
    AiJobNotFound,
    AiJobRunning,
    AiRateLimited,
    DeadlineExceeded,
    IdempotencyConflict,
    PublishBlocked,
    RequestInvalid,
    ServiceError,
)
from app.core.operations import validate_key

logger = logging.getLogger("insighthub.ai_jobs")

# Giới hạn nghiệp vụ của SRS, không phải tham số vận hành: đổi giá trị nghĩa là đổi yêu cầu.
CHAT_TIMEOUT_SECONDS = 60  # LIM-11 hỏi đáp (nhánh dự phòng, xem D8)
TOOL_TIMEOUT_SECONDS = 120  # LIM-11 công cụ AI
MAX_RUNNING_JOBS = 1  # LIM-10
RATE_LIMIT_REQUESTS = 10  # LIM-10
RATE_LIMIT_WINDOW_SECONDS = 60  # LIM-10
IDEMPOTENCY_TTL_HOURS = 24  # LIM-12

JOB_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
TERMINAL_STATUSES = frozenset({"Succeeded", "NoEvidence", "Failed"})
# Trường được phép trong một bản ghi usage. Không có chỗ cho prompt, nội dung nguồn hay body của provider.
USAGE_FIELDS = frozenset({
    "provider", "model", "prompt_version", "attempt", "fallback", "outcome", "input_tokens", "output_tokens",
    "latency_ms", "finish_reason", "estimated_cost_usd", "error_code",
})

_COLUMNS = (
    "id::text, user_id::text, notebook_id::text, job_type, status, error_code, input_snapshot, "
    "accepted_at, deadline_at, finished_at, result_ref, retry_of::text"
)


@dataclass(frozen=True)
class Job:
    id: str
    user_id: str
    notebook_id: str | None
    job_type: str
    status: str
    error_code: str | None
    input_snapshot: dict
    accepted_at: datetime
    deadline_at: datetime
    finished_at: datetime | None
    result_ref: str | None
    retry_of: str | None

    def public(self) -> dict:
        """Trạng thái trả cho chủ sở hữu. Không gồm snapshot và usage; học viên tự thêm phần được phép đọc."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "notebook_id": self.notebook_id,
            "status": self.status,
            "error_code": self.error_code,
            "accepted_at": self.accepted_at.isoformat(),
            "deadline_at": self.deadline_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "result_ref": self.result_ref,
            "retry_of": self.retry_of,
        }


@dataclass(frozen=True)
class JobOutcome:
    """Kết quả executor trả về. `payload` là dữ liệu của học viên, cơ chế không đọc nội dung."""
    status: Literal["Succeeded", "NoEvidence"]
    payload: Any = None


class JobPolicy(Protocol):
    """Học viên hiện thực theo nghiệp vụ. Cả hai hàm chạy trong transaction của cơ chế.

    can_read: người dùng còn quyền đọc job theo trạng thái hiện hành (Notebook còn, chưa bị xóa).
    can_publish: điều kiện công bố còn (nguồn, Notebook, hội thoại đích chưa bị xóa, BR-08, BR-09).
    Để chống race với thao tác xóa, can_publish nên khóa các dòng liên quan (SELECT ... FOR SHARE)
    và thao tác xóa khóa cùng dòng đó (FOR UPDATE).
    """

    def can_read(self, conn, job: Job) -> bool: ...

    def can_publish(self, conn, job: Job) -> bool: ...


class DenyAllPolicy:
    """Mặc định từ chối: chưa có policy của học viên thì không đọc lại và không công bố được."""

    def can_read(self, conn, job: Job) -> bool:
        return False

    def can_publish(self, conn, job: Job) -> bool:
        return False


DENY_ALL = DenyAllPolicy()
_POLICIES: dict[str, JobPolicy] = {}


def register_policy(job_type: str, policy: JobPolicy) -> None:
    """Đăng ký policy cho một loại job, thường gọi khi import router của học viên."""
    _check_job_type(job_type)
    _POLICIES[job_type] = policy


def policy_for(job_type: str) -> JobPolicy:
    return _POLICIES.get(job_type, DENY_ALL)


def timeout_for(job_type: str) -> int:
    return CHAT_TIMEOUT_SECONDS if job_type == "chat" else TOOL_TIMEOUT_SECONDS


def _check_job_type(job_type: str) -> str:
    if not isinstance(job_type, str) or not JOB_TYPE_PATTERN.match(job_type):
        raise RequestInvalid(fields=[{"field": "job_type", "code": "invalid"}])
    return job_type


def normalize_source_ids(ids, *, field: str = "source_ids") -> list:
    """Tập ID nguồn theo mục 3.3.2: từ chối ID lặp, sắp xếp để đổi thứ tự không tạo request khác.
    Số lượng 1-3 nguồn và trạng thái Ready do học viên kiểm theo IH-AI-002."""
    if not isinstance(ids, (list, tuple)) or not ids:
        raise RequestInvalid(fields=[{"field": field, "code": "required"}])
    kinds = {type(item) for item in ids}
    if kinds not in ({int}, {str}) or any(isinstance(item, bool) for item in ids):
        raise RequestInvalid(fields=[{"field": field, "code": "invalid"}])
    if len(set(ids)) != len(ids):
        raise RequestInvalid(fields=[{"field": field, "code": "duplicate"}])
    return sorted(ids)


def job_fingerprint(job_type: str, notebook_id: str | None, normalized_input: dict) -> str:
    """Notebook, loại tác vụ và đầu vào đã chuẩn hóa xác định "cùng dữ liệu" (mục 3.3.2)."""
    canonical = json.dumps(
        {"job_type": job_type, "notebook_id": notebook_id, "input": normalized_input},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _job(row) -> Job:
    return Job(*row)


def _seconds_left(job: Job) -> float:
    return (job.deadline_at - datetime.now(timezone.utc)).total_seconds()


def _expire(conn, user_id: str | None = None) -> None:
    """Job quá deadline chuyển Failed và giải phóng suất chạy (LIM-11). Không bao giờ gia hạn."""
    if user_id is None:
        conn.execute(
            "UPDATE ai_jobs SET status='Failed', error_code='deadline_exceeded', finished_at=clock_timestamp() "
            "WHERE status='Processing' AND deadline_at<=clock_timestamp()"
        )
    else:
        conn.execute(
            "UPDATE ai_jobs SET status='Failed', error_code='deadline_exceeded', finished_at=clock_timestamp() "
            "WHERE user_id=%s AND status='Processing' AND deadline_at<=clock_timestamp()",
            (user_id,),
        )


def recover_expired_jobs() -> None:
    """Dọn toàn bộ job quá hạn. accept_job và get_job đã tự dọn theo người dùng."""
    with operation_deadline(5), get_conn() as conn:
        _expire(conn)


def fail_job(job: Job | str, error_code: str) -> None:
    """Chuyển job đang chạy sang Failed với mã ổn định. Không ghi đè job đã kết thúc."""
    job_id = job.id if isinstance(job, Job) else job
    try:
        with operation_deadline(5), get_conn() as conn:
            conn.execute(
                "UPDATE ai_jobs SET status='Failed', error_code=%s, finished_at=clock_timestamp() "
                "WHERE id=%s AND status='Processing'",
                (error_code, job_id),
            )
    except Exception:
        # Recovery theo deadline sẽ chuyển job sang Failed nếu database tạm thời không ghi được.
        logger.warning("AI job failure persistence deferred: id=%s", job_id)


def accept_job(
    *,
    user_id: str,
    job_type: str,
    idempotency_key: str,
    normalized_input: dict,
    notebook_id: str | None = None,
    retry_of: str | None = None,
    policy: JobPolicy | None = None,
) -> tuple[Job, bool]:
    """Tiếp nhận một tác vụ AI. Trả (job, replay).

    Thứ tự trong một transaction có khóa theo người dùng (mục 3.3.2, LIM-10):
    1. Idempotency: cùng key cùng dữ liệu trả job cũ (replay=True, kiểm can_read), khác dữ liệu báo xung đột.
    2. Tối đa 1 job đang chạy. 3. Tối đa 10 job mới trong 60 giây. 4. Ghi job Processing kèm deadline.
    Request bị từ chối ở bước 2, 3 không được ghi nên không tính lượt.
    """
    _check_job_type(job_type)
    key = validate_key(idempotency_key)
    if not isinstance(normalized_input, dict):
        raise RequestInvalid(fields=[{"field": "input", "code": "invalid"}])
    try:
        fingerprint = job_fingerprint(job_type, notebook_id, normalized_input)
    except (TypeError, ValueError):
        raise RequestInvalid(fields=[{"field": "input", "code": "not_serializable"}]) from None
    seconds = timeout_for(job_type)
    with operation_deadline(5), get_conn() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"insighthub:ai_jobs:user:{user_id}",))
        _expire(conn, user_id)
        # Hết LIM-12 thì nhả key (job và kết quả giữ nguyên) để key có thể dùng cho thao tác mới.
        conn.execute(
            "UPDATE ai_jobs SET idempotency_key=NULL WHERE user_id=%s AND job_type=%s AND idempotency_key=%s "
            "AND idempotency_expires_at<=now()",
            (user_id, job_type, key),
        )
        row = conn.execute(
            f"SELECT {_COLUMNS}, request_fingerprint FROM ai_jobs "
            "WHERE user_id=%s AND job_type=%s AND idempotency_key=%s",
            (user_id, job_type, key),
        ).fetchone()
        if row is not None:
            if row[-1] != fingerprint:
                raise IdempotencyConflict()
            job = _job(row[:-1])
            if not (policy or policy_for(job_type)).can_read(conn, job):
                raise AiJobNotFound()
            return job, True

        running = conn.execute(
            "SELECT GREATEST(1, ceil(extract(epoch FROM deadline_at - clock_timestamp())))::int "
            "FROM ai_jobs WHERE user_id=%s AND status='Processing' ORDER BY deadline_at DESC",
            (user_id,),
        ).fetchall()
        if len(running) >= MAX_RUNNING_JOBS:
            raise AiJobRunning(retry_after_seconds=running[-1][0])

        window = f"{RATE_LIMIT_WINDOW_SECONDS} seconds"
        count = conn.execute(
            "SELECT count(*) FROM ai_jobs WHERE user_id=%s AND accepted_at > clock_timestamp() - %s::interval",
            (user_id, window),
        ).fetchone()[0]
        if count >= RATE_LIMIT_REQUESTS:
            # Chờ tới khi đủ số yêu cầu cũ rời cửa sổ để còn chỗ cho một yêu cầu mới.
            wait = conn.execute(
                "SELECT GREATEST(1, ceil(extract(epoch FROM accepted_at + %s::interval - clock_timestamp())))::int "
                "FROM ai_jobs WHERE user_id=%s AND accepted_at > clock_timestamp() - %s::interval "
                "ORDER BY accepted_at ASC OFFSET %s LIMIT 1",
                (window, user_id, window, count - RATE_LIMIT_REQUESTS),
            ).fetchone()[0]
            raise AiRateLimited(retry_after_seconds=wait)

        if retry_of is not None:
            previous = conn.execute(
                "SELECT 1 FROM ai_jobs WHERE id::text=%s AND user_id=%s AND job_type=%s AND status='Failed'",
                (str(retry_of), user_id, job_type),
            ).fetchone()
            if previous is None:
                raise RequestInvalid(fields=[{"field": "retry_of", "code": "invalid"}])

        row = conn.execute(
            "INSERT INTO ai_jobs(user_id, notebook_id, job_type, idempotency_key, request_fingerprint, input_snapshot, "
            "accepted_at, deadline_at, idempotency_expires_at, retry_of) "
            "VALUES (%s, %s, %s, %s, %s, %s, clock_timestamp(), clock_timestamp() + %s * interval '1 second', "
            f"clock_timestamp() + %s * interval '1 hour', %s) RETURNING {_COLUMNS}",
            (user_id, notebook_id, job_type, key, fingerprint, Jsonb(normalized_input), seconds,
             IDEMPOTENCY_TTL_HOURS, retry_of),
        ).fetchone()
    job = _job(row)
    logger.info("AI job accepted: id=%s type=%s deadline_at=%s", job.id, job.job_type, job.deadline_at.isoformat())
    return job, False


def run_job(job: Job, executor: Callable[[Job], JobOutcome]) -> JobOutcome:
    """Chạy executor của học viên trong deadline còn lại của job (retry nội bộ không gia hạn).
    Lỗi chuyển job sang Failed với mã ổn định rồi ném tiếp để endpoint trả envelope lỗi."""
    seconds = _seconds_left(job)
    if seconds <= 0:
        fail_job(job, DeadlineExceeded.code)
        raise DeadlineExceeded()
    try:
        with operation_deadline(seconds):
            outcome = executor(job)
            check_deadline()
        if not isinstance(outcome, JobOutcome) or outcome.status not in {"Succeeded", "NoEvidence"}:
            raise ServiceError()
        return outcome
    except ServiceError as exc:
        fail_job(job, exc.code)
        raise
    except Exception as exc:
        # Không log nội dung exception: có thể chứa prompt hoặc body của provider.
        logger.warning("AI job executor failed: id=%s error=%s", job.id, type(exc).__name__)
        fail_job(job, ServiceError.code)
        raise ServiceError() from None


def publish(
    job: Job,
    outcome: JobOutcome,
    *,
    write_result: Callable[[Any, Job, JobOutcome], str | None] | None = None,
    policy: JobPolicy | None = None,
) -> Job:
    """Publish fence: khóa dòng job, kiểm còn Processing và còn deadline, gọi policy.can_publish,
    gọi write_result(conn, job, outcome) của học viên rồi chuyển Succeeded hoặc NoEvidence.
    Tất cả trong một transaction: điều kiện sai thì không có kết quả nào được lưu (BR-08, BR-09, LIM-11)."""
    policy = policy or policy_for(job.job_type)
    seconds = _seconds_left(job)
    try:
        if seconds <= 0:
            raise DeadlineExceeded()
        with operation_deadline(seconds), get_conn() as conn:
            row = conn.execute(
                "SELECT status, deadline_at > clock_timestamp() FROM ai_jobs WHERE id=%s FOR UPDATE", (job.id,)
            ).fetchone()
            if row is None or row[0] != "Processing" or not row[1]:
                raise DeadlineExceeded()
            if not policy.can_publish(conn, job):
                raise PublishBlocked()
            result_ref = write_result(conn, job, outcome) if write_result is not None else None
            published = conn.execute(
                f"UPDATE ai_jobs SET status=%s, result_ref=%s, finished_at=clock_timestamp() WHERE id=%s RETURNING {_COLUMNS}",
                (outcome.status, None if result_ref is None else str(result_ref), job.id),
            ).fetchone()
    except ServiceError as exc:
        fail_job(job, exc.code)
        raise
    except Exception as exc:
        logger.warning("AI job publish failed: id=%s error=%s", job.id, type(exc).__name__)
        fail_job(job, ServiceError.code)
        raise ServiceError() from None
    return _job(published)


def get_job(
    user_id: str,
    *,
    job_id: str | None = None,
    job_type: str | None = None,
    idempotency_key: str | None = None,
    policy: JobPolicy | None = None,
) -> Job:
    """Đọc trạng thái job của đúng người dùng theo id hoặc (job_type, key). Không tạo job mới.
    Không tồn tại, của người khác hoặc policy từ chối đều trả cùng AiJobNotFound (mục 3.3.1)."""
    if job_id is not None:
        try:
            uuid.UUID(str(job_id))
        except ValueError:
            raise AiJobNotFound() from None
        where, params = "id=%s::uuid AND user_id=%s", (str(job_id), user_id)
    elif job_type is not None and idempotency_key is not None:
        _check_job_type(job_type)
        where, params = "job_type=%s AND idempotency_key=%s AND idempotency_expires_at>now() AND user_id=%s", (
            job_type, validate_key(idempotency_key), user_id)
    else:
        raise RequestInvalid(fields=[{"field": "job_id", "code": "required"}])
    with operation_deadline(5), get_conn() as conn:
        _expire(conn, user_id)
        row = conn.execute(f"SELECT {_COLUMNS} FROM ai_jobs WHERE {where}", params).fetchone()
        if row is None:
            raise AiJobNotFound()
        job = _job(row)
        if not (policy or policy_for(job.job_type)).can_read(conn, job):
            raise AiJobNotFound()
    return job


def record_usage(job: Job | str, usage: dict) -> None:
    """Ghi một lần gọi model (IH-AI-005-AC02). Chỉ nhận trường trong USAGE_FIELDS với giá trị đơn."""
    unknown = set(usage) - USAGE_FIELDS
    if unknown:
        raise ValueError(f"Trường usage không hỗ trợ: {sorted(unknown)}")
    for name, value in usage.items():
        if not (value is None or isinstance(value, (bool, int, float)) or (isinstance(value, str) and len(value) <= 128)):
            raise ValueError(f"Giá trị usage không hợp lệ: {name}")
    job_id = job.id if isinstance(job, Job) else job
    entry = {**usage, "recorded_at": datetime.now(timezone.utc).isoformat()}
    with get_conn() as conn:
        conn.execute("UPDATE ai_jobs SET usage = usage || jsonb_build_array(%s::jsonb) WHERE id=%s", (Jsonb(entry), job_id))


def job_usage(job: Job | str) -> list[dict]:
    job_id = job.id if isinstance(job, Job) else job
    with get_conn(read_only=True) as conn:
        row = conn.execute("SELECT usage FROM ai_jobs WHERE id=%s", (job_id,)).fetchone()
    return list(row[0]) if row else []
