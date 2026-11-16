"""Admin account status operations."""

from __future__ import annotations

from app.dao.user_account_dao import UserAccountDAO
from app.models import AccountStatus, AccountSummary, Role
from app.security.session import Session
from app.service.exceptions import AuthorizationError, ValidationError


class AccountService:
    def __init__(self, account_dao: UserAccountDAO) -> None:
        self._account_dao = account_dao

    def list_accounts(self, session: Session) -> list[AccountSummary]:
        self._require_admin(session)
        return self._account_dao.list_summaries()

    def set_account_status(
        self,
        session: Session,
        account_id: int,
        status: AccountStatus,
    ) -> None:
        self._require_admin(session)
        if account_id == session.account_id and status is AccountStatus.INACTIVE:
            raise ValidationError("Không thể khóa tài khoản đang đăng nhập.")
        if self._account_dao.find_by_id(account_id) is None:
            raise ValidationError("Tài khoản không tồn tại.")
        self._account_dao.update_status(account_id, status)

    @staticmethod
    def _require_admin(session: Session) -> None:
        if session.role is not Role.ADMIN or session.is_expired():
            raise AuthorizationError("Chỉ quản trị viên mới được quản lý trạng thái tài khoản.")
