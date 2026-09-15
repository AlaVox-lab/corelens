# dependencies.md

> **Mục đích**: danh mục toàn bộ phụ thuộc của dự án kèm giấy phép và kết quả kiểm
> tra tương thích.
>
> Tệp này phục vụ trực tiếp tiêu chí PoF mục 5 về quản lý thư viện và gói đính kèm
> (10 điểm), và mục 2 về cấp phép (10 điểm).
>
> **Bắt buộc cập nhật ngay** khi thêm bất kỳ phụ thuộc mới nào, trong cùng công việc
> đó, không để lại sau.

---

## Quy trình bắt buộc trước khi thêm phụ thuộc

1. Tra tên giấy phép của dự án đó trên trang chính thức của họ
2. Đối chiếu với danh sách được công nhận tại `https://opensource.org/licenses`
3. Kiểm tra tương thích với giấy phép MIT của sản phẩm
4. Ghi kết quả vào bảng tương ứng bên dưới
5. Nếu là nền tảng lớn (không phải thư viện nhỏ), tạo thêm một bản ghi quyết định
   trong `docs/adr/`

**Không thêm phụ thuộc mà bỏ qua bước kiểm tra.** Một giấy phép sai có thể khiến
toàn bộ dự án không được chấm điểm.

---

## Cảnh báo: giấy phép KHÔNG được OSI công nhận

Nhiều nền tảng tự nhận là nguồn mở nhưng dùng giấy phép không nằm trong danh sách
OSI. Dùng chúng khiến dự án **không đủ điều kiện chấm điểm** theo thể lệ.

Các dạng cần cảnh giác:

| Giấy phép | Vấn đề |
|---|---|
| Business Source License (BSL) | Hạn chế thương mại có thời hạn, không thuộc OSI |
| Server Side Public License (SSPL) | Bị OSI từ chối công nhận |
| Elastic License | Không thuộc OSI |
| Commons Clause | Điều khoản bổ sung làm mất tính nguồn mở |
| fair-code | Không phải giấy phép chuẩn, không thuộc OSI |

Một số nền tảng phổ biến trong mảng tự động hóa luồng công việc và quản trị tri thức
rơi vào nhóm này. Luôn kiểm tra trước khi đánh giá tính năng.

---

## Lưu ý về giấy phép copyleft mạnh

GPL, AGPL đều **được OSI công nhận** nên hợp lệ về mặt thể lệ. Nhưng bảng chấm trừ
5 điểm nếu *"mã nguồn tự thân chứa sự không tương thích của các giấy phép"*.

Nếu buộc phải dùng một nền tảng copyleft mạnh:

- Triển khai như **dịch vụ độc lập**, giao tiếp qua HTTP hoặc giao thức mạng
- **Không** nhúng thư viện của nó vào mã nguồn dự án
- Ghi rõ ranh giới kiến trúc này vào `ARCHITECTURE.md` và bản ghi quyết định tương ứng

### Các trường hợp đang áp dụng

| Thành phần | Giấy phép | Ranh giới đang giữ |
|---|---|---|
| **psycopg2-binary** | LGPL kèm ngoại lệ | Chỉ cài vào **ảnh chứa của Superset**, không nằm trong mã nguồn dự án. LGPL nhẹ hơn GPL: dùng như thư viện nạp động thì không lan giấy phép sang phần mềm gọi nó. Ràng buộc phải giữ: **không sửa mã thư viện**, và người dùng phải thay thế được nó |
| **psycopg 3** | LGPL-3.0-only | Trình điều khiển PostgreSQL của **dịch vụ ứng dụng**. Đây là phụ thuộc copyleft đầu tiên nằm trong mã nguồn của chính nhóm, nên ranh giới phải nói rõ: dự án chỉ `import` nó như thư viện, không sao chép mã, không sửa mã. LGPL cho phép đúng cách dùng này. Người dùng thay thế được bằng cách sửa một dòng trong `backend/requirements.txt` và một tiền tố trong chuỗi kết nối — hai bản lùi permissive là `pg8000` (BSD-3-Clause) và `asyncpg` (Apache-2.0) |
| **sharp** và `@img/sharp-libvips-*` | Apache-2.0 (sharp) · LGPL-3.0-or-later (libvips) | Phụ thuộc **tùy chọn** mà Next.js kéo theo để tối ưu ảnh. Thư viện gốc `libvips` là nhị phân dựng sẵn, nạp động, thay thế được — đúng điều kiện LGPL cho phép. Cổng người dùng hiện **không dùng ảnh nào**; nếu muốn loại bỏ hẳn thì đặt `images: { unoptimized: true }` trong `next.config.ts` |
| **Metabase** *(đã loại)* | AGPL-3.0 | Không dùng — xem ADR-0003 |
| **Garage**, **MinIO** *(phương án lùi)* | AGPL-3.0 | Nếu phải dùng thì chỉ chạy như dịch vụ độc lập qua S3 API — xem ADR-0002 |

