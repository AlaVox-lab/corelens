# Khảo sát cơ sở dữ liệu véc-tơ và khung LLM — Không gian I

> **Mục đích**: ghi lại quá trình và kết quả khảo sát cơ sở dữ liệu véc-tơ, môi trường chạy mô
> hình ngôn ngữ cục bộ và khung LLM cho không gian `I`, làm căn cứ cho bản ghi quyết định
> ADR-0008 (navigator đã giữ số).
>
> **Issue liên quan**: #47 · **Ngày thực hiện**: 2026-10-08 (giấy phép, ảnh chứa — Nguyễn Thanh
> Nguyên), 2026-10-10 (sáu phép thử — navigator) · **Phạm vi**: khảo sát và dựng thử ngoài kho mã,
> chưa tích hợp vào hệ thống
>
> **Hai lượt đo.** Lượt đầu trên máy của người khảo sát dừng giữa chừng vì đĩa dữ liệu Docker có
> dấu hiệu hỏng (mục 6) — không số đo nào của lượt đó được dùng. Lượt hai trên máy navigator chạy
> đủ sáu phép thử có đáp án biết trước (mục 5). Kết luận ở mục 7, bản ghi quyết định là
> [ADR-0008](adr/0008-chon-co-so-du-lieu-vec-to-va-mo-hinh-cuc-bo.md).

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
*Giấy phép khai* đọc từ trường `license` trong siêu dữ liệu Hugging Face (API `models/<tên>`).
Cột *Kiểm tận gốc* (ngày 2026-10-10): mở tệp `LICENSE` ở gốc kho mô hình; kho nào không có tệp đó
thì đọc dòng `license:` trong phần đầu tệp `README.md` (thẻ mô hình) — nguồn ở mục 8.

| Mô hình | Dùng cho | Tệp, kích thước | Giấy phép khai | Kiểm tận gốc |
|---|---|---|---|---|
| `Qwen/Qwen2.5-1.5B-Instruct-GGUF` | Sinh văn bản | `qwen2.5-1.5b-instruct-q4_k_m.gguf`, 1.117.320.736 byte | apache-2.0 | Tệp `LICENSE`, dòng đầu *Apache License* |
| `Qwen/Qwen3-0.6B-GGUF` | Sinh văn bản, bản nhẹ | `Qwen3-0.6B-Q8_0.gguf`, 639.446.688 byte | apache-2.0 | Tệp `LICENSE`, dòng đầu *Apache License* |
| `Qwen/Qwen3-Embedding-0.6B-GGUF` | Nhúng véc-tơ, đa ngữ | `Qwen3-Embedding-0.6B-Q8_0.gguf`, 639.150.592 byte | apache-2.0 | **Không có** tệp `LICENSE` — cả kho GGUF lẫn kho gốc `Qwen/Qwen3-Embedding-0.6B`; thẻ mô hình của cả hai ghi `license: apache-2.0` |
| `intfloat/multilingual-e5-small` | Nhúng véc-tơ, đa ngữ, chạy bằng ONNX | `onnx/model.onnx`, 448 MiB | mit | Không có tệp `LICENSE`; thẻ mô hình ghi `license: mit` |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Nhúng véc-tơ, đa ngữ | `onnx/model.onnx`, 449 MiB | apache-2.0 | Không có tệp `LICENSE`; thẻ mô hình ghi `license: apache-2.0`. Chưa tải |
| `BAAI/bge-m3` | Nhúng véc-tơ, đa ngữ | — | mit | Không có tệp `LICENSE`; thẻ mô hình ghi `license: mit`. Chưa tải |

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
| `chromadb/chroma:1.5.9` | **Không có** tệp `LICENSE` trong ảnh. Ảnh không có nhãn OCI. Lệnh `chroma --version` trong ảnh in **`chroma 1.4.4`** dù thẻ ảnh là `1.5.9`; điểm cuối `/api/v2/version` trả `"1.0.0"` | Lượt đo hai kéo lại ảnh, thấy **y hệt** (ảnh tạo ngày 2026-05-05). Chưa rõ vì sao số phiên bản lệch; bản ghi chỉ ghi theo thẻ ảnh và máy khách `chromadb-client 1.5.9`. Không ảnh hưởng kết luận vì Chroma không được chọn |
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

