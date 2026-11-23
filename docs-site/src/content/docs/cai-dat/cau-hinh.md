---
title: Cấu hình
description: Các biến trong infra/.env — cổng, mật khẩu, giới hạn tệp đính kèm, bộ quét hạn — và phần nào phải đổi trước khi triển khai thật.
sidebar:
  order: 2
---

Cấu hình **vận hành** nằm trong `infra/.env`, chép từ `infra/.env.example`. Cấu hình **nghiệp vụ**
— trạng thái, vai trò, hạn xử lý, phòng ban, loại yêu cầu — không nằm ở đây mà trong dữ liệu khởi
tạo, xem [Tùy biến quy trình](../../quan-tri/tuy-bien-quy-trinh/).

Đổi `.env` thì khởi động lại dịch vụ liên quan bằng `docker compose --env-file .env up -d`; không
cần xóa dữ liệu.

## Phải đổi trước khi triển khai thật

| Biến | Vì sao |
|---|---|
| `DXLAB_DB_PASSWORD`, `SUPERSET_READONLY_PASSWORD` | Mật khẩu cơ sở dữ liệu |
| `KEYCLOAK_ADMIN_PASSWORD`, `SUPERSET_ADMIN_PASSWORD` | Tài khoản quản trị Keycloak, Superset (mẫu là `admin`) |
| `SEAWEEDFS_SECRET_KEY` | Khóa S3 của kho tệp — phải khớp `infra/seaweedfs/s3-config.json` |
| `KEYCLOAK_PORTAL_SECRET`, `KEYCLOAK_DIRECTORY_SECRET` | Bí mật hai client — phải khớp `infra/keycloak/realm-dx-os-lab.json` |
| `KEYCLOAK_INTEGRATION_SECRET` | Bí mật của tài khoản dịch vụ gọi API của lõi — đổi xong chạy `python scripts/tai_khoan_dich_vu.py` để Keycloak nhận bí mật mới |
| `PORTAL_SESSION_SECRET` | Khóa mã hóa cookie phiên của cổng — sinh bằng `openssl rand -base64 32` |
| `SUPERSET_SECRET_KEY` | Khóa ký phiên của Superset — sinh bằng `openssl rand -base64 42` |
| `MINING_READONLY_PASSWORD` | Tài khoản chỉ đọc của dịch vụ khai phá — đổi sau khi đã dựng cụm thì `ALTER ROLE` bằng tay rồi đổi ở đây |
| `KEYCLOAK_INTEGRATION_HEAD_SECRET`, `KEYCLOAK_INTEGRATION_REVIEWER_SECRET` | Hai tài khoản dịch vụ của ví dụ quy trình mua sắm — đổi, hoặc tắt hai client đó |
| `WIKI_OIDC_SECRET`, `WIKI_ADMIN_PASSWORD` | Chỉ khi bật kho tri thức (hồ sơ `tri-thuc`) |

## Cổng

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `FRONTEND_PORT` | `3000` | Cổng người dùng. Giữ nguyên khi dùng realm mẫu — địa chỉ chuyển hướng đăng nhập gắn với cổng này |
| `KEYCLOAK_PORT` | `8080` | Giữ nguyên khi dùng realm mẫu, cùng lý do |
| `GATEWAY_PORT` | `9080` | **Cổng API** — cửa vào duy nhất của API, tài liệu API ở `/docs` |
| `SUPERSET_PORT` | `8088` | |
| `SEAWEEDFS_S3_PORT` | `8333` | |
| `BACKEND_PORT` | `8000` | Dịch vụ ứng dụng — **chỉ** khi thêm tệp `docker-compose.phat-trien.yml`; cấu hình mặc định không mở |
| `POSTGRES_PORT` | `5432` | PostgreSQL — như trên |

## Cổng API

