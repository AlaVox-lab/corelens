# ADR-0008: Cơ sở dữ liệu véc-tơ và mô hình ngôn ngữ cục bộ cho không gian I

| Mục | Giá trị |
|---|---|
| Trạng thái | Đã chấp nhận (2026-11-08) — đợt #316/#317 cài phần sinh văn bản; #319 cài nhúng véc-tơ và pgvector |
| Ngày | 2026-10-10 |
| Không gian kiến trúc | `I` |
| Issue liên quan | #47 · #316 · #317 · #319 |
| Người quyết định | Navigator (`AlaVox-lab`) chấp nhận ngày 2026-11-08 |

---

## Bối cảnh

Tầng `I` cần hai năng lực cho các gợi ý đã định ở `ARCHITECTURE.md` mục 2.2:

1. **Truy xuất tri thức** — tìm bài hướng dẫn nội bộ gần nghĩa nhất với câu hỏi, làm nguồn cho
   nháp trả lời. Cần nơi lưu và tìm véc-tơ
2. **Sinh gợi ý** — gợi ý loại yêu cầu (`suggested_category`), soạn nháp câu trả lời. Cần một mô
   hình ngôn ngữ và cách gọi nó

Ràng buộc:

1. **Giấy phép** — bảng chấm PoF mục Giấy phép (10 điểm). Mảng này nhiều sản phẩm "nguồn mở một
   phần"; giấy phép của **trọng số mô hình** phải kiểm riêng với phần mềm chạy nó
2. **Chạy được với mô hình cục bộ**, không phụ thuộc mạng ngày trình diễn (`CLAUDE.md` mục 4.3,
   lý do thứ ba), và có đường dự phòng khi mô hình lỗi
3. **AI chỉ ghi trường gợi ý** — đầu ra phải nằm trong tập giá trị hợp lệ, người có thẩm quyền
   xác nhận
4. **Ít dịch vụ, dựng bằng một lệnh trên máy sạch** — bảng chấm PoF mục Dựng từ mã nguồn (10
   điểm); `ARCHITECTURE.md` mục 3.2 đã nêu ưu tiên phần mở rộng véc-tơ ngay trên PostgreSQL
5. **Thứ tự H → P → D → I** (`CLAUDE.md` mục 3.1) — bản ghi này chọn công nghệ, chưa tích hợp

Quá trình khảo sát, sáu phép thử có đáp án biết trước, số liệu đo và nguồn ghi trong
[`../vector-llm-survey.md`](../vector-llm-survey.md). Lượt đầu (kiểm giấy phép, ảnh chứa) do
Nguyễn Thanh Nguyên thực hiện; lượt đo do navigator chạy lại trên máy khác vì đĩa Docker của máy
đầu có dấu hiệu hỏng.

---

## Các phương án đã cân nhắc

### Lưu véc-tơ

#### Phương án A1 — pgvector `0.8.7` (phần mở rộng PostgreSQL)

| Mục | Nội dung |
|---|---|
| Giấy phép | Kiểu PostgreSQL License — tệp `LICENSE` mở đầu *Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group*; có trong ảnh tại `/usr/share/doc/pgvector/LICENSE` |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | 194 MiB sau phép thử — **không thêm dịch vụ**, chạy trong PostgreSQL đang có |
| Khả năng đóng gói bằng container | Ảnh chính thức `pgvector/pgvector:0.8.7-pg16-bookworm`, 152 MiB nén; chỉ có thẻ Debian, cụm chính đang dùng `postgres:16-alpine` |
| Độ khó tích hợp | Thấp — truy vấn là câu SQL qua `psycopg` đã có |

**Ưu điểm**

- Phép A: top-3 trùng vét cạn 20/20. Phép B: quét chính xác 21 ms mỗi câu ở 10.000 véc-tơ 1024
  chiều, recall 1,0; HNSW đạt recall 1,0 ở `ef_search` 100
- Véc-tơ nằm cạnh dữ liệu hồ sơ: một nguồn sự thật, một bản sao lưu, cùng giao dịch

**Nhược điểm**

- Đổi ảnh PostgreSQL của cụm chính
- HNSW mặc định (`ef_search` 40) recall thấp trên dữ liệu không có cấu trúc — phải chỉnh nếu dùng chỉ mục

