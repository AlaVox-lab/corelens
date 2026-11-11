# Giấy phép theo thư mục

DX-OS Lab dùng **mô hình nhiều giấy phép**: phần lớn kho theo MIT, riêng dịch vụ khai phá quy trình theo
GNU AGPL phiên bản 3 hoặc mới hơn. Cả hai đều thuộc danh sách giấy phép được
[OSI công nhận](https://opensource.org/licenses).

**Ngoại lệ của tệp `LICENSE` ở gốc kho:** tệp đó giữ nguyên văn bản MIT (để công cụ và GitHub nhận đúng
giấy phép), nhưng **không** áp cho thư mục `services/khai-pha/` — thư mục này theo AGPL-3.0-or-later, toàn
văn ở `services/khai-pha/LICENSE`.

| Thư mục | Nội dung | Giấy phép | Toàn văn |
|---|---|---|---|
| `backend/` | Dịch vụ ứng dụng (FastAPI) | MIT | [`LICENSE`](LICENSE) |
| `frontend/` | Cổng người dùng (Next.js) | MIT | [`LICENSE`](LICENSE) |
| `e2e/` | Kiểm thử giao diện | MIT | [`LICENSE`](LICENSE) |
| `scripts/` | Kịch bản tiện ích, kiểm header | MIT | [`LICENSE`](LICENSE) |
| `infra/` | Docker Compose, cấu hình nền tảng | MIT | [`LICENSE`](LICENSE) |
| `docs/`, `docs-site/` | Tài liệu, trang tài liệu | MIT | [`LICENSE`](LICENSE) |
| Tệp ở gốc kho và `.github/` | Quy tắc, cấu hình CI | MIT | [`LICENSE`](LICENSE) |
| **`services/khai-pha/`** | **Dịch vụ khai phá quy trình** — cả `app/`, `tests/`, `Dockerfile` | **AGPL-3.0-or-later** | [`services/khai-pha/LICENSE`](services/khai-pha/LICENSE) |

Mỗi tệp mã mang định danh SPDX của thư mục chứa nó ở đầu tệp (`SPDX-License-Identifier: MIT` hoặc
`SPDX-License-Identifier: AGPL-3.0-or-later`). Kịch bản [`scripts/kiem_header.py`](scripts/kiem_header.py)
chạy trên mỗi pull request và báo lỗi tệp thiếu header lẫn tệp mang giấy phép của thư mục khác.

## Vì sao dịch vụ khai phá theo AGPL

- Dịch vụ khai phá dùng thư viện [PM4Py](https://github.com/process-intelligence-solutions/pm4py)
  `2.7.23.8`, giấy phép AGPL-3.0-or-later ([ADR-0007](docs/adr/0007-chon-thu-vien-khai-pha-quy-trinh.md)).
  Mã của nhóm trong thư mục đó gọi thẳng thư viện, nên cả thư mục phát hành theo cùng giấy phép
- **Ranh giới là HTTP.** Dịch vụ khai phá chạy trong ảnh chứa riêng, chỉ nghe trong mạng của Compose. Dịch
  vụ ứng dụng gọi nó qua HTTP và nhận JSON; cổng chỉ nói chuyện với dịch vụ ứng dụng. Các phần MIT không
  liên kết, không nhập mã AGPL — chúng là tác phẩm riêng biệt đi cùng nhau (*aggregate*, điều 5 của AGPL),
  nên AGPL không lan sang
- **CI chặn vượt ranh giới**: bước *Ranh giới AGPL* trong [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
  báo lỗi khi có `import pm4py` ngoài `services/khai-pha/`, hay khi PM4Py được khai làm phụ thuộc của dịch
  vụ ứng dụng, cổng hoặc trang tài liệu
- Chiều MIT sang AGPL tương thích (danh sách giấy phép của GNU xếp MIT/Expat là *"compatible with the GNU
  GPL"*), nên mã MIT của kho dùng lại được trong dịch vụ khai phá. Chiều ngược lại thì không: **không chép
  mã từ `services/khai-pha/` sang thư mục MIT**

## Nghĩa vụ AGPL và cách dự án đáp ứng

| Nghĩa vụ | Cách đáp ứng |
|---|---|
| Kèm toàn văn giấy phép (điều 4) | [`services/khai-pha/LICENSE`](services/khai-pha/LICENSE) — văn bản GNU AGPL v3 nguyên văn |
| Giữ thông báo bản quyền và giấy phép (điều 4, 5) | Header SPDX và dòng bản quyền ở đầu mọi tệp mã của thư mục; thông báo bên thứ ba ở [`NOTICE`](NOTICE) |
| Cung cấp mã nguồn tương ứng khi phân phối (điều 6) | Kho mã công khai; ảnh chứa dựng từ chính thư mục này, phụ thuộc ghim phiên bản trong `services/khai-pha/requirements.txt` |
| **Người dùng tương tác qua mạng lấy được mã nguồn (điều 13)** | Màn *Báo cáo → Quy trình thực tế* của cổng — nơi người dùng thấy kết quả của dịch vụ khai phá — luôn có dòng *"Phân tích bởi dịch vụ khai phá quy trình, giấy phép AGPL-3.0 — mã nguồn"* dẫn tới mã nguồn của dịch vụ. Địa chỉ là biến `MINING_SOURCE_URL` của cổng (`infra/.env`), mặc định thư mục `services/khai-pha` trên kho GitHub của dự án |
| Không sửa mã thư viện | Dự án cài PM4Py từ PyPI, không chép, không sửa mã của nó |

**Bạn tự triển khai DX-OS Lab và sửa dịch vụ khai phá?** Phần sửa cũng theo AGPL-3.0-or-later: công khai
mã đã sửa và đặt `MINING_SOURCE_URL` trỏ về nơi chứa bản đó, để người dùng của bạn lấy được đúng mã đang
chạy. Bộ máy dự phòng không cần PM4Py ([`services/khai-pha/README.md`](services/khai-pha/README.md)) bỏ
được thư viện, nhưng mã của thư mục vẫn phát hành theo AGPL-3.0-or-later.

## Phụ thuộc bên thứ ba

Thông báo ngắn ở [`NOTICE`](NOTICE); danh sách đầy đủ kèm giấy phép từng gói ở
[`docs/dependencies.md`](docs/dependencies.md).
