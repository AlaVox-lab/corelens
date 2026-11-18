# Hướng dẫn đóng góp

Cảm ơn bạn đã quan tâm tới dự án. Tài liệu này mô tả quy trình làm việc,
quy ước mã nguồn và các tiêu chuẩn mà mọi đóng góp cần tuân thủ.

Dự án theo mô hình nhiều giấy phép (bảng ở [`LICENSES.md`](LICENSES.md)): thư mục
`services/khai-pha/` theo AGPL-3.0-or-later, phần còn lại của kho theo MIT. Khi gửi
đóng góp, bạn đồng ý rằng phần đóng góp của mình được phát hành theo giấy phép của
thư mục chứa nó.

---

## 1. Kiến trúc và thuật ngữ

Dự án được tổ chức theo khung kiến trúc **H-P-D-I**:

| Ký hiệu | Không gian | Phạm vi |
|---------|-----------|---------|
| `H` | Human — Nhân sự | Định danh tập trung, phân quyền, cổng tự phục vụ, kho tri thức |
| `P` | Process — Quy trình | Máy trạng thái, luồng phê duyệt, ràng buộc Poka-yoke, SLA |
| `D` | Data — Dữ liệu | Nguồn dữ liệu duy nhất, nhật ký sự kiện, bảng điều khiển, xuất dữ liệu mở |
| `I` | Intelligence — Trí tuệ nhân tạo | Phân loại tự động, truy xuất tri thức, khai phá quy trình |

Ký hiệu này được dùng nhất quán trong nhãn issue, phạm vi commit và cấu trúc thư mục.

---

## 2. Quy trình làm việc

### 2.1. Sơ đồ nhánh

```
main      ──●────────────────●──────────────●──   (ổn định, luôn build được, nơi đặt tag)
             \              /              /
dev       ────●──●──●──●───●──●──●──●─────●───    (tích hợp, kiểm thử)
               \  /     \  /     \  /
feature         ●●       ●●       ●●              (nhánh công việc, tạo từ dev)
```

- `main` — nhánh mặc định. Luôn ở trạng thái build được và trình diễn được.
  Chỉ nhận thay đổi từ `dev` hoặc `hotfix/*`. Mọi tag phát hành đặt trên nhánh này.
- `dev` — nhánh tích hợp. Nơi các nhánh công việc hội tụ và được kiểm thử.
- Nhánh công việc — tạo từ `dev`, mỗi nhánh giải quyết đúng một issue.
- `hotfix/*` — tạo từ `main` khi cần sửa gấp. Sau khi merge vào `main`
  phải merge ngược `main` về `dev` để hai nhánh không lệch.

### 2.2. Các bước

1. **Mọi công việc đều bắt đầu từ một Issue.** Không có issue thì không mở PR.
2. Issue được gán nhãn đầy đủ và gán người phụ trách trước khi bắt đầu.
3. Tạo nhánh từ `dev` theo quy ước đặt tên ở mục 3.
   Có thể dùng nút *Create a branch* trong trang Issue để nhánh tự liên kết với issue;
   nhớ chọn `dev` làm nguồn trong hộp thoại.
4. Commit theo chuẩn Conventional Commits (mục 4).
5. Mở Pull Request vào `dev`, điền đầy đủ mẫu PR, liên kết tới issue.
6. Cần ít nhất một thành viên phê duyệt và toàn bộ kiểm tra tự động phải xanh.
7. Merge vào `dev` bằng **Squash and merge**.
8. Theo nhịp phát hành, merge `dev` vào `main` bằng **Merge commit** (không squash).

### 2.3. Chiến lược merge

| Chặng | Cách merge | Lý do |
|-------|-----------|-------|
| nhánh công việc → `dev` | Squash and merge | Gộp các commit trung gian thành một commit sạch. Sửa lại tiêu đề cho đúng chuẩn Conventional trước khi xác nhận. |
| `dev` → `main` | Merge commit | Giữ nguyên từng commit để công cụ sinh nhật ký thay đổi phân loại được. |

### 2.4. Định nghĩa hoàn thành

Một issue chỉ được coi là hoàn thành khi thỏa mãn tất cả các điều kiện sau:

- [ ] Toàn bộ mục trong phần *Việc cần làm* của issue đã được tick
- [ ] Mã nguồn mới có header giấy phép (mục 5)
- [ ] Tài liệu liên quan trong `docs/` đã được cập nhật
- [ ] Kiểm tra tự động chạy xanh
- [ ] Có ít nhất một phê duyệt từ thành viên khác
- [ ] `docker compose up` vẫn chạy được trên máy sạch

### 2.5. Quyền cập nhật tài liệu trạng thái

`docs/PROJECT_STATE.md` do người điều phối kho mã cập nhật theo nhịp tuần.
Thành viên không sửa tệp này trong các pull request công việc.

Lý do: nếu nhiều người cùng sửa một tệp tổng hợp, mọi pull request đều xung đột
ở cùng vị trí, và nội dung trở thành danh sách rời rạc thay vì bản tóm tắt mạch
lạc. Ngoài ra, chỉ người điều phối mới có bức tranh toàn cảnh về tiến độ của cả
nhóm, các vướng mắc đang tồn tại và thứ tự ưu tiên của tuần tiếp theo.

Thông tin về việc ai làm gì không mất đi — nó đã nằm trong issue, pull request
và lịch sử commit. Tệp trạng thái chỉ là bản tóm tắt để đọc nhanh.

Quy trình cập nhật của người điều phối:

1. Chờ mọi công việc trong tuần đã hợp nhất vào nhánh tích hợp
2. Đồng bộ nhánh tích hợp về máy
3. Tạo nhánh riêng, ví dụ `docs/state-tuan-N`
4. Lọc danh sách issue đã đóng theo mốc công việc để làm nguồn dữ liệu
5. Viết lại tệp trạng thái, không cộng dồn từng dòng
6. Mở pull request như quy trình thông thường

### 2.6. Tích hợp liên tục

Mỗi pull request vào `dev` hay `main` chạy quy trình
`.github/workflows/ci.yml`. Sáu kiểm tra hiện riêng trên trang pull request:

