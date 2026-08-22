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
| Cập nhật lần cuối | 2026-08-21 |
| Phiên bản hiện tại | `v0.1.0` |
| Giai đoạn | Giai đoạn 1 — Khảo sát và thiết kế (đang bắt đầu) |
| Mốc công việc đang chạy | Tuần 3 — Bắt Đầu |
| Trạng thái kho mã | Riêng tư, sẽ chuyển công khai trước khi nộp bài |
| Có mã nguồn ứng dụng chưa | **Chưa** |
| Số ngày còn lại tới chấm kho mã | Tính từ 07/12/2026 |

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

## Đang làm

Chưa có công việc nào đang dở. Ba khảo sát Open-Core (#19, #20, #21) đã mở và gán,
chờ bắt đầu.

---

## Việc tiếp theo

Xếp theo thứ tự ưu tiên. Chi tiết từng giai đoạn xem `ROADMAP.md`.

### Ưu tiên cao

1. **Thực hiện ba khảo sát Open-Core** đã mở: định danh tập trung cho `H` (#19),
   tự động hóa luồng công việc cho `P` (#20), kinh doanh thông minh cho `D` (#21).
   Mỗi khảo sát kết thúc bằng tài liệu so sánh trong `docs/` và một bản ghi quyết định
   trong `docs/adr/`
2. **Thiết kế nghiệp vụ** (Giai đoạn 1.3), dựa trên `docs/process-flow.md`: bảng trạng
   thái và quy tắc chuyển, ma trận phân quyền theo vai trò, danh sách ràng buộc
   Poka-yoke, lược đồ nhật ký sự kiện, danh mục chỉ số cho bảng điều khiển

### Ưu tiên trung bình

3. Thêm `CODE_OF_CONDUCT.md` — chuẩn cộng đồng nguồn mở
4. Thêm hai thành viên (quyền Write) và giảng viên (quyền Read hoặc Triage) vào kho mã;
   điền bảng Đội ngũ trong `README.md`

### Chờ điều kiện

5. Hạ tầng phát triển: `docker-compose.yml`, `.env.example`, tích hợp liên tục — cần có
   cấu trúc thư mục mã nguồn trước
6. Chuyển kho mã sang công khai — làm trước khi nộp bài, khi đó quy tắc bảo vệ nhánh mới
   có hiệu lực

---

## Đang vướng

| Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| Quy tắc bảo vệ nhánh chưa có hiệu lực | Quy trình phụ thuộc kỷ luật cá nhân thay vì ràng buộc kỹ thuật | Chuyển kho mã sang công khai. Trong lúc chờ, tuân thủ tự giác |
| Chưa chốt công cụ quản trị cơ sở dữ liệu | Chưa ảnh hưởng, chỉ là công cụ hỗ trợ | Đã trình hai phương án, chờ ý kiến giảng viên |
| Chưa chốt nền tảng Open-Core nào | Chưa bắt đầu viết mã được | Ba issue khảo sát đã mở (#19, #20, #21), chờ thực hiện và ra bản ghi quyết định |

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
