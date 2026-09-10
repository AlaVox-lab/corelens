# CLAUDE.md

Tệp này cung cấp bối cảnh dự án cho Claude Code. Đọc kỹ trước khi thực hiện
bất kỳ thao tác nào trong kho mã này.

---

## QUY TẮC TUYỆT ĐỐI — ĐỌC TRƯỚC TIÊN

### Không bao giờ tự thực hiện thao tác Git

Claude Code **KHÔNG ĐƯỢC** chạy bất kỳ lệnh nào sau đây, trong mọi hoàn cảnh,
kể cả khi người dùng có vẻ đang yêu cầu gián tiếp:

- `git commit` (mọi biến thể, kể cả `--amend`, `-m`, `--no-verify`)
- `git push` (mọi biến thể)
- `git merge`, `git rebase`, `git cherry-pick`
- `git tag`
- `git reset --hard`, `git checkout` sang nhánh khác, `git switch`
- `git branch` (tạo hoặc xóa nhánh)
- `gh pr create`, `gh pr merge`, `gh issue create`, `gh release create`
- Bất kỳ lệnh nào ghi vào lịch sử Git hoặc lên máy chủ từ xa

**Lý do:** toàn bộ lịch sử commit của kho mã này là căn cứ chấm điểm trong một
cuộc thi. Mọi commit phải do thành viên trong nhóm tự thực hiện thủ công, với
danh tính thật của họ. Commit mang dấu vết công cụ tự động là không chấp nhận được.

### Được phép

- `git status`, `git diff`, `git log`, `git show`, `git branch --list`
- Đọc, tạo, sửa tệp trong thư mục làm việc
- Chạy lệnh build, test, lint, chạy thử ứng dụng

### Khi hoàn thành một công việc

Thay vì commit, hãy làm như sau:

1. Tóm tắt các tệp đã thay đổi
2. **Soạn sẵn commit message đúng chuẩn** (xem mục Quy ước commit) và in ra
   trong khối mã để người dùng sao chép
3. Dừng lại, để người dùng tự chạy lệnh

Ví dụ cách kết thúc một công việc:

> Đã sửa xong 3 tệp: `backend/app/workflow/state_machine.py`,
> `backend/app/workflow/rules.py`, `backend/tests/test_state_machine.py`.
>
> Commit message đề xuất:
>
> ```
> feat(p-workflow): thêm cơ chế leo thang khi quá hạn SLA
>
> Khi một yêu cầu vượt ngưỡng thời gian cấu hình sẵn, hệ thống tự động
> chuyển người phụ trách lên cấp quản lý trực tiếp và ghi một sự kiện
> vào nhật ký để phục vụ phân tích quy trình về sau.
>
> Closes #34
> ```

### Lưu ý về commit message tiếng Việt

Commit message viết **tiếng Việt có dấu**. Trên Windows, PowerShell làm hỏng ký tự
có dấu khi truyền qua cờ `-m`, nên người dùng đã cấu hình dùng trình soạn thảo:

```powershell
git config --global core.editor "code --wait"
```

Vì vậy khi soạn commit message, hướng dẫn người dùng chạy `git commit` **không kèm
cờ `-m`**, rồi dán nội dung vào cửa sổ Visual Studio Code mở ra.

---

## 0. THỨ TỰ ĐỌC BẮT BUỘC

Trước khi làm bất cứ việc gì, đọc theo đúng thứ tự này:

| Thứ tự | Tệp | Biết được gì |
|---|---|---|
| 1 | `docs/PROJECT_STATE.md` | Dự án đang ở đâu, vừa làm gì, đang vướng gì, việc tiếp theo |
| 2 | `docs/ARCHITECTURE.md` | Hệ thống được tổ chức thế nào, các khuôn mẫu đang dùng |
| 3 | `docs/ROADMAP.md` | Giai đoạn hiện tại và việc sắp tới |
| 4 | `docs/adr/` | Vì sao chọn công nghệ đó — tránh đề xuất lại thứ đã bác bỏ |
| 5 | `docs/dependencies.md` | Phụ thuộc hiện có và giấy phép của chúng |
| 6 | `CONTRIBUTING.md` | Quy ước chi tiết về nhánh, commit, mã nguồn |

