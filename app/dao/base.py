"""Tiện ích dùng chung cho DAO: mở kết nối, chạy truy vấn có tham số, dịch lỗi MySQL."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Sequence
from typing import Any

import mysql.connector
from mysql.connector import errorcode

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.db import Database


def like_pattern(keyword: str) -> str:
    """Mẫu LIKE khớp một phần; escape % _ \\ để người dùng không phá truy vấn."""
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def translate(exc: mysql.connector.Error, action: str) -> DataAccessError:
    code = getattr(exc, "errno", None)
    if code == errorcode.ER_DUP_ENTRY:
        return DuplicateRecordError("Dữ liệu bị trùng với bản ghi đã có.")
    if code in (errorcode.ER_ROW_IS_REFERENCED, errorcode.ER_ROW_IS_REFERENCED_2):
        return DataAccessError("Không thể xóa vì còn dữ liệu liên quan đang tham chiếu.")
    if code in (errorcode.ER_NO_REFERENCED_ROW, errorcode.ER_NO_REFERENCED_ROW_2):
        return DataAccessError("Dữ liệu tham chiếu không tồn tại.")
    return DataAccessError(f"Không thể {action}: {exc}")


class BaseDAO:
    def __init__(self, database: Database) -> None:
        self._database = database

    def query(self, sql: str, params: Sequence[Any] = (), *, action: str = "đọc dữ liệu", conn=None) -> list[tuple]:
        try:
            if conn is not None:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, tuple(params))
                    return cursor.fetchall()
                finally:
                    cursor.close()
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute(sql, tuple(params))
                    return cursor.fetchall()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise translate(exc, action) from exc

    def one(self, sql: str, params: Sequence[Any] = (), *, action: str = "đọc dữ liệu", conn=None) -> tuple | None:
        rows = self.query(sql, params, action=action, conn=conn)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: Sequence[Any] = (), *, action: str = "đọc dữ liệu", conn=None) -> Any:
        row = self.one(sql, params, action=action, conn=conn)
        return row[0] if row else None

    def execute(self, sql: str, params: Sequence[Any] = (), *, action: str = "ghi dữ liệu", conn=None) -> tuple[int, int]:
        """Trả về (rowcount, lastrowid)."""
        try:
            if conn is not None:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, tuple(params))
                    return cursor.rowcount, cursor.lastrowid or 0
                finally:
                    cursor.close()
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute(sql, tuple(params))
                    return cursor.rowcount, cursor.lastrowid or 0
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise translate(exc, action) from exc

    @contextlib.contextmanager
    def transaction(self, action: str = "ghi dữ liệu") -> Iterator[Any]:
        """Giao dịch: commit khi thành công, rollback toàn bộ khi có lỗi (UC-09 AF4, UC-11 AF4)."""
        try:
            connection = self._database.connect()
        except DataAccessError:
            raise
        try:
            connection.start_transaction()
            yield connection
            connection.commit()
        except mysql.connector.Error as exc:
            with contextlib.suppress(mysql.connector.Error):
                connection.rollback()
            raise translate(exc, action) from exc
        except BaseException:
            with contextlib.suppress(mysql.connector.Error):
                connection.rollback()
            raise
        finally:
            connection.close()
