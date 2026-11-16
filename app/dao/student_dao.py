"""Truy vấn và ghi hồ sơ sinh viên."""

from __future__ import annotations

import contextlib
from datetime import date

import mysql.connector

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.dao.user_account_dao import UserAccountDAO
from app.db import Database
from app.models import (
    AccountStatus,
    DashboardStats,
    LecturerStudent,
    LecturerStudentSearchResult,
    Role,
    StudentOption,
    StudentRecord,
    StudentSearchResult,
)

_SELECT = "SELECT StudentID, StudentCode, FullName, ClassName FROM Students"
_SELECT_ADMIN = """
    SELECT StudentID, AccountID, StudentCode, FullName, Gender, DateOfBirth,
           Email, Phone, ClassName, EnrollmentYear
    FROM Students
"""
_SELECT_LECTURER = "SELECT StudentID, FullName, ClassName FROM Students"
_SELECT_BY_ACCOUNT = _SELECT + " WHERE AccountID = %s"
_SELECT_BY_ID = _SELECT + " WHERE StudentID = %s"
_SELECT_ADMIN_BY_ID = _SELECT_ADMIN + " WHERE StudentID = %s"
_SELECT_ALL = _SELECT + " ORDER BY StudentCode"
_INSERT_STUDENT = """
    INSERT INTO Students (
        AccountID, StudentCode, FullName, Gender, DateOfBirth, Email, Phone,
        ClassName, EnrollmentYear
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
_UPDATE_STUDENT = """
    UPDATE Students
    SET FullName = %s, Gender = %s, DateOfBirth = %s, Email = %s, Phone = %s,
        ClassName = %s, EnrollmentYear = %s
    WHERE StudentID = %s
"""
_COUNT_STUDENTS = "SELECT COUNT(*) FROM Students"
_COUNT_CLASSES = "SELECT COUNT(DISTINCT ClassName) FROM Students"
_SELECT_CLASSES = "SELECT DISTINCT ClassName FROM Students ORDER BY ClassName"
_COUNT_GRADES = "SELECT COUNT(*) FROM Grades WHERE StudentID = %s"
_ADMIN_DASHBOARD = """
    SELECT
        (SELECT COUNT(*) FROM Students),
        (SELECT COUNT(*) FROM Lecturers),
        (SELECT COUNT(*) FROM Courses),
        (SELECT COUNT(DISTINCT ClassName) FROM Students)