Nếu một trong các tệp trên chưa tồn tại, báo cho người dùng biết thay vì đoán.

---

## 1. Bối cảnh dự án

### 1.1. Cuộc thi

Dự án dự thi **Phần mềm nguồn mở (PMNM) — Olympic Tin học Sinh viên Việt Nam 2026**,
do Hội Tin học Việt Nam tổ chức, CLB VFOSSA thường trực.

- Chủ đề: **Xây dựng Hệ điều hành Doanh nghiệp số (DX-OS)** theo kiến trúc Open-Core
- Đội tối đa 3 sinh viên, có giảng viên hướng dẫn
- Đề thi chính thức công bố **tháng 11/2026**, chấm kho mã **7–9/12**,
  chung kết **10/12**

### 1.2. Hệ quả quan trọng của lịch trình

Đề thi chỉ ra trước chung kết một tháng. Mọi thứ xây dựng trong giai đoạn hiện tại
là **bộ khung tái sử dụng**, không phải sản phẩm cuối. Nguyên tắc kỹ thuật bắt buộc:

> Trạng thái, vai trò, ngưỡng SLA, danh mục chỉ số — tất cả phải nằm trong
> **cấu hình hoặc dữ liệu**, tuyệt đối không mã cứng trong mã nguồn.

Khi viết code, luôn ưu tiên phương án cho phép thay đổi nghiệp vụ bằng cách sửa
dữ liệu khởi tạo thay vì sửa mã.

**Kiểm tra nhanh:** nếu một chuỗi như `"Đang xử lý"` xuất hiện trong câu lệnh `if`
của mã nguồn, đó là vi phạm. Trạng thái phải tra từ bảng.

### 1.3. Trạng thái hiện tại của kho mã

Phiên bản `v0.1.0` — đang khép Giai đoạn 1: Khảo sát và thiết kế.

Kho mã **vẫn chưa có mã nguồn ứng dụng**, mới có bộ quy chuẩn, tài liệu bối cảnh và
bốn bản ghi quyết định kiến trúc. Nếu người dùng yêu cầu sửa một tệp mã nguồn nào đó,
kiểm tra sự tồn tại trước thay vì giả định.

**Bốn quyết định Open-Core đã chốt** — đọc `docs/adr/` trước khi đề xuất lại bất cứ
thứ gì thuộc bốn mảng này:

| Không gian | Quyết định | Bản ghi |
|---|---|---|
| `H` | Keycloak `26.7.3` làm nền tảng định danh | ADR-0001 |
| `core` | SeaweedFS `4.45` làm kho lưu trữ tệp đính kèm | ADR-0002 |
| `D` | Apache Superset `6.1.0` làm nền tảng báo cáo | ADR-0003 |
| `P` | **Tự viết engine máy trạng thái**, không lắp ghép nền tảng nào | ADR-0004 |

Xem `docs/PROJECT_STATE.md` để biết tiến độ cập nhật nhất.

---

## 2. Bảng điểm — căn cứ cho mọi quyết định kỹ thuật

Thang 100 điểm, chia hai phần bằng nhau.

### 2.1. Phần I — 50 điểm PoF (chấm trên kho mã, trước chung kết)

