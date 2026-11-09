# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấu hình dịch vụ ứng dụng, đọc từ biến môi trường.
#
# Không có giá trị nghiệp vụ nào ở đây. Trạng thái, vai trò, phòng ban, ngưỡng SLA
# đều nằm trong bảng dữ liệu — xem ARCHITECTURE.md mục 5. Tệp này chỉ giữ những thứ
# thuộc môi trường triển khai: chuỗi kết nối, cổng, mức ghi nhật ký.

from functools import lru_cache

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
    app_name: str = "DX-OS Lab — Cổng vận hành yêu cầu nội bộ"
    app_version: str = "0.3.0"

    # Bật chế độ gỡ lỗi của SQLAlchemy. Không bao giờ bật ở bản triển khai thật.
    database_echo: bool = False

    # Thư mục dữ liệu khởi tạo (infra/seed/ gắn vào container), bộ nạp đọc lần đầu dựng cụm (#254)
    seed_dir: str = "/seed"

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

    # Giới hạn tệp đính kèm là cấu hình triển khai, không phải mã (CLAUDE.md mục 1.2). Giao
    # diện hỏi dịch vụ giới hạn thay vì tự giữ bản sao — xem GET /attachments/policy.
    attachment_allowed_extensions: str = (
        "png,jpg,jpeg,gif,webp,pdf,doc,docx,xls,xlsx,txt,csv"
    )
    attachment_max_mb: int = 10
    attachment_max_files: int = 5
    attachment_max_files_per_case: int = 20

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


@lru_cache
def get_settings() -> Settings:
    """Đọc cấu hình đúng một lần cho cả vòng đời tiến trình."""
    return Settings()
