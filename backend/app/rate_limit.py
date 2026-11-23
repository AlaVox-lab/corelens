# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Giới hạn tốc độ cho các điểm cuối ghi nhạy cảm (#243): tạo hồ sơ, tải tệp lên, gửi lời nhắn.
#
# Bộ đếm nằm trong PostgreSQL (bảng `rate_limit_hits`), không trong bộ nhớ tiến trình: dịch vụ ứng
# dụng có thể chạy nhiều bản, và hai bản mà mỗi bản tự đếm thì giới hạn thực tế thành gấp đôi.
#
# Cửa sổ thời gian CỐ ĐỊNH, không trượt. Đổi lại sự thô — người dùng có thể gọi dồn gấp đôi quanh
# ranh giới hai cửa sổ — là một câu lệnh nguyên tử duy nhất, `INSERT ... ON CONFLICT DO UPDATE ...
# RETURNING`, đúng dưới tải đồng thời mà không cần khóa. Với mục đích chặn vòng lặp kẹt hay lạm
# dụng thô, độ thô đó chấp nhận được.
#
# Khóa đếm theo người dùng (`Actor.id`) và tên giới hạn, nên hai người dùng đếm riêng, và tạo hồ sơ
# không ăn vào hạn mức gửi lời nhắn. Con số của từng giới hạn là cấu hình triển khai (`config.py`),
# không nằm trong hàm.

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.config import get_settings
from app.db import get_session
from app.workflow.context import Actor

# Mỗi giới hạn: tiền tố các biến cấu hình, và cụm từ chỉ việc đang làm để đặt vào câu thông báo
# ("Bạn <việc> quá nhanh"). Thêm một giới hạn mới là thêm hai biến vào `Settings` và một dòng ở đây.
DANH_MUC: dict[str, tuple[str, str]] = {
    "create-case": ("rate_limit_create_case", "gửi yêu cầu"),
    "upload-attachment": ("rate_limit_upload", "tải tệp lên"),
    "send-message": ("rate_limit_message", "gửi lời nhắn"),
    "bulk-transition": ("rate_limit_bulk", "thao tác hàng loạt"),
}

# Dòng đếm cũ được giữ thêm chừng này lần cửa sổ dài nhất trước khi dọn
HE_SO_GIU_DONG_CU = 2


@dataclass(frozen=True, slots=True)
class GioiHan:
    ten: str
    toi_da: int
    cua_so_giay: int
    viec: str


def gioi_han(ten: str) -> GioiHan:
    """Giới hạn đang áp dụng cho `ten`, đọc từ cấu hình ở thời điểm gọi."""
    cau_hinh = get_settings()
    tien_to, viec = DANH_MUC[ten]
    return GioiHan(
        ten=ten,
        toi_da=getattr(cau_hinh, f"{tien_to}_max"),
        cua_so_giay=getattr(cau_hinh, f"{tien_to}_window_seconds"),
        viec=viec,
    )


def ghi_nhan_luot_goi(
    session: Session,
    ten: str,
    khoa: str,
    cua_so_giay: int,
    luc: dt.datetime | None = None,
) -> tuple[int, int]:
    """Đếm thêm một lượt gọi. Trả (số lượt trong cửa sổ hiện tại tính cả lượt này, số giây còn
    lại tới khi sang cửa sổ mới).

    `luc` là thời điểm xét, mặc định đồng hồ của cơ sở dữ liệu — mọi bản dịch vụ chia nhau một
    đồng hồ nên không lệch cửa sổ. Bài kiểm thử truyền một mốc tương lai để sang cửa sổ mới mà
    không phải ngồi chờ. Dùng `clock_timestamp()` chứ không `now()`: trong một giao dịch dài,
    `now()` đứng yên ở lúc giao dịch bắt đầu.
    """
    dong = session.execute(
        text(
            """
            INSERT INTO rate_limit_hits (key, window_start, hits)
            VALUES (
                :khoa,
                to_timestamp(
                    floor(extract(epoch FROM COALESCE(CAST(:luc AS timestamptz), clock_timestamp()))
                          / :cua_so) * :cua_so
                ),
                1
            )
            ON CONFLICT (key, window_start) DO UPDATE SET hits = rate_limit_hits.hits + 1
            RETURNING
                hits,
                ceil(extract(epoch FROM (
                    window_start + make_interval(secs => :cua_so)
                    - COALESCE(CAST(:luc AS timestamptz), clock_timestamp())
                )))::int AS con_lai
            """
        ),
        {"khoa": f"{ten}:{khoa}", "luc": luc, "cua_so": cua_so_giay},
    ).one()
    return dong.hits, max(1, dong.con_lai)


def don_dong_cu(session: Session) -> int:
    """Xóa các dòng đếm của những cửa sổ đã qua từ lâu. Trả số dòng đã xóa.

    Gọi từ vòng của bộ quét nền. Nhiều bản dịch vụ cùng dọn cũng vô hại: câu lệnh chỉ xóa dòng quá
    hạn, bản nào xóa trước thì bản sau thấy không còn gì.
    """
    cua_so_dai_nhat = max(gioi_han(ten).cua_so_giay for ten in DANH_MUC)
    giu_giay = max(60, HE_SO_GIU_DONG_CU * cua_so_dai_nhat)
    return session.execute(
        text(
            "DELETE FROM rate_limit_hits"
            " WHERE window_start < clock_timestamp() - make_interval(secs => :giu)"
        ),
        {"giu": giu_giay},
    ).rowcount


def gioi_han_toc_do(ten: str):
    """Dựng một phụ thuộc FastAPI giới hạn tốc độ cho giới hạn `ten`.

    Dùng ở decorator của điểm cuối: `dependencies=[Depends(gioi_han_toc_do("create-case"))]`. Phụ
    thuộc tự lấy người gọi, nên người chưa đăng nhập nhận 401 trước khi chạm tới bộ đếm.

    Bộ đếm ghi xong là COMMIT NGAY, không đợi điểm cuối: các điểm cuối của dự án gọi
    `session.rollback()` khi bị từ chối, và nếu lượt đếm nằm chung giao dịch thì chính những yêu
    cầu hỏng — loại lạm dụng cần chặn nhất — lại được đếm rồi bị hoàn tác. Cấu trúc này cũng
    chạy đúng trong bộ kiểm thử, nơi commit chỉ nhả điểm lưu của giao dịch ngoài.
    """
    if ten not in DANH_MUC:
        raise KeyError(f"Chưa khai giới hạn tốc độ '{ten}' trong DANH_MUC")

    def kiem_tra(
        session: Annotated[Session, Depends(get_session)],
        actor: Annotated[Actor, Depends(current_actor)],
    ) -> None:
        cau_hinh = gioi_han(ten)
        if cau_hinh.toi_da <= 0:
            return

        so_luot, con_lai = ghi_nhan_luot_goi(session, ten, actor.id, cau_hinh.cua_so_giay)
        session.commit()

        if so_luot > cau_hinh.toi_da:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate-limited",
                    "message": (
                        f"Bạn {cau_hinh.viec} quá nhanh. "
                        f"Thử lại sau {con_lai} giây."
                    ),
                },
                headers={"Retry-After": str(con_lai)},
            )

    return kiem_tra
