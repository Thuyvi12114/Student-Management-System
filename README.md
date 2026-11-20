# Student Management System – Group 05 (Software Testing)

## 1. Test Suite Overview
- `tests/test_core_grades_vananh.py`: login, password change, grade authorization, and GPA calculation.
- `tests/test_modules_nghia.py`: profile, accounts, student CRUD, search, and rollback behavior.
- `tests/test_search_courses_son.py`: search, dashboard, lecturers, courses, and SQL injection checks.
- `tests/test_auth_session.py`: additional login, logout, and password change tests.
- `tests/test_validators.py`: unit tests for input and data validation functions.
- `tests/test_database_constraints.py`: `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, and `CHECK` constraints in MySQL.
- `tests/conftest.py`: automatic test fixture setup before each test with database safety guards.

## 2. Prerequisites
- Run from the project root directory after merging Stage 3 (containing `app/`, `database/`, and `main.py`).
- Python environment configured according to `requirements.txt` with MySQL 8 or MariaDB running.
- Install dependencies:
  python -m pip install -r requirements.txt
  python -m pip install pytest
- The MySQL command-line client (`mysql`) must be available in `PATH`.

## 3. Running Tests (PowerShell)
Set environment variables targeting the test database before running `pytest`:

$env:SMS_DB_HOST = "127.0.0.1"
$env:SMS_DB_PORT = "3306"
$env:SMS_DB_NAME = "student_management_test"
$env:SMS_DB_USER = "root"
$env:SMS_DB_PASSWORD = ""
python -m pytest tests -v

Run individual test files:

python -m pytest tests/test_core_grades_vananh.py -v
python -m pytest tests/test_database_constraints.py -v

> **Safety Warning:** The test fixture drops and recreates tables in the configured database before **every** test. Always use a dedicated test database ending with `_test` (default: `student_management_test`). Never set `SMS_DB_NAME=student_management` or point to any database containing production/real data.

## 4. Test Execution & Reporting
- `PASSED`: test executed and met expected assertions.
- `FAILED`: test executed and returned an unexpected result.
- `ERROR`: environment, connection, configuration, or setup/teardown error before test execution.
- `SKIPPED`: test skipped during execution.

Record actual test results directly on each test case in the Excel file based on real test runs; do not manually fill in hardcoded pass results.

## 5. UI, Integration, and Performance Testing
- Test cases covering the 18 screens, integration flows, and performance scenarios are maintained in the Excel file.
- Performance test dataset target on the test database: **1,000 students**, **100 lecturers**, **100 courses**, and **5,000 grade records**.
- Target response thresholds: search operations under **2 seconds** and standard operations under **3 seconds**. Never run performance data generation or tests against a production database.
