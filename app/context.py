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
from app.service.account_service import AccountService
from app.service.auth_service import AuthService
from app.service.course_service import CourseService
from app.service.grade_service import GradeService
from app.service.lecturer_service import LecturerService
from app.service.student_service import StudentService


@dataclass(frozen=True)
class AppContext:
    auth_service: AuthService
    account_service: AccountService
    grade_service: GradeService
    student_service: StudentService
    lecturer_service: LecturerService
    course_service: CourseService

    @classmethod
    def create(cls) -> "AppContext":
        config = DatabaseConfig.load()
        database = Database(config)

        account_dao = UserAccountDAO(database)
        session_manager = SessionManager()
        auth_service = AuthService(account_dao, session_manager)
        account_service = AccountService(account_dao)

        grade_dao = GradeDAO(database)
        course_dao = CourseDAO(database)
        student_dao = StudentDAO(database, account_dao)
        lecturer_dao = LecturerDAO(database)

        grade_service = GradeService(
            grade_dao=grade_dao,
            course_dao=course_dao,
            student_dao=student_dao,
            lecturer_dao=lecturer_dao,
        )
        student_service = StudentService(
            student_dao=student_dao,
            lecturer_dao=lecturer_dao,
            user_account_dao=account_dao,
        )
        lecturer_service = LecturerService(lecturer_dao)
        course_service = CourseService(
            course_dao=course_dao,
            lecturer_dao=lecturer_dao,
            user_account_dao=account_dao,
        )
        return cls(
            auth_service=auth_service,
            account_service=account_service,
            grade_service=grade_service,
            student_service=student_service,
            lecturer_service=lecturer_service,
            course_service=course_service,
        )
