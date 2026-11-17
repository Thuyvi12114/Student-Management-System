"""Truy vấn tìm kiếm và thống kê sinh viên (Module 4 - Tra cứu sinh viên & Dashboard, Sơn)."""

from __future__ import annotations

from app.dao.base import BaseDAO, like_pattern
from app.dao.student_dao import _COLUMNS, _record
from app.models import (
    LecturerStudent,
    LecturerStudentSearchResult,
    StudentSearchResult,
)


class StudentSearchDAO(BaseDAO):
    def search(self, keyword: str | None, *, page: int, page_size: int, class_name: str | None = None) -> StudentSearchResult:
        where, params = ["1 = 1"], []
        if keyword and keyword.strip():
            pattern = like_pattern(keyword.strip())
            where.append("(student_id LIKE %s OR full_name LIKE %s OR class_name LIKE %s)")
            params += [pattern, pattern, pattern]
        if class_name:
            where.append("class_name = %s")
            params.append(class_name)
        clause = " AND ".join(where)
        total = int(self.scalar(f"SELECT COUNT(*) FROM Students WHERE {clause}", params, action="đếm sinh viên") or 0)
        pages = (total + page_size - 1) // page_size
        page = max(1, min(page, pages)) if pages else 1
        rows = self.query(
            f"SELECT {_COLUMNS} FROM Students WHERE {clause} ORDER BY student_id LIMIT %s OFFSET %s",
            [*params, page_size, (page - 1) * page_size],
            action="tìm kiếm sinh viên",
        )
        return StudentSearchResult([_record(r) for r in rows], total, page, page_size, pages)

    def search_basic(
        self, keyword: str | None, *, page: int, page_size: int, class_name: str | None = None
    ) -> LecturerStudentSearchResult:
        """UC-01 cho giảng viên: cột trả về giới hạn ở student_id, full_name, class_name."""
        where, params = ["1 = 1"], []
        if keyword and keyword.strip():
            pattern = like_pattern(keyword.strip())
            where.append("(student_id LIKE %s OR full_name LIKE %s OR class_name LIKE %s)")
            params += [pattern, pattern, pattern]
        if class_name:
            where.append("class_name = %s")
            params.append(class_name)
        clause = " AND ".join(where)
        total = int(self.scalar(f"SELECT COUNT(*) FROM Students WHERE {clause}", params, action="đếm sinh viên") or 0)
        pages = (total + page_size - 1) // page_size
        page = max(1, min(page, pages)) if pages else 1
        rows = self.query(
            f"SELECT student_id, full_name, class_name FROM Students WHERE {clause} "
            "ORDER BY student_id LIMIT %s OFFSET %s",
            [*params, page_size, (page - 1) * page_size],
            action="tìm kiếm sinh viên",
        )
        items = [LecturerStudent(str(r[0]), str(r[1]), str(r[2])) for r in rows]
        return LecturerStudentSearchResult(items, total, page, page_size, pages)

    def class_names(self) -> list[str]:
        return [str(r[0]) for r in self.query("SELECT DISTINCT class_name FROM Students ORDER BY class_name", action="tải danh sách lớp")]

    def count_all(self) -> int:
        return int(self.scalar("SELECT COUNT(*) FROM Students", action="đếm sinh viên") or 0)

    def count_classes(self) -> int:
        return int(self.scalar("SELECT COUNT(DISTINCT class_name) FROM Students", action="đếm lớp") or 0)
