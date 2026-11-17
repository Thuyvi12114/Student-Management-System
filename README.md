# UniCore — Hệ thống quản lý sinh viên (Nhóm 05)

Ứng dụng desktop **Python + Tkinter** kết nối **MySQL 8**, làm lại theo tài liệu
`RequirementAndDesignDocument_Group05` (5 bảng, 19 use case, 3 vai trò).

Kiến trúc 3 lớp: `Config → Database → DAO → Service → UI (Tkinter)`.

```
app/
  config.py  db.py  context.py      # cấu hình, kết nối, khởi tạo các service
  models.py                         # thực thể (UserAccounts, Students, Lecturers, Courses, Grades)
  dao/                              # SQL tham số hóa (%s), giao dịch trong BaseDAO
  service/                          # nghiệp vụ + phân quyền + kiểm tra dữ liệu
  security/                         # băm mật khẩu PBKDF2, phiên đăng nhập, RBAC
  ui/                               # màn hình Tkinter (accounts, profile, students, search, dashboard, lecturers, courses, grades)
database/student_management.sql     # schema + dữ liệu mẫu
tests/                              # pytest (cần MySQL đang chạy)
docs/GIT_WORKFLOW.md                # hướng dẫn nhánh/commit cho nhóm
scripts/                            # script commit theo từng người + OWNERSHIP.txt (file nào của ai)
```

## 1. Cài đặt

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

> Nếu PowerShell chặn script: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
> Nếu `pip.exe` bị chặn: luôn dùng `python -m pip`.

## 2. Chạy MySQL

**Docker (khuyến nghị)**

```powershell
docker compose up -d          # lần đầu tự import database/student_management.sql
docker compose ps             # đợi trạng thái "healthy"
```

Nếu cổng 3306 đã bị chiếm (XAMPP/MySQL cài sẵn): đổi `"3306:3306"` trong `docker-compose.yml`
thành `"3307:3306"` rồi đặt `port = 3307` trong `config.ini`.

Reset toàn bộ dữ liệu: `docker compose down -v` rồi `docker compose up -d`.

**XAMPP / MySQL cài sẵn**: bật MySQL rồi nạp file SQL một lần

```powershell
mysql -u root -p < database/student_management.sql
```

## 3. Cấu hình kết nối

Sao chép `config.example.ini` thành `config.ini` (đã được `.gitignore`, không commit mật khẩu):

```ini
[database]
host = 127.0.0.1
port = 3306
name = student_management
user = root
password =
```

Hoặc dùng biến môi trường `SMS_DB_HOST`, `SMS_DB_PORT`, `SMS_DB_NAME`, `SMS_DB_USER`, `SMS_DB_PASSWORD`
(biến môi trường ưu tiên hơn `config.ini`).

## 4. Chạy ứng dụng

```powershell
python main.py
```

### Tài khoản mẫu

| Tên đăng nhập | Vai trò | Mật khẩu |
|---|---|---|
| `admin` | Quản trị viên | `Admin@123` |
| `GV001`, `GV002`, `GV003` | Giảng viên | `Gv001@123`, `Gv002@123`, `Gv003@123` |
| `SV001` … `SV010` | Sinh viên | `Sv001@123` … `Sv010@123` |

Tên đăng nhập không phân biệt hoa/thường. `SV005` là tài khoản **Inactive** để thử chặn đăng nhập.
Với sinh viên/giảng viên, **tên đăng nhập luôn bằng mã SV/GV** (đúng tài liệu thiết kế).

## 5. Chạy kiểm thử

```powershell
python -m pip install pytest
python -m pytest -q           # dùng CSDL riêng student_management_test, tự nạp lại SQL mỗi test
```

Test cần lệnh `mysql` (client) trong PATH để nạp `database/student_management.sql`.
Đổi CSDL test: `set SMS_DB_NAME=ten_khac` trước khi chạy.

## 6. Quy tắc nghiệp vụ chính (theo tài liệu thiết kế)

- Mã SV/GV/học phần là khóa chính dạng chữ (`VARCHAR(20)`); mã sinh viên **không đổi được** sau khi tạo.
- Tạo/xóa sinh viên, giảng viên: hồ sơ + tài khoản trong **một giao dịch** (lỗi thì rollback cả hai).
- Không xóa sinh viên đã có điểm, không xóa học phần đã có điểm, không xóa giảng viên còn phụ trách học phần
  (khóa ngoại `RESTRICT` + kiểm tra ở service).
- Sinh viên chỉ sửa **email, số điện thoại, địa chỉ**; hồ sơ giảng viên chỉ đọc.
- Admin chỉ **xem** điểm; giảng viên chỉ nhập điểm cho học phần mình phụ trách; mỗi cặp (sinh viên, học phần) một điểm 0–10.
- Điểm trung bình = Σ(điểm × tín chỉ) / Σ tín chỉ.
- Mật khẩu: tối thiểu 8 ký tự, có hoa, thường, số, không khoảng trắng; lưu băm PBKDF2-HMAC-SHA256.
