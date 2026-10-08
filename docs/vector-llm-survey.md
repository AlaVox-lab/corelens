# Khảo sát cơ sở dữ liệu véc-tơ và khung LLM — Không gian I

> **Mục đích**: ghi lại quá trình và kết quả khảo sát cơ sở dữ liệu véc-tơ, môi trường chạy mô
> hình ngôn ngữ cục bộ và khung LLM cho không gian `I`, làm căn cứ cho bản ghi quyết định
> ADR-0008 (navigator đã giữ số).
>
> **Issue liên quan**: #47 · **Ngày thực hiện**: 2026-10-08 · **Phạm vi**: khảo sát và dựng thử
> ngoài kho mã, chưa tích hợp vào hệ thống
>
> **Trạng thái tài liệu: BẢN DỞ DANG.** Đã kiểm xong giấy phép tận gốc và kích thước ảnh chứa,
> đã dựng được cụm thử. **Chưa có số đo hiệu năng hay độ đúng nào**: đĩa dữ liệu của Docker trên
> máy đo có dấu hiệu hỏng (mục 6), nên mọi số đo có ghi đĩa trên máy đó không dùng được. Phần còn
> lại chuyển navigator — danh sách ở mục 7. ADR-0008 chưa viết.

---

## 1. Mục tiêu và tiêu chí

Tầng `I` cần hai năng lực cho các gợi ý đã định trong `ARCHITECTURE.md` mục 2.2 và
`PROJECT_STATE.md` mục Chờ giảng viên:

1. **Truy xuất tri thức** — tìm bài hướng dẫn nội bộ gần nghĩa nhất với câu hỏi, làm nguồn cho
   gợi ý trả lời trong hộp thư. Cần một nơi lưu và tìm véc-tơ
2. **Sinh gợi ý** — gợi ý loại yêu cầu (`suggested_category`), soạn nháp câu trả lời. Cần một mô
   hình ngôn ngữ và cách gọi nó

Khảo sát trả lời ba câu: lưu véc-tơ ở đâu, chạy mô hình bằng gì, có cần khung LLM không.

| Tiêu chí | Vì sao |
|---|---|
| Giấy phép được OSI công nhận, tương thích MIT — kiểm tận tệp `LICENSE` và trong ảnh chứa | Bảng chấm PoF mục Giấy phép (10 điểm). Mảng này nhiều sản phẩm "nguồn mở một phần" |
| Ít dịch vụ thêm vào cụm | `ARCHITECTURE.md` mục 3.2: ưu tiên phần mở rộng véc-tơ ngay trên PostgreSQL |
| Chạy được với **mô hình cục bộ**, không phụ thuộc mạng ngày trình diễn | `CLAUDE.md` mục 4.3, lý do thứ ba |
| Có đường dự phòng khi mô hình lỗi | Hệ thống phải chạy tiếp ở chế độ thủ công |
| AI chỉ ghi trường gợi ý | `CLAUDE.md` mục 4.3 — đầu ra của mô hình phải bị giới hạn trong tập giá trị hợp lệ |
| Dung lượng ảnh chứa và bộ nhớ | Bảng chấm PoF mục Dựng từ mã nguồn — cụm phải dựng được trên máy sạch; ngân sách hiện 1,55 GiB |
| Đọc hiểu tiếng Việt | Nội dung hồ sơ và kho tri thức đều bằng tiếng Việt |

---

## 2. Ứng viên và giấy phép

Mọi dòng giấy phép dưới đây lấy từ tệp giấy phép ở gốc kho mã của ứng viên, đường dẫn ở mục 8.
Cột *Dòng đầu tệp* chép nguyên văn để người đọc thấy tệp đã được mở thật.

### 2.1. Cơ sở dữ liệu véc-tơ

