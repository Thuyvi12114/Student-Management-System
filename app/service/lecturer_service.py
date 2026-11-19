"""UC-14 Quản lý giảng viên (Module 5)."""

from __future__ import annotations

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.dao.lecturer_dao import LecturerDAO
from app.dao.user_account_dao import UserAccountDAO
from app.models import Lecturer, LecturerSearchResult, Role
from app.security.password_hasher import hash_password
from app.security.password_policy import violations
from app.security.session import Session
from app.service import validators as v
from app.service.access import require_role
from app.service.exceptions import ValidationError

_ADMIN_ONLY = "Chỉ quản trị viên mới được quản lý giảng viên."


class LecturerService:
    def __init__(self, lecturer_dao: LecturerDAO, account_dao: UserAccountDAO) -> None:
        self._lecturer_dao = lecturer_dao
        self._account_dao = account_dao

    def list_all(self, session: Session) -> list[Lecturer]:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        return self._lecturer_dao.list_all()

    def search(
        self, session: Session, keyword: str | None = None, *, page: int = 1, page_size: int = 20,
        department: str | None = None,
    ) -> LecturerSearchResult:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        if not 1 <= page_size <= 200:
            raise ValidationError("Kích thước trang phải nằm trong khoảng 1 đến 200.")
        return self._lecturer_dao.search(keyword, page=max(page, 1), page_size=page_size, department=department)

    def departments(self, session: Session) -> list[str]:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        return self._lecturer_dao.list_departments()

    def count_all(self, session: Session) -> int:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        return self._lecturer_dao.count_all()

    def get_by_id(self, session: Session, lecturer_id: str) -> Lecturer:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        lecturer = self._lecturer_dao.find_by_id(lecturer_id)
        if lecturer is None:
            raise ValidationError("Giảng viên không tồn tại.")
        return lecturer

    def create(
        self, session: Session, *, lecturer_id: str, full_name: str, email: str, phone: str,
        department: str, password: str,
    ) -> Lecturer:
        """Tạo hồ sơ + tài khoản (username = mã giảng viên) trong một giao dịch."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        code = v.identifier(lecturer_id, "Mã giảng viên")
        name = v.required_text(full_name, "Họ và tên", 100)
        clean_email, clean_phone = v.email(email), v.phone(phone)
        dept = v.required_text(department, "Khoa/bộ môn", 100)
        errors = violations(password)
        if errors:
            raise ValidationError(" ".join(errors))
        if self._lecturer_dao.exists(code) or self._account_dao.username_exists(code):
            raise ValidationError("Mã giảng viên đã tồn tại.")
        try:
            with self._lecturer_dao.transaction("tạo giảng viên") as conn:
                account_id = self._account_dao.insert(code, hash_password(password), Role.LECTURER, conn=conn)
                self._lecturer_dao.insert(Lecturer(code, account_id, name, clean_email, clean_phone, dept), conn=conn)
        except DuplicateRecordError as exc:
            raise ValidationError("Mã giảng viên hoặc tên đăng nhập đã tồn tại.") from exc
        created = self._lecturer_dao.find_by_id(code)
        if created is None:
            raise DataAccessError("Đã tạo giảng viên nhưng không đọc lại được hồ sơ.")
        return created

    def update(
        self, session: Session, lecturer_id: str, *, full_name: str, email: str, phone: str, department: str,
    ) -> Lecturer:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        current = self._lecturer_dao.find_by_id(lecturer_id)
        if current is None:
            raise ValidationError("Giảng viên không tồn tại.")
        self._lecturer_dao.update(Lecturer(
            current.lecturer_id, current.account_id,
            v.required_text(full_name, "Họ và tên", 100), v.email(email), v.phone(phone),
            v.required_text(department, "Khoa/bộ môn", 100),
        ))
        return self._lecturer_dao.find_by_id(lecturer_id)  # type: ignore[return-value]

    def delete(self, session: Session, lecturer_id: str) -> None:
        """Chặn xóa khi còn học phần phụ trách (RESTRICT); xóa hồ sơ + tài khoản trong một giao dịch."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        with self._lecturer_dao.transaction("xóa giảng viên") as conn:
            rows = self._lecturer_dao.query(
                "SELECT account_id FROM Lecturers WHERE lecturer_id = %s FOR UPDATE", (lecturer_id,), conn=conn
            )
            if not rows:
                raise ValidationError("Giảng viên không tồn tại.")
            if self._lecturer_dao.count_courses(lecturer_id, conn=conn) > 0:
                raise ValidationError("Không thể xóa giảng viên đang phụ trách ít nhất một học phần.")
            self._lecturer_dao.delete(lecturer_id, conn=conn)
            self._account_dao.delete(int(rows[0][0]), conn=conn)
