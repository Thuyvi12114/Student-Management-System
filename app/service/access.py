"""Tiện ích kiểm tra quyền dùng chung cho các service."""

from __future__ import annotations

from app.models import Role
from app.security.session import Session
from app.service.exceptions import AuthorizationError


def require_role(session: Session, role: Role, message: str = "Bạn không có quyền thực hiện thao tác này.") -> None:
    """Ném AuthorizationError nếu session không có đúng vai trò."""
    if session.role is not role:
        raise AuthorizationError(message)