| Ứng viên | Bản mới nhất (2026-10-08) | Dòng đầu tệp giấy phép | Giấy phép | OSI | Hệ quả với dự án MIT |
|---|---|---|---|---|---|
| **pgvector** — phần mở rộng PostgreSQL | `v0.8.7` | *Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group* | Kiểu PostgreSQL License | Có | Có — cùng họ giấy phép với PostgreSQL đang dùng |
| **Qdrant** | `v1.19.2` | *Apache License Version 2.0, January 2004* | Apache-2.0 | Có | Có — thêm một dịch vụ |
| **Chroma** | `1.5.9` | *Apache License Version 2.0, January 2004* | Apache-2.0 | Có | Có — thêm một dịch vụ |
| **Milvus** | chưa kiểm | *Apache License Version 2.0, January 2004* | Apache-2.0 | Có | Có — chưa dựng |
| **Weaviate** | chưa kiểm | *Source code in this repository is variously licensed under the BSD-3-Clause License, or the Weaviate License.* | BSD-3-Clause **trộn** mã độc quyền | Một phần | **Có điều kiện** — xem mục 2.5 |

### 2.2. Môi trường chạy mô hình cục bộ

| Ứng viên | Bản mới nhất (2026-10-08) | Dòng đầu tệp giấy phép | Giấy phép | OSI |
|---|---|---|---|---|
| **llama.cpp** (`llama-server`) | bản dựng `b11491` | *MIT License Copyright (c) 2023-2026 The ggml authors* | MIT | Có |
| **Ollama** | `v0.40.1` | *MIT License Copyright (c) Ollama* | MIT | Có |

Cả hai đều có điểm cuối kiểu OpenAI (`/v1/chat/completions`, `/v1/embeddings`), nên mã gọi từ
dịch vụ ứng dụng không phụ thuộc vào việc chọn cái nào. Ollama không dựng được trên máy đo vì
kích thước ảnh — mục 4.

### 2.3. Khung LLM

| Ứng viên | Dòng đầu tệp giấy phép | Giấy phép | OSI | Đã dựng |
|---|---|---|---|---|
| **LangChain** | *MIT License Copyright (c) LangChain, Inc.* | MIT | Có | Chưa |
| **LlamaIndex** | *The MIT License Copyright (c) Jerry Liu* | MIT | Có | Chưa |
| **Haystack** | *Apache License Version 2.0, January 2004* | Apache-2.0 | Có | Chưa |
| **Không dùng khung** — gọi thẳng điểm cuối HTTP | — | — | — | Một phần, mục 5 |

Một dữ kiện cho phương án *không dùng khung*: `backend/requirements.txt` **đã có sẵn**
`psycopg[binary]==3.3.5` và `httpx==0.28.1`. Truy vấn pgvector chỉ là câu SQL qua psycopg, gọi
mô hình chỉ là một yêu cầu HTTP — phương án này **không thêm phụ thuộc Python nào** vào dịch vụ
ứng dụng. Ba khung trên chưa được cài để đếm số gói kéo theo.

### 2.4. Mô hình (trọng số)

Giấy phép của **trọng số mô hình** phải kiểm riêng, độc lập với giấy phép phần mềm chạy nó. Cột
giấy phép dưới đây đọc từ trường `license` trong siêu dữ liệu Hugging Face (API `models/<tên>`) —
**chưa mở tận tệp `LICENSE`** của từng mô hình.

