"""Truy cập bảng UserAccounts với prepared statement (chống SQL Injection)."""

from __future__ import annotations

import contextlib
from datetime import datetime

import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared

from app.dao.errors import DataAccessError
from app.db import Database
from app.models import AccountStatus, AccountSummary, Role, UserAccount

_SELECT_COLUMNS = """
    SELECT AccountID, Username, PasswordHash, FullName, Role, Status, LastLoginAt, CreatedAt
    FROM UserAccounts
"""
_SELECT_BY_USERNAME = _SELECT_COLUMNS + " WHERE Username = %s"
_SELECT_BY_ID = _SELECT_COLUMNS + " WHERE AccountID = %s"
_SELECT_SUMMARIES = """
    SELECT AccountID, Username, FullName, Role, Status
    FROM UserAccounts
    ORDER BY Role, Username
"""
_SELECT_STATUS_BY_ID = "SELECT Status FROM UserAccounts WHERE AccountID = %s"
_INSERT = """
    INSERT INTO UserAccounts (Username, PasswordHash, FullName, Role, Status)
    VALUES (%s, %s, %s, %s, %s)
"""

_UPDATE_PASSWORD = """
    UPDATE UserAccounts
    SET PasswordHash = %s, UpdatedAt = CURRENT_TIMESTAMP
    WHERE AccountID = %s
"""
_UPDATE_LAST_LOGIN = """
    UPDATE UserAccounts
    SET LastLoginAt = %s
    WHERE AccountID = %s
"""
_UPDATE_STATUS = """
    UPDATE UserAccounts
    SET Status = %s, UpdatedAt = CURRENT_TIMESTAMP
    WHERE AccountID = %s
"""


class UserAccountDAO:
    """DAO cho bảng UserAccounts.

    Mọi câu lệnh dùng ``cursor(prepared=True)`` cùng placeholder ``%s``;
    không nối chuỗi đầu vào của người dùng vào SQL.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    def find_by_username(self, username: str) -> UserAccount | None:
        return self._find_one(_SELECT_BY_USERNAME, (username,), "đọc tài khoản theo tên đăng nhập")

    def find_by_id(self, account_id: int) -> UserAccount | None:
        return self._find_one(_SELECT_BY_ID, (account_id,), "đọc tài khoản theo mã")

    def list_summaries(self) -> list[AccountSummary]:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_SUMMARIES)
                    rows = cursor.fetchall()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đọc được danh sách tài khoản: {exc}") from exc
        return [
            AccountSummary(
                account_id=int(row[0]),
                username=str(row[1]),
                full_name=str(row[2]),
                role=Role.from_db(str(row[3])),
                status=AccountStatus.from_db(str(row[4])),
            )
            for row in rows
        ]

    def is_active(self, account_id: int) -> bool:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_STATUS_BY_ID, (account_id,))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không kiểm tra được trạng thái tài khoản: {exc}") from exc
        return bool(row and str(row[0]).upper() == AccountStatus.ACTIVE.value)

    def username_exists(self, username: str) -> bool:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(
                        "SELECT 1 FROM UserAccounts WHERE Username = %s LIMIT 1",
                        (username,),
                    )
                    exists = cursor.fetchone() is not None
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không kiểm tra được tên đăng nhập: {exc}") from exc
        return exists

    @staticmethod
    def insert_with_cursor(
        cursor: MySQLCursorPrepared,
        username: str,
        password_hash: str,
        full_name: str,
        role: Role,
        status: AccountStatus = AccountStatus.ACTIVE,
    ) -> int:
        """Insert into a caller-owned transaction and return the generated AccountID."""
        cursor.execute(
            _INSERT,
            (username, password_hash, full_name, role.value, status.value),
        )
        return int(cursor.lastrowid)

    def create(
        self,
        username: str,
        password_hash: str,
        full_name: str,
        role: Role,
        status: AccountStatus = AccountStatus.ACTIVE,
    ) -> int:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(
                        _INSERT,
                        (username, password_hash, full_name, role.value, status.value),
                    )
                    new_id = int(cursor.lastrowid)
                finally:
                    cursor.close()
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                raise DataAccessError("Tên đăng nhập đã tồn tại trong hệ thống.") from exc
            raise DataAccessError(f"Không thêm được tài khoản: {exc}") from exc
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không thêm được tài khoản: {exc}") from exc
        return new_id

    def update_password_hash(self, account_id: int, password_hash: str) -> None:
        self._execute(
            _UPDATE_PASSWORD,
            (password_hash, account_id),
            "cập nhật mật khẩu",
            require_row=True,
        )

    def update_last_login(self, account_id: int, login_time: datetime) -> None:
        self._execute(
            _UPDATE_LAST_LOGIN,
            (login_time.replace(microsecond=0), account_id),
            "ghi nhận thời điểm đăng nhập",
            require_row=False,
        )

    def update_status(self, account_id: int, status: AccountStatus) -> None:
        self._execute(
            _UPDATE_STATUS,
            (status.value, account_id),
            "cập nhật trạng thái tài khoản",
            require_row=True,
        )

    def _find_one(self, sql: str, params: tuple[object, ...], action: str) -> UserAccount | None:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(sql, params)
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không {action} được: {exc}") from exc
        return self._map(row) if row else None

    def _execute(
        self,
        sql: str,
        params: tuple[object, ...],
        action: str,
        *,
        require_row: bool,
    ) -> None:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(sql, params)
                    affected = cursor.rowcount
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không {action} được: {exc}") from exc
        if require_row and affected != 1:
            raise DataAccessError(f"Thao tác {action} ảnh hưởng {affected} dòng, mong đợi 1.")

    @staticmethod
    def _map(row: tuple[object, ...]) -> UserAccount:
        return UserAccount(
            account_id=int(row[0]),
            username=str(row[1]),
            password_hash=str(row[2]),
            full_name=str(row[3]),
            role=Role.from_db(str(row[4])),
            status=AccountStatus.from_db(str(row[5])),
            last_login_at=row[6] if isinstance(row[6], datetime) else None,
            created_at=row[7] if isinstance(row[7], datetime) else None,
        )
