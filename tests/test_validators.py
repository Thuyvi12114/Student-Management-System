"""Unit tests for student input validation."""
from datetime import date
import pytest
from app.service.validators import (
    identifier,
    email,
    phone,
    gender,
    birth_date
)
from app.service.exceptions import ValidationError

# 1. Test student ID validation
def test_identifier_normalizes_to_uppercase():
    assert identifier(" sv001 ", "Student ID") == "SV001"
@pytest.mark.parametrize("value", ["", "SV 01", "SV@01", "A" * 21])
def test_identifier_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        identifier(value, "Student ID")

# 2. Test email validation
def test_email_normalizes_to_lowercase():
    assert email("TEST@EXAMPLE.COM") == "test@example.com"
@pytest.mark.parametrize("value", ["abc", "a@", "", "a b@x.com"])
def test_email_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        email(value)

# 3. Test phone validation
def test_phone_accepts_valid_number():
    assert phone("0901234567") == "0901234567"
@pytest.mark.parametrize("value", ["12", "abc", "", "phone123"])
def test_phone_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        phone(value)

# 4. Test gender validation
@pytest.mark.parametrize("value", ["Nam", "Nữ", "Khác"])
def test_gender_accepts_allowed_value(value):
    assert gender(value) == value
def test_gender_rejects_other_value():
    with pytest.raises(ValidationError):
        gender("Không xác định")

# 5. Test date of birth validation
def test_birth_date_accepts_ddmmyyyy():
    assert birth_date("15/08/2006") == date(2006, 8, 15)
@pytest.mark.parametrize(
    "value",
    ["31/02/2006", "01/01/2099", "", "not-a-date"]
)
def test_birth_date_rejects_invalid_value(value):
    with pytest.raises(ValidationError):
        birth_date(value)
