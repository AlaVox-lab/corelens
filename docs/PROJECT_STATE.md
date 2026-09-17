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
| Cập nhật lần cuối | 2026-09-17 |
| Phiên bản hiện tại | `v0.3.0`, cắt ngày 16/09. `main` đi trước thẻ một commit tài liệu |
| Giai đoạn | **Giai đoạn 2 đang chạy** — `H` và `P` đã thông đầu-cuối, có giao diện người dùng thật |
| Mốc công việc đang chạy | Tuần 6 — Engine máy trạng thái và tích hợp định danh, hạn 20/09 |
| Trạng thái kho mã | Riêng tư, sẽ chuyển công khai trước khi nộp bài |
| Có mã nguồn ứng dụng chưa | **Có.** `backend/` FastAPI và `frontend/` Next.js đều chạy; cụm gồm **sáu dịch vụ** |
| Issue đang mở | **4** — #45, #46, #47, #48 (chưa kể việc tồn đọng của #44, xem mục Việc tiếp theo) |
| Quyết định kiến trúc đã chốt | **4** — Keycloak `H` · SeaweedFS `core` · Superset `D` · tự viết engine `P` |
| Còn chờ khảo sát | 3 — quản trị tri thức `H` (#46), véc-tơ và LLM `I` (#47), khai phá quy trình `I` (#48) |
| Bộ kiểm thử tự động | **68 bài**, chạy trên PostgreSQL thật. Bốn bài tích hợp Keycloak tự bỏ qua nếu chưa dựng dịch vụ định danh |
| Tổng bộ nhớ toàn cụm | **1,55 GiB**, đo thật trên cụm sáu dịch vụ |
| Số ngày còn lại tới chấm kho mã | **82 ngày** (07/12/2026) |
| Số ngày còn lại tới khi công bố đề thi | khoảng **46 ngày** (tháng 11/2026) |

**Một câu tóm tắt trạng thái**: nhân viên đăng nhập bằng Keycloak → gửi yêu cầu qua
biểu mẫu ba bước → engine tra bảng quy tắc và chạy ràng buộc Poka-yoke → ghi nhật ký sự
kiện → bộ quét nền tự leo thang khi quá hạn → người gửi theo dõi toàn bộ đường đi của
hồ sơ trên dòng thời gian. Toàn bộ vòng đó chạy được trên máy sạch bằng một lệnh.

Thứ còn thiếu là **phía bên kia của quy trình**: điều phối viên, người xét duyệt và
người xử lý vẫn chưa có màn hình nào. Họ thao tác được qua API nhưng chưa qua giao diện
— đó là #45.

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

## Đang làm

Không có công việc nào đang dở. Milestone *Tuần 6*, hạn 20/09, còn bốn issue:

| Issue | Ưu tiên | Việc | Ghi chú |
|---|---|---|---|
| **#45** | **P2** | Buồng lái vận hành | **Đã mở khóa.** Cần thiết kế giao diện riêng — dùng `khong-dung/` của #44 làm tham khảo |
| #46 | P2 | Khảo sát quản trị tri thức cho `H` | Độc lập với mã nguồn — giao được cho `@Senning-Dd` |
| #47 | P3 | Khảo sát véc-tơ và khung LLM cho `I` | |
| #48 | P3 | Khảo sát thư viện khai phá quy trình cho `I` | |

**Bốn issue trong ba ngày còn lại vẫn là quá tay.** Ba khảo sát cuối mỗi cái tương đương
một tuần việc — nhìn lại #19, #20, #21 thì rõ: liệt kê ba ứng viên, kiểm giấy phép bên
trong ảnh chứa phát hành, dựng thử bằng Docker, đo tài nguyên, viết tài liệu và một ADR.
Làm vội cả ba sẽ cho ra tài liệu hời hợt, mà đây đúng là loại tài liệu ăn điểm.

Giảng viên cũng đã chốt: ba khảo sát này **làm sớm để biết ràng buộc, chưa tích hợp**
cho tới khi luồng chính ổn định. Không có gì gấp.

**Hai điểm suy luận trong `process-flow.md` mục 8 vẫn chưa được giảng viên xác nhận**:
cạnh `classified → closed` khi không phòng nào nhận, và cạnh `completed → in-progress`
khi người tạo mở lại. Cả hai đã đi vào dữ liệu khởi tạo và đánh dấu `[CHỜ XÁC NHẬN]` —
thầy bác thì xóa một dòng dữ liệu, không đụng mã.

**Một quyết định nghiệp vụ mới cần thầy xác nhận**: thời gian hồ sơ nằm ở
`awaiting-info` **không tính** vào SLA, nhưng tổng thời gian dừng vẫn được ghi riêng.
Cũng là một cờ trong dữ liệu — xem `states.sla_running`.

---

## Việc tiếp theo

Toàn bộ việc kỹ thuật đã có issue, xếp theo đường tới hạn. Chi tiết từng giai đoạn xem
`ROADMAP.md`.

### Đường tới hạn — chỉ còn một mắt xích

Theo chiến lược giảng viên chốt: đi sâu một luồng trước, rồi mới mở rộng.

```
#37 ─► #40 ─► #41 ─┬─► #42        (xong)
#38 ─► #62 ────────┴─► #43        (xong)
                       │
                       └─► #44 ─► #45   (còn #45)
```

Đường tới hạn chỉ còn **một mắt xích**. Một nửa quy trình đã có giao diện — nửa của
người gửi yêu cầu. Nửa còn lại, của điều phối viên và phòng ban, là #45.

| Issue | Ưu tiên | Việc | Chặn bởi |
|---|---|---|---|
| #45 | P2 | Buồng lái vận hành | **đã mở khóa** |

**#45 kế thừa được nhiều hơn tưởng.** Bộ token màu, nhãn trạng thái mang dấu hiệu, cách
định dạng thời gian theo múi giờ Việt Nam, lớp gọi dịch vụ có xử lý lỗi — tất cả đã nằm
trong `frontend/lib/` và `frontend/components/`. Bảng ánh xạ mã lỗi engine sang mã HTTP
(`MA_HTTP` trong `backend/app/workflow/routes.py`) cũng viết sẵn để dùng lại.

Khuôn mẫu bắt buộc giữ, ghi ở `ARCHITECTURE.md` mục 7.2: **nút bấm dựng từ
`allowed_transitions` của API, không từ một bảng trong mã nguồn giao diện**. #44 đã
chứng minh vì sao — bản thiết kế vẽ hai cái nút mà dữ liệu không cho phép.

**Một việc phải làm TRƯỚC khi viết #45**: vá lỗ hổng `CHANGEABLE_FIELDS`, xem mục Việc
tiếp theo bên dưới. Cổng #44 né được vì nó không nhận trường `changes`, nhưng buồng lái
thì bắt buộc phải nhận.

### Không chặn ai, làm khi có khoảng trống

| Issue | Ưu tiên | Việc | Giao được cho |
|---|---|---|---|
| #46 | P2 | Khảo sát hệ thống quản trị tri thức cho `H` | `@Senning-Dd` — độc lập hoàn toàn với mã nguồn |
| #47 | P3 | Khảo sát cơ sở dữ liệu véc-tơ và khung LLM cho `I` | |
| #48 | P3 | Khảo sát thư viện khai phá quy trình cho `I` | |

### Issue cần mở, sinh ra từ #44

Ba việc phát hiện trong lúc làm #44, cố ý **không** vá lén trong cùng issue:

1. **Vá lỗ hổng `CHANGEABLE_FIELDS`** — `P`, `P1`, **chặn #45**. Engine cho đặt
   `priority_code` ở **mọi** cạnh, không chỉ cạnh mang ràng buộc `set-priority`. Cổng #44
   né được bằng cách không nhận trường `changes`, nhưng buồng lái bắt buộc phải nhận, và
   khi đó người xử lý sẽ tự nâng mức ưu tiên việc của mình được. Cách vá đúng: engine chỉ
   cho đặt trường nào mà cạnh đang đi có ràng buộc tương ứng — quan hệ đó đã khai sẵn ở
   bảng `transition_guards`, không cần thêm bảng mới
2. **Mô hình hóa cạnh "quay về trạng thái trước"** — `P`, `P2`. Từ `awaiting-info` hiện
   có hai cạnh về `classified` và `in-progress`, và engine chào **cả hai** vì nó chỉ nhìn
   `from_state`. Chỉ một cái đúng: hồ sơ phải quay về nơi nó vừa rời đi. Người gửi đang
   phải tự đoán giữa hai cái nút gần như giống hệt nhau, đoán sai thì hồ sơ đi lùi thêm
   một nhịp. Đây là ràng buộc cần biết lịch sử, nên phải làm thành một `guard` mới chứ
   không sửa được bằng dữ liệu
3. **Đính kèm tệp cho yêu cầu** — `core`, `P2`. Tách khỏi #44 ngay từ đầu. SeaweedFS đã
   dựng và giới hạn kích thước đã đo ở #39, nên phần hạ tầng sẵn sàng

Hai việc nhỏ hơn, gộp vào #45 hoặc làm riêng tùy dung lượng:

4. **Tra tên người từ định danh Keycloak.** Cột `assignee_id` giữ `sub` dạng UUID, và
   dịch vụ chưa có đường tra ngược ra tên. Cổng #44 hiện không hiện trường này, vì đưa
   một dãy ký tự vô nghĩa lên màn hình thì tệ hơn là không đưa gì
5. **Ba nút không phải chuyển trạng thái** mà bản thiết kế #44 có: *Sửa nội dung*,
   *Nhắn điều phối viên*, *Hỏi tiến độ*. Đã bỏ khỏi #44 vì chúng không ứng với cạnh nào
   trong bộ quy tắc. Muốn có thì phải quyết trước: chúng là cạnh mới, hay là tính năng
   nằm ngoài máy trạng thái

### Việc vận hành, không cần issue

1. Chuyển bộ sinh dữ liệu ảo thành mã sản phẩm trong `infra/seed/`. Bản dựng thử nằm ở
   `E:\Workspace\_scratch\dx-os-lab\sinh_du_lieu.py` trên máy của navigator — sinh 1.000 hồ
   sơ bám đúng `process-flow.md`. **Lưu ý**: bộ sinh viết theo mô hình cũ bốn vai trò, cần
   cập nhật theo mười trạng thái và năm vai trò mới
2. Thiết kế giao diện cho #45 trước khi viết mã. Bảng điều khiển phân tích **không cần
   thiết kế** vì Superset tự mang giao diện
3. Thêm `CODE_OF_CONDUCT.md` — chuẩn cộng đồng nguồn mở
4. Gửi `TRO-LY-THANH-VIEN.md` cho `@NguyentimAnh` và `@Senning-Dd` — bộ luật đã cập
   nhật ngày 16/09, có thêm mục 2.7 hướng dẫn dựng hệ thống

### Chờ điều kiện

5. Tích hợp liên tục — giờ đã có cấu trúc thư mục mã nguồn và 68 bài kiểm thử, nên
   điều kiện đã đủ. Một quy trình chạy `pytest` và `next build` trên mỗi pull request
   sẽ bắt được hồi quy trước khi nó vào `dev`. #44 vừa cho một lý do cụ thể: có loại lỗi
   `next build` báo thành công nhưng trang vẫn trả 500 lúc chạy
6. Chuyển kho mã sang công khai — làm trước khi nộp bài. Khi đó quy tắc bảo vệ nhánh mới
   có hiệu lực, và **bật lại được `delete_branch_on_merge`** một cách an toàn
7. Giai đoạn đóng gói: hướng dẫn cài đặt trong `README.md`, đo hiệu năng, công bố **cấu
   hình máy tối thiểu** — giảng viên nhắc trước để nhóm không quên

---

## Đang vướng

| Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| Quy tắc bảo vệ nhánh chưa có hiệu lực | Quy trình phụ thuộc kỷ luật cá nhân thay vì ràng buộc kỹ thuật | Chuyển kho mã sang công khai. Trong lúc chờ, tuân thủ tự giác |
| Chưa chốt công cụ quản trị cơ sở dữ liệu | Chưa ảnh hưởng, chỉ là công cụ hỗ trợ | Đã trình hai phương án, chờ ý kiến giảng viên |
| **Hai điểm suy luận trong sơ đồ luồng chưa được giảng viên xác nhận** | Nếu sai thì bảng `transitions` ở #40 phải sửa theo | Xem `process-flow.md` mục 8: cạnh `classified → closed` và cạnh `completed → in-progress`. Hỏi ở buổi trao đổi tới |
| Ngân sách bộ nhớ tăng dần theo từng nền tảng | Bảng chấm đòi dựng được trên máy sạch ngày chấm | **Đo thật cả cụm sáu dịch vụ: 1,55 GiB.** Hai dịch vụ ứng dụng chỉ thêm khoảng 110 MB; phần tăng còn lại là Keycloak phình theo JVM. Đo lại sau mỗi quyết định mới |
| **Chưa có tích hợp liên tục** | 51 bài kiểm thử chỉ chạy khi ai đó nhớ chạy. Một hồi quy lọt vào `dev` sẽ không ai biết cho tới lần dựng sau | Điều kiện đã đủ — có cấu trúc thư mục và bộ kiểm thử. Dựng một quy trình chạy `pytest` và `next build` trên mỗi pull request |
| **Quyết định SLA chưa được giảng viên xác nhận** | Nếu thầy muốn tính cả thời gian chờ bổ sung vào SLA thì số liệu hiện có sẽ lệch | Hiện đặt **không tính**, nhưng ghi riêng tổng thời gian dừng. Đổi ý chỉ là bật cờ `states.sla_running` trong dữ liệu khởi tạo |
| **Lược đồ khởi tạo chỉ nạp một lần** | Ai đã có volume cũ mà kéo mã mới về sẽ gặp lỗi thiếu cột, và thông báo lỗi không chỉ ra nguyên nhân | Mỗi lần `infra/postgres/init/` hoặc `infra/seed/` đổi, cả nhóm phải `docker compose down -v` rồi dựng lại. Ghi trong mô tả pull request mỗi khi chạm hai thư mục đó |
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
