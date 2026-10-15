"""Đọc trạng thái tác vụ AI sau khi client mất kết nối (AI Job scaffold, SRS mục 3.3.1 "Đọc trạng thái").

Chỉ đọc, không tạo job. Kiểm phiên (Auth scaffold) và policy của loại job; mặc định DenyAllPolicy nên
trả 404 cho tới khi học viên đăng ký policy bằng app.core.ai_jobs.register_policy.
Endpoint tạo job Summary, Quiz là việc của học viên, xem docs/AI_Job_Framework.md. Chat của bài tập R1 giữ
cơ chế operation của Starter (Requirements mục 17.3, mã D8), không tạo job tại đây.
"""

from fastapi import APIRouter, Depends

from app.core.ai_jobs import get_job
from app.core.auth import CurrentUser, current_user

router = APIRouter(prefix="/ai-jobs", tags=["ai-jobs"])


@router.get("/{job_id}")
def read_job(job_id: str, user: CurrentUser = Depends(current_user)) -> dict:
    return get_job(user.id, job_id=job_id).public()


@router.get("/by-key/{job_type}/{idempotency_key}")
def read_job_by_key(job_type: str, idempotency_key: str, user: CurrentUser = Depends(current_user)) -> dict:
    return get_job(user.id, job_type=job_type, idempotency_key=idempotency_key).public()
