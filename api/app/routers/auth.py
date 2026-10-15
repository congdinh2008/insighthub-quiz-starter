"""Endpoint mẫu của Auth scaffold: đọc người dùng hiện tại từ phiên."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "email_verified": user.email_verified}
