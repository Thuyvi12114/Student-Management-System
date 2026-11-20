SOFTWARE TESTING | STUDENT MANAGEMENT SYSTEM – GROUP 05

1. Nội dung
- tests/test_core_grades_vananh.py: đăng nhập, đổi mật khẩu, phân quyền điểm, GPA.
- tests/test_modules_nghia.py: hồ sơ, tài khoản, CRUD sinh viên, tìm kiếm, rollback.
- tests/test_search_courses_son.py: tìm kiếm, dashboard, giảng viên, học phần, SQL injection.
- tests/test_stage4_auth_session.py: kiểm thử bổ sung đăng nhập, đăng xuất, đổi mật khẩu.
- tests/test_stage4_validators.py: unit test hàm kiểm tra dữ liệu.
- tests/test_stage4_database_constraints.py: PK, FK, UNIQUE, CHECK ở MySQL.
- tests/conftest.py: tự nạp dữ liệu mẫu trước mỗi test; có khóa an toàn CSDL.

2. Điều kiện
- Chạy trong thư mục gốc project đã merge Stage 3 (có app/, database/, main.py).
- Python theo requirements.txt; MySQL 8/MariaDB đang chạy.
- Cài: python -m pip install -r requirements.txt
        python -m pip install pytest
- MySQL command-line client `mysql` phải có trong PATH.

3. Chạy kiểm thử (PowerShell)
$env:SMS_DB_HOST = "127.0.0.1"
$env:SMS_DB_PORT = "3306"
$env:SMS_DB_NAME = "student_management_test"
$env:SMS_DB_USER = "root"
$env:SMS_DB_PASSWORD = ""
python -m pytest tests -v

Hoặc chạy riêng:
python -m pytest tests/test_core_grades_vananh.py -v
python -m pytest tests/test_stage4_database_constraints.py -v

4. CẢNH BÁO AN TOÀN
Fixture sẽ DROP và tạo lại các bảng trong database đã cấu hình trước MỖI test.
Chỉ được dùng CSDL kiểm thử có tên kết thúc bằng `_test` (mặc định student_management_test).
Không đặt SMS_DB_NAME=student_management hoặc tên CSDL đang chứa dữ liệu thật.

5. Kết quả
- PASSED: test chạy và đạt kết quả mong đợi.
- FAILED: chương trình trả kết quả không đúng.
- ERROR: lỗi môi trường/kết nối/cấu hình hoặc lỗi trước khi test chạy.
- SKIPPED: test được bỏ qua.
Ghi số liệu chạy thực tế vào sheet Test Summary trong file Excel; không tự điền Pass.

6. Kiểm thử hiệu năng và giao diện
- Checklist 18 màn hình, kiểm thử tích hợp và kịch bản hiệu năng được lập trong Excel.
- Hiệu năng cần tạo bộ dữ liệu 1.000 SV, 100 GV, 100 học phần, 5.000 điểm trên CSDL test;
  đo tìm kiếm <2 giây và thao tác thông thường <3 giây. Không chạy trên CSDL thật.
