""" - Ràng buộc CSDL (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK) & bền vững dữ liệu sau tắt/mở ứng dụng
- Hiệu năng (nạp 1.000 SV, 100 GV, 100 môn, 5.000 điểm; tìm kiếm < 2s, thao tác < 3s)
- Tích hợp end-to-end, phân quyền màn hình/module theo vai trò & thông báo lỗi dễ hiểu
"""
from __future__ import annotations

import os
import random
import time

import pytest

from app.context import AppContext
from app.dao.errors import DataAccessError
from app.security.password_hasher import hash_password
from app.security.rbac import AppModule, RbacPolicy
from app.service.exceptions import ValidationError


def count(ctx: AppContext, table: str, where: str = "1=1") -> int:
    return int(ctx.student_service._student_dao.scalar(f"SELECT COUNT(*) FROM {table} WHERE {where}"))


# 1. Ràng buộc CSDL & Bền vững sau khi tắt/mở ứng dụng
class TestDatabaseConstraintsAndPersistence:
    def test_primary_key_and_unique_constraints(self, ctx):
        dao = ctx.student_service._student_dao
        # PRIMARY KEY trùng trên Students & Courses
        with pytest.raises(DataAccessError):
            dao.execute(
                "INSERT INTO Students VALUES ('SV001', 5, 'X', '2006-01-01', 'Nam', 'x@u.vn', '0901111111', NULL, 'K1')"
            )
        with pytest.raises(DataAccessError):
            dao.execute("INSERT INTO Courses VALUES ('CS101', 'GV001', 'Trùng PK', 3, NULL)")
        # UNIQUE username trên UserAccounts & UNIQUE (student_id, course_id) trên Grades
        with pytest.raises(DataAccessError):
            dao.execute(
                "INSERT INTO UserAccounts (username, password_hash, role, status) VALUES ('SV001', 'h', 'Student', 'Active')"
            )
        with pytest.raises(DataAccessError):
            dao.execute("INSERT INTO Grades (student_id, course_id, grade_value) VALUES ('SV001', 'CS101', 8.0)")

    def test_foreign_key_constraints(self, ctx):
        dao = ctx.student_service._student_dao
        # Tham chiếu khóa ngoại không tồn tại
        with pytest.raises(DataAccessError):
            dao.execute("INSERT INTO Courses VALUES ('IT888', 'GV999', 'FK lỗi', 3, NULL)")
        with pytest.raises(DataAccessError):
            dao.execute("INSERT INTO Grades (student_id, course_id, grade_value) VALUES ('SV999', 'CS101', 7.5)")
        # ON DELETE RESTRICT khi xóa cha còn con
        with pytest.raises(DataAccessError):
            dao.execute("DELETE FROM Lecturers WHERE lecturer_id='GV001'")
        with pytest.raises(DataAccessError):
            dao.execute("DELETE FROM Courses WHERE course_id='CS101'")

    def test_check_constraints(self, ctx):
        dao = ctx.student_service._student_dao
        with pytest.raises(DataAccessError):
            dao.execute("INSERT INTO Courses VALUES ('IT777', 'GV001', 'Tín chỉ 0', 0, NULL)")
        with pytest.raises(DataAccessError):
            dao.execute("INSERT INTO Grades (student_id, course_id, grade_value) VALUES ('SV007', 'CS301', 10.5)")
        with pytest.raises(DataAccessError):
            dao.execute("INSERT INTO Grades (student_id, course_id, grade_value) VALUES ('SV007', 'CS301', -0.5)")
        with pytest.raises(DataAccessError):
            dao.execute("UPDATE Students SET gender='Không hợp lệ' WHERE student_id='SV001'")

    def test_data_persists_after_app_restart(self, ctx, admin):
        ctx.lecturer_service.create(
            admin,
            lecturer_id="GV200",
            full_name="Giảng Viên Bền Vững",
            email="gv200@u.vn",
            phone="0909888777",
            department="HTTT",
            password="Gv200@123",
        )
        ctx.course_service.create(
            admin, course_id="IS301", course_name="Hệ thống thông tin", credits=3, lecturer_id="GV200"
        )
        gv200 = ctx.auth_service.login("GV200", "Gv200@123")
        ctx.grade_service.save_grade(gv200, "IS301", "SV001", "9.25")
        ctx.auth_service.logout(gv200)

        # Giả lập tắt hẳn ứng dụng và khởi tạo AppContext mới kết nối lại MySQL
        restarted_ctx = AppContext.create()
        reloaded_gv = restarted_ctx.auth_service.login("GV200", "Gv200@123")
        courses = restarted_ctx.course_service.list_all(reloaded_gv)
        assert any(c.course_id == "IS301" and c.course_name == "Hệ thống thông tin" for c in courses)
        sv1 = restarted_ctx.auth_service.login("SV001", "Sv001@123")
        results = restarted_ctx.grade_service.student_results(sv1)
        assert any(item.course_id == "IS301" and str(item.grade_value) == "9.25" for item in results.items)

