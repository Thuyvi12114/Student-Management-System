"""Truy vấn và cập nhật bảng Grades với prepared statement."""

from __future__ import annotations

import contextlib
from decimal import Decimal

import mysql.connector

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.db import Database
from app.models import CourseGradeRow, GradeEntry

_SELECT_JOIN = """
    SELECT g.GradeID, g.StudentID, s.StudentCode, s.FullName,
           g.CourseID, c.CourseCode, c.CourseName, c.Credits, c.Semester, c.AcademicYear,
           g.ProcessScore, g.FinalScore, g.Status
    FROM Grades g
    JOIN Students s ON s.StudentID = g.StudentID
    JOIN Courses c ON c.CourseID = g.CourseID
"""
_SELECT_BY_ID = _SELECT_JOIN + " WHERE g.GradeID = %s"
_SELECT_BY_STUDENT_COURSE = _SELECT_JOIN + " WHERE g.StudentID = %s AND g.CourseID = %s"
_SELECT_BY_STUDENT = _SELECT_JOIN + " WHERE g.StudentID = %s ORDER BY c.Semester, c.CourseCode"

_SELECT_ROSTER = """
    SELECT s.StudentID, s.StudentCode, s.FullName, s.ClassName,
           g.GradeID, g.ProcessScore, g.FinalScore, g.Status
    FROM Students s
    LEFT JOIN Grades g ON g.StudentID = s.StudentID AND g.CourseID = %s
    ORDER BY s.StudentCode
"""

_INSERT = """
    INSERT INTO Grades (StudentID, CourseID, ProcessScore, FinalScore, Status)
    VALUES (%s, %s, %s, %s, %s)
"""
_UPDATE = """
    UPDATE Grades
    SET ProcessScore = %s, FinalScore = %s, Status = %s, UpdatedAt = CURRENT_TIMESTAMP
    WHERE GradeID = %s
"""


class GradeDAO:
    def __init__(self, database: Database) -> None:
        self._database = database

    def search(self, student_id: int | None, course_id: int | None) -> list[GradeEntry]:
        conditions: list[str] = []
        params: list[object] = []
        if student_id is not None:
            conditions.append("g.StudentID = %s")
            params.append(student_id)
        if course_id is not None:
            conditions.append("g.CourseID = %s")
            params.append(course_id)

        sql = _SELECT_JOIN
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY s.StudentCode, c.CourseCode"
        return self._fetch_grades(sql, tuple(params), "tra cứu điểm")

    def list_for_student(self, student_id: int) -> list[GradeEntry]:
        return self._fetch_grades(
            _SELECT_BY_STUDENT,
            (student_id,),
            "đọc bảng điểm sinh viên",
        )

    def find_by_student_course(self, student_id: int, course_id: int) -> GradeEntry | None:
        rows = self._fetch_grades(
            _SELECT_BY_STUDENT_COURSE,
            (student_id, course_id),
            "đọc điểm của sinh viên",
        )
        return rows[0] if rows else None

    def find_by_id(self, grade_id: int) -> GradeEntry | None:
        rows = self._fetch_grades(_SELECT_BY_ID, (grade_id,), "đọc điểm")
        return rows[0] if rows else None

    def list_roster(self, course_id: int) -> list[CourseGradeRow]:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_ROSTER, (course_id,))
                    rows = cursor.fetchall()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đọc được danh sách điểm học phần: {exc}") from exc

        return [
            CourseGradeRow(
                student_id=int(row[0]),
                student_code=str(row[1]),
                student_name=str(row[2]),
                class_name=str(row[3]) if row[3] is not None else "",
                grade_id=int(row[4]) if row[4] is not None else None,
                process_score=self._decimal(row[5]),
                final_score=self._decimal(row[6]),
                status=str(row[7]) if row[7] is not None else None,
            )
            for row in rows
        ]

    def insert(
        self,
        student_id: int,
        course_id: int,
        process_score: Decimal | None,
        final_score: Decimal | None,
        status: str,
    ) -> int:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(
                        _INSERT,
                        (student_id, course_id, process_score, final_score, status),
                    )
                    new_id = int(cursor.lastrowid)
                finally:
                    cursor.close()
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                raise DuplicateRecordError(
                    "Sinh viên đã có điểm cho học phần này."
                ) from exc
            raise DataAccessError(f"Không thêm được điểm: {exc}") from exc
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không thêm được điểm: {exc}") from exc
        return new_id

    def update(
        self,
        grade_id: int,
        process_score: Decimal | None,
        final_score: Decimal | None,
        status: str,
    ) -> None:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_UPDATE, (process_score, final_score, status, grade_id))
                    affected = cursor.rowcount
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không cập nhật được điểm: {exc}") from exc
        if affected != 1:
            raise DataAccessError(f"Thao tác cập nhật điểm ảnh hưởng {affected} dòng, mong đợi 1.")

    def _fetch_grades(
        self,
        sql: str,
        params: tuple[object, ...],
        action: str,
    ) -> list[GradeEntry]:
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
        return [self._map_grade(row) for row in rows]

    @staticmethod
    def _map_grade(row: tuple[object, ...]) -> GradeEntry:
        return GradeEntry(
            grade_id=int(row[0]),
            student_id=int(row[1]),
            student_code=str(row[2]),
            student_name=str(row[3]),
            course_id=int(row[4]),
            course_code=str(row[5]),
            course_name=str(row[6]),
            credits=int(row[7]),
            semester=str(row[8]),
            academic_year=str(row[9]),
            process_score=GradeDAO._decimal(row[10]),
            final_score=GradeDAO._decimal(row[11]),
            status=str(row[12]),
        )

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
