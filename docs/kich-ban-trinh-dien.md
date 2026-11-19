# Kịch bản trình diễn chung kết

> **Mục đích**: cả nhóm luyện theo một thứ tự duy nhất cho 15 phút trước ban giám khảo ngày 10/12/2026.
> Tệp chỉ dùng tính năng đã có trên `dev`; tính năng mới vào `dev` thì cập nhật bảng ở mục 3.
>
> **Issue**: #399 · **Căn cứ**: đề thi PMNM OLP 2026 mục 6 — mỗi đội 15 phút, gồm giải pháp và lựa chọn công
> nghệ, tính năng nền tảng và bài toán ứng dụng minh họa, kết quả và demo, định hướng phát triển.

---

## 1. Thông điệp một câu

> **Corelens là nền tảng lõi nguồn mở không giao diện — định danh, cổng API, dữ liệu, động cơ luồng công
> việc — mà quy trình chạy trên nó *tự soi lại chính mình*: mọi bước chuyển ghi nhật ký, từ nhật ký hệ
> thống vẽ lại quy trình thật và chỉ ra chỗ nghẽn.**

Mọi phần bên dưới quay về câu này. Giám khảo hỏi "khác gì một helpdesk" thì trả lời bằng nửa sau của câu.

---

## 2. Phân bổ 15 phút

| Phút | Phần của đề | Nội dung | Người nói |
|---|---|---|---|
| 0:00–1:00 | Mở đầu | Vấn đề của đề (ốc đảo dữ liệu, lệ thuộc nhà cung cấp) và thông điệp một câu | Navigator |
| 1:00–4:00 | Giải pháp và lựa chọn công nghệ | Tháp ba tầng → bộ lắp ghép (mục 4.1), vì sao tự viết engine (ADR-0004), mô hình nhiều giấy phép | Navigator |
| 4:00–6:00 | Tính năng nền tảng | Lõi không giao diện: `/core/v1` qua cổng API, ứng dụng ngoài chạy trọn một quy trình bằng API (demo A) | Thành viên 1 |
| 6:00–12:00 | Bài toán minh họa và demo | Cổng yêu cầu nội bộ đi qua H → P → D → I (demo B, C, D) | Thành viên 2 điều khiển, Navigator dẫn |
| 12:00–14:00 | Kết quả | Con số của kho mã (mục 4.3), bảng đối chiếu đề thi | Thành viên 1 |
| 14:00–15:00 | Định hướng | Ba việc tiếp theo (mục 4.4) và lời kết | Navigator |

Cột *Người nói* là đề xuất — nhóm chốt lại khi luyện. Giữ **6 phút demo là trục**: phần nói bị lố thì cắt
mục 4, không cắt demo.

---

## 3. Thứ tự thao tác demo

Bốn cửa sổ trình duyệt ẩn danh mở sẵn, đã đăng nhập (mật khẩu chung `matkhau123`), xếp cạnh nhau trên màn
chiếu; một cửa sổ dòng lệnh ở gốc kho:

| Cửa sổ | Tài khoản | Vai |
|---|---|---|
| ① | `an.nguyen` | Người gửi |
| ② | `binh.tran` | Điều phối viên |
| ③ | `dung.pham` | Trưởng phòng Công nghệ thông tin |
| ④ | `cuong.le` | Người xử lý Công nghệ thông tin |

### Demo A — Nền tảng lõi không giao diện (≈ 2 phút, phút 4–6)

| Bước | Thao tác | Giám khảo phải thấy |
|---|---|---|
| A1 | Mở `http://localhost:9080/docs` | Bảy nhóm "Lõi — …" đứng đầu tài liệu API: luồng công việc, tệp, nhật ký sự kiện, lưu trữ lạnh, thông báo, webhook, định danh |
| A2 | Cửa sổ dòng lệnh: `python examples/goi-loi/quy_trinh_mua_sam.py` | Một chương trình **không phải cổng người dùng** dùng ba tài khoản dịch vụ chạy trọn quy trình thứ hai (đề xuất mua sắm) chỉ bằng API — không một dòng mã riêng cho quy trình đó |
| A3 | Chỉ vào dòng "Lõi chạy 2 quy trình" trong đầu ra | Động cơ chạy nhiều quy trình cùng lúc, quy trình là dữ liệu |

Câu dẫn: *"Đề bắt nền tảng lõi không có giao diện. Đây là lõi đó — một ứng dụng khác vừa dùng nó."*

