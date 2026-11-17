-- =====================================================================
-- UniCore - Student Management System | Nhóm 05
-- Script tạo cơ sở dữ liệu MySQL 8.0 (tương thích MariaDB 10.5+) theo đúng
-- tài liệu thiết kế: 5 bảng UserAccounts, Students, Lecturers, Courses, Grades.
-- Chạy: mysql -u root -p < database/student_management.sql
--
-- Tài khoản mẫu (mật khẩu lưu dạng băm PBKDF2-HMAC-SHA256, không lưu dạng thô):
--   admin / Admin@123    GV001..GV003 / Gv001@123 ...    SV001..SV010 / Sv001@123 ...
--   Tên đăng nhập không phân biệt hoa/thường (gv001 = GV001).
--   SV005 là tài khoản Inactive để kiểm thử chặn đăng nhập.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS student_management
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_management;

SET NAMES utf8mb4;


-- Xóa theo thứ tự ngược của khóa ngoại để có thể chạy lại script
DROP TABLE IF EXISTS Grades;
DROP TABLE IF EXISTS Courses;
DROP TABLE IF EXISTS Lecturers;
DROP TABLE IF EXISTS Students;
DROP TABLE IF EXISTS UserAccounts;

-- ---------------------------------------------------------------------
-- 1. UserAccounts: tài khoản đăng nhập (3 vai trò)
--    Collation *_ci nên tên đăng nhập không phân biệt hoa/thường.
-- ---------------------------------------------------------------------
CREATE TABLE UserAccounts (
    account_id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username      VARCHAR(50)     NOT NULL,
    password_hash VARCHAR(255)    NOT NULL,
    role          ENUM('Administrator', 'Lecturer', 'Student') NOT NULL,
    status        ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
    CONSTRAINT pk_useraccounts PRIMARY KEY (account_id),
    CONSTRAINT uq_useraccounts_username UNIQUE (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 2. Students: mỗi sinh viên có đúng 1 tài khoản (account_id UNIQUE NOT NULL)
-- ---------------------------------------------------------------------
CREATE TABLE Students (
    student_id    VARCHAR(20)     NOT NULL,
    account_id    BIGINT UNSIGNED NOT NULL,
    full_name     VARCHAR(100)    NOT NULL,
    date_of_birth DATE            NOT NULL,
    gender        VARCHAR(20)     NOT NULL,
    email         VARCHAR(254)    NOT NULL,
    phone_number  VARCHAR(20)     NOT NULL,
    address       VARCHAR(255)    NULL,
    class_name    VARCHAR(50)     NOT NULL,
    CONSTRAINT pk_students PRIMARY KEY (student_id),
    CONSTRAINT uq_students_account UNIQUE (account_id),
    CONSTRAINT fk_students_account FOREIGN KEY (account_id)
        REFERENCES UserAccounts (account_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_students_gender CHECK (gender IN ('Nam', 'Nữ', 'Khác')),
    INDEX idx_students_name (full_name),
    INDEX idx_students_class (class_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 3. Lecturers: mỗi giảng viên có đúng 1 tài khoản
-- ---------------------------------------------------------------------
CREATE TABLE Lecturers (
    lecturer_id  VARCHAR(20)     NOT NULL,
    account_id   BIGINT UNSIGNED NOT NULL,
    full_name    VARCHAR(100)    NOT NULL,
    email        VARCHAR(254)    NOT NULL,
    phone_number VARCHAR(20)     NOT NULL,
    department   VARCHAR(100)    NOT NULL,
    CONSTRAINT pk_lecturers PRIMARY KEY (lecturer_id),
    CONSTRAINT uq_lecturers_account UNIQUE (account_id),
    CONSTRAINT fk_lecturers_account FOREIGN KEY (account_id)
        REFERENCES UserAccounts (account_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_lecturers_name (full_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 4. Courses: mỗi học phần có đúng 1 giảng viên phụ trách
--    (RESTRICT: không xóa được giảng viên đang phụ trách học phần)
-- ---------------------------------------------------------------------
CREATE TABLE Courses (
    course_id   VARCHAR(20)      NOT NULL,
    lecturer_id VARCHAR(20)      NOT NULL,
    course_name VARCHAR(150)     NOT NULL,
    credits     TINYINT UNSIGNED NOT NULL,
    description TEXT             NULL,
    CONSTRAINT pk_courses PRIMARY KEY (course_id),
    CONSTRAINT fk_courses_lecturer FOREIGN KEY (lecturer_id)
        REFERENCES Lecturers (lecturer_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_courses_credits CHECK (credits > 0),
    INDEX idx_courses_lecturer (lecturer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 5. Grades: điểm cuối kỳ. Mỗi cặp (student_id, course_id) tối đa 1 điểm.
--    (RESTRICT: không xóa sinh viên / học phần đã có điểm)
-- ---------------------------------------------------------------------
CREATE TABLE Grades (
    grade_id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id  VARCHAR(20)     NOT NULL,
    course_id   VARCHAR(20)     NOT NULL,
    grade_value DECIMAL(4, 2)   NOT NULL,
    CONSTRAINT pk_grades PRIMARY KEY (grade_id),
    CONSTRAINT uq_grades_student_course UNIQUE (student_id, course_id),
    CONSTRAINT fk_grades_student FOREIGN KEY (student_id)
        REFERENCES Students (student_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_grades_course FOREIGN KEY (course_id)
        REFERENCES Courses (course_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_grades_value CHECK (grade_value BETWEEN 0 AND 10),
    INDEX idx_grades_course (course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================================
-- DỮ LIỆU MẪU
-- =====================================================================

INSERT INTO UserAccounts (username, password_hash, role, status) VALUES
  ('admin', 'pbkdf2_sha256$210000$Ll2uM2FY8AAFIFoKws0lIg==$nwhbBUqUQuhbNlbAb3ICOVzG2ktZ3AF8nc6LfJ/q/EY=', 'Administrator', 'Active'),
  ('GV001', 'pbkdf2_sha256$210000$wS1jO+AcDAZn+8YGW+lj0Q==$Naj3EXH7IIPViQCOKDaA+96qR87Tz8u/Guq0obZ6psA=', 'Lecturer', 'Active'),
  ('GV002', 'pbkdf2_sha256$210000$3whAEK/c8vxAILKPu287zA==$LpUkaXl/JKZmiFEqJBt9TS5advhSOUiXk7jaT/LBJLU=', 'Lecturer', 'Active'),
  ('GV003', 'pbkdf2_sha256$210000$x/TXQf85DRr+63+eM37LzA==$iMoSlzDv4h9sWR15TEpZ/TJv8hcCCIjnDX4pCRXrhqo=', 'Lecturer', 'Active'),
  ('SV001', 'pbkdf2_sha256$210000$lTHlC4rFNk+I/S8jXie0cA==$XLpUqyCh026wflAdrtmm2992t+EbehApuUPjBDIr2LE=', 'Student', 'Active'),
  ('SV002', 'pbkdf2_sha256$210000$aE23iHSyY+y787nK26LbOQ==$R5CwEaLgYdpqUXDMni5N/FNrHhDXK7cQk5VuCaEbdTo=', 'Student', 'Active'),
  ('SV003', 'pbkdf2_sha256$210000$56kXhgy9kqlZdQBDIGDtew==$WgSJqjiliCm2uo+fPaVmvL3vVvuWaETcVTtTP0Y7VlY=', 'Student', 'Active'),
  ('SV004', 'pbkdf2_sha256$210000$nKTPDxTZ5HF0xGb7/XzZPg==$u0++LX5r8CPDjJNWDMdEgpS0fExqW4jfVXxwry4TAMM=', 'Student', 'Active'),
  ('SV005', 'pbkdf2_sha256$210000$vO0CktkSjzPJw6MPU2/csA==$QR1pn4D354LXf2FZuaJMVTpY+2IEE7hg5Ou1awNbqzo=', 'Student', 'Inactive'),
  ('SV006', 'pbkdf2_sha256$210000$L91J7Wd/06WsT8xH7103rQ==$H/GwrCgLqvj7fk+/zmpzPWO+JjN4HVSn2akL7qoIbb4=', 'Student', 'Active'),
  ('SV007', 'pbkdf2_sha256$210000$xsB+LlZUEUyRvy6GX0anbw==$NHqMSwbAEEVogQABVa/KitCEudlciiDGz8TL8kdo1zE=', 'Student', 'Active'),
  ('SV008', 'pbkdf2_sha256$210000$0wyxhAVkkYkvi0djCRGOlw==$DlIOlKAPutYUV2o+DH8wlYkZ23r0Ju7+JGSsltFGiec=', 'Student', 'Active'),
  ('SV009', 'pbkdf2_sha256$210000$qGEo1Hm4qnuR2i6Tq3WFAQ==$oK6RPsg42WtcP4vCjlNZAWaL4d/CNM9IBIx/2ucYWtI=', 'Student', 'Active'),
  ('SV010', 'pbkdf2_sha256$210000$ZD+hbJNu/mNbnsO0u4+gng==$d5qWOh+N2dLbhV8jQFRlCchn4SerTYWkrfFDw/k4Lo0=', 'Student', 'Active');

INSERT INTO Lecturers (lecturer_id, account_id, full_name, email, phone_number, department) VALUES
  ('GV001', (SELECT account_id FROM UserAccounts WHERE username = 'GV001'), 'Trần Hoàng Nam', 'nam.tran@unicore.edu.vn', '0903456789', 'Công nghệ thông tin'),
  ('GV002', (SELECT account_id FROM UserAccounts WHERE username = 'GV002'), 'Lê Thị Mai', 'mai.le@unicore.edu.vn', '0904567890', 'Toán - Tin'),
  ('GV003', (SELECT account_id FROM UserAccounts WHERE username = 'GV003'), 'Phạm Quốc Việt', 'viet.pham@unicore.edu.vn', '0905678901', 'Công nghệ phần mềm');

INSERT INTO Students (student_id, account_id, full_name, date_of_birth, gender, email, phone_number, address, class_name) VALUES
  ('SV001', (SELECT account_id FROM UserAccounts WHERE username = 'SV001'), 'Nguyễn Minh Anh', '2006-08-15', 'Nữ', 'minhanh.nguyen@sv.unicore.edu.vn', '0901234567', '24 Nguyễn Văn Cừ, Phường 4, Quận 5, TP. Hồ Chí Minh', 'CNTT-K24A'),
  ('SV002', (SELECT account_id FROM UserAccounts WHERE username = 'SV002'), 'Trần Quốc Bảo', '2006-03-02', 'Nam', 'quocbao.tran@sv.unicore.edu.vn', '0912345678', '15 Lê Lợi, Quận 1, TP. Hồ Chí Minh', 'CNTT-K24A'),
  ('SV003', (SELECT account_id FROM UserAccounts WHERE username = 'SV003'), 'Lê Hoàng Phúc', '2005-11-20', 'Nam', 'hoangphuc.le@sv.unicore.edu.vn', '0933456789', NULL, 'CNTT-K24A'),
  ('SV004', (SELECT account_id FROM UserAccounts WHERE username = 'SV004'), 'Phạm Ngọc Linh', '2006-01-09', 'Nữ', 'ngoclinh.pham@sv.unicore.edu.vn', '0904567890', '88 Trần Hưng Đạo, Quận 5, TP. Hồ Chí Minh', 'CNTT-K24B'),
  ('SV005', (SELECT account_id FROM UserAccounts WHERE username = 'SV005'), 'Võ Đức Huy', '2005-07-30', 'Nam', 'duchuy.vo@sv.unicore.edu.vn', '0905678901', NULL, 'CNTT-K24B'),
  ('SV006', (SELECT account_id FROM UserAccounts WHERE username = 'SV006'), 'Đặng Thu Hà', '2006-05-12', 'Nữ', 'thuha.dang@sv.unicore.edu.vn', '0916789012', '7 Hai Bà Trưng, Quận 3, TP. Hồ Chí Minh', 'QTKD-K24A'),
  ('SV007', (SELECT account_id FROM UserAccounts WHERE username = 'SV007'), 'Bùi Gia Hân', '2006-09-25', 'Nữ', 'giahan.bui@sv.unicore.edu.vn', '0927890123', NULL, 'QTKD-K24A'),
  ('SV008', (SELECT account_id FROM UserAccounts WHERE username = 'SV008'), 'Đỗ Tuấn Kiệt', '2005-12-03', 'Nam', 'tuankiet.do@sv.unicore.edu.vn', '0938901234', NULL, 'CNTT-K24A'),
  ('SV009', (SELECT account_id FROM UserAccounts WHERE username = 'SV009'), 'Nguyễn Hoàng Long', '2006-04-18', 'Nam', 'hoanglong.nguyen@sv.unicore.edu.vn', '0949012345', NULL, 'CNTT-K24B'),
  ('SV010', (SELECT account_id FROM UserAccounts WHERE username = 'SV010'), 'Nguyễn Khánh Vy', '2006-06-21', 'Nữ', 'khanhvy.nguyen@sv.unicore.edu.vn', '0950123456', NULL, 'CNTT-K24A');

INSERT INTO Courses (course_id, lecturer_id, course_name, credits, description) VALUES
  ('CS101', 'GV001', 'Nhập môn lập trình', 3, 'Làm quen với tư duy lập trình, biến, cấu trúc điều khiển, hàm và xử lý dữ liệu cơ bản.'),
  ('CS201', 'GV001', 'Cơ sở dữ liệu', 3, 'Trang bị kiến thức về mô hình dữ liệu quan hệ, thiết kế cơ sở dữ liệu, chuẩn hóa và ngôn ngữ truy vấn SQL. Thực hành tổ chức, khai thác và bảo toàn tính toàn vẹn dữ liệu.'),
  ('CS202', 'GV001', 'Cấu trúc dữ liệu và giải thuật', 4, 'Các cấu trúc dữ liệu nền tảng (danh sách, cây, đồ thị) và giải thuật sắp xếp, tìm kiếm.'),
  ('SE201', 'GV003', 'Công nghệ phần mềm', 3, 'Quy trình phát triển phần mềm, phân tích yêu cầu, thiết kế và kiểm thử.'),
  ('MA101', 'GV002', 'Toán rời rạc', 3, 'Logic, tập hợp, quan hệ, đồ thị và tổ hợp ứng dụng trong khoa học máy tính.'),
  ('CS203', 'GV003', 'Lập trình hướng đối tượng', 4, 'Các nguyên lý hướng đối tượng: đóng gói, kế thừa, đa hình và mẫu thiết kế cơ bản.'),
  ('CS301', 'GV002', 'Mạng máy tính', 3, NULL);

INSERT INTO Grades (student_id, course_id, grade_value) VALUES
  ('SV001', 'CS101', 8.50),
  ('SV001', 'CS201', 9.00),
  ('SV001', 'CS202', 8.00),
  ('SV001', 'MA101', 8.50),
  ('SV002', 'CS101', 7.50),
  ('SV002', 'CS201', 7.50),
  ('SV002', 'MA101', 6.50),
  ('SV003', 'CS101', 7.00),
  ('SV003', 'CS201', 8.00),
  ('SV004', 'CS101', 9.00),
  ('SV005', 'CS101', 6.00),
  ('SV006', 'SE201', 8.00);
