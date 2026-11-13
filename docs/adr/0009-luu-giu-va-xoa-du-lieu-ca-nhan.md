# ADR-0009: Lưu giữ và xử lý yêu cầu xóa dữ liệu cá nhân

| Mục | Giá trị |
|---|---|
| Trạng thái | **Đã chấp nhận** |
| Ngày | 2026-11-13 |
| Không gian kiến trúc | `core` — quy ước dữ liệu dùng chung; chạm `D` (nhật ký sự kiện) và `I` (khai phá, hồ sơ tương tự) |
| Issue liên quan | #246 (thuộc nhóm #240) |
| Người quyết định | **Giảng viên hướng dẫn** chốt ngày 13/11/2026 cả ba ý: viết trong phạm vi thi, xử lý yêu cầu xóa bằng ẩn danh hóa nhãn tên, thời hạn lưu giữ cấu hình được; navigator (`AlaVox-lab`) đề xuất và ghi bản ghi |

---

## Bối cảnh

Hệ thống giữ lịch sử hồ sơ để làm hai việc: kiểm toán (ai làm gì, lúc nào) và khai phá quy trình — thành
phần chịu lực của không gian `I` (`docs/ARCHITECTURE.md` mục 6.4). Ba quyết định trước đó khiến hệ thống
hiện **không có đường nào** xóa hay ẩn dữ liệu cá nhân khi có yêu cầu hợp lệ:

