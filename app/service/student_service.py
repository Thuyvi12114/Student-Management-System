"""UC-09/10/11/18/19 Quản lý sinh viên - thêm, sửa, xóa (Module 3, Nghĩa)."""

from __future__ import annotations

from datetime import date

from app.dao.errors import DataAccessError, DuplicateRecordError
from app.dao.student_dao import StudentDAO
from app.dao.user_account_dao import UserAccountDAO
from app.models import Role, StudentRecord
from app.security.password_hasher import hash_password
from app.security.password_policy import violations
from app.security.session import Session
from app.service import validators as v
from app.service.access import require_role
from app.service.exceptions import ValidationError

_ADMIN_ONLY = "Chỉ quản trị viên mới được quản lý sinh viên."


class StudentService:
    def __init__(self, student_dao: StudentDAO, user_account_dao: UserAccountDAO) -> None:
        self._student_dao = student_dao
        self._account_dao = user_account_dao

    # ---- UC-19 --------------------------------------------------------
    def is_student_id_available(self, session: Session, student_id: str) -> bool:
        """UC-19 Check Duplicate Student ID: chỉ đọc, không sửa dữ liệu."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        code = v.identifier(student_id, "Mã sinh viên")
        return not self._student_dao.exists(code) and not self._account_dao.username_exists(code)

    # ---- UC-09 --------------------------------------------------------
    def create(
        self, session: Session, *, student_id: str, full_name: str, gender: str, date_of_birth: date | str,
        email: str, phone: str, address: str | None, class_name: str, password: str,
    ) -> StudentRecord:
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        code = v.identifier(student_id, "Mã sinh viên")
        clean = self._clean(full_name, gender, date_of_birth, email, phone, address, class_name)
        errors = violations(password)
        if errors:
            raise ValidationError(" ".join(errors))
        if self._student_dao.exists(code):  # AF1
            raise ValidationError("Mã sinh viên đã tồn tại.")
        if self._account_dao.username_exists(code):  # AF2
            raise ValidationError("Tên đăng nhập trùng mã sinh viên đã được tài khoản khác sử dụng.")
        try:
            # Một giao dịch duy nhất: tài khoản + hồ sơ, lỗi bất kỳ thì rollback cả hai (AF4).
            with self._student_dao.transaction("tạo sinh viên") as conn:
                account_id = self._account_dao.insert(code, hash_password(password), Role.STUDENT, conn=conn)
                self._student_dao.insert(StudentRecord(code, account_id, **clean), conn=conn)
        except DuplicateRecordError as exc:
            raise ValidationError("Mã sinh viên hoặc tên đăng nhập đã tồn tại.") from exc
        created = self._student_dao.find_by_id(code)
        if created is None:
            raise DataAccessError("Đã tạo sinh viên nhưng không đọc lại được hồ sơ.")
        return created

    # ---- UC-10 --------------------------------------------------------
    def update(
        self, session: Session, student_id: str, *, full_name: str, gender: str, date_of_birth: date | str,
        email: str, phone: str, address: str | None, class_name: str,
    ) -> StudentRecord:
        """Mã sinh viên và account_id bất biến; các trường còn lại được sửa."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        current = self._student_dao.find_by_id(student_id)
        if current is None:  # AF1
            raise ValidationError("Sinh viên không tồn tại.")
        clean = self._clean(full_name, gender, date_of_birth, email, phone, address, class_name)
        self._student_dao.update(StudentRecord(current.student_id, current.account_id, **clean))
        return self._student_dao.find_by_id(student_id)  # type: ignore[return-value]

    # ---- UC-11 (+ UC-18 xác nhận ở giao diện) ----------------------------
    def can_delete(self, session: Session, student_id: str) -> None:
        """Bước kiểm tra trước khi hỏi xác nhận: tồn tại và không còn điểm (AF1/AF3)."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        if self._student_dao.find_by_id(student_id) is None:
            raise ValidationError("Sinh viên không tồn tại.")
        if self._student_dao.count_grades(student_id) > 0:
            raise ValidationError(
                "Không thể xóa sinh viên đã có bản ghi điểm. Hãy giữ hồ sơ để bảo toàn lịch sử học tập."
            )

    def delete(self, session: Session, student_id: str) -> None:
        """Xóa hồ sơ và tài khoản trong một giao dịch; khóa dòng để tránh điểm xuất hiện giữa chừng."""
        require_role(session, Role.ADMIN, _ADMIN_ONLY)
        with self._student_dao.transaction("xóa sinh viên") as conn:
            row = self._student_dao.query(
                "SELECT account_id FROM Students WHERE student_id = %s FOR UPDATE", (student_id,), conn=conn
            )
            if not row:
                raise ValidationError("Sinh viên không tồn tại.")
            if self._student_dao.count_grades(student_id, conn=conn) > 0:
                raise ValidationError(
                    "Không thể xóa sinh viên đã có bản ghi điểm. Hãy giữ hồ sơ để bảo toàn lịch sử học tập."
                )
            self._student_dao.delete(student_id, conn=conn)
            self._account_dao.delete(int(row[0][0]), conn=conn)

    @staticmethod
    def _clean(full_name, gender, date_of_birth, email, phone, address, class_name) -> dict:
        return {
            "full_name": v.required_text(full_name, "Họ và tên", 100),
            "date_of_birth": v.birth_date(date_of_birth),
            "gender": v.gender(gender),
            "email": v.email(email),
            "phone": v.phone(phone),
            "address": v.optional_text(address, "Địa chỉ", 255),
            "class_name": v.required_text(class_name, "Lớp", 50),
        }
