"""Nghiệp vụ quản lý giảng viên."""

from __future__ import annotations

import re
from datetime import date

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.dao.lecturer_dao import LecturerDAO
from app.models import Lecturer, LecturerSearchResult, Role
from app.security.password_hasher import hash_password
from app.security.password_policy import violations
from app.security.session import Session
from app.service.exceptions import AuthorizationError, ValidationError

_EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class LecturerService:
    def __init__(self, lecturer_dao: LecturerDAO) -> None:
        self._lecturer_dao = lecturer_dao

    def list_all(self, session: Session) -> list[Lecturer]:
        self._require_admin(session)
        return self._lecturer_dao.list_all()

    def search(
        self,
        session: Session,
        keyword: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
        department: str | None = None,
    ) -> LecturerSearchResult:
        self._require_admin(session)
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 200:
            raise ValidationError("Kích thước trang phải nằm trong khoảng 1 đến 200.")
        return self._lecturer_dao.search(
            keyword, page=page, page_size=page_size, department=department
        )

    def departments(self, session: Session) -> list[str]:
        self._require_admin(session)
        return self._lecturer_dao.list_departments()

    def count_all(self, session: Session) -> int:
        self._require_admin(session)
        return self._lecturer_dao.count_all()

    def get_by_id(self, session: Session, lecturer_id: int) -> Lecturer:
        self._require_admin(session)
        lecturer = self._lecturer_dao.find_by_id(lecturer_id)
        if lecturer is None:
            raise ValidationError("Giảng viên không tồn tại.")
        return lecturer

    def create(
        self,
        session: Session,
        *,
        username: str,
        password: str,
        lecturer_code: str,
        full_name: str,
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        department: str,
        degree: str,
    ) -> Lecturer:
        self._require_admin(session)
        self._validate_required(username, lecturer_code, full_name, gender, email, department, degree)
        self._validate_password(password)
        self._validate_profile(gender, date_of_birth, email, phone, degree)
        normalized = self._normalize_personal_data(username, lecturer_code, full_name, email, department, degree)
        if len(normalized["username"]) < 3 or len(normalized["username"]) > 50:
            raise ValidationError("Tên đăng nhập phải có từ 3 đến 50 ký tự.")
        if not 3 <= len(normalized["lecturer_code"]) <= 20 or len(normalized["full_name"]) > 100:
            raise ValidationError("Mã giảng viên hoặc họ tên vượt quá độ dài cho phép.")
        if len(normalized["email"]) > 100 or len(normalized["department"]) > 100:
            raise ValidationError("Email hoặc khoa/bộ môn vượt quá độ dài cho phép.")
        phone = (phone or "").strip() or None

        if self._lecturer_dao.find_by_code(normalized["lecturer_code"]) is not None:
            raise ValidationError("Mã giảng viên đã tồn tại.")
        if self._lecturer_dao.find_by_email(normalized["email"]) is not None:
            raise ValidationError("Email giảng viên đã tồn tại.")

        try:
            lecturer_id = self._lecturer_dao.create_with_account(
                normalized["username"],
                hash_password(password),
                normalized["full_name"],
                normalized["lecturer_code"],
                gender,
                date_of_birth,
                normalized["email"],
                phone,
                normalized["department"],
                normalized["degree"],
            )
        except DuplicateRecordError as exc:
            raise ValidationError(
                "Tên đăng nhập, mã giảng viên hoặc email đã tồn tại."
            ) from exc

        lecturer = self._lecturer_dao.find_by_id(lecturer_id)
        if lecturer is None:
            raise DataAccessError("Tạo giảng viên thành công nhưng không đọc lại được hồ sơ.")
        return lecturer

    def update(
        self,
        session: Session,
        lecturer_id: int,
        *,
        lecturer_code: str,
        full_name: str,
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        department: str,
        degree: str,
    ) -> Lecturer:
        self._require_admin(session)
        self._validate_required(lecturer_code, full_name, gender, email, department, degree)
        phone = (phone or "").strip() or None
        self._validate_profile(gender, date_of_birth, email, phone, degree)
        lecturer = self._lecturer_dao.find_by_id(lecturer_id)
        if lecturer is None:
            raise ValidationError("Giảng viên không tồn tại.")

        normalized = self._normalize_personal_data(lecturer.lecturer_code, lecturer_code, full_name, email, department, degree)
        if not 3 <= len(normalized["lecturer_code"]) <= 20 or len(normalized["full_name"]) > 100:
            raise ValidationError("Mã giảng viên hoặc họ tên vượt quá độ dài cho phép.")
        if len(normalized["email"]) > 100 or len(normalized["department"]) > 100:
            raise ValidationError("Email hoặc khoa/bộ môn vượt quá độ dài cho phép.")
        existing_code = self._lecturer_dao.find_by_code(normalized["lecturer_code"])
        if existing_code is not None and existing_code.lecturer_id != lecturer_id:
            raise ValidationError("Mã giảng viên đã tồn tại.")
        existing_email = self._lecturer_dao.find_by_email(normalized["email"])
        if existing_email is not None and existing_email.lecturer_id != lecturer_id:
            raise ValidationError("Email giảng viên đã tồn tại.")

        try:
            self._lecturer_dao.update(
                lecturer_id,
                lecturer.account_id,
                normalized["lecturer_code"],
                normalized["full_name"],
                gender,
                date_of_birth,
                normalized["email"],
                phone,
                normalized["department"],
                normalized["degree"],
            )
        except DuplicateRecordError as exc:
            raise ValidationError("Mã giảng viên hoặc email đã tồn tại.") from exc
        updated = self._lecturer_dao.find_by_id(lecturer_id)
        if updated is None:
            raise DataAccessError("Cập nhật giảng viên thành công nhưng không đọc lại được dữ liệu.")
        return updated

    def delete(self, session: Session, lecturer_id: int) -> None:
        self._require_admin(session)
        lecturer = self._lecturer_dao.find_by_id(lecturer_id)
        if lecturer is None:
            raise ValidationError("Giảng viên không tồn tại.")
        if not self._lecturer_dao.delete_if_unassigned(lecturer_id):
            raise ValidationError("Không thể xóa giảng viên đang phụ trách ít nhất một môn học.")

    @staticmethod
    def _require_admin(session: Session) -> None:
        if (
            not isinstance(session, Session)
            or session.is_expired()
            or session.role is not Role.ADMIN
        ):
            raise AuthorizationError("Chỉ quản trị viên mới có quyền quản lý giảng viên.")

    @staticmethod
    def _validate_required(*values: str | None) -> None:
        for value in values:
            if value is None or str(value).strip() == "":
                raise ValidationError("Vui lòng nhập đầy đủ thông tin bắt buộc.")

    @staticmethod
    def _validate_password(password: str) -> None:
        password_errors = violations(password)
        if password_errors:
            raise ValidationError(" ".join(password_errors))

    @staticmethod
    def _validate_profile(
        gender: str,
        date_of_birth: date,
        email: str,
        phone: str | None,
        degree: str,
    ) -> None:
        if gender not in {"Male", "Female", "Other"}:
            raise ValidationError("Giới tính không hợp lệ.")
        if not isinstance(date_of_birth, date) or date_of_birth > date.today():
            raise ValidationError("Ngày sinh không hợp lệ.")
        if len(email.strip()) > 100 or not _EMAIL_PATTERN.fullmatch(email.strip()):
            raise ValidationError("Email không hợp lệ.")
        if phone is not None:
            digits = phone[1:] if phone.startswith("+") else phone
            if len(phone) > 15 or not digits.isdigit() or not 7 <= len(digits) <= 15:
                raise ValidationError(
                    "Số điện thoại phải có từ 7 đến 15 chữ số, có thể bắt đầu bằng dấu +."
                )
        if degree not in {"Bachelor", "Master", "Doctor"}:
            raise ValidationError("Học vị không hợp lệ.")

    @staticmethod
    def _normalize_personal_data(username: str, lecturer_code: str, full_name: str, email: str, department: str, degree: str) -> dict[str, str]:
        return {
            "username": (username or "").strip(),
            "lecturer_code": (lecturer_code or "").strip().upper(),
            "full_name": (full_name or "").strip(),
            "email": (email or "").strip().lower(),
            "department": (department or "").strip(),
            "degree": (degree or "").strip(),
        }