| Mô hình | Dùng cho | Tệp, kích thước | Giấy phép khai | Ghi chú |
|---|---|---|---|---|
| `Qwen/Qwen2.5-1.5B-Instruct-GGUF` | Sinh văn bản | `qwen2.5-1.5b-instruct-q4_k_m.gguf`, 1.117.320.736 byte | apache-2.0 | Kho có tệp `LICENSE` |
| `Qwen/Qwen3-0.6B-GGUF` | Sinh văn bản, bản nhẹ | `Qwen3-0.6B-Q8_0.gguf`, 639.446.688 byte | apache-2.0 | Kho có tệp `LICENSE` |
| `Qwen/Qwen3-Embedding-0.6B-GGUF` | Nhúng véc-tơ, đa ngữ | `Qwen3-Embedding-0.6B-Q8_0.gguf`, 639.150.592 byte | apache-2.0 | Kho GGUF **không có** tệp `LICENSE`, chỉ khai ở thẻ mô hình |
| `intfloat/multilingual-e5-small` | Nhúng véc-tơ, đa ngữ, chạy bằng ONNX | `onnx/model.onnx`, 448 MiB | mit | |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Nhúng véc-tơ, đa ngữ | `onnx/model.onnx`, 449 MiB | apache-2.0 | Chưa tải |
| `BAAI/bge-m3` | Nhúng véc-tơ, đa ngữ | — | mit | Chưa tải |

Ba tệp GGUF đã tải được **đối chiếu SHA-256** với giá trị Hugging Face công bố — khớp cả ba:

| Tệp | SHA-256 | Commit của kho |
|---|---|---|
| `qwen2.5-1.5b-instruct-q4_k_m.gguf` | `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` | `91cad51170dc346986eccefdc2dd33a9da36ead9` |
| `Qwen3-0.6B-Q8_0.gguf` | `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031` | `23749fefcc72300e3a2ad315e1317431b06b590a` |
| `Qwen3-Embedding-0.6B-Q8_0.gguf` | `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439` | `370f27d7550e0def9b39c1f16d3fbaa13aa67728` |

**Chưa xét** các họ mô hình mang giấy phép riêng của nhà phát triển (ví dụ giấy phép cộng đồng
của Llama, điều khoản của Gemma) — các giấy phép đó cần đối chiếu với danh sách OSI trước khi
đưa vào bảng.

### 2.5. Có điều kiện hoặc bị loại

| Ứng viên | Giấy phép, theo tệp ở gốc kho | Kết luận |
|---|---|---|
| **Weaviate** | Ngoài thư mục `wl` là BSD-3-Clause (`LICENSE-BSD`). Trong `wl`: *"Copyright Weaviate BV 2026-present, all rights reserved, and is only available under a separate enterprise license"*, tính năng doanh nghiệp bật bằng khóa giấy phép | **Có điều kiện, chưa kiểm ảnh.** Cùng dạng với n8n ở #20: mã độc quyền nằm chung kho. Muốn xét tiếp phải soi ảnh phát hành xem có kèm mã `wl` không |
| **Elasticsearch** | Mặc định ba giấy phép AGPL-3.0-only / SSPL-1 / Elastic License 2.0; mã trong `x-pack` **chỉ** theo Elastic License 2.0 | **Không chọn.** Phần AGPL hợp lệ nếu chạy như dịch vụ riêng, nhưng bản phân phối có mã chỉ-ELv2 phải tách bạch; chưa dựng, chưa soi ảnh |
| **Redis 8** | Ba giấy phép RSALv2 / SSPLv1 / AGPLv3 từ Redis 8; bản 7.2 trở về trước là BSD-3 | **Không chọn.** Có lựa chọn AGPL; năng lực tìm véc-tơ chưa kiểm |
| **MongoDB** (Community Server) | *Server Side Public License VERSION 1* | **Loại** — SSPL không thuộc danh sách OSI |

---

## 3. Kiểm trong ảnh chứa

Bài học từ #20 và #21: nhãn kho mã không đủ, phải soi thứ thật sự được phát hành.

