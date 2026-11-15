---
title: Công cụ kiểm chứng
description: Dựng cụm thử cách ly, dò đăng nhập thật, tạo hồ sơ thử theo từng trạng thái và chạy phép thử đột biến — để người khác chạy lại được bằng chứng chất lượng.
sidebar:
  order: 4
---

Thư mục `scripts/kiem_chung/` chứa bốn công cụ mà nhóm dùng để kiểm chứng từng thay đổi: không chỉ
chạy bộ kiểm thử xanh, mà còn **đăng nhập thật** vào một cụm riêng và **cố ý làm hỏng mã** để xem
bộ kiểm thử có thật sự bắt được không. Có chúng trong kho thì ai cũng chạy lại được, kể cả người chưa
từng làm việc với dự án.

| Công cụ | Làm gì |
|---|---|
| `cum_thu` | Dựng, hỏi trạng thái, gỡ một cụm thử cách ly chạy cạnh cụm đang dùng |
| `do_dang_nhap` | Đi trọn luồng đăng nhập OIDC như trình duyệt, mở trang, kiểm chuỗi mong đợi |
| `tao_ho_so_thu` | Tạo hồ sơ nằm ở từng trạng thái của bộ quy tắc, qua engine |
| `dot_bien` | Phép thử đột biến: cố ý làm hỏng một chỗ trong mã, bài kiểm thử phải đỏ |

Không công cụ nào viết cứng tên trạng thái, vai trò hay phòng ban: mọi thứ được đọc từ cơ sở dữ liệu
của cụm, nên đổi bộ quy tắc thì công cụ vẫn chạy đúng.

## Yêu cầu máy

- Docker (Docker Desktop, hoặc Docker Engine 24 trở lên kèm Compose v2), cùng tài nguyên như khi
  [cài cụm chính](../../cai-dat/cai-dat/). Cụm thử chạy **thêm** cạnh cụm đang dùng, nên máy cần đủ
  bộ nhớ cho cả hai; thêm `--khong-superset` để nhẹ hơn
- Python 3.10 trở lên. Công cụ chỉ dùng thư viện chuẩn, không cần `pip install` gì

Mọi lệnh chạy **ở gốc kho mã**, dạng `python -m scripts.kiem_chung.<tên công cụ>`. Chạy trên
PowerShell, Git Bash hay Linux đều được. Trên Windows nên thêm `-X utf8` sau `python` để tiếng Việt có
dấu không vỡ.

## Đường nhanh: tái hiện một lượt kiểm chứng

Năm lệnh, theo thứ tự, trên máy sạch:

```bash
python -m scripts.kiem_chung.cum_thu dung --khong-superset
python -m scripts.kiem_chung.do_dang_nhap --tai-khoan an.nguyen --tim "Chào"
python -m scripts.kiem_chung.tao_ho_so_thu --moi-trang-thai
python -m scripts.kiem_chung.dot_bien scripts/kiem_chung/vi_du/actor_not_requester.json
python -m scripts.kiem_chung.cum_thu go --xoa-anh
```

Lệnh đầu dựng cụm (lần đầu mất vài phút để tải và dựng ảnh), lệnh thứ hai đăng nhập thật, lệnh thứ ba
tạo hồ sơ ở mọi trạng thái, lệnh thứ tư chạy phép thử đột biến và phải báo mọi đột biến **BẮT**, lệnh
cuối gỡ sạch.

## 1. Cụm thử cách ly — `cum_thu`

Cụm chính (`docker compose up` theo README) và cụm thử là hai cụm đầy đủ độc lập. Cụm thử khác ở
chỗ nó không đụng được tới cụm kia:

| Thứ | Cụm chính | Cụm thử (mặc định) |
|---|---|---|
| Tên dự án Compose | `dx-os-lab` | `dxlab-thu` |
| Tên container | `dxlab-backend`… | `thu-backend`… |
| Ảnh tự dựng | `dxlab-backend:<phiên bản>`, `dxlab-frontend:…`, `dxlab-superset:…` | cùng ba ảnh, nhãn `cum-thu` |
| Cổng | trong `infra/.env.example` | cổng đó **cộng 20000**: 23000 (cổng người dùng), 28080 (Keycloak), 29080 (cổng API), 28088, 28333 |
| Dữ liệu | volume `dx-os-lab_*` | volume `dxlab-thu_*` |

