"""Truy vấn hồ sơ giảng viên để kiểm tra phân công học phần."""

from __future__ import annotations

import contextlib

import mysql.connector

from app.dao.errors import DataAccessError
from app.db import Database

_SELECT_ID_BY_ACCOUNT = "SELECT LecturerID FROM Lecturers WHERE AccountID = %s"


class LecturerDAO:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_id_by_account(self, account_id: int) -> int | None:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_ID_BY_ACCOUNT, (account_id,))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đọc được hồ sơ giảng viên: {exc}") from exc
        return int(row[0]) if row else None
