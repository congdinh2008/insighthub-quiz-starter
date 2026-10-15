"""Auth scaffold (learner-r1.3): xác định người dùng từ phiên Better Auth.

Better Auth chạy trong Next.js và lưu phiên ở bảng auth_session (migration 004). Trình duyệt
gửi cookie `insighthub.session_token` tới web, web chuyển tiếp cookie sang API. API tra token
trong database mỗi request, nên phiên bị xóa (logout, thu hồi) bị từ chối ngay (LIM-07).

Đây là phần nền. Học viên tự quyết định route nào bắt buộc đăng nhập, kiểm quyền sở hữu
Notebook và tài nguyên (IH-NB-004), chặn tài khoản PendingVerification (IH-AUTH-001-AC01)...
Không bao giờ nhận định danh người dùng từ header hoặc body do client gửi.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from urllib.parse import unquote

from fastapi import Request

from app.core.db import get_conn
from app.core.errors import NotAuthenticated

COOKIE_NAMES = ("__Secure-insighthub.session_token", "insighthub.session_token")


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    name: str
    email_verified: bool


def _session_token(request: Request) -> str | None:
    raw = next((request.cookies.get(name) for name in COOKIE_NAMES if request.cookies.get(name)), None)
    if not raw:
        return None
    value = unquote(raw)
    dot = value.rfind(".")
    if dot < 1:
        return None
    token, signature = value[:dot], value[dot + 1:]
    secret = os.environ.get("BETTER_AUTH_SECRET", "")
    if secret:
        expected = base64.b64encode(hmac.new(secret.encode(), token.encode(), hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(expected, signature):
            return None
    return token


def optional_user(request: Request) -> CurrentUser | None:
    """Người dùng của phiên hợp lệ, hoặc None. Dùng cho endpoint cho phép khách."""
    token = _session_token(request)
    if token is None:
        return None
    with get_conn(read_only=True) as conn:
        row = conn.execute(
            "SELECT u.id::text, u.email, u.name, u.email_verified FROM auth_session s "
            "JOIN auth_user u ON u.id = s.user_id WHERE s.token = %s AND s.expires_at > now()",
            (token,),
        ).fetchone()
    return CurrentUser(*row) if row else None


def current_user(request: Request) -> CurrentUser:
    """Dependency FastAPI: `user: CurrentUser = Depends(current_user)`. Trả 401 khi không có phiên hợp lệ."""
    user = optional_user(request)
    if user is None:
        raise NotAuthenticated()
    return user
