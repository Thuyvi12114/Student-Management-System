"""Kiểm thử phần của Nghĩa: Module 2 (Tài khoản & hồ sơ) và Module 3 (CRUD sinh viên)."""
from __future__ import annotations

import pytest

from app.models import AccountStatus, Lecturer, Role, StudentRecord
from app.service.exceptions import AuthError, AuthorizationError, ValidationError

NEW = dict(
    student_id="SV100", full_name="Hoàng Mai", gender="Nữ", date_of_birth="12/03/2006",
    email="mai@sv.edu.vn", phone="0911222333", address="1 Lê Lợi", class_name="CNTT-K24A", password="Sv100@123",
)


def count(ctx, table, where="1=1"):
    return ctx.student_service._student_dao.scalar(f"SELECT COUNT(*) FROM {table} WHERE {where}")


# ------------------------------------------------------------------ UC-03 / UC-08
class TestProfile:
    def test_student_sees_own_profile(self, ctx, student):
        p = ctx.profile_service.my_profile(student)
        assert isinstance(p, StudentRecord) and p.student_id == "SV001" and p.address

    def test_lecturer_sees_own_profile(self, ctx, lecturer):
        p = ctx.profile_service.my_profile(lecturer)
        assert isinstance(p, Lecturer) and p.lecturer_id == "GV001"

    def test_admin_has_no_profile(self, ctx, admin):
        with pytest.raises(AuthorizationError):
            ctx.profile_service.my_profile(admin)

    def test_student_updates_only_contact(self, ctx, student):
        before = ctx.profile_service.my_profile(student)
        after = ctx.profile_service.update_contact(student, email="new@x.vn", phone="0999888777", address="Địa chỉ mới")
        assert (after.email, after.phone, after.address) == ("new@x.vn", "0999888777", "Địa chỉ mới")
        assert (after.student_id, after.full_name, after.class_name, after.date_of_birth) == (
            before.student_id, before.full_name, before.class_name, before.date_of_birth)

    def test_address_can_be_cleared(self, ctx, student):
        assert ctx.profile_service.update_contact(student, email="a@b.vn", phone="0999888777", address="  ").address is None

    @pytest.mark.parametrize("email,phone", [("abc", "0999888777"), ("a@b.vn", "12"), ("", "0999888777"), ("a@b.vn", "")])
    def test_invalid_contact_keeps_data(self, ctx, student, email, phone):
        before = ctx.profile_service.my_profile(student)
        with pytest.raises(ValidationError):
            ctx.profile_service.update_contact(student, email=email, phone=phone, address="x")
        assert ctx.profile_service.my_profile(student) == before

    def test_lecturer_cannot_edit_profile(self, ctx, lecturer):
        with pytest.raises(AuthorizationError):
            ctx.profile_service.update_contact(lecturer, email="a@b.vn", phone="0999888777", address="x")


# ------------------------------------------------------------------ UC-07
class TestAccounts:
    def test_list_excludes_admin(self, ctx, admin):
        accounts = ctx.account_service.list_accounts(admin)
        assert len(accounts) == 13 and all(a.role is not Role.ADMIN for a in accounts)
        assert next(a for a in accounts if a.username == "SV001").full_name == "Nguyễn Minh Anh"

    def test_non_admin_denied(self, ctx, student, lecturer):
        for s in (student, lecturer):
            with pytest.raises(AuthorizationError):
                ctx.account_service.list_accounts(s)

    def test_deactivate_blocks_login_keeps_profile(self, ctx, admin):
        acc = next(a for a in ctx.account_service.list_accounts(admin) if a.username == "SV002")
        ctx.account_service.set_account_status(admin, acc.account_id, AccountStatus.INACTIVE)
        with pytest.raises(AuthError):
            ctx.auth_service.login("SV002", "Sv002@123")
        assert count(ctx, "Students", "student_id='SV002'") == 1
        ctx.account_service.set_account_status(admin, acc.account_id, AccountStatus.ACTIVE)
        assert ctx.auth_service.login("SV002", "Sv002@123").username == "SV002"

    def test_reset_password(self, ctx, admin):
        acc = next(a for a in ctx.account_service.list_accounts(admin) if a.username == "SV003")
        ctx.account_service.reset_password(admin, acc.account_id, "NewPass@456")
        with pytest.raises(AuthError):
            ctx.auth_service.login("SV003", "Sv003@123")
        assert ctx.auth_service.login("SV003", "NewPass@456")
        hash_ = ctx.student_service._student_dao.scalar("SELECT password_hash FROM UserAccounts WHERE username='SV003'")
        assert hash_.startswith("pbkdf2_sha256$") and "NewPass" not in hash_

    def test_reset_invalid_password_keeps_old(self, ctx, admin):
        acc = next(a for a in ctx.account_service.list_accounts(admin) if a.username == "SV003")
        with pytest.raises(ValidationError):
            ctx.account_service.reset_password(admin, acc.account_id, "abc")
        assert ctx.auth_service.login("SV003", "Sv003@123")

    def test_unknown_account(self, ctx, admin):
        with pytest.raises(ValidationError):
            ctx.account_service.reset_password(admin, 99999, "NewPass@456")
        with pytest.raises(ValidationError):
            ctx.account_service.set_account_status(admin, 99999, AccountStatus.INACTIVE)

    def test_cannot_manage_admin_account(self, ctx, admin):
        admin_id = ctx.student_service._student_dao.scalar("SELECT account_id FROM UserAccounts WHERE username='admin'")
        with pytest.raises(ValidationError):
            ctx.account_service.set_account_status(admin, admin_id, AccountStatus.INACTIVE)

    def test_accounts_not_independently_creatable(self, ctx):
        """Tài khoản chỉ được sinh qua UC-09/UC-14: AccountService không có hàm tạo/xóa."""
        assert not hasattr(ctx.account_service, "create") and not hasattr(ctx.account_service, "delete")


