"""Test đăng nhập, đăng xuất, đổi mật khẩu (FR-02; UC-04, 05, 06).

Mã TC-AUTH-xx trong docstring dùng để điền vào cột "Mã test case" ở file Excel.
Tài khoản mẫu lấy từ README: SV001 / Sv001@123, admin / Admin@123.
"""
import pytest

from app.service.exceptions import AuthError, ValidationError


# ---------- UC-04: đăng nhập ----------
@pytest.mark.parametrize(
    "username, password",
    [
        ("", "Admin@123"),    # bỏ trống tên đăng nhập
        ("admin", ""),        # bỏ trống mật khẩu
        (" ", "Admin@123"),   # tên đăng nhập chỉ có dấu cách
    ],
    ids=["thieu_username", "thieu_password", "username_dau_cach"],
)
def test_tc_auth_01_login_thieu_du_lieu(ctx, username, password):
    """TC-AUTH-01: thiếu tên đăng nhập hoặc mật khẩu thì bị từ chối."""
    with pytest.raises(ValidationError):
        ctx.auth_service.login(username, password)


def test_tc_auth_02_login_sai_mat_khau(ctx):
    """TC-AUTH-02: đúng tên đăng nhập, sai mật khẩu."""
    with pytest.raises(AuthError):
        ctx.auth_service.login("SV001", "Sai@12345")


def test_tc_auth_03_login_tai_khoan_khong_ton_tai(ctx):
    """TC-AUTH-03: tên đăng nhập không có trong hệ thống."""
    with pytest.raises(AuthError):
        ctx.auth_service.login("khongtontai", "Sv001@123")


def test_tc_auth_09_login_tai_khoan_inactive(ctx):
    """TC-AUTH-09: tài khoản bị vô hiệu (SV005 là Inactive trong dữ liệu mẫu)."""
    with pytest.raises(AuthError):
        ctx.auth_service.login("SV005", "Sv005@123")


# ---------- UC-05: đăng xuất ----------
def test_tc_auth_04_logout_huy_phien(ctx):
    """TC-AUTH-04: sau khi đăng xuất thì phiên không còn hiệu lực."""
    ctx.auth_service.login("SV001", "Sv001@123")
    ctx.auth_service.logout()
    with pytest.raises(AuthError):
        ctx.auth_service.require_active_session()


# ---------- UC-06: đổi mật khẩu ----------
def test_tc_auth_05_doi_mat_khau_sai_mat_khau_cu(ctx):
    """TC-AUTH-05: nhập sai mật khẩu hiện tại."""
    ctx.auth_service.login("SV001", "Sv001@123")
    with pytest.raises(AuthError):
        ctx.auth_service.change_password("Wrong@123", "NewPass@123", "NewPass@123")


def test_tc_auth_06_doi_mat_khau_xac_nhan_khong_khop(ctx):
    """TC-AUTH-06: mật khẩu mới và ô xác nhận không giống nhau."""
    ctx.auth_service.login("SV001", "Sv001@123")
    with pytest.raises(ValidationError):
        ctx.auth_service.change_password("Sv001@123", "NewPass@123", "Other@123")


def test_tc_auth_07_doi_mat_khau_qua_yeu(ctx):
    """TC-AUTH-07: mật khẩu mới không đạt chính sách (quá ngắn, quá đơn giản)."""
    ctx.auth_service.login("SV001", "Sv001@123")
    with pytest.raises(ValidationError):
        ctx.auth_service.change_password("Sv001@123", "weak", "weak")


def test_tc_auth_08_doi_mat_khau_thanh_cong(ctx):
    """TC-AUTH-08: đổi thành công, đăng nhập lại bằng mật khẩu mới được."""
    ctx.auth_service.login("SV001", "Sv001@123")
    ctx.auth_service.change_password("Sv001@123", "NewPass@123", "NewPass@123")
    ctx.auth_service.logout()
    ctx.auth_service.login("SV001", "NewPass@123")
