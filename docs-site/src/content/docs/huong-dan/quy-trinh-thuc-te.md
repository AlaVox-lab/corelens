---
title: Quy trình thực tế
description: Đọc sơ đồ quy trình vẽ lại từ nhật ký sự kiện — điểm nghẽn, nhánh lệch, đường đi phổ biến — và biết ai thấy gì.
sidebar:
  order: 7
---

Mục **Báo cáo** có hai màn, chuyển qua lại bằng thanh ở đầu trang: **Bảng điều khiển** (số liệu tồn đọng,
trễ hạn) và **Quy trình thực tế**. Màn thứ hai trả lời một câu hỏi khác: *hồ sơ đang thật sự đi đường nào,
và chỗ nào làm chậm hay lệch khỏi thiết kế?* Nó vẽ lại quy trình từ nhật ký sự kiện — mỗi lần hồ sơ đổi
trạng thái đều đã được ghi — nên không ai phải nhập thêm gì.

Địa chỉ: `/bao-cao/quy-trinh`.

## Ai thấy gì

Quyền xem báo cáo cấp theo vai trò, cùng cửa với bảng điều khiển:

| Vai | Thấy |
|---|---|
| Người gửi | Không có mục Báo cáo. Mở thẳng địa chỉ thì gặp lời báo "Tài khoản này không mở được khu vực này" |
| Trưởng phòng | Chỉ hồ sơ của phòng mình. Dòng **Phạm vi số liệu** dưới thanh chuyển ghi tên phòng |
| Điều phối viên, quản trị viên | Toàn công ty |

Mã hồ sơ trên màn là liên kết: điều phối viên mở được trang hồ sơ ở buồng lái **Điều phối**, người làm
việc ở phòng mở ở buồng lái **Phòng ban**. Ai không vào được buồng lái nào thì thấy mã dạng chữ thường.

## Chọn khoảng ngày

Màn tính trên các hồ sơ **gửi** trong khoảng ngày đã chọn. Mặc định là **90 ngày gần nhất**, tới hôm nay
và gồm cả hôm nay. Ba nút chọn nhanh — **30 ngày**, **90 ngày**, **12 tháng** (365 ngày) — hoặc gõ hai ô
ngày. Khoảng nằm trên địa chỉ trang (`?tu=2026-08-13&den=2026-11-10`): tải lại hay gửi đường dẫn cho
người khác thì giữ khoảng đó.

Khoảng dài nhất là 366 ngày. Chọn sai (ngày bắt đầu sau ngày kết thúc, hay quá dài) thì lời báo hiện ngay
dưới hai ô ngày. Ngày được cắt theo múi giờ của lịch làm việc mặc định, không theo giờ UTC.

## Câu kết luận

Đầu màn là vài câu tóm tắt, dựng từ đúng các con số bên dưới bằng mẫu câu cố định: cùng số liệu luôn ra
cùng câu, không do mô hình ngôn ngữ viết. Các câu nói lần lượt:

1. Có bao nhiêu hồ sơ được gửi, trong khoảng nào, thuộc phạm vi nào
2. **Điểm nghẽn rõ nhất** — trạng thái hồ sơ chờ lâu nhất, chờ bao lâu, gấp mấy lần mức chung, và nhóm
   chậm nhất (theo phòng khi bạn thấy toàn công ty và có từ hai phòng, không thì theo loại yêu cầu).
   Không trạng thái nào nghẽn thì câu nói rõ điều đó
3. Mỗi **nhánh lệch** có hồ sơ: bao nhiêu phần trăm, bao nhiêu hồ sơ, nhiều nhất ở loại yêu cầu nào
   (và phòng nào, khi so sánh được giữa các phòng)
4. Những bước của luồng thiết kế mà **chưa hồ sơ nào đi qua**, nếu có

### Khuyến nghị cải tiến

