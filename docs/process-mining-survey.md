# Khảo sát thư viện khai phá quy trình — Không gian I

> **Mục đích**: ghi lại quá trình và kết quả khảo sát thư viện khai phá quy trình (process
> mining) cho không gian `I`, làm căn cứ cho bản ghi quyết định
> [`adr/0007-chon-thu-vien-khai-pha-quy-trinh.md`](adr/0007-chon-thu-vien-khai-pha-quy-trinh.md).
>
> **Issue liên quan**: #48 · **Ngày thực hiện**: 2026-09-28 · **Phạm vi**: khảo sát và chạy
> thử ngoài kho mã, chưa tích hợp vào hệ thống

---

## 1. Mục tiêu và tiêu chí

Mỗi lần hồ sơ đổi trạng thái, engine ghi một dòng vào `event_log`. Khai phá quy trình đọc
nhật ký đó để vẽ lại quy trình **đang thật sự chạy**, rồi so với quy trình **đã thiết kế**
ở [`process-flow.md`](process-flow.md) mục 3 — chỉ ra cạnh lệch chuẩn, vòng lặp và điểm
nghẽn. Đây là vòng phản hồi tự soi quy trình, thành phần chịu lực của tầng `I`
(`CLAUDE.md` mục 4.1).

Khảo sát trả lời hai câu:

1. Nên lắp ghép thư viện nào?
2. Nhật ký hiện tại có đủ dữ liệu cho thư viện đó không, hay phải thêm trường?

| Tiêu chí | Vì sao |
|---|---|
| Giấy phép được OSI công nhận, tương thích MIT | Bảng chấm PoF mục Giấy phép (10 điểm); mảng này có thư viện copyleft mạnh |
| Ngôn ngữ | Ảnh hưởng cách tích hợp: cùng Python với `backend/` hay phải thêm môi trường chạy |
| Định dạng nhật ký đầu vào | Đọc thẳng được bảng `event_log` xuất ra CSV không, hay phải chuyển sang XES |
| Vẽ quy trình thực tế | Sơ đồ đọc được cho người vận hành |
| Đối chiếu quy trình thiết kế | Bắt được cạnh ngoài 24 cạnh thiết kế, và chỉ ra đúng hồ sơ nào lệch |
| Tìm vòng lặp và điểm nghẽn | Hai mẫu lệch chuẩn ở `process-flow.md` mục 6; thời gian nằm ở mỗi trạng thái |
| Tài nguyên | Thời gian chạy và bộ nhớ cho 1.000 hồ sơ, cộng vào ngân sách toàn hệ thống |
| Độ trưởng thành | Phiên bản, nhịp phát hành, số thuật toán có sẵn |

---

## 2. Nhật ký hiện tại và ánh xạ cột

### 2.1. Dữ liệu đã dùng

Bảng `event_log` trong cụm lúc khảo sát còn trống (cụm vừa dựng lại từ đầu), nên dữ liệu
lấy từ bộ sinh nhật ký ảo của #124, chạy ở gốc kho khi cụm đang chạy:

```
python scripts/sinh_nhat_ky_ao.py --ra ..\_scratch\dx-os-lab\thu-48\du-lieu
```

Tham số mặc định, hạt giống `20260924`, nên ai chạy lại cũng ra đúng số liệu dưới đây. Bộ
sinh đọc bộ quy tắc đang chạy — **10 trạng thái, 24 cạnh** — và xuất CSV đúng các cột của
bảng thật (đã đối chiếu bằng `\d event_log` trên cụm).

| Chỉ số | Giá trị |
|---|---|
| Số hồ sơ | 1.000, trong 180 ngày từ 2026-03-01 |
| Số sự kiện | 6.736 (trung bình 6,7 mỗi hồ sơ); cộng 1.000 sự kiện mở đầu là 7.736 |
| Hồ sơ đã kết thúc | 989 — 918 đã đóng, 71 đã hủy; 11 hồ sơ còn dở lúc chốt dữ liệu |
| Mã hoạt động có mặt | 16, cộng `submit` dựng thêm là 17 |

### 2.2. Bảng ánh xạ

Thư viện khai phá quy trình theo chuẩn XES (IEEE 1849) cần ba cột: mã hồ sơ, hoạt động,
thời điểm.