| Hạng mục | Điểm | Các lỗi bị trừ |
|---|---|---|
| Quản lý mã nguồn công khai | 5 | Không có web viewer (−3); không truy cập mở (−3); không thực sự sử dụng (−5) |
| Giấy phép OSI-approved | 10 | Không ghi giấy phép trong **từng tệp mã** (−5); giấy phép không tương thích (−5); không có thông báo mục đích (−5); không có bản sao toàn văn (−5) |
| Có bản phát hành | 5 | Không có release (−5); không theo phiên bản (−3); dùng `.zip`/`.rar` (−3) |
| Build từ mã nguồn | 10 | Không có hướng dẫn build (−5); phải sửa tay tệp header (−5); không cấu hình được trước khi dịch (−5); dịch bằng công cụ nguồn đóng (−5); không chạy được ngoài thư mục mã nguồn (−5) |
| Thư viện và gói đính kèm | 10 | Không dùng thư viện sẵn có (−5); phát hành kèm gói của dự án khác (−5); **sửa mã nguồn thư viện bên thứ ba** (−5) |
| Tài liệu và giao tiếp | 10 | Không có bug tracker (−5); không có changelog (−5); không có README và hướng dẫn (−5) |

### 2.2. Phần II — 50 điểm sản phẩm (chấm tại chung kết)

Tính nguyên gốc của kiến trúc lắp ghép · Mức độ hoàn thiện · Thân thiện người dùng ·
Phát triển bền vững (chấm qua **tài liệu kỹ thuật**) · Phong cách trình diễn.

### 2.3. Hệ quả trực tiếp khi viết code

- **Mọi tệp mã nguồn mới bắt buộc có header giấy phép** (xem mục 5.1)
- **Không bao giờ sửa mã nguồn thư viện bên thứ ba.** Nếu cần đổi hành vi,
  dùng cấu hình, plugin, hoặc lớp bọc
- **Không sao chép mã thư viện vào kho.** Khai báo qua trình quản lý gói kèm tệp khóa
- **Tệp khóa phiên bản (`package-lock.json`, `requirements.txt` ghim bằng `==`,
  `uv.lock`, `poetry.lock`) BẮT BUỘC commit lên kho mã, tuyệt đối không đưa vào
  `.gitignore`.** Không có tệp khóa thì mỗi người và ban giám khảo sẽ nhận bộ phiên bản
  khác nhau, làm hỏng khả năng dựng lại từ mã nguồn. Nếu người dùng yêu cầu bỏ tệp khóa
  khỏi kho mã, hãy nêu rõ rủi ro này trước khi thực hiện
- **Toàn bộ tài liệu trong `docs/` phải được commit và công khai**, không đưa vào
  `.gitignore`. Tài liệu chiếm tới 20 trên 100 điểm — tài liệu bị giấu là tài liệu
  không tồn tại với ban giám khảo
- **Luôn giữ hệ thống dựng được bằng một lệnh** `docker compose up` trên máy sạch
- Trước khi thêm bất kỳ phụ thuộc mới nào: kiểm tra giấy phép có thuộc danh sách
  OSI-approved và tương thích MIT không, ghi vào `docs/dependencies.md`

---

## 3. Kiến trúc H-P-D-I

Toàn bộ hệ thống tổ chức theo bốn không gian. Ký hiệu này dùng nhất quán trong
nhãn issue, phạm vi commit và cấu trúc thư mục.

| Ký hiệu | Không gian | Phạm vi |
|---|---|---|
| `H` | Human — Nhân sự | SSO, phân quyền theo vai trò, cổng tự phục vụ, kho tri thức |
| `P` | Process — Quy trình | Máy trạng thái, luồng phê duyệt, ràng buộc Poka-yoke, SLA, sinh event log |
| `D` | Data — Dữ liệu | Nguồn sự thật duy nhất, nhật ký sự kiện, dashboard BI, xuất CSV/JSON |
| `I` | Intelligence — AI | Phân loại tự động, RAG, khai phá quy trình (process mining) |

Chi tiết đầy đủ về từng không gian và các khuôn mẫu thiết kế: xem
`docs/ARCHITECTURE.md`.

### 3.1. Tính tuyến tính bắt buộc

Không thể xây `I` khi `P` và `D` chưa chuẩn. Tích hợp AI vào quy trình chưa chuẩn hóa
sẽ sinh ảo giác dữ liệu. Thứ tự triển khai: **H → P → D → I**.

Nếu người dùng yêu cầu làm tầng AI trước khi `P` và `D` ổn định, hãy nêu vấn đề này
trước khi thực hiện.