Khi cụm bật mô hình ngôn ngữ (hồ sơ `tri-tue`), dưới các câu kết luận có thêm khối **Khuyến nghị cải
tiến**: vài câu ngắn mô hình viết từ chính các con số trên, ví dụ nên bổ sung người cho phòng chậm nhất
hay rà lại biểu mẫu của loại hay bị trả về. Màn **không chờ** khối này — kết quả và câu kết luận hiện
trước, khuyến nghị tới sau vài giây tới vài chục giây.

- **Con số luôn của hệ thống**: mỗi câu gồm việc nên làm do mô hình viết, rồi *căn cứ* chép nguyên dòng
  số liệu tương ứng từ kết quả khai phá. Phần mô hình viết mà có con số hay tên trạng thái, loại, phòng
  không thuộc đúng dòng căn cứ đó thì cả câu bị bỏ
- **Chỉ để đọc**: đây là gợi ý của hệ thống, không tự đổi cấu hình hay hồ sơ nào. Quyết định cải tiến là
  của bạn
- Mở lại màn với cùng số liệu thì khuyến nghị có ngay; có hồ sơ mới làm số đổi thì hệ thống viết lại
- Mô hình tắt hay không câu nào qua phép đối chiếu thì khối không hiện — màn vẫn đủ câu kết luận

Thời gian chờ luôn tính bằng **giờ làm việc** theo lịch trong dữ liệu — cùng phép đo với đồng hồ hạn xử
lý — nên "9 giờ 5 phút làm việc" là chín tiếng năm phút trong giờ làm, không phải thời gian đồng hồ.

## Đọc sơ đồ

Mỗi **ô** là một trạng thái: tên, số lượt hồ sơ vào, và thời gian chờ trung vị ở đó. Ô bắt đầu và kết
thúc mang nhãn góc trên. Mỗi **đường nối** là một lần chuyển trạng thái; số trên đường là số lượt đi qua,
nét càng dày càng nhiều lượt.

| Màu đường | Nghĩa |
|---|---|
| Xanh dương | Luồng chính — hồ sơ đi đúng thiết kế |
| Cam | Trả về làm lại |
| Đỏ | Leo thang do quá hạn xử lý |
| Xanh lục lam | Hệ thống tự chuyển khi hết hạn chờ |
| Tím | Mở lại sau khi kết thúc |

**Nét đứt mờ**, kèm số 0, là một bước của luồng thiết kế mà chưa có hồ sơ nào đi qua trong khoảng đang
xem. Ô tô vàng kèm chữ **Nghẽn** là điểm nghẽn.

Rê chuột hay dùng phím Tab tới một ô hay một đường để xem số cụ thể: số lượt, số hồ sơ, và với đường
nối thì tách theo từng loại. Kéo để di chuyển, các nút **+**, **−** để phóng to thu nhỏ, nút định vị để
đưa sơ đồ về giữa. Trên màn hẹp có thêm **Xem toàn màn hình**; Esc để đóng.

### Điểm nghẽn tính thế nào

Với mỗi trạng thái chưa kết thúc, hệ thống lấy **trung vị** thời gian chờ của mọi lượt hồ sơ ở đó. Một
trạng thái là điểm nghẽn khi trung vị đó **gấp từ 2 lần** trung vị chung của mọi lượt ở mọi trạng thái
chưa kết thúc. Khối **Điểm nghẽn** xếp hạng các trạng thái từ chờ lâu nhất xuống.

Bội số 2 là con số cấu hình, không nằm trong mã: quản trị viên đổi bằng biến môi trường
`MINING_BOTTLENECK_FACTOR` (tệp `infra/.env`, mặc định `2`) rồi khởi động lại dịch vụ khai phá. Đặt thấp
thì nhiều trạng thái bị gọi là nghẽn, đặt cao thì chỉ còn những chỗ thật sự tệ.

### Năm loại nhánh lệch

Nhánh lệch là hồ sơ đi **ra khỏi luồng chính**. Có đúng năm loại, hệ thống nhận biết qua cờ khai trong
bộ quy tắc chứ không qua tên trạng thái:

