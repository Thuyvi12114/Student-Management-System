#!/usr/bin/env bash
# Script commit của Nghĩa (macOS/Linux/Git Bash). Chạy từ thư mục gốc repo: bash scripts/commit_nghia.sh
set -euo pipefail
BRANCH="${1:-feature/m2-m3-accounts-students}"
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

save_commit 'feat(accounts): xem danh sách, khóa/mở khóa tài khoản, đặt lại mật khẩu (UC-07)' 'app/service/account_service.py' 'app/ui/accounts/'
save_commit 'feat(profile): xem hồ sơ cá nhân và sinh viên sửa email/SĐT/địa chỉ (UC-03, UC-08)' 'app/service/profile_service.py' 'app/ui/profile/'
save_commit 'feat(students): thêm/sửa/xóa sinh viên, kiểm tra trùng mã, giao dịch hồ sơ+tài khoản, chặn xóa khi có điểm (UC-09, 10, 11, 18, 19)' 'app/dao/student_dao.py' 'app/service/student_service.py' 'app/ui/students/'
save_commit 'test(accounts-students): kiểm thử tài khoản, hồ sơ, CRUD sinh viên' 'tests/test_modules_nghia.py'

if [ "$NOPUSH" = "1" ]; then echo 'Đã commit xong (không push).'; exit 0; fi
git push -u origin "$BRANCH"
echo "Xong. Mở GitHub -> Compare & pull request cho nhánh $BRANCH."