### 3.2. Yêu cầu Open-Core

Ban tổ chức yêu cầu **lắp ghép các nền tảng nguồn mở có sẵn**, không phải viết lại
mọi thứ từ đầu. Tiêu chí chấm ghi rõ "tính nguyên gốc của **kiến trúc lắp ghép**".

Phân định:

- **Lắp ghép:** SSO, kho tri thức wiki, BI dashboard, vector store, LLM framework,
  thư viện process mining
- **Tự viết:** cổng yêu cầu và UX, engine máy trạng thái cấu hình được, lớp Poka-yoke,
  bộ sinh event log, và **lớp điều phối kết nối bốn không gian**

Khi đề xuất giải pháp, ưu tiên tích hợp nền tảng có sẵn hơn là tự cài đặt lại,
trừ khi thành phần đó thuộc nhóm "tự viết" ở trên.

---

## 4. Bài toán nghiệp vụ

**Cổng vận hành yêu cầu nội bộ** — tiếp nhận và điều phối tập trung mọi loại yêu cầu
trong doanh nghiệp: sự cố thiết bị, cấp quyền phần mềm, giấy xác nhận nhân sự,
đề xuất mua vật tư.

### 4.1. Điểm sáng tạo: vòng phản hồi tự soi quy trình

Mọi lần chuyển trạng thái ghi một bản ghi vào **event log** chuẩn hóa
(`case_id`, `activity`, `timestamp`, `actor`, `from_state`, `to_state`). Từ log này,
hệ thống tự khai phá lại quy trình thực tế đang chạy và đối chiếu với quy trình thiết
kế, chỉ ra điểm nghẽn và nhánh lệch chuẩn.

Đây là thành phần chịu lực của tầng `I` — gỡ nó ra thì sản phẩm tụt xuống mức
helpdesk thông thường. Khi viết code cho tầng `P`, **luôn nhớ phát sinh event log**
ở mọi điểm chuyển trạng thái.

**Lưu ý về múi giờ:** `timestamp` luôn lưu theo UTC. Lưu giờ cục bộ sẽ làm sai lệch
kết quả khai phá quy trình khi so sánh giữa các bản ghi.

### 4.2. Bốn vai trò

Người gửi yêu cầu · Điều phối viên · Người xử lý · Trưởng bộ phận

### 4.3. NGUYÊN TẮC BẮT BUỘC: AI chỉ gợi ý, con người quyết định

Tầng `I` **chỉ được ghi vào các trường mang tính gợi ý**, không bao giờ ghi trực tiếp
vào trường quyết định. Mọi kết quả từ AI đều phải đi qua một bước xác nhận của người
có thẩm quyền, dù chỉ là một cú nhấn chuột.

Cụ thể trong lược đồ dữ liệu, tách rõ hai nhóm trường:

| Trường gợi ý (AI ghi) | Trường quyết định (người ghi) |
|---|---|
| `suggested_category` | `category` |
| `suggested_assignee_id` | `assignee_id` |
| `suggested_priority` | `priority` |

Đồng thời ghi lại việc con người có ghi đè gợi ý của AI hay không, phục vụ đo lường
độ chính xác thực tế của mô hình và làm dữ liệu cho phân tích về sau.

**Ba lý do:**

1. Đúng nguyên lý "Human-in-the-loop" mà tài liệu Ban tổ chức nêu: nhân sự giữ vai trò
   giám sát và phê duyệt ngoại lệ
2. Nếu AI phân luồng sai, người dùng vẫn điều chỉnh được bằng tay. Không có đường
   điều chỉnh thủ công là lỗi thiết kế nghiêm trọng
3. Bảo hiểm cho buổi trình diễn: nếu mô hình lỗi hoặc mạng chậm vào ngày chấm,
   hệ thống vẫn vận hành được ở chế độ thủ công

