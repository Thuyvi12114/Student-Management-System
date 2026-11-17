"""UC-12 Xem học phần, UC-13 Quản lý học phần (Module 5)."""

from __future__ import annotations

from app.dao.course_dao import CourseDAO
from app.dao.errors import DuplicateRecordError
from app.dao.lecturer_dao import LecturerDAO
from app.dao.user_account_dao import UserAccountDAO
from app.models import CourseOption, CourseSearchResult, Role
from app.security.session import Session
from app.service import validators as v
from app.service.access import require_role
from app.service.exceptions import AuthorizationError, ValidationError

_ADMIN_ONLY = "Chỉ quản trị viên mới được quản lý học phần."


class CourseService:
    def __init__(self, course_dao: CourseDAO, lecturer_dao: LecturerDAO, account_dao: UserAccountDAO) -> None:
        self._course_dao = course_dao
        self._lecturer_dao = lecturer_dao
        self._account_dao = account_dao

    def _lecturer_scope(self, session: Session) -> str | None:
        """Admin/Student xem toàn bộ; Lecturer chỉ xem học phần của mình."""
        if session.is_expired():
            raise AuthorizationError("Phiên đăng nhập đã hết hạn.")
        if session.role is Role.LECTURER:
            lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
            if lecturer_id is None:
                raise AuthorizationError("Tài khoản chưa được liên kết với hồ sơ giảng viên.")
            return lecturer_id
        return None

    def list_all(self, session: Session) -> list[CourseOption]:
        scope = self._lecturer_scope(session)
        return self._course_dao.list_by_lecturer(scope) if scope else self._course_dao.list_all()

    def search(
        self, session: Session, keyword: str | None = None, *, page: int = 1, page_size: int = 20,
    ) -> CourseSearchResult:
        scope = self._lecturer_scope(session)
        if not 1 <= page_size <= 200:
            raise ValidationError("Kích thước trang phải nằm trong khoảng 1 đến 200.")
        return self._course_dao.search(keyword, page=max(page, 1), page_size=page_size, lecturer_id=scope)

    def get_by_id(self, session: Session, course_id: str) -> CourseOption:
        scope = self._lecturer_scope(session)
        course = self._course_dao.find_by_id(course_id)
        if course is None:
            raise ValidationError("Học phần không tồn tại.")
        if scope and course.lecturer_id != scope:
            raise AuthorizationError("Học phần không được phân công cho bạn.")
        return course

    def create(
        self, session: Session, *, course_id: str, course_name: str, credits: int | str,
        lecturer_id: str, description: str | None = None,
    ) -> CourseOption:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        code = v.identifier(course_id, "Mã học phần")
        name = v.required_text(course_name, "Tên học phần", 150)
        credit = v.credits(credits)
        desc = v.optional_text(description, "Mô tả", 5000)
        self._require_lecturer(lecturer_id)
        if self._course_dao.exists(code):
            raise ValidationError("Mã học phần đã tồn tại.")
        try:
            self._course_dao.insert(code, lecturer_id, name, credit, desc)
        except DuplicateRecordError as exc:
            raise ValidationError("Mã học phần đã tồn tại.") from exc
        return self._course_dao.find_by_id(code)  # type: ignore[return-value]

    def update(
        self, session: Session, course_id: str, *, course_name: str, credits: int | str,
        lecturer_id: str, description: str | None = None,
    ) -> CourseOption:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        if self._course_dao.find_by_id(course_id) is None:
            raise ValidationError("Học phần không tồn tại.")
        self._require_lecturer(lecturer_id)
        self._course_dao.update(
            course_id, lecturer_id, v.required_text(course_name, "Tên học phần", 150),
            v.credits(credits), v.optional_text(description, "Mô tả", 5000),
        )
        return self._course_dao.find_by_id(course_id)  # type: ignore[return-value]

    def delete(self, session: Session, course_id: str) -> None:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        if self._course_dao.find_by_id(course_id) is None:
            raise ValidationError("Học phần không tồn tại.")
        if self._course_dao.count_grades(course_id) > 0:
            raise ValidationError("Không thể xóa học phần đã có điểm sinh viên.")
        self._course_dao.delete(course_id)

    def _require_lecturer(self, lecturer_id: str) -> None:
        """Giảng viên phụ trách phải tồn tại và có tài khoản đang hoạt động (Active)."""
        lecturer = self._lecturer_dao.find_by_id(lecturer_id) if lecturer_id else None
        if lecturer is None:
            raise ValidationError("Mỗi học phần phải được phân công cho một giảng viên hợp lệ.")
        if not self._account_dao.is_active(lecturer.account_id):
            raise ValidationError("Giảng viên phụ trách phải có tài khoản đang hoạt động.")
