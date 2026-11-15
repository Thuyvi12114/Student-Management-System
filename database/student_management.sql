-- =====================================================================
-- STUDENT MANAGEMENT SYSTEM — Script tạo cơ sở dữ liệu MySQL 8.0
-- Chạy: mysql -u root -p < database/student_management.sql
--
-- Bao gồm 5 bảng: UserAccounts, Students, Lecturers, Courses, Grades
-- Kèm khóa ngoại, ràng buộc UNIQUE, CHECK và dữ liệu mẫu.
-- Mật khẩu mẫu được lưu dưới dạng băm PBKDF2-HMAC-SHA256 (xem PasswordHasher.java).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS student_management
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE student_management;

SET NAMES utf8mb4;

-- Xóa bảng theo thứ tự khóa ngoại để chạy lại script được nhiều lần.
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Grades;
DROP TABLE IF EXISTS Courses;
DROP TABLE IF EXISTS Students;
DROP TABLE IF EXISTS Lecturers;
DROP TABLE IF EXISTS UserAccounts;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- 1. UserAccounts: tài khoản đăng nhập và vai trò (RBAC)
-- ---------------------------------------------------------------------
CREATE TABLE UserAccounts (
    AccountID    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    Username     VARCHAR(50)     NOT NULL,
    PasswordHash VARCHAR(255)    NOT NULL,
    FullName     VARCHAR(100)    NOT NULL,
    Role         VARCHAR(20)     NOT NULL,
    Status       VARCHAR(10)     NOT NULL DEFAULT 'ACTIVE',
    LastLoginAt  DATETIME        NULL,
    CreatedAt    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (AccountID),
    CONSTRAINT uq_useraccounts_username UNIQUE (Username),
    CONSTRAINT ck_useraccounts_role CHECK (Role IN ('ADMIN', 'LECTURER', 'STUDENT')),
    CONSTRAINT ck_useraccounts_status CHECK (Status IN ('ACTIVE', 'INACTIVE')),
    CONSTRAINT ck_useraccounts_username_length CHECK (CHAR_LENGTH(Username) >= 3),
    CONSTRAINT ck_useraccounts_password_hash CHECK (CHAR_LENGTH(PasswordHash) >= 32)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 2. Students: hồ sơ sinh viên, 1-1 với UserAccounts
-- ---------------------------------------------------------------------
CREATE TABLE Students (
    StudentID      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    AccountID      BIGINT UNSIGNED NOT NULL,
    StudentCode    VARCHAR(20)     NOT NULL,
    FullName       VARCHAR(100)    NOT NULL,
    Gender         VARCHAR(10)     NOT NULL,
    DateOfBirth    DATE            NOT NULL,
    Email          VARCHAR(100)    NOT NULL,
    Phone          VARCHAR(15)     NULL,
    ClassName      VARCHAR(30)     NOT NULL,
    EnrollmentYear SMALLINT        NOT NULL,
    CreatedAt      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (StudentID),
    CONSTRAINT uq_students_account UNIQUE (AccountID),
    CONSTRAINT uq_students_code UNIQUE (StudentCode),
    CONSTRAINT uq_students_email UNIQUE (Email),
    CONSTRAINT fk_students_account FOREIGN KEY (AccountID)
        REFERENCES UserAccounts (AccountID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_students_gender CHECK (Gender IN ('Male', 'Female', 'Other')),
    CONSTRAINT ck_students_enrollment_year CHECK (EnrollmentYear BETWEEN 2000 AND 2100),
    CONSTRAINT ck_students_email CHECK (Email LIKE '%_@_%._%')
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 3. Lecturers: hồ sơ giảng viên, 1-1 với UserAccounts
-- ---------------------------------------------------------------------
CREATE TABLE Lecturers (
    LecturerID   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    AccountID    BIGINT UNSIGNED NOT NULL,
    LecturerCode VARCHAR(20)     NOT NULL,
    FullName     VARCHAR(100)    NOT NULL,
    Gender       VARCHAR(10)     NOT NULL,
    DateOfBirth  DATE            NOT NULL,
    Email        VARCHAR(100)    NOT NULL,
    Phone        VARCHAR(15)     NULL,
    Department   VARCHAR(100)    NOT NULL,
    Degree       VARCHAR(20)     NOT NULL,
    CreatedAt    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (LecturerID),
    CONSTRAINT uq_lecturers_account UNIQUE (AccountID),
    CONSTRAINT uq_lecturers_code UNIQUE (LecturerCode),
    CONSTRAINT uq_lecturers_email UNIQUE (Email),
    CONSTRAINT fk_lecturers_account FOREIGN KEY (AccountID)
        REFERENCES UserAccounts (AccountID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_lecturers_gender CHECK (Gender IN ('Male', 'Female', 'Other')),
    CONSTRAINT ck_lecturers_degree CHECK (Degree IN ('Bachelor', 'Master', 'Doctor')),
    CONSTRAINT ck_lecturers_email CHECK (Email LIKE '%_@_%._%')
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 4. Courses: môn học và giảng viên phụ trách
-- ---------------------------------------------------------------------
CREATE TABLE Courses (
    CourseID    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    CourseCode  VARCHAR(20)     NOT NULL,
    CourseName  VARCHAR(100)    NOT NULL,
    Credits     TINYINT UNSIGNED NOT NULL,
    LecturerID  BIGINT UNSIGNED NULL,
    Semester    VARCHAR(10)     NOT NULL,
    AcademicYear VARCHAR(9)     NOT NULL,
    CreatedAt   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (CourseID),
    CONSTRAINT uq_courses_code UNIQUE (CourseCode),
    CONSTRAINT fk_courses_lecturer FOREIGN KEY (LecturerID)
        REFERENCES Lecturers (LecturerID)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT ck_courses_credits CHECK (Credits BETWEEN 1 AND 10),
    CONSTRAINT ck_courses_semester CHECK (Semester IN ('HK1', 'HK2', 'HK3')),
    CONSTRAINT ck_courses_academic_year CHECK (AcademicYear LIKE '____-____')
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 5. Grades: điểm quá trình / cuối kỳ của sinh viên theo môn học
-- ---------------------------------------------------------------------
CREATE TABLE Grades (
    GradeID      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    StudentID    BIGINT UNSIGNED NOT NULL,
    CourseID     BIGINT UNSIGNED NOT NULL,
    ProcessScore DECIMAL(4, 2)  NULL,
    FinalScore   DECIMAL(4, 2)  NULL,
    Status       VARCHAR(10)    NOT NULL DEFAULT 'PENDING',
    CreatedAt    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (GradeID),
    CONSTRAINT uq_grades_student_course UNIQUE (StudentID, CourseID),
    CONSTRAINT fk_grades_student FOREIGN KEY (StudentID)
        REFERENCES Students (StudentID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_grades_course FOREIGN KEY (CourseID)
        REFERENCES Courses (CourseID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_grades_process_score CHECK (ProcessScore IS NULL OR ProcessScore BETWEEN 0 AND 10),
    CONSTRAINT ck_grades_final_score CHECK (FinalScore IS NULL OR FinalScore BETWEEN 0 AND 10),
    CONSTRAINT ck_grades_status CHECK (Status IN ('PENDING', 'PASSED', 'FAILED'))
) ENGINE = InnoDB;

-- =====================================================================
-- DỮ LIỆU MẪU
-- Mật khẩu mẫu (lưu dạng băm PBKDF2, không lưu mật khẩu gốc):
--   admin / Admin@123      (ADMIN)
--   gv001 / Lecturer@123   (LECTURER)
--   sv001 / Student@123    (STUDENT, Active)
--   sv002 / Student@123    (STUDENT, Inactive — dùng để kiểm thử chặn đăng nhập)
-- =====================================================================

INSERT INTO UserAccounts (AccountID, Username, PasswordHash, FullName, Role, Status) VALUES
(1, 'admin', 'pbkdf2_sha256$210000$4CsYy877ObhxClY4l/RAhw==$ul4dUCYLiZ/ZFD6uHwvaKVnjS8Q64J+AZquTpvOzSWM=', 'Quản trị viên hệ thống', 'ADMIN', 'ACTIVE'),
(2, 'gv001', 'pbkdf2_sha256$210000$2aRrmNaRteInsXdUVXv+Pw==$J6sJ7k9sc7BEjCiGwba+JigwK2/JHGpfiIQ+vOSFGnA=', 'Nguyễn Văn Minh', 'LECTURER', 'ACTIVE'),
(3, 'sv001', 'pbkdf2_sha256$210000$fmeEAjzoyFMN5n+3YOpZsw==$z7Rc6J8Tx9aYV0jLSWBZ1tNGCk1EQkKmxu0FCmYQL+I=', 'Trần Thị Lan', 'STUDENT', 'ACTIVE'),
(4, 'sv002', 'pbkdf2_sha256$210000$fmeEAjzoyFMN5n+3YOpZsw==$z7Rc6J8Tx9aYV0jLSWBZ1tNGCk1EQkKmxu0FCmYQL+I=', 'Lê Hoàng Nam', 'STUDENT', 'INACTIVE');

INSERT INTO Lecturers (LecturerID, AccountID, LecturerCode, FullName, Gender, DateOfBirth, Email, Phone, Department, Degree) VALUES
(1, 2, 'GV001', 'Nguyễn Văn Minh', 'Male', '1980-05-12', 'minh.nv@university.edu.vn', '0901234567', 'Khoa Công nghệ thông tin', 'Doctor');

INSERT INTO Students (StudentID, AccountID, StudentCode, FullName, Gender, DateOfBirth, Email, Phone, ClassName, EnrollmentYear) VALUES
(1, 3, 'SV001', 'Trần Thị Lan', 'Female', '2004-03-08', 'lan.tt@student.edu.vn', '0912345678', 'CNTT-K22', 2022),
(2, 4, 'SV002', 'Lê Hoàng Nam', 'Male', '2004-11-21', 'nam.lh@student.edu.vn', '0987654321', 'CNTT-K22', 2022);

INSERT INTO Courses (CourseID, CourseCode, CourseName, Credits, LecturerID, Semester, AcademicYear) VALUES
(1, 'INT2203', 'Cơ sở dữ liệu', 3, 1, 'HK1', '2025-2026'),
(2, 'INT2204', 'Lập trình hướng đối tượng', 3, 1, 'HK1', '2025-2026'),
(3, 'INT3306', 'Phát triển ứng dụng web', 4, 1, 'HK2', '2025-2026');

INSERT INTO Grades (GradeID, StudentID, CourseID, ProcessScore, FinalScore, Status) VALUES
(1, 1, 1, 8.50, 9.00, 'PASSED'),
(2, 1, 2, 7.50, 8.00, 'PASSED'),
(3, 2, 1, 4.00, 5.50, 'FAILED');