"""
_LECTURER_DASHBOARD = "SELECT COUNT(*) FROM Courses WHERE LecturerID = %s"


class StudentDAO:
    def __init__(
        self,
        database: Database,
        user_account_dao: UserAccountDAO | None = None,
    ) -> None:
        self._database = database
        self._user_account_dao = user_account_dao or UserAccountDAO(database)

    def student_code_exists(self, student_code: str) -> bool:
        return (
            self._fetch_one_row(
                "SELECT 1 FROM Students WHERE StudentCode = %s LIMIT 1",
                (student_code,),
                "kiểm tra mã sinh viên",
            )
            is not None
        )

    def email_exists(self, email: str) -> bool:
        return (
            self._fetch_one_row(
                "SELECT 1 FROM Students WHERE Email = %s LIMIT 1",
                (email,),
                "kiểm tra email sinh viên",
            )
            is not None
        )

    def create_with_account(
        self,
        *,
        student_code: str,
        password_hash: str,
        full_name: str,
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        class_name: str,
        enrollment_year: int,
    ) -> StudentRecord:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "SELECT StudentID FROM Students WHERE StudentCode = %s FOR UPDATE",
                (student_code,),
            )
            if cursor.fetchone() is not None:
                raise DuplicateRecordError("Mã sinh viên đã tồn tại.")
            cursor.execute(
                "SELECT AccountID FROM UserAccounts WHERE Username = %s FOR UPDATE",
                (student_code,),
            )
            if cursor.fetchone() is not None:
                raise DuplicateRecordError("Tên đăng nhập đã tồn tại.")

            account_id = self._user_account_dao.insert_with_cursor(
                cursor,
                username=student_code,
                password_hash=password_hash,
                full_name=full_name,
                role=Role.STUDENT,
                status=AccountStatus.ACTIVE,
            )
            cursor.execute(
                _INSERT_STUDENT,
                (
                    account_id,
                    student_code,
                    full_name,
                    gender,
                    date_of_birth,
                    email,
                    phone,
                    class_name,
                    enrollment_year,
                ),
            )
            student_id = int(cursor.lastrowid)
            connection.commit()
        except DuplicateRecordError:
            connection.rollback()
            raise
        except mysql.connector.IntegrityError as exc:
            connection.rollback()
            message = str(exc).lower()
            if "uq_useraccounts_username" in message:
                reason = "Tên đăng nhập đã tồn tại."
            elif "uq_students_email" in message:
                reason = "Email sinh viên đã tồn tại."
            elif "uq_students_code" in message:
                reason = "Mã sinh viên đã tồn tại."
            else:
                reason = "Mã sinh viên, tên đăng nhập hoặc email đã tồn tại."
            raise DuplicateRecordError(reason) from exc
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không tạo được hồ sơ sinh viên: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

        return StudentRecord(
            student_id=student_id,
            account_id=account_id,
            student_code=student_code,
            full_name=full_name,
            gender=gender,
            date_of_birth=date_of_birth,
            email=email,
            phone=phone,
            class_name=class_name,
            enrollment_year=enrollment_year,
        )

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

    def count_all(self) -> int:
        return self._fetch_count(_COUNT_STUDENTS, "đếm tổng số sinh viên")

    def count_classes(self) -> int:
        return self._fetch_count(_COUNT_CLASSES, "đếm số lớp")

    def list_class_names(self) -> list[str]:
        rows = self._fetch_rows(_SELECT_CLASSES, (), "đọc danh sách lớp")
        return [str(row[0]) for row in rows]

    def search_admin(
        self,
        keyword: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
        class_name: str | None = None,
    ) -> StudentSearchResult:
        safe_page = max(int(page), 1)
        safe_size = max(int(page_size), 1)

        keyword_conditions: list[str] = []
        keyword_params: list[object] = []
        term = (keyword or "").strip()
        if term:
            pattern = f"%{term}%"
            keyword_conditions.extend(
                [
                    "LOWER(StudentCode) LIKE LOWER(%s)",
                    "LOWER(FullName) LIKE LOWER(%s)",
                ]
            )
            keyword_params.extend([pattern, pattern])

        conditions: list[str] = []
        params: list[object] = []
        if keyword_conditions:
            conditions.append("(" + " OR ".join(keyword_conditions) + ")")
            params.extend(keyword_params)
        selected_class = (class_name or "").strip()
        if selected_class:
            conditions.append("ClassName = %s")
            params.append(selected_class)

        count_sql = "SELECT COUNT(*) FROM Students"
        if conditions:
            count_sql += " WHERE " + " OR ".join(conditions)

        total_count = self._fetch_count(
            count_sql, "đếm số sinh viên phù hợp", tuple(params)
        )
        total_pages = (total_count + safe_size - 1) // safe_size if total_count else 0
        safe_page = min(safe_page, total_pages) if total_pages else 1

        data_sql = _SELECT_ADMIN
        if conditions:
            data_sql += " WHERE " + " OR ".join(conditions)
        data_sql += " ORDER BY StudentCode LIMIT %s OFFSET %s"
        offset = (safe_page - 1) * safe_size
        rows = self._fetch_rows(data_sql, tuple(params + [safe_size, offset]), "đọc danh sách sinh viên theo bộ lọc")

        return StudentSearchResult(
            items=[self._map_record(row) for row in rows],
            total_count=total_count,
            page=safe_page,
            page_size=safe_size,
            total_pages=total_pages,
        )

    def update_profile(
        self,
        *,
        student_id: int,
        account_id: int,
        full_name: str,
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        class_name: str,
        enrollment_year: int,
    ) -> StudentRecord:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "SELECT StudentID FROM Students WHERE StudentID = %s AND AccountID = %s FOR UPDATE",
                (student_id, account_id),
            )
            if cursor.fetchone() is None:
                raise DataAccessError("Sinh viên không tồn tại hoặc hồ sơ đã thay đổi.")

            cursor.execute(
                _UPDATE_STUDENT,
                (
                    full_name,
                    gender,
                    date_of_birth,
                    email,
                    phone,
                    class_name,
                    enrollment_year,
                    student_id,
                ),
            )
            cursor.execute(
                "UPDATE UserAccounts SET FullName = %s, UpdatedAt = CURRENT_TIMESTAMP "
                "WHERE AccountID = %s",
                (full_name, account_id),
            )
            connection.commit()
        except DataAccessError:
            connection.rollback()
            raise
        except mysql.connector.IntegrityError as exc:
            connection.rollback()
            if exc.errno == 1062:
                raise DuplicateRecordError("Email sinh viên đã tồn tại.") from exc
            raise DataAccessError(f"Không cập nhật được hồ sơ sinh viên: {exc}") from exc
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không cập nhật được hồ sơ sinh viên: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

        record = self.find_admin_record(student_id)
        if record is None:
            raise DataAccessError("Cập nhật thành công nhưng không đọc lại được hồ sơ sinh viên.")
        return record

    def delete_if_without_grades(self, student_id: int) -> bool:
        connection = self._database.connect()
        cursor = None
        try:
            connection.start_transaction()
            cursor = connection.cursor(prepared=True)
            cursor.execute(
                "SELECT AccountID FROM Students WHERE StudentID = %s FOR UPDATE",
                (student_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise DataAccessError("Sinh viên không tồn tại.")

            account_id = int(row[0])
            cursor.execute(_COUNT_GRADES, (student_id,))
            grade_row = cursor.fetchone()
            if grade_row and int(grade_row[0]) > 0:
                connection.rollback()
                return False

            cursor.execute("DELETE FROM UserAccounts WHERE AccountID = %s", (account_id,))
            if cursor.rowcount != 1:
                raise DataAccessError("Không xóa được tài khoản liên kết với sinh viên.")
            connection.commit()
            return True
        except DataAccessError:
            connection.rollback()
            raise
        except mysql.connector.Error as exc:
            connection.rollback()
            raise DataAccessError(f"Không xóa được hồ sơ sinh viên: {exc}") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def search_lecturer(
        self,
        keyword: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> LecturerStudentSearchResult:
        safe_page = max(int(page), 1)
        safe_size = max(int(page_size), 1)
        term = (keyword or "").strip()
        conditions: list[str] = []
        params: list[object] = []
        if term:
            pattern = f"%{term}%"
            conditions = [
                "LOWER(StudentCode) LIKE LOWER(%s)",
                "LOWER(FullName) LIKE LOWER(%s)",
                "LOWER(ClassName) LIKE LOWER(%s)",
            ]
            params = [pattern, pattern, pattern]

        where_clause = " WHERE " + " OR ".join(conditions) if conditions else ""
        total_count = self._fetch_count(
            "SELECT COUNT(*) FROM Students" + where_clause,
            "đếm số sinh viên phù hợp",
            tuple(params),
        )
        total_pages = (total_count + safe_size - 1) // safe_size if total_count else 0
        safe_page = min(safe_page, total_pages) if total_pages else 1
        rows = self._fetch_rows(
            _SELECT_LECTURER
            + where_clause
            + " ORDER BY StudentID LIMIT %s OFFSET %s",
            tuple(params + [safe_size, (safe_page - 1) * safe_size]),
            "đọc danh sách sinh viên dành cho giảng viên",
        )
        return LecturerStudentSearchResult(
            items=[
                LecturerStudent(
                    student_id=int(row[0]),
                    full_name=str(row[1]),
                    class_name=str(row[2]),
                )
                for row in rows
            ],
            total_count=total_count,
            page=safe_page,
            page_size=safe_size,
            total_pages=total_pages,
        )

    def find_admin_record(self, student_id: int) -> StudentRecord | None:
        rows = self._fetch_rows(
            _SELECT_ADMIN_BY_ID,
            (student_id,),
            "đọc đầy đủ hồ sơ sinh viên",
        )
        return self._map_record(rows[0]) if rows else None

    def admin_dashboard_stats(self) -> DashboardStats:
        row = self._fetch_one_row(_ADMIN_DASHBOARD, (), "tổng hợp dashboard quản trị")
        if row is None:
            raise DataAccessError("Không lấy được số liệu dashboard quản trị.")
        return DashboardStats(
            total_students=int(row[0]),
            total_lecturers=int(row[1]),
            total_courses=int(row[2]),
            total_classes=int(row[3]),
        )

    def lecturer_dashboard_stats(self, lecturer_id: int) -> DashboardStats:
        assigned = self._fetch_count(
            _LECTURER_DASHBOARD,
            "đếm số học phần được phân công",
            (lecturer_id,),
        )
        return DashboardStats(assigned_courses=assigned)

    def _fetch_rows(self, sql: str, params: tuple[object, ...], action: str) -> list[tuple[object, ...]]:
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
        return rows

    def _fetch_count(self, sql: str, action: str, params: tuple[object, ...] = ()) -> int:
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

    def _fetch_one_row(
        self,
        sql: str,
        params: tuple[object, ...],
        action: str,
    ) -> tuple[object, ...] | None:
        rows = self._fetch_rows(sql, params, action)
        return rows[0] if rows else None

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

    @staticmethod
    def _map_record(row: tuple[object, ...]) -> StudentRecord:
        return StudentRecord(
            student_id=int(row[0]),
            account_id=int(row[1]),
            student_code=str(row[2]),
            full_name=str(row[3]),
            gender=str(row[4]),
            date_of_birth=row[5],
            email=str(row[6]),
            phone=str(row[7]) if row[7] is not None else None,
            class_name=str(row[8]),
            enrollment_year=int(row[9]),
        )