Nhãn ảnh riêng là chỗ quan trọng nhất: tên ảnh mặc định dùng chung giữa hai cụm, nên dựng cụm thử
mà không đổi nhãn sẽ **ghi đè ảnh của cụm đang dùng**. Công cụ từ chối các tham số làm cụm thử trùng
tên dự án, tiền tố container, nhãn ảnh hay cổng với cụm chính.

```bash
python -m scripts.kiem_chung.cum_thu dung                  # dựng, chờ sẵn sàng, in địa chỉ
python -m scripts.kiem_chung.cum_thu dung --khong-superset # bỏ Superset cho nhẹ máy
python -m scripts.kiem_chung.cum_thu trang-thai            # đang chạy hay không, ở đâu
python -m scripts.kiem_chung.cum_thu go --xoa-anh          # gỡ: xóa dữ liệu và ba ảnh nhãn riêng
```

`dung` làm lần lượt: sinh tệp biến môi trường `infra/.env.cum-thu` từ `infra/.env.example` (tệp mẫu
không bị sửa; tệp sinh ra nằm trong `.gitignore`), chạy một lệnh `docker compose up -d --build` với tệp
ghi đè `infra/docker-compose.cum-thu.yml`, chờ dịch vụ ứng dụng báo khỏe, rồi thêm địa chỉ cổng của
cụm thử vào danh sách chuyển hướng của client đăng nhập `dx-portal` trong Keycloak (không có bước này
Keycloak từ chối đăng nhập ở cổng 23000). Cuối cùng in bảng địa chỉ.

`go` in ra **chính xác lệnh sẽ chạy** trước khi chạy: `down -v` chỉ trên dự án Compose của cụm thử,
nên chỉ xóa container, mạng và volume của cụm thử; `--xoa-anh` xóa ba ảnh theo đúng tên.

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `--tien-to` | `thu-` | Tiền tố tên container |
| `--nhan` | `cum-thu` | Nhãn ba ảnh tự dựng |
| `--du-an` | `dxlab-thu` | Tên dự án Compose |
| `--dich-cong` | `20000` | Số cộng vào mọi cổng của `.env.example` |
| `--tep-env` | `infra/.env.cum-thu` | Nơi ghi tệp biến môi trường sinh ra |
| `--khong-superset` | tắt | (chỉ `dung`) Không dựng Superset |
| `--xoa-anh` | tắt | (chỉ `go`) Xóa luôn ba ảnh nhãn riêng |

Muốn chạy hai cụm thử cùng lúc thì đổi cả bốn: `--du-an`, `--tien-to`, `--nhan` và `--dich-cong`.

## 2. Dò đăng nhập thật — `do_dang_nhap`

Đăng nhập một tài khoản mẫu qua **đúng luồng OIDC của cổng**: bấm đăng nhập, điền biểu mẫu của
Keycloak, quay về cổng bằng cookie phiên thật. Không tự đúc cookie — một lỗi đăng nhập từng bị che
chính vì kiểm thử tự đúc cookie. Sau đó mở các trang và kiểm chúng có chứa chuỗi mong đợi.

```bash
# Người gửi: trang đích chứa câu chào; trang Gửi yêu cầu liệt kê loại "Sự cố thiết bị"
python -m scripts.kiem_chung.do_dang_nhap --tai-khoan an.nguyen --tim "Chào" \
    --trang "yeu-cau/moi::Sự cố thiết bị"

# Điều phối viên: mở hàng đợi điều phối
python -m scripts.kiem_chung.do_dang_nhap --tai-khoan binh.tran --tim "Chào" --trang "dieu-phoi::Hàng đợi điều phối"
```

| Tham số | Ý nghĩa |
|---|---|
| `--tai-khoan` | Bắt buộc. Tên đăng nhập của tài khoản mẫu (xem README) |
| `--tim "a,b"` | Các chuỗi phải có trên mỗi trang, kể cả trang đích ngay sau đăng nhập |
| `--trang đường-dẫn` | Mở thêm một trang (dùng nhiều lần), viết không có dấu `/` đầu — Git Bash tự đổi tham số mở đầu bằng `/` thành đường dẫn trên máy. `đường-dẫn::a,b` đòi riêng chuỗi `a`, `b` trên trang đó |
| `--cong` | Địa chỉ cổng người dùng. Mặc định `http://localhost:23000`, hoặc biến `CONG` |
| `--mat-khau` | Mặc định biến `MAT_KHAU`, rồi mật khẩu mẫu công khai trong README |
| `--in-chu N` | In N ký tự chữ đầu của mỗi trang |
| `--tho` | So chuỗi với HTML thô thay vì chữ nhìn thấy |

