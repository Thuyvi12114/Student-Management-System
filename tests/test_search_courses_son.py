"""Kiểm thử Module 4 (Tìm kiếm, Dashboard) và Module 5 (Giảng viên, Học phần) - Sơn."""
from __future__ import annotations

import pytest

from app.models import Role
from app.service.exceptions import AuthError, AuthorizationError, ValidationError


class TestCoursesLecturers:
    def test_course_crud_and_restrict(self, ctx, admin):
        c = ctx.course_service.create(admin, course_id="IT900", course_name="Môn mới", credits=3, lecturer_id="GV001")
        assert c.lecturer_name == "Trần Hoàng Nam"
        ctx.course_service.update(admin, "IT900", course_name="Đổi tên", credits=4, lecturer_id="GV002")
        ctx.course_service.delete(admin, "IT900")
        with pytest.raises(ValidationError):
            ctx.course_service.delete(admin, "CS101")  # đã có điểm
        with pytest.raises(ValidationError):
            ctx.course_service.create(admin, course_id="CS101", course_name="x", credits=3, lecturer_id="GV001")
        with pytest.raises(ValidationError):
            ctx.course_service.create(admin, course_id="IT901", course_name="x", credits=0, lecturer_id="GV001")

    def test_lecturer_only_sees_own_courses(self, ctx, lecturer):
        assert {c.course_id for c in ctx.course_service.list_all(lecturer)} == {"CS101", "CS201", "CS202"}

    def test_lecturer_create_delete(self, ctx, admin):
        ctx.lecturer_service.create(admin, lecturer_id="GV100", full_name="Giảng Viên Mới", email="gv100@u.vn",
                                    phone="0900111222", department="CNTT", password="Gv100@123")
        assert ctx.auth_service.login("gv100", "Gv100@123").role is Role.LECTURER
        ctx.lecturer_service.delete(admin, "GV100")
        with pytest.raises(AuthError):
            ctx.auth_service.login("gv100", "Gv100@123")
        with pytest.raises(ValidationError, match="phụ trách"):
            ctx.lecturer_service.delete(admin, "GV001")


class TestSearchAndVisibility:
    """UC-01/02 (Sơn, M4) và UC-12/13 (Sơn, M5) theo đúng file phân công."""

    def test_lecturer_search_returns_only_three_fields(self, ctx, lecturer):
        r = ctx.student_search_service.search_students_basic(lecturer, "k24a", page=1, page_size=20)
        assert r.total_count == 7 and r.items  # khớp một phần theo lớp, không phân biệt hoa thường
        assert set(vars(r.items[0])) == {"student_id", "full_name", "class_name"}

    def test_lecturer_search_partial_name_and_id(self, ctx, lecturer):
        assert ctx.student_search_service.search_students_basic(lecturer, "nguyễn").total_count == 3
        assert ctx.student_search_service.search_students_basic(lecturer, "sv00").total_count == 9

    def test_admin_search_by_class_keyword(self, ctx, admin):
        assert ctx.student_search_service.search_students(admin, "qtkd").total_count == 2

    def test_search_roles(self, ctx, admin, lecturer, student):
        with pytest.raises(AuthorizationError):
            ctx.student_search_service.search_students(lecturer, "")  # bản đầy đủ chỉ Admin
        with pytest.raises(AuthorizationError):
            ctx.student_search_service.search_students_basic(admin, "")
        with pytest.raises(AuthorizationError):
            ctx.student_search_service.search_students_basic(student, "")
        with pytest.raises(AuthorizationError):
            ctx.student_search_service.student_detail(lecturer, "SV001")  # UC-02 chi tiết: chỉ Admin

    def test_sql_injection_in_search_is_harmless(self, ctx, admin, lecturer):
        for kw in ("' OR '1'='1", "'; DROP TABLE Students; --", "%", "_"):
            assert ctx.student_search_service.search_students(admin, kw).total_count == 0
            assert ctx.student_search_service.search_students_basic(lecturer, kw).total_count == 0
        assert ctx.student_search_service.dashboard(admin).total_students == 10

    def test_lecturer_dashboard_progress(self, ctx, lecturer):
        d = ctx.student_search_service.dashboard(lecturer)
        assert (d.assigned_courses, d.graded_entries, d.expected_entries) == (3, 9, 30)

    def test_course_requires_active_lecturer(self, ctx, admin):
        from app.models import AccountStatus
        lec = ctx.lecturer_service.get_by_id(admin, "GV002")
        ctx.account_service.set_account_status(admin, lec.account_id, AccountStatus.INACTIVE)
        with pytest.raises(ValidationError, match="đang hoạt động"):
            ctx.course_service.create(admin, course_id="IT800", course_name="X", credits=3, lecturer_id="GV002")
        with pytest.raises(ValidationError, match="đang hoạt động"):
            ctx.course_service.update(admin, "CS101", course_name="X", credits=3, lecturer_id="GV002")

    def test_change_lecturer_revokes_grade_rights(self, ctx, admin, lecturer):
        ctx.course_service.update(admin, "CS101", course_name="Nhập môn lập trình", credits=3, lecturer_id="GV003")
        with pytest.raises(AuthorizationError):
            ctx.grade_service.save_grade(lecturer, "CS101", "SV006", "7")  # GV001 không còn phụ trách
        gv3 = ctx.auth_service.login("GV003", "Gv003@123")
        assert ctx.grade_service.save_grade(gv3, "CS101", "SV006", "7")

    def test_student_sees_catalog_but_cannot_edit(self, ctx, student):
        assert len(ctx.course_service.list_all(student)) == 7
        assert ctx.course_service.search(student, "dữ liệu").total_count == 2
        with pytest.raises(AuthorizationError):
            ctx.course_service.create(student, course_id="IT1", course_name="x", credits=3, lecturer_id="GV001")
        with pytest.raises(AuthorizationError):
            ctx.course_service.delete(student, "CS301")

    def test_credits_must_be_positive(self, ctx, admin):
        for bad in (0, -1, "abc", 11):
            with pytest.raises(ValidationError):
                ctx.course_service.create(admin, course_id="IT2", course_name="x", credits=bad, lecturer_id="GV001")

    def test_lecturer_duplicate_and_students_blocked_delete(self, ctx, admin):
        with pytest.raises(ValidationError):
            ctx.lecturer_service.create(admin, lecturer_id="gv001", full_name="Trùng", email="t@u.vn",
                                        phone="0900111222", department="X", password="Gv001@123")
