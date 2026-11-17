"""Kiểm thử Module 1 (Đăng nhập, đổi mật khẩu) và Module 6 (Điểm) - Vân Anh."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import Role
from app.service.exceptions import AuthError, AuthorizationError, ValidationError


class TestAuth:
    def test_login_variants(self, ctx):
        assert ctx.auth_service.login("admin", "Admin@123").role is Role.ADMIN
        assert ctx.auth_service.login("gv001", "Gv001@123").role is Role.LECTURER
        with pytest.raises(AuthError):
            ctx.auth_service.login("SV001", "sai")
        with pytest.raises(AuthError):
            ctx.auth_service.login("SV005", "Sv005@123")  # Inactive

    def test_change_password(self, ctx, student):
        ctx.auth_service.change_password("Sv001@123", "Abcd@1234", "Abcd@1234")
        assert ctx.auth_service.login("SV001", "Abcd@1234")


class TestGrades:
    def test_lecturer_grades_assigned_course_only(self, ctx, lecturer):
        gid = ctx.grade_service.save_grade(lecturer, "CS101", "SV006", "8,25")
        assert gid
        with pytest.raises(AuthorizationError):
            ctx.grade_service.save_grade(lecturer, "MA101", "SV006", "8")  # GV002 phụ trách

    def test_one_grade_per_pair_and_update(self, ctx, lecturer):
        a = ctx.grade_service.save_grade(lecturer, "CS101", "SV001", "5")
        b = ctx.grade_service.save_grade(lecturer, "CS101", "SV001", "9.5")
        assert a == b
        assert ctx.grade_service._grade_dao.find_by_student_course("SV001", "CS101").grade_value == Decimal("9.50")

    @pytest.mark.parametrize("bad", ["", "abc", "-1", "10.01", "8.555"])
    def test_invalid_grade(self, ctx, lecturer, bad):
        with pytest.raises(ValidationError):
            ctx.grade_service.save_grade(lecturer, "CS101", "SV001", bad)

    def test_admin_view_only(self, ctx, admin):
        assert len(ctx.grade_service.admin_search(admin)) == 12
        with pytest.raises(AuthorizationError):
            ctx.grade_service.save_grade(admin, "CS101", "SV001", "9")

    def test_student_results_gpa(self, ctx, student):
        r = ctx.grade_service.student_results(student)
        # (8.5*3 + 9*3 + 8*4 + 8.5*3) / 13 = 110 / 13
        assert r.total_credits == 13 and r.gpa == Decimal("8.46") and r.passed_credits == 13