Mã thoát: `0` đạt · `1` đăng nhập được nhưng một trang lỗi hay thiếu chuỗi · `2` không đăng nhập được
(sai tài khoản, Keycloak từ chối, cổng không đặt cookie phiên). Dùng được trong tập lệnh hay quy trình
tích hợp liên tục.

:::caution
Mật khẩu mẫu là giá trị công khai của realm dựng thử. Chỉ dùng công cụ này trên cụm thử.
:::

## 3. Hồ sơ thử theo từng trạng thái — `tao_ho_so_thu`

Tạo hồ sơ **đang nằm ở** một trạng thái đích, để kiểm từng màn hình hay từng ràng buộc mà khỏi bấm tay
cả quy trình.

```bash
python -m scripts.kiem_chung.tao_ho_so_thu --moi-trang-thai   # mỗi trạng thái một hồ sơ
python -m scripts.kiem_chung.tao_ho_so_thu --trang-thai <mã>  # chỉ trạng thái đó (nhiều lần được)
```

Cách làm, để biết kết quả đáng tin tới đâu:

- Hồ sơ đi **qua engine** (`create_case`, rồi `perform_transition` từng bước) chạy trong container dịch
  vụ ứng dụng của cụm thử. Không INSERT thẳng vào bảng hồ sơ hay nhật ký, nên mỗi hồ sơ có đủ nhật ký
  sự kiện và mọi ràng buộc Poka-yoke đã chạy
- Đường đi tìm bằng duyệt đồ thị các cạnh **của người** trong bộ quy tắc đang bật. Tác nhân mỗi bước
  dựng từ vai trò đi được cạnh đó; người thao tác khác người gửi (có ràng buộc cấm điều phối hồ sơ của
  chính mình); trường phải nhập (mức ưu tiên, phòng ban…) lấy giá trị mặc định từ dữ liệu; cạnh đòi ghi
  chú thì có ghi chú
- Đường ngắn nhất không đi được (ví dụ ràng buộc "quay về đúng bước trước") thì thử đường khác
- Trạng thái nào engine không cho tới được thì **báo rõ là không tạo được và vì sao**, kèm lời từ chối
  của engine. Với bộ quy tắc mẫu, trạng thái *Đã leo thang* chỉ bước hệ thống (quá hạn) dẫn tới, nên
  được liệt kê ở mục KHÔNG TẠO ĐƯỢC
- Hồ sơ mang tiêu đề bắt đầu bằng `[Thử]`. Cụm đã có hồ sơ **không** mang tiền tố đó thì công cụ dừng,
  trừ khi thêm `--cho-tron` (chỉ khi chắc là cụm thử). Kịch bản e2e ở dưới gửi một hồ sơ không mang
  tiền tố, nên chạy công cụ này **trước** e2e, hoặc thêm `--cho-tron`

Người gửi mặc định là tài khoản `an.nguyen`; định danh của họ được hỏi từ Keycloak của cụm thử, nên
đăng nhập tài khoản đó vào cổng sẽ thấy các hồ sơ thử trong danh sách của mình. Đổi bằng `--nguoi-gui`;
đổi loại yêu cầu bằng `--loai`.

## 4. Phép thử đột biến — `dot_bien`

Bộ kiểm thử xanh chưa chứng minh nó canh được gì. Phép thử đột biến kiểm điều đó: **cố ý làm hỏng
một chỗ** trong mã, chạy lại các bài liên quan. Bài đỏ nghĩa là đột biến bị **BẮT** — tốt. Bài vẫn xanh
nghĩa là đột biến **SỐNG** — có hành vi mà không bài nào canh, và cần thêm hay siết bài kiểm thử.

```bash
python -m scripts.kiem_chung.dot_bien scripts/kiem_chung/vi_du/actor_not_requester.json
```

Ví dụ kèm kho thử ràng buộc `actor_not_requester` trong `backend/app/rules/guards.py` (điều phối viên
không tự điều phối hồ sơ do chính mình gửi) bằng năm đột biến; ba bài kiểm thử trong
`backend/tests/test_coordination.py` phải bắt cả năm. Đầu ra mẫu:

```text
GỐC           | 3 passed, 1 warning in 1.68s
BẮT           | ràng buộc không bao giờ chặn (điều kiện luôn sai) | 1 failed, 1 warning in 0.74s
…
SAU KHI TRẢ   | 1 tệp trong container trùng bản trong kho (so bảng băm sha256)
Đột biến: 5 · BẮT 5 · SỐNG 0 · BỎ 0 · LỖI 0
```

Mỗi đột biến diễn ra thế này: chép tệp đã đổi vào container dịch vụ ứng dụng của cụm thử, chạy `pytest`
có giới hạn giờ, rồi **luôn trả tệp gốc** (kể cả khi lỗi hay bị ngắt; cuối cùng so bảng băm để chắc đã
trả). Tệp trong kho không bao giờ bị sửa. Bài chạy quá giờ — đột biến bỏ khóa có thể làm bài treo — thì
container được khởi động lại và đột biến tính là bị bắt.

### Viết phép thử cho một ràng buộc khác

Tạo tệp JSON (hoặc tệp Python khai hai biến `BAI` và `DOT_BIEN`):

```json
{
  "mo_ta": "Một dòng nói phép thử này canh gì",
  "bai": ["tests/test_x.py::test_a", "tests/test_x.py::test_b"],
  "dot_bien": [
    {
      "ten": "tên đột biến",
      "tep": "backend/app/rules/guards.py",
      "goc": "đoạn chữ xuất hiện đúng một lần trong tệp",
      "thay": "chữ thế vào"
    }
  ]
}
```

- `bai`: đường dẫn tính từ `backend/`, đúng dạng đối số của `pytest`
- `goc` phải xuất hiện **đúng một lần** trong tệp, nếu không đột biến bị đánh dấu BỎ (và coi là lỗi)
- Chọn đột biến theo cách một người sửa sai thật sự: đổi `==` thành `!=`, bỏ một điều kiện, đăng ký
  nhầm hàm, đổi nội dung thông báo. Mỗi đột biến nên làm hỏng **một** hành vi
- Thêm một đột biến chỉ đổi chữ trong chú thích để thấy bộ chạy báo **SỐNG** (thử một lần rồi bỏ đi)

Bộ chạy cần cụm thử đang chạy và bộ bài gốc xanh hoàn toàn (bài bị bỏ qua không tính). Mã thoát: `0`
mọi đột biến bị bắt · `1` còn đột biến sống, mô tả sai hay không trả được tệp gốc · `2` bộ bài gốc
không xanh. Tham số: `--container` (mặc định `thu-backend`), `--gioi-han` giây mỗi lượt (mặc định 180),
`--chi "chuỗi"` chỉ chạy đột biến có tên chứa chuỗi đó.

## 5. Kiểm tra giao diện trên cụm thử

Kịch bản [Kiểm thử giao diện](../kiem-thu-giao-dien/) trong `e2e/` chạy được trên cụm thử bằng cách trỏ
biến `CONG` vào cổng của nó. Đứng ở thư mục `e2e/`:

```bash
npm ci
npm run cai-trinh-duyet            # chỉ lần đầu
CONG=http://localhost:23000 npm run kiem
```

Trên PowerShell: `$env:CONG = "http://localhost:23000"; npm run kiem`. Máy đã có Chrome thì thêm
`KENH=chrome` để khỏi tải Chromium.

Bài kiểm trang *Báo cáo* (#305) cần Superset, nên **dựng cụm thử không kèm `--khong-superset`** khi
chạy e2e; bỏ Superset thì đúng các bài đó đỏ, các bài khác vẫn đạt.

## An toàn khi dùng

- Mọi công cụ chỉ nhắm vào cụm thử. `cum_thu` từ chối tham số trùng tên với cụm chính; `dot_bien` từ
  chối container có tiền tố `dxlab-`; `tao_ho_so_thu` dừng khi gặp hồ sơ không phải hồ sơ thử
- Tệp biến môi trường `infra/.env.cum-thu` và mật khẩu mẫu chỉ có ý nghĩa trên cụm thử. Đừng dùng
  chúng để triển khai thật
- Hồ sơ thử không gỡ riêng ra được (nhật ký sự kiện chỉ ghi thêm). Muốn sạch lại thì gỡ cả cụm thử
  bằng `cum_thu go`