| Ảnh | Tìm thấy trong ảnh | Ghi chú |
|---|---|---|
| `pgvector/pgvector:0.8.7-pg16-bookworm` | `/usr/share/doc/pgvector/LICENSE`, dòng đầu trùng tệp ở kho. `vector.control`: `default_version = '0.8.7'`. `postgres --version`: *PostgreSQL 16.15 (Debian 16.15-1.pgdg12+2)* | Cùng PostgreSQL 16 với cụm chính |
| `qdrant/qdrant:v1.19.1` | **Không có** tệp `LICENSE`. Có SBOM `/qdrant/qdrant.spdx.json` (sinh bởi `cargo-sbom-v0.10.0`): gói `qdrant` `1.19.1` khai `Apache-2.0`; các thư viện kéo theo khai MIT, Apache-2.0, Unicode-3.0, MPL-2.0, `BSL-1.0`… | **`BSL-1.0` trong SBOM là Boost Software License 1.0**, mã SPDX của giấy phép Boost — **không phải** Business Source License. Đừng loại nhầm. MPL-2.0 là copyleft mức tệp, cần ghi chú khi tích hợp |
| `chromadb/chroma:1.5.9` | **Không có** tệp `LICENSE` trong ảnh. Ảnh không có nhãn OCI. Lệnh `chroma --version` trong ảnh in **`chroma 1.4.4`** dù thẻ ảnh là `1.5.9`; điểm cuối `/api/v2/version` trả `"1.0.0"` | Chưa rõ vì sao số phiên bản lệch — cần hỏi lại trước khi ghi phiên bản vào bản ghi |
| `ghcr.io/ggml-org/llama.cpp:server` | **Không có** tệp `LICENSE` của llama.cpp trong ảnh. Nhãn OCI trỏ `https://github.com/ggml-org/llama.cpp`, `llama-server --version`: *version: 0.6.0-dev (build 11459, commit f498f864f)* | Căn cứ giấy phép là tệp ở kho |

---

## 4. Kích thước ảnh chứa

Kích thước **nén** của bản amd64, đọc từ API Docker Hub và registry ghcr.io ngày 2026-10-08.
Kích thước **giải nén** đọc bằng `docker images` trên máy đo.

| Ảnh | Nén | Giải nén |
|---|---|---|
| `ollama/ollama:0.40.1` | **3.604 MiB** | không kéo |
| `ollama/ollama:0.40.1-rocm` | 1.383 MiB | không kéo |
| `ghcr.io/ggml-org/llama.cpp:server` (build 11459) | 297 MiB | 1,21 GB |
| `pgvector/pgvector:0.8.7-pg16-bookworm` | 152 MiB | chưa ghi |
| `qdrant/qdrant:v1.19.2` | 71 MiB | 286 MB |
| `chromadb/chroma:1.5.9` | 168 MiB | 826 MB |
| `python:3.12-slim` (môi trường đo) | 41 MiB | 177 MB |

**Ảnh Ollama mặc định nặng 3,6 GiB nén** vì đóng gói kèm thư viện GPU. Ảnh `llama.cpp:server`
chỉ chạy CPU, nhẹ hơn khoảng mười hai lần ở dạng nén, và vẫn có đủ hai điểm cuối kiểu OpenAI.
Với tiêu chí dựng được trên máy sạch, đây là chênh lệch đáng kể. Ảnh Ollama chỉ chạy CPU thì
chưa tìm thấy trong danh sách thẻ.

Ghi nhận phụ: pgvector chỉ có thẻ dựng trên Debian (`trixie`, `bookworm`) trong các thẻ đã xem,
còn cụm chính đang dùng `postgres:16-alpine`. Đổi sang pgvector nghĩa là đổi ảnh PostgreSQL của
cụm — việc của bước tích hợp, chưa đánh giá.

---

## 5. Dựng thử

### 5.1. Môi trường

Cụm thử dựng ngoài kho mã, tên dự án riêng `thu47`, cổng không trùng cụm chính:

| Dịch vụ | Ảnh | Cổng máy |
|---|---|---|
| `pgvector` | `pgvector/pgvector:0.8.7-pg16-bookworm` | 15432 |
| `qdrant` | `qdrant/qdrant:v1.19.1`, tắt telemetry | 16333 |
| `chroma` | `chromadb/chroma:1.5.9`, tắt telemetry | 18001 |
| `llm` | `llama.cpp:server` + `qwen2.5-1.5b-instruct-q4_k_m.gguf`, ngữ cảnh 4096, 6 luồng | 18080 |
| `emb` | `llama.cpp:server --embedding --pooling last` + `Qwen3-Embedding-0.6B-Q8_0.gguf` | 18081 |
| `py` | `python:3.12-slim`, môi trường ảo trong volume riêng của cụm thử | — |

