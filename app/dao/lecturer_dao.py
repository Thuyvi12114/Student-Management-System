"""Truy cập bảng Lecturers."""

from __future__ import annotations

from app.dao.base import BaseDAO, like_pattern
from app.models import Lecturer, LecturerSearchResult

_COLUMNS = "lecturer_id, account_id, full_name, email, phone_number, department"


def _lecturer(row: tuple) -> Lecturer:
    return Lecturer(str(row[0]), int(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]))


class LecturerDAO(BaseDAO):
    def find_by_id(self, lecturer_id: str, *, conn=None) -> Lecturer | None:
        row = self.one(f"SELECT {_COLUMNS} FROM Lecturers WHERE lecturer_id = %s", (lecturer_id,), action="tìm giảng viên", conn=conn)
        return _lecturer(row) if row else None

    def find_by_account(self, account_id: int) -> Lecturer | None:
        row = self.one(f"SELECT {_COLUMNS} FROM Lecturers WHERE account_id = %s", (account_id,), action="tìm hồ sơ giảng viên")
        return _lecturer(row) if row else None

    def find_id_by_account(self, account_id: int) -> str | None:
        value = self.scalar("SELECT lecturer_id FROM Lecturers WHERE account_id = %s", (account_id,), action="tìm giảng viên")
        return None if value is None else str(value)

    def exists(self, lecturer_id: str, *, conn=None) -> bool:
        return self.one("SELECT 1 FROM Lecturers WHERE lecturer_id = %s", (lecturer_id,), action="kiểm tra mã giảng viên", conn=conn) is not None

    def insert(self, lecturer: Lecturer, *, conn=None) -> None:
        self.execute(
            f"INSERT INTO Lecturers ({_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s)",
            (lecturer.lecturer_id, lecturer.account_id, lecturer.full_name, lecturer.email, lecturer.phone, lecturer.department),
            action="tạo hồ sơ giảng viên",
            conn=conn,
        )

    def update(self, lecturer: Lecturer) -> int:
        count, _ = self.execute(
            "UPDATE Lecturers SET full_name = %s, email = %s, phone_number = %s, department = %s WHERE lecturer_id = %s",
            (lecturer.full_name, lecturer.email, lecturer.phone, lecturer.department, lecturer.lecturer_id),
            action="cập nhật giảng viên",
        )
        return count

    def count_courses(self, lecturer_id: str, *, conn=None) -> int:
        return int(self.scalar("SELECT COUNT(*) FROM Courses WHERE lecturer_id = %s", (lecturer_id,), action="đếm học phần", conn=conn) or 0)

    def delete(self, lecturer_id: str, *, conn=None) -> int:
        count, _ = self.execute("DELETE FROM Lecturers WHERE lecturer_id = %s", (lecturer_id,), action="xóa giảng viên", conn=conn)
        return count

    def search(self, keyword: str | None, *, page: int, page_size: int, department: str | None = None) -> LecturerSearchResult:
        where, params = ["1 = 1"], []
        if keyword and keyword.strip():
            pattern = like_pattern(keyword.strip())
            where.append("(lecturer_id LIKE %s OR full_name LIKE %s OR email LIKE %s)")
            params += [pattern, pattern, pattern]
        if department:
            where.append("department = %s")
            params.append(department)
        clause = " AND ".join(where)
        total = int(self.scalar(f"SELECT COUNT(*) FROM Lecturers WHERE {clause}", params, action="đếm giảng viên") or 0)
        pages = (total + page_size - 1) // page_size
        page = max(1, min(page, pages)) if pages else 1
        rows = self.query(
            f"SELECT {_COLUMNS} FROM Lecturers WHERE {clause} ORDER BY lecturer_id LIMIT %s OFFSET %s",
            [*params, page_size, (page - 1) * page_size],
            action="tìm kiếm giảng viên",
        )
        return LecturerSearchResult([_lecturer(r) for r in rows], total, page, page_size, pages)

    def list_all(self) -> list[Lecturer]:
        return [_lecturer(r) for r in self.query(f"SELECT {_COLUMNS} FROM Lecturers ORDER BY lecturer_id", action="tải giảng viên")]

    def list_departments(self) -> list[str]:
        return [str(r[0]) for r in self.query("SELECT DISTINCT department FROM Lecturers ORDER BY department", action="tải khoa")]

    def count_all(self) -> int:
        return int(self.scalar("SELECT COUNT(*) FROM Lecturers", action="đếm giảng viên") or 0)
