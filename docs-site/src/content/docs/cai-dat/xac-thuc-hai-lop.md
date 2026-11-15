---
title: Xác thực hai lớp
description: Bật hay tắt mã dùng một lần (TOTP) khi đăng nhập cho mọi tài khoản công ty, chỉ bằng cấu hình Keycloak.
sidebar:
  order: 2.5
---

Xác thực hai lớp buộc người dùng, sau mật khẩu, nhập thêm **mã dùng một lần** sáu chữ số do ứng dụng xác
thực trên điện thoại sinh ra (Google Authenticator, Microsoft Authenticator, FreeOTP…), đổi mỗi 30 giây. Lộ
mật khẩu thôi thì chưa vào được tài khoản.

Cụm mặc định **tắt** — cụm trình diễn đăng nhập bằng mật khẩu như cũ. Người cài bật cho mọi tài khoản của realm
`dx-os-lab` bằng một lệnh, và tắt lại được.

## Cách làm

Không có mã nào của dự án hay của Keycloak bị sửa, không dựng ảnh riêng. Kịch bản
`scripts/xac_thuc_hai_lop.py` chỉ đổi cấu hình qua API quản trị của Keycloak, dùng hai thứ có sẵn của nền tảng:

| Thứ có sẵn | Vai trò |
|---|---|
| Hành động bắt buộc *Configure OTP* (`CONFIGURE_TOTP`) | Buộc tài khoản thiết lập mã ở lần đăng nhập kế. `bat` đặt nó thành mặc định cho tài khoản mới và gán cho mọi tài khoản hiện có chưa có mã |
| Luồng đăng nhập trình duyệt mặc định (`browser`) | Đã có sẵn bước *OTP Form*: tài khoản nào có mã thì bị hỏi mã sau mật khẩu. Kịch bản không đổi luồng này, chỉ kiểm nó còn bật |

Vì sao không sửa `infra/keycloak/realm-dx-os-lab.json`: Keycloak chỉ nạp tệp realm **lúc tạo realm**, nên cụm
đã chạy không bao giờ thấy thay đổi trong tệp. API quản trị chạy được cho cả cụm mới lẫn cụm đã có dữ liệu.

Mọi tài khoản đăng nhập qua Keycloak đều chịu chung một luật: cổng, và kho tri thức nếu đã bật (đăng nhập một
lần qua cùng phiên Keycloak). Tài khoản quản trị Keycloak (`admin`, realm `master`) không bị ảnh hưởng.

## Bật

Ở gốc kho mã, khi cụm đang chạy (cần Python 3.10 trở lên, không cần cài gói nào):

```bash
python scripts/xac_thuc_hai_lop.py bat
```

```text
Đã đặt: tài khoản mới phải thiết lập mã ở lần đăng nhập đầu.
Gán thiết lập mã cho 13 tài khoản chưa có mã (an.nguyen, binh.tran, cuong.le, …).
Giữ nguyên 0 tài khoản đã có mã, 0 tài khoản đã chờ thiết lập từ trước.
Xong. Lần đăng nhập kế, người dùng quét mã QR bằng ứng dụng xác thực (FreeOTP, Google Authenticator…).
```

Phiên đang mở không bị cắt; luật áp dụng từ lần đăng nhập kế. Lệnh chạy lại bao nhiêu lần cũng được: tài khoản
đã có mã hay đã chờ thiết lập thì để yên. Nếu luồng đăng nhập trình duyệt của realm đã bị ai đó tắt bước hỏi mã,
lệnh dừng và không đổi gì — bật lúc ấy sẽ bắt người dùng thiết lập mã mà không bao giờ hỏi mã.

## Người dùng thấy gì

**Lần đăng nhập đầu sau khi bật**: sau mật khẩu là màn *Thiết lập xác thực hai lớp* có mã QR. Người dùng quét
bằng ứng dụng xác thực, nhập mã sáu chữ số ứng dụng hiện ra, đặt tên thiết bị nếu muốn, nhấn **Gửi** rồi vào cổng
như thường. Không quét được thì nhấn *Không quét được mã QR?* để hiện khóa dạng chữ và các thông số (loại, thuật
toán, số chữ số, chu kỳ) để nhập tay.

**Những lần sau**: sau mật khẩu là màn nhập *Mã một lần*. Mã sai thì báo *Mã xác thực không hợp lệ.* và cho
nhập lại. Một mã chỉ dùng được một lần — vừa dùng để thiết lập thì chờ mã kế tiếp.

Các màn này dùng chủ đề đăng nhập của dự án (`infra/keycloak/themes/dx-os-lab/`), tiếng Việt. Chữ lấy từ bản
dịch đi kèm Keycloak; vài chuỗi được thay cho khớp tên gọi ở trang này, trong
`login/messages/messages_vi.properties` của chủ đề.

