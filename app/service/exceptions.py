"""Lỗi nghiệp vụ ở tầng service."""


class ServiceError(RuntimeError):
    """Lỗi nghiệp vụ có thông điệp hiển thị được cho người dùng."""


class AuthError(ServiceError):
    """Sai thông tin đăng nhập, tài khoản bị khóa hoặc phiên không hợp lệ."""


class ValidationError(ServiceError):
    """Dữ liệu người dùng nhập không hợp lệ."""
