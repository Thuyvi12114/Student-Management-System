"""Thực thể ánh xạ các bảng trong cơ sở dữ liệu."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
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
