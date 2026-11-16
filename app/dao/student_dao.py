"""Truy vấn hồ sơ sinh viên phục vụ tra cứu điểm."""

from __future__ import annotations

import contextlib

import mysql.connector

from app.dao.errors import DataAccessError
from app.db import Database
from app.models import StudentOption

_SELECT = "SELECT StudentID, StudentCode, FullName, ClassName FROM Students"
_SELECT_BY_ACCOUNT = _SELECT + " WHERE AccountID = %s"
_SELECT_BY_ID = _SELECT + " WHERE StudentID = %s"
_SELECT_ALL = _SELECT + " ORDER BY StudentCode"


class StudentDAO:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_by_account_id(self, account_id: int) -> StudentOption | None:
        return self._fetch_one(_SELECT_BY_ACCOUNT, (account_id,), "đọc hồ sơ sinh viên theo tài khoản")

    def find_by_id(self, student_id: int) -> StudentOption | None:
        return self._fetch_one(_SELECT_BY_ID, (student_id,), "đọc hồ sơ sinh viên theo mã")

    def list_all(self) -> list[StudentOption]:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_ALL)
                    rows = cursor.fetchall()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đọc được danh sách sinh viên: {exc}") from exc
        return [self._map(row) for row in rows]

    def _fetch_one(self, sql: str, params: tuple[object, ...], action: str) -> StudentOption | None:
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

    @staticmethod
    def _map(row: tuple[object, ...]) -> StudentOption:
        return StudentOption(
            student_id=int(row[0]),
            student_code=str(row[1]),
            full_name=str(row[2]),
            class_name=str(row[3]),
        )
