"""Hàm kiểm tra và chuẩn hóa dữ liệu đầu vào dùng chung cho các service."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.service.exceptions import ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^0\d{9,10}$")


def required_text(value: str | None, label: str, max_len: int = 255) -> str:
    text = (value or "").strip()
    if not text:
        raise ValidationError(f"{label} không được để trống.")
    if len(text) > max_len:
        raise ValidationError(f"{label} không được vượt quá {max_len} ký tự.")
    return text


def optional_text(value: str | None, label: str, max_len: int = 255) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > max_len:
        raise ValidationError(f"{label} không được vượt quá {max_len} ký tự.")
    return text


def identifier(value: str | None, label: str) -> str:
    text = required_text(value, label, 20)
    if not re.match(r"^[A-Za-z0-9]+$", text):
        raise ValidationError(f"{label} chỉ được chứa chữ cái và chữ số.")
    return text.upper()


def email(value: str | None) -> str:
    text = required_text(value, "Email", 100)
    if not _EMAIL_RE.match(text):
        raise ValidationError("Email không hợp lệ.")
    return text.lower()


def phone(value: str | None) -> str:
    text = required_text(value, "Số điện thoại", 15)
    digits = re.sub(r"\D", "", text)
    if not _PHONE_RE.match(digits):
        raise ValidationError("Số điện thoại không hợp lệ (phải bắt đầu bằng 0, 10–11 chữ số).")
    return digits


def gender(value: str | None) -> str:
    text = required_text(value, "Giới tính", 10)
    if text not in ("Male", "Female", "Nam", "Nữ", "Other"):
        raise ValidationError("Giới tính không hợp lệ (Male/Female/Other).")
    mapping = {"Nam": "Male", "Nữ": "Female"}
    return mapping.get(text, text)


def birth_date(value: date | str | None) -> date:
    if isinstance(value, date):
        d = value
    elif isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                d = datetime.strptime(value, fmt).date()
                break
            except ValueError:
                continue
        else:
            raise ValidationError("Ngày sinh không hợp lệ (định dạng YYYY-MM-DD).")
    else:
        raise ValidationError("Ngày sinh không được để trống.")

    today = date.today()
    if d >= today:
        raise ValidationError("Ngày sinh phải nhỏ hơn ngày hiện tại.")
    age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    if age < 15 or age > 100:
        raise ValidationError("Tuổi sinh viên phải từ 15 đến 100.")
    return d