# ------------------------------------------------------------------ UC-09 / UC-19
class TestAddStudent:
    def test_create_makes_profile_and_account(self, ctx, admin):
        rec = ctx.student_service.create(admin, **NEW)
        assert rec.student_id == "SV100" and rec.account_id
        s = ctx.auth_service.login("sv100", "Sv100@123")  # username = mã SV, không phân biệt hoa thường
        assert s.role is Role.STUDENT and s.full_name == "Hoàng Mai"
        assert count(ctx, "UserAccounts", "username='SV100'") == 1

    def test_id_is_uppercased(self, ctx, admin):
        assert ctx.student_service.create(admin, **{**NEW, "student_id": "sv101"}).student_id == "SV101"

    def test_address_optional(self, ctx, admin):
        assert ctx.student_service.create(admin, **{**NEW, "address": ""}).address is None

    def test_uc19_duplicate_check(self, ctx, admin):
        assert ctx.student_service.is_student_id_available(admin, "SV100") is True
        assert ctx.student_service.is_student_id_available(admin, "SV001") is False
        assert ctx.student_service.is_student_id_available(admin, "admin") is False  # trùng username

    def test_duplicate_student_id_rejected(self, ctx, admin):
        with pytest.raises(ValidationError, match="đã tồn tại"):
            ctx.student_service.create(admin, **{**NEW, "student_id": "SV001"})
        assert count(ctx, "Students") == 10 and count(ctx, "UserAccounts") == 14

    def test_duplicate_username_rejected(self, ctx, admin):
        with pytest.raises(ValidationError):
            ctx.student_service.create(admin, **{**NEW, "student_id": "GV001"})
        assert count(ctx, "Students") == 10

    @pytest.mark.parametrize("field,value", [
        ("full_name", ""), ("gender", "Khác nữa"), ("date_of_birth", "31/02/2006"), ("date_of_birth", "01/01/2099"),
        ("email", "sai-email"), ("phone", "abc"), ("class_name", ""), ("student_id", "SV 1"), ("student_id", ""),
        ("password", "weak"), ("password", "nouppercase1"),
    ])
    def test_invalid_input_saves_nothing(self, ctx, admin, field, value):
        with pytest.raises(ValidationError):
            ctx.student_service.create(admin, **{**NEW, field: value})
        assert count(ctx, "Students") == 10 and count(ctx, "UserAccounts") == 14

    def test_rollback_when_profile_insert_fails(self, ctx, admin, monkeypatch):
        """AF4: tạo tài khoản xong nhưng ghi hồ sơ lỗi → không để lại tài khoản mồ côi."""
        from app.dao.errors import DataAccessError
        def boom(*a, **k):
            raise DataAccessError("lỗi giả lập")
        monkeypatch.setattr(ctx.student_service._student_dao, "insert", boom)
        with pytest.raises(DataAccessError):
            ctx.student_service.create(admin, **NEW)
        assert count(ctx, "UserAccounts", "username='SV100'") == 0 and count(ctx, "Students", "student_id='SV100'") == 0

    def test_only_admin(self, ctx, lecturer, student):
        for s in (lecturer, student):
            with pytest.raises(AuthorizationError):
                ctx.student_service.create(s, **NEW)


