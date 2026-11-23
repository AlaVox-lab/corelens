---
title: Màn Hệ thống và vận hành
description: Theo dõi tình trạng cụm, chạy bộ quét hạn ngay, quản lý người dùng qua Keycloak.
sidebar:
  order: 3
---

## Màn Hệ thống

Quản trị viên (tài khoản mẫu `khanh.vo`) mở **Hệ thống** (`/he-thong`) để xem tình trạng cụm, đọc
từ điểm cuối chi tiết `GET /system/health` của dịch vụ ứng dụng (chỉ quản trị viên gọi được): cổng
người dùng, dịch vụ ứng dụng và phiên bản, cơ sở dữ liệu, bộ quy tắc quy trình đã nạp và có bao nhiêu
trạng thái, và **nhịp hai bộ quét nền** — lần quét thành công cuối cách đây bao lâu, bản dịch vụ nào đã
chạy, hỏng liên tiếp mấy lượt và câu lỗi gần nhất. Người dùng khác không thấy mục này — trang chủ của
họ chỉ có việc cần làm, không có chữ kỹ thuật.

Dòng **Mô hình ngôn ngữ** cho biết mô hình gợi ý đang *tắt* (mặc định — điều phối thủ công), *sẵn sàng*,
hay *không phản hồi* kèm lý do. Khi mô hình bật, màn có thêm dòng nhịp của *Bộ quét gợi ý phân loại*.
Mô hình là tùy chọn, nên "không phản hồi" không làm tình trạng chung xấu đi — xem
[Mô hình ngôn ngữ](../../cai-dat/mo-hinh-ngon-ngu/).

![Màn Hệ thống của quản trị viên](../../../assets/anh/he-thong.png)

Quản trị viên **không đứng trong quy trình**: không đi bước nào trên hồ sơ, không mở hồ sơ ở buồng lái
nào.

## Kiểm sức khỏe không cần đăng nhập

`http://localhost:9080/health` (qua cổng API, không cần token) trả tình trạng chung của dịch vụ ứng dụng —
dùng được cho công cụ giám sát. Chỉ có `{"service": …, "status": "ok"}` hoặc `"degraded"`, không phiên
bản, không chi tiết lỗi. Bản thân cổng API báo khỏe qua healthcheck của Docker
(`docker compose --env-file .env ps`, dòng `cong-api`).

- `200` + `ok` — khỏe.
- `200` + `degraded` — dịch vụ vẫn phục vụ nhưng bộ quét nền im quá lâu hoặc hỏng liên tiếp: hồ sơ quá
  hạn có thể không tự leo thang. Mở màn Hệ thống xem bộ quét nào, lỗi gì.
- `503` — cơ sở dữ liệu hay lược đồ quy trình không dùng được. Chi tiết chỉ nằm ở nhật ký
  (`docker compose logs backend`) và màn Hệ thống.

## Bộ quét hạn

Dịch vụ ứng dụng chạy hai bộ quét nền, mặc định mỗi 60 giây: leo thang hồ sơ quá hạn và đi các bước
tự động khi hồ sơ nằm im quá hạn chờ. Bật tắt và chu kỳ ở `SLA_SCAN_ENABLED`,
`SLA_SCAN_INTERVAL_SECONDS` trong `.env`. Quản trị viên chạy được một lượt ngay bằng `POST /sla/scan`.

Chạy nhiều bản dịch vụ ứng dụng thì mỗi lượt chỉ một bản quét (khóa tư vấn của PostgreSQL), bản kia bỏ
lượt. Mỗi lượt ghi nhịp vào cơ sở dữ liệu; ngưỡng cảnh báo ở `SLA_SCAN_STALE_AFTER_SECONDS` và
`SLA_SCAN_MAX_CONSECUTIVE_ERRORS` — xem [Cấu hình](../../cai-dat/cau-hinh/).

**Thử leo thang mà không phải chờ hết hạn thật** (chỉ trên cụm thử): đẩy một hồ sơ đang xử lý sang quá
hạn — lùi cả mốc vào trạng thái, không thì hồ sơ còn nằm trong ân hạn — rồi chờ một lượt quét:

