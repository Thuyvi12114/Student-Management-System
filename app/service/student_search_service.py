"""UC-01 Tìm kiếm sinh viên, UC-02 Xem chi tiết và thống kê dashboard (Module 4, Sơn)."""

from __future__ import annotations

from app.dao.lecturer_dao import LecturerDAO
from app.dao.student_dao import StudentDAO
from app.dao.student_search_dao import StudentSearchDAO
from app.models import (
    DashboardStats,
    LecturerStudentSearchResult,
    Role,
    StudentOption,
    StudentRecord,
    StudentSearchResult,
)
from app.security.session import Session
from app.service.access import require_role
from app.service.exceptions import AuthorizationError, ValidationError

_ADMIN_ONLY = "Chỉ quản trị viên mới được xem đầy đủ thông tin sinh viên."


class StudentSearchService:
    def __init__(self, search_dao: StudentSearchDAO, student_dao: StudentDAO, lecturer_dao: LecturerDAO) -> None:
        self._search_dao = search_dao
        self._student_dao = student_dao
        self._lecturer_dao = lecturer_dao

    def search_students(
        self, session: Session, keyword: str | None = None, *, page: int = 1, page_size: int = 20,
        class_name: str | None = None,
    ) -> StudentSearchResult:
        """UC-01 (Admin): khớp một phần, không phân biệt hoa thường theo mã SV, họ tên, lớp; trả đủ hồ sơ."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        self._check_page_size(page_size)
        return self._search_dao.search(keyword, page=max(page, 1), page_size=page_size, class_name=class_name)

    def search_students_basic(
        self, session: Session, keyword: str | None = None, *, page: int = 1, page_size: int = 20,
        class_name: str | None = None,
    ) -> LecturerStudentSearchResult:
        """UC-01 (Giảng viên): chỉ trả mã sinh viên, họ tên, lớp; không lộ email, SĐT, ngày sinh, địa chỉ."""
        require_role(session, Role.LECTURER, "Chỉ giảng viên mới dùng chức năng tra cứu này.")
        self._check_page_size(page_size)
        return self._search_dao.search_basic(keyword, page=max(page, 1), page_size=page_size, class_name=class_name)

    def class_names(self, session: Session) -> list[str]:
        if session.role not in (Role.ADMIN, Role.LECTURER) or session.is_expired():
            raise AuthorizationError("Bạn không có quyền xem danh sách lớp.")
        return self._search_dao.class_names()

    def student_detail(self, session: Session, student_id: str) -> StudentRecord:
        """UC-02: chỉ Admin xem đầy đủ chi tiết sinh viên."""
        require_role(session, Role.ADMIN, "Chỉ quản trị viên mới xem được chi tiết đầy đủ của sinh viên.")
        record = self._student_dao.find_by_id(student_id)
        if record is None:
            raise ValidationError("Sinh viên không tồn tại.")
        return record

    def list_options(self, session: Session) -> list[StudentOption]:
        if session.role not in (Role.ADMIN, Role.LECTURER):
            raise AuthorizationError("Bạn không có quyền xem danh sách sinh viên.")
        return self._student_dao.list_options()

    def dashboard(self, session: Session) -> DashboardStats:
        """Thống kê KPI cho Admin và giảng viên (tiến độ nhập điểm)."""
        if session.role is Role.ADMIN:
            return DashboardStats(
                total_students=self._search_dao.count_all(),
                total_lecturers=self._lecturer_dao.count_all(),
                total_courses=int(self._search_dao.scalar("SELECT COUNT(*) FROM Courses") or 0),
                total_classes=self._search_dao.count_classes(),
            )
        if session.role is Role.LECTURER:
            lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
            if lecturer_id is None:
                raise AuthorizationError("Tài khoản chưa được liên kết với hồ sơ giảng viên.")
            own = self._lecturer_dao.count_courses(lecturer_id)
            students = self._search_dao.count_all()
            graded = self._search_dao.scalar(
                "SELECT COUNT(*) FROM Grades g JOIN Courses c ON c.course_id = g.course_id WHERE c.lecturer_id = %s",
                (lecturer_id,),
            ) or 0
            return DashboardStats(
                total_students=students,
                total_courses=own,
                total_classes=self._search_dao.count_classes(),
                assigned_courses=own,
                graded_entries=int(graded),
                expected_entries=own * students,
            )
        raise AuthorizationError("Thông tin dashboard quản lý không dành cho sinh viên.")

    @staticmethod
    def _check_page_size(page_size: int) -> None:
        if not 1 <= page_size <= 200:
            raise ValidationError("Kích thước trang phải nằm trong khoảng 1 đến 200.")
