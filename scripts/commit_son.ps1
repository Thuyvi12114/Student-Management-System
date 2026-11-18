# Script commit của Sơn - chạy trong thư mục gốc của repo đã clone.
# Cách dùng:  powershell -ExecutionPolicy Bypass -File scripts\commit_son.ps1
# Chỉ git add các file THUỘC PHẦN CỦA BẠN; commit bằng tài khoản Git của chính bạn.
param([string]$Branch = 'feature/m4-m5-search-courses', [string]$Base = 'develop', [switch]$NoPush)
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

Save-Commit 'feat(search): tìm kiếm sinh viên cho Admin và tra cứu rút gọn cho giảng viên (UC-01, UC-02, UI 1.18)' @('app/dao/student_search_dao.py', 'app/service/student_search_service.py', 'app/ui/search/')
Save-Commit 'feat(dashboard): dashboard theo vai trò Admin/Giảng viên/Sinh viên (UI 1.2, 1.6, 1.7, 1.17)' @('app/ui/dashboard/')
Save-Commit 'feat(lecturers): quản lý giảng viên, chặn xóa khi còn học phần, tạo tài khoản cùng giao dịch (UC-12, UI 1.4)' @('app/dao/lecturer_dao.py', 'app/service/lecturer_service.py', 'app/ui/lecturers/')
Save-Commit 'feat(courses): quản lý học phần, giảng viên phụ trách phải Active, chặn xóa khi có điểm (UC-13, UC-14, UI 1.10, 1.15)' @('app/dao/course_dao.py', 'app/service/course_service.py', 'app/ui/courses/')
Save-Commit 'test(search-courses): kiểm thử tìm kiếm, phân quyền hiển thị, giảng viên, học phần' @('tests/test_search_courses_son.py')

if ($NoPush) { Write-Host 'Đã commit xong (không push).' ; exit 0 }
git push -u origin $Branch
if ($LASTEXITCODE -ne 0) { Write-Error 'git push lỗi (kiểm tra quyền truy cập repo/đăng nhập GitHub)'; exit 1 }
Write-Host "Xong. Mở GitHub -> Compare & pull request cho nhánh $Branch." -ForegroundColor Green