### Một gói không mang giấy phép phần mềm

`caniuse-lite` mang giấy phép **CC-BY-4.0** — giấy phép nội dung, không nằm trong danh
sách OSI vì nó không phải giấy phép phần mềm. Đây **không phải vi phạm**:

- Nội dung của nó là **bảng dữ liệu** về khả năng tương thích trình duyệt, không phải mã
- Nó chỉ tham gia **lúc biên dịch**, không đi vào kết quả dựng, nên không được phát hành
  kèm sản phẩm
- CC-BY-4.0 chỉ đòi ghi công, và tệp giấy phép của nó nằm nguyên trong gói

Ghi lại ở đây để nếu ban giám khảo tra `package-lock.json` thì đã có sẵn câu trả lời.

---

## Phụ thuộc hạ tầng

| Thành phần | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| Docker Engine | 24+ | Apache-2.0 | Có | Có | Đóng gói và dựng hệ thống |
| Docker Compose | v2 | Apache-2.0 | Có | Có | Dựng toàn hệ thống bằng một lệnh |
| PostgreSQL | `16-alpine` | PostgreSQL License | Có | Có | Một thực thể, ba database: `dxlab`, `keycloak`, `superset` |
| Python *(ảnh nền)* | `3.13-slim` | Python-2.0 | Có | Có | Ảnh nền của dịch vụ ứng dụng — `backend/Dockerfile` |
| Node.js *(ảnh nền)* | `24-alpine` | MIT | Có | Có | Ảnh nền của cổng người dùng — `frontend/Dockerfile` |
| psycopg2-binary | `2.9.13` | LGPL kèm ngoại lệ | Có | Có, **có điều kiện** | Trình điều khiển PostgreSQL. Cài vào **ảnh dẫn xuất của Superset** vì ảnh gốc không kèm sẵn — xem `infra/superset/Dockerfile`. Không nhúng vào mã nguồn dự án, không sửa mã thư viện. Chi tiết ràng buộc ở mục Lưu ý về giấy phép copyleft |

---

## Phụ thuộc giao diện

Khai báo trong `frontend/package.json`, ghim chính xác trong `frontend/package-lock.json`.
**Tệp khóa bắt buộc commit.**

| Gói | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| next | `16.3.5` | MIT | Có | Có | Khung ứng dụng. Dựng ở chế độ `standalone` để ảnh chứa không phải mang cả `node_modules` |
| react | `19.3.0` | MIT | Có | Có | |
| react-dom | `19.3.0` | MIT | Có | Có | |
| typescript | `5.9.3` | Apache-2.0 | Có | Có | Giữ ở nhánh 5.x. Bản 7 là bản viết lại bằng Go, mới ra và chưa rõ Next 16 đã theo kịp — chưa đáng mạo hiểm |
| @types/node · @types/react · @types/react-dom | `26.5.1` · `19.3.0` · `19.3.0` | MIT | Có | Có | Chỉ là khai báo kiểu, không đi vào kết quả dựng |

Toàn bộ cây phụ thuộc có **61 gói**. Đã rà giấy phép từng gói bằng siêu dữ liệu trong
tệp khóa, không dựa vào trí nhớ: 24 MIT, 17 Apache-2.0, 14 gói `sharp`/`libvips` mang
LGPL, 2 ISC, 1 BSD-3-Clause, 1 0BSD, 1 CC-BY-4.0. Hai nhóm cuối đã giải thích ở mục
Lưu ý về giấy phép copyleft.

---

## Phụ thuộc dịch vụ ứng dụng

Khai báo và ghim trong `backend/requirements.txt` bằng `==`. **Tệp này là tệp khóa
phiên bản, bắt buộc commit.**

| Gói | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| fastapi | `0.141.1` | MIT | Có | Có | Khung dịch vụ web |
| uvicorn[standard] | `0.53.0` | BSD-3-Clause | Có | Có | Máy chủ ASGI |
| sqlalchemy | `2.0.53` | MIT | Có | Có | Truy cập cơ sở dữ liệu |
| alembic | `1.20.0` | MIT | Có | Có | Migration. Được cấu hình **bỏ qua mười một bảng** do lược đồ khởi tạo sở hữu — xem `backend/alembic/env.py` |
| psycopg[binary] | `3.3.5` | **LGPL-3.0-only** | Có | Có, **có điều kiện** | Trình điều khiển PostgreSQL. Phụ thuộc copyleft duy nhất trong mã nguồn của nhóm — ranh giới ghi ở mục Lưu ý về giấy phép copyleft |
| pydantic-settings | `2.15.0` | MIT | Có | Có | Đọc cấu hình từ biến môi trường |

