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
        "Xem tài khoản sinh viên/giảng viên, khóa hoặc mở khóa và đặt lại mật khẩu.",
        frozenset({Role.ADMIN}),
    )
    STUDENT_MANAGEMENT = (
        "Quản lý sinh viên",
        "Thêm, sửa, xóa hồ sơ sinh viên; tài khoản đăng nhập được tạo/xóa cùng hồ sơ.",
        frozenset({Role.ADMIN}),
    )
    LECTURER_MANAGEMENT = (
        "Quản lý giảng viên",
        "Hồ sơ giảng viên, khoa/bộ môn; tài khoản được tạo/xóa cùng hồ sơ.",
        frozenset({Role.ADMIN}),
    )
    COURSE_MANAGEMENT = (
        "Học phần",
        "Admin quản lý danh mục; giảng viên xem học phần được phân công; sinh viên xem danh mục.",
        frozenset({Role.ADMIN, Role.LECTURER, Role.STUDENT}),
    )
    LECTURER_STUDENT_SEARCH = (
        "Tra cứu sinh viên",
        "Tìm sinh viên theo mã, họ tên, lớp; chỉ hiển thị mã sinh viên, họ tên và lớp.",
        frozenset({Role.LECTURER}),
    )
    ADMIN_GRADE_LOOKUP = (
        "Tra cứu điểm",
        "Xem bảng điểm toàn hệ thống và lọc theo sinh viên hoặc học phần (chỉ đọc).",
        frozenset({Role.ADMIN}),
    )
    GRADE_MANAGEMENT = (
        "Nhập & cập nhật điểm",
        "Nhập và cập nhật điểm cho sinh viên thuộc học phần được phân công.",
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
        "Hồ sơ cá nhân",
        "Xem hồ sơ của mình; sinh viên cập nhật email, số điện thoại, địa chỉ; đổi mật khẩu.",
        frozenset({Role.LECTURER, Role.STUDENT}),
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
