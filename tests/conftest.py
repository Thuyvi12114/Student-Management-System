"""Cấu hình pytest: dùng CSDL RIÊNG để test (mặc định student_management_test).

Chạy:  python -m pytest -q          (cần MySQL/MariaDB đang chạy, xem config.ini hoặc biến SMS_DB_*)
Đổi CSDL test:  SMS_DB_NAME=ten_khac python -m pytest -q
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SMS_DB_NAME", "student_management_test")
os.environ.setdefault("SMS_DB_HOST", "127.0.0.1")

from app.config import DatabaseConfig  # noqa: E402
from app.context import AppContext  # noqa: E402

SCRIPT = (ROOT / "database" / "student_management.sql").read_text(encoding="utf-8")


def _reload_database() -> None:
    cfg = DatabaseConfig.load()
    sql = SCRIPT.replace("student_management", cfg.database)
    cmd = ["mysql", f"-h{cfg.host}", f"-P{cfg.port}", f"-u{cfg.user}"]
    if cfg.password:
        cmd.append(f"-p{cfg.password}")
    subprocess.run(cmd, input=sql.encode("utf-8"), check=True, capture_output=True)


@pytest.fixture()
def ctx() -> AppContext:
    """CSDL test được nạp lại từ đúng file database/student_management.sql trước mỗi test."""
    _reload_database()
    return AppContext.create()


@pytest.fixture()
def admin(ctx):
    return ctx.auth_service.login("admin", "Admin@123")


@pytest.fixture()
def lecturer(ctx):
    return ctx.auth_service.login("GV001", "Gv001@123")


@pytest.fixture()
def student(ctx):
    return ctx.auth_service.login("SV001", "Sv001@123")