Phụ thuộc gián tiếp đáng kể: `pydantic` (MIT), `starlette` (BSD-3-Clause).

---

## Nền tảng Open-Core

Các nền tảng lớn được tích hợp theo yêu cầu kiến trúc Open-Core của đề bài. Mỗi mục
phải có một bản ghi quyết định tương ứng trong `docs/adr/`.

| Không gian | Nền tảng | Giấy phép | OSI công nhận | Cách tích hợp | Bản ghi quyết định |
|---|---|---|---|---|---|
| `H` | Keycloak `26.7.3` | Apache-2.0 | Có | Dịch vụ độc lập, giao tiếp qua OIDC. Không nhúng thư viện, không sửa mã nền tảng | [ADR-0001](adr/0001-chon-nen-tang-sso.md) |
| `H` | *Chờ khảo sát* — hệ thống quản trị tri thức | | | | |
| `P` | **Không dùng nền tảng ngoài** — engine máy trạng thái do nhóm tự viết | MIT (mã của dự án) | — | Không tích hợp. Trạng thái và quy tắc chuyển lưu trong bảng PostgreSQL | [ADR-0004](adr/0004-tu-viet-engine-may-trang-thai.md) |
| `D` | Apache Superset `6.1.0` | Apache-2.0 | Có | Dịch vụ độc lập, chỉ đọc CSDL nghiệp vụ, nhúng vào cổng qua guest token. Cần ảnh dẫn xuất bổ sung trình điều khiển PostgreSQL | [ADR-0003](adr/0003-chon-nen-tang-bi.md) |
| `I` | *Chờ khảo sát* | | | | |
| `I` | *Chờ khảo sát* | | | | |
| `core` | SeaweedFS `4.45` | Apache-2.0 | Có | Dịch vụ độc lập, giao tiếp qua S3 API chuẩn. Không nhúng thư viện, không dùng API riêng của nền tảng | [ADR-0002](adr/0002-chon-nen-tang-luu-tru-doi-tuong.md) |

Cột **Cách tích hợp** ghi rõ: nhúng thư viện, hay chạy như dịch vụ độc lập giao tiếp
qua mạng. Với nền tảng copyleft mạnh, bắt buộc phải là phương án thứ hai.

---

## Công cụ phát triển

Không phải phụ thuộc của sản phẩm, nhưng ghi lại để minh bạch chuỗi công cụ.

| Công cụ | Giấy phép | Vai trò | Có trong chuỗi dựng không |
|---|---|---|---|
| git-cliff | MIT hoặc Apache-2.0 | Sinh nhật ký thay đổi | Không |
| GitHub CLI | MIT | Khởi tạo hệ thống nhãn | Không |
| Visual Studio Code | MIT (bản mã nguồn) | Trình soạn thảo | Không |

**Lưu ý về bảng chấm**: mục PoF số 4 trừ 5 điểm nếu *"mã nguồn được dịch bằng công
cụ nguồn đóng hoặc tự tạo"*. Các công cụ ở bảng trên đều không tham gia vào chuỗi
dựng sản phẩm, nên không thuộc phạm vi bị trừ. Nếu về sau đưa một công cụ nào vào
chuỗi dựng, phải kiểm tra lại điều kiện này.

---

## Quy tắc không được vi phạm

| Quy tắc | Lý do |
|---|---|
| Không sao chép mã thư viện vào kho mã | Bảng chấm trừ 5 điểm cho *"phát hành cùng với gói đính kèm của các dự án khác"* |
| Không chỉnh sửa mã thư viện bên thứ ba | Trừ 5 điểm cho *"mã nguồn của gói đính kèm đã bị chỉnh sửa"*. Cần đổi hành vi thì dùng cấu hình, plugin, hoặc lớp bọc |
| Ưu tiên thư viện có sẵn của hệ thống | Trừ 5 điểm cho *"không cố gắng sử dụng các thư viện sẵn có trong hệ thống"* |
| Tệp khóa phiên bản bắt buộc commit | Không có tệp khóa thì mỗi người và ban giám khảo nhận bộ phiên bản khác nhau, hỏng khả năng dựng lại từ mã nguồn |

---

## Ghi chú

Thông tin giấy phép của các dự án nguồn mở **có thể thay đổi theo thời gian**. Đã có
tiền lệ các dự án lớn chuyển từ giấy phép OSI sang giấy phép hạn chế hơn.

Vì vậy, ngoài việc kiểm tra tại thời điểm thêm phụ thuộc, cần **rà soát lại toàn bộ
bảng này trước khi nộp bài** vào tháng 12.
