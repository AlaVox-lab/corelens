# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấu hình dịch vụ ứng dụng, đọc từ biến môi trường.
#
# Không có giá trị nghiệp vụ nào ở đây. Trạng thái, vai trò, phòng ban, ngưỡng SLA
# đều nằm trong bảng dữ liệu — xem ARCHITECTURE.md mục 5. Tệp này chỉ giữ những thứ
# thuộc môi trường triển khai: chuỗi kết nối, cổng, mức ghi nhật ký.

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Bộ quét im quá chừng này chu kỳ mà không có lượt thành công nào thì coi là quá lâu. Năm chu kỳ:
# một vài lượt trượt (cơ sở dữ liệu khởi động lại, một bản khác đang giữ khóa) không làm đèn đỏ,
# nhưng bộ quét chết thật thì phát hiện được trong vài phút ở chu kỳ mặc định.
BOI_SO_CHU_KY_QUA_LAU = 5


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường mang tiền tố DXLAB_."""

    model_config = SettingsConfigDict(
        env_prefix="DXLAB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Chuỗi kết nối đầy đủ, dựng sẵn trong docker-compose.yml từ các biến rời rạc.
    # Dùng psycopg 3: tiền tố là postgresql+psycopg, không phải postgresql+psycopg2.
    database_uri: str = "postgresql+psycopg://dxlab:dxlab@localhost:5432/dxlab"

    # Nhãn hiển thị trong tài liệu API tự sinh
    app_name: str = "Corelens — Cổng vận hành yêu cầu nội bộ"
    app_version: str = "0.3.0"

    # Bật chế độ gỡ lỗi của SQLAlchemy. Không bao giờ bật ở bản triển khai thật.
    database_echo: bool = False

    # Thư mục dữ liệu khởi tạo (infra/seed/ gắn vào container), bộ nạp đọc lần đầu dựng cụm (#254)
    seed_dir: str = "/seed"

    # Nhật ký (#247): `json` — mỗi dòng một đối tượng JSON mang mã yêu cầu, cho công cụ gom nhật ký;
    # `text` — dạng chữ, khi đọc tay. Xem app/quan_sat.py
    log_format: Literal["json", "text"] = "json"
    log_level: str = "INFO"

    # --- Dịch vụ khai phá quy trình (#314, ADR-0007) ------------------------
    #
    # Dịch vụ riêng, chỉ nghe trong mạng của Compose; chỉ dịch vụ này gọi nó, sau khi đã kiểm vai trò
    # và gắn phạm vi phòng. Tắt thì chỉ màn quy trình thực tế báo không phản hồi.
    mining_url: str = "http://khai-pha:8000"
    mining_timeout_seconds: float = 30.0
    # Tài khoản cơ sở dữ liệu chỉ đọc riêng của dịch vụ khai phá — migration 0019 tạo và cấp quyền
    mining_db_user: str = "khai_pha_readonly"
    mining_db_password: str = ""

    # --- Mô hình ngôn ngữ cục bộ (#316, ADR-0008) ------------------------------
    #
    # Dịch vụ mô hình là TÙY CHỌN: cụm mặc định không có nó (hồ sơ Compose `tri-tue`), và địa chỉ
    # rỗng nghĩa là tắt — không gợi ý nào được sinh, mọi thao tác chạy thủ công như cũ. Mọi lời gọi
    # đi qua đúng một lớp, `app/intelligence/mo_hinh.py`; lỗi nào cũng thành "không có gợi ý".
    llm_url: str = ""
    # Tên mô hình gửi kèm lời gọi kiểu OpenAI và ghi vào ghi chú gợi ý. llama.cpp server chạy đúng
    # một mô hình nên không chọn theo tên; đổi tệp GGUF thì đổi cả tên này cho ghi chú khỏi nói sai.
    llm_model: str = "qwen2.5-1.5b-instruct-q4_k_m"
    # Hạn chót của MỘT lần hỏi mô hình, tính cả lúc chờ hàng. Gợi ý sinh ở nền, không ai đứng chờ,
    # nên hạn này rộng; quá hạn thì bỏ, không thử kéo dài.
    llm_timeout_seconds: float = 30.0
    # Hạn chót của lần hỏi tình trạng cho màn Hệ thống — người quản trị đang chờ trang tải
    llm_health_timeout_seconds: float = 2.0
    # Trần số token sinh ra mỗi lần — đủ cho ba mã và ba câu lý do ngắn
    llm_max_tokens: int = 512

    # --- Gợi ý loại, mức ưu tiên, phòng ban (#317) ----------------------------
    #
    # Hai đường sinh gợi ý: tác vụ nền ngay sau khi hồ sơ được gửi, và bộ quét bù này cho hồ sơ còn ở
    # chỗ điều phối mà chưa có gợi ý (tác vụ nền rơi khi dịch vụ khởi động lại, mô hình bật muộn). Bộ
    # quét chỉ chạy khi mô hình bật (`llm_url` khác rỗng).
    suggest_scan_enabled: bool = True
    suggest_scan_interval_seconds: int = 30
    # Số hồ sơ tối đa mỗi lượt quét, xử lý lần lượt từng cái
    suggest_scan_batch_size: int = 5
    # Một hồ sơ được thử tối đa chừng này lần (thành công thì thôi), cách nhau ít nhất chừng ấy giây.
    # Mô hình không tới được thì lần đó không tính — chỉ lần mô hình trả lời mà hỏng mới tính.
    suggest_max_attempts: int = 3
    suggest_retry_after_seconds: int = 600
    # Gợi ý PHÒNG BAN của mô hình chỉ thay gợi ý theo bảng ánh xạ khi bật cờ này. Mặc định TẮT; chỉ
    # bật khi đo trên bộ mẫu có nhãn đạt từ 80 % đúng (scripts/do_chinh_xac_goi_y.py). Tắt thì mô
    # hình vẫn gợi ý loại và mức ưu tiên; phòng nó đoán chỉ nằm trong ghi chú để đo.
    suggest_department_from_model: bool = False

    # --- Gợi ý người xử lý (#318) ----------------------------------------------
    #
    # Không cần mô hình ngôn ngữ: điểm tính từ nhật ký và danh bạ. Mỗi ứng viên — người của đúng phòng
    # nhận được việc — được điểm `trọng số kinh nghiệm × ln(1 + số hồ sơ cùng loại đã làm xong)` trừ
    # `trọng số tải × số việc đang giữ`; điểm cao nhất được gợi ý. Tắt thì ô chọn như trước.
    assignee_suggest_enabled: bool = True
    assignee_suggest_load_weight: float = 1.0
    assignee_suggest_experience_weight: float = 1.0
    # Kinh nghiệm chỉ đếm hồ sơ làm xong trong chừng này ngày gần nhất — người đã lâu không làm loại
    # này thì kinh nghiệm cũ không còn đáng kể
    assignee_suggest_history_days: int = 365

    # --- Hồ sơ đã giải quyết tương tự (#319, ADR-0008 đợt 2) -------------------
    #
    # Mô hình nhúng chạy ở dịch vụ riêng `mo-hinh-nhung` (llama.cpp, hồ sơ `tri-tue`). Địa chỉ rỗng là
    # TẮT: không lập chỉ mục, biểu mẫu Gửi yêu cầu không hiện gợi ý nào, mọi thứ khác như cũ.
    embedding_url: str = ""
    embedding_model: str = "qwen3-embedding-0.6b-q8_0"
    # Qwen3-Embedding nhúng câu hỏi kèm một lời dặn tác vụ, tài liệu thì không (thẻ mô hình của Qwen).
    # Lời dặn viết tiếng Anh như khuyến nghị của nhà phát triển; đổi mô hình thì đổi chuỗi này.
    embedding_query_instruction: str = (
        "Given an internal IT or administrative support request, retrieve previously resolved "
        "requests that describe the same problem"
    )
    # Hạn chót một lần nhúng ở bộ lập chỉ mục — chạy nền, không ai chờ
    embedding_timeout_seconds: float = 20.0
    # Hạn chót một lần tìm từ biểu mẫu: người gửi đang gõ, quá hạn thì không hiện gì
    similar_timeout_seconds: float = 2.0
    similar_max_results: int = 3
    # Độ tương đồng cosine tối thiểu để một hồ sơ được hiện — dưới ngưỡng là không liên quan
    similar_min_score: float = 0.55
    # Bộ lập chỉ mục bù theo khuôn `nhip_quet.py`: nhặt hồ sơ mới đóng đạt chưa có trong chỉ mục
    similar_index_enabled: bool = True
    similar_index_interval_seconds: int = 60
    similar_index_batch_size: int = 16
    # Người gửi xem gợi ý mà quá chừng này phút không gửi hồ sơ thì tính là bỏ không gửi (ngăn chặn)
    similar_abandon_after_minutes: int = 30

    # --- Kho tri thức (#321, ADR-0006) -----------------------------------------
    #
    # Wiki.js chạy dưới hồ sơ Compose `tri-thuc`. Địa chỉ công khai rỗng là TẮT: thanh bên không có lối
    # vào, không lập chỉ mục bài, gợi ý khi soạn chỉ có hồ sơ đã giải quyết như trước. Bộ lập chỉ mục bài
    # cần thêm mô hình nhúng (`embedding_url`); thiếu nó thì có lối vào nhưng không gợi ý bài.
    wiki_public_url: str = ""
    # Địa chỉ trong mạng Compose để đọc bài qua GraphQL
    wiki_internal_url: str = "http://kho-tri-thuc:3000"
    # Khóa API chỉ đọc do bước khởi tạo (infra/tri-thuc/khoi_tao.py) ghi vào volume chung
    wiki_api_key_file: str = "/run/tri-thuc/wiki-api-key"
    # Chiến lược đăng nhập của Wiki.js: lối vào trên thanh bên mở /login/<khóa> để vào thẳng qua Keycloak
    wiki_strategy_key: str = "keycloak"
    # Mã nguồn của Wiki.js đang chạy (AGPL-3.0) — cổng hiện đường dẫn này cạnh lối vào và gợi ý bài
    wiki_source_url: str = "https://github.com/requarks/wiki/tree/v2.5.315"
    wiki_timeout_seconds: float = 10.0
    wiki_index_interval_seconds: int = 120
    wiki_index_batch_size: int = 8
    # Số ký tự đầu của bài đem nhúng — đủ phần mô tả vấn đề, không cần cả bài
    wiki_embed_chars: int = 1500
    wiki_max_results: int = 2
    # Độ tương đồng cosine tối thiểu để một bài được gợi ý
    wiki_min_score: float = 0.55

    # --- Khuyến nghị cải tiến bằng câu chữ (#320) -------------------------------
    #
    # Mô hình sinh văn bản (`llm_url`) viết vài câu khuyến nghị từ kết quả khai phá quy trình. Sinh ở
    # nền, màn quy trình thực tế không chờ; tắt hay mô hình tắt thì màn chỉ có câu kết luận tất định.
    recommendation_enabled: bool = True
    # Hạn chót một lần sinh — chạy nền, nên rộng hơn hạn của gợi ý phân loại
    recommendation_timeout_seconds: float = 90.0
    recommendation_max_tokens: int = 400
    # Số câu khuyến nghị tối đa mô hình được viết; câu sai số bị bỏ nên có thể hiện ít hơn
    recommendation_max_sentences: int = 4
    # Bộ nhớ đệm theo khoảng ngày, phạm vi và chính kết quả khai phá: cùng dữ liệu thì không hỏi lại
    recommendation_cache_size: int = 64
    # Lần sinh hỏng (mô hình không tới được, quá hạn) nhớ chừng này giây rồi mới thử lại
    recommendation_retry_after_seconds: int = 120

    @property
    def embedding_enabled(self) -> bool:
        return bool(self.embedding_url.strip())

    @property
    def wiki_enabled(self) -> bool:
        return bool(self.wiki_public_url.strip())

    @property
    def wiki_index_stale_threshold_seconds(self) -> int:
        return BOI_SO_CHU_KY_QUA_LAU * self.wiki_index_interval_seconds

    @property
    def similar_index_stale_threshold_seconds(self) -> int:
        return BOI_SO_CHU_KY_QUA_LAU * self.similar_index_interval_seconds

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_url.strip())

    @property
    def suggest_scan_stale_threshold_seconds(self) -> int:
        """Ngưỡng "quá lâu" của bộ quét gợi ý, cùng cách tính với bộ quét hạn."""
        return BOI_SO_CHU_KY_QUA_LAU * self.suggest_scan_interval_seconds

    # --- Định danh tập trung, xem ADR-0001 và #43 --------------------------
    #
    # Vì sao hai địa chỉ khác nhau cho cùng một Keycloak: trình duyệt đi qua
    # `localhost:8080`, còn container đi qua `keycloak:8080`. Token do Keycloak phát
    # luôn mang địa chỉ công khai trong claim `iss`, nên dịch vụ phải đối chiếu `iss`
    # với địa chỉ công khai, trong khi tự đi lấy khóa qua địa chỉ nội bộ.
    #
    # Dùng nhầm một trong hai sẽ cho lỗi "Invalid issuer" hoặc "Connection refused",
    # và cả hai đều tốn thời gian truy.
    oidc_issuer: str = "http://localhost:8080/realms/dx-os-lab"
    oidc_jwks_url: str = (
        "http://keycloak:8080/realms/dx-os-lab/protocol/openid-connect/certs"
    )

    # Token phải mang đúng tên dịch vụ trong claim `aud`. Mặc định Keycloak đặt
    # `aud = "account"`, nên realm có một protocol mapper thêm giá trị này vào.
    oidc_audience: str = "dx-api"

    # Phòng ban của người dùng lấy từ claim `groups`, dưới dạng đường dẫn đầy đủ như
    # `/phong-ban/it`. Tiền tố để cấu hình được vì doanh nghiệp triển khai có thể tổ
    # chức cây group theo cách khác — mã nguồn không được giả định cấu trúc đó.
    oidc_department_group_prefix: str = "/phong-ban/"

    # Khoảng lệch đồng hồ chấp nhận được khi kiểm hạn token, tính bằng giây.
    oidc_leeway_seconds: int = 10

    # --- Danh bạ người dùng, xem #84 ---------------------------------------
    #
    # Đường thứ hai sang Keycloak, khác hẳn đường kiểm token ở trên. Kiểm token chạy ở
    # MỌI yêu cầu nên phải cục bộ; tra danh bạ chỉ chạy khi trưởng phòng mở ô chọn
    # người xử lý, hay khi nhân viên xem liên hệ của người gửi (#131), nên được phép gọi
    # mạng. Lý do đầy đủ ở app/auth/directory.py.
    #
    # Chỉ dịch vụ đi đường này, trình duyệt thì không — nên dùng địa chỉ nội bộ.
    keycloak_internal_url: str = "http://keycloak:8080"
    keycloak_realm: str = "dx-os-lab"

    # Client riêng, mang đúng một quyền chỉ đọc `view-users`. Không dùng chung với
    # `dx-api`: client đó là nơi nhận token của người dùng, không có lý do gì để nó
    # đọc được cả danh bạ.
    directory_client_id: str = "dx-directory"
    directory_client_secret: str = ""

    # Trần thời gian cho CẢ một lần tra, không phải cho từng lần gọi. Một lần tra gồm
    # vài lần gọi nối tiếp; đặt trần riêng cho từng lần thì Keycloak treo sẽ giữ trang
    # lâu bằng mấy lần trần cộng lại.
    directory_timeout_seconds: float = 3.0

    # Ủy quyền khi vắng mặt (#252): khoảng dài nhất một lần khai, tính bằng ngày. Ủy quyền dài hơn thế
    # là thay người phụ trách, việc của danh bạ chứ không của ủy quyền tạm thời.
    delegation_max_days: int = 60

    # Tên thuộc tính người dùng chứa số điện thoại (#131), khai trong user profile của
    # realm. Doanh nghiệp đặt tên khác — `mobile`, `phone` — thì đổi ở đây.
    directory_phone_attribute: str = "phoneNumber"

    # --- Theo dõi SLA, xem #42 --------------------------------------------
    #
    # Ngưỡng SLA của từng loại yêu cầu nằm trong bảng `request_types`, và trạng thái
    # nào làm đồng hồ chạy nằm ở cột `states.sla_running`. Ở đây chỉ có tham số vận
    # hành: bộ quét chạy hay không, và bao lâu một lần.
    sla_scan_enabled: bool = True

    # Sáu mươi giây là đủ mịn cho ngưỡng tính bằng giờ. Giảm xuống vài giây khi cần
    # trình diễn việc tự leo thang mà không phải ngồi chờ.
    sla_scan_interval_seconds: int = 60

    # --- Nhịp bộ quét và ngưỡng cảnh báo, xem #253 ----------------------------
    #
    # Chạy nhiều bản dịch vụ thì mỗi lượt chỉ một bản quét (khóa tư vấn của PostgreSQL), bản kia
    # bỏ lượt. Mỗi lượt ghi nhịp vào bảng `scanner_heartbeats`; `/health` báo `degraded` khi bộ
    # quét im quá lâu hoặc hỏng liên tiếp. Hai con số dưới đây là ngưỡng đó.
    #
    # Quá bao nhiêu giây không có lượt quét thành công thì coi là quá lâu. 0 là để dịch vụ tự tính
    # bằng `BOI_SO_CHU_KY_QUA_LAU` lần chu kỳ quét: đổi chu kỳ thì ngưỡng đi theo, không phải nhớ
    # sửa hai chỗ.
    sla_scan_stale_after_seconds: int = 0

    # Số lượt quét hỏng liên tiếp tới mức coi bộ quét là đang hỏng
    sla_scan_max_consecutive_errors: int = 3

    # --- Giới hạn tốc độ, xem #243 ---------------------------------------------
    #
    # Mỗi giới hạn là một cặp: số lần tối đa mỗi người dùng trong một cửa sổ thời gian cố định.
    # Vượt thì dịch vụ trả 429 kèm `Retry-After`. Đặt số lần tối đa bằng 0 để tắt giới hạn đó.
    # Bộ đếm nằm trong PostgreSQL nên đúng khi chạy nhiều bản dịch vụ.
    #
    # Mặc định đủ rộng để người dùng thật không bao giờ chạm tới, mà vẫn chặn một vòng lặp hay một
    # nút bấm bị kẹt gửi hàng trăm hồ sơ mỗi phút.
    rate_limit_create_case_max: int = 30
    rate_limit_create_case_window_seconds: int = 60
    rate_limit_upload_max: int = 20
    rate_limit_upload_window_seconds: int = 60
    rate_limit_message_max: int = 60
    rate_limit_message_window_seconds: int = 60
    # Một lần gọi thao tác hàng loạt (#440) đi tới `bulk_max_cases` hồ sơ, nên giới hạn đếm theo lô
    rate_limit_bulk_max: int = 10
    rate_limit_bulk_window_seconds: int = 60

    # --- Thao tác hàng loạt ở buồng lái điều phối, xem #440 ------------------
    #
    # Điều phối viên chọn nhiều hồ sơ rồi đi một bước cho cả lô. Mỗi hồ sơ vẫn qua cửa chuyển trạng
    # thái duy nhất, một giao dịch riêng — xem app/workflow/coordination.py. Đây chỉ là tham số vận
    # hành: lô lớn nhất, và những bước nào được làm hàng loạt. Mã bước là `transitions.activity_code`
    # của bộ quy tắc; bước nào không có cạnh của vai điều phối thì không hiện ra.
    bulk_max_cases: int = Field(default=50, ge=1)
    bulk_activities: str = "classify,route-to-department"

    # --- Đánh giá mức hài lòng, xem #433 --------------------------------------
    #
    # Người gửi chấm 1–5 kèm nhận xét khi xác nhận hồ sơ hoàn tất, đều tùy chọn. Cạnh nào cho chấm là dữ
    # liệu (`transitions.collects_feedback`); ở đây chỉ trần độ dài nhận xét, tính bằng ký tự.
    feedback_comment_max_chars: int = Field(default=1000, ge=1)

    # --- Khóa trùng lặp cho lệnh của lõi, xem #426 -------------------------------
    #
    # Hệ thống tích hợp gửi tiêu đề `Idempotency-Key` ở lệnh tạo hồ sơ và bước chuyển của `/core/v1`; gọi lặp
    # cùng khóa trả lại kết quả đã lưu, không chạy lệnh lần hai — xem app/workflow/khoa_trung_lap.py. Khóa sống
    # chừng này giờ; một lần đang chạy giữ khóa chừng này giây, quá thì coi là bỏ dở và lần sau chiếm lại.
    idempotency_ttl_hours: int = Field(default=24, ge=1)
    idempotency_lock_seconds: int = Field(default=60, ge=1)

    @property
    def bulk_activity_codes(self) -> list[str]:
        """Các mã bước làm được hàng loạt, theo thứ tự khai — thứ tự nút trên thanh thao tác."""
        return list(dict.fromkeys(ma.strip() for ma in self.bulk_activities.split(",") if ma.strip()))

    @property
    def sla_scan_stale_threshold_seconds(self) -> int:
        """Ngưỡng "quá lâu không quét thành công" đang áp dụng, tính bằng giây."""
        if self.sla_scan_stale_after_seconds > 0:
            return self.sla_scan_stale_after_seconds
        return BOI_SO_CHU_KY_QUA_LAU * self.sla_scan_interval_seconds

    # --- Tệp đính kèm, xem #80 và ADR-0002 ----------------------------------
    #
    # Tệp nằm trong SeaweedFS, gọi qua S3 API chuẩn bằng boto3 — không nhúng thư viện của
    # SeaweedFS, không dùng API riêng của nó. Đổi nền tảng lưu trữ (Garage, MinIO) chỉ là
    # đổi bốn giá trị dưới đây. Địa chỉ là địa chỉ NỘI BỘ trong mạng Compose: trình duyệt
    # không bao giờ nói chuyện với kho, tệp đi qua dịch vụ ứng dụng để quyền kiểm ở mỗi lần.
    s3_endpoint: str = "http://seaweedfs:8333"
    s3_access_key: str = "dxlab_access_key"
    s3_secret_key: str = ""
    s3_bucket: str = "dxlab-attachments"
    # SeaweedFS không dùng vùng, nhưng chữ ký S3 vẫn đòi một giá trị
    s3_region: str = "us-east-1"

    # --- Lưu trữ lạnh, xem #378 -------------------------------------------------
    #
    # Bộ quét theo khuôn `nhip_quet.py` xuất nhật ký sự kiện và hồ sơ đã kết thúc của mỗi tháng đã khép
    # ra kho đối tượng (CSV gzip + manifest.json có mã băm). Bản lưu đã niêm phong thì không ghi đè.
    archive_enabled: bool = True
    # Một giờ là đủ: mỗi tháng chỉ có một bản, lượt không có việc chỉ là vài truy vấn nhỏ
    archive_interval_seconds: int = 3600
    # Tháng đã khép: cũ hơn chừng này tháng so với tháng hiện tại (UTC). 1 — tháng trước trở về trước.
    # Tối thiểu 1: tháng đang chạy còn nhận sự kiện, chưa niêm phong được.
    archive_min_age_months: int = Field(default=1, ge=1)
    # Số tháng tối đa mỗi lượt, để lần đầu bật trên cụm có nhiều năm dữ liệu không giữ khóa quá lâu
    archive_max_months_per_run: int = Field(default=6, ge=1)
    # Thùng rỗng là dùng chung thùng tệp đính kèm: khóa S3 mẫu chỉ có quyền tạo đúng thùng đó
    # (infra/seaweedfs/s3-config.json). Thùng riêng thì cấp thêm `Admin:<tên thùng>` ở tệp đó.
    archive_bucket: str = ""
    archive_prefix: str = "luu-tru-lanh/"

    @property
    def archive_bucket_name(self) -> str:
        return self.archive_bucket.strip() or self.s3_bucket

    @property
    def archive_stale_threshold_seconds(self) -> int:
        return BOI_SO_CHU_KY_QUA_LAU * self.archive_interval_seconds

    # Giới hạn tệp đính kèm là cấu hình triển khai, không phải mã (CLAUDE.md mục 1.2). Giao
    # diện hỏi dịch vụ giới hạn thay vì tự giữ bản sao — xem GET /attachments/policy.
    attachment_allowed_extensions: str = (
        "png,jpg,jpeg,gif,webp,pdf,doc,docx,xls,xlsx,txt,csv"
    )
    attachment_max_mb: int = 10
    attachment_max_files: int = 5
    attachment_max_files_per_case: int = 20

    # --- Quét mã độc tệp đính kèm, xem #248 -------------------------------------
    #
    # ClamAV là dịch vụ TÙY CHỌN (hồ sơ Compose `quet-tep`), gọi qua giao thức mạng của clamd —
    # app/storage/quet_ma_doc.py. Địa chỉ rỗng là TẮT, mặc định của cụm: không quét, tệp đi như cũ.
    clamav_host: str = ""
    clamav_port: int = 3310
    # Hạn chót cho cả một lần quét. Tệp tối đa vài chục MB, clamd quét trong vài giây
    clamav_timeout_seconds: float = 15.0
    # Quét bật mà clamd không phản hồi thì làm gì: `accept` — nhận tệp, gắn cờ "chưa quét", ghi
    # nhật ký (mặc định: dịch vụ tùy chọn hỏng không được chặn người gửi bổ sung hồ sơ); `reject` —
    # từ chối lần tải, cho nơi coi quét là bắt buộc. Lý do ở ARCHITECTURE.md mục tệp đính kèm.
    clamav_on_unavailable: Literal["accept", "reject"] = "accept"

    # --- Thông báo thư điện tử, xem #251 ---------------------------------------
    #
    # Máy chủ thư rỗng là TẮT — mặc định của cụm: không xếp hàng, không gửi gì, bộ quét gửi không
    # chạy. Hồ sơ Compose `thu-thu` có Mailpit làm hộp thư thử (SMTP_HOST=thu-thu, cổng 1025).
    # Loại thông báo, tiêu đề, nội dung nằm trong DỮ LIỆU (bảng `notification_types`, infra/seed/05).
    smtp_host: str = ""
    smtp_port: int = 25
    smtp_username: str = ""
    smtp_password: str = ""
    # `none` (Mailpit, máy chủ nội bộ), `starttls` (cổng 587), `ssl` (cổng 465)
    smtp_security: Literal["none", "starttls", "ssl"] = "none"
    smtp_from: str = "DX-OS Lab <khong-tra-loi@dx-os-lab.test>"
    smtp_timeout_seconds: float = 10.0
    # Nhịp bộ quét gửi: phát hiện mốc báo trước, tìm người nhận, gửi thư đến hạn
    notify_scan_interval_seconds: int = 30
    # Số lần thử gửi tối đa một thư, và giây chờ trước lần thử kế (nhân đôi mỗi lần)
    notify_max_attempts: int = 5
    notify_retry_after_seconds: int = 60
    # Số thư tối đa mỗi lượt, để một hàng đợi dồn không giữ khóa quét quá lâu
    notify_batch_size: int = 50
    # Danh sách người của danh bạ được nhớ chừng này giây giữa các lượt gửi
    notify_directory_cache_seconds: int = 120

    @property
    def notify_enabled(self) -> bool:
        return bool(self.smtp_host.strip())

    @property
    def notify_scan_stale_threshold_seconds(self) -> int:
        return BOI_SO_CHU_KY_QUA_LAU * self.notify_scan_interval_seconds

    # --- Bảng điều khiển phân tích nhúng trong cổng, xem #305 và ADR-0003 ---------
    #
    # Hai địa chỉ cho cùng một Superset, như Keycloak ở trên: dịch vụ xin token khách qua địa chỉ
    # nội bộ, còn trình duyệt tải bảng điều khiển nhúng từ địa chỉ công khai — dịch vụ trả địa
    # chỉ đó cho cổng cùng với token, để giao diện không giữ cấu hình nào.
    superset_internal_url: str = "http://superset:8088"
    superset_public_url: str = "http://localhost:8088"
    # Tài khoản quản trị của Superset, chỉ dùng để xin token khách. Người xem không bao giờ
    # đăng nhập Superset: danh tính và vai trò vẫn đến từ token Keycloak của cổng.
    superset_admin_user: str = "admin"
    superset_admin_password: str = ""
    # Dashboard nhúng, tra theo `slug` trong tệp cấu hình ở infra/superset/bang-dieu-khien/
    superset_dashboard_slug: str = "van-hanh-yeu-cau"
    # Gốc của cổng — Superset chỉ cho trang này nhúng bảng điều khiển (allowed_domains)
    portal_public_url: str = "http://localhost:3000"
    superset_timeout_seconds: float = 5.0

    # --- Cập nhật thời gian thực, xem #387 và app/thoi_gian_thuc.py -----------------------
    #
    # Nhịp gửi dòng giữ kết nối khi không có tín hiệu: phải ngắn hơn hạn chờ đọc của cổng API
    # (GATEWAY_TIMEOUT_SECONDS) và của mọi proxy đứng trước, không thì luồng bị cắt giữa chừng.
    realtime_keepalive_seconds: float = 15.0
    # Luồng tự đóng sau chừng này giây; trình duyệt nối lại ngay, bằng token mới. Nhờ vậy không có
    # luồng nào sống lâu hơn hạn của access token đã mở nó (Keycloak mặc định 5 phút).
    realtime_max_stream_seconds: float = 240.0
    # Mỗi luồng giữ riêng một kết nối PostgreSQL để LISTEN. Quá số này thì từ chối 503 và cổng quay
    # về hỏi định kỳ — không để luồng ăn hết kết nối mà các lời gọi khác cần.
    realtime_max_streams: int = 40

    # --- Webhook — truyền phát sự kiện ra ngoài, xem #390 và app/webhook.py ---------------
    #
    # Bộ gửi luôn chạy (không đăng ký nào thì một lượt chỉ là hai câu truy vấn rỗng). Đặt chu kỳ 0 để tắt.
    webhook_scan_interval_seconds: int = 5
    # Mỗi lượt xét tối đa chừng này sự kiện cho mỗi đăng ký, và gửi tối đa chừng này lần
    webhook_batch_size: int = 100
    # Hạn chờ một bên nhận trả lời. Ngắn: một bên nhận chậm không được giữ cả lượt
    webhook_timeout_seconds: float = 5.0
    # Thử lại khi hỏng: chờ `webhook_retry_after_seconds`, nhân đôi mỗi lần, tối đa `webhook_max_attempts`
    # lần rồi đánh dấu hỏng hẳn
    webhook_max_attempts: int = 6
    webhook_retry_after_seconds: int = 10

    @property
    def webhook_enabled(self) -> bool:
        return self.webhook_scan_interval_seconds > 0

    @property
    def webhook_scan_stale_threshold_seconds(self) -> int:
        return BOI_SO_CHU_KY_QUA_LAU * self.webhook_scan_interval_seconds


@lru_cache
def get_settings() -> Settings:
    """Đọc cấu hình đúng một lần cho cả vòng đời tiến trình."""
    return Settings()
