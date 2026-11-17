"""Thực thể ánh xạ 5 bảng của tài liệu thiết kế: UserAccounts, Students, Lecturers, Courses, Grades."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

GENDERS = ("Nam", "Nữ", "Khác")
PASS_THRESHOLD = Decimal("5.00")


class Role(str, Enum):
    """Ba vai trò; giá trị khớp ENUM của UserAccounts.role."""

    ADMIN = "Administrator"
    LECTURER = "Lecturer"
    STUDENT = "Student"

    @property
    def label(self) -> str:
        return {
            Role.ADMIN: "Quản trị viên",
            Role.LECTURER: "Giảng viên",
            Role.STUDENT: "Sinh viên",
        }[self]

    @property
    def description(self) -> str:
        return {
            Role.ADMIN: "Quản lý sinh viên, giảng viên, học phần, tài khoản và xem điểm.",
            Role.LECTURER: "Xem học phần được phân công và nhập điểm cho sinh viên.",
            Role.STUDENT: "Xem hồ sơ, cập nhật liên hệ và xem kết quả học tập của mình.",
        }[self]

    @classmethod
    def from_db(cls, value: str | None) -> "Role":
        text = str(value or "").strip().lower()
        for role in cls:
            if role.value.lower() == text:
                return role
        raise ValueError(f"Vai trò không hợp lệ: {value}")


class AccountStatus(str, Enum):
    """Trạng thái tài khoản; giá trị khớp ENUM của UserAccounts.status."""

    ACTIVE = "Active"
    INACTIVE = "Inactive"

    @property
    def label(self) -> str:
        return "Đang hoạt động" if self is AccountStatus.ACTIVE else "Đã khóa"

    @classmethod
    def from_db(cls, value: str | None) -> "AccountStatus":
        text = str(value or "").strip().lower()
        for status in cls:
            if status.value.lower() == text:
                return status
        raise ValueError(f"Trạng thái tài khoản không hợp lệ: {value}")


@dataclass(frozen=True)
class UserAccount:
    """Bản ghi UserAccounts; full_name lấy từ hồ sơ Students/Lecturers để hiển thị."""

    account_id: int
    username: str
    password_hash: str
    role: Role
    status: AccountStatus
    full_name: str = ""

    @property
    def is_active(self) -> bool:
        return self.status is AccountStatus.ACTIVE


@dataclass(frozen=True)
class AccountSummary:
    """Dòng danh sách tài khoản cho Admin (không có mật khẩu)."""

    account_id: int
    username: str
    full_name: str
    role: Role
    status: AccountStatus


@dataclass(frozen=True)
class StudentRecord:
    """Hồ sơ sinh viên (bảng Students). student_id là mã sinh viên và cũng là username."""

    student_id: str
    account_id: int
    full_name: str
    date_of_birth: date
    gender: str
    email: str
    phone: str
    address: str | None
    class_name: str

    @property
    def student_code(self) -> str:
        return self.student_id


Student = StudentRecord


@dataclass(frozen=True)
class StudentOption:
    """Sinh viên rút gọn dùng cho bộ lọc và bảng điểm."""

    student_id: str
    full_name: str
    class_name: str

    @property
    def student_code(self) -> str:
        return self.student_id


@dataclass(frozen=True)
class StudentSearchResult:
    items: list[StudentRecord]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class LecturerStudent:
    """UC-01: giảng viên chỉ được thấy mã sinh viên, họ tên và lớp."""

    student_id: str
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
class Lecturer:
    """Hồ sơ giảng viên (bảng Lecturers). lecturer_id là mã giảng viên và cũng là username."""

    lecturer_id: str
    account_id: int
    full_name: str
    email: str
    phone: str
    department: str

    @property
    def lecturer_code(self) -> str:
        return self.lecturer_id


@dataclass(frozen=True)
class LecturerSearchResult:
    items: list[Lecturer]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class CourseOption:
    """Học phần kèm tên giảng viên phụ trách."""

    course_id: str
    course_name: str
    credits: int
    lecturer_id: str
    lecturer_name: str
    description: str | None = None

    @property
    def course_code(self) -> str:
        return self.course_id

    @property
    def label(self) -> str:
        return f"{self.course_id} - {self.course_name} ({self.credits} TC)"


Course = CourseOption


@dataclass(frozen=True)
class CourseSearchResult:
    items: list[CourseOption]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class GradeEntry:
    """Một điểm đã nhập, kèm thông tin sinh viên và học phần."""

    grade_id: int
    student_id: str
    student_name: str
    course_id: str
    course_name: str
    credits: int
    grade_value: Decimal

    @property
    def student_code(self) -> str:
        return self.student_id

    @property
    def course_code(self) -> str:
        return self.course_id

    @property
    def passed(self) -> bool:
        return self.grade_value >= PASS_THRESHOLD


Grade = GradeEntry


@dataclass(frozen=True)
class CourseGradeRow:
    """Sinh viên trong bảng điểm của một học phần; grade_id/grade_value là None nếu chưa có điểm."""

    student_id: str
    student_name: str
    class_name: str
    grade_id: int | None
    grade_value: Decimal | None

    @property
    def student_code(self) -> str:
        return self.student_id


@dataclass(frozen=True)
class DashboardStats:
    total_students: int = 0
    total_lecturers: int = 0
    total_courses: int = 0
    total_classes: int = 0
    assigned_courses: int = 0
    graded_entries: int = 0     # số điểm đã nhập trong các học phần của giảng viên
    expected_entries: int = 0   # số học phần × số sinh viên


def weighted_gpa(entries: list[GradeEntry]) -> Decimal | None:
    """GPA = Σ(điểm × tín chỉ) / Σ tín chỉ (thang 10), làm tròn 2 chữ số."""
    credits = sum(entry.credits for entry in entries)
    if credits == 0:
        return None
    total = sum(entry.grade_value * entry.credits for entry in entries)
    return (total / credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
