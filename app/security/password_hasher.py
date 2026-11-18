"""Băm và kiểm tra mật khẩu bằng PBKDF2-HMAC-SHA256.

Định dạng lưu trữ giữ nguyên như dữ liệu mẫu trong SQL:
``pbkdf2_sha256$<iterations>$<salt-base64>$<hash-base64>``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_ALGORITHM = "sha256"
_PREFIX = "pbkdf2_sha256"
_ITERATIONS = 210_000
_SALT_BYTES = 16
_KEY_BYTES = 32


def hash_password(raw_password: str) -> str:
    """Băm mật khẩu gốc với salt ngẫu nhiên mới."""
    if raw_password is None:
        raise ValueError("Mật khẩu không được null")
    salt = secrets.token_bytes(_SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        _ALGORITHM,
        raw_password.encode("utf-8"),
        salt,
        _ITERATIONS,
        dklen=_KEY_BYTES,
    )
    return "$".join(
        (
            _PREFIX,
            str(_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(derived_key).decode("ascii"),
        )
    )


def verify_password(raw_password: str | None, stored_hash: str | None) -> bool:
    """Kiểm tra mật khẩu gốc với chuỗi băm đã lưu."""
    if raw_password is None or stored_hash is None:
        return False
    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != _PREFIX:
        return False
    try:
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2], validate=True)
        expected = base64.b64decode(parts[3], validate=True)
    except (ValueError, TypeError):
        return False
    if iterations <= 0 or not salt or not expected:
        return False
    actual = hashlib.pbkdf2_hmac(
        _ALGORITHM,
        raw_password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected),
    )
    return hmac.compare_digest(expected, actual)