**Mất điện thoại**: quản trị viên mở trang quản trị Keycloak (`http://localhost:8080`, realm `dx-os-lab`; trang
quản trị hiện tiếng Anh) → *Users* → chọn tài khoản → thẻ *Credentials* → xóa dòng loại `otp`. Rồi chạy lại `bat`
(hoặc chọn *Configure OTP* ở ô *Required user actions* của thẻ *Details*) để lần đăng nhập kế người dùng thiết lập
mã trên máy mới. Không làm bước này thì tài khoản đó đăng nhập chỉ bằng mật khẩu.

## Xem trạng thái

```bash
python scripts/xac_thuc_hai_lop.py trang-thai
```

```text
Realm dx-os-lab tại http://localhost:8080
Xác thực hai lớp: BẬT
  Hành động bắt buộc CONFIGURE_TOTP ("Configure OTP"): đang bật, mặc định cho tài khoản mới: có
  Luồng đăng nhập trình duyệt "browser": hỏi mã với tài khoản đã có mã (bước auth-otp-form: ALTERNATIVE)
  Chính sách mã: TOTP, HmacSHA1, 6 chữ số, đổi mỗi 30 giây
Tài khoản (13):
  đã thiết lập mã:                    0
  phải thiết lập ở lần đăng nhập kế:  13
  chưa có mã, không bị buộc:          0
```

| Dòng tổng | Nghĩa |
|---|---|
| `BẬT` | Tài khoản mới phải thiết lập mã, mọi tài khoản hiện có đã có mã hoặc đang chờ thiết lập |
| `TẮT` | Không ai bị buộc, không ai còn mã |
| `TẮT (một số tài khoản vẫn giữ mã …)` | Không ai bị buộc nữa, nhưng ai đã thiết lập mã vẫn bị hỏi mã — xem mục Tắt |
| `LỆCH` | Nửa bật nửa tắt, thường do ai đó đổi tay trong trang quản trị. Chạy lại `bat` hoặc `tat` |

Tài khoản dịch vụ của client (đăng nhập bằng bí mật client, không qua trình duyệt) không được đếm và không bị đụng.

## Tắt

```bash
python scripts/xac_thuc_hai_lop.py tat
```

Bỏ mặc định với tài khoản mới, gỡ yêu cầu thiết lập mã còn treo ở mọi tài khoản chưa kịp thiết lập (kể cả yêu cầu
quản trị viên gán tay). Tài khoản **đã thiết lập mã thì vẫn bị hỏi mã** — mã là thông tin xác thực của chính người
dùng, kịch bản không tự xóa. Muốn xóa luôn, để mọi người đăng nhập lại chỉ bằng mật khẩu:

```bash
python scripts/xac_thuc_hai_lop.py tat --xoa-ma
```

Hoặc để từng người tự gỡ mã của mình ở trang tài khoản Keycloak
(`http://localhost:8080/realms/dx-os-lab/account`), phần bảo mật đăng nhập. Sau `tat --xoa-ma`, `trang-thai` báo
`TẮT` và cụm trở lại đúng như lúc mới dựng.

## Tham số

Kịch bản đọc địa chỉ và tài khoản quản trị từ tệp env của cụm, mặc định `infra/.env`: `KEYCLOAK_PORT` (Keycloak ở
`http://localhost:<cổng>`), `KEYCLOAK_REALM`, `KEYCLOAK_ADMIN_USER`, `KEYCLOAK_ADMIN_PASSWORD`. Biến môi trường
cùng tên ghi đè tệp; tham số ghi đè cả hai:

| Tham số | Dùng khi |
|---|---|
| `--env-file đường/dẫn/.env` | Cụm dựng từ tệp env khác |
| `--keycloak http://máy:cổng` | Keycloak không ở `localhost` (hoặc đặt biến `KEYCLOAK_URL`) |
| `--realm tên` | Realm khác `KEYCLOAK_REALM` |

Chính sách mã (thuật toán, số chữ số, chu kỳ) là mặc định của Keycloak, đổi ở trang quản trị → *Authentication* →
thẻ *Policies* → *OTP Policy*. Đổi **trước** khi người dùng thiết lập: mã đã quét theo chính sách cũ sẽ không còn khớp.

## Kiểm thử

Kịch bản giao diện `e2e/kiem/xac-thuc-hai-lop.spec.ts` đăng nhập thật qua trình duyệt: tạo một tài khoản thử qua API
quản trị (mượn vai trò của tài khoản người gửi mẫu), thiết lập mã từ khóa hiện trên màn *Không quét được mã QR?*,
thử mã sai, đăng nhập lại bằng mã tính theo RFC 6238, rồi xóa tài khoản thử. Lượt kiểm mặc định bỏ qua bài này;
chạy sau khi `bat`, trong `e2e/`:

```bash
HAI_LOP=1 KEYCLOAK=http://localhost:8080 npx playwright test --project=hai-lop
```

Khi bật, mười ba tài khoản mẫu cũng phải thiết lập mã nên bước chuẩn bị của các bài khác không đăng nhập được —
`tat` trước khi chạy trọn bộ.
