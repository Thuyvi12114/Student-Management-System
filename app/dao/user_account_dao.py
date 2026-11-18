"""Truy cập bảng UserAccounts."""

from __future__ import annotations

from app.dao.base import BaseDAO
from app.models import AccountStatus, AccountSummary, Role, UserAccount

# Tên hiển thị lấy từ hồ sơ liên kết (username = mã SV/GV); Admin không có hồ sơ.
_DISPLAY = (
    "COALESCE(s.full_name, l.full_name, "
    "CASE WHEN u.role = 'Administrator' THEN 'Quản trị viên' ELSE u.username END)"
)
_FROM = (
    "FROM UserAccounts u "
    "LEFT JOIN Students s ON s.account_id = u.account_id "
    "LEFT JOIN Lecturers l ON l.account_id = u.account_id"
)


class UserAccountDAO(BaseDAO):
    def _map(self, row: tuple) -> UserAccount:
        return UserAccount(
            account_id=int(row[0]),
            username=str(row[1]),
            password_hash=str(row[2]),
            role=Role.from_db(row[3]),
            status=AccountStatus.from_db(row[4]),
            full_name=str(row[5]),
        )

    def find_by_username(self, username: str) -> UserAccount | None:
        row = self.one(
            f"SELECT u.account_id, u.username, u.password_hash, u.role, u.status, {_DISPLAY} {_FROM} "
            "WHERE u.username = %s",
            (username,),
            action="tìm tài khoản",
        )
        return self._map(row) if row else None

    def find_by_id(self, account_id: int) -> UserAccount | None:
        row = self.one(
            f"SELECT u.account_id, u.username, u.password_hash, u.role, u.status, {_DISPLAY} {_FROM} "
            "WHERE u.account_id = %s",
            (account_id,),
            action="tìm tài khoản",
        )
        return self._map(row) if row else None

    def list_summaries(self) -> list[AccountSummary]:
        rows = self.query(
            f"SELECT u.account_id, u.username, {_DISPLAY}, u.role, u.status {_FROM} "
            "WHERE u.role <> 'Administrator' ORDER BY u.role DESC, u.username",
            action="tải danh sách tài khoản",
        )
        return [
            AccountSummary(int(r[0]), str(r[1]), str(r[2]), Role.from_db(r[3]), AccountStatus.from_db(r[4]))
            for r in rows
        ]

    def is_active(self, account_id: int) -> bool:
        return self.scalar(
            "SELECT status FROM UserAccounts WHERE account_id = %s", (account_id,), action="kiểm tra tài khoản"
        ) == AccountStatus.ACTIVE.value

    def username_exists(self, username: str, *, conn=None) -> bool:
        return self.one(
            "SELECT 1 FROM UserAccounts WHERE username = %s", (username,), action="kiểm tra tên đăng nhập", conn=conn
        ) is not None

    def insert(self, username: str, password_hash: str, role: Role, *, conn=None) -> int:
        """Tạo tài khoản (luôn Active); trả về account_id. Dùng trong giao dịch tạo hồ sơ."""
        _, new_id = self.execute(
            "INSERT INTO UserAccounts (username, password_hash, role, status) VALUES (%s, %s, %s, 'Active')",
            (username, password_hash, role.value),
            action="tạo tài khoản",
            conn=conn,
        )
        return new_id

    def update_password_hash(self, account_id: int, password_hash: str) -> None:
        self.execute(
            "UPDATE UserAccounts SET password_hash = %s WHERE account_id = %s",
            (password_hash, account_id),
            action="đổi mật khẩu",
        )

    def update_status(self, account_id: int, status: AccountStatus) -> None:
        self.execute(
            "UPDATE UserAccounts SET status = %s WHERE account_id = %s",
            (status.value, account_id),
            action="cập nhật trạng thái tài khoản",
        )

    def delete(self, account_id: int, *, conn=None) -> None:
        self.execute("DELETE FROM UserAccounts WHERE account_id = %s", (account_id,), action="xóa tài khoản", conn=conn)
