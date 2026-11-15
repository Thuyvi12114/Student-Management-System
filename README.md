# Hệ thống quản lý sinh viên — Core System, Database & Xác thực

Đồ án nhóm môn học, ứng dụng desktop **Python (tkinter) + MySQL** theo **kiến trúc 3 lớp**.
Phạm vi thành viên 1: khởi tạo dự án, cơ sở dữ liệu, tài khoản/xác thực (Auth/Account),
màn hình đăng nhập và khung điều hướng phân quyền cho 3 vai trò.

## 1. Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ / giao diện | Python 3.10+ (đã kiểm thử với Python 3.14.6), tkinter |
| Cơ sở dữ liệu | MySQL 8.0 (InnoDB, utf8mb4) |
| Truy cập dữ liệu | `mysql-connector-python` 26.10.0, prepared statement |
| Băm mật khẩu | PBKDF2-HMAC-SHA256, 210.000 vòng, salt ngẫu nhiên 16 byte |
| Quản lý phụ thuộc | `venv` + `requirements.txt` |

## 2. Cấu trúc cây thư mục

```text
Student-Management-System/
├── main.py                       # Điểm khởi động, điều phối Login ↔ Workspace
├── requirements.txt              # mysql-connector-python
├── config.example.ini            # Mẫu cấu hình kết nối MySQL
├── README.md
├── .gitignore                    # Bỏ qua .venv/, __pycache__/, config.ini
├── database/
│   └── student_management.sql    # 5 bảng + FK + UNIQUE + CHECK + dữ liệu mẫu
└── app/
    ├── __init__.py
    ├── config.py                 # Đọc config.ini hoặc biến môi trường SMS_DB_*
    ├── db.py                     # Cấp kết nối MySQL, kiểm tra kết nối
    ├── models.py                 # Role, AccountStatus và 5 dataclass thực thể
    ├── context.py                # Nối các lớp: Config → DAO → Service
    ├── dao/
    │   ├── __init__.py
    │   ├── errors.py             # DataAccessError
    │   └── user_account_dao.py   # UserAccountDAO với prepared statement
    ├── security/
    │   ├── __init__.py
    │   ├── password_hasher.py    # Băm/kiểm tra PBKDF2
    │   ├── password_policy.py    # Quy tắc độ mạnh mật khẩu
    │   ├── session.py            # Session + SessionManager (8 giờ)
    │   └── rbac.py               # AppModule + RbacPolicy
    ├── service/
    │   ├── __init__.py
    │   ├── exceptions.py         # ServiceError, AuthError, ValidationError
    │   └── auth_service.py       # Đăng nhập, đăng xuất, đổi mật khẩu
    └── ui/
        ├── __init__.py
        ├── theme.py              # Màu, font, widget dùng chung
        ├── login_view.py         # UI 1.1 — màn hình đăng nhập
        ├── main_view.py          # Khung điều hướng RBAC sau đăng nhập
        └── change_password_dialog.py
```

Luồng phụ thuộc một chiều: **UI → Service → DAO → Database**.
UI không viết SQL, DAO không chứa nghiệp vụ, service không biết tkinter.

## 3. Thiết kế cơ sở dữ liệu

| Bảng | Khóa chính | Ràng buộc chính |
|---|---|---|
| `UserAccounts` | `AccountID` | `Username` UNIQUE, CHECK `Role`, CHECK `Status` |
| `Students` | `StudentID` | `AccountID` FK UNIQUE, `StudentCode`/`Email` UNIQUE, CHECK giới tính, năm nhập học, email |
| `Lecturers` | `LecturerID` | `AccountID` FK UNIQUE, `LecturerCode`/`Email` UNIQUE, CHECK giới tính, học vị |
| `Courses` | `CourseID` | `CourseCode` UNIQUE, FK `LecturerID` (SET NULL), CHECK tín chỉ 1–10, học kỳ, năm học |
| `Grades` | `GradeID` | UNIQUE (`StudentID`, `CourseID`), FK CASCADE, CHECK điểm 0–10, trạng thái |

Quan hệ: `UserAccounts 1—1 Students`, `UserAccounts 1—1 Lecturers`,
`Lecturers 1—n Courses`, `Students n—n Courses` (qua `Grades`).

## 4. Cài đặt và chạy

### Bước 1 — Tạo môi trường Python

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Cài phụ thuộc:

```bash
pip install -r requirements.txt
```

### Bước 2 — Tạo cơ sở dữ liệu

```bash
mysql -u root -p < database/student_management.sql
```