#### Phương án A2 — Qdrant `1.19.2`

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 — tệp `LICENSE` ở kho; ảnh **không có** tệp `LICENSE`, SBOM trong ảnh khai `Apache-2.0` |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | 170–310 MiB; **thêm một dịch vụ** |
| Khả năng đóng gói bằng container | Ảnh chính thức, 71 MiB nén |
| Độ khó tích hợp | Trung bình — thêm máy khách `qdrant-client` |

**Ưu điểm**: kết quả phép A 20/20; truy vấn nhanh. **Nhược điểm**: thêm dịch vụ; ở tập nhỏ mặc
định **không dựng HNSW** (`indexing_threshold` 10.000 KB) và tìm chính xác dưới
`full_scan_threshold` — lợi thế chỉ mục không có tác dụng ở quy mô dự án.

#### Phương án A3 — Chroma `1.5.9`

| Mục | Nội dung |
|---|---|
| Giấy phép | Apache-2.0 — tệp `LICENSE` ở kho; ảnh không có tệp `LICENSE`, không có nhãn OCI |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | 135 MiB; **thêm một dịch vụ**; ảnh 826 MB giải nén |
| Độ khó tích hợp | Trung bình — thêm máy khách `chromadb-client` |

**Nhược điểm thêm**: ảnh thẻ `1.5.9` tự báo phiên bản `1.4.4`, API báo `1.0.0` — chưa rõ lý do;
HNSW mặc định recall 0,50 ở phép B.

### Chạy mô hình cục bộ

#### Phương án B1 — llama.cpp server

| Mục | Nội dung |
|---|---|
| Giấy phép | MIT — tệp `LICENSE` mở đầu *MIT License Copyright (c) 2023-2026 The ggml authors*; ảnh không kèm tệp, nhãn OCI trỏ đúng kho |
| Được OSI công nhận | Có |
| Tương thích với MIT | Có |
| Tài nguyên khi chạy | Sinh văn bản 1,21 GiB, nhúng 1,57 GiB (hai tiến trình) |
| Khả năng đóng gói bằng container | Ảnh chính thức `ghcr.io/ggml-org/llama.cpp:server`, chỉ CPU, **297 MiB nén** |
| Độ khó tích hợp | Thấp — điểm cuối kiểu OpenAI `/v1/chat/completions`, `/v1/embeddings`; hỗ trợ ràng buộc đầu ra bằng JSON schema |

#### Phương án B2 — Ollama `0.40.1`

Giấy phép MIT, cũng có điểm cuối kiểu OpenAI. **Không chọn**: ảnh mặc định **3,6 GiB nén** vì kèm
thư viện GPU — gấp khoảng mười hai lần llama.cpp server, đi ngược tiêu chí dựng trên máy sạch; chưa
tìm thấy ảnh chỉ CPU.

### Mô hình (trọng số)

| Vai trò | Mô hình | Giấy phép | Kiểm tận gốc |
|---|---|---|---|
| Sinh văn bản | `Qwen/Qwen2.5-1.5B-Instruct-GGUF`, `q4_k_m`, 1,12 GB | Apache-2.0 | Tệp `LICENSE` trong kho |
| Nhúng véc-tơ | `Qwen/Qwen3-Embedding-0.6B-GGUF`, `Q8_0`, 0,64 GB | Apache-2.0 | Kho không có tệp `LICENSE`; thẻ mô hình của kho GGUF và kho gốc đều ghi `license: apache-2.0` |

Hai tệp đã đối chiếu SHA-256 với giá trị Hugging Face công bố. Họ mô hình mang giấy phép riêng của
nhà phát triển (giấy phép cộng đồng của Llama, điều khoản của Gemma) **không xét** — không thuộc
danh sách OSI.

### Khung LLM

#### Phương án C1 — Không dùng khung: gọi thẳng HTTP và SQL

`httpx==0.28.1` và `psycopg[binary]==3.3.5` **đã có** trong `backend/requirements.txt` — không
thêm phụ thuộc nào. 10 gói, 39 MB, nạp 0,10 giây.

#### Phương án C2, C3, C4 — LangChain `1.4.4` (MIT), LlamaIndex `0.14.25` (MIT), Haystack `3.3.0` (Apache-2.0)

Cả ba đạt giấy phép. Với gói tối thiểu cho pgvector và điểm cuối kiểu OpenAI: LangChain 54 gói,
257 MB, nạp 0,95 s; LlamaIndex 74 gói, 302 MB, 1,24 s; Haystack 47 gói, 195 MB, 0,38 s.