# 2. Hiệu năng (1.000 SV, 100 GV, 100 môn, 5.000 điểm)
def _seed_performance_dataset(ctx: AppContext) -> None:
    """Nạp đúng 1.000 sinh viên, 100 giảng viên, 100 môn học, 5.000 điểm trên CSDL test."""
    assert os.environ.get("SMS_DB_NAME", "student_management_test").endswith("_test")
    dao = ctx.student_service._student_dao
    pw_hash = hash_password("Perf@123")

    with dao.transaction("nạp dữ liệu hiệu năng") as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM Grades")
            cur.execute("DELETE FROM Courses")
            cur.execute("DELETE FROM Lecturers")
            cur.execute("DELETE FROM Students")
            cur.execute("DELETE FROM UserAccounts WHERE username <> 'admin'")

            # 100 Lecturers
            lec_accounts = [(f"GV{i:04d}", pw_hash, "Lecturer", "Active") for i in range(1, 101)]
            cur.executemany(
                "INSERT INTO UserAccounts (username, password_hash, role, status) VALUES (%s, %s, %s, %s)",
                lec_accounts,
            )
            cur.execute("SELECT username, account_id FROM UserAccounts WHERE role='Lecturer'")
            lec_acc_map = dict(cur.fetchall())
            lecturers = [
                (
                    f"GV{i:04d}",
                    lec_acc_map[f"GV{i:04d}"],
                    f"Giảng Viên {i:04d}",
                    f"gv{i:04d}@unicore.edu.vn",
                    f"091{i:07d}",
                    f"Khoa {(i % 5) + 1}",
                )
                for i in range(1, 101)
            ]
            cur.executemany(
                "INSERT INTO Lecturers (lecturer_id, account_id, full_name, email, phone_number, department) VALUES (%s, %s, %s, %s, %s, %s)",
                lecturers,
            )

            # 1.000 Students
            stu_accounts = [(f"SV{i:04d}", pw_hash, "Student", "Active") for i in range(1, 1001)]
            cur.executemany(
                "INSERT INTO UserAccounts (username, password_hash, role, status) VALUES (%s, %s, %s, %s)",
                stu_accounts,
            )
            cur.execute("SELECT username, account_id FROM UserAccounts WHERE role='Student'")
            stu_acc_map = dict(cur.fetchall())
            students = [
                (
                    f"SV{i:04d}",
                    stu_acc_map[f"SV{i:04d}"],
                    f"Sinh Viên {i:04d}",
                    "2006-05-15",
                    "Nữ" if i % 2 == 0 else "Nam",
                    f"sv{i:04d}@sv.unicore.edu.vn",
                    f"098{i:07d}",
                    f"Số {i} Đường ABC",
                    f"CNTT-K{(i % 10) + 20}",
                )
                for i in range(1, 1001)
            ]
            cur.executemany(
                "INSERT INTO Students (student_id, account_id, full_name, date_of_birth, gender, email, phone_number, address, class_name) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                students,
            )

            # 100 Courses
            courses = [
                (
                    f"MH{i:04d}",
                    f"GV{((i - 1) % 100) + 1:04d}",
                    f"Học phần kiểm thử {i:04d}",
                    (i % 4) + 1,
                    f"Mô tả học phần {i:04d}",
                )
                for i in range(1, 101)
            ]
            cur.executemany(
                "INSERT INTO Courses (course_id, lecturer_id, course_name, credits, description) VALUES (%s, %s, %s, %s, %s)",
                courses,
            )

            # 5.000 Grades (50 môn đầu x 100 sinh viên đầu = 5.000 bản ghi duy nhất)
            rng = random.Random(42)
            grades = [
                (f"SV{s:04d}", f"MH{c:04d}", round(rng.uniform(4.0, 10.0), 2))
                for c in range(1, 51)
                for s in range(1, 101)
            ]
            cur.executemany(
                "INSERT INTO Grades (student_id, course_id, grade_value) VALUES (%s, %s, %s)",
                grades,
            )
        finally:
            cur.close()