- Nhật ký sự kiện, lời nhắn và nhật ký sửa cấu hình **chỉ ghi thêm**, chặn bằng trigger ở cơ sở dữ liệu
  (mục 6.1, #255)
- Tên người được **chụp thành nhãn** tại thời điểm thao tác (`*_label`), không tra ngược lúc đọc — để lịch
  sử kể đúng sự thật của lúc đó khi người đổi tên hay nghỉ việc (`app/workflow/context.py`)
- Tệp đính kèm **giữ vĩnh viễn** (ADR-0002, #80)

Yêu cầu pháp lý tham chiếu ở issue gốc là Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân, cùng các văn
bản thay thế hay bổ sung về sau. Bản ghi này là quyết định kỹ thuật của nhóm, không phải tư vấn pháp lý,
và không trích điều khoản cụ thể; doanh nghiệp triển khai tự đối chiếu với quy định đang hiệu lực.

---

## Dữ liệu cá nhân nằm ở đâu

Kiểm kê trên lược đồ tại bản sửa `0025` (truy vấn `information_schema.columns`, ngày 13/11/2026).

| Nơi | Dữ liệu | Ghi chú |
|---|---|---|
| Keycloak (database riêng) | Họ tên, tên đăng nhập, thư điện tử, số điện thoại, phòng ban, vai trò | **Nguồn gốc** của danh tính. Thư và số điện thoại không chép sang cơ sở dữ liệu ứng dụng — tra danh bạ lúc mở trang (#131) hay lúc gửi thư (#251) |
| `requests` | `requester_id`, `requester_label`, `assignee_id`, `assignee_label`, `suggested_assignee_id`; nội dung tự do `title`, `description`, `details` | Mã định danh là `sub` của Keycloak (UUID) — bí danh, không phải tên |
| `event_log` | `actor`, `actor_label`; `note`, `changes` | Chỉ ghi thêm. Khai phá quy trình đọc `actor` |
| `case_messages` | `author`, `author_label`, `body` | Chỉ ghi thêm |
| `case_attachments` + kho SeaweedFS | `uploaded_by`, `uploaded_by_label`, `filename`; nội dung tệp | Tệp có thể là giấy tờ cá nhân (giấy xác nhận nhân sự) |
| `config_changes` | `actor_id`, `actor_label` | Chỉ ghi thêm (#255) |
| `notification_outbox`, `notification_deliveries` | Mã người nhận, tiêu đề và thân thư đã điền tên | Không lưu địa chỉ thư |
| `similar_case_index` | Bản chép `title`, `description` và véc-tơ nhúng của hồ sơ đã giải quyết | Dữ liệu dẫn xuất, dựng lại được (#319) |
| `similar_case_views` | `requester_id` | Đo hiệu quả gợi ý |
| View báo cáo `bao_cao_*` | Nhãn tên, mã tác nhân | Superset đọc qua tài khoản chỉ đọc; không lưu bản sao |
| Bản sao lưu (`scripts/sao_luu.py`, #245) | Toàn bộ những thứ trên | Nằm ngoài cụm, do người vận hành giữ |

---

## Các phương án đã cân nhắc

Không có phần mềm bên thứ ba nào được đưa vào ở quyết định này.

### Phương án A — Ẩn danh hóa nhãn tên bằng thao tác quản trị có ghi vết (đã chọn)

Một thao tác của quản trị viên thay mọi nhãn tên của một người (`requester_label`, `assignee_label`,
`actor_label`, `author_label`, `uploaded_by_label`) bằng một **bí danh ổn định** — cùng một người luôn ra cùng
một bí danh, ví dụ "Người dùng đã ẩn danh 07". Mã định danh (`sub`) giữ nguyên; sau khi tài khoản bị xóa
khỏi Keycloak, mã đó không còn trỏ tới ai. Dòng nhật ký không bị xóa.

**Ưu điểm**

- Giữ tính chất chỉ ghi thêm: số dòng, thứ tự, mốc thời gian, cạnh đi qua không đổi — kết quả khai phá quy
  trình (biến thể, điểm nghẽn, thời gian chờ) **không đổi**
- Bí danh ổn định giữ được phân tích theo người thực hiện trên bảng điều khiển (một người xử lý bao nhiêu
  hồ sơ) mà không lộ tên
- Có ghi vết riêng: ai ẩn danh ai, lúc nào, theo yêu cầu nào

**Nhược điểm**

- Phải mở một lối sửa có kiểm soát qua trigger chỉ ghi thêm (dưới)
- Nội dung tự do (tiêu đề, mô tả, lời nhắn, ghi chú) có thể chứa tên — không tự dò được

### Phương án B — Xóa cứng dòng

Xóa hồ sơ, dòng nhật ký, lời nhắn và tệp của người yêu cầu.

**Nhược điểm**

- Phá tính chất chỉ ghi thêm — mất giá trị kiểm toán của cả nhật ký, không riêng phần của người đó
- Hồ sơ không thuộc riêng một người: xóa dòng của người xử lý là làm hỏng lịch sử hồ sơ của người gửi khác
- Kết quả khai phá đổi theo thời gian mà quy trình thực tế không đổi — loại

### Phương án C — Mã hóa nhãn tên, xóa khóa khi có yêu cầu

Mỗi người một khóa; nhãn lưu dạng mã hóa; xóa khóa là nhãn không đọc được nữa.

**Nhược điểm**

- Mọi chỗ đọc nhãn (giao diện, view báo cáo, Superset, dịch vụ khai phá) phải giải mã — đổi rộng ở ba
  không gian để giải một yêu cầu hiếm
- Quản lý khóa thêm một nơi phải sao lưu và có thể mất — loại

---

## Quyết định

Xử lý yêu cầu xóa bằng **phương án A**: ẩn danh hóa nhãn tên của đúng một người bằng một thao tác quản trị
có ghi vết riêng; không xóa dòng nhật ký. Thời hạn lưu giữ hồ sơ và tệp là **cấu hình**, mặc định để trống —
nghĩa là giữ vô thời hạn cho tới khi doanh nghiệp triển khai đặt giá trị.

---

## Lý do

Giá trị của hệ thống nằm ở nhật ký sự kiện chuẩn hóa: kiểm toán và khai phá quy trình đều cần chuỗi sự kiện
đầy đủ, không cần biết tên thật của người thực hiện. Ẩn danh hóa tách đúng hai thứ đó — bỏ phần nhận diện
được, giữ phần cấu trúc. Phương án B phá chính thứ hệ thống được xây để giữ; phương án C đúng về mặt lý
thuyết nhưng chi phí rải khắp ba không gian.

Thời hạn lưu giữ để cấu hình vì đó là chính sách của từng doanh nghiệp, đúng nguyên tắc nghiệp vụ nằm
trong dữ liệu (`CLAUDE.md` mục 1.2); nhóm không có căn cứ để chọn một con số thay họ.

---

## Cách tích hợp

Phần này mô tả thiết kế để cài đặt về sau. Issue #246 chỉ viết bản ghi; cài đặt là issue riêng.

1. **Bảng ghi vết** `personal_data_requests`: mã người (`sub`), loại yêu cầu (ẩn danh hóa), bí danh đã cấp,
   người thực hiện, lúc nào, căn cứ (số văn bản yêu cầu). Chỉ ghi thêm như các nhật ký khác
2. **Lối sửa có kiểm soát qua trigger chỉ ghi thêm**: một hàm `SECURITY DEFINER` duy nhất được phép đổi,
   và **chỉ đổi các cột `*_label`**, của những dòng có mã tác nhân trùng `sub` được ẩn danh. Trigger chặn
   sửa nhận biết lối này qua một biến cục bộ của giao dịch do hàm đặt; mọi đường khác vẫn bị chặn như cũ
3. **Dữ liệu dẫn xuất xóa thẳng**: dòng `similar_case_index` của hồ sơ có người được ẩn danh là người gửi
   bị xóa và lập lại từ nội dung đã ẩn danh; thư đã gửi (`notification_deliveries`) của người đó bị xóa
4. **Thời hạn lưu giữ** là hai giá trị cấu hình (số tháng giữ hồ sơ đã đóng, số tháng giữ tệp đính kèm),
   rỗng là giữ mãi. Bộ quét theo khuôn `nhip_quet.py` xử lý hồ sơ quá hạn lưu giữ theo đúng thao tác ẩn
   danh hóa ở trên, rồi xóa tệp đính kèm khỏi kho — không xóa dòng nhật ký
5. **Ngoài cụm**: tài khoản Keycloak xóa trên màn quản trị Keycloak; bản sao lưu cũ hết hạn theo vòng
   giữ bản sao lưu của người vận hành

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Trả lời được yêu cầu xóa mà không đánh đổi kiểm toán hay khai phá quy trình
- Người đọc kho biết dữ liệu cá nhân nằm ở đâu — bảng kiểm kê ở trên

**Điều gì trở nên khó hơn**

- Lịch sử hồ sơ của người đã ẩn danh hiện bí danh thay tên — đúng chủ ý, nhưng người cùng phòng không còn
  nhận ra ai đã xử lý hồ sơ cũ
- Nội dung tự do không được ẩn danh tự động; quản trị viên phải xem từng hồ sơ nếu yêu cầu bao gồm nội dung
- Bản sao lưu tạo trước lần ẩn danh vẫn chứa tên thật cho tới khi hết vòng giữ

**Việc phải làm tiếp sau quyết định này**

- [ ] Issue riêng: thao tác ẩn danh hóa, bảng ghi vết, lối sửa có kiểm soát (nếu làm trong phạm vi thi)
- [ ] Issue riêng: hai giá trị cấu hình thời hạn lưu giữ và bộ quét
- [x] `docs/ARCHITECTURE.md` mục 6 trỏ tới bản ghi này

---

## Ghi chú

- Kiểm kê lấy từ cụm thử dựng mới ở bản sửa `0025_quan_tri_cau_hinh`. Thêm bảng có cột người hay nội dung
  tự do thì cập nhật bảng kiểm kê bằng một bản ghi thay thế hoặc ghi chú bổ sung
- Kết quả khai phá không đổi khi đổi nhãn: dịch vụ khai phá hiện không đọc cột tác nhân nào, chỉ đọc mã hồ
  sơ, hoạt động, mốc thời gian và hai trạng thái (`services/khai-pha/app/du_lieu.py`, kiểm ngày 13/11/2026).
  Khi cài đặt, giữ điều đó bằng một phép thử có đáp án biết trước: khai phá trước và sau khi ẩn danh phải
  ra cùng kết quả
