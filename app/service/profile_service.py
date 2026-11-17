"""UC-03 Xem hồ sơ cá nhân và UC-08 Cập nhật thông tin liên hệ (Module 2, Nghĩa)."""

from __future__ import annotations

from app.dao.lecturer_dao import LecturerDAO
from app.dao.student_dao import StudentDAO
from app.models import Lecturer, Role, StudentRecord
from app.security.session import Session
from app.service import validators as v
from app.service.exceptions import AuthorizationError, ValidationError


class ProfileService:
    def __init__(self, student_dao: StudentDAO, lecturer_dao: LecturerDAO) -> None:
        self._student_dao = student_dao
        self._lecturer_dao = lecturer_dao

    def my_profile(self, session: Session) -> StudentRecord | Lecturer:
        """Chỉ trả về hồ sơ của chính tài khoản đang đăng nhập."""
        if session.is_expired():
            raise AuthorizationError("Phiên đăng nhập đã hết hạn.")
        if session.role is Role.STUDENT:
            record = self._student_dao.find_by_account(session.account_id)
        elif session.role is Role.LECTURER:
            record = self._lecturer_dao.find_by_account(session.account_id)
        else:
            raise AuthorizationError("Tài khoản quản trị viên không có hồ sơ cá nhân.")
        if record is None:  # AF1
            raise ValidationError("Không tìm thấy hồ sơ cá nhân liên kết với tài khoản này.")
        return record

    def update_contact(self, session: Session, *, email: str, phone: str, address: str | None) -> StudentRecord:
        """UC-08: chỉ email, số điện thoại, địa chỉ; mã SV, lớp, điểm… không được sửa."""
        if session.role is not Role.STUDENT or session.is_expired():
            raise AuthorizationError("Chỉ sinh viên mới được cập nhật thông tin liên hệ của mình.")
        current = self.my_profile(session)
        assert isinstance(current, StudentRecord)
        clean_email = v.email(email)
        clean_phone = v.phone(phone)
        clean_address = v.optional_text(address, "Địa chỉ", 255)
        self._student_dao.update_contact(current.student_id, clean_email, clean_phone, clean_address)
        return self.my_profile(session)