Script tạo database `student_management`, 5 bảng và dữ liệu mẫu; chạy lại được nhiều lần.

### Bước 3 — Cấu hình kết nối

```bash
cp config.example.ini config.ini
```

Windows: `copy config.example.ini config.ini`. Sau đó sửa `password` (và `host`/`port` nếu cần).
Tệp `config.ini` đã nằm trong `.gitignore`, không đưa lên GitHub.

Có thể cấu hình bằng biến môi trường thay cho tệp:
`SMS_DB_HOST`, `SMS_DB_PORT`, `SMS_DB_NAME`, `SMS_DB_USER`, `SMS_DB_PASSWORD`.

### Bước 4 — Chạy ứng dụng

```bash
python main.py
```

## 5. Tài khoản mẫu

| Tên đăng nhập | Mật khẩu | Vai trò | Trạng thái |
|---|---|---|---|
| `admin` | `Admin@123` | Admin | Active |
| `gv001` | `Lecturer@123` | Giảng viên | Active |
| `sv001` | `Student@123` | Sinh viên | Active |
| `sv002` | `Student@123` | Sinh viên | **Inactive** (kiểm thử chặn đăng nhập) |

Mật khẩu trong CSDL chỉ tồn tại dưới dạng băm PBKDF2; mật khẩu gốc không được lưu.

## 6. Phân quyền (RBAC)

| Module | Admin | Giảng viên | Sinh viên |
|---|:---:|:---:|:---:|
| Tổng quan | ✓ | ✓ | ✓ |
| Tài khoản & phân quyền | ✓ |  |  |
| Quản lý sinh viên | ✓ |  |  |
| Quản lý giảng viên | ✓ |  |  |
| Quản lý môn học | ✓ | ✓ |  |
| Quản lý điểm | ✓ | ✓ |  |
| Kết quả học tập |  |  | ✓ |
| Thông tin cá nhân | ✓ | ✓ | ✓ |

Thanh điều hướng chỉ hiển thị module theo vai trò; `MainView._select_module`
kiểm tra lại bằng `RbacPolicy.can_access` trước khi mở nội dung.

## 7. Đối chiếu yêu cầu

| Yêu cầu | Nơi triển khai |
|---|---|
| Khởi tạo cấu trúc 3 lớp, kết nối MySQL, cấu hình Git | `app/`, `app/context.py`, `.gitignore`, README |
| Script 5 bảng + khóa ngoại + UNIQUE + CHECK + dữ liệu mẫu | `database/student_management.sql` |
| `UserAccountDAO` với truy vấn tham số hóa | `app/dao/user_account_dao.py` |
| Đăng nhập, kiểm tra Active/Inactive, băm mật khẩu | `app/service/auth_service.py`, `app/security/password_hasher.py` |
| Đăng xuất (hủy phiên), đổi mật khẩu | `AuthService.logout`, `AuthService.change_password`, `SessionManager` |
| Màn hình Login (UI 1.1) | `app/ui/login_view.py` |
| Khung điều hướng phân quyền 3 vai trò | `app/ui/main_view.py`, `app/security/rbac.py` |

Use case liên quan: **FR-02**, **UC-04** (đăng nhập), **UC-05** (đăng xuất),
**UC-06** (đổi mật khẩu), **UI 1.1** (Login).

## 8. Ghi chú bảo mật

- Mọi câu lệnh SQL dùng `cursor(prepared=True)` với placeholder `%s` — không nối chuỗi đầu vào, chống SQL Injection.
- Mật khẩu băm PBKDF2-HMAC-SHA256 với salt riêng cho từng tài khoản; so sánh bằng `hmac.compare_digest`.
- Sai tên đăng nhập và sai mật khẩu trả về cùng một thông điệp để tránh dò tài khoản.
- Tài khoản `INACTIVE` bị chặn khi đăng nhập và bị kiểm tra lại mỗi lần thao tác cần phiên hợp lệ.
- Đăng xuất hủy token phiên trong `SessionManager`; phiên có thời hạn 8 giờ.
- Thông tin kết nối MySQL nằm ngoài mã nguồn (`config.ini` / biến môi trường), không commit lên Git.

## 9. Git / GitHub

```bash
git add .
git commit -m "Chuyển dự án sang Python tkinter, giữ nguyên CSDL và module xác thực"
git remote add origin https://github.com/<tài-khoản>/Student-Management-System.git
git branch -M main
git push -u origin main
```

Nếu repository đã có `origin`, chỉ cần `git add .`, commit và `git push`.