## 5. Dựng thử và số đo

### 5.1. Môi trường

Cụm thử dựng ngoài kho mã, tên dự án riêng `thu47`, cổng không trùng cụm chính:

| Dịch vụ | Ảnh | Cổng máy | Tham số |
|---|---|---|---|
| `pgvector` | `pgvector/pgvector:0.8.7-pg16-bookworm` | 15432 | mặc định |
| `qdrant` | `qdrant/qdrant:v1.19.2`, tắt telemetry | 16333 | mặc định, trừ phép B (mục 5.3) |
| `chroma` | `chromadb/chroma:1.5.9`, tắt telemetry | 18001 | mặc định |
| `llm` | `ghcr.io/ggml-org/llama.cpp:server` (build 11541, commit `f2918cabb`) + `qwen2.5-1.5b-instruct-q4_k_m.gguf` | 18080 | `-c 4096 -t 6` |
| `emb` | cùng ảnh + `Qwen3-Embedding-0.6B-Q8_0.gguf` | 18081 | `--embedding --pooling last -c 8192 -ub 8192 -t 6` |
| `py` | `python:3.12-slim`, môi trường ảo trong volume riêng của cụm thử | — | — |

| Mục | Lượt đo hai (dùng cho mọi số dưới đây) |
|---|---|
| Máy | Intel Core i7-13700HX, 15,6 GB RAM, Windows 11 Pro |
| Docker | Engine `29.7.2`, Docker Desktop trên WSL2, máy ảo 24 nhân logic, 7,75 GiB; đĩa dữ liệu Docker trên ổ còn trống 379 GB |
| Gói Python đo | `httpx 0.28.1`, `psycopg 3.3.5`, `numpy 2.5.3`, `qdrant-client 1.19.1`, `chromadb-client 1.5.9` |
| Tệp mô hình | Hai tệp GGUF tải lại từ kho Qwen; **SHA-256 khớp** bảng ở mục 2.4 |

Mọi thời gian đo **phía máy khách** (container `py`, cùng mạng Docker với ba cơ sở dữ liệu), chỉ
chạy CPU, không GPU. Số đo phụ thuộc máy; dùng để so các phương án với nhau, không phải con số
cam kết.

### 5.2. Sáu phép thử có đáp án biết trước

Năm phép A–E giữ đúng thiết kế của lượt đầu, theo bài học #48. Thêm phép F so chi phí của khung
LLM.

| Phép thử | Dữ liệu | Đáp án biết trước | Đo gì |
|---|---|---|---|
| A — truy xuất kho tri thức | 20 bài hướng dẫn nội bộ tiếng Việt; 20 câu hỏi **diễn đạt lại** bằng từ khác ("Tôi không nhớ pass để vào hộp mail" cho bài *Đặt lại mật khẩu email công ty*) | Bài đúng của từng câu | recall@1, recall@3 của mô hình nhúng (xếp hạng vét cạn bằng numpy); mỗi cơ sở dữ liệu có **trùng** thứ hạng vét cạn không |
| B — chỉ mục xấp xỉ | 10.000 véc-tơ 1024 chiều ngẫu nhiên, hạt giống `47`; 100 câu hỏi là bản nhiễu nhẹ của 100 véc-tơ đã biết | Véc-tơ gốc của từng câu; top-10 vét cạn | Thời gian nạp, dựng HNSW, truy vấn p50/p95; recall@10 |
| C — gợi ý loại yêu cầu | 20 yêu cầu, mỗi loại năm mẫu; danh mục loại **đọc từ dữ liệu khởi tạo** `infra/seed/02-co-cau-to-chuc.sql`, không viết cứng | Loại đúng của từng yêu cầu | Số đúng, số đầu ra ngoài tập, p50/p95. Đầu ra ràng buộc bằng JSON schema có `enum` = mã loại |
| D — soạn nháp trả lời | Câu hỏi phép A, 3 bài gần nhất | Bài đúng | Bài đúng có trong top-3 không; mô hình chọn đúng bài không (`enum` = mã 3 bài) |
| E — dự phòng | Dịch vụ mô hình không tồn tại; cổng đóng; mô hình sống nhưng chậm hơn hạn | Phải trả *không có gợi ý* trong hạn chót 3 giây | Thời gian trước khi bỏ cuộc |
| F — chi phí khung LLM | Mỗi phương án một môi trường ảo riêng, cài gói tối thiểu cho pgvector + điểm cuối kiểu OpenAI | — | Số gói, dung lượng, thời gian `import` lần một và lần hai |

