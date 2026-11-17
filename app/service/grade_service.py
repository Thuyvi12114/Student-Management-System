"""Nghiệp vụ điểm số và kết quả học tập."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.dao.course_dao import CourseDAO
from app.dao.errors import DuplicateRecordError
from app.dao.grade_dao import GradeDAO
from app.dao.lecturer_dao import LecturerDAO
from app.dao.student_dao import StudentDAO
from app.models import (
    CourseGradeRow,
    CourseOption,
    GradeEntry,
    Role,
    StudentOption,
    course_average,
)
from app.security.session import Session
from app.service.exceptions import AuthorizationError, ValidationError

PASS_THRESHOLD = Decimal("5.00")
_WEIGHTED_AVERAGE = Decimal("0")


@dataclass(frozen=True)
class StudentResult:
    student: StudentOption
    grades: list[GradeEntry]
    gpa: Decimal | None
    total_credits: int
    passed_credits: int


@dataclass(frozen=True)
class CourseGradeSheet:
    course: CourseOption
    rows: list[CourseGradeRow]


class GradeService:
    """Tra cứu, nhập và cập nhật điểm; mọi ràng buộc nghiệp vụ nằm ở đây."""

    def __init__(
        self,
        grade_dao: GradeDAO,
        course_dao: CourseDAO,
        student_dao: StudentDAO,
        lecturer_dao: LecturerDAO,
    ) -> None:
        self._grade_dao = grade_dao
        self._course_dao = course_dao
        self._student_dao = student_dao
        self._lecturer_dao = lecturer_dao

    # ------------------------------------------------------------------
    # Truy vấn
    # ------------------------------------------------------------------
    def list_filter_options(
        self, session: Session
    ) -> tuple[list[StudentOption], list[CourseOption]]:
        """Danh sách cho bộ lọc của Admin (chỉ đọc)."""
        self._require_admin(session)
        return self._student_dao.list_options(), self._course_dao.list_all()

    def lecturer_courses(self, session: Session) -> list[CourseOption]:
        lecturer_id = self._require_lecturer(session)
        return self._course_dao.list_by_lecturer(lecturer_id)

    def course_grade_sheet(self, session: Session, course_id: int) -> CourseGradeSheet:
        course = self._course_dao.find_by_id(course_id)
        if course is None:
            raise ValidationError("Học phần không tồn tại.")

        if session.role is Role.ADMIN:
            pass
        elif session.role is Role.LECTURER:
            self._require_assigned_lecturer(session, course)
        else:
            raise AuthorizationError("Bạn không có quyền xem bảng điểm của học phần này.")

        return CourseGradeSheet(course, self._grade_dao.list_roster(course.course_id))

    def student_results(self, session: Session) -> StudentResult:
        """Kết quả học tập của chính sinh viên đang đăng nhập, kèm GPA theo tín chỉ."""
        if session.role is not Role.STUDENT:
            raise AuthorizationError("Chức năng này chỉ dành cho sinh viên.")

        student = self._student_dao.find_option_by_account(session.account_id)
        if student is None:
            raise ValidationError(
                "Tài khoản chưa được liên kết với hồ sơ sinh viên. "
                "Vui lòng liên hệ quản trị viên."
            )

        grades = self._grade_dao.list_for_student(student.student_id)
        graded = [grade for grade in grades if grade.final_score is not None]
        total_credits = sum(grade.credits for grade in graded)
        passed_credits = sum(
            grade.credits
            for grade in grades
            if grade.final_score is not None
            and grade.final_score >= PASS_THRESHOLD
        )

        gpa: Decimal | None = None
        if total_credits > 0:
            weighted_sum = sum(
                (grade.final_score * grade.credits for grade in graded),
                _WEIGHTED_AVERAGE,
            )
            gpa = (weighted_sum / total_credits).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        return StudentResult(
            student=student,
            grades=grades,
            gpa=gpa,
            total_credits=total_credits,
            passed_credits=passed_credits,
        )

    def admin_search(
        self,
        session: Session,
        student_id: int | None = None,
        course_id: int | None = None,
    ) -> list[GradeEntry]:
        """Tra cứu điểm chỉ đọc cho Admin, lọc theo sinh viên và/hoặc học phần."""
        self._require_admin(session)
        return self._grade_dao.search(student_id, course_id)

    # ------------------------------------------------------------------
    # Nhập / cập nhật điểm
    # ------------------------------------------------------------------
    def save_final_grade(
        self,
        session: Session,
        course_id: int,
        student_id: int,
        final_score: str,
        grade_id: int | None = None,
    ) -> None:
        """Ghi hoặc cập nhật duy nhất điểm cuối kỳ (thang 0–10)."""
        course = self._course_dao.find_by_id(course_id)
        if course is None:
            raise ValidationError("Học phần không tồn tại.")
        self._require_assigned_lecturer(session, course)

        if self._student_dao.find_option_by_id(student_id) is None:
            raise ValidationError("Sinh viên không tồn tại.")

        final = _parse_score(final_score, "Điểm cuối kỳ")
        if final is None:
            raise ValidationError("Vui lòng nhập điểm cuối kỳ.")
        status = _derive_status(final)

        if grade_id is None:
            existing = self._grade_dao.find_by_student_course(student_id, course_id)
            if existing is not None:
                raise ValidationError(
                    "Sinh viên đã có điểm cho học phần này. "
                    "Hãy chọn dòng tương ứng để cập nhật thay vì thêm mới."
                )
            try:
                self._grade_dao.insert(student_id, course_id, None, final, status)
            except DuplicateRecordError as exc:
                raise ValidationError(
                    "Sinh viên đã có điểm cho học phần này. "
                    "Hãy chọn dòng tương ứng để cập nhật."
                ) from exc
            return

        existing = self._grade_dao.find_by_id(grade_id)
        if existing is None:
            raise ValidationError("Bản ghi điểm không tồn tại.")
        if existing.student_id != student_id or existing.course_id != course_id:
            raise ValidationError("Bản ghi điểm không thuộc sinh viên/học phần đã chọn.")
        self._grade_dao.update(
            grade_id, existing.process_score, final, status
        )

    def save_grade(
        self,
        session: Session,
        course_id: int,
        student_id: int,
        process_score: str,
        final_score: str,
        grade_id: int | None = None,
    ) -> None:
        """Tương thích API cũ; giao diện hiện tại chỉ dùng điểm cuối kỳ."""
        self.save_final_grade(
            session, course_id, student_id, final_score, grade_id
        )

    # ------------------------------------------------------------------
    # Kiểm tra quyền
    # ------------------------------------------------------------------
    @staticmethod
    def _require_admin(session: Session) -> None:
        if session.role is not Role.ADMIN:
            raise AuthorizationError("Chức năng này chỉ dành cho quản trị viên.")

    def _require_lecturer(self, session: Session) -> int:
        if session.role is not Role.LECTURER:
            raise AuthorizationError("Chức năng này chỉ dành cho giảng viên.")
        lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
        if lecturer_id is None:
            raise AuthorizationError(
                "Tài khoản chưa được liên kết với hồ sơ giảng viên. "
                "Vui lòng liên hệ quản trị viên."
            )
        return lecturer_id

    def _require_assigned_lecturer(self, session: Session, course: CourseOption) -> None:
        lecturer_id = self._require_lecturer(session)
        if course.lecturer_id != lecturer_id:
            raise AuthorizationError(
                "Bạn không được phân công giảng dạy học phần này nên không thể "
                "nhập hoặc sửa điểm."
            )


def _parse_score(raw_value: str, label: str) -> Decimal | None:
    text = (raw_value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{label} phải là số (ví dụ 8.5).") from exc
    if not value.is_finite():
        raise ValidationError(f"{label} không hợp lệ.")
    if value < 0 or value > 10:
        raise ValidationError(f"{label} phải nằm trong khoảng 0 đến 10.")
    if -value.as_tuple().exponent > 2:
        raise ValidationError(f"{label} chỉ được có tối đa 2 chữ số thập phân.")
    return value.quantize(Decimal("0.01"))


def _derive_status(final: Decimal | None) -> str:
    if final is None:
        return "PENDING"
    return "PASSED" if final >= PASS_THRESHOLD else "FAILED"