| Mục | Giá trị |
|---|---|
| Máy | Intel Core i5-13420H, 15,5 GB RAM, Windows 11 Home Single Language |
| Docker | Engine `28.3.2`, Docker Desktop trên WSL2; máy ảo được cấp 7,5 GiB; trình lưu trữ `overlayfs` qua containerd snapshotter |
| Gói Python đo | `httpx 0.28.1`, `psycopg 3.3.5`, `numpy 2.5.3`, `onnxruntime 1.30.0`, `tokenizers 0.23.2`, `qdrant-client 1.19.1`, `chromadb-client` |

Máy đo không cài Python nên mọi kịch bản chạy trong container `py`. Hai phiên bản lệch so với
bản mới nhất **không do ứng viên**: thẻ `pgvector …-pg16-trixie` và `qdrant v1.19.2` hỏng lớp
dữ liệu trong bộ đệm Docker của máy đo (mục 6), nên cụm thử dùng bản `bookworm` và `v1.19.1`.

### 5.2. Phép thử đã thiết kế, chưa chạy xong

Mọi phép thử đều **có đáp án biết trước**, theo bài học #48:

| Phép thử | Dữ liệu | Đáp án biết trước | Đo gì |
|---|---|---|---|
| A — truy xuất kho tri thức | 20 bài hướng dẫn nội bộ tiếng Việt; 20 câu hỏi **diễn đạt lại** bằng từ khác | Bài đúng của từng câu | Kết quả mỗi cơ sở dữ liệu có **trùng** thứ hạng tính vét cạn bằng numpy không; recall@1, recall@3 của hai mô hình nhúng |
| B — chỉ mục xấp xỉ | 10.000 véc-tơ 1024 chiều, hạt giống `47`; 100 câu hỏi là bản nhiễu nhẹ của 100 véc-tơ đã biết | Láng giềng gốc của từng câu hỏi; top-10 vét cạn | Thời gian nạp, dựng HNSW, truy vấn p50/p95; recall@10 so với vét cạn |
| C — gợi ý loại yêu cầu | 20 yêu cầu, mỗi loại năm mẫu; danh mục loại **đọc từ dữ liệu** khởi tạo, không viết cứng | Loại đúng của từng yêu cầu | Số đúng, thời gian p50/p95. Đầu ra ràng buộc bằng JSON schema có `enum` = mã loại, nên mô hình **không trả được mã lạ** |
| D — soạn nháp trả lời | Câu hỏi phép A, 3 bài gần nhất | Bài đúng | Bài đúng có trong top-3 không; mô hình có chọn đúng bài để trích không |
| E — dự phòng | Gọi tới dịch vụ mô hình không tồn tại, hạn chót 3 giây | Phải trả *không có gợi ý* | Thời gian trước khi bỏ cuộc |

Dữ liệu và kịch bản nằm ngoài kho, trong thư mục thử của người khảo sát; navigator cần thì gửi
kèm.

### 5.3. Đã chạy được tới đâu

- Sáu dịch vụ của cụm thử lên đủ. `llm` và `emb` báo `healthy`; `/v1/models` của `llm` liệt kê
  đúng tệp Qwen2.5, ngữ cảnh 4096
- Phép A chạy qua bước nhúng bằng Qwen3-Embedding, nạp và truy vấn pgvector không lỗi, rồi
  **hỏng ở bước nạp Qdrant**: tạo một bộ sưu tập rỗng mất 39,6 giây, lệnh nạp kế tiếp bị máy chủ
  ngắt kết nối. Kết quả chưa được ghi lại