```bash
docker exec dxlab-postgres psql -U dxlab -d dxlab -c "UPDATE requests SET sla_running_seconds = 999999, sla_segment_since = now() - interval '1 day' WHERE id = <số hồ sơ>"
```

## Người dùng và phòng ban

Người dùng, vai trò và phòng ban quản lý ở Keycloak (`http://localhost:8080`, tài khoản quản trị
trong `.env`):

- **Vai trò** là vai trò của realm: `requester`, `classifier`, `approver`, `handler`, `administrator`
- **Phòng ban** là nhóm dưới đường dẫn `/phong-ban/` (đổi bằng `KEYCLOAK_DEPARTMENT_GROUP_PREFIX`)
- Khóa tài khoản người nghỉ việc thì họ không đăng nhập được và không còn trong danh sách nhận việc
  (tài khoản mẫu `tuan.ngo`)
- Gán vai qua **nhóm** cũng được, như doanh nghiệp thật hay làm — tài khoản mẫu `lan.vu` nhận vai người
  xử lý qua nhóm `/nhom-vai-tro/nguoi-xu-ly`
- Client `dx-directory` không dùng để đăng nhập: đó là tài khoản dịch vụ chỉ đọc, để dịch vụ ứng dụng
  tra tên người trong phòng cho ô chọn người xử lý

Thêm phòng ban mới phải thêm cả nhóm trong Keycloak lẫn dòng trong bảng `departments` — xem
[Danh mục và các con số](../danh-muc-va-con-so/).

## Xuất nhật ký sự kiện

Khối **Xuất nhật ký sự kiện** trên màn Hệ thống tải nhật ký dạng CSV hoặc JSON, chọn khoảng ngày (theo
UTC) hay bỏ trống để lấy hết. Mỗi dòng một sự kiện: `case_id`, `activity`, `timestamp` (UTC),
`actor`, `from_state`, `to_state`, cùng loại yêu cầu, phòng ban, mức ưu tiên và bộ quy tắc của hồ
sơ; mỗi hồ sơ mở đầu bằng sự kiện `create-case` lúc tạo. Người thao tác chỉ ghi bằng mã định danh,
không có tên và ghi chú. Tệp CSV mở thẳng bằng bảng tính, chữ có dấu hiện đúng. Công cụ khác gọi
`GET /analytics/event-log?format=csv&from=2026-11-01&to=2026-11-30` bằng token của quản trị viên.

## Webhook

Khối **Webhook** cuối màn Hệ thống quản lý việc nền tảng lõi đẩy sự kiện ra ứng dụng khác: mỗi lần hồ sơ
chuyển bước, lõi gửi `POST` JSON tới các địa chỉ đã đăng ký, ký HMAC-SHA256, tự thử lại khi bên nhận lỗi.
Khối gọi đúng API `/core/v1/webhooks` của lõi — làm trên cổng hay qua API là một.

- **Đăng ký**: điền địa chỉ nhận (`http` hay `https`), mô tả nếu muốn, và mã hoạt động nếu chỉ muốn nhận vài
  loại sự kiện (cách nhau bởi dấu phẩy, ví dụ `cancel, confirm-done`; bỏ trống là mọi hoạt động). Bấm
  **Đăng ký webhook**. Bí mật ký hiện **một lần duy nhất** ngay dưới biểu mẫu — bấm **Chép** rồi dán sang
  bên nhận để kiểm tiêu đề `X-DXOS-Signature`. Tải lại trang là không xem lại được nữa
- **Theo dõi**: mỗi đăng ký liệt kê năm lần gửi gần nhất — mã sự kiện, và *Đã gửi* (kèm giờ, mã phản hồi),
  *Chờ thử lại* (lần thứ mấy, giờ thử lại, lỗi cuối — ví dụ bên nhận đang tắt) hay *Hỏng hẳn* (đã hết số
  lần thử). Tải lại trang để xem lần gửi mới
- **Hủy**: nút **Hủy** cạnh đăng ký, xác nhận một lần. Các lần gửi đang chờ bỏ theo

Đăng ký chỉ nhận sự kiện xảy ra **sau** lúc tạo. Khi có ít nhất một đăng ký đang bật, phần *Các dịch vụ* có
thêm dòng nhịp **Bộ gửi webhook**. Cách viết bên nhận và kiểm chữ ký: `examples/goi-loi/nhan_webhook.py`.

