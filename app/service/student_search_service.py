"""UC-06 Tra cứu sinh viên — tìm kiếm và phân trang phía server."""

from __future__ import annotations

import math

from app.dao.student_dao import StudentDAO
from app.models import StudentRecord, StudentSearchResult
from app.security.session import Session
from app.service.access import require_role
from app.models import Role

_PAGE_SIZE = 20


class StudentSearchService:
    def __init__(self, student_dao: StudentDAO) -> None:
        self._dao = student_dao

    def search(
        self,
        session: Session,
        keyword: str = "",
        class_name: str = "",
        page: int = 1,
        page_size: int = _PAGE_SIZE,
    ) -> StudentSearchResult:
        require_role(session, Role.ADMIN, "Chỉ quản trị viên mới được tra cứu sinh viên.")
        all_students = self._dao.list_all()
        kw = keyword.strip().lower()
        cls = class_name.strip().lower()

        filtered = [
            s for s in all_students
            if (not kw or kw in s.student_id.lower() or kw in s.full_name.lower())
            and (not cls or cls in s.class_name.lower())
        ]

        total = len(filtered)
        total_pages = max(1, math.ceil(total / page_size))
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        items = filtered[start: start + page_size]

        return StudentSearchResult(
            items=items,
            total_count=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
