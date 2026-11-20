"""Cấu hình kết nối MySQL cho ứng dụng.

Thứ tự ưu tiên: biến môi trường (SMS_DB_*) ghi đè giá trị trong config.ini.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.ini"
EXAMPLE_FILE = PROJECT_ROOT / "config.example.ini"


class ConfigurationError(RuntimeError):
    """Cấu hình kết nối thiếu hoặc không hợp lệ."""


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def endpoint(self) -> str:
        """Mô tả kết nối để hiển thị, không chứa mật khẩu."""
        return f"{self.user}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def load(cls) -> "DatabaseConfig":
        file_values = cls._read_file()

        host = os.getenv("SMS_DB_HOST", file_values.get("host", "")).strip()
        port_raw = os.getenv("SMS_DB_PORT", file_values.get("port", "3306")).strip()
        database = os.getenv("SMS_DB_NAME", file_values.get("name", "student_management")).strip()
        user = os.getenv("SMS_DB_USER", file_values.get("user", "root")).strip()
        password = os.getenv("SMS_DB_PASSWORD", file_values.get("password", ""))

        if not host:
            raise ConfigurationError(
                "Chưa có cấu hình kết nối MySQL.\n"
                f"Hãy sao chép {EXAMPLE_FILE.name} thành {CONFIG_FILE.name} rồi điền thông tin, "
                "hoặc đặt các biến môi trường SMS_DB_HOST, SMS_DB_PORT, SMS_DB_NAME, "
                "SMS_DB_USER, SMS_DB_PASSWORD."
            )

        try:
            port = int(port_raw)
        except ValueError as exc:
            raise ConfigurationError(f"Cổng MySQL không hợp lệ: {port_raw}") from exc

        return cls(host=host, port=port, database=database, user=user, password=password)

    @staticmethod
    def _read_file() -> dict[str, str]:
        if not CONFIG_FILE.exists():
            return {}
        parser = configparser.ConfigParser()
        try:
            parser.read(CONFIG_FILE, encoding="utf-8")
        except configparser.Error as exc:
            raise ConfigurationError(f"Không đọc được {CONFIG_FILE.name}: {exc}") from exc
        if not parser.has_section("database"):
            return {}
        return {
            key: parser.get("database", key, fallback="")
            for key in ("host", "port", "name", "user", "password")
        }