Apache APISIX đứng trước dịch vụ ứng dụng: kiểm access token của Keycloak tại biên, giới hạn tốc độ chung
theo địa chỉ người gọi, rồi chuyển lời gọi tới dịch vụ — dịch vụ vẫn tự kiểm token lại. Tuyến và plugin là
tệp trong kho, `infra/cong-api/`. Cả năm biến có mặc định trong `docker-compose.yml`.

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `GATEWAY_RATE_LIMIT_COUNT` | `3000` | Số lời gọi tối đa của một địa chỉ trong một cửa sổ, cho mọi đường. Vượt thì `429` |
| `GATEWAY_RATE_LIMIT_WINDOW_SECONDS` | `60` | Độ dài cửa sổ, giây |
| `GATEWAY_MAX_BODY_MB` | `64` | Trần thân một yêu cầu. Không đặt thấp hơn `ATTACHMENT_MAX_FILES` × `ATTACHMENT_MAX_MB` cộng phần đầu biểu mẫu, không thì lượt tải nhiều tệp nhận `413` |
| `GATEWAY_TIMEOUT_SECONDS` | `120` | Chờ gửi/đọc từ dịch vụ ứng dụng |
| `GATEWAY_TOKEN_LEEWAY_SECONDS` | `10` | Độ lệch đồng hồ cho phép khi xét hạn token, cùng giá trị với dịch vụ ứng dụng |

## Tệp đính kèm

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `ATTACHMENT_ALLOWED_EXTENSIONS` | ảnh, PDF, Word, Excel, văn bản, CSV | Cố ý không có `zip`, `exe`, `bat`, `js`, `sh`. Dịch vụ còn kiểm nội dung khớp đuôi |
| `ATTACHMENT_MAX_MB` | `10` | Mỗi tệp |
| `ATTACHMENT_MAX_FILES` | `5` | Mỗi lần tải |
| `ATTACHMENT_MAX_FILES_PER_CASE` | `20` | Mỗi hồ sơ |
| `SEAWEEDFS_BUCKET` | `dxlab-attachments` | Đổi tên thùng thì đổi cả quyền trong `infra/seaweedfs/s3-config.json` |

Giao diện hỏi dịch vụ các giới hạn này, nên đổi một chỗ là hai lớp chặn cùng đổi.

## Định danh

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `KEYCLOAK_REALM` | `dx-os-lab` | Realm nạp từ `infra/keycloak/realm-dx-os-lab.json` |
| `KEYCLOAK_DEPARTMENT_GROUP_PREFIX` | `/phong-ban/` | Phòng ban là nhóm Keycloak dưới đường dẫn này. Tổ chức cây nhóm khác thì đổi ở đây |
| `KEYCLOAK_ADMIN_USER` | `admin` | Tài khoản quản trị Keycloak, đi cùng `KEYCLOAK_ADMIN_PASSWORD` |
| `KEYCLOAK_PORTAL_CLIENT_ID` | `dx-portal` | Client bí mật của cổng người dùng; luồng OIDC chạy phía máy chủ Next.js |
| `KEYCLOAK_API_CLIENT_ID` | `dx-api` | Token gọi dịch vụ ứng dụng phải mang tên này trong claim `aud` |
| `KEYCLOAK_DIRECTORY_CLIENT_ID` | `dx-directory` | Tài khoản dịch vụ chỉ đọc (`view-users`) để tra tên người trong phòng ban |
| `KEYCLOAK_MAX_HEAP` | `768m` | Keycloak là dịch vụ nặng nhất cụm; dưới `512m` khởi động chậm hẳn |

### Tài khoản dịch vụ gọi API của lõi

Ứng dụng khác gọi API của nền tảng lõi (`/core/v1`) bằng token của một tài khoản dịch vụ — xem
[API](../../tham-khao/api/). Dịch vụ ứng dụng **không** đọc các biến này; chỉ `examples/goi-loi/` và
`scripts/tai_khoan_dich_vu.py` dùng. Realm mẫu đã khai ba client `dx-integration`, `dx-integration-truong-phong`, `dx-integration-duyet` với đúng các giá trị mặc
định; đổi biến nào thì chạy `python scripts/tai_khoan_dich_vu.py` để Keycloak theo.

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `KEYCLOAK_INTEGRATION_CLIENT_ID` | `dx-integration` | Client bí mật, chỉ bật client credentials; token mang `aud` của dịch vụ ứng dụng |
| `KEYCLOAK_INTEGRATION_SECRET` | giá trị mẫu | Đổi trước khi triển khai thật |
| `KEYCLOAK_INTEGRATION_ROLES` | `requester` | Vai realm của tài khoản dịch vụ, cách nhau dấu phẩy. Kịch bản chỉ gán thêm, không gỡ vai nào |
| `KEYCLOAK_INTEGRATION_HEAD_*` | `dx-integration-truong-phong`, vai `approver`, group `/phong-ban/admin-office` | Tài khoản trưởng phòng của ví dụ quy trình thứ hai (`_CLIENT_ID`, `_SECRET`, `_ROLES`, `_GROUP`). Tùy chọn: bỏ trống thì kịch bản bỏ qua |
| `KEYCLOAK_INTEGRATION_REVIEWER_*` | `dx-integration-duyet`, vai `classifier` | Tài khoản duyệt cấp hai của ví dụ quy trình thứ hai (`_CLIENT_ID`, `_SECRET`, `_ROLES`). Tùy chọn |