### Bị loại vì giấy phép

| Ứng viên | Giấy phép | Kết luận |
|---|---|---|
| MongoDB Community | SSPL-1 | **Loại** — không thuộc danh sách OSI |
| Elasticsearch | AGPL-3.0 / SSPL-1 / Elastic License 2.0; mã `x-pack` chỉ theo ELv2 | **Không chọn** — phải tách bạch phần chỉ-ELv2 |
| Redis 8 | RSALv2 / SSPLv1 / AGPLv3 | **Không chọn** |
| Weaviate | BSD-3-Clause trộn mã độc quyền trong thư mục `wl` | **Có điều kiện, không chọn** — cùng dạng n8n ở #20 |

Milvus (Apache-2.0) không bị loại vì giấy phép nhưng chưa dựng: một cụm Milvus kéo theo nhiều dịch
vụ phụ, ngược ràng buộc ít dịch vụ.

---

## Quyết định

Chọn **pgvector** làm nơi lưu véc-tơ ngay trên PostgreSQL của hệ thống, **llama.cpp server**
chạy hai mô hình Qwen giấy phép Apache-2.0 (sinh văn bản `Qwen2.5-1.5B-Instruct` Q4_K_M, nhúng
`Qwen3-Embedding-0.6B` Q8_0), gọi bằng **HTTP và SQL trực tiếp, không dùng khung LLM**.

Navigator chấp nhận ngày 2026-11-08. Cài đặt chia hai đợt:

- **Đợt 1 — #316, #317 (đã cài):** dịch vụ `mo-hinh` (ảnh `ghcr.io/ggml-org/llama.cpp:server-b11889`,
  phát hành 2026-10-25) dưới hồ sơ Compose `tri-tue`, mô hình sinh văn bản trong volume `mo-hinh`
  (tải bằng `scripts/tai_mo_hinh.py`, ghim commit kho và SHA-256). Dịch vụ ứng dụng gọi qua đúng một
  lớp, `backend/app/intelligence/mo_hinh.py`, để gợi ý loại yêu cầu, mức ưu tiên, phòng ban
- **Đợt 2 — #319 (đã cài):** ảnh PostgreSQL đổi sang `pgvector/pgvector:0.8.6-pg16` (ghim cả mã băm;
  PostgreSQL 16.15, Debian bookworm). Phép khảo sát chạy trên 0.8.7, nhưng ảnh 0.8.7 mới dựng lại chưa
  đủ hai tuần trước ngày cài nên navigator chốt 0.8.6 (ảnh dựng 2026-08-13) ngày 2026-11-11 — cùng
  PostgreSQL 16.15, phép quét chính xác không đổi giữa hai bản. Dịch vụ nhúng `mo-hinh-nhung` chạy
  chính ảnh llama.cpp đã ghim, chế độ `--embeddings`, cùng hồ sơ `tri-tue`; tệp
  `Qwen3-Embedding-0.6B-Q8_0.gguf` cùng volume `mo-hinh`. Dùng cho gợi ý hồ sơ đã giải quyết tương tự
  trên biểu mẫu Gửi yêu cầu (ARCHITECTURE.md mục 6.6)

---

## Lý do

- **Độ đúng nằm ở mô hình nhúng, không ở nơi lưu véc-tơ.** Phép A: ba cơ sở dữ liệu cho cùng
  top-3 với xếp hạng vét cạn, 20/20. Ở quy mô kho tri thức nội bộ, pgvector quét chính xác đủ
  nhanh (21 ms ở 10.000 bài) và luôn đúng — Qdrant hay Chroma chỉ thêm một dịch vụ mà không thêm
  năng lực
- **llama.cpp server nhẹ hơn Ollama khoảng mười hai lần** ở dạng nén, cùng giấy phép MIT, cùng
  điểm cuối kiểu OpenAI — nên nếu sau này đổi sang Ollama hay dịch vụ khác, mã gọi không đổi
- **Ràng buộc đầu ra bằng JSON schema** (`enum` = mã trong dữ liệu) làm mô hình không trả được giá
  trị lạ — phép C: 0 đầu ra ngoài tập. Gợi ý luôn ghi được vào trường `suggested_*`, đúng
  nguyên tắc AI chỉ gợi ý
