---
title: API
description: Tài liệu API của dịch vụ ứng dụng, tự sinh từ mã nguồn theo chuẩn OpenAPI.
sidebar:
  order: 1
---

Dịch vụ ứng dụng (FastAPI) tự sinh tài liệu API theo chuẩn **OpenAPI** từ chính mã nguồn, nên tài
liệu luôn khớp phiên bản đang chạy. Mọi lời gọi API từ ngoài cụm đi qua **cổng API** (Apache APISIX) ở
cổng `9080` — đường dẫn giữ nguyên như của dịch vụ. Khi cụm đang chạy:

| Địa chỉ | Nội dung |
|---|---|
| `http://localhost:9080/docs` | Giao diện tương tác — xem và gọi thử từng điểm cuối (nút **Authorize** để dán token) |
| `http://localhost:9080/redoc` | Bản đọc dạng tài liệu |
| `http://localhost:9080/openapi.json` | Bản đặc tả máy đọc được, dùng sinh mã khách |
| `http://localhost:9080/health` | Tình trạng chung (`ok` / `degraded`), không cần đăng nhập, không chi tiết lỗi |
| `http://localhost:9080/system/health` | Chi tiết sức khỏe và nhịp bộ quét, chỉ quản trị viên (màn Hệ thống đọc từ đây) |

Dịch vụ ứng dụng không mở cổng `8000` ra máy ở cấu hình mặc định; gọi thẳng nó chỉ được khi thêm tệp
`docker-compose.phat-trien.yml` — xem [Cài đặt](../../cai-dat/cai-dat/).

