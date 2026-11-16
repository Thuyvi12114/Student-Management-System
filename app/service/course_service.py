"""Nghiệp vụ quản lý học phần."""

from __future__ import annotations

from app.dao.course_dao import CourseDAO
from app.dao.errors import DuplicateRecordError
from app.dao.lecturer_dao import LecturerDAO
from app.dao.user_account_dao import UserAccountDAO
from app.models import CourseOption, CourseSearchResult, Role
from app.security.session import Session
from app.service.exceptions import AuthorizationError, ValidationError


class CourseService:
    def __init__(
        self,
        course_dao: CourseDAO,
        lecturer_dao: LecturerDAO,
        user_account_dao: UserAccountDAO,
    ) -> None:
        self._course_dao = course_dao
        self._lecturer_dao = lecturer_dao
        self._user_account_dao = user_account_dao

    def list_all(self, session: Session) -> list[CourseOption]:
        if session.role in {Role.ADMIN, Role.STUDENT}:
            return self._course_dao.list_all()
        if session.role is Role.LECTURER:
            lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
            if lecturer_id is None:
                raise AuthorizationError(
                    "Tài khoản chưa được liên kết với hồ sơ giảng viên."
                )
            return self._course_dao.list_by_lecturer(lecturer_id)
        raise AuthorizationError("Vai trò hiện tại không được phép xem danh sách học phần.")

    def search(
        self,
        session: Session,
        keyword: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
        semester: str | None = None,
    ) -> CourseSearchResult:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 200:
            raise ValidationError("Kích thước trang phải nằm trong khoảng 1 đến 200.")
        if semester is not None and semester not in {"HK1", "HK2", "HK3"}:
            raise ValidationError("Học kỳ không hợp lệ.")
        if session.role in {Role.ADMIN, Role.STUDENT}:
            return self._course_dao.search(
                keyword, page=page, page_size=page_size, semester=semester
            )
        if session.role is Role.LECTURER:
            lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
            if lecturer_id is None:
                raise AuthorizationError(
                    "Tài khoản chưa được liên kết với hồ sơ giảng viên."
                )
            return self._course_dao.search(
                keyword,
                page=page,
                page_size=page_size,
                lecturer_id=lecturer_id,
                semester=semester,
            )
        raise AuthorizationError("Vai trò hiện tại không được phép xem học phần.")

    def get_by_id(self, session: Session, course_id: int) -> CourseOption:
        if session.role in {Role.ADMIN, Role.STUDENT}:
            course = self._course_dao.find_by_id(course_id)
            if course is None:
                raise ValidationError("Học phần không tồn tại.")
            return course
        if session.role is Role.LECTURER:
            lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
            if lecturer_id is None:
                raise AuthorizationError(
                    "Tài khoản chưa được liên kết với hồ sơ giảng viên."
                )
            course = self._course_dao.find_by_id_for_lecturer(
                course_id, lecturer_id
            )
            if course is not None:
                return course
            raise AuthorizationError(
                "Học phần không tồn tại hoặc không được phân công cho bạn."
            )
        raise AuthorizationError("Vai trò hiện tại không được phép xem chi tiết học phần.")

    def create(
        self,
        session: Session,
        *,
        course_code: str,
        course_name: str,
        credits: int,
        lecturer_id: int | None,
        semester: str,
        academic_year: str,
    ) -> CourseOption:
        self._require_admin(session)
        self._validate(course_code, course_name, credits, semester, academic_year)
        self._validate_assigned_lecturer(lecturer_id)
        try:
            new_id = self._course_dao.insert(course_code.strip(), course_name.strip(), int(credits), lecturer_id, semester.strip(), academic_year.strip())
        except DuplicateRecordError as exc:
            raise ValidationError("Mã học phần đã tồn tại.") from exc
        course = self._course_dao.find_by_id(new_id)
        if course is None:
            raise ValidationError("Tạo học phần thành công nhưng không đọc lại được dữ liệu.")
        return course

    def update(
        self,
        session: Session,
        course_id: int,
        *,
        course_code: str,
        course_name: str,
        credits: int,
        lecturer_id: int | None,
        semester: str,
        academic_year: str,
    ) -> CourseOption:
        self._require_admin(session)
        current = self._course_dao.find_by_id(course_id)
        if current is None:
            raise ValidationError("Học phần không tồn tại.")
        self._validate(course_code, course_name, credits, semester, academic_year)
        self._validate_assigned_lecturer(lecturer_id)
        try:
            self._course_dao.update(course_id, course_code.strip(), course_name.strip(), int(credits), lecturer_id, semester.strip(), academic_year.strip())
        except DuplicateRecordError as exc:
            raise ValidationError("Mã học phần đã tồn tại.") from exc
        updated = self._course_dao.find_by_id(course_id)
        if updated is None:
            raise ValidationError("Cập nhật học phần thành công nhưng không đọc lại được dữ liệu.")
        return updated

    def delete(self, session: Session, course_id: int) -> None:
        self._require_admin(session)
        current = self._course_dao.find_by_id(course_id)
        if current is None:
            raise ValidationError("Học phần không tồn tại.")
        if not self._course_dao.delete_if_without_grades(course_id):
            raise ValidationError("Không thể xóa học phần đã có điểm sinh viên.")

    @staticmethod
    def _require_admin(session: Session) -> None:
        if session.role is not Role.ADMIN or session.is_expired():
            raise AuthorizationError("Chỉ quản trị viên mới có quyền quản lý học phần.")

    def _validate_assigned_lecturer(self, lecturer_id: int | None) -> None:
        if lecturer_id is None:
            raise ValidationError("Mỗi học phần phải được phân công cho một giảng viên.")
        lecturer = self._lecturer_dao.find_by_id(lecturer_id)
        if lecturer is None:
            raise ValidationError("Giảng viên được phân công không tồn tại.")
        if not self._user_account_dao.is_active(lecturer.account_id):
            raise ValidationError("Giảng viên được gán phải có tài khoản đang hoạt động.")

    @staticmethod
    def _validate(course_code: str, course_name: str, credits: int, semester: str, academic_year: str) -> None:
        if not all(
            value and value.strip()
            for value in (course_code, course_name, semester, academic_year)
        ):
            raise ValidationError("Vui lòng nhập đầy đủ thông tin học phần.")
        try:
            credit_value = int(credits)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Số tín chỉ phải là số nguyên.") from exc
        if credit_value < 1 or credit_value > 10:
            raise ValidationError("Số tín chỉ phải nằm trong khoảng 1 đến 10.")
        if semester.strip() not in {"HK1", "HK2", "HK3"}:
            raise ValidationError("Học kỳ phải là HK1, HK2 hoặc HK3.")
        year = academic_year.strip()
        if len(year) != 9 or year[4] != "-" or not (year[:4] + year[5:]).isdigit():
            raise ValidationError("Năm học phải có định dạng YYYY-YYYY.")
