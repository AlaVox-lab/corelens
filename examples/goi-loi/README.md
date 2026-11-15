# Gọi nền tảng lõi từ một ứng dụng khác

Ví dụ cho #365: một chương trình **không phải cổng người dùng** — đóng vai phần mềm nhân sự, ứng dụng di
động hay kịch bản tích hợp — tạo hồ sơ và đi một bước chuyển trạng thái **chỉ bằng API của nền tảng lõi**
`/core/v1`, qua cổng API. Ranh giới lõi và ứng dụng minh họa: `docs/ARCHITECTURE.md` mục 2.3.

`goi_loi.py` chỉ dùng thư viện chuẩn của Python 3.10 trở lên:

1. Xin token của tài khoản dịch vụ `dx-integration` bằng luồng **client credentials** của Keycloak
2. Rồi chỉ gọi cổng API dưới `/core/v1`: danh tính → danh mục loại yêu cầu → tạo hồ sơ → bước được phép →
   đi một bước → lịch sử

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

## Viết ứng dụng của riêng mình

- Token: `POST {keycloak}/realms/{realm}/protocol/openid-connect/token` với `grant_type=client_credentials`,
  `client_id`, `client_secret`. Token sống 5 phút; hết thì xin lại
- Mọi lời gọi: `Authorization: Bearer <token>`, tới cổng API (`http://localhost:9080` ở cụm mặc định),
  đường bắt đầu bằng `/core/v1`. Danh sách điểm cuối ở `/docs` của cổng API, nhóm "Lõi — …"
- Lỗi nghiệp vụ trả `{"detail": {"code": …, "message": …}}`, câu tiếng Việt; vượt giới hạn tốc độ trả `429`
- Cần thêm vai: thêm vào `KEYCLOAK_INTEGRATION_ROLES` rồi chạy lại `scripts/tai_khoan_dich_vu.py` (kịch bản
  chỉ gán thêm, không gỡ vai nào). Mỗi ứng dụng thật nên có client riêng theo cùng khuôn, để thu hồi được
  từng ứng dụng một
