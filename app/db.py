"""Kết nối MySQL dùng mysql-connector-python."""

from __future__ import annotations

import contextlib

import mysql.connector

from app.config import DatabaseConfig
from app.dao.errors import DataAccessError


class Database:
    """Cấp kết nối tới MySQL; mỗi thao tác DAO tự mở và đóng kết nối."""

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config

    @property
    def config(self) -> DatabaseConfig:
        return self._config

    def connect(self) -> mysql.connector.MySQLConnection:
        try:
            return mysql.connector.connect(
                host=self._config.host,
                port=self._config.port,
                database=self._config.database,
                user=self._config.user,
                password=self._config.password,
                charset="utf8mb4",
                use_pure=True,
                autocommit=True,
                connection_timeout=5,
            )
        except mysql.connector.Error as exc:
            raise DataAccessError(
                f"Không thể kết nối MySQL ({self._config.endpoint}). "
                f"Kiểm tra MySQL đã chạy và thông tin trong config.ini. Chi tiết: {exc}"
            ) from exc

    def verify(self) -> None:
        """Kiểm tra kết nối và quyền đăng nhập cơ sở dữ liệu."""
        try:
            with contextlib.closing(self.connect()) as connection:
                connection.ping(reconnect=False, attempts=1, delay=0)
        except mysql.connector.Error as exc:
            raise DataAccessError(f"Không kiểm tra được kết nối MySQL: {exc}") from exc
