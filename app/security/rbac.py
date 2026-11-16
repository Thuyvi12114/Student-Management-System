"""Phân quyền theo vai trò (RBAC) cho khung điều hướng."""

from __future__ import annotations

from enum import Enum

from app.models import Role


class AppModule(Enum):
    """Module trên giao diện kèm các vai trò được phép truy cập."""

    DASHBOARD = (
        "Tổng quan",
        "Trang tổng quan hiển thị thông tin phiên đăng nhập và các chức năng theo vai trò.",
        frozenset({Role.ADMIN, Role.LECTURER, Role.STUDENT}),
    )
    ACCOUNT_MANAGEMENT = (
        "Tài khoản & phân quyền",
        "Tạo, khóa/mở khóa tài khoản và gán vai trò Admin, Giảng viên, Sinh viên.",
        frozenset({Role.ADMIN}),
    )
    STUDENT_MANAGEMENT = (
        "Quản lý sinh viên",
        "Hồ sơ sinh viên, lớp học, thông tin liên hệ gắn với tài khoản đăng nhập.",
        frozenset({Role.ADMIN}),
    )
    LECTURER_MANAGEMENT = (
        "Quản lý giảng viên",
        "Hồ sơ giảng viên, khoa/bộ môn và phân công giảng dạy.",
        frozenset({Role.ADMIN}),
    )
    COURSE_MANAGEMENT = (
        "Quản lý môn học",
        "Danh mục môn học, số tín chỉ, học kỳ, năm học và giảng viên phụ trách.",
        frozenset({Role.ADMIN, Role.LECTURER}),
    )
    ADMIN_GRADE_LOOKUP = (
        "Tra cứu điểm",
        "Xem bảng điểm toàn hệ thống và lọc theo sinh viên hoặc học phần (chỉ đọc).",
        frozenset({Role.ADMIN}),
    )
    GRADE_MANAGEMENT = (
        "Nhập & cập nhật điểm",
        "Nhập điểm quá trình, điểm cuối kỳ và cập nhật điểm cho sinh viên.",
        frozenset({Role.LECTURER}),
    )
    LECTURER_COURSE_GRADES = (
        "Học phần & điểm",
        "Xem chi tiết học phần được phân công và bảng điểm sinh viên.",
        frozenset({Role.LECTURER}),
    )
    MY_GRADES = (
        "Kết quả học tập",
        "Xem bảng điểm và điểm trung bình tích lũy theo tín chỉ của sinh viên.",
        frozenset({Role.STUDENT}),
    )
    PROFILE = (
        "Thông tin cá nhân",
        "Xem thông tin tài khoản đang đăng nhập và đổi mật khẩu.",
        frozenset({Role.ADMIN, Role.LECTURER, Role.STUDENT}),
    )

    def __init__(self, label: str, description: str, allowed_roles: frozenset[Role]) -> None:
        self.label = label
        self.description = description
        self.allowed_roles = allowed_roles

    @property
    def allowed_roles_label(self) -> str:
        order = {Role.ADMIN: 0, Role.LECTURER: 1, Role.STUDENT: 2}
        return ", ".join(role.label for role in sorted(self.allowed_roles, key=order.get))


class RbacPolicy:
    """Ma trận phân quyền; mọi thao tác mở module đều phải đi qua can_access."""

    @staticmethod
    def navigation_for(role: Role) -> list[AppModule]:
        return [module for module in AppModule if role in module.allowed_roles]

    @staticmethod
    def can_access(role: Role | None, module: AppModule | None) -> bool:
        if role is None or module is None:
            return False
        return role in module.allowed_roles
