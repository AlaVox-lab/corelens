# Gọi nền tảng lõi từ một ứng dụng khác

Ví dụ cho #365: một chương trình **không phải cổng người dùng** — đóng vai phần mềm nhân sự, ứng dụng di
động hay kịch bản tích hợp — tạo hồ sơ và đi một bước chuyển trạng thái **chỉ bằng API của nền tảng lõi**
`/core/v1`, qua cổng API. Ranh giới lõi và ứng dụng minh họa: `docs/ARCHITECTURE.md` mục 2.3.

`goi_loi.py` chỉ dùng thư viện chuẩn của Python 3.10 trở lên:

1. Xin token của tài khoản dịch vụ `dx-integration` bằng luồng **client credentials** của Keycloak
2. Rồi chỉ gọi cổng API dưới `/core/v1`: danh tính → danh mục loại yêu cầu → tạo hồ sơ → bước được phép,
   bước chưa được kèm lý do (`transition-options`, #424) → đi một bước → lịch sử

Không mã cứng mã trạng thái, mã loại hay mã bước nào: kịch bản chọn từ dữ liệu API trả về — loại đầu tiên
của danh mục, trường riêng bắt buộc điền theo kiểu khai báo, bước chính của người gọi hoặc bước đầu tiên
làm đổi trạng thái. Với dữ liệu mẫu, tài khoản dịch vụ mang vai `requester` nên ở "Đã gửi" chỉ có "Sửa nội
dung" và "Hủy yêu cầu" — kịch bản đi "Hủy yêu cầu", hồ sơ thử không nằm lại trong hàng đợi của điều phối
viên.

## Chạy

Cụm đang chạy (`docker compose up`), đứng ở gốc kho mã:

```bash
python examples/goi-loi/goi_loi.py
```

Địa chỉ và tài khoản đọc từ `infra/.env`: `GATEWAY_PORT`, `KEYCLOAK_PORT`, `KEYCLOAK_REALM`,
`KEYCLOAK_INTEGRATION_CLIENT_ID`, `KEYCLOAK_INTEGRATION_SECRET`. Cụm khác thì chỉ tệp env khác hay địa chỉ
khác:

```bash
python examples/goi-loi/goi_loi.py --env-file duong/toi/tep.env
python examples/goi-loi/goi_loi.py --cong-api http://localhost:9080 --keycloak http://localhost:8080
```

Cụm dựng trước khi có `/core/v1` chưa có client `dx-integration` (Keycloak chỉ nạp realm lúc tạo realm).
Tạo nó một lần, không cần xóa dữ liệu:

```bash
python scripts/tai_khoan_dich_vu.py
```

## Đầu ra mẫu

Chạy trên cụm thử vừa dựng sạch, ngay sau một lượt kiểm thử (nên số hồ sơ không bắt đầu từ 1), 15/11/2026:

```
1. Token của tài khoản dịch vụ dx-integration: luồng client credentials, sống 300 giây
2. Danh tính theo lõi: service-account-dx-integration · vai default-roles-dx-os-lab, offline_access, requester, uma_authorization
3. Danh mục: 4 loại yêu cầu (Sự cố thiết bị, Cấp quyền phần mềm, Giấy xác nhận nhân sự, Đề xuất mua vật tư); chọn “Sự cố thiết bị”
4. Đã tạo hồ sơ YC-2026-0017 (mã 17), trạng thái “Đã gửi”
   Bước tài khoản dịch vụ đi được: Sửa nội dung → Đã gửi; Hủy yêu cầu → Đã hủy
5. Đã đi bước “Hủy yêu cầu”: hồ sơ giờ ở “Đã hủy”
6. Lịch sử hồ sơ YC-2026-0017 (1 sự kiện, giờ UTC):
   2026-11-15 16:44:47 · dx-integration · Hủy yêu cầu: Đã gửi → Đã hủy
```

Hồ sơ mang nhãn người gửi `dx-integration` — tên client, vì token của tài khoản dịch vụ không có tên người.
Trên buồng lái điều phối, hồ sơ hiện như mọi hồ sơ khác.

## Quy trình thứ hai: đề xuất mua sắm duyệt hai cấp

Ví dụ cho #376: động cơ luồng công việc chạy **nhiều quy trình**, và một ứng dụng khác chạy trọn quy trình
của riêng nó chỉ qua `/core/v1`. `quy_trinh_mua_sam.py` đóng vai phần mềm mua sắm, dùng ba tài khoản dịch
vụ (luồng client credentials):

| Vai trong ví dụ | Client | Biến trong `.env` | Vai realm |
|---|---|---|---|
| Người đề xuất | `dx-integration` | `KEYCLOAK_INTEGRATION_*` | `requester` |
| Trưởng phòng | `dx-integration-truong-phong` | `KEYCLOAK_INTEGRATION_HEAD_*` | `approver`, thuộc phòng Hành chính |
| Duyệt cấp hai | `dx-integration-duyet` | `KEYCLOAK_INTEGRATION_REVIEWER_*` | `classifier` |

Danh mục quy trình → loại và trạng thái của quy trình → người đề xuất tạo hồ sơ, gửi trưởng phòng của phòng
đề xuất → trưởng phòng thấy hồ sơ trong việc chờ mình (`needs_action=true`) và duyệt → người duyệt cấp hai
duyệt → đọc lịch sử. Từ #397 quy trình **rẽ nhánh theo số tiền** bằng điều kiện trên cạnh khai trong dữ liệu:
dưới 5.000.000 đồng trưởng phòng duyệt là xong; `--so-tien` chọn số tiền gửi (mặc định 2.500.000). Mỗi người đi **bước chính** mà lõi trả về cho chính họ; không mã cứng mã quy trình,
trạng thái hay bước nào. Cửa bước chuyển của lõi xét vai và phạm vi của từng người gọi: trưởng phòng chỉ thấy
đề xuất của phòng mình, người đề xuất gọi nhầm bước của trưởng phòng nhận `403`.

```bash
python examples/goi-loi/quy_trinh_mua_sam.py
python examples/goi-loi/quy_trinh_mua_sam.py --so-tien 12000000
python examples/goi-loi/quy_trinh_mua_sam.py --quy-trinh purchase-approval --env-file duong/toi/tep.env
```

Cụm dựng từ `v1.0.0` trở về trước: chép thêm các dòng `KEYCLOAK_INTEGRATION_HEAD_*`,
`KEYCLOAK_INTEGRATION_REVIEWER_*` từ `infra/.env.example` sang `.env`, rồi chạy `python
scripts/tai_khoan_dich_vu.py` một lần. Quy trình thứ hai do bản sửa lược đồ `0028` thêm lúc dịch vụ khởi động.

Đầu ra phần duyệt, cụm phát triển 17/11/2026 — dưới ngưỡng (mặc định, 2.500.000 đồng):

```
4. Trưởng phòng: hồ sơ CÓ trong danh sách đang chờ mình
   Bước trưởng phòng đi được: Duyệt (dưới ngưỡng) → Đã duyệt (chính); Trả lại để bổ sung → Trả lại bổ sung; Từ chối đề xuất → Từ chối
   Trưởng phòng đã đi “Duyệt (dưới ngưỡng)”: hồ sơ giờ ở “Đã duyệt” — trạng thái kết thúc
6. Lịch sử hồ sơ YC-2026-7150 — các dòng nhật ký sự kiện (2, giờ UTC):
   2026-11-17 11:12:03 · dx-integration · Gửi trưởng phòng duyệt: Đã gửi đề xuất → Chờ trưởng phòng duyệt
   2026-11-17 11:12:03 · dx-integration-truong-phong · Duyệt (dưới ngưỡng): Chờ trưởng phòng duyệt → Đã duyệt
```

Từ ngưỡng trở lên (`--so-tien 12000000`) thì đi đủ hai cấp như đầu ra trước #397, trên cụm thử vừa dựng sạch,
16/11/2026:

```
1. Token client credentials của ba tài khoản dịch vụ: dx-integration (người đề xuất), dx-integration-truong-phong (trưởng phòng), dx-integration-duyet (duyệt cấp hai)
2. Lõi chạy 2 quy trình: internal-requests “Cổng yêu cầu nội bộ” (của ứng dụng minh họa); purchase-approval “Đề xuất mua sắm duyệt hai cấp”
   Chọn “Đề xuất mua sắm duyệt hai cấp”: loại “Đề xuất mua sắm”, 7 trạng thái (Đã gửi đề xuất, Chờ trưởng phòng duyệt, Chờ duyệt cấp hai, Trả lại bổ sung, Đã duyệt, Từ chối, Đã rút)
3. Người đề xuất tạo hồ sơ YC-2026-1489 (mã 1489) thuộc quy trình “Đề xuất mua sắm duyệt hai cấp”, trạng thái “Đã gửi đề xuất”, trường riêng {'ly-do': 'Nhập từ ứng dụng tích hợp mẫu', 'so-tien': 2500000}
   Bước người đề xuất đi được: Gửi trưởng phòng duyệt → Chờ trưởng phòng duyệt (chính); Sửa nội dung → Đã gửi đề xuất; Rút đề xuất → Đã rút
   Người đề xuất đã đi “Gửi trưởng phòng duyệt”: hồ sơ giờ ở “Chờ trưởng phòng duyệt”
4. Trưởng phòng: hồ sơ CÓ trong danh sách đang chờ mình
   Bước trưởng phòng đi được: Duyệt cấp một → Chờ duyệt cấp hai (chính); Trả lại để bổ sung → Trả lại bổ sung; Từ chối đề xuất → Từ chối
   Trưởng phòng đã đi “Duyệt cấp một”: hồ sơ giờ ở “Chờ duyệt cấp hai”
5. Người duyệt cấp hai: hồ sơ CÓ trong danh sách đang chờ mình
   Bước người duyệt cấp hai đi được: Duyệt cấp hai → Đã duyệt (chính); Trả lại để bổ sung → Trả lại bổ sung; Từ chối đề xuất → Từ chối
   Người duyệt cấp hai đã đi “Duyệt cấp hai”: hồ sơ giờ ở “Đã duyệt” — trạng thái kết thúc
6. Lịch sử hồ sơ YC-2026-1489 — các dòng nhật ký sự kiện (3, giờ UTC):
   2026-11-16 14:24:49 · dx-integration · Gửi trưởng phòng duyệt: Đã gửi đề xuất → Chờ trưởng phòng duyệt
   2026-11-16 14:24:49 · dx-integration-truong-phong · Duyệt cấp một: Chờ trưởng phòng duyệt → Chờ duyệt cấp hai
   2026-11-16 14:24:50 · dx-integration-duyet · Duyệt cấp hai: Chờ duyệt cấp hai → Đã duyệt
```

Hồ sơ này không hiện trên cổng người dùng, buồng lái hay bảng điều khiển: các màn của ứng dụng minh họa chỉ
dùng quy trình mặc định. Nó có trong nhật ký sự kiện xuất ra (`GET /core/v1/events?process=purchase-approval`).

## Nhận sự kiện bằng webhook

Ví dụ cho #390: thay vì tự hỏi lại API, ứng dụng để nền tảng lõi **chủ động báo** mỗi khi hồ sơ chuyển bước.
`nhan_webhook.py` mở một máy chủ HTTP nhỏ trên máy, đăng ký chính địa chỉ đó qua `POST /core/v1/webhooks`,
rồi kiểm chữ ký HMAC, mốc thời gian, bỏ sự kiện trùng và in từng sự kiện tới. Ctrl+C thì hủy đăng ký.

Đăng ký webhook cần vai `administrator`. Trên cụm thử, thêm vai cho tài khoản dịch vụ một lần:
`KEYCLOAK_INTEGRATION_ROLES=requester,administrator` trong `infra/.env`, rồi:

```bash
python scripts/tai_khoan_dich_vu.py
python examples/goi-loi/nhan_webhook.py
```

Lõi gọi tới `http://host.docker.internal:8765/su-kien` (Docker Desktop); máy Linux không có tên đó thì chỉ
địa chỉ khác bằng `--dia-chi-nhan`. `--hoat-dong <mã> …` chỉ nhận vài mã hoạt động.

Đầu ra mẫu, cụm phát triển ngày 17/11/2026 — chạy `nhan_webhook.py`, rồi ở cửa sổ khác `goi_loi.py` (tạo một
hồ sơ rồi đi bước "Hủy yêu cầu"):

```
Máy chủ nhận đang nghe cổng 8765
1. Token của tài khoản dịch vụ dx-integration: luồng client credentials, sống 300 giây
2. Đã đăng ký webhook 13 → http://host.docker.internal:8765/su-kien
3. Chuyển bước một hồ sơ trên cổng người dùng; sự kiện hiện dưới đây (Ctrl+C để dừng):
  sự kiện 3715 · hồ sơ 2843 (internal-requests) · cancel: submitted → cancelled · bởi dx-integration · 2026-11-16T17:12:04.208863+00:00
```

Lần thử trước đó (16/11) bên nhận hỏng giữa chừng không trả lời; lõi tự gửi lại ở lượt sau, bên nhận nhận ra
sự kiện trùng theo `X-DXOS-Event-Id` và trả 204.

## Viết ứng dụng của riêng mình

- Token: `POST {keycloak}/realms/{realm}/protocol/openid-connect/token` với `grant_type=client_credentials`,
  `client_id`, `client_secret`. Token sống 5 phút; hết thì xin lại
- Mọi lời gọi: `Authorization: Bearer <token>`, tới cổng API (`http://localhost:9080` ở cụm mặc định),
  đường bắt đầu bằng `/core/v1`. Danh sách điểm cuối ở `/docs` của cổng API, nhóm "Lõi — …"
- Lỗi nghiệp vụ trả `{"detail": {"code": …, "message": …}}`, câu tiếng Việt; vượt giới hạn tốc độ trả `429`
- Cần thêm vai: thêm vào `KEYCLOAK_INTEGRATION_ROLES` rồi chạy lại `scripts/tai_khoan_dich_vu.py` (kịch bản
  chỉ gán thêm, không gỡ vai nào). Mỗi ứng dụng thật nên có client riêng theo cùng khuôn, để thu hồi được
  từng ứng dụng một
