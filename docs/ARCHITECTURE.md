# ARCHITECTURE.md

> **Mục đích của tệp này**: đây là nguồn thông tin duy nhất về cách kho mã được tổ
> chức và vì sao. Bất kỳ ai — người hay công cụ AI — khi bắt đầu làm việc với dự án
> đều phải đọc tệp này **trước khi** khám phá mã nguồn, trước khi viết mã mới.
>
> **Tệp này mô tả HIỆN TRẠNG của mã nguồn, không phải nhật ký thay đổi và không
> phải kế hoạch.** Kế hoạch tương lai thuộc về `ROADMAP.md`. Tiến độ tuần thuộc về
> `PROJECT_STATE.md`. Khi thay đổi một khuôn mẫu thiết kế (không phải sửa lỗi bên
> trong khuôn mẫu đã có), **bắt buộc** cập nhật mục tương ứng ngay trong cùng công
> việc đó. Xem mục 12.

---

## 1. Tóm tắt dự án

**dx-os-lab** — Trạm thực hành số (DX-Lab) mô phỏng một Hệ điều hành Doanh nghiệp
số, xây dựng theo kiến trúc Open-Core cho cuộc thi Phần mềm nguồn mở, Olympic Tin
học Sinh viên Việt Nam 2026.

**Bài toán nghiệp vụ**: Cổng vận hành yêu cầu nội bộ — tiếp nhận và điều phối tập
trung mọi loại yêu cầu trong doanh nghiệp (sự cố thiết bị, cấp quyền phần mềm, giấy
xác nhận nhân sự, đề xuất mua vật tư).

**Điểm khác biệt**: vòng phản hồi tự soi quy trình. Mọi chuyển trạng thái ghi vào
nhật ký sự kiện có cấu trúc; từ đó hệ thống tự khai phá lại quy trình thực tế đang
chạy và đối chiếu với quy trình đã thiết kế, chỉ ra điểm nghẽn và nhánh lệch chuẩn.

**Giai đoạn hiện tại**: Giai đoạn 5 — thích ứng đề thi. Bốn không gian `H`, `P`, `D`, `I` đã chạy
đầu-cuối (Giai đoạn 2 tới 4 đã khép). Số phiên bản xem `git tag` hoặc trang Releases.

Đã cài đặt: cụm mặc định tám dịch vụ dựng bằng một lệnh, mọi lời gọi API vào qua một cổng API (mục 7.4),
và bốn hồ sơ Compose tùy chọn; lược đồ cấu
hình đầy đủ của engine máy trạng thái, **điểm chuyển trạng thái duy nhất**, **nhật ký sự kiện**, lời
nhắn ngoài máy trạng thái; cổng Next.js gồm cổng người gửi, buồng lái điều phối, buồng lái phòng ban,
hộp thư chung, màn quản trị cấu hình; ở không gian `D` có lớp báo cáo trên nhật ký sự kiện, bảng điều
khiển nhúng trong cổng và xuất dữ liệu mở (mục 6.3); ở không gian `I` có khai phá quy trình, gợi ý phân
loại, hồ sơ tương tự và khuyến nghị cải tiến (mục 6.4 tới 6.7). Những mục còn ở dạng thiết kế đều ghi rõ
*"chưa cài đặt"* ngay đầu mục.

**Đề thi** công bố tháng 11/2026 yêu cầu một nền tảng lõi không giao diện (định danh, cổng API, dữ liệu,
luồng công việc) và ít nhất một ứng dụng minh họa trong H-P-D-I. Bảng đối chiếu từng yêu cầu với hiện
trạng, kể cả phần còn thiếu, ở [`doi-chieu-de-thi.md`](doi-chieu-de-thi.md); mục 10 ghi nguyên tắc thiết
kế đã chuẩn bị cho việc này.

---

## 2. Khung kiến trúc H-P-D-I

Toàn bộ hệ thống tổ chức theo bốn không gian chức năng do đề bài quy định. Ký hiệu
này được dùng nhất quán trong nhãn issue, phạm vi commit, cấu trúc thư mục và tên
biến.

| Ký hiệu | Không gian | Trách nhiệm |
|---|---|---|
| **H** | Human — Nhân sự | Định danh tập trung, phân quyền theo vai trò, cổng tự phục vụ, kho tri thức nội bộ |
| **P** | Process — Quy trình | Máy trạng thái, luồng phê duyệt, ràng buộc Poka-yoke, theo dõi SLA, sinh nhật ký sự kiện |
| **D** | Data — Dữ liệu | Nguồn sự thật duy nhất, nhật ký sự kiện chuẩn hóa, bảng điều khiển, xuất dữ liệu mở |
| **I** | Intelligence — Trí tuệ nhân tạo | Phân loại tự động, truy xuất tri thức, khai phá quy trình |

### 2.1. Tính tuyến tính bắt buộc

Bốn không gian phải xây dựng **theo thứ tự H → P → D → I**. Không thể đạt năng lực
tự động hóa ở `I` khi `P` chưa có ràng buộc và `D` chưa chuẩn hóa. Tích hợp AI vào
quy trình chưa chuẩn hóa sẽ sinh ảo giác dữ liệu.

**Hệ quả thực hành**: nếu một công việc yêu cầu xây dựng thành phần thuộc `I` trong
khi `P` và `D` chưa ổn định, hãy nêu vấn đề trước khi thực hiện.

### 2.2. Nguyên tắc bất di dịch: AI chỉ gợi ý, con người quyết định

Tầng `I` **chỉ được ghi vào các trường mang tính gợi ý**, không bao giờ ghi trực
tiếp vào trường quyết định. Mọi kết quả từ AI phải đi qua một bước xác nhận của
người có thẩm quyền, dù chỉ là một cú nhấn chuột.

Trong lược đồ dữ liệu, tách rõ hai nhóm trường:

| Trường gợi ý (AI ghi) | Trường quyết định (người ghi) |
|---|---|
| `suggested_category` | `category` |
| `suggested_assignee_id` | `assignee_id` |
| `suggested_priority` | `priority` |

Đồng thời ghi lại việc con người có ghi đè gợi ý của AI hay không, phục vụ đo lường
độ chính xác thực tế của mô hình.

