"""Kiểm tra quyền dùng chung cho các service."""

from __future__ import annotations

from app.models import Role
from app.security.session import Session
from app.service.exceptions import AuthorizationError


def require_role(session: Session, role: Role, message: str) -> None:
    if not isinstance(session, Session) or session.is_expired() or session.role is not role:
        raise AuthorizationError(message)
