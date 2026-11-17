"""UC-15 Xem điểm, UC-16 Quản lý điểm, UC-17 Xem điểm của mình (Module 6)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.dao.course_dao import CourseDAO
from app.dao.grade_dao import GradeDAO
from app.dao.lecturer_dao import LecturerDAO
from app.dao.student_dao import StudentDAO
from app.models import (
    CourseGradeRow, CourseOption, GradeEntry, Role, StudentOption, StudentRecord, weighted_gpa,
)
from app.security.session import Session
from app.service import validators as v
from app.service.exceptions import AuthorizationError, ValidationError


@dataclass(frozen=True)
class StudentResult:
    student: StudentRecord
    grades: list[GradeEntry]
    gpa: Decimal | None
    total_credits: int
    passed_credits: int


@dataclass(frozen=True)
class CourseGradeSheet:
    course: CourseOption
    rows: list[CourseGradeRow]


class GradeService:
    def __init__(self, grade_dao: GradeDAO, course_dao: CourseDAO, student_dao: StudentDAO, lecturer_dao: LecturerDAO) -> None:
        self._grade_dao = grade_dao
        self._course_dao = course_dao
        self._student_dao = student_dao
        self._lecturer_dao = lecturer_dao

    def list_filter_options(self, session: Session) -> tuple[list[StudentOption], list[CourseOption]]:
        self._require_admin(session)
        return self._student_dao.list_options(), self._course_dao.list_all()

    def lecturer_courses(self, session: Session) -> list[CourseOption]:
        return self._course_dao.list_by_lecturer(self._require_lecturer(session))

    def course_grade_sheet(self, session: Session, course_id: str) -> CourseGradeSheet:
        course = self._course_dao.find_by_id(course_id)
        if course is None:
            raise ValidationError("Học phần không tồn tại.")
        if session.role is Role.LECTURER:
            self._require_assigned(session, course)
        elif session.role is not Role.ADMIN:
            raise AuthorizationError("Bạn không có quyền xem bảng điểm của học phần này.")
        return CourseGradeSheet(course, self._grade_dao.list_roster(course.course_id))

    def student_results(self, session: Session) -> StudentResult:
        """UC-17: kết quả của chính sinh viên đăng nhập; GPA = Σ(điểm × tín chỉ) / Σ tín chỉ."""
        if session.role is not Role.STUDENT:
            raise AuthorizationError("Chức năng này chỉ dành cho sinh viên.")
        student = self._student_dao.find_by_account(session.account_id)
        if student is None:
            raise ValidationError("Tài khoản chưa được liên kết với hồ sơ sinh viên. Vui lòng liên hệ quản trị viên.")
        grades = self._grade_dao.list_for_student(student.student_id)
        return StudentResult(
            student=student, grades=grades, gpa=weighted_gpa(grades),
            total_credits=sum(g.credits for g in grades),
            passed_credits=sum(g.credits for g in grades if g.passed),
        )

    def admin_search(self, session: Session, student_id: str | None = None, course_id: str | None = None) -> list[GradeEntry]:
        """UC-15: Admin chỉ xem điểm, không sửa."""
        self._require_admin(session)
        return self._grade_dao.search(student_id, course_id)

    def save_grade(self, session: Session, course_id: str, student_id: str, grade_value: str | Decimal) -> int:
        """UC-16: giảng viên nhập/sửa điểm cho học phần mình phụ trách; mỗi cặp SV–học phần một điểm."""
        course = self._course_dao.find_by_id(course_id)
        if course is None:
            raise ValidationError("Học phần không tồn tại.")
        self._require_assigned(session, course)
        if self._student_dao.find_by_id(student_id) is None:
            raise ValidationError("Sinh viên không tồn tại.")
        return self._grade_dao.upsert(student_id, course_id, v.grade_value(grade_value))

    @staticmethod
    def _require_admin(session: Session) -> None:
        if session.role is not Role.ADMIN or session.is_expired():
            raise AuthorizationError("Chức năng này chỉ dành cho quản trị viên.")

    def _require_lecturer(self, session: Session) -> str:
        if session.role is not Role.LECTURER or session.is_expired():
            raise AuthorizationError("Chức năng này chỉ dành cho giảng viên.")
        lecturer_id = self._lecturer_dao.find_id_by_account(session.account_id)
        if lecturer_id is None:
            raise AuthorizationError("Tài khoản chưa được liên kết với hồ sơ giảng viên. Vui lòng liên hệ quản trị viên.")
        return lecturer_id

    def _require_assigned(self, session: Session, course: CourseOption) -> None:
        if self._require_lecturer(session) != course.lecturer_id:
            raise AuthorizationError("Bạn không được phân công giảng dạy học phần này nên không thể nhập hoặc sửa điểm.")
