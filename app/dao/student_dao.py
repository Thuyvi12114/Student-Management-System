"""Truy cập bảng Students (Module 3 - Quản lý sinh viên, Nghĩa)."""

from __future__ import annotations

from app.dao.base import BaseDAO
from app.models import StudentOption, StudentRecord

_COLUMNS = "student_id, account_id, full_name, date_of_birth, gender, email, phone_number, address, class_name"


def _record(row: tuple) -> StudentRecord:
    return StudentRecord(
        student_id=str(row[0]),
        account_id=int(row[1]),
        full_name=str(row[2]),
        date_of_birth=row[3],
        gender=str(row[4]),
        email=str(row[5]),
        phone=str(row[6]),
        address=None if row[7] is None else str(row[7]),
        class_name=str(row[8]),
    )


class StudentDAO(BaseDAO):
    def find_by_id(self, student_id: str, *, conn=None) -> StudentRecord | None:
        row = self.one(f"SELECT {_COLUMNS} FROM Students WHERE student_id = %s", (student_id,), action="tìm sinh viên", conn=conn)
        return _record(row) if row else None

    def find_by_account(self, account_id: int) -> StudentRecord | None:
        row = self.one(f"SELECT {_COLUMNS} FROM Students WHERE account_id = %s", (account_id,), action="tìm hồ sơ sinh viên")
        return _record(row) if row else None

    def exists(self, student_id: str, *, conn=None) -> bool:
        """UC-19: kiểm tra trùng mã sinh viên (không sửa dữ liệu)."""
        return self.one(
            "SELECT 1 FROM Students WHERE student_id = %s", (student_id,), action="kiểm tra mã sinh viên", conn=conn
        ) is not None

    def insert(self, record: StudentRecord, *, conn=None) -> None:
        self.execute(
            f"INSERT INTO Students ({_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                record.student_id, record.account_id, record.full_name, record.date_of_birth, record.gender,
                record.email, record.phone, record.address, record.class_name,
            ),
            action="tạo hồ sơ sinh viên",
            conn=conn,
        )

    def update(self, record: StudentRecord) -> int:
        """UC-10: sửa mọi trường trừ student_id và account_id."""
        count, _ = self.execute(
            "UPDATE Students SET full_name = %s, date_of_birth = %s, gender = %s, email = %s, "
            "phone_number = %s, address = %s, class_name = %s WHERE student_id = %s",
            (
                record.full_name, record.date_of_birth, record.gender, record.email,
                record.phone, record.address, record.class_name, record.student_id,
            ),
            action="cập nhật sinh viên",
        )
        return count

    def update_contact(self, student_id: str, email: str, phone: str, address: str | None) -> int:
        """UC-08: sinh viên chỉ được sửa email, số điện thoại và địa chỉ."""
        count, _ = self.execute(
            "UPDATE Students SET email = %s, phone_number = %s, address = %s WHERE student_id = %s",
            (email, phone, address, student_id),
            action="cập nhật thông tin liên hệ",
        )
        return count

    def count_grades(self, student_id: str, *, conn=None) -> int:
        return int(self.scalar("SELECT COUNT(*) FROM Grades WHERE student_id = %s", (student_id,), action="đếm điểm", conn=conn) or 0)

    def delete(self, student_id: str, *, conn=None) -> int:
        count, _ = self.execute("DELETE FROM Students WHERE student_id = %s", (student_id,), action="xóa sinh viên", conn=conn)
        return count

    def list_options(self) -> list[StudentOption]:
        rows = self.query("SELECT student_id, full_name, class_name FROM Students ORDER BY student_id", action="tải danh sách sinh viên")
        return [StudentOption(str(r[0]), str(r[1]), str(r[2])) for r in rows]
