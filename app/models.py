"""Thực thể ánh xạ các bảng trong cơ sở dữ liệu."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class Role(str, Enum):
    """Ba vai trò, khớp ràng buộc CHECK của UserAccounts.Role."""

    ADMIN = "ADMIN"
    LECTURER = "LECTURER"
    STUDENT = "STUDENT"

    @property
    def label(self) -> str:
        return {
            self.ADMIN: "Quản trị viên",
            self.LECTURER: "Giảng viên",
            self.STUDENT: "Sinh viên",
        }[self]

    @property
    def description(self) -> str:
        return {
            self.ADMIN: "Toàn quyền quản lý tài khoản, sinh viên, giảng viên, môn học và điểm.",
            self.LECTURER: "Quản lý môn học được phân công và nhập điểm cho sinh viên.",
            self.STUDENT: "Xem thông tin cá nhân, môn học và kết quả học tập của mình.",
        }[self]

    @classmethod
    def from_db(cls, value: str | None) -> "Role":
        try:
            return cls(str(value).upper())
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Vai trò không hợp lệ: {value}") from exc


class AccountStatus(str, Enum):
    """Trạng thái tài khoản, khớp ràng buộc CHECK của UserAccounts.Status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    @property
    def label(self) -> str:
        return "Active" if self is AccountStatus.ACTIVE else "Inactive"

    @classmethod
    def from_db(cls, value: str | None) -> "AccountStatus":
        try:
            return cls(str(value).upper())
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Trạng thái tài khoản không hợp lệ: {value}") from exc


@dataclass(frozen=True)
class UserAccount:
    """Bản ghi bảng UserAccounts."""

    account_id: int
    username: str
    password_hash: str
    full_name: str
    role: Role
    status: AccountStatus
    last_login_at: datetime | None
    created_at: datetime | None

    @property
    def is_active(self) -> bool:
        return self.status is AccountStatus.ACTIVE


@dataclass(frozen=True)
class AccountSummary:
    """Account fields safe for the Admin account list; excludes password data."""

    account_id: int
    username: str
    full_name: str
    role: Role
    status: AccountStatus


@dataclass(frozen=True)
class Student:
    student_id: int
    account_id: int
    student_code: str
    full_name: str
    gender: str
    date_of_birth: date
    email: str
    phone: str | None
    class_name: str
    enrollment_year: int


@dataclass(frozen=True)
class Lecturer:
    lecturer_id: int
    account_id: int
    lecturer_code: str
    full_name: str
    gender: str
    date_of_birth: date
    email: str
    phone: str | None
    department: str
    degree: str


@dataclass(frozen=True)
class LecturerSearchResult:
    items: list[Lecturer]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class Course:
    course_id: int
    course_code: str
    course_name: str
    credits: int
    lecturer_id: int | None
    semester: str
    academic_year: str


@dataclass(frozen=True)
class Grade:
    grade_id: int
    student_id: int
    course_id: int
    process_score: Decimal | None
    final_score: Decimal | None
    status: str


def course_average(process_score: Decimal | None, final_score: Decimal | None) -> Decimal | None:
    """Điểm trung bình học phần: 40% quá trình + 60% cuối kỳ."""
    if process_score is None or final_score is None:
        return None
    return (process_score * Decimal("0.4") + final_score * Decimal("0.6")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


@dataclass(frozen=True)
class StudentOption:
    """Sinh viên dùng cho bộ lọc và bảng điểm."""

    student_id: int
    student_code: str
    full_name: str
    class_name: str


@dataclass(frozen=True)
class StudentSearchResult:
    """Kết quả tìm kiếm sinh viên có hỗ trợ phân trang phía server."""

    items: list["StudentRecord"]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class LecturerStudent:
    """Thông tin sinh viên được phép hiển thị cho giảng viên."""

    student_id: int
    full_name: str
    class_name: str


@dataclass(frozen=True)
class LecturerStudentSearchResult:
    items: list[LecturerStudent]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class StudentRecord:
    """Thông tin sinh viên đầy đủ theo các cột hiện có trong bảng Students."""

    student_id: int
    account_id: int
    student_code: str
    full_name: str
    gender: str
    date_of_birth: date
    email: str
    phone: str | None
    class_name: str
    enrollment_year: int


@dataclass(frozen=True)
class DashboardStats:
    """Thống kê nhanh cho dashboard."""

    total_students: int = 0
    total_lecturers: int = 0
    total_courses: int = 0
    total_classes: int = 0
    assigned_courses: int = 0


@dataclass(frozen=True)
class CourseOption:
    """Học phần kèm giảng viên phụ trách."""

    course_id: int
    course_code: str
    course_name: str
    credits: int
    semester: str
    academic_year: str
    lecturer_id: int | None
    lecturer_name: str | None

    @property
    def label(self) -> str:
        return f"{self.course_code} - {self.course_name} ({self.credits} TC, {self.semester} {self.academic_year})"


@dataclass(frozen=True)
class CourseSearchResult:
    items: list[CourseOption]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class GradeEntry:
    """Một dòng điểm đã nhập, kèm thông tin sinh viên và học phần."""

    grade_id: int
    student_id: int
    student_code: str
    student_name: str
    course_id: int
    course_code: str
    course_name: str
    credits: int
    semester: str
    academic_year: str
    process_score: Decimal | None
    final_score: Decimal | None
    status: str

    @property
    def average_score(self) -> Decimal | None:
        return course_average(self.process_score, self.final_score)


@dataclass(frozen=True)
class CourseGradeRow:
    """Sinh viên trong danh sách học phần; grade_id null nếu chưa nhập điểm."""

    student_id: int
    student_code: str
    student_name: str
    grade_id: int | None
    process_score: Decimal | None
    final_score: Decimal | None
    status: str | None

    @property
    def average_score(self) -> Decimal | None:
        return course_average(self.process_score, self.final_score)