Kịch bản đo và dữ liệu thử nằm ngoài kho mã (thư mục thử của navigator), không đưa vào kho.

### 5.3. Kết quả

**A — truy xuất kho tri thức** (Qwen3-Embedding-0.6B Q8_0, 1024 chiều; câu hỏi kèm chỉ dẫn theo
thẻ mô hình, bài để nguyên)

| Đo | Kết quả |
|---|---|
| recall@1 | **18/20** |
| recall@3 | **20/20** |
| Hai câu sai hạng 1 | "Máy lạnh phòng họp nhỏ nhỏ giọt xuống bàn" → hạng 1 là *Đặt phòng họp*, bài đúng *Báo hỏng điều hòa* ở hạng 2. "Muốn dùng một công cụ vẽ sơ đồ chưa có trên máy" → bài đúng ở hạng 3 |
| Top-3 trùng vét cạn | pgvector **20/20**, Qdrant **20/20**, Chroma **20/20** |
| Thời gian nhúng | 20 bài 4,95 giây; 20 câu hỏi 2,79 giây (một lô) |

Ở quy mô này ba cơ sở dữ liệu cho **cùng một kết quả**: độ đúng nằm ở mô hình nhúng, không ở nơi
lưu véc-tơ.

**B — chỉ mục xấp xỉ** (10.000 × 1024, tham số HNSW mặc định của từng sản phẩm)

| | Nạp | Dựng chỉ mục | Truy vấn p50 / p95 | recall@10 | Gốc ở hạng 1 |
|---|---|---|---|---|---|
| pgvector — HNSW, `ef_search` 40 (mặc định) | 3,05 s | 8,51 s | 1,5 / 2,4 ms | 0,378 | 86/100 |
| pgvector — HNSW, `ef_search` 100 | | | 21,4 / 24,4 ms | 1,0 | 100/100 |
| pgvector — **quét chính xác, không chỉ mục** | 3,05 s | — | **21,4 / 23,2 ms** | **1,0** | **100/100** |
| Qdrant | 5,28 s | 0,52 s | 2,7 / 3,2 ms | 1,0 | 100/100 |
| Chroma (dựng HNSW trong lúc nạp) | 2,93 s | | 2,8 / 5,6 ms | 0,501 | 96/100 |

Đọc bảng này cẩn thận:

- **Véc-tơ ngẫu nhiên 1024 chiều là trường hợp xấu nhất của HNSW** — không có cụm nào để đồ thị
  bám vào. Recall thấp của pgvector và Chroma ở tham số mặc định nói về dữ liệu này, không nói
  về véc-tơ nhúng thật, vốn có cấu trúc
- **Qdrant mặc định không dựng HNSW cho tập nhỏ.** Với `indexing_threshold` mặc định
  10.000 KB, 10.000 véc-tơ chia thành nhiều đoạn nhỏ hơn ngưỡng và bị quét phẳng
  (`indexed_vectors_count = 0`). Lượt đo hạ ngưỡng xuống 1.000 KB để Qdrant dựng chỉ mục; dù
  vậy, đoạn nhỏ hơn `full_scan_threshold` (mặc định 10.000 KB) vẫn được tìm chính xác — nên
  recall 1,0 của Qdrant là **tìm chính xác**, không phải HNSW tốt hơn
