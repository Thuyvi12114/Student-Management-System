"""Truy vấn hồ sơ giảng viên để kiểm tra phân công học phần."""

from __future__ import annotations

import contextlib

import mysql.connector

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.db import Database
from app.models import Lecturer, LecturerSearchResult
from app.models import AccountStatus, Role

_SELECT_COLUMNS = """
    SELECT LecturerID, AccountID, LecturerCode, FullName, Gender, DateOfBirth,
           Email, Phone, Department, Degree
    FROM Lecturers
"""
_SELECT_ID_BY_ACCOUNT = "SELECT LecturerID FROM Lecturers WHERE AccountID = %s"
_SELECT_BY_ID = _SELECT_COLUMNS + " WHERE LecturerID = %s"
_SELECT_BY_ACCOUNT = _SELECT_COLUMNS + " WHERE AccountID = %s"
_SELECT_ALL = _SELECT_COLUMNS + " ORDER BY LecturerCode"
_SELECT_BY_CODE = _SELECT_COLUMNS + " WHERE LecturerCode = %s"
_SELECT_BY_EMAIL = _SELECT_COLUMNS + " WHERE Email = %s"
_COUNT_BY_ACCOUNT = "SELECT COUNT(*) FROM Lecturers WHERE AccountID = %s"
_COUNT_BY_LECTURER = "SELECT COUNT(*) FROM Courses WHERE LecturerID = %s"
_COUNT_ALL = "SELECT COUNT(*) FROM Lecturers"
_SELECT_DEPARTMENTS = "SELECT DISTINCT Department FROM Lecturers ORDER BY Department"
_INSERT = """
    INSERT INTO Lecturers (AccountID, LecturerCode, FullName, Gender, DateOfBirth,
                           Email, Phone, Department, Degree)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
_UPDATE = """
    UPDATE Lecturers
    SET LecturerCode = %s, FullName = %s, Gender = %s, DateOfBirth = %s,
        Email = %s, Phone = %s, Department = %s, Degree = %s
    WHERE LecturerID = %s
