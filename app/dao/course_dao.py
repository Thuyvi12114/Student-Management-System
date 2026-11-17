"""Truy cập bảng Courses."""

from __future__ import annotations

from app.dao.base import BaseDAO, like_pattern
from app.models import CourseOption, CourseSearchResult

_SELECT = (
    "SELECT c.course_id, c.course_name, c.credits, c.lecturer_id, l.full_name, c.description "
    "FROM Courses c JOIN Lecturers l ON l.lecturer_id = c.lecturer_id"
)


def _course(row: tuple) -> CourseOption:
    return CourseOption(
        course_id=str(row[0]), course_name=str(row[1]), credits=int(row[2]),
        lecturer_id=str(row[3]), lecturer_name=str(row[4]),
        description=None if row[5] is None else str(row[5]),
    )


class CourseDAO(BaseDAO):
    def find_by_id(self, course_id: str, *, conn=None) -> CourseOption | None:
        row = self.one(f"{_SELECT} WHERE c.course_id = %s", (course_id,), action="tìm học phần", conn=conn)
        return _course(row) if row else None

    def exists(self, course_id: str) -> bool:
        return self.one("SELECT 1 FROM Courses WHERE course_id = %s", (course_id,), action="kiểm tra mã học phần") is not None

    def list_all(self) -> list[CourseOption]:
        return [_course(r) for r in self.query(f"{_SELECT} ORDER BY c.course_id", action="tải học phần")]

    def list_by_lecturer(self, lecturer_id: str) -> list[CourseOption]:
        return [_course(r) for r in self.query(f"{_SELECT} WHERE c.lecturer_id = %s ORDER BY c.course_id", (lecturer_id,), action="tải học phần")]

    def search(self, keyword: str | None, *, page: int, page_size: int, lecturer_id: str | None = None) -> CourseSearchResult:
        where, params = ["1 = 1"], []
        if keyword and keyword.strip():
            pattern = like_pattern(keyword.strip())
            where.append("(c.course_id LIKE %s OR c.course_name LIKE %s OR l.full_name LIKE %s)")
            params += [pattern, pattern, pattern]
        if lecturer_id:
            where.append("c.lecturer_id = %s")
            params.append(lecturer_id)
        clause = " AND ".join(where)
        total = int(self.scalar(
            f"SELECT COUNT(*) FROM Courses c JOIN Lecturers l ON l.lecturer_id = c.lecturer_id WHERE {clause}",
            params, action="đếm học phần") or 0)
        pages = (total + page_size - 1) // page_size
        page = max(1, min(page, pages)) if pages else 1
        rows = self.query(
            f"{_SELECT} WHERE {clause} ORDER BY c.course_id LIMIT %s OFFSET %s",
            [*params, page_size, (page - 1) * page_size], action="tìm kiếm học phần",
        )
        return CourseSearchResult([_course(r) for r in rows], total, page, page_size, pages)

    def insert(self, course_id: str, lecturer_id: str, course_name: str, credits: int, description: str | None) -> None:
        self.execute(
            "INSERT INTO Courses (course_id, lecturer_id, course_name, credits, description) VALUES (%s, %s, %s, %s, %s)",
            (course_id, lecturer_id, course_name, credits, description), action="tạo học phần",
        )

    def update(self, course_id: str, lecturer_id: str, course_name: str, credits: int, description: str | None) -> int:
        count, _ = self.execute(
            "UPDATE Courses SET lecturer_id = %s, course_name = %s, credits = %s, description = %s WHERE course_id = %s",
            (lecturer_id, course_name, credits, description, course_id), action="cập nhật học phần",
        )
        return count

    def count_grades(self, course_id: str) -> int:
        return int(self.scalar("SELECT COUNT(*) FROM Grades WHERE course_id = %s", (course_id,), action="đếm điểm") or 0)

    def delete(self, course_id: str) -> int:
        count, _ = self.execute("DELETE FROM Courses WHERE course_id = %s", (course_id,), action="xóa học phần")
        return count

    def count_all(self) -> int:
        return int(self.scalar("SELECT COUNT(*) FROM Courses", action="đếm học phần") or 0)
