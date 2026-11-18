# Script commit của Nghĩa - chạy trong thư mục gốc của repo đã clone.
# Cách dùng:  powershell -ExecutionPolicy Bypass -File scripts\commit_nghia.ps1
# Chỉ git add các file THUỘC PHẦN CỦA BẠN; commit bằng tài khoản Git của chính bạn.
param([string]$Branch = 'feature/m2-m3-accounts-students', [string]$Base = 'develop', [switch]$NoPush)
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

Save-Commit 'feat(accounts): xem danh sách, khóa/mở khóa tài khoản, đặt lại mật khẩu (UC-07)' @('app/service/account_service.py', 'app/ui/accounts/')
Save-Commit 'feat(profile): xem hồ sơ cá nhân và sinh viên sửa email/SĐT/địa chỉ (UC-03, UC-08)' @('app/service/profile_service.py', 'app/ui/profile/')
Save-Commit 'feat(students): thêm/sửa/xóa sinh viên, kiểm tra trùng mã, giao dịch hồ sơ+tài khoản, chặn xóa khi có điểm (UC-09, 10, 11, 18, 19)' @('app/dao/student_dao.py', 'app/service/student_service.py', 'app/ui/students/')
Save-Commit 'test(accounts-students): kiểm thử tài khoản, hồ sơ, CRUD sinh viên' @('tests/test_modules_nghia.py')

if ($NoPush) { Write-Host 'Đã commit xong (không push).' ; exit 0 }
git push -u origin $Branch
if ($LASTEXITCODE -ne 0) { Write-Error 'git push lỗi (kiểm tra quyền truy cập repo/đăng nhập GitHub)'; exit 1 }
Write-Host "Xong. Mở GitHub -> Compare & pull request cho nhánh $Branch." -ForegroundColor Green