| Cột `event_log` | Trường XES | Ghi chú |
|---|---|---|
| `case_id` | `case:concept:name` | Đủ |
| `activity` | `concept:name` — góc nhìn **hoạt động** | Hiện hành vi người dùng: ai bấm gì |
| `to_state` | `concept:name` — góc nhìn **trạng thái** | Dùng để đối chiếu thiết kế, xem mục 2.3 |
| `timestamp` | `time:timestamp` | `TIMESTAMPTZ`, lưu UTC; CSV ra dạng ISO 8601 có `+00:00` |
| `actor` | `org:resource` | Đủ; tác nhân hệ thống khi leo thang là `sla-watcher` |
| `from_state` | — | Không cần: suy được từ sự kiện trước. Dùng để kiểm nhật ký liền mạch |
| `note`, `changes`, `actor_label` | Thuộc tính sự kiện | Tùy chọn. `changes` tách được "định tuyến lại cùng phòng" — mục 4.6 |
| `requests.request_type_code`, `department_code`, `priority_code` | Thuộc tính hồ sơ `case:*` | Nối theo `case_id` khi cần lọc theo loại, phòng |

### 2.3. Thư viện còn đòi gì mà nhật ký không có

1. **Sự kiện mở đầu.** Tạo hồ sơ không sinh sự kiện (`ARCHITECTURE.md` mục 6), nên sự kiện
   đầu tiên của mỗi hồ sơ là *Phân loại*, và khoảng hồ sơ nằm ở *Đã gửi* lần đầu bị mất.
   Cách xử lý đã được kiến trúc định sẵn: lúc xuất, dựng thêm một sự kiện mở đầu từ
   `requests.created_at`. Khảo sát làm đúng như vậy với mã `submit` và `to_state =
   submitted`
2. **Mã hoạt động dùng chung nhiều cạnh.** `provide-info` đi ba cạnh, `request-info` ba
   cạnh, `cancel` bốn cạnh, `edit-content` hai cạnh. Khai phá theo `activity` cho đồ thị
   **48 cạnh trên 17 hoạt động** — không so được với 24 cạnh thiết kế. Khai phá theo
   `to_state` cho đúng **24 cạnh trên 10 trạng thái**, khớp một-một với bảng `transitions`
3. **Vòng đời hoạt động** (`lifecycle:transition`). Mỗi sự kiện chỉ có một mốc — lúc
   chuyển xong — nên thư viện không tách được "thời gian làm" với "thời gian chờ" trong một
   hoạt động; nút trên sơ đồ thời gian hiện `0ns`. Không thiếu gì cho bài toán này: trạng
   thái của hồ sơ chính là khoảng chờ, và thời gian đó nằm trên cạnh

**Kết luận: nhật ký hiện tại dùng được ngay, không cần thêm trường.** Chỉ cần hai việc ở
bước xuất của tầng `D`: dựng sự kiện mở đầu từ `requests.created_at`, và chọn `to_state`
làm `concept:name` khi đối chiếu thiết kế (giữ `activity` khi xem hành vi).