- Phép B, C, D, E: **chưa chạy**
- Bộ nhớ từng dịch vụ (`docker stats --no-stream`): **chưa đo**

**Chưa có số liệu nào để so sánh.** Không kết luận được gì về hiệu năng hay độ đúng từ lần dựng
này.

---

## 6. Sự cố trên máy đo — đĩa dữ liệu của Docker

Ghi lại để người dựng lại biết số đo của lần này không dùng được, và vì máy thành viên từng gặp
lỗi dựng ở #48. **Nguyên nhân chưa xác nhận.**

| Quan sát | Chi tiết |
|---|---|
| Ổ chứa đĩa ảo Docker gần đầy | `docker_data.vhdx` 17,5 GB nằm trên ổ C:; ổ C: còn 11 GB trống lúc bắt đầu, 7,9 GB (97 %) sau khi kéo ảnh |
| Ảnh vừa kéo không chạy được | `pgvector …-pg16-trixie`: `exec /usr/lib/postgresql/16/bin/postgres: input/output error`, `exec /bin/ls: exec format error`. `qdrant v1.19.2` và `v1.19.2-unprivileged`: `exec /qdrant/qdrant: input/output error`. **Gỡ ảnh rồi kéo lại vẫn lỗi y nguyên**; đổi sang thẻ có lớp dữ liệu khác (`bookworm`, `v1.19.1`) thì chạy |
| Docker treo | `docker run` kẹt ở trạng thái `Created`, `docker info` và `docker system df` quá hạn 30 giây; vài phút sau tự hồi |
| Hệ tệp không được tắt sạch từ lần trước | Nhật ký nhân máy ảo Docker lúc khởi động: `EXT4-fs (sde): recovery complete`. Không thấy dòng lỗi I/O nào khác trong nhật ký nhân |
| Ghi đồng bộ cực chậm | Đo bằng `dd` trong volume của container pgvector. Ghi tuần tự 200 MiB rồi `fsync` một lần: 3,84 giây, 54,6 MB/s — bình thường. Ghi 500 khối 4 KiB, **mỗi khối một lần đồng bộ** (`oflag=dsync`): **589 giây, 3,5 kB/s**, khoảng 1,2 giây cho mỗi lần đồng bộ. Cơ sở dữ liệu đồng bộ xuống đĩa rất thường xuyên, nên đây là lý do khả dĩ nhất cho việc tạo một bộ sưu tập rỗng trong Qdrant mất 39,6 giây |

Nghi do ổ C: gần đầy, hoặc đĩa ảo của Docker đã hỏng sau lần tắt không sạch — chưa phân biệt
được. Hệ quả cho khảo sát: mọi số đo có ghi đồng bộ xuống đĩa — nạp dữ liệu, dựng chỉ mục của cả
ba cơ sở dữ liệu — trên máy này sẽ phản ánh lỗi đĩa chứ không phản ánh ứng viên. Hướng xử lý đề xuất: chuyển *Disk image location* của Docker Desktop sang ổ còn trống, khởi
động lại Docker Desktop, rồi dựng lại cụm thử. Nếu hiện hộp thoại lỗi có nút *Reset to factory
defaults* thì **không bấm** (`TRO-LY-THANH-VIEN.md` mục 2.7).

---

## 7. Việc còn lại

- [ ] Đọc bình luận giao việc của #47 và đối chiếu phạm vi — người khảo sát chưa đọc được vì máy
      chưa cài `gh`
- [ ] Dựng lại cụm thử trên máy có đĩa Docker ổn định, chạy năm phép thử ở mục 5.2
- [ ] Đo bộ nhớ từng dịch vụ bằng `docker stats --no-stream`; đo thời gian nạp thư viện từ lần chạy
      thứ hai
- [ ] Cài ba khung LLM vào ba môi trường riêng: đếm số gói kéo theo, dung lượng, thời gian nạp,
      chạy cùng một luồng truy xuất để so với phương án không dùng khung
