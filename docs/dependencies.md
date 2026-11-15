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
- **Không** nhúng thư viện của nó vào dịch vụ ứng dụng hay cổng. Thư viện copyleft mạnh chỉ được
  `import` bên trong **một dịch vụ tách riêng** (thư mục, ảnh chứa riêng, giao tiếp HTTP) — trường hợp
  duy nhất hiện nay là PM4Py trong `services/khai-pha/` (ADR-0007); CI chặn `import pm4py` ở nơi khác
- Ghi rõ ranh giới kiến trúc này vào `ARCHITECTURE.md` và bản ghi quyết định tương ứng

### Các trường hợp đang áp dụng

| Thành phần | Giấy phép | Ranh giới đang giữ |
|---|---|---|
| **psycopg2-binary** | LGPL kèm ngoại lệ | Chỉ cài vào **ảnh chứa của Superset**, không nằm trong mã nguồn dự án. LGPL nhẹ hơn GPL: dùng như thư viện nạp động thì không lan giấy phép sang phần mềm gọi nó. Ràng buộc phải giữ: **không sửa mã thư viện**, và người dùng phải thay thế được nó |
| **psycopg 3** | LGPL-3.0-only | Trình điều khiển PostgreSQL của **dịch vụ ứng dụng**. Đây là phụ thuộc copyleft đầu tiên nằm trong mã nguồn của chính nhóm, nên ranh giới phải nói rõ: dự án chỉ `import` nó như thư viện, không sao chép mã, không sửa mã. LGPL cho phép đúng cách dùng này. Người dùng thay thế được bằng cách sửa một dòng trong `backend/requirements.txt` và một tiền tố trong chuỗi kết nối — hai bản lùi permissive là `pg8000` (BSD-3-Clause) và `asyncpg` (Apache-2.0) |
| **sharp** và `@img/sharp-libvips-*` | Apache-2.0 (sharp) · LGPL-3.0-or-later (libvips) | Phụ thuộc **tùy chọn** mà Next.js kéo theo để tối ưu ảnh. Thư viện gốc `libvips` là nhị phân dựng sẵn, nạp động, thay thế được — đúng điều kiện LGPL cho phép. Cổng người dùng hiện **không dùng ảnh nào**; nếu muốn loại bỏ hẳn thì đặt `images: { unoptimized: true }` trong `next.config.ts` |
| **lightningcss** | MPL-2.0 | Công cụ xử lý CSS mà Astro dùng **lúc dựng** trang tài liệu. MPL-2.0 là copyleft theo từng tệp: chỉ ràng buộc khi sửa chính tệp của thư viện. Dự án dùng qua trình quản lý gói, không sửa, không chép mã; kết quả dựng là CSS do dự án viết |
| **PM4Py** | AGPL-3.0-or-later — dòng đầu `LICENSE` trong gói đã cài: `GNU AFFERO GENERAL PUBLIC LICENSE` | Chỉ cài trong ảnh của **dịch vụ khai phá** `services/khai-pha/`, chỉ một tệp `import` (`app/bo_may/pm4py_bo_may.py`). Dịch vụ ứng dụng và cổng nhận JSON qua HTTP — tác phẩm riêng biệt gộp chung, AGPL không lan sang. Cả thư mục dịch vụ, kể cả mã của nhóm, theo AGPL-3.0-or-later (toàn văn `services/khai-pha/LICENSE`, bảng theo thư mục ở `LICENSES.md`); màn Quy trình thực tế dẫn tới mã nguồn của dịch vụ để đáp ứng điều 13. Không sửa, không chép mã thư viện. Có bộ máy dự phòng Python thuần: `MINING_ENGINE=noi_bo` rồi xóa dòng pm4py — xem ADR-0007 |
| **cvxopt** | GPL-3.0-or-later — `LICENSE` trong gói đã cài: *"GNU General Public License … either version 3"* | Phụ thuộc gián tiếp **bắt buộc** của PM4Py, cùng nằm sau ranh giới dịch vụ khai phá. GPL-3.0 và AGPL-3.0 kết hợp được (điều 13 của cả hai). Dự án không gọi trực tiếp; gỡ PM4Py thì gỡ luôn |
| **Wiki.js** | AGPL-3.0 — `/wiki/LICENSE` trong ảnh: `GNU AFFERO GENERAL PUBLIC LICENSE` | Kho tri thức **tùy chọn** (hồ sơ `tri-thuc`, #321). Chạy nguyên ảnh chính thức như dịch vụ độc lập; bước khởi tạo `infra/tri-thuc/khoi_tao.py` (MIT) và dịch vụ ứng dụng chỉ nói chuyện qua HTTP/GraphQL và OIDC — không nhập, không dẫn xuất mã, nên không thư mục nào của kho mang AGPL. Không sửa mã nên mã nguồn tương ứng (điều 13) là bản thượng nguồn; cổng vẫn dẫn tới đó cạnh lối vào kho tri thức (`LICENSES.md`) |
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
| PostgreSQL kèm pgvector *(ảnh)* | `pgvector/pgvector:0.8.6-pg16@sha256:ccc6e83d…4d6b` — PostgreSQL 16.15, pgvector 0.8.6, Debian bookworm | PostgreSQL License (cả PostgreSQL lẫn pgvector) | Có | Có | Một thực thể, ba database: `dxlab`, `keycloak`, `superset`. Thay `postgres:16-alpine` từ #319 (ADR-0008) để có phần mở rộng `vector`: cùng PostgreSQL 16 nên thư mục dữ liệu cũ dùng tiếp, migration `0022` REINDEX một lần vì musl → glibc đổi thứ tự sắp chữ. Ảnh chính thức của dự án pgvector, dựng 2026-08-13 — chọn 0.8.6 thay 0.8.7 vì ảnh 0.8.7 mới dựng lại chưa đủ hai tuần (quyết định ngày 11/11/2026). `/usr/share/doc/pgvector/LICENSE` trong ảnh mở đầu *Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group* — kiểu PostgreSQL License. Phần mở rộng chạy trong PostgreSQL, bật bằng `CREATE EXTENSION`; dịch vụ ứng dụng chỉ gửi câu SQL, không thêm gói Python nào |
| Apache APISIX *(ảnh)* | `apache/apisix:3.20.0-debian@sha256:013de62a…e759a` (dựng 2026-11-13) | Apache-2.0 | Có | Có | Dịch vụ `cong-api` ở **cụm mặc định** (#364, ADR-0010): cổng API trước dịch vụ ứng dụng. Dòng đầu `LICENSE` của kho `apache/apisix`: `Apache License Version 2.0, January 2004`. Ảnh chính thức nguyên bản, không dựng lại; hai tệp cấu hình trong `infra/cong-api/` (MIT) gắn chỉ đọc. Một tiến trình làm việc (`worker_processes: 1`) — để mặc định thì sinh một tiến trình mỗi nhân máy. Chỉ nạp ba plugin có sẵn trong ảnh, không thêm plugin bên ngoài. **Lưu ý:** ảnh mới dựng hai ngày khi ADR-0010 chốt (15/11/2026), chưa đủ hai tuần như thói quen chọn bản của kho (pgvector, ClamAV); ADR-0010 chọn bản này vì đó là bản đã đo thật ở bản khảo sát |
| Python *(ảnh nền)* | `python:3.13.17-slim@sha256:d98cc29d…2962` (Debian trixie, thẻ đẩy 2026-10-24) | Python-2.0 | Có | Có | Ảnh nền của dịch vụ ứng dụng (`backend/Dockerfile`) và dịch vụ khai phá (`services/khai-pha/Dockerfile`) |
| Node.js *(ảnh nền)* | `node:24.22.1-alpine@sha256:06d7adf3…8b53` (thẻ đẩy 2026-10-22) | MIT | Có | Có | Ảnh nền của cổng người dùng — `frontend/Dockerfile`, cùng một ảnh cho cả ba tầng. Ghim thẻ cụ thể kèm mã băm thay `24-alpine` trôi (11/11/2026): thẻ trôi từng làm `next build` hỏng chập chờn ở bước nạp `@next/swc-linux-x64-*` |
| llama.cpp server *(ảnh)* | `ghcr.io/ggml-org/llama.cpp:server-b11889@sha256:5741ab30…b0c` | MIT | Có | Có | Dịch vụ `mo-hinh`, **tùy chọn** (hồ sơ Compose `tri-tue`, #316, ADR-0008). Thẻ ghim cụ thể, phát hành 2026-10-25 (bản dựng `org.opencontainers.image.revision` `d854d98`). Dòng đầu `LICENSE` ở thẻ `b11889` của kho `ggml-org/llama.cpp`: `MIT License` — `Copyright (c) 2023-2026 The ggml authors`. Chạy như dịch vụ độc lập, gọi qua HTTP kiểu OpenAI; không nhúng, không sửa |
| ClamAV *(ảnh)* | `clamav/clamav:1.5.3@sha256:d06c1d6a…87bb` (thẻ đẩy 2026-08-03) | GPL-2.0 | Có | Có — **chỉ vì ranh giới mạng** | Dịch vụ `quet-tep`, **tùy chọn** (hồ sơ Compose `quet-tep`, #248): quét mã độc tệp đính kèm. `COPYING.txt` của kho `Cisco-Talos/clamav`: `GNU GENERAL PUBLIC LICENSE Version 2`. Chạy như dịch vụ độc lập; dịch vụ ứng dụng gửi tệp qua giao thức mạng clamd (`INSTREAM`) viết bằng thư viện chuẩn Python — không nhúng, không liên kết `libclamav`, không thêm gói Python nào (`LICENSES.md`). Chọn `1.5.3` thay `1.5.4` vì thẻ `1.5.x` mới nhất được đẩy 2026-11-09, chưa đủ hai tuần. Bộ mẫu nhận diện kèm trong ảnh do Cisco Talos phát hành, không phát hành lại |
| Mailpit *(ảnh)* | `axllent/mailpit:v1.32.0@sha256:0790692b…0498` (thẻ đẩy 2026-10-22) | MIT | Có | Có | Dịch vụ `thu-thu`, **tùy chọn** (hồ sơ Compose `thu-thu`, #251): hộp thư thử nhận thư thông báo qua SMTP để trình diễn. `LICENSE` của kho `axllent/mailpit`: `The MIT License (MIT)` — `Copyright (c) 2022-Now() Ralph Slooten`. Dịch vụ ứng dụng gửi thư bằng `smtplib` của thư viện chuẩn |
| Wiki.js *(ảnh)* | `requarks/wiki:2.5.315@sha256:af71a17d…638c` (dựng 2026-09-21) | AGPL-3.0 | Có | Có — **chỉ vì ranh giới mạng** | Dịch vụ `kho-tri-thuc`, **tùy chọn** (hồ sơ Compose `tri-thuc`, #321, ADR-0006). `/wiki/LICENSE` trong ảnh: `GNU AFFERO GENERAL PUBLIC LICENSE Version 3`; `package.json`: `"license": "AGPL-3.0"`. Dữ liệu trong database riêng `wiki` trên PostgreSQL của cụm — không thêm ảnh CSDL. Hai bước khởi tạo chạy trong ảnh của dịch vụ ứng dụng, không thêm gói Python nào |
| Qwen2.5-1.5B-Instruct GGUF *(tệp mô hình)* | `qwen2.5-1.5b-instruct-q4_k_m.gguf`, kho `Qwen/Qwen2.5-1.5B-Instruct-GGUF` commit `91cad51` | Apache-2.0 | Có | Có | Trọng số mô hình sinh văn bản cho gợi ý (#317). **Không** nằm trong kho mã hay ảnh: `scripts/tai_mo_hinh.py` tải vào volume `mo-hinh`, kiểm SHA-256 `6a1a2eb6…407e`. `LICENSE` của kho Hugging Face: `Apache License Version 2.0, January 2004` — `Copyright 2024 Alibaba Cloud`. Ghi công trong `NOTICE` |
| Qwen3-Embedding-0.6B GGUF *(tệp mô hình)* | `Qwen3-Embedding-0.6B-Q8_0.gguf`, kho `Qwen/Qwen3-Embedding-0.6B-GGUF` commit `370f27d` | Apache-2.0 | Có | Có | Mô hình nhúng véc-tơ cho hồ sơ đã giải quyết tương tự (#319, ADR-0008), chạy ở dịch vụ `mo-hinh-nhung` — **cùng ảnh llama.cpp đã ghim** ở trên, chế độ `--embeddings`, hồ sơ `tri-tue`. **Không** nằm trong kho mã hay ảnh: `scripts/tai_mo_hinh.py` tải vào volume `mo-hinh`, kiểm SHA-256 `06507c7b…e439` (639.150.592 byte). Kho Hugging Face không kèm tệp `LICENSE`; thẻ mô hình ở commit đó khai `license: apache-2.0`. Ghi công trong `NOTICE` |
| psycopg2-binary | `2.9.13` | LGPL kèm ngoại lệ | Có | Có, **có điều kiện** | Trình điều khiển PostgreSQL. Cài vào **ảnh dẫn xuất của Superset** vì ảnh gốc không kèm sẵn — xem `infra/superset/Dockerfile`. Không nhúng vào mã nguồn dự án, không sửa mã thư viện. Chi tiết ràng buộc ở mục Lưu ý về giấy phép copyleft |

---

## Phụ thuộc giao diện

Khai báo trong `frontend/package.json`, ghim chính xác trong `frontend/package-lock.json`.
**Tệp khóa bắt buộc commit.**

| Gói | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| next | `16.4.5` | MIT | Có | Có | Khung ứng dụng. Dựng ở chế độ `standalone` để ảnh chứa không phải mang cả `node_modules`. Nâng từ `16.3.5` ở #313 để vá các cảnh báo mức nghiêm trọng của `npm audit`; kéo theo `sharp` 0.35.5 và `source-map-js` 1.2.2 (gián tiếp) |
| react | `19.3.0` | MIT | Có | Có | |
| react-dom | `19.3.0` | MIT | Có | Có | |
| typescript | `5.9.3` | Apache-2.0 | Có | Có | Giữ ở nhánh 5.x. Bản 7 là bản viết lại bằng Go, mới ra và chưa rõ Next 16 đã theo kịp — chưa đáng mạo hiểm |
| openid-client | `6.8.8` | MIT | Có | Có | Luồng mã ủy quyền OIDC. **Bản cài đặt được OpenID Foundation chứng nhận** — chọn nó thay vì `next-auth` vì bản v5 của `next-auth` còn beta, và vì giao thức thì nên lắp ghép thư viện chuẩn |
| jose | `6.2.12` | MIT | Có | Có | Mã hóa cookie phiên. Cũng là phụ thuộc của `openid-client` |
| lucide-react | `1.52.0` | ISC | Có | Có | Bộ icon của thanh bên và nút bấm (#158). Không kéo phụ thuộc nào khác; chỉ icon được `import` mới vào bản dựng. Dùng qua gói chứ không chép đường vẽ SVG vào kho |
| @superset-ui/embedded-sdk | `0.4.0` | Apache-2.0 | Có | Có | Thư viện nhúng chính thức của Superset: dựng khung nhúng bảng điều khiển ở mục Báo cáo và tự xin lại token khách trước khi hết hạn (#305). Chọn thay vì tự viết khung và giao thức trao đổi tin nhắn với Superset — lắp ghép thư viện của chính nền tảng |
| @xyflow/react | `12.12.0` | MIT | Có | Có | Vẽ sơ đồ quy trình thực tế ở màn Báo cáo → Quy trình thực tế (#315): nút, cạnh, kéo, phóng to. Chỉ chạy ở trình duyệt, nạp CSS nền `base.css` của gói rồi chỉnh màu bằng biến CSS của cổng — không sửa mã gói. Dòng đầu `LICENSE`: `MIT License` |
| @dagrejs/dagre | `3.1.3` | MIT | Có | Có | Bố cục sơ đồ quy trình thực tế (#315): xếp trạng thái theo hàng và dẫn đường cho cạnh quay ngược. Hàm thuần trong `lib/bo-cuc-quy-trinh.ts`. Dòng đầu `LICENSE`: `Copyright (c) 2012-2014 Chris Pettitt` (giấy phép MIT) |
| @types/node · @types/react · @types/react-dom | `26.5.1` · `19.3.0` · `19.3.0` | MIT | Có | Có | Chỉ là khai báo kiểu, không đi vào kết quả dựng |

Hai gói của sơ đồ (#315) ghim **chính xác** `12.12.0` và `3.1.3`: các bản mới hơn tại thời điểm thêm
(10/11/2026) chưa đủ hai tuần phát hành, nên không lấy bản mới nhất.

Phụ thuộc gián tiếp đáng kể: `oauth4webapi` (MIT) — lõi giao thức của `openid-client`;
`@superset-ui/switchboard` (Apache-2.0) và `jwt-decode` (MIT) — kênh tin nhắn với khung nhúng và
đọc hạn của token khách, đi kèm `@superset-ui/embedded-sdk`.

Phụ thuộc gián tiếp của sơ đồ (#315), 20 gói do hai gói trên kéo theo. Mở tệp giấy phép thật trong
`node_modules` của từng gói để ghi; cột cuối là dòng đầu của tệp đó:

| Gói | Phiên bản | Giấy phép | Kéo theo bởi · dùng để | Dòng đầu tệp giấy phép |
|---|---|---|---|---|
| @xyflow/system | `0.0.83` | MIT | `@xyflow/react` · lõi tính toán khung nhìn, đường đi | `MIT License` |
| zustand | `4.5.7` | MIT | `@xyflow/react` · kho trạng thái của sơ đồ | `MIT License` |
| classcat | `5.0.5` | MIT | `@xyflow/react` · nối tên lớp CSS | `Copyright © Jorge Bucaran <<https://jorgebucaran.com>>` (`LICENSE.md`) |
| use-sync-external-store | `1.7.0` | MIT | `zustand` · đăng ký kho với React | `MIT License` |
| @dagrejs/graphlib | `4.0.6` | MIT | `@dagrejs/dagre` · cấu trúc đồ thị | `Copyright (c) 2012-2014 Chris Pettitt` |
| d3-color · d3-dispatch · d3-drag · d3-interpolate · d3-selection · d3-timer · d3-transition · d3-zoom | `3.1.1` · `3.0.2` · `3.0.1` · `3.0.2` · `3.0.1` · `3.0.2` · `3.0.2` · `3.0.1` | ISC | `@xyflow/system` · kéo và phóng khung nhìn | `Copyright 2010-2026 Mike Bostock` (văn bản ISC) |
| d3-ease | `3.0.2` | BSD-3-Clause | `d3-transition` · đường cong chuyển động | `Copyright 2010-2026 Mike Bostock` (văn bản BSD 3 điều khoản) |
| @types/d3-color · d3-drag · d3-interpolate · d3-selection · d3-transition · d3-zoom | `3.1.3` · `3.0.7` · `3.0.4` · `3.0.12` · `3.0.9` · `3.0.9` | MIT | `@xyflow/system` · chỉ là khai báo kiểu | `MIT License` |

Cả hai giấy phép ngoài MIT — ISC và BSD-3-Clause — đều thuộc danh sách OSI và tương thích MIT.

Toàn bộ cây phụ thuộc có **89 gói** (đếm lại ở #315, trước đó 67 gói ở #305). Đã rà giấy phép từng
gói bằng siêu dữ liệu trong tệp khóa, không dựa vào trí nhớ: 41 MIT, 19 Apache-2.0, 14 gói
`sharp`/`libvips` mang LGPL, 11 ISC, 2 BSD-3-Clause, 1 0BSD, 1 CC-BY-4.0. Hai nhóm cuối đã giải thích
ở mục Lưu ý về giấy phép copyleft.

---

## Phụ thuộc trang tài liệu

Trang tài liệu (#279) ở `docs-site/`, khai báo trong `docs-site/package.json`, ghim chính xác trong
`docs-site/package-lock.json`. **Tệp khóa bắt buộc commit.** Mọi gói dưới đây chỉ chạy **lúc dựng**:
kết quả là trang HTML tĩnh, không phụ thuộc nào chạy cùng hệ thống, và không gói nào đi vào ảnh chứa
của cụm.

| Gói | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| astro | `7.3.8` | MIT | Có | Có | Bộ dựng trang tĩnh. Cần Node.js 22.12 trở lên |
| @astrojs/starlight | `0.42.6` | MIT | Có | Có | Giao diện trang tài liệu, tìm kiếm cục bộ qua Pagefind (MIT), chế độ sáng và tối. Chọn thay Material for MkDocs vì dự án đó vào chế độ chỉ bảo trì từ 11/2025 |

Chọn bản đã phát hành ít nhất hai tuần khi thêm (01/11/2026). Toàn bộ cây có **352 gói**, rà giấy
phép bằng siêu dữ liệu trong tệp khóa: 283 MIT, 16 Apache-2.0, 12 MPL-2.0 (`lightningcss`), 10
LGPL-3.0-or-later (`@img/sharp-libvips-*`, tùy chọn) cùng 4 gói `@img/sharp-*` mang Apache-2.0 và
LGPL, 9 ISC, 8 BSD-2-Clause, 3 BSD-3-Clause, 3 BlueOak-1.0.0, 2 CC0-1.0 (`mdn-data`, dữ liệu thuộc
tính CSS), 1 Python-2.0, 1 0BSD. `lightningcss` và `sharp` giải thích ở mục Lưu ý về giấy phép copyleft.

---

## Phụ thuộc kiểm thử giao diện

Kịch bản kiểm tra giao diện (#238) ở `e2e/`, khai báo trong `e2e/package.json`, ghim trong
`e2e/package-lock.json`. **Tệp khóa bắt buộc commit.** Chỉ dùng khi kiểm thử, không đi vào ảnh chứa
của cụm hay trang tài liệu.

| Gói | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| @playwright/test | `1.64.1` | Apache-2.0 | Có | Có | Điều khiển trình duyệt thật, đăng nhập qua trang Keycloak. Kéo theo `playwright` và `playwright-core`, cùng Apache-2.0 — cả cây chỉ ba gói. Trình duyệt Chromium tải riêng bằng `npm run cai-trinh-duyet`, hoặc dùng Chrome cài sẵn |

---

## Phụ thuộc dịch vụ ứng dụng

Khai báo và ghim trong `backend/requirements.txt` bằng `==`. **Tệp này là tệp khóa
phiên bản, bắt buộc commit.** Gói kéo theo khóa ở `backend/constraints.txt` (#368): sinh
bằng `pip freeze` trong ảnh dựng từ `requirements.txt`, Dockerfile cài bằng
`pip install -r requirements.txt -c constraints.txt`, nên dựng lại về sau nhận đúng từng
phiên bản dưới đây — cả gói gián tiếp. Đổi `requirements.txt` thì sinh lại tệp đó theo lệnh
ghi ở đầu tệp; cách làm ở `CONTRIBUTING.md` mục 5.3. Lúc thêm tệp (15/11/2026), `pip freeze`
trong ảnh dựng lại có ràng buộc giống hệt ảnh trước đó, 47 gói.

| Gói | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| fastapi | `0.141.1` | MIT | Có | Có | Khung dịch vụ web |
| uvicorn[standard] | `0.53.0` | BSD-3-Clause | Có | Có | Máy chủ ASGI |
| sqlalchemy | `2.0.53` | MIT | Có | Có | Truy cập cơ sở dữ liệu |
| alembic | `1.20.0` | MIT | Có | Có | Migration. Được cấu hình **bỏ qua mười một bảng** do lược đồ khởi tạo sở hữu — xem `backend/alembic/env.py` |
| psycopg[binary] | `3.3.5` | **LGPL-3.0-only** | Có | Có, **có điều kiện** | Trình điều khiển PostgreSQL. Phụ thuộc copyleft duy nhất trong mã nguồn của nhóm — ranh giới ghi ở mục Lưu ý về giấy phép copyleft |
| pydantic-settings | `2.15.0` | MIT | Có | Có | Đọc cấu hình từ biến môi trường |
| pyjwt[crypto] | `2.14.0` | MIT | Có | Có | Kiểm chữ ký token OIDC **cục bộ**. Keycloak không nằm trên đường đi nóng — xem ADR-0001 |
| cryptography | `50.0.2` | Apache-2.0 hoặc BSD-3-Clause | Có | Có | Phụ thuộc gián tiếp của `pyjwt[crypto]`, dùng để đọc khóa RSA từ JWKS |
| boto3 | `1.43.118` | Apache-2.0 | Có | Có | Gọi S3 API chuẩn của SeaweedFS để lưu tệp đính kèm (#80) — đúng cách ADR-0002 chốt: dịch vụ độc lập qua giao thức chuẩn, không nhúng thư viện của SeaweedFS. Kiểm giấy phép trên gói đã cài: `Apache-2.0` |
| python-multipart | `0.0.32` | Apache-2.0 | Có | Có | FastAPI cần để đọc biểu mẫu tải tệp lên (#80) |

Phụ thuộc gián tiếp đáng kể: `pydantic` (MIT), `starlette` (BSD-3-Clause). Do `boto3` kéo theo:
`botocore` (Apache-2.0), `s3transfer` (Apache-2.0), `jmespath` (MIT), `urllib3` (MIT),
`python-dateutil` (Apache-2.0 hoặc BSD-3-Clause, ghi "Dual License" trong siêu dữ liệu gói) và
`six` (MIT). Đã kiểm trên gói cài thật trong ảnh chứa của dịch vụ ứng dụng — không gói nào
nằm ngoài danh sách OSI, và không gói nào copyleft.

Chỉ dùng khi phát triển và kiểm thử: `pytest` `9.1.1` (MIT) và `httpx` `0.28.1`
(BSD-3-Clause). `httpx` là thứ `TestClient` của FastAPI chạy bên dưới để gọi ứng dụng
mà không cần dựng một máy chủ thật, nên nó không đi vào đường chạy của bản triển khai.
Giấy phép đọc từ siêu dữ liệu của chính gói đã cài, không đọc từ tài liệu trên mạng.

Trong nhánh phụ thuộc của `httpx` có `certifi` mang giấy phép **MPL-2.0**. Giấy phép
này được OSI công nhận và là copyleft ở mức từng tệp: ràng buộc chỉ phát sinh nếu nhóm
**sửa tệp nguồn của chính gói đó**, mà điều đó thì CLAUDE.md mục 2.3 đã cấm sẵn.
`certifi` cũng chỉ là một bó chứng thư số CA đi kèm, không phải mã nguồn chạy trong
sản phẩm.

## Phụ thuộc dịch vụ khai phá quy trình

Khai báo và ghim trong `services/khai-pha/requirements.txt` bằng `==` (#314, ADR-0007). Phần mở rộng
`[stable]` của chính PM4Py ghim sẵn bộ thư viện số học kéo theo; phần còn lại (starlette, pydantic, anyio…)
khóa ở `services/khai-pha/constraints.txt` (#368), cùng cách với dịch vụ ứng dụng ở trên — 50 gói, `pip freeze`
trước và sau khi thêm tệp giống hệt. Nên ai dựng lại cũng nhận đúng bộ phiên
bản dưới đây. Mọi gói trong bảng **chỉ nằm trong ảnh của dịch vụ khai phá**, không nằm trong dịch vụ ứng
dụng hay cổng. Giấy phép đọc từ siêu dữ liệu gói đã cài trong ảnh; gói nào siêu dữ liệu không ghi thì
đã mở tệp `LICENSE` trong gói.

Mã do nhóm viết trong `services/khai-pha/` mang **AGPL-3.0-or-later**, khác phần còn lại của kho (MIT) —
mô hình nhiều giấy phép ở [`LICENSES.md`](../LICENSES.md), thông báo bên thứ ba ở [`NOTICE`](../NOTICE) (#340).
Cột *Tương thích MIT* dưới đây vì vậy chỉ còn ý nghĩa khi so với phần MIT của kho; trong dịch vụ này mọi
gói đều phải tương thích AGPL-3.0, và đều đạt: MIT, BSD, Apache-2.0, MPL-2.0, PSF, LGPL-3.0 và
GPL-3.0-or-later đều kết hợp được với AGPL-3.0.

| Gói | Phiên bản | Giấy phép | OSI công nhận | Tương thích MIT | Ghi chú |
|---|---|---|---|---|---|
| pm4py[stable] | `2.7.23.8` | AGPL-3.0-or-later | Có | Có, **có điều kiện** | Khám phá đồ thị trực tiếp và biến thể. Ranh giới ở mục Lưu ý về giấy phép copyleft |
| fastapi | `0.141.1` | MIT | Có | Có | Cùng bản với dịch vụ ứng dụng |
| uvicorn[standard] | `0.53.0` | BSD-3-Clause | Có | Có | |
| psycopg[binary] | `3.3.5` | LGPL-3.0-only | Có | Có, **có điều kiện** | Như dịch vụ ứng dụng — chỉ `import`, không sửa |
| pandas | `3.0.5` | BSD-3-Clause | Có | Có | Bảng sự kiện đưa vào PM4Py; bộ máy dự phòng không cần |
| pytest | `9.1.1` | MIT | Có | Có | Bài kiểm thử đáp án biết trước, chạy trong container |
| httpx | `0.28.1` | BSD-3-Clause | Có | Có | `TestClient` của FastAPI |
| cvxopt *(gián tiếp)* | `1.3.3` | GPL-3.0-or-later | Có | Có, **có điều kiện** | Bắt buộc của PM4Py; xem mục copyleft |
| numpy *(gián tiếp)* | `2.5.1` | BSD-3-Clause AND 0BSD AND MIT AND Zlib… | Có | Có | |
| scipy *(gián tiếp)* | `1.18.0` | BSD-3-Clause | Có | Có | |
| networkx *(gián tiếp)* | `3.6.1` | BSD-3-Clause | Có | Có | |
| lxml *(gián tiếp)* | `6.1.1` | BSD-3-Clause | Có | Có | |
| matplotlib *(gián tiếp)* | `3.11.1` | Matplotlib License (dựa trên PSF License) | Văn bản gốc PSF-2.0 có trong danh sách OSI; bản của Matplotlib chỉ đổi tên bên cấp phép | Có | Dễ dãi kiểu BSD. PM4Py kéo theo để vẽ, dịch vụ không vẽ gì. Ghi riêng để người chấm thấy đã xét |
| pillow, contourpy, cycler, kiwisolver, fonttools, pyparsing *(gián tiếp, cùng matplotlib)* | theo `[stable]` | MIT-CMU · BSD-3-Clause · BSD-3-Clause · BSD-3-Clause · MIT · MIT | Có | Có | |
| graphviz *(gián tiếp, gói Python)* | `0.21` | MIT | Có | Có | Chỉ là lớp gọi; ảnh không cài chương trình Graphviz |
| pytz, python-dateutil, six, tqdm, packaging *(gián tiếp)* | theo `[stable]` | MIT · Apache-2.0 hoặc BSD-3-Clause · MIT · MPL-2.0 AND MIT · Apache-2.0 hoặc BSD-2-Clause | Có | Có | tqdm MPL-2.0 theo từng tệp, không sửa tệp nào |

---

## Nền tảng Open-Core

Các nền tảng lớn được tích hợp theo yêu cầu kiến trúc Open-Core của đề bài. Mỗi mục
phải có một bản ghi quyết định tương ứng trong `docs/adr/`.

| Không gian | Nền tảng | Giấy phép | OSI công nhận | Cách tích hợp | Bản ghi quyết định |
|---|---|---|---|---|---|
| `H` | Keycloak `26.7.3` | Apache-2.0 | Có | Dịch vụ độc lập, giao tiếp qua OIDC. Không nhúng thư viện, không sửa mã nền tảng. Ảnh ghim kèm mã băm `@sha256:ff4257d0…1c54` (bản dựng 31/08/2026) | [ADR-0001](adr/0001-chon-nen-tang-sso.md) |
| `H` | Wiki.js `2.5.315` — **tùy chọn** (hồ sơ Compose `tri-thuc`) | AGPL-3.0 | Có | Dịch vụ độc lập: ảnh chính thức nguyên bản, người dùng đăng nhập qua OIDC, dịch vụ ứng dụng đọc bài qua GraphQL bằng khóa API chỉ đọc. Không nhúng, không sửa, không dựng lại ảnh. Ảnh ghim `@sha256:af71a17d…638c` (dựng 21/09/2026) | [ADR-0006](adr/0006-chon-nen-tang-kho-tri-thuc.md) |
| `P` | **Không dùng nền tảng ngoài** — engine máy trạng thái do nhóm tự viết | MIT (mã của dự án) | — | Không tích hợp. Trạng thái và quy tắc chuyển lưu trong bảng PostgreSQL | [ADR-0004](adr/0004-tu-viet-engine-may-trang-thai.md) |
| `D` | Apache Superset `6.1.0` | Apache-2.0 | Có | Dịch vụ độc lập, chỉ đọc CSDL nghiệp vụ, nhúng vào cổng qua guest token. Cần ảnh dẫn xuất bổ sung trình điều khiển PostgreSQL. Ảnh gốc ghim kèm mã băm `@sha256:59cd4af6…f29d` (ARG `SUPERSET_DIGEST`) | [ADR-0003](adr/0003-chon-nen-tang-bi.md) |
| `I` | PM4Py `2.7.23.8` | AGPL-3.0-or-later | Có | Thư viện, chỉ `import` trong dịch vụ khai phá tách riêng `services/khai-pha/` (cả thư mục theo AGPL), dịch vụ ứng dụng gọi qua HTTP — mục copyleft ở trên | [ADR-0007](adr/0007-chon-thu-vien-khai-pha-quy-trinh.md) |
| `I` | llama.cpp server `b11889` + Qwen2.5-1.5B-Instruct, Qwen3-Embedding-0.6B — **tùy chọn** (hồ sơ `tri-tue`) | MIT · Apache-2.0 | Có | Dịch vụ độc lập, điểm cuối kiểu OpenAI trong mạng Compose; tệp mô hình trong volume, không trong kho hay ảnh | [ADR-0008](adr/0008-chon-co-so-du-lieu-vec-to-va-mo-hinh-cuc-bo.md) |
| `core` | SeaweedFS `4.45` | Apache-2.0 | Có | Dịch vụ độc lập, giao tiếp qua S3 API chuẩn. Không nhúng thư viện, không dùng API riêng của nền tảng. Ảnh ghim kèm mã băm `@sha256:fc9f76fa…69e5` | [ADR-0002](adr/0002-chon-nen-tang-luu-tru-doi-tuong.md) |
| `core` | Apache APISIX `3.20.0` — cổng API, cửa vào duy nhất của API (#364) | Apache-2.0 | Có | Dịch vụ độc lập ở cụm mặc định, ảnh chính thức nguyên bản ghim `@sha256:013de62a…e759a`, chế độ standalone đọc `infra/cong-api/` (gắn chỉ đọc), không etcd, không API quản trị. Chỉ dùng plugin có sẵn (`openid-connect`, `limit-count`, `real-ip`); không sửa, không dựng lại ảnh. Nói chuyện với Keycloak qua điểm cuối khám phá OIDC, với dịch vụ ứng dụng qua HTTP | [ADR-0010](adr/0010-chon-nen-tang-cong-api.md) |

Cột **Cách tích hợp** ghi rõ: nhúng thư viện, hay chạy như dịch vụ độc lập giao tiếp
qua mạng. Với nền tảng copyleft mạnh, bắt buộc phải là phương án thứ hai.

---

## Công cụ phát triển

Không phải phụ thuộc của sản phẩm, nhưng ghi lại để minh bạch chuỗi công cụ.

| Công cụ | Giấy phép | Vai trò | Có trong chuỗi dựng không |
|---|---|---|---|
| git-cliff | MIT hoặc Apache-2.0 | Sinh nhật ký thay đổi | Không |
| GitHub CLI | MIT | Khởi tạo hệ thống nhãn | Không |
| `actions/checkout`, `actions/setup-node` (GitHub Actions) | MIT | Tích hợp liên tục, `.github/workflows/ci.yml` | Không — chỉ chạy kiểm tra, sản phẩm vẫn dựng bằng `docker compose` |
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
