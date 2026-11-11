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
# Thứ tự nguồn: cột `suggested_*` của hồ sơ có giá trị (mô hình ngôn ngữ ghi, #317 — xem
# `phan_loai.py`) thì dùng nó; trống thì tra bảng ánh xạ của dữ liệu khởi tạo — hiện chỉ phòng ban có
# bảng ánh xạ. Không nguồn nào có gì thì không có gợi ý, và thao tác vẫn đi bình thường — đường chỉnh
# tay luôn mở.

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Request
from app.models.workflow_config import Department, Priority, RequestType, RequestTypeRouting

# Mã nguồn ghi vào nhật ký. Đây là từ vựng của hệ thống — nơi gợi ý sinh ra — chứ không phải
# cấu hình nghiệp vụ, nên nằm trong mã như tên cột.
NGUON_BANG_ANH_XA = "routing"
NGUON_MO_HINH = "model"
# Gợi ý người xử lý (#318): điểm từ số việc đang giữ và kinh nghiệm với loại yêu cầu
NGUON_TAI_VIEC = "workload"

NHAN_NGUON = {
    NGUON_BANG_ANH_XA: "Bảng ánh xạ loại yêu cầu",
    NGUON_MO_HINH: "Mô hình phân loại",
    NGUON_TAI_VIEC: "Tải việc và kinh nghiệm",
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


LY_DO_MO_HINH_MAC_DINH = "Mô hình phân loại gợi ý từ nội dung hồ sơ."


def _ly_do_mo_hinh(ho_so: Request, truong: str) -> str:
    """Câu lý do mô hình viết cho trường này (#317), lưu trong `suggestion_note`. Ghi chú thiếu hay
    hỏng thì lùi về một câu chung — lý do là phần giải thích, không được làm mất gợi ý."""
    ghi_chu = ho_so.suggestion_note if isinstance(ho_so.suggestion_note, dict) else {}
    ly_do = (ghi_chu.get("reasons") or {}).get(truong) if ghi_chu.get("ok") else None
    return ly_do if isinstance(ly_do, str) and ly_do.strip() else LY_DO_MO_HINH_MAC_DINH


def goi_y_phong(session: Session, ho_so: Request, ma_loai: str | None) -> GoiY | None:
    """Gợi ý phòng ban cho hồ sơ, với loại yêu cầu `ma_loai` — loại cuối cùng của hồ sơ.

    Phía gọi truyền loại vì lúc chuyển trạng thái, điều phối viên có thể đổi loại ngay trong
    cùng thao tác: gợi ý phải theo loại mới, đúng như thẻ trên màn hình đã đổi theo.

    Cột `suggested_department_code` chỉ được tầng I ghi khi cờ "phòng ban theo mô hình" bật (#317,
    `DXLAB_SUGGEST_DEPARTMENT_FROM_MODEL`) — cờ tắt thì cột trống và gợi ý theo bảng ánh xạ.
    """
    phong = _phong_dang_hoat_dong(session, ho_so.suggested_department_code)
    if phong is not None:
        return GoiY(
            field="department_code",
            code=phong.code,
            label=phong.label,
            reason=_ly_do_mo_hinh(ho_so, "department_code"),
            source=NGUON_MO_HINH,
        )
    return goi_y_phong_theo_loai(session, ma_loai)


def goi_y_loai(session: Session, ho_so: Request, ma_loai: str | None = None) -> GoiY | None:
    """Gợi ý loại yêu cầu của mô hình (#317). Chỉ một nguồn: không có bảng ánh xạ nào cho loại.
    Loại đã ngừng dùng từ sau lúc gợi ý thì không gợi ý nữa."""
    ma = ho_so.suggested_request_type_code
    loai = session.get(RequestType, ma) if ma else None
    if loai is None or not loai.is_active:
        return None
    return GoiY(
        field="request_type_code",
        code=loai.code,
        label=loai.label,
        reason=_ly_do_mo_hinh(ho_so, "request_type_code"),
        source=NGUON_MO_HINH,
    )


def goi_y_uu_tien(session: Session, ho_so: Request, ma_loai: str | None = None) -> GoiY | None:
    """Gợi ý mức ưu tiên của mô hình (#317). Mức mặc định của bảng không phải gợi ý — nó chỉ là
    giá trị điền sẵn khi không có gợi ý, nên không ghi giữ hay ghi đè cho nó."""
    ma = ho_so.suggested_priority_code
    muc = session.get(Priority, ma) if ma else None
    if muc is None:
        return None
    return GoiY(
        field="priority_code",
        code=muc.code,
        label=muc.label,
        reason=_ly_do_mo_hinh(ho_so, "priority_code"),
        source=NGUON_MO_HINH,
    )


def goi_y_nguoi_xu_ly(session: Session, ho_so: Request, ma_loai: str | None = None) -> GoiY | None:
    """Gợi ý người xử lý (#318), đọc từ cột `suggested_assignee_id` và ghi chú đi kèm.

    Không gọi danh bạ ở đây: cửa chuyển trạng thái gọi hàm này lúc ghi nhật ký, và engine không gọi
    ra ngoài. Tên và lý do đã được `nguoi_xu_ly.py` ghi cùng lúc tính — lúc hồ sơ về phòng, và lại
    lúc trưởng phòng mở ô chọn — nên thẻ trên màn và dấu giữ hay ghi đè đọc cùng một giá trị. Ghi chú
    phải nói về đúng người trong cột; lệch thì coi như không có gợi ý.
    """
    ma = ho_so.suggested_assignee_id
    ghi_chu = ho_so.assignee_suggestion if isinstance(ho_so.assignee_suggestion, dict) else {}
    if not ma or ghi_chu.get("id") != ma:
        return None
    return GoiY(
        field="assignee_id",
        code=ma,
        label=str(ghi_chu.get("label") or ma),
        reason=str(ghi_chu.get("reason") or ""),
        source=NGUON_TAI_VIEC,
    )


# Trường quyết định nào có gợi ý, và hàm sinh gợi ý cho nó. Thêm gợi ý cho một trường mới là thêm
# một dòng ở đây.
_NGUON_GOI_Y: dict[str, Callable[[Session, Request, str | None], GoiY | None]] = {
    "request_type_code": goi_y_loai,
    "priority_code": goi_y_uu_tien,
    "department_code": goi_y_phong,
    "assignee_id": goi_y_nguoi_xu_ly,
}


def ghi_nhan_goi_y(
    session: Session, ho_so: Request, thay_doi: dict, actor_id: str | None = None
) -> dict | None:
    """Dấu giữ hay ghi đè cho lần chuyển trạng thái sắp ghi nhật ký.

    Gọi từ cửa chuyển trạng thái, sau khi mọi ràng buộc đã qua và `thay_doi` đã đủ. Mỗi trường
    có gợi ý mà người dùng gửi kèm thì ghi một mục `{suggested, chosen, overridden, source,
    confidence}` — kể cả khi giá trị gửi trùng giá trị hồ sơ đang có, vì người dùng vẫn đã xác
    nhận nó. Trường không gửi kèm, hay không có gợi ý nào, thì không ghi gì. Trả `None` khi rỗng.

    Người thực hiện là chính người gửi hồ sơ (`actor_id`) thì không ghi gì: người gửi không bao giờ
    thấy thẻ gợi ý, nên lần họ sửa loại yêu cầu ở cạnh Sửa nội dung không phải là giữ hay ghi đè
    gợi ý — tính vào thì tỷ lệ ghi đè của loại yêu cầu (#317) sai.
    """
    if actor_id is not None and actor_id == ho_so.requester_id:
        return None
    ma_loai = thay_doi.get("request_type_code", ho_so.request_type_code)
    dau: dict = {}
    for truong, sinh in _NGUON_GOI_Y.items():
        # Ô để trống — nhận hồ sơ mà chưa giao ai — không phải một lựa chọn khác gợi ý
        if thay_doi.get(truong) in (None, ""):
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