- **Kết luận dùng được**: ở quy mô kho tri thức nội bộ (vài nghìn tới vài chục nghìn bài), quét
  chính xác trên pgvector mất khoảng 21 ms mỗi câu ở 10.000 bài mà luôn đúng. Chưa cần chỉ mục;
  khi cần, HNSW của pgvector đạt recall 1,0 ở `ef_search` 100

**C — gợi ý loại yêu cầu** (Qwen2.5-1.5B-Instruct Q4_K_M, nhiệt độ 0)

| Đo | Kết quả |
|---|---|
| Đúng | **19/20** |
| Đầu ra ngoài tập mã loại | **0** — JSON schema có `enum` chặn ở bước sinh |
| Thời gian p50 / p95 | 620 / 775 ms |
| Câu sai | "Xin quyền thư mục dùng chung phòng Nhân sự" → gợi ý *Giấy xác nhận nhân sự*, đúng là *Cấp quyền phần mềm* — chữ "Nhân sự" kéo lệch |

Mô hình không trả được mã lạ, nên đầu ra luôn ghi được vào `suggested_category` — đúng nguyên
tắc AI chỉ ghi trường gợi ý. Một câu sai trên hai mươi là lý do người phân loại vẫn phải xác
nhận.

**D — soạn nháp trả lời**

| Đo | Kết quả |
|---|---|
| Bài đúng có trong top-3 | **20/20** |
| Mô hình chọn đúng bài | **18/20** |
| Thời gian p50 / p95 | 3,0 / 4,2 s |
| Chất lượng nháp | Không đều: có câu chép gần nguyên văn bài hướng dẫn, có câu chỉ trả tên bài ("Đổi mật khẩu email công ty"). Đủ làm **nháp cho nhân viên sửa**, không đủ để tự gửi |

**E — dự phòng** (hàm gợi ý mẫu, hạn chót 3 giây; lỗi hay quá hạn đều trả *không có gợi ý*)

| Tình huống | Trả *không có gợi ý* | Thời gian |
|---|---|---|
| Dịch vụ không tồn tại (tên máy sai) | Có | 1,96 s |
| Cổng đóng | Có | 0,01 s |
| Mô hình sống nhưng sinh chậm hơn hạn | Có | 3,01 s |

Luồng thủ công không bao giờ chờ quá hạn chót, dù mô hình hỏng theo cách nào.

**F — chi phí khung LLM** (gói tối thiểu cho pgvector + điểm cuối kiểu OpenAI; thời gian `import`
lần hai, sau khi Python đã biên dịch)

| Phương án | Gói cài | Phiên bản chính | Số gói | Dung lượng | `import` |
|---|---|---|---|---|---|
| **Không dùng khung** | `httpx`, `psycopg[binary]` — **đã có sẵn** trong `backend/requirements.txt` | — | 10 | 39 MB | 0,10 s |
| LangChain | `langchain`, `langchain-openai`, `langchain-postgres` | `langchain 1.4.4` | 54 | 257 MB | 0,95 s |
| LlamaIndex | `llama-index-core` + ba gói tích hợp | `llama-index-core 0.14.25` | 74 | 302 MB | 1,24 s |
| Haystack | `haystack-ai`, `pgvector-haystack` | `haystack-ai 3.3.0` | 47 | 195 MB | 0,38 s |

Năm phép A–E đều chạy bằng **gọi thẳng HTTP và SQL**, không khung nào — nên năng lực cần cho các
gợi ý đã định không đòi khung. Khung thêm 37–64 gói kéo theo vào dịch vụ ứng dụng.

**Bộ nhớ** (`docker stats --no-stream` sau khi chạy xong cả sáu phép)

| Dịch vụ | Bộ nhớ |
|---|---|
| `llm` — Qwen2.5-1.5B Q4_K_M, ngữ cảnh 4096 | 1,21 GiB |
| `emb` — Qwen3-Embedding-0.6B Q8_0, ngữ cảnh 8192 | 1,57 GiB |
| `pgvector` | 194 MiB |
| `qdrant` | 170 MiB |
| `chroma` | 135 MiB |