| Loại | Hồ sơ nào được tính |
|---|---|
| Trả về làm lại | Đi qua một bước đánh dấu làm lại |
| Leo thang do quá hạn | Bị bộ quét nền tự chuyển vì quá hạn xử lý |
| Tự chuyển khi hết hạn chờ | Bị hệ thống tự chuyển vì hồ sơ nằm im quá hạn chờ |
| Mở lại sau khi kết thúc | Được mở lại sau khi đã kết thúc |
| Chuyển phòng nhiều lần | Được đặt phòng phụ trách từ hai lần trở lên |

Bốn loại đầu hiện thành đường màu trên sơ đồ; loại thứ năm là thuộc tính của hồ sơ chứ không phải một
bước, nên chỉ có trong khối **Nhánh lệch**. Tỷ lệ tính trên tổng số hồ sơ trong khoảng.

### Các đường đi phổ biến

Mỗi hồ sơ có một chuỗi trạng thái nó đã đi qua. Khối **Các đường đi phổ biến** liệt kê năm chuỗi gặp
nhiều nhất, kèm tỷ lệ và số hồ sơ; dòng "còn lại" gộp mọi chuỗi hiếm hơn. Bấm một chuỗi để **tô sáng**
đường đó trên sơ đồ (phần còn lại mờ đi); bấm lại hay nút **Bỏ chọn** để trở về.

## Từ con số tới hồ sơ cụ thể

Mọi con số đều bấm được để xem hồ sơ đứng sau nó, ở ngăn bên phải:

- Bấm một **trạng thái** (ô trên sơ đồ hay dòng xếp hạng điểm nghẽn): các hồ sơ **chờ lâu nhất** ở đó,
  kèm thời gian chờ, số lượt, và nhãn "đang chờ" nếu hồ sơ còn nằm ở đó
- Bấm một **nhánh lệch** (dòng trong khối nhánh lệch, hay số trên đường màu): các hồ sơ của nhánh, đầu
  danh sách có số tách theo loại yêu cầu và theo phòng
- Bấm một **đường đi phổ biến**: các hồ sơ đi đúng chuỗi đó

Danh sách bị cắt khi quá dài; ngăn ghi rõ "Hiện 200 trên 315 hồ sơ". Esc đóng ngăn.

Mở một hồ sơ trong nhánh lệch, trang hồ sơ có khối **Đi lệch quy trình thiết kế** chỉ ra đúng bước đã
rẽ khỏi luồng chính, cùng cách tính với màn này — xem trang [Phòng ban](../phong-ban/), mục *Hồ sơ đi lệch quy trình*.

## Khi dịch vụ khai phá không chạy

Màn nói **"Hệ thống không phản hồi"** và có nút **Thử lại**. Chỉ màn này bị ảnh hưởng: hồ sơ, bảng điều
khiển và mọi thao tác khác vẫn bình thường, vì không dịch vụ nào của cổng phụ thuộc vào dịch vụ khai phá.

Chưa có hồ sơ nào gửi trong khoảng thì màn hiện "Không có hồ sơ nào gửi trong khoảng này" — thử chọn
khoảng dài hơn.

## Mã nguồn của dịch vụ khai phá

Dịch vụ khai phá dùng thư viện PM4Py nên theo giấy phép **AGPL-3.0-or-later**, khác phần còn lại của
Corelens (MIT). Điều 13 của AGPL đòi người dùng qua mạng lấy được mã nguồn, nên cuối màn luôn có dòng
*"Phân tích bởi dịch vụ khai phá quy trình, giấy phép AGPL-3.0 — mã nguồn"*, kể cả khi khoảng ngày
không có hồ sơ nào. Khối bước lệch trên trang hồ sơ mang cùng dòng đó.

Liên kết **mã nguồn** đọc từ biến môi trường `MINING_SOURCE_URL` của cổng (tệp `infra/.env`, mặc định
thư mục `services/khai-pha` trên kho GitHub của dự án). Doanh nghiệp tự triển khai mà **sửa** dịch vụ
khai phá thì phải trỏ biến này về kho chứa bản đã sửa, rồi khởi động lại cổng.
