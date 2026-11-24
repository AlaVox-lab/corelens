# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Tên hiển thị Corelens trong mẫu thư thông báo (#538).
#
# Mã bản sửa    : 0039_ten_hien_thi_corelens
# Sửa đổi từ    : 0038_nhat_ky_truy_cap
#
# Dự án đổi tên hiển thị thành Corelens ngày 19/11; định danh kỹ thuật (realm `dx-os-lab`, tiền tố `dxlab`) giữ
# nguyên. Mẫu tiêu đề và chân thư của ba loại thông báo nằm trong DỮ LIỆU (`notification_types`, infra/seed/05),
# chỉ nạp lúc dựng cụm — cụm đã dựng vẫn gửi thư "[DX-OS Lab] …". Bản sửa này đổi chúng ở cụm cũ.
#
# CÓ ĐIỀU KIỆN: chỉ đổi ô còn NGUYÊN VĂN chữ cũ của seed. Quản trị viên đã sửa lời thư thì ô đó khác chữ cũ và
# được giữ — bản sửa không ghi đè lựa chọn của doanh nghiệp. `downgrade` đổi ngược với cùng điều kiện. Cụm mới
# dựng chưa có dòng nào lúc migration chạy (bộ nạp chạy seed sau), nên bản sửa không làm gì ở đó.
#
# Chỉ đổi dữ liệu, không đổi lược đồ: nâng cấp bằng `up -d --build`, không `down -v`.

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_ten_hien_thi_corelens"
down_revision: str | None = "0038_nhat_ky_truy_cap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEN_CU = "DX-OS Lab"
TEN_MOI = "Corelens"
CHAN_THU = "\n\n— Thư tự động từ {ten}. Tắt loại thư này ở trang Thông báo của cổng."

# Nguyên văn seed 05 trước #538, với `{ten}` ở chỗ tên hiển thị: (mã loại, mẫu tiêu đề, mẫu nội dung)
MAU_THU = [
    (
        "viec-cho-toi",
        "[{ten}] $ma_ho_so chờ bạn: $buoc",
        'Chào $ten_nguoi_nhan,\n\nHồ sơ $ma_ho_so "$tieu_de" đang ở trạng thái "$trang_thai" và chờ bạn: $buoc.'
        "\n\nMở cổng để xử lý: $lien_ket" + CHAN_THU,
    ),
    (
        "sap-tu-dong",
        "[{ten}] $ma_ho_so sẽ $canh_tu_dong lúc $han_tu_dong",
        'Chào $ten_nguoi_nhan,\n\nHồ sơ $ma_ho_so "$tieu_de" đang chờ bạn ở trạng thái "$trang_thai" ($buoc). '
        "Nếu không ai thao tác, hệ thống sẽ $canh_tu_dong lúc $han_tu_dong.\n\nMở cổng để xử lý: $lien_ket"
        + CHAN_THU,
    ),
    (
        "da-tu-dong",
        "[{ten}] $ma_ho_so: $canh_tu_dong",
        'Chào $ten_nguoi_nhan,\n\nHồ sơ $ma_ho_so "$tieu_de" của bạn vừa được hệ thống chuyển từ "$tu_trang_thai" '
        'sang "$trang_thai" ($canh_tu_dong) vì hết hạn chờ mà chưa ai thao tác.\n\nXem hồ sơ: $lien_ket'
        + CHAN_THU,
    ),
]

_DOI = {
    cot: sa.text(
        f"UPDATE notification_types SET {cot} = :moi WHERE code = :ma AND {cot} = :cu"
    )
    for cot in ("subject_template", "body_template")
}


def doi_mau_thu(ket_noi: sa.Connection, tu: str, sang: str) -> int:
    """Đổi tên hiển thị `tu` thành `sang` ở mẫu thư còn nguyên văn bản seed mang tên `tu`. Trả số ô đã đổi.

    Tách khỏi `upgrade` để bài kiểm gọi thẳng trên giao dịch của nó (backend/tests/test_ten_hien_thi.py)."""
    so = 0
    for ma, tieu_de, noi_dung in MAU_THU:
        for cot, mau in (("subject_template", tieu_de), ("body_template", noi_dung)):
            so += ket_noi.execute(
                _DOI[cot], {"ma": ma, "cu": mau.format(ten=tu), "moi": mau.format(ten=sang)}
            ).rowcount
    return so


def upgrade() -> None:
    doi_mau_thu(op.get_bind(), TEN_CU, TEN_MOI)


def downgrade() -> None:
    doi_mau_thu(op.get_bind(), TEN_MOI, TEN_CU)
