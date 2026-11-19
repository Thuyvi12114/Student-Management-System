"""UC-07 Quản lý tài khoản (Module 2, Nghĩa): xem, khóa/mở khóa, đặt lại mật khẩu."""

from __future__ import annotations

from app.dao.user_account_dao import UserAccountDAO
from app.models import AccountStatus, AccountSummary, Role
from app.security.password_hasher import hash_password
from app.security.password_policy import violations
from app.security.session import Session
from app.service.access import require_role
from app.service.exceptions import ValidationError

_ADMIN_ONLY = "Chỉ quản trị viên mới được quản lý tài khoản."


class AccountService:
    def __init__(self, account_dao: UserAccountDAO) -> None:
        self._account_dao = account_dao

    def list_accounts(self, session: Session) -> list[AccountSummary]:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        return self._account_dao.list_summaries()

    def set_account_status(self, session: Session, account_id: int, status: AccountStatus) -> None:
        """Khóa (Inactive) hoặc mở khóa (Active); không xóa hồ sơ cá nhân liên kết."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        account = self._managed_account(account_id)
        self._account_dao.update_status(account.account_id, status)

    def reset_password(self, session: Session, account_id: int, new_password: str) -> None:
        """AF2: mật khẩu mới phải thỏa chính sách; lưu dạng băm PBKDF2."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        account = self._managed_account(account_id)
        errors = violations(new_password)
        if errors:
            raise ValidationError(" ".join(errors))
        self._account_dao.update_password_hash(account.account_id, hash_password(new_password))

    def _managed_account(self, account_id: int):
        account = self._account_dao.find_by_id(account_id)  # AF1: không tìm thấy
        if account is None:
            raise ValidationError("Tài khoản không tồn tại.")
        if account.role is Role.ADMIN:
            raise ValidationError("Chỉ quản lý tài khoản sinh viên và giảng viên.")
        return account
