---
title: Tài khoản mẫu
description: Mười ba tài khoản có sẵn trong realm mẫu, vai trò và phòng ban của từng người.
sidebar:
  order: 1
---

Realm `dx-os-lab` tự nạp lúc khởi động: năm vai trò, bốn phòng ban, mười ba tài khoản. Mọi tài
khoản dùng mật khẩu **`matkhau123`**. Bấm **Đăng nhập bằng tài khoản công ty** trên trang chủ cổng.

| Tài khoản | Vai trên giao diện | Phòng ban |
|---|---|---|
| `an.nguyen` | Người gửi | — |
| `binh.tran` | Điều phối viên (cũng gửi được yêu cầu) | — |
| `dung.pham` | Trưởng phòng | Công nghệ thông tin |
| `cuong.le` | Người xử lý | Công nghệ thông tin |
| `lan.vu` | Người xử lý — nhận vai qua nhóm | Công nghệ thông tin |
| `tuan.ngo` | Người xử lý — **đã khóa**, đóng vai người nghỉ việc | Công nghệ thông tin |
| `giang.hoang` | Trưởng phòng | Nhân sự |
| `ha.do` | Người xử lý | Nhân sự |
| `minh.dang` | Trưởng phòng | Hành chính |
| `nam.bui` | Người xử lý | Hành chính |
| `phuong.ly` | Trưởng phòng | Tài chính kế toán |
| `quang.trinh` | Người xử lý | Tài chính kế toán |
| `khanh.vo` | Quản trị viên — xem màn Hệ thống | — |

Số điện thoại mẫu là số giả `0900 000 001` tới `013`. Mỗi người tự sửa số của mình ở trang tài
khoản `http://localhost:8080/realms/dx-os-lab/account`.

Mỗi phòng có ít nhất một trưởng phòng và một người xử lý, nên hồ sơ chuyển về phòng nào cũng có
người nhận. Thêm phòng ban hay đổi vai trò là sửa `infra/keycloak/realm-dx-os-lab.json` — xem
[Danh mục và các con số](../../quan-tri/danh-muc-va-con-so/).

:::tip
Thử nhiều vai cùng lúc: mỗi tài khoản một cửa sổ ẩn danh hoặc một hồ sơ trình duyệt riêng.
:::