**Thứ tự xây dựng bắt buộc:** hoàn thiện luồng thủ công chạy đúng trước, sau đó mới
gắn AI vào như một lớp hỗ trợ. Không xây AI song song với luồng nghiệp vụ.

---

## 5. Bộ công nghệ

| Tầng | Công nghệ | Giấy phép |
|---|---|---|
| Giao diện | Next.js (React) | MIT |
| Dịch vụ ứng dụng | FastAPI (Python) | MIT |
| Cơ sở dữ liệu | PostgreSQL | PostgreSQL License |
| Đóng gói | Docker + Docker Compose | Apache-2.0 |
| Định danh tập trung | Keycloak `26.7.3` | Apache-2.0 |
| Lưu trữ đối tượng | SeaweedFS `4.45` | Apache-2.0 |
| Kinh doanh thông minh | Apache Superset `6.1.0` | Apache-2.0 |

Ba nền tảng Open-Core cuối bảng đều **chạy như dịch vụ độc lập**, giao tiếp qua giao
thức chuẩn (OIDC, S3 API, guest token). Không nhúng thư viện, không sửa mã nền tảng.

**Không gian `P` không dùng nền tảng ngoài** — engine máy trạng thái do nhóm tự viết,
với trạng thái và quy tắc chuyển lưu trong bảng dữ liệu. Xem ADR-0004.

Ba mảng còn **chờ khảo sát**, chưa có issue: hệ thống quản trị tri thức cho `H`, cơ sở
dữ liệu véc-tơ và khung LLM cho `I`, thư viện khai phá quy trình cho `I`.

Kết quả mọi khảo sát ghi trong `docs/adr/`. **Đọc thư mục này trước khi đề xuất công
nghệ mới** — bốn quyết định đã chốt, đề xuất lại là lãng phí thời gian của cả nhóm.

### 5.1. Header giấy phép — bắt buộc trên mọi tệp mã mới

Python:

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
```

TypeScript / JavaScript:

```typescript
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
```

Thiếu header này bị trừ 5 điểm. Khi tạo tệp mã mới, luôn thêm header ngay.

### 5.2. Cảnh báo về giấy phép

Nhiều nền tảng tự nhận nguồn mở nhưng dùng giấy phép **không** thuộc danh sách OSI:
BSL, SSPL, Elastic License, Commons Clause, fair-code. Dùng chúng sẽ khiến dự án
không được chấm điểm.

Với AGPL (hợp lệ nhưng copyleft mạnh): chỉ dùng dưới dạng dịch vụ độc lập giao tiếp
qua HTTP/API, không nhúng thư viện vào mã nguồn.

Khi đề xuất bất kỳ thư viện hay nền tảng nào, **luôn nêu giấy phép của nó**.

---

## 6. Quy ước Git

### 6.1. Mô hình nhánh

```
main    — nhánh mặc định, luôn build được, nơi đặt tag. Chỉ nhận từ dev hoặc hotfix
dev     — nhánh tích hợp, nơi các nhánh công việc hội tụ
<loại>/<số-issue>-<mô-tả>  — nhánh công việc, tạo từ dev
hotfix/<mô-tả>             — tạo từ main khi cần sửa gấp
```

Ví dụ tên nhánh: `feat/12-request-submission-form`, `fix/27-sla-timer-timezone`

### 6.2. Quy ước commit — Conventional Commits

```
<loại>(<phạm vi>): <mô tả ngắn, thì hiện tại, dưới 72 ký tự>

<thân commit: giải thích TẠI SAO, không phải CÁI GÌ>