"""


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

    def find_by_account(self, account_id: int) -> Lecturer | None:
        rows = self._fetch_all(_SELECT_BY_ACCOUNT, (account_id,), "đọc hồ sơ giảng viên theo tài khoản")
        return rows[0] if rows else None

    def find_by_id(self, lecturer_id: int) -> Lecturer | None:
        rows = self._fetch_all(_SELECT_BY_ID, (lecturer_id,), "đọc hồ sơ giảng viên theo mã")
        return rows[0] if rows else None

    def find_by_code(self, lecturer_code: str) -> Lecturer | None:
        rows = self._fetch_all(_SELECT_BY_CODE, (lecturer_code,), "đọc hồ sơ giảng viên theo mã giảng viên")
        return rows[0] if rows else None

    def find_by_email(self, email: str) -> Lecturer | None:
        rows = self._fetch_all(_SELECT_BY_EMAIL, (email,), "đọc hồ sơ giảng viên theo email")
        return rows[0] if rows else None

    def list_all(self) -> list[Lecturer]:
        return self._fetch_all(_SELECT_ALL, (), "đọc danh sách giảng viên")

    def search(
        self,
        keyword: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
        department: str | None = None,
    ) -> LecturerSearchResult:
        safe_page = max(int(page), 1)
        safe_size = max(int(page_size), 1)
        term = (keyword or "").strip()
        conditions: list[str] = []
        params: list[object] = []
        if term:
            pattern = f"%{term}%"
            conditions.append(
                "(LOWER(LecturerCode) LIKE LOWER(%s)"
                " OR LOWER(FullName) LIKE LOWER(%s)"
                " OR LOWER(Department) LIKE LOWER(%s))"
            )
            params.extend((pattern, pattern, pattern))
        selected_department = (department or "").strip()
        if selected_department:
            conditions.append("Department = %s")
            params.append(selected_department)
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        total_count = self._fetch_count(
            "SELECT COUNT(*) FROM Lecturers" + where_clause,
            tuple(params),
            "đếm số giảng viên phù hợp",
        )
        total_pages = (total_count + safe_size - 1) // safe_size if total_count else 0
        safe_page = min(safe_page, total_pages) if total_pages else 1
        sql = _SELECT_COLUMNS + where_clause
        sql += " ORDER BY LecturerCode LIMIT %s OFFSET %s"
        offset = (safe_page - 1) * safe_size
        rows = self._fetch_all(
            sql, tuple(params) + (safe_size, offset), "tìm kiếm giảng viên"
        )
        return LecturerSearchResult(
            items=rows,
            total_count=total_count,
            page=safe_page,
            page_size=safe_size,
            total_pages=total_pages,
        )

    def count_all(self) -> int:
        return self._fetch_count(_COUNT_ALL, (), "đếm số giảng viên")

    def list_departments(self) -> list[str]:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_SELECT_DEPARTMENTS)
                    rows = cursor.fetchall()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đọc được danh sách khoa/bộ môn: {exc}") from exc
        return [str(row[0]) for row in rows]

    def insert(self, account_id: int, lecturer_code: str, full_name: str, gender: str, date_of_birth, email: str, phone: str | None, department: str, degree: str) -> int:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(
                        _INSERT,
                        (
                            account_id,
                            lecturer_code,
                            full_name,
                            gender,
                            date_of_birth,
                            email,
                            phone,
                            department,
                            degree,
                        ),
                    )
                    new_id = int(cursor.lastrowid)
                finally:
                    cursor.close()
        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                raise DuplicateRecordError("Giảng viên hoặc tài khoản đã tồn tại trong hệ thống.") from exc
            raise DataAccessError(f"Không thêm được giảng viên: {exc}") from exc
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không thêm được giảng viên: {exc}") from exc
        return new_id

    def create_with_account(
        self,
        username: str,
        password_hash: str,
        full_name: str,
        lecturer_code: str,
        gender: str,
        date_of_birth,
        email: str,
        phone: str | None,
        department: str,
        degree: str,
    ) -> int:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                """
                INSERT INTO UserAccounts (Username, PasswordHash, FullName, Role, Status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    username,
                    password_hash,
                    full_name,
                    Role.LECTURER.value,
                    AccountStatus.ACTIVE.value,
                ),
            )
            account_id = int(cursor.lastrowid)
            cursor.execute(
                _INSERT,
                (
                    account_id,
                    lecturer_code,
                    full_name,
                    gender,
                    date_of_birth,
                    email,
                    phone,
                    department,
                    degree,
                ),
            )
            lecturer_id = int(cursor.lastrowid)
            connection.commit()
            return lecturer_id
        except mysql.connector.IntegrityError as exc:
            connection.rollback()
            if exc.errno == 1062:
                raise DuplicateRecordError(
                    "Tên đăng nhập, mã giảng viên hoặc email đã tồn tại."
                ) from exc
            raise DataAccessError(f"Không tạo được giảng viên: {exc}") from exc
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không tạo được giảng viên: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def update(self, lecturer_id: int, account_id: int, lecturer_code: str, full_name: str, gender: str, date_of_birth, email: str, phone: str | None, department: str, degree: str) -> None:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "SELECT LecturerID FROM Lecturers WHERE LecturerID = %s AND AccountID = %s FOR UPDATE",
                (lecturer_id, account_id),
            )
            if cursor.fetchone() is None:
                raise DataAccessError("Giảng viên không tồn tại hoặc hồ sơ đã thay đổi.")
            cursor.execute(
                _UPDATE,
                (
                    lecturer_code,
                    full_name,
                    gender,
                    date_of_birth,
                    email,
                    phone,
                    department,
                    degree,
                    lecturer_id,
                ),
            )
            cursor.execute(
                "UPDATE UserAccounts SET FullName = %s, UpdatedAt = CURRENT_TIMESTAMP WHERE AccountID = %s",
                (full_name, account_id),
            )
            connection.commit()
        except DataAccessError:
            connection.rollback()
            raise
        except mysql.connector.IntegrityError as exc:
            connection.rollback()
            if exc.errno == 1062:
                raise DuplicateRecordError(
                    "Mã giảng viên hoặc email đã tồn tại."
                ) from exc
            raise DataAccessError(f"Không cập nhật được giảng viên: {exc}") from exc
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không cập nhật được giảng viên: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def delete_if_unassigned(self, lecturer_id: int) -> bool:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "SELECT AccountID FROM Lecturers WHERE LecturerID = %s FOR UPDATE",
                (lecturer_id,),
            )
            lecturer_row = cursor.fetchone()
            if lecturer_row is None:
                raise DataAccessError("Giảng viên không tồn tại.")
            account_id = int(lecturer_row[0])
            cursor.execute(_COUNT_BY_LECTURER, (lecturer_id,))
            course_row = cursor.fetchone()
            if course_row and int(course_row[0]) > 0:
                connection.rollback()
                return False
            cursor.execute("DELETE FROM UserAccounts WHERE AccountID = %s", (account_id,))
            if cursor.rowcount != 1:
                raise DataAccessError("Không xóa được tài khoản liên kết với giảng viên.")
            connection.commit()
            return True
        except DataAccessError:
            connection.rollback()
            raise
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không xóa được giảng viên: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def count_courses(self, lecturer_id: int) -> int:
        try:
            with contextlib.closing(self._database.connect()) as connection:
                cursor = connection.cursor(prepared=True)
                try:
                    cursor.execute(_COUNT_BY_LECTURER, (lecturer_id,))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không đếm được số môn học của giảng viên: {exc}") from exc
        return int(row[0]) if row and row[0] is not None else 0

    def _fetch_count(
        self, sql: str, params: tuple[object, ...], action: str
    ) -> int:
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

    def _fetch_all(
        self,
        sql: str,
        params: tuple[object, ...],
        action: str,
    ) -> list[Lecturer]:
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
    def _map(row: tuple[object, ...]) -> Lecturer:
        return Lecturer(
            lecturer_id=int(row[0]),
            account_id=int(row[1]),
            lecturer_code=str(row[2]),
            full_name=str(row[3]),
            gender=str(row[4]),
            date_of_birth=row[5],
            email=str(row[6]),
            phone=str(row[7]) if row[7] is not None else None,
            department=str(row[8]),
            degree=str(row[9]),
        )
