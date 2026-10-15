"""Read-only operation reconciliation after a client loses the response."""

from typing import Literal

from fastapi import APIRouter

from app.core.db import get_conn
from app.core.errors import OperationNotFound
from app.core.operations import public_response, recover_expired_operations

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/{operation_type}/{operation_key}")
def get_operation(
    operation_type: Literal["upload", "retry", "chat", "delete"],
    operation_key: str,
):
    recover_expired_operations()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id,status,http_status,response_body,error_code,created_at,updated_at,expires_at "
            "FROM operation_records WHERE operation_type=%s AND operation_key=%s AND expires_at>now()",
            (operation_type, operation_key),
        ).fetchone()
    if row is None:
        raise OperationNotFound()
    return {
        "id": row[0], "operation_type": operation_type, "operation_key": operation_key,
        "status": row[1], "http_status": row[2], "response": public_response(operation_type, row[3]), "error_code": row[4],
        "created_at": row[5].isoformat(), "updated_at": row[6].isoformat(), "expires_at": row[7].isoformat(),
    }