class TestPerformance:
    def test_seed_volume_and_response_thresholds(self, ctx, admin):
        _seed_performance_dataset(ctx)
        assert count(ctx, "Students") == 1000
        assert count(ctx, "Lecturers") == 100
        assert count(ctx, "Courses") == 100
        assert count(ctx, "Grades") == 5000

        # 1. Tìm kiếm dưới 2 giây
        t0 = time.perf_counter()
        stu_res = ctx.student_search_service.search_students(admin, "Sinh Viên 05", page=1, page_size=50)
        t_search_stu = time.perf_counter() - t0
        assert stu_res.total_count > 0 and t_search_stu < 2.0

        t0 = time.perf_counter()
        lec_res = ctx.lecturer_service.search(admin, "Giảng Viên", page=1, page_size=50)
        t_search_lec = time.perf_counter() - t0
        assert lec_res.total_count == 100 and t_search_lec < 2.0

        t0 = time.perf_counter()
        crs_res = ctx.course_service.search(admin, "Học phần", page=1, page_size=50)
        t_search_crs = time.perf_counter() - t0
        assert crs_res.total_count == 100 and t_search_crs < 2.0

        # 2. Các thao tác nghiệp vụ dưới 3 giây
        t0 = time.perf_counter()
        gv_session = ctx.auth_service.login("GV0001", "Perf@123")
        t_login = time.perf_counter() - t0
        assert t_login < 3.0

        t0 = time.perf_counter()
        ctx.grade_service.save_grade(gv_session, "MH0001", "SV0001", "9.5")
        t_save_grade = time.perf_counter() - t0
        assert t_save_grade < 3.0

        t0 = time.perf_counter()
        sv_session = ctx.auth_service.login("SV0001", "Perf@123")
        gpa_res = ctx.grade_service.student_results(sv_session)
        t_gpa = time.perf_counter() - t0
        assert gpa_res.total_credits > 0 and t_gpa < 3.0


# 3. Tích hợp & Phân quyền màn hình / module theo vai trò
class TestIntegrationAndRoleScreens:
    def test_rbac_navigation_screens_for_three_roles(self, admin, lecturer, student):
        admin_mods = set(RbacPolicy.navigation_for(admin.role))
        lec_mods = set(RbacPolicy.navigation_for(lecturer.role))
        stu_mods = set(RbacPolicy.navigation_for(student.role))

        assert admin_mods == {
            AppModule.DASHBOARD,
            AppModule.ACCOUNT_MANAGEMENT,
            AppModule.STUDENT_MANAGEMENT,
            AppModule.LECTURER_MANAGEMENT,
            AppModule.COURSE_MANAGEMENT,
            AppModule.ADMIN_GRADE_LOOKUP,
        }
        assert lec_mods == {
            AppModule.DASHBOARD,
            AppModule.COURSE_MANAGEMENT,
            AppModule.LECTURER_STUDENT_SEARCH,
            AppModule.GRADE_MANAGEMENT,
            AppModule.LECTURER_COURSE_GRADES,
            AppModule.PROFILE,
        }
        assert stu_mods == {
            AppModule.DASHBOARD,
            AppModule.COURSE_MANAGEMENT,
            AppModule.MY_GRADES,
            AppModule.PROFILE,
        }
        assert not RbacPolicy.can_access(student.role, AppModule.LECTURER_MANAGEMENT)
        assert not RbacPolicy.can_access(lecturer.role, AppModule.ACCOUNT_MANAGEMENT)

    def test_end_to_end_flow_and_user_friendly_errors(self, ctx, admin):
        # 1. Admin tạo GV -> tạo SV -> tạo môn học gán GV
        ctx.lecturer_service.create(
            admin, lecturer_id="GV300", full_name="Lê Minh Tâm", email="tam@u.vn",
            phone="0907111222", department="CNTT", password="Gv300@123",
        )
        ctx.student_service.create(
            admin, student_id="SV300", full_name="Phạm Thảo Nhi", gender="Nữ", date_of_birth="20/05/2006",
            email="nhi@sv.u.vn", phone="0907333444", address="TP.HCM", class_name="CNTT-K24C", password="Sv300@123",
        )
        ctx.course_service.create(
            admin, course_id="SE305", course_name="Kiểm thử tự động", credits=3, lecturer_id="GV300"
        )

        # 2. GV đăng nhập nhập điểm -> SV đăng nhập xem điểm & GPA
        gv_sess = ctx.auth_service.login("GV300", "Gv300@123")
        ctx.grade_service.save_grade(gv_sess, "SE305", "SV300", "8.75")

        sv_sess = ctx.auth_service.login("SV300", "Sv300@123")
        res = ctx.grade_service.student_results(sv_sess)
        assert len(res.items) == 1 and str(res.gpa) == "8.75"

        # 3. Thông báo lỗi tiếng Việt rõ ràng, dễ hiểu
        with pytest.raises(ValidationError) as exc_info:
            ctx.course_service.delete(admin, "SE305")
        assert "Không thể xóa học phần đã có điểm sinh viên" in str(exc_info.value)
