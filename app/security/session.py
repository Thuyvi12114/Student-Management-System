"""Phiên đăng nhập và quản lý phiên trong bộ nhớ."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models import Role, UserAccount

SESSION_LIFETIME = timedelta(hours=8)


@dataclass(frozen=True)
class Session:
    token: str
    account_id: int
    username: str
    full_name: str
    role: Role
    issued_at: datetime
    expires_at: datetime

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def has_role(self, role: Role) -> bool:
        return self.role is role


class SessionManager:
    """Giữ phiên hiện tại; đăng xuất sẽ hủy token và xóa phiên."""

    def __init__(self) -> None:
        self._active_session: Session | None = None

    def start(self, account: UserAccount) -> Session:
        now = datetime.now()
        session = Session(
            token=uuid.uuid4().hex,
            account_id=account.account_id,
            username=account.username,
            full_name=account.full_name,
            role=account.role,
            issued_at=now,
            expires_at=now + SESSION_LIFETIME,
        )
        self._active_session = session
        return session

    def current(self) -> Session | None:
        session = self._active_session
        if session is None:
            return None
        if session.is_expired():
            self._active_session = None
            return None
        return session

    def is_authenticated(self) -> bool:
        return self.current() is not None

    def end(self) -> None:
        self._active_session = None
