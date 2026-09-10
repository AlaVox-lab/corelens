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
| Cập nhật lần cuối | 2026-09-07 |
| Phiên bản hiện tại | `v0.1.0` |
| Giai đoạn | Giai đoạn 1 — Khảo sát và thiết kế (**xong phần khảo sát**) |
| Mốc công việc đang chạy | Tuần 5 — Chốt kiến trúc và dựng hạ tầng, hạn 13/09 |
| Trạng thái kho mã | Riêng tư, sẽ chuyển công khai trước khi nộp bài |
| Có mã nguồn ứng dụng chưa | **Chưa** — issue #38 là việc đầu tiên tạo ra mã thật |
| Issue đang mở | **12** (#37–#48), trong đó 4 thuộc mốc Tuần 5 |
| Quyết định kiến trúc đã chốt | **4** — Keycloak `H` · SeaweedFS `core` · Superset `D` · tự viết engine `P` |
| Còn chờ khảo sát | 3 — quản trị tri thức `H`, véc-tơ và LLM `I`, khai phá quy trình `I` |
| Số ngày còn lại tới chấm kho mã | **91 ngày** (07/12/2026) |
| Số ngày còn lại tới khi công bố đề thi | khoảng **55 ngày** (tháng 11/2026) |

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
      viên, tài liệu `docs/workflow-engine-survey.md` đã lên `main`. **Chưa chốt** —
      xem mục Đang làm

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

## Đang làm

Milestone *Tuần 5 — Chốt kiến trúc và dựng hạ tầng*, hạn 13/09, có bốn issue:

| Issue | Ưu tiên | Việc |
|---|---|---|
| **#37** | **P0** | Vẽ lại sơ đồ luồng theo mô hình năm vai trò |
| **#38** | **P0** | Dựng hạ tầng phát triển bằng Docker Compose |
| #40 | P1 | Bảng dữ liệu cho engine máy trạng thái |
| #39 | P2 | Đo giới hạn kích thước tệp tải lên SeaweedFS |

Hai issue P0 nằm trên đường tới hạn nhưng **độc lập nhau**, làm song song được: #37 chặn
#40, còn #38 chặn #43 trở đi.

**Đang chờ giảng viên trả lời một câu** ảnh hưởng tới #37: vai trò *Người xét duyệt* đảm
nhiệm **hai cổng** (xác duyệt định tuyến luôn có, phê duyệt chi phí chỉ khi cần) hay chỉ
một cổng duy nhất. Nếu chưa kịp trả lời thì vẽ theo giả định hai cổng và ghi rõ là giả
định — sửa lại nhanh vì tất cả đều là dữ liệu.

---

## Việc tiếp theo

Toàn bộ việc kỹ thuật đã có issue, xếp theo đường tới hạn. Chi tiết từng giai đoạn xem
`ROADMAP.md`.

### Đường tới hạn — luồng nghiệp vụ chạy hoàn chỉnh

Theo chiến lược giảng viên chốt: đi sâu một luồng trước, rồi mới mở rộng.

```
#37 ──► #40 ──► #41 ──► #43 ──► #44 ──► #45
        ▲
#38 ────┘   (song song, nhưng #43 trở đi cần #38 xong)
```

| Issue | Ưu tiên | Việc | Chặn bởi |
|---|---|---|---|
| **#37** | P0 | Vẽ lại sơ đồ luồng theo mô hình năm vai trò | — |
| **#38** | P0 | Dựng hạ tầng Docker Compose · **PoF mục 4, 10 điểm** | — |
| #40 | P1 | Bảng dữ liệu cho engine máy trạng thái | #37 |
| #41 | P1 | Điểm chuyển trạng thái duy nhất và sinh nhật ký sự kiện | #40 |
| #43 | P1 | Tích hợp Keycloak vào dịch vụ ứng dụng và cổng | #38 |
| #44 | P1 | Cổng gửi yêu cầu và tra cứu trạng thái | #41, #43 |
| #45 | P2 | Buồng lái vận hành | #44 |
| #42 | P2 | Theo dõi SLA và tự leo thang | #41 |

### Không chặn ai, làm khi có khoảng trống

| Issue | Ưu tiên | Việc |
|---|---|---|
| #39 | P2 | Đo giới hạn kích thước tệp tải lên SeaweedFS — giảng viên yêu cầu |
| #46 | P2 | Khảo sát hệ thống quản trị tri thức cho `H` |
| #47 | P3 | Khảo sát cơ sở dữ liệu véc-tơ và khung LLM cho `I` |
| #48 | P3 | Khảo sát thư viện khai phá quy trình cho `I` |

### Việc vận hành, không cần issue

1. **Cắt bản phát hành `v0.2.0`** — Giai đoạn 1 đã trọn phần khảo sát: bốn tài liệu khảo
   sát, bốn bản ghi quyết định. Cần cài lại `git-cliff`; số commit bị bỏ qua phải đúng **13**
2. Chuyển bộ sinh dữ liệu ảo thành mã sản phẩm trong `infra/seed/`
3. Thiết kế giao diện cho #44 và #45 trước khi viết mã. Bảng điều khiển phân tích **không
   cần thiết kế** vì Superset tự mang giao diện
4. Thêm `CODE_OF_CONDUCT.md` — chuẩn cộng đồng nguồn mở
5. Thêm hai thành viên (quyền Write) và giảng viên (quyền Read hoặc Triage) vào kho mã;
   điền bảng Đội ngũ trong `README.md`. Khi đó chia lại người phụ trách: nhóm `H`
   (#43, #44, #45) hợp với người làm giao diện, nhóm `I` (#46, #47, #48) hợp với người
   làm dữ liệu

### Chờ điều kiện

6. Tích hợp liên tục — cần có cấu trúc thư mục mã nguồn trước
7. Chuyển kho mã sang công khai — làm trước khi nộp bài. Khi đó quy tắc bảo vệ nhánh mới
   có hiệu lực, và **bật lại được `delete_branch_on_merge`** một cách an toàn
8. Giai đoạn đóng gói: hướng dẫn cài đặt trong `README.md`, đo hiệu năng, công bố **cấu
   hình máy tối thiểu** — giảng viên nhắc trước để nhóm không quên

---

## Đang vướng

| Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| Quy tắc bảo vệ nhánh chưa có hiệu lực | Quy trình phụ thuộc kỷ luật cá nhân thay vì ràng buộc kỹ thuật | Chuyển kho mã sang công khai. Trong lúc chờ, tuân thủ tự giác |
| Chưa chốt công cụ quản trị cơ sở dữ liệu | Chưa ảnh hưởng, chỉ là công cụ hỗ trợ | Đã trình hai phương án, chờ ý kiến giảng viên |
| **Chờ giảng viên xác nhận vai trò Người xét duyệt** | Ảnh hưởng số trạng thái trong #37, và #40 phụ thuộc #37 | Đã gửi câu hỏi. Nếu chưa kịp trả lời thì vẽ theo giả định hai cổng và ghi rõ là giả định |
| Ngân sách bộ nhớ tăng dần theo từng nền tảng | Bảng chấm đòi dựng được trên máy sạch ngày chấm | Đang ở ~1,29 GB. Không gian `P` tự viết nên không cộng thêm. Đo lại sau mỗi quyết định mới |
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

---

## Ghi chú kỹ thuật đáng nhớ

Những phát hiện trong quá trình làm, ghi lại để không phải điều tra lại.

**Cảnh báo commit bị bỏ qua khi sinh nhật ký thay đổi**

git-cliff sẽ báo `N commit(s) were skipped due to parse error(s)`. Con số `N` phải
bằng **số merge commit cộng một** (cộng thêm một cho `Initial commit`).

Nếu `N` lớn hơn, nghĩa là có commit viết sai chuẩn và bị loại khỏi nhật ký. Kiểm tra
bằng `git-cliff --unreleased -vv` rồi đối chiếu với `git log --oneline`.

Nguyên nhân các commit này không được luật `skip` trong `cliff.toml` xử lý: tùy chọn
`filter_unconventional` loại chúng ở giai đoạn phân tích, trước khi tới bước phân
nhóm. Cảnh báo vô hại.

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
  giờ. Cấu hình sản phẩm bắt buộc thêm `-telemetry=false`
- **Ảnh `apache/superset` không kèm trình điều khiển PostgreSQL.** Phải cài
  `psycopg2-binary` vào `/app/.venv`, và môi trường đó **không có `pip`** — dùng `uv`.
  Bản sản phẩm cần ảnh chứa dẫn xuất
- **Metabase chạy JVM không đặt `-Xmx`** nên lấy dần bộ nhớ theo mức sẵn có: trong một
  phiên đo tăng từ 1,56 lên 1,98 GiB

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

**Biến thể thứ ba của lỗi mã hóa tiếng Việt trên Windows**

Cùng một gốc vấn đề nhưng lộ ra ở ba chỗ khác nhau, lần nào cũng mất thời gian truy:

| Chỗ hỏng | Ví dụ đã gặp |
|---|---|
| Tiếng Việt qua **tham số** dòng lệnh | `git commit -m "..."` làm hỏng dấu |
| Tiếng Việt ở **đầu ra** stdout | `python -c "print(...)"` báo `UnicodeEncodeError` |
| Tiếng Việt ở **đầu ra lệnh ngoài đọc ngược vào PowerShell** | Kịch bản tạo issue tra cứu milestone theo tiêu đề, `gh api ... \| Out-String` trả về chuỗi hỏng dấu nên tra không khớp, milestone bị bỏ qua âm thầm |

**Nguyên tắc chung**: đừng để tiếng Việt đi qua ranh giới tiến trình. Ghi vào tệp UTF-8
rồi để công cụ đọc tệp — `git commit -F`, `gh api --input`, `--body-file`. Khi buộc phải
đọc ngược đầu ra lệnh ngoài, đặt trước:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

Trong cả ba lần, tham chiếu tới đối tượng bằng **số** thay vì tên tiếng Việt luôn an toàn
hơn — ví dụ gán milestone bằng `-F milestone=4` thay vì bằng tiêu đề.

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
