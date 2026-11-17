# Script commit của Vân Anh - chạy trong thư mục gốc của repo đã clone.
# Cách dùng:  powershell -ExecutionPolicy Bypass -File scripts\commit_vananh.ps1
# Chỉ git add các file THUỘC PHẦN CỦA BẠN; commit bằng tài khoản Git của chính bạn.
param([string]$Branch = 'feature/m1-m6-core-auth-grades', [string]$Base = 'develop', [switch]$NoPush)
$ErrorActionPreference = 'Continue'
$name  = git config user.name
$email = git config user.email
if (-not $name -or -not $email) { Write-Error 'Chưa cấu hình git config user.name / user.email bằng tài khoản của bạn.'; exit 1 }
Write-Host "Commit với danh tính: $name <$email>" -ForegroundColor Cyan
$current = git rev-parse --abbrev-ref HEAD
if ($current -ne $Branch) {
  git rev-parse --verify --quiet $Branch *> $null
  if ($LASTEXITCODE -eq 0) { git checkout $Branch } else { git fetch origin; git checkout -b $Branch "origin/$Base" }
  if ($LASTEXITCODE -ne 0) { exit 1 }
}
$utf8 = New-Object System.Text.UTF8Encoding $false
function Save-Commit([string]$msg, [string[]]$paths) {
  git add -- $paths
  if ($LASTEXITCODE -ne 0) { Write-Error 'git add lỗi'; exit 1 }
  git diff --cached --quiet
  if ($LASTEXITCODE -eq 0) { Write-Host "(bỏ qua, không có thay đổi) $msg" -ForegroundColor DarkGray; return }
  $tmp = New-TemporaryFile
  [System.IO.File]::WriteAllText($tmp.FullName, $msg + "`n", $utf8)
  git commit -F $tmp.FullName
  $code = $LASTEXITCODE
  Remove-Item $tmp.FullName
  if ($code -ne 0) { Write-Error 'git commit lỗi'; exit 1 }
}

Save-Commit 'chore(repo): khởi tạo cấu hình repo, requirements, docker-compose, config mẫu' @('.gitignore', '.dockerignore', 'requirements.txt', 'docker-compose.yml', 'config.example.ini')
Save-Commit 'feat(db): schema 5 bảng theo tài liệu thiết kế, ràng buộc RESTRICT và dữ liệu mẫu' @('database/student_management.sql')
Save-Commit 'feat(core): cấu hình, kết nối MySQL, models, BaseDAO và AppContext (nền tảng chung)' @('app/__init__.py', 'app/config.py', 'app/db.py', 'app/models.py', 'app/context.py', 'app/dao/__init__.py', 'app/dao/base.py', 'app/dao/errors.py', 'app/service/__init__.py', 'app/service/exceptions.py', 'app/service/access.py', 'app/service/validators.py')
Save-Commit 'feat(auth): đăng nhập, phiên làm việc, băm mật khẩu PBKDF2, chính sách mật khẩu, RBAC (UC-04, UC-05, UC-06)' @('app/dao/user_account_dao.py', 'app/service/auth_service.py', 'app/security/')
Save-Commit 'feat(ui): đăng nhập, đổi mật khẩu, khung MainView, widget dùng chung (UI 1.1)' @('main.py', 'app/ui/__init__.py', 'app/ui/theme.py', 'app/ui/login_view.py', 'app/ui/change_password_dialog.py', 'app/ui/main_view.py', 'app/ui/management/')
Save-Commit 'feat(grades): nhập/sửa điểm, bảng điểm sinh viên, tra cứu điểm của Admin, GPA có trọng số tín chỉ (UC-15, UC-16, UC-17)' @('app/dao/grade_dao.py', 'app/service/grade_service.py', 'app/ui/grades/')
Save-Commit 'test(core-grades): kiểm thử đăng nhập, đổi mật khẩu, điểm và phân quyền điểm' @('tests/__init__.py', 'tests/conftest.py', 'tests/test_core_grades_vananh.py')
Save-Commit 'docs: README hướng dẫn cài đặt, chạy, Docker và quy trình Git' @('README.md', 'docs/GIT_WORKFLOW.md', 'scripts/')

if ($NoPush) { Write-Host 'Đã commit xong (không push).' ; exit 0 }
git push -u origin $Branch
if ($LASTEXITCODE -ne 0) { Write-Error 'git push lỗi (kiểm tra quyền truy cập repo/đăng nhập GitHub)'; exit 1 }
Write-Host "Xong. Mở GitHub -> Compare & pull request cho nhánh $Branch." -ForegroundColor Green
