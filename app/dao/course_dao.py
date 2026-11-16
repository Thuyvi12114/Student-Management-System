"""Truy vấn học phần kèm giảng viên phụ trách."""

from __future__ import annotations

import contextlib

import mysql.connector

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.db import Database
from app.models import Course, CourseOption, CourseSearchResult

_SELECT = """
    SELECT c.CourseID, c.CourseCode, c.CourseName, c.Credits, c.Semester,
           c.AcademicYear, c.LecturerID, l.FullName
    FROM Courses c
    LEFT JOIN Lecturers l ON l.LecturerID = c.LecturerID
"""
_SELECT_ALL = _SELECT + " ORDER BY c.Semester, c.CourseCode"
_SELECT_BY_LECTURER = _SELECT + " WHERE c.LecturerID = %s ORDER BY c.Semester, c.CourseCode"
_SELECT_BY_ID = _SELECT + " WHERE c.CourseID = %s"
_SELECT_BY_ID_FOR_LECTURER = (
    _SELECT + " WHERE c.CourseID = %s AND c.LecturerID = %s"
)
_SELECT_BY_CODE = "SELECT CourseID, CourseCode, CourseName, Credits, LecturerID, Semester, AcademicYear FROM Courses WHERE CourseCode = %s"
_SELECT_BY_ID_FULL = "SELECT CourseID, CourseCode, CourseName, Credits, LecturerID, Semester, AcademicYear FROM Courses WHERE CourseID = %s"
_COUNT_ALL = "SELECT COUNT(*) FROM Courses"
_INSERT = """
    INSERT INTO Courses (CourseCode, CourseName, Credits, LecturerID, Semester, AcademicYear)
    VALUES (%s, %s, %s, %s, %s, %s)
"""
_UPDATE = """
    UPDATE Courses
    SET CourseCode = %s, CourseName = %s, Credits = %s, LecturerID = %s, Semester = %s, AcademicYear = %s
    WHERE CourseID = %s
"""
_DELETE = "DELETE FROM Courses WHERE CourseID = %s"
_COUNT_GRADES = "SELECT COUNT(*) FROM Grades WHERE CourseID = %s"


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

    def find_by_id_for_lecturer(
        self, course_id: int, lecturer_id: int
    ) -> CourseOption | None:
        rows = self._fetch_all(
            _SELECT_BY_ID_FOR_LECTURER,
            (course_id, lecturer_id),
            "đọc học phần được phân công",
        )
        return rows[0] if rows else None

    def find_full_by_id(self, course_id: int) -> Course | None:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_BY_ID_FULL, (course_id,))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đọc được học phần: {exc}") from exc
        if row is None:
            return None
        return Course(
            course_id=int(row[0]),
            course_code=str(row[1]),
            course_name=str(row[2]),
            credits=int(row[3]),
            lecturer_id=int(row[4]) if row[4] is not None else None,
            semester=str(row[5]),
            academic_year=str(row[6]),
        )

    def find_by_code(self, course_code: str) -> CourseOption | None:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_BY_CODE, (course_code,))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đọc được học phần theo mã: {exc}") from exc
        if row is None:
            return None
        return CourseOption(
            course_id=int(row[0]),
            course_code=str(row[1]),
            course_name=str(row[2]),
            credits=int(row[3]),
            semester=str(row[5]),
            academic_year=str(row[6]),
            lecturer_id=int(row[4]) if row[4] is not None else None,
            lecturer_name=None,
        )

    def search(
        self,
        keyword: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
        lecturer_id: int | None = None,
        semester: str | None = None,
    ) -> CourseSearchResult:
        safe_page = max(int(page), 1)
        safe_size = max(int(page_size), 1)
        term = (keyword or "").strip()
        conditions: list[str] = []
        params: list[object] = []
        if lecturer_id is not None:
            conditions.append("c.LecturerID = %s")
            params.append(lecturer_id)
        if semester:
            conditions.append("c.Semester = %s")
            params.append(semester)
        if term:
            pattern = f"%{term}%"
            conditions.append(
                "(LOWER(c.CourseCode) LIKE LOWER(%s)"
                " OR LOWER(c.CourseName) LIKE LOWER(%s)"
                " OR LOWER(l.FullName) LIKE LOWER(%s))"
            )
            params.extend((pattern, pattern, pattern))
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        count_sql = (
            "SELECT COUNT(*) FROM Courses c "
            "LEFT JOIN Lecturers l ON l.LecturerID = c.LecturerID"
            + where_clause
        )
        total_count = self._fetch_count(
            count_sql, tuple(params), "đếm số học phần phù hợp"
        )
        total_pages = (total_count + safe_size - 1) // safe_size if total_count else 0
        safe_page = min(safe_page, total_pages) if total_pages else 1
        sql = _SELECT + where_clause
        sql += " ORDER BY c.Semester, c.CourseCode LIMIT %s OFFSET %s"
        offset = (safe_page - 1) * safe_size
        items = self._fetch_all(
            sql, tuple(params) + (safe_size, offset), "tìm kiếm học phần"
        )
        return CourseSearchResult(
            items=items,
            total_count=total_count,
            page=safe_page,
            page_size=safe_size,
            total_pages=total_pages,
        )

    def count_all(self) -> int:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_COUNT_ALL)
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đếm được tổng số học phần: {exc}") from exc
        return int(row[0]) if row and row[0] is not None else 0

    def count_grade_rows(self, course_id: int) -> int:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_COUNT_GRADES, (course_id,))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không kiểm tra được điểm của học phần: {exc}") from exc
        return int(row[0]) if row and row[0] is not None else 0

    def _fetch_count(self, sql: str, params: tuple[object, ...], action: str) -> int:
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
        return int(row[0]) if row and row[0] is not None else 0

    def insert(
        self,
        course_code: str,
        course_name: str,
        credits: int,
        lecturer_id: int | None,
        semester: str,
        academic_year: str,
    ) -> int:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(
                        _INSERT,
                        (course_code, course_name, credits, lecturer_id, semester, academic_year),
                    )
                    new_id = int(cursor.lastrowid)
                finally:
                    cursor.close()
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                raise DuplicateRecordError("Mã học phần đã tồn tại.") from exc
            raise DataAccessError(f"Không thêm được học phần: {exc}") from exc
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không thêm được học phần: {exc}") from exc
        return new_id

    def update(
        self,
        course_id: int,
        course_code: str,
        course_name: str,
        credits: int,
        lecturer_id: int | None,
        semester: str,
        academic_year: str,
    ) -> None:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "SELECT CourseID FROM Courses WHERE CourseID = %s FOR UPDATE",
                (course_id,),
            )
            if cursor.fetchone() is None:
                raise DataAccessError("Học phần không tồn tại.")
            cursor.execute(
                _UPDATE,
                (
                    course_code,
                    course_name,
                    credits,
                    lecturer_id,
                    semester,
                    academic_year,
                    course_id,
                ),
            )
            connection.commit()
        except DataAccessError:
            connection.rollback()
            raise
        except mysql.connector.IntegrityError as exc:
            connection.rollback()
            if exc.errno == 1062:
                raise DuplicateRecordError("Mã học phần đã tồn tại.") from exc
            raise DataAccessError(f"Không cập nhật được học phần: {exc}") from exc
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không cập nhật được học phần: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def delete_if_without_grades(self, course_id: int) -> bool:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "SELECT CourseID FROM Courses WHERE CourseID = %s FOR UPDATE",
                (course_id,),
            )
            if cursor.fetchone() is None:
                raise DataAccessError("Học phần không tồn tại.")
            cursor.execute(_COUNT_GRADES, (course_id,))
            grade_row = cursor.fetchone()
            if grade_row and int(grade_row[0]) > 0:
                connection.rollback()
                return False
            cursor.execute(_DELETE, (course_id,))
            if cursor.rowcount != 1:
                raise DataAccessError("Không xóa được học phần.")
            connection.commit()
            return True
        except DataAccessError:
            connection.rollback()
            raise
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không xóa được học phần: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

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
