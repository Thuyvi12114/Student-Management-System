"""Nghiệp vụ sinh viên: tìm kiếm, xem hồ sơ và dashboard."""

from __future__ import annotations

import re
from datetime import date

from app.dao.errors import DuplicateRecordError
from app.dao.lecturer_dao import LecturerDAO
from app.dao.student_dao import StudentDAO
from app.dao.user_account_dao import UserAccountDAO
from app.models import (
    DashboardStats,
    LecturerStudentSearchResult,
    Role,
    StudentRecord,
    StudentSearchResult,
)
from app.security.password_hasher import hash_password
from app.security.password_policy import violations as password_violations
from app.security.session import Session
from app.service.exceptions import AuthorizationError, ValidationError

_EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class StudentService:
    def __init__(
        self,
        student_dao: StudentDAO,
        lecturer_dao: LecturerDAO,
        user_account_dao: UserAccountDAO,
    ) -> None:
        self._student_dao = student_dao
        self._lecturer_dao = lecturer_dao
        self._user_account_dao = user_account_dao

    def create(
        self,
        session: Session,
        *,
        student_code: str,
        full_name: str,
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        class_name: str,
        enrollment_year: int,
        password: str,
    ) -> StudentRecord:
        self._require_admin(session)
        student_code = (student_code or "").strip().upper()
        if not 3 <= len(student_code) <= 20:
            raise ValidationError("Mã sinh viên phải có từ 3 đến 20 ký tự.")
        values = self._normalize_profile(
            full_name=full_name,
            gender=gender,
            date_of_birth=date_of_birth,
            email=email,
            phone=phone,
            class_name=class_name,
            enrollment_year=enrollment_year,
        )
        password_errors = password_violations(password)
        if password_errors:
            raise ValidationError(" ".join(password_errors))

        if self._student_dao.student_code_exists(student_code):
            raise ValidationError("Mã sinh viên đã tồn tại.")
        if self._user_account_dao.username_exists(student_code):
            raise ValidationError("Tên đăng nhập đã tồn tại.")
        if self._student_dao.email_exists(email):
            raise ValidationError("Email sinh viên đã tồn tại.")

        try:
            return self._student_dao.create_with_account(
                student_code=student_code,
                password_hash=hash_password(password),
                **values,
            )
        except DuplicateRecordError as exc:
            raise ValidationError(str(exc)) from exc

    def search_students(
        self,
        session: Session,
        keyword: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
        class_name: str | None = None,
    ) -> StudentSearchResult | LecturerStudentSearchResult:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 200:
            raise ValidationError("Kích thước trang phải nằm trong khoảng 1 đến 200.")
        if session.role is Role.ADMIN:
            self._require_admin(session)
            return self._student_dao.search_admin(
                keyword, page=page, page_size=page_size, class_name=class_name
            )
        if session.role is Role.LECTURER:
            return self._student_dao.search_lecturer(
                keyword, page=page, page_size=page_size
            )
        raise AuthorizationError(
            "Sinh viên không được phép tìm kiếm hồ sơ của các sinh viên khác."
        )

    def class_names(self, session: Session) -> list[str]:
        self._require_admin(session)
        return self._student_dao.list_class_names()

    def student_detail(self, session: Session, student_id: int) -> StudentRecord:
        self._require_admin(session)
        record = self._student_dao.find_admin_record(student_id)
        if record is None:
            raise ValidationError("Sinh viên không tồn tại.")
        return record

    def update(
        self,
        session: Session,
        student_id: int,
        *,
        full_name: str,
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        class_name: str,
        enrollment_year: int,
    ) -> StudentRecord:
        self._require_admin(session)
        current = self._student_dao.find_admin_record(student_id)
        if current is None:
            raise ValidationError("Sinh viên không tồn tại.")
        values = self._normalize_profile(
            full_name=full_name,
            gender=gender,
            date_of_birth=date_of_birth,
            email=email,
            phone=phone,
            class_name=class_name,
            enrollment_year=enrollment_year,
        )
        try:
            return self._student_dao.update_profile(
                student_id=student_id,
                account_id=current.account_id,
                **values,
            )
        except DuplicateRecordError as exc:
            raise ValidationError(str(exc)) from exc

    def delete(self, session: Session, student_id: int) -> None:
        self._require_admin(session)
        if self._student_dao.find_admin_record(student_id) is None:
            raise ValidationError("Sinh viên không tồn tại.")
        if not self._student_dao.delete_if_without_grades(student_id):
            raise ValidationError(
                "Không thể xóa sinh viên đã có bản ghi điểm. "
                "Hãy giữ hồ sơ để bảo toàn lịch sử học tập."
            )

    def dashboard(self, session: Session) -> DashboardStats:
        if session.role is Role.ADMIN:
            self._require_admin(session)
            return self._student_dao.admin_dashboard_stats()
        if session.role is Role.LECTURER:
            lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
            if lecturer_id is None:
                raise AuthorizationError(
                    "Tài khoản chưa được liên kết với hồ sơ giảng viên."
                )
            return self._student_dao.lecturer_dashboard_stats(lecturer_id)
        raise AuthorizationError(
            "Thông tin dashboard quản lý không dành cho sinh viên."
        )

    @staticmethod
    def _require_admin(session: Session) -> None:
        if (
            not isinstance(session, Session)
            or session.is_expired()
            or session.role is not Role.ADMIN
        ):
            raise AuthorizationError("Chỉ quản trị viên đang đăng nhập mới có quyền thêm sinh viên.")

    @staticmethod
    def _normalize_profile(
        *,
        full_name: str,
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        class_name: str,
        enrollment_year: int,
    ) -> dict[str, object]:
        full_name = (full_name or "").strip()
        email = (email or "").strip().lower()
        class_name = (class_name or "").strip()
        phone = (phone or "").strip() or None

        if not full_name or not gender or not email or not class_name:
            raise ValidationError("Vui lòng nhập đầy đủ các trường bắt buộc.")
        if len(full_name) > 100:
            raise ValidationError("Họ tên không được vượt quá 100 ký tự.")
        if gender not in {"Male", "Female", "Other"}:
            raise ValidationError("Giới tính không hợp lệ.")
        if type(date_of_birth) is not date or date_of_birth > date.today():
            raise ValidationError("Ngày sinh không hợp lệ.")
        if len(email) > 100 or not _EMAIL_PATTERN.fullmatch(email):
            raise ValidationError("Email không hợp lệ.")
        if phone is not None:
            digits = phone[1:] if phone.startswith("+") else phone
            if (
                len(phone) > 15
                or not digits.isdigit()
                or not 7 <= len(digits) <= 15
            ):
                raise ValidationError(
                    "Số điện thoại phải có từ 7 đến 15 chữ số, có thể bắt đầu bằng dấu +."
                )
        if len(class_name) > 30:
            raise ValidationError("Tên lớp không được vượt quá 30 ký tự.")
        if type(enrollment_year) is not int or not 2000 <= enrollment_year <= 2100:
            raise ValidationError("Năm nhập học phải nằm trong khoảng 2000 đến 2100.")
        return {
            "full_name": full_name,
            "gender": gender,
            "date_of_birth": date_of_birth,
            "email": email,
            "phone": phone,
            "class_name": class_name,
            "enrollment_year": enrollment_year,
        }