## Bộ quét hạn

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `SLA_SCAN_ENABLED` | `true` | Bộ quét nền tự leo thang hồ sơ quá hạn và đi các bước tự động khi hồ sơ nằm im |
| `SLA_SCAN_INTERVAL_SECONDS` | `60` | Hạ xuống `5` khi cần trình diễn leo thang mà không phải chờ |
| `SLA_SCAN_STALE_AFTER_SECONDS` | `0` | Quá chừng này giây không có lượt quét thành công thì `/health` báo `degraded`. `0` là tự tính: năm lần chu kỳ quét |
| `SLA_SCAN_MAX_CONSECUTIVE_ERRORS` | `3` | Số lượt quét hỏng liên tiếp tới mức coi bộ quét là đang hỏng |

Chạy nhiều bản dịch vụ ứng dụng thì mỗi lượt chỉ một bản quét, bản kia bỏ lượt. Hai biến cuối có mặc
định trong `docker-compose.yml`, nên tệp `.env` cũ không cần thêm.

Ngưỡng hạn của từng loại yêu cầu **không** nằm ở đây — xem
[Danh mục và các con số](../../quan-tri/danh-muc-va-con-so/).

## Lưu trữ lạnh

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `ARCHIVE_ENABLED` | `true` | Bộ quét nền niêm phong mỗi tháng đã khép ra kho đối tượng. Tắt là tắt lịch; `POST /archive/scan` vẫn chạy được |
| `ARCHIVE_INTERVAL_SECONDS` | `3600` | Chu kỳ quét |
| `ARCHIVE_MIN_AGE_MONTHS` | `1` | Tháng cũ hơn chừng này tháng so với tháng hiện tại (UTC) mới niêm phong. Tối thiểu `1` |
| `ARCHIVE_MAX_MONTHS_PER_RUN` | `6` | Số tháng tối đa mỗi lượt, để lần đầu bật trên cụm nhiều năm dữ liệu không giữ khóa lâu |
| `ARCHIVE_BUCKET` | trống | Trống là dùng chung thùng `SEAWEEDFS_BUCKET`. Thùng riêng thì cấp thêm `Admin:<tên thùng>` trong `infra/seaweedfs/s3-config.json` |
| `ARCHIVE_PREFIX` | `luu-tru-lanh/` | Tiền tố khóa của các bản lưu trong thùng |