Chạy thêm `--so-tien 12000000` để thấy cùng quy trình rẽ sang duyệt cấp hai khi số tiền vượt ngưỡng — điều
kiện trên cạnh (#397), ngưỡng nằm trong dữ liệu. Giám khảo hỏi về chuẩn mô tả quy trình: quy trình xuất được
ra BPMN 2.0 qua `GET /core/v1/workflow/processes/{mã}/bpmn` (#405), mở bằng công cụ BPMN nguồn mở.

### Demo B — Một hồ sơ đi qua H và P (≈ 2,5 phút, phút 6–8:30)

| Bước | Cửa sổ | Thao tác | Giám khảo phải thấy |
|---|---|---|---|
| B1 | ① | *Gửi yêu cầu* → **Sự cố thiết bị** → điền tiêu đề, mô tả, mã tài sản, vị trí → gửi | Biểu mẫu có trường riêng theo loại, khai trong dữ liệu |
| B2 | ② | Trang chủ — hồ sơ vừa gửi **tự hiện** ở *Cần bạn xử lý*, không tải lại trang | Cập nhật thời gian thực (#387) |
| B3 | ② | **Phân loại yêu cầu**, đặt mức ưu tiên → **Chuyển về phòng ban** *Công nghệ thông tin* | Poka-yoke: chỉ điều phối viên đặt được mức ưu tiên |
| B4 | ③ | **Xác duyệt và giao xử lý**, chọn `cuong.le` | Đồng hồ hạn bắt đầu chạy, tính theo giờ làm việc |
| B4a | ③ | (nếu còn thời gian) Hàng đợi phòng ban → **Dạng bảng** | Cùng hồ sơ, xem dạng Kanban theo trạng thái (#403) |
| B5 | ④ | **Hoàn thành xử lý** | — |
| B6 | ① | **Xác nhận đạt** → mở **dòng thời gian** | Mỗi bước: ai bấm, lúc nào, giá trị nào đổi — đó là nhật ký sự kiện |

Câu dẫn ở B6: *"Mỗi dòng ở đây là một bản ghi nhật ký chỉ ghi thêm. Phần sau dùng chính nhật ký này."*

### Demo C — D: dữ liệu và bảng điều khiển (≈ 1 phút, phút 8:30–9:30)

| Bước | Cửa sổ | Thao tác | Giám khảo phải thấy |
|---|---|---|---|
| C1 | ② | Mục **Báo cáo** → **Bảng điều khiển** | Bảng điều khiển Superset nhúng trong cổng, không đăng nhập lần hai, số từ dữ liệu trình diễn |
| C2 | ③ | Cũng mục **Báo cáo** | Trưởng phòng chỉ thấy số của phòng mình — cùng bảng, phạm vi theo vai |

### Demo D — I: vòng phản hồi tự soi quy trình (≈ 2,5 phút, phút 9:30–12) — **điểm nhấn**

| Bước | Cửa sổ | Thao tác | Giám khảo phải thấy |
|---|---|---|---|
| D1 | ② | **Báo cáo** → **Quy trình thực tế**, nút **90 ngày** | Sơ đồ quy trình **vẽ lại từ nhật ký**, không ai nhập tay |
| D2 | ② | Đọc to các **câu kết luận** đầu màn | Điểm nghẽn rõ nhất (trạng thái chờ lâu nhất, gấp mấy lần mức chung), nhánh lệch khỏi thiết kế |
| D3 | ② | Bấm một mã hồ sơ trong danh sách nhánh lệch | Mở đúng hồ sơ đó — mọi con số tra ngược được |
| D4 | ② | Nếu cụm bật hồ sơ `tri-tue`: chỉ khối **Khuyến nghị cải tiến** | AI chỉ gợi ý bằng câu chữ; con số luôn do hệ thống gắn — câu nào lệch số bị bỏ |

Câu dẫn: *"Đây là thứ một helpdesk không có: quy trình thiết kế một đằng, chạy thật một nẻo — hệ thống tự nói
ra chỗ lệch."*

---

## 4. Nội dung nói

### 4.1. Tháp ba tầng và bộ lắp ghép (phút 1–4)

Một trang chiếu: tháp ba tầng của đề, tô màu phần nhóm làm.

| Tầng của đề | Nhóm dùng | Giấy phép | Lắp hay tự viết |
|---|---|---|---|
| Định danh, SSO | Keycloak | Apache-2.0 | Lắp — ADR-0001 |
| Cổng API | Apache APISIX | Apache-2.0 | Lắp — ADR-0010 |
| Dữ liệu có cấu trúc | PostgreSQL + pgvector | PostgreSQL License | Lắp |
| Dữ liệu phi cấu trúc | SeaweedFS | Apache-2.0 | Lắp — ADR-0002 |
| Động cơ luồng công việc | Engine máy trạng thái của nhóm | MIT | **Tự viết** — ADR-0004 |
| Báo cáo | Apache Superset | Apache-2.0 | Lắp — ADR-0003 |
| Khai phá quy trình | PM4Py trong dịch vụ tách riêng | AGPL-3.0 | Lắp, cô lập — ADR-0007 |
| Mô hình ngôn ngữ (tùy chọn) | llama.cpp + Qwen2.5-1.5B | MIT · Apache-2.0 | Lắp — ADR-0008 |

Ba ý phải nói:

1. **Lắp những gì thế giới đã làm tốt, tự viết phần tạo khác biệt** — engine quy trình, Poka-yoke, nhật
   ký sự kiện, lớp nối bốn không gian
2. **Mọi lựa chọn có bản ghi quyết định** trong `docs/adr/`, kèm khảo sát ứng viên và lý do loại
3. **Giấy phép làm đúng**: AGPL chỉ nằm trong một dịch vụ tách riêng, tích hợp liên tục chặn `import`
   sai chỗ (`LICENSES.md`)

### 4.2. Bốn nguyên lý của đề

Không trình bày riêng; khi giám khảo hỏi thì dẫn tới `docs/doi-chieu-de-thi.md` mục 4: tách dữ liệu theo
vòng đời (tầng lạnh), phả hệ dữ liệu sinh tự động, zero-trust với token kiểm hai lớp. Nguyên lý hội tụ IT/OT
nói thẳng là ngoài phạm vi và vì sao.

### 4.3. Con số của kho mã (phút 12–14)

Đọc từ kho ngay trước buổi thi — đừng chép số cũ:

```powershell
git fetch origin
git tag --sort=-creatordate | Select-Object -First 1
docker exec dxlab-backend python -m pytest -p no:cacheprovider -q
docker exec dxlab-khai-pha python -m pytest -p no:cacheprovider -q
```

Nói: số bản phát hành, số bài kiểm thử tự động của hai dịch vụ, năm kiểm tra chạy trên mỗi pull request,
số bản ghi quyết định đã chấp nhận, trang tài liệu `docs-site/`, nhật ký thay đổi sinh từ lịch sử commit.

### 4.4. Định hướng (phút 14–15)

Chọn ba, nói mỗi việc một câu:

- Tách động cơ luồng công việc thành dịch vụ riêng (Mức 3 trong `docs/doi-chieu-de-thi.md`)
- Trục truyền phát sự kiện chuyên dụng (Kafka, Apache-2.0) đọc cùng con trỏ với webhook hiện có
- Triển khai thật: TLS, két bí mật, sao lưu tự động — các mục *Trước khi dùng thật* của README

---

## 5. Chuẩn bị trước buổi thi

### 5.1. Một ngày trước

1. Máy trình diễn: Docker Desktop chạy, ổ chứa dữ liệu Docker còn trống trên 15 GB, cổng 3000 · 8080 ·
   8088 · 8333 · 9080 trống — tắt mọi cụm khác (`docker ps`)
2. Dựng cụm sạch từ bản phát hành dự thi, ở gốc kho:

   ```powershell
   docker compose --env-file infra/.env -f infra/docker-compose.yml down -v
   docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build
   ```

   `down -v` xóa mọi dữ liệu thử — chỉ chạy trên máy trình diễn, sau khi nhóm đồng ý
3. Nạp dữ liệu trình diễn (vài trăm hồ sơ giả trải vài tháng, không gỡ ra được):

   ```powershell
   python scripts/nap_du_lieu_trinh_dien.py --xac-nhan
   ```

4. Tài khoản dịch vụ cho demo A — `.env` phải có các dòng `KEYCLOAK_INTEGRATION_*` của `.env.example`:

   ```powershell
   python scripts/tai_khoan_dich_vu.py
   python examples/goi-loi/quy_trinh_mua_sam.py
   ```

5. Tùy chọn mô hình ngôn ngữ cho D4 — tốn thêm khoảng 1,5 GB bộ nhớ, chỉ bật nếu máy đủ:
   `docker compose --env-file infra/.env -f infra/docker-compose.yml --profile tri-tue up -d`
6. **Sao lưu ngay sau khi chuẩn bị xong** — đây là điểm khôi phục nếu demo hỏng:

   ```powershell
   python scripts/sao_luu.py tao sao-luu/truoc-chung-ket
   ```

7. Chạy trọn demo A–D một lần, bấm giờ, rồi khôi phục bản sao lưu để dữ liệu sạch như lúc đầu

### 5.2. Ba mươi phút trước

- `docker compose … ps`: sáu dịch vụ `healthy`, `keycloak` và `seaweedfs` `Up`; đăng nhập `khanh.vo` mở
  màn **Hệ thống** (`/he-thong`) — mọi tầng xanh
- Mở sẵn bốn cửa sổ ở mục 3, đã đăng nhập; phóng chữ trình duyệt 125 % cho dễ đọc trên máy chiếu
- Tắt thông báo hệ điều hành, tắt chế độ ngủ của máy

---

## 6. Phương án dự phòng

| Sự cố | Dấu hiệu | Làm gì — không dừng phần trình bày |
|---|---|---|
| Mạng hội trường chậm hay mất | Trang tải lâu | Cụm chạy trọn trên máy, không cần Internet. Không dùng tài nguyên ngoài |
| Mô hình ngôn ngữ chậm hay lỗi | Khối khuyến nghị không hiện | Bỏ D4, nói: "Gợi ý là lớp phụ — tắt đi hệ thống vẫn chạy thủ công." Đó chính là nguyên tắc AI chỉ gợi ý |
| Hồ sơ không tự hiện ở B2 | Cửa sổ ② đứng yên | Cổng tự hỏi lại sau tối đa 12 giây; hoặc tải lại trang. Không giải thích dài |
| Một dịch vụ chết | Màn **Hệ thống** báo đỏ, trang báo "hệ thống không phản hồi" | `docker compose … up -d <dịch vụ>`; trong lúc chờ chuyển sang phần nói mục 4 |
| Dữ liệu demo bị làm rối khi luyện | Số trên bảng điều khiển lạ | `python scripts/sao_luu.py khoi-phuc sao-luu/truoc-chung-ket` (dưới 15 phút) |
| Máy trình diễn hỏng hẳn | — | Máy thứ hai đã dựng sẵn theo mục 5.1; tệ nhất thì phát video quay sẵn cả bốn demo |

Quay sẵn một video demo A–D (màn hình, không lời) sau buổi luyện tập cuối — đây là phương án cuối cùng.

---

## 7. Câu hỏi dự kiến của ban giám khảo

| Câu hỏi | Ý trả lời | Dẫn chứng trong kho |
|---|---|---|
| Sao tự viết engine quy trình mà không dùng Flowable, Camunda? | Đã khảo sát; engine nhỏ, trạng thái và quy tắc là dữ liệu, ghi nhật ký ở đúng một cửa — điều kiện để khai phá quy trình tin được | `docs/adr/0004-tu-viet-engine-may-trang-thai.md`, `docs/workflow-engine-survey.md` |
| Nền tảng lõi "không giao diện" ở chỗ nào, khi cổng người dùng chung dịch vụ? | API lõi tách bằng không gian địa chỉ `/core/v1`, ứng dụng khác chạy trọn quy trình chỉ qua đó (demo A); tách tiến trình là Mức 3 | `docs/ARCHITECTURE.md` mục 2.3, `examples/goi-loi/` |
| AI làm gì, nếu AI sai thì sao? | AI chỉ ghi trường gợi ý, người xác nhận mới thành quyết định; hệ thống đo tỷ lệ người ghi đè | `CLAUDE.md` mục 4.3, `docs/adr/0008-chon-co-so-du-lieu-vec-to-va-mo-hinh-cuc-bo.md` |
| Dùng AGPL có làm cả dự án thành AGPL không? | Không: PM4Py chỉ trong `services/khai-pha/`, giao tiếp qua HTTP, thư mục đó mang AGPL, phần còn lại MIT; CI chặn `import` sai chỗ | `LICENSES.md`, `docs/adr/0007-chon-thu-vien-khai-pha-quy-trinh.md` |
| Bảo mật thế nào? | Token kiểm hai lớp — tại cổng API và lại ở dịch vụ; dịch vụ và cơ sở dữ liệu không mở cổng ra ngoài; giới hạn tốc độ; xác thực hai lớp tùy chọn | `docs/doi-chieu-de-thi.md` mục 4 (iv), ADR-0010 |
| Mở rộng sang doanh nghiệp khác thế nào? | Đổi quy trình, vai, hạn, loại yêu cầu bằng dữ liệu hay màn **Cấu hình quy trình**, không sửa mã; thêm quy trình mới như quy trình mua sắm | `docs-site/src/content/docs/quan-tri/tuy-bien-quy-trinh.md` |
| Dữ liệu demo có thật không? | Hồ sơ giả do bộ sinh đi đúng cạnh, đúng vai của bộ quy tắc đang bật; nhật ký vẫn chỉ ghi thêm | `scripts/nap_du_lieu_trinh_dien.py` |
| Đội làm việc thế nào? | Issue → nhánh → pull request có review → squash vào `dev` → phát hành; nhật ký thay đổi sinh từ commit | `CONTRIBUTING.md`, `CHANGELOG.md`, trang Releases |

---

## 8. Luyện tập

- Ít nhất **ba lần** trọn 15 phút, bấm giờ từng phần theo mục 2; ghi lại phần nào lố
- Lần cuối luyện trên đúng máy và đúng màn chiếu sẽ dùng
- Mỗi người trả lời thử hai câu ở mục 7 mà không nhìn tài liệu
