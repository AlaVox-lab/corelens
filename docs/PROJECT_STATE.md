# PROJECT_STATE.md

> **Mục đích**: sổ bàn giao ca của dự án. Đọc tệp này là biết ngay dự án đang ở đâu,
> vừa làm gì, đang vướng gì và việc tiếp theo là gì — không cần hỏi ai.
>
> **Nhịp cập nhật**: cuối mỗi tuần, và mỗi khi cắt bản phát hành.
>
> Tệp này chỉ ghi **hiện tại và quá khứ gần**. Kế hoạch dài hạn thuộc `ROADMAP.md`.
> Mô tả kiến trúc thuộc `ARCHITECTURE.md`.

---

## Ảnh chụp nhanh

| Mục | Giá trị |
|---|---|
| Cập nhật lần cuối | 2026-09-24 |
| Phiên bản hiện tại | `v0.3.0`, cắt ngày 16/09. `main` đi trước thẻ **16 commit nội dung** — đủ điều kiện cắt `v0.4.0` |
| Giai đoạn | **Giai đoạn 2 đang chạy** — `H` và `P` thông đầu-cuối cho **cả bốn vai trò** trên giao diện thật |
| Mốc công việc đang chạy | Tuần 7 — Buồng lái vận hành và khảo sát Open-Core, hạn 27/09 |
| Trạng thái kho mã | Riêng tư, sẽ chuyển công khai trước khi nộp bài |
| Có mã nguồn ứng dụng chưa | **Có.** `backend/` FastAPI và `frontend/` Next.js với ba màn hình: cổng người gửi, buồng lái điều phối, buồng lái phòng ban. Cụm gồm **sáu dịch vụ** |
| Issue đang mở | **7** — #46, #47, #48, #80, #81, #101, #102 |
| Quyết định kiến trúc đã chốt | **5** — Keycloak `H` · SeaweedFS `core` · Superset `D` · tự viết engine `P` · ranh giới máy trạng thái (ADR-0005) |
| Còn chờ khảo sát | 3 — quản trị tri thức `H` (#46, đang làm), véc-tơ và LLM `I` (#47), khai phá quy trình `I` (#48, đang làm) |
| Bộ kiểm thử tự động | **171 bài**, chạy trên PostgreSQL thật. Mọi issue từ #78 đều qua phép thử đột biến |
| Tổng bộ nhớ toàn cụm | **1,55 GiB**, đo ngày 16/09. Chưa đo lại — hai buồng lái không thêm dịch vụ nào |
| Số ngày còn lại tới chấm kho mã | **74 ngày** (07/12/2026) |
| Số ngày còn lại tới khi công bố đề thi | khoảng **38 ngày** (đầu tháng 11/2026) |

**Một câu tóm tắt trạng thái**: nhân viên gửi yêu cầu → điều phối viên phân loại, đặt
mức ưu tiên, chuyển về phòng ban → trưởng phòng nhận hoặc trả lại, giao người xử lý tra
từ danh bạ Keycloak → người xử lý làm, hỏi thêm người gửi khi cần → quá hạn thì tự leo
thang, có ân hạn sau khi phân công lại → người gửi xác nhận đạt hoặc mở lại. Mọi bước
ghi nhật ký sự kiện, kèm lịch sử thay đổi của trường quyết định. Chạy được trên máy
sạch bằng một lệnh.

Thứ còn thiếu trong luồng thủ công: **thao tác không đổi trạng thái** — nhắn, hỏi tiến
độ, nhận việc, sửa nội dung (#81, thiết kế đã chốt ở ADR-0005), **đính kèm tệp** (#80),
**chỉnh hạn từng hồ sơ** (#101, chờ giảng viên). Tầng `D` và `I` chưa cài đặt.

---

## Đã hoàn thành

### Tuần 1 — Dựng nền kho mã

**Hạ tầng kho mã**

- [x] Tạo kho mã `AlaVox-lab/dx-os-lab` với giấy phép MIT
- [x] Tạo nhánh `dev` làm nhánh tích hợp
- [x] Cấu hình quy tắc bảo vệ nhánh cho `main` và `dev` (chưa có hiệu lực do kho mã
      còn riêng tư trên gói miễn phí; sẽ tự động áp dụng khi chuyển công khai)
- [x] Cấu hình cách hợp nhất: bật squash và merge commit, tắt rebase, tự xóa nhánh
      sau khi hợp nhất

**Bộ quy chuẩn**

- [x] `CONTRIBUTING.md` — quy trình làm việc, quy ước commit, quy ước mã nguồn
- [x] Ba mẫu issue: báo lỗi, đề xuất tính năng, khảo sát kỹ thuật
- [x] Mẫu đề nghị hợp nhất với danh sách kiểm tra
- [x] `cliff.toml` — cấu hình sinh nhật ký thay đổi, đã kiểm chứng chạy được
- [x] `.gitignore` — bao phủ Node, Python, Docker, tệp bí mật
- [x] `.gitattributes` — chuẩn hóa ký tự kết thúc dòng giữa các hệ điều hành
- [x] `scripts/setup-labels.sh` — kịch bản khởi tạo hệ thống nhãn
- [x] Tạo hệ thống nhãn ban đầu (8 nhãn thủ công)

**Vận hành**

- [x] Tạo mốc công việc `Tuần 1&2 — Khởi động`
- [x] Chạy trọn ba vòng quy trình: issue → nhánh → commit → PR → merge
- [x] Kiểm chứng cả hai cơ chế đóng issue: tự động bằng `Closes` và thủ công
- [x] Sinh `CHANGELOG.md` tự động bằng git-cliff
- [x] Cắt bản phát hành `v0.1.0`

**Issue đã đóng**: #1, #4, #7

### Tuần 3 — Bắt Đầu

**Tài liệu bối cảnh và quy chuẩn**

- [x] Bộ bảy tệp tài liệu bối cảnh: `CLAUDE.md`, `README.md` (bản đầy đủ),
      `docs/ARCHITECTURE.md`, `docs/PROJECT_STATE.md`, `docs/ROADMAP.md`,
      `docs/dependencies.md`, `docs/adr/0000-mau-ban-ghi-quyet-dinh.md` (#10)
- [x] Mục 2.5 trong `CONTRIBUTING.md` — quyền cập nhật tài liệu trạng thái (#13)
- [x] Sơ đồ luồng nghiệp vụ bằng Mermaid tại `docs/process-flow.md` (#16)

**Vận hành**

- [x] Hoàn thiện hệ thống nhãn bằng `scripts/setup-labels.sh` — đủ 23 nhãn theo khung H-P-D-I
- [x] Cài đặt GitHub CLI (`gh`)
- [x] Mở ba issue khảo sát Open-Core cho không gian H, P, D (#19, #20, #21)

**Issue đã đóng**: #10, #13, #16

---

### Tuần 4 — Khảo sát Open-Core

Tuần đầu tiên có kết quả kỹ thuật đo được thay vì chỉ tài liệu quy chuẩn. Mọi kết luận
đều dựa trên số liệu dựng thử bằng Docker, không dựa trên tài liệu nhà cung cấp.

**Ba nền tảng đã chốt**

- [x] `H` — **Keycloak `26.7.3`** làm nền tảng định danh tập trung (#19).
      Tài liệu khảo sát `docs/sso-platform-survey.md`, bản ghi quyết định ADR-0001
- [x] `core` — **SeaweedFS `4.45`** làm kho lưu trữ đối tượng cho tệp đính kèm (#24).
      Tài liệu `docs/object-storage-survey.md`, ADR-0002
- [x] `D` — **Apache Superset `6.1.0`** làm nền tảng kinh doanh thông minh (#21).
      Tài liệu `docs/bi-platform-survey.md`, ADR-0003

**Một khảo sát hoàn thành nhưng chưa ra quyết định**

- [x] `P` — khảo sát nền tảng tự động hóa luồng công việc (#20). Đã dựng thử bốn ứng
      viên, tài liệu `docs/workflow-engine-survey.md` đã lên `main`. Chưa chốt ở thời
      điểm đó — quyết định tự viết engine đưa ra ở tuần 5, xem ADR-0004

**Kết quả phụ ngoài dự kiến**

Hai mục của Giai đoạn 1.3 tiến triển nhờ công việc của #21:

- [x] **Lược đồ nhật ký sự kiện** đã hiện thực thành bảng SQL chạy được, kiểm chứng
      bằng 1.000 hồ sơ ảo và 5.496 sự kiện
- [x] **Danh mục chỉ số cho bảng điều khiển** — bốn chỉ số đã tính được đầu cuối qua
      Superset: tồn đọng theo bộ phận, thời gian xử lý trung vị, tỷ lệ vi phạm SLA,
      phân bố loại yêu cầu

**Ngân sách bộ nhớ tích lũy**: khoảng **1,29 GB** cho ba nền tảng đã chốt. Con số này
cần theo dõi vì bảng chấm PoF mục 4 đòi `docker compose up` chạy được trên máy sạch.

**Issue đã đóng**: #19, #21, #24

---

### Tuần 5 — Chốt kiến trúc

**Không gian `P`: tự viết engine máy trạng thái** (#20, ADR-0004).

Giảng viên hướng dẫn cho ý kiến ngày 07/09 và dời trọng tâm câu hỏi: vấn đề không phải
*"dùng Flowable hay tự viết"* mà là *"điểm sáng tạo của đề tài nằm ở đâu"*. Ba lý do
được ghi lại:

1. Engine không phải nơi tạo ra giá trị; giá trị nằm ở vòng phản hồi tự soi quy trình,
   nên nhóm dồn sức vào khai phá quy trình thay vì vào việc chọn công cụ
2. Flowable không giải quyết vấn đề cốt lõi — nhật ký của nó thiếu `from_state` và
   `to_state`, nên nhóm vẫn phải tự viết lớp sinh nhật ký dù có lắp engine hay không
3. Tự viết cho toàn quyền kiểm soát dữ liệu, và giảm rủi ro so với việc học một khung
   làm việc mới trong quỹ thời gian còn lại

Bổ sung mục 6.1 vào `ARCHITECTURE.md`: cơ chế **một cửa duy nhất** — mọi lần đổi trạng
thái đi qua đúng một điểm trong mã, điểm đó tra bảng quy tắc, kiểm quyền, chạy Poka-yoke
rồi ghi nhật ký trước khi cập nhật hồ sơ. Đây là điều kiện bảo đảm nhật ký không bao giờ
thiếu bản ghi.

**Dọn dẹp kho mã**: xóa 13 nhánh cũ còn sót trên máy chủ; tắt `allow_rebase_merge`, bật
Discussions — hai cấu hình trước đó lệch với tài liệu. Có bật thêm
`delete_branch_on_merge` rồi phải tắt lại, lý do xem mục Ghi chú kỹ thuật.

**Mô hình nghiệp vụ được giảng viên mở rộng** trong cùng buổi trao đổi, ba thay đổi:

1. **Năm vai trò thay vì bốn** — thêm Quản trị viên. Không cần sửa ADR-0001: quyết định
   chọn Keycloak vẫn đúng, và đây đúng là lúc tính chất *vai trò nằm trong dữ liệu* trả
   cổ tức — thêm vai trò chỉ là sửa tệp realm JSON
2. **Thêm chặng định tuyến phòng ban** — sau khi phân loại, yêu cầu chuyển về phòng ban
   tương ứng, phòng ban đó xác duyệt xem có đúng việc của mình không. Nếu sai thì trả về
   để định tuyến lại. Vòng lặp này là điểm cộng cho tầng `I`: đúng loại lệch chuẩn mà
   khai phá quy trình sinh ra để phát hiện
3. **Sản phẩm phải tùy biến được cho doanh nghiệp khác** — khách hàng tải về rồi tự sửa
   phòng ban và loại yêu cầu theo đặc thù của mình. Ý này nâng nguyên tắc cấu-hình-thay-vì-
   mã-cứng từ biện pháp đối phó đề thi tháng 11 thành **mục tiêu sản phẩm**

**Chiến lược được giảng viên chốt**: đi sâu một luồng nghiệp vụ chạy hoàn chỉnh trước,
rồi mới mở rộng bốn không gian. Ba khảo sát còn lại nên làm sớm để biết trước ràng buộc
nhưng **chưa tích hợp** cho tới khi luồng chính ổn định.

**Mở 12 issue** cho toàn bộ việc tồn đọng: #37 tới #48.

**Issue đã đóng**: #20

---

### Tuần 5 (tiếp) — Hạ tầng chạy được và khép Giai đoạn 1

**Hạ tầng phát triển** (#38, `infra/`). Bốn dịch vụ ghép lại dựng được bằng một lệnh trên
máy sạch: PostgreSQL, Keycloak, SeaweedFS, Apache Superset. **Tổng bộ nhớ đo thật 1,17 GB.**

Chọn **một thực thể PostgreSQL chứa ba database** (`dxlab`, `keycloak`, `superset`) thay vì
mỗi dịch vụ một cơ sở dữ liệu riêng — ba thực thể sẽ tốn gấp ba bộ nhớ mà không đổi lại lợi
ích nào ở quy mô trình diễn. Superset chỉ được cấp tài khoản **chỉ đọc** trên dữ liệu
nghiệp vụ, đúng ràng buộc ADR-0003.

Ba lỗi chỉ lộ ra khi chạy thật, chi tiết ở mục Ghi chú kỹ thuật: cờ telemetry của SeaweedFS
ghi sai trong bốn tài liệu, Superset lặng lẽ dùng SQLite, và ảnh Superset không tự khởi tạo.

**Mô hình nghiệp vụ chốt xong** (#37). Giảng viên trả lời câu hỏi về vai trò *Người xét
duyệt*: **chỉ một cổng duyệt duy nhất**, không phải hai. Cổng đó chỉ trả lời *nhận* hay
*không nhận*; khi phát sinh chi phí thì người phụ trách phòng lập **một phiếu yêu cầu mới**
theo luồng riêng, tính là hồ sơ khác. Trạng thái `Chờ phê duyệt` cũ bị bỏ hẳn.

Nguyên tắc quan trọng nhất rút ra: **đã nhận là không trả về**. Sau khi phòng ban xác duyệt,
hồ sơ không quay lui được; vấn đề phát sinh do chính phòng đó xử lý. Diễn đạt thành bảng
quy tắc chứ không phải lời khuyên — đơn giản là không tồn tại cạnh nào đi ngược.

Kết quả: **10 trạng thái, 19 cạnh chuyển, 5 vai trò, 4 ràng buộc Poka-yoke** trong
`process-flow.md`. Đây là dữ liệu khởi tạo trực tiếp cho bảng `states` và `transitions` ở #40.

**Bảng Đội ngũ** trong `README.md` điền đủ bốn người kèm liên kết GitHub.

**Bản phát hành `v0.2.0`** cắt ngày 12/09, khép Giai đoạn 1. Nhật ký thay đổi 14 mục, sinh
bằng `git-cliff` — cách chạy trên máy này xem mục Ghi chú kỹ thuật.

**Issue đã đóng**: #37, #38

---

### Tuần 6 — Những dòng mã nghiệp vụ đầu tiên

Tuần đầu tiên kho mã có **mã nguồn ứng dụng chạy được**, không chỉ tài liệu và hạ tầng.
Năm issue khép lại trong hai ngày, và cuối tuần `main` có một vòng nghiệp vụ hoàn chỉnh.

**Lược đồ cấu hình của engine** (#40). Mười một bảng trong
`infra/postgres/init/02-luoc-do-quy-trinh.sql`, dữ liệu khởi tạo tách riêng sang
`infra/seed/` vì đó là phần doanh nghiệp triển khai sẽ sửa. Ba lớp bảo vệ, không lớp
nào nằm trong mã ứng dụng: khóa ngoại, chỉ mục duy nhất từng phần, và một lớp kiểm tra
mức đồ thị làm cụm Docker **dừng khởi động** nếu bộ quy tắc hỏng.

Mẹo đáng nhớ nhất: cột kỹ thuật `transitions.from_is_terminal` luôn bằng `FALSE` và
tham chiếu tới `states (rule_set_id, code, is_terminal)`, nên **không thể tạo cạnh rời
khỏi một trạng thái đã đóng**. Dữ liệu khởi tạo không bao giờ nhắc tới cột này.

**Bộ khung ứng dụng** (#62 — issue mở bổ sung giữa tuần). Đường tới hạn cũ bỏ sót mắt
xích này vì #40 là dữ liệu thuần SQL nên không cần tầng ứng dụng; mãi tới dòng Python
đầu tiên vấn đề mới lộ ra. `backend/` FastAPI, `frontend/` Next.js, cụm thành sáu dịch
vụ, và hai tệp khóa phiên bản đi vào kho mã.

**Điểm chuyển trạng thái duy nhất** (#41). Trái tim của đề tài. Năm bước theo đúng thứ
tự `ARCHITECTURE.md` mục 6.1, khóa dòng hồ sơ bằng `SELECT FOR UPDATE`, danh sách trắng
bốn trường quyết định được phép đặt. Nhật ký sự kiện **chỉ ghi thêm** — một trigger
PL/pgSQL chặn mọi `UPDATE` và `DELETE`, đặt ở tầng cơ sở dữ liệu vì Superset và mọi
kết nối `psql` đều đi vòng qua tầng ứng dụng.

**Tích hợp định danh** (#43). Phòng ban lấy từ **nhóm** Keycloak thay vì thuộc tính
người dùng. Hàm `actor_from_claims` là chỗ duy nhất dịch giữa ngôn ngữ của Keycloak và
ngôn ngữ của engine, nên engine không biết Keycloak tồn tại. Token không bao giờ tới
trình duyệt: cổng giữ chúng trong cookie `httpOnly` đã mã hóa.

**Đồng hồ SLA và tự leo thang** (#42). Ba cột thay cho một mốc hạn chót tính sẵn, vì
đồng hồ dừng rồi chạy lại nhiều lần trong đời một hồ sơ. Leo thang **đi qua điểm chuyển
trạng thái duy nhất**, không đi tắt — đi tắt thì nhật ký sẽ thiếu đúng những bản ghi
thú vị nhất, các lần trễ hạn.

**Bộ kiểm thử 51 bài**, chạy trên PostgreSQL thật vì lược đồ dùng chỉ mục duy nhất từng
phần, khóa ngoại tổng hợp, `TIMESTAMPTZ` và trigger PL/pgSQL — SQLite không thay được,
mà chính những thứ đó mới là cái cần kiểm. Chất lượng bộ kiểm thử được đo bằng **phép
thử đột biến**: gỡ bước chạy ràng buộc làm đổ đúng sáu bài Poka-yoke, gỡ bước ghi nhật
ký làm đổ đúng tám bài, gỡ phần kế toán đồng hồ làm đổ đúng ba bài.

**Issue đã đóng**: #40, #41, #42, #43, #62

### Tuần 6 (tiếp) — Cổng người dùng và bản phát hành `v0.3.0`

**Đo giới hạn tệp tải lên SeaweedFS** (#39). Kết quả ghi trong `docs/`. Điểm đáng nhớ
của phép đo: con số giới hạn thật chỉ tìm ra bằng cách **thử tải lên cho tới khi hỏng**,
không đọc từ tài liệu — đúng nguyên tắc kiểm chứng bằng thực nghiệm mà nhóm đã áp dụng
từ đợt loại Temporal.

**Bản phát hành `v0.3.0`**, cắt ngày 16/09. Tăng MINOR vì đợt này toàn `feat`. Nhật ký
thay đổi sinh bằng `git-cliff`; số commit bị bỏ qua đúng bằng số merge commit cộng một,
nên không có commit nào viết sai chuẩn.

**Cổng gửi yêu cầu** (#44). Ba màn hình cho người gửi: biểu mẫu ba bước, danh sách hồ sơ
của mình, và trang chi tiết có dòng thời gian đầy đủ. Năm điểm cuối mới cho không gian
`H`, cộng một điểm cuối danh mục trạng thái phục vụ bảng chú giải.

Điều đáng ghi nhất của issue này **không phải mã nguồn mà là một phát hiện**: bản thiết
kế giao diện đặt nút *"Hủy yêu cầu"* ở hai trạng thái mà dữ liệu không có cạnh đó, tức
là bản thiết kế mâu thuẫn với chính bộ quy tắc quy trình. Cách xử lý đã thành một khuôn
mẫu, ghi ở `ARCHITECTURE.md` mục 7.2: **giao diện dựng nút bấm thẳng từ
`allowed_transitions` của API**, không giữ bản sao nào của bộ quy tắc. Hai cái nút sai
tự biến mất, và không có đường nào cho chúng quay lại.

Ba quyết định phụ đi kèm:

- **Loại yêu cầu mở cho người gửi, mức ưu tiên thì không.** Chọn sai loại chỉ làm hồ sơ
  đi chậm một nhịp và người phân loại nắn lại ngay; còn ai cũng đánh dấu việc của mình
  là khẩn thì thứ tự ưu tiên mất hết ý nghĩa
- **Dấu hiệu riêng cho từng trạng thái** (`○ ◐ ◌ ● ! ✓ ✕ ▲ ■ –`), để bản in đen trắng
  và người không phân biệt được màu vẫn đọc được. Bản in là một khối `@media print`, tự
  kích hoạt khi bấm Ctrl+P, không phải một nút bật tắt như trong bản thiết kế
- **Phông chữ tải lúc dựng, tự phục vụ từ máy chủ của hệ thống.** Trình duyệt nhân viên
  không gọi sang máy chủ Google mỗi lần mở một hồ sơ nội bộ, và hệ thống chạy được trong
  mạng không có đường ra Internet

**Bộ kiểm thử lên 68 bài.** Một lỗi chỉ lộ ra khi chạy thật chứ không khi dựng: tệp mang
chỉ thị `"use server"` chỉ được xuất ra hàm bất đồng bộ, nên một hằng số xuất kèm làm
trang trả 500 — mà `next build` vẫn báo thành công. Xem `frontend/app/yeu-cau/ket-qua.ts`.

**Issue đã đóng**: #39, #44

---

### Tuần 7 — Buồng lái vận hành, và một lượt duyệt kịch bản kiểm thử

**Vá lỗ `CHANGEABLE_FIELDS` trước khi mở buồng lái** (#78). Engine cũ cho đặt mọi trường
quyết định ở mọi cạnh — người xử lý bấm *Hoàn thành* kèm `priority_code` là tự nâng được
mức ưu tiên việc của mình. Giờ mỗi ràng buộc khai trường nó quản, và một lần chuyển chỉ
đặt được trường mà ràng buộc trên **chính cạnh đó** quản. Xem `ARCHITECTURE.md` mục 7.

**Đăng nhập bằng trình duyệt thật không giữ được phiên** (#87, `P0`). Cookie phiên chứa
cả bộ token vượt trần 4096 byte, trình duyệt lặng lẽ bỏ nó. Bộ kiểm thử không bắt được vì
nó tự đúc cookie thay vì đi đường đăng nhập thật. Sửa bằng cách tách thành hai cookie; từ
đó mọi lần kiểm trang đều đi trọn luồng OIDC.

**Buồng lái vận hành — khép #45** bằng ba issue con:

- **Buồng lái điều phối viên** (#82): phân loại, đặt mức ưu tiên, sửa loại người gửi chọn
  sai, chuyển phòng với gợi ý từ bảng ánh xạ, định tuyến lại khi bị trả
- **Danh bạ Keycloak** (#84): client `dx-directory` đọc thành viên từng phòng qua Admin API,
  để ô chọn người xử lý hiện tên thật. Danh bạ không trả lời thì vẫn nhận được hồ sơ, chỉ
  không giao được người
- **Buồng lái phòng ban** (#83): trưởng phòng nhận hoặc trả, giao người, phân công lại khi
  leo thang; người xử lý làm và hỏi thêm. Ai giao việc, ai nhận việc đều suy từ dữ liệu

**Lượt duyệt kịch bản kiểm thử bằng tay.** Navigator chạy từng bước một vòng đời hồ sơ,
hỏi "chuyện gì xảy ra nếu…" ở mỗi nút, và ghi chín phát hiện. Mỗi phát hiện thành một
issue, sửa và lên `main` ngay trong ngày thay vì gom tới cuối:

| Issue | Phát hiện | Cách sửa |
|---|---|---|
| #97 | Bốn lỗi hiển thị: câu đồng hồ khi chưa chạy, bảng thao tác bị cắt, danh sách lệch cột | Sửa giao diện |
| #94 | Trưởng phòng phân công lại xong, hồ sơ bị leo thang lại ngay lượt quét sau | **Khoảng ân hạn** theo loại yêu cầu — cột `request_types.sla_grace_hours` |
| #98 | "Hủy yêu cầu" bấm là mất hồ sơ, không hỏi lại | Cạnh dẫn tới trạng thái kết thúc mở bảng xác nhận, suy từ `states.is_terminal` |
| #99 | Người xử lý hỏi thêm xong, hồ sơ biến khỏi hàng đợi của họ | Nhóm *chỉ để theo dõi* trong hàng đợi phòng ban |
| #100 | Điều phối sửa loại người gửi chọn sai, giá trị cũ mất dấu | Cột `event_log.changes` ghi mọi lần đổi trường quyết định dạng "từ → sang" |
| #79 | Người gửi thấy hai nút "Bổ sung thông tin", phải đoán ai đã hỏi mình | Ràng buộc `return-to-previous-state`: hồ sơ về đúng chỗ đã hỏi. Trưởng phòng cũng hỏi thêm được |

#79 kéo theo hai thay đổi đáng nhớ. **Ràng buộc không cần nhập liệu chạy luôn lúc chào
nút**, nên cạnh chắc chắn bị từ chối không hiện ra. Và tệp kiểm tra đồ thị có **phép kiểm
thứ sáu**: một nơi hỏi thêm mà thiếu đường quay về thì cụm dừng khởi động.

**ADR-0005 — ranh giới của máy trạng thái** (#81). Bốn thao tác người dùng cần lại không
đổi trạng thái: nhắn điều phối viên, hỏi tiến độ, nhận việc về mình, sửa nội dung. Bản ghi
so ba phương án trên dữ kiện đọc từ mã nguồn; giảng viên duyệt ngày 24/09 kèm một điều
chỉnh — người gửi được sửa nội dung khi hồ sơ chưa tới phòng ban. Chưa viết mã.

**Chuẩn bị cho thành viên dùng trợ lý AI** (#117). `AGENTS.md` ở gốc kho cho Antigravity và
Codex — hai công cụ không đọc `CLAUDE.md` — để quy tắc không tự commit áp dụng cho mọi trợ
lý. `CLAUDE.md` bỏ các câu đã lỗi thời về hiện trạng kho.

**Nhịp phát hành đổi**: từ 22/09, mỗi issue một pull request `dev → main` ngay sau khi
squash. Issue đóng ngay, `main` luôn có bản mới nhất để thử.

**Bộ kiểm thử lên 171 bài.** Mọi issue từ #78 đều qua phép thử đột biến trên một cụm thử
cách ly; phép đột biến nào sống sót thì hoặc thêm bài, hoặc gỡ đoạn mã thừa mà nó chỉ ra.

**Issue đã đóng**: #45, #78, #79, #82, #83, #84, #87, #94, #97, #98, #99, #100, #117

---

## Đang làm

| Issue | Ưu tiên | Việc | Người làm |
|---|---|---|---|
| #46 | P2 | Khảo sát hệ thống quản trị tri thức cho `H` | `@Senning-Dd`, navigator cùng theo — bản ghi giữ chỗ **ADR-0006** |
| #48 | P3 | Khảo sát thư viện khai phá quy trình cho `I` | `@NguyentimAnh`, navigator cùng theo — bản ghi giữ chỗ **ADR-0007** |

Hai issue khảo sát là việc đầu tiên của thành viên trên kho mã: không đụng mã nguồn, sản
phẩm là tài liệu khảo sát cộng bản ghi quyết định ở trạng thái *Đề xuất*. Bình luận giao
việc trên từng issue ghi đủ đầu vào, các bước, đầu ra và điều kiện hoàn thành.

**#81 đã chốt thiết kế** ở ADR-0005 nhưng chưa bắt đầu viết mã.

---

## Việc tiếp theo

### Theo thứ tự

1. **#81 — thao tác không đổi trạng thái**, theo ADR-0005. Tách thành ba issue con khi bắt
   tay: bảng lời nhắn, nhận việc về mình, sửa nội dung trước khi tới phòng ban. Đổi lược đồ
   khởi tạo — gỡ ràng buộc cấm cạnh tự trỏ — nên cả nhóm phải `down -v`
2. **#102 — tài liệu**: gỡ nhãn `[CHỜ XÁC NHẬN]` ở hai cạnh đã được giữ, ghi quy tắc mở lại
3. **Lượt kiểm thử tổng thể** theo tệp kịch bản kiểm thử, gồm các điểm chỉ kiểm được bằng
   mắt đã hẹn ở #97, #98, #79
4. **Cắt `v0.4.0`** — đợt này có `feat`, tăng MINOR
5. **#80 — đính kèm tệp**. SeaweedFS đã dựng và giới hạn kích thước đã đo ở #39
6. **#47 — khảo sát véc-tơ và khung LLM**, sau khi #46 và #48 xong

### Chờ giảng viên

- **#101 — điều phối viên chỉnh hạn xử lý từng hồ sơ**: ba câu hỏi ghi trong issue
- **Thời gian ở *Chờ bổ sung thông tin* có tính vào SLA không** — hiện không tính, là một
  cờ trong dữ liệu
- **Người gửi có được đổi mức ưu tiên không** — ví dụ của giảng viên ở #81 có nhắc; nhóm giữ
  ràng buộc Poka-yoke và đã báo lại

### Việc vận hành, không cần issue

1. Tạo mốc *Tuần 8*, dời các issue còn mở sang
2. Tích hợp liên tục: chạy `pytest` và `next build` trên mỗi pull request. Điều kiện đã đủ
   từ lâu — 171 bài kiểm thử hiện chỉ chạy khi có người nhớ chạy
3. Cập nhật bộ sinh dữ liệu ảo theo mười trạng thái, năm vai trò, 21 cạnh, rồi đưa vào kho.
   Bản hiện nằm ở máy navigator và vẫn theo mô hình cũ; #48 cần dùng nó
4. Thêm `CODE_OF_CONDUCT.md`
5. Chuyển kho mã sang công khai trước khi nộp bài; khi đó mới bật lại được
   `delete_branch_on_merge` an toàn
6. Giai đoạn đóng gói: đo hiệu năng, công bố **cấu hình máy tối thiểu** — giảng viên nhắc
   trước để nhóm không quên

---

## Đang vướng

| Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| Quy tắc bảo vệ nhánh chưa có hiệu lực | Quy trình phụ thuộc kỷ luật cá nhân thay vì ràng buộc kỹ thuật | Chuyển kho mã sang công khai. Trong lúc chờ, tuân thủ tự giác |
| Chưa chốt công cụ quản trị cơ sở dữ liệu | Chưa ảnh hưởng, chỉ là công cụ hỗ trợ | Đã trình hai phương án, chờ ý kiến giảng viên |
| Ngân sách bộ nhớ tăng dần theo từng nền tảng | Bảng chấm đòi dựng được trên máy sạch ngày chấm | **Đo thật cả cụm sáu dịch vụ: 1,55 GiB.** Hai dịch vụ ứng dụng chỉ thêm khoảng 110 MB; phần tăng còn lại là Keycloak phình theo JVM. Đo lại sau mỗi quyết định mới |
| **Chưa có tích hợp liên tục** | 171 bài kiểm thử chỉ chạy khi ai đó nhớ chạy. Một hồi quy lọt vào `dev` sẽ không ai biết cho tới lần dựng sau | Điều kiện đã đủ — có cấu trúc thư mục và bộ kiểm thử. Dựng một quy trình chạy `pytest` và `next build` trên mỗi pull request |
| **Quyết định SLA chưa được giảng viên xác nhận** | Nếu thầy muốn tính cả thời gian chờ bổ sung vào SLA thì số liệu hiện có sẽ lệch | Hiện đặt **không tính**, nhưng ghi riêng tổng thời gian dừng. Đổi ý chỉ là bật cờ `states.sla_running` trong dữ liệu khởi tạo |
| **Lược đồ khởi tạo chỉ nạp một lần** | Ai đã có volume cũ mà kéo mã mới về sẽ gặp lỗi thiếu cột, và thông báo lỗi không chỉ ra nguyên nhân | Mỗi lần `infra/postgres/init/`, `infra/seed/` hoặc realm Keycloak đổi, cả nhóm phải `down -v` rồi dựng lại; migration Alembic thì tự chạy. Thành viên tự kiểm sau mỗi lần `pull` bằng lệnh ở bộ luật trợ lý thành viên mục 9. Tuần 7 đã có ba lần như vậy: #84 đổi realm, #94 và #79 đổi lược đồ và dữ liệu khởi tạo |
| Đường truyền tới `github.com` chập chờn | Có lúc `git push` và `git pull` treo rồi thất bại | Đã đặt `http.version HTTP/1.1` và hai tham số tốc độ tối thiểu, khắc phục được. Nếu tái diễn thì chuyển remote sang SSH — cả cổng 22 lẫn 443 của SSH đều thông |

---

## Quyết định đã chốt

Ghi vắn tắt để tránh bàn lại. Chi tiết và lý do xem `docs/adr/`.

| Quyết định | Ghi chú |
|---|---|
| Bài toán nghiệp vụ: Cổng vận hành yêu cầu nội bộ | Đã trình giảng viên, được duyệt |
| Điểm sáng tạo: vòng phản hồi tự soi quy trình (khai phá quy trình) | Đã trình giảng viên, được duyệt |
| Bộ công nghệ nền: Next.js + FastAPI + PostgreSQL + Docker | Thống nhất với giảng viên |
| Giấy phép sản phẩm: MIT | |
| Mô hình nhánh ba tầng: nhánh công việc → `dev` → `main` | |
| Cách hợp nhất: squash cho chặng vào `dev`, merge commit cho chặng lên `main` | Squash sai chặng sẽ hỏng nhật ký thay đổi |
| Nguyên tắc AI chỉ gợi ý, con người quyết định | Theo góp ý của giảng viên |
| Thứ tự xây dựng: hoàn thiện luồng thủ công trước, gắn AI sau | Theo góp ý của giảng viên |
| Tệp khóa phiên bản bắt buộc commit, không đưa vào `.gitignore` | Ảnh hưởng tiêu chí PoF mục 4 và 5 |
| Toàn bộ tài liệu kỹ thuật công khai, không gitignore | Ảnh hưởng tiêu chí chấm số 10 và PoF mục 6 |
| Luồng nghiệp vụ chốt bằng sơ đồ trạng thái | Mười trạng thái, ba lối phê duyệt, Poka-yoke khi hủy, tự leo thang SLA — xem `docs/process-flow.md` |
| `PROJECT_STATE.md` do navigator cập nhật theo tuần | Thành viên không sửa trong PR công việc — xem `CONTRIBUTING.md` mục 2.5 |
| `H` — Keycloak `26.7.3` làm nền tảng định danh | Nạp trọn realm từ tệp JSON nên đổi vai trò là đổi dữ liệu — ADR-0001 |
| `core` — SeaweedFS `4.45` làm kho lưu trữ đối tượng | Garage là bản lùi mặc định, MinIO là bản lùi có điều kiện — ADR-0002 |
| `D` — Apache Superset `6.1.0` làm nền tảng BI | Metabase bị loại vì khóa tính năng nhúng sau giấy phép trả phí — ADR-0003 |
| `P` — **tự viết engine máy trạng thái**, không lắp ghép | Theo ý kiến giảng viên: engine không phải nơi tạo giá trị, và Flowable không giúp giảm việc vì nhật ký vẫn phải tự viết — ADR-0004 |
| Mọi lần đổi trạng thái đi qua **một cửa duy nhất** | Điều kiện bảo đảm nhật ký sự kiện không thủng — `ARCHITECTURE.md` mục 6.1 |
| Kiến trúc lai cho tầng trình bày | Buồng lái vận hành **tự viết** trong cổng; bảng điều khiển phân tích **lắp ghép** bằng Superset — ADR-0003 |
| Định danh vai trò và trạng thái viết bằng tiếng Anh | Nhãn hiển thị và tên hoạt động trong nhật ký viết tiếng Việt — theo `ARCHITECTURE.md` mục 8.3 |
| Lược đồ và dữ liệu khởi tạo **để tách nhau** | Lược đồ ở `infra/postgres/init/` vì thuộc kiến trúc; dữ liệu ở `infra/seed/` vì là phần doanh nghiệp triển khai sẽ sửa |
| Nhật ký sự kiện **chỉ ghi thêm**, chặn bằng trigger ở tầng cơ sở dữ liệu | Superset và mọi kết nối `psql` đều đi vòng qua tầng ứng dụng, nên ràng buộc phải đặt dưới cùng. Lịch sử sửa được thì không còn là lịch sử |
| **Tạo hồ sơ không sinh sự kiện** | Không phải một lần *chuyển* trạng thái, và ghi sự kiện ở đó buộc phải bịa một mã hoạt động không có trong bảng quy tắc. Mốc bắt đầu là cột `created_at` |
| Phòng ban lấy từ **nhóm** Keycloak, không từ thuộc tính người dùng | Đúng ngữ nghĩa, có sẵn giao diện quản lý, cho phép một người thuộc nhiều phòng. Tiền tố đường dẫn nhóm là cấu hình được |
| Dịch vụ **tự kiểm chữ ký token cục bộ** qua JWKS | Keycloak nằm ngoài đường đi nóng — ADR-0001 |
| Token **không bao giờ tới trình duyệt** | Cổng giữ trong cookie `httpOnly` đã mã hóa, tự gắn vào header khi gọi dịch vụ. Khuôn mẫu cổng chặn trước |
| `openid-client` thay vì `next-auth` | Bản cài đặt được OpenID Foundation chứng nhận, MIT, chạy phía máy chủ; `next-auth` v5 còn beta |
| Thời gian ở `awaiting-info` **không tính** vào SLA, nhưng ghi riêng tổng thời gian dừng | Người xử lý không bị phạt khi người tạo chậm; tổng thời gian dừng để khai phá quy trình phát hiện lạm dụng. **Chờ giảng viên xác nhận** |
| Trạng thái nào chạy đồng hồ SLA là **dữ liệu**, không phải mã | Cột `states.sla_running` trả lời cả hai câu: đồng hồ bắt đầu từ đâu và dừng ở đâu |
| Trường quyết định chỉ đặt được ở cạnh có ràng buộc quản nó | Người xử lý không tự nâng được mức ưu tiên việc của mình — #78, `ARCHITECTURE.md` mục 7 |
| Giao người xử lý là **tùy chọn** | Ngoài đời người trong phòng hay tự chia việc; hồ sơ chưa giao ai vẫn thuộc cả phòng. Navigator chốt 23/09 |
| Leo thang lại có **khoảng ân hạn**, không cấp hạn mới | Hồ sơ vẫn được ghi nhận quá hạn; người vừa được giao lại có ân hạn trước khi bị leo thang lần nữa. Ân hạn là dữ liệu theo loại yêu cầu — #94 |
| Bổ sung thông tin xong thì **về đúng chỗ đã hỏi** | Hỏi ở *Đã gửi* về *Đã gửi*, trưởng phòng hỏi thì về *Chờ phòng ban xác duyệt*, người xử lý hỏi thì về *Đang xử lý* — #79 |
| Mở lại khi chưa đạt: **không giới hạn số lần, không cấp hạn mới** | Navigator chốt 23/09. Giữ hai cạnh từng đánh dấu `[CHỜ XÁC NHẬN]` — `classified → closed` và `completed → in-progress`; gỡ nhãn ở #102 |
| Hồ sơ bị phòng ban trả **giữ phòng cũ** tới khi điều phối chọn lại | Nhật ký ghi đủ lần đổi phòng nhờ cột `changes` — #100 |
| Lý do *Từ chối vì sai chuyên môn* **bắt buộc** | Là cờ `requires_note` trong dữ liệu |
| **Ranh giới máy trạng thái** — ADR-0005 | Thao tác đổi hồ sơ — trạng thái, trường quyết định, nội dung — đi qua cửa chuyển trạng thái; lời nhắn đi bảng riêng. Người gửi sửa được nội dung khi hồ sơ chưa tới phòng ban. Giảng viên duyệt 24/09 |
| Mức ưu tiên vẫn chỉ điều phối viên đặt | Ví dụ của giảng viên ở #81 có nhắc người gửi đổi mức ưu tiên; nhóm giữ ràng buộc Poka-yoke và đã báo lại |
| Nhịp phát hành: **mỗi issue một pull request `dev → main`** | Từ 22/09. Issue đóng ngay; nhật ký thay đổi vẫn tách đúng từng mục |
| Mọi trợ lý AI đọc chung một bộ quy tắc | `AGENTS.md` trỏ về `CLAUDE.md`, để Antigravity và Codex cũng không tự commit — #117 |

---

## Ghi chú kỹ thuật đáng nhớ

Những phát hiện trong quá trình làm, ghi lại để không phải điều tra lại.

**Tệp `"use server"` chỉ được xuất ra hàm bất đồng bộ**

Xuất kèm một hằng số hay một đối tượng sẽ làm trang trả 500 với thông điệp
`A "use server" file can only export async functions, found object`. Lý do: mọi thứ tệp
đó xuất ra đều trở thành một điểm cuối gọi được từ trình duyệt, mà một đối tượng thì
không phải điểm cuối.

**Điểm nguy hiểm: `next build` báo thành công.** Lỗi chỉ nổ ra lúc chạy, khi một thành
phần phía trình duyệt nạp tệp đó. Nghĩa là trang vẫn dựng xong, vẫn lên ảnh chứa, rồi
hỏng ngay lần đầu người dùng mở. Kiểu kiểm tra duy nhất bắt được nó là mở trang thật.

Cách làm đúng: để hằng số và kiểu dữ liệu ở một tệp riêng không mang chỉ thị đó — xem
`frontend/app/yeu-cau/ket-qua.ts`.

**Không tin cách `Intl` xếp ngày theo địa phương `vi-VN`**

Thứ tự và dấu phân cách đổi giữa các phiên bản thư viện ICU. Bản ICU trong ảnh chứa
`node:24` hiện cho ra `08:29 17-09` — giờ đứng trước ngày, dấu phân cách là gạch ngang,
không phải `17/09 08:29` như người Việt quen đọc.

Cách làm đúng: lấy từng phần bằng `formatToParts` rồi tự ghép. Con số sẽ không đổi chỗ
khi ai đó nâng cấp ảnh nền — xem `frontend/lib/dinh-dang.ts`.

Vẫn phải nêu `timeZone: "Asia/Ho_Chi_Minh"` tường minh ở mọi chỗ. Ảnh chứa chạy giờ UTC,
nên bỏ tham số đó đi là mọi mốc thời gian hiện ra lệch bảy tiếng — một lỗi âm thầm, chỉ
lộ khi có người đối chiếu với đồng hồ thật.

**Chạy thử cụm mà không đụng dữ liệu của người khác**

Dùng một dự án Compose tách riêng: `docker compose -p dxlab-kiem-tra ... up -d`. Volume
của nó mang tiền tố `dxlab-kiem-tra_`, khác hẳn `dx-os-lab_` của cụm thật, nên
`down -v` trên cụm thử không bao giờ xóa nhầm dữ liệu đang dùng.

Tiếng Việt **không được đi qua cờ dòng lệnh** trên Windows — `curl -d '{"title":"Thử"}'`
sẽ gửi lên `Th? t?o`. Đặt chuỗi vào một tệp `.py` mã hóa UTF-8 rồi chạy tệp đó.

`docker exec <ảnh> python /tmp/x.py` trên Git Bash bị đổi đường dẫn thành
`/app/C:/Users/...`. Thêm `MSYS_NO_PATHCONV=1` vào trước lệnh.

**Cách chạy git-cliff trên máy này**

`winget` bản 1.2 trên máy navigator **hỏng nguồn** (`Data required by the source is
missing`) nên không cài được git-cliff. Máy cũng không có cargo, scoop lẫn choco.

Đường vòng đã dùng thành công — chạy qua npm mà không cài cố định:

```powershell
npx --yes git-cliff@latest --tag v0.2.0 --output CHANGELOG.md
```

Bản `v0.2.0` sinh bằng `git-cliff 2.13.1` theo cách này.

**Cảnh báo commit bị bỏ qua khi sinh nhật ký thay đổi**

git-cliff sẽ báo `N commit(s) were skipped due to parse error(s)`. Công thức đối chiếu:

```
N = số merge commit trên nhánh đang sinh
  + 1  (Initial commit)
  + số commit squash lỡ mang tiêu đề bắt đầu bằng "Merge"
```

**Đếm merge commit trên đúng nhánh đang sinh nhật ký.** Nhánh `main` có nhiều merge commit
hơn `dev` vì nó tích lũy thêm mỗi lần phát hành — đếm nhầm nhánh là ra con số sai.

Ở lần sinh `v0.2.0` (12/09/2026), `N = 14` = 12 merge commit trên `dev` + 1 `Initial commit`
+ 1 commit hỏng ở PR #49. Số hạng cuối là **nợ vĩnh viễn**: PR #49 bị sót bước sửa ô commit
message nên commit squash mang tiêu đề `Merge pull request #49 from ...`, và `cliff.toml` có
luật bỏ qua mọi commit bắt đầu bằng `Merge`. Hậu quả: mục cập nhật trạng thái tuần 5 không
bao giờ xuất hiện trong nhật ký. Không sửa được vì commit đã lên `main`.

Nếu `N` lớn hơn công thức trên thì mới là có commit viết sai chuẩn mới. Kiểm bằng
`npx git-cliff --unreleased -vv` rồi đối chiếu `git log --oneline`.

Nguyên nhân các commit này không được luật `skip` trong `cliff.toml` xử lý: tùy chọn
`filter_unconventional` loại chúng ở giai đoạn phân tích, trước khi tới bước phân nhóm.
Cảnh báo vô hại.

**Gõ tiếng Việt có dấu trong commit trên Windows**

PowerShell làm hỏng ký tự có dấu khi truyền qua cờ `-m`. Giải pháp: cấu hình
`git config --global core.editor "code --wait"` rồi dùng `git commit` **không kèm
`-m`**. Visual Studio Code mở ra, gõ nội dung có dấu bình thường.

Cách khác khi làm nhiều commit liên tiếp hoặc không muốn mở trình soạn thảo: ghi nội
dung vào một tệp UTF-8 (không BOM) rồi `git commit -F <đường-dẫn-tệp>`. Cách này tránh
cả việc PowerShell làm hỏng dấu lẫn tranh chấp khi mở trình soạn thảo.

Khi đọc tệp có dấu bằng PowerShell, thêm `-Encoding UTF8`.

**Issue chỉ đóng khi commit tới nhánh mặc định**

GitHub chỉ tự đóng issue khi commit chứa `Closes #N` đi vào `main`. Do quy trình đi
qua `dev`, issue sẽ mở cho tới lần hợp nhất `dev → main`. Đây là hành vi bình thường.
Dùng mốc công việc để theo dõi tiến độ tuần thay vì đếm issue đã đóng.

**Xóa nhánh sau khi squash merge**

Squash merge tạo commit với mã băm mới, nên Git không nhận ra nhánh đã được hòa nhập
và `git branch -d` sẽ từ chối. Dùng `git branch -D` viết hoa.

**Kiểm giấy phép phải soi trong ảnh chứa, đừng tin siêu dữ liệu kho mã**

Tuần 4 gặp ba tình huống mà siêu dữ liệu trên kho mã cho kết luận sai hoặc thiếu:

- **n8n** — kho báo `NOASSERTION`. Soi vào gói thì `package.json` khai báo
  `LicenseRef-n8n-sustainable-use`, và ảnh phát hành mang **122 tệp `.ee.`** là bản cài
  đặt thương mại thật. Loại.
- **Camunda 8** — GitHub không nhận diện được giấy phép nào. Ảnh chứa mang **hai** tệp
  cùng lúc, trong đó `CAMUNDA-LICENSE-1.0.txt` chỉ cho dùng ở môi trường phi sản xuất,
  và ứng dụng còn tự đòi `CAMUNDA_LICENSE_KEY` lúc khởi động. Loại.
- **Metabase** — cũng báo `NOASSERTION` nên ban đầu bị nghi giống n8n. Nhưng soi vào jar
  thì 71 mục "enterprise" đều là cơ chế điều phối AGPL, **không phải mã tính năng**.
  Ảnh nguồn mở đúng là AGPL sạch. Hợp lệ.

Bài học: hai dự án cùng bị báo `NOASSERTION` có thể ở hai tình trạng pháp lý hoàn toàn
khác nhau. Luôn kiểm trong ảnh chứa sẽ được phát hành, vì đó mới là thứ đi kèm sản phẩm.

**Loại ứng viên bằng thực nghiệm, không bằng suy luận từ tài liệu**

Temporal có giấy phép MIT sạch nên không loại được bằng giấy phép. Phép thử quyết định:
tạo một hồ sơ mang tên quy trình mà Temporal chưa biết định nghĩa. Nó **vẫn nhận** nhưng
hồ sơ treo vĩnh viễn, vì định nghĩa nằm trong mã Worker chứ không nằm trong Temporal.
Giao diện dòng lệnh cũng không có lệnh nạp định nghĩa dạng dữ liệu. Kết luận vững hơn
hẳn so với việc chỉ đọc tài liệu rồi phán đoán.

**Vài cạm bẫy cấu hình đã gặp**

- **SeaweedFS gửi thống kê ra ngoài theo mặc định** về `telemetry.seaweedfs.com` mỗi 24
  giờ. Cấu hình sản phẩm bắt buộc thêm `-master.telemetry=false`
- **Ảnh `apache/superset` không kèm trình điều khiển PostgreSQL.** Phải cài
  `psycopg2-binary` vào `/app/.venv`, và môi trường đó **không có `pip`** — dùng `uv`.
  Bản sản phẩm cần ảnh chứa dẫn xuất
- **Metabase chạy JVM không đặt `-Xmx`** nên lấy dần bộ nhớ theo mức sẵn có: trong một
  phiên đo tăng từ 1,56 lên 1,98 GiB

**Ba cạm bẫy khi ghép ba nền tảng vào một cụm Compose**

Cả ba chỉ lộ ra khi dựng thật ở #38, không tài liệu nào nói trước:

| Nền tảng | Cạm bẫy | Cách xử lý |
|---|---|---|
| **SeaweedFS** | Cờ tắt telemetry là `-master.telemetry=false`, **không phải** `-telemetry=false` như bốn tài liệu của nhóm từng ghi. Đặt sai thì container khởi động lại vô tận | Đã sửa cả bốn chỗ. Dòng gợi ý trong nhật ký của SeaweedFS ghi thiếu tiền tố `master.` — đừng chép nguyên văn |
| **Superset** | **Không đọc biến môi trường tuỳ ý.** Đặt `SQLALCHEMY_DATABASE_URI` qua biến thì bị bỏ qua âm thầm và nó lặng lẽ dùng SQLite. Dấu hiệu duy nhất là một dòng `Context impl SQLiteImpl` lẫn trong nhật ký | Nạp cấu hình từ tệp Python trỏ bởi `SUPERSET_CONFIG_PATH` — xem `infra/superset/superset_config.py` |
| **Superset** | **Ảnh gốc không tự khởi tạo.** Không chạy `db upgrade` lẫn `fab create-admin`. Nguy hiểm vì điểm cuối sức khoẻ vẫn trả HTTP 200 và container vẫn báo `healthy`, nhưng không ai đăng nhập được | Thêm điểm vào riêng — xem `infra/superset/docker-entrypoint.sh` |

Thêm một chi tiết về môi trường ảo của Superset: nó nằm ở `/app/.venv` và **không có `pip`**
trong đó, nên phải cài gói bằng `uv`.

**JSON không mang được header giấy phép SPDX**

Đã thử nhét header vào một trường `_comment` trong tệp realm của Keycloak. Kết quả: Keycloak
**từ chối nạp realm** vì trình phân tích của nó bác mọi trường lạ. Hai tệp JSON trong
`infra/` vì vậy không có header — JSON không có cú pháp chú thích, đây là giới hạn của định
dạng chứ không phải sơ suất.

**Sinh dữ liệu ảo: quyết định trước rồi co giãn, đừng cộng dồn ngẫu nhiên**

Bản sinh dữ liệu đầu tiên của #21 cho tỷ lệ vi phạm SLA **80,3 %** vì thời gian được cộng
dồn ngẫu nhiên qua từng bước, khiến tổng luôn vượt ngưỡng. Bảng điều khiển hiện 80 % vi
phạm trông như hệ thống hỏng, và chỉ số mất hết biến thiên để so sánh.

Cách đúng: quyết định trước mỗi hồ sơ có vi phạm hay không, rồi **co giãn toàn bộ chuỗi
sự kiện** cho khớp tổng thời gian mục tiêu. Kết quả 19,2 %, trung vị nằm dưới ngưỡng ở
mọi loại yêu cầu.

**Đừng bật `delete_branch_on_merge` khi còn dùng mô hình nhánh ba tầng**

Cấu hình này của GitHub xóa **nhánh nguồn** sau mỗi lần hợp nhất. Với mô hình hai tầng
(nhánh công việc → `main`) thì rất tiện. Nhưng dự án dùng ba tầng, mà ở chặng `dev → main`
thì **nhánh nguồn chính là `dev`** — nên nó xóa luôn nhánh tích hợp.

Đã xảy ra thật ngày 07/09: bật cấu hình để dọn 13 nhánh cũ, merge một đợt phát hành, và
`dev` biến mất khỏi máy chủ. Không mất dữ liệu vì `dev` không có commit nào mà `main`
thiếu, khôi phục bằng `git merge --ff-only main` rồi đẩy lên lại.

Bật lại được **sau khi kho chuyển công khai**, vì lúc đó quy tắc bảo vệ nhánh mới có hiệu
lực và tùy chọn *Allow deletions: Tắt* sẽ chặn được. Hiện kho còn riêng tư trên gói miễn
phí nên quy tắc bảo vệ chưa áp dụng.

**Năm biến thể của lỗi mã hóa tiếng Việt trên Windows**

Cùng một gốc vấn đề nhưng lộ ra ở ba chỗ khác nhau, lần nào cũng mất thời gian truy:

| Chỗ hỏng | Ví dụ đã gặp |
|---|---|
| Tiếng Việt qua **tham số** dòng lệnh | `git commit -m "..."` làm hỏng dấu |
| Tiếng Việt ở **đầu ra** stdout | `python -c "print(...)"` báo `UnicodeEncodeError` |
| Tiếng Việt ở **đầu ra lệnh ngoài đọc ngược vào PowerShell** | Kịch bản tạo issue tra cứu milestone theo tiêu đề, `gh api ... \| Out-String` trả về chuỗi hỏng dấu nên tra không khớp, milestone bị bỏ qua âm thầm |
| Tiếng Việt trong **tệp `.ini`** | `alembic.ini` và `pytest.ini` được đọc qua `configparser` với mã hóa cục bộ của hệ điều hành. Trên Windows là cp1252, nên một chữ có dấu làm mọi lệnh `alembic` chết ngay lúc khởi động. Trong container thì không lộ ra vì Linux dùng UTF-8 — lỗi chỉ đánh vào máy thành viên |
| Tiếng Việt trong **commit message qua Bash heredoc** | Vỡ dấu. Luôn ghi nội dung vào tệp UTF-8 rồi để công cụ đọc tệp |

**Nguyên tắc chung**: đừng để tiếng Việt đi qua ranh giới tiến trình. Ghi vào tệp UTF-8
rồi để công cụ đọc tệp — `git commit -F`, `gh api --input`, `--body-file`. Khi buộc phải
đọc ngược đầu ra lệnh ngoài, đặt trước:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

Tham chiếu tới đối tượng bằng **số** thay vì tên tiếng Việt luôn an toàn hơn — ví dụ gán
milestone bằng `-F milestone=4` thay vì bằng tiêu đề. Với tệp `.ini` thì không có cách
nào cứu: viết chú thích bằng tiếng Anh và để phần giải thích sang tệp `.py` bên cạnh.

**Git xóa mọi dòng commit message mở đầu bằng `#`**

Git coi chúng là chú thích. Dự án tham chiếu issue liên tục nên rất dễ dính: một dòng
thân commit xuống hàng đúng chỗ số issue là mất nguyên dòng đó, để lại một câu cụt.

Đã xảy ra ở commit của #62 ngày 15/09. Cách tránh: soạn lại câu sao cho không dòng nào
mở đầu bằng `#`, ví dụ `issue #43, #44 và #45...`. Dấu `#` giữa dòng vô hại, nên
`Closes #62` ở footer không sao. Sau khi commit, soát bằng `git log -1 --format='%b'`.

**Chữ `Merge` ở đầu tiêu đề: sai ở một chặng, đúng ở chặng kia**

Hai chặng hợp nhất đòi hai thứ ngược nhau, và đây là chỗ dễ lẫn nhất trong cả quy trình:

| Chặng | Cách merge | Tiêu đề đúng |
|---|---|---|
| nhánh công việc → `dev` | Squash and merge | `<loại>(<phạm vi>): <mô tả> (#số PR)` — thấy chữ `Merge` là **sai** |
| `dev` → `main` | Create a merge commit | `Merge pull request #N from ...` — chữ `Merge` là **đúng** |

`cliff.toml` có luật `{ message = "^Merge", skip = true }`, nên commit hợp nhất ở chặng
hai bị bỏ qua đúng như mong muốn, còn commit squash ở chặng một mang chữ đó sẽ **biến
mất khỏi nhật ký thay đổi**.

**Cách nhận ra chọn nhầm cách merge**: cấu hình kho đặt `merge_commit_title: MERGE_MESSAGE`
và `squash_merge_commit_title: COMMIT_OR_PR_TITLE`. Nên ở chặng `dev → main`, nếu ô
Commit message hiện tiêu đề dạng `feat(...): ... (#68) (#69)` thay vì `Merge pull request`,
đó là đang chọn **Squash** chứ không phải merge commit — bấm Cancel và đổi lại. Nhãn nút
"Confirm merge" không phân biệt được. Đã suýt sai ở PR #69 ngày 16/09.

**Một Keycloak, hai địa chỉ**

Trình duyệt đi qua `localhost:8080`, container đi qua `keycloak:8080`. Không cố định
`KC_HOSTNAME` thì token lấy theo hai đường mang hai giá trị `iss` khác nhau, và dịch vụ
từ chối một nửa số token tùy đường đi.

Cấu hình đang dùng: `KC_HOSTNAME` cố định địa chỉ công khai, `KC_HOSTNAME_BACKCHANNEL_DYNAMIC`
cho phép tài liệu discovery trả địa chỉ nội bộ. Keycloak tự tách đúng hai chiều —
`authorization_endpoint` và `end_session_endpoint` ra địa chỉ công khai cho trình duyệt,
`token_endpoint` và `jwks_uri` ra địa chỉ nội bộ cho máy chủ. Không phải viết dòng nào
để đổi URL.

Hệ quả kèm theo: `openid-client` kiểm rằng `issuer` đọc được phải khớp URL đã gọi, nên
hàm `discovery()` sẽ báo lỗi với cặp địa chỉ lệch nhau này. Phải tự tải tài liệu rồi
dựng `Configuration` thẳng từ siêu dữ liệu — xem `frontend/lib/oidc.ts`.

**Trong container, `request.url` trỏ về `0.0.0.0`**

Máy chủ Next.js nghe ở `0.0.0.0:3000`, nên `new URL("/", request.url)` cho ra
`http://0.0.0.0:3000/` và trình duyệt đi tới đó sẽ lạc. Địa chỉ công khai của cổng phải
khai riêng bằng `PORTAL_PUBLIC_URL`, không được suy ra. Cùng một gốc vấn đề với chuyện
`KC_HOSTNAME` ở trên.

**Bộ đếm milestone của GitHub tính cả pull request**

Milestone Tuần 6 báo *10 đã đóng* trong khi chỉ có 5 issue. Năm cái còn lại là các pull
request mang nhãn mốc. Không phải lỗi, nhưng đừng đọc con số đó thành tiến độ — lọc bằng
`is:issue is:closed milestone:"..."` mới ra số thật.

**Đo chất lượng bộ kiểm thử bằng phép thử đột biến**

Bộ kiểm thử xanh không chứng minh nó có răng. Cách kiểm: cố tình gỡ một bước trong mã
rồi xem có đúng những bài liên quan đổ không.

Đã áp dụng ba lần trong tuần 6 — gỡ bước chạy ràng buộc làm đổ đúng sáu bài Poka-yoke,
gỡ bước ghi nhật ký làm đổ đúng tám bài, gỡ phần kế toán đồng hồ làm đổ đúng ba bài.
Lần thứ ba phát hiện một bài **đậu giả**: nó khẳng định đồng hồ đã dừng, mà khi gỡ kế
toán thì đồng hồ vốn chưa bao giờ chạy. Đã siết lại bằng cách khẳng định trạng thái
*trước* đã, rồi mới khẳng định trạng thái *sau*.

Tuần 7 đưa phép thử này thành thói quen: mọi issue từ #78 chạy đột biến trên một cụm thử
cách ly, dựng bằng tên dự án Compose riêng để không đụng dữ liệu của ai. Phép đột biến
sống sót thì hoặc thêm bài, hoặc **gỡ đoạn mã mà nó chỉ ra là thừa** — ví dụ ở #99, một
phép loại trạng thái kết thúc gỡ đi không bài nào đổ, vì trạng thái kết thúc vốn không
bao giờ thỏa điều kiện còn lại. Một điều kiện: kết quả đột biến chỉ có giá trị khi bản
gốc xanh ngay trước đó. Để sót dữ liệu thử trong cơ sở dữ liệu làm bài đỏ sẵn, và mọi
phép đột biến sau đó đều "bị bắt" giả.

**Trình duyệt lặng lẽ bỏ cookie vượt 4096 byte** (#87)

Cookie phiên chứa cả bộ token của Keycloak vượt trần, và trình duyệt không báo lỗi gì —
nó chỉ không lưu. Người dùng đăng nhập xong vẫn bị coi là chưa đăng nhập. Bộ kiểm thử
không bắt được vì nó tự đúc cookie thay vì đi đường đăng nhập thật. Bài học rộng hơn:
**kiểm tính năng cần đăng nhập bằng đúng luồng OIDC thật**, không bằng phiên tự dựng.

**`timeout` của `urllib` không bao gồm phân giải tên miền** (#84)

Gọi Admin API của Keycloak với `timeout=3` mà treo tám giây khi tên máy không phân giải
được. Hạn chót thật phải đặt bên ngoài lời gọi — chạy trong `ThreadPoolExecutor` rồi chờ
kết quả có hạn. Xem `backend/app/auth/directory.py`.

**Bài kiểm thử đếm số lượng phải so chênh lệch, không so tuyệt đối**

Cụm dùng để chạy bài thường đã có sẵn hồ sơ từ lúc thử tay. Bài khẳng định "nhóm này có
đúng một hồ sơ" sẽ đỏ trên cụm của navigator dù mã đúng. Đếm trước khi dựng cảnh, rồi
khẳng định số tăng thêm — xem `_dem_nhom` trong `backend/tests/test_department.py`.

**Lỡ commit lên `dev` ở máy thay vì nhánh công việc**

Gặp ngày 24/09 ở #98: chạy `git checkout dev` để đồng bộ rồi quên quay lại. Chưa push
`dev` thì không mất gì — chuyển commit sang nhánh công việc bằng `merge --ff-only`, rồi
dời `dev` ở máy về `origin/dev`. Phòng từ đầu: kiểm `git branch --show-current` ngay trước
lệnh commit. Cả hai bộ luật trợ lý đều đã ghi cách cứu.

---

## Cách cập nhật tệp này

Cuối mỗi tuần, hoặc mỗi khi cắt bản phát hành:

1. Cập nhật bảng **Ảnh chụp nhanh**
2. Chuyển các mục từ **Đang làm** sang **Đã hoàn thành**, ghi số issue tương ứng
3. Rà soát lại **Việc tiếp theo**, xếp lại thứ tự nếu ưu tiên thay đổi
4. Cập nhật **Đang vướng** — bỏ mục đã giải quyết, thêm mục mới
5. Bổ sung vào **Quyết định đã chốt** nếu có quyết định mới
6. Bổ sung **Ghi chú kỹ thuật** nếu phát hiện điều gì đáng nhớ

Viết lại tệp dựa trên **danh sách issue đã đóng theo mốc công việc**, không cộng dồn
từng dòng và không viết theo trí nhớ. Cam kết bằng một commit riêng với tiền tố
`docs(state):`.
