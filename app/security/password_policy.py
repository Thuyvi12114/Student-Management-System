"""Quy tắc độ mạnh mật khẩu dùng cho chức năng đổi mật khẩu."""

from __future__ import annotations

MIN_LENGTH = 8


def violations(password: str | None) -> list[str]:
    """Trả về danh sách lỗi; danh sách rỗng nghĩa là mật khẩu hợp lệ."""
    errors: list[str] = []
    if not password or not password.strip():
        return ["Mật khẩu mới không được để trống."]
    if len(password) < MIN_LENGTH:
        errors.append(f"Mật khẩu phải có ít nhất {MIN_LENGTH} ký tự.")
    if not any(character.isupper() for character in password):
        errors.append("Mật khẩu phải có ít nhất một chữ in hoa.")
    if not any(character.islower() for character in password):
        errors.append("Mật khẩu phải có ít nhất một chữ thường.")
    if not any(character.isdigit() for character in password):
        errors.append("Mật khẩu phải có ít nhất một chữ số.")
    if any(character.isspace() for character in password):
        errors.append("Mật khẩu không được chứa khoảng trắng.")
    return errors
