# SOFTWARE TESTING | STUDENT MANAGEMENT SYSTEM – GROUP 05

Nhánh `test/system-testing` hoàn thiện phần kiểm thử hệ thống, tài liệu test case, minh chứng sử dụng công cụ và theo dõi lỗi cho dự án **UniCore – Student Management System** (Python + Tkinter + MySQL).

## 1. Nội dung

* `tests/test_system_hungvi.py`: ràng buộc CSDL (`PRIMARY KEY`, `UNIQUE`, `FOREIGN KEY`, `ON DELETE RESTRICT`, `CHECK`), bền vững dữ liệu khi tạo lại `AppContext`, nạp dữ liệu lớn và ngưỡng phản hồi, điều hướng/RBAC theo 3 vai trò (`Administrator`, `Lecturer`, `Student`), luồng E2E và thông báo lỗi nghiệp vụ.

* `tests/test_auth_session.py`: kiểm thử đăng nhập, phiên làm việc, tài khoản `Inactive` (`SV005`) và đổi mật khẩu.

* `tests/test_validators.py`: unit test các hàm kiểm tra dữ liệu đầu vào.

* `tests/test_core_grades_vananh.py`: kiểm thử nghiệp vụ điểm, phân quyền nhập/xem điểm và tính GPA.

* `tests/test_modules_nghia.py`: kiểm thử hồ sơ, quản lý tài khoản, CRUD sinh viên, tìm kiếm và rollback giao dịch.

* `tests/test_search_courses_son.py`: kiểm thử tìm kiếm, dashboard, giảng viên, học phần và an toàn truy vấn.

* `tests/conftest.py`: tự nạp lại `database/student_management.sql` trước mỗi test; có khóa an toàn bắt buộc tên CSDL kết thúc bằng `_test`.

* `testcase/`: tài liệu test case Excel (`SMS Testcase_system_hungvi.xlsx`, `SMS_TestCases_InputValidation.xlsx`, `Test_Cases_Auth_Session.xlsx`).

* Công cụ theo dõi lỗi & minh chứng (`evidence of tool usage`): Git/GitHub (`docs/GIT_WORKFLOW.md`), `pytest`, MySQL và bảng theo dõi lỗi trên **Jira** (`To Do → In Progress → In Review → Done`).

## 2. Điều kiện

* Chạy trong thư mục gốc project đã có đầy đủ `app/`, `database/`, `tests/`, `testcase/` và `main.py`.

* Python theo `requirements.txt` (cài thêm `pytest` để chạy bộ kiểm thử); MySQL 8 / MariaDB / MySQL 9.x đang chạy.

* Cài đặt:

  ```
  python -m pip install -r requirements.txt
  python -m pip install pytest
  
  ```

* Client `mysql` phải nằm trong `PATH` và tương thích với cấu hình xác thực của MySQL Server đang chạy (nếu máy có nhiều bản MySQL/XAMPP, đưa đúng thư mục `bin` đang dùng lên đầu `PATH`).

## 3. Chạy kiểm thử (PowerShell)

```
$env:SMS_DB_HOST = "127.0.0.1"
$env:SMS_DB_PORT = "3306"
$env:SMS_DB_NAME = "student_management_test"
$env:SMS_DB_USER = "root"
$env:SMS_DB_PASSWORD = ""
python -m pytest -v

```

Hoặc chạy riêng:

```
python -m pytest tests/test_system_hungvi.py -v
python -m pytest tests/test_auth_session.py -v

```

## 4. CẢNH BÁO AN TOÀN

* Fixture trong `tests/conftest.py` sẽ nạp lại schema/dữ liệu từ `database/student_management.sql` trên database test trước MỖI test.

* Chỉ được dùng CSDL kiểm thử có tên kết thúc bằng `_test` (mặc định `student_management_test`).

* Tuyệt đối không đặt `SMS_DB_NAME=student_management` hoặc trỏ vào CSDL chứa dữ liệu thật.

## 5. Kết quả

* `PASSED`: test chạy và đạt kết quả mong đợi.

* `FAILED`: chương trình hoặc ràng buộc trả về kết quả không đúng mong đợi.

* `ERROR`: lỗi môi trường, kết nối/xác thực MySQL, thiếu client `mysql` trên `PATH` hoặc lỗi trước khi test chạy.

* `SKIPPED`: test bị bỏ qua theo điều kiện kiểm thử.

* Ghi nhận kết quả chạy thực tế vào tài liệu kiểm thử (`testcase/SMS Testcase_system_hungvi.xlsx` và các file test case liên quan), đồng thời ghi nhận/cập nhật các lỗi phát sinh trên **Jira** kèm ảnh chụp màn hình làm minh chứng (`evidence of tool usage`).

## 6. Kiểm thử hiệu năng, phân quyền và tích hợp

* Kiểm thử hệ thống (`tests/test_system_hungvi.py`) bao phủ ràng buộc CSDL, bền vững sau khi tạo lại `AppContext`, phân quyền/điều hướng 3 vai trò và luồng E2E.

* Hiệu năng nạp bộ dữ liệu `1.000` SV, `100` GV, `100` học phần, `5.000` điểm trên CSDL `*_test` (`student_management_test`); đo thời gian tìm kiếm `< 2.0s` và thao tác đăng nhập / lưu điểm / xem GPA `< 3.0s`. Không chạy trên CSDL thật.
