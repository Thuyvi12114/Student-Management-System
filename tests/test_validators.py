"""Unit test cho các hàm kiểm tra dữ liệu đầu vào."""
from datetime import date
from decimal import Decimal

import pytest

from app.service.validators import (
    identifier, email, phone, gender, birth_date, grade_value, credits
)
from app.service.exceptions import ValidationError


def test_identifier_normalizes_to_uppercase():
    assert identifier(" sv001 ", "Mã") == "SV001"


@pytest.mark.parametrize("value", ["", "SV 01", "SV@01", "A" * 21])
def test_identifier_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        identifier(value, "Mã")


def test_email_normalizes_to_lowercase():
    assert email("TEST@EXAMPLE.COM") == "test@example.com"


@pytest.mark.parametrize("value", ["abc", "a@", "", "a b@x.com"])
def test_email_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        email(value)


def test_phone_accepts_valid_number():
    assert phone("0901234567") == "0901234567"


@pytest.mark.parametrize("value", ["12", "abc", "", "phone123"])
def test_phone_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        phone(value)


@pytest.mark.parametrize("value", ["Nam", "Nữ", "Khác"])
def test_gender_accepts_allowed_value(value):
    assert gender(value) == value


def test_gender_rejects_other_value():
    with pytest.raises(ValidationError):
        gender("Không xác định")


def test_birth_date_accepts_ddmmyyyy():
    assert birth_date("15/08/2006") == date(2006, 8, 15)


@pytest.mark.parametrize("value", ["31/02/2006", "01/01/2099", "", "not-a-date"])
def test_birth_date_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        birth_date(value)


@pytest.mark.parametrize("value,expected", [("8", Decimal("8.00")), ("8,25", Decimal("8.25")), ("0", Decimal("0.00")), ("10", Decimal("10.00"))])
def test_grade_value_accepts_valid_range(value, expected):
    assert grade_value(value) == expected


@pytest.mark.parametrize("value", ["", "abc", "-1", "10.01", "8.555", "NaN"])
def test_grade_value_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        grade_value(value)


@pytest.mark.parametrize("value,expected", [(1, 1), ("3", 3), (10, 10)])
def test_credits_accepts_valid_range(value, expected):
    assert credits(value) == expected


@pytest.mark.parametrize("value", [0, -1, 11, "abc", ""])
def test_credits_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        credits(value)
