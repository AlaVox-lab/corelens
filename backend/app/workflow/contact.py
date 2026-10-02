# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Liên hệ người gửi cho nhân viên mở được hồ sơ (#131).
#
# Điều phối viên hay phòng ban thấy người gửi là "An Nguyễn" mà không có cách gọi nhanh
# khi cần hỏi thêm. Email và số điện thoại nằm ở Keycloak, nên tra danh bạ lúc mở trang
# chứ không chép vào hồ sơ: người gửi đổi số ở trang tài khoản thì lần mở sau thấy ngay
# số mới, và cơ sở dữ liệu nghiệp vụ không giữ thêm một bản thông tin cá nhân nào.
#
# Hai buồng lái mỗi bên có một điểm cuối riêng, đi đúng cửa nhìn thấy hồ sơ của buồng lái
# đó — điều phối thấy mọi hồ sơ, phòng ban chỉ thấy hồ sơ của phòng mình. Phần tra danh bạ
# và cách báo lỗi dùng chung ở đây. Cổng người gửi không có điểm cuối nào như vậy.
#
# Điểm cuối tách khỏi trang chi tiết là cố ý: danh bạ hỏng thì trang chi tiết vẫn mở, chỉ
# ô liên hệ báo không tra được — cùng nguyên tắc với ô chọn người xử lý ở #84.

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.auth.directory import DirectoryUnavailable, KeycloakDirectory
from app.models.case import Request
from app.workflow.schemas import LienHeNguoiGuiRa

logger = logging.getLogger(__name__)


def lien_he_nguoi_gui(danh_ba: KeycloakDirectory, ho_so: Request) -> LienHeNguoiGuiRa:
    """Tra liên hệ của người gửi hồ sơ. Phía gọi đã kiểm người này mở được hồ sơ.

    Danh bạ không trả lời thì 503 kèm lý do, không trả liên hệ rỗng: rỗng nghĩa là
    *người gửi chưa điền*, còn 503 nghĩa là *không biết* — gộp hai điều đó làm một là
    giả vờ ổn.
    """
    try:
        lien_he = danh_ba.contact(ho_so.requester_id)
    except DirectoryUnavailable as loi:
        logger.warning(
            "Không tra được liên hệ người gửi hồ sơ %s: %s", ho_so.id, loi.message
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "directory-unavailable", "message": loi.message},
        ) from loi

    if lien_he is None:
        return LienHeNguoiGuiRa(name=ho_so.requester_label, found=False)
    return LienHeNguoiGuiRa(
        name=ho_so.requester_label,
        email=lien_he.email,
        phone=lien_he.phone,
        found=True,
    )
