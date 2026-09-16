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

    # --- Theo dõi SLA, xem #42 --------------------------------------------
    #
    # Ngưỡng SLA của từng loại yêu cầu nằm trong bảng `request_types`, và trạng thái
    # nào làm đồng hồ chạy nằm ở cột `states.sla_running`. Ở đây chỉ có tham số vận
    # hành: bộ quét chạy hay không, và bao lâu một lần.
    sla_scan_enabled: bool = True

    # Sáu mươi giây là đủ mịn cho ngưỡng tính bằng giờ. Giảm xuống vài giây khi cần
    # trình diễn việc tự leo thang mà không phải ngồi chờ.
    sla_scan_interval_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    """Đọc cấu hình đúng một lần cho cả vòng đời tiến trình."""
    return Settings()
