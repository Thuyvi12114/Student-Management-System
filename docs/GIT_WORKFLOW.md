# Quy trình Git cho nhóm 05

Repo: `Thuyvi12114/Student-Management-System` (private). Mỗi thành viên **commit bằng tài khoản GitHub của chính mình**
để cô xem được minh chứng đóng góp. Không commit hộ người khác, không đổi `user.name/user.email` của người khác.

## 1. Thiết lập một lần

```powershell
git config --global user.name  "Họ Tên của bạn"
git config --global user.email "email-gắn-với-GitHub-của-bạn"
git clone https://github.com/Thuyvi12114/Student-Management-System.git
cd Student-Management-System
git fetch --all
git branch -a          # thấy origin/develop và các nhánh feature/m*
```

## 2. Phân chia file theo người (khớp file phân công lập trình)

Danh sách đầy đủ từng file: `scripts/OWNERSHIP.txt` (mỗi file thuộc đúng một người).

| Người | Module | File chính |
|---|---|---|
| **Vân Anh** | M1 Core/DB/Auth (FR-02; UC-04/05/06; UI 1.1) | `database/`, `app/{config,db,models,context}.py`, `app/dao/{base,errors,user_account_dao}.py`, `app/service/{auth_service,access,validators,exceptions}.py`, `app/security/`, `main.py`, `app/ui/{theme,login_view,change_password_dialog,main_view}.py`, `app/ui/management/` |
| **Vân Anh** | M6 Điểm (FR-06; UC-15/16/17; UI 1.5, 1.11, 1.13, 1.16) | `app/dao/grade_dao.py`, `app/service/grade_service.py`, `app/ui/grades/`, `tests/test_core_grades_vananh.py` |
| **Nghĩa** | M2 Tài khoản & hồ sơ (FR-01/02; UC-03/07/08; UI 1.3, 1.12, 1.14) | `app/service/{account,profile}_service.py`, `app/ui/accounts/`, `app/ui/profile/` |
| **Nghĩa** | M3 CRUD sinh viên (FR-03; UC-09/10/11/18/19; UI 1.8, 1.9) | `app/dao/student_dao.py`, `app/service/student_service.py`, `app/ui/students/`, `tests/test_modules_nghia.py` |
| **Sơn** | M4 Tìm kiếm & Dashboard (FR-01; UC-01/02; UI 1.2, 1.6, 1.7, 1.17, 1.18) | `app/dao/student_search_dao.py`, `app/service/student_search_service.py`, `app/ui/search/`, `app/ui/dashboard/` |
| **Sơn** | M5 Giảng viên & Học phần (FR-04/05; UC-12/13/14; UI 1.4, 1.10, 1.15) | `app/dao/{lecturer,course}_dao.py`, `app/service/{lecturer,course}_service.py`, `app/ui/{lecturers,courses}/`, `tests/test_search_courses_son.py` |

**Nền tảng dùng chung** (schema, `models.py`, `base.py`, `context.py`, `rbac.py`) thuộc Vân Anh. Thay đổi các file này
phải thống nhất với Vân Anh trước, vì mọi module khác phụ thuộc vào chúng.

## 2b. Quy trình commit (nhánh nền `develop`)

Lịch sử cũ của repo đã được lưu lại bằng tag `backup/*` rồi dọn sạch; repo bắt đầu lại từ một commit rỗng trên nhánh
`develop` (nhánh mặc định). Mỗi người làm **song song** trên nhánh riêng, chỉ commit **file của mình**
(danh sách ở `scripts/OWNERSHIP.txt`), nên merge không xung đột.

| Người | Nhánh | Script |
|---|---|---|
| Vân Anh | `feature/m1-m6-core-auth-grades` | `scripts/commit_vananh.ps1` |
| Nghĩa | `feature/m2-m3-accounts-students` | `scripts/commit_nghia.ps1` |
| Sơn | `feature/m4-m5-search-courses` | `scripts/commit_son.ps1` |

Mỗi người làm đúng thứ tự, trong **một bản clone mới**:

```powershell
git clone https://github.com/Thuyvi12114/Student-Management-System.git SMS-final
cd SMS-final
git config user.name  "Họ Tên"            # dùng tài khoản của chính mình
git config user.email "email-GitHub"
git checkout -b <tên-nhánh-của-mình> origin/develop     # TRƯỚC khi chép file
# chép toàn bộ nội dung zip đè vào thư mục SMS-final (không có .git)
powershell -ExecutionPolicy Bypass -File scripts\commit_<tên>.ps1
```

Sau đó mở Pull Request với **base = `develop`**. Vân Anh review và merge 3 PR. Xong cả 3: `git pull`, chạy
`python -m pytest -q` (73 test xanh) và `python main.py`.

Mỗi script: kiểm tra đã cấu hình `git config user.name/user.email`, chuyển/tạo nhánh, `git add` **chỉ file của người đó**
theo từng commit nhỏ có nghĩa, rồi `git push -u origin <nhánh>`. Thêm `-NoPush` (PowerShell) hoặc `NOPUSH=1` (bash) để chỉ commit.

## 3. Nhánh

```
develop                              nhánh nền, mặc định trên GitHub
feature/m1-m6-core-auth-grades       Vân Anh (M1 + M6)
feature/m2-m3-accounts-students      Nghĩa  (M2 + M3)
feature/m4-m5-search-courses         Sơn    (M4 + M5)
```

Lịch sử cũ nằm ở các tag `backup/*` (xem bằng `git tag -l "backup/*"`), không còn nằm trên nhánh nào.

## 4. Commit nhỏ, đúng phạm vi, có nghĩa

Các script đã chia sẵn commit theo `loại(phạm-vi): mô tả` (ví dụ `feat(accounts): khóa/mở khóa tài khoản (UC-07)`).
Muốn tự commit tay, chỉ `git add` file **của mình** (xem `scripts/OWNERSHIP.txt`), kiểm tra bằng `git status`
và `git diff --staged` trước khi commit. Không `git add .` hay `git add -A`.

## 5. Pull Request

```powershell
git push
# GitHub → Compare & pull request → base: nhánh nền chung → ghi rõ UC/FR đã làm, cách chạy pytest
```

Trước khi mở PR: `python -m pytest -q` phải xanh và `python main.py` đăng nhập được 3 vai trò.

## 6. Khi bị xung đột (conflict)

```powershell
git fetch origin
git rebase origin/develop    # hoặc git merge
# sửa file xung đột -> git add <file> -> git rebase --continue
```

Xung đột ở file nền tảng (schema, `models.py`) → hỏi Vân Anh, không tự ý chọn bản của mình.