Không cần dựng cụm để đọc **hợp đồng API của nền tảng lõi**: đặc tả OpenAPI riêng các đường dưới `/core/v1`
nằm trong kho ở
[`docs/api/core-v1.openapi.json`](https://github.com/AlaVox-lab/corelens/blob/main/docs/api/core-v1.openapi.json)
— mở bằng bất kỳ công cụ đọc OpenAPI nào, hoặc sinh mã khách từ đó. Tệp sinh từ mã nguồn bằng
`python scripts/dac_ta_loi.py --anh dxlab-backend:<phiên bản>`; CI sinh lại ở mỗi PR và báo đỏ khi API lõi
đổi mà tệp chưa cập nhật, nên mỗi lần hợp đồng đổi đều hiện trong lịch sử git.

## Xác thực

Mọi điểm cuối, trừ `/`, `/health`, `/health/live`, `/health/ready` và bốn đường tài liệu ở trên, cần
**token truy cập** do Keycloak cấp, gửi trong header `Authorization: Bearer <token>`. Token được kiểm
**hai lần**:

1. **Tại cổng API** — chữ ký theo khóa công khai của Keycloak, nơi phát, hạn dùng, và `dx-api` trong
   trường `aud`. Hỏng thì lời gọi không tới dịch vụ: thiếu token, hết hạn, ký sai nhận `401` kèm
   `WWW-Authenticate`; token phát cho client khác nhận `403`
2. **Tại dịch vụ** — kiểm lại đủ bốn thứ trên, rồi đọc vai trò và phòng ban trong token để phân quyền

Cổng người dùng giữ token ở phía máy chủ và tự gắn vào lời gọi — trình duyệt không bao giờ thấy token.
Lời gọi của cổng người dùng cũng đi qua cổng API.

## API của nền tảng lõi — `/core/v1`

Đề thi tách **nền tảng lõi không giao diện** (Tầng 1) khỏi **ứng dụng minh họa** (Tầng 2). Phần API dành
cho mọi ứng dụng tầng trên nằm dưới tiền tố có phiên bản `/core/v1`, nhóm theo dịch vụ lõi; trong `/docs`
sáu nhóm này đứng đầu, nhãn bắt đầu bằng **"Lõi — "**. Các đường còn lại thuộc ứng dụng minh họa — cổng vận
hành yêu cầu nội bộ — và có thể đổi theo giao diện của nó.

| Nhóm | Điểm cuối |
|---|---|
| Luồng công việc | `GET /core/v1/workflow/processes` — danh mục quy trình · `GET /core/v1/workflow/request-types`, `/states` (`?process=`), `/priorities`, `/departments` — danh mục cấu hình · `POST /core/v1/workflow/requests` — tạo hồ sơ, loại yêu cầu quyết định quy trình · `GET /core/v1/workflow/requests` (`?process=`, `needs_action=true`), `/requests/{case_id}` — danh sách, chi tiết kèm **bước đi được** (`allowed_transitions`) và **lịch sử** (`history`) · `GET /core/v1/workflow/requests/{case_id}/transition-options` — mọi bước kèm **lý do chưa đi được** (chỉ có ở lõi) · `POST /core/v1/workflow/requests/{case_id}/transitions` — đi một bước |
| Tệp | `GET /core/v1/files/policy` · `POST /core/v1/files/requests/{case_id}/attachments` · `GET /core/v1/files/{attachment_id}` |
| Nhật ký sự kiện | `GET /core/v1/events?format=csv\|json\|xes&from=…&to=…&process=…` — chỉ quản trị viên; mỗi dòng mang `process_code`; `xes` mở thẳng bằng công cụ khai phá quy trình (ProM, Disco, PM4Py) |
| Lưu trữ lạnh | `GET /core/v1/archive` — các bản lưu theo tháng · `GET /core/v1/archive/{YYYY-MM}` — bản kê (`manifest`, số dòng, SHA-256) và liên kết tải · `GET /core/v1/archive/{YYYY-MM}/files/{tệp}` — tải một tệp; chỉ quản trị viên, chỉ có ở lõi |
| Thông báo | `GET /core/v1/notifications/preferences` · `POST /core/v1/notifications/preferences/{code}` |
| Định danh | `GET /core/v1/identity/me` |

Mỗi đường của lõi là **cùng một điểm cuối** với một đường cũ mà cổng người dùng đang dùng (ví dụ
`/core/v1/workflow/states` và `/states`): cùng kết quả, cùng phân quyền, cùng giới hạn tốc độ. Riêng danh
sách, chi tiết và bước chuyển hồ sơ khác ở **phạm vi** (xem dưới). Bảng ánh xạ đầy đủ và danh sách điểm cuối
thuộc ứng dụng minh họa ở `docs/ARCHITECTURE.md` mục 2.3.

### Nhiều quy trình

Động cơ luồng công việc chạy **nhiều quy trình** cùng lúc. Mỗi quy trình có bộ trạng thái, bước chuyển, vai
đi được và hạn xử lý riêng — toàn là dữ liệu; mỗi loại yêu cầu thuộc một quy trình, nên tạo hồ sơ bằng loại
nào là chạy quy trình đó. Dữ liệu mẫu có hai quy trình: cổng yêu cầu nội bộ (quy trình của ứng dụng minh
họa) và **đề xuất mua sắm duyệt hai cấp** — người đề xuất gửi, trưởng phòng của phòng đề xuất duyệt, điều
phối viên duyệt cấp hai. Các điểm cuối đọc theo quy trình nhận `process=<mã>`; bỏ trống là quy trình của ứng
dụng minh họa.

Danh sách, chi tiết và bước chuyển hồ sơ dưới `/core/v1` **trung lập với vai**: người gọi thấy hồ sơ mình
tạo, hồ sơ của phòng mình nếu mang vai phòng ban, mọi hồ sơ nếu là điều phối viên — hồ sơ ngoài phạm vi trả
`404`. Đi bước nào thì engine quyết theo vai và ràng buộc của bước, như trên giao diện: trưởng phòng duyệt
được đề xuất của phòng mình, người gửi gọi nhầm bước của trưởng phòng nhận `403`. Đường cũ `/requests` của
cổng người dùng vẫn chỉ là hồ sơ do chính người gọi tạo.

### Bước chưa đi được và vì sao

`allowed_transitions` của chi tiết hồ sơ chỉ có bước người gọi đi được. Ứng dụng muốn nói với người dùng vì
sao một nút không có thì gọi `GET /core/v1/workflow/requests/{case_id}/transition-options`: **mọi** bước rời
trạng thái hiện tại (theo thứ tự hiển thị của quy trình), mỗi bước mang

- `allowed` — người gọi đi được lúc này không. Tập bước `allowed` trùng hệt `allowed_transitions`: hai đường
  dùng chung một hàm xét bước của engine
- `reasons` — rỗng khi đi được; mỗi lý do có `code`, `category`, `message` (câu tiếng Việt của chính lỗi mà
  engine sẽ trả nếu cứ gọi bước đó) và `condition`:

  | `category` | `code` | Khi nào |
  |---|---|---|
  | `role-not-permitted` | `role-not-permitted` | Vai của người gọi không đi được bước này. Sai vai thì chỉ có lý do này — ràng buộc không xét, như engine |
  | `system-transition-only` | `system-transition-only` | Bước do hệ thống tự đi (leo thang, tự đóng) |
  | `guard-violation` | mã ràng buộc, ví dụ `actor-in-case-department`, `actor-not-requester`, `requester-owns-case` | Một ràng buộc không cần nhập liệu từ chối; vướng nhiều ràng buộc thì đủ cả |
  | `guard-violation` | `edge-condition` | Hồ sơ chưa thỏa điều kiện trên bước; `condition` mang `id`, `field`, `operator`, `value` của dòng điều kiện |
- `requires_input` — trường nhập liệu gửi trong `changes` khi đi bước (ví dụ phân loại: `request_type_code`,
  `priority_code`). Ràng buộc trên các trường này chỉ xét lúc đi thật, nên bước vẫn `allowed` mà giá trị gửi
  sai vẫn bị từ chối; `requires_note`, `note_label` — bước bắt buộc ghi chú

Chỉ đọc — không ghi nhật ký, không đổi hồ sơ. Phạm vi nhìn thấy như chi tiết hồ sơ: ngoài phạm vi `404`; hồ
sơ ở trạng thái không còn bước nào đi ra thì `transitions` rỗng. Ví dụ, tài khoản dịch vụ vai `requester` ở
"Đã gửi" (rút gọn còn hai bước):

```json
{
  "case_id": 1979,
  "state": {"code": "submitted", "label": "Đã gửi", "is_terminal": false},
  "transitions": [
    {"activity_code": "classify", "activity_label": "Phân loại yêu cầu", "to_state": "classified",
     "to_state_label": "Đã phân loại", "keeps_state": false, "is_system": false, "allowed": false,
     "reasons": [{"code": "role-not-permitted", "category": "role-not-permitted", "condition": null,
                  "message": "Vai trò hiện tại không thực hiện được “Phân loại yêu cầu”. Bước này dành cho: Điều phối viên."}],
     "requires_input": ["request_type_code", "priority_code"], "requires_note": false, "note_label": null},
    {"activity_code": "cancel", "activity_label": "Hủy yêu cầu", "to_state": "cancelled",
     "to_state_label": "Đã hủy", "keeps_state": false, "is_system": false, "allowed": true,
     "reasons": [], "requires_input": [], "requires_note": false, "note_label": null}
  ]
}
```

### Quy trình dạng BPMN 2.0

`GET /core/v1/workflow/processes/{code}/bpmn` trả bộ quy tắc đang bật của quy trình `code` thành tệp **BPMN
2.0** (chuẩn OMG, ISO/IEC 19510) kèm bố cục sơ đồ, tải về tên `<code>.bpmn`. Kéo tệp vào
[demo.bpmn.io](https://demo.bpmn.io) hay mở bằng Camunda Modeler là thấy sơ đồ quy trình:

- trạng thái thành `userTask`, trạng thái kết thúc thành `endEvent`, một `startEvent` dẫn vào trạng thái đầu
- mỗi cạnh thành `sequenceFlow` mang nhãn hoạt động; cạnh hệ thống tự đi ghi "(tự động)"; vai đi được, ghi chú
  bắt buộc, cạnh làm lại nằm trong `documentation` của cạnh

Xuất một chiều để đọc, trao đổi với người phân tích nghiệp vụ hay mang sang công cụ khác — sửa quy trình vẫn là
sửa dữ liệu cấu hình ([Tùy biến quy trình](../../quan-tri/tuy-bien-quy-trinh/)). Mọi tài khoản đăng nhập gọi
được, như danh mục quy trình.

### Token cho ứng dụng khác: tài khoản dịch vụ

Một ứng dụng không có người dùng đăng nhập (phần mềm nhân sự, ứng dụng di động, kịch bản tích hợp) xin token
bằng **luồng client credentials** của Keycloak, với client `dx-integration` — biến `KEYCLOAK_INTEGRATION_*`
trong `.env`, xem [Cấu hình](../../cai-dat/cau-hinh/):

```bash
curl -s http://localhost:8080/realms/dx-os-lab/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=dx-integration \
  -d client_secret=<KEYCLOAK_INTEGRATION_SECRET>
```

Token mang `dx-api` trong `aud` và vai `requester`, nên qua được cổng API và dịch vụ như token của người dùng
— không phép kiểm nào được nới. Hồ sơ tài khoản dịch vụ tạo mang nhãn người gửi là tên client
(`dx-integration`). Rồi gọi lõi qua cổng API:

```bash
curl -s http://localhost:9080/core/v1/workflow/request-types -H "Authorization: Bearer <token>"
```

Ví dụ đầy đủ, chỉ dùng thư viện chuẩn của Python: `examples/goi-loi/` — `goi_loi.py` tạo một hồ sơ, đi một
bước, in lịch sử; `quy_trinh_mua_sam.py` chạy trọn quy trình thứ hai tới khi duyệt xong bằng ba tài khoản
dịch vụ — người đề xuất, trưởng phòng (`dx-integration-truong-phong`), người duyệt cấp hai
(`dx-integration-duyet`) — toàn bộ qua `/core/v1`. Cụm dựng trước bản có `/core/v1` thì tạo client trước bằng
`python scripts/tai_khoan_dich_vu.py` — xem [Nâng cấp](../../cai-dat/nang-cap/).

### Gọi lặp an toàn: `Idempotency-Key`

Mạng đứt sau khi gửi lệnh thì ứng dụng không biết lệnh đã chạy chưa. Gửi lại mà không có khóa thì hồ sơ có
thể bị tạo hai lần, hay đi một bước hai lần. Hai lệnh ghi của lõi — `POST /core/v1/workflow/requests` (tạo hồ
sơ) và `POST /core/v1/workflow/requests/{case_id}/transitions` (đi một bước) — nhận tiêu đề **tùy chọn**
`Idempotency-Key`: mỗi lệnh một chuỗi riêng (một UUID là đủ), gửi lại thì dùng đúng chuỗi đó.

```bash
KHOA=$(uuidgen)   # sinh một lần cho lệnh này, giữ lại để gửi lại
curl -s -i http://localhost:9080/core/v1/workflow/requests/42/transitions \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: $KHOA" \
  -H "Content-Type: application/json" \
  -d '{"to_state": "cancelled", "note": "Gửi nhầm"}'
# Mất kết nối? Gửi lại nguyên lệnh trên, cùng $KHOA: nhận lại đúng phản hồi lần đầu kèm
# "Idempotent-Replayed: true", bước không đi lần hai, nhật ký sự kiện chỉ có một dòng
```

| Tình huống | Phản hồi |
|---|---|
| Lần đầu với khóa này | Lệnh chạy như thường (`201` khi tạo, `200` khi đi bước) |
| Gửi lại cùng khóa, cùng lệnh | Đúng mã và thân của lần đầu, thêm tiêu đề `Idempotent-Replayed: true`; lệnh không chạy lại, không sinh sự kiện, không gửi webhook |
| Gửi lại khi lần đầu còn đang chạy | `409` `idempotency-request-in-progress` kèm `Retry-After` (giây) — chờ rồi gửi lại |
| Cùng khóa nhưng khác thân hay khác hồ sơ | `422` `idempotency-key-reused` — mỗi lệnh cần khóa riêng |
| Khóa rỗng, dài quá 255 ký tự hay có ký tự ngoài ASCII in được | `422` `idempotency-key-invalid` |
| Lần đầu bị từ chối (`4xx`, `5xx`) | Khóa không được giữ: sửa lệnh rồi gửi lại cùng khóa được |
| Không gửi tiêu đề | Như trước khi có khóa — mỗi lần gửi là một lệnh |

Khóa tính **theo người gọi**: hai tài khoản dùng trùng chuỗi không đụng nhau. Khóa sống
`IDEMPOTENCY_TTL_HOURS` giờ (mặc định 24); quá hạn thì cùng chuỗi là lệnh mới. Lần đang chạy giữ khóa
`IDEMPOTENCY_LOCK_SECONDS` giây (mặc định 60) — tiến trình chết giữa chừng thì quá mốc đó lần gửi lại tự nhận
việc. Xem [Cấu hình](../../cai-dat/cau-hinh/). Đường của cổng người dùng (không có `/core/v1`) bỏ qua tiêu đề
này.

## Quy tắc chung

- Cổng API giới hạn tốc độ **chung** theo địa chỉ người gọi, cho mọi đường: vượt ngưỡng trả `429` với
  `{"error_msg": …}` và các header `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Tạo hồ sơ, tải tệp lên và gửi lời nhắn còn có **giới hạn tốc độ** theo người dùng ở dịch vụ. Vượt giới
  hạn trả `429` kèm header `Retry-After` (số giây) và `detail` dạng `{"code": "rate-limited", "message": …}`
  bằng tiếng Việt. Con số của cả hai giới hạn do `.env` quyết — xem [Cấu hình](../../cai-dat/cau-hinh/)
- Chuyển trạng thái hồ sơ: `POST /requests/{case_id}/transitions` (người gửi, cũng là
  `/core/v1/workflow/requests/{case_id}/transitions` của lõi), `/coordination/requests/{case_id}/transitions`
  (điều phối), `/department/requests/{case_id}/transitions` (phòng ban), kèm trạng thái đích. Cả ba gọi vào
  **cùng một cửa** của engine, kiểm vai và ràng buộc, từ chối bằng thông báo tiếng Việt. Gọi thẳng API vẫn
  bị chặn như trên giao diện
- Chi tiết hồ sơ trả kèm **danh sách bước đi được** cho người đang gọi — giao diện dựng nút từ danh
  sách này
- Lời nhắn nội bộ không bao giờ trả cho người gửi của hồ sơ, ở bất kỳ điểm cuối nào
