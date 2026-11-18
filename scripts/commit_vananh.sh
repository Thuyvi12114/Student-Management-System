#!/usr/bin/env bash
# Script commit của Vân Anh (macOS/Linux/Git Bash). Chạy từ thư mục gốc repo: bash scripts/commit_vananh.sh
set -euo pipefail
BRANCH="${1:-feature/m1-m6-core-auth-grades}"
BASE="${BASE:-develop}"
NOPUSH="${NOPUSH:-0}"
name=$(git config user.name || true); email=$(git config user.email || true)
[ -n "$name" ] && [ -n "$email" ] || { echo 'Chưa cấu hình git user.name / user.email'; exit 1; }
echo "Commit với danh tính: $name <$email>"
current=$(git rev-parse --abbrev-ref HEAD)
if [ "$current" != "$BRANCH" ]; then
  if git rev-parse --verify --quiet "$BRANCH" >/dev/null; then git checkout "$BRANCH"; else git fetch origin; git checkout -b "$BRANCH" "origin/$BASE"; fi
fi
save_commit() { local msg="$1"; shift; git add -- "$@"; if git diff --cached --quiet; then echo "(bỏ qua) $msg"; else git commit -q -m "$msg"; echo "✔ $msg"; fi; }

save_commit 'chore(repo): khởi tạo cấu hình repo, requirements, docker-compose, config mẫu' '.gitignore' '.dockerignore' 'requirements.txt' 'docker-compose.yml' 'config.example.ini'
save_commit 'feat(db): schema 5 bảng theo tài liệu thiết kế, ràng buộc RESTRICT và dữ liệu mẫu' 'database/student_management.sql'
save_commit 'feat(core): cấu hình, kết nối MySQL, models, BaseDAO và AppContext (nền tảng chung)' 'app/__init__.py' 'app/config.py' 'app/db.py' 'app/models.py' 'app/context.py' 'app/dao/__init__.py' 'app/dao/base.py' 'app/dao/errors.py' 'app/service/__init__.py' 'app/service/exceptions.py' 'app/service/access.py' 'app/service/validators.py'
save_commit 'feat(auth): đăng nhập, phiên làm việc, băm mật khẩu PBKDF2, chính sách mật khẩu, RBAC (UC-04, UC-05, UC-06)' 'app/dao/user_account_dao.py' 'app/service/auth_service.py' 'app/security/'
save_commit 'feat(ui): đăng nhập, đổi mật khẩu, khung MainView, widget dùng chung (UI 1.1)' 'main.py' 'app/ui/__init__.py' 'app/ui/theme.py' 'app/ui/login_view.py' 'app/ui/change_password_dialog.py' 'app/ui/main_view.py' 'app/ui/management/'
save_commit 'feat(grades): nhập/sửa điểm, bảng điểm sinh viên, tra cứu điểm của Admin, GPA có trọng số tín chỉ (UC-15, UC-16, UC-17)' 'app/dao/grade_dao.py' 'app/service/grade_service.py' 'app/ui/grades/'
save_commit 'test(core-grades): kiểm thử đăng nhập, đổi mật khẩu, điểm và phân quyền điểm' 'tests/__init__.py' 'tests/conftest.py' 'tests/test_core_grades_vananh.py'
save_commit 'docs: README hướng dẫn cài đặt, chạy, Docker và quy trình Git' 'README.md' 'docs/GIT_WORKFLOW.md' 'scripts/'

if [ "$NOPUSH" = "1" ]; then echo 'Đã commit xong (không push).'; exit 0; fi
git push -u origin "$BRANCH"
echo "Xong. Mở GitHub -> Compare & pull request cho nhánh $BRANCH."
