"""Nghiệp vụ xác thực và tài khoản: đăng nhập, đăng xuất, đổi mật khẩu."""

from __future__ import annotations

from app.dao.user_account_dao import UserAccountDAO
from app.security.password_hasher import hash_password, verify_password
from app.security.password_policy import violations
from app.security.session import Session, SessionManager
from app.service.exceptions import AuthError, ValidationError

_INVALID_CREDENTIALS = "Tên đăng nhập hoặc mật khẩu không đúng."
_INACTIVE_ACCOUNT = (
    "Tài khoản đang ở trạng thái Inactive. "
    "Vui lòng liên hệ quản trị viên để được mở khóa."
)


class AuthService:
    """Xác thực người dùng và quản lý phiên đăng nhập."""

    def __init__(self, account_dao: UserAccountDAO, session_manager: SessionManager) -> None:
        self._account_dao = account_dao
        self._session_manager = session_manager

    def login(self, username: str, password: str) -> Session:
        normalized_username = (username or "").strip()
        if not normalized_username or not password:
            raise ValidationError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")

        account = self._account_dao.find_by_username(normalized_username)
        if account is None:
            raise AuthError(_INVALID_CREDENTIALS)
        if not account.is_active:
            raise AuthError(_INACTIVE_ACCOUNT)
        if not verify_password(password, account.password_hash):
            raise AuthError(_INVALID_CREDENTIALS)

        return self._session_manager.start(account)

    def require_active_session(self) -> Session:
        """Trả về phiên hiện tại sau khi kiểm tra lại trạng thái tài khoản."""
        session = self._session_manager.current()
        if session is None:
            raise AuthError(
                "Phiên đăng nhập không tồn tại hoặc đã hết hạn. Vui lòng đăng nhập lại."
            )

        account = self._account_dao.find_by_id(session.account_id)
        if account is None:
            raise AuthError("Tài khoản của phiên đăng nhập không còn tồn tại.")
        if not account.is_active:
            self._session_manager.end()
            raise AuthError(_INACTIVE_ACCOUNT)
        return session

    def logout(self) -> None:
        """Đăng xuất: hủy phiên hiện tại."""
        self._session_manager.end()

    def change_password(self, current_password: str, new_password: str, confirm_password: str) -> None:
        """Đổi mật khẩu của tài khoản đang đăng nhập."""
        session = self.require_active_session()

        if not current_password:
            raise ValidationError("Vui lòng nhập mật khẩu hiện tại.")
        errors = violations(new_password)
        if errors:
            raise ValidationError(" ".join(errors))
        if new_password != confirm_password:
            raise ValidationError("Xác nhận mật khẩu mới không khớp.")

        account = self._account_dao.find_by_id(session.account_id)
        if account is None:
            raise AuthError("Không tìm thấy tài khoản của phiên hiện tại.")
        if not verify_password(current_password, account.password_hash):
            raise AuthError("Mật khẩu hiện tại không đúng.")
        if verify_password(new_password, account.password_hash):
            raise ValidationError("Mật khẩu mới phải khác mật khẩu hiện tại.")

        self._account_dao.update_password_hash(account.account_id, hash_password(new_password))
