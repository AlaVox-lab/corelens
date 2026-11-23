# Đối chiếu với đề thi Phần mềm nguồn mở OLP 2026

> **Mục đích**: đặt từng yêu cầu của đề thi cạnh hiện trạng dự án — đáp ứng bằng gì, nằm ở đâu, còn
> thiếu gì, phần nào để ngoài phạm vi và vì sao.
>
> **Issue liên quan**: #363 (issue gốc #369) · **Đối chiếu trên bản**: `v0.16.0` · **Ngày**: 2026-11-15
>
> Tệp này cập nhật khi từng issue của Giai đoạn 5 hoàn thành. Cột *Hiện trạng* chỉ ghi điều đã có trong
> mã; việc dự định làm nằm ở cột *Việc còn lại*.

---

## 1. Đề thi yêu cầu gì

Đề yêu cầu dựng mô hình **DX-OS Open-Core** theo tháp ba tầng:

| Tầng | Vai trò | Bắt buộc trong bài thi |
|---|---|---|
| 1 — Nền tảng dịch vụ lõi số | Dịch vụ dùng chung chạy ngầm, **không giao diện**, phục vụ ứng dụng tầng trên | **Có** — định danh/SSO, cổng API, quản trị dữ liệu cấu trúc và phi cấu trúc, động cơ luồng công việc |
| 2 — Không gian năng lực số H-P-D-I | Ứng dụng có giao diện cho người dùng cuối | **Có** — ít nhất một ứng dụng minh họa |
| 3 — Nền tảng kinh doanh số | Ứng dụng chuyên ngành | Không |

Hạn gửi bài: 17:00 ngày 06/12/2026. Chấm kho mã 07–09/12, trình diễn 10/12 (15 phút mỗi đội).

---

## 2. Tầng 1 — bốn dịch vụ lõi bắt buộc

