# Hướng dẫn đóng góp

Cảm ơn bạn đã quan tâm tới dự án. Tài liệu này mô tả quy trình làm việc,
quy ước mã nguồn và các tiêu chuẩn mà mọi đóng góp cần tuân thủ.

Dự án được phát hành theo giấy phép MIT. Khi gửi đóng góp, bạn đồng ý rằng
phần đóng góp của mình được phát hành theo cùng giấy phép này.

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

- Dòng tiêu đề tối đa 72 ký tự, viết ở thì hiện tại, không kết thúc bằng dấu chấm
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
chú thích phù hợp với ngôn ngữ:

```
SPDX-License-Identifier: MIT
Copyright (c) 2026 AlaVox-lab
```

Yêu cầu này bắt nguồn từ tiêu chí chấm điểm của cuộc thi: mã nguồn không ghi
giấy phép trong từng tệp sẽ bị trừ điểm.

### 5.2. Thư viện bên thứ ba

- Khai báo phụ thuộc qua trình quản lý gói, kèm tệp khóa phiên bản
- Không sao chép mã nguồn thư viện vào kho mã của dự án
- Không chỉnh sửa mã nguồn của thư viện bên thứ ba. Nếu cần thay đổi hành vi,
  dùng cơ chế cấu hình, plugin hoặc lớp bọc
- Trước khi thêm một phụ thuộc mới, kiểm tra giấy phép của nó có nằm trong
  danh sách được OSI công nhận và có tương thích với MIT hay không.
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

### 5.4. Tệp không được đưa vào kho mã

Không commit: biến môi trường thật, khóa API, mật khẩu, tệp cơ sở dữ liệu,
thư mục phụ thuộc, tệp build. Dùng `.env.example` với giá trị mặc định an toàn.

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
   ở định dạng mở (`.tar.gz`). Không dùng các định dạng không mở như `.zip` hay `.rar`
5. Cập nhật `CHANGELOG.md` vào kho mã

---

## 8. Báo lỗi và đề xuất

Dùng các mẫu có sẵn trong mục Issues. Trước khi tạo mới, tìm xem đã có
issue tương tự chưa. Với lỗi, cung cấp đủ các bước tái hiện và thông tin
môi trường để người khác dựng lại được tình huống.
