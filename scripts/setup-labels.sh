#!/usr/bin/env bash
#
# Tạo toàn bộ hệ thống nhãn cho kho mã.
#
# Yêu cầu: GitHub CLI đã cài và đã đăng nhập (gh auth login)
# Cách dùng: chạy trong thư mục kho mã đã clone
#
#   bash scripts/setup-labels.sh
#
# Script an toàn khi chạy lại: nhãn đã tồn tại sẽ được cập nhật thay vì báo lỗi.

set -euo pipefail

create() {
  local name="$1" color="$2" desc="$3"
  if gh label create "$name" --color "$color" --description "$desc" 2>/dev/null; then
    echo "  tạo mới : $name"
  else
    gh label edit "$name" --color "$color" --description "$desc" >/dev/null
    echo "  cập nhật: $name"
  fi
}

echo "Nhóm type"
create "type/feat"     "0E8A16" "Tính năng mới"
create "type/fix"      "D73A4A" "Sửa lỗi"
create "type/docs"     "0075CA" "Tài liệu"
create "type/research" "7057FF" "Khảo sát, so sánh, dựng thử"
create "type/refactor" "FBCA04" "Sửa cấu trúc code, không đổi hành vi"
create "type/test"     "BFD4F2" "Kiểm thử"
create "type/chore"    "CFD3D7" "Cấu hình, hạ tầng, phụ trợ"

echo "Nhóm space"
create "space/H"    "1D76DB" "Không gian nhân sự và định danh"
create "space/P"    "5319E7" "Không gian quy trình"
create "space/D"    "006B75" "Không gian dữ liệu"
create "space/I"    "D93F0B" "Không gian trí tuệ nhân tạo"
create "space/core" "444444" "Hạ tầng chung, xuyên suốt các không gian"

echo "Nhóm priority"
create "priority/P0" "B60205" "Chặn cả nhóm, xử lý ngay"
create "priority/P1" "D93F0B" "Quan trọng, hoàn thành trong tuần"
create "priority/P2" "FBCA04" "Bình thường"
create "priority/P3" "C2E0C6" "Làm khi có thời gian"

echo "Nhóm status"
create "status/blocked"          "E4E669" "Đang chờ một việc khác hoàn thành"
create "status/needs-discussion" "D4C5F9" "Cần cả nhóm thảo luận và quyết định"
create "status/wontfix"          "EEEEEE" "Đã quyết định không thực hiện"

echo "Nhóm scoring"
create "scoring/pof"   "B60205" "Liên quan tiêu chí chấm điểm PoF"
create "scoring/final" "0052CC" "Liên quan tiêu chí chấm điểm vòng chung kết"

echo "Nhóm community"
create "good first issue" "7057FF" "Phù hợp cho người mới tham gia dự án"
create "help wanted"      "008672" "Cần thêm người hỗ trợ"

echo
echo "Xóa các nhãn mặc định không dùng (bỏ qua nếu không tồn tại)"
for l in "bug" "documentation" "enhancement" "duplicate" "invalid" "question" "wontfix"; do
  gh label delete "$l" --yes 2>/dev/null && echo "  đã xóa : $l" || true
done

echo
echo "Hoàn tất."