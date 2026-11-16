"""Khởi tạo các thành phần theo kiến trúc 3 lớp: Config → DAO → Service → UI."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import DatabaseConfig
from app.dao.course_dao import CourseDAO
from app.dao.grade_dao import GradeDAO
from app.dao.lecturer_dao import LecturerDAO
from app.dao.student_dao import StudentDAO
from app.dao.user_account_dao import UserAccountDAO
from app.db import Database
from app.security.session import SessionManager
from app.service.auth_service import AuthService
from app.service.grade_service import GradeService


@dataclass(frozen=True)
class AppContext:
    auth_service: AuthService
    grade_service: GradeService

    @classmethod
    def create(cls) -> "AppContext":
        config = DatabaseConfig.load()
        database = Database(config)

        account_dao = UserAccountDAO(database)
        session_manager = SessionManager()
        auth_service = AuthService(account_dao, session_manager)

        grade_service = GradeService(
            grade_dao=GradeDAO(database),
            course_dao=CourseDAO(database),
            student_dao=StudentDAO(database),
            lecturer_dao=LecturerDAO(database),
        )
        return cls(auth_service=auth_service, grade_service=grade_service)
