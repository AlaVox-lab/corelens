# Dịch vụ khai phá quy trình

Dịch vụ riêng của không gian `I` (#314, [ADR-0007](../../docs/adr/0007-chon-thu-vien-khai-pha-quy-trinh.md)):
đọc nhật ký sự kiện bằng tài khoản cơ sở dữ liệu **chỉ đọc riêng**, trả đồ thị quy trình thực tế, nhánh
lệch, điểm nghẽn và biến thể dưới dạng JSON. Không ghi gì vào cơ sở dữ liệu, không ghi vào trường quyết
định nào của hồ sơ.

## Giấy phép

**Cả thư mục này theo AGPL-3.0-or-later** — khác phần còn lại của kho (MIT). Toàn văn ở
[`LICENSE`](LICENSE) cạnh tệp này; bảng giấy phép theo thư mục ở [`LICENSES.md`](../../LICENSES.md).

| Phần | Giấy phép |
|---|---|
| Mã của nhóm trong thư mục này (`app/`, `tests/`, `Dockerfile`) | AGPL-3.0-or-later — header `SPDX-License-Identifier: AGPL-3.0-or-later` |
| Thư viện [PM4Py](https://github.com/process-intelligence-solutions/pm4py) `2.7.23.8` | AGPL-3.0-or-later |

- **Chỉ thư mục này** cài và nhập `pm4py` — đúng một tệp: `app/bo_may/pm4py_bo_may.py`. Dịch vụ ứng
  dụng (`backend/`) và cổng (`frontend/`) không bao giờ nhập nó; chúng nhận JSON qua HTTP, nên AGPL không
  lan sang phần còn lại (tác phẩm riêng biệt gộp chung, điều 5 của AGPL). CI chặn nhập `pm4py` ở nơi khác
- **Điều 13**: người dùng thấy kết quả của dịch vụ này ở màn *Báo cáo → Quy trình thực tế*; chân màn luôn
  có dòng dẫn tới mã nguồn của thư mục này. Địa chỉ là biến `MINING_SOURCE_URL` của cổng (`infra/.env`).
  Tự triển khai mà sửa dịch vụ này thì công khai bản sửa và trỏ biến đó về nơi chứa nó
- Không sửa mã PM4Py, không chép mã thư viện vào kho. Không chép mã từ thư mục này sang thư mục MIT
- Danh sách phụ thuộc và giấy phép từng gói: [`docs/dependencies.md`](../../docs/dependencies.md); thông
  báo bên thứ ba: [`NOTICE`](../../NOTICE)

## Bộ máy dự phòng

Phần thuật toán đứng sau giao diện `BoMay` (`app/bo_may/`). Hai bộ máy cho cùng kết quả, cùng bị bài
kiểm thử có đáp án biết trước kiểm:

| `KHAI_PHA_BO_MAY` | Bộ máy |
|---|---|
| `pm4py` (mặc định) | PM4Py khám phá đồ thị trực tiếp và biến thể |
| `noi_bo` | Python thuần, không thư viện khai phá nào |

Muốn bỏ thư viện PM4Py thì đặt `KHAI_PHA_BO_MAY=noi_bo` và xóa dòng `pm4py` trong `requirements.txt` —
dịch vụ ứng dụng và cổng không phải sửa gì. Mã của thư mục này vẫn phát hành theo AGPL-3.0-or-later.

## Cấu hình

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `KHAI_PHA_DATABASE_URI` | — | Chuỗi kết nối của tài khoản chỉ đọc riêng (Compose dựng sẵn) |
| `KHAI_PHA_BO_MAY` | `pm4py` | Bộ máy khai phá |
| `KHAI_PHA_BOI_SO_NGHEN` | `2` | Trạng thái nghẽn khi chờ trung vị gấp từ chừng này lần trung vị chung |
| `KHAI_PHA_SO_BIEN_THE` | `10` | Số biến thể phổ biến nhất trả về |
| `KHAI_PHA_SO_HO_SO_MOI_NHOM` | `200` | Số mã hồ sơ tối đa kèm mỗi nhánh lệch, mỗi biến thể |

Dịch vụ chỉ nghe trong mạng của Compose, không mở cổng ra máy. Người gọi duy nhất là dịch vụ ứng dụng
(`GET /analytics/process-mining`), nơi kiểm vai trò và gắn phạm vi phòng. Khuôn đầy đủ:
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) mục 6.4.
