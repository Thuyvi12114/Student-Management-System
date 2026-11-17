"""BaseDAO — lớp cơ sở dùng chung cho các DAO (Module accounts-student, Nghĩa)."""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from typing import Any

import mysql.connector

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.db import Database


class BaseDAO:
    """Cung cấp các helper query/execute/transaction để các DAO con kế thừa."""

    def __init__(self, database: Database) -> None:
        self._db = database

    # ------------------------------------------------------------------ read

    def one(self, sql: str, params: tuple = (), *, action: str = "truy vấn", conn=None) -> tuple | None:
        try:
            if conn is not None:
                cur = conn.cursor(prepared=True)
                try:
                    cur.execute(sql, params)
                    return cur.fetchone()
                finally:
                    cur.close()
            with contextlib.closing(self._db.connect()) as c:
                cur = c.cursor(prepared=True)
                try:
                    cur.execute(sql, params)
                    return cur.fetchone()
                finally:
                    cur.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không {action} được: {exc}") from exc

    def query(self, sql: str, params: tuple = (), *, action: str = "truy vấn", conn=None) -> list[tuple]:
        try:
            if conn is not None:
                cur = conn.cursor(prepared=True)
                try:
                    cur.execute(sql, params)
                    return cur.fetchall()
                finally:
                    cur.close()
            with contextlib.closing(self._db.connect()) as c:
                cur = c.cursor(prepared=True)
                try:
                    cur.execute(sql, params)
                    return cur.fetchall()
                finally:
                    cur.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không {action} được: {exc}") from exc

    def scalar(self, sql: str, params: tuple = (), *, action: str = "truy vấn", conn=None) -> Any:
        row = self.one(sql, params, action=action, conn=conn)
        return row[0] if row else None

    # ------------------------------------------------------------------ write

    def execute(self, sql: str, params: tuple = (), *, action: str = "thực thi", conn=None) -> tuple[int, int]:
        """Trả về (rowcount, lastrowid)."""
        try:
            if conn is not None:
                cur = conn.cursor(prepared=True)
                try:
                    cur.execute(sql, params)
                    return cur.rowcount, (cur.lastrowid or 0)
                finally:
                    cur.close()
            with contextlib.closing(self._db.connect()) as c:
                cur = c.cursor(prepared=True)
                try:
                    cur.execute(sql, params)
                    rowcount = cur.rowcount
                    lastrowid = cur.lastrowid or 0
                finally:
                    cur.close()
                c.commit()
            return rowcount, lastrowid
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                raise DuplicateRecordError(f"Dữ liệu trùng khi {action}.") from exc
            raise DataAccessError(f"Không {action} được: {exc}") from exc
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không {action} được: {exc}") from exc

    # ------------------------------------------------------------------ transaction

    @contextmanager
    def transaction(self, label: str = "giao dịch"):
        """Context manager mở một kết nối autocommit=False, commit khi thoát hoặc rollback khi lỗi."""
        try:
            conn = self._db.connect()
            conn.autocommit = False
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không mở kết nối cho {label}: {exc}") from exc
        try:
            yield conn
            conn.commit()
        except (DataAccessError, DuplicateRecordError):
            conn.rollback()
            raise
        except mysql.connector.IntegrityError as exc:
            conn.rollback()
            if exc.errno == 1062:
                raise DuplicateRecordError(f"Dữ liệu trùng trong {label}.") from exc
            raise DataAccessError(f"Lỗi toàn vẹn dữ liệu trong {label}: {exc}") from exc
        except mysql.connector.Error as exc:
            conn.rollback()
            raise DataAccessError(f"Lỗi MySQL trong {label}: {exc}") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
