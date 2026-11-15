"""Khởi tạo các thành phần theo kiến trúc 3 lớp: Config → DAO → Service → UI."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import DatabaseConfig
from app.dao.user_account_dao import UserAccountDAO
from app.db import Database
from app.security.session import SessionManager
from app.service.auth_service import AuthService


@dataclass(frozen=True)
class AppContext:
    auth_service: AuthService

    @classmethod
    def create(cls) -> "AppContext":
        config = DatabaseConfig.load()
        database = Database(config)
        account_dao = UserAccountDAO(database)
        session_manager = SessionManager()
        return cls(auth_service=AuthService(account_dao, session_manager))
