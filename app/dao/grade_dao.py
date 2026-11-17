"""Truy cập bảng Grades."""

from __future__ import annotations

from decimal import Decimal

from app.dao.base import BaseDAO
from app.models import CourseGradeRow, GradeEntry

_SELECT = (
    "SELECT g.grade_id, g.student_id, s.full_name, g.course_id, c.course_name, c.credits, g.grade_value "
    "FROM Grades g JOIN Students s ON s.student_id = g.student_id JOIN Courses c ON c.course_id = g.course_id"
)


def _entry(row: tuple) -> GradeEntry:
    return GradeEntry(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), int(row[5]), Decimal(str(row[6])))


class GradeDAO(BaseDAO):
    def search(self, student_id: str | None, course_id: str | None) -> list[GradeEntry]:
        where, params = ["1 = 1"], []
        if student_id:
            where.append("g.student_id = %s")
            params.append(student_id)
        if course_id:
            where.append("g.course_id = %s")
            params.append(course_id)
        rows = self.query(f"{_SELECT} WHERE {' AND '.join(where)} ORDER BY g.student_id, g.course_id", params, action="tra cứu điểm")
        return [_entry(r) for r in rows]

    def list_for_student(self, student_id: str) -> list[GradeEntry]:
        return self.search(student_id, None)

    def find_by_student_course(self, student_id: str, course_id: str) -> GradeEntry | None:
        row = self.one(f"{_SELECT} WHERE g.student_id = %s AND g.course_id = %s", (student_id, course_id), action="tìm điểm")
        return _entry(row) if row else None

    def find_by_id(self, grade_id: int) -> GradeEntry | None:
        row = self.one(f"{_SELECT} WHERE g.grade_id = %s", (grade_id,), action="tìm điểm")
        return _entry(row) if row else None

    def list_roster(self, course_id: str) -> list[CourseGradeRow]:
        """Toàn bộ sinh viên kèm điểm (nếu có) của học phần; sinh viên chưa có điểm có grade_id None."""
        rows = self.query(
            "SELECT s.student_id, s.full_name, s.class_name, g.grade_id, g.grade_value "
            "FROM Students s LEFT JOIN Grades g ON g.student_id = s.student_id AND g.course_id = %s "
            "ORDER BY s.student_id",
            (course_id,), action="tải bảng điểm học phần",
        )
        return [
            CourseGradeRow(str(r[0]), str(r[1]), str(r[2]), None if r[3] is None else int(r[3]), None if r[4] is None else Decimal(str(r[4])))
            for r in rows
        ]

    def upsert(self, student_id: str, course_id: str, value: Decimal) -> int:
        """Mỗi cặp (student_id, course_id) tối đa một điểm: UNIQUE + ON DUPLICATE KEY UPDATE."""
        self.execute(
            "INSERT INTO Grades (student_id, course_id, grade_value) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE grade_value = VALUES(grade_value)",
            (student_id, course_id, value), action="lưu điểm",
        )
        return int(self.scalar("SELECT grade_id FROM Grades WHERE student_id = %s AND course_id = %s", (student_id, course_id), action="lưu điểm"))
