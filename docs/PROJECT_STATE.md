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
| Cập nhật lần cuối | 2026-11-11 |
| Phiên bản hiện tại | **`v0.13.0`** (11/11) — gợi ý người xử lý, hồ sơ tương tự, khuyến nghị cải tiến (#318, #319, #320). Trước đó: `v0.12.0` (11/11) mô hình ngôn ngữ cục bộ và gợi ý phân loại (#316, #317), mô hình nhiều giấy phép (#340); `v0.11.0` (10/11) khai phá quy trình thực tế (#314, #315); `v0.10.0` (09/11) nâng cấp giữ dữ liệu và thẻ gợi ý có xác nhận. `main` không có gì chưa phát hành |
| Giai đoạn | **Giai đoạn 4 — không gian `I` đã khép về chức năng** (`v0.10.0`–`v0.13.0`): khai phá quy trình thực tế, gợi ý loại, mức ưu tiên, phòng, người xử lý, hồ sơ tương tự và khuyến nghị bằng câu chữ — mọi thứ chỉ là gợi ý, tắt mô hình thì luồng thủ công vẫn chạy. Kho tri thức (#321) để ngoài phạm vi thi. Giai đoạn 5 chờ đề thi |
| Mốc công việc | **Giai đoạn 4 — Không gian I** (hạn 29/11): 21 đóng, 2 mở — issue gốc #322 và #321. **Tuần 16 — Nền tảng vận hành** (hạn 29/11): 8 đóng, 10 mở |
| Trạng thái kho mã | Riêng tư, sẽ chuyển công khai trước khi nộp bài |
| Có mã nguồn ứng dụng chưa | **Có.** `backend/` FastAPI và `frontend/` Next.js với trang chủ theo việc cần làm, cổng người gửi, buồng lái điều phối, buồng lái phòng ban, hộp thư chung, mục Báo cáo (bảng điều khiển và màn Quy trình thực tế) và màn Hệ thống cho quản trị viên; `services/khai-pha/` là dịch vụ khai phá tách riêng. Cụm mặc định gồm **bảy dịch vụ**, thêm hai dịch vụ mô hình dưới hồ sơ `tri-tue` khi bật. Bộ quy tắc mẫu có **11 trạng thái, 32 cạnh** |
| Issue đang mở | **12** — 2 ở Giai đoạn 4, 10 ở Tuần 16 (danh sách ở *Việc tiếp theo*) |
| Quyết định kiến trúc đã chốt | **7** — Keycloak `H` · SeaweedFS `core` · Superset `D` · tự viết engine `P` · ranh giới máy trạng thái (ADR-0005) · PM4Py trong dịch vụ khai phá tách riêng (ADR-0007) · llama.cpp, mô hình cục bộ và pgvector (ADR-0008) |
| Bản ghi chờ duyệt | **1** — ADR-0006 Wiki.js cho kho tri thức `H`, *Đề xuất*; nhóm đề xuất để ngoài phạm vi thi (#46, #321) |
| Còn chờ khảo sát | **0** — #47 khép mảng khảo sát cuối cùng ngày 10/10 |
| Bộ kiểm thử tự động | **650 bài** pytest ở dịch vụ ứng dụng và **176 bài** ở dịch vụ khai phá (chạy trên cả hai bộ máy), trên PostgreSQL và Keycloak thật, **tự chạy trên mỗi pull request** từ 28/10 (#241). Giao diện có **kịch bản Playwright `e2e/`** (#238): bốn vai đăng nhập thật, bốn cấu hình hiển thị, **159 bài** — chạy trên cụm thử trước khi mở pull request sửa giao diện. Số đo ở #346 trên cụm thử dựng sạch. Công cụ kiểm chứng — cụm thử cách ly, dò đăng nhập, tạo hồ sơ thử, phép thử đột biến — nằm trong `scripts/kiem_chung/` (#249). Mọi issue từ #78 đều qua phép thử đột biến |
| Tổng bộ nhớ toàn cụm | **Cụm mặc định bảy dịch vụ: 1,66 GiB**, đo lại ngày 12/11 (#247) bằng `docker stats --no-stream` sau một lượt dùng thật (không phải lúc vừa khởi động): Keycloak 700 MiB, Superset 354 MiB, khai phá 183 MiB, SeaweedFS 158 MiB, dịch vụ ứng dụng 121 MiB, cổng 95 MiB, PostgreSQL 85 MiB. Hồ sơ tùy chọn: `quet-tep` (ClamAV) **+1,03 GiB**, `thu-thu` (Mailpit) **+24 MiB**. `tri-tue` chưa đo lại lần này — vẫn theo ước tính cũ: khoảng 1,5 GB cho mô hình sinh văn bản theo trang tài liệu, ADR-0008 ước khoảng 2,8 GiB cho cả hai mô hình. Ảnh dịch vụ khai phá **982 MB** (ADR-0007). Lần đo trước: 1,4 GB lúc rảnh ngày 15/10 (#206) |
| Số ngày còn lại tới chấm kho mã | **26 ngày** (07/12/2026) |
| Số ngày còn lại tới khi công bố đề thi | **trong tháng 11/2026**, chưa công bố tới ngày 11/11 |

**Một câu tóm tắt trạng thái**: nhân viên gửi yêu cầu → điều phối viên phân loại, đặt
mức ưu tiên, chuyển về phòng ban → trưởng phòng nhận hoặc trả lại, giao người xử lý tra
từ danh bạ Keycloak → người xử lý làm, hỏi thêm người gửi khi cần → quá hạn thì tự leo
thang, có ân hạn sau khi phân công lại → người gửi xác nhận đạt hoặc mở lại — tối đa hai
lần, trong bảy ngày làm việc kể từ khi đóng, mỗi lần có hạn mới; quá giới hạn thì tạo hồ sơ
mới nối với hồ sơ cũ. Điều phối viên còn có lối **không tiếp nhận** khi không phòng nào nhận.
Dọc đường,
người gửi sửa được nội dung khi hồ sơ chưa tới phòng ban, người xử lý tự nhận việc về
mình, và hai bên nhắn qua lại trên hồ sơ — người gửi hỏi tiến độ được khi hồ sơ nằm ở
phòng ban. Mọi bước đổi hồ sơ ghi nhật ký sự kiện, kèm lịch sử thay đổi của trường quyết
định. Điều phối viên và nhân viên phòng ban thấy email và số điện thoại của người gửi,
tra từ danh bạ Keycloak. Mọi lời nhắn gom về **một hộp thư chung**, mỗi cuộc trò chuyện gắn
một hồ sơ; nhân viên có thêm **cuộc trò chuyện nội bộ** mà người gửi không thấy. Điều phối
viên không tự điều phối hồ sơ do chính mình gửi. Người gửi **đính kèm tệp** (ảnh, PDF, văn
bản) lúc gửi, lúc sửa nội dung và lúc bổ sung thông tin; tệp nằm trong SeaweedFS và chỉ người
mở được hồ sơ mới tải về được. Trang hồ sơ đặt hạn và nút thao tác lên
trước nhật ký. Mọi hạn đếm theo **giờ làm việc** của một lịch khai trong dữ liệu; hạn xử lý
đi theo loại yêu cầu nhân hệ số mức ưu tiên, gia hạn được tối đa hai lần, có lý do. Hồ sơ
nằm im ở ba trạng thái chờ thì được báo trước rồi **tự trả về điều phối hay tự đóng**. Chạy
được trên máy sạch bằng một lệnh, kể cả từ tệp nén của bản phát hành.

Mở cổng lên là thấy **việc đang chờ chính mình**, xếp theo độ gấp, nút mang đúng tên bước —
cờ "cần tôi xử lý" tính từ bước chính khai trong dữ liệu. Biểu mẫu gửi có **trường riêng
theo loại yêu cầu**, cũng khai trong dữ liệu. Giao diện có chế độ sáng và tối, màn đăng nhập
Keycloak bằng tiếng Việt. Mọi danh sách **phân trang, tìm và lọc ở dịch vụ**, gõ không dấu vẫn ra; bấm một
dòng hàng đợi là mở **ngăn xem nhanh** bên phải, duyệt bằng phím mũi tên, làm bước chính ngay trong
ngăn. Tài liệu cho người dùng và người triển khai nằm ở trang tài liệu `docs-site/`.

Trưởng phòng, điều phối viên và quản trị viên mở mục **Báo cáo** là thấy bảng điều khiển phân tích
ngay trong cổng, không đăng nhập lần hai: trưởng phòng chỉ thấy số của phòng mình. Quản trị viên tải
**nhật ký sự kiện** dạng CSV hay JSON ở màn Hệ thống.

Mục Báo cáo có thêm màn **Quy trình thực tế**: sơ đồ quy trình đang thật sự chạy khai phá từ nhật ký,
nhánh lệch khỏi luồng chính, điểm nghẽn theo thời gian chờ, bấm vào là mở đúng hồ sơ; khi bật mô hình,
kèm khuyến nghị cải tiến bằng câu chữ mà mọi con số do hệ thống gắn. Bật mô hình ngôn ngữ cục bộ thì
điều phối viên thấy **thẻ gợi ý** loại, mức ưu tiên, phòng; trưởng phòng thấy gợi ý người xử lý; người
gửi đang soạn thấy tối đa ba hồ sơ đã giải quyết tương tự. Mọi gợi ý chỉ ghi trường `suggested_*`, người
giữ hay đổi bằng thao tác sẵn có, hệ thống ghi lại giữ hay ghi đè.

Luồng thủ công đã đủ theo các quyết định của giảng viên, tầng `D` đã chạy, tầng `I` đã khép về chức năng.

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

### Tuần 7 (tiếp) — Thao tác ngoài máy trạng thái và hai khảo sát Open-Core

**Bộ sinh nhật ký sự kiện ảo** (#124, `scripts/sinh_nhat_ky_ao.py`). Khảo sát khai phá quy
trình cần khoảng một nghìn hồ sơ, mà bộ sinh của khảo sát #21 viết theo mô hình trước ngày
10/09 — không có chặng phòng ban nên không có vòng lặp định tuyến sai cần tìm, và xuất ra
tệp SQL xóa bảng nhật ký. Bộ sinh mới **đọc bộ quy tắc đang chạy** bằng một câu `SELECT`,
đi đúng luật của engine, xuất CSV đúng các cột của bảng thật ra thư mục ngoài kho, rồi tự
kiểm từng sự kiện với bộ quy tắc. Tỷ lệ rẽ nhánh là kịch bản thay được, không lẫn vào logic.

**Khép #81 bằng hai issue con**, theo đúng phương án C của ADR-0005:

- **Nhận việc về mình và sửa nội dung** (#127) — hai thao tác đổi hồ sơ mà giữ nguyên
  trạng thái, nên là **cạnh tự trỏ** đi qua cửa chuyển trạng thái để nhật ký giữ giá trị
  cũ. Lược đồ gỡ ràng buộc cấm cạnh tự trỏ nhưng giữ `UNIQUE`, nên mỗi trạng thái có tối
  đa một cạnh như vậy; phép kiểm đồ thị thứ bảy cấm cạnh tự trỏ ở trạng thái chờ người
  khác. Sửa ở *Đã phân loại* đưa hồ sơ về *Đã gửi*, vì phân loại cũ dựa trên nội dung cũ
- **Lời nhắn hai chiều và hỏi tiến độ** (#128) — thao tác không đổi hồ sơ thì **không phải
  cạnh**. Lời nhắn nằm ở bảng `case_messages` chỉ ghi thêm, không vào nhật ký sự kiện,
  không chạm dòng hồ sơ hay đồng hồ SLA. Loại lời nhắn khai trong dữ liệu, cùng khuôn với
  `allowed_transitions`: giao diện dựng nút từ danh sách API trả về

#127 đưa quy trình thiết kế lên **24 cạnh**. Cả hai issue đổi lược đồ khởi tạo, nên cả nhóm
phải `down -v` hai lần.

**Hai khảo sát Open-Core có bản ghi đề xuất**, cả hai chờ giảng viên:

- **Kho tri thức `H`** (#46, ADR-0006) — đề xuất **Wiki.js `2.5.315`** chạy như dịch vụ
  độc lập, đăng nhập qua Keycloak đã thử được, GraphQL tạo và đọc lại nguyên văn trang
  tiếng Việt. Outline bị loại vì BSL 1.1 không thuộc danh sách OSI. Đây là **pull request
  đầu tiên của thành viên** được hợp nhất (`@Senning-Dd`), qua một lượt yêu cầu sửa bốn
  điểm — trong đó ba đường dẫn giấy phép trỏ tới trang không tồn tại
- **Khai phá quy trình `I`** (#48, ADR-0007) — navigator tiếp quản vì máy thành viên thiếu
  dung lượng dựng cụm. PM4Py và pm4js chạy thử trên 1.000 hồ sơ ảo: cả hai vẽ lại đúng 24
  cạnh thiết kế và bắt đúng tám hồ sơ cài lệch có chủ đích. **Nhật ký hiện tại dùng được
  ngay, không cần thêm trường.** Đề xuất PM4Py trong một dịch vụ khai phá tách riêng vì
  giấy phép AGPL; pm4js là phương án lùi

**Issue mới từ buổi xem demo của giảng viên**: #131 — nhân viên thấy tên người gửi nhưng
không có cách liên hệ nhanh. Chốt làm riêng, sau #128.

**Bộ kiểm thử lên 211 bài.**

**Issue đã đóng**: #46, #48, #81, #124, #127, #128

### Tuần 8 — Liên hệ người gửi, chạy tay trọn luồng và `v0.4.0`

**Liên hệ người gửi cho nhân viên** (#131, từ buổi xem demo của giảng viên). Số điện thoại
là thuộc tính `phoneNumber` khai trong hồ sơ người dùng của realm — không bắt buộc, người
dùng tự sửa ở trang tài khoản Keycloak, kiểm định dạng ngay tại đó. Dịch vụ tra danh bạ lúc
mở trang qua tài khoản dịch vụ `dx-directory` và **không lưu vào cơ sở dữ liệu**, nên đổi số
là thấy ngay. Mỗi buồng lái có điểm cuối riêng, trần ba giây: danh bạ không trả lời thì chỉ
ô liên hệ báo lỗi, trang vẫn mở. Cổng người gửi không hiện liên hệ của nhân viên.

**Tài khoản mẫu cho ba phòng còn thiếu** (#145). Realm có **13 tài khoản**, phòng nào cũng
có trưởng phòng và người xử lý, nên hồ sơ chuyển về phòng nào cũng có người nhận.

**Chạy tay trọn luồng: 54/54 kịch bản đạt** (02/10), ở một phiên riêng chỉ đọc, đối chiếu
nhật ký sự kiện sau từng thao tác. Cả 24 cạnh được bấm ít nhất một lần, mỗi lần đúng một
dòng nhật ký; thao tác bị chặn không sinh dòng nào. Bảy bất thường, navigator chốt từng cái:

- Người cùng phòng hoàn thành được hồ sơ đã giao người khác — **giữ nguyên**, nhật ký ghi
  đúng người bấm
- Ba lỗi sửa ngay trong tuần: **phiên hết hạn hiện trang 404** (#150), **câu chú giải nói
  sai người đang giữ hồ sơ** (#151), **thứ tự ô Sửa nội dung khác biểu mẫu tạo hồ sơ** (#152)
- Hai thay đổi đã chốt, làm Tuần 9: đếm *quay lui* theo cạnh làm lại khai trong dữ liệu
  (#153), và điều phối viên không tự điều phối hồ sơ do chính mình gửi (#154)

#150 có nguyên nhân sâu hơn cái nhìn thấy: cứ năm phút, cổng làm mới token thành công
nhưng không ghi được cookie lúc dựng trang, và lỗi ghi cookie làm token mới bị vứt — xem
Ghi chú kỹ thuật.

**Rà luồng tìm chỗ hồ sơ nằm im.** Ba trạng thái chờ mà người phải bấm không bấm thì hồ sơ
đứng mãi: *Chờ phòng ban xác duyệt* (#142), *Chờ bổ sung thông tin* (#143), *Hoàn tất*
(#144). Mỗi issue nêu ba phương án và ràng buộc lược đồ, chờ giảng viên chọn.

**Khung chat theo ý giảng viên** — navigator chốt hướng ngày 04/10: hộp thư chung kiểu
Messenger, mỗi cuộc trò chuyện gắn một hồ sơ, gom theo người (#155); thêm trò chuyện nội bộ
chỉ nhân viên thấy (#156). *Yêu cầu bổ sung thông tin* giữ nguyên là nút trong bảng thao
tác — hộp thư mở rộng lời nhắn của #128, không đổi engine.

**Bộ kiểm thử lên 233 bài.**

**Issue đã đóng**: #131, #145, #150, #151, #152

### Tuần 9 — Hộp thư trao đổi, trò chuyện nội bộ và giao diện mới

**Thiết kế giao diện trước hộp thư** (navigator đổi thứ tự ngày 05/10): hộp thư cần một khung
để đặt vào. Đợt thiết kế dùng skill `ui-ux` của evondevKit (MIT) — bản mô tả, hai tới ba
wireframe mỗi màn, navigator chọn rồi mới dựng; mỗi màn đo bằng công cụ dò của skill ở 1280 và
375 px, sáng và tối. Ba màn đã dựng:

- **Khung thanh bên** có số hồ sơ còn mở từng mục và nút sáng/tối nhớ lựa chọn (#158). Thêm
  `lucide-react` (ISC) cho icon
- **Trang hồ sơ nhân viên hai cột**: thanh các bước suy từ thứ tự trạng thái trong dữ liệu,
  lời nhắn tách sang thẻ *Trao đổi* dạng chat (#169)
- **Hai hàng đợi** dùng chung một bảng có ô tìm lọc ngay trên trình duyệt; phòng ban chia nhóm
  theo mức gấp, điều phối lọc bằng hàng tab (#170)

Không màn nào đụng `backend/`, điểm cuối hay Server Action.

**Hộp thư chung kiểu Messenger** (#155). Đọc đúng bảng lời nhắn của #128, không có kho tin thứ
hai. Mỗi người chỉ thấy hồ sơ mình đang giữ — điều phối viên thấy hàng đợi điều phối cộng hồ
sơ mình đã nhắn. Mốc đã đọc của từng người là bảng mới thêm bằng migration, không cần `down -v`.

**Trò chuyện nội bộ chỉ nhân viên thấy** (#156) — loại lời nhắn mới khai trong dữ liệu, mang
cờ ẩn với người gửi. Ẩn **theo hồ sơ** chứ không theo vai trò: điều phối viên mở hồ sơ do chính
mình gửi cũng không thấy cuộc nội bộ. Bộ lọc nằm một chỗ; một bài kiểm thử quét mọi điểm cuối
`GET` trong OpenAPI với tư cách người gửi, để điểm cuối thêm sau này không lọt tin nội bộ. Hộp
thư có hai cuộc mỗi hồ sơ, mốc đã đọc riêng từng cuộc.

**Hai thay đổi chốt từ lượt chạy tay 02/10**: *quay lui* đếm theo cạnh làm lại khai trong dữ
liệu (#153) — hồ sơ bị trả một lần kèm một vòng hỏi đáp giờ đếm 1, cách cũ ra 3; và điều phối
viên không tự điều phối hồ sơ do chính mình gửi (#154), ràng buộc gắn trong dữ liệu vào năm cạnh
của vai điều phối. Kế hoạch gộp #153, #154, #156 vào **một** lần `down -v` không giữ được: #156
lên `main` trễ một ngày, nên cả nhóm làm hai lần, ngày 05/10 và 06/10.

**Khảo sát véc-tơ và LLM** (#47) — mảng khảo sát cuối cùng. @NguyentimAnh kiểm giấy phép mười
ba ứng viên; đĩa ảo Docker trên máy thành viên nằm ở ổ gần đầy làm hỏng lượt đo, nên navigator
tiếp quản ngay trên nhánh pull request và chạy lại sáu phép thử có đáp án biết trước. Ba cơ sở dữ
liệu véc-tơ cho cùng kết quả truy xuất (20/20); mô hình 1,5 tỉ tham số gợi ý đúng loại yêu cầu
19/20, không lần nào ra ngoài danh mục. ADR-0008 đề xuất **pgvector** ngay trên PostgreSQL,
**llama.cpp server** với hai mô hình Qwen giấy phép Apache-2.0, và **không dùng khung LLM**.

**Giảng viên chốt năm câu treo** (08/10), nguyên văn trong bình luận #142, #143, #144, #101,
#102: hồ sơ nằm im thì cảnh báo trước rồi tự trả về hay tự đóng; hạn theo mức ưu tiên (50, 75,
100, 150 % hạn chuẩn) và điều phối viên chỉnh hạn có lý do, có nhật ký; mở lại trong 7 ngày làm
việc sau khi đóng, tối đa hai lần, cấp hạn mới — **thay** quyết định ngày 23/09. Hai chỗ vướng
chung khi làm: cạnh tự động của hệ thống trùng cặp trạng thái với cạnh người bấm, mà lược đồ
giữ `UNIQUE (rule_set_id, from_state, to_state)`; và *giờ làm việc* trong khi đồng hồ SLA đang
tính giờ lịch.

**Nhận xét giao diện của giảng viên** (11/10): trang hồ sơ nghiêng về nhật ký, người dùng phải
thấy trước việc của mình và hạn. #189 thu gọn dòng thời gian về bước hiện tại (mở ra được, nhớ
lựa chọn), dưới 1100 px đưa thẻ hạn và thao tác lên ngay dưới tiêu đề, và trên trang người gửi
đưa thao tác lên đầu, lời nhắn thành khung chat riêng. Cùng đợt sửa lỗi biểu mẫu lộ ra khi chạy
kịch bản đầu–cuối: bấm *Tiếp tục* ở bước 2 là gửi luôn, bỏ qua bước *Xem lại* (#188). Bảng chú
giải trạng thái ở *Hồ sơ của tôi* sẽ thay bằng sơ đồ nhỏ hiện khi rê vào nhãn — #192.

**Kịch bản đầu–cuối qua giao diện thật**: một hồ sơ đi hết luồng qua đủ bốn vai trò, 19 bước
đạt; kịch bản tin nhắn đạt 20/20 điều kiện.

**Bộ kiểm thử lên 261 bài.**

**Issue đã đóng**: #47, #153, #154, #155, #156, #158, #169, #170, #188, #189

### Tuần 10 — Lịch làm việc, luật hồ sơ nằm im và `v0.5.0`

**Hồ sơ của tôi xem nhanh vị trí** (#192). Bảng chú giải mười trạng thái cuối trang bỏ đi; rê
chuột, Tab tới hay chạm vào nhãn trạng thái thì hiện sơ đồ nhỏ của đường chính, suy từ dữ liệu
như thanh bước trang hồ sơ, kèm một dòng khi hồ sơ đang dừng ở nhánh phụ.

**Lịch làm việc** (#199, issue mới trong tuần). Giảng viên chốt các hạn chờ tính theo giờ làm
việc, mà đồng hồ SLA đang đếm giờ lịch — hồ sơ cam kết 8 giờ nhận chiều thứ Sáu đã quá hạn từ
đêm thứ Sáu. Navigator chốt làm lịch **trước** #142 và #144 và áp cho mọi đồng hồ, để cả hệ
thống chỉ có một loại giờ. Lịch là dữ liệu: khung giờ theo thứ, ngày nghỉ, múi giờ; mẫu là thứ
Hai đến thứ Sáu, nghỉ trưa, ngày lễ năm 2026. Mọi phép đo đi qua hai hàm trong PostgreSQL, vì
bộ quét phải đo ngay trong SQL; Python gọi đúng hai hàm đó nên hai nơi không đo lệch nhau.

**Hồ sơ nằm im ở ba trạng thái chờ** — luật giảng viên chốt 08/10, mỗi trạng thái một issue,
dùng chung một khuôn: **cạnh hệ thống** cùng cặp trạng thái với cạnh của người, hạn chờ và mốc
báo trước là hai cột dữ liệu trên cạnh, một bộ quét chạy cùng vòng với bộ quét leo thang và đi
qua cửa chuyển trạng thái duy nhất.

| Trạng thái | Hết hạn chờ thì | Hạn chờ · báo trước (giờ làm việc) | Issue |
|---|---|---|---|
| *Chờ phòng ban xác duyệt* | tự trả về điều phối viên; điều phối viên cũng rút về được trước hạn, có lý do | 24 · 4 | #142 |
| *Hoàn tất* | tự đóng, nhật ký ghi lý do | 24 · 8 | #144 |
| *Chờ bổ sung thông tin* | tự đóng sang *Đã đóng*, không sang *Đã hủy* vì người gửi không chủ động bỏ | 40 · 24 | #143 |

Chỗ vướng ghi ở tuần trước được gỡ: ràng buộc duy nhất của bảng cạnh thêm cột `is_system`,
nên một cặp trạng thái có tối đa một cạnh của người và một cạnh của hệ thống. Tự trả về
**không** tính là quay lui — phòng ban không từ chối nội dung, chỉ để quá hạn.

**Ngưỡng sắp hết hạn trong dữ liệu** (#175). Ngưỡng là phần trăm cam kết, khai theo loại yêu
cầu, mẫu 75 %. Dịch vụ trả thêm cờ *sắp hết hạn*; thẻ hạn và vạch chuyển vàng, hàng đợi phòng
ban có nhóm *Sắp hết hạn* giữa *Quá hạn* và *Trong hạn*. Chọn phần trăm thay vì số giờ để
ngưỡng co giãn theo hạn của từng hồ sơ.

**Hạn theo mức ưu tiên và gia hạn từng hồ sơ** (#101). Hạn gốc là hạn chuẩn của loại nhân hệ
số trong bảng mức ưu tiên — Khẩn 50 %, Cao 75 %, Bình thường 100 %, Thấp 150 %; ân hạn nhân
cùng hệ số. Gia hạn là cạnh tự trỏ theo ADR-0005, nhập số giờ cộng thêm kèm lý do: điều phối
viên gia hạn lần đầu trước khi phòng ban nhận việc, trưởng phòng gia hạn khi hồ sơ đã leo
thang. Mỗi lần tối đa 50 % hạn gốc, tổng tối đa hai lần — giảng viên để ngỏ con số X, navigator
chốt 50 % trong dữ liệu. Bộ quy tắc mẫu lên **31 cạnh**.

**Bản cài đặt đầu tiên cho nhóm khác dùng thử.** Giảng viên giao: hai nhóm gửi nhau bản cài
đặt, nhóm kia cài chỉ dựa vào README. Nhóm gửi tệp `.tar.gz` của bản phát hành — cũng là cách
ban giám khảo lấy mã — nên README thêm cách cài từ tệp nén, có lệnh cho PowerShell và bash,
yêu cầu máy đo lại, cách kiểm cụm đã lên và bảng sự cố thường gặp (#206). Lệnh cũ
`cd dx-os-lab/infra` sai tên thư mục khi giải nén tệp của GitHub. Cắt **`v0.5.0`** ngay sau
#101, rồi chạy thử đúng tệp `.tar.gz` của Release theo bốn lệnh trong README: kịch bản
đầu–cuối 19/19 bước đạt. Tệp chưa gửi tới nhóm kia.

**Sự cố khi phát hành**: pull request sinh nhật ký thay đổi (#215) vào thẳng `main` vì ô
`base` để mặc định. Không revert — `dev` lúc đó là tổ tiên của `main`, nên tua thẳng `dev` lên
`main` và đặt thẻ ngay trên `main`; sau đó hai nhánh cùng một commit.

Kiểm qua đường thật bắt được hai lỗi mà bộ kiểm thử không thấy, cả hai sửa trong pull request
của #101: trang hồ sơ trả 500 khi dòng thời gian kể lại một giá trị số, và khung gia hạn vẫn
mở sau khi gia hạn xong — xem Ghi chú kỹ thuật.

**Bộ kiểm thử lên 362 bài.**

**Issue đã đóng**: #101, #142, #143, #144, #175, #192, #199, #206

### Tuần 11–12 — Mở lại có giới hạn, đính kèm tệp và từ ngữ

Mốc Tuần 11 hết hạn 25/10 mà chưa đóng issue nào; ba issue dời sang mốc Tuần 12 và làm xong
trong ngày 26/10, mỗi issue một pull request squash cộng một pull request phát hành.

**Mở lại có giới hạn và trạng thái *Không tiếp nhận*** (#102). Giảng viên chốt 08/10, thay quyết
định 23/09 "mở lại không giới hạn, không cấp hạn mới". Navigator chốt chi tiết 26/10:

- Nhánh điều phối viên đóng khi không phòng nào nhận sang **trạng thái kết thúc riêng**
  *Không tiếp nhận*, lý do bắt buộc, không mở lại được; tầng `D` đếm riêng khỏi hồ sơ đã xử lý
- Mở lại từ cả *Hoàn tất* lẫn *Đã đóng*, **dùng chung một bộ đếm** tối đa 2 lần
  (`request_types.reopen_max_count`), mỗi lần có lý do. Mở lại sau khi đóng chỉ trong **56 giờ
  làm việc** — 7 ngày với lịch mẫu 8 giờ một ngày — và chỉ với hồ sơ **từng làm xong**: hồ sơ
  tự đóng vì chưa bổ sung thông tin thì không
- **Hạn mới**: mở lại là chu kỳ xử lý mới, đồng hồ đếm lại từ 0 và gia hạn cũ về 0. Đây là chỗ
  đảo lại ân hạn của #94 cho riêng trường hợp mở lại
- Hết lượt, quá cửa sổ hay *Không tiếp nhận* thì người gửi bấm *Tạo hồ sơ mới từ hồ sơ này*:
  biểu mẫu chép sẵn nội dung, hồ sơ mới mang `parent_request_id` (migration `0011`), hai trang
  liệt kê nhau. Dịch vụ chỉ nhận hồ sơ gốc của chính người gửi và đã kết thúc

Phát hiện lúc làm đã đổi thiết kế: lược đồ **cấm hẳn** cạnh rời khỏi trạng thái kết thúc, nên
mở lại từ *Đã đóng* không có chỗ đi. Navigator chọn nới ràng buộc: cạnh rời trạng thái kết thúc
nay hợp lệ nhưng **bắt buộc khai cửa sổ thời gian** (`reopen_window_hours`), và cạnh mở lại sau
khi đóng là cạnh duy nhất loại đó — xem Ghi chú kỹ thuật. Bộ quy tắc mẫu lên **11 trạng thái, 32
cạnh**. Phép thử đột biến 19/19 bị bắt, đường thật 36/36.

**Đính kèm tệp vào hồ sơ** (#80). Tệp lưu trong SeaweedFS qua S3 API bằng `boto3` (ADR-0002);
hồ sơ chỉ giữ siêu dữ liệu ở bảng `case_attachments` (migration `0012`), chỉ ghi thêm nên hồ sơ
hủy vẫn giữ tệp. Navigator chốt 26/10:

- **Tệp đi qua dịch vụ ứng dụng**, không presigned URL: quyền kiểm ở mỗi lần tải, người ngoài
  nhận 404. Phía Next.js dùng Route Handler vì Server Action giới hạn thân yêu cầu 1 MB
- **Ai mở được hồ sơ thì xem được tệp** — dùng lại ba luật xem hồ sơ, không viết luật quyền thứ hai
- **Chỉ người gửi đính kèm, và chỉ khi có cạnh mang cờ** `transitions.accepts_attachments` — *Sửa
  nội dung* và *Bổ sung thông tin*; tới phòng ban thì khóa
- **Giới hạn là cấu hình** trong `.env`: mẫu 10 MB mỗi tệp, 5 tệp mỗi lần, 20 tệp mỗi hồ sơ, đuôi
  ảnh, PDF, Word, Excel, văn bản. Giao diện hỏi `GET /attachments/policy` nên hai lớp chặn không
  lệch nhau; dịch vụ còn kiểm nội dung khớp đuôi theo chữ ký đầu tệp

Thêm hai phụ thuộc `boto3` và `python-multipart`, cùng Apache-2.0; các gói kéo theo đã kiểm trên
ảnh chứa thật. Một lần tải nhận cả lô hoặc từ chối cả lô; tải hỏng sau khi gửi thì hồ sơ vẫn đã
gửi và trang hồ sơ nhắc thêm tệp lại. Không quét vi-rút — ngoài phạm vi. Phép thử đột biến 21/21
bị bắt, đường thật 29/29.

**Rà từ ngữ giao diện** (#157). Trợ lý lập bảng 20 dòng theo từng màn, tách chữ trong mã với chữ
trong dữ liệu; navigator duyệt 19 dòng, giữ "quay lui". Một khái niệm một tên ở mọi màn hình:
người gửi, điều phối viên (không còn "người tiếp nhận"), người xử lý (không còn "người phụ
trách"), *Trao đổi* cho thẻ của người gửi như tab của nhân viên, *dòng thời gian* thay cho
"nhật ký", đồng hồ hạn xử lý. Bỏ từ kỹ thuật khỏi màn người dùng cuối — định tuyến, bộ quy tắc,
nhánh lệch chuẩn, dịch vụ ứng dụng — và thông báo lỗi của engine nói bằng nhãn trạng thái, vai
trò thay vì mã tiếng Anh. Chỉ một nhãn nằm trong dữ liệu (*Chuyển lại sang phòng khác*). Quy tắc
đặt tên ghi ở `ARCHITECTURE.md` mục 8.3. Đột biến 5/5, đường thật 32/32.

**Bộ kiểm thử lên 418 bài.**

**Issue đã đóng**: #80, #102, #157

### Tuần 13 — `v0.6.0`, cổng theo việc cần làm, `v0.7.0`, buổi báo cáo 29/10 và khép đợt giao diện

**Phát hành `v0.6.0`** (27/10, #256/#257) khép Giai đoạn 2 — mở lại có giới hạn, đính kèm tệp,
rà từ ngữ. ROADMAP dời `D` sang `v0.8.0`, `I` sang `v0.9.0`.

**Đánh giá dự án và 30 issue mới** (27/10). Hai issue gốc: **#226 làm mới giao diện** (#227–#238,
mốc Tuần 13) và **#240 nền tảng vận hành** cho môi trường thật (#241–#249, mốc Tuần 14), cộng
#239 và #250–#255. Navigator cho phép gom nhiều issue cùng nhóm vào một pull request, mỗi issue
một dòng `Closes`.

**Tích hợp liên tục** (#241). `.github/workflows/ci.yml` chạy ba kiểm tra trên mỗi pull request
vào `dev` và `main`: header giấy phép (`scripts/kiem_header.py`), giao diện (dựng và kiểm kiểu),
cụm (dựng ảnh rồi chạy toàn bộ pytest; bài bị bỏ qua tính là hỏng). Không chạy khi nhánh nhận
commit, để không trùng sáu kiểm tra. Thử ba pull request cố ý hỏng — mỗi cái đỏ đúng kiểm tra
của nó. Một lượt dưới ba phút.

**Cổng theo việc cần làm** — năm issue, ba pull request:

- **Cờ "cần tôi xử lý"** (#227): cột `transitions.primary_scope` đánh dấu **bước chính** của mỗi
  trạng thái (theo vai, hay chỉ người được giao); dịch vụ tính cờ cho cả danh sách bằng một
  truy vấn. Không dùng "có nút bấm được": người gửi hủy được ở *Đã gửi* nhưng hồ sơ không chờ họ
- **Trang chủ theo việc cần làm** (#228): một danh sách việc chờ mình gộp mọi vai, mặc định xếp
  theo độ gấp (quá hạn → sắp hạn hay sắp tự đi → chờ lâu nhất), đổi được và trình duyệt nhớ;
  cột phải tổng quan theo vai. Nút trên dòng chỉ mở trang hồ sơ ở khối thao tác — bước chính
  thường cần nhập thêm
- **Màn Hệ thống** (#229) cho quản trị viên; bảng trạng thái cụm rời khỏi trang chủ
- **Thanh bên** (#230): số đậm là việc chờ mình, số mờ là hồ sơ đang mở, chấm báo khi có việc
  gấp; thu gọn được, nút ở đáy, trình duyệt nhớ
- **Nhận diện mới** cùng đợt: phẳng, nền xám trung tính, thẻ trắng viền mảnh, nhấn chàm, đủ sáng
  và tối, giữ phông Be Vietnam Pro — navigator chọn từ hai phương án wireframe

**Màn rỗng, khung chờ, màn không phản hồi** (#234, #235). Danh sách trống thì giải thích và chỉ
việc tiếp theo; tám tuyến có khung chờ khi tải; trang không tìm thấy và trang lỗi riêng. Dịch vụ
không trả lời trong thời hạn cấu hình thì màn *hệ thống không phản hồi* dựng ngay ở máy chủ —
xem Ghi chú kỹ thuật.

**Trường thông tin riêng theo loại yêu cầu** (#250). Bảng cấu hình `request_type_fields` khai
trường của từng loại (văn bản, số, ngày, lựa chọn; bắt buộc hay không); giá trị lưu ở cột JSONB
`requests.details` (migration `0013`). Biểu mẫu gửi, phép kiểm ở dịch vụ, trang hồ sơ và dòng
thời gian đều dựng từ khai báo — thêm một trường là thêm một dòng dữ liệu, có bài kiểm thử chứng
minh. Sửa qua cạnh *Sửa nội dung*; điều phối đổi loại thì trường của loại mới hiện "chưa có",
không chặn.

**Hàng đợi có dải số và đăng nhập tiếng Việt** (#231, #236). Đầu hàng đợi là dải ô bấm để lọc,
mỗi ô có số hồ sơ và dòng phụ quá hạn hay sắp hạn bằng biểu tượng kèm chữ; cột *Việc tiếp theo*.
Màn đăng nhập dùng chủ đề riêng **kế thừa chủ đề của Keycloak, chỉ thêm CSS** — không sửa mã nền
tảng; realm đặt tiếng Việt mặc định. Bản sửa sau phát hành (#272): cổng gửi tham số chuẩn OIDC
`ui_locales=vi`, vì trình duyệt đặt tiếng Anh vẫn nhận màn tiếng Anh.

**Phát hành `v0.7.0`** (28/10, #270/#271) — "Cổng theo việc cần làm".

**Buổi báo cáo trước ba thầy** (29/10, thầy Kiệt, thầy Phong, thầy Duật). Kết luận: sản phẩm
tốt. Góp ý:

- Slide và lời nói dùng AI quá nhiều, nghe xong chưa rõ dự án làm gì — navigator tự soạn lại
- Tìm sản phẩm cùng loại trong nước và quốc tế, nêu điểm hơn → #277
- Các con số (gia hạn, mở lại, hạn chờ) cần cơ sở → #276
- Đổi quy trình thì hồ sơ cũ, hồ sơ mới ra sao → #278
- Có thầy hiểu nhầm cổng là luồng cố định qua các phòng như cổng dịch vụ công; giảng viên hướng
  dẫn xác nhận đề tài đúng — điều phối viên chọn phòng cho từng hồ sơ, chỉ là trình bày chưa rõ
- Nghẽn ở điều phối viên khi hồ sơ nhiều — tầng `I` gợi ý phân loại (#239); chờ chốt hướng
- Dựng trang tài liệu riêng, chỉnh README → #279

**Sau buổi báo cáo** (01/11): #274 khung trao đổi chia phía theo người viết — trước đó tin của
đồng nghiệp nằm bên phải như tin của mình; #275 vùng nội dung căn giữa trên màn hình rộng; #276
bảng cơ sở các con số ở `process-flow.md` mục 9 — lịch làm việc theo Bộ luật Lao động 2019, hạn
tự đóng và ngưỡng cảnh báo đối chiếu giá trị mặc định của các nền tảng bàn dịch vụ, con số chưa
có nguồn ghi rõ là giá trị mẫu; #277 tài liệu so sánh với tám sản phẩm cùng loại
(`docs/so-sanh-san-pham.md`).

**Trang tài liệu và README gọn** (#279, 01/11). Trang `docs-site/` dựng bằng Starlight (MIT), chia
theo người đọc: người dùng theo vai, người cài đặt, người phát triển; 19 trang, 9 ảnh chụp. README
rút từ 418 xuống 139 dòng, trỏ sang trang tài liệu; thêm `CODE_OF_CONDUCT.md`, `SECURITY.md`. Tích hợp
liên tục thêm kiểm tra thứ tư: dựng trang tài liệu. Trang chỉ dựng trên máy cho tới khi kho công khai
— lúc đó đăng qua GitHub Pages hoặc Vercel.

**Kịch bản kiểm tra giao diện qua đăng nhập thật** (#238, 01/11). Playwright trong `e2e/`: bốn tài
khoản đăng nhập qua trang của Keycloak — không tự đúc cookie, vì cookie tự đúc từng che lỗi #87 — rồi
chạy cùng bộ bài ở bốn cấu hình (rộng sáng, rộng tối, 375 px, giảm chuyển động). Mỗi màn: mở được,
không lỗi phía trình duyệt, không cuộn ngang; cộng các điều kiện nghiệp vụ như số trên trang chủ khớp
danh sách việc chờ.

**Danh sách có phân trang, ngăn xem nhanh, chuyển động** — ba issue cuối của đợt giao diện, ba pull
request (02/11):

- **Phân trang và bộ lọc phía dịch vụ** (#232): bốn danh sách nhận `limit` (mặc định 50, trần 200),
  `offset`, ô tìm `q` và bộ lọc, trả kèm tổng số; số đếm nhóm tính trên cả tập đã lọc nên không đổi khi
  sang trang. Tìm không phân biệt dấu ở cả SQL lẫn Python. Đo trên cụm thử với 6.001 hồ sơ, phần lớn đã
  hủy: *Hồ sơ của tôi* từ 9,1 giây xuống 0,08 giây; hàng đợi điều phối từ 1,1 giây xuống 0,09 giây và
  không tăng khi gấp đôi lịch sử — xem Ghi chú kỹ thuật
- **Ngăn xem nhanh** (#233): bấm dòng hàng đợi mở hồ sơ ở ngăn bên phải (`?xem=`), nút trước/sau
  "2 trên 14", phím mũi tên, Esc trả tiêu điểm về đúng dòng, toàn màn hình ở 375 px. Nút chính ở đáy
  ngăn là bước chính — dịch vụ đánh dấu `is_primary` trên từng cạnh đi được, cùng nguồn với cờ "cần tôi
  xử lý"; làm xong thì ngăn sang hồ sơ kế. Trang chi tiết và ngăn dùng chung phần nạp dữ liệu và khối
  thao tác
- **Chuyển động thống nhất** (#237): bảng quy tắc ở `ARCHITECTURE.md` mục 8.4 — chỉ để định hướng và báo
  phản hồi, thao tác lặp lại không quá 300 ms, không đếm số từ 0, giảm chuyển động thì tắt hết. Ngăn
  xem nhanh và hộp xác nhận có hiệu ứng hiện và ẩn; thông báo kết quả chỉ có hiệu ứng hiện. Chữ số cuộn
  khi đổi giá trị lúc đang xem. Bỏ vạch hạn chạy từ 0 mỗi lần mở trang

Danh sách việc chờ ở trang chủ tải tối đa 200 việc mỗi vai; vượt trần thì ghi "Đang hiện 200 trên N"
kèm đường sang hàng đợi.

**Navigator đổi nhịp pull request** (02/11): một nhánh và một pull request vào `dev` gom một tới ba
issue liên quan, và một pull request phát hành `dev → main` cho cả đợt thay vì sau từng nhánh.

**Bộ kiểm thử lên 462 bài pytest và 54 bài giao diện.**

**Issue đã đóng**: #226 (issue gốc), #227, #228, #229, #230, #231, #232, #233, #234, #235, #236, #237,
#238, #241, #250, #274, #275, #276, #277, #279

---

### Tuần 14–15 — `v0.8.0`, không gian `D`, `v0.9.0` và mở Giai đoạn 4

**Đổi quy trình thì hồ sơ đang chạy ra sao** (#278, #299, 02/11) — câu hỏi của buổi báo cáo 29/10.
Engine đã đúng thiết kế: hồ sơ giữ bộ quy tắc lúc tạo, nút, nhật ký và đồng hồ hạn tra theo bộ của
hồ sơ. Bài kiểm thử mới chép bộ đang bật thành bộ thứ hai ngay trong giao dịch của bài, đổi sáu chỗ
như một lần đổi quy trình thật, rồi cho hồ sơ của cả hai bộ đi tiếp. Bài lộ ra một lỗi, tách thành
#299: hai hàng đợi chỉ lọc theo bộ đang bật, nên vừa đổi bộ là hồ sơ cũ còn mở biến khỏi hàng đợi dù
vẫn chạy đồng hồ và vẫn tự leo thang. Nay mọi màn liệt kê lấy hồ sơ của mọi bộ còn hồ sơ đang mở và
chọn hồ sơ bằng cặp bộ cùng trạng thái. `ARCHITECTURE.md` mục 6.1 ghi câu trả lời.

**Phát hành `v0.8.0`** (02/11, #302/#303) — khép đợt giao diện Tuần 13. ROADMAP dời `D` sang `v0.9.0`,
`I` sang `v0.10.0`.

**Không gian `D`** — mốc Tuần 15, issue gốc #307, hai pull request:

- **Lớp báo cáo và bảng điều khiển dựng từ tệp cấu hình** (#304). Chỉ số nằm trong các view
  `bao_cao_*` (migration `0014`, tự chạy). View không tra mã trạng thái nào: kết thúc tra
  `is_terminal`, đã tới phòng ban tra `sla_running`, mỗi hồ sơ theo bộ quy tắc của chính nó; giờ xử lý
  đo bằng giờ làm việc. Dashboard *Vận hành yêu cầu* với bốn biểu đồ của ROADMAP lưu thành YAML trong
  `infra/superset/bang-dieu-khien/`; Superset tự nạp đè theo uuid mỗi lần khởi động, sau khi dịch vụ
  ứng dụng chạy xong migration. Tích hợp liên tục thêm kiểm tra thứ năm cho dashboard tự nạp
- **Dữ liệu mở và dữ liệu trình diễn** (#306). Quản trị viên tải nhật ký sự kiện dạng CSV hay JSON ở
  màn Hệ thống: cột cố định, mốc UTC, có sự kiện mở đầu từ lúc tạo hồ sơ, người thao tác chỉ bằng mã
  định danh. `scripts/nap_du_lieu_trinh_dien.py` dùng lại kịch bản của bộ sinh nhật ký ảo, đổi đồng hồ
  sang giờ làm việc thật và chỉ ghi thêm — biểu đồ có số mà nhật ký vẫn không bị sửa
- **Nhúng bảng điều khiển vào cổng, lọc theo phòng** (#305). Mục *Báo cáo* trên thanh bên nhúng
  dashboard bằng thư viện nhúng chính thức của Superset, không đăng nhập lần hai: dịch vụ ứng dụng kiểm
  vai trò bằng token Keycloak rồi xin Superset một token khách sống 5 phút, kèm điều kiện lọc theo dòng
  `ma_phong`. Ai xem được và xem tới đâu là cột `roles.report_scope` trong dữ liệu (migration `0015`
  thêm cột cho cụm cũ, nên không phải `down -v`); mã phòng trong token được đối chiếu bảng
  `departments` trước khi vào điều kiện lọc. Trưởng phòng thấy phòng mình, điều phối viên và quản trị
  viên thấy toàn công ty, người gửi và người xử lý không thấy mục và nhận 403 khi gọi thẳng. Superset
  tắt thì mục hiện màn không phản hồi. Kiểm bằng mắt điều kiện lọc trên 600 hồ sơ trình diễn; 11 phép
  thử đột biến đều bị bắt

**Phát hành `v0.9.0`** (03/11, #311/#312) — khép Giai đoạn 3.

**Mở Giai đoạn 4 ở mức issue** (03/11). Kế hoạch tầng `I` chia bốn đợt; navigator chốt **khai phá quy
trình làm trước** phân loại, làm cả bốn đợt trước 07/12, một mốc *Giai đoạn 4 — Không gian I* hạn
29/11. Issue gốc #322, con #239 và #314–#320; #313 nâng khung giao diện có cảnh báo bảo mật; #321 kho
tri thức để khi còn thời gian. Chưa viết mã issue nào của tầng `I`: ba bản ghi ADR-0006/0007/0008 vẫn
ở *Đề xuất*. Nhóm hỏi giảng viên bằng bình luận trên từng issue ngày 03/11 — ba bản ghi và sáu issue
cần thảo luận của Tuần 14 — và nhắc lại ở #322 ngày 08/11.

**Bộ kiểm thử lên 507 bài pytest và 74 bài giao diện.**

**Issue đã đóng**: #278, #299, #304, #305, #306, #307 (issue gốc)

### Tuần 16 (09–11/11) — `v0.10.0` tới `v0.13.0`, khép Giai đoạn 4 về chức năng

Bốn bản phát hành trong ba ngày, mỗi bản một pull request `dev → main` theo nhịp chốt 02/11.

**`v0.10.0`** (09/11, #332) — nền tảng vận hành và thẻ gợi ý, trước khai phá:

- **Nâng cấp giữ dữ liệu** (#254). Lược đồ cấu hình của engine chuyển vào chuỗi migration (bản gốc
  `0000` là ảnh chụp lược đồ `v0.9.1`), dữ liệu khởi tạo do dịch vụ ứng dụng nạp lần đầu, chín phép kiểm
  đồ thị thành hàm `kiem_tra_cau_hinh()` (migration `0018`). Từ `v0.9.1` trở đi, nâng cấp chỉ cần
  `up -d --build`; đổi quy trình trên cụm đang chạy là một bản sửa dữ liệu tạo bộ quy tắc phiên bản mới.
  Kiểm thật: nâng cụm `v0.9.1` có 600 hồ sơ, `scripts/kiem_nang_cap.py` báo số dòng và mã băm khớp
- **Công cụ kiểm chứng vào kho** (#249). Cụm thử cách ly, dò đăng nhập thật, tạo hồ sơ thử theo từng
  trạng thái, phép thử đột biến ở `scripts/kiem_chung/`, kèm trang hướng dẫn — người khác, kể cả ban
  giám khảo, tái hiện được bằng chứng chất lượng. Chưa thử trên PowerShell và Linux
- **Lớp biên và bộ quét** (#243, #253). CSP nonce ở cổng, giới hạn tốc độ đếm trong PostgreSQL trả 429
  kèm `Retry-After`, `/health` công khai không lộ chi tiết; bộ quét nền có khóa khi chạy nhiều bản và
  nhịp sức khỏe trên màn Hệ thống
- **Thẻ gợi ý có xác nhận** (#239). Gợi ý phòng hiện thành thẻ có lý do và nguồn; cửa chuyển trạng thái
  ghi giữ hay ghi đè vào cột `event_log.suggestion`; bảng điều khiển thêm tỷ lệ ghi đè

**`v0.11.0`** (10/11, #337) — khai phá quy trình thực tế, điểm sáng tạo của đề tài:

- **Dịch vụ khai phá** (#314). `services/khai-pha/` là dịch vụ FastAPI riêng, không mở cổng ra máy, đọc
  lớp báo cáo bằng tài khoản chỉ đọc riêng tạo ở migration `0019` — không cần `down -v`. Hai bộ máy sau
  một giao diện hẹp: `pm4py` mặc định và `noi_bo` Python thuần dự phòng, bài kiểm thử đòi JSON giống
  hệt. Tích hợp liên tục chặn `import pm4py` ngoài thư mục này. 617 hồ sơ trình diễn khai phá trong
  0,39 giây
- **Màn Quy trình thực tế** (#315) trong mục Báo cáo: sơ đồ tương tác, câu kết luận dựng tất định từ số
  liệu, bấm điểm nghẽn hay nhánh lệch là mở đúng hồ sơ, phạm vi phòng như bảng điều khiển

**`v0.12.0`** (11/11, #343) — mô hình ngôn ngữ cục bộ:

- **Mô hình nhiều giấy phép** (#340) — điều kiện giảng viên đặt khi xác nhận ADR-0007 ngày 10/11.
  `services/khai-pha/` mang AGPL-3.0-or-later với toàn văn riêng, còn lại MIT; `LICENSES.md`, `NOTICE`;
  `scripts/kiem_header.py` bắt cả tệp mang sai giấy phép theo thư mục; màn Quy trình thực tế dẫn tới mã
  nguồn dịch vụ khai phá (điều 13 AGPL)
- **Dịch vụ mô hình** (#316): llama.cpp server cùng Qwen2.5-1.5B-Instruct `q4_k_m` dưới hồ sơ Compose
  `tri-tue`, tải bằng `scripts/tai_mo_hinh.py` có kiểm SHA-256; mọi lời gọi đi qua
  `backend/app/intelligence/mo_hinh.py`, lỗi gì cũng ra "không có gợi ý". Cụm mặc định không đổi
- **Gợi ý loại, mức ưu tiên, phòng** (#317) bằng tác vụ nền sau khi gửi, có bộ quét bù. Đo trên 80 hồ sơ
  mẫu có nhãn: loại 92,5 %, mức ưu tiên 38,8 %, phòng 62,5 % so với bảng ánh xạ 86,2 % — nên gợi ý phòng
  của mô hình tắt mặc định (`SUGGEST_DEPARTMENT_FROM_MODEL`), giữ bảng ánh xạ. Gửi hồ sơ vẫn phản hồi
  0,1 giây; gợi ý tới sau 4–7 giây trên CPU

**`v0.13.0`** (11/11, #347) — ba gợi ý còn lại:

- **Gợi ý người xử lý** (#318) theo số việc đang giữ và kinh nghiệm với loại yêu cầu, trọng số trong
  biến môi trường, chỉ người đúng phòng; không cần mô hình
- **Hồ sơ đã giải quyết tương tự** (#319). Ảnh PostgreSQL đổi sang `pgvector/pgvector:0.8.6-pg16`,
  mô hình nhúng Qwen3-Embedding-0.6B dưới `tri-tue`; biểu mẫu gửi hiện tối đa ba hồ sơ, ẩn tên và liên
  hệ; ghi nhận yêu cầu được ngăn chặn lên bảng điều khiển. Bộ đo 40 câu: recall@3 40/40, trung vị 0,18
  giây mỗi lần tìm. Nâng cụm cũ 200 hồ sơ sang ảnh mới giữ nguyên dữ liệu
- **Khuyến nghị cải tiến bằng câu chữ** (#320) trên màn Quy trình thực tế: mô hình viết việc nên làm,
  con số do hệ thống gắn từ kết quả khai phá, câu không có căn cứ bị bỏ; tắt mô hình thì về câu kết luận
  tất định

Tắt mô hình giữa chừng: tìm tương tự trả rỗng trong hạn chót 2 giây, gửi hồ sơ và phân loại tay vẫn
chạy. **Giai đoạn 4 không có lần `down -v` nào**: mọi thay đổi lược đồ đi bằng migration `0016`–`0022`.

**Bộ kiểm thử** qua bốn bản: pytest dịch vụ ứng dụng 566 → 580 → 608 → **650**; dịch vụ khai phá 148 →
168 → **176**; kịch bản giao diện 95 → 139 → 143 → **159**.

**ADR**: ADR-0007 navigator chấp nhận 08/11, **giảng viên xác nhận 10/11** kèm điều kiện mô hình nhiều
giấy phép (#340). ADR-0008 chấp nhận 08/11, phần sinh văn bản cài ở #316/#317, nhúng véc-tơ và pgvector
ở #319.

**Issue đã đóng**: #239, #243, #249, #253, #254, #314, #315, #316, #317, #318, #319, #320, #340

---

## Đang làm

Không có issue nào đang làm dở. Giai đoạn 4 đã khép về chức năng; issue gốc #322 còn mở chờ
navigator đóng, #321 để ngoài phạm vi thi.

---

## Việc tiếp theo

### Theo thứ tự

1. **Tuần 16 — nền tảng vận hành, đợt `v0.14.0`**: #247 quan sát vận hành, #248 kiểm chữ ký tệp và
   quyết định về quét mã độc, #251 kênh thông báo thư điện tử
2. **Giai đoạn 5 khi có đề thi** — phân tích đề, thay dữ liệu khởi tạo, bổ sung phần thiếu, phát hành
   **`v1.0.0`**. Đề thi công bố trong tháng 11 — có thể đổi thứ tự toàn bộ danh sách này
3. **Gửi tệp `.tar.gz` cho nhóm kia** và ghi lại lỗi họ gặp khi cài theo README — việc giảng
   viên giao từ 15/10; gửi bản phát hành mới nhất

### Chờ giảng viên

Đã hỏi bằng bình luận trên từng issue ngày 03/11, nhắc lại ở #322 ngày 08/11:

- **ADR-0006** (#46) — nhóm đề xuất để kho tri thức ngoài phạm vi thi (#321); truy xuất tri thức ở
  Giai đoạn 4 chỉ làm trên hồ sơ đã giải quyết (#319)
- **Sáu issue Tuần 16 cần thảo luận**: #242, #244, #245 (chạm "triển khai lên máy chủ thật" ngoài phạm
  vi), #246 (lưu giữ và xóa dữ liệu cá nhân), #252 (ủy quyền khi vắng mặt), #255 (màn quản trị cấu hình
  quy trình)
- **Xác nhận các con số navigator đã đặt tạm trong dữ liệu** — cơ sở và nguồn của từng số đã
  ghi ở `process-flow.md` mục 9 (#276). Những số còn ghi "giá trị mẫu, chưa có nguồn": gia hạn
  50 % mỗi lần, ân hạn một phần tư hạn, cửa sổ mở lại 7 ngày, hạn chuẩn theo loại; giới hạn tệp
  đính kèm 10 MB, 5 tệp mỗi lần, 20 tệp mỗi hồ sơ (#80)
- **Nghẽn ở điều phối viên khi hồ sơ nhiều** (góp ý 29/10) — nhóm đã làm hướng gợi ý phân loại có xác
  nhận (#239, #317); còn chờ ý giảng viên có cần thêm lối cho loại rõ ràng đi thẳng phòng không
- **Có cần quét vi-rút tệp đính kèm không** (#80) — hiện chỉ chặn bằng danh sách đuôi chặt và
  kiểm chữ ký đầu tệp
- **Công khai kho mã khi nào** — phải trước 07/12; công khai thì bật lại quy tắc bảo vệ nhánh
- **Kênh thông báo** — các luật mới đều "gửi thông báo", hệ thống chưa có kênh nào. Đề xuất
  tạm dùng lời nhắn tự động trên hồ sơ cộng dấu trên hàng đợi; email là việc riêng
- **AI trong hộp thư được tự động tới đâu** — nhóm đề xuất AI chỉ soạn nháp câu hỏi và tóm
  tắt câu trả lời, không tự bấm cạnh nào, theo `CLAUDE.md` mục 4.3
- **Mọi nhân viên có vai trò người gửi không** — ảnh hưởng realm mẫu

### Việc vận hành, không cần issue

1. Bật bắt buộc dấu xanh của tích hợp liên tục trước khi merge — chỉ có hiệu lực khi kho công
   khai (`CONTRIBUTING.md` mục 2.6)
2. Chuyển kho mã sang công khai trước khi nộp bài; khi đó mới bật lại được
   `delete_branch_on_merge` an toàn, và đăng trang tài liệu `docs-site/`
3. Giai đoạn đóng gói: đo hiệu năng, công bố **cấu hình máy tối thiểu** — giảng viên nhắc
   trước để nhóm không quên

---

## Đang vướng

| Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| Quy tắc bảo vệ nhánh chưa có hiệu lực | Quy trình phụ thuộc kỷ luật cá nhân thay vì ràng buộc kỹ thuật | Chuyển kho mã sang công khai. Trong lúc chờ, tuân thủ tự giác |
| Chưa chốt công cụ quản trị cơ sở dữ liệu | Chưa ảnh hưởng, chỉ là công cụ hỗ trợ | Đã trình hai phương án, chờ ý kiến giảng viên |
| Ngân sách bộ nhớ tăng dần theo từng nền tảng | Bảng chấm đòi dựng được trên máy sạch ngày chấm | **Đo thật cả cụm sáu dịch vụ: 1,55 GiB.** Hai dịch vụ ứng dụng chỉ thêm khoảng 110 MB; phần tăng còn lại là Keycloak phình theo JVM. Dịch vụ khai phá thêm khoảng 174 MiB cho 1.000 hồ sơ (ADR-0007); mô hình là tùy chọn. **Chưa đo lại cả cụm bảy dịch vụ** — làm ở giai đoạn đóng gói cùng cấu hình máy tối thiểu |
| **Ảnh dịch vụ khai phá nặng khoảng 1 GB** (982 MB, vì bộ thư viện số học kéo theo PM4Py) | Lần dựng đầu trên máy sạch lâu hơn, tốn ổ đĩa; README và trang tài liệu còn ghi 6 GB ổ đĩa đo trước khi có dịch vụ này | Đo lại ổ đĩa cả cụm ở giai đoạn đóng gói. Nếu cần nhẹ hơn, bộ máy dự phòng `noi_bo` không dùng PM4Py đã có sẵn |
| **Mô hình 1,5B gợi ý mức ưu tiên yếu** (38,8 % trên 80 hồ sơ mẫu) và **gợi ý phòng dưới ngưỡng** (62,5 % so với bảng ánh xạ 86,2 %, ngưỡng 80 %) | Gợi ý sai làm điều phối viên mất tin vào thẻ gợi ý | Gợi ý phòng của mô hình tắt mặc định, giữ bảng ánh xạ. Mức ưu tiên vẫn hiện thẻ nhưng người quyết định; tỷ lệ ghi đè trên bảng điều khiển đo độ chính xác thật. Đổi mô hình lớn hơn là đổi tệp trong volume, không đổi mã |
| **Bộ đo hồ sơ tương tự do nhóm soạn bằng công cụ** (#319) | Recall@3 40/40 đo trên câu hỏi do chính nhóm soạn, không phải dữ liệu người dùng thật — dễ bị ban giám khảo hỏi | Nói rõ nguồn bộ đo khi trình diễn; số thật là tỷ lệ ngăn chặn ghi nhận trên bảng điều khiển |
| **Nhận diện giấy phép trên GitHub** | Khi `LICENSE` gốc có thêm đoạn ngoại lệ (#340), API kho trả `NOASSERTION` / "Other" (kiểm 11/11) | Navigator chốt 11/11: `LICENSE` gốc giữ nguyên văn MIT, ngoại lệ cho `services/khai-pha/` chuyển sang `LICENSES.md` (cùng `README.md`, `NOTICE`); kiểm lại nhãn MIT sau khi lên `main` |
| **Lược đồ khởi tạo chỉ nạp một lần** | Ai đã có volume cũ mà kéo mã mới về sẽ gặp lỗi thiếu cột, và thông báo lỗi không chỉ ra nguyên nhân | Mỗi lần `infra/postgres/init/`, `infra/seed/` hoặc realm Keycloak đổi, cả nhóm phải `down -v` rồi dựng lại; migration Alembic thì tự chạy. Thành viên tự kiểm sau mỗi lần `pull` bằng lệnh ở bộ luật trợ lý thành viên mục 9. Tuần 7 có năm lần như vậy: #84 đổi realm; #94, #79, #127 và #128 đổi lược đồ và dữ liệu khởi tạo. Tuần 8 có hai: #131 và #145 đổi realm. Tuần 9 có hai: #153 và #154 ngày 05/10, #156 ngày 06/10. Tuần 10 có năm: #199 và #142 ngày 12/10 đổi lược đồ, #144 đổi dữ liệu cùng ngày; #143, #175, #101 ngày 15/10. Gom lên `main` sát nhau nên cả nhóm chỉ `down -v` hai lần, mỗi ngày một lần. Tuần 11–12 có ba, cùng ngày 26/10: #102 và #80 đổi lược đồ và dữ liệu khởi tạo, #157 đổi một nhãn; kéo `dev` từ trước 26/10 về thì `down -v` một lần. #80 còn thêm biến vào `infra/.env.example` — có giá trị mặc định trong Compose nên `.env` cũ vẫn chạy. Tuần 13 có ba: #227 (cột `primary_scope`), #250 (bảng `request_type_fields`), #236 (realm, chủ đề đăng nhập); kéo `dev` qua 28/10 thì `down -v` một lần. Tuần 14–15 **không có lần nào**: #304 chỉ thêm migration; #305 đổi lược đồ và dữ liệu khởi tạo nhưng kèm migration `0015` thêm cột cho cụm cũ — lệnh kiểm vẫn báo `down -v`, chỉ cần `up -d --build`. **Từ #254 (`v0.10.0`) lược đồ cấu hình nằm trong migration**: cụm dựng từ `v0.9.1` trở đi nâng bằng `up -d --build`, Giai đoạn 4 không có lần `down -v` nào — kể cả tài khoản chỉ đọc của dịch vụ khai phá (`0019`) và ảnh pgvector (#319). Cụm cũ hơn `v0.9.1` vẫn phải dựng lại |
| **Máy thành viên không đủ tài nguyên dựng cụm** | #48 phải chuyển người làm: bản dựng ảnh chứa hỏng giữa chừng với lỗi `EOF` trên một máy còn khoảng 7,5 GB trống. **Nguyên nhân chưa xác nhận** — nghi ổ gần đầy, hoặc Docker mất kết nối khi dựng nhiều ảnh cùng lúc. Con số 15 GB mà một trợ lý AI đòi cũng chưa đo. Ở #47, đĩa ảo Docker nằm trên ổ C gần đầy làm ảnh vừa kéo báo lỗi đọc ghi và ghi đồng bộ chỉ vài kB/s — số đo trên máy đó bỏ đi | Giao cho máy đó việc không cần dựng cụm — tài liệu, review pull request — cho tới khi giải phóng được ổ đĩa. Trước khi dựng hay đo, chuyển *Disk image location* của Docker Desktop sang ổ còn trống. Con số này cũng là dữ liệu cho mục **cấu hình máy tối thiểu** ở giai đoạn đóng gói |
| **Sáu issue Tuần 16 chờ giảng viên**: #242, #244, #245, #246, #252, #255 | Chưa làm được trong mốc hạn 29/11; vài issue chạm "triển khai lên máy chủ thật" ngoài phạm vi thi | Đã hỏi 03/11, nhắc lại 08/11 ở #322. Trong lúc chờ làm #247 #248 #251 |
| Đường truyền tới `github.com` chập chờn | Có lúc `git push` và `git pull` treo rồi thất bại | Đã đặt `http.version HTTP/1.1` và hai tham số tốc độ tối thiểu, khắc phục được. Nếu tái diễn thì chuyển remote sang SSH — cả cổng 22 lẫn 443 của SSH đều thông |

---

## Quyết định đã chốt

Ghi vắn tắt để tránh bàn lại. Chi tiết và lý do xem `docs/adr/`.

| Quyết định | Ghi chú |
|---|---|
| Bài toán nghiệp vụ: Cổng vận hành yêu cầu nội bộ | Đã trình giảng viên, được duyệt |
| Điểm sáng tạo: vòng phản hồi tự soi quy trình (khai phá quy trình) | Đã trình giảng viên, được duyệt |
| Bộ công nghệ nền: Next.js + FastAPI + PostgreSQL + Docker | Thống nhất với giảng viên |
| Giấy phép sản phẩm: MIT, riêng `services/khai-pha/` AGPL-3.0-or-later | Mô hình nhiều giấy phép, bảng ở `LICENSES.md` — điều kiện giảng viên đặt khi xác nhận ADR-0007 ngày 10/11, #340 |
| Mô hình nhánh ba tầng: nhánh công việc → `dev` → `main` | |
| Cách hợp nhất: squash cho chặng vào `dev`, merge commit cho chặng lên `main` | Squash sai chặng sẽ hỏng nhật ký thay đổi |
| Nguyên tắc AI chỉ gợi ý, con người quyết định | Theo góp ý của giảng viên |
| Thứ tự xây dựng: hoàn thiện luồng thủ công trước, gắn AI sau | Theo góp ý của giảng viên |
| Tệp khóa phiên bản bắt buộc commit, không đưa vào `.gitignore` | Ảnh hưởng tiêu chí PoF mục 4 và 5 |
| Toàn bộ tài liệu kỹ thuật công khai, không gitignore | Ảnh hưởng tiêu chí chấm số 10 và PoF mục 6 |
| Luồng nghiệp vụ chốt bằng sơ đồ trạng thái | Mười một trạng thái, ba lối phê duyệt, Poka-yoke khi hủy, tự leo thang SLA — xem `docs/process-flow.md` |
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
| Thời gian ở `awaiting-info` **không tính** vào SLA, nhưng ghi riêng tổng thời gian dừng | Người xử lý không bị phạt khi người tạo chậm; tổng thời gian dừng để khai phá quy trình phát hiện lạm dụng. **Giảng viên xác nhận 08/10** ở #143 |
| Trạng thái nào chạy đồng hồ SLA là **dữ liệu**, không phải mã | Cột `states.sla_running` trả lời cả hai câu: đồng hồ bắt đầu từ đâu và dừng ở đâu |
| Trường quyết định chỉ đặt được ở cạnh có ràng buộc quản nó | Người xử lý không tự nâng được mức ưu tiên việc của mình — #78, `ARCHITECTURE.md` mục 7 |
| Giao người xử lý là **tùy chọn** | Ngoài đời người trong phòng hay tự chia việc; hồ sơ chưa giao ai vẫn thuộc cả phòng. Navigator chốt 23/09 |
| Leo thang lại có **khoảng ân hạn**, không cấp hạn mới | Hồ sơ vẫn được ghi nhận quá hạn; người vừa được giao lại hay vừa bổ sung xong có ân hạn trước khi bị leo thang lần nữa. Ân hạn là dữ liệu theo loại yêu cầu — #94. **Mở lại thì khác**: cấp hạn mới, xem dưới — #102 |
| Bổ sung thông tin xong thì **về đúng chỗ đã hỏi** | Hỏi ở *Đã gửi* về *Đã gửi*, trưởng phòng hỏi thì về *Chờ phòng ban xác duyệt*, người xử lý hỏi thì về *Đang xử lý* — #79 |
| Mở lại: **trong 7 ngày làm việc sau khi đóng, tối đa hai lần, có lý do, cấp hạn mới**; quá hai lần thì tạo hồ sơ mới liên kết `parent_request_id` | Giảng viên chốt 08/10, **thay** quyết định 23/09 "không giới hạn, không cấp hạn mới". Hai cạnh từng đánh dấu `[CHỜ XÁC NHẬN]` được giữ và nhãn đã gỡ. Đã làm ở #102: mở lại từ cả *Hoàn tất* lẫn *Đã đóng*, chung một bộ đếm; cửa sổ 56 giờ làm việc và số lần nằm trong dữ liệu |
| Nhánh điều phối viên đóng khi không phòng nào nhận sang trạng thái kết thúc riêng ***Không tiếp nhận*** | Không đọc như hồ sơ đã xử lý xong; lý do bắt buộc; không mở lại — người gửi tạo hồ sơ mới liên kết. Giảng viên đề xuất 08/10, navigator chốt tên 26/10 — #102 |
| Mở lại sau khi đóng chỉ với hồ sơ **từng làm xong**; mở lại là **chu kỳ xử lý mới** | Hồ sơ tự đóng vì chưa bổ sung thông tin chưa có gì "chưa đạt". Đồng hồ đếm lại từ 0, gia hạn cũ về 0; số liệu chu kỳ cũ còn nguyên trong nhật ký. Navigator chốt 26/10 — #102 |
| Cạnh rời trạng thái kết thúc **hợp lệ khi khai cửa sổ thời gian** | Lược đồ trước đó cấm hẳn. Nay `CHECK` đòi cạnh rời trạng thái kết thúc phải có `reopen_window_hours`; cạnh *Mở lại sau khi đóng* là cạnh duy nhất. Navigator chốt 26/10 — #102 |
| Tệp đính kèm **đi qua dịch vụ ứng dụng**, không presigned URL | Quyền kiểm mỗi lần tải; người ngoài nhận 404 chứ không 403. Navigator chốt 26/10 — #80 |
| Ai mở được hồ sơ thì xem được tệp; **chỉ người gửi đính kèm**, ở cạnh mang cờ `accepts_attachments` | Không luật quyền thứ hai để lệch với luật xem hồ sơ; đính kèm khóa khi hồ sơ tới phòng ban. Navigator chốt 26/10 — #80 |
| Hồ sơ hủy **vẫn giữ tệp đính kèm** | Truy vết; bảng `case_attachments` chỉ ghi thêm, không có thao tác xóa nào. Navigator chốt 26/10 — #80 |
| Giới hạn tệp đính kèm là **biến môi trường** | Đuôi, MB mỗi tệp, số tệp — đổi `.env` rồi khởi động lại, không `down -v`; giao diện hỏi dịch vụ nên hai lớp chặn không lệch. Navigator chốt 26/10 — #80 |
| **Một khái niệm một tên** trên giao diện | Người gửi, điều phối viên, người xử lý, Trao đổi, dòng thời gian; thông báo lỗi nói bằng nhãn chứ không bằng mã. Bảng ở `ARCHITECTURE.md` mục 8.3. Navigator duyệt 26/10 — #157 |
| Hồ sơ bị phòng ban trả **giữ phòng cũ** tới khi điều phối chọn lại | Nhật ký ghi đủ lần đổi phòng nhờ cột `changes` — #100 |
| Lý do *Từ chối vì sai chuyên môn* **bắt buộc** | Là cờ `requires_note` trong dữ liệu |
| **Ranh giới máy trạng thái** — ADR-0005 | Thao tác đổi hồ sơ — trạng thái, trường quyết định, nội dung — đi qua cửa chuyển trạng thái; lời nhắn đi bảng riêng. Người gửi sửa được nội dung khi hồ sơ chưa tới phòng ban. Giảng viên duyệt 24/09 |
| Mức ưu tiên vẫn chỉ điều phối viên đặt | Ví dụ của giảng viên ở #81 có nhắc người gửi đổi mức ưu tiên; nhóm giữ ràng buộc Poka-yoke và đã báo lại |
| Nhịp phát hành: **gom một tới ba issue mỗi pull request vào `dev`, một pull request `dev → main` cho cả đợt** | Từ 02/11, thay nhịp "mỗi issue một pull request `dev → main`" dùng từ 22/09. Nhật ký thay đổi vẫn mỗi commit squash một mục; đợt khép ít nhất mỗi cuối tuần. Navigator chốt 02/11 |
| Mọi trợ lý AI đọc chung một bộ quy tắc | `AGENTS.md` trỏ về `CLAUDE.md`, để Antigravity và Codex cũng không tự commit — #117 |
| Đổi hồ sơ mà giữ trạng thái là **cạnh tự trỏ** | Nhận việc về mình, sửa nội dung — đi qua cửa chuyển trạng thái để nhật ký giữ giá trị cũ. Mỗi trạng thái tối đa một cạnh tự trỏ, không có ở trạng thái chờ người khác — #127 |
| Lời nhắn **không phải cạnh** | Bảng riêng chỉ ghi thêm, không vào nhật ký sự kiện, không chạm dòng hồ sơ. Hai chiều; ai mở được hồ sơ thì nhắn được; hồ sơ kết thúc thì chỉ đọc — #128 |
| *Hỏi tiến độ* chỉ của người gửi, chỉ khi hồ sơ ở phòng ban | Hỏi lại khi đã có trả lời hoặc quá bốn giờ, để số lần phòng ban bị hối mà tầng `I` đếm là số thật. Dấu hiệu hàng đợi suy từ ai nhắn sau cùng, không theo dõi đã đọc — #128 |
| Liên hệ người gửi **tra lúc mở trang, không lưu** | Số điện thoại là thuộc tính hồ sơ người dùng trong realm, không bắt buộc, người dùng tự sửa. Điểm cuối riêng ở mỗi buồng lái; cổng người gửi không hiện liên hệ nhân viên — #131 |
| Người cùng phòng **hoàn thành được** hồ sơ đã giao người khác | Nhật ký ghi đúng người bấm. Navigator chốt 02/10 sau buổi chạy thử |
| *Quay lui* là đi qua **cạnh làm lại khai trong dữ liệu** | Từ chối, mở lại, sửa nội dung ở *Đã phân loại* — không phải mọi lần vào lại trạng thái cũ. Vòng hỏi – đáp không tính — #153 |
| Điều phối viên **không tự điều phối** hồ sơ do chính mình gửi | Chỉ gắn vào các cạnh của vai điều phối; phòng ban vẫn tự làm việc của mình — #154 |
| Khung chat: **hộp thư chung, mỗi cuộc trò chuyện gắn một hồ sơ** | Không làm phòng theo cặp người: đổi người xử lý thì người mới phải đọc được trao đổi cũ, và mọi tin phải gắn hồ sơ cho khai phá quy trình. *Yêu cầu bổ sung thông tin* giữ nguyên trong bảng thao tác. Có trò chuyện nội bộ chỉ nhân viên thấy. Navigator chốt 04/10 — #155, #156 |
| Thành viên làm khảo sát **không cần `pull` giữa chừng** | Pull request khảo sát chỉ thêm tệp trong `docs/`, không xung đột với mã đang đổi |
| Hộp thư: mỗi người thấy **hồ sơ mình đang giữ** | Điều phối viên thấy hàng đợi điều phối cộng hồ sơ mình đã nhắn. Đã đọc khi lời nhắn đang hiện trên màn hình. Navigator chốt 05/10 — #155 |
| Trò chuyện nội bộ ẩn **theo hồ sơ**, không theo vai trò | Người gửi của hồ sơ không thấy, kể cả khi người đó là nhân viên. Hai cuộc mỗi hồ sơ; hồ sơ kết thúc thì chỉ đọc — #156 |
| Hồ sơ nằm im: **cảnh báo trước, rồi tự trả về hay tự đóng**, ghi sự kiện | *Chờ phòng ban xác duyệt* tự trả về điều phối viên; *Chờ bổ sung thông tin* nhắc rồi tự đóng; *Hoàn tất* nhắc rồi tự đóng. Mọi ngưỡng là dữ liệu. Giảng viên chốt 08/10 — #142, #143, #144 |
| Hạn mặc định theo **loại yêu cầu × mức ưu tiên** | Khẩn 50 %, cao 75 %, bình thường 100 %, thấp 150 % hạn chuẩn. Điều phối viên chỉnh hạn được, có lý do và nhật ký, không chỉnh sau khi đóng. Giảng viên chốt 08/10 — #101 |
| Trang hồ sơ đặt **việc và hạn trước nhật ký** | Dòng thời gian mặc định thu gọn về bước hiện tại; màn hẹp đưa thẻ hạn và thao tác lên đầu. Theo nhận xét của giảng viên 11/10 — #189 |
| Mọi hạn đếm theo **giờ làm việc** của một lịch trong dữ liệu | Một lịch mặc định cho cả công ty; mọi phép đo đi qua hai hàm SQL dùng chung cho bộ quét và dịch vụ. Navigator chốt 12/10 — #199 |
| Một cặp trạng thái có tối đa **một cạnh người và một cạnh hệ thống** | Ràng buộc duy nhất của bảng cạnh thêm `is_system`; engine chọn cạnh theo loại tác nhân. Hạn chờ và mốc báo trước là cột trên cạnh. Navigator chốt 12/10 — #142 |
| Tự trả về điều phối **không** tính là quay lui | Phòng ban không từ chối nội dung, chỉ để quá hạn. Navigator chốt 12/10 — #142 |
| Hồ sơ tự đóng ở *Chờ bổ sung thông tin* sang ***Đã đóng***, không sang *Đã hủy* | Người gửi không chủ động bỏ yêu cầu; hồ sơ này **không** mở lại được (chưa từng làm xong) — người gửi tạo hồ sơ mới. Navigator chốt 15/10 và 26/10 — #143, #102 |
| Ngưỡng sắp hết hạn là **phần trăm** theo loại yêu cầu | Co giãn theo hạn của từng hồ sơ, kể cả khi hạn đổi theo mức ưu tiên. Navigator chốt 15/10 — #175 |
| Gia hạn: **điều phối viên lần đầu, trưởng phòng khi đã leo thang** | Điều phối viên gia hạn ở *Đã phân loại* và *Chờ phòng ban xác duyệt*; trưởng phòng ở *Đã leo thang*, vì *Đang xử lý* đã có cạnh tự trỏ *Nhận việc về mình*. Nhập số giờ cộng thêm kèm lý do. Navigator chốt 15/10 — #101 |
| Bản cài đặt gửi người ngoài là **tệp `.tar.gz` của bản phát hành** | Cùng đường ban giám khảo lấy mã; kho còn riêng tư nên gửi tệp, không gửi liên kết. Navigator chốt 15/10 — #206 |
| Cờ "cần tôi xử lý" là **bước chính khai trong dữ liệu** | Cột `transitions.primary_scope` (theo vai hay chỉ người được giao); không suy từ "có nút bấm được". Navigator duyệt 27/10 — #227 |
| Nút trên dòng việc **chỉ mở trang hồ sơ** ở khối thao tác | Không bấm-là-xong: bước chính thường cần nhập thêm, bảng thao tác là chỗ duy nhất gửi lệnh. Navigator chốt 27/10 — #228 |
| Trạng thái hệ thống **chỉ quản trị viên thấy** | Màn Hệ thống riêng; trang chủ không còn bảng tình trạng cụm. Navigator chốt 27/10 — #229 |
| **Nhận diện mới**: phẳng, xám trung tính, nhấn chàm, có sáng và tối | Navigator chọn phương án B (danh sách việc + cột tổng quan) cho cả bốn vai, 27/10 — #226 |
| Trường riêng theo loại **lưu JSONB, khai ở bảng cấu hình** | Không dùng bảng thực thể–thuộc tính–giá trị; sửa qua cạnh *Sửa nội dung*; điều phối đổi loại không chặn. Navigator chốt 27/10 — #250 |
| Gom nhiều issue cùng nhóm vào **một pull request** | Mỗi issue một dòng `Closes #N` trong thân PR và commit. Ngoại lệ cho nhóm #226 và #240; mặc định vẫn mỗi issue một PR. Navigator chốt 27/10 |
| Tích hợp liên tục **chỉ chạy trên pull request** | Không chạy khi nhánh nhận commit, tránh sáu kiểm tra trùng. Navigator chốt 28/10 — #241 |
| Khung trao đổi **chia phía theo người viết** | Bên phải chỉ là tin của chính người xem; tin của người gửi có nền riêng. Navigator góp ý 28/10 — #274 |
| Con số của quy trình mẫu **có cơ sở hoặc ghi rõ là giá trị mẫu** | Bảng ở `process-flow.md` mục 9; mọi con số vẫn là dữ liệu doanh nghiệp tự đặt. Theo góp ý buổi báo cáo 29/10 — #276 |
| Đổi quy trình: hồ sơ đang chạy **giữ bộ quy tắc lúc tạo** tới khi kết thúc | Mọi màn liệt kê lấy hồ sơ của mọi bộ còn hồ sơ đang mở; không chuyển hồ sơ sang bộ mới giữa chừng — #278, #299 |
| Chỉ số báo cáo nằm trong **view cơ sở dữ liệu**, không tra mã trạng thái | View tra cờ trên bảng trạng thái và bộ quy tắc của từng hồ sơ, nên đổi quy trình không phải sửa view; bảng điều khiển là tệp YAML trong kho, Superset tự nạp — #304 |
| Phạm vi xem báo cáo là **cột `roles.report_scope`** | `department` (phòng mình), `all` (toàn công ty), để trống là không xem; không tra tên vai trò trong mã. Navigator chốt 03/11 — #305 |
| Bảng điều khiển **nhúng bằng thư viện chính thức**, cổng tự ghi tiêu đề và phạm vi | Không tự viết khung nhúng; ẩn tiêu đề và thanh lọc tiếng Anh của Superset. Navigator chốt 03/11 — #305 |
| Tầng `I`: **khai phá quy trình làm trước** phân loại | Đổi thứ tự ROADMAP (trước đó phân loại → truy xuất → khai phá): khai phá là điểm sáng tạo của đề tài và chỉ chờ một bản ghi. Navigator chốt 04/11 — #322 |
| Lệch chuẩn trong khai phá đo **so với luồng chính**, không so với cạnh thiết kế | Engine chỉ cho đi cạnh có trong bộ quy tắc, nên so với thiết kế luôn ra không lệch; đo làm lại, leo thang, mở lại, chuyển phòng nhiều lần và điểm nghẽn theo thời gian chờ — #314 |
| Dịch vụ khai phá có **tài khoản cơ sở dữ liệu chỉ đọc riêng** | Không dùng chung tài khoản chỉ đọc của Superset. Navigator chốt 04/11; khi cài đặt tạo bằng migration `0019` thay vì lược đồ khởi tạo, nên không cần `down -v` — #314 |
| `I` — **PM4Py chỉ trong dịch vụ khai phá tách riêng**, kèm bộ máy dự phòng không dùng thư viện đó | Giao tiếp qua HTTP, tích hợp liên tục chặn `import pm4py` ở nơi khác; đổi bộ máy bằng một biến môi trường. Giảng viên xác nhận 10/11 — ADR-0007, #314 |
| `I` — **mô hình ngôn ngữ cục bộ là tùy chọn** (hồ sơ `tri-tue`), gọi qua một lớp duy nhất | llama.cpp server, Qwen2.5-1.5B-Instruct và Qwen3-Embedding-0.6B, pgvector trong ảnh PostgreSQL; cụm mặc định chạy đủ ở chế độ thủ công — ADR-0008, #316, #319 |
| Gợi ý phòng của mô hình **chỉ thay bảng ánh xạ khi đo đạt từ 80 %** | Đo 62,5 % nên tắt mặc định (`SUGGEST_DEPARTMENT_FROM_MODEL`) — #317 |
| Khuyến nghị bằng câu chữ: **mô hình viết câu, hệ thống gắn số** | Câu nhắc tới con số không tra được trong kết quả khai phá thì bỏ — #320 |

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

**Kiểm "không chạm dòng hồ sơ" phải so cả `ctid`** (#128)

Bài kiểm muốn chứng minh gửi lời nhắn không ghi gì vào `requests`. So giá trị các cột là
chưa đủ: bài kiểm dựng hồ sơ và gửi lời nhắn trong cùng một giao dịch, mà `now()` trả cùng
một mốc suốt giao dịch, nên một lệnh `UPDATE ... SET updated_at = now()` ghi ra đúng giá trị
cũ và lọt qua. PostgreSQL tạo phiên bản dòng mới mỗi lần `UPDATE`, nên `ctid` đổi — so
thêm `ctid` trước và sau mới bắt được.

**Squash giữ người mở pull request làm tác giả**

Navigator sửa thêm một commit trên nhánh của thành viên (#135) rồi squash: commit trên
`dev` vẫn đứng tên thành viên. Nên sửa lỗi nhỏ thay thành viên trước khi hợp nhất không
làm mất phần đóng góp của họ. Xóa sạch ô Extended description tự sinh, kể cả các dòng
`Co-authored-by`, như mọi lần squash.

**Luôn mở thử đường dẫn nguồn, kể cả khi trợ lý AI viết**

Ở #135, ba trên bốn đường dẫn tới tệp giấy phép trỏ tới trang không tồn tại — trợ lý của
thành viên đoán đường dẫn theo khuôn quen thuộc thay vì mở tệp. Soát khảo sát thì mở từng
đường dẫn, và ghi dòng đầu của tệp giấy phép vào bảng để người đọc thấy tệp đã được mở
thật.

**Phép thử phải có đáp án biết trước**

Ở #48, dữ liệu ảo do bộ sinh tạo ra luôn đi đúng thiết kế, nên "không tìm thấy cạnh lệch"
không chứng minh thư viện bắt được lệch. Cách làm: cài lệch có chủ đích vào vài hồ sơ đã
biết số, rồi đòi thư viện chỉ ra đúng những hồ sơ đó. Bản đầu của chính phép thử cũng sai —
chọn trúng một hồ sơ không có bước cần bỏ, nên không có gì lệch — và chỉ lộ ra vì đáp án
biết trước không khớp.

**Next không cho ghi cookie lúc dựng trang** (#150)

`cookies().set()` chỉ chạy trong Server Action và Route Handler; gọi lúc dựng trang thì ném
lỗi. Cổng làm mới access token ngay trong lời gọi dịch vụ, mà lời gọi lúc dựng trang lại là
chỗ hay làm mới nhất. Lỗi ghi cookie nằm chung một khối `catch` với lỗi làm mới, nên token
mới vừa lấy được bị vứt, lời gọi đi bằng token hết hạn và nhận 401 — mỗi năm phút một lần.
Không có dòng nhật ký nào, vì `catch` nuốt sạch. Cách tìm ra: hạ hạn access token của realm
cụm thử xuống 60 giây rồi đăng nhập thật, chờ hết hạn, mở lại trang.

**Tài khoản nạp từ realm phải khai vai trò mặc định** (#131)

Người dùng khai `realmRoles` riêng trong tệp realm thì **không** tự nhận
`default-roles-dx-os-lab`, nên thiếu quyền vào trang tài khoản Keycloak: trang đó trả 401 dù
đăng nhập đúng. Mọi tài khoản mẫu thêm sau này phải liệt kê vai trò mặc định trong
`realmRoles`.

**Hai nút cùng chỗ trong React phải có `key` riêng** (#188)

Bước 2 của biểu mẫu có nút *Tiếp tục* (`type="button"`), bước 3 có nút *Gửi yêu cầu*
(`type="submit"`), cùng một vị trí trong cây. Không có `key`, React dùng lại đúng phần tử đó và
chỉ đổi thuộc tính: cú bấm *Tiếp tục* chuyển sang bước 3, phần tử thành nút gửi **trước khi**
trình duyệt xử lý xong cú bấm, và biểu mẫu được gửi luôn. Lỗi không lộ khi đọc mã hay khi gọi
`click()` bằng script — chỉ cú bấm chuột thật mới thấy. Cách làm đúng: `key` khác nhau cho hai
nút, và nút không gửi chặn hành vi mặc định.

**`style` viết thẳng trên thẻ thắng quy tắc ẩn trong CSS** (#189)

Ô đặt `display` trong thuộc tính `style` thì quy tắc `.an-tren-hep { display: none }` trong
`globals.css` không ẩn được nó ở màn hẹp, vì thuộc tính viết thẳng trên thẻ đứng trên mọi bộ
chọn. Quy tắc ẩn theo màn hình phải mang `!important`, hoặc bỏ `display` khỏi `style`.

**Bài kiểm thử quét điểm cuối phải đọc OpenAPI, không đọc `app.routes`** (#156)

Router lồng nhau của FastAPI không hiện đủ trong `app.routes`, nên bài quét "người gửi không
thấy tin nội bộ ở bất kỳ điểm cuối `GET` nào" bỏ sót phần lớn điểm cuối mà vẫn xanh. Lấy danh
sách từ `app.openapi()["paths"]` — đúng thứ máy khách thấy.

**SQLAlchemy 2: `/` giữa hai số nguyên là chia số thực** (#101)

Biểu thức `a / b` trên hai cột số nguyên sinh phép chia ra số thực, không cắt như `/` của
PostgreSQL viết tay. Bộ quét tính hạn bằng `//` để khớp phép tính trong Python.

**Cột `SMALLINT` nhân 3600 trong SQL bị tràn** (#142)

Giờ khai bằng `SMALLINT`, đổi ra giây thì vượt miền giá trị. Ép `cast(..., BigInteger)` trước
khi nhân.

**Seed gắn vai trò theo cặp trạng thái phải loại cạnh hệ thống** (#142)

Phép nối theo `(from_state, to_state)` gắn vai trò, ràng buộc cho mọi cạnh cùng cặp. Từ khi một
cặp có cả cạnh người lẫn cạnh hệ thống, phải thêm `AND NOT t.is_system`, không thì cạnh hệ thống
nhận luôn vai trò của cạnh người.

**Kể lại thay đổi trên dòng thời gian không được ép mọi giá trị về chuỗi** (#101)

Cột `changes` lần đầu mang giá trị số — số giờ gia hạn. Đoạn kể lại giả định mọi giá trị là
chuỗi nên trang hồ sơ trả 500. Bộ kiểm thử không thấy vì chỉ kiểm dịch vụ; kiểm qua đăng nhập
OIDC thật mới thấy.

**Khung thao tác phải gắn `key` theo `updated_at` của hồ sơ** (#101)

Sau cạnh tự trỏ, trạng thái không đổi nên React giữ nguyên khung thao tác cũ — khung gia hạn
vẫn mở sau khi đã gửi. Khóa theo cả `updated_at` để khung dựng lại sau mỗi lần đổi hồ sơ.

**Lược đồ cấm cạnh rời trạng thái kết thúc — nới có điều kiện, không bỏ** (#102)

`transitions` có `CHECK (from_is_terminal = FALSE)` và khóa ngoại tổng hợp tới
`states.is_terminal`, nên không thể tạo cạnh xuất phát từ *Đã đóng*. Chỉ đọc luật của giảng viên
thì không thấy — lỗi hiện ra lúc viết cạnh *Mở lại sau khi đóng*. Cách nới: bỏ `CHECK` cấm hẳn,
thêm `CHECK` đòi cạnh nào rời trạng thái kết thúc thì phải khai `reopen_window_hours`, và cột đó
chỉ hợp lệ trên cạnh của người xuất phát từ trạng thái kết thúc. Lỡ tay thêm cạnh thường đi ra
từ một trạng thái kết thúc vẫn bị lược đồ từ chối.

**Cửa sổ thời gian lưu bằng giờ, không phải ngày** (#102)

Lịch làm việc khai khung giờ theo thứ, nên "7 ngày làm việc" không có một con số giờ cố định.
Cột `reopen_window_hours` giữ 56 giờ làm việc — 7 ngày với lịch mẫu 8 giờ — cùng khuôn với
`auto_after_hours`. Đổi lịch thì xem lại con số này, như hai hạn chờ kia.

**Bài kiểm thử cửa sổ phải thay hàm đo thời gian, không lùi nhật ký** (#102)

`event_log` chỉ ghi thêm nên không lùi được mốc vào *Đã đóng*. Ràng buộc `reopen-window` gọi
`giay_lam_viec` ở cấp mô-đun; bài kiểm thử thay hàm đó để thử đúng mốc, quá một giây và đổi cột
dữ liệu — cùng tinh thần "thời điểm xét" của bộ quét hạn chờ.

**Khóa S3 của SeaweedFS cần quyền `Admin` riêng cho thùng mới** (#80)

Khóa chỉ có `Read`, `Write`, `List`, `Tagging` thì `CreateBucket` bị `AccessDenied`. Cấp
`Admin:dxlab-attachments` trong `infra/seaweedfs/s3-config.json` là đủ, và chỉ cho đúng một
thùng. Không cần tạo thùng bằng tay: dịch vụ tự tạo khi tải tệp đầu tiên lên. Đổi
`SEAWEEDFS_BUCKET` thì phải đổi cả tệp đó. SeaweedFS khởi động chậm sau khi khởi động lại
container — gọi ngay sẽ gặp lỗi kết nối.

**Server Action giới hạn thân yêu cầu 1 MB** (#80)

Tải tệp đính kèm đi qua Route Handler (`/api/tep/...`), không qua Server Action. Biểu mẫu gửi vì
vậy tạo hồ sơ bằng Server Action rồi tải tệp bằng `fetch` từ trình duyệt, và tự chuyển trang
khi xong. Tệp tải hỏng thì hồ sơ vẫn đã gửi: chuyển sang trang hồ sơ kèm lời nhắc, không báo lỗi
ở biểu mẫu — báo ở đó thì người gửi bấm gửi lần nữa và sinh hồ sơ thứ hai.

**Thông báo lỗi của engine hiện mã tiếng Anh nếu không tra nhãn** (#157)

`TransitionNotAllowed` và `RoleNotPermitted` từng in `'completed'`, `classifier`. Người gặp
chúng thường là người bấm nút của một trang đã cũ — hồ sơ vừa được người khác chuyển đi — và họ
đọc được nhãn, không đọc được mã. Engine nay tra `states.label` và `roles.label`.

**Bộ quét hạn chờ quét cả dữ liệu thử còn lại trên cụm thử**

Hồ sơ thử còn nằm ở *Chờ bổ sung thông tin* hay *Hoàn tất* trên cụm thử khiến bài kiểm thử so
danh sách chính xác của bộ quét ra thừa mã hồ sơ. Không phải lỗi mã: hủy hay đóng các hồ sơ thử
đó rồi chạy lại, hoặc dựng lại cụm thử. Bài đếm nên so chênh lệch, không so số tuyệt đối.

**Lỗi trong layout của Server Component làm `error.tsx` trắng trang** (#235)

Ném lỗi từ layout phía máy chủ khi dịch vụ không trả lời thì `error.tsx` (thành phần phía trình
duyệt) gặp lỗi React #441 và trang trắng. Màn *hệ thống không phản hồi* vì vậy dựng ngay ở máy chủ
(`KhongPhanHoi`) khi lời gọi quá thời hạn `BACKEND_TIMEOUT_MS`; `error.tsx` giữ cho lỗi bất ngờ.

**`curl` không gửi ngôn ngữ nên che lỗi màn đăng nhập tiếng Anh** (#236)

Keycloak chọn ngôn ngữ theo `Accept-Language` của trình duyệt; `curl` không gửi nên luôn nhận
ngôn ngữ mặc định của realm là tiếng Việt, trong khi trình duyệt đặt tiếng Anh thấy "Sign in". Kiểm
bằng trình duyệt thật với `locale: "en-US"`. Cổng nay gửi `ui_locales=vi`. Chủ đề gốc `keycloak.v2`
đặt màu tiêu đề bằng `!important`, nên chủ đề kế thừa phải `!important` khi đè.

**Qdrant tìm chính xác khi tập nhỏ — recall 1,0 không chứng minh HNSW tốt** (#47)

Qdrant chỉ dựng chỉ mục HNSW khi đoạn dữ liệu vượt `indexing_threshold` (mặc định 10.000 KB),
và dưới `full_scan_threshold` thì quét vét cạn. Đo trên tập vài nghìn véc-tơ mà không hạ hai
ngưỡng đó là đang đo quét chính xác. Véc-tơ ngẫu nhiên lại là trường hợp xấu nhất của HNSW,
nên số recall trên dữ liệu ngẫu nhiên thấp hơn dữ liệu thật.

**Bản đồ định danh của SQLAlchemy chỉ giữ tham chiếu yếu** (#232)

`session.get(RequestType, ma)` trả đối tượng từ bản đồ định danh nếu nó còn ở đó — nhưng bản đồ chỉ
giữ tham chiếu yếu, nên đối tượng bị thu gom ngay khi hàm tính hạn trả về, và hồ sơ kế tiếp lại hỏi
cơ sở dữ liệu. Hàng đợi vài trăm hồ sơ vì thế tốn vài trăm truy vấn chỉ để đọc lại cùng một loại yêu
cầu. Cách chữa: nạp sẵn danh mục và giữ biến suốt lời gọi (`routes._giu_danh_muc`). Cùng đợt, giờ đã
nằm ở trạng thái tính ngay trong câu truy vấn hàng đợi thay vì mỗi hồ sơ một truy vấn — hàng đợi điều
phối 271 hồ sơ từ khoảng 1,1 giây xuống 0,09 giây.

**`position: fixed` lệch trong phần tử còn giữ hiệu ứng `transform`** (#233, #237)

Hiệu ứng hiện trang `.vao` chạy với `animation-fill-mode: both` nên sau khi xong khung nội dung vẫn mang
`transform`, và mọi phần tử `fixed` bên trong tính vị trí theo khung đó chứ không theo cửa sổ: ngăn xem
nhanh lệch xuống, khối thao tác ở đáy rơi khỏi màn hình. Ngăn gắn thẳng vào `<body>`; từ #237 hiệu ứng
hiện trang dùng `backwards`, không để lại `transform`.

**Token khách của Superset: ba chỗ hỏng im lặng** (#305)

Luồng ở `ARCHITECTURE.md` mục 6.3; đây là những chỗ làm mất thời gian điều tra. Thứ nhất, API xin token
khách và API bật cấu hình nhúng đòi **phiên cookie cùng header `X-CSRFToken`** — chỉ gửi token
đăng nhập dạng bearer thì bị từ chối. Thứ hai, token khách chỉ tới dashboard theo **id số của
dashboard**, không theo uuid của cấu hình nhúng, dù thư viện nhúng ở trình duyệt lại nhận uuid. Thứ
ba, ảnh gốc của Superset **không cấp cho vai khách quyền đọc kết nối dữ liệu**: token vẫn ký được, khung
vẫn mở, nhưng biểu đồ trống hoặc trả 404 mà không có thông báo nào chỉ ra quyền — vì vậy quyền được cấp
bằng kịch bản lúc khởi động, và kiểm tra thứ năm của tích hợp liên tục kiểm luôn quyền này. Ngoài ra,
Superset mặc định gửi `X-Frame-Options: SAMEORIGIN`; cổng khác cổng thì phải đặt CSP `frame-ancestors`.

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