| Kiểm tra | Làm gì | Chạy tay ở máy |
|---|---|---|
| Header giấy phép | Mọi tệp mã kho đang theo dõi có dòng bản quyền và dòng SPDX đúng giấy phép theo thư mục; trang phả hệ dữ liệu khớp định nghĩa view; phụ thuộc trực tiếp có dòng trong `docs/dependencies.md` | `python scripts/kiem_header.py`, `python scripts/pha_he.py --kiem` và `python scripts/doi_soat_phu_thuoc.py` |
| Linter — ruff và eslint | `ruff check .` cho mọi mã Python (cấu hình `ruff.toml` ở gốc); `npm run lint` trong `frontend/` (cấu hình `frontend/eslint.config.mjs`). Lỗi làm đỏ, cảnh báo thì không | Xem đoạn *Linter* ngay dưới |
| Giao diện — dựng và kiểm kiểu | `npm ci`, `npm run build`, `npm run typecheck` trong `frontend/` | Ba lệnh đó |
| Trang tài liệu — dựng | `npm ci`, `npm run build` trong `docs-site/` (cần Node.js 22.12 trở lên) | Hai lệnh đó; xem trực tiếp bằng `npm run dev` |
| Cụm — dựng ảnh và kiểm thử dịch vụ | Dựng hai ảnh `backend`, `frontend` từ `.env.example`, bật PostgreSQL, Keycloak, SeaweedFS và cổng API, kiểm từ máy chủ rằng cổng `8000`, `5432` đã đóng và cổng API chặn lời gọi thiếu token, chạy toàn bộ `pytest` trong container (kể cả `tests/test_cong_api.py` đi qua cổng API) | `docker exec dxlab-backend python -m pytest -p no:cacheprovider -q` khi cụm đang chạy |
| Bảng điều khiển — dựng và tự nạp | Dựng và bật PostgreSQL, dịch vụ ứng dụng, Superset; dashboard *Vận hành yêu cầu* đủ năm biểu đồ đã tự nạp từ `infra/superset/bang-dieu-khien/`, tài khoản chỉ đọc đọc được mọi view mà dataset trỏ tới (#304) | `docker compose ... up -d --build --wait postgres backend superset` rồi mở `http://localhost:8088` |

**Linter** (#382) — chạy ở gốc kho trước khi push:

```bash
pip install ruff==0.17.3        # một lần; hoặc: pipx run --spec ruff==0.17.3 ruff check .
ruff check .                    # thêm --fix để ruff tự sửa phần sửa được an toàn
cd frontend && npm run lint     # sau npm ci
```

**Tùy chọn — tự kiểm trước mỗi commit** (#484): `.pre-commit-config.yaml` ở gốc chạy ruff (cùng bản với CI),
kiểm header giấy phép, trang phả hệ dữ liệu, chặn dấu xung đột hợp nhất và tệp trên 1 MB — lỗi hiện ngay trên
máy thay vì chờ CI. Cài một lần: `pip install pre-commit==4.7.0` rồi `pre-commit install`; chạy trên cả kho:
`pre-commit run --all-files`. Không cài thì không ảnh hưởng gì.

Bộ luật ruff chọn tường minh trong `ruff.toml` (lỗi cú pháp, import và biến thừa, mẫu dễ sinh lỗi của
bugbear); luật nào tắt đều ghi lý do ngay cạnh. Kho không chạy `ruff format` — không ép kiểu trình bày.
Phiên bản ruff ghim ở hai chỗ, `ruff.toml` (`required-version`) và `ci.yml`; nâng thì nâng cả hai.

**Kiểm thử giao diện qua đăng nhập thật** (#238) chạy tay trước khi mở pull request có sửa giao diện,
trên cụm thử: `npm ci`, `npm run cai-trinh-duyet` (lần đầu), `npm run kiem` trong `e2e/`. Trên tích hợp
liên tục, quy trình riêng `.github/workflows/e2e.yml` dựng trọn cụm mặc định từ `.env.example` trên máy
sạch rồi chạy **toàn bộ** kịch bản bằng Chromium — chỉ cho pull request vào `main` và khi bấm *Run
workflow* ở thẻ *Actions* (mất khoảng nửa giờ, nên không chạy cho mỗi pull request vào `dev`). Hỏng thì
tải tệp `bao-cao-e2e` ở trang lượt chạy: báo cáo HTML (`npx playwright show-report bao-cao`) và vết của
bài hỏng (kéo `trace.zip` vào `https://trace.playwright.dev`). Kịch bản đăng
nhập bốn vai qua Keycloak, kiểm các màn chính ở bốn cấu hình hiển thị và chụp ảnh — chi tiết ở trang tài
liệu, phần *Phát triển → Kiểm thử giao diện*. Kịch bản gửi một hồ sơ thật, nên không chạy trên hệ thống
đang dùng thật.

**Công cụ kiểm chứng** (#249) — dựng cụm thử cách ly, dò đăng nhập thật, tạo hồ sơ thử theo từng trạng
thái, chạy phép thử đột biến — nằm ở `scripts/kiem_chung/`, hướng dẫn ở trang tài liệu *Phát triển →
Công cụ kiểm chứng* (`docs-site/src/content/docs/phat-trien/kiem-chung.md`).

Trong quy trình, bài kiểm thử bị **bỏ qua** cũng tính là hỏng (biến `DXLAB_CAM_BO_QUA=1`): bộ
kiểm thử tự bỏ qua khi không gọi được PostgreSQL hay Keycloak, nên không có cờ này thì cụm
dựng hỏng vẫn ra xanh. Chạy tay ở máy thì không đặt biến, giữ cách cũ.

Kiểm tra đỏ thì mở **Details** cạnh kiểm tra đó. Job cụm in 200 dòng nhật ký cuối của từng
dịch vụ khi hỏng. Sửa trên cùng nhánh, push tiếp, quy trình tự chạy lại.

**Khi kho chuyển công khai**, quy tắc bảo vệ nhánh mới có hiệu lực. Bật thêm cho cả `main` và
`dev` (*Settings → Branches*):

- *Require status checks to pass before merging*, chọn đủ sáu kiểm tra ở bảng trên; riêng `main`
  chọn thêm *Kịch bản giao diện — cụm sạch, đăng nhập thật*
- *Require branches to be up to date before merging*
- Giữ nguyên các tùy chọn đã có: bắt buộc pull request, 1 phê duyệt, bỏ phê duyệt cũ khi có
  commit mới, giải quyết hết hội thoại, cấm force push, cấm xóa nhánh

Tới lúc đó, pull request lỡ đặt `base: main` (như #215) vẫn phải chờ các kiểm tra xanh mới
merge được.

---

## 3. Quy ước đặt tên nhánh

```
<loại>/<số-issue>-<mô-tả-ngắn-không-dấu>
```

Ví dụ:

```
feat/12-request-submission-form
fix/27-sla-timer-timezone
docs/3-readme-build-instructions
research/1-sso-platform-survey
chore/45-github-actions-ci
```

Quy tắc: chữ thường, phân tách bằng dấu gạch ngang, không dấu tiếng Việt,
tối đa khoảng năm từ trong phần mô tả.

---

## 4. Quy ước commit

Dự án dùng chuẩn [Conventional Commits](https://www.conventionalcommits.org/).
Nhật ký thay đổi và số phiên bản được sinh tự động từ lịch sử commit,
nên việc tuân thủ chuẩn này là bắt buộc.

### 4.1. Cấu trúc

```
<loại>(<phạm vi>): <mô tả ngắn>

<thân commit, tùy chọn>

<footer, tùy chọn>
```

- Dòng tiêu đề tối đa 64 ký tự, viết ở thì hiện tại, không kết thúc bằng dấu chấm. Khi squash,
  GitHub gắn thêm ` (#số PR)` vào cuối, nên dòng đầu commit trên `dev` vẫn dưới 72 ký tự
- Thân commit giải thích **tại sao** thay đổi, không phải **thay đổi cái gì**
- Footer chứa từ khóa liên kết issue hoặc thông báo phá vỡ tương thích

### 4.2. Các loại được dùng

| Loại | Dùng khi | Ảnh hưởng phiên bản |
|------|----------|---------------------|
| `feat` | Thêm tính năng mới | MINOR |
| `fix` | Sửa lỗi | PATCH |
| `docs` | Chỉ thay đổi tài liệu | Không |
| `refactor` | Sửa cấu trúc code, không đổi hành vi | Không |
| `perf` | Cải thiện hiệu năng | PATCH |
| `test` | Thêm hoặc sửa kiểm thử | Không |
| `build` | Thay đổi hệ thống build hoặc phụ thuộc | Không |
| `ci` | Thay đổi cấu hình tích hợp liên tục | Không |
| `chore` | Công việc phụ trợ khác | Không |
| `revert` | Hoàn tác một commit trước đó | Tùy |

Thay đổi phá vỡ tương thích: thêm `!` sau phạm vi, hoặc thêm dòng
`BREAKING CHANGE: <mô tả>` ở footer. Cả hai đều làm tăng MAJOR.

### 4.3. Phạm vi

Phạm vi phản ánh không gian kiến trúc hoặc thành phần bị ảnh hưởng:

| Phạm vi | Ý nghĩa |
|---------|---------|
| `h-auth` | Định danh, đăng nhập, phân quyền |
| `h-portal` | Cổng người dùng, giao diện tự phục vụ |
| `p-workflow` | Máy trạng thái, luồng xử lý |
| `p-rules` | Ràng buộc nghiệp vụ, Poka-yoke, SLA |
| `d-schema` | Lược đồ cơ sở dữ liệu, migration |
| `d-analytics` | Nhật ký sự kiện, bảng điều khiển, xuất dữ liệu |
| `i-classify` | Phân loại và định tuyến tự động |
| `i-rag` | Truy xuất tri thức, vector |
| `i-mining` | Khai phá quy trình |
| `infra` | Docker, biến môi trường, triển khai |
| `ci` | Quy trình tự động hóa |
| `docs` | Tài liệu |

Tích hợp liên tục kiểm tiêu đề pull request vào `dev` theo đúng bảng trên: loại hợp lệ, có phạm vi
thuộc bảng, tối đa 64 ký tự (`.github/workflows/tieu-de-pr.yml`), và kiểm mọi commit trong lịch sử
đều được git-cliff nhận vào changelog. Chạy trước ở máy:

```
python scripts/kiem_commit.py --tieu-de "feat(p-workflow): thêm …"
python scripts/kiem_commit.py --lich-su HEAD
```

### 4.4. Ví dụ

```
feat(p-workflow): thêm cơ chế leo thang khi quá hạn SLA

Khi một yêu cầu vượt ngưỡng thời gian cấu hình sẵn, hệ thống tự động
chuyển người phụ trách lên cấp quản lý trực tiếp và ghi một sự kiện
vào nhật ký để phục vụ phân tích quy trình về sau.

Closes #34
```

```
fix(d-schema): sửa múi giờ khi ghi mốc thời gian sự kiện

Mốc thời gian trước đây lưu theo giờ cục bộ khiến kết quả khai phá
quy trình sai lệch khi so sánh giữa các bản ghi. Chuyển toàn bộ sang UTC.

Closes #58
```

```
feat(h-auth)!: chuyển sang xác thực bằng OIDC

BREAKING CHANGE: cơ chế đăng nhập bằng phiên nội bộ không còn được hỗ trợ.
Cần cấu hình lại biến môi trường theo hướng dẫn trong docs/setup.md.
```

### 4.5. Từ khóa liên kết issue

| Từ khóa | Tác dụng |
|---------|----------|
| `Closes #N`, `Fixes #N`, `Resolves #N` | Đóng issue khi commit vào nhánh mặc định |
| `Refs #N` | Tạo liên kết mà không đóng issue |

Dùng `Refs` cho các commit trung gian, `Closes` cho commit hoặc PR cuối cùng.

Lưu ý: GitHub chỉ tự động đóng issue khi thay đổi được đưa vào nhánh mặc định
(`main`). Pull request merge vào `dev` sẽ tạo liên kết nhưng chưa đóng issue.

---

## 5. Quy ước mã nguồn

### 5.1. Header giấy phép

Mọi tệp mã nguồn mới phải bắt đầu bằng khối chú thích sau, dùng cú pháp
chú thích phù hợp với ngôn ngữ. Giấy phép theo **thư mục chứa tệp**:

| Thư mục | Khối chú thích |
|---|---|
| `services/khai-pha/` (cả `app/`, `tests/`, `Dockerfile`) | `SPDX-License-Identifier: AGPL-3.0-or-later` |
| Mọi nơi khác | `SPDX-License-Identifier: MIT` |

```
SPDX-License-Identifier: MIT
Copyright (c) 2026 AlaVox-lab
```

```
SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2026 AlaVox-lab
```

Yêu cầu này bắt nguồn từ tiêu chí chấm điểm của cuộc thi: mã nguồn không ghi
giấy phép trong từng tệp sẽ bị trừ điểm. `scripts/kiem_header.py` báo lỗi cả tệp
thiếu header lẫn tệp mang giấy phép của thư mục khác. Kịch bản xét mã nguồn và
cả tệp cấu hình có cú pháp chú thích (`.yml`, `.yaml`, `.toml`, `.ini`,
`.properties`, `.svg`, `Dockerfile`, `.env.example`); không xét JSON và Markdown.

### 5.2. Thư viện bên thứ ba

- Khai báo phụ thuộc qua trình quản lý gói, kèm tệp khóa phiên bản
- Không sao chép mã nguồn thư viện vào kho mã của dự án
- Không chỉnh sửa mã nguồn của thư viện bên thứ ba. Nếu cần thay đổi hành vi,
  dùng cơ chế cấu hình, plugin hoặc lớp bọc
- Trước khi thêm một phụ thuộc mới, kiểm tra giấy phép của nó có nằm trong
  danh sách được OSI công nhận và có tương thích với giấy phép của thư mục dùng nó
  (MIT, hoặc AGPL-3.0-or-later trong `services/khai-pha/`) hay không.
  Ghi kết quả kiểm tra vào `docs/dependencies.md`

### 5.3. Tệp khóa phiên bản

Các tệp khóa phiên bản (`package-lock.json` ở phía giao diện, tệp ghim phiên bản
ở phía dịch vụ) **bắt buộc được commit lên kho mã**, không đưa vào `.gitignore`.

Lý do: tệp khai báo phụ thuộc chỉ ghi khoảng phiên bản, nên hai người cài ở hai thời
điểm khác nhau sẽ nhận hai bộ thư viện khác nhau. Tệp khóa ghim chính xác từng phiên
bản của toàn bộ cây phụ thuộc, bảo đảm mọi thành viên và người đánh giá đều dựng lại
được đúng môi trường đã kiểm thử.

Khi cần cài lại phụ thuộc mà không muốn thay đổi tệp khóa, dùng lệnh cài đặt theo
tệp khóa (`npm ci`) thay vì lệnh cài đặt thông thường.

Khi xảy ra xung đột ở tệp khóa, **không sửa tay**. Lấy một phía bất kỳ rồi chạy lại
lệnh cài đặt để trình quản lý gói tự dựng lại tệp khóa từ tệp khai báo phụ thuộc.

Phía Python (`backend/`, `services/khai-pha/`) có **hai** tệp: `requirements.txt` ghim gói
dùng trực tiếp bằng `==`, `constraints.txt` khóa nốt mọi gói kéo theo (#368). Dockerfile
cài bằng `pip install -r requirements.txt -c constraints.txt`. Đổi một dòng trong
`requirements.txt` thì sinh lại `constraints.txt` của cùng thư mục bằng `pip freeze` trong
ảnh nền của Dockerfile — lệnh chính xác ghi ở đầu tệp `constraints.txt` — rồi dựng lại ảnh
và chạy kiểm thử. Không sửa tay từng dòng của `constraints.txt`.

### 5.4. Tệp không được đưa vào kho mã

Không commit: biến môi trường thật, khóa API, mật khẩu, tệp cơ sở dữ liệu,
thư mục phụ thuộc, tệp build. Dùng `.env.example` với giá trị mặc định an toàn.

### 5.5. Migration lược đồ (phạm vi `d-schema`)

Mọi thay đổi lược đồ là một migration Alembic trong `backend/alembic/versions/`, tên
`NNNN_mo_ta_khong_dau.py`. Trong tệp, `revision` trùng tên tệp bỏ đuôi `.py`, `down_revision`
trỏ bản ngay trước — ví dụ `0031_webhook.py` có `revision = "0031_webhook"`,
`down_revision = "0030_bao_thay_doi_ho_so"`. Dịch vụ ứng dụng chạy `alembic upgrade head` lúc
khởi động, nên chuỗi phải **thẳng một đường**: hai bản cùng nối sau một bản là hai đầu, Alembic
từ chối và cụm không lên.

**Số migration dùng chung cho cả kho, không phải của riêng nhánh.** Hai người làm song song, mỗi
người lấy "số kế tiếp" trong thư mục ở máy mình, là trùng số. GitHub vẫn báo pull request "không
xung đột" vì hai tệp khác tên — lỗi chỉ lộ ra khi cụm khởi động. Mỗi lần công việc có migration:

1. **Trước khi tạo**, xem số lớn nhất trên `origin/dev`, không xem thư mục ở máy:

   ```bash
   git fetch origin
   git ls-tree --name-only origin/dev backend/alembic/versions/
   ```

   Lấy số kế tiếp; `down_revision` trỏ bản cuối đó. Có pull request khác đang mở cũng thêm
   migration thì trao đổi trên issue trước khi chốt số.
2. **Trước khi mở pull request** — và mỗi lần `dev` nhận migration mới khi pull request còn mở —
   đưa `dev` vào nhánh bằng `git merge origin/dev` (không rebase rồi force push). Nếu `dev` đã có
   bản **cùng số**: đổi tên tệp sang số kế tiếp, sửa `revision`, `down_revision`, chú thích, tài
   liệu nhắc số cũ và tệp SQL đi kèm trong `backend/alembic/sql/` nếu có. Migration tạo hay đổi
   view báo cáo thì chạy lại `python scripts/pha_he.py`.
3. **Kiểm đúng một đầu** sau khi dựng lại cụm (`docker compose ... up -d --build`):

   ```bash
   docker exec dxlab-backend alembic heads
   ```

   phải ra **đúng một dòng**, mang tên migration của bạn. Ghi kết quả vào mô tả pull request.
4. **Không nối vào migration của pull request chưa merge.** `down_revision` chỉ trỏ bản đã có trên
   `dev`; cũng không đặt nhánh đích là nhánh của pull request kia. Cần lược đồ của nó thì chờ nó
   vào `dev` rồi tạo migration theo bước 1.
5. Cụm thử của bạn đã chạy migration mang số cũ thì bảng `alembic_version` ghi tên một bản không
   còn tồn tại, dịch vụ ứng dụng không lên: dựng lại cụm thử (`down -v` rồi `up -d --build`, mất
   dữ liệu thử).

---

## 6. Nhãn issue

Mỗi issue phải có đúng một nhãn từ mỗi nhóm bắt buộc:

| Nhóm | Bắt buộc | Các giá trị |
|------|----------|-------------|
| `type/` | Có | `feat` `fix` `docs` `research` `refactor` `test` `chore` |
| `space/` | Có | `H` `P` `D` `I` `core` |
| `priority/` | Có | `P0` `P1` `P2` `P3` |
| `status/` | Không | `blocked` `needs-discussion` `wontfix` |
| `scoring/` | Không | `pof` `final` |

---

## 7. Phát hành

1. Merge `dev` vào `main`
2. Sinh nhật ký thay đổi từ lịch sử commit
3. Đặt tag theo [Semantic Versioning](https://semver.org/): `vMAJOR.MINOR.PATCH`
4. Tạo bản phát hành trên nền tảng quản lý mã nguồn, đính kèm gói mã nguồn
   ở định dạng mở (`.tar.gz`). Không dùng các định dạng không mở như `.zip` hay `.rar`. Đính kèm thêm
   `bao-cao-giay-phep.md` — giấy phép của mọi gói phụ thuộc kể cả gián tiếp — tải từ artifact
   *bao-cao-giay-phep* của lần chạy CI trên commit được gắn tag, hoặc sinh ở máy bằng
   `python scripts/quet_giay_phep.py --anh backend=dxlab-backend:<bản> --anh khai-pha=dxlab-khai-pha:<bản> --bao-cao bao-cao-giay-phep.md`
5. Cập nhật `CHANGELOG.md` vào kho mã

### 7.1. Đăng trang tài liệu

Trang tài liệu `docs-site/` là trang tĩnh (Astro + Starlight). Địa chỉ và đường gốc lấy từ biến
môi trường lúc dựng (`docs-site/astro.config.mjs`), nên cùng một mã nguồn đăng được ở nhiều nơi:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DOCS_SITE_URL` | trống — trên Vercel tự lấy tên miền chính thức của dự án | Địa chỉ đầy đủ, dùng cho đường dẫn chuẩn và sơ đồ trang (`sitemap`). GitHub Pages của kho: `https://alavox-lab.github.io` |
| `DOCS_BASE_PATH` | `/` | Đường gốc. GitHub Pages của kho: `/dx-os-lab`; Vercel và tên miền riêng để trống |

Liên kết giữa các trang và ảnh viết tương đối hoặc qua `import`, nên trang chạy đúng với mọi đường
gốc. Dựng ở máy không cần biến nào: `npm run build` trong `docs-site/`, xem ở `npm run preview`.

**Đăng lên GitHub Pages** — cách kho đang dùng, tại `https://alavox-lab.github.io/dx-os-lab/`.
Workflow `.github/workflows/trang-tai-lieu.yml` dựng trang với `DOCS_SITE_URL=https://alavox-lab.github.io`
và `DOCS_BASE_PATH=/dx-os-lab` rồi đăng mỗi lần `main` đổi, hoặc khi bấm chạy tay (*Actions → Trang tài
liệu → Run workflow*). GitHub Pages miễn phí chỉ dành cho kho công khai, nên khi kho còn riêng tư việc tự
bỏ qua. Người điều phối kho mã bật một lần sau khi kho công khai:

1. *Settings → Pages → Build and deployment → Source*: chọn **GitHub Actions**.
2. Chạy tay workflow *Trang tài liệu* một lần, hoặc chờ lần phát hành kế tiếp lên `main`.
3. Sửa ô *Website* của kho:

   ```bash
   gh repo edit AlaVox-lab/dx-os-lab --homepage https://alavox-lab.github.io/dx-os-lab/
   ```

Dựng thử bản Pages ở máy: đặt hai biến trên rồi `npm run build`. Trên Git Bash cho Windows, đặt thêm
`MSYS_NO_PATHCONV=1` — không thì Git Bash đổi `/dx-os-lab` thành đường thư mục cài Git và bản dựng hỏng.

**Phương án khác — Vercel** (khi cần bản xem trước cho từng pull request hay tên miền gọn): đăng
nhập [vercel.com](https://vercel.com) bằng tài khoản GitHub, *Add New → Project*, nhập kho
`AlaVox-lab/dx-os-lab`, *Root Directory* `docs-site`. Vercel tự nhận Astro (lệnh dựng `npm run build`,
thư mục ra `dist`, Node theo `engines` trong `docs-site/package.json`) và tự lấy tên miền của dự án cho
`DOCS_SITE_URL`; `DOCS_BASE_PATH` để trống. Rồi trỏ ô *Website* tới địa chỉ Vercel cấp bằng
`gh repo edit --homepage`.

---

## 8. Báo lỗi và đề xuất

Dùng các mẫu có sẵn trong mục Issues. Trước khi tạo mới, tìm xem đã có
issue tương tự chưa. Với lỗi, cung cấp đủ các bước tái hiện và thông tin
môi trường để người khác dựng lại được tình huống.