**Khuôn gợi ý và ghi đè — đã cài đặt (#239).**

- **Một gợi ý** là `GoiY(field, code, label, reason, source, confidence)` trong
  `backend/app/intelligence/goi_y.py`. `confidence` để trống khi nguồn không có con số thật — bảng
  ánh xạ không có, nên giao diện không vẽ độ tin cậy nào cho nó
- **Nguồn, theo thứ tự**: cột `suggested_*` của hồ sơ có giá trị (tầng `I` ghi, nguồn `model`) thì
  dùng nó; trống thì tra bảng ánh xạ của dữ liệu khởi tạo (`request_type_routing`, nguồn `routing`)
  theo **loại cuối cùng** của hồ sơ — kể cả loại vừa đổi trong cùng thao tác. Không nguồn nào có gì
  thì không có gợi ý, ô chọn vẫn dùng tay. Thêm gợi ý cho một trường quyết định mới là thêm một hàm
  vào `_NGUON_GOI_Y`
- **Một hàm cho cả hai đầu**: màn điều phối vẽ thẻ gợi ý và cửa chuyển trạng thái đem so đều gọi
  cùng hàm, nên thứ người dùng thấy đúng là thứ được ghi. Danh mục `/request-types` mang phòng gợi
  ý của từng loại, để thẻ đổi theo ngay khi điều phối viên đổi loại
- **Xác nhận bằng chính thao tác thật.** Gợi ý chỉ điền sẵn ô; không có nút "chấp nhận" riêng, không
  có "hoàn tác" — chuyển trạng thái không quay lui và nhật ký chỉ ghi thêm
- **Dấu giữ hay ghi đè ghi ở cửa chuyển trạng thái** (mục 6.1, bước 4), vào cột riêng
  `event_log.suggestion` = `{trường: {suggested, chosen, overridden, source, confidence}}` — mỗi
  trường có gợi ý mà người dùng gửi kèm. Cột riêng chứ không trộn vào `changes`, để `changes` giữ
  đúng một nghĩa "trường nào đổi từ gì sang gì". Không lưu dấu nào trên dòng hồ sơ: hồ sơ chỉ mang
  giá trị hiện tại, còn mỗi lần xác nhận là một sự kiện
- **Đo trên lớp báo cáo**: view `bao_cao_goi_y` (mục 6.3), biểu đồ tỷ lệ ghi đè theo trường và nguồn
  trên bảng điều khiển. Đây là con số quyết định khi nào gợi ý của mô hình được thay bảng ánh xạ
- **Ba trường có gợi ý (#317)**: loại yêu cầu và mức ưu tiên chỉ có nguồn `model` (không có bảng ánh
  xạ nào cho chúng — mức mặc định của bảng `priorities` là giá trị điền sẵn, không phải gợi ý); phòng
  ban có cả hai nguồn, nhưng mô hình chỉ ghi `suggested_department_code` khi bật cờ
  `DXLAB_SUGGEST_DEPARTMENT_FROM_MODEL` (mặc định tắt, mục 6.5). Lần sửa của chính người gửi hồ sơ
  không ghi giữ hay ghi đè: họ không bao giờ thấy thẻ gợi ý
- **Người xử lý (#318), nguồn `workload`, không cần mô hình** — `backend/app/intelligence/nguoi_xu_ly.py`.
  Ứng viên là đúng danh sách ô chọn (`nguoi_nhan_viec`: người của phòng đang giữ hồ sơ, nhận được việc),
  nên người phòng khác hay không nhận được việc không bao giờ được gợi ý. Điểm = `w_kn × ln(1 + kinh
  nghiệm) − w_tải × đang giữ`; *đang giữ* là hồ sơ giao cho người đó ở trạng thái hàng đợi phòng ban,
  *kinh nghiệm* là số hồ sơ cùng loại người đó đã đi cạnh `primary_scope = 'assignee'` (bước chính của
  người được giao, mục 7.3) — không mã trạng thái nào. Trọng số và cửa sổ ngày ở `DXLAB_ASSIGNEE_SUGGEST_*`.
  Tính hai lúc: hồ sơ **về phòng** — vào trạng thái có cạnh cho đặt `assignee_id` — bằng tác vụ nền sau
  phản hồi chuyển trạng thái; và lúc trưởng phòng **mở ô chọn** (`/departments/{code}/assignees?case_id=`,
  vốn đã gọi danh bạ) — tải việc đổi thì gợi ý đổi theo. Ghi `suggested_assignee_id` và cột ghi chú riêng
  `assignee_suggestion` (tên, lý do, số liệu; migration `0021`) bằng UPDATE riêng giữ `updated_at`;
  `goi_y_nguoi_xu_ly` đọc lại hai cột đó cho cả thẻ lẫn cửa chuyển trạng thái, không gọi danh bạ. Danh bạ
  không trả lời thì không có gợi ý, ô chọn báo lỗi như cũ. Ô để trống (nhận mà chưa giao ai) không tính
  là ghi đè

Ba lý do: đúng nguyên lý Human-in-the-loop mà đề bài nêu; nếu AI phân luồng sai thì
người dùng vẫn điều chỉnh được; và nếu mô hình lỗi vào ngày trình diễn, hệ thống
vẫn vận hành ở chế độ thủ công.

**Thứ tự xây dựng bắt buộc**: hoàn thiện luồng thủ công chạy đúng trước, sau đó mới
gắn AI vào như một lớp hỗ trợ.

### 2.3. Ranh giới lõi và ứng dụng minh họa

**Đã cài đặt ở Mức 1** (#365, giảng viên chốt ngày 15/11/2026). Đề thi tách nền tảng dịch vụ lõi không
giao diện (Tầng 1) khỏi ứng dụng minh họa có giao diện (Tầng 2). Mức 1 giữ **một** dịch vụ ứng dụng và vẽ
ranh giới bằng không gian địa chỉ: API của lõi có phiên bản, nằm dưới `/core/v1`, đi qua cổng API; ứng dụng
minh họa — cổng vận hành yêu cầu nội bộ — dùng các đường còn lại. **Mức 2 đã cài** (#376, mục "Nhiều quy
trình" dưới đây): engine chạy nhiều quy trình cùng lúc, kèm một quy trình mẫu thứ hai mà một ứng dụng khác
chạy trọn chỉ qua `/core/v1`. **Chưa làm**: tách engine thành dịch vụ riêng (Mức 3).

**Khuôn mẫu: gắn router thêm một lần, không chép mã.** `backend/app/main.py` gắn mỗi router của lõi thêm
một lần với tiền tố `/core/v1/<nhóm>` (hàm `_gan_loi`). Đường cũ và đường của lõi là **cùng một hàm xử lý,
cùng phụ thuộc** — kiểm token, phân quyền, giới hạn tốc độ theo người dùng, cửa chuyển trạng thái duy nhất
(mục 6.1) — nên hai đường không thể kể hai chuyện. Đường cũ giữ nguyên cho cổng người dùng. Router nào trộn
điểm cuối lõi với điểm cuối của ứng dụng thì tách đôi ngay trong tệp của nó, chỉ dời khai báo:
`workflow/routes.py` có `router_loi` (lõi) và `router` (lời nhắn trên hồ sơ, của ứng dụng);
`workflow/attachment_routes.py` có `router` (chính sách, tải về) và `router_tai_len` vì hai đường cũ khác
tiền tố. Router mang tiền tố riêng (`/analytics`, `/me/notifications`) chuyển tiền tố ra lúc gắn.

Nhãn OpenAPI gắn lúc gắn router, không khai ở router: nhãn của router cộng dồn vào **mọi** lần gắn, nên
thao tác dưới `/core/v1` sẽ mang thêm nhãn cũ. Kết quả: thao tác của lõi chỉ mang một nhãn "Lõi — …"; sáu
nhóm này khai trong `openapi_tags` (`NHOM_LOI` ở `main.py`) nên đứng đầu `/docs`, kèm mô tả. Mã thao tác
FastAPI tự sinh từ tên hàm cộng đường dẫn, nên bản của lõi không trùng bản ở đường cũ. Bề mặt đường cũ đối
chiếu từng dòng trước và sau thay đổi — đường, phương thức, nhãn, mã thao tác, tham số, mã phản hồi — giống
hệt.

| Nhóm lõi (nhãn OpenAPI) | Đường cũ (giữ nguyên) | Đường của lõi |
|---|---|---|
| Lõi — Luồng công việc | `GET /processes` | `GET /core/v1/workflow/processes` |
| | `GET /request-types` | `GET /core/v1/workflow/request-types` (`process`) |
| | `GET /states` | `GET /core/v1/workflow/states` (`process`) |
| | `GET /priorities` | `GET /core/v1/workflow/priorities` |
| | `GET /departments` | `GET /core/v1/workflow/departments` |
| | `POST /requests` | `POST /core/v1/workflow/requests` — loại yêu cầu quyết định quy trình |
| | `GET /requests` ¹ | `GET /core/v1/workflow/requests` (`process`) ¹ |
| | `GET /requests/{case_id}` ¹ | `GET /core/v1/workflow/requests/{case_id}` ¹ |
| | `POST /requests/{case_id}/transitions` ¹ | `POST /core/v1/workflow/requests/{case_id}/transitions` ¹ |
| | — | `GET /core/v1/workflow/processes/{code}/bpmn` ² — bộ quy tắc đang bật dạng BPMN 2.0 kèm bố cục (#405) |
| Lõi — Tệp | `GET /attachments/policy` | `GET /core/v1/files/policy` |
| | `POST /requests/{case_id}/attachments` | `POST /core/v1/files/requests/{case_id}/attachments` |
| | `GET /attachments/{attachment_id}` | `GET /core/v1/files/{attachment_id}` |
| Lõi — Nhật ký sự kiện | `GET /analytics/event-log` | `GET /core/v1/events` (`format=csv\|json`, `from`, `to`, `process`) |
| Lõi — Lưu trữ lạnh ² | — | `GET /core/v1/archive` · `GET /core/v1/archive/{YYYY-MM}` · `GET /core/v1/archive/{YYYY-MM}/files/{tệp}` |
| Lõi — Webhook ² | — | `POST`, `GET /core/v1/webhooks` · `GET`, `DELETE /core/v1/webhooks/{id}` · `GET /core/v1/webhooks/{id}/deliveries` (#390, mục 6.8) |
| Lõi — Thông báo | `GET /me/notifications` | `GET /core/v1/notifications/preferences` |
| | `POST /me/notifications/{code}` | `POST /core/v1/notifications/preferences/{code}` |
| Lõi — Định danh | `GET /me` | `GET /core/v1/identity/me` |

¹ Cùng đường, **khác cửa nhìn thấy** (#376): đường cũ là cổng người gửi — chỉ hồ sơ do người gọi tạo; đường
của lõi là cửa trung lập với vai (`app/workflow/loi.py`, xem "Nhiều quy trình"). Ba điểm cuối này vì thế là
hai hàm xử lý dùng chung thân (`liet_ke_ho_so`, `_dung_chi_tiet`, `di_buoc` trong `workflow/routes.py`):
đường cũ ở `router_nguoi_gui`, lõi ở `router_loi_rieng`. Mọi điểm cuối khác vẫn là một hàm gắn hai lần.
Tham số `process` bỏ trống là quy trình mặc định của ứng dụng — ví dụ và cổng người dùng cũ không vỡ.

² **Chỉ có ở lõi** (#378, mục 6.3a; webhook #390, mục 6.8): cổng người dùng không dùng nên không có đường cũ. Bài kiểm khai chúng
trong `CHI_LOI` của `backend/tests/test_loi_api.py`, cạnh `ANH_XA`. Quyền như `GET /core/v1/events` — chỉ
quản trị viên.

Bước chuyển được phép và lịch sử không có điểm cuối riêng: chúng là trường `allowed_transitions` và
`history` của chi tiết hồ sơ (`GET …/requests/{case_id}`), như ở đường cũ. Thêm điểm cuối cho lõi: khai
trong router đã gắn ở cả hai nơi, thêm một dòng vào bảng trên và vào `ANH_XA` của
`backend/tests/test_loi_api.py` — bài kiểm so khít tập đường `/core/v1` trong OpenAPI với bảng đó, nên điểm
cuối của ứng dụng không lọt vào lõi mà không ai hay.

**Điểm cuối của ứng dụng minh họa** — chỉ ở đường cũ, dưới `/core/v1` trả `404`:

| Phần của ứng dụng | Đường |
|---|---|
| Buồng lái điều phối | `/coordination/*` — hàng đợi, chi tiết, bước chuyển, lời nhắn, liên hệ người gửi |
| Buồng lái phòng ban | `/department/*` — cùng các phần như trên |
| Lời nhắn và hộp thư | `POST /requests/{case_id}/messages`, `/inbox`, `/inbox/unread`, `/inbox/{case_id}/read` |
| Ủy quyền khi vắng mặt | `/delegations`, `/delegations/members`, `/delegations/{ma}/revoke` |
| Giao việc, danh bạ | `GET /departments/{department_code}/assignees` |
| Báo cáo nhúng | `POST /analytics/dashboard/guest-token` |
| Khai phá quy trình | `/analytics/process-mining`, `/analytics/process-mining/recommendation` |
| Hồ sơ tương tự | `/similar-cases/search`, `/similar-cases/abandon` |
| Quản trị cấu hình | `/admin/config`, `/admin/config/{loai}/{ma}` |
| Vận hành | `/system/health`, `/sla/scan`, `/archive/scan` (#378), `/metrics`; công khai `/`, `/health`, `/health/live`, `/health/ready` |

**Nhiều quy trình (Mức 2, #376).** Lõi phục vụ nhiều ứng dụng, mỗi ứng dụng một quy trình riêng, cùng một
engine — không một dòng mã nào biết quy trình nào tồn tại.

- *Dữ liệu* (bản sửa `0028_nhieu_quy_trinh`, seed `00-quy-trinh.sql`): bảng `processes` (`code`, `label`,
  `description`, `display_order`, `is_app_default`). `rule_sets.process_code` và `request_types.process_code`
  là khóa ngoại NOT NULL. Chỉ mục duy nhất từng phần "một bộ đang bật cả hệ thống" thay bằng **một bộ đang
  bật cho mỗi quy trình**; `kiem_tra_cau_hinh()` phép kiểm 11 chặn quy trình không bộ nào bật và đòi đúng một
  dòng `is_app_default`. `rule_sets.version` vẫn duy nhất toàn bảng — bộ của quy trình khác đặt mã phiên bản
  khác (`purchase-v1`), mọi chỗ tra bộ theo `version` không đổi. `requests` **không** có cột quy trình: quy
  trình của hồ sơ suy từ `rule_set_id` hồ sơ ghim lúc tạo — một nguồn sự thật; truy vấn lọc bằng
  `rule_set_id IN (bộ của quy trình)` (`bo_cua_quy_trinh`). Vai, phòng ban, mức ưu tiên, lịch làm việc dùng
  chung mọi quy trình
- *Engine*: `get_active_rule_set(session, process_code)` và `rule_sets_in_use(session, process_code)` bắt
  buộc truyền quy trình. **Loại yêu cầu quyết định quy trình**: hồ sơ mới nhận bộ đang bật của quy trình mà
  loại thuộc về; đổi loại sang loại của quy trình khác bị từ chối (`invalid-field-value`). Kích hoạt bộ mới
  (`cau_hinh/bo_quy_tac.kich_hoat`) chỉ tắt bộ cũ của **cùng** quy trình. Mọi luật — Poka-yoke, hạn theo giờ
  làm việc, leo thang, mở lại, trường riêng theo loại, đính kèm, nhật ký chỉ ghi thêm — đọc từ bộ của hồ sơ
  nên chạy cho mọi quy trình
- *Quy trình của ứng dụng minh họa*: `ma_quy_trinh_ung_dung(session)` tra dòng `is_app_default` (hiện là
  `internal-requests`). Mọi màn của ứng dụng — cổng người gửi, hai buồng lái, hộp thư, ủy quyền, giao việc,
  màn cấu hình quy trình (#255), gợi ý AI sau khi gửi, bộ quét gợi ý — chỉ dùng quy trình này. Không có
  `if` theo mã quy trình nào: quy trình khác vắng mặt ở các màn đó vì truy vấn lọc theo cờ
- *Cửa trung lập với vai* (`app/workflow/loi.py`): danh sách, chi tiết, bước chuyển dưới `/core/v1/workflow`
  thấy hợp của **ba cửa nhìn thấy sẵn có**, bằng chính hàm của chúng — hồ sơ người gọi tạo (cổng người gửi);
  hồ sơ phòng mình nếu người gọi vào được buồng lái phòng ban (`vao_duoc_phong_ban`); mọi hồ sơ nếu vào được
  buồng lái điều phối (`vao_duoc_buong_lai`). Ngoài phạm vi trả `404`. Đi cạnh nào thì **engine** quyết
  bằng `transitions`, `transition_roles` và ràng buộc trên cạnh (`requester-owns-case`,
  `actor-in-case-department`, `actor-not-requester`) — không bộ kiểm quyền thứ hai. `allowed_transitions`
  của chi tiết tính theo người gọi; `needs_action=true` là hàng việc của một người duyệt
- *Báo cáo và khai phá*: `bao_cao_ho_so` — nền mọi biểu đồ của bảng điều khiển — chỉ hồ sơ của quy trình
  mặc định (thêm cột cuối `ma_quy_trinh`), nên số trên biểu đồ cũ không đổi. `bao_cao_nhat_ky` giữ mọi quy
  trình, thêm cột cuối `process_code`; `GET /core/v1/events?process=` lọc một quy trình. Dịch vụ khai phá
  nhận `process` (bỏ trống là quy trình mặc định) và không bao giờ trộn nhật ký hai quy trình vào một mô hình
- *Quy trình mẫu thứ hai* (`infra/seed/06-quy-trinh-mua-sam.sql`, thuần dữ liệu): `purchase-approval`, loại
  `purchase-request` với trường riêng số tiền và lý do. Người đề xuất (`requester`) gửi và chọn phòng đề xuất
  (trường quyết định `department_code`, ràng buộc `select-department`) → trưởng phòng đó (`approver`,
  `actor-in-case-department`) duyệt cấp một → điều phối viên (`classifier`, `actor-not-requester`) duyệt cấp
  hai → Đã duyệt; mỗi cấp trả lại bổ sung hoặc từ chối được, cả hai bắt buộc ghi lý do; người đề xuất sửa,
  gửi lại hoặc rút. Hai trạng thái chờ duyệt chạy đồng hồ, cạnh vào mỗi cấp mang `restarts_sla`, nên **mỗi
  cấp có hạn riêng** bằng `sla_hours` của loại

**Điều kiện trên cạnh (#397).** Rẽ nhánh theo dữ liệu của hồ sơ là dữ liệu: bảng `transition_conditions`
(bản sửa 0032) gắn vào một cạnh các dòng *trường riêng — phép so — giá trị* (`<`, `<=`, `>`, `>=`, `=`, `!=`
trên `requests.details`). Cạnh chỉ đi được khi mọi điều kiện đúng; cạnh không có dòng nào chạy như trước.
`app/rules/dieu_kien.py` chỉ biết cách so, không biết trường hay ngưỡng nào; nó chạy trong chính hai hàm của
ràng buộc Poka-yoke — `input_free_guards_pass` (lúc chào nút: cạnh không thỏa không hiện, kể cả ở bước chính
và hàng việc "đang chờ tôi") và `run_guards` (lúc đi: từ chối bằng mã ràng buộc `edge-condition`). Quy tắc
so để rẽ nhánh đoán trước được: hai phía là số thì so số, `=`/`!=` với chữ thì so chữ, trường thiếu hay so
lớn nhỏ chữ với số là sai. Bản sửa nội dung gửi kèm cạnh (`changes.details`) được xét thay bản đang lưu.
Quy trình mua sắm mẫu dùng hai cạnh rời "Chờ trưởng phòng duyệt" với điều kiện bù nhau trên `so-tien`:
dưới 5.000.000 đồng thì "Duyệt (dưới ngưỡng)" sang thẳng "Đã duyệt", từ ngưỡng trở lên "Duyệt cấp một" sang
cấp hai (`infra/seed/07-dieu-kien-mua-sam.sql`; bản sửa 0032 chạy tệp đó trên cụm đã có quy trình). Đổi
ngưỡng là một câu `UPDATE` trên hai dòng điều kiện. Bài kiểm thử chặn điều kiện trỏ tới trường không khai
cho loại nào của cùng quy trình.

**Giới hạn của Mức 2.** Điều kiện chỉ so trường riêng của hồ sơ với hằng số, nối bằng "và" — chưa có "hoặc",
chưa so trường quyết định (phòng, mức ưu tiên). Màn của ứng dụng
minh họa chỉ hiện quy trình mặc định: người gửi không thấy đề xuất mua sắm của mình trong cổng (thấy qua
`/core/v1`), màn cấu hình quy trình chỉ sửa quy trình mặc định — quy trình khác sửa bằng seed và bản sửa.
Các view báo cáo về gợi ý AI (`bao_cao_goi_y`, `bao_cao_ngan_chan`) không lọc quy trình vì chỉ quy trình mặc
định có gợi ý. Engine vẫn chạy trong dịch vụ ứng dụng (tách ra là Mức 3).

**Tài khoản dịch vụ.** Client `dx-integration` (biến `KEYCLOAK_INTEGRATION_*`): bí mật, chỉ bật client
credentials, không đăng nhập người dùng; bộ ánh xạ đưa `dx-api` vào `aud` như client của cổng người dùng,
nên token qua cổng API và dịch vụ mà không nới phép kiểm nào; tài khoản mang vai `requester` — đủ để tạo hồ
sơ và đi các cạnh của người gửi trên hồ sơ của chính nó. Không dùng lại `dx-directory`: client đó chỉ để
tra danh bạ, token không mang `aud` của dịch vụ. Hai đường tạo, cùng một cấu hình:

- Cụm dựng mới: khai trong `infra/keycloak/realm-dx-os-lab.json`, bí mật khớp `infra/.env.example`. Mô tả
  client giữ dưới 255 ký tự — cột của Keycloak chỉ chừng đó; vượt là Keycloak không nạp được realm và khởi
  động lại liên tục (đã gặp lúc làm #365)
- Cụm đang chạy (Keycloak chỉ nạp tệp realm lúc tạo realm): `python scripts/tai_khoan_dich_vu.py` — kiểm,
  thiếu thì tạo, có rồi thì đặt lại cấu hình và bí mật theo `.env`, gán vai còn thiếu, rồi xin thử một
  token và kiểm `aud`, vai. Chạy lại bao nhiêu lần cũng được; không gỡ vai nào

Hai tài khoản **duyệt** cho ví dụ quy trình thứ hai (#376), cùng hai đường tạo ấy: `dx-integration-truong-phong`
(`KEYCLOAK_INTEGRATION_HEAD_*`, vai `approver`, thuộc group `/phong-ban/admin-office`, có bộ ánh xạ `groups`
để dịch vụ đọc phòng của người gọi như với người dùng thật) và `dx-integration-duyet`
(`KEYCLOAK_INTEGRATION_REVIEWER_*`, vai `classifier`). Tách riêng thay vì nới vai của `dx-integration` hay
dùng luồng mật khẩu của tài khoản mẫu: tài khoản tạo hồ sơ vẫn chỉ là người gửi, hai cấp duyệt là hai danh
tính khác nhau (ràng buộc `actor-not-requester` có nghĩa), và không client nào bật luồng mật khẩu. Hai
tài khoản này chỉ để trình diễn — triển khai thật thì tắt hoặc đổi bí mật (README, *Trước khi dùng thật*).

Token của tài khoản dịch vụ không có `name`; `groups` chỉ có khi client gắn bộ ánh xạ group. `actor_from_claims` (`backend/app/auth/identity.py`)
lấy mã client trong `azp` làm tên hiển thị khi tên người dùng đúng là `service-account-<azp>` — người dùng
thường không mượn được nhãn này. Hồ sơ do ứng dụng khác tạo mang nhãn người gửi `dx-integration`, dòng nhật
ký mang `actor` là `sub` của tài khoản dịch vụ. Muốn nhãn khác: gắn claim `name` cho client trong Keycloak,
claim đó luôn được ưu tiên.

**Ví dụ chạy được.** `examples/goi-loi/goi_loi.py`, chỉ thư viện chuẩn: xin token client credentials từ
Keycloak, rồi **chỉ** gọi cổng API dưới `/core/v1` — danh tính, danh mục loại yêu cầu, tạo hồ sơ, đọc bước
được phép, đi một bước, đọc lịch sử. Không mã cứng mã trạng thái hay mã loại: chọn bước chính của người gọi,
không có thì bước đầu tiên làm đổi trạng thái. Với dữ liệu mẫu, vai `requester` ở "Đã gửi" chỉ có "Sửa nội
dung" (giữ trạng thái) và "Hủy yêu cầu", nên kịch bản đi "Hủy yêu cầu" — hồ sơ thử không nằm lại trong hàng
đợi của điều phối viên. `examples/goi-loi/quy_trinh_mua_sam.py` chạy trọn quy trình thứ hai bằng ba tài
khoản dịch vụ: danh mục quy trình → loại và trạng thái của quy trình → tạo đề xuất, gửi trưởng phòng →
trưởng phòng thấy hồ sơ trong việc chờ mình, duyệt → người duyệt cấp hai duyệt → đọc lịch sử. Mỗi người đi
bước chính lõi trả về cho chính họ, trường bắt buộc điền theo khai báo — không mã cứng mã nào. Hướng dẫn:
`examples/goi-loi/README.md`.

**Tại cổng API** không thêm tuyến nào: `/core/v1/*` rơi vào tuyến `can-token` (mục 7.4) — thiếu token là
`401` ngay tại cổng, kể cả đường lõi chưa tồn tại.

**Kiểm chứng Mức 2.** `backend/tests/test_nhieu_quy_trinh.py` (14 bài): mỗi quy trình đúng một bộ đang bật
(chỉ mục chặn hai bộ, `kiem_tra_cau_hinh()` chặn không bộ nào), kích hoạt bộ mới không đụng quy trình khác,
hồ sơ nhận bộ của quy trình mà loại thuộc về, không đổi loại sang quy trình khác; danh mục và lọc theo quy
trình; chạy trọn quy trình thứ hai chỉ qua `/core/v1` — đúng vai đúng phòng đi được, sai phòng `404`, sai vai
bị engine chặn; hồ sơ quy trình thứ hai không lọt vào hàng đợi, buồng lái, cổng người gửi, view báo cáo của
quy trình mặc định; nhật ký xuất lọc được theo quy trình; realm khóa tạm đúng ở lần sai thứ `failureFactor`,
từ chối mật khẩu ngắn, tài khoản mẫu vẫn đăng nhập. Dịch vụ khai phá có bài riêng: hồ sơ của quy trình khác
không vào mô hình.

**Kiểm chứng Mức 1.** `backend/tests/test_loi_api.py` (60 bài, chạy trong container dịch vụ như mọi bài khác):
OpenAPI khớp bảng ánh xạ, đúng nhãn, không trùng mã thao tác; mỗi đường của lõi trả cùng kết quả với đường cũ, cả đọc lẫn ghi (tạo hồ sơ, đi bước, bước bị từ chối,
tải tệp, đổi tùy chọn thông báo, xuất nhật ký); điểm cuối của ứng dụng `404` dưới `/core/v1`; không token
`401`; token client credentials **thật** của Keycloak tạo hồ sơ và đi một bước chỉ bằng `/core/v1`; qua cổng
API thật, không token bị chặn tại cổng còn tài khoản dịch vụ vào được. Ba phép đột biến đều làm bài đỏ: bỏ
nhãn tên client của tài khoản dịch vụ, gắn router hộp thư vào lõi, để lại nhãn ở router của lõi.
`examples/goi-loi/` chạy tay được trên cả cụm nâng cấp (client tạo bằng kịch bản) lẫn cụm dựng mới (client
từ realm); nó ngoài ảnh của dịch vụ nên không nằm trong bộ kiểm thử tự động.

---

## 3. Bộ công nghệ

Không đưa vào công nghệ thay thế mà không cập nhật mục này và tạo một bản ghi quyết
định kiến trúc trong `docs/adr/`.

### 3.1. Đã chốt

| Tầng | Công nghệ | Giấy phép | Ghi chú |
|---|---|---|---|
| Giao diện | Next.js (React) | MIT | Cổng người dùng và bảng điều khiển |
| Dịch vụ ứng dụng | FastAPI (Python) | MIT | Cùng ngôn ngữ với toàn bộ tầng `I`, không phải bắc cầu sang dịch vụ khác |
| Cơ sở dữ liệu | PostgreSQL 16 kèm pgvector `0.8.6` — ảnh `pgvector/pgvector:0.8.6-pg16` | PostgreSQL License | Được OSI công nhận. Phần mở rộng `vector` cho hồ sơ tương tự ở `I` (#319, mục 6.6); thay `postgres:16-alpine`, dữ liệu cũ dùng tiếp |
| Đóng gói | Docker + Docker Compose | Apache-2.0 | Dựng toàn hệ thống bằng một lệnh |
| Định danh tập trung | Keycloak `26.7.3` | Apache-2.0 | Không gian `H`. Chạy như dịch vụ độc lập, giao tiếp qua OIDC. Xem [ADR-0001](adr/0001-chon-nen-tang-sso.md) |
| Lưu trữ đối tượng | SeaweedFS `4.45` | Apache-2.0 | `core`. Lưu tệp đính kèm, giao tiếp qua S3 API chuẩn. Xem [ADR-0002](adr/0002-chon-nen-tang-luu-tru-doi-tuong.md) |
| Cổng API | Apache APISIX `3.20.0` — ảnh `apache/apisix:3.20.0-debian` nguyên bản | Apache-2.0 | `core`. Cửa vào duy nhất của API ở cụm mặc định (#364): kiểm token Keycloak tại biên, giới hạn tốc độ chung, định tuyến tới dịch vụ ứng dụng. Chế độ standalone, một tiến trình, cấu hình là tệp trong `infra/cong-api/`. Xem [ADR-0010](adr/0010-chon-nen-tang-cong-api.md) và mục 7.4 |
| Kinh doanh thông minh | Apache Superset `6.1.0` | Apache-2.0 | Không gian `D`. Bảng điều khiển phân tích, chỉ đọc, nhúng vào cổng qua guest token. Xem [ADR-0003](adr/0003-chon-nen-tang-bi.md) |
| Kho tri thức | Wiki.js `2.5.315` — ảnh `requarks/wiki` nguyên bản | AGPL-3.0 | Không gian `H`. Dịch vụ **tùy chọn** (hồ sơ Compose `tri-thuc`, #321), chạy như dịch vụ độc lập, đăng nhập một lần qua OIDC, nội dung đọc qua GraphQL; không mã nào của nhóm mang AGPL. Navigator chấp nhận 14/11/2026, chờ giảng viên xác nhận. Xem [ADR-0006](adr/0006-chon-nen-tang-kho-tri-thuc.md) |
| Máy chủ mô hình ngôn ngữ | llama.cpp server `b11889` | MIT | Không gian `I`. Dịch vụ `mo-hinh` **tùy chọn** (hồ sơ Compose `tri-tue`), điểm cuối kiểu OpenAI, chỉ trong mạng Compose. Xem [ADR-0008](adr/0008-chon-co-so-du-lieu-vec-to-va-mo-hinh-cuc-bo.md) và mục 6.5 |
| Mô hình sinh văn bản | Qwen2.5-1.5B-Instruct GGUF `q4_k_m` | Apache-2.0 | Tệp dữ liệu, không trong kho hay ảnh: nằm ở volume `mo-hinh`, tải bằng `scripts/tai_mo_hinh.py` (ghim commit kho Hugging Face và SHA-256) |
| Mô hình nhúng | Qwen3-Embedding-0.6B GGUF `Q8_0` | Apache-2.0 | Dịch vụ `mo-hinh-nhung` — cùng ảnh llama.cpp, chế độ `--embeddings`, hồ sơ `tri-tue` (#319). Tệp cùng volume `mo-hinh`, cùng lệnh tải |
| Khai phá quy trình | PM4Py `2.7.23.8` | AGPL-3.0-or-later | Không gian `I`. Chỉ nằm trong **dịch vụ khai phá tách riêng** `services/khai-pha/`, giao tiếp qua HTTP; có bộ máy dự phòng không dùng thư viện này. Xem [ADR-0007](adr/0007-chon-thu-vien-khai-pha-quy-trinh.md) và mục 6.4 |
| Quản trị CSDL | Chờ quyết định | | Hai phương án: pgAdmin 4 (chạy trong Compose) hoặc DBeaver Community |

Các thành phần trên dùng giấy phép nhóm dễ dãi, tương thích hoàn toàn với MIT của sản phẩm, trừ hai
thành phần AGPL: Wiki.js chạy nguyên khối như dịch vụ độc lập, còn PM4Py bị giữ sau ranh giới dịch vụ
và cả thư mục dịch vụ khai phá theo AGPL — mục 3.3.

**Hai loại bảng điều khiển, đừng lẫn lộn.** *Buồng lái vận hành* — duyệt, phân công,
leo thang — có tương tác và ghi dữ liệu, thuộc nhóm **tự viết** trong cổng Next.js.
*Bảng điều khiển phân tích* trên nhật ký sự kiện chỉ đọc, thuộc nhóm **lắp ghép** và do
Superset đảm nhiệm. Đây là kiến trúc lai, xem ADR-0003.

Vai trò nghiệp vụ **không khai báo trong mã nguồn**. Keycloak nạp toàn bộ realm gồm
vai trò, ứng dụng khách, nhóm và người dùng từ một tệp JSON lúc khởi động, nên việc đổi
bộ vai trò khi đề thi công bố chỉ là thay dữ liệu. Đây là một trường hợp cụ thể của
khuôn mẫu ở mục 5.

**Cách hai không gian nối vào nhau.** Keycloak là nguồn sự thật về *ai mang vai trò gì
và thuộc phòng nào*; bảng `transitions` là nguồn sự thật về *vai trò nào đi được cạnh
nào*. Hàm `actor_from_claims` ở `backend/app/auth/identity.py` là chỗ duy nhất dịch
giữa hai ngôn ngữ đó. Nhờ vậy engine ở không gian `P` không biết Keycloak tồn tại, và
đổi nền tảng định danh sẽ không đụng tới một dòng nào của engine.

Phòng ban lấy từ **nhóm** chứ không từ thuộc tính người dùng: nhóm đúng ngữ nghĩa hơn,
có sẵn giao diện quản lý trong Keycloak, và cho phép một người thuộc nhiều phòng. Token
mang đường dẫn đầy đủ như `/phong-ban/it`; tiền tố là **cấu hình được**, vì doanh nghiệp
triển khai có thể tổ chức cây nhóm theo cách khác.

**Dịch vụ ứng dụng tự kiểm chữ ký token, không gọi ngược sang Keycloak ở mỗi yêu cầu.**
Khóa công khai tải một lần qua JWKS rồi giữ trong bộ nhớ; Keycloak xoay khóa thì token
mới mang `kid` lạ và thư viện tự đi lấy lại. Keycloak vì thế nằm ngoài đường đi nóng —
nó chậm hay khởi động lại cũng không làm cả hệ thống đứng.

**Một Keycloak, hai địa chỉ — và đây là chỗ dễ mất thời gian nhất.** Trình duyệt đi qua
`localhost:8080`, còn container đi qua `keycloak:8080`. Nếu không cố định `KC_HOSTNAME`,
token lấy theo hai đường sẽ mang hai giá trị `iss` khác nhau và dịch vụ từ chối một nửa
số token. Cấu hình đang dùng: `KC_HOSTNAME` cố định địa chỉ công khai, còn
`KC_HOSTNAME_BACKCHANNEL_DYNAMIC` cho phép tài liệu discovery trả địa chỉ nội bộ cho
các điểm cuối máy chủ gọi. Keycloak tự tách đúng hai chiều — `authorization_endpoint`
và `end_session_endpoint` ra địa chỉ công khai cho trình duyệt, `token_endpoint` và
`jwks_uri` ra địa chỉ nội bộ cho máy chủ. Cổng API (#364) dựa đúng vào điều này: nó đọc
tài liệu discovery qua `keycloak:8080`, tài liệu vẫn ghi `issuer` theo địa chỉ công khai —
khớp `iss` của token — còn `jwks_uri` theo địa chỉ nội bộ (đo thật trên cụm, mục 7.4).

Cùng một gốc vấn đề ở phía cổng: trong container, máy chủ Next.js nghe ở `0.0.0.0`, nên
mọi chuyển hướng dựng từ địa chỉ yêu cầu sẽ trỏ về `http://0.0.0.0:3000` và trình duyệt
đi tới đó sẽ lạc. Địa chỉ công khai của cổng vì vậy phải khai riêng bằng biến môi trường,
không được suy ra.

**Token không bao giờ tới trình duyệt.** Cổng giữ chúng trong cookie `httpOnly` đã mã
hóa và tự gắn vào header khi gọi dịch vụ — khuôn mẫu cổng chặn trước. Mã lạ lọt vào
trang cũng không đọc được token, khác hẳn với việc để token trong `localStorage`.

Phiên nằm ở **hai** cookie, không phải một: `dxlab_session` giữ access token và refresh
token, dùng ở mọi lần gọi dịch vụ; `dxlab_id_token` giữ id token, chỉ dùng lúc đăng xuất.
Lý do là trần 4096 byte của trình duyệt: ba token của Keycloak mã hóa chung nặng 4227–4311
byte, và trình duyệt âm thầm vứt cookie quá khổ nên không ai đăng nhập được (#87). Thêm
claim vào token, hoặc thêm nhóm và vai trò cho người dùng, đều làm cookie phình ra — cổng
ghi lỗi vào nhật ký khi một cookie vượt 4000 byte. Cờ `Secure` bám theo giao thức của
`PORTAL_PUBLIC_URL` chứ không theo `NODE_ENV`, vì bản dựng Docker chạy chế độ production
qua HTTP, và Safari cùng các trình duyệt nhúng bỏ cookie `Secure` gửi qua HTTP.

**Làm mới token lúc dựng trang không ghi được cookie** (#150). Access token sống năm phút
(mặc định của Keycloak); `frontend/lib/api.ts` làm mới khi nó sắp hết hạn. Nhưng Next chỉ
cho ghi cookie trong Server Action và Route Handler, không cho ghi lúc dựng trang. Nên
làm mới xong mà không lưu được thì lời gọi vẫn đi bằng token **mới**, còn cookie giữ
refresh token cũ — dùng lại được vì realm không bật `revokeRefreshToken` — tới lần bấm
thao tác kế tiếp mới được thay. Bật `revokeRefreshToken` thì phải chuyển việc làm mới
sang lớp `proxy` của Next, nơi ghi được cookie trước khi trang dựng. Phiên hết hạn thật
thì trang chi tiết mời đăng nhập lại và quay về đúng trang; trang 404 chỉ dành cho hồ sơ
không có hoặc không được xem.

**Ba lối hỏng khi gọi dịch vụ, ba màn khác nhau** (#235). Mọi lời gọi từ `frontend/lib/api.ts`
có thời hạn chờ `THOI_HAN_GOI_MS` (đặt một chỗ, đổi qua `BACKEND_TIMEOUT_MS`); quá hạn tính như
không kết nối được. Khung và trang chủ đọc `/me` bằng `docDichVu` để tách: `khong-ket-noi-duoc` →
màn **"Hệ thống không phản hồi"** dựng ngay ở máy chủ (`KhongPhanHoi`), có nút thử lại; phiên
hết hạn → mời đăng nhập lại; 404 → `app/not-found.tsx`, câu chung cho cả hồ sơ không tồn tại
lẫn hồ sơ không được xem. Màn không phản hồi không đi qua `app/error.tsx` vì ranh giới lỗi chỉ
hiện sau khi JavaScript chạy; `error.tsx` để dành cho lỗi bất ngờ. Màn danh sách và trang hồ sơ
có `loading.tsx` vẽ khung chờ đúng hình màn thật (`components/khung-cho.tsx`).

**Danh bạ là lối duy nhất dịch vụ gọi ngược sang Keycloak** — `backend/app/auth/directory.py`,
từ #84. Trưởng phòng giao việc phải chọn người từ một danh sách có tên thật, trong khi cơ
sở dữ liệu nghiệp vụ chỉ giữ `sub`. Dịch vụ tra thành viên nhóm `/phong-ban/<mã>` qua
Admin API, bằng tài khoản dịch vụ của một client riêng, `dx-directory`, mang đúng một quyền
chỉ đọc `view-users`. Quyền tối thiểu được kiểm chứ không chỉ được khai: bài kiểm thử xác
nhận tài khoản đó bị từ chối khi đọc cấu hình client hay tạo người dùng.

Từ #131 danh bạ làm thêm một việc: tra **email và số điện thoại của người gửi** khi điều
phối viên hay nhân viên phòng ban mở trang chi tiết hồ sơ. Số điện thoại là thuộc tính
`phoneNumber` khai trong user profile của realm, không bắt buộc; người dùng tự sửa ở trang
tài khoản của Keycloak, quản trị viên cũng sửa được. Mỗi buồng lái có điểm cuối riêng
`/requests/{id}/requester-contact`, phần dùng chung ở `backend/app/workflow/contact.py`, đi
đúng cửa nhìn thấy hồ sơ của buồng lái đó — hồ sơ
phòng khác trả 404 trước khi danh bạ bị hỏi. Cổng người gửi không có điểm cuối nào như vậy.
Cơ sở dữ liệu nghiệp vụ không chép thông tin liên hệ: tra lúc mở trang, nên người gửi đổi
số thì lần mở sau thấy ngay số mới.

Bẫy gặp khi làm #131: tài khoản **nạp từ tệp realm** mà khai sẵn `realmRoles` thì chỉ nhận
đúng các vai trò đó, không tự nhận vai trò mặc định `default-roles-dx-os-lab` như tài khoản
tạo trên giao diện quản trị. Thiếu nó là thiếu `manage-account` và `view-profile`, nên trang
tài khoản trả 401 — tám tài khoản mẫu chưa từng vào được trang này cho tới #131. Tài khoản
mẫu thêm về sau phải khai cả vai trò mặc định trong `realmRoles`.

Điều ADR-0001 bảo vệ vẫn giữ nguyên. Danh bạ chỉ được hỏi khi mở ô chọn người, khi giao
việc và khi mở trang chi tiết hồ sơ ở hai buồng lái, không ở mỗi yêu cầu, và engine không
gọi tới nó. Ba quyết định đi kèm:

- **Không giữ bộ đệm danh bạ.** Người vừa rời phòng phải biến khỏi danh sách ngay, vì giao
  việc cho người đã đi là lỗi thật chứ không phải chuyện hiển thị chậm; và bộ đệm cũ sẽ che
  mất việc Keycloak không phản hồi. Chỉ token của tài khoản dịch vụ được giữ lại
- **Hỏng thì nói là hỏng.** Keycloak không trả lời thì điểm cuối trả 503 kèm lý do, không
  trả danh sách rỗng — rỗng nghĩa là *phòng không có ai*, 503 nghĩa là *không biết phòng
  có ai*. Liên hệ người gửi đi điểm cuối riêng cũng vì vậy: danh bạ hỏng thì chỉ ô liên hệ
  báo lỗi, trang chi tiết vẫn mở. Trần 3 giây giữ ở vòng ngoài bằng một luồng riêng, vì `timeout` của urllib không
  phủ bước tra DNS: đo thật khi tắt Keycloak trong cụm Compose, bước đó treo 8 giây
- **Lấy vai trò hiệu lực**, kể cả vai trò nhận qua nhóm, vì đó mới là thứ có trong token.
  Realm mẫu cố ý có `lan.vu` nhận vai trò người xử lý qua nhóm `/nhom-vai-tro/nguoi-xu-ly`
  thay vì gán thẳng, để bài kiểm thử phân biệt được hai cách đọc

**Không gian `P` không dùng nền tảng ngoài.** Engine máy trạng thái do nhóm tự viết, với
trạng thái và quy tắc chuyển lưu trong bảng dữ liệu. Quyết định này được đưa ra sau khi
khảo sát và dựng thử bốn ứng viên — xem
[ADR-0004](adr/0004-tu-viet-engine-may-trang-thai.md). Lý do cốt lõi: nhật ký sự kiện là
nơi tạo ra giá trị của đề tài, và không nền tảng nào sinh sẵn nhật ký đúng lược đồ mà
`I` cần, nên nhóm phải tự viết lớp đó dù có lắp engine hay không.

### 3.2. Đã khảo sát, chờ duyệt

Hiện không còn bản ghi nào ở trạng thái *Đề xuất*. Ba nhóm thành phần khảo sát cho hệ sinh thái Open-Core
đều đã chấp nhận và nằm ở mục 3.1: kho tri thức (ADR-0006, navigator chấp nhận 14/11/2026, chờ giảng
viên xác nhận), thư viện khai phá quy trình (ADR-0007), mô hình ngôn ngữ (ADR-0008). Thành phần mới
khảo sát về sau vào đây trước, với bản ghi *Đề xuất*; **chưa phải quyết định** cho tới khi bản ghi chuyển
sang *Đã chấp nhận*.

ADR-0008 đã cài đủ hai đợt: sinh văn bản (#316, #317) và nhúng véc-tơ cùng pgvector (#319) — mục 3.1.

### 3.3. Quy tắc kiểm tra giấy phép

Trước khi thêm bất kỳ phụ thuộc nào:

1. Đối chiếu tên giấy phép với danh sách chính thức tại `opensource.org/licenses`
2. Kiểm tra tương thích với giấy phép của thư mục dùng nó — MIT, hoặc AGPL-3.0-or-later trong
   `services/khai-pha/`
3. Ghi kết quả vào `docs/dependencies.md`

Cảnh giác với các giấy phép **không** thuộc danh sách OSI: BSL, SSPL, Elastic
License, Commons Clause, fair-code. Dùng chúng khiến dự án không được chấm điểm.

Với giấy phép copyleft mạnh (AGPL): hợp lệ vì được OSI công nhận, nhưng chỉ dùng trong **một
dịch vụ tách riêng** — thư mục riêng, ảnh chứa riêng, giao tiếp với phần còn lại qua HTTP. Hoặc cả
nền tảng chạy nguyên khối như dịch vụ độc lập, hoặc thư viện được `import` chỉ bên trong dịch vụ đó
(ADR-0007: PM4Py chỉ trong `services/khai-pha/`, đúng một tệp `app/bo_may/pm4py_bo_may.py`). Dịch vụ
ứng dụng và cổng không bao giờ `import` thư viện AGPL — CI có bước `grep` chặn. Ghi rõ ranh giới này
trong bản ghi quyết định và `docs/dependencies.md`.

**Mô hình nhiều giấy phép (#340).** Kho không còn một giấy phép duy nhất:

| Thư mục | Giấy phép | Tệp toàn văn |
|---|---|---|
| `services/khai-pha/` — cả mã của nhóm (`app/`, `tests/`, `Dockerfile`) | AGPL-3.0-or-later | `services/khai-pha/LICENSE` |
| Mọi thư mục khác (`backend/`, `frontend/`, `e2e/`, `scripts/`, `infra/`, `docs/`, `docs-site/`) | MIT | `LICENSE` ở gốc (văn bản MIT nguyên văn; ngoại lệ ghi ở `LICENSES.md`) |

- Bảng đầy đủ và lý do ở `LICENSES.md`; thông báo bên thứ ba (PM4Py và các gói copyleft nó kéo theo, các
  nền tảng chạy như dịch vụ riêng) ở `NOTICE`
- Header SPDX theo thư mục; `scripts/kiem_header.py` (CI) báo lỗi tệp mang giấy phép của thư mục khác.
  Thêm một thư mục mang giấy phép riêng thì sửa cùng lúc bảng `GIAY_PHEP_THEO_THU_MUC` trong kịch bản đó
  và `LICENSES.md`
- **Điều 13**: dịch vụ khai phá phục vụ người dùng qua mạng (gián tiếp qua cổng), nên màn Quy trình thực
  tế có dòng dẫn tới mã nguồn của dịch vụ. Địa chỉ là cấu hình (`MINING_SOURCE_URL` của cổng), không mã
  cứng — bản tự triển khai có sửa dịch vụ thì trỏ về kho của bản sửa
- Chiều MIT sang AGPL tương thích, nên mã MIT của kho dùng lại được trong dịch vụ khai phá; chiều ngược
  lại thì không — **không chép mã từ `services/khai-pha/` sang thư mục MIT**

---

## 4. Cấu trúc thư mục

### 4.1. Hiện trạng

```
dx-os-lab/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml       # biểu mẫu, trường bắt buộc (#422)
│   │   ├── config.yml
│   │   ├── feature_request.yml  # bắt buộc trường "Đã kiểm trong mã chưa"
│   │   └── research.md
│   └── pull_request_template.md
├── backend/                     # FastAPI — dịch vụ ứng dụng
│   ├── app/
│   │   ├── main.py              # điểm vào, điểm cuối kiểm tra sức khỏe
│   │   ├── config.py            # cấu hình từ biến môi trường
│   │   ├── rate_limit.py        # giới hạn tốc độ theo người dùng, đếm trong PostgreSQL (#243)
│   │   ├── thoi_gian_thuc.py    # [H] luồng SSE "hồ sơ vừa đổi" GET /me/stream, nghe NOTIFY (#387)
<<<<<<< HEAD
│   │   ├── webhook.py           # [core] truyền phát sự kiện ra ngoài: /core/v1/webhooks, bộ gửi ký HMAC (#390)
=======
>>>>>>> origin/dev
│   │   ├── db.py                # kết nối dùng chung
│   │   ├── models/              # lược đồ dữ liệu, dùng chung mọi không gian
│   │   ├── workflow/            # [P] ĐIỂM CHUYỂN TRẠNG THÁI DUY NHẤT; ủy quyền khi vắng mặt (#252)
│   │   ├── rules/               # [P] ràng buộc Poka-yoke, đồng hồ SLA, điều kiện trên cạnh (#397)
│   │   ├── events/              # [P→D] nơi ghi nhật ký sự kiện duy nhất
│   │   ├── auth/                # [H] kiểm token OIDC, dịch claim thành Actor, danh bạ
│   │   ├── analytics/           # [D] xuất nhật ký CSV, JSON (#306), lưu trữ lạnh (#378); [I] lối vào khai phá (#314)
│   │   ├── cau_hinh/            # [P] nạp dữ liệu khởi tạo, phiên bản bộ quy tắc (#254), quản trị cấu hình (#255)
│   │   └── intelligence/        # [I] gợi ý cho trường quyết định, dấu giữ hay ghi đè (#239); lớp gọi mô hình,
│   │                            #     người xử lý (#318), hồ sơ tương tự (#319), khuyến nghị cải tiến (#320),
│   │                            #     bài kho tri thức làm nguồn gợi ý thứ hai (#321)
│   ├── alembic/                 # MỌI LƯỢC ĐỒ — bản gốc 0000 là lược đồ cấu hình (#254)
│   │   └── sql/                 # SQL thô của bản gốc 0000 và các bản hàm kiểm (0018, 0025), không sửa nữa
│   ├── tests/
│   ├── requirements.txt         # TỆP KHÓA PHIÊN BẢN gói dùng trực tiếp, bắt buộc commit
│   └── constraints.txt          # khóa nốt gói kéo theo, sinh bằng pip freeze (#368)
├── services/
│   └── khai-pha/                # [I] dịch vụ khai phá quy trình (#314) — nơi DUY NHẤT dùng PM4Py (AGPL)
│       ├── LICENSE              # AGPL-3.0 toàn văn: cả thư mục theo AGPL-3.0-or-later (#340)
│       ├── requirements.txt, constraints.txt # như backend/ (#368)
│       ├── app/du_lieu.py       # mọi câu SQL, chỉ đọc lớp báo cáo + cờ của bộ quy tắc
│       ├── app/phan_tich.py     # nhánh lệch, thời gian chờ, điểm nghẽn — chung cho hai bộ máy
│       └── app/bo_may/          # pm4py (mặc định) và noi_bo (dự phòng, Python thuần)
├── frontend/                    # Next.js — cổng người dùng
│   ├── app/
│   │   ├── api/auth/            # [H] ba chặng của luồng đăng nhập OIDC
│   │   ├── api/hop-thu/         # [H] số lời nhắn chưa đọc cho thanh bên tự hỏi
│   │   ├── yeu-cau/             # [H] cổng gửi yêu cầu — ba màn hình của #44
│   │   ├── dieu-phoi/           # [H] buồng lái điều phối viên — #82
│   │   ├── phong-ban/           # [H] buồng lái phòng ban — #83
│   │   ├── hop-thu/             # [H] hộp thư chung, kể cả trò chuyện nội bộ — #155, #156
│   │   ├── bao-cao/             # [D] bảng điều khiển nhúng (#305); quy-trinh/ là màn quy trình thực tế (#315)
│   │   ├── api/bao-cao/         # [D] token khách Superset; quy-trinh/ chuyển JSON khai phá (#315)
│   │   ├── globals.css          # token màu OKLCH, ba chế độ sáng/tối/in
│   │   └── layout.tsx           # phông chữ tải lúc dựng, không gọi ra ngoài
│   ├── components/              # bộ phận dùng lại giữa nhiều màn
│   ├── lib/                     # gọi dịch vụ, phiên, định dạng, siêu dữ liệu, chính sách nội dung
│   ├── proxy.ts                 # [H] CSP theo lượt, giới hạn đăng nhập quay về (#243)
│   └── package-lock.json        # TỆP KHÓA PHIÊN BẢN, bắt buộc commit
├── docs/
│   ├── adr/                     # bản ghi quyết định kiến trúc, kèm mẫu 0000
│   ├── ARCHITECTURE.md          # tệp này
│   ├── PROJECT_STATE.md         # trạng thái hiện tại, cập nhật hàng tuần
│   ├── ROADMAP.md               # lộ trình tới tháng 12
│   ├── process-flow.md          # sơ đồ trạng thái, nguồn của dữ liệu khởi tạo
│   ├── dependencies.md          # danh mục phụ thuộc và giấy phép
│   ├── so-sanh-san-pham.md      # so sánh với sản phẩm cùng loại (#277)
│   └── *-survey.md              # bảy tài liệu khảo sát Open-Core
├── e2e/                         # kiểm tra giao diện qua đăng nhập thật, Playwright (#238)
├── examples/
│   └── goi-loi/                 # [core] ứng dụng khác gọi API của lõi /core/v1 bằng tài khoản dịch vụ (#365)
├── docs-site/                   # trang tài liệu theo người đọc, dựng bằng Starlight (#279)
│   ├── src/content/docs/        # mỗi trang một tệp Markdown; dẫn sang docs/, không chép lại
│   └── package-lock.json        # TỆP KHÓA PHIÊN BẢN, bắt buộc commit
├── infra/                       # dựng cả cụm bằng một lệnh
│   ├── docker-compose.yml
│   ├── docker-compose.cum-thu.yml # tệp ghi đè dựng cụm thử cách ly cạnh cụm chính (#249)
│   ├── docker-compose.phat-trien.yml # tệp ghi đè mở lại cổng 8000, 5432 cho người phát triển (#364)
│   ├── .env.example
│   ├── cong-api/                # [core] cổng API APISIX (#364): config.yaml (tiến trình), apisix.yaml (tuyến, plugin)
│   ├── keycloak/                # realm nạp lúc khởi động: vai trò là dữ liệu
│   ├── seaweedfs/
│   ├── superset/                # ảnh dẫn xuất, ảnh gốc thiếu trình điều khiển
│   │   └── bang-dieu-khien/     # [D] dashboard dạng YAML, tự nạp lúc khởi động (#304)
│   ├── postgres/init/           # chỉ tạo hai database còn lại và tài khoản chỉ đọc
│   │   └── 01-tao-cac-database.sh
│   ├── tri-thuc/                # [H] khởi tạo kho tri thức Wiki.js (hồ sơ `tri-thuc`, #321) và bài mẫu
│   └── seed/                    # DỮ LIỆU — phần doanh nghiệp triển khai sửa, nạp lần đầu dựng cụm
│       ├── 01-quy-tac-quy-trinh.sql
│       ├── 02-co-cau-to-chuc.sql
│       └── 03-lich-lam-viec.sql
├── scripts/
│   ├── setup-labels.sh          # khởi tạo hệ thống nhãn
│   ├── sinh_nhat_ky_ao.py       # sinh nhật ký sự kiện ảo theo bộ quy tắc đang chạy
│   ├── nap_du_lieu_trinh_dien.py # nạp hồ sơ giả vào cụm thử để bảng điều khiển có số
│   ├── kiem_nang_cap.py         # chụp số liệu trước khi nâng cấp, so sau khi nâng (#254)
│   ├── sao_luu.py               # sao lưu tay, khôi phục, đối soát cơ sở dữ liệu và kho tệp (#245)
│   ├── doc_luu_tru.py           # đọc lại một bản lưu trữ lạnh, kiểm mã băm và số dòng (#378)
│   ├── pha_he.py                # sinh, kiểm trang phả hệ dữ liệu từ view và bảng điều khiển (#379)
│   ├── tai_khoan_dich_vu.py     # tạo, cập nhật tài khoản dịch vụ gọi lõi trên cụm đang chạy (#365)
│   ├── du_lieu/                 # hồ sơ đã giải quyết có nội dung thật cho dữ liệu trình diễn (#319)
│   ├── do_ho_so_tuong_tu.py     # đo recall@3, MRR của hồ sơ tương tự trên bộ 40 câu (#319)
│   └── kiem_chung/              # công cụ kiểm chứng chạy lại được (#249), chạy bằng `python -m`
│       ├── cum_thu.py           # dựng, hỏi trạng thái, gỡ cụm thử cách ly (tên, nhãn ảnh, cổng riêng)
│       ├── do_dang_nhap.py      # đăng nhập thật qua OIDC, mở trang, kiểm chuỗi mong đợi
│       ├── tao_ho_so_thu.py     # tạo hồ sơ ở từng trạng thái, qua engine; phần trong container ở tao_ho_so_trong_cum.py
│       ├── dot_bien.py          # phép thử đột biến theo tệp mô tả
│       └── vi_du/               # tệp mô tả đột biến chạy được (actor_not_requester.json)
├── .gitattributes               # chuẩn hóa ký tự kết thúc dòng
├── .gitignore
├── AGENTS.md                    # lối vào cho Antigravity, Codex — trỏ về CLAUDE.md
├── CHANGELOG.md                 # sinh tự động bằng git-cliff
├── CLAUDE.md                    # quy tắc cho mọi trợ lý AI làm việc trên kho
├── CONTRIBUTING.md              # quy trình làm việc và quy ước mã nguồn
├── LICENSE                      # MIT toàn văn (ngoại lệ services/khai-pha/ ở LICENSES.md)
├── LICENSES.md                  # bảng giấy phép theo thư mục, nghĩa vụ AGPL (#340)
├── NOTICE                       # thông báo bên thứ ba
├── README.md
└── cliff.toml                   # cấu hình sinh nhật ký thay đổi
```

### 4.2. Quy ước đặt thư mục cho phần thêm mới

Phần đã tồn tại xem mục 4.1 — đó là nguồn đúng về hiện trạng. Sơ đồ dưới đây là quy ước đặt chỗ ghi từ
đầu dự án để mỗi người không đặt một kiểu; chỗ nào lệch với mục 4.1 thì theo mục 4.1.

```
dx-os-lab/
├── frontend/                    # Next.js
│   ├── app/
│   │   ├── (portal)/            # [H] cổng người dùng, tự phục vụ
│   │   ├── (admin)/             # [H] quản trị, phân quyền
│   │   └── (dashboard)/         # [D] bảng điều khiển vận hành
│   ├── components/
│   ├── lib/
│   └── types/                   # kiểu dữ liệu dùng chung, nguồn duy nhất
│
├── backend/                     # FastAPI
│   ├── app/
│   │   ├── auth/                # [H] định danh, phân quyền
│   │   ├── workflow/            # [P] máy trạng thái, quy tắc chuyển
│   │   ├── rules/               # [P] ràng buộc Poka-yoke, SLA
│   │   ├── events/              # [P→D] sinh và lưu nhật ký sự kiện
│   │   ├── analytics/           # [D] truy vấn chỉ số, xuất dữ liệu mở
│   │   ├── intelligence/        # [I] phân loại, RAG, khai phá quy trình
│   │   └── models/              # lược đồ dữ liệu
│   ├── alembic/                 # migration
│   └── tests/
│
├── infra/
│   ├── docker-compose.yml       # dựng toàn hệ thống bằng một lệnh
│   ├── .env.example             # biến môi trường mẫu, giá trị chạy được ngay
│   └── seed/                    # dữ liệu khởi tạo, tự nạp khi khởi động
│
└── docs/
```

**Nguyên tắc đặt tên thư mục backend**: theo không gian kiến trúc, không theo tầng
kỹ thuật. Nghĩa là `workflow/` chứa cả model, service, router liên quan tới quy
trình — thay vì tách thành `models/`, `services/`, `routers/` rồi rải logic khắp nơi.

---

## 5. Khuôn mẫu: cấu hình thay vì mã cứng

Đây là khuôn mẫu quan trọng nhất của dự án. Ban đầu nó xuất phát từ ràng buộc đề thi
tháng 11, nhưng từ 10/09/2026 nó được nâng thành **mục tiêu sản phẩm** — xem mục 5.1.

**Quy tắc**: trạng thái, vai trò, phòng ban, loại yêu cầu, ngưỡng SLA, danh mục chỉ số —
tất cả nằm trong **cấu hình hoặc bảng dữ liệu**, tuyệt đối không mã cứng trong mã nguồn.

| Thuộc kiến trúc (giữ nguyên khi đổi đề) | Thuộc nghiệp vụ (thay được bằng dữ liệu) |
|---|---|
| Cơ chế máy trạng thái và quy tắc chuyển | Tên và số lượng trạng thái |
| Hệ phân quyền theo vai trò | Danh sách vai trò |
| Cơ chế định tuyến yêu cầu | **Danh sách phòng ban, loại yêu cầu, và bảng ánh xạ loại → phòng ban** |
| Cơ chế theo dõi SLA và cảnh báo | Ngưỡng thời gian từng loại yêu cầu |
| Quy trình truy xuất tri thức, cách lập chỉ mục | Nội dung kho tri thức |
| Khung bảng điều khiển, cách truy vấn | Danh mục chỉ số cụ thể |
| Cấu trúc nhật ký sự kiện, thuật toán khai phá | Tên các hoạt động trong quy trình |

Nếu tuân thủ, việc thích ứng với đề thi mới chỉ là thay dữ liệu khởi tạo.

### 5.1. Vì sao đây là mục tiêu sản phẩm, không chỉ là biện pháp đối phó

Buổi trao đổi với giảng viên hướng dẫn ngày 10/09/2026 đặt thêm một yêu cầu: sản phẩm phải
để **một doanh nghiệp bất kỳ tải về rồi tự tùy biến** phòng ban, loại yêu cầu và quy trình
theo đặc thù của họ, mà không cần sửa mã.

Điều này đổi bản chất của khuôn mẫu. Trước đây nó là cách giảm rủi ro khi đề thi công bố
muộn; giờ nó là **một tính năng người dùng thấy được**, và là lý do tồn tại của vai trò
`administrator` trong bộ năm vai trò.

Hệ quả cụ thể khi viết mã:

- Mọi danh mục nghiệp vụ đều có bảng riêng, không phải hằng số trong mã hay kiểu liệt kê
- Có màn hình quản trị để sửa các bảng đó, không bắt người dùng đụng vào cơ sở dữ liệu
- Dữ liệu khởi tạo chỉ là **ví dụ mẫu**, không phải phần cứng của sản phẩm

Danh sách đầy đủ các chiều cấu hình được ghi ở [`process-flow.md`](process-flow.md) mục 7.

**Kiểm tra nhanh**: nếu một chuỗi như `"Đang xử lý"` xuất hiện trong câu lệnh `if`
của mã nguồn, đó là vi phạm. Trạng thái phải tra từ bảng.

### 5.2. Lược đồ cấu hình đã hiện thực

Mười bảy bảng, định nghĩa ở bản sửa gốc `0000_luoc_do_cau_hinh` của Alembic (SQL thô ở
`backend/alembic/sql/`, từ #254 — trước đó là lược đồ khởi tạo của PostgreSQL), chia năm nhóm:

| Nhóm | Bảng | Vai trò |
|---|---|---|
| Phiên bản | `rule_sets` · `processes` | Hồ sơ cũ chạy theo quy tắc cũ khi quản trị viên sửa luồng giữa chừng — mục 6.1. Từ #376 mỗi bộ thuộc một quy trình (`processes`, bản sửa `0028`) — mục 2.3 |
| Máy trạng thái | `states` · `transitions` · `roles` · `transition_roles` · `guards` · `transition_guards` | Trạng thái, cạnh chuyển, ma trận phân quyền, ràng buộc Poka-yoke theo cạnh |
| Cơ cấu tổ chức | `departments` · `request_types` · `request_type_fields` · `request_type_routing` · `priorities` | Phần doanh nghiệp triển khai sửa đầu tiên; trường riêng theo loại ở mục 5.3 |
| Lời nhắn | `message_kinds` · `message_kind_roles` | Loại lời nhắn trên hồ sơ và vai trò gửi được từng loại (#128), kể cả loại nội bộ ẩn với người gửi (#156) — xem mục 6.2 |
| Lịch làm việc | `work_calendars` · `work_hours` · `holidays` | Giờ làm theo thứ, ngày nghỉ, múi giờ (#199). Mọi khoảng thời gian của quy trình đo bằng giờ làm việc theo lịch mặc định — xem mục 7.1 |

**Lược đồ và dữ liệu để tách nhau có chủ ý.** Lược đồ nằm trong chuỗi migration vì nó
thuộc kiến trúc; dữ liệu khởi tạo nằm trong `infra/seed/` vì nó chỉ là ví dụ mẫu mà công ty
khác sẽ xóa đi khai lại. Lẫn hai thứ vào nhau thì người triển khai phải dò giữa hai loại nội
dung khác hẳn nhau. Dữ liệu khởi tạo nạp **một lần**, lúc dựng cụm, và đổi cấu hình của cụm
đang chạy là việc của bản sửa dữ liệu — mục 5.4.

**Ba lớp bảo vệ, không lớp nào nằm trong mã ứng dụng:**

1. **Khóa ngoại** chặn cạnh trỏ tới trạng thái không tồn tại. Thêm một mẹo nhỏ: cột
   `transitions.from_is_terminal` tham chiếu tới `states (rule_set_id, code, is_terminal)`
   nên luôn khớp trạng thái nguồn, và một `CHECK` buộc cạnh rời khỏi trạng thái kết thúc
   phải khai `reopen_window_hours` — **chỉ cạnh mở lại có cửa sổ thời gian** (#102) rời được
   một trạng thái kết thúc, không thể tạo cạnh thường đi ra từ đó. Trước #102 `CHECK` cấm
   hẳn; "kết thúc" nay nghĩa là hết chu kỳ hồ sơ, chưa hẳn là không còn đường ra
2. **Chỉ mục duy nhất từng phần** bảo đảm mỗi bộ quy tắc có đúng một trạng thái bắt đầu,
   mỗi lúc mỗi quy trình có đúng một bộ quy tắc kích hoạt (#376), mỗi loại yêu cầu có đúng một phòng ban mặc định
3. **Kiểm tra mức đồ thị** — hàm `kiem_tra_cau_hinh()` trong cơ sở dữ liệu (bản sửa `0018`,
   #254; trước đó là khối `infra/seed/99-…` chỉ chạy lúc nạp) — bắt những
   lỗi mà từng dòng vẫn hợp lệ nhưng cả luồng thì hỏng: ngõ cụt không phải trạng thái
   đóng, trạng thái không tới được từ điểm vào, cạnh không vai trò nào đi được, và từ #79
   là trạng thái chờ có đường vào mà thiếu đường quay về tương ứng, từ #127 là cạnh tự trỏ
   ở trạng thái chờ, từ #128 là loại lời nhắn không vai trò nào gửi được, từ #199 là lịch
   làm việc thiếu lịch mặc định, sai tên múi giờ, không có giờ làm hay có khung chồng nhau, từ #255
   (bản sửa `0025`) là loại yêu cầu đang dùng mà phòng mặc định đã ngưng, hay không còn loại yêu cầu
   nào đang dùng. Hàm chạy mỗi lần dịch vụ khởi động, trước mỗi lần kích hoạt bộ quy tắc mới và trong
   mỗi lần sửa trên màn quản trị cấu hình (mục 5.5); sai một điều thì
   **dịch vụ dừng khởi động** hay **bản cập nhật bị từ chối**, thay vì chạy với luồng hỏng rồi
   để một hồ sơ thật mắc kẹt mới lộ ra

Hai ràng buộc Poka-yoke quan trọng nhất **không có dòng dữ liệu nào** vì chúng được thực
thi bằng sự vắng mặt: *đã nhận là không trả về* và *chỉ hủy trước khi vào xử lý*. Không
phải "không nên đi", mà là "không có đường mà đi". Khóa sửa nội dung sau khi hồ sơ tới
phòng ban (#127) cũng thực thi theo đúng cách đó.

**Cạnh tự trỏ được phép từ ADR-0005** (#127) — lược đồ gỡ ràng buộc `CHECK (from_state <>
to_state)`. Vì sao cần cạnh tự trỏ: mục 6.2.

**Một cặp trạng thái: tối đa một cạnh người, một cạnh hệ thống** (#142). Ràng buộc là
`UNIQUE (rule_set_id, from_state, to_state, is_system)` — *Chờ phòng ban xác duyệt → Đã phân
loại* có cả cạnh điều phối viên rút hồ sơ lẫn cạnh hệ thống tự trả về. Người không đi được cạnh
hệ thống và ngược lại, nên engine tra cạnh bằng cặp trạng thái cộng loại tác nhân; API và giao
diện chỉ thấy cạnh của người nên vẫn nhận diện bằng cặp. Dữ liệu khởi tạo gắn vai trò và ràng
buộc bằng phép nối theo cặp — phép nối đó phải bỏ cạnh hệ thống, không thì cạnh hệ thống nhận
luôn vai trò của cạnh người cùng cặp.

Cột `is_initial` đáng chú ý riêng: nhờ nó mà mã nguồn hỏi *"trạng thái bắt đầu là gì"*
thay vì viết `if state == "submitted"`. Mỗi cột kiểu này là một câu lệnh `if` không bao
giờ phải viết.

### 5.3. Trường thông tin riêng theo loại yêu cầu

**Đã cài đặt** — #250.

Mỗi loại yêu cầu khai danh sách trường của nó trong bảng cấu hình `request_type_fields`: mã,
nhãn, kiểu (`text`, `number`, `date`, `choice`), bắt buộc hay không, câu hướng dẫn, đơn vị, lựa
chọn. Giá trị lưu ở cột JSONB `requests.details` (migration `0013`), khóa là mã trường — một
cột thay vì bảng mỗi giá trị một dòng, để danh sách đọc một lần và PostgreSQL, Superset vẫn lọc
được theo khóa.

Ba nơi đọc cùng một khai báo, không nơi nào biết tên trường:

| Nơi | Làm gì |
|---|---|
| `GET /request-types` | Mỗi loại kèm `fields`; biểu mẫu gửi dựng ô từ đây (`components/o-truong-rieng.tsx`) |
| `app/rules/truong_rieng.py` | `kiem_chi_tiet` kiểm và chuẩn hóa: khóa lạ, sai kiểu, thiếu bắt buộc thì từ chối bằng nhãn trường ("Chưa điền Vị trí.") |
| `GET /requests/{id}` | `details` và `detail_fields` của loại hiện tại; trường khai mà chưa có giá trị hiện "chưa có" |

Sửa sau khi gửi đi qua cạnh **Sửa nội dung** (ADR-0005), như tiêu đề và mô tả: `details` nằm
trong `CHANGEABLE_FIELDS`, ràng buộc `edit-content` quản nó và kiểm theo loại *sau khi sửa*.
Người gửi đổi loại mà không gửi trường riêng thì bộ cũ bị bỏ và trường bắt buộc của loại mới
được nhắc. Nhật ký ghi bộ cũ và bộ mới; dòng thời gian kể bằng nhãn ("Vị trí: Tầng 3 → Tầng 5").
Điều phối viên đổi loại lúc phân loại thì **không** bị chặn — trường thiếu hiện "chưa có", họ
hỏi thêm người gửi nếu cần.

`create_case` chỉ kiểm khi được truyền `details`: `None` là lối gọi nội bộ chưa có trường riêng
(bộ sinh dữ liệu, kiểm thử cũ). Điểm cuối gửi yêu cầu luôn truyền một bộ, nên người dùng không
lách được phép kiểm. Đổi bảng cấu hình là một bản sửa Alembic, như mọi bảng cấu hình khác
(mục 5.4).

### 5.4. Nâng cấp giữ nguyên dữ liệu

**Đã cài đặt** — #254. Mốc bắt đầu là `v0.9.1`: cụm dựng từ bản đó trở đi nâng lên bản mới bằng
`up -d --build`, không mất hồ sơ, nhật ký hay tệp; bản cũ hơn vẫn phải dựng lại.

Trước #254, bảng cấu hình do lược đồ khởi tạo của PostgreSQL tạo, dữ liệu do `infra/seed/` nạp — cả
hai chạy đúng một lần lúc tạo thực thể, ngoài tầm Alembic. Mọi thay đổi cấu hình buộc `down -v`, và
hai nguồn sự thật cho lược đồ làm nâng cấp không đồng nhất. Nay mỗi loại thay đổi có đúng một đường:

| Thay đổi | Đi đường nào | Cụm đang chạy |
|---|---|---|
| Lược đồ — bảng, cột, ràng buộc, hàm, view | Bản sửa Alembic mới trong `backend/alembic/versions/` | Tự chạy lúc dịch vụ khởi động |
| Dữ liệu quy trình — trạng thái, cạnh, vai trò đi cạnh, ràng buộc trên cạnh | Bản sửa dữ liệu tạo **bộ quy tắc phiên bản mới** (dưới) | Hồ sơ đang chạy giữ bộ cũ, hồ sơ mới nhận bộ mới |
| Dữ liệu dùng chung — phòng ban, loại yêu cầu, lịch, loại lời nhắn | Màn quản trị cấu hình (mục 5.5) cho các trường mở trên màn; còn lại là bản sửa dữ liệu sửa thẳng dòng, rồi gọi `kiem_tra_cau_hinh()` | Áp ngay cho mọi hồ sơ |
| Dữ liệu mẫu cho cụm dựng mới | Sửa `infra/seed/` | Không đụng — bộ nạp không nạp lại |

**Khởi động dịch vụ, ba bước** (`backend/docker-entrypoint.sh`):

1. `alembic upgrade head`. Cụm dựng mới đi trọn chuỗi từ bản gốc `0000` (tạo mười bảy bảng cấu hình và
   hai hàm giờ làm việc). Cụm từ v0.9.x đã ghi một bản sau trong `alembic_version`, nên Alembic coi
   `0000` là tổ tiên đã chạy và chỉ chạy bản còn thiếu — đây là lý do bản gốc được chèn **trước** `0001`
   mà không cụm cũ nào phải chạy lại nó. SQL của `0000` là ảnh chụp lược đồ tại v0.9.1: không sửa nữa
2. `python -m app.cau_hinh.khoi_tao`: xin khóa tư vấn (chạy nhiều bản dịch vụ thì một bản nạp, các bản
   kia chờ); chưa có bộ quy tắc nào thì chạy lần lượt `infra/seed/*.sql` (gắn vào container ở `/seed`);
   lần nào cũng gọi `kiem_tra_cau_hinh()`. Một giao dịch: nạp dở hay kiểm hỏng thì không gì được ghi,
   lệnh thoát mã lỗi, dịch vụ không lên
3. Máy chủ ứng dụng

PostgreSQL chỉ còn `infra/postgres/init/01-…`: tạo hai database của Keycloak, Superset và tài khoản
chỉ đọc kèm quyền đọc mặc định — bảng do migration tạo về sau vẫn đọc được, vì cùng chủ sở hữu.

**Bộ quy tắc phiên bản mới** (`app/cau_hinh/bo_quy_tac.py`). Hồ sơ ghim `rule_set_id` lúc tạo, engine
chỉ tra trạng thái và cạnh trong đúng bộ đó, hàng đợi thấy mọi bộ còn hồ sơ mở (#278). Nên đổi luồng
không sửa bộ đang chạy, mà trong **một** bản sửa Alembic:

```python
from alembic import op
from sqlalchemy import text

from app.cau_hinh.bo_quy_tac import kich_hoat, sao_chep


def upgrade() -> None:
    ket_noi = op.get_bind()
    cu = ket_noi.execute(text("SELECT id FROM rule_sets WHERE is_active AND process_code = :qt"),
                         {"qt": "internal-requests"}).scalar_one()  # bộ đang bật của MỘT quy trình (#376)
    moi = sao_chep(ket_noi, cu, "v2", "Thêm bước xác nhận của trưởng phòng")
    ket_noi.execute(text("INSERT INTO transitions (rule_set_id, from_state, …) VALUES (:moi, …)"),
                    {"moi": moi})
    kich_hoat(ket_noi, moi)  # gọi kiem_tra_cau_hinh() trước khi đổi bộ đang bật
```

`sao_chep` chép trạng thái, cạnh, vai trò đi cạnh và ràng buộc trên cạnh sang một bộ chưa bật — cột
tra từ `information_schema` lúc chạy, nên thêm cột cấu hình về sau vẫn chép đủ; đổi được mã trạng
thái ngay trên đường chép. `kich_hoat` gọi `kiem_tra_cau_hinh()` rồi mới đổi bộ đang bật (hai câu
`UPDATE` riêng vì chỉ mục duy nhất từng phần). Bộ mới tạo ngõ cụt hay trạng thái không tới được thì
PostgreSQL ném lỗi, cả bản sửa hoàn tác, dịch vụ không lên với cấu hình hỏng.

**Kiểm chứng.** `tests/test_cau_hinh.py` dựng một lược đồ PostgreSQL tạm trong giao dịch của bài, chạy
SQL của `0000` và `0018` rồi bộ nạp — cấu hình ra phải y hệt cụm đang chạy, lần sau không nạp lại; chép
bộ đang bật, thêm một cạnh, kích hoạt — hồ sơ mới đi được cạnh mới, hồ sơ cũ thì không; bộ có ngõ cụt
bị từ chối và không để lại gì. Lần nâng thật kiểm bằng `scripts/kiem_nang_cap.py`: chụp số dòng và mã
băm cột cố định của hồ sơ, nhật ký, lời nhắn, tệp đính kèm cùng sự có mặt của từng tệp trong kho trước
khi nâng, rồi so sau khi nâng. Cách nâng cho người dùng: README mục nâng cấp và trang tài liệu.

### 5.5. Màn quản trị cấu hình

**Đã cài đặt** — #255 (`backend/app/cau_hinh/quan_tri.py`, `frontend/app/quan-tri/cau-hinh/`). Phạm vi
giảng viên chốt ngày 13/11/2026: xem bộ quy tắc đang chạy, sửa phần ít rủi ro; đồ thị quy trình vẫn chỉ đổi
bằng bộ quy tắc phiên bản mới (mục 5.4).

| | |
|---|---|
| Ai | Chỉ vai `administrator`, gác ở dịch vụ (`require_roles`) — giao diện chỉ ẩn mục thanh bên |
| Xem | Trạng thái và cạnh của bộ đang bật kèm vai trò, ràng buộc, hạn chờ tự đi; loại yêu cầu, mức ưu tiên, phòng ban kèm số hồ sơ đang mở; lịch mặc định; 50 dòng nhật ký sửa mới nhất |
| Sửa | Loại yêu cầu: tên, mô tả, `sla_hours`, `sla_grace_hours`, `sla_warn_percent`, `is_active`, phòng mặc định. Mức ưu tiên: tên, `sla_factor_percent`. Phòng ban: tên, mô tả, `is_active` |
| Không | Thêm hay xóa dòng (phòng ban mới cần người trong Keycloak), lịch làm việc, đồ thị quy trình |

**Áp ngay, có xem trước.** Đây là "dữ liệu dùng chung" của mục 5.4: sửa thẳng dòng, có hiệu lực cho mọi
hồ sơ kể cả hồ sơ đang mở — hạn tính lúc đọc từ `sla_hours` × `sla_factor_percent` (mục 7.1), không có bản
sao nào phải cập nhật. Phương án loại: chụp hạn vào hồ sơ lúc tạo để chỉ hồ sơ mới theo hạn mới — phải
thêm cột, sửa engine lẫn truy vấn của bộ quét, trong khi người quản trị đổi hạn thường muốn áp ngay. Bù lại,
mỗi lần sửa có lượt **chạy thử** (`dry_run`) đi trọn đường thật rồi hoàn tác, để màn báo "N hồ sơ đang mở
sẽ đổi hạn" trước khi người sửa bấm Lưu.

**Một lần sửa, một giao dịch** (điểm lưu lồng trong phiên): ghi dòng cấu hình → `kiem_tra_cau_hinh()` →
một dòng `config_changes` cho mỗi trường đổi giá trị. Hàm kiểm ném lỗi thì cả lần sửa hoàn tác, câu lỗi
của hàm (đã là tiếng Việt) về tới màn. Danh sách trường sửa được, nhãn và khoảng giá trị khai một chỗ
(`DANH_MUC` trong `quan_tri.py`); đó là ranh giới kiến trúc — cột nào an toàn để sửa lúc chạy — còn giá trị
vẫn nằm trong bảng. Giao diện đọc nhãn trường từ dịch vụ, không giữ bản sao.

**Nhật ký thay đổi cấu hình** — bảng `config_changes` (bản sửa `0025`): ai (mã và tên tại thời điểm sửa),
lúc nào (UTC), bảng, mã dòng, trường, giá trị cũ và mới dạng JSON. Chỉ ghi thêm, chặn bằng trigger như
`event_log` và `case_messages`. Bảng tách khỏi `event_log` có chủ ý: nhật ký sự kiện là lịch sử của từng
hồ sơ cho khai phá quy trình, mỗi dòng mang `case_id`; sửa cấu hình không thuộc hồ sơ nào.

**Kiểm chứng.** `tests/test_quan_tri_cau_hinh.py`: vai khác bị 403; đổi hạn thì hồ sơ đang mở và hồ sơ mới
cùng theo hạn mới; chạy thử không để lại dòng nào; ngưng phòng đang là mặc định và tắt loại yêu cầu cuối
cùng bị từ chối; nhật ký không sửa được. Ba phép đột biến (bỏ lệnh gọi hàm kiểm, bỏ hoàn tác chạy thử, bỏ
ghi nhật ký) đều làm bài đỏ. `e2e/` có ba bài đăng nhập thật: sửa hạn có xem trước và nhật ký, đổi tên
phòng, lần sửa hỏng bị chặn kèm lý do.

---

## 6. Khuôn mẫu: nhật ký sự kiện

**Đã cài đặt** — bảng `event_log`, mô hình ở `backend/app/models/case.py`, nơi ghi
duy nhất ở `backend/app/events/log.py`.

Mọi lần chuyển trạng thái trong không gian `P` **bắt buộc** phát sinh một bản ghi
vào nhật ký sự kiện, với cấu trúc tối thiểu:

| Trường | Ý nghĩa |
|---|---|
| `case_id` | Định danh hồ sơ, nối các sự kiện thuộc cùng một yêu cầu |
| `activity` | Tên hoạt động, ví dụ `Tiếp nhận`, `Phân công`, `Phê duyệt` |
| `timestamp` | Mốc thời gian, **luôn lưu theo UTC** |
| `actor` | Người hoặc hệ thống thực hiện |
| `from_state` / `to_state` | Trạng thái trước và sau |

Nhật ký này là tài sản quý nhất của hệ thống: nó nuôi bảng điều khiển ở `D` và
thuật toán khai phá quy trình ở `I`.

**Lưu ý về múi giờ**: lưu UTC là bắt buộc. Lưu giờ cục bộ sẽ làm sai lệch kết quả
khai phá quy trình khi so sánh giữa các bản ghi. Cột dùng kiểu `TIMESTAMPTZ` và mốc
thời gian do PostgreSQL tự điền bằng `now()` — một đồng hồ duy nhất cho cả cụm, thay
vì mỗi tiến trình một đồng hồ lệch nhau vài giây.

Ba quyết định cài đặt đáng ghi lại:

**Nhật ký chỉ ghi thêm.** Một trigger PL/pgSQL chặn mọi `UPDATE` và `DELETE` trên
`event_log`. Ràng buộc đặt ở tầng cơ sở dữ liệu chứ không ở tầng ứng dụng, vì
Superset, công cụ quản trị và mọi kết nối `psql` đều đi vòng qua tầng ứng dụng. Lịch
sử sửa được thì không còn là lịch sử.

**Tạo hồ sơ không sinh sự kiện.** Tạo hồ sơ không phải một lần *chuyển* trạng thái —
không có trạng thái nào trước nó, và không có cạnh nào trong bảng `transitions` ứng với
việc tạo. (Từ #79 có một cạnh quay *về* trạng thái đầu — bổ sung thông tin xong thì hồ
sơ về lại tay điều phối — nhưng đó là một lần chuyển thật, có dòng nhật ký như mọi lần
khác.) Mốc bắt đầu của hồ sơ là cột `requests.created_at`. Khi xuất dữ
liệu cho khai phá quy trình, tầng `D` dựng thêm một sự kiện mở đầu từ cột đó nếu công
cụ phân tích cần. Cách này tránh phải bịa một mã hoạt động không có trong dữ liệu.

**Thêm cột `note`** ngoài sáu trường bắt buộc, chứa lý do của những cạnh mang cờ
`requires_note` — từ chối vì sai chuyên môn, đóng hồ sơ khi không phòng nào nhận, mở
lại vì chưa đạt. Lý do thuộc về *lần chuyển*, không thuộc về hồ sơ: mỗi lần từ chối
có lý do riêng của nó. Ghi chú không phải lúc nào cũng là lý do: ở cạnh hỏi thêm nó là
câu hỏi, ở cạnh bổ sung thông tin nó là câu trả lời. Cột `transitions.note_label` (#79)
đặt tên cho ô ghi chú của từng cạnh, và dòng thời gian gọi ghi chú bằng đúng tên đó.

**Thêm cột `changes`** (#100): những trường quyết định — từ #127 cả hai trường nội dung
`title`, `description` — mà lần chuyển này **đổi giá trị**, dạng `{trường: {from, to}}`,
kiểu JSONB. Hồ sơ chỉ mang giá trị hiện tại; lịch
sử đổi nằm ở đây. Trước #100, điều phối viên sửa loại yêu cầu người gửi chọn sai thì
giá trị cũ bị ghi đè và mất dấu — mất đúng dữ liệu "người gửi hay chọn nhầm loại nào",
"bảng ánh xạ loại sang phòng sai ở đâu" mà tầng `I` cần. Ba quy tắc:

- Chỉ ghi trường thật sự đổi. Gửi lại đúng giá trị đang có không sinh ra dòng "A → A";
  không đổi gì thì cột để NULL
- Ghi mã, nhãn tra lúc đọc — kể cả mục đã ngừng dùng, để lịch sử cũ vẫn đọc được bằng
  tên. Riêng người xử lý ghi kèm tên cũ và mới tại thời điểm đổi, cùng lý do với
  `actor_label`: định danh Keycloak không tự nói lên người nào
- Ghi ở bước 4 của `perform_transition`, lúc hồ sơ chưa bị ghi đè — sau bước 5 thì giá
  trị cũ mất. Cùng một giao dịch với lần chuyển, nên không có khe nào để lịch sử lệch

**Dữ liệu cá nhân trong nhật ký** (#246, ADR-0009). Nhãn tên (`actor_label` và các cột `*_label` khác) là
dữ liệu cá nhân. Yêu cầu xóa được xử lý bằng ẩn danh hóa nhãn tên qua một lối sửa có kiểm soát, không xóa
dòng — tính chất chỉ ghi thêm và kết quả khai phá giữ nguyên. Thời hạn lưu giữ là cấu hình, mặc định giữ
mãi. Bảng kiểm kê dữ liệu cá nhân và thiết kế cài đặt ở ADR-0009.

### 6.1. Cơ chế bảo đảm: một cửa duy nhất

Nhật ký chỉ có giá trị nếu **không bao giờ thiếu bản ghi**. Một nhật ký thủng làm sai
lệch kết quả khai phá quy trình, và khi đó điểm sáng tạo của đề tài mất giá trị.

Cơ chế bảo đảm điều này: **mọi lần đổi trạng thái đi qua đúng một điểm trong mã**, và
điểm đó lần lượt tra bảng quy tắc chuyển, kiểm quyền theo vai trò, chạy ràng buộc
Poka-yoke, ghi nhật ký, rồi mới cập nhật trạng thái hồ sơ.

Không tồn tại đường nào khác để đổi trạng thái. Bất kỳ chỗ nào cập nhật trạng thái trực
tiếp đều là vi phạm khuôn mẫu, kể cả khi nó "chỉ sửa một trường".

**Đã cài đặt** — `backend/app/workflow/engine.py`, hàm `perform_transition`. Cách soát
lại khuôn mẫu này khi review:

```bash
grep -rn 'current_state\s*=' backend/app --include='*.py' | grep -v '=='
```

Kết quả chỉ được có hai dòng, cả hai trong `engine.py`: một ở `create_case` đặt trạng
thái đầu, một ở `perform_transition` đặt trạng thái đích. Dòng thứ ba ở bất kỳ tệp nào
khác là một lần chuyển không có bản ghi nhật ký.

Hai chi tiết cài đặt giữ cho bảo đảm này không rò rỉ:

- **Khóa dòng hồ sơ** bằng `SELECT ... FOR UPDATE` ngay đầu hàm. Không có nó, hai yêu
  cầu đồng thời cùng đọc trạng thái cũ rồi cùng ghi nhật ký
- **Danh sách trắng các trường được đặt.** Một lần chuyển chỉ đặt được bốn trường quyết
  định và, từ #127, hai trường nội dung; `current_state` và mọi trường `suggested_*` đều
  nằm ngoài. Nhờ vậy không ai
  dùng lần chuyển trạng thái làm cửa sau để sửa trường bất kỳ

**Đổi quy trình giữa chừng: hồ sơ đi theo bộ quy tắc của chính nó** (#278, #299). `create_case`
ghi vào hồ sơ `rule_set_id` của bộ đang bật, và cột đó giữ nguyên tới khi hồ sơ kết thúc. Mọi chỗ
tra cấu hình đều tra theo bộ **của hồ sơ**, không theo bộ đang bật: cạnh đi được và nút trên giao
diện (`allowed_transitions`, bước chính), bước 1 của `perform_transition`, cờ `sla_running` của
đồng hồ hạn, bộ quét quá hạn và bộ quét hạn chờ. Doanh nghiệp bật một bộ mới thì:

| | Hồ sơ tạo trước khi đổi | Hồ sơ tạo sau |
|---|---|---|
| Bộ quy tắc | bộ cũ, tới khi kết thúc | bộ đang bật |
| Nút, cạnh đi được | cạnh của bộ cũ — cạnh bộ mới đã bỏ vẫn đi được | cạnh của bộ mới |
| Nhật ký sự kiện | mã hoạt động của bộ cũ | mã hoạt động của bộ mới |
| Đồng hồ hạn | chạy ở những trạng thái bộ cũ bật `sla_running` | theo bộ mới |
| Hàng đợi, Hồ sơ của tôi, hộp thư | vẫn có mặt, xét theo trạng thái hàng đợi, nhãn, kết thúc của bộ cũ | như thường |

Bật lại bộ cũ cũng chỉ đổi hồ sơ tạo sau đó. Không có đường chuyển một hồ sơ đang chạy sang bộ
mới — nếu cần thì phải là một lần chuyển có dòng nhật ký, chưa có thiết kế. Nhật ký giữ đúng sự
thật của lúc xảy ra, nên khai phá quy trình tách được từng phiên bản theo `rule_set_id`.

Màn liệt kê lấy hồ sơ của mọi bộ trong `rule_sets_in_use` — bộ đang bật, rồi các bộ cũ còn hồ sơ
chưa kết thúc — và chọn hồ sơ bằng cặp (bộ, trạng thái), không bằng mã trạng thái thôi: hai bộ có
thể dùng cùng một mã cho hai vai khác nhau, ví dụ bộ mới giao cho điều phối viên một cạnh rời *Đang
xử lý*. Dải lọc gộp nhóm theo mã, nhãn lấy từ bộ đang bật trước. Trước #299 hai hàng đợi chỉ lọc
theo bộ đang bật: vừa đổi bộ là hồ sơ cũ còn mở biến khỏi hàng đợi, dù vẫn chạy đồng hồ và vẫn tự
leo thang. `backend/tests/test_hai_bo_quy_tac.py` chép bộ đang bật thành bộ thứ hai ngay trong giao
dịch của bài, đổi sáu chỗ như một lần đổi quy trình thật, rồi cho hồ sơ của cả hai bộ đi tiếp.

Quyết định tự viết engine máy trạng thái thay vì lắp ghép nền tảng có sẵn xuất phát chính
từ yêu cầu này — xem [ADR-0004](adr/0004-tu-viet-engine-may-trang-thai.md).

### 6.2. Ranh giới: thao tác nào đi qua cửa chuyển trạng thái

**Đã cài đặt** — phần cạnh ở #127, phần lời nhắn ở #128. Quyết định ở
[ADR-0005](adr/0005-ranh-gioi-may-trang-thai.md), giảng viên duyệt ngày 24/09/2026.

Quy tắc một câu: **thao tác đổi hồ sơ thì là cạnh; thao tác không đổi gì thì không.**

| Thao tác | Đổi gì trên hồ sơ | Đi đường nào |
|---|---|---|
| Chuyển trạng thái | `current_state`, có thể kèm trường quyết định | Cạnh thường |
| Nhận việc về mình, sửa nội dung ở *Đã gửi* | Người xử lý; tiêu đề, mô tả, loại | **Cạnh tự trỏ** — trạng thái giữ nguyên |
| Lời nhắn hai chiều, hỏi tiến độ, nhắn nội bộ | Không đổi gì | Bảng lời nhắn `case_messages` (#128, #156) — không phải cạnh, không vào `event_log` |
| Đánh dấu đã đọc lời nhắn | Không đổi gì | Bảng `case_message_reads` (#155) — mốc đã đọc của từng người, mỗi cuộc một mốc (#156), không vào `event_log` |

Vì sao thao tác đổi hồ sơ mà không đổi trạng thái vẫn phải là cạnh: mọi thay đổi trên hồ
sơ cần một dòng nhật ký giữ giá trị cũ (cột `changes`), cần qua kiểm quyền và ràng buộc
Poka-yoke, và chỉ `perform_transition` làm đủ cả ba. Một điểm cuối "chỉ sửa một trường"
là đúng loại cửa sau mà mục 6.1 cấm. Ngược lại, lời nhắn mà đi qua cửa chuyển trạng thái
thì nhật ký — nguồn của khai phá quy trình — lẫn đầy những hoạt động không đổi gì, và mỗi
trạng thái cần nhiều cạnh tự trỏ, phá chỉ mục duy nhất ở mục 5.2.

Bốn hệ quả mã nguồn phải giữ:

- Dòng nhật ký tự trỏ có `from_state = to_state`. Nó không đưa hồ sơ **vào** trạng thái
  nào, nên ràng buộc `return-to-previous-state` bỏ qua nó khi tìm chỗ cũ (mục 7)
- Số lần đổi trạng thái trên dòng thời gian không đếm mốc tự trỏ; mốc đó hiện là *Giữ
  nguyên trạng thái*. Nhãn *Quay lui* từ #153 đếm theo **cạnh làm lại khai trong dữ liệu**
  — cột `transitions.is_rework`, dịch vụ trả kèm từng mốc lịch sử — chứ không theo trạng
  thái lặp: hỏi đáp bổ sung thông tin, phân công lại sau leo thang không tính
- Không có cạnh tự trỏ ở trạng thái chờ người khác — hồ sơ đang chờ người gửi trả lời mà
  bị sửa tại chỗ thì câu hỏi mất nghĩa. Phép kiểm đồ thị số 7 chặn khởi động nếu có
- Mỗi cạnh trong `allowed_transitions` mang cờ `keeps_state`, để giao diện nói "trạng
  thái giữ nguyên" thay cho "hồ sơ sẽ chuyển sang" — suy từ cặp trạng thái, không tra bảng

**Phần lời nhắn** (#128, `backend/app/workflow/messages.py`). Bảng `case_messages` do
Alembic sở hữu và chỉ ghi thêm như `event_log` — trigger chặn UPDATE và DELETE. Loại lời
nhắn là cấu hình: `message_kinds` và `message_kind_roles` của lược đồ khởi tạo, chốt với
navigator ngày 24/09/2026. Luật gửi:

1. **Ai mở được hồ sơ thì nhắn được.** Không thêm quyền nhìn thấy nào: mỗi buồng lái dùng
   lại đúng cửa của trang chi tiết — người gửi trên hồ sơ của mình, điều phối viên trên
   mọi hồ sơ, người của phòng trên hồ sơ của phòng mình. Bảng chỉ thu hẹp thêm theo vai trò
2. Hồ sơ ở trạng thái kết thúc thì lời nhắn chỉ đọc
3. `owner_only` — chỉ người gửi của chính hồ sơ. `department_stage_only` — chỉ khi hồ sơ
   nằm trong hàng đợi phòng ban, tập trạng thái suy bằng đúng hàm của hàng đợi
   (`trang_thai_hang_doi_phong_ban`), nên "hồ sơ đang ở phòng ban" nghĩa là một thứ ở mọi nơi
4. `reask_after_hours` — luật hỏi lại: gửi lại loại đó chỉ khi phía bên kia đã nhắn sau
   lần gửi trước, hoặc đã quá chừng ấy giờ. "Hỏi tiến độ" vì vậy không bấm dồn được, và
   số lần phòng ban bị hối mà tầng `I` đếm là số thật. Loại đang chờ vẫn có trong danh sách
   loại gửi được, kèm mốc `retry_at`, để giao diện nói rõ vì sao nút mờ
5. `hidden_from_requester` — trò chuyện nội bộ (#156): người gửi của **chính hồ sơ** không đọc,
   không gửi được loại đó, kể cả khi họ cũng là nhân viên. Ràng buộc theo hồ sơ chứ không
   theo vai trò, vì cùng một người vừa gửi yêu cầu vừa điều phối. Bộ lọc chỉ có một nơi —
   `messages.py` (`thay_noi_bo`, `ma_loai_noi_bo`) — và mọi chỗ trả lời nhắn hay suy điều gì
   từ lời nhắn đều đi qua đó: chi tiết hồ sơ của cả ba cửa, hộp thư, cờ
   `last_message_from_requester`, luật hỏi lại. Tin nội bộ không phải câu trả lời cho người
   gửi, nên không tính vào hai cờ sau. Bài kiểm thử quét mọi điểm cuối GET trong lược đồ
   OpenAPI với tư cách người gửi, nên điểm cuối thêm sau này cũng bị canh

Ghi lời nhắn **không chạm dòng `requests`** — không trạng thái, không trường, không
`updated_at`, không đồng hồ. Bài kiểm thử so cả `ctid` của dòng: mọi lệnh UPDATE, kể cả
ghi lại đúng giá trị cũ, đều đổi `ctid`, còn so giá trị thì bỏ lọt, vì trong cùng một giao
dịch `now()` không đổi. Hàng đợi biết hồ sơ nào đang chờ trả lời nhờ cờ
`last_message_from_requester`, suy từ tác giả của lời nhắn sau cùng — không theo dõi đã đọc
hay chưa. Dòng thời gian trộn lời nhắn với mốc theo thời gian, hai loại trông khác nhau, và
số lần đổi trạng thái chỉ đếm mốc.

**Tệp đính kèm** (#80) đi cùng đường với lời nhắn: đính kèm không đổi hồ sơ nên không phải cạnh,
không vào nhật ký, và chỉ ghi thêm — bảng `case_attachments` chặn UPDATE và DELETE bằng trigger,
nên hồ sơ hủy vẫn giữ tệp (navigator chốt 26/10). Bảng chỉ giữ siêu dữ liệu; nội dung nhị phân
nằm trong SeaweedFS qua S3 API bằng `boto3` (ADR-0002), dưới khóa ngẫu nhiên không mang tên tệp.
Mọi cuộc gọi sang kho đi qua `app/storage/objects.py`; kho tắt chỉ làm phần đính kèm báo lỗi
(502), hồ sơ vẫn mở được.

Bốn quyết định đáng nhớ:

- **Tệp đi qua dịch vụ ứng dụng, không presigned URL.** Trình duyệt không bao giờ nói chuyện với
  kho: quyền kiểm ở MỖI lần tải, và người không có quyền nhận 404 — không 403, cùng lý do với
  hồ sơ ở #44. Đổi lại tệp đi qua backend nên có trần dung lượng. Phía Next.js dùng Route Handler
  (`/api/tep/...`) thay vì Server Action, vì Server Action giới hạn thân yêu cầu 1 MB mặc định
- **Ai xem được tệp thì dùng lại luật xem hồ sơ**: người gửi, điều phối viên, nhân viên của
  phòng đang giữ hồ sơ (`mo_duoc_ho_so`). Không có luật quyền thứ hai để lệch với luật thứ nhất
- **Ai đính kèm được và lúc nào nằm trong dữ liệu**: cờ `transitions.accepts_attachments` bật cho
  cạnh Sửa nội dung và Bổ sung thông tin. Người gửi đính kèm được khi họ đang có một cạnh mang
  cờ — dịch vụ trả `can_attach` suy từ `allowed_transitions`, không so tên trạng thái nào. Tới
  phòng ban thì không còn cạnh nào mang cờ và việc đính kèm khóa lại, như Sửa nội dung
- **Giới hạn là cấu hình triển khai**: đuôi cho phép, MB mỗi tệp, số tệp mỗi lần và mỗi hồ sơ nằm
  trong `.env`. Giao diện hỏi `GET /attachments/policy` thay vì giữ bản sao, nên hai lớp chặn không
  lệch nhau. Dịch vụ kiểm ba thứ: đuôi trong danh sách, dung lượng, và nội dung khớp đuôi theo chữ
  ký đầu tệp — đổi đuôi một tệp chạy được thành `.png` không qua được. Loại nội dung lấy từ dữ
  liệu theo đuôi, không tin tiêu đề trình duyệt; tải về luôn là `attachment` kèm `nosniff`

Một lần tải lên hoặc nhận cả lô hoặc từ chối cả lô: kiểm hết trước khi ghi gì xuống kho. Hồ sơ
chưa tồn tại lúc người gửi chọn tệp ở bước 2 của biểu mẫu, nên biểu mẫu tạo hồ sơ trước rồi tải
tệp lên chính hồ sơ đó; tải hỏng thì hồ sơ vẫn đã gửi và trang hồ sơ nhắc thêm tệp lại, để người
gửi không bấm gửi lần nữa.

**Chữ ký, macro, quét mã độc** (#248) xếp thành bốn lớp, lớp rẻ trước, cả lô qua hết mới ghi kho:

1. **Đuôi** trong `ATTACHMENT_ALLOWED_EXTENSIONS` — cấu hình triển khai quyết đuôi nào được NHẬN
2. **Chữ ký** theo bảng `attachment_file_types` (dữ liệu `infra/seed/04-loai-tep-dinh-kem.sql`, cụm
   cũ nhận qua migration 0023 chạy chính tệp đó): mỗi đuôi một dòng — mẫu hex (`??` là byte bất kỳ),
   vùng tìm (PDF cho phép rác trước `%PDF-`), cờ văn bản thuần, loại nội dung. Mã chỉ biết ba cách đọc
   dữ liệu đó, không có `if` theo đuôi. Tệp `.pdf` mà nội dung khác bị từ chối với thông báo "không
   phải tệp .pdf thật … có thể đã bị đổi đuôi". Đuôi được phép mà bảng chưa có dòng thì chỉ kiểm đuôi
   và ghi cảnh báo — thà kiểm ít còn hơn chặn nhầm kiểu tệp doanh nghiệp chủ động mở
3. **Macro**: cột `macro_check` (`ooxml` — gói ZIP có `vbaProject.bin`; `ole` — tệp Office đời cũ có
   kho `_VBA_PROJECT`) và `always_macro` (.docm/.xlsm/.pptm). Tệp có macro được **nhận** nhưng ghi cờ
   `case_attachments.has_macro`, giao diện hiện nhãn "có macro — cẩn thận khi mở" ở khối tệp (mọi trang
   hồ sơ dùng chung một khối). Lý do nhận thay vì chặn: bảng tính có macro là việc thường ngày của bộ
   phận tài chính, chặn thì họ đổi đuôi hoặc gửi qua kênh khác không kiểm gì. Đổi đuôi `.docm` thành
   `.docx` không giấu được — dò theo nội dung gói, không theo đuôi. Đuôi có macro chỉ nhận khi nằm
   trong danh sách cho phép (mặc định không có)
4. **Quét mã độc** — ClamAV, hồ sơ Compose `quet-tep`, **tắt** mặc định (`CLAMAV_HOST` rỗng: không
   gọi gì, cột `scan_status = 'disabled'`). Bật thì `app/storage/quet_ma_doc.py` gửi tệp sang clamd
   qua lệnh `INSTREAM` bằng `socket` của thư viện chuẩn, có hạn chót. Bị báo nhiễm → từ chối cả lô
   (422 `attachment-infected`). clamd không phản hồi → theo `CLAMAV_ON_UNAVAILABLE`: mặc định
   `accept` — nhận, gắn `scan_status = 'unscanned'` (nhãn "chưa quét mã độc"), ghi nhật ký cảnh báo;
   `reject` — 503, người gửi thử lại. Mặc định là nhận vì một dịch vụ **tùy chọn** hỏng không được
   chặn người gửi bổ sung hồ sơ đang chờ (luật chung của cụm: thành phần tùy chọn hỏng chỉ làm mất
   phần của nó), và ba lớp trên vẫn chạy; nơi coi quét là bắt buộc thì đặt `reject`. Màn Hệ thống
   báo dịch vụ quét ở ba mức tắt / sẵn sàng / không phản hồi (lệnh `PING`, hạn chót 3 giây) kèm
   chính sách đang áp. Ranh giới giấy phép GPL-2.0 là ranh giới mạng — `LICENSES.md`

### 6.3. Lớp báo cáo và dữ liệu mở (không gian `D`)

**Đã cài đặt** — #304, #306, nhúng vào cổng #305.

Nhật ký sự kiện nuôi ba thứ đọc cùng một nguồn: bảng điều khiển phân tích, dữ liệu xuất, và về
sau khai phá quy trình ở tầng `I`. Chỉ số không tính ở ba nơi — chúng nằm trong các **view
`bao_cao_*`** của migration `0014`, tự chạy khi nâng cấp, không phải `down -v`:

| View | Một dòng là | Dùng cho |
|---|---|---|
| `bao_cao_ho_so` | một hồ sơ: loại, phòng, trạng thái, đã kết thúc, đã qua phòng ban, giờ xử lý, ngưỡng hạn, giờ đồng hồ, vi phạm | nền của mọi view dưới, biểu đồ trung vị |
| `bao_cao_ton_dong` | phòng × trạng thái của hồ sơ chưa kết thúc | Tồn đọng theo phòng ban |
| `bao_cao_vi_pham` | phòng × loại: số hồ sơ đã xong, số vi phạm | Tỷ lệ vi phạm hạn |
| `bao_cao_phan_bo_loai` | tuần gửi × phòng × loại | Phân bố loại yêu cầu |
| `bao_cao_thoi_gian_xu_ly` | loại: trung vị giờ xử lý, tỷ lệ vi phạm toàn công ty | tóm tắt |
| `bao_cao_nhat_ky` | một sự kiện, kèm sự kiện mở đầu `create-case` dựng từ lúc tạo | dữ liệu xuất, tầng `I` |
| `bao_cao_goi_y` | một gợi ý đã được giữ hay ghi đè: trường, nguồn, giá trị gợi ý và giá trị chọn (migration `0016`, #239) | Tỷ lệ ghi đè gợi ý |

Ba quy tắc giữ view đúng khi doanh nghiệp đổi quy trình:

- **Không tra mã trạng thái.** Kết thúc hay chưa tra `states.is_terminal`; hồ sơ đã tới phòng ban
  hay chưa tra `states.sla_running` — hồ sơ hủy trước khi tới phòng, hay *Không tiếp nhận*, không
  bao giờ vào trạng thái chạy đồng hồ, nên tự rơi khỏi thời gian xử lý và tỷ lệ vi phạm. Mỗi hồ
  sơ xét theo bộ quy tắc của chính nó (mục 6.1)
- **Cùng phép đo với hệ thống.** Giờ xử lý đo bằng `so_giay_lam_viec` theo lịch mặc định; ngưỡng
  hạn là hạn chuẩn của loại nhân hệ số ưu tiên cộng giờ gia hạn, như `gioi_han_giay`; vi phạm là
  đồng hồ hạn của hồ sơ đã kết thúc vượt ngưỡng đó
- **Mọi view bảng điều khiển đọc đều có `ma_phong`**, để bản nhúng lọc theo phòng của người xem
  bằng một điều kiện trên cột đó. Trung vị không cộng gộp được giữa các phòng, nên biểu đồ trung
  vị tính `PERCENTILE_CONT` trên `bao_cao_ho_so`, không trên bản tóm tắt

View đặt ở schema `public` và chạy bằng quyền của chủ sở hữu: tài khoản chỉ đọc của Superset nhận
quyền đọc mặc định cấp lúc dựng cụm, không đọc thẳng được gì nó không cần. Đổi một view thì tạo
migration mới bằng `CREATE OR REPLACE VIEW`.

**Bảng điều khiển là tệp cấu hình.** Kết nối dữ liệu, dataset, năm biểu đồ (thứ năm là tỷ lệ ghi đè gợi ý, #239) và dashboard *Vận hành
yêu cầu* nằm ở `infra/superset/bang-dieu-khien/` dạng YAML. Lúc khởi động, điểm vào của ảnh
Superset thay chuỗi kết nối chỉ đọc vào chỗ giữ chỗ rồi chạy `superset import-directory
--overwrite` — nạp đè theo uuid, khởi động lại không sinh bản trùng, cụm dựng mới có sẵn bảng
điều khiển. Superset chờ dịch vụ ứng dụng báo khỏe, tức là đã chạy xong migration tạo view. Sửa
bảng điều khiển: đăng nhập giao diện Superset bằng tài khoản quản trị, sửa, rồi `superset
export-dashboards` và chép các tệp đã đổi về thư mục đó — không xuất lại thì lần khởi động sau
nạp đè mất.

**Nhúng trong cổng, lọc theo phòng (#305).** Mục *Báo cáo* trên thanh bên mở bảng điều khiển trong
khung nhúng, không đăng nhập lần hai. Luồng:

1. Thư viện nhúng chính thức của Superset (`@superset-ui/embedded-sdk`) gọi `/api/bao-cao/token` của
   cổng; Route Handler chuyển sang `POST /analytics/dashboard/guest-token` kèm token Keycloak
2. Dịch vụ tra **phạm vi** của người gọi trong cột `roles.report_scope` (migration `0015`, giá trị ở
   dữ liệu khởi tạo): `all` — toàn công ty, `department` — phòng của chính người xem theo claim
   `groups`, trống — không xem. Nhiều vai trò thì lấy phạm vi rộng nhất. Không có phạm vi, hay
   trưởng phòng chưa thuộc phòng nào: 403. Cùng một hàm `pham_vi_cua` quyết cả mục `reports` trong
   `workspaces` của `/me`, nên thanh bên và quyền mở không lệch nhau
3. Dịch vụ đăng nhập API Superset bằng tài khoản quản trị, bật cấu hình nhúng cho dashboard (lần đầu,
   chỉ cho gốc của cổng nhúng) rồi xin **token khách** sống 5 phút cho đúng dashboard đó, kèm điều
   kiện lọc theo dòng `ma_phong IN (...)`. Mã phòng đối chiếu bảng `departments` trước — không chuỗi
   nào từ token đi thẳng vào điều kiện. Superset gắn điều kiện vào mọi câu truy vấn của dashboard
   và ký token, nên trình duyệt không nới được phạm vi
4. Thư viện dựng khung từ địa chỉ công khai của Superset mà dịch vụ trả kèm, tự xin lại token trước
   khi hết hạn; khung theo chế độ sáng/tối của cổng, ẩn tiêu đề và thanh bộ lọc gốc

Hai thứ phía Superset để token khách vẽ được: vai khách (`GUEST_ROLE_NAME`) được cấp quyền đọc kết
nối *Dữ liệu nghiệp vụ* lúc khởi động (`infra/superset/cap_quyen_khach.py`), và CSP
`frame-ancestors` cho phép gốc của cổng đặt Superset trong khung (`superset_config.py`). Superset
tắt thì điểm cuối trả 503 và mục Báo cáo hiện màn "không phản hồi", phần còn lại của cổng chạy
bình thường. Lưới của Superset không xếp lại dưới 768 px, nên màn hẹp giữ khung rộng 760 px và cuộn
ngang trong khung.

**Dữ liệu mở.** `GET /analytics/event-log?format=csv|json&from=&to=`, chỉ quản trị viên, trên màn
Hệ thống của cổng. Cột cố định (`app/analytics/xuat_du_lieu.py` `COT`), mốc UTC, khoảng ngày theo
UTC; người thao tác bằng mã định danh, không có tên và ghi chú; CSV có BOM để bảng tính trên Windows
hiện đúng chữ có dấu.

**Dữ liệu trình diễn.** `scripts/nap_du_lieu_trinh_dien.py --xac-nhan` nạp vài trăm hồ sơ giả theo
kịch bản của bộ sinh nhật ký ảo (#124), đi đúng bộ quy tắc đang bật và qua bước tự kiểm của bộ
sinh. Đây là **lối ghi duy nhất ngoài `perform_transition`**: engine chỉ ghi được mốc hiện tại, còn
lịch sử trình diễn phải lùi về quá khứ. Lệnh chỉ chạy INSERT — hồ sơ mang sẵn trạng thái cuối,
nhật ký mang sẵn mốc cũ — nên nguyên tắc nhật ký chỉ ghi thêm vẫn giữ. Đồng hồ của bộ sinh được
coi là giây làm việc và đổi sang giờ thật bằng `moc_sau_giay_lam_viec`: sự kiện rơi vào giờ hành
chính, đồng hồ hạn đúng bằng cách hệ thống tự đo, không sự kiện nào ở tương lai. Lệnh từ chối
chạy khi thiếu `--xac-nhan`, và khi cụm đã có hồ sơ không mang tiền tố `[Mẫu]` (trừ khi thêm
`--cho-tron`). Hồ sơ mẫu không gỡ ra được — trigger chặn xóa nhật ký — nên muốn sạch thì `down -v`.

### 6.3a. Lưu trữ lạnh và phả hệ dữ liệu (không gian `D`)

**Đã cài đặt** — #378 (lưu trữ lạnh, nguyên lý (i) của đề) và #379 (phả hệ, nguyên lý (iii)).

**Hai tầng theo vòng đời.** Tầng nóng là PostgreSQL: bảng tác nghiệp, nhật ký chỉ ghi thêm, view báo cáo.
Tầng lạnh là kho đối tượng SeaweedFS: mỗi **tháng UTC đã khép** một bản lưu niêm phong. Tầng lạnh là **bản
sao** để phân tích dài hạn, không phải nơi dời dữ liệu đi: đợt này **không dọn gì khỏi tầng nóng** — nhật
ký chỉ ghi thêm là nền của khai phá quy trình và kiểm toán. Xóa khỏi tầng nóng là việc tương lai, theo
chính sách lưu giữ của ADR-0009, và khi làm thì bản lưu lạnh là thứ cho phép làm.

**Bộ quét `cold-archive`** (`app/analytics/luu_tru_lanh.py`) theo khuôn `nhip_quet.py` (mục 7.1): khóa tư
vấn, dòng nhịp, hiện trên màn Hệ thống; vòng nền riêng để lần đầu bật trên cụm nhiều năm dữ liệu không làm
trễ bộ quét hạn. Mỗi lượt lấy các tháng từ mốc sớm nhất có dữ liệu tới tháng đã khép cuối cùng còn thiếu
bản lưu, cũ trước, tối đa `ARCHIVE_MAX_MONTHS_PER_RUN`. Tháng trống cũng có bản lưu, nên sổ không lỗ hổng.
Cấu hình (`app/config.py`, `infra/.env.example`): `ARCHIVE_ENABLED`, `ARCHIVE_INTERVAL_SECONDS`,
`ARCHIVE_MIN_AGE_MONTHS` (tối thiểu 1 — tháng đang chạy còn nhận sự kiện), `ARCHIVE_BUCKET` (rỗng là chung
thùng tệp đính kèm — khóa S3 mẫu chỉ được tạo đúng thùng đó), `ARCHIVE_PREFIX`. Chạy ngay một lượt:
`POST /archive/scan` (quản trị viên) — tắt bộ quét là tắt lịch, không tắt khả năng xuất.

Một bản lưu, dưới `<tiền tố><YYYY-MM>/`:

| Tệp | Nội dung |
|---|---|
| `nhat-ky-su-kien.csv.gz` | sự kiện của tháng từ view `bao_cao_nhat_ky`, **đúng cột của `GET /core/v1/events`** |
| `ho-so-ket-thuc.csv.gz` | hồ sơ kết thúc trong tháng (cùng nghĩa "kết thúc" với `bao_cao_ho_so`: trạng thái `is_terminal`, mốc là sự kiện cuối) — trường quyết định, người bằng mã, đồng hồ hạn |
| `manifest.json` | định dạng, phiên bản lược đồ, kỳ, khoảng UTC, lúc xuất, số sự kiện và hồ sơ theo quy trình, mỗi tệp: cột, số dòng, số byte, SHA-256 |

- **Định dạng mở, không thư viện mới.** CSV RFC 4180, UTF-8 có dòng tiêu đề, nén gzip với `mtime=0` — cùng
  nội dung ra cùng byte. Đọc được bằng mọi bảng tính hay pandas, không cần hệ thống
- **Bất biến, chạy lại an toàn.** `manifest.json` ghi **sau cùng**: có nó là bản đã niêm phong, không bao
  giờ ghi đè. Bảng `cold_archives` (migration `0029`) là sổ, chỉ ghi thêm bằng trigger như `event_log`.
  Lượt hỏng giữa lúc ghi kho và ghi sổ: lượt sau thấy manifest trong kho, ghi sổ theo nó, không xuất lại.
  Tệp dữ liệu không có manifest là dở dang, ghi lại được
- **Dữ liệu cá nhân (ADR-0009).** Không nhãn tên, không nội dung tự do (tiêu đề, mô tả, trường riêng, lời
  nhắn), không nội dung tệp đính kèm; người chỉ có mã định danh. Lý do: bản lưu bất biến, nên tên lọt vào
  thì không bao giờ ẩn danh hóa được nữa — giữ tên ngoài bản lưu thì thao tác ẩn danh hóa ở tầng nóng
  vẫn đủ
- **Đọc lại.** `GET /core/v1/archive` (mục 2.3) liệt kê, đọc bản kê, tải từng tệp; dịch vụ kiểm mã băm
  trước khi trả, tệp bị sửa trong kho thì `502 archive-corrupted`. `scripts/doc_luu_tru.py <YYYY-MM>`
  tải qua container dịch vụ hoặc qua API, kiểm SHA-256, giải nén, đếm dòng so với bản kê; `--doi-chieu`
  so thêm số dòng nhật ký với tầng nóng — chứng minh báo cáo dựng từ tầng lạnh khớp nguồn

Cụm mới chỉ có bản lưu khi có dữ liệu của tháng trước: dữ liệu trình diễn (`nap_du_lieu_trinh_dien.py`,
mặc định rải 90 ngày) có sẵn hai, ba tháng đã khép.

**Phả hệ dữ liệu** (`scripts/pha_he.py`, chỉ thư viện chuẩn) đọc **tĩnh** từ kho, không cần cụm: định nghĩa
view từ các bản sửa Alembic (chạy `upgrade()` với mô-đun giả, ghi lại mọi `CREATE`/`DROP VIEW` theo chuỗi
`down_revision`), biểu đồ và bộ dữ liệu từ YAML ở `infra/superset/bang-dieu-khien/`, và câu SQL của những
nơi khác đọc nhật ký (xuất dữ liệu, khai phá, lưu trữ lạnh). Kết quả là [`pha-he-du-lieu.md`](pha-he-du-lieu.md)
cùng trang tương ứng của trang tài liệu: biểu đồ → bộ dữ liệu → view → bảng nguồn và cột, sơ đồ mermaid,
và nguồn gốc nhật ký từ cửa chuyển trạng thái tới mọi nơi đọc. Không sửa tay hai tệp đó: đổi view hay
bảng điều khiển thì chạy lại `python scripts/pha_he.py`. Tích hợp liên tục chạy `--kiem` trong việc
kiểm header — trang lệch định nghĩa là đỏ.

### 6.4. Khai phá quy trình (không gian `I`)

**Đã cài đặt** — #314, theo [ADR-0007](adr/0007-chon-thu-vien-khai-pha-quy-trinh.md). Màn trình bày ở
cổng (#315): xem đoạn **Màn ở cổng** cuối mục này.

Đây là vòng phản hồi tự soi quy trình của `CLAUDE.md` mục 4.1: từ nhật ký sự kiện, vẽ lại quy trình
đang thật sự chạy và chỉ ra chỗ cần cải tiến. Engine chỉ cho đi cạnh có trong bộ quy tắc, nên đối chiếu
"cạnh có hay không" với thiết kế luôn ra không lệch. Thứ đáng khai phá là hồ sơ đi **ra khỏi luồng
chính** bao nhiêu, ở đâu, tốn bao lâu.

**Ba lớp, ranh giới giấy phép ở lớp giữa:**

```
Cổng ──► dịch vụ ứng dụng (MIT)  ──HTTP──►  dịch vụ khai phá (AGPL, cả mã nhóm lẫn thư viện)  ──SQL chỉ đọc──► PostgreSQL
         GET /analytics/process-mining       POST /khai-pha
         kiểm vai, gắn phạm vi phòng          không mở cổng ra máy, không tự kiểm danh tính
```

- **Dịch vụ ứng dụng** (`app/analytics/khai_pha.py`) dùng đúng `pham_vi_cua` của bảng điều khiển (#305):
  `roles.report_scope` quyết ai xem và tới đâu. Danh sách phòng gửi đi đã đối chiếu với bảng. 403 khi vai
  không được xem, 422 khi khoảng ngày sai (tối đa 366 ngày), 503 khi dịch vụ khai phá không phản hồi
- **Dịch vụ khai phá** (`services/khai-pha/`) chỉ nghe trong mạng của Compose; người gọi duy nhất là dịch
  vụ ứng dụng. Tắt nó thì cổng, bảng điều khiển và mọi luồng nghiệp vụ vẫn chạy (không dịch vụ nào
  `depends_on` nó)
- **Tài khoản cơ sở dữ liệu chỉ đọc riêng** (migration `0019`, nhờ #254 không cần `down -v`): SELECT đúng
  bảy bảng/view phép khai phá đọc, phiên mặc định chỉ đọc, không quyền đọc mặc định trên bảng mới. Không
  dùng chung tài khoản của Superset

**Phân tích — mọi tiêu chí là cờ trong dữ liệu, không mã trạng thái nào trong mã:**

| Kết quả | Cách tính |
|---|---|
| Hồ sơ xét | Hồ sơ **gửi** trong khoảng ngày (ngày theo múi giờ của lịch làm việc mặc định), trong phạm vi phòng; mỗi hồ sơ theo bộ quy tắc của chính nó |
| Lượt | Mỗi lần hồ sơ vào một trạng thái — sự kiện mở đầu (view `bao_cao_nhat_ky`) hay cạnh đổi trạng thái; cạnh tự trỏ (ADR-0005) không tính. Hoạt động = trạng thái vào, theo ghi chú của ADR-0007 |
| Đồ thị | Đồ thị trực tiếp trên chuỗi lượt (bộ máy); mỗi cạnh kèm số hồ sơ và loại theo cờ của cạnh đã đi |
| Luồng chính thiết kế | Cạnh người, không `is_rework`, không `reopen_window_hours`, có đổi trạng thái |
| Nhánh lệch | `rework` — đi cạnh `is_rework` · `escalation` — cạnh hệ thống **không** `auto_after_hours` (cùng tiêu chí với bộ quét SLA) · `wait_expiry` — cạnh hệ thống **có** `auto_after_hours` · `reopen` — cạnh `reopen_window_hours` · `multiple_routing` — `event_log.changes` đặt `department_code` từ hai lần |
| Thời gian chờ | `so_giay_lam_viec(vào, ra)` mỗi lượt — cùng phép đo với đồng hồ hạn và bảng điều khiển; lượt còn dở tính tới bây giờ; trạng thái kết thúc không có |
| Điểm nghẽn | Trạng thái xếp theo thời gian chờ trung vị; nghẽn khi trung vị gấp từ `KHAI_PHA_BOI_SO_NGHEN` (mặc định 2) lần trung vị chung của mọi lượt ở trạng thái chưa kết thúc |
| Biến thể | Chuỗi trạng thái của từng hồ sơ (bộ máy), `KHAI_PHA_SO_BIEN_THE` biến thể nhiều nhất |
| Tách nhóm (#315) | Nhánh lệch đếm theo loại yêu cầu và phòng **hiện tại** của hồ sơ, kèm tỷ lệ trên tổng hồ sơ của nhóm; thời gian chờ mỗi trạng thái lấy trung vị theo từng nhóm. Nhóm rỗng (hồ sơ chưa chuyển phòng) xếp cuối |
| Hồ sơ chờ lâu nhất (#315) | Mỗi trạng thái chưa kết thúc: hồ sơ xếp theo tổng giây làm việc mọi lượt ở đó, kèm số lượt và cờ hồ sơ còn nằm ở đó; tối đa `KHAI_PHA_SO_HO_SO_MOI_NHOM` hồ sơ |

**Hai bộ máy, một hợp đồng.** Phần thuật toán — đồ thị trực tiếp và biến thể — đứng sau giao diện
`BoMay`: `pm4py` (mặc định) và `noi_bo` (dự phòng, Python thuần). Phần còn lại ở `app/phan_tich.py`, chung
cho cả hai. Bài kiểm thử có đáp án biết trước chạy trên cả hai và đòi kết quả giống hệt. Không dùng được
AGPL thì `MINING_ENGINE=noi_bo` và xóa dòng `pm4py` khỏi `requirements.txt` — dịch vụ ứng dụng và cổng
không đổi gì.

**Hợp đồng trả về** (khóa tiếng Anh như mọi API của dự án): `range`, `departments`, `engine`,
`cases_count`, `events_count`, `groups` (`request_types[]`, `departments[]`: `code`, `cases_count`),
`states[]` (`code`, `label`, `is_initial`, `is_terminal`, `visits`, `cases`, `median_wait_seconds`,
`is_bottleneck`, `longest_waits[]` — `case`, `seconds`, `visits`, `current` —, `by_request_type[]` và
`by_department[]` — `code`, `visits`, `median_wait_seconds`), `edges[]` (`from`, `to`, `count`, `cases`,
`is_main`, `kinds`), `designed_main_flow[]` (`from`, `to`, `from_label`, `to_label` — bước chưa ai đi vẫn có
nhãn), `deviations[]` (`kind`, `cases_count`, `ratio`, `cases`,
`by_request_type[]` và `by_department[]` — `code`, `cases_count`, `ratio`), `bottlenecks`
(`overall_median_wait_seconds`, `factor`, `threshold_seconds`, `ranking[]`), `variants[]` (`sequence`,
`cases_count`, `ratio`, `cases`), `other_variants_cases`. Dịch vụ khai phá chỉ trả **mã** nhóm; dịch vụ
ứng dụng thêm `scope`, `labels` (`request_types`, `departments`: mã → nhãn, đọc từ bảng danh mục) và
`case_codes` (mã hồ sơ → mã hiển thị `YC-2026-0184` của mọi hồ sơ kết quả nêu tên, cùng hàm với trang hồ sơ) —
tài khoản chỉ đọc của dịch vụ khai phá không cần thêm quyền.

**Màn ở cổng (#315).** Trang con `/bao-cao/quy-trinh` của mục Báo cáo; hai màn của mục (bảng điều khiển
và quy trình thực tế) là hai trang riêng, nối bằng thanh `ThanhBaoCao`, nên mở màn này không tải khung
Superset. Cùng cửa `reports` với bảng điều khiển. Trình duyệt gọi Route Handler
`frontend/app/api/bao-cao/quy-trinh/route.ts` (`GET ?tu&den`), nó chuyển sang
`GET /analytics/process-mining` qua `lib/api.ts` — token Keycloak không tới trình duyệt — và đổi mã lỗi
về 401, 403, 422 (kèm thông điệp) hay 503. Khoảng ngày nằm trên địa chỉ trang, mặc định 90 ngày. Sơ đồ
vẽ bằng `@xyflow/react` với bố cục `@dagrejs/dagre` (`lib/bo-cuc-quy-trinh.ts`, hàm thuần); màu lấy từ
biến CSS của cổng nên theo sáng/tối. **Câu kết luận dựng tất định**: `lib/ket-luan-quy-trinh.ts` là hàm
thuần từ JSON ra câu tiếng Việt bằng mẫu cố định, cùng JSON luôn cùng câu, không mô hình ngôn ngữ. Tên
trạng thái, loại yêu cầu, phòng đều đọc từ JSON (`states[].label`, `labels`); chỉ năm mã nhánh lệch của
hợp đồng có bảng nhãn trong mã vì đó là loại phân tích do dịch vụ khai phá định nghĩa. Bấm một trạng
thái, nhánh lệch hay đường đi mở ngăn danh sách hồ sơ (`longest_waits`, `deviations[].cases`,
`variants[].cases`); mã hồ sơ dẫn tới buồng lái điều phối hoặc phòng ban tùy `workspaces` của `/me`
(`duongDanHoSo` ở `lib/khong-gian.ts`). Chân màn luôn có dòng *"Phân tích bởi dịch vụ khai phá quy
trình, giấy phép AGPL-3.0 — mã nguồn"* (#340, điều 13 — mục 3.3): trang máy chủ đọc `MINING_SOURCE_URL`,
chỉ nhận `http(s)`, truyền xuống thành phần; màn không nêu tên bộ máy. Hướng dẫn người dùng: `docs-site`
— *Quy trình thực tế*.

**Tầng `I` chỉ gợi ý** (`CLAUDE.md` mục 4.3): khai phá chỉ đọc và phân tích, không ghi trường nào của hồ sơ.

### 6.5. Gợi ý phân loại bằng mô hình ngôn ngữ (không gian `I`)

Đã cài ở #316 (dịch vụ mô hình) và #317 (gợi ý loại, mức ưu tiên, phòng ban), theo
[ADR-0008](adr/0008-chon-co-so-du-lieu-vec-to-va-mo-hinh-cuc-bo.md).

**Dịch vụ tùy chọn.** `mo-hinh` (llama.cpp server) nằm dưới hồ sơ Compose `tri-tue`: cụm mặc định
không có nó, không tải gì thêm, chạy đủ ở chế độ thủ công. Không dịch vụ nào `depends_on` nó, không
mở cổng ra máy. Tệp GGUF ở volume `mo-hinh` (`scripts/tai_mo_hinh.py`). Dịch vụ ứng dụng bật gợi ý
khi `DXLAB_LLM_URL` khác rỗng.

**Khuôn mẫu: một lớp duy nhất gọi mô hình** — `backend/app/intelligence/mo_hinh.py`.

- Điểm cuối kiểu OpenAI (`/v1/chat/completions`), gọi bằng `urllib` của thư viện chuẩn, không khung
  LLM nào. Đổi máy chủ mô hình (Ollama, dịch vụ khác cùng chuẩn) là đổi địa chỉ, không đổi mã
- **Danh mục đọc từ bảng lúc gọi**: loại và phòng đang bật, mọi mức ưu tiên, kèm nhãn và mô tả. Lời
  dặn không nêu mã hay nhãn nghiệp vụ nào; doanh nghiệp đổi danh mục thì lời dặn đổi theo
- **Ràng buộc đầu ra bằng JSON schema**: `enum` của từng trường là mã danh mục đó; llama.cpp ràng
  buộc ngữ pháp nên không sinh được mã lạ. Phía gọi vẫn kiểm lại — máy chủ bỏ qua lược đồ cũng không
  làm lọt mã ngoài danh mục
- **Hạn chót cứng** (`DXLAB_LLM_TIMEOUT_SECONDS`): lời gọi chạy ở luồng riêng và chờ bằng
  `result(timeout=...)`, cùng lý do với danh bạ (mục 3.1) — `timeout` của urllib không phủ bước tra DNS
- **Mọi lỗi thành một loại** `LoiMoHinh(ma)`: tắt, không tới được, quá hạn, lỗi máy chủ, sai định
  dạng, ngoài danh mục. Không lỗi nào nổi lên người dùng; hàm tiện dụng trả `None` = "không có gợi ý"
- Lớp này **không ghi gì** vào cơ sở dữ liệu. `tinh_trang()` cho `/system/health` (`language_model`:
  `disabled` / `ready` / `unreachable`) — mô hình là tùy chọn nên không bao giờ làm `status` xấu đi

**Đường ghi gợi ý — `backend/app/intelligence/phan_loai.py`, không qua cửa chuyển trạng thái.**

- Hai đường vào: tác vụ nền (`BackgroundTasks`) ngay sau khi `POST /requests` trả về — người gửi
  không chờ mô hình; và **bộ quét bù** `suggestion-backfill` theo khuôn `nhip_quet.py` (khóa tư vấn,
  dòng nhịp, có trong `scanners`), vòng nền riêng để một lượt chờ mô hình không làm leo thang hạn
  muộn. Bộ quét nhặt hồ sơ ở các trạng thái của hàng đợi điều phối (suy từ `transitions`) mà chưa có
  gợi ý, xử lý lần lượt từng cái
- Mỗi lần thử ba giao dịch ngắn: **giành** hồ sơ bằng một `UPDATE` có điều kiện (đặt
  `suggestion_attempted_at`, cộng `suggestion_attempts` — hai đường không hỏi cùng hồ sơ hai lần);
  **hỏi mô hình** không giữ giao dịch hay khóa dòng nào; **ghi** trường `suggested_*` và
  `suggestion_note` (JSONB: lý do từng trường, mô hình, thời gian, phòng mô hình đoán) — kiểm lại mã
  với danh mục đang bật, chỉ ghi khi hồ sơ còn ở trạng thái lúc giành, giữ nguyên `updated_at`
- Không bao giờ chạm trường quyết định, không ghi nhật ký sự kiện: gợi ý không phải một lần chuyển
  trạng thái (ADR-0005). Giữ hay ghi đè được ghi khi người xác nhận, ở cửa chuyển trạng thái (mục 2.2)
- Thử lại có giới hạn: mô hình trả lời mà hỏng thì tính một lượt, tối đa `DXLAB_SUGGEST_MAX_ATTEMPTS`,
  cách nhau ít nhất `DXLAB_SUGGEST_RETRY_AFTER_SECONDS`; không tới được mô hình thì trả lại lượt và lượt
  quét dừng sớm
- **Ngưỡng 80 % cho phòng ban**: phòng của mô hình chỉ thay bảng ánh xạ khi bật
  `DXLAB_SUGGEST_DEPARTMENT_FROM_MODEL`; chỉ khuyên bật khi `scripts/do_chinh_xac_goi_y.py` đo trên bộ
  mẫu có nhãn (`backend/tests/du_lieu/bo_mau_phan_loai.json`) đạt từ 80 % và hơn bảng ánh xạ. Cờ tắt
  thì phòng mô hình đoán vẫn nằm trong ghi chú để đo

**Màn điều phối**: `GET /coordination/requests/{id}` mang `suggested_request_type`,
`suggested_priority`, `suggested_department` cùng khuôn `GoiY`; thẻ gợi ý (#239) hiện trên từng ô. Ô
loại giữ lựa chọn của người gửi, thẻ báo khi khác gợi ý; ô mức ưu tiên điền sẵn gợi ý (trước mức mặc
định). Không có gợi ý thì màn như trước.

### 6.6. Hồ sơ đã giải quyết tương tự (không gian `I`)

Đã cài ở #319, theo ADR-0008 đợt 2 — `backend/app/intelligence/tuong_tu.py`. Người gửi đang gõ tiêu
đề và mô tả thì thấy tối đa ba hồ sơ **đã giải quyết** giống vấn đề của mình, kèm cách đã giải quyết.
Đủ dùng thì họ bấm *"Đã giải quyết được, không gửi nữa"* — một yêu cầu được ngăn chặn.

**Không gói mới.** Véc-tơ nằm ngay trong PostgreSQL (ảnh `pgvector/pgvector:0.8.6-pg16`, migration `0022`
bật `vector`); mô hình nhúng chạy ở `mo-hinh-nhung` (llama.cpp, `--embeddings`, hồ sơ `tri-tue`), gọi qua
`mo_hinh.hoi_nhung` — cùng lớp, cùng hạn chót cứng, cùng `LoiMoHinh` với mục 6.5. `DXLAB_EMBEDDING_URL`
rỗng là tắt: không lập chỉ mục, biểu mẫu không hiện gì. Đổi ảnh PostgreSQL từ Alpine (musl) sang Debian
(glibc) đổi thứ tự sắp chữ của `en_US.utf8`: migration `0022` nhận ra cơ sở dữ liệu dựng dưới musl
(`datcollversion` rỗng mà thư viện đang chạy có phiên bản) và `REINDEX DATABASE` từng cơ sở dữ liệu của
cụm một lần — đã nâng thật một cụm có dữ liệu, `scripts/kiem_nang_cap.py so` đạt, mọi chỉ mục B-tree qua
`amcheck`.

**Chỉ mục — chỉ hồ sơ đóng ĐẠT, nhận ra bằng dữ liệu.** Sự kiện cuối của hồ sơ là một cạnh người vào
trạng thái kết thúc, xuất phát từ trạng thái mà bước chính của người được giao (`primary_scope =
'assignee'`, mục 7.3) dẫn tới — tức người gửi xác nhận đạt. Tự đóng vì hết hạn chờ (cạnh hệ thống) và hủy
không tính; không mã trạng thái nào. Bảng `similar_case_index` (tầng `I`, tách khỏi bảng quyết định): tiêu
đề, mô tả, loại, **cách giải quyết** = ghi chú của bước hoàn thành cộng lời nhắn cuối người gửi thấy được
của phía xử lý (không bao giờ lời nhắn nội bộ), lúc đóng, tên mô hình, véc-tơ. Véc-tơ nhúng phần mô tả vấn
đề; câu tìm kèm lời dặn tác vụ của Qwen3-Embedding (`embedding_query_instruction` trong `app/config.py`).
Cột véc-tơ không khai số chiều — số chiều thuộc mô hình; câu tìm chỉ so véc-tơ cùng mô hình. Không chỉ mục
HNSW: quét chính xác đủ nhanh ở quy mô này và luôn đúng (ADR-0008, phép B).

**Ẩn danh lúc ghi.** Email, số điện thoại (mẫu Việt Nam) và tên người hệ thống biết — người gửi, người xử
lý, người thao tác, người nhắn, tên từ hai chữ — bị thay trước khi vào bảng, cả tên gọi sau từ xưng hô
("anh Cường"). Bảng chỉ mục không giữ chúng; kết quả trả về không có mã hồ sơ hay đường dẫn.

**Bộ lập chỉ mục bù `similar-index`** theo khuôn `nhip_quet.py` (khóa tư vấn, dòng nhịp, màn Hệ thống):
nhặt hồ sơ mới đóng đạt, hồ sơ đóng lại sau khi mở lại, hồ sơ nhúng bằng mô hình cũ; ba bước như
`phan_loai.py` — đọc, hỏi mô hình không giữ giao dịch, ghi. Mô hình hỏng thì lượt sau thử lại cả lô.

**Biểu mẫu không bao giờ chờ.** `components/goi-y-tuong-tu.tsx` hỏi sau 700 ms ngừng gõ, hủy lời hỏi cũ,
hạn chót trình duyệt 4 giây; Route Handler `app/api/yeu-cau/tuong-tu` chuyển sang `POST /similar-cases/search`
(hạn chót `DXLAB_SIMILAR_TIMEOUT_SECONDS`, ngưỡng `DXLAB_SIMILAR_MIN_SCORE`, tối đa
`DXLAB_SIMILAR_MAX_RESULTS`). Mô hình tắt, chậm, hỏng — danh sách rỗng, không lỗi; dịch vụ báo tắt thì biểu
mẫu thôi hỏi trong phiên. Nút Gửi không phụ thuộc khối này.

**Đo ngăn chặn.** Mỗi biểu mẫu sinh một mã phiên soạn. Có gợi ý thì `similar_case_views` ghi một dòng (hồ
sơ gợi ý, số lần xem); gửi hồ sơ kèm mã phiên thì nối `submitted_case_id`; bấm "không gửi nữa"
(`POST /similar-cases/abandon`) hay quá `DXLAB_SIMILAR_ABANDON_AFTER_MINUTES` mà không gửi (bộ quét đánh
dấu) thì là bỏ không gửi. View `bao_cao_ngan_chan` (mang `ma_phong` của hồ sơ gợi ý đầu như mọi view bảng
điều khiển, mục 6.3) cho biểu đồ *Tỷ lệ yêu cầu được ngăn chặn nhờ gợi ý hồ sơ tương tự*.

**Bộ đo.** `scripts/du_lieu/ho_so_da_giai_quyet.json` — 60 hồ sơ đã giải quyết, `nap_du_lieu_trinh_dien.py`
gắn vào hồ sơ mẫu đóng đạt; `backend/tests/du_lieu/bo_do_tuong_tu.json` — 40 câu viết khác chữ kèm đáp án;
`scripts/do_ho_so_tuong_tu.py` đo recall@3 và MRR qua đúng `tuong_tu.tim` trong container. Bộ đo do nhóm
soạn bằng công cụ. Số đo ở trang *Mô hình ngôn ngữ* của `docs-site`.

### 6.7. Khuyến nghị cải tiến bằng câu chữ (không gian `I`)

Đã cài ở #320 — `backend/app/intelligence/khuyen_nghi.py`, điểm cuối
`GET /analytics/process-mining/recommendation` (cùng cửa quyền, cùng phạm vi với `/process-mining`, mục
6.4). Gọi ở **dịch vụ ứng dụng**, không trong dịch vụ khai phá AGPL; mô hình qua `mo_hinh.hoi_json`.

- **Bảng dữ kiện tất định**: từ JSON khai phá dựng vài dòng tiếng Việt — tổng hồ sơ, trung vị chờ chung,
  năm trạng thái chờ lâu nhất (gấp bao nhiêu lần, nhóm chậm nhất), từng nhánh lệch có hồ sơ, đường đi phổ
  biến nhất — số viết sẵn kiểu Việt Nam như màn hình. Tên trạng thái, loại, phòng đọc từ JSON; chỉ năm
  nhãn nhánh lệch có bảng trong mã, cùng lý do với `ket-luan-quy-trinh.ts`. Mô hình chỉ thấy bảng này
- **Mô hình viết việc, hệ thống gắn căn cứ**: dòng *vấn đề* (trạng thái chờ, nhánh lệch) được đánh số;
  lược đồ JSON buộc mô hình trả `{dong, viec}` — số thứ tự vấn đề (`enum`) và một câu "Nên …". Câu hiện ra
  là `viec — căn cứ: <dòng dữ kiện>`: con số người đọc thấy luôn là số của hệ thống. Lý do: đo trên dữ liệu
  trình diễn, để Qwen2.5-1.5B tự viết cả câu có số thì nó gắn số thật cho sai đối tượng (trung vị của phòng
  này nói thành của phòng kia), ghép số hai dòng thành "từ … lên …", hay chỉ chép lại dòng dữ kiện
- **Kiểm số và kiểm đối tượng** cho phần mô hình viết: tách số (dấu chấm nghìn, dấu phẩy thập phân) kèm đơn
  vị đứng sau (`%`, giờ, phút, hồ sơ, lần) và các tên (trạng thái, loại, phòng, nhánh lệch — đọc từ kết
  quả); mọi số phải có trong **chính dòng** nó trỏ tới, cùng đơn vị, mọi tên cũng thuộc dòng đó — sai là
  **bỏ cả câu**. Số thứ tự đầu mục ("1.") bị gỡ trước. `kiem_cau` (cả câu tự do) dùng cùng phép. Số viết
  bằng chữ không bắt được — giới hạn đã biết
- **Không chờ, không hỏi lại**: lần hỏi đầu xếp việc sinh vào một luồng nền và trả `pending`; màn hỏi lại 3
  giây một lần. Bộ nhớ đệm trong tiến trình theo khoảng ngày, phạm vi và **mã băm của chính kết quả khai
  phá** — cùng dữ liệu thì có ngay, số đổi thì sinh lại; lần hỏng nhớ `DXLAB_RECOMMENDATION_RETRY_AFTER_SECONDS`
- **Chỉ để đọc**: không ghi gì, không đổi cấu hình nào. Khối *Khuyến nghị cải tiến* nằm dưới câu kết luận,
  ghi "Gợi ý của hệ thống"; mô hình tắt hay không câu nào qua phép kiểm thì khối không hiện, màn vẫn đủ
  câu kết luận tất định

### 6.8. Thông báo thư điện tử (không gian `P`)

**Đã cài đặt** — #251. Mã ở `backend/app/thong_bao/`, bảng ở migration 0024, dữ liệu ở
`infra/seed/05-loai-thong-bao.sql`.

**Tắt mặc định.** `SMTP_HOST` rỗng thì không sự kiện nào được xếp hàng, bộ gửi không chạy, màn Hệ thống
ghi "tắt". Hồ sơ Compose `thu-thu` có Mailpit (MIT) làm hộp thư thử để trình diễn.

**Loại thông báo là dữ liệu.** Bảng `notification_types`: mã, nhãn, mẫu tiêu đề và nội dung
(`string.Template`, biến viết sai để nguyên chứ không làm hỏng việc gửi), mặc định bật/tắt, cột
`trigger` và `recipients`. Mã chỉ biết ba **cơ chế kích hoạt** — `state-entered` (mọi lần chuyển đổi
trạng thái hay đổi người được giao), `auto-warning` (vào khoảng báo trước của cạnh tự đi, tính từ
`auto_after_hours`/`warn_before_hours` đã có, #142), `auto-done` (hệ thống vừa tự đi cạnh đó) — và hai
**cách chọn người nhận** — `primary-step` (người đang có bước chính, cùng phép tính `my_primary_steps`
với cờ "cần tôi xử lý", mục 7.3) và `requester`. Thêm loại, đổi lời, tắt một loại là sửa dữ liệu.

**Hai tầng hàng đợi, tách khỏi giao dịch nghiệp vụ:**

1. `notification_outbox` — một dòng mỗi **sự kiện**, ghi bằng `xep_hang()` **trong cùng giao dịch** với
   chuyển trạng thái (`perform_transition`, bước 5) hay với lượt quét hạn chờ. Chỉ một câu INSERT, không
   gọi mạng: giao dịch hủy thì sự kiện mất theo, giao dịch thành công thì sự kiện chắc chắn còn — không
   có thư "ma" cho thao tác bị hoàn tác, không mất thư cho thao tác đã xong. Sửa nội dung (cạnh tự trỏ,
   không đổi người được giao) không xếp gì
2. `notification_deliveries` — một dòng mỗi **thư cho một người**: tiêu đề, nội dung đã dựng, trạng thái
   (`pending`, `sent`, `failed`, `skipped`), số lần thử, lỗi cuối, lúc gửi. Đây là **vết để đối soát**;
   ràng buộc duy nhất (sự kiện, loại, người) chặn gửi trùng

**Bộ gửi** (`bo_gui.quet_gui`) là một bộ quét nền theo khuôn `nhip_quet.py` (#253): khóa tư vấn
`email-notify` — nhiều bản dịch vụ không gửi trùng — và dòng nhịp hiện trên màn Hệ thống. Một lượt:
(1) phát hiện hồ sơ vào khoảng báo trước, xếp `auto-warning` với khóa chống trùng (hồ sơ, lúc vào
trạng thái) — mỗi lần vào trạng thái báo đúng một lần; (2) mở rộng sự kiện thành thư — sự kiện **lỗi
thời** (hồ sơ đã đi tiếp trước khi bộ gửi kịp xử lý) bị bỏ, để người có việc ở trạng thái mới không nhận
hai thư; người vừa làm thao tác không nhận thư về chính thao tác đó; (3) gửi thư đến hạn qua `smtplib`
của thư viện chuẩn, một kết nối cho cả lượt. Tùy chọn của người nhận và địa chỉ thư kiểm **lúc gửi**:
tắt loại thì thư chờ thành `skipped`; danh bạ không có email cũng `skipped`.

**Lỗi không lan ngược.** Máy chủ thư sập: thư `pending`, thử lại sau `NOTIFY_RETRY_AFTER_SECONDS` nhân
đôi mỗi lần, tối đa `NOTIFY_MAX_ATTEMPTS` rồi `failed`; không mở được kết nối thì các thư còn lại đợi lượt
sau thay vì chờ hạn chót từng thư. Danh bạ sập: sự kiện nằm chờ, nhịp bộ gửi vẫn tốt (danh bạ là phụ
thuộc của việc gửi, không phải của bộ quét). Không trường hợp nào chạm tới chuyển trạng thái — nó đã
commit từ trước.

**Danh bạ.** Địa chỉ thư không lưu trong cơ sở dữ liệu của dịch vụ: tra Keycloak lúc gửi. Người có bước
chính có thể thuộc một vai không gắn phòng ban (điều phối viên), mà quyền `view-users` của tài khoản danh
bạ không đọc được `/roles/<vai>/users` (Keycloak trả 403 — đã thử trên cụm), nên `KeycloakDirectory.everyone()`
đọc cả danh bạ theo trang rồi tra vai trò và nhóm từng người, và bộ gửi nhớ kết quả
`NOTIFY_DIRECTORY_CACHE_SECONDS` giây. Hợp với quy mô vài chục tới vài trăm tài khoản; danh bạ hàng nghìn
người thì nên gom vai vào nhóm Keycloak và đọc thành viên nhóm, hoặc cấp thêm quyền xem vai trò cho tài
khoản danh bạ — quyết định để ngỏ.

**Tùy chọn người dùng.** `notification_preferences` (người, loại, bật); không có dòng là theo
`default_enabled` của loại. `GET /me/notifications`, `POST /me/notifications/{loại}` — định danh lấy từ
token, không ai đổi được tùy chọn của người khác. Cổng có trang `/thong-bao`, mở từ biểu tượng chuông
cạnh tên ở thanh bên.

**Webhook — truyền phát sự kiện ra ngoài (#390).** Cùng khuôn hàng đợi, nhưng cho ứng dụng khác chứ không
cho người: `backend/app/webhook.py`, bản sửa 0031. Quản trị viên (người hay tài khoản dịch vụ mang vai
`administrator` — cùng mức với xuất nhật ký, vì đăng ký nhận sự kiện của mọi hồ sơ) đăng ký một địa chỉ ở
`POST /core/v1/webhooks`, bộ lọc theo mã hoạt động và mã quy trình nằm trong dòng đăng ký. Nguồn là
`event_log` — không thêm chỗ ghi nào vào cửa chuyển trạng thái. Mỗi đăng ký giữ con trỏ `last_event_id`
(đăng ký mới bắt đầu từ sự kiện lớn nhất lúc tạo); mỗi lượt bộ gửi biến sự kiện mới khớp bộ lọc thành dòng
`webhook_deliveries` — khóa duy nhất (đăng ký, sự kiện) nên không gửi trùng — rồi dời con trỏ, cùng giao
dịch. Gửi là `POST` JSON (mã sự kiện, hồ sơ, quy trình, hoạt động, từ → sang, người làm, mốc UTC) ký
`X-DXOS-Signature: sha256=HMAC(bí mật, "<X-DXOS-Timestamp>.<thân>")`; bí mật chỉ trả một lần lúc tạo. 2xx là
xong; khác thì chờ `DXLAB_WEBHOOK_RETRY_AFTER_SECONDS` nhân đôi mỗi lần, quá `DXLAB_WEBHOOK_MAX_ATTEMPTS` lần
là hỏng hẳn; `GET /core/v1/webhooks/{id}/deliveries` cho thấy mã phản hồi và lỗi cuối. Bộ gửi chạy theo
khuôn #253 (khóa tư vấn, dòng nhịp "Bộ gửi webhook" ở màn Hệ thống), chu kỳ `DXLAB_WEBHOOK_SCAN_INTERVAL_SECONDS`
(5 giây; 0 là tắt). Bên nhận có thể nhận lại một sự kiện nếu trả lời không kịp — bỏ trùng theo
`X-DXOS-Event-Id`; ví dụ bên nhận ở `examples/goi-loi/nhan_webhook.py`. Quản trị viên đăng ký, theo dõi năm lần
gửi gần nhất và hủy ngay trên màn **Hệ thống** của cổng (#401, `frontend/app/he-thong/quan-ly-webhook.tsx`):
khối chỉ gọi API lõi qua hành động máy chủ, bí mật ký hiện một lần rồi không lưu phía cổng. Sự kiện "tạo hồ sơ" không phải
dòng `event_log` (nó dựng từ `requests` trong view xuất nhật ký) nên không đi qua webhook.

Chọn webhook qua HTTP chứ không một trục truyền phát như Kafka: quy mô trình diễn (mục 9), không thêm dịch
vụ hay phụ thuộc, bên nhận chỉ cần một địa chỉ HTTP; đọc lại từ đầu đã có `GET /core/v1/events` trên nhật ký
chỉ ghi thêm. Hướng mở rộng: thêm một "đầu ra" Kafka (Apache-2.0) đọc cùng con trỏ — cần khảo sát và ADR
trước; Redpanda dùng BSL, không thuộc danh sách OSI.

### 6.9. Kho tri thức (không gian `H`)

**Đã cài đặt** — #321, [ADR-0006](adr/0006-chon-nen-tang-kho-tri-thuc.md). Wiki.js `2.5.315` dưới hồ sơ Compose
**tùy chọn** `tri-thuc`; cụm mặc định không đổi, không tải thêm gì.

**Ranh giới AGPL.** Ảnh chính thức chạy nguyên bản. Mã của nhóm chỉ nói chuyện với nó qua mạng: bước khởi tạo
qua `/finalize` và GraphQL, người dùng qua OIDC, dịch vụ ứng dụng qua GraphQL bằng khóa API chỉ đọc. Không thư
mục nào mang AGPL vì Wiki.js — khác PM4Py (mục 6.4), vốn là thư viện được nhập vào mã của nhóm (`LICENSES.md`).

**Khởi tạo bằng dữ liệu, lặp lại an toàn** (`infra/tri-thuc/khoi_tao.py`, chạy trong ảnh dịch vụ ứng dụng — không
thêm ảnh):

| Bước | Trước / sau Wiki.js | Việc | Lặp lại |
|---|---|---|---|
| `chuan-bi` | Trước | Database `wiki` trên PostgreSQL của cụm; client OIDC `dx-wiki` trong Keycloak và bộ ánh xạ vai trò realm → claim `wiki_groups` | Có rồi thì cập nhật địa chỉ, bí mật |
| `khoi-tao` | Sau | `/finalize` lần đầu (tắt thống kê sử dụng); tiêu đề, ngôn ngữ; nhóm theo vai trò; chiến lược đăng nhập; khóa API; bài mẫu từ `infra/tri-thuc/bai-mau/` | Đã cài thì bỏ qua cài đặt; khóa cũ còn dùng được thì giữ; bài đã có không ghi đè |

Client OIDC tạo qua API quản trị chứ không khai trong `realm-dx-os-lab.json`, vì Keycloak chỉ nạp tệp realm lúc tạo
realm: một đường duy nhất chạy được cho cả cụm dựng mới lẫn cụm cũ nâng lên, không `down -v`.

**Đăng nhập một lần, quyền theo vai trò.** Chiến lược OIDC khóa `keycloak`: trình duyệt mở Keycloak bằng địa chỉ công
khai, Wiki.js đổi token và gọi userinfo trong mạng Compose; `KC_HOSTNAME` cố định `iss` công khai nên hai đường khớp
nhau (mục 3, ghi chú "một Keycloak, hai địa chỉ"). Cổng dẫn thẳng `/login/keycloak`, nên người đã đăng nhập cổng vào
kho tri thức không phải nhập mật khẩu lần hai. Wiki.js `mapGroups` gán người dùng vào nhóm có **tên trùng** giá trị
trong claim nhóm và đồng bộ ở mỗi lần đăng nhập, nên mỗi vai trò realm là một nhóm cùng tên; vai nào đọc, vai nào viết
nằm ở `WIKI_READ_ROLES`, `WIKI_WRITE_ROLES`. `updateStrategies` của Wiki.js xóa mọi chiến lược không có trong danh
sách gửi lên, nên bước khởi tạo luôn gửi kèm `local` (tài khoản quản trị wiki), tắt tự đăng ký cục bộ.

**Khóa API chỉ đọc** cấp cho nhóm `dx-os-lab-doc` (chỉ `read:pages`, `read:source`), ghi vào volume `tri-thuc-khoa` để
dịch vụ ứng dụng đọc. Kiểm trên cụm thử: khóa đọc và tìm được bài tiếng Việt có dấu, gọi `pages.delete` thì bị
`Forbidden`.

**Kiểm chứng (cụm thử).** Đăng nhập cổng bằng `an.nguyen`, `binh.tran`, `dung.pham` qua trang Keycloak thật rồi mở
`/login/keycloak`: vào thẳng, không ô mật khẩu nào; người gửi chỉ đọc, điều phối viên có nút sửa. Chạy lại hai bước
khởi tạo: không lỗi, không tạo trùng. Nâng cụm dựng từ v0.15.0 có dữ liệu: client mới vào realm cũ, đăng nhập một lần
chạy, `scripts/kiem_nang_cap.py` đối soát đạt. Bộ nhớ Wiki.js khoảng 276 MiB ngay sau một lượt dùng.

**Nối vào cổng — một công tắc `WIKI_URL`.** Rỗng (mặc định) là tắt: `/me` trả `knowledge_base: null`, thanh bên
không có lối vào, gợi ý khi soạn chỉ có hồ sơ (#319). Đặt thì `/me` trả địa chỉ `/login/keycloak` và mã nguồn của
Wiki.js; thanh bên có mục **Kho tri thức** mở thẻ mới, dưới tên ghi *Wiki.js · AGPL-3.0 · mã nguồn* (`LICENSES.md`).
Bước khởi tạo bật `authAutoLogin` của Wiki.js: `/login` chuyển thẳng sang Keycloak, nên liên kết tới một bài
mở được ngay; quản trị wiki vào `/login?all=1`.

**Nguồn thứ hai cho truy xuất tri thức (`I`, #319).** Bảng `knowledge_articles` (bản sửa `0027`, pgvector): một
dòng cho mỗi bài đã xuất bản, không riêng tư — bản sao dẫn xuất, dựng lại được, không ghi vết. Bộ lập chỉ mục
`wiki-index` (`app/intelligence/tri_thuc.py`, khuôn `nhip_quet.py`, hiện trên màn Hệ thống) chỉ chạy khi cả
`WIKI_URL` lẫn mô hình nhúng bật: đọc danh sách bài qua GraphQL, so mốc `updatedAt` và mô hình, nhúng tối đa
`wiki_index_batch_size` bài mới hay vừa sửa, xóa dòng của bài đã xóa hay thôi xuất bản. Nội dung bài đọc qua trang
mã nguồn `/s/<ngôn ngữ>/<đường dẫn>` chứ không qua GraphQL: ở Wiki.js 2.5, `pages.single` đòi `manage:pages`
hoặc `delete:pages` — quyền sửa, xóa — chỉ để đọc, còn trang mã nguồn chỉ cần `read:source`, đúng quyền của khóa.
Định dạng trang ổn định vì ảnh ghim phiên bản; bài kiểm thử giữ một mẫu trang.

Điểm cuối gợi ý khi soạn (`/similar-cases/search`) nhúng câu đang gõ **một lần** rồi tìm cả hồ sơ đã giải quyết
lẫn bài (`wiki_max_results`, ngưỡng `wiki_min_score`), trả thêm `articles` và `articles_source_url`. Bài đọc từ chỉ
mục trong cơ sở dữ liệu, không gọi sang wiki: wiki tắt hay chậm không làm chậm biểu mẫu. Vẫn chỉ là gợi ý — người
gửi bấm mở bài, hoặc gửi yêu cầu như thường (CLAUDE.md mục 4.3).

**Kiểm chứng phần nối.** `tests/test_tri_thuc.py` (13 bài, GraphQL giả, mô hình nhúng giả): bỏ bài nháp và riêng tư;
bài sửa nhúng lại, bài xóa bỏ khỏi chỉ mục; giới hạn lô; một trong hai công tắc tắt thì không làm gì; wiki hay mô
hình hỏng thì bỏ lượt, chỉ mục còn nguyên; bài vào gợi ý cùng một lần nhúng; `/me` có/không có lối vào. Bốn phép đột
biến (bỏ lọc riêng tư, bỏ xóa bài, bỏ so mốc sửa, bỏ công tắc ở bước tìm) đều làm bài đỏ. Trên cụm thử có hồ sơ
`tri-thuc` và mô hình nhúng thật: viết một bài mới ("Laptop không kết nối được Wi-Fi văn phòng"), sau một lượt quét
người gửi gõ "Laptop không vào được Wi-Fi" trên biểu mẫu thật thì khung gợi ý hiện đúng bài đó, bấm mở vào thẳng
wiki; tắt wiki giữa chừng thì gợi ý vẫn hiện từ chỉ mục và gửi yêu cầu vẫn chạy.

---

## 7. Khuôn mẫu: ràng buộc Poka-yoke

**Đã cài đặt** — `backend/app/rules/guards.py`. Nguyên tắc: chặn thao tác sai **tại
điểm chạm đầu vào**, thay vì phát hiện sau khi dữ liệu đã hỏng.

Ràng buộc chia hai loại, và loại thứ nhất mạnh hơn hẳn:

**Loại cấu trúc — thực thi bằng sự VẮNG MẶT.** Không cần dòng mã nào canh cửa, vì
không có cửa. *"Đã nhận là không trả về"* đơn giản là bảng `transitions` không có
dòng nào đi từ `in-progress` ngược về phía trước. *"Chỉ hủy trước khi vào xử lý"*
là cạnh hủy chỉ xuất phát từ bốn trạng thái đầu. Không phải *không nên đi*, mà là
**không có đường mà đi**.

**Loại kiểm tra lúc chạy — khai trong bảng, cài trong mã.** Bảng `guards` khai mã
ràng buộc, bảng `transition_guards` nối mã với từng cạnh, `guards.py` cài hàm tương
ứng. Nhờ tách như vậy, gắn thêm một ràng buộc đã có cho một cạnh khác chỉ là thêm một
dòng dữ liệu; chỉ khi cần một *loại* ràng buộc mới mới phải viết mã.

Điểm quan trọng: mã ràng buộc có trong bảng mà thiếu hàm cài đặt sẽ làm engine **từ
chối chuyển trạng thái**, không im lặng bỏ qua. Im lặng cho qua sẽ biến một ràng buộc
nghiệp vụ thành vô hiệu mà không ai biết.

**Ràng buộc còn quyết định trường nào đặt được ở cạnh nào** — từ #78. Mỗi mục trong
`GUARD_REGISTRY` khai, cạnh hàm kiểm tra, tập trường mà ràng buộc đó chịu trách nhiệm.
Một lần chuyển trạng thái chỉ kèm được trường mà ràng buộc gắn trên **chính cạnh đó**
quản; gửi trường khác thì engine từ chối bằng `field-not-permitted` và không ghi dòng
nhật ký nào.

Hai biên, giữ ở hai thời điểm khác nhau:

| Biên | Chặn gì | Kiểm lúc | Nằm ở |
|---|---|---|---|
| Ngoài | Ràng buộc quản hay tự đặt trường không thuộc bốn trường quyết định và hai trường nội dung — `current_state`, `suggested_*` | **Nạp mô-đun** — sai thì dịch vụ không khởi động | `CHANGEABLE_FIELDS` trong `engine.py` |
| Trong | Lần chuyển gửi kèm trường mà cạnh đang đi không quản | **Mỗi lần chuyển** — sai thì bị từ chối | `permitted_fields()` trong `guards.py` |

Biên ngoài không cần kiểm lại lúc chạy: trường một cạnh cho đặt luôn là tập con của
trường được ràng buộc quản, mà tập đó đã được xác nhận nằm trong biên lúc nạp. Phép
thử đột biến ở #78 xác nhận điều này — một phép kiểm biên ngoài lúc chạy, gỡ đi, không
làm đổ bài nào, vì nó không bao giờ tự mình chặn được gì.

Trước #78 chỉ có tầng ngoài, nên ai đi được một cạnh bất kỳ cũng sửa được mọi trường
quyết định — người xử lý bấm *Hoàn thành xử lý* kèm `priority_code` là tự nâng được mức
ưu tiên việc của mình. Ràng buộc Poka-yoke *người tạo không tự đặt mức ưu tiên* khi đó
chỉ đứng được nhờ giao diện không có ô nhập, tức là đúng kiểu *chỉ chặn ở giao diện* mà
mục này cảnh báo.

Bản đồ trường nằm trong mã chứ không trong bảng, vì nó là bản chất của chính hàm:
`set_priority` đọc `changes["priority_code"]`. Khai trong bảng thì dữ liệu và mã có thể
âm thầm nói hai điều khác nhau. Nhưng **gắn** ràng buộc vào cạnh nào thì vẫn là dữ liệu:
gỡ `set-priority` khỏi một cạnh trong `infra/seed/` là cạnh đó hết đặt được mức ưu tiên.

**Ràng buộc không cần nhập liệu chạy luôn lúc chào nút** — từ #79. Mỗi mục trong
`GUARD_REGISTRY` khai thêm cờ `input_free`: ràng buộc chỉ đối chiếu người thao tác, hồ sơ
và lịch sử hồ sơ, không đọc giá trị người dùng định đặt. `allowed_transitions()` chạy nhóm
này nên cạnh chắc chắn bị từ chối không hiện thành nút — người gửi không thấy nút trên hồ
sơ của người khác, trưởng phòng không thấy nút trên hồ sơ của phòng khác. Ràng buộc đọc
`changes` thì chưa chạy được lúc chào nút, vì chưa ai biết người dùng sẽ chọn gì; chạy nó
với `changes` rỗng sẽ giấu mất những cạnh hoàn toàn đi được. Lúc chào nút chỉ nuốt lỗi
Poka-yoke: mã ràng buộc chưa cài đặt vẫn nổ, vì giấu nút đi thì cấu hình sai trông như
"không có thao tác nào".

**Ràng buộc đầu tiên đọc lịch sử hồ sơ** — `return-to-previous-state`, cũng từ #79. Nó chỉ
cho đi cạnh về đúng trạng thái hồ sơ đã ở ngay trước trạng thái hiện tại. Không có bảng ánh
xạ "hỏi ở đâu thì về đâu": quy tắc chỉ là "về chỗ cũ", và chỗ cũ là `from_state` của dòng
nhật ký mới nhất **có đổi trạng thái** — dòng tự trỏ bị bỏ qua (mục 6.2). Engine tra sẵn
giá trị đó vào `TransitionContext.previous_state`, nên hàm ràng buộc vẫn không tự truy vấn
cơ sở dữ liệu — đúng quy ước của lớp bối cảnh. Gắn ràng buộc này vào cạnh nào là dữ liệu;
tệp kiểm tra mức đồ thị chặn khởi động nếu một đường vào trạng thái chờ thiếu đường về
tương ứng.

**Ràng buộc có tác động — tự đặt trường thay người dùng** (#127). Ngoài tập trường nó
*quản* (`governs` — người dùng được gửi), một mục trong `GUARD_REGISTRY` có thể khai tập
trường nó *tự đặt* (`sets`) cùng hàm tác động (`effect`). *Nhận việc về mình* là ví dụ đầu
tiên: ràng buộc `assign-self` kiểm hồ sơ chưa giao ai, rồi tự đặt `assignee_id` bằng chính
người bấm. Ba quy tắc:

- Trường tự đặt **không** nằm trong `permitted_fields()`, nên người dùng không gửi kèm được
  — nhận việc mà gửi `assignee_id` của người khác thì bị từ chối bằng `field-not-permitted`.
  Cũng vì thế người xử lý **không** thành vai trò giao việc: tập đó suy từ cạnh *cho đặt*
  `assignee_id` (mục 7.2), và cạnh nhận việc không cho đặt, chỉ tự đặt
- Tác động chạy **sau** khi mọi ràng buộc đã qua, **trước** khi ghi nhật ký: lần chuyển bị
  từ chối không đặt gì, và cột `changes` vẫn có đủ phần "từ → sang" như mọi thay đổi khác
- Hàm tác động trả trường chưa khai trong `sets` thì `apply_effects()` ném lỗi lập trình,
  không lặng lẽ ghi. Và `governs ∪ sets` của mọi ràng buộc phải nằm trong biên ngoài
  `CHANGEABLE_FIELDS` — kiểm lúc nạp mô-đun như trước

Còn một cách diễn đạt thứ ba, đặt ở tầng thấp nhất: **khóa ngoại và chỉ mục duy nhất
từng phần** trong lược đồ — xem mục 5.2. Mỗi tầng bắt một loại sai khác nhau, và tầng
càng thấp thì càng khó lách.

Ví dụ dự kiến:

- Không cho đóng hồ sơ nếu thiếu ghi chú xử lý
- Không cho phân công cho người đang vượt ngưỡng tải
- Không cho chọn ngày hoàn thành trong quá khứ
- Không cho chuyển trạng thái không có trong bảng quy tắc

Ràng buộc phải cài đặt ở **cả hai phía**: giao diện chặn để trải nghiệm tốt, dịch
vụ chặn để bảo đảm toàn vẹn. Chỉ chặn ở giao diện là không đủ.

### 7.1. Đồng hồ SLA và tự leo thang

**Đã cài đặt** — `backend/app/rules/sla.py` và `backend/app/workflow/escalation.py`.

ADR-0004 ghi rõ: chọn tự viết engine đồng nghĩa nhận trách nhiệm tự làm bộ đếm thời
gian, thứ mà một nền tảng workflow có sẵn sẽ cho không. Đây là món nợ đó.

**Ba cột thay cho một mốc hạn chót.** `requests` giữ `sla_running_seconds`,
`sla_paused_seconds` và `sla_segment_since`. Lý do không tính sẵn một mốc hạn chót:
đồng hồ dừng rồi chạy lại nhiều lần trong đời một hồ sơ, nên mốc cố định sẽ sai ngay
lần đầu người dùng bị hỏi thêm thông tin.

**Đồng hồ đếm giờ làm việc, không đếm giờ lịch** (#199). Hồ sơ cam kết 8 giờ mà phòng ban
nhận lúc 15:00 thứ Sáu thì hạn là 15:00 thứ Hai — đêm, cuối tuần, nghỉ trưa, ngày lễ không
trôi. Lịch là dữ liệu (mục 5.2): khung giờ theo thứ, ngày nghỉ, múi giờ, một lịch mặc định
cho cả công ty. Mọi phép đo đi qua hai hàm của lược đồ khởi tạo — `so_giay_lam_viec(từ,
đến)` và phép ngược `moc_sau_giay_lam_viec(từ, số giây)` — không chỗ nào trong mã tự trừ
hai mốc thời gian. Đặt hàm trong PostgreSQL vì truy vấn tìm hồ sơ quá hạn của bộ quét cần
đo ngay trong SQL; Python gọi đúng hàm đó, nên hai nơi không thể đo lệch nhau. Áp cho cả
đoạn chạy lẫn đoạn dừng, ân hạn, và hạn chót `sla_due_at` dịch vụ trả cho giao diện ("hạn
15:00 Thứ Hai 19/10" — chỉ có khi đồng hồ đang chạy, vì lúc dừng chưa biết nó chạy lại
khi nào). `sla_hours`, `sla_grace_hours` giữ nguyên số, nay là giờ làm việc. Mốc thời gian
vẫn lưu UTC; lịch chỉ dùng để đo khoảng.

**Hạn của hồ sơ = hạn chuẩn × hệ số ưu tiên + giờ đã gia hạn** (#101). `gioi_han_giay` cộng
ba con số trong dữ liệu: `request_types.sla_hours`, `priorities.sla_factor_percent`,
`requests.sla_extension_total_hours`; ân hạn nhân cùng hệ số. Truy vấn của bộ quét tính đúng
phép đó trong SQL — chia nguyên, ép `BIGINT` trước khi nhân — để Python và bộ quét không lệch
nhau một giây. Gia hạn là cạnh tự trỏ theo ADR-0005: ô nhập là số giờ của lần này
(`sla_extension_hours`), còn tổng và số lần do **tác động** của ràng buộc `extend-deadline`
tự đặt, người dùng không gửi được. Vì thế một trường có thể vừa nằm trong `governs` vừa trong
`sets` của cùng ràng buộc: ô nhập là chuỗi, tác động ghi lại dạng số nguyên. Ai gia hạn lần
nào là ràng buộc gắn trên từng cạnh (`first-extension`, `extension-limit`), không mã cứng vai
trò.

**Ngưỡng "sắp hết hạn" là phần trăm cam kết, khai theo loại yêu cầu** (#175). Cột
`request_types.sla_warn_percent` (mẫu 75, lược đồ chặn ngoài khoảng 1–99): hồ sơ đã dùng từ
chừng ấy phần trăm hạn của chính nó mà chưa quá hạn thì `sap_het_han` trả đúng, dịch vụ trả
cờ `sla_due_soon` cạnh `sla_overdue`. Chọn phần trăm thay vì số giờ còn lại để ngưỡng co giãn
theo hạn của từng hồ sơ — hạn đổi thì không phải sửa ngưỡng. Thẻ hạn tô vàng, hàng đợi phòng
ban có nhóm *Sắp hết hạn* giữa *Quá hạn* và *Trong hạn*.

**Trạng thái nào làm đồng hồ chạy là dữ liệu, không phải mã.** Cột `states.sla_running`
trả lời cả hai câu — đồng hồ bắt đầu từ đâu, và dừng ở đâu — nên mã nguồn không phải
viết `if state == "in-progress"`. Hiện chỉ `in-progress` và `escalated` bật cờ này.

Hệ quả nghiệp vụ có chủ đích: **thời gian ở `awaiting-info` không tính vào SLA**, vì
người xử lý không nên bị phạt khi người tạo chậm trả lời. Nhưng tổng thời gian dừng
vẫn cộng dồn vào `sla_paused_seconds`, để khai phá quy trình phát hiện ai lạm dụng
cách hỏi thêm thông tin để dừng đồng hồ. Muốn tính vào thì bật cờ cho `awaiting-info` —
sửa một giá trị trong `infra/seed/`, không đụng mã.

**Leo thang cũng đi qua điểm chuyển trạng thái duy nhất.** Bộ quét không tự đặt
`current_state`; nó gọi `perform_transition` với tác nhân hệ thống. Nếu đi tắt cho
nhanh thì nhật ký sẽ thiếu đúng những bản ghi thú vị nhất — các lần trễ hạn — và khai
phá quy trình mất khả năng chỉ ra điểm nghẽn.

**Trạng thái đích cũng không viết cứng.** Bộ quét tra bảng `transitions` tìm cạnh mang
cờ `is_system` xuất phát từ trạng thái hiện tại. Nhờ vậy hồ sơ ĐANG ở `escalated` không
bị nhặt lại mỗi vòng — từ đó không còn cạnh hệ thống nào — mà không cần thêm một cột
*"đã leo thang chưa"*.

**Hạn chờ: cạnh hệ thống tự đi khi hồ sơ nằm im** (#142). Đồng hồ SLA không giúp gì ở trạng
thái chờ một người bấm — nó chưa chạy hay đang dừng. Cạnh hệ thống mang
`transitions.auto_after_hours` tự đi khi hồ sơ nằm ở trạng thái nguồn đủ chừng ấy giờ làm việc,
đo từ lần chuyển gần nhất đổi trạng thái vào đó (cạnh tự trỏ không đặt lại); `warn_before_hours`
để màn hình báo trước. Mỗi trạng thái tối đa một cạnh như vậy (chỉ mục duy nhất từng phần). Bộ
quét thứ hai `quet_het_han_cho` chạy cùng vòng với bộ quét leo thang, mỗi bộ một giao dịch, tác
nhân `wait-watcher`, và cũng đi qua cửa chuyển trạng thái duy nhất. Hai bộ quét không giẫm nhau:
bộ leo thang chỉ nhận cạnh hệ thống **không** có hạn chờ. Dịch vụ trả `auto_transition` (nhãn
cạnh, lúc tự đi, đã vào khoảng báo trước chưa) để giao diện ghi "Tự trả về điều phối lúc …" và
nhấn màu khi sắp tới. Tính lúc vào trạng thái từ nhật ký, nên bộ quét nhận *thời điểm xét* làm
tham số — bài kiểm thử truyền một mốc tương lai thay cho việc sửa nhật ký vốn chỉ ghi thêm.

**Ân hạn sau mỗi lần vào lại trạng thái đếm giờ** (#94). Chỉ riêng cấu trúc dữ liệu thì
chưa đủ: trưởng phòng phân công lại thì hồ sơ về `in-progress`, đồng hồ tổng vẫn quá
hạn, và lượt quét kế tiếp leo thang lại ngay — đo thật được 38 giây. Mở lại một hồ sơ đã
quá hạn, hay bổ sung thông tin xong, cũng rơi vào đúng chỗ đó. Bộ quét vì vậy đòi thêm
một điều kiện: hồ sơ đã ở trạng thái hiện tại lâu hơn `request_types.sla_grace_hours`.
Mốc đo là `sla_segment_since`, vốn mở lại ở mỗi lần chuyển trạng thái.

Ba lựa chọn đã cân nhắc: cho ân hạn, chỉ leo thang một lần, hay đặt lại đồng hồ. Chọn
ân hạn vì hai cái kia mỗi cái hỏng một thứ — chỉ leo thang một lần thì hồ sơ bị bỏ bê
lần hai không ai biết, đặt lại đồng hồ thì số liệu thời gian xử lý mà tầng `I` cần bị
xóa dấu. Với ân hạn, đồng hồ tổng giữ nguyên, hồ sơ vẫn được ghi nhận là quá hạn, và
hết ân hạn mà vẫn chưa xong thì leo thang lại. Ân hạn không được dài hơn chính hạn xử
lý — ràng buộc `CHECK` chặn, vì khi đó lần leo thang đầu tiên cũng bị hoãn. Giao diện
nói "Quá hạn … · ân hạn còn …" để không ai tưởng hệ thống quên hồ sơ.

**Mở lại có giới hạn và hạn mới** (#102). Hai cạnh mở lại — *Mở lại, chưa đạt* từ `completed`
và *Mở lại sau khi đóng* từ `closed` — dùng chung ràng buộc `reopen-limit`: số lần đếm ở
`requests.reopen_count`, trần ở `request_types.reopen_max_count`, và tác động của ràng buộc đặt
lại ba trường gia hạn về 0 rồi đếm thêm một lần. Đồng hồ SLA đếm lại từ 0 nhờ cờ dữ liệu
`transitions.restarts_sla`, xử lý trong `cap_nhat_dong_ho` sau khi chốt đoạn vừa qua: số giây đã
chạy không phải trường quyết định để kể trên dòng thời gian, nên không đi qua `changes`. Chiều
này đảo lại điều #94 đã chọn cho riêng trường hợp mở lại — **đặt lại đồng hồ** thay vì ân hạn —
vì giảng viên chốt 08/10 "cấp hạn mới cho chu kỳ xử lý mới"; số liệu của chu kỳ cũ vẫn nằm trọn
trong nhật ký sự kiện cho tầng `I`. Ân hạn của #94 giữ nguyên cho phân công lại sau leo thang và
bổ sung thông tin xong.

Cạnh rời trạng thái kết thúc (*Mở lại sau khi đóng*) là cạnh DUY NHẤT thuộc loại đó, và lược đồ
bắt nó khai `reopen_window_hours`: cửa sổ đo bằng giờ làm việc từ lúc hồ sơ vào trạng thái kết
thúc, theo cùng hàm lịch với `auto_after_hours`, ràng buộc `reopen-window` đọc cột này của chính
cạnh đang đi. `reopen-from-rework` chỉ cho mở lại hồ sơ mà trạng thái đứng ngay trước khi kết
thúc có cạnh làm lại (`is_rework`) về cùng đích — suy từ dữ liệu và nhật ký như
`return-to-previous-state`, không có danh sách trạng thái nào trong mã. Cả ba ràng buộc đều
`input_free`: hết lượt hay quá cửa sổ thì nút biến mất khỏi `allowed_transitions`, và giao diện
mời tạo hồ sơ mới thay vào. Hồ sơ mới mang `requests.parent_request_id`, chỉ đặt lúc tạo —
`kiem_ho_so_goc` đòi hồ sơ gốc là của chính người gửi và đã ở trạng thái kết thúc; lỗi giống nhau
cho "không có" và "của người khác" để không lộ hồ sơ của người khác. Tạo hồ sơ không sinh dòng
nhật ký (§6), nên liên kết hiện qua hai trường `parent` và `children` của trang hồ sơ chứ không
qua một mốc trên dòng thời gian của hồ sơ cũ.

Hai phép kiểm tra trong `kiem_tra_cau_hinh()` canh bộ quy tắc: phải
có ít nhất một trạng thái chạy đồng hồ, và trạng thái kết thúc không được chạy đồng hồ.
Thiếu điều kiện đầu thì cơ chế leo thang thành mã chết mà không ai biết.

**Chạy nhiều bản dịch vụ: khóa và nhịp của bộ quét** (#253). Hai bộ quét (`BO_QUET` trong
`escalation.py`: `sla-escalation`, `wait-expiry`) chạy trong tiến trình của dịch vụ ứng dụng, nên
chạy hai bản thì cả hai cùng quét. Dữ liệu không hỏng — cổng chuyển trạng thái khóa dòng hồ sơ —
nhưng làm việc trùng và sinh nhiễu nhật ký. `chay_luot_quet` (`workflow/nhip_quet.py`) bọc mỗi lượt:

- **Khóa.** Đầu giao dịch của lượt xin `pg_try_advisory_xact_lock` theo tên bộ quét. Bản nào xin
  được thì quét; bản kia **bỏ lượt** — không chờ, không tính là lỗi. Khóa mức giao dịch nên tự nhả
  khi giao dịch kết thúc, kể cả khi tiến trình chết giữa chừng: không có khóa treo cần dọn. Mỗi bộ
  quét một khóa, nên hai bộ vẫn chạy song song được trên hai bản. Chạy một bản thì lúc nào cũng
  giành được khóa, hành vi như trước.
- **Nhịp.** Bảng `scanner_heartbeats` (migration `0017`) một dòng mỗi bộ quét: lần chạy cuối, lần
  thành công cuối, lần lỗi cuối và câu lỗi, **số lỗi liên tiếp**, bản nào chạy (tên máy chủ, mã tiến
  trình). Lượt thành công ghi nhịp cùng giao dịch với kết quả quét rồi đặt số lỗi liên tiếp về 0.
  Lượt hỏng **hoàn tác trước, rồi mới ghi lỗi ở giao dịch riêng** — ghi chung thì chính dấu vết của
  lượt hỏng bị hoàn tác theo.
- **Tín hiệu.** `/health` (xem 7.4) báo `degraded` khi một bộ quét hỏng liên tiếp tới
  `SLA_SCAN_MAX_CONSECUTIVE_ERRORS` lượt (mặc định 3), hoặc lần thành công cuối đã quá
  `SLA_SCAN_STALE_AFTER_SECONDS` (mặc định 0 = tự tính, năm lần chu kỳ quét). Vế "quá lâu" chỉ xét
  khi chính tiến trình đã chạy quá ngưỡng: vừa khởi động lại sau thời gian dừng dài thì bộ quét
  chưa có cơ hội chạy, không báo đỏ ngay. Tắt bộ quét bằng `SLA_SCAN_ENABLED=false` là chủ ý của
  người vận hành, không phải sự cố.

Bộ quét hỏng **không** làm `/health` trả 503: dịch vụ vẫn phục vụ yêu cầu bình thường, chỉ hồ sơ quá
hạn không tự leo thang. Healthcheck của Docker và các dịch vụ chờ `service_healthy` (cổng, Superset)
không được rớt hay kẹt vì một bộ quét trượt — họ đọc `status` nếu cần phân biệt. Nhịp chi tiết hiện ở
màn Hệ thống.

### 7.2. Giao diện không giữ bản sao của bộ quy tắc

**Đã cài đặt** — `frontend/app/yeu-cau/` từ #44, kéo dài sang `frontend/app/dieu-phoi/` ở #82.

Một cổng người dùng bình thường sẽ có đâu đó một bảng đại loại *"trạng thái nào thì
hiện nút nào"*. Cổng này **không có bảng đó**, và điều đó là cố ý.

Điểm cuối `GET /requests/{id}` trả về `allowed_transitions` — danh sách cạnh mà chính
người đang đăng nhập đi được từ trạng thái hiện tại của hồ sơ, do
`allowed_transitions()` sinh ra từ bảng `transitions` và ma trận phân quyền. Giao diện
dựng nút bấm thẳng từ danh sách đó, lấy cả nhãn chữ (`activity_label`), cờ bắt buộc
ghi lý do (`requires_note`) và tên ô ghi chú (`note_label`, #79). Không có cạnh thì không
có nút. Nút nào tô màu hành động chính cũng theo dữ liệu: cạnh đứng đầu theo
`display_order`. Trước #79 cổng người gửi đoán bằng cờ `requires_note`, và đoán sai ngay
khi cạnh bổ sung thông tin bắt đầu đòi ghi chú — nút *Hủy yêu cầu* thành nút chính.

Đây không phải chuyện gọn mã. Bản thiết kế giao diện của #44 có một bảng như vậy, và
nó **vẽ sai hai chỗ**: đặt nút *"Hủy yêu cầu"* ở `in-progress` và `escalated`, trong
khi dữ liệu không có cạnh nào đi từ hai trạng thái đó tới `cancelled` — đúng ràng buộc
Poka-yoke *"chỉ hủy được trước khi phòng ban bắt tay vào việc"*. Chép bảng ấy vào mã
nguồn sẽ dựng ra hai cái nút bấm vào là báo lỗi. Lấy nút từ API thì hai nút sai tự
biến mất, và không có đường nào cho chúng quay lại.

Ranh giới cần giữ: giao diện **được phép** giữ siêu dữ liệu thuần thị giác — trạng
thái nào mang dấu hiệu gì, thuộc họ màu nào, và đồng hồ hạn xử lý đứng ở đó để chờ
người gửi trả lời hay chờ xác nhận — thứ chỉ dùng để chọn câu chữ, còn đồng hồ có
đứng hay không vẫn do dịch vụ quyết (`frontend/lib/trang-thai.ts`, #97). Bảng
`states` mô tả quy trình, không mô tả cách vẽ quy trình, nên những thứ đó không có chỗ
trong cơ sở dữ liệu. Nhưng bảng ấy phải có **phương án lùi** cho mã trạng thái lạ:
doanh nghiệp thêm một trạng thái vào bộ quy tắc phải thấy nó hiện ra ngay, dù chưa ai
gán dấu hiệu cho nó. Một giao diện vỡ vì dữ liệu hợp lệ là lỗi của giao diện.

Nửa còn lại của Poka-yoke vẫn nằm ở engine: một cạnh hiện ra trên màn hình vẫn bị kiểm
lại khi yêu cầu thật gửi lên. Chặn ở giao diện thôi thì không đủ, vì ai cũng gọi thẳng
API được.

**Nút nào phải hỏi lại cũng đến từ dữ liệu** (#98). Mỗi cạnh mang thêm cờ
`to_state_is_terminal`, tra từ `states.is_terminal`, và từ #102 thêm `to_state_reopen_hours`:
trạng thái kết thúc đích còn cạnh mở lại thì dịch vụ báo cửa sổ bao nhiêu giờ làm việc, để câu
cảnh báo nói đúng "còn mở lại được" thay vì "không hoàn tác được". Cạnh dẫn tới trạng thái kết
thúc thì giao diện mở bảng xác nhận, kèm cảnh báo và ô lý do tùy chọn; cạnh bắt
buộc lý do (`requires_note`) thì lý do vẫn bắt buộc. Trước đó "Hủy yêu cầu" bấm là mất
hồ sơ. Không có danh sách "thao tác nguy hiểm" nào trong mã: doanh nghiệp thêm một trạng
thái kết thúc mới thì mọi cạnh dẫn tới nó tự được hỏi lại.

**Từ #82, khuôn mẫu kéo dài từ nút bấm sang ô nhập.** Buồng lái điều phối viên phải cho
nhập mức ưu tiên, loại yêu cầu, phòng ban. Mỗi cạnh trong `allowed_transitions` nay mang
thêm `fields` — những trường cạnh đó cho đặt, lấy thẳng từ `permitted_fields()` của
ràng buộc gắn trên cạnh (mục 7). Giao diện thấy cạnh *Phân loại yêu cầu* cho đặt
`priority_code` và `request_type_code` thì dựng hai ô chọn; không có bảng nào trong
TypeScript nói *"Phân loại thì hiện ô mức ưu tiên"*.

Hệ quả kiểm chứng được: #78 gắn `set-request-type` thêm vào cạnh chuyển về phòng ban, và
ô *Loại yêu cầu* tự hiện ra ở bảng thao tác của cạnh đó — không ai viết thêm dòng giao
diện nào.

Ranh giới giống hệt ranh giới của trạng thái: `frontend/lib/truong.ts` giữ nhãn hiển
thị và nguồn danh mục của bốn trường quyết định và hai trường nội dung, kèm phương án lùi
cho trường lạ. Các trường đó là lược đồ của hồ sơ chứ không phải cấu hình nghiệp vụ, nên
một bảng nhỏ ở đây không phải bản sao của bộ quy tắc.

**Từ #127, cổng người gửi cũng dựng ô nhập từ `fields`.** Cạnh *Sửa nội dung* cho đặt tiêu
đề, mô tả, loại yêu cầu, nên bảng thao tác của người gửi hiện ba ô điền sẵn nội dung đang
có — cùng một thành phần ô nhập với buồng lái. Đọc biểu mẫu theo đúng loại ô đã vẽ
(`frontend/lib/bieu-mau.ts`): ô chọn để trống nghĩa là chưa chọn, nên bỏ qua; ô chữ để trống
nghĩa là xóa, nên gửi `null`. Loại ô tra từ cùng bảng `truong.ts` quyết định vẽ ô chọn hay
ô chữ, nên cách đọc không lệch được với cách vẽ.

**Hai loại quyền, không trộn.** Buồng lái gác bằng vai trò ở cửa — `require_roles` trong
`backend/app/workflow/coordination.py` — nhưng đó là quyền **nhìn thấy hồ sơ**, không phải
quyền đi cạnh. Cạnh nào đi được vẫn do engine quyết qua `transition_roles`. Chú thích của
`require_roles` cấm dùng nó để kiểm quyền chuyển trạng thái, vì hai nguồn quyền sẽ lệch
nhau. Cửa nhìn thấy gác luôn điểm cuối chuyển trạng thái, để người không có quyền dò số
định danh không đọc được từ mã lỗi của engine rằng hồ sơ nào có thật.

Giao diện cũng không chứa tên vai trò nào. `/me` trả danh sách `workspaces` do dịch vụ
tính, và thanh điều hướng dựng theo danh sách đó.

**Từ #158, khung ứng dụng là thanh bên.** `frontend/components/khung-lam-viec.tsx` (máy chủ)
lấy `/me`, dựng mục theo `workspaces` qua `lib/khong-gian.ts` — mỗi mục mang icon và nhóm
ngay trong dữ liệu đó — rồi đếm hồ sơ còn mở cho từng mục bằng **chính điểm cuối trang của
mục dùng** (`/requests` bỏ trạng thái `is_terminal`, `/coordination/queue`, `/department/queue`
bỏ nhóm chỉ theo dõi). Không có điểm cuối đếm riêng, nên dịch vụ không đổi; một điểm cuối
lỗi thì mục đó mất số, trang vẫn hiện. `components/khung-ung-dung.tsx` (trình duyệt) giữ
phần thuộc về trình duyệt: ngăn kéo dưới 768px, tiêu đề thanh đầu trang và nút sáng/tối.
Lựa chọn sáng/tối lưu ở `localStorage` khóa `dxlab-theme`; một đoạn mã trong `<head>` của
`app/layout.tsx` đặt `data-theme` trước khi trang vẽ để không nháy màu, chưa chọn thì vẫn
theo hệ điều hành. Token màu, chuyển động (150–300 ms, tắt khi máy bật giảm chuyển động) và
kiểu khung nằm trong `app/globals.css`.

**Từ #84, ai giao việc và ai nhận việc cũng suy từ dữ liệu.** Điểm cuối
`GET /departments/{mã}/assignees` — nguồn của ô chọn người xử lý — không chứa tên vai trò
nào. Người giao việc là vai trò đi được một cạnh cho đặt `assignee_id`, tức cạnh mang ràng
buộc quản trường đó. Người nhận việc là vai trò đi được cạnh người ra khỏi trạng thái mà
hồ sơ tới sau khi được giao. Với bộ quy tắc hiện tại, hai tập đó là trưởng phòng và người
xử lý; gỡ ràng buộc `assign-handler` khỏi mọi cạnh thì không ai mở được danh sách nữa, và
có bài kiểm thử cho đúng điều đó. Trưởng phòng chỉ xem được người của phòng mình. Buồng
lái phòng ban (#83) mở cho đúng hai tập đó, và hàng đợi của nó là những trạng thái mà hai
vai có cạnh đi ra — cũng không có tên vai trò hay tên trạng thái nào trong mã. Từ #99,
hàng đợi có thêm nhóm **chỉ để theo dõi**: trạng thái mà cạnh của phòng ban dẫn tới và
từ đó có đường quay về hàng đợi — hiện là *Chờ bổ sung thông tin* và *Hoàn tất*. Thiếu
nhóm này thì người xử lý hỏi thêm xong là hồ sơ biến khỏi hàng đợi của họ.

**Từ #83, người được giao phải đi qua danh bạ.** `assignee_id` là trường quyết định duy
nhất có danh mục nằm ngoài cơ sở dữ liệu — trong Keycloak. Engine không gọi ra ngoài, nên
phép kiểm nằm ở tầng điểm cuối: `kiem_nguoi_duoc_giao` trong
`backend/app/workflow/assignment.py`, và **mọi** điểm cuối nhận `changes` đều gọi nó —
kể cả cửa điều phối, vì một người có thể mang cùng lúc vai trò điều phối và vai trò giao
việc. Phép kiểm chỉ tra danh bạ khi chắc lần chuyển sẽ tới bước đặt người, và người gọi
thuộc phòng đang giữ hồ sơ; thiếu điều kiện nào thì nhường engine báo lỗi của nó, để lỗi
503 của danh bạ không che mất lỗi 403 thật, và để người phòng khác không dò được ai thuộc
phòng nào. Tên người được giao lấy từ danh bạ chứ không từ trình duyệt, ghi vào
`requests.assignee_label` cùng lúc với định danh — cùng khuôn với `requester_label` và
`actor_label`. Danh bạ không trả lời thì không giao được người, nhưng vẫn nhận được hồ
sơ: người xử lý là tùy chọn, và cả phòng vẫn thấy hồ sơ đó.

**Khung lời nhắn (#128) cùng khuôn với bảng thao tác.** Nút dựng từ `message_kinds` mà
dịch vụ trả kèm chi tiết hồ sơ, như nút chuyển trạng thái dựng từ `allowed_transitions`.
Không có bảng "vai trò nào gửi được loại nào" hay "trạng thái nào được hỏi tiến độ" trong
TypeScript. Loại không cần nội dung thì nút của nó bỏ qua phép kiểm của trình duyệt
(`formNoValidate`), nên "Hỏi tiến độ" bấm là gửi được ngay. Khung nằm dưới dòng thời gian
chứ không ở cột thao tác: cột đó dính khi cuộn, thêm thẻ là cao quá màn hình.

**Từ #169, trang hồ sơ phía nhân viên tách mốc và lời nhắn thành hai thẻ.** Thẻ "Dòng
thời gian" chỉ còn các mốc đổi hồ sơ; thẻ "Trao đổi" hiện lời nhắn dạng hội thoại
(`components/khung-chat.tsx`) với ô soạn kiểu chat của cùng khung lời nhắn — cùng dữ liệu,
cùng điểm cuối, chỉ khác cách trình bày; trang người gửi tách theo ở #189. Thanh "hồ sơ
đang ở đâu" suy từ dữ liệu (`lib/buoc.ts`): đường chính là các trạng thái theo
`display_order`, tính tới và gồm trạng thái kết thúc đầu tiên; hồ sơ ở trạng thái nhánh thì
thanh dừng ở bước đường chính cuối cùng nó đã vào. Đổi đường chính là đổi thứ tự trong dữ
liệu khởi tạo, không sửa mã. Thẻ hạn phân ba mức trong hạn, sắp hết hạn, quá hạn theo cờ
dịch vụ trả — ngưỡng "sắp hạn" nằm trong dữ liệu (mục 7.1, #175), giao diện không tự đặt.

**Khung trao đổi chia phía theo người viết (#274).** Bên phải chỉ là lời nhắn của chính người
đang xem (cờ `mine` dịch vụ trả kèm mỗi lời nhắn), ở cả cuộc với người gửi lẫn cuộc nội bộ, ở
cả hộp thư lẫn thẻ Trao đổi. Trước đó cuộc với người gửi chia theo phe nhân viên / người gửi,
nên tin của đồng nghiệp nằm bên phải như tin của mình. Tin người khác ghi tên kèm "Người gửi hồ
sơ" hay "Nhân viên"; tin của người gửi mang nền nhấn nhạt để nhân viên phân biệt với đồng
nghiệp. Lời nhắn không lưu vai trò của người viết, nên chưa ghi được "điều phối viên" hay
"trưởng phòng" trên từng tin.

**Bề rộng nội dung (#275).** Vùng nội dung (`.vung`) rộng tối đa 1240 px và căn giữa phần còn
lại sau thanh bên; màn có bảng hàng đợi nhiều cột được 1440 px; hộp thư giãn trọn chiều ngang.
Màn hình rộng vì vậy không còn một khoảng trống lớn ở một phía.

**Từ #189, trang hồ sơ đặt việc của người dùng trước nhật ký** (nhận xét của giảng viên
11/10/2026). Ba điều, áp cho cả trang nhân viên lẫn trang người gửi:

- **Dòng thời gian mặc định thu gọn**, chỉ còn bước hiện tại — mốc đổi trạng thái mới nhất;
  nút *Xem toàn bộ N mốc* mở đủ. Cả hai khối dựng sẵn ở máy chủ, CSS ẩn hiện theo thuộc tính
  `data-dong-thoi-gian` trên `<html>` (`components/nut-dong-thoi-gian.tsx`). Lựa chọn nhớ trong
  `localStorage` và được đoạn mã đầu trang (`app/layout.tsx`, cùng chỗ đọc chế độ sáng/tối) đặt
  trước khi trình duyệt vẽ, nên không nháy. Bản in luôn đủ mốc
- **Màn hẹp dưới 1100 px**: cột phải tan vào lưới (`display: contents`), thẻ *Hạn xử lý* và
  *Bạn có thể làm gì* lên ngay dưới tiêu đề, cột đọc (`.cot-doc`) theo sau — chỉ đổi thứ tự
  bằng CSS
- **Trang người gửi**: khối thao tác lên ngay dưới phần đầu hồ sơ; lời nhắn tách khỏi dòng thời
  gian thành khung trò chuyện riêng như thẻ Trao đổi phía nhân viên, để thu gọn nhật ký không
  giấu mất tin nhắn. Trên điện thoại, chữ giải thích phụ và số liệu nhật ký (`.an-tren-hep`)
  nhường chỗ để nút thao tác nằm trong màn hình đầu

**Từ #192, "Hồ sơ của tôi" trả lời "hồ sơ đang ở đâu" ngay trên dòng của nó**, thay cho bảng
giải thích mười trạng thái từng nằm cuối trang. Nhãn trạng thái của mỗi dòng là một nút
(`components/xem-nhanh-trang-thai.tsx`): rê chuột, Tab tới hay chạm vào thì hiện sơ đồ nhỏ —
thanh chấm của đường chính suy bằng chính `lib/buoc.ts` ở trên, câu *Bước x/y*, và một dòng
*Đang dừng ở…* khi hồ sơ ở trạng thái nhánh (vế "chờ bạn trả lời" lấy từ nhóm trình bày trong
`lib/trang-thai.ts`, không từ tên trạng thái). Ba quy ước đi kèm:

- **Dòng không còn là một thẻ `<a>`**: nút bên trong liên kết là HTML sai, nên dòng dùng liên kết
  trong suốt phủ kín dòng như bảng hàng đợi (`.lk-dong`), nút nhãn nằm trên liên kết
- **Lịch sử chỉ tải cho hồ sơ cần nó**: danh sách `/requests` không có lịch sử, nên trang gọi thêm
  `/requests/{id}` — điểm cuối có sẵn — cho riêng các hồ sơ đang ở trạng thái nhánh chưa kết
  thúc. Trạng thái kết thúc ngoài đường chính (đã hủy) chỉ có dòng chữ, không tô bước, để hồ sơ
  cũ dồn lên theo thời gian không kéo theo số lời gọi
- **Sơ đồ gắn vào `<body>` và đặt `fixed` theo nút**: thẻ danh sách cắt phần tràn, và khung nội
  dung có hiệu ứng hiện trang mang `transform` — đặt trong dòng thì sơ đồ bị cắt hoặc lệch. Mở
  bằng rê thì sơ đồ là tooltip: chuột đi xuyên qua nó (nó phủ lên nhãn của dòng dưới), rời nhãn
  hay cuộn trang là đóng. Bấm/chạm thì ghim: sơ đồ nhận chạm và bám theo nút khi cuộn. Chạm ra
  ngoài hay Esc thì đóng; mỗi lúc chỉ một sơ đồ mở

**Từ #170, hai hàng đợi dùng chung một bảng** (`components/bang-hang-doi.tsx`). Trang ở máy
chủ chia nhóm và dịch mỗi hồ sơ thành một dòng; bảng lo hàng công cụ và thu gọn nhóm. Hàng đợi
phòng ban chia nhóm theo mức gấp: Quá hạn, Sắp hết hạn (#175), Trong hạn (đồng hồ đang chạy),
mỗi trạng thái đồng hồ chưa chạy một nhóm mang nhãn trong dữ liệu, cuối cùng nhóm chỉ để theo
dõi (`watch_only`) — từ #232 dịch vụ chia (`urgency_groups`, `urgency` trên từng dòng). Hàng đợi
điều phối lọc bằng hàng tab dựng từ `groups`. Không tệp nào liệt kê tên trạng thái.

**Từ #232, mọi danh sách có phân trang, và tìm, lọc, xếp đều ở dịch vụ.** Bốn điểm cuối —
`GET /requests`, `/coordination/queue`, `/department/queue`, `/inbox` — nhận `limit` (mặc định
50, trần 200, `backend/app/workflow/phan_trang.py`), `offset`, `q` và bộ lọc riêng (loại yêu cầu,
mức ưu tiên, phòng, trạng thái, nhóm), trả kèm `total`. Không điểm cuối danh sách nào trả cả tập
khi người gọi không nói gì. Ba quy ước:

- **Số đếm nhóm tính trên cả tập đã lọc, trước khi lọc nhóm và cắt trang**: số trên dải lọc, chip
  hộp thư không đổi khi sang trang hay khi đang đứng ở một nhóm. Kèm `waiting_me` và `urgent` cho
  thanh bên và trang chủ — hai chỗ này gọi `limit=1` để lấy số, và trang chủ gọi thêm
  `needs_action=true` để lấy đúng các việc chờ, không tải cả danh sách để đếm — tối đa 200 việc mỗi vai;
  vượt trần thì dưới danh sách ghi "Đang hiện 200 trên 204 việc" kèm đường sang hàng đợi (#237)
- **Hai cách cắt trang theo hình dạng dữ liệu**: `/requests` và `/inbox` phình theo lịch sử (mọi
  hồ sơ từng gửi, từng nhắn), nên lọc, đếm, cắt trang trong SQL; hộp thư lấy lời nhắn cuối của
  mọi cuộc bằng một truy vấn gom nhóm. Hai hàng đợi chỉ gồm hồ sơ đang mở, lớn theo khối việc chứ
  không theo lịch sử, nên lọc và tính cờ hạn trên cả hàng đợi rồi mới cắt; tóm tắt đầy đủ — phần
  tốn nhất — chỉ dựng cho dòng của trang. Cờ hạn cả hàng đợi tính gọn: giờ làm việc đã nằm ở trạng
  thái tính ngay trong câu truy vấn hàng đợi (`han_cho.giay_da_o_trang_thai`), cạnh tự đi tra một
  lần (`canh_tu_di_theo_trang_thai`), và danh mục loại, mức ưu tiên, trạng thái được giữ tham chiếu
  suốt lời gọi (`routes._giu_danh_muc`) — bản đồ định danh của phiên chỉ giữ tham chiếu yếu, không
  giữ thì mỗi hồ sơ lại hỏi cơ sở dữ liệu một lần. Hàng đợi phòng ban xếp theo thứ tự nhóm trước
  rồi mới theo cách xếp đã chọn, để trang sau nối tiếp đúng nhóm trang trước
- **Tìm không phân biệt dấu ở cả hai phía**: SQL bỏ dấu bằng `translate` có sẵn của PostgreSQL
  (không cần phần mở rộng), Python bằng `unicodedata` — một bài kiểm thử giữ hai bảng khớp nhau

Giao diện đặt trang, ô tìm, bộ lọc và cách xếp lên địa chỉ trang (`?trang=`, `?q=`, `?xep=`,
`?loai=`, `?uu-tien=`, …; `lib/trang.ts`, `components/loc-url.tsx`): tải lại, bấm lùi hay gửi
đường dẫn đều giữ nguyên. Đổi bộ lọc thì về trang đầu; trang vượt trang cuối thì chuyển sang
trang cuối. Bộ lọc đang bật hiện thành chip bỏ được, từ hai chip có "Xóa tất cả"; dòng chân ghi
"Đang xem 51–100 trên 230 hồ sơ · xếp theo …" kèm trang trước, trang sau.

Đo trên cụm thử (gọi trong tiến trình, trung vị 7 lần, hàng đợi điều phối 271 hồ sơ, phòng ban
250): với 3.001 rồi 6.001 hồ sơ — phần lớn đã hủy — `GET /requests` từ 5,6 giây và 9,1 giây xuống
0,22 giây và 0,08 giây; hàng đợi điều phối từ khoảng 1,1 giây xuống 0,09 giây ở cả hai mức; hàng
đợi phòng ban từ khoảng 1,7 giây xuống 0,44–0,48 giây. Gấp đôi lịch sử, thời gian hàng đợi không
tăng.

**Từ #233, bấm một dòng hàng đợi mở ngăn xem nhanh bên phải** thay vì rời danh sách. Hồ sơ đang
xem nằm trên địa chỉ trang (`?xem=<mã>`, hay `dau`/`cuoi` khi nút trước/sau sang trang kế), nên
ngăn gửi đường dẫn được; trang chi tiết đầy đủ vẫn mở thẳng như cũ. Ba quy ước:

- **Không nhân đôi logic**: nạp dữ liệu, hàng thông tin và khối thao tác của một hồ sơ nằm ở
  `app/dieu-phoi/ho-so.tsx` và `app/phong-ban/ho-so.tsx`, trang chi tiết và ngăn cùng gọi; nội dung
  ngăn (`components/ngan-ho-so.tsx`) ghép đúng các khối của trang chi tiết
- **Nút chính dựng từ dữ liệu**: mỗi cạnh trong `allowed_transitions` mang `is_primary` — dịch vụ
  đánh dấu bằng `my_primary_steps()`, cùng nguồn với cờ `needs_my_action` (mục 7.3). Ở đáy ngăn,
  bước chính thành nút chính, các thao tác còn lại vào menu; gửi xong thì ngăn sang hồ sơ kế
- **Bàn phím và tiêu điểm** (`components/khung-ngan.tsx`): mở ngăn thì tiêu điểm vào tiêu đề hồ sơ,
  mũi tên sang hồ sơ trước/sau theo thứ tự danh sách ("2 trên 14"), Esc đóng và trả tiêu điểm về
  đúng dòng — trừ khi đang gõ trong ô nhập hay một menu đã nhận phím đó. Ngăn gắn thẳng vào
  `<body>`: khung nội dung mang `transform` của hiệu ứng hiện trang, `position: fixed` bên trong nó
  tính theo khung đó chứ không theo cửa sổ. Màn hẹp: ngăn chiếm toàn màn hình

**Từ #155, hộp thư chung gom lời nhắn theo người** (`backend/app/workflow/inbox.py`,
`frontend/app/hop-thu/`). Không có kho tin nhắn thứ hai: mỗi cuộc trò chuyện là lời nhắn
`case_messages` của một hồ sơ. Hộp thư không viết lại cửa nhìn thấy — một hồ sơ vào hộp
thư khi người đó mở được nó qua cổng người gửi, buồng lái phòng ban hay điều phối, rồi thu
hẹp theo việc đang giữ (điều phối viên chỉ thấy hồ sơ ở hàng đợi điều phối và hồ sơ mình đã
nhắn). Dịch vụ trả kèm `workspace` cho từng cuộc; giao diện đọc chi tiết và gửi lời nhắn qua
đúng điểm cuối, đúng Server Action của cửa đó, nên luật của #128 chỉ có một nơi. Mốc đã đọc
nằm ở bảng `case_message_reads` (migration 0008, không cần `down -v`), chỉ dời lên, ghi từ
trình duyệt khi lời nhắn thật sự đang hiện — không ghi lúc dựng trang, để tải trước không
đánh dấu nhầm. Trang hộp thư tự tải lại khoảng 12 giây một lần bằng `router.refresh()`;
thanh bên hỏi riêng con số qua `app/api/hop-thu/chua-doc` — không thêm dịch vụ nào vào
Compose.

**Từ #387, cổng nhận tín hiệu thời gian thực** (`backend/app/thoi_gian_thuc.py`,
`frontend/app/api/su-kien/`, `frontend/components/nghe-thay-doi.tsx`). Bản sửa 0030 đặt trigger
`pg_notify('ho_so_thay_doi', <mã hồ sơ>)` sau mỗi lần tạo hay sửa dòng `requests` và mỗi lời nhắn
mới — mã ghi hồ sơ, cửa chuyển trạng thái và `event_log` không đổi. `GET /me/stream` trả
Server-Sent Events: mỗi luồng `LISTEN` trên một kết nối bất đồng bộ riêng của psycopg, lọc mã hồ sơ
bằng đúng luật cửa của hộp thư (`_Cua.noi_mo`) rồi mới đẩy `event: ho-so` chỉ mang `case_id` — người
không mở được hồ sơ không biết nó vừa đổi. Luồng gửi dòng giữ kết nối mỗi
`DXLAB_REALTIME_KEEPALIVE_SECONDS` (15 giây, dưới hạn chờ đọc của cổng API), tự đóng sau
`DXLAB_REALTIME_MAX_STREAM_SECONDS` (240 giây) để trình duyệt nối lại bằng token mới, và có trần
`DXLAB_REALTIME_MAX_STREAMS` (40) vì mỗi luồng giữ một kết nối PostgreSQL — quá trần trả 503. Phản hồi
mang `X-Accel-Buffering: no` nên APISIX không gom vào bộ đệm; cổng API không thêm tuyến nào. Máy chủ
Next.js chuyển tiếp luồng ở `/api/su-kien` (token vẫn ở máy chủ, dịch vụ từ chối thì trả 204 để
trình duyệt thôi nối lại); khung ứng dụng nhận tín hiệu thì gộp trong 300 ms rồi `router.refresh()`
và báo thanh bên hỏi lại số chưa đọc. Hỏi định kỳ 12 giây giữ nguyên làm đường dự phòng.

**Từ #156, mỗi hồ sơ có hai cuộc trò chuyện.** Hộp thư trả mỗi cặp (hồ sơ, kênh) thành một
cuộc với cờ `internal`; mốc đã đọc thêm cột `internal` vào khóa chính (migration 0009), nên
đọc cuộc này không làm cuộc kia thành đã đọc. Địa chỉ `?ho-so=<id>&kenh=noi-bo` mở cuộc nội
bộ; nút chuyển ở đầu khung chat mở được cả cuộc chưa có tin, để bắt đầu nhắn nội bộ ngay từ
hộp thư. Trang hồ sơ phía nhân viên có thẻ thứ ba "Nội bộ" khi dịch vụ trả `sees_internal`.
Giao diện chỉ chia `messages` và `message_kinds` theo cờ `internal` dịch vụ đã gắn, không
biết mã loại nào là nội bộ; cuộc nội bộ có nền vàng nhạt viền đứt để không nhắn nhầm cho
người gửi.

### 7.3. Bước chính và cờ "cần tôi xử lý"

**Đã cài đặt** — #227.

"Bấm được" không đồng nghĩa "đang chờ tôi". Người gửi sửa hay hủy được hồ sơ ở *Đã gửi*, *Đã
phân loại*, *Chờ phòng ban xác duyệt*, nhưng lúc đó hồ sơ chờ điều phối viên hay phòng ban.
Suy cờ từ `allowed_transitions` sẽ báo mọi hồ sơ vừa gửi là "cần bạn xử lý".

Nên mỗi trạng thái khai **bước chính** của nó trong dữ liệu, bằng cột `transitions.primary_scope`:

| Giá trị | Nghĩa | Cạnh trong bộ quy tắc mẫu |
|---|---|---|
| `NULL` | Không phải bước chính: bấm được nhưng hồ sơ không chờ người này | sửa nội dung, hủy, gia hạn, hỏi thêm, rút về, nhận việc, từ chối, mở lại |
| `role` | Hồ sơ chờ mọi người có vai đi được cạnh | phân loại, chuyển về phòng ban, xác duyệt, chuyển lại phòng khác, phân công lại, bổ sung thông tin, xác nhận đạt |
| `assignee` | Hồ sơ chờ người đang được giao; chưa giao ai thì như `role` | hoàn thành xử lý |

`needs_my_action()` trong `backend/app/workflow/engine.py` tính cờ cho cả một danh sách: đúng khi
có một cạnh bước chính rời trạng thái hiện tại mà người xem qua được hai lớp kiểm như
`allowed_transitions` — vai trò và ràng buộc không cần nhập liệu (mục 7) — cộng điều kiện người
được giao với cạnh `assignee`. Nhờ đi qua ràng buộc, điều phối viên không thấy cờ trên hồ sơ chính
mình gửi (#154), trưởng phòng không thấy cờ trên hồ sơ của phòng khác. Cờ có trên ba danh sách:
`GET /requests`, hàng đợi điều phối, hàng đợi phòng ban; trang chi tiết trả `null`, vì ở đó nút
bấm đã dựng từ `allowed_transitions`.

Số truy vấn không tăng theo số dòng: một lần tải cạnh bước chính (kèm vai trò và ràng buộc), một lần
đọc trạng thái trước cho mọi hồ sơ bằng `DISTINCT ON`. Hệ quả cho người viết dữ liệu: ràng buộc gắn
trên cạnh bước chính nên là loại không tự truy vấn, không thì mỗi dòng thêm một truy vấn.

CHECK `transitions_buoc_chinh_hop_le` cấm khai bước chính cho cạnh hệ thống: không ai "phải bấm"
cạnh hệ thống tự đi. Đổi bước chính của một trạng thái là sửa dữ liệu khởi tạo, không sửa mã — có
bài kiểm thử đổi cột ngay trong giao dịch và thấy cờ đổi theo.

**Trang chủ theo việc cần làm (#228, #230).** `my_primary_steps()` trả luôn cạnh bước chính, nên mỗi
dòng danh sách còn có `next_step_label` — chữ trên nút của dòng việc ("Phân loại yêu cầu →"). Trang chủ
gộp hồ sơ có cờ từ mọi vai người xem có (người gửi, điều phối, phòng ban) thành một khối "Cần bạn xử
lý"; tổng quan thì tách theo vai. Nút trên dòng mở trang hồ sơ ở khối `#thao-tac`, không đi cạnh ngay
trên trang chủ: bước chính thường cần nhập thêm (mức ưu tiên, người xử lý, lý do), và bảng thao tác
dựng từ `allowed_transitions` vẫn là chỗ duy nhất gửi lệnh chuyển. Quy tắc xếp mặc định **độ gấp**: quá
hạn trước, rồi sắp hạn hay sắp bị hệ thống tự đi (`sla_due_soon`, `auto_transition.warn`), rồi chờ lâu
nhất; người dùng đổi được sang hạn gần nhất, chờ lâu nhất, mới nhất — trình duyệt nhớ lựa chọn.
Thanh bên đếm cùng cờ đó: số đặc là việc chờ mình, số mờ là hồ sơ đang mở, chấm đỏ khi có việc chờ
mình đã quá hạn hoặc sắp tự đi. Từ #232 cả hai đọc số từ `waiting_me`, `urgent`, `total`,
`open_count` mà dịch vụ đếm trên cả danh sách (mục 7.2).

### 7.3a. Ủy quyền khi vắng mặt

**Đã cài đặt** — #252 (`backend/app/workflow/uy_quyen.py`, `uy_quyen_routes.py`, migration `0026`, màn
`/uy-quyen`). Navigator chốt 13/11/2026 theo đề xuất của nhóm, giảng viên đồng ý làm trước thi.

| Câu | Chốt |
|---|---|
| Ai được ủy quyền | Người cùng phòng; mang vai của người vắng, chỉ trong phòng đó |
| Ai khai | Người vắng tự khai; người giao việc của phòng (trưởng phòng) khai thay cho người không mang vai giao việc |
| Xác nhận | Không; trang chủ người làm thay hiện dải báo (`/me` trả `acting_for`) |
| Chuyển tiếp | Không: chỉ vai RIÊNG của người vắng — vai trong token, hay vai trong danh bạ khi khai thay |
| Hiệu lực | Theo ngày: [00:00 ngày đầu, 00:00 ngày sau ngày cuối) theo múi giờ lịch mặc định, lưu UTC; tối đa `delegation_max_days` |

**Gắn ở định danh, kiểm ở cửa chuyển trạng thái.** `current_actor` gọi `ap_uy_quyen` ở mọi yêu cầu: ủy quyền
đang hiệu lực (đồng hồ của cơ sở dữ liệu) được gộp vào `Actor.roles`, còn vai trong token giữ ở
`Actor.vai_goc`. Nhờ gộp vai, hàng đợi, nút bấm, danh sách người nhận việc, báo cáo thấy người làm thay
"như vai tương ứng" mà không chỗ nào phải biết ủy quyền. Ba điều gộp vai không nói được thì
`perform_transition` tự kiểm ngay sau bước kiểm vai (`_lam_thay_cho`): bước chỉ đi được nhờ vai làm thay phải
đúng phòng được ủy quyền, không phải hồ sơ do chính người bấm gửi (cùng tinh thần `actor-not-requester`,
#154), và nhật ký ghi người vắng ở `event_log.on_behalf_of` / `on_behalf_of_label` — `actor` vẫn là người
thật bấm. Bước đi được bằng vai riêng thì không ghi "thay mặt". Bước chính kiểu `assignee` (#227) tính cả
hồ sơ giao cho người vắng là việc của người làm thay.

Tính lại ở mỗi yêu cầu nên hết hạn hay thu hồi là mất quyền ngay ở lần bấm kế tiếp — không phiên nào giữ
quyền cũ. Thu hồi điền `revoked_*`, không xóa dòng. Phương án loại: thêm vai vào Keycloak trong khoảng ngày
(phải có tác vụ hẹn giờ gỡ vai, và token cũ còn giữ vai tới khi hết hạn); kiểm ủy quyền riêng ở từng điểm
cuối (hai nguồn sự thật về quyền, dễ lệch).

**Kiểm chứng.** `tests/test_uy_quyen.py` (21 bài): ngoài khoảng, thu hồi, khác phòng thì không có gì; làm thay
trưởng phòng ghi "thay mặt", dùng vai riêng thì không; hết hạn mất quyền ngay; không duyệt hồ sơ mình gửi;
việc của người xử lý vắng vào việc chờ của người làm thay; không chuyển tiếp; các lần khai sai. Bốn phép đột
biến (bỏ chặn hồ sơ tự gửi, bỏ ghi "thay mặt", bỏ việc chờ của người vắng, bỏ điều kiện hết hạn) đều làm bài
đỏ. `e2e/` có bài trưởng phòng khai, người xử lý thấy dải báo, thu hồi là mất.

### 7.4. Lớp biên: cổng API, tiêu đề bảo mật, giới hạn tốc độ và `/health`

**Đã cài đặt** — cổng API ở #364 (ADR-0010), lớp trong dịch vụ và cổng người dùng ở #243. Biên có
**hai lớp**: cổng API đứng trước dịch vụ ứng dụng, chặn lời gọi không hợp lệ trước khi chúng tới dịch
vụ; dịch vụ và cổng người dùng vẫn tự giữ phần của mình như trước, không lớp nào tin lớp kia thay mình.
Cùng một nguyên tắc cho cả hai: chặt vừa đủ để giao diện vẫn chạy, và thứ gì lộ ra cho người chưa đăng
nhập thì chỉ là thứ không có hại khi lộ.

#### Ai mở cổng nào ra máy

```
Trình duyệt ──► frontend :3000 ──(X-Real-IP)──► cong-api :9081 (chỉ trong mạng Compose) ─┐
                                                                                         ├─► kiểm token ─► giới hạn ─► backend :8000
Bên gọi API ngoài cụm ─────────────────────────► cong-api :9080 = GATEWAY_PORT ──────────┘
                                                      │ tài liệu discovery + bộ khóa công khai
                                                      └──────────────► keycloak :8080 (địa chỉ nội bộ)
```

| Dịch vụ | Cổng trên máy (biến) | Vì sao |
|---|---|---|
| `cong-api` | `9080` (`GATEWAY_PORT`) | **Cửa vào duy nhất của API**, kể cả tài liệu `/docs` |
| `frontend` | `3000` (`FRONTEND_PORT`) | Giao diện người dùng |
| `keycloak`, `superset`, `seaweedfs` | `8080`, `8088`, `8333` | Giao diện của nền tảng (trang đăng nhập, khung bảng điều khiển nhúng, S3) — giữ như trước |
| `kho-tri-thuc`, `thu-thu` *(tùy chọn)* | `3100`, `8025` | Giao diện của nền tảng, chỉ khi bật hồ sơ |
| `backend`, `postgres` | **không** | Chỉ nghe trong mạng Compose. Người phát triển mở lại `8000`, `5432` bằng tệp thứ hai `infra/docker-compose.phat-trien.yml`; kịch bản trong `scripts/` đi qua `docker exec` |
| `khai-pha`, `mo-hinh`, `mo-hinh-nhung`, `quet-tep` | không | Như trước: chỉ dịch vụ ứng dụng gọi trong mạng |

#### Lớp 1 — cổng API

Apache APISIX `3.20.0`, ảnh chính thức nguyên bản, chế độ **standalone**: hai tệp trong `infra/cong-api/`
gắn chỉ đọc — `config.yaml` (tiến trình: một tiến trình làm việc, tắt API quản trị, chỉ nạp ba plugin) và
`apisix.yaml` (tuyến, plugin). Không etcd; sửa `apisix.yaml` là APISIX tự nạp lại. Mọi con số chính sách
là biến môi trường (`GATEWAY_*`, mặc định ở `docker-compose.yml` và `infra/.env.example`). Mọi đường được
chuyển tới `backend:8000` **giữ nguyên đường dẫn**; API của nền tảng lõi nằm dưới `/core/v1` (#365, mục 2.3)
và đi qua đúng tuyến cần token như mọi đường không công khai — không tuyến riêng.

**Đường nào cần token.** Tuyến `cong-khai` khớp *đúng* từng đường (không dấu sao), chỉ `GET`/`HEAD`; mọi
đường và phương thức khác rơi xuống tuyến `can-token`. Danh sách công khai lấy từ OpenAPI của dịch vụ: các
điểm cuối không khai `security` cộng tài liệu tự sinh của FastAPI. Thêm đường công khai mới ở dịch vụ thì
thêm vào cả `apisix.yaml` lẫn bảng này.

| Đường | Tại cổng API | Tại dịch vụ ứng dụng |
|---|---|---|
| `/`, `/health`, `/health/live`, `/health/ready` (GET, HEAD) | Công khai | Công khai; `/health*` chỉ trả trạng thái chung (dưới) |
| `/docs`, `/docs/oauth2-redirect`, `/redoc`, `/openapi.json` (GET, HEAD) | Công khai | Công khai (tài liệu tự sinh) |
| `/metrics`, `/system/health`, `/sla/scan`, `/archive/scan` | Cần token | Cần vai `administrator` — chính sách #247 giữ nguyên |
| `/core/v1/*` — API của nền tảng lõi (mục 2.3) | Cần token, kể cả đường lõi chưa có | Như đường cũ tương ứng: cùng hàm, cùng phụ thuộc |
| Mọi đường khác, và đường công khai với phương thức khác (`POST /health`) | Cần token | Cần token; phân quyền theo vai trò và phạm vi như cũ |

**Cổng trả gì.** Đo thật với Keycloak của cụm (`backend/tests/test_cong_api.py`):

| Lời gọi | Cổng API trả | Tới dịch vụ? |
|---|---|---|
| Không token | `401`, `WWW-Authenticate: Bearer realm="dx-os-lab"` | Không |
| Token ký bằng khóa lạ — kể cả mạo đúng `kid` của Keycloak — hay `alg: none` | `401`, `error="invalid_token"` | Không |
| Token hết hạn (quá `GATEWAY_TOKEN_LEEWAY_SECONDS`, cùng 10 giây như dịch vụ) | `401`, `error="invalid_token"` | Không |
| Token thật của Keycloak nhưng phát cho client khác (`aud` không có `dx-api`) | `403`, `{"error":"mismatched audience"}` | Không |
| Token đúng | Chuyển tiếp nguyên tiêu đề `Authorization`, không thêm tiêu đề phụ | Có — dịch vụ kiểm lại đủ chữ ký, hạn, nơi phát, người nhận (`backend/app/auth/tokens.py` không nới) |
| Vượt ngưỡng tốc độ | `429`, `{"error_msg": …}`, `X-RateLimit-Remaining: 0` | Không |

Cách kiểm: plugin `openid-connect` (`bearer_only`, `use_jwks`, chỉ RS256, `claim_validator.audience` khớp
client `dx-api`) đọc tài liệu discovery qua địa chỉ **nội bộ** `keycloak:8080`. Lo ngại `iss` theo địa chỉ
công khai trong khi cổng gọi địa chỉ nội bộ đã đo thật: tài liệu discovery trả `issuer` theo `KC_HOSTNAME`
— đúng `iss` của token — nên khớp; `jwks_uri` trả địa chỉ nội bộ nhờ `KC_HOSTNAME_BACKCHANNEL_DYNAMIC` (mục
3.1). Bộ khóa và tài liệu discovery giữ trong bộ nhớ của cổng, nên như dịch vụ ứng dụng, Keycloak nằm ngoài
đường đi nóng; Keycloak xoay khóa thì token mang `kid` lạ và cổng tự tải lại bộ khóa.

Đường vòng không lách được tuyến công khai: `/health/../me`, `/health/%2e%2e/me`, `/health/..%2fme`,
`/docs/../metrics`, `//me`, `/health/` đều nhận 401 tại cổng — APISIX chuẩn hóa đường dẫn trước khi chọn
tuyến và chuyển tiếp đúng đường đã chuẩn hóa.

**Khi Keycloak chưa sẵn sàng.** Cổng API cố ý không `depends_on` Keycloak. Đo thật: dừng Keycloak, khởi
động lại cổng — cổng vẫn báo khỏe sau khoảng 6 giây, đường công khai trả 200, lời gọi kèm token nhận 401
`issuer validation unavailable` (plugin từ chối khi không đối chiếu được nơi phát, không cho qua). Bật lại
Keycloak, cùng token đó qua được sau 15 giây — đúng lúc Keycloak nạp xong — mà không khởi động lại cổng.
Cụm không kẹt: cổng chờ dịch vụ ứng dụng khỏe (`service_healthy`), cổng người dùng chờ cổng API khỏe.
Healthcheck hỏi `/status/ready` (mọi tiến trình đã nạp tuyến) ở cổng trạng thái nội bộ `127.0.0.1:7085`
bằng `bash`, vì ảnh không có `curl`.

**Giới hạn tốc độ chung.** Plugin `limit-count` trong một luật toàn cục: một bộ đếm cho mọi tuyến, theo địa
chỉ người gọi, cửa sổ cố định `GATEWAY_RATE_LIMIT_WINDOW_SECONDS`, tối đa `GATEWAY_RATE_LIMIT_COUNT` lời gọi.
Đếm trong bộ nhớ dùng chung của tiến trình — một tiến trình làm việc nên đếm đúng. Chạy **sau** bước kiểm
token (APISIX chạy plugin xác thực ở pha trước pha giới hạn): lời gọi không token bị từ chối trước, không ăn
vào hạn mức của ai. Bộ đếm theo người dùng trong PostgreSQL của dịch vụ (dưới) giữ nguyên cho ba thao tác
ghi. Mặc định 3000 lời gọi mỗi 60 giây cho một địa chỉ: đủ cho một văn phòng dùng chung địa chỉ. Đo thật:
lượt e2e trọn bộ (bốn cấu hình hiển thị, 204 bài, 7,3 phút) gửi 5.816 lời gọi qua cổng, tất cả từ một địa
chỉ, đỉnh 969 lời gọi trong một phút — mặc định gấp ba đỉnh đó, và không lời gọi nào của lượt đó bị cổng từ
chối (mọi 403, 429 trong nhật ký cổng đều do dịch vụ trả).

Mọi người dùng cổng người dùng đều tới cổng API từ **một** container — đếm theo địa chỉ kết nối thì gộp hết
về một bộ đếm. Nên cổng API nghe hai cổng: `9080` (ánh xạ ra máy) đếm theo địa chỉ kết nối và **không** tin
tiêu đề nào; `9081` (không ánh xạ ra máy, chỉ container trong cụm tới được) có plugin `real-ip` đọc
`X-Real-IP` mà `frontend/lib/api.ts` gắn. Cổng người dùng lấy địa chỉ đó bằng đúng hàm `diaChiIp` của giới
hạn đăng nhập ở dưới (phần tử đầu của `X-Forwarded-For`, Next.js tự đặt từ địa chỉ kết nối khi không có), nên
chịu cùng điều kiện: chỉ đúng tuyệt đối khi cổng người dùng đứng sau reverse proxy đặt tiêu đề đó. Đo trên
cụm thử: nhật ký của cổng API ghi địa chỉ của máy gọi (`172.21.0.1`), không phải của container cổng người
dùng (`172.21.0.9`). Người ngoài gửi `X-Real-IP` giả vào `9080` không né được giới hạn — bài kiểm có bước này.
Gặp 429 của cổng API, `lib/api.ts` dịch thành câu "Bạn gửi yêu cầu quá nhanh. Thử lại sau N giây." như 429
của dịch vụ.

**Kích thước và thời gian chờ.** Trần thân yêu cầu `GATEWAY_MAX_BODY_MB` (mặc định 64) không thấp hơn một
lượt tải tệp lớn nhất dịch vụ nhận: `ATTACHMENT_MAX_FILES` × `ATTACHMENT_MAX_MB` = 5 × 10 MB cộng phần đầu
biểu mẫu — tăng hai biến kia thì tăng biến này. Chờ gửi/đọc `GATEWAY_TIMEOUT_SECONDS` (mặc định 120) không
thấp hơn lời gọi đồng bộ lâu nhất của dịch vụ (tải năm tệp kèm quét mã độc 15 giây mỗi tệp, khai phá quy
trình 30 giây); cổng người dùng vẫn tự cắt ở `BACKEND_TIMEOUT_MS`. Kết nối giữ sẵn từ cổng tới dịch vụ bị
cổng đóng sau 3 giây rỗi — phải ngắn hơn 5 giây mà uvicorn tự đóng kết nối rỗi. Lượt e2e đầu tiên chạy với
mặc định 60 giây của APISIX gặp 2 lời gọi `502` (`Connection reset by peer`) trên 5.857: cổng gửi đúng lúc
uvicorn đang đóng kết nối.

**Tài nguyên.** Một tiến trình làm việc: 51,37 MiB (`docker stats --no-stream` của container cổng API ngay
sau lượt e2e trọn bộ trên cụm thử, 15/11/2026), sát số 57 MiB đo ở bản khảo sát với bộ khóa giả lập. Ảnh
chính thức 638 MB, kéo về một lần, không dựng.

**Kiểm chứng.** `backend/tests/test_cong_api.py` (31 bài) chạy trong container dịch vụ, cùng bộ kiểm thử dịch
vụ ở CI: đường công khai mở; thiếu token, khóa lạ, `alg: none`, hết hạn, sai người nhận bị chặn; token đúng
tới dịch vụ; `/metrics` vẫn chỉ quản trị; vượt ngưỡng 429 theo từng địa chỉ. Token hết hạn là token **thật**
của Keycloak: bài tạo một client tạm phát token sống 1 giây (gỡ ngay sau bài), thấy cổng nhận nó khi còn
trong độ lệch rồi chặn khi quá. Bằng chứng "không tới dịch vụ" là mã yêu cầu: dịch vụ trả lại `X-Request-ID`
ở mọi phản hồi (mục 7.5), cổng API thì không — vì dịch vụ cũng tự trả 401 khi thiếu token, chỉ nhìn mã 401
sẽ không phân biệt được. Bốn phép đột biến trên cổng tạm dựng từ chính `apisix.yaml` đều làm bài đỏ: tắt
`openid-connect` (18 bài đỏ), tắt `limit-count`, cho `real-ip` tin cả cổng `9080`, bỏ kiểm người nhận; bản
không sửa thì xanh. Job Cụm của CI còn kiểm từ máy chủ rằng `8000` và `5432` không kết nối được, `/health`
qua cổng API trả 200, `/me` không token nhận 401 không mang mã yêu cầu.

#### Lớp 2 — trong dịch vụ và cổng người dùng

**Tiêu đề bảo mật ở cổng.** Hai nơi, chia theo việc tiêu đề có đổi theo yêu cầu hay không:

- `frontend/next.config.ts` đặt tĩnh cho mọi đường dẫn, kể cả tệp tĩnh và tuyến API:
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Strict-Transport-Security`, `Permissions-Policy` tắt camera, micro, vị trí, và `X-Frame-Options:
  DENY` cho trình duyệt cũ chưa hiểu `frame-ancestors`. Trình duyệt bỏ qua HSTS trên `http`, nên cụm
  thử ở `http://localhost` không bị ảnh hưởng.
- `frontend/proxy.ts` (Next.js 16 đổi tên `middleware.ts` thành `proxy.ts`) sinh **số dùng một lần
  mỗi yêu cầu** và đặt `Content-Security-Policy`. Số nằm cả ở header yêu cầu để Next gắn vào script
  của chính nó, và ở `x-nonce` để `app/layout.tsx` gắn vào đoạn chống nháy sáng/tối tự viết. Vì cần
  số mới mỗi lượt nên mọi trang dựng động — layout gốc đọc header nên đã vậy. Chính sách dựng ở
  `lib/bao-mat.ts`:

  ```
  default-src 'self'; script-src 'self' 'nonce-<mỗi lượt>' 'strict-dynamic'; style-src 'self'
  'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src
  <gốc công khai của Superset>; object-src 'none'; base-uri 'self'; form-action 'self' <gốc Keycloak>;
  frame-ancestors 'none'
  ```

  Chế độ phát triển thêm `'unsafe-eval'` vào `script-src` (React cần để dựng lại dấu vết lỗi) và
  `ws: wss:` vào `connect-src` (nạp nóng). `style-src` cho `'unsafe-inline'` có chủ đích: giao diện
  dùng thuộc tính `style={{…}}` của React ở rất nhiều chỗ, và CSP không cho nối số dùng một lần vào
  thuộc tính style. Rủi ro còn lại là chèn kiểu dáng, không phải chạy mã — `script-src` vẫn chặt.
  `frame-src` chỉ nhận gốc Superset (biến `SUPERSET_PUBLIC_URL` của cổng, cùng giá trị dịch vụ ứng
  dụng đã dùng ở #305); `form-action` thêm gốc Keycloak vì đăng nhập, đăng xuất chuyển hướng qua đó
  và Chrome kiểm `form-action` cả trên đích chuyển hướng.

Bài kiểm tra giao diện (`e2e/`) bắt sự kiện `securitypolicyviolation` ở mọi màn, kể cả Báo cáo nhúng
Superset: vi phạm chính sách chỉ ghi vào bảng điều khiển của trình duyệt, không ném lỗi trang, nên
chỉ nghe `pageerror` thì bỏ lọt.

**Giới hạn tốc độ.** Ngoài giới hạn chung theo địa chỉ ở cổng API (lớp 1), còn hai tầng, hai nơi đếm — vì
hai tầng có hai hoàn cảnh khác nhau:

- *Dịch vụ ứng dụng* (`backend/app/rate_limit.py`) giới hạn ba thao tác ghi: **tạo hồ sơ**, **tải tệp
  lên**, **gửi lời nhắn** (cả ba cửa của lời nhắn). Bộ đếm nằm trong **PostgreSQL**, bảng
  `rate_limit_hits(key, window_start, hits)` (migration `0017`): cửa sổ thời gian cố định, tăng bằng
  một câu `INSERT … ON CONFLICT DO UPDATE … RETURNING` nguyên tử, nên đúng khi chạy nhiều bản dịch vụ
  mà không cần khóa. Khóa đếm là `<tên giới hạn>:<định danh người dùng>`: hai người đếm riêng, và
  tạo hồ sơ nhiều không ăn vào hạn mức nhắn tin. Dùng đồng hồ của cơ sở dữ liệu nên các bản không
  lệch cửa sổ. Phụ thuộc `gioi_han_toc_do(tên)` gắn ở decorator của điểm cuối, chạy **sau** kiểm
  token (người lạ nhận 401, không tiêu hao hạn mức của ai) và **commit ngay** khi đếm xong: điểm
  cuối của dự án `rollback()` khi từ chối, nên đếm chung giao dịch thì chính những yêu cầu hỏng —
  loại lạm dụng cần chặn nhất — lại được đếm rồi bị hoàn tác. Vượt giới hạn trả `429`, header
  `Retry-After`, `detail = {code: "rate-limited", message: "Bạn gửi yêu cầu quá nhanh. Thử lại sau N
  giây."}` — cùng dạng với lỗi nghiệp vụ nên `lib/api.ts` chuyển thẳng thành thông báo cho biểu mẫu,
  không trang 500. Số lần tối đa và độ dài cửa sổ của từng giới hạn là biến môi trường
  (`RATE_LIMIT_*`, `infra/.env.example`; 0 là tắt giới hạn đó), không nằm trong hàm. Dòng đếm cũ
  được dọn trong vòng của bộ quét nền.
- *Cổng* giới hạn **đăng nhập quay về** (`/api/auth/callback`) theo địa chỉ IP ở `proxy.ts`. Cổng
  không chạm cơ sở dữ liệu nên bộ đếm nằm trong **bộ nhớ tiến trình**, và giới hạn **từng bản**:
  chạy N bản cổng thì mỗi bản đếm riêng, giới hạn thực tế lỏng hơn theo N. Chấp nhận, vì mục đích là
  chặn vòng lặp thử đổi mã ủy quyền dồn dập chứ không phải chặn tuyệt đối. Địa chỉ IP lấy từ
  `X-Forwarded-For`, nên chỉ có nghĩa khi cổng đứng sau reverse proxy đặt header đó; không có header
  thì mọi người dùng chung một bộ đếm. Vượt thì trang `429` tiếng Việt kèm `Retry-After`.

**`/health` công khai chỉ trả trạng thái chung.** `{"service": …, "status": "ok" | "degraded"}` và
mã `503` khi cơ sở dữ liệu hay lược đồ quy trình không dùng được. Không phiên bản, không tên cơ sở
dữ liệu, không câu lỗi: trước #243 nhánh lỗi trả `str(lỗi)[:200]`, mà câu lỗi của trình điều khiển có
thể mang tên máy chủ, cổng và tên tài khoản cho người chưa đăng nhập. Chi tiết lỗi **chỉ ghi vào nhật
ký** (`logging`) và hiện ở `GET /system/health`, điểm cuối chỉ quản trị viên — cùng hàm đo
(`_do_suc_khoe` trong `main.py`) với `/health`, nên hai nơi không thể kể hai chuyện khác nhau. Màn
Hệ thống (#229) đọc đúng điểm cuối này, không có đường thứ hai: phiên bản, bộ quy tắc đã nạp, nhịp
từng bộ quét (mục 7.1), và `detail` khi hỏng. Bộ quét hỏng làm `status` thành `degraded` nhưng mã
vẫn `200` — lý do ở mục 7.1.

### 7.5. Quan sát vận hành: sống, sẵn sàng, số đo, nhật ký

**Đã cài đặt** — #247. Mã ở `backend/app/quan_sat.py`, không thêm thư viện nào.

**Sống và sẵn sàng là hai câu hỏi.** `GET /health/live` chỉ trả lời "tiến trình còn chạy, vòng sự
kiện còn phục vụ" — không chạm cơ sở dữ liệu, để cơ sở dữ liệu chậm không khiến bộ điều phối giết một
tiến trình vẫn khỏe. `GET /health/ready` trả `503` khi phụ thuộc **bắt buộc** chưa dùng được — cơ sở
dữ liệu và bộ quy tắc đã nạp — cùng hàm đo với `/health` (giữ lại cho bộ giám sát và tài liệu cũ).
Dịch vụ tùy chọn (mô hình, quét mã độc, máy chủ thư, Superset) không tính: thiếu chúng thì dịch vụ vẫn
phục vụ, màn Hệ thống báo riêng. Healthcheck của ảnh dịch vụ (`backend/Dockerfile`) gọi `/health/ready`,
nên cổng và Superset chờ `service_healthy` là chờ đúng lúc dịch vụ làm được việc. Docker Compose
không tự khởi động lại container `unhealthy`, nên một healthcheck là đủ; bộ điều phối tách hai khái
niệm (Kubernetes) thì dùng `live` cho liveness, `ready` cho readiness.

**Mã yêu cầu xuyên cổng → dịch vụ.** `proxy.ts` của cổng gắn một mã mới (`x-request-id`) vào mỗi lượt
tải trang — luôn sinh mới, không nhận mã trình duyệt gửi; `lib/api.ts` gửi mã đó theo mọi lời gọi dịch
vụ trong lượt (tuyến API không đi qua proxy thì mỗi lời gọi tự sinh). Lớp giữa ASGI của dịch vụ nhận mã
nếu hợp lệ (chữ, số, `-`, `_`, `.`, tối đa 64 ký tự — chặn chèn dòng giả vào nhật ký), không thì tự
sinh, đặt vào biến ngữ cảnh và trả lại ở tiêu đề phản hồi. Lớp giữa viết thẳng bằng ASGI chứ không qua
`BaseHTTPMiddleware`, để biến ngữ cảnh tới được điểm cuối và cả luồng `to_thread`.

**Nhật ký JSON.** Mỗi dòng một đối tượng: `ts` (UTC), `level`, `logger`, `msg`, `request_id`, `exc` khi
có ngoại lệ. Bộ ghi của uvicorn gom về cùng định dạng; dòng truy cập do lớp giữa ghi (uvicorn chạy
`--no-access-log`) với `method`, `path`, `route`, `status`, `duration_ms` — trừ `/health*` bị gọi mỗi
vài giây. `LOG_FORMAT=text` trả về dạng chữ khi đọc tay.

**Số đo** ở `GET /metrics`, văn bản kiểu Prometheus viết tay: số yêu cầu theo phương thức, **mẫu đường
dẫn** (`/requests/{case_id}`, không phải `/requests/123` — số chuỗi không phình theo số hồ sơ) và mã
trạng thái; phân bố độ trễ; số lỗi 5xx; độ dài hàng đợi thư (#251); lượt quét thành công cuối và số
lượt hỏng liên tiếp của từng bộ quét. **Chỉ quản trị viên**: mẫu đường dẫn, độ dài hàng đợi là thông tin
vận hành không cho người ngoài. Từ #364 cổng dịch vụ không còn mở ra máy ở cấu hình mặc định, nhưng chính
sách không đổi — tệp phát triển mở lại cổng `8000`, và ranh giới mạng không thay được kiểm quyền. Bộ thu số
đo đi qua cổng API bằng token của một tài khoản quản trị.
Phần đếm yêu cầu nằm trong bộ nhớ của **từng bản** dịch vụ; phần đọc từ cơ sở dữ liệu là chung cả cụm.

Màn Hệ thống hiện thêm **lượt cuối** của từng bộ quét (`last_started_at` của nhịp, mục 7.1) bên cạnh lần
thành công cuối.

---

## 8. Quy ước đặt tên và mã nguồn

### 8.1. Header giấy phép

Mọi tệp mã nguồn mới **bắt buộc** bắt đầu bằng:

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
```

```typescript
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
```

Thiếu header này bị trừ 5 điểm theo bảng chấm.

### 8.2. Thư viện bên thứ ba

- Khai báo qua trình quản lý gói, kèm tệp khóa phiên bản
- **Không** sao chép mã thư viện vào kho mã
- **Không** chỉnh sửa mã thư viện bên thứ ba. Cần đổi hành vi thì dùng cấu hình,
  plugin, hoặc lớp bọc
- Tệp khóa phiên bản (`package-lock.json`, `requirements.txt` ghim bằng `==`)
  **bắt buộc commit**, không đưa vào `.gitignore`

### 8.3. Ngôn ngữ

| Nội dung | Ngôn ngữ |
|---|---|
| Tên biến, hàm, lớp, tệp | Tiếng Anh |
| Chú thích trong mã | Tiếng Việt có dấu |
| Commit message | Tiếng Việt có dấu |
| Tài liệu | Tiếng Việt có dấu |
| Chuỗi hiển thị cho người dùng | Tiếng Việt có dấu |

**Từ ngữ trên giao diện** (rà ở #157, navigator duyệt 26/10/2026). Một khái niệm một tên, ở mọi
màn hình, thông báo lỗi và tài liệu hướng người dùng:

| Khái niệm | Tên duy nhất | Không dùng |
|---|---|---|
| Người gửi yêu cầu | **người gửi** | người tạo, chủ hồ sơ |
| Người phân loại và chuyển phòng | **điều phối viên** | người tiếp nhận, người phân loại |
| Người làm việc ở phòng | **người xử lý** (được giao), **trưởng phòng** (giao việc) | người phụ trách, người xét duyệt |
| Thứ được gửi / thứ được theo dõi | **yêu cầu** (lúc gửi, theo loại) / **hồ sơ** (sau khi gửi) | — |
| Cuộc nói chuyện trên một hồ sơ | **Trao đổi**; từng tin là **lời nhắn**; danh sách chung là **Hộp thư** | — |
| Chuỗi mốc của hồ sơ | **dòng thời gian** | nhật ký, lịch sử hồ sơ |
| Bộ đếm hạn | **đồng hồ hạn xử lý** | đồng hồ trơ trọi, SLA |
| Lỗi hạ tầng người dùng gặp | **hệ thống không phản hồi** | dịch vụ ứng dụng, máy chủ |
| Chuyển hồ sơ sang phòng khác | **chuyển** (về, lại sang) | định tuyến |

"Nhật ký sự kiện" và "dịch vụ ứng dụng" vẫn là tên đúng trong tài liệu kỹ thuật và bảng trạng thái
vận hành ở màn Hệ thống, nơi chỉ quản trị viên vào được (#229) — quy tắc trên chỉ áp cho chữ người
dùng cuối đọc. Thông báo lỗi nói bằng
**nhãn** của trạng thái và vai trò (tra từ bảng `states`, `roles`), không bao giờ bằng mã tiếng Anh.
Chữ nằm ở mã (`frontend/`, `backend/`) đổi không cần `down -v`; chữ nằm trong dữ liệu (nhãn trạng thái,
cạnh, ô ghi chú trong `infra/seed/`) thì phải.

### 8.4. Chuyển động

**Đã cài đặt** — #158, quy tắc chung từ #237.

Chuyển động chỉ để **định hướng** (mắt theo kịp chỗ vừa đổi) và **báo phản hồi** (thao tác đã nhận).
Không hạt, phát sáng hay hiệu ứng chỉ để trang trí; không con số nào đếm từ 0 khi mở trang — số việc
cần làm thoáng hiện 0 thì người đọc lướt tưởng không có việc. Chỉ dùng CSS, tăng cường dần: trình duyệt
không hỗ trợ thì không có hiệu ứng mà giao diện vẫn dùng được. Đường cong chung `--nhanh`
(`cubic-bezier(0.2, 0.7, 0.2, 1)`), hiệu ứng ra dùng `ease-in`.

| Khi nào | Hiệu ứng | Thời lượng |
|---|---|---|
| Rê, bấm nút, chip, dòng, ô nhập | đổi nền, viền, màu | 150 ms |
| Trang mới hiện (`.vao`) | mờ dần vào, nhích 6 px | 180 ms |
| Dòng hàng đợi hiện lần lượt | như trên, trễ 20 ms mỗi dòng, tối đa 6 dòng | ≤ 300 ms cả lượt |
| Mở ngăn xem nhanh / đóng | trượt vào từ mép phải 24 px / trượt ra rồi mới rời `?xem=` | 220 / 140 ms |
| Hộp xác nhận, thông báo kết quả (`role="alert"`), menu thao tác | hiện ra (`hien-ra`); hộp xác nhận ẩn đi (`data-an`) rồi mới gỡ | 150 / 140 ms |
| Số đếm đổi giá trị lúc đang xem (`SoCuon`) | chữ số cuộn vào từ phía số đi: lên khi tăng, xuống khi giảm | 200 ms |
| Menu sắp xếp, sơ đồ xem nhanh trạng thái, gạch dưới tab | hiện ra | 150–200 ms |
| Mở, thu gọn thanh bên; mũi tên thu gọn nhóm, dòng thời gian | đổi bề ngang, xoay | 150–240 ms |
| Ngăn kéo thanh bên ở màn hẹp | trượt, lớp phủ mờ dần | 250–300 ms |
| Đổi sáng/tối | chuyển màu toàn trang, chỉ trong lúc vừa bấm | 220 ms |
| Khung chờ (đang tải) | vạch sáng lặp | 1,2 s lặp — chỉ báo trạng thái, không phải thao tác |

Thao tác lặp lại không quá **300 ms kể cả độ trễ**. Hiệu ứng ẩn chạy xong mới gỡ phần tử: `useAnCham`
trong `lib/chuyen-dong.ts` đặt `data-an`, chờ `THOI_LUONG_AN_MS` (cùng số với CSS) rồi mới đóng. Hiện
trang dùng `animation-fill-mode: backwards`, không `both`: phần tử còn giữ `transform` sau hiệu ứng thì
`position: fixed` bên trong tính theo nó chứ không theo cửa sổ (gặp ở #233). Đã bỏ: vạch hạn chạy từ 0
lên khi mở trang (0,6 s), dòng hàng đợi trễ 40 ms × 12 (tới 0,72 s).

Máy bật **giảm chuyển động** thì khối cuối mục chuyển động trong `globals.css` tắt mọi hiệu ứng và
chuyển tiếp, và `useAnCham` đóng ngay không chờ. Kịch bản kiểm tra giao diện (`e2e/`) giữ ba điều: không
hiệu ứng nào quá 300 ms trên trang chủ, hàng đợi và ngăn xem nhanh; mở trang chủ không số nào cuộn; giảm
chuyển động thì không phần tử nào còn khai hiệu ứng. Danh sách 200 việc chờ ở trang chủ cuộn và đổi cách
xếp không có tác vụ nào trên 50 ms (đo 02/11/2026, Chrome, ba lượt liên tiếp).

---

## 9. Ngoài phạm vi

Không xây dựng những thứ sau vào mã nguồn ở giai đoạn hiện tại:

- Triển khai lên máy chủ thật hoặc dịch vụ đám mây — kể cả cấu hình mẫu có TLS (#244) và chặn khởi động
  khi còn mật khẩu hay tài khoản mẫu (#242): giảng viên chốt không làm ngày 13/11/2026; README có mục
  *Trước khi dùng thật*. Sao lưu chỉ có bản tay cho quy mô trình diễn (#245, `scripts/sao_luu.py`) —
  sao lưu tự động theo lịch nằm ngoài phạm vi
- Khôi phục mật khẩu qua thư điện tử. Xác thực hai lớp bằng mã dùng một lần đã có dưới dạng tùy chọn, mặc
  định tắt (#366, `scripts/xac_thuc_hai_lop.py`): chỉ đổi cấu hình qua API quản trị Keycloak, không sửa
  realm JSON hay mã nền tảng
- Ứng dụng di động
- Đa ngôn ngữ giao diện
- Thanh toán, tích hợp hệ thống tài chính
- Tối ưu hiệu năng cho quy mô lớn — hệ thống chỉ cần chạy tốt ở quy mô trình diễn

Nếu một yêu cầu chạm vào danh sách này, dừng lại và trao đổi trước khi thực hiện.

---

## 10. Chiến lược đối phó với đề thi tháng 11

Đề thi chính thức công bố tháng 11/2026, chấm kho mã ngày 7–9/12, chung kết 10/12.

**Nguyên tắc**: mọi thứ xây dựng trước tháng 11 phải tái sử dụng được. Tách bạch
phần kiến trúc giữ nguyên và phần nghiệp vụ thay được — xem bảng ở mục 5.

**Hệ quả với `main`**: nhánh `main` luôn phải ở trạng thái dựng được và trình diễn
được, vì đó là thứ ban giám khảo nhìn thấy khi chấm kho mã. Đây là lý do tồn tại
của nhánh tích hợp `dev`.

---

## 11. Quy trình làm việc của tác nhân AI

Áp dụng cho mọi công việc trong kho mã này, bất kể công cụ nào đang chạy.

**Thứ tự đọc bắt buộc trước khi làm gì:**

1. `docs/PROJECT_STATE.md` — biết dự án đang ở đâu, vừa làm gì, đang vướng gì
2. `docs/ARCHITECTURE.md` (tệp này) — biết hệ thống hoạt động thế nào
3. `docs/ROADMAP.md` — biết việc tiếp theo là gì
4. `docs/adr/` — biết vì sao chọn công nghệ đó, tránh đề xuất lại thứ đã bác bỏ
5. `CLAUDE.md` — các ràng buộc vận hành, đặc biệt là quy tắc cấm tự chạy lệnh Git

**Sau đó:**

6. **Phân tích** yêu cầu — xác định chính xác tệp và khuôn mẫu nào bị ảnh hưởng.
   Nếu yêu cầu mâu thuẫn với một khuôn mẫu đã ghi hoặc chạm vào mục 9, **dừng lại
   và hỏi** thay vì tự quyết định.

7. **Thực hiện** — bám theo khuôn mẫu đã có. Ưu tiên mở rộng khuôn mẫu hiện tại hơn
   là phát minh khuôn mẫu mới.

8. **Không tự chạy** kiểm thử, máy chủ phát triển, hoặc lệnh triển khai trừ khi
   được yêu cầu rõ ràng. Sinh ra mã không đồng nghĩa với đã kiểm chứng mã chạy được.

9. **Không tự chạy bất kỳ lệnh Git nào ghi vào lịch sử** — commit, push, merge,
   tag, tạo nhánh. Soạn sẵn lệnh và nội dung để người dùng tự chạy. Lịch sử commit
   phải mang danh tính thật của con người. Xem `CLAUDE.md`.

10. **Trả về kết quả để rà soát** — tóm tắt tệp đã đổi và vì sao. Không coi công
    việc là xong chỉ vì mã biên dịch được.

11. **Cập nhật tệp này** nếu thay đổi vừa rồi tạo ra hoặc sửa đổi một khuôn mẫu —
    ngay trong cùng công việc, không để lại sau.

---

## 12. Khi nào cập nhật tệp này

| Tình huống | Cập nhật? |
|---|---|
| Sửa lỗi bên trong một khuôn mẫu đã có | **Không** — mô tả khuôn mẫu vẫn đúng |
| Thêm trường mới vào lược đồ mà mã khác cần biết | **Có** — cập nhật mục tương ứng |
| Đưa vào một cơ chế mới, hoặc đổi cách hai thành phần giao tiếp | **Có** |
| Chốt một nền tảng nguồn mở sau khảo sát | **Có** — cập nhật mục 3, đồng thời tạo bản ghi quyết định trong `docs/adr/` |
| Thêm một trang hoặc một điểm cuối API mới | **Có** — bổ sung vào mục 4 |
| Thay đổi thuần túy về giao diện hoặc câu chữ | **Không** |
| Thêm kế hoạch cho giai đoạn sau | **Không** — kế hoạch thuộc về `ROADMAP.md` |
| Cập nhật tiến độ tuần | **Không** — tiến độ thuộc về `PROJECT_STATE.md` |

**Tự kiểm tra trước khi kết thúc mỗi công việc**: nếu một người hoặc một tác nhân AI
mở phiên làm việc mới ngay bây giờ và chỉ đọc tệp này, họ có hiểu đúng hành vi hiện
tại của hệ thống không, hay sẽ tưởng nhầm một khuôn mẫu đã không còn tồn tại?

Nếu là vế sau, cập nhật tệp trước khi kết thúc công việc.