Mọi biến có mặc định trong `docker-compose.yml`, tệp `.env` cũ không cần thêm. Bản đã niêm phong giữ thùng
và tiền tố lúc xuất, nên đổi hai biến cuối không làm mất dấu bản cũ. Cách dùng ở
[Màn Hệ thống và vận hành](../../quan-tri/he-thong/#lưu-trữ-lạnh).

## Gợi ý người xử lý

Thẻ gợi ý trên ô chọn người xử lý của trưởng phòng (#318). Không cần mô hình ngôn ngữ. Mỗi người nhận
được việc trong phòng được điểm *trọng số kinh nghiệm × ln(1 + số hồ sơ cùng loại đã làm xong) − trọng
số tải × số việc đang giữ*; người điểm cao nhất được gợi ý. Cả bốn biến có mặc định trong
`docker-compose.yml`.

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `ASSIGNEE_SUGGEST_ENABLED` | `true` | `false` thì ô chọn người như trước, không thẻ gợi ý |
| `ASSIGNEE_SUGGEST_LOAD_WEIGHT` | `1.0` | Mỗi việc đang giữ trừ chừng này điểm |
| `ASSIGNEE_SUGGEST_EXPERIENCE_WEIGHT` | `1.0` | Nhân với ln(1 + số hồ sơ cùng loại đã làm xong) |
| `ASSIGNEE_SUGGEST_HISTORY_DAYS` | `365` | Kinh nghiệm chỉ đếm hồ sơ làm xong trong chừng này ngày |

## Hồ sơ tương tự và khuyến nghị cải tiến

Hai gợi ý của tầng `I` cần mô hình (hồ sơ Compose `tri-tue`); cách bật ở
[Mô hình ngôn ngữ](../mo-hinh-ngon-ngu/). Mọi biến có mặc định trong `docker-compose.yml`.

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `EMBEDDING_URL` | rỗng | Dịch vụ mô hình nhúng (`http://mo-hinh-nhung:8080`). **Rỗng là tắt** hồ sơ tương tự trên biểu mẫu Gửi yêu cầu |
| `SIMILAR_TIMEOUT_SECONDS` | `2` | Hạn chót một lần tìm khi người gửi đang gõ; quá hạn thì không hiện gì |
| `SIMILAR_MAX_RESULTS` | `3` | Số hồ sơ tương tự tối đa |
| `SIMILAR_MIN_SCORE` | `0.55` | Độ tương đồng cosine tối thiểu để một hồ sơ được hiện |
| `SIMILAR_ABANDON_AFTER_MINUTES` | `30` | Xem gợi ý mà quá chừng này phút không gửi thì tính là yêu cầu được ngăn chặn |
| `RECOMMENDATION_ENABLED` | `true` | Khuyến nghị cải tiến trên màn Quy trình thực tế; cần cả `LLM_URL` |
| `RECOMMENDATION_TIMEOUT_SECONDS` | `90` | Hạn chót một lần sinh (chạy nền, màn không chờ) |
| `RECOMMENDATION_MAX_SENTENCES` | `4` | Số câu tối đa mô hình được viết; câu sai số bị bỏ |

## Giới hạn tốc độ

Mỗi người dùng chỉ được gọi một số lần nhất định trong một cửa sổ thời gian cố định; vượt thì thao tác
báo "Bạn … quá nhanh. Thử lại sau N giây." thay vì thực hiện. Đặt số lần tối đa bằng `0` để tắt giới
hạn đó. Cả mười biến có mặc định trong `docker-compose.yml`, nên tệp `.env` cũ không cần thêm.

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `RATE_LIMIT_CREATE_CASE_MAX` / `_WINDOW_SECONDS` | `30` / `60` | Gửi yêu cầu mới |
| `RATE_LIMIT_UPLOAD_MAX` / `_WINDOW_SECONDS` | `20` / `60` | Tải tệp đính kèm lên |
| `RATE_LIMIT_MESSAGE_MAX` / `_WINDOW_SECONDS` | `60` / `60` | Gửi lời nhắn, ở cả ba buồng lái |
| `RATE_LIMIT_BULK_MAX` / `_WINDOW_SECONDS` | `10` / `60` | Thao tác hàng loạt ở buồng lái điều phối — đếm theo lô, mỗi lô tới `BULK_MAX_CASES` hồ sơ |
| `RATE_LIMIT_LOGIN_MAX` / `_WINDOW_SECONDS` | `30` / `60` | Đăng nhập quay về, theo địa chỉ IP. Đếm trong bộ nhớ của từng bản cổng; địa chỉ IP lấy từ `X-Forwarded-For` nên cần reverse proxy đặt header đó |

## Bảng đầy đủ các biến còn lại

Mọi biến trong `infra/.env.example` đều có một dòng trên trang này. `scripts/kiem_bien_moi_truong.py`
chạy trong tích hợp liên tục và báo lỗi khi thêm biến vào `.env.example` mà quên ghi ở đây (#413).

### Cơ sở dữ liệu và phiên bản

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `DXLAB_DB_NAME` | `dxlab` | Database nghiệp vụ, cũng là chủ sở hữu thực thể PostgreSQL |
| `DXLAB_DB_USER` | `dxlab` | Tài khoản của dịch vụ ứng dụng, đi cùng `DXLAB_DB_PASSWORD` |
| `KEYCLOAK_DB_NAME` | `keycloak` | Database của Keycloak, tạo bởi kịch bản trong `infra/postgres/init/` |
| `SUPERSET_DB_NAME` | `superset` | Database siêu dữ liệu của Superset, như trên |
| `SUPERSET_READONLY_USER` | `superset_readonly` | Tài khoản chỉ đọc Superset dùng trên database nghiệp vụ (ADR-0003) |
| `SUPERSET_ADMIN_USER` | `admin` | Tài khoản quản trị Superset, đi cùng `SUPERSET_ADMIN_PASSWORD` |
| `SUPERSET_VERSION` | `6.1.0` | Phiên bản ảnh Superset; đổi là đổi nền tảng, đọc ADR-0003 trước |
| `DXLAB_VERSION` | `0.3.0` | Thẻ của các ảnh do nhóm tự dựng, chỉ để nhận diện ảnh trên máy |

### Kho tệp và quét mã độc

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `SEAWEEDFS_ACCESS_KEY` | `dxlab_access_key` | Khóa truy cập S3, phải khớp `infra/seaweedfs/s3-config.json` |
| `SEAWEEDFS_VOLUME_LIMIT_MB` | `512` | Kích thước tối đa một khối lưu trữ của SeaweedFS |
| `CLAMAV_HOST` | rỗng | **Rỗng là tắt** quét mã độc. Bật: đặt `quet-tep` và chạy hồ sơ Compose `quet-tep` (khoảng 1 GB bộ nhớ) |
| `CLAMAV_PORT` | `3310` | Cổng của dịch vụ quét trong cụm |
| `CLAMAV_TIMEOUT_SECONDS` | `15` | Hạn chót một lần quét |
| `CLAMAV_ON_UNAVAILABLE` | `accept` | Dịch vụ quét không phản hồi: `accept` nhận tệp và gắn cờ "chưa quét", `reject` từ chối lượt tải. Tệp có mã độc luôn bị từ chối |
| `CLAMAV_NO_FRESHCLAMD` | `false` | `true` thì không tự cập nhật mẫu nhận diện, dùng bộ mẫu kèm ảnh khi không có mạng |

Chi tiết ở [Thư điện tử và quét tệp](../thu-va-quet-tep/).

### Thông báo thư điện tử

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `SMTP_HOST` | rỗng | **Rỗng là tắt** thông báo thư. Trình diễn: `thu-thu` với hồ sơ Compose `thu-thu` (Mailpit) |
| `SMTP_PORT` | `25` | Mailpit dùng `1025` |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | rỗng | Tài khoản máy chủ thư thật |
| `SMTP_SECURITY` | `none` | `none`, `starttls` (587) hay `ssl` (465) |
| `SMTP_FROM` | `DX-OS Lab <khong-tra-loi@dx-os-lab.test>` | Người gửi hiện trên thư |
| `NOTIFY_SCAN_INTERVAL_SECONDS` | `30` | Nhịp bộ gửi thư |
| `NOTIFY_MAX_ATTEMPTS` | `5` | Số lần thử tối đa một thư |
| `NOTIFY_RETRY_AFTER_SECONDS` | `60` | Chờ trước lần thử lại đầu, nhân đôi mỗi lần |
| `NOTIFY_DIRECTORY_CACHE_SECONDS` | `120` | Bộ gửi nhớ danh bạ Keycloak chừng này giây |
| `MAILPIT_UI_PORT` | `8025` | Giao diện web của hộp thư thử Mailpit |
| `MAILPIT_MAX_MESSAGES` | `500` | Số thư Mailpit giữ |

### Nhật ký dịch vụ ứng dụng

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `LOG_FORMAT` | `json` | `json`: mỗi dòng một đối tượng mang `request_id`; `text`: dạng chữ để đọc tay |
| `LOG_LEVEL` | `INFO` | Mức nhật ký theo chuẩn của Python |

### Khai phá quy trình

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `MINING_READONLY_USER` | `khai_pha_readonly` | Tài khoản chỉ đọc riêng của dịch vụ khai phá, tạo bằng migration |
| `MINING_ENGINE` | `pm4py` | `pm4py` hay `noi_bo` — bộ máy dự phòng không dùng thư viện AGPL, cùng kết quả |
| `MINING_BOTTLENECK_FACTOR` | `2` | Trạng thái là điểm nghẽn khi thời gian chờ trung vị gấp chừng này lần trung vị chung |
| `MINING_SOURCE_URL` | thư mục `services/khai-pha` trên GitHub | Màn Quy trình thực tế và khối bước lệch trên trang hồ sơ dẫn tới đây (AGPL điều 13). Bản đã sửa thì trỏ về kho chứa bản đó |

### Mô hình ngôn ngữ và gợi ý

Cách bật ở [Mô hình ngôn ngữ](../mo-hinh-ngon-ngu/).

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `LLM_URL` | rỗng | **Rỗng là tắt**: không gợi ý nào được sinh, điều phối chạy thủ công |
| `LLM_TIMEOUT_SECONDS` | `30` | Hạn chót một lần hỏi mô hình; quá hạn là "không có gợi ý" |
| `LLM_CONTEXT_SIZE` | `4096` | Ngữ cảnh của dịch vụ mô hình sinh văn bản |
| `LLM_THREADS` | `4` | Số luồng CPU của dịch vụ mô hình |
| `EMBEDDING_CONTEXT_SIZE` | `8192` | Ngữ cảnh của dịch vụ mô hình nhúng |
| `SUGGEST_SCAN_INTERVAL_SECONDS` | `30` | Nhịp bộ quét bù gợi ý |
| `SUGGEST_MAX_ATTEMPTS` | `3` | Số lần thử tối đa cho một hồ sơ |
| `SUGGEST_RETRY_AFTER_SECONDS` | `600` | Khoảng cách tối thiểu giữa hai lần thử |
| `SUGGEST_DEPARTMENT_FROM_MODEL` | `false` | Chỉ bật khi `scripts/do_chinh_xac_goi_y.py` đo được từ 80 % và hơn bảng ánh xạ |

### Ủy quyền

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `DELEGATION_MAX_DAYS` | `60` | Một lần ủy quyền dài tối đa chừng này ngày |

### Thao tác hàng loạt

Điều phối viên chọn nhiều hồ sơ trên hàng đợi rồi đi một bước cho cả lô; mỗi hồ sơ vẫn là một lần
chuyển trạng thái riêng, một dòng nhật ký riêng, hồ sơ bị chặn báo riêng. Cách dùng ở trang
[Điều phối viên](../../huong-dan/dieu-phoi-vien/).

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `BULK_MAX_CASES` | `50` | Số hồ sơ tối đa mỗi lô; lô lớn hơn bị từ chối cả lô (`422`) |
| `BULK_ACTIVITIES` | `classify,route-to-department` | Mã bước (`transitions.activity_code`) làm được hàng loạt, cách nhau dấu phẩy, theo thứ tự nút. Bước không có cạnh của vai điều phối thì không hiện |

### Đánh giá mức hài lòng

Người gửi chấm 1–5 kèm nhận xét khi xác nhận hồ sơ hoàn tất, đều không bắt buộc. Bước nào cho chấm nằm
trong dữ liệu quy tắc (cột `transitions.collects_feedback`), không phải biến môi trường.

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `FEEDBACK_COMMENT_MAX_CHARS` | `1000` | Nhận xét dài tối đa chừng này ký tự; dài hơn thì bị từ chối (`422`), ô nhận xét đếm ký tự theo số này |

### Kho tri thức

Chỉ dùng khi bật hồ sơ Compose `tri-thuc`; cách bật ở [Kho tri thức](../kho-tri-thuc/).

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `WIKI_PORT` | `3100` | Cổng web của Wiki.js trên máy |
| `WIKI_URL` | rỗng | Địa chỉ trình duyệt mở wiki. **Rỗng là tắt** lối vào và gợi ý bài trên cổng |
| `WIKI_INDEX_INTERVAL_SECONDS` | `120` | Nhịp bộ lập chỉ mục bài viết |
| `WIKI_DB_NAME` | `wiki` | Database riêng của Wiki.js, bước khởi tạo tự tạo |
| `WIKI_OIDC_CLIENT_ID` | `dx-wiki` | Client OIDC của wiki trong Keycloak, bước khởi tạo tự tạo |
| `WIKI_READ_ROLES` | năm vai | Vai realm được đọc bài, cách nhau dấu phẩy |
| `WIKI_WRITE_ROLES` | `classifier,approver,administrator` | Vai realm được viết bài |
| `WIKI_ADMIN_EMAIL` | `quan-tri-wiki@dx-os-lab.test` | Tài khoản quản trị cục bộ của Wiki.js, không qua Keycloak |
| `WIKI_LOCALE` | `vi` | Ngôn ngữ giao diện; tải gói ngôn ngữ cần mạng, không tải được thì giữ tiếng Anh |
