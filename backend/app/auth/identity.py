# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Dựng tác nhân nghiệp vụ từ phần claim của token.
#
# Đây là chỗ nối giữa không gian `H` và không gian `P`: Keycloak là nguồn sự thật về
# AI mang vai trò nào và thuộc phòng nào, còn bảng `transitions` là nguồn sự thật về
# vai trò nào đi được cạnh nào. Hàm dưới đây dịch từ ngôn ngữ thứ nhất sang thứ hai.
#
# Hàm thuần, không đụng mạng lẫn cơ sở dữ liệu, nên kiểm thử được mà không cần dựng
# Keycloak.

from __future__ import annotations

from app.config import get_settings
from app.workflow.context import Actor

# Keycloak đặt tên người dùng của tài khoản dịch vụ là tiền tố này cộng mã client (viết thường) — từ vựng
# của Keycloak, không phải giá trị nghiệp vụ.
TIEN_TO_TAI_KHOAN_DICH_VU = "service-account-"


def _ten_hien_thi(claims: dict) -> str | None:
    """Tên ghi vào nhật ký và nhãn người gửi: claim `name`, rồi tới tên người dùng.

    Token của tài khoản dịch vụ (client credentials, #365) không có `name`, còn tên người dùng là
    `service-account-<mã client>`. Khi đó lấy mã client trong `azp` — hồ sơ do một ứng dụng khác tạo mang
    nhãn người gửi là tên ứng dụng đó. Chỉ nhận khi tên người dùng đúng là tài khoản dịch vụ của chính
    client phát token, để một người dùng thường không mượn được nhãn của ứng dụng. Muốn nhãn khác thì gắn
    claim `name` cho client trong Keycloak: claim đó luôn được ưu tiên.
    """
    if claims.get("name"):
        return claims["name"]
    ten = claims.get("preferred_username")
    client = claims.get("azp")
    if ten and client and ten.lower() == f"{TIEN_TO_TAI_KHOAN_DICH_VU}{client}".lower():
        return client
    return ten


def actor_from_claims(claims: dict, *, department_prefix: str | None = None) -> Actor:
    """Dịch claim của token thành một `Actor` mà engine hiểu được.

    Ba thứ được lấy ra:

    - `sub` → định danh người dùng, cũng là giá trị ghi vào cột `actor` của nhật ký
      sự kiện và cột `requester_id` của hồ sơ
    - `realm_access.roles` → tập vai trò
    - `groups` → tập mã phòng ban, sau khi cắt tiền tố đường dẫn

    Kèm tên hiển thị (`_ten_hien_thi`): token của tài khoản dịch vụ thiếu `name` và `groups`, vẫn dựng
    được tác nhân bình thường.

    Vai trò lấy nguyên xi, kể cả những vai trò mặc định của Keycloak như
    `offline_access` hay `uma_authorization`. Không lọc, vì engine chỉ giao nhau tập
    này với cột vai trò của từng cạnh — vai trò thừa không mở thêm cửa nào. Lọc ở đây
    sẽ buộc tầng định danh phải biết danh sách vai trò nghiệp vụ, tức là kéo một phụ
    thuộc từ `P` ngược lên `H`.

    Group nào không mang đúng tiền tố thì bỏ qua, vì doanh nghiệp triển khai có thể
    dùng cây group cho nhiều mục đích khác ngoài phòng ban.
    """
    tien_to = (
        department_prefix
        if department_prefix is not None
        else get_settings().oidc_department_group_prefix
    )

    vai_tro = claims.get("realm_access", {}).get("roles", [])

    phong_ban = {
        duong_dan[len(tien_to) :]
        for duong_dan in claims.get("groups", [])
        if duong_dan.startswith(tien_to) and len(duong_dan) > len(tien_to)
    }

    return Actor(
        id=claims["sub"],
        name=_ten_hien_thi(claims),
        roles=frozenset(vai_tro),
        departments=frozenset(phong_ban),
    )