| Dịch vụ | Hiện trạng | Nằm ở đâu | Việc còn lại |
|---|---|---|---|
| Định danh, đăng nhập một lần | **Có.** Keycloak `26.7.3`; dịch vụ ứng dụng kiểm chữ ký, nơi phát, người nhận, hạn dùng của token; bảng điều khiển và kho tri thức dùng chung đăng nhập. Ứng dụng khác gọi lõi bằng **tài khoản dịch vụ** (client `dx-integration`, luồng client credentials, #365; hai tài khoản duyệt của ví dụ quy trình thứ hai, #376); `GET /core/v1/identity/me`. Realm mẫu bật chống dò mật khẩu (khóa tạm sau 10 lần sai, tự mở) và chính sách mật khẩu tối thiểu (#377) | `infra/keycloak/`, `backend/app/auth/`, `scripts/tai_khoan_dich_vu.py`, `scripts/xac_thuc_hai_lop.py`, ADR-0001 | Xác thực hai lớp tùy chọn — #366 |
| **Cổng API** | **Có** (#364). Apache APISIX `3.20.0` ở cụm mặc định là cửa vào duy nhất của API: kiểm chữ ký, nơi phát, người nhận, hạn dùng của token Keycloak ngay tại biên (thiếu, hết hạn, khóa lạ: 401; phát cho client khác: 403 — không tới dịch vụ), giới hạn tốc độ chung theo địa chỉ người gọi, định tuyến tới dịch vụ ứng dụng. Cổng người dùng cũng gọi qua nó; dịch vụ ứng dụng và PostgreSQL không còn mở cổng ra máy; dịch vụ vẫn kiểm token lại. API của lõi có phiên bản dưới `/core/v1` (#365) đi qua tuyến cần token — thiếu token là 401 tại cổng, kể cả đường lõi chưa có | `infra/cong-api/`, `backend/tests/test_cong_api.py`, `backend/tests/test_loi_api.py`, ADR-0010, `ARCHITECTURE.md` mục 7.4 | — |
| Dữ liệu có cấu trúc | **Có.** PostgreSQL 16 + pgvector, lược đồ do migration quản lý, nâng cấp giữ dữ liệu, tài khoản chỉ đọc riêng cho báo cáo và khai phá. Nhật ký sự kiện chuẩn hóa phơi qua API của lõi: `GET /core/v1/events` (CSV, JSON — #365); bản lưu trữ lạnh theo tháng: `GET /core/v1/archive` (#378) | `backend/alembic/`, `ARCHITECTURE.md` mục 2.3, 5.4, 6.3a | — |
| Dữ liệu phi cấu trúc | **Có.** SeaweedFS `4.45` qua S3 API; kiểm chữ ký tệp, quét mã độc tùy chọn. Phơi qua API của lõi: `/core/v1/files/…` — chính sách, tải lên, tải về (#365) | `backend/app/storage/`, ADR-0002, `ARCHITECTURE.md` mục 2.3 | — |
| Động cơ luồng công việc | **Có, Mức 2** (#365 Mức 1, #376 Mức 2). Engine máy trạng thái tự viết: trạng thái, bước chuyển, vai trò, ràng buộc chống sai, hạn xử lý đều là dữ liệu; bộ quy tắc có phiên bản; mọi bước chuyển ghi nhật ký chỉ ghi thêm. **Chạy nhiều quy trình cùng lúc**: danh mục `processes`, mỗi quy trình một bộ quy tắc đang bật, loại yêu cầu quyết định quy trình của hồ sơ. Quy trình mẫu thứ hai — đề xuất mua sắm duyệt hai cấp — thuần dữ liệu, không một dòng mã riêng. **Điều kiện trên cạnh** (#397): rẽ nhánh theo trường riêng của hồ sơ khai trong bảng `transition_conditions` — đề xuất dưới 5.000.000 đồng trưởng phòng duyệt là xong, từ ngưỡng trở lên mới sang cấp hai; đổi ngưỡng là sửa dữ liệu. API của lõi dưới `/core/v1/workflow`: danh mục quy trình, loại và trạng thái theo quy trình, tạo và đọc hồ sơ, bước được phép, bước chưa được kèm lý do (sai vai, ràng buộc, điều kiện trên cạnh — #424), đi bước, lịch sử; cửa bước chuyển **trung lập với vai** — người gửi, trưởng phòng, điều phối viên đi đúng cạnh của mình trong phạm vi của mình. Một chương trình ngoài cổng người dùng chạy trọn quy trình thứ hai chỉ bằng API đó, với ba tài khoản dịch vụ (`examples/goi-loi/quy_trinh_mua_sam.py`). Báo cáo, khai phá và các màn của ứng dụng không lẫn quy trình | `backend/app/workflow/`, `infra/seed/06-quy-trinh-mua-sam.sql`, `infra/seed/07-dieu-kien-mua-sam.sql`, `app/rules/dieu_kien.py`, `examples/goi-loi/`, ADR-0004, ADR-0005, `ARCHITECTURE.md` mục 2.3 | Engine vẫn chung một dịch vụ với các màn của ứng dụng; điều kiện trên cạnh chỉ nối "và", chỉ so trường riêng với hằng số. Mức 3 — tách engine thành dịch vụ riêng: ngoài đợt này |
| Nguyên tắc lõi không giao diện | **Có ở Mức 1** (#365). API của lõi không giao diện, có phiên bản, dưới `/core/v1`, sáu nhóm "Lõi — …" đứng đầu mô tả OpenAPI; các đường còn lại thuộc ứng dụng minh họa. Ranh giới vẽ bằng không gian địa chỉ trong cùng một dịch vụ, chưa tách tiến trình | `backend/app/main.py`, `ARCHITECTURE.md` mục 2.3 | Tài liệu tổng quan ba tầng — #367 |

### Các nhóm dịch vụ lõi khác đề có nêu

Đề liệt kê bảy nhóm dịch vụ; bốn dịch vụ ở trên là phần bắt buộc. Hiện trạng các phần còn lại:

| Nhóm | Đã có | Chưa có / ngoài phạm vi |
|---|---|---|
| Vận hành, giám sát, kiểm toán | Nhật ký sự kiện bất biến; nhật ký có cấu trúc kèm mã yêu cầu; điểm cuối sống, sẵn sàng, số đo; sao lưu tay và khôi phục có đối soát; **truyền phát sự kiện ra ngoài bằng webhook**: `/core/v1/webhooks`, ký HMAC, thử lại, con trỏ trên nhật ký chỉ ghi thêm (#390) | Trục truyền phát chuyên dụng (Kafka) — hướng mở rộng, cần ADR; sao lưu tự động theo lịch |
| Truyền thông, giao vận | Hàng đợi thông báo thư có thử lại (hộp thư đi trong cơ sở dữ liệu); **kết nối thời gian thực** bằng Server-Sent Events: PostgreSQL `NOTIFY` → `GET /me/stream` lọc theo quyền xem → cổng tự làm mới, hỏi định kỳ làm dự phòng (#387) | WebSocket hai chiều — chưa cần, cổng chỉ nhận |
| Đa thuê ước, cá thể hóa | Ẩn danh hóa nhãn tên theo thời hạn lưu giữ (ADR-0009); lọc dữ liệu báo cáo theo phòng | Đa thuê ước; đa ngôn ngữ giao diện — ngoài phạm vi |
| Két bí mật, chữ ký số | — | Ngoài phạm vi; bí mật nằm trong `infra/.env` |

---

## 3. Tầng 2 — ứng dụng minh họa

Ứng dụng minh họa là **cổng vận hành yêu cầu nội bộ**, phủ cả bốn không gian:

| Không gian | Có gì | Nằm ở đâu |
|---|---|---|
| `H` | Cổng theo vai, hộp thư trao đổi trên hồ sơ, ủy quyền khi vắng mặt, kho tri thức đăng nhập một lần (tùy chọn), **bảng Kanban** của buồng lái phòng ban — cột theo trạng thái lấy từ dữ liệu (#403) | `frontend/`, `infra/tri-thuc/` |
| `P` | Luồng 11 trạng thái, 32 bước; phân loại, định tuyến, leo thang, mở lại có giới hạn; màn cấu hình quy trình; **phân loại và chuyển phòng hàng loạt** trên hàng đợi điều phối — mỗi hồ sơ vẫn qua cửa chuyển trạng thái duy nhất, một dòng nhật ký, hồ sơ bị chặn báo riêng (#440) | `backend/app/workflow/`, `docs/process-flow.md` |
| `D` | Lớp báo cáo trên nhật ký sự kiện, bảng điều khiển nhúng trong cổng lọc theo phòng, xuất CSV và JSON; **mức hài lòng của người gửi** chấm khi xác nhận hoàn tất, lên bảng điều khiển theo phòng — điểm trung bình, tỷ lệ được chấm, phân bố điểm (#433) | `backend/app/analytics/`, `infra/superset/` |
| `I` | Khai phá quy trình thực tế; gợi ý phân loại và người xử lý; hồ sơ tương tự; gợi ý bài tri thức. Mọi gợi ý cần người xác nhận, có đo tỷ lệ ghi đè | `services/khai-pha/`, `backend/app/intelligence/` |

Yêu cầu "ít nhất một ứng dụng minh họa" đã đạt.

---

## 4. Bốn nguyên lý thiết kế của đề

| Nguyên lý | Hiện trạng | Việc còn lại |
|---|---|---|
| (i) Tách dữ liệu theo vòng đời và tốc độ | **Có.** Tầng nóng: bảng tác nghiệp tách khỏi view báo cáo; nhật ký sự kiện chỉ ghi thêm; báo cáo và khai phá đọc bằng tài khoản chỉ đọc riêng nên không khóa bảng tác nghiệp. **Tầng lạnh** (#378): bộ quét `cold-archive` niêm phong mỗi tháng đã khép ra kho đối tượng — nhật ký sự kiện và hồ sơ đã kết thúc, CSV gzip định dạng mở kèm `manifest.json` có số dòng và SHA-256; bản lưu bất biến, chạy lại an toàn, không mang tên người (ADR-0009); đọc lại qua `GET /core/v1/archive` và `scripts/doc_luu_tru.py` (kiểm mã băm, đối chiếu tầng nóng) | Dọn dữ liệu cũ khỏi tầng nóng chưa làm — nhật ký chỉ ghi thêm là nền của khai phá và kiểm toán; việc đó theo chính sách lưu giữ của ADR-0009 |
| (ii) Hội tụ dữ liệu hành chính và vận hành | **Chưa có** | Ngoài phạm vi: bài toán minh họa không có thiết bị hiện trường |
| (iii) Quản trị dữ liệu: phả hệ, nguồn gốc, chất lượng | **Có.** Trang phả hệ [`pha-he-du-lieu.md`](pha-he-du-lieu.md) sinh tự động từ định nghĩa bảng điều khiển và view (#379): mỗi biểu đồ → bộ dữ liệu → view → bảng nguồn và cột, sơ đồ, nguồn gốc nhật ký sự kiện từ cửa chuyển trạng thái tới bảng điều khiển, khai phá và lưu trữ lạnh; tích hợp liên tục báo đỏ khi trang lệch định nghĩa (`scripts/pha_he.py --kiem`). Mọi con số trên màn Quy trình thực tế tra ngược được về kết quả khai phá; hàm kiểm cấu hình chặn dữ liệu cấu hình sai; nhật ký sửa cấu hình; bản lưu lạnh mang mã băm | Phả hệ mức cột từ cột biểu đồ tới cột nguồn chưa tách riêng — trang ghi cột dùng của biểu đồ và cột tham chiếu của view |
| (iv) Bảo mật không tín nhiệm gắn với hạ tầng bằng mã | **Có.** Kiểm token hai lớp: tại biên ở cổng API (#364) và lại ở dịch vụ; giới hạn tốc độ tại biên và theo người dùng trong dịch vụ; chỉ cổng API, cổng người dùng và giao diện các nền tảng mở cổng ra máy; chính sách nội dung có nonce, quét mã độc tệp tùy chọn, kiểm sức khỏe từng dịch vụ; tuyến và chính sách biên là tệp trong kho (`infra/cong-api/`), cả cụm khai bằng Docker Compose | — |

---

## 5. Điều kiện của thể lệ

| Điều kiện | Hiện trạng |
|---|---|
| Giấy phép OSI, ghi trong từng tệp mã, có toàn văn | Đạt — `LICENSES.md`, `scripts/kiem_header.py` chạy trong CI |
| Mã nguồn truy cập tự do trên Internet | **Chưa** — kho chuyển công khai trước hạn nộp |
| Có bản phát hành theo phiên bản, định dạng mở | Đạt — 17 bản; bản dự thi `v1.0.0` ở #368 |
| Dựng được từ mã nguồn, có hướng dẫn | Đạt — README mục Cài nhanh; kiểm lại từ tệp phát hành ở #368 |
| Làm rõ thư viện, không sửa mã bên thứ ba | Đạt — `docs/dependencies.md`, `NOTICE` |
| Có bug tracker, nhật ký thay đổi, README | Đạt |
