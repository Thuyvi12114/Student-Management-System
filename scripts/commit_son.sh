#!/usr/bin/env bash
# Script commit của Sơn (macOS/Linux/Git Bash). Chạy từ thư mục gốc repo: bash scripts/commit_son.sh
set -euo pipefail
BRANCH="${1:-feature/m4-m5-search-courses}"
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

save_commit 'feat(search): tìm kiếm sinh viên cho Admin và tra cứu rút gọn cho giảng viên (UC-01, UC-02, UI 1.18)' 'app/dao/student_search_dao.py' 'app/service/student_search_service.py' 'app/ui/search/'
save_commit 'feat(dashboard): dashboard theo vai trò Admin/Giảng viên/Sinh viên (UI 1.2, 1.6, 1.7, 1.17)' 'app/ui/dashboard/'
save_commit 'feat(lecturers): quản lý giảng viên, chặn xóa khi còn học phần, tạo tài khoản cùng giao dịch (UC-12, UI 1.4)' 'app/dao/lecturer_dao.py' 'app/service/lecturer_service.py' 'app/ui/lecturers/'
save_commit 'feat(courses): quản lý học phần, giảng viên phụ trách phải Active, chặn xóa khi có điểm (UC-13, UC-14, UI 1.10, 1.15)' 'app/dao/course_dao.py' 'app/service/course_service.py' 'app/ui/courses/'
save_commit 'test(search-courses): kiểm thử tìm kiếm, phân quyền hiển thị, giảng viên, học phần' 'tests/test_search_courses_son.py'

if [ "$NOPUSH" = "1" ]; then echo 'Đã commit xong (không push).'; exit 0; fi
git push -u origin "$BRANCH"
echo "Xong. Mở GitHub -> Compare & pull request cho nhánh $BRANCH."