<footer: Closes #N hoặc Refs #N>
```

Loại: `feat` `fix` `docs` `refactor` `perf` `test` `build` `ci` `chore` `revert`

Phạm vi theo không gian kiến trúc:

| Phạm vi | Ý nghĩa |
|---|---|
| `h-auth` | Định danh, đăng nhập, phân quyền |
| `h-portal` | Cổng người dùng, giao diện tự phục vụ |
| `p-workflow` | Máy trạng thái, luồng xử lý |
| `p-rules` | Ràng buộc nghiệp vụ, Poka-yoke, SLA |
| `d-schema` | Lược đồ CSDL, migration |
| `d-analytics` | Event log, dashboard, xuất dữ liệu |
| `i-classify` | Phân loại và định tuyến tự động |
| `i-rag` | Truy xuất tri thức, vector |
| `i-mining` | Khai phá quy trình |
| `infra` | Docker, biến môi trường, triển khai |
| `ci` | Tự động hóa |
| `docs` | Tài liệu |

Từ khóa liên kết issue: `Refs #N` cho commit trung gian, `Closes #N` cho commit cuối.

**CHANGELOG.md được sinh tự động từ lịch sử commit bằng git-cliff.** Commit sai chuẩn
sẽ bị bỏ sót khỏi changelog, dẫn tới mất điểm. Vì vậy commit message phải luôn đúng chuẩn.

### 6.3. Nhãn issue

Mỗi issue có đúng một nhãn từ mỗi nhóm bắt buộc:

- `type/` — `feat` `fix` `docs` `research` `refactor` `test` `chore` (bắt buộc)
- `space/` — `H` `P` `D` `I` `core` (bắt buộc)
- `priority/` — `P0` `P1` `P2` `P3` (bắt buộc)
- `status/` — `blocked` `needs-discussion` `wontfix` (tùy chọn)
- `scoring/` — `pof` `final` (tùy chọn)

### 6.4. Ghi chú kỹ thuật đã biết

**Issue chỉ đóng khi commit tới nhánh mặc định.** GitHub chỉ tự đóng issue khi commit
chứa `Closes #N` đi vào `main`. Do quy trình đi qua `dev`, issue sẽ mở cho tới lần
hợp nhất `dev → main`. Đây là hành vi bình thường.

**Xóa nhánh sau khi squash merge** phải dùng `git branch -D` viết hoa, vì squash tạo
commit với mã băm mới nên Git không nhận ra nhánh đã được hòa nhập.

**Cảnh báo commit bị bỏ qua khi sinh changelog:** số commit bị skip phải bằng
số merge commit cộng một. Lệch nghĩa là có commit viết sai chuẩn.

---

## 7. Quy tắc làm việc với Claude Code

### 7.1. Trước khi bắt đầu

- Đọc theo thứ tự ở mục 0
- Chạy `git status` và `git branch --list` để biết đang ở đâu
- Nếu yêu cầu mâu thuẫn với một khuôn mẫu đã ghi trong `docs/ARCHITECTURE.md`,
  **dừng lại và hỏi** thay vì tự quyết định

### 7.2. Trong khi làm

- Ưu tiên sửa tệp có sẵn hơn tạo tệp mới
- Không tạo tệp tài liệu mới trừ khi được yêu cầu rõ ràng
- Mọi tệp mã mới phải có header giấy phép
- Giữ cấu hình nghiệp vụ trong dữ liệu, không mã cứng
- Khi thêm phụ thuộc: nêu giấy phép, cập nhật `docs/dependencies.md`
- Không tự chạy kiểm thử, máy chủ phát triển, hoặc lệnh triển khai trừ khi được
  yêu cầu rõ ràng

### 7.3. Khi kết thúc

- Tóm tắt tệp đã thay đổi
- Soạn sẵn commit message đúng chuẩn trong khối mã
- Nếu thay đổi tạo ra hoặc sửa đổi một khuôn mẫu thiết kế, **cập nhật
  `docs/ARCHITECTURE.md` ngay trong cùng công việc**
- **Dừng lại. Không chạy git.** Người dùng sẽ tự commit và push.

### 7.4. Khi phát hiện vấn đề

Nếu thấy điều gì có nguy cơ mất điểm — thiếu header giấy phép, phụ thuộc có giấy phép
đáng ngờ, thay đổi làm hỏng khả năng build, mã cứng giá trị nghiệp vụ, tài liệu bị
đưa vào `.gitignore` — **nêu ngay** thay vì im lặng thực hiện.
