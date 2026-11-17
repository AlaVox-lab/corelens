# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 AlaVox-lab
#
# Lớp đọc dữ liệu của dịch vụ khai phá: mọi câu SQL nằm ở đây, chỉ đọc.
#
# Nguồn là lớp báo cáo của không gian D — view `bao_cao_nhat_ky` (migration 0014), đã có sẵn sự kiện
# mở đầu dựng từ thời điểm tạo hồ sơ — cộng cấu hình của bộ quy tắc. Không câu nào biết tên trạng
# thái hay vai trò: mọi phân loại đi theo cờ trên cạnh mà hồ sơ đã thật sự đi qua.
#
# Một lần khai phá chỉ đọc hồ sơ của MỘT quy trình (#376): view mang cột `process_code`, bỏ trống thì quy
# trình mặc định của ứng dụng (`processes.is_app_default`). Trộn nhật ký hai quy trình vào một mô hình sẽ
# vẽ ra một luồng không có thật.
#
#   is_rework                       — cạnh làm lại (#153)
#   is_system, auto_after_hours     — hệ thống tự đi: KHÔNG có hạn chờ là leo thang do quá hạn,
#                                     CÓ hạn chờ là tự đi khi hết hạn chờ (cùng tiêu chí với bộ quét)
#   reopen_window_hours             — cạnh mở lại sau khi kết thúc (#102)
#   event_log.changes.department_code — lần chuyển trạng thái này đặt phòng ban phụ trách
#
# Cạnh của một sự kiện ghép theo (bộ quy tắc, từ, đến, mã hoạt động): một cặp trạng thái có thể có cả
# cạnh người lẫn cạnh hệ thống, mã hoạt động phân biệt hai cạnh đó. Mỗi hồ sơ xét theo bộ quy tắc của
# chính nó. Thời gian chờ đo bằng `so_giay_lam_viec` — cùng phép đo với đồng hồ hạn và bảng điều khiển.

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

CAU_MUI_GIO = "SELECT time_zone FROM work_calendars WHERE is_default"

# Sự kiện mở đầu trong view mang thứ tự 0 (dựng từ requests.created_at, không phải dòng nhật ký)
CAU_SU_KIEN = """
WITH ho_so AS (
    SELECT case_id
    FROM bao_cao_nhat_ky
    WHERE thu_tu = 0
      AND timestamp >= %(tu)s::timestamp AT TIME ZONE %(mui_gio)s
      AND timestamp < (%(den)s::date + 1)::timestamp AT TIME ZONE %(mui_gio)s
      AND (%(tat_ca)s OR department_code = ANY(%(phong)s::text[]))
      AND process_code = coalesce(%(quy_trinh)s::text, (SELECT code FROM processes WHERE is_app_default))
)
SELECT n.case_id, n.thu_tu, n.activity, n.timestamp, n.from_state, n.to_state, n.rule_set_id,
       n.request_type_code, n.department_code,
       coalesce(e.changes ? 'department_code', FALSE) AS doi_phong,
       coalesce(t.is_rework, FALSE) AS lam_lai,
       coalesce(t.is_system AND t.auto_after_hours IS NULL, FALSE) AS leo_thang,
       coalesce(t.is_system AND t.auto_after_hours IS NOT NULL, FALSE) AS het_han_cho,
       coalesce(t.reopen_window_hours IS NOT NULL, FALSE) AS mo_lai
FROM bao_cao_nhat_ky n
JOIN ho_so h ON h.case_id = n.case_id
LEFT JOIN event_log e ON e.id = n.thu_tu AND n.thu_tu > 0
LEFT JOIN transitions t
       ON t.rule_set_id = n.rule_set_id AND t.from_state = n.from_state
      AND t.to_state = n.to_state AND t.activity_code = n.activity
ORDER BY n.case_id, n.timestamp, n.thu_tu
"""

# Mỗi lần hồ sơ VÀO một trạng thái (sự kiện mở đầu, hay sự kiện đổi trạng thái — cạnh tự trỏ của
# ADR-0005 không tính) là một lượt; lượt kết thúc khi hồ sơ vào trạng thái kế. Lượt còn dở tính tới
# bây giờ, để hồ sơ đang kẹt vẫn hiện ra. Trạng thái kết thúc không có thời gian chờ.
CAU_LUOT = """
WITH ho_so AS (
    SELECT case_id
    FROM bao_cao_nhat_ky
    WHERE thu_tu = 0
      AND timestamp >= %(tu)s::timestamp AT TIME ZONE %(mui_gio)s
      AND timestamp < (%(den)s::date + 1)::timestamp AT TIME ZONE %(mui_gio)s
      AND (%(tat_ca)s OR department_code = ANY(%(phong)s::text[]))
      AND process_code = coalesce(%(quy_trinh)s::text, (SELECT code FROM processes WHERE is_app_default))
),
vao AS (
    SELECT n.case_id, n.rule_set_id, n.to_state, n.timestamp AS luc_vao, n.thu_tu,
           lead(n.timestamp) OVER (PARTITION BY n.case_id ORDER BY n.timestamp, n.thu_tu) AS luc_ra
    FROM bao_cao_nhat_ky n
    JOIN ho_so h ON h.case_id = n.case_id
    WHERE n.from_state IS NULL OR n.from_state <> n.to_state
)
SELECT v.case_id, v.to_state, v.luc_vao, s.is_terminal,
       CASE WHEN s.is_terminal THEN NULL
            ELSE so_giay_lam_viec(v.luc_vao, coalesce(v.luc_ra, now())) END AS so_giay
FROM vao v
JOIN states s ON s.rule_set_id = v.rule_set_id AND s.code = v.to_state
ORDER BY v.case_id, v.luc_vao, v.thu_tu
"""