- **Không cần khung**: năm phép A–E chạy hết bằng HTTP và SQL. Khung thêm 37–64 gói vào dịch vụ
  ứng dụng mà không đem năng lực nào các gợi ý đã định cần tới
- **Dự phòng đã thử**: phép E — dịch vụ mô hình không tồn tại, cổng đóng, hay sinh chậm hơn hạn,
  hàm gợi ý đều trả *không có gợi ý* trong hạn chót 3 giây; luồng thủ công không bị chặn

---

## Cách tích hợp

- **pgvector**: đổi ảnh PostgreSQL của cụm sang ảnh có phần mở rộng `vector`, bật bằng
  `CREATE EXTENSION vector` trong migration. Bảng véc-tơ thuộc tầng `I`, tách khỏi bảng quyết định
- **llama.cpp server**: hai **dịch vụ độc lập** trong Compose, giao tiếp qua HTTP kiểu OpenAI.
  Nên đặt sau một hồ sơ Compose riêng (`profiles`) để máy ít bộ nhớ vẫn dựng được phần lõi bằng
  một lệnh — tầng `I` tắt thì hệ thống chạy thủ công, đúng phép E
- **Tệp mô hình không đưa vào kho mã** (1,76 GB): tải lúc dựng từ kho Hugging Face chính thức,
  ghim theo commit của kho và kiểm SHA-256
- Mọi gợi ý chỉ ghi vào trường `suggested_*`; danh mục giá trị hợp lệ đọc từ dữ liệu khởi tạo, không
  viết cứng

---

## Hệ quả

**Điều gì trở nên dễ hơn**

- Truy xuất tri thức và dữ liệu hồ sơ dùng chung một cơ sở dữ liệu, một lần sao lưu
- Không thêm phụ thuộc Python nào vào dịch vụ ứng dụng
- Đổi mô hình chỉ là đổi tệp GGUF và tham số dòng lệnh

**Điều gì trở nên khó hơn**

- **Bộ nhớ**: hai dịch vụ mô hình cộng khoảng 2,8 GiB — gần gấp đôi ngân sách 1,55 GiB hiện tại.
  Bắt buộc có hồ sơ Compose để tắt tầng `I`
- Đổi ảnh PostgreSQL từ Alpine sang Debian cho cụm chính
- Nháp trả lời của mô hình 1,5B chất lượng không đều (phép D) — chỉ dùng làm nháp cho nhân viên sửa

**Việc phải làm tiếp sau quyết định này**

- [x] Cập nhật `docs/ARCHITECTURE.md` — mục 3.4 và khuôn mẫu lớp gọi mô hình (#316)
- [x] Cập nhật `docs/dependencies.md` — llama.cpp server và mô hình sinh văn bản (#316); pgvector và
  mô hình nhúng thêm ở #319
- [x] Bổ sung vào `docker-compose.yml` dưới hồ sơ riêng cho tầng `I` — hồ sơ `tri-tue` (#316)
- [x] Mô hình nhúng và pgvector (#319)
- [x] Đánh giá đổi ảnh PostgreSQL trên cụm có dữ liệu thật — #319: cụm `postgres:16-alpine` có dữ liệu
  nâng lên ảnh pgvector bằng `up -d --build`, `scripts/kiem_nang_cap.py so` báo giữ nguyên dữ liệu, mọi chỉ
  mục B-tree qua `amcheck` sau REINDEX của migration `0022`
- [ ] Đo lại với bài thật của kho tri thức khi ADR-0006 được chấp nhận; so thêm một mô hình nhúng thứ hai

---

## Ghi chú

- Số liệu đo trên Intel Core i7-13700HX, Docker Engine 29.7.2 trên WSL2, chỉ CPU, ngày 2026-10-10;
  cách đo và kết quả từng phép ở [`../vector-llm-survey.md`](../vector-llm-survey.md) mục 5
- Lượt đo đầu dừng vì đĩa Docker của máy đo có dấu hiệu hỏng — mục 6 của tài liệu khảo sát;
  không số đo nào của lượt đó được dùng
- Điều kiện cần xem lại: kho tri thức vượt vài trăm nghìn bài (cân nhắc chỉ mục hay dịch vụ véc-tơ
  riêng); máy trình diễn không đủ bộ nhớ cho hai mô hình; giảng viên muốn mô hình lớn hơn cho nháp
  trả lời