## Nhật ký truy cập dữ liệu cá nhân

Nhật ký sự kiện ghi mọi lần **đổi** hồ sơ. Khối **Nhật ký truy cập dữ liệu cá nhân** cuối màn Hệ thống trả lời câu
còn lại: **ai đã xem** dữ liệu cá nhân của người khác, lúc nào — phục vụ việc theo dõi xử lý dữ liệu cá nhân (Nghị
định 13/2023/NĐ-CP). Bốn loại truy cập được ghi:

| Loại | Khi nào |
|---|---|
| Xem chi tiết hồ sơ | Điều phối viên, phòng ban mở trang hồ sơ (kể cả ngăn xem nhanh của hàng đợi); ứng dụng khác đọc chi tiết hồ sơ qua API lõi |
| Xem liên hệ người gửi | Thư điện tử và số điện thoại của người gửi hiện trên trang hồ sơ |
| Tải tệp đính kèm | Ai đó tải một tệp — cột *Tệp* ghi tên tệp |
| Xuất nhật ký sự kiện | Tải CSV, JSON, XES — cột *Hồ sơ* ghi định dạng và khoảng ngày đã xuất |

**Không ghi** người gửi xem hồ sơ của chính mình (kể cả tải tệp mình đính kèm), xem danh sách, hàng đợi, tìm kiếm,
và các thao tác trên hồ sơ — thao tác đã nằm trong nhật ký sự kiện. Lần bị từ chối (không có quyền, không thấy hồ
sơ) cũng không ghi.

- **Lọc**: mã hồ sơ (`YC-2026-0184` hay chỉ `184`), người (một phần tên, không cần gõ dấu, hay mã người), loại truy
  cập, khoảng ngày theo giờ Việt Nam. Bấm **Lọc**; mỗi bộ lọc đang bật là một chip, bấm chip để bỏ. Địa chỉ trang
  giữ bộ lọc — gửi đường dẫn cho người khác là họ thấy đúng kết quả đó
- **Bảng**: mới nhất trước, mỗi trang 50 dòng. Cột *Kênh* là **Cổng** (các màn của cổng người dùng) hay **API lõi**
  (ứng dụng khác gọi `/core/v1`, ví dụ tài khoản dịch vụ). Bấm mã hồ sơ: quản trị viên có cả vai điều phối thì mở
  hồ sơ, còn không thì lọc nhật ký theo đúng hồ sơ đó. Màn hẹp hiện mỗi lượt thành một khối nhãn–giá trị
- **Chỉ ghi thêm**: không ai sửa hay xóa được dòng nào, kể cả quản trị viên. Xóa hồ sơ thì dòng vẫn còn, chỉ mất
  liên kết tới hồ sơ. Xem nhật ký này không tự sinh dòng mới
- **Gọi bằng API**: `GET /admin/access-audit?case_id=…&actor=…&access_kind=…&from=…&to=…&limit=…&offset=…` bằng token
  quản trị viên; `from`/`to` là mốc ISO 8601, không ghi múi giờ thì hiểu là UTC. Danh sách mã loại:
  `GET /admin/access-audit/kinds`

Ghi nhật ký hỏng (cơ sở dữ liệu chậm, mất kết nối) không chặn người dùng: trang vẫn mở, dịch vụ ghi một dòng lỗi
có cấu trúc vào nhật ký vận hành (`Không ghi được nhật ký truy cập`, kèm loại, người, hồ sơ). Chưa có thời hạn
lưu giữ riêng cho nhật ký này; nó không vào bản lưu trữ lạnh.

## Lưu trữ lạnh

Dữ liệu lịch sử có thêm một bản ở **tầng lạnh** — kho đối tượng SeaweedFS. Bộ quét nền *Bộ lưu trữ lạnh*
(mặc định bật, mỗi giờ một lượt, nhịp hiện trên màn Hệ thống như các bộ quét khác) niêm phong mỗi **tháng
UTC đã khép** — tháng trước trở về trước — thành một bản lưu dưới `luu-tru-lanh/<YYYY-MM>/` trong thùng
tệp đính kèm:

- `nhat-ky-su-kien.csv.gz` — nhật ký sự kiện của tháng, đúng cột của khối xuất ở trên
- `ho-so-ket-thuc.csv.gz` — hồ sơ kết thúc trong tháng: loại, phòng, ưu tiên, trạng thái cuối, người gửi
  và người xử lý bằng mã, đồng hồ hạn
- `manifest.json` — số dòng, cột và mã băm SHA-256 của từng tệp

CSV UTF-8 nén gzip: mở được bằng bảng tính hay bất kỳ công cụ nào, không cần hệ thống. Bản lưu **không bao
giờ bị ghi đè** — chạy lại bao nhiêu lần cũng an toàn — và không chứa tên người hay nội dung tự do. Cơ sở
dữ liệu đang chạy giữ nguyên, không dọn gì.

Chạy ngay một lượt thay vì chờ, rồi đọc lại và kiểm (gốc kho mã, cụm đang chạy):

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:9080/archive/scan
python scripts/doc_luu_tru.py 2026-10 --doi-chieu
```

`doc_luu_tru.py` tải bản kê và từng tệp, kiểm mã băm, đếm dòng so với bản kê, và với `--doi-chieu` so số
dòng nhật ký với cơ sở dữ liệu. Công cụ khác dùng API của lõi `GET /core/v1/archive` (chỉ quản trị viên) —
xem [API](../../tham-khao/api/). Cụm mới dựng chưa có tháng nào đã khép; nạp dữ liệu trình diễn (dưới) để
có hai, ba tháng. Bật tắt, chu kỳ, thùng và tiền tố: [Cấu hình](../../cai-dat/cau-hinh/). Đường đi của dữ
liệu từ nhật ký tới bản lưu: [Phả hệ dữ liệu](../../tham-khao/pha-he-du-lieu/).

## Báo cáo

Apache Superset (`http://localhost:8088`) có sẵn dashboard **Vận hành yêu cầu** ngay khi dựng cụm:
tồn đọng theo phòng ban, thời gian xử lý trung vị theo loại yêu cầu, tỷ lệ vi phạm hạn theo phòng
ban, phân bố loại yêu cầu theo tuần. Superset đọc dữ liệu nghiệp vụ bằng tài khoản chỉ đọc; dashboard
nạp từ tệp trong `infra/superset/bang-dieu-khien/` mỗi lần khởi động. Đăng nhập Superset bằng tài
khoản quản trị trong `.env` (`SUPERSET_ADMIN_USER`) để sửa; sửa xong phải xuất lại ra thư mục đó —
cách làm ở `docs/ARCHITECTURE.md` mục 6.3.

Người dùng cổng xem dashboard ở mục **Báo cáo** trên thanh bên, không đăng nhập Superset: trưởng
phòng thấy số của phòng mình, điều phối viên và quản trị viên thấy toàn công ty. Vai trò nào xem được
và xem tới đâu là cột `report_scope` của bảng `roles` (`department`, `all`, hay để trống) — đổi bằng
dữ liệu, không sửa mã. Superset tắt thì mục Báo cáo báo không phản hồi, phần còn lại của cổng vẫn
chạy. Đổi cổng công bố của cổng người dùng (`FRONTEND_PORT`) thì dựng lại Superset, vì nó chỉ cho
đúng địa chỉ đó nhúng bảng điều khiển.

**Dữ liệu trình diễn.** Cụm mới dựng chỉ có vài hồ sơ, biểu đồ gần như trống. Trên cụm thử hay cụm
trình diễn, nạp vài trăm hồ sơ giả trải ba tháng, đi đúng bộ quy tắc đang bật:

```bash
python scripts/nap_du_lieu_trinh_dien.py --xac-nhan
```

Chạy ở gốc kho mã khi cụm đang chạy, chỉ cần Python 3.10 trở lên. Hồ sơ mẫu mang tiền tố `[Mẫu]` và
**không gỡ ra được** — nhật ký sự kiện chỉ ghi thêm — nên muốn sạch lại thì `down -v`. Lệnh dừng khi
cụm đã có hồ sơ thật; trên cụm thử có vài hồ sơ tạo tay thì thêm `--cho-tron`. Đổi số hồ sơ và số
ngày bằng `--so-ho-so`, `--so-ngay`.