- [ ] Mở tận tệp `LICENSE` của từng mô hình ở mục 2.4
- [ ] Làm rõ số phiên bản lệch trong ảnh Chroma (mục 3)
- [ ] Soi ảnh phát hành của Weaviate nếu còn muốn xét
- [ ] Viết ADR-0008 trạng thái *Đề xuất*

**Hướng sơ bộ, chưa phải kết luận**: dữ kiện đã có nghiêng về pgvector (không thêm dịch vụ,
cùng họ giấy phép PostgreSQL), llama.cpp server cho mô hình cục bộ (ảnh nhẹ, MIT, có điểm cuối
kiểu OpenAI), và gọi thẳng HTTP thay vì khung (không thêm phụ thuộc Python). Cả ba cần số đo ở
mục 5.2 mới đủ căn cứ.

---

## 8. Nguồn

Mọi đường dẫn dưới đây đã được mở ngày 2026-10-08 và trả về nội dung.

| Nguồn | Đường dẫn |
|---|---|
| pgvector — giấy phép | <https://raw.githubusercontent.com/pgvector/pgvector/master/LICENSE> |
| Qdrant — giấy phép | <https://raw.githubusercontent.com/qdrant/qdrant/master/LICENSE> |
| Chroma — giấy phép | <https://raw.githubusercontent.com/chroma-core/chroma/main/LICENSE> |
| Milvus — giấy phép | <https://raw.githubusercontent.com/milvus-io/milvus/master/LICENSE> |
| Weaviate — giấy phép | <https://raw.githubusercontent.com/weaviate/weaviate/main/LICENSE> |
| llama.cpp — giấy phép | <https://raw.githubusercontent.com/ggml-org/llama.cpp/master/LICENSE> |
| Ollama — giấy phép | <https://raw.githubusercontent.com/ollama/ollama/main/LICENSE> |
| LangChain — giấy phép | <https://raw.githubusercontent.com/langchain-ai/langchain/master/LICENSE> |
| LlamaIndex — giấy phép | <https://raw.githubusercontent.com/run-llama/llama_index/main/LICENSE> |
| Haystack — giấy phép | <https://raw.githubusercontent.com/deepset-ai/haystack/main/LICENSE> |
| Elasticsearch — giấy phép | <https://raw.githubusercontent.com/elastic/elasticsearch/main/LICENSE.txt> |
| Redis — giấy phép | <https://raw.githubusercontent.com/redis/redis/unstable/LICENSE.txt> |
| MongoDB — giấy phép | <https://raw.githubusercontent.com/mongodb/mongo/master/LICENSE-Community.txt> |
| Phiên bản mới nhất | <https://api.github.com/repos/qdrant/qdrant/releases/latest> · <https://api.github.com/repos/chroma-core/chroma/releases/latest> · <https://api.github.com/repos/ollama/ollama/releases/latest> · <https://api.github.com/repos/pgvector/pgvector/tags> · <https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=3> |
| Kích thước ảnh Docker Hub | <https://hub.docker.com/v2/repositories/ollama/ollama/tags> · <https://hub.docker.com/v2/repositories/pgvector/pgvector/tags/0.8.7-pg16-bookworm> · <https://hub.docker.com/v2/repositories/qdrant/qdrant/tags/v1.19.2> · <https://hub.docker.com/v2/repositories/chromadb/chroma/tags/1.5.9> |
| Mô hình — siêu dữ liệu, giấy phép khai, SHA-256 | <https://huggingface.co/api/models/Qwen/Qwen2.5-1.5B-Instruct-GGUF> · <https://huggingface.co/api/models/Qwen/Qwen3-0.6B-GGUF> · <https://huggingface.co/api/models/Qwen/Qwen3-Embedding-0.6B-GGUF> · <https://huggingface.co/api/models/intfloat/multilingual-e5-small> · <https://huggingface.co/api/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2> · <https://huggingface.co/api/models/BAAI/bge-m3> |
