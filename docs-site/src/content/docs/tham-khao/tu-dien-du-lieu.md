---
title: Từ điển dữ liệu
description: Mỗi bảng của dịch vụ ứng dụng — nghĩa, cột, kiểu, khóa — sinh tự động từ mô hình.
sidebar:
  order: 4
---

<!-- Tệp SINH TỰ ĐỘNG bởi scripts/tu_dien_du_lieu.py từ backend/app/models/. Đừng sửa tay: sửa mô hình
     hay chú thích của cột rồi chạy python scripts/tu_dien_du_lieu.py. Tích hợp liên tục chạy --kiem
     và báo đỏ khi trang này lệch với mô hình. -->

35 bảng mà dịch vụ ứng dụng ánh xạ, xếp theo tên. Nghĩa của bảng lấy từ docstring của lớp mô
hình, nghĩa của cột từ chú thích ngay trên cột trong mã — cột chưa có chú thích để trống ô *Ý nghĩa*.
Lược đồ do các bản sửa Alembic tạo (`backend/alembic/versions/`); các view báo cáo và nguồn gốc của
chúng ở trang [Phả hệ dữ liệu](../pha-he-du-lieu/).

| Bảng | Số cột | Mô hình |
|---|---|---|
| [`attachment_file_types`](#attachment_file_types) | 8 | `AttachmentFileType` · `backend/app/models/case.py` |
| [`case_attachments`](#case_attachments) | 11 | `CaseAttachment` · `backend/app/models/case.py` |
| [`case_feedback`](#case_feedback) | 6 | `CaseFeedback` · `backend/app/models/case.py` |
| [`case_message_reads`](#case_message_reads) | 5 | `CaseMessageRead` · `backend/app/models/case.py` |
| [`case_messages`](#case_messages) | 7 | `CaseMessage` · `backend/app/models/case.py` |
| [`cold_archives`](#cold_archives) | 9 | `ColdArchive` · `backend/app/models/luu_tru.py` |
| [`config_changes`](#config_changes) | 9 | `ConfigChange` · `backend/app/models/quan_tri.py` |
| [`delegations`](#delegations) | 15 | `Delegation` · `backend/app/models/quan_tri.py` |
| [`departments`](#departments) | 5 | `Department` · `backend/app/models/workflow_config.py` |
| [`event_log`](#event_log) | 13 | `EventLog` · `backend/app/models/case.py` |
| [`guards`](#guards) | 3 | `Guard` · `backend/app/models/workflow_config.py` |
| [`idempotency_keys`](#idempotency_keys) | 12 | `IdempotencyKey` · `backend/app/models/van_hanh.py` |
| [`message_kind_roles`](#message_kind_roles) | 2 | `MessageKindRole` · `backend/app/models/workflow_config.py` |
| [`message_kinds`](#message_kinds) | 9 | `MessageKind` · `backend/app/models/workflow_config.py` |
| [`notification_deliveries`](#notification_deliveries) | 13 | `NotificationDelivery` · `backend/app/models/thong_bao.py` |
| [`notification_outbox`](#notification_outbox) | 10 | `NotificationOutbox` · `backend/app/models/thong_bao.py` |
| [`notification_preferences`](#notification_preferences) | 4 | `NotificationPreference` · `backend/app/models/thong_bao.py` |
| [`notification_types`](#notification_types) | 10 | `NotificationType` · `backend/app/models/thong_bao.py` |
| [`priorities`](#priorities) | 5 | `Priority` · `backend/app/models/workflow_config.py` |
| [`processes`](#processes) | 5 | `Process` · `backend/app/models/workflow_config.py` |
| [`rate_limit_hits`](#rate_limit_hits) | 3 | `RateLimitHit` · `backend/app/models/van_hanh.py` |
| [`request_type_fields`](#request_type_fields) | 9 | `RequestTypeField` · `backend/app/models/workflow_config.py` |
| [`request_type_routing`](#request_type_routing) | 3 | `RequestTypeRouting` · `backend/app/models/workflow_config.py` |
| [`request_types`](#request_types) | 12 | `RequestType` · `backend/app/models/workflow_config.py` |
| [`requests`](#requests) | 31 | `Request` · `backend/app/models/case.py` |
| [`roles`](#roles) | 5 | `Role` · `backend/app/models/workflow_config.py` |
| [`rule_sets`](#rule_sets) | 7 | `RuleSet` · `backend/app/models/workflow_config.py` |
| [`scanner_heartbeats`](#scanner_heartbeats) | 8 | `ScannerHeartbeat` · `backend/app/models/van_hanh.py` |
| [`states`](#states) | 8 | `State` · `backend/app/models/workflow_config.py` |
| [`transition_conditions`](#transition_conditions) | 6 | `TransitionCondition` · `backend/app/models/workflow_config.py` |
| [`transition_guards`](#transition_guards) | 2 | `TransitionGuard` · `backend/app/models/workflow_config.py` |
| [`transition_roles`](#transition_roles) | 2 | `TransitionRole` · `backend/app/models/workflow_config.py` |
| [`transitions`](#transitions) | 19 | `Transition` · `backend/app/models/workflow_config.py` |
| [`webhook_deliveries`](#webhook_deliveries) | 10 | `WebhookDelivery` · `backend/app/models/webhook.py` |
| [`webhook_subscriptions`](#webhook_subscriptions) | 9 | `WebhookSubscription` · `backend/app/models/webhook.py` |

6 bảng khác không có lớp mô hình — dịch vụ đọc và ghi chúng bằng SQL thô, nên trang
này chưa liệt kê cột; định nghĩa đầy đủ ở tệp bản sửa tạo ra chúng:

| Bảng | Tạo ở |
|---|---|
| `holidays` | `backend/alembic/sql/0000_luoc_do_cau_hinh.sql` |
| `knowledge_articles` | `backend/alembic/versions/0027_bai_tri_thuc.py` |
| `similar_case_index` | `backend/alembic/versions/0022_ho_so_tuong_tu.py` |
| `similar_case_views` | `backend/alembic/versions/0022_ho_so_tuong_tu.py` |
| `work_calendars` | `backend/alembic/sql/0000_luoc_do_cau_hinh.sql` |
| `work_hours` | `backend/alembic/sql/0000_luoc_do_cau_hinh.sql` |

## attachment_file_types

Cách kiểm nội dung một đuôi tệp đính kèm (#248) — dữ liệu, nạp từ infra/seed/04.

Mô hình `AttachmentFileType` trong `backend/app/models/case.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `extension` | `Text` | không | khóa chính |  |
| `content_type` | `Text` | không |  |  |
| `signatures` | `ARRAY(Text)` | không |  | Mẫu hex, `??` là byte bất kỳ; khớp một mẫu là đạt |
| `search_bytes` | `Integer` | không |  | 0: mẫu nằm ngay đầu tệp; lớn hơn 0: nằm đâu đó trong chừng ấy byte đầu |
| `text_only` | `Boolean` | không |  |  |
| `macro_check` | `Text` | có |  | `ooxml`, `ole` hoặc rỗng |
| `always_macro` | `Boolean` | không |  |  |
| `note` | `Text` | có |  |  |

## case_attachments

Một tệp đính kèm trên hồ sơ (#80).

Mô hình `CaseAttachment` trong `backend/app/models/case.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `case_id` | `BigInteger` | không | khóa ngoại → `requests.id` |  |
| `filename` | `Text` | không |  | Tên người dùng đặt, đã làm sạch. Chỉ để hiển thị và đặt tên tệp lúc tải về |
| `content_type` | `Text` | không |  |  |
| `size_bytes` | `BigInteger` | không |  |  |
| `storage_key` | `Text` | không | duy nhất |  |
| `uploaded_by` | `Text` | không |  | Định danh `sub` và tên tại thời điểm đính kèm — cùng lý do với `author_label` |
| `uploaded_by_label` | `Text` | không |  |  |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |
| `has_macro` | `Boolean` | không | mặc định `'false'` | Tệp mang macro (#248): nhận nhưng giao diện cảnh báo ở mọi nơi liệt kê tệp |
| `scan_status` | `Text` | không | mặc định `'disabled'` | Kết quả quét mã độc lúc đính kèm (#248): `disabled` (quét tắt), `clean`, `unscanned` (quét bật mà dịch vụ quét không phản hồi, chính sách cho nhận) |

## case_feedback

Mức hài lòng người gửi chấm khi xác nhận hồ sơ hoàn tất (#433).

Mô hình `CaseFeedback` trong `backend/app/models/case.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `case_id` | `BigInteger` | không | khóa ngoại → `requests.id` |  |
| `event_id` | `BigInteger` | không | khóa ngoại → `event_log.id`, duy nhất | Dòng nhật ký của lần xác nhận mang điểm này — gắn điểm với đúng chu kỳ xử lý |
| `score` | `SmallInteger` | không |  | Điểm 1–5, ràng buộc CHECK ở cơ sở dữ liệu |
| `comment` | `Text` | có |  | Nhận xét chữ, tùy chọn; chỉ trang hồ sơ của điều phối viên, phòng ban và chính người gửi đọc |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |

## case_message_reads

Một người đã đọc lời nhắn của một hồ sơ tới đâu — cho hộp thư chung (#155).

Mô hình `CaseMessageRead` trong `backend/app/models/case.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `case_id` | `BigInteger` | không | khóa chính, khóa ngoại → `requests.id` |  |
| `reader` | `Text` | không | khóa chính |  |
| `internal` | `Boolean` | không | khóa chính | Mốc của cuộc nội bộ — lời nhắn thuộc loại `hidden_from_requester` |
| `last_read_id` | `BigInteger` | không | khóa ngoại → `case_messages.id` |  |
| `read_at` | `DateTime` | không | mặc định `func.now()` |  |

## case_messages

Một lời nhắn trên hồ sơ (#128, ADR-0005).

Mô hình `CaseMessage` trong `backend/app/models/case.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `case_id` | `BigInteger` | không | khóa ngoại → `requests.id` |  |
| `kind` | `Text` | không | khóa ngoại → `message_kinds.code` |  |
| `author` | `Text` | không |  |  |
| `author_label` | `Text` | không |  |  |
| `body` | `Text` | có |  |  |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |

## cold_archives

Một bản lưu trữ lạnh đã niêm phong: một tháng UTC, mọi quy trình.

Mô hình `ColdArchive` trong `backend/app/models/luu_tru.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `period` | `Text` | không | khóa chính | Kỳ dạng `YYYY-MM`, tính theo UTC như mốc trong nhật ký |
| `bucket` | `Text` | không |  | Thùng và tiền tố khóa trong kho đối tượng lúc xuất — đổi cấu hình về sau không làm mất dấu bản cũ |
| `object_prefix` | `Text` | không |  |  |
| `schema_version` | `SmallInteger` | không |  |  |
| `event_rows` | `Integer` | không |  |  |
| `case_rows` | `Integer` | không |  |  |
| `manifest` | `JSONB` | không |  | Bản sao nguyên văn của manifest.json trong kho, và mã băm của chính tệp đó |
| `manifest_sha256` | `Text` | không |  |  |
| `exported_at` | `DateTime` | không | mặc định `text('now()')` |  |

## config_changes

Một trường cấu hình bị quản trị viên sửa trên màn quản trị: ai, lúc nào, từ đâu sang đâu.

Mô hình `ConfigChange` trong `backend/app/models/quan_tri.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `changed_at` | `DateTime` | không | mặc định `func.now()` |  |
| `actor_id` | `Text` | không |  |  |
| `actor_label` | `Text` | có |  |  |
| `entity` | `Text` | không |  |  |
| `entity_code` | `Text` | không |  |  |
| `field` | `Text` | không |  |  |
| `old_value` | `JSONB` | không |  |  |
| `new_value` | `JSONB` | không |  |  |

## delegations

Người vắng cho một người cùng phòng mang vai của mình trong phòng đó, trong một khoảng thời gian.

Mô hình `Delegation` trong `backend/app/models/quan_tri.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `delegator_id` | `Text` | không |  |  |
| `delegator_label` | `Text` | không |  |  |
| `delegate_id` | `Text` | không |  |  |
| `delegate_label` | `Text` | không |  |  |
| `department_code` | `Text` | không | khóa ngoại → `departments.code` |  |
| `roles` | `ARRAY(Text)` | không |  |  |
| `starts_at` | `DateTime` | không |  |  |
| `ends_at` | `DateTime` | không |  |  |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |
| `created_by_id` | `Text` | không |  |  |
| `created_by_label` | `Text` | không |  |  |
| `revoked_at` | `DateTime` | có |  |  |
| `revoked_by_id` | `Text` | có |  |  |
| `revoked_by_label` | `Text` | có |  |  |

## departments

Phòng ban. Doanh nghiệp triển khai tự khai lại theo cơ cấu của mình.

Mô hình `Department` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `is_active` | `Boolean` | không |  |  |
| `display_order` | `SmallInteger` | không |  |  |

## event_log

Nhật ký sự kiện — tài sản quý nhất của hệ thống.

Mô hình `EventLog` trong `backend/app/models/case.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `case_id` | `BigInteger` | không | khóa ngoại → `requests.id` |  |
| `activity` | `Text` | không |  |  |
| `timestamp` | `DateTime` | không | mặc định `func.now()` | Kiểu TIMESTAMPTZ: PostgreSQL luôn quy về UTC lúc lưu, bất kể múi giờ của phía ghi vào. Lưu giờ cục bộ sẽ làm sai lệch khai phá quy trình khi so sánh giữa các bản ghi sinh ra ở nhiều máy. |
| `actor` | `Text` | không |  |  |
| `actor_label` | `Text` | có |  | Tên hiển thị của người thực hiện, ghi lại tại thời điểm hành động. Cố ý lưu kèm thay vì tra ngược từ Keycloak lúc đọc: người nghỉ việc thì tài khoản bị xóa, người đổi tên thì lịch sử sẽ kể sai. |
| `from_state` | `Text` | không |  |  |
| `to_state` | `Text` | không |  |  |
| `note` | `Text` | có |  |  |
| `changes` | `JSONB` | có |  | Trường quyết định mà lần chuyển này ĐỔI giá trị, dạng {trường: {"from", "to"}} — người xử lý kèm thêm "from_label", "to_label" là tên tại thời điểm đổi (#100). Hồ sơ chỉ mang giá trị hiện tại; lịch sử đổi nằm ở đây. NULL khi không đổi gì. |
| `suggestion` | `JSONB` | có |  | Người giữ hay ghi đè gợi ý của hệ thống ở lần chuyển này (#239), dạng {trường: {"suggested", "chosen", "overridden", "source", "confidence"}} — xem `app/intelligence/goi_y.py`. Cột riêng chứ không nằm trong `changes`, để `changes` giữ đúng một nghĩa "trường nào đổi từ gì sang gì". NULL khi lần chuyển không gửi trường nào có gợi ý, hoặc không nguồn gợi ý nào có giá trị. `none_as_null`: không có nó, SQLAlchemy ghi `None` thành giá trị JSON `null` chứ không phải SQL NULL, và `jsonb_each` của lớp báo cáo nổ "non-object" trên mọi dòng không có gợi ý. |
| `on_behalf_of` | `Text` | có |  | Lần chuyển chỉ đi được nhờ ủy quyền (#252): người vắng mà `actor` làm thay — mã và tên tại thời điểm thao tác. `actor` vẫn là người thật bấm. NULL khi người bấm dùng vai của chính mình. |
| `on_behalf_of_label` | `Text` | có |  |  |

## guards

Một loại ràng buộc Poka-yoke kiểm tra lúc chạy.

Mô hình `Guard` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `description` | `Text` | không |  |  |

## idempotency_keys

Khóa trùng lặp `Idempotency-Key` của lệnh tạo hồ sơ và bước chuyển ở lõi `/core/v1` (#426).

Mô hình `IdempotencyKey` trong `backend/app/models/van_hanh.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `actor` | `Text` | không |  | Mã người gọi trong token (`sub`) — tài khoản dịch vụ hay người. Không lưu tên |
| `endpoint` | `Text` | không |  | Phương thức và mẫu đường, ví dụ `POST /core/v1/workflow/requests/{case_id}/transitions` |
| `key` | `Text` | không |  | Giá trị tiêu đề `Idempotency-Key` người gọi gửi: 1–255 ký tự ASCII in được |
| `request_hash` | `Text` | không |  | sha256 của thân yêu cầu chuẩn hóa cộng tham số đường: cùng khóa mà khác lệnh thì bị từ chối |
| `status` | `Text` | không |  | `in_progress` khi lần gọi đang chạy, `completed` khi lệnh đã commit |
| `case_id` | `BigInteger` | có |  | Hồ sơ lệnh đã tạo hay đã chuyển, đặt cùng giao dịch với lệnh |
| `response_status` | `SmallInteger` | có |  | Mã HTTP của lần thành công, trả lại nguyên cho lần gọi lặp. Ghi sau commit, giao dịch riêng |
| `response_body` | `JSONB` | có |  | Thân phản hồi JSON của lần thành công. Trống nếu ghi sau commit hỏng: lần lặp dựng lại chi tiết hồ sơ `case_id` |
| `created_at` | `DateTime` | không | mặc định `func.now()` | Lúc lần gọi đầu giữ khóa |
| `locked_until` | `DateTime` | không |  | Lần đang chạy giữ khóa tới mốc này (`IDEMPOTENCY_LOCK_SECONDS`); quá mốc thì coi là bỏ dở, lần sau chiếm lại |
| `expires_at` | `DateTime` | không |  | Khóa sống tới mốc này (`IDEMPOTENCY_TTL_HOURS`); quá mốc thì gọi lại cùng khóa là lệnh mới |

## message_kind_roles

Vai trò nào gửi được loại lời nhắn nào.

Mô hình `MessageKindRole` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `kind_code` | `Text` | không | khóa chính, khóa ngoại → `message_kinds.code` |  |
| `role_code` | `Text` | không | khóa chính, khóa ngoại → `roles.code` |  |

## message_kinds

Một loại lời nhắn trên hồ sơ (#128, ADR-0005).

Mô hình `MessageKind` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `owner_only` | `Boolean` | không |  | Chỉ người gửi của chính hồ sơ gửi được — như ràng buộc requester-owns-case |
| `department_stage_only` | `Boolean` | không |  | Chỉ gửi được khi hồ sơ nằm trong hàng đợi phòng ban, tập trạng thái suy từ bộ quy tắc |
| `reask_after_hours` | `SmallInteger` | có |  | Gửi lại chỉ được khi phía bên kia đã trả lời, hoặc đã quá chừng này giờ |
| `body_required` | `Boolean` | không |  |  |
| `hidden_from_requester` | `Boolean` | không |  | Trò chuyện nội bộ (#156): người gửi của hồ sơ không thấy, không gửi được — theo hồ sơ, không theo vai trò |
| `display_order` | `SmallInteger` | không |  |  |

## notification_deliveries

Một thư cho một người — vết gửi để đối soát (#251).

Mô hình `NotificationDelivery` trong `backend/app/models/thong_bao.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính |  |
| `outbox_id` | `BigInteger` | không | khóa ngoại → `notification_outbox.id` |  |
| `type_code` | `Text` | không | khóa ngoại → `notification_types.code` |  |
| `case_id` | `Integer` | không | khóa ngoại → `requests.id` |  |
| `recipient_id` | `Text` | không |  |  |
| `status` | `Text` | không |  | `pending` (chờ gửi hay chờ thử lại), `sent`, `failed` (hết lượt thử), `skipped` (người nhận tắt loại này, hay danh bạ không có email) |
| `attempts` | `SmallInteger` | không |  |  |
| `next_attempt_at` | `DateTime` | không | mặc định `func.now()` |  |
| `last_error` | `Text` | có |  |  |
| `subject` | `Text` | có |  | Tiêu đề và nội dung dựng từ mẫu lúc tìm người nhận — thư gửi đi đúng như vết ghi |
| `body` | `Text` | có |  |  |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |
| `sent_at` | `DateTime` | có |  |  |

## notification_outbox

Một sự kiện chờ bộ quét gửi tìm người nhận.

Mô hình `NotificationOutbox` trong `backend/app/models/thong_bao.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính |  |
| `trigger` | `Text` | không |  |  |
| `case_id` | `Integer` | không | khóa ngoại → `requests.id` |  |
| `context` | `JSONB` | không |  | Biến cho mẫu thư chụp lúc sự kiện xảy ra (trạng thái cũ, cạnh tự đi, hạn…) |
| `dedupe_key` | `Text` | có | duy nhất | Khóa chống trùng — mốc báo trước chỉ báo một lần mỗi lần hồ sơ vào trạng thái |
| `actor_id` | `Text` | có |  | Người vừa làm thao tác sinh sự kiện: không gửi thư cho chính họ |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |
| `processed_at` | `DateTime` | có |  |  |
| `attempts` | `SmallInteger` | không |  |  |
| `last_error` | `Text` | có |  |  |

## notification_preferences

Người dùng bật hay tắt một loại thông báo. Không có dòng là theo `default_enabled`.

Mô hình `NotificationPreference` trong `backend/app/models/thong_bao.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `user_id` | `Text` | không | khóa chính |  |
| `type_code` | `Text` | không | khóa chính, khóa ngoại → `notification_types.code` |  |
| `enabled` | `Boolean` | không |  |  |
| `updated_at` | `DateTime` | không | mặc định `func.now()` |  |

## notification_types

Một loại thông báo — dữ liệu, nạp từ infra/seed/05-loai-thong-bao.sql.

Mô hình `NotificationType` trong `backend/app/models/thong_bao.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `trigger` | `Text` | không |  |  |
| `recipients` | `Text` | không |  |  |
| `subject_template` | `Text` | không |  |  |
| `body_template` | `Text` | không |  |  |
| `default_enabled` | `Boolean` | không |  | Người dùng chưa chọn gì thì theo giá trị này |
| `is_active` | `Boolean` | không |  |  |
| `display_order` | `SmallInteger` | không |  |  |

## priorities

Mức độ ưu tiên. Người tạo yêu cầu không bao giờ tự đặt được.

Mô hình `Priority` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `is_default` | `Boolean` | không |  |  |
| `display_order` | `SmallInteger` | không |  |  |
| `sla_factor_percent` | `SmallInteger` | không |  | Hạn của mức này bằng chừng ấy phần trăm hạn chuẩn của loại yêu cầu (#101) |

## processes

Một quy trình của động cơ luồng công việc (#376). Mỗi quy trình có đúng một bộ quy tắc đang bật; loại yêu cầu thuộc một quy trình và quyết định hồ sơ chạy theo quy trình nào.

Mô hình `Process` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `display_order` | `SmallInteger` | không |  |  |
| `is_app_default` | `Boolean` | không |  | Quy trình mà các màn của ứng dụng minh họa dùng — đúng một dòng (kiem_tra_cau_hinh, phép kiểm 11) |

## rate_limit_hits

Số lần gọi trong một cửa sổ thời gian cố định, theo khóa (#243).

Mô hình `RateLimitHit` trong `backend/app/models/van_hanh.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `key` | `Text` | không | khóa chính |  |
| `window_start` | `DateTime` | không | khóa chính |  |
| `hits` | `Integer` | không |  |  |

## request_type_fields

Một trường thông tin riêng của một loại yêu cầu (#250). Xem lược đồ khởi tạo.

Mô hình `RequestTypeField` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `request_type_code` | `Text` | không | khóa chính, khóa ngoại → `request_types.code` |  |
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `kind` | `Text` | không |  |  |
| `required` | `Boolean` | không |  |  |
| `help_text` | `Text` | có |  |  |
| `unit` | `Text` | có |  |  |
| `options` | `ARRAY(Text)` | có |  |  |
| `display_order` | `SmallInteger` | không |  |  |

## request_type_routing

Ánh xạ loại yêu cầu sang phòng ban phụ trách.

Mô hình `RequestTypeRouting` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `request_type_code` | `String` | không | khóa chính, khóa ngoại → `request_types.code` |  |
| `department_code` | `String` | không | khóa chính, khóa ngoại → `departments.code` |  |
| `is_default` | `Boolean` | không |  |  |

## request_types

Loại yêu cầu, kèm ngưỡng SLA riêng.

Mô hình `RequestType` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `process_code` | `Text` | không | khóa ngoại → `processes.code` | Quy trình mà hồ sơ của loại này chạy theo (#376) |
| `label` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `sla_hours` | `Integer` | không |  |  |
| `sla_grace_hours` | `Integer` | không |  | Ân hạn sau mỗi lần hồ sơ vào lại trạng thái đếm giờ — xem rules/sla.py (#94) |
| `sla_warn_percent` | `SmallInteger` | không |  | Đã dùng từ chừng này phần trăm cam kết thì "sắp hết hạn" (#175) |
| `sla_extension_max_percent` | `SmallInteger` | không |  | Gia hạn (#101): mỗi lần tối đa chừng này phần trăm hạn gốc, tổng tối đa chừng ấy lần |
| `sla_extension_max_count` | `SmallInteger` | không |  |  |
| `reopen_max_count` | `SmallInteger` | không |  | Mở lại (#102): tổng số lần người gửi mở lại một hồ sơ; quá thì phải tạo hồ sơ mới |
| `is_active` | `Boolean` | không |  |  |
| `display_order` | `SmallInteger` | không |  |  |

## requests

Một hồ sơ yêu cầu nội bộ.

Mô hình `Request` trong `backend/app/models/case.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `rule_set_id` | `SmallInteger` | không | khóa ngoại → `rule_sets.id` | Bộ quy tắc hồ sơ này chạy theo, ghi lại lúc tạo và giữ nguyên tới khi đóng. Nhờ cột này, quản trị viên sửa luồng giữa chừng không làm hồ sơ đang dở đổi luật giữa đường. |
| `current_state` | `Text` | không |  |  |
| `title` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `requester_id` | `Text` | không |  | Định danh người dùng lấy từ claim `sub` của token Keycloak — xem #43. |
| `requester_label` | `Text` | có |  | Tên người gửi tại thời điểm gửi, cùng lý do với `event_log.actor_label`: tra ngược từ Keycloak lúc đọc thì người nghỉ việc mất tên, người đổi tên thì hồ sơ cũ hiện tên mới. Việc tạo hồ sơ không sinh dòng nhật ký nào, nên tên phải nằm ở đây. NULL với hồ sơ có trước #82 — giao diện lùi về hiển thị mã định danh. |
| `request_type_code` | `Text` | có | khóa ngoại → `request_types.code` | --- Trường QUYẾT ĐỊNH: chỉ con người ghi ------------------------------ Người gửi đặt loại yêu cầu ngay lúc tạo hồ sơ — họ là người biết rõ nhất mình đang cần gì, và người phân loại vẫn sửa lại được ở cạnh `submitted -> classified` nếu chọn sai. Ba trường còn lại rỗng cho tới khi người có thẩm quyền đi cạnh tương ứng: người phân loại đặt mức ưu tiên và phòng ban, người xét duyệt đặt người xử lý. Vì sao loại yêu cầu mở cho người gửi mà mức ưu tiên thì không: chọn sai loại chỉ làm hồ sơ đi chậm một nhịp và người phân loại nắn lại ngay, còn ai cũng đánh dấu yêu cầu của mình là khẩn thì thứ tự ưu tiên mất hết ý nghĩa. Đây là ràng buộc Poka-yoke *người gửi không tự đặt mức ưu tiên*. |
| `department_code` | `Text` | có | khóa ngoại → `departments.code` |  |
| `priority_code` | `Text` | có | khóa ngoại → `priorities.code` |  |
| `assignee_id` | `Text` | có |  |  |
| `assignee_label` | `Text` | có |  | Tên người được giao tại thời điểm giao, cùng lý do với `requester_label`. Không phải trường quyết định — trường quyết định là `assignee_id` ở trên — mà là nhãn đi kèm nó: engine ghi hai cột cùng lúc, và tên lấy từ danh bạ Keycloak chứ không từ trình duyệt (#83). NULL khi chưa giao cho ai. |
| `suggested_request_type_code` | `Text` | có |  | --- Trường GỢI Ý: chỉ tầng I ghi -------------------------------------- NGUYÊN TẮC BẤT DI DỊCH của đề tài: AI chỉ gợi ý, con người quyết định. Tầng I không bao giờ được ghi vào bốn trường quyết định ở trên — xem CLAUDE.md mục 4.3. Không có cột nào trên hồ sơ ghi "người dùng có ghi đè gợi ý hay không": một cột lưu sẵn sẽ lệch khỏi sự thật ngay lần đầu ai đó quên cập nhật nó, và một hồ sơ có thể được xác nhận nhiều lần. Mỗi lần xác nhận là một sự kiện — dấu giữ hay ghi đè nằm ở `EventLog.suggestion`, do cửa chuyển trạng thái ghi (#239). |
| `suggested_department_code` | `Text` | có |  |  |
| `suggested_priority_code` | `Text` | có |  |  |
| `suggested_assignee_id` | `Text` | có |  |  |
| `suggestion_note` | `JSONB` | có |  | Ghi chú của lần sinh gợi ý gần nhất (#317): thành công thì {"ok": true, "model", "at", "elapsed_ms", "reasons": {trường: lý do}, "model_department"}, hỏng thì {"ok": false, "error", "at"}. `model_department` là phòng mô hình đoán, giữ cả khi cờ cho phòng ban của mô hình tắt để đo về sau. Không phải trường quyết định, không phải dấu giữ hay ghi đè (cái đó ở nhật ký). |
| `assignee_suggestion` | `JSONB` | có |  | Gợi ý người xử lý (#318): tên người, lý do, số liệu làm căn cứ, lúc tính — đi cùng `suggested_assignee_id`. Tách khỏi `suggestion_note` của mô hình phân loại: hai đường ghi khác nhau, không đường nào ghi đè ghi chú của đường kia. |
| `suggestion_attempted_at` | `DateTime` | có |  | Mốc lần thử gần nhất và số lần đã thử — bộ quét bù đọc để không hỏi lại mãi một hồ sơ |
| `suggestion_attempts` | `SmallInteger` | không |  |  |
| `sla_running_seconds` | `Integer` | không |  | --- Đồng hồ SLA ------------------------------------------------------- Ba cột thay cho một cột hạn chót cố định, vì đồng hồ có thể dừng rồi chạy lại nhiều lần. Trạng thái nào làm đồng hồ chạy do cột `states.sla_running` quyết định — xem app/rules/sla.py. |
| `sla_paused_seconds` | `Integer` | không |  |  |
| `sla_segment_since` | `DateTime` | có |  | Mốc bắt đầu của đoạn đang tính. NULL nghĩa là đồng hồ chưa từng khởi động, hoặc hồ sơ đã đóng. |
| `sla_extension_hours` | `Integer` | không |  | Gia hạn xử lý (#101). Hạn của hồ sơ = hạn gốc (loại yêu cầu nhân hệ số ưu tiên) cộng tổng số giờ đã gia hạn. Ô người dùng nhập là số giờ của lần này; tổng và số lần do ràng buộc `extend-deadline` tự đặt — xem app/rules/guards.py. |
| `sla_extension_total_hours` | `Integer` | không |  |  |
| `sla_extension_count` | `SmallInteger` | không |  |  |
| `reopen_count` | `SmallInteger` | không |  | Mở lại có giới hạn (#102): đã mở lại mấy lần, tính cả mở lại từ Hoàn tất lẫn từ Đã đóng. Do ràng buộc `reopen-limit` tự đặt, người dùng không gửi được. |
| `parent_request_id` | `BigInteger` | có | khóa ngoại → `requests.id` | Hồ sơ này được tạo lại từ hồ sơ nào (#102): hết lượt mở lại, quá cửa sổ mở lại hay bị Không tiếp nhận thì người gửi tạo hồ sơ mới và liên kết hồ sơ cũ. Chỉ đặt lúc tạo. |
| `details` | `JSONB` | không |  | Trường thông tin riêng theo loại yêu cầu (#250): {mã trường: giá trị}, mã khai ở bảng cấu hình `request_type_fields`. Kiểm ở `app/rules/truong_rieng.py`, đổi qua cạnh Sửa nội dung như tiêu đề và mô tả — nhật ký giữ giá trị cũ. |
| `created_at` | `DateTime` | không | mặc định `func.now()` | --- Mốc thời gian, luôn UTC ------------------------------------------- |
| `updated_at` | `DateTime` | không | mặc định `func.now()` |  |

## roles

Vai trò nghiệp vụ. Mã trùng tên vai trò realm trong Keycloak.

Mô hình `Role` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `display_order` | `SmallInteger` | không |  |  |
| `report_scope` | `Text` | có |  | Phạm vi xem bảng điều khiển phân tích (#305): `department`, `all`, hay không thấy |

## rule_sets

Phiên bản bộ quy tắc của một quy trình. Hồ sơ cũ chạy theo quy tắc cũ.

Mô hình `RuleSet` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `SmallInteger` | không | khóa chính |  |
| `process_code` | `Text` | không | khóa ngoại → `processes.code` |  |
| `version` | `Text` | không | duy nhất |  |
| `label` | `Text` | không |  |  |
| `effective_from` | `DateTime` | không |  |  |
| `is_active` | `Boolean` | không |  |  |
| `note` | `Text` | có |  |  |

## scanner_heartbeats

Nhịp của một bộ quét nền: lần chạy cuối, lần thành công cuối, lần lỗi cuối (#253).

Mô hình `ScannerHeartbeat` trong `backend/app/models/van_hanh.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `name` | `Text` | không | khóa chính |  |
| `last_started_at` | `DateTime` | có |  |  |
| `last_success_at` | `DateTime` | có |  |  |
| `last_error_at` | `DateTime` | có |  |  |
| `last_error` | `Text` | có |  | Câu lỗi ngắn của lần hỏng gần nhất. Chỉ quản trị viên đọc được (màn Hệ thống), không bao giờ nằm trong `/health` công khai |
| `consecutive_errors` | `Integer` | không | mặc định `text('0')` | Số lượt hỏng liên tiếp tính từ lần thành công cuối; một lượt thành công đặt về 0 |
| `runner_host` | `Text` | có |  | Bản dịch vụ chạy lượt gần nhất — tên máy chủ (trong Docker là mã container) và mã tiến trình |
| `runner_pid` | `Integer` | có |  |  |

## states

Một trạng thái trong vòng đời hồ sơ.

Mô hình `State` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `rule_set_id` | `SmallInteger` | không | khóa chính, khóa ngoại → `rule_sets.id` |  |
| `code` | `Text` | không | khóa chính |  |
| `label` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `is_initial` | `Boolean` | không |  |  |
| `is_terminal` | `Boolean` | không |  |  |
| `sla_running` | `Boolean` | không |  | Đồng hồ SLA có chạy khi hồ sơ nằm ở trạng thái này không. Một cột này trả lời cả hai câu: đồng hồ bắt đầu từ đâu, và dừng ở đâu. |
| `display_order` | `SmallInteger` | không |  |  |

## transition_conditions

Điều kiện trên một cạnh (#397): so trường riêng `field_code` của hồ sơ với `value` bằng `operator`.

Mô hình `TransitionCondition` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `Integer` | không | khóa chính |  |
| `transition_id` | `Integer` | không | khóa ngoại → `transitions.id` |  |
| `field_code` | `Text` | không |  |  |
| `operator` | `Text` | không |  |  |
| `value` | `JSONB` | không |  |  |
| `description` | `Text` | có |  |  |

## transition_guards

Gán một ràng buộc Poka-yoke cho một cạnh cụ thể.

Mô hình `TransitionGuard` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `transition_id` | `Integer` | không | khóa chính, khóa ngoại → `transitions.id` |  |
| `guard_code` | `Text` | không | khóa chính, khóa ngoại → `guards.code` |  |

## transition_roles

Ma trận phân quyền: vai trò nào đi được cạnh nào.

Mô hình `TransitionRole` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `transition_id` | `Integer` | không | khóa chính, khóa ngoại → `transitions.id` |  |
| `role_code` | `Text` | không | khóa chính, khóa ngoại → `roles.code` |  |

## transitions

Một cạnh hợp lệ giữa hai trạng thái.

Mô hình `Transition` trong `backend/app/models/workflow_config.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `Integer` | không | khóa chính |  |
| `rule_set_id` | `SmallInteger` | không | khóa ngoại → `rule_sets.id` |  |
| `from_state` | `Text` | không |  |  |
| `to_state` | `Text` | không |  |  |
| `activity_code` | `Text` | không |  |  |
| `activity_label` | `Text` | không |  |  |
| `is_system` | `Boolean` | không |  |  |
| `requires_note` | `Boolean` | không |  |  |
| `note_label` | `Text` | có |  | Tên ô ghi chú của cạnh này (#79). Trống thì giao diện gọi nó là "Lý do"; cạnh bổ sung thông tin gọi nó là "Thông tin bổ sung", vì ở đó ghi chú là câu trả lời chứ không phải lời giải thích. |
| `display_order` | `SmallInteger` | không |  |  |
| `is_rework` | `Boolean` | không |  | Cạnh làm lại (#153): đi qua là hồ sơ bị đẩy ngược để làm lại. Dòng thời gian đếm quay lui theo cờ này — xem lược đồ khởi tạo. |
| `auto_after_hours` | `SmallInteger` | có |  | Cạnh hệ thống tự đi sau chừng này giờ làm việc ở trạng thái nguồn, và báo trước chừng này giờ (#142). NULL là không tự đi theo thời gian chờ. |
| `warn_before_hours` | `SmallInteger` | có |  |  |
| `from_is_terminal` | `Boolean` | không |  | Trạng thái nguồn có phải trạng thái kết thúc không; khóa ngoại tổng hợp buộc nó khớp với `states.is_terminal`. Cạnh rời khỏi trạng thái kết thúc chỉ được là cạnh mở lại có cửa sổ thời gian (#102). Mã nguồn không đọc hay ghi cột này. |
| `reopen_window_hours` | `SmallInteger` | có |  | Cạnh mở lại sau khi hồ sơ kết thúc (#102): đi được khi hồ sơ vào trạng thái kết thúc chưa quá chừng này giờ làm việc. NULL là cạnh thường. |
| `restarts_sla` | `Boolean` | không |  | Đi qua cạnh này là mở chu kỳ xử lý mới: đồng hồ SLA đếm lại từ 0 (#102) |
| `accepts_attachments` | `Boolean` | không |  | Người đang đứng ở cạnh này đính kèm được tệp vào hồ sơ (#80) |
| `collects_feedback` | `Boolean` | không |  | Người đi cạnh này chấm được mức hài lòng 1–5 kèm nhận xét, đều tùy chọn (#433) — cạnh Xác nhận đạt |
| `primary_scope` | `Text` | có |  | Bước chính ở trạng thái nguồn (#227): NULL, 'role' hay 'assignee' — xem lược đồ khởi tạo |

## webhook_deliveries

Một lần đưa một sự kiện tới một đăng ký, kèm vết các lần thử.

Mô hình `WebhookDelivery` trong `backend/app/models/webhook.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `subscription_id` | `BigInteger` | không | khóa ngoại → `webhook_subscriptions.id` |  |
| `event_id` | `BigInteger` | không | khóa ngoại → `event_log.id` |  |
| `status` | `Text` | không |  |  |
| `attempts` | `Integer` | không |  |  |
| `next_attempt_at` | `DateTime` | không | mặc định `func.now()` |  |
| `last_status_code` | `Integer` | có |  |  |
| `last_error` | `Text` | có |  |  |
| `delivered_at` | `DateTime` | có |  |  |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |

## webhook_subscriptions

Một địa chỉ nhận sự kiện. `activities`, `process_code` để trống là nhận mọi sự kiện.

Mô hình `WebhookSubscription` trong `backend/app/models/webhook.py`.

| Cột | Kiểu | Để trống | Ràng buộc | Ý nghĩa |
|---|---|---|---|---|
| `id` | `BigInteger` | không | khóa chính, `Identity` |  |
| `url` | `Text` | không |  |  |
| `secret` | `Text` | không |  |  |
| `description` | `Text` | có |  |  |
| `activities` | `ARRAY(Text)` | có |  |  |
| `process_code` | `Text` | có | khóa ngoại → `processes.code` |  |
| `is_active` | `Boolean` | không |  |  |
| `owner_id` | `Text` | không |  |  |
| `created_at` | `DateTime` | không | mặc định `func.now()` |  |
