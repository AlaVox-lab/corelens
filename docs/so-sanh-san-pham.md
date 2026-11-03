# So sánh với các sản phẩm cùng loại

Tài liệu đặt DX-OS Lab cạnh các sản phẩm đang dùng để tiếp nhận và xử lý yêu cầu nội bộ, trong
nước và quốc tế, để chỉ ra dự án khác ở đâu và còn kém ở đâu (#277, góp ý buổi báo cáo 29/10/2026).

**Cách làm.** Thông tin lấy từ trang chính thức và tài liệu hướng dẫn của từng sản phẩm, mở ngày
01/11/2026; giấy phép của sản phẩm nguồn mở đọc từ tệp `LICENSE` trong kho mã của họ. Ô ghi
"không thấy" nghĩa là tài liệu đã đọc không nhắc tới — không có nghĩa là sản phẩm chắc chắn không
có; ô ghi "chưa kiểm" là chưa tìm được trang nguồn để xác nhận. Đường dẫn nguồn ở cuối tài liệu.

---

## 1. Ba nhóm sản phẩm

| Nhóm | Sản phẩm | Mô hình xử lý |
|---|---|---|
| **Bàn dịch vụ thương mại** (quốc tế) | Jira Service Management (Atlassian), ServiceNow | Phiếu yêu cầu đi qua nhóm hỗ trợ, đo hạn theo cam kết dịch vụ |
| **Bàn dịch vụ nguồn mở** (quốc tế) | Zammad, GLPI, osTicket | Như trên, tự cài được trên máy chủ riêng |
| **Phần mềm phê duyệt văn phòng** (Việt Nam) | Base Request (Base.vn), 1Office, MISA AMIS Quy trình | Đề xuất đi qua chuỗi người duyệt dựng sẵn cho từng loại đề xuất: tuần tự, song song, hay rẽ nhánh theo điều kiện |

DX-OS Lab đứng giữa hai mô hình: hồ sơ không đi theo một chuỗi người duyệt cố định, mà **điều
phối viên chọn phòng ban phù hợp cho từng hồ sơ** (gợi ý theo loại, chọn khác được); phòng sai
chuyên môn thì từ chối kèm lý do và hồ sơ được chuyển lại. Trong phòng, trưởng phòng xác duyệt
rồi giao người xử lý.

## 2. Bảng so sánh

| Tiêu chí | Jira Service Management | ServiceNow | Zammad | GLPI | osTicket | Base Request | 1Office | MISA AMIS Quy trình | **DX-OS Lab** |
|---|---|---|---|---|---|---|---|---|---|
| Giấy phép | Thương mại | Thương mại | AGPL-3.0 | GPL-3.0 | GPL-2.0 | Thương mại | Thương mại | Thương mại | **MIT** |
| Tự cài trên máy chủ riêng | Có bản tự quản (Server, Data Center) | Không thấy | Có | Có | Có | Không thấy | Không thấy | Không thấy | **Có**, một lệnh Docker Compose |
| Hạn xử lý theo lịch làm việc | Có (lịch SLA) | Có | Có (lịch, ngày lễ) | Có (lịch gắn SLA) | Không thấy | Có hạn cho từng người duyệt | Không thấy | Có cảnh báo chậm tiến độ | **Có**: lịch, ngày lễ Việt Nam, hệ số theo mức ưu tiên |
| Tự leo thang khi quá hạn | Chưa kiểm | Báo người được giao và quản lý ở 75% hạn và khi quá hạn | Qua trigger | Có mức leo thang | Không thấy | Không thấy | Không thấy | Không thấy | **Có**, cạnh hệ thống trong quy trình |
| Định tuyến | Chưa kiểm | Chưa kiểm | Chưa kiểm | Chưa kiểm | Chưa kiểm | Chuỗi người duyệt của nhóm đề xuất | Chuỗi duyệt của từng đối tượng | Chuỗi duyệt, rẽ nhánh theo điều kiện | **Điều phối viên chọn phòng cho từng hồ sơ**, phòng được từ chối |
| Quy trình nằm ở đâu | Chưa kiểm | Chưa kiểm | Chưa kiểm | Chưa kiểm | Chưa kiểm | Giao diện cấu hình nhóm đề xuất | Giao diện nút (node) | Trình thiết kế quy trình, hơn 500 mẫu | **Bảng dữ liệu** (trạng thái, cạnh, vai trò, ràng buộc), đọc được và kiểm thử được |
| Nhật ký phục vụ khai phá quy trình | Không thấy | Có sản phẩm Process Mining riêng | Không thấy | Không thấy | Không thấy | Không thấy | Không thấy | Có lịch sử hoạt động | **Có**: nhật ký chỉ ghi thêm theo dạng `case_id, activity, timestamp`; khai phá ở Giai đoạn 4 |
| Tiếng Việt | Chưa kiểm | Chưa kiểm | Chưa kiểm | Chưa kiểm | Chưa kiểm | Gốc tiếng Việt | Gốc tiếng Việt | Gốc tiếng Việt | **Gốc tiếng Việt** |

## 3. Điểm khác của DX-OS Lab

1. **Điều phối theo từng hồ sơ, không theo chuỗi duyệt cố định.** Phần mềm phê duyệt trong nước
   giỏi ở việc "đề xuất này đi qua những ai" — chuỗi người duyệt dựng trước cho mỗi loại. Yêu cầu
   nội bộ thì nhiều khi người gửi không biết thuộc phòng nào: điều phối viên đọc, phân loại, đặt
   ưu tiên, chọn phòng; phòng sai thì trả lại kèm lý do. Đây là chỗ bị hiểu nhầm ở buổi báo cáo
   — DX-OS Lab không phải luồng cố định qua các phòng như cổng dịch vụ công.
2. **Quy trình là dữ liệu đọc được.** Trạng thái, cạnh, vai trò, ràng buộc và mọi con số nằm trong
   bảng, có tệp kiểm tính nhất quán chặn khởi động khi khai sai, có bộ kiểm thử chạy trên cơ sở
   dữ liệu thật. Đổi quy trình là sửa dữ liệu khởi tạo, xem lại được trong lịch sử mã nguồn —
   không phải bấm lại trên giao diện của một hệ thống đóng.
3. **Nhật ký sinh ra để khai phá quy trình.** Mọi lần chuyển trạng thái ghi một dòng, chỉ ghi thêm,
   trong cùng giao dịch với việc đổi hồ sơ, phân biệt người bấm với hệ thống tự đi, đánh dấu cạnh
   làm lại. Trong các sản phẩm đã xem, chỉ ServiceNow có khai phá quy trình, và là sản phẩm
   thương mại bán riêng.
4. **Giấy phép MIT, tự cài bằng một lệnh.** Không phụ thuộc nhà cung cấp; doanh nghiệp giữ dữ liệu
   trên máy chủ của mình. Các thành phần lắp ghép (Keycloak, SeaweedFS, Superset) đều Apache-2.0.
5. **Thiết kế cho Việt Nam từ đầu.** Lịch làm việc và ngày lễ theo Bộ luật Lao động 2019, từ ngữ
   giao diện thống nhất bằng tiếng Việt.

## 4. Chỗ DX-OS Lab còn kém

Nói thẳng để người đọc cân nhắc đúng:

- **Độ trưởng thành.** Các sản phẩm trên có nhiều năm vận hành và nhiều khách hàng; DX-OS Lab là
  dự án dự thi, chưa triển khai thật ở doanh nghiệp nào.
- **Chưa có màn quản trị cấu hình** — sửa quy trình hiện là sửa dữ liệu khởi tạo (#255).
- **Chưa gửi thông báo thư điện tử** (#251), chưa có ứng dụng di động.
- **Chưa có khai phá quy trình** — tầng Dữ liệu đã có bảng điều khiển (v0.9.0), tầng Trí tuệ (v0.10.0) chưa làm.
- **Ít tích hợp.** Không có kho tích hợp sẵn với công cụ khác như các sản phẩm thương mại.
- **Một bộ quy tắc mẫu.** Phần mềm phê duyệt trong nước có hàng trăm mẫu quy trình; DX-OS Lab có
  một bộ quy tắc mẫu cho bốn loại yêu cầu.

## 5. Nguồn

Mở ngày 01/11/2026.

- Jira Service Management — tự đóng yêu cầu đã giải quyết: https://support.atlassian.com/jira-service-management-cloud/docs/auto-close-resolved-service-requests/
- Jira Service Management Data Center — lịch SLA: https://confluence.atlassian.com/display/SERVICEMANAGEMENTSERVER0416/Create+and+edit+SLA+calendars
- ServiceNow — thông báo SLA: https://www.servicenow.com/docs/r/QykF2iRSIs6VXztArCSo3w/51ukburjOhboUBChIEhkYQ
- ServiceNow — Process Mining: https://www.servicenow.com/docs/r/now-intelligence/process-mining/key-features.html
- Zammad — giấy phép (dòng đầu: GNU AFFERO GENERAL PUBLIC LICENSE, Version 3): https://github.com/zammad/zammad/blob/develop/LICENSE
- Zammad — SLA và lịch làm việc: https://admin-docs.zammad.org/en/latest/manage/slas.html
- GLPI — giấy phép (dòng đầu: GNU GENERAL PUBLIC LICENSE, Version 3): https://github.com/glpi-project/glpi/blob/main/LICENSE
- GLPI — mức dịch vụ, lịch, leo thang: https://help.glpi-project.org/tutorials/helpdesk/service_levels
- osTicket — giấy phép (dòng đầu: GNU GENERAL PUBLIC LICENSE, Version 2): https://github.com/osTicket/osTicket/blob/develop/LICENSE.txt
- Base Request — kiểu luồng phê duyệt (song song, tuần tự, một người duyệt): https://help.base.vn/support/solutions/articles/63000284885-base-request-change-the-approval-flow-in-the-request-group
- Base Request — giới thiệu: https://help.base.vn/support/solutions/articles/63000284976-base-request-introduce-base-request-and-table-of-contents
- 1Office — quy trình phê duyệt phiên bản mới: https://1office.vn/?p=61060
- MISA AMIS Quy trình — giới thiệu phần mềm phê duyệt: https://amis.misa.vn/157571/phan-mem-phe-duyet-online/