Nguồn thứ hai về sau là bảng `case_messages` (#128): số lần *Hỏi tiến độ* và thời gian chờ
trả lời chỉ ra điểm nghẽn mà nhật ký trạng thái không thấy (`process-flow.md` mục 6). Bảng
này không vào nhật ký sự kiện và chưa được thử trong khảo sát.

---

## 3. Ứng viên và giấy phép

Giấy phép kiểm ở tệp gốc trong kho mã của ứng viên, và với gói đã cài thì đọc thêm tệp
giấy phép nằm trong gói. Đối chiếu danh sách OSI tại <https://opensource.org/licenses>.

| Ứng viên | Phiên bản | Ngôn ngữ | Giấy phép | Nguồn kiểm | OSI | Hệ quả với dự án MIT |
|---|---|---|---|---|---|---|
| **PM4Py** | `2.7.23.8` (PyPI, 2026-09-01) | Python | AGPL-3.0-or-later; có bán giấy phép thương mại riêng | `LICENSE` nhánh `release` của kho: dòng đầu *GNU AFFERO GENERAL PUBLIC LICENSE*; `pm4py-2.7.23.8.dist-info/licenses/LICENSE` trong gói đã cài: cùng nội dung; `METADATA`: `License-Expression: AGPL-3.0-or-later` | Có | Có điều kiện — chỉ trong dịch vụ tách riêng, mục 6 |
| **pm4js** | `0.0.38` (npm, 2023-10-20); kho đã ở `0.0.39` | JavaScript | BSD-3-Clause | `LICENSE` của kho và của gói trong `node_modules/pm4js`: văn bản BSD ba điều khoản; `package.json`: `"license": "BSD-3-Clause"` | Có | Có, nhưng gói kèm `heapq.js` theo **CC BY-SA 2.5** (tự khai ở `README.THIRD_PARTY.md`) — không phải giấy phép OSI cho mã nguồn |
| **bupaR** | `1.0.1` (CRAN, 2026-01-27); `processmapR` `0.5.8`, `processcheckR` `0.1.5` | R | MIT + tệp `LICENSE` | `DESCRIPTION` trên CRAN của cả ba gói: `License: MIT + file LICENSE`; `LICENSE` của kho `bupaR`: *COPYRIGHT HOLDER: Hasselt University* | Có | Có; nhưng thêm cả môi trường chạy R. Chưa kiểm giấy phép các gói R mà chúng kéo theo |
| **ProM** | `6.15` | Java | Lõi GPL, phần lớn plug-in L-GPL | Kho `ProM-Framework` **không có** tệp `LICENSE` ở gốc; 89 trên 91 kho của tổ chức `promworkbench` không khai giấy phép. Căn cứ là trang <https://promtools.org>: lõi GPL, *"any software that uses the core also needs to be distributed using the GPL license"*; plug-in L-GPL | Có | Có điều kiện. Là ứng dụng máy tính có giao diện, không chạy được như dịch vụ |
| **Celonis**, **Disco** (Fluxicon) | — | — | Thương mại, mã đóng | Trang sản phẩm | **Không** | **Loại** — không phải phần mềm nguồn mở |

Hai điều người sau cần biết:

- **PM4Py tự nhắc giấy phép khi chạy.** Nạp thư viện là nó in khung *"License: AGPL v3 —
  Commercial use requires open-sourcing your application"*, kèm lời mời mua giấy phép
  thương mại. Đó là cách hiểu của nhà phát triển; ràng buộc thật do văn bản AGPL quy định,
  phân tích ở mục 6
- **Giấy phép dễ dãi của gói không bảo đảm mọi tệp trong gói cũng vậy.** pm4js là BSD-3,
  nhưng chính nó khai một tệp lấy từ StackOverflow theo CC BY-SA 2.5

---

## 4. Kết quả chạy thử

### 4.1. Môi trường

Chạy trong thư mục `thu-48\` **ngoài kho mã**, mỗi thư viện một môi trường riêng: PM4Py
trong môi trường ảo Python (`python -m venv .venv`), pm4js trong một thư mục `npm` riêng.
Không cài gì vào container của dự án, không ghi gì vào cơ sở dữ liệu.

| Mục | Giá trị |
|---|---|
| Máy | Intel Core i7-13700HX, 24 luồng, 15,6 GB RAM, Windows 11 Pro |
| PM4Py | `2.7.23.8`, Python `3.13.7`, pandas `3.0.6` |
| pm4js | `0.0.38`, Node.js `24.11.1` |
| Vẽ ảnh | Graphviz `12.2.1` trong container dùng một lần (`alpine:3.22`), vì máy không có lệnh `dot` |

Hai thư viện đọc **cùng một nhật ký**: CSV của bộ sinh, thêm sự kiện mở đầu (mục 2.3).

### 4.2. Đoạn mã chính (PM4Py)

```python
import json
import pandas as pd
import pm4py

su_kien = pd.read_csv("du-lieu/event_log.csv")
ho_so = pd.read_csv("du-lieu/requests.csv")
# Tạo hồ sơ không sinh sự kiện: dựng sự kiện mở đầu từ requests.created_at
mo_dau = pd.DataFrame({"id": 0, "case_id": ho_so["id"], "activity": "submit",
                       "timestamp": ho_so["created_at"], "to_state": "submitted"})
nk = pd.concat([mo_dau, su_kien], ignore_index=True)
nk["timestamp"] = pd.to_datetime(nk["timestamp"], utc=True)
nk = nk.sort_values(["case_id", "timestamp", "id"], kind="stable")
nk["case_id"] = nk["case_id"].astype(str)

# Góc nhìn trạng thái: concept:name = to_state
df = pm4py.format_dataframe(nk, case_id="case_id", activity_key="to_state",
                            timestamp_key="timestamp")
dfg, dau, cuoi = pm4py.discover_dfg(df)                # sơ đồ thực tế
hieu_nang, _, _ = pm4py.discover_performance_dfg(df)   # thời gian trên từng cạnh

# Quy trình thiết kế: 24 cạnh trong quy_tac.json do bộ sinh xuất từ bảng transitions
q = json.load(open("du-lieu/quy_tac.json", encoding="utf-8"))
thiet_ke = {(c["tu"], c["den"]): 1 for c in q["canh"]}
bat_dau = {s["ma"]: 1 for s in q["trang_thai"] if s["bat_dau"]}
ket_thuc = {s["ma"]: 1 for s in q["trang_thai"] if s["ket_thuc"]}
ngoai_thiet_ke = set(dfg) - set(thiet_ke)

luoi, m_dau, m_cuoi = pm4py.convert_to_petri_net(thiet_ke, bat_dau, ket_thuc)
cuoi_ho_so = df.groupby("case:concept:name")["concept:name"].last()
da_xong = df[df["case:concept:name"].isin(cuoi_ho_so[cuoi_ho_so.isin(ket_thuc)].index)]
chan_doan = pm4py.conformance_diagnostics_token_based_replay(da_xong, luoi, m_dau, m_cuoi)
ho_so_lech = [i for i, r in enumerate(chan_doan) if not r["trace_is_fit"]]

# Thời gian nằm ở mỗi trạng thái: từ lúc vào tới sự kiện kế tiếp của cùng hồ sơ
df["roi_di"] = df.groupby("case:concept:name")["time:timestamp"].shift(-1)
df["gio"] = (df["roi_di"] - df["time:timestamp"]).dt.total_seconds() / 3600
nam_lai = df.dropna(subset=["gio"]).groupby("concept:name")["gio"].describe()
```

pm4js làm tương đương bằng `CsvImporter`, `FrequencyDfgDiscovery`, `PerformanceDfgDiscovery`
và `DfgAlignments` trên đồ thị thiết kế dựng từ cùng tệp `quy_tac.json`.

### 4.3. Thời gian chạy và bộ nhớ — 1.000 hồ sơ

| Bước | PM4Py | pm4js |
|---|---|---|
| Nạp thư viện | 1,7–7,0 giây khi đã có bộ đệm; **95 giây lần đầu** sau khi cài (Python biên dịch mã lần đầu) | 4,1 giây |
| Đọc và ánh xạ nhật ký | 0,17 giây | 0,01 giây |
| Ba đồ thị DFG (hoạt động, trạng thái, thời gian) | 0,13 giây | 0,01 giây (tần suất và thời gian) |
| Inductive Miner | 0,50 giây | 0,02 giây |
| Đối chiếu thiết kế | 0,70 giây (phát lại token, 989 hồ sơ) | 0,01 giây (gióng hàng trên DFG) |
| **Bộ nhớ tiến trình (RSS)** | 143 MiB sau khi nạp, **174 MiB** lúc xong | 45 MiB sau khi nạp, **69 MiB** lúc xong |

Đo bằng `time.perf_counter` và `psutil` (Python), `process.hrtime` và
`process.memoryUsage` (Node), mỗi thư viện một tiến trình. Đỉnh cấp phát riêng của phần
phân tích PM4Py đo bằng `tracemalloc` là 21,7 MiB — phần lớn bộ nhớ là chính thư viện và
các gói nó kéo theo (numpy, scipy, pandas, matplotlib, networkx, lxml, cvxopt).

Con số 95 giây chỉ xảy ra một lần trên máy mới cài. Trong ảnh Docker thì biên dịch sẵn lúc
dựng ảnh là tránh được.

### 4.4. Việc 1 — vẽ sơ đồ quy trình thực tế

| Góc nhìn | Kết quả |
|---|---|
| Theo trạng thái (`to_state`) | **10 nút, 24 cạnh** kèm tần suất — đọc được, khớp sơ đồ ở `process-flow.md`. Ảnh đính kèm pull request |
| Theo hoạt động (`activity`) | 17 hoạt động, 48 cạnh — rối vì mã hoạt động dùng chung (mục 2.3) |
| Inductive Miner trên hoạt động | Lưới Petri 27 vị trí, 50 chuyển tiếp — đúng nhưng khó đọc với người vận hành |

Cả hai thư viện cho **cùng 24 cạnh với cùng tần suất**, ví dụ *Đã gửi → Đã phân loại*
1.028 lần, *Đã phân loại → Chờ phòng ban xác duyệt* 1.071 lần, *Chờ phòng ban xác duyệt →
Đang xử lý* 906 lần. Hai cạnh tự trỏ hiện đúng: *Sửa nội dung* ở *Đã gửi* 46 lần, *Nhận
việc về mình* ở *Đang xử lý* 60 lần.

**Đề xuất cho giao diện: vẽ theo góc nhìn trạng thái**, nhãn tiếng Việt tra từ bộ quy tắc.

### 4.5. Việc 2 — đối chiếu với quy trình thiết kế

Trên nhật ký gốc: **0 cạnh ngoài thiết kế, 0 cạnh thiết kế chưa ai đi**; phát lại token
trên lưới thiết kế cho độ khớp 1,0 với cả 989 hồ sơ đã kết thúc.

Kết quả đó là **tất nhiên** — bộ sinh tự kiểm để mọi sự kiện đi đúng một cạnh của bộ quy
tắc — nên nó không chứng minh thư viện bắt được lệch chuẩn. Vì vậy khảo sát **cài lệch có
chủ đích** vào 8 hồ sơ đã kết thúc (chọn ngẫu nhiên, hạt giống `48`) rồi xem thư viện có
bắt đúng không:

| Kiểu cài | Hồ sơ | Cạnh lạ sinh ra |
|---|---|---|
| Bỏ bước *Hoàn tất* | 238, 429, 665, 673, 826 | `in-progress → closed` |
| Trả về phòng ban sau khi đã nhận — mẫu thứ hai ở `process-flow.md` mục 6 | 416, 652, 908 | `in-progress → awaiting-acceptance` |

| | PM4Py | pm4js |
|---|---|---|
| Cạnh lạ tìm thấy | Đúng hai cạnh, đếm 5 và 3 | Đúng hai cạnh |
| Hồ sơ không khớp thiết kế | **Đúng 8 hồ sơ đã cài**, không báo nhầm hồ sơ nào | **Đúng 8 hồ sơ đã cài**, 981/989 khớp |

Một lỗi của chính phép thử, đã sửa: bản đầu chọn ngẫu nhiên trong mọi hồ sơ đã đóng, trúng
một hồ sơ đóng thẳng ở bước điều phối (*Đóng hồ sơ, không phòng nào nhận*) — không có bước
*Hoàn tất* để bỏ, nên không có gì lệch. Bản sửa chỉ chọn hồ sơ có đi qua *Hoàn tất*.

**Một giới hạn của pm4js**: phát lại token trên lưới Petri chuyển từ đồ thị thiết kế báo
**cả 989 hồ sơ không khớp**, kể cả hồ sơ đúng luật. Lưới đó có nhiều chuyển tiếp trùng nhãn
(mỗi cạnh đi vào một trạng thái là một chuyển tiếp mang tên trạng thái đó); PM4Py chọn đúng
chuyển tiếp đang bật được, pm4js thì không. Gióng hàng trên DFG của pm4js cho kết quả đúng
như bảng trên.

### 4.6. Việc 3 — vòng lặp định tuyến sai

Mẫu `classified → awaiting-acceptance → rejected-by-department → classified`:

| Cách đếm | Kết quả |
|---|---|
| Theo cạnh *Từ chối vì sai chuyên môn* — mỗi lần từ chối là một vòng | **127 hồ sơ** (12,7 %): 120 hồ sơ một vòng, 7 hồ sơ hai vòng |
| Theo đúng chuỗi bốn trạng thái liền nhau | 119 hồ sơ — thiếu 8 hồ sơ |
| Hồ sơ được định tuyến từ hai lần | 120 |
| Hồ sơ đổi phòng ban thật từ hai lần, theo cột `changes` | 100 |

Tám hồ sơ lọt khỏi cách đếm theo chuỗi liền nhau vì phòng ban **hỏi thêm rồi mới từ chối**:
`awaiting-acceptance → awaiting-info → awaiting-acceptance → rejected-by-department`, ví dụ
hồ sơ 260. Vậy **phải đếm theo cạnh từ chối**, không theo chuỗi trạng thái cố định.

Hai con số cuối cho thấy giá trị của cột `changes` (#100): trong 120 hồ sơ được định tuyến
lại, 20 hồ sơ **quay về đúng phòng cũ** — phòng ban không đổi. Chỉ nhìn chuỗi trạng thái thì
không phân biệt được hai trường hợp này.

### 4.7. Việc 4 — điểm nghẽn

Thời gian hồ sơ nằm ở mỗi trạng thái, tính từ lúc vào tới sự kiện kế tiếp của cùng hồ sơ:

| Trạng thái | Số lần vào | Trung bình (giờ) | Trung vị | Phân vị 90 | Giả định của bộ sinh |
|---|---|---|---|---|---|
| Chờ bổ sung thông tin | 340 | **17,21** | 11,57 | 40,73 | 18 |
| Hoàn tất | 968 | 13,78 | 9,26 | 32,61 | 14 |
| Đang xử lý | 1.446 | 11,34 | 5,21 | 29,90 | Theo ngưỡng SLA của loại yêu cầu |
| Chờ phòng ban xác duyệt | 1.186 | 4,83 | 3,38 | 10,91 | 5 |
| Đã gửi | 1.200 | 2,95 | 2,11 | 6,63 | 3 |
| Đã leo thang | 300 | 2,70 | 1,89 | 6,09 | 2,5 |
| Bị phòng ban từ chối | 134 | 1,90 | 1,22 | 4,50 | 2 |
| Đã phân loại | 1.162 | 1,45 | 1,01 | 3,21 | 1,5 |

Cạnh chậm nhất trên sơ đồ thời gian của PM4Py: *Đang xử lý → Đã leo thang* trung bình 21,7
giờ, rồi ba cạnh rời *Chờ bổ sung thông tin* (15,7–18,9 giờ) và *Hoàn tất → Đang xử lý*
(mở lại) 16,9 giờ.

**Đọc đúng con số này**: dữ liệu là dữ liệu ảo, nên bảng trên chứng minh thư viện **đọc lại
đúng** giả định thời gian chờ của bộ sinh (cột cuối, trong phạm vi sai số mẫu), chưa phải
phát hiện nghiệp vụ. Điểm nghẽn thật chỉ có khi chạy trên nhật ký của hệ thống đang vận
hành.

---

## 5. So sánh

| Tiêu chí | PM4Py | pm4js | bupaR | ProM |
|---|---|---|---|---|
| Giấy phép | AGPL-3.0-or-later | BSD-3-Clause, kèm một tệp CC BY-SA 2.5 | MIT | Lõi GPL, plug-in L-GPL |
| Ngôn ngữ | Python — cùng `backend/` | JavaScript | R | Java |
| Đầu vào | DataFrame, CSV, XES | CSV, XES | Đối tượng `eventlog` của R | Chưa kiểm |
| Vẽ quy trình | Có, **đã chạy** | Có, **đã chạy** | Có (`processmapR`) — chưa chạy | Chưa kiểm |
| Đối chiếu thiết kế | Phát lại token — **8/8** | Gióng hàng trên DFG — **8/8**; phát lại token sai với lưới trùng nhãn | Kiểm theo luật (`processcheckR`) — chưa chạy | Chưa kiểm |
| Vòng lặp, điểm nghẽn | Có — đo được | Có — đo được | Chưa kiểm | Chưa kiểm |
| Bộ nhớ, 1.000 hồ sơ | 174 MiB | 69 MiB | Chưa đo | Chưa đo |
| Độ trưởng thành | Nhiều thuật toán, phát hành 2026-09-01 | `0.0.x`, bản npm gần nhất 2023-10 | `1.0.1`, CRAN 2026-01 | `6.15`, lâu đời |
| Chạy như dịch vụ | Được, trong container Python | Được, trong container Node | Được, cần thêm R | **Không** — ứng dụng có giao diện |

---

## 6. Đề xuất và nguồn

### 6.1. Đề xuất

**Chọn PM4Py `2.7.23.8`, chạy trong một dịch vụ khai phá tách riêng**, giao tiếp với phần còn
lại qua HTTP. Chi tiết và ranh giới giấy phép ở ADR-0007.

- **Nhiều thuật toán nhất và đã chạy đủ bốn việc** của issue, kể cả đối chiếu thiết kế đúng
  8/8 bằng phát lại token trên chính lưới mà pm4js xử lý sai
- **Cùng Python với dịch vụ ứng dụng** — nhóm không phải thêm ngôn ngữ để bảo trì
- **Còn được phát triển tích cực** — bản mới nhất phát hành 2026-09-01

**Ranh giới giấy phép.** AGPL buộc PM4Py nằm trong một dịch vụ riêng: thư mục và container
riêng là nơi duy nhất `import pm4py`; dịch vụ ứng dụng MIT chỉ gọi nó qua HTTP. Chiều MIT
sang AGPL là tương thích — danh sách giấy phép của GNU ghi giấy phép MIT (Expat) *"compatible
with the GNU GPL"* — nên các tệp của nhóm vẫn giữ header MIT. Dịch vụ khai phá khi phục vụ
người dùng qua mạng thì chịu điều 13 của AGPL: phải cho người dùng lấy được mã nguồn; kho mã
đã công khai nên đáp ứng sẵn. Câu *"không nhúng thư viện vào mã nguồn dự án"* ở `CLAUDE.md`
mục 5.2, `ARCHITECTURE.md` mục 3.3 và `dependencies.md` phải sửa cho khớp khi ADR được chấp
nhận.

> **Cập nhật 2026-11-10 (#340).** Đoạn trên ghi đề xuất lúc khảo sát. Khi xác nhận ADR-0007, giảng
> viên đặt điều kiện mô tả kho theo mô hình hai giấy phép: cả thư mục `services/khai-pha/`, kể cả mã
> của nhóm, nay theo AGPL-3.0-or-later; màn Quy trình thực tế dẫn tới mã nguồn của dịch vụ cho điều 13.
> Xem `LICENSES.md` ở gốc kho.

**Phương án lùi: pm4js** — nếu giảng viên muốn tránh hẳn copyleft. Đổi lại ít thuật toán
hơn, bản `0.0.x`, thêm Node vào tầng `I`, và phải xử lý tệp CC BY-SA 2.5 đi kèm.

**Chưa thử**: bupaR và ProM chỉ kiểm giấy phép, chưa dựng. Bảng `case_messages` chưa đưa vào
phân tích. Toàn bộ số liệu chạy trên nhật ký ảo — cần chạy lại khi có nhật ký thật.

### 6.2. Nguồn

| Nguồn | Đường dẫn |
|---|---|
| PM4Py — kho mã và giấy phép | <https://github.com/process-intelligence-solutions/pm4py/blob/release/LICENSE> |
| PM4Py — gói và phiên bản | <https://pypi.org/project/pm4py/> |
| PM4Py — trang giấy phép thương mại | <https://processintelligence.solutions/pm4py> |
| pm4js — giấy phép | <https://github.com/pm4js/pm4js-core/blob/main/LICENSE> |
| pm4js — thành phần bên thứ ba | <https://github.com/pm4js/pm4js-core/blob/main/README.THIRD_PARTY.md> |
| pm4js — gói npm | <https://registry.npmjs.org/pm4js> |
| bupaR — giấy phép | <https://github.com/bupaverse/bupaR/blob/master/LICENSE> |
| bupaR, processmapR, processcheckR trên CRAN | <https://cran.r-project.org/package=bupaR> · <https://cran.r-project.org/package=processmapR> · <https://cran.r-project.org/package=processcheckR> |
| ProM — trang chính, giấy phép | <https://promtools.org/> |
| ProM — kho mã lõi | <https://github.com/promworkbench/ProM-Framework> |
| Celonis, Disco | <https://www.celonis.com/> · <https://fluxicon.com/disco/> |
| Danh sách giấy phép OSI | <https://opensource.org/licenses> |
| AGPL-3.0 | <https://www.gnu.org/licenses/agpl-3.0.html> |
| MIT (Expat) tương thích GPL | <https://www.gnu.org/licenses/license-list.html#Expat> |
| Chuẩn XES | <https://www.xes-standard.org/> · <https://standards.ieee.org/ieee/1849/5722/> |
