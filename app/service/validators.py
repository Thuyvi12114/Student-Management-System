"""Kiểm tra và chuẩn hóa dữ liệu nhập; mỗi hàm trả về giá trị sạch hoặc ném ValidationError."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models import GENDERS
from app.service.exceptions import ValidationError

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,20}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9 .\-]{6,18}[0-9]$")


def required_text(value: Any, label: str, max_length: int = 255) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValidationError(f"{label} không được để trống.")
    if len(text) > max_length:
        raise ValidationError(f"{label} tối đa {max_length} ký tự.")
    return text


def optional_text(value: Any, label: str, max_length: int = 255) -> str | None:
    text = ("" if value is None else str(value)).strip()
    if not text:
        return None
    if len(text) > max_length:
        raise ValidationError(f"{label} tối đa {max_length} ký tự.")
    return text


def identifier(value: Any, label: str) -> str:
    text = required_text(value, label, 20).upper()
    if not _ID_RE.match(text):
        raise ValidationError(f"{label} chỉ gồm chữ, số, dấu gạch ngang/gạch dưới (tối đa 20 ký tự).")
    return text


def email(value: Any, label: str = "Email") -> str:
    text = required_text(value, label, 254)
    if not _EMAIL_RE.match(text):
        raise ValidationError(f"{label} không đúng định dạng.")
    return text.lower()


def phone(value: Any, label: str = "Số điện thoại") -> str:
    text = required_text(value, label, 20)
    if not _PHONE_RE.match(text):
        raise ValidationError(f"{label} không hợp lệ (8-15 chữ số).")
    return text


def gender(value: Any) -> str:
    text = required_text(value, "Giới tính", 20)
    if text not in GENDERS:
        raise ValidationError("Giới tính phải là Nam, Nữ hoặc Khác.")
    return text


def birth_date(value: Any) -> date:
    """Nhận date hoặc chuỗi dd/mm/yyyy hay yyyy-mm-dd."""
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = ("" if value is None else str(value)).strip()
        if not text:
            raise ValidationError("Ngày sinh không được để trống.")
        parsed = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValidationError("Ngày sinh phải có dạng dd/mm/yyyy.")
    if parsed >= date.today() or parsed.year < 1900:
        raise ValidationError("Ngày sinh không hợp lệ.")
    return parsed


def grade_value(value: Any) -> Decimal:
    """Điểm thang 0-10, tối đa 2 chữ số thập phân (không tự làm tròn: 8.555 bị từ chối)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError("Điểm không được để trống.")
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation:
        raise ValidationError("Điểm phải là một số.") from None
    if not number.is_finite():
        raise ValidationError("Điểm phải là một số.")
    if number < 0 or number > 10:
        raise ValidationError("Điểm phải nằm trong khoảng từ 0 đến 10.")
    if number != number.quantize(Decimal("0.01")):
        raise ValidationError("Điểm chỉ được có tối đa 2 chữ số thập phân.")
    return number.quantize(Decimal("0.01"))


def credits(value: Any) -> int:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValidationError("Số tín chỉ không được để trống.")
    try:
        number = int(text)
    except ValueError:
        raise ValidationError("Số tín chỉ phải là số nguyên.") from None
    if not 1 <= number <= 10:
        raise ValidationError("Số tín chỉ phải nằm trong khoảng 1 đến 10.")
    return number
