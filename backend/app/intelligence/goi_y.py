# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Gợi ý của hệ thống cho trường quyết định, và dấu giữ hay ghi đè (#239).
#
# Nguyên tắc của đề tài: hệ thống chỉ gợi ý, con người quyết định (CLAUDE.md mục 4.3). Gợi ý
# không bao giờ tự ghi vào trường quyết định. Nó điền sẵn ô chọn; người xác nhận bằng chính thao
# tác của quy trình, và cửa chuyển trạng thái ghi lại họ giữ hay đổi giá trị gợi ý.
#
# Một hàm cho mỗi trường có gợi ý. Màn điều phối và cửa chuyển trạng thái gọi CÙNG hàm, nên thứ
# người dùng thấy trên thẻ và thứ được đem so lúc ghi nhật ký không bao giờ lệch nhau.
#
# Thứ tự nguồn: cột `suggested_*` của hồ sơ có giá trị (tầng I ghi về sau, #317) thì dùng nó;
# trống thì tra bảng ánh xạ của dữ liệu khởi tạo. Không nguồn nào có gì thì không có gợi ý, và
# thao tác vẫn đi bình thường — đường chỉnh tay luôn mở.

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Request
from app.models.workflow_config import Department, RequestType, RequestTypeRouting

# Mã nguồn ghi vào nhật ký. Đây là từ vựng của hệ thống — nơi gợi ý sinh ra — chứ không phải
# cấu hình nghiệp vụ, nên nằm trong mã như tên cột.
NGUON_BANG_ANH_XA = "routing"
NGUON_MO_HINH = "model"

NHAN_NGUON = {
    NGUON_BANG_ANH_XA: "Bảng ánh xạ loại yêu cầu",
    NGUON_MO_HINH: "Mô hình phân loại",
}


@dataclass(frozen=True)
class GoiY:
    """Dữ liệu của một gợi ý: giá trị, lý do, nguồn, độ tin cậy.

    `confidence` để trống khi nguồn không có con số thật — bảng ánh xạ không có độ tin cậy, và
    giao diện không được vẽ một con số giả.
    """

    field: str
    code: str
    label: str
    reason: str
    source: str
    confidence: float | None = None

    @property
    def source_label(self) -> str:
        return NHAN_NGUON.get(self.source, self.source)


def _phong_dang_hoat_dong(session: Session, ma: str | None) -> Department | None:
    if not ma:
        return None
    phong = session.get(Department, ma)
    return phong if phong is not None and phong.is_active else None


def goi_y_phong_theo_loai(session: Session, ma_loai: str | None) -> GoiY | None:
    """Phòng mặc định của một loại yêu cầu trong bảng ánh xạ, kèm lý do."""
    if not ma_loai:
        return None
    dong = session.execute(
        select(Department, RequestType)
        .join(RequestTypeRouting, RequestTypeRouting.department_code == Department.code)
        .join(RequestType, RequestType.code == RequestTypeRouting.request_type_code)
        .where(
            RequestTypeRouting.request_type_code == ma_loai,
            RequestTypeRouting.is_default,
            Department.is_active,
        )
    ).first()
    if dong is None:
        return None
    phong, loai = dong
    return GoiY(
        field="department_code",
        code=phong.code,
        label=phong.label,
        reason=f"Loại “{loai.label}” mặc định chuyển về phòng này.",
        source=NGUON_BANG_ANH_XA,
    )


def goi_y_phong(session: Session, ho_so: Request, ma_loai: str | None) -> GoiY | None:
    """Gợi ý phòng ban cho hồ sơ, với loại yêu cầu `ma_loai` — loại cuối cùng của hồ sơ.

    Phía gọi truyền loại vì lúc chuyển trạng thái, điều phối viên có thể đổi loại ngay trong
    cùng thao tác: gợi ý phải theo loại mới, đúng như thẻ trên màn hình đã đổi theo.
    """
    phong = _phong_dang_hoat_dong(session, ho_so.suggested_department_code)
    if phong is not None:
        return GoiY(
            field="department_code",
            code=phong.code,
            label=phong.label,
            reason="Mô hình phân loại gợi ý từ nội dung hồ sơ.",
            source=NGUON_MO_HINH,
        )
    return goi_y_phong_theo_loai(session, ma_loai)


# Trường quyết định nào có gợi ý, và hàm sinh gợi ý cho nó. Thêm gợi ý cho trường mới — loại
# yêu cầu, mức ưu tiên, người xử lý (#317, #318) — là thêm một dòng ở đây.
_NGUON_GOI_Y: dict[str, Callable[[Session, Request, str | None], GoiY | None]] = {
    "department_code": goi_y_phong,
}


def ghi_nhan_goi_y(session: Session, ho_so: Request, thay_doi: dict) -> dict | None:
    """Dấu giữ hay ghi đè cho lần chuyển trạng thái sắp ghi nhật ký.

    Gọi từ cửa chuyển trạng thái, sau khi mọi ràng buộc đã qua và `thay_doi` đã đủ. Mỗi trường
    có gợi ý mà người dùng gửi kèm thì ghi một mục `{suggested, chosen, overridden, source,
    confidence}` — kể cả khi giá trị gửi trùng giá trị hồ sơ đang có, vì người dùng vẫn đã xác
    nhận nó. Trường không gửi kèm, hay không có gợi ý nào, thì không ghi gì. Trả `None` khi rỗng.
    """
    ma_loai = thay_doi.get("request_type_code", ho_so.request_type_code)
    dau: dict = {}
    for truong, sinh in _NGUON_GOI_Y.items():
        if truong not in thay_doi:
            continue
        goi_y = sinh(session, ho_so, ma_loai)
        if goi_y is None:
            continue
        chon = thay_doi[truong]
        dau[truong] = {
            "suggested": goi_y.code,
            "chosen": chon,
            "overridden": chon != goi_y.code,
            "source": goi_y.source,
            "confidence": goi_y.confidence,
        }
    return dau or None