# Nhãn và cờ của trạng thái: một mã có ở nhiều bộ quy tắc thì lấy bộ mới nhất
CAU_TRANG_THAI = """
SELECT DISTINCT ON (code) code, label, is_initial, is_terminal, display_order
FROM states
WHERE rule_set_id = ANY(%(bo)s)
ORDER BY code, rule_set_id DESC
"""

# Luồng chính theo thiết kế: cạnh người, không làm lại, không phải cạnh mở lại, có đổi trạng thái
CAU_LUONG_CHINH = """
SELECT DISTINCT from_state, to_state
FROM transitions
WHERE rule_set_id = ANY(%(bo)s)
  AND NOT is_rework AND NOT is_system AND reopen_window_hours IS NULL
  AND from_state <> to_state
ORDER BY from_state, to_state
"""


@dataclass(frozen=True)
class SuKien:
    ho_so: int
    hoat_dong: str
    luc: dt.datetime
    tu: str | None
    den: str
    bo_quy_tac: int
    doi_phong: bool
    lam_lai: bool
    leo_thang: bool
    het_han_cho: bool
    mo_lai: bool

    @property
    def doi_trang_thai(self) -> bool:
        """Sự kiện đưa hồ sơ vào một trạng thái — sự kiện mở đầu hay cạnh không tự trỏ."""
        return self.tu is None or self.tu != self.den


@dataclass(frozen=True)
class Luot:
    ho_so: int
    trang_thai: str
    luc_vao: dt.datetime
    ket_thuc: bool
    so_giay: int | None


@dataclass(frozen=True)
class TrangThai:
    ma: str
    nhan: str
    bat_dau: bool
    ket_thuc: bool
    thu_tu: int


@dataclass(frozen=True)
class HoSo:
    """Thuộc tính của hồ sơ dùng để tách nhóm (#315). View báo cáo lấy hai mã này từ `requests` ở
    mọi dòng, nên đó là loại và phòng HIỆN TẠI của hồ sơ — hồ sơ chưa chuyển phòng có phòng rỗng."""

    loai: str | None
    phong: str | None


@dataclass(frozen=True)
class DuLieu:
    su_kien: list[SuKien]
    luot: list[Luot]
    trang_thai: dict[str, TrangThai]
    luong_chinh: list[tuple[str, str]]
    ho_so: dict[int, HoSo]


def doc_du_lieu(
    ket_noi: psycopg.Connection,
    tu: dt.date,
    den: dt.date,
    phong: list[str] | None,
    quy_trinh: str | None = None,
) -> DuLieu:
    """Đọc mọi thứ phân tích cần cho hồ sơ gửi từ ngày `tu` tới hết ngày `den`, trong phạm vi phòng
    (None là toàn công ty), của một quy trình (None là quy trình mặc định của ứng dụng). Ngày tính theo
    múi giờ của lịch làm việc mặc định — cùng múi giờ với giờ làm việc — chứ không theo UTC. Một giao
    dịch chỉ đọc, nên mọi câu thấy cùng một ảnh dữ liệu."""
    with ket_noi.cursor(row_factory=dict_row) as c:
        mui_gio = c.execute(CAU_MUI_GIO).fetchone()
        tham_so = {"tu": tu, "den": den, "tat_ca": phong is None, "phong": phong or [],
                   "mui_gio": mui_gio["time_zone"] if mui_gio else "UTC", "quy_trinh": quy_trinh}
        su_kien: list[SuKien] = []
        ho_so: dict[int, HoSo] = {}
        for d in c.execute(CAU_SU_KIEN, tham_so):
            su_kien.append(SuKien(
                ho_so=d["case_id"], hoat_dong=d["activity"], luc=d["timestamp"], tu=d["from_state"],
                den=d["to_state"], bo_quy_tac=d["rule_set_id"], doi_phong=d["doi_phong"],
                lam_lai=d["lam_lai"], leo_thang=d["leo_thang"], het_han_cho=d["het_han_cho"],
                mo_lai=d["mo_lai"],
            ))
            ho_so.setdefault(d["case_id"], HoSo(loai=d["request_type_code"], phong=d["department_code"]))
        luot = [
            Luot(ho_so=d["case_id"], trang_thai=d["to_state"], luc_vao=d["luc_vao"],
                 ket_thuc=d["is_terminal"], so_giay=d["so_giay"])
            for d in c.execute(CAU_LUOT, tham_so)
        ]
        bo = sorted({s.bo_quy_tac for s in su_kien})
        trang_thai = {
            d["code"]: TrangThai(ma=d["code"], nhan=d["label"], bat_dau=d["is_initial"],
                                 ket_thuc=d["is_terminal"], thu_tu=d["display_order"])
            for d in c.execute(CAU_TRANG_THAI, {"bo": bo})
        }
        luong_chinh = [(d["from_state"], d["to_state"]) for d in c.execute(CAU_LUONG_CHINH, {"bo": bo})]
    return DuLieu(su_kien=su_kien, luot=luot, trang_thai=trang_thai, luong_chinh=luong_chinh, ho_so=ho_so)


def mo_ket_noi(database_uri: str) -> psycopg.Connection:
    """Kết nối chỉ đọc. Tài khoản riêng vốn chỉ có quyền SELECT; đặt chỉ đọc ở phiên nữa cho chắc."""
    ket_noi = psycopg.connect(database_uri, connect_timeout=5)
    ket_noi.read_only = True
    return ket_noi
