# UniCore — Student Management System (Group 05)

A **Python + Tkinter** desktop application backed by **MySQL 8**, rebuilt from the
`RequirementAndDesignDocument_Group05` specification (5 tables, 19 use cases, 3 roles).

Three-layer architecture: `Config → Database → DAO → Service → UI (Tkinter)`.

```
app/
  config.py  db.py  context.py      # configuration, connection, service wiring
  models.py                         # entities (UserAccounts, Students, Lecturers, Courses, Grades)
  dao/                              # parameterized SQL (%s), transactions in BaseDAO
  service/                          # business rules + authorization + validation
  security/                         # PBKDF2 password hashing, login session, RBAC
  ui/                               # Tkinter screens (accounts, profile, students, search, dashboard, lecturers, courses, grades)
database/student_management.sql     # schema + seed data
tests/                              # pytest (requires a running MySQL server)
docs/GIT_WORKFLOW.md                # branch/commit guide for the team
scripts/                            # per-member commit scripts + OWNERSHIP.txt (who owns which files)
```

## 1. Install

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

> If PowerShell blocks scripts: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
> If `pip.exe` is blocked: always use `python -m pip`.

## 2. Start MySQL

**Docker (recommended)**

```powershell
docker compose up -d          # first run imports database/student_management.sql automatically
docker compose ps             # wait for "healthy"
```

If port 3306 is already taken (XAMPP or a local MySQL install), change `"3306:3306"` in
`docker-compose.yml` to `"3307:3306"` and set `port = 3307` in `config.ini`.

To reset all data: `docker compose down -v` then `docker compose up -d`.

**XAMPP / local MySQL**: start MySQL, then load the SQL file once

```powershell
mysql -u root -p < database/student_management.sql
```

## 3. Connection settings

Copy `config.example.ini` to `config.ini` (already covered by `.gitignore`, so passwords are never committed):

```ini
[database]
host = 127.0.0.1
port = 3306
name = student_management
user = root
password =
```

Alternatively use the environment variables `SMS_DB_HOST`, `SMS_DB_PORT`, `SMS_DB_NAME`,
`SMS_DB_USER`, `SMS_DB_PASSWORD` (environment variables take precedence over `config.ini`).

## 4. Run the application

```powershell
python main.py
```

### Sample accounts

| Username | Role | Password |
|---|---|---|
| `admin` | Administrator | `Admin@123` |
| `GV001`, `GV002`, `GV003` | Lecturer | `Gv001@123`, `Gv002@123`, `Gv003@123` |
| `SV001` … `SV010` | Student | `Sv001@123` … `Sv010@123` |

Usernames are case-insensitive. `SV005` is an **Inactive** account, useful for testing the login block.
For students and lecturers the **username always equals the student/lecturer ID** (as required by the design document).

## 5. Run the tests

```powershell
python -m pip install pytest
python -m pytest -q           # uses a separate student_management_test database, reloads the SQL before each test
```

The tests need the `mysql` client on `PATH` so they can load `database/student_management.sql`.
To use a different test database: `set SMS_DB_NAME=other_name` before running.

## 6. Key business rules (from the design document)

- Student/lecturer/course IDs are textual primary keys (`VARCHAR(20)`); a student ID **cannot be changed** once created.
- Creating or deleting a student/lecturer writes the profile and the account in **one transaction** (any failure rolls back both).
- A student with grades cannot be deleted, nor a course with grades, nor a lecturer who still teaches a course
  (`RESTRICT` foreign keys plus a service-level check).
- Students may edit **email, phone and address** only; lecturer profiles are read-only.
- Administrators may only **view** grades; lecturers may only enter grades for courses they teach; each (student, course) pair has one grade in the 0–10 range.
- Grade point average = Σ(grade × credits) / Σ credits.
- Passwords: at least 8 characters with upper case, lower case and a digit, no spaces; stored as a PBKDF2-HMAC-SHA256 hash.