Hai dịch vụ mô hình cộng **khoảng 2,8 GiB** — gần gấp đôi ngân sách 1,55 GiB hiện tại của cụm.
Ngữ cảnh 8192 của `emb` là thừa cho bài hướng dẫn ngắn; hạ xuống sẽ bớt bộ nhớ, **chưa đo**.

---

## 6. Sự cố ở lượt đo đầu — đĩa dữ liệu của Docker

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

## 7. Kết luận và việc còn lại

**Kết luận** — chi tiết lập luận và các phương án bị loại ở
[ADR-0008](adr/0008-chon-co-so-du-lieu-vec-to-va-mo-hinh-cuc-bo.md):

| Câu hỏi | Chọn | Căn cứ |
|---|---|---|
| Lưu véc-tơ ở đâu | **pgvector** — phần mở rộng trên PostgreSQL đang dùng | Phép A: cả ba cơ sở dữ liệu cùng kết quả 20/20; phép B: quét chính xác 21 ms ở 10.000 bài, recall 1,0. Không thêm dịch vụ, cùng họ giấy phép PostgreSQL |
| Chạy mô hình bằng gì | **llama.cpp server** (MIT), hai tiến trình: sinh văn bản và nhúng | Ảnh 297 MiB nén so với 3,6 GiB của Ollama; điểm cuối kiểu OpenAI; phép C, D chạy được trên CPU |
| Mô hình | Sinh văn bản `Qwen2.5-1.5B-Instruct` Q4_K_M; nhúng `Qwen3-Embedding-0.6B` Q8_0 — cả hai Apache-2.0 | Phép A recall@3 20/20; phép C 19/20, không đầu ra ngoài tập; phép D chọn đúng bài 18/20 |
| Có cần khung LLM không | **Không** — gọi thẳng HTTP và SQL bằng `httpx`, `psycopg` đã có | Phép F: khung thêm 37–64 gói, 195–302 MB; năm phép A–E đều chạy không cần khung |
| Dự phòng | Hạn chót 3 giây, lỗi hay quá hạn thì *không có gợi ý* | Phép E: cả ba tình huống lỗi trả về trong hạn |

**Chưa làm, ghi lại để người sau không tưởng đã làm**

- [ ] Mô hình nhúng thứ hai (`multilingual-e5-small`, `bge-m3`) — chưa tải, chưa so recall
- [ ] Đo lại với dữ liệu thật của kho tri thức khi #46 (Wiki.js, ADR-0006) được chấp nhận và có bài
- [ ] Bộ nhớ của `emb` khi hạ ngữ cảnh xuống 2048; chạy hai mô hình trong **một** tiến trình
      llama.cpp — chưa kiểm
- [ ] Đổi ảnh PostgreSQL của cụm chính từ `postgres:16-alpine` sang ảnh có pgvector — chưa đánh giá
      ảnh hưởng tới dữ liệu và bộ quy tắc hiện có
- [ ] Soi ảnh phát hành của Weaviate — không cần nữa vì không chọn
- [ ] Vì sao ảnh Chroma `1.5.9` tự báo `1.4.4` — không cần nữa vì không chọn

---

## 8. Nguồn

Mọi đường dẫn dưới đây đã được mở ngày 2026-10-08; mười ba đường dẫn tệp giấy phép được mở lại
ngày 2026-10-10 khi soát, dòng đầu khớp bảng mục 2.

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
| Mô hình — tệp `LICENSE` (mở 2026-10-10) | <https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/LICENSE> · <https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/LICENSE> |
| Mô hình — thẻ mô hình, dòng `license:` (mở 2026-10-10) | <https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/README.md> · <https://huggingface.co/Qwen/Qwen3-Embedding-0.6B/resolve/main/README.md> · <https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/README.md> · <https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/README.md> · <https://huggingface.co/BAAI/bge-m3/resolve/main/README.md> |
| Tải tệp mô hình đã đo | <https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf> · <https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf> |