# ------------------------------------------------------------------ UC-10
class TestUpdateStudent:
    EDIT = dict(full_name="Tên Mới", gender="Nam", date_of_birth="01/02/2005", email="n@x.vn",
                phone="0900000001", address="Địa chỉ X", class_name="CNTT-K24B")

    def test_update_keeps_id_and_account(self, ctx, admin):
        before = ctx.student_search_service.student_detail(admin, "SV001")
        after = ctx.student_service.update(admin, "SV001", **self.EDIT)
        assert (after.student_id, after.account_id) == (before.student_id, before.account_id)
        assert (after.full_name, after.class_name, after.address) == ("Tên Mới", "CNTT-K24B", "Địa chỉ X")
        assert ctx.auth_service.login("SV001", "Sv001@123").full_name == "Tên Mới"

    def test_not_found(self, ctx, admin):
        with pytest.raises(ValidationError):
            ctx.student_service.update(admin, "NOPE", **self.EDIT)

    def test_invalid_keeps_record(self, ctx, admin):
        before = ctx.student_search_service.student_detail(admin, "SV001")
        with pytest.raises(ValidationError):
            ctx.student_service.update(admin, "SV001", **{**self.EDIT, "email": "bad"})
        assert ctx.student_search_service.student_detail(admin, "SV001") == before


# ------------------------------------------------------------------ UC-11 / UC-18
class TestDeleteStudent:
    def test_blocked_when_has_grades(self, ctx, admin):
        with pytest.raises(ValidationError, match="bản ghi điểm"):
            ctx.student_service.can_delete(admin, "SV001")
        with pytest.raises(ValidationError, match="bản ghi điểm"):
            ctx.student_service.delete(admin, "SV001")
        assert count(ctx, "Students", "student_id='SV001'") == 1 and count(ctx, "UserAccounts", "username='SV001'") == 1

    def test_delete_removes_profile_and_account(self, ctx, admin):
        ctx.student_service.can_delete(admin, "SV007")
        ctx.student_service.delete(admin, "SV007")
        assert count(ctx, "Students", "student_id='SV007'") == 0 and count(ctx, "UserAccounts", "username='SV007'") == 0
        with pytest.raises(AuthError):
            ctx.auth_service.login("SV007", "Sv007@123")

    def test_not_found(self, ctx, admin):
        with pytest.raises(ValidationError):
            ctx.student_service.delete(admin, "NOPE")
        with pytest.raises(ValidationError):
            ctx.student_service.can_delete(admin, "NOPE")

    def test_rollback_when_account_delete_fails(self, ctx, admin, monkeypatch):
        from app.dao.errors import DataAccessError
        def boom(*a, **k):
            raise DataAccessError("lỗi giả lập")
        monkeypatch.setattr(ctx.student_service._account_dao, "delete", boom)
        with pytest.raises(DataAccessError):
            ctx.student_service.delete(admin, "SV007")
        assert count(ctx, "Students", "student_id='SV007'") == 1 and count(ctx, "UserAccounts", "username='SV007'") == 1

    def test_database_restrict_blocks_direct_delete(self, ctx):
        from app.dao.errors import DataAccessError
        with pytest.raises(DataAccessError):
            ctx.student_service._student_dao.execute("DELETE FROM Students WHERE student_id='SV001'")

    def test_only_admin(self, ctx, lecturer):
        with pytest.raises(AuthorizationError):
            ctx.student_service.delete(lecturer, "SV007")


# ------------------------------------------------------------------ Tìm kiếm / phân trang dùng chung
class TestSearch:
    def test_paging_and_filters(self, ctx, admin):
        r = ctx.student_search_service.search_students(admin, "", page=1, page_size=4)
        assert (r.total_count, r.total_pages, len(r.items)) == (10, 3, 4)
        assert ctx.student_search_service.search_students(admin, "SV00", page=1, page_size=20).total_count == 9
        assert ctx.student_search_service.search_students(admin, "100%", page=1, page_size=20).total_count == 0  # ký tự % được escape
        assert ctx.student_search_service.search_students(admin, None, class_name="QTKD-K24A").total_count == 2
        assert ctx.student_search_service.search_students(admin, "", page=99, page_size=4).page == 3

    def test_student_cannot_search(self, ctx, student):
        with pytest.raises(AuthorizationError):
            ctx.student_search_service.search_students(student, "")
