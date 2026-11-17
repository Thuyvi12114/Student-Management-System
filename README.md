# UniCore — Hệ thống quản lý sinh viên

Ứng dụng desktop Python + Tkinter, kết nối MySQL.

---

## Yêu cầu

- Python 3.10+
- Docker Desktop **hoặc** XAMPP (để chạy MySQL)

---

## Cách chạy

### Dùng Docker (khuyến nghị — không cần cài XAMPP)

```bash
# 1. Khởi động MySQL trong container (lần đầu sẽ tự import database)
docker compose up -d

# 2. Chờ container sẵn sàng (~15 giây)
docker compose ps        # cột Status phải là "healthy"

# 3. Chạy ứng dụng
.venv\Scripts\python.exe main.py   # Windows
# hoặc
python main.py                      # nếu đã kích hoạt venv
```

Dừng MySQL:
```bash
docker compose down
```

Xóa cả dữ liệu (reset hoàn toàn):
```bash
docker compose down -v
```

---

### Dùng XAMPP

1. Mở **XAMPP Control Panel** → Start **MySQL**
2. Chạy ứng dụng:
   ```bash
   .venv\Scripts\python.exe main.py
   ```

---

## Cấu hình kết nối

File `config.ini` (không được commit lên Git):

```ini
[database]
host     = localhost
port     = 3306
name     = student_management
user     = root
password =
```

Hoặc dùng biến môi trường:

| Biến             | Mặc định            |
|------------------|---------------------|
| `SMS_DB_HOST`    | localhost           |
| `SMS_DB_PORT`    | 3306                |
| `SMS_DB_NAME`    | student_management  |
| `SMS_DB_USER`    | root                |
| `SMS_DB_PASSWORD`| (trống)             |

---

## Tài khoản mặc định

| Tên đăng nhập | Vai trò        | Mật khẩu  |
|---------------|---------------|-----------|
| `admin`       | Quản trị viên | `Admin@123` |
| `gv001`       | Giảng viên    | `Gv001@123` |
| `sv001`       | Sinh viên     | `Sv001@123` |
| `sv002`       | Sinh viên     | `Sv002@123` |

---

## Cài đặt lần đầu

```bash
# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Cài thư viện
pip install -r requirements.txt
```
