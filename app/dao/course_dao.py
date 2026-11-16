"""Truy vấn học phần kèm giảng viên phụ trách."""

from __future__ import annotations

import contextlib

import mysql.connector

from app.dao.errors import DataAccessError
from app.db import Database
from app.models import CourseOption

_SELECT = """
    SELECT c.CourseID, c.CourseCode, c.CourseName, c.Credits, c.Semester,
           c.AcademicYear, c.LecturerID, l.FullName
    FROM Courses c
    LEFT JOIN Lecturers l ON l.LecturerID = c.LecturerID
"""
_SELECT_ALL = _SELECT + " ORDER BY c.Semester, c.CourseCode"
_SELECT_BY_LECTURER = _SELECT + " WHERE c.LecturerID = %s ORDER BY c.Semester, c.CourseCode"
_SELECT_BY_ID = _SELECT + " WHERE c.CourseID = %s"


class CourseDAO:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_all(self) -> list[CourseOption]:
        return self._fetch_all(_SELECT_ALL, (), "đọc danh sách học phần")

    def list_by_lecturer(self, lecturer_id: int) -> list[CourseOption]:
        return self._fetch_all(
            _SELECT_BY_LECTURER,
            (lecturer_id,),
            "đọc học phần được phân công",
        )

    def find_by_id(self, course_id: int) -> CourseOption | None:
        rows = self._fetch_all(_SELECT_BY_ID, (course_id,), "đọc học phần")
        return rows[0] if rows else None

    def _fetch_all(
        self,
        sql: str,
        params: tuple[object, ...],
        action: str,
    ) -> list[CourseOption]:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không {action} được: {exc}") from exc
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: tuple[object, ...]) -> CourseOption:
        return CourseOption(
            course_id=int(row[0]),
            course_code=str(row[1]),
            course_name=str(row[2]),
            credits=int(row[3]),
            semester=str(row[4]),
            academic_year=str(row[5]),
            lecturer_id=int(row[6]) if row[6] is not None else None,
            lecturer_name=str(row[7]) if row[7] is not None else None,
        )
