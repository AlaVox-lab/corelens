# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bộ dữ liệu ĐÁP ÁN BIẾT TRƯỚC cho dịch vụ khai phá (#314).
#
# Mọi mã trạng thái, hoạt động, phòng ban ở đây là của BỘ QUY TẮC GIẢ của bài kiểm thử, không phải
# của sản phẩm: dịch vụ không biết tên nào, nó chỉ đi theo cờ trên cạnh. Bộ dữ liệu được nạp vào bốn
# BẢNG TẠM trùng tên với bảng thật (`bao_cao_nhat_ky`, `event_log`, `states`, `transitions`). Bảng tạm
# nằm ở `pg_temp`, được tra trước `public`, nên `doc_du_lieu` đọc dữ liệu của bài; cuối bài giao dịch bị
# hoàn tác, không gì còn lại và không gì ghi vào `public`.
#
# --- Bộ quy tắc giả (mã 901) -----------------------------------------------------------------------
#
#   moi (bắt đầu) → cho-1 → xu-ly → xong (kết thúc)
#   cho-1 → cho-2 → xu-ly            leo thang: cạnh hệ thống KHÔNG có hạn chờ
#   xu-ly → cho-kh → xu-ly           chờ bổ sung
#   cho-kh → huy (kết thúc)          tự đi khi hết hạn chờ: cạnh hệ thống CÓ hạn chờ
#   xu-ly → cho-1                    làm lại (is_rework)
#   xong → xu-ly                     mở lại (reopen_window_hours)
#   xu-ly → xu-ly                    tự trỏ: không thành cạnh đồ thị, không thành lượt mới
#
# --- Mười sáu hồ sơ, mốc giờ theo MÚI GIỜ CỦA LỊCH MẶC ĐỊNH (đọc từ bảng, không giả định) -------------
#
# Khoảng thử chính là thứ Hai 2026-03-09 tới thứ Sáu 2026-03-13. Giờ làm việc của lịch mẫu là
# 08:00-12:00 và 13:00-17:00 các ngày thứ Hai tới thứ Sáu, nên mọi mốc đặt trong giờ làm việc để số
# giây chờ tính tay được; bài `test_lich_dung_gia_dinh` kiểm đúng giả định đó trước hết.
#
#   hồ sơ  phòng  loại   đường đi (chỉ trạng thái vào)                          điểm đặc biệt
#   1      A      may    moi cho-1 xu-ly xong                                   luồng thường
#   2      A      may    moi cho-1 xu-ly xong                                   hai lần đổi ưu tiên: KHÔNG phải đặt phòng
#   3      A      may    moi cho-1 xu-ly xong                                   thêm một lần xu-ly → xu-ly (tự trỏ)
#   4      A      quyen  moi cho-1 xu-ly cho-1 xu-ly xong                       làm lại 1 lần
#   5      A      quyen  moi cho-1 (xu-ly cho-1)x2 xu-ly xong                   làm lại 2 lần
#   6      B      may    moi cho-1 cho-2 xu-ly xong                             leo thang
#   7      B      giay   moi cho-1 xu-ly cho-kh xu-ly xong                      chờ bổ sung, người đi tiếp
#   8      B      giay   moi cho-1 xu-ly cho-kh huy                             hết hạn chờ
#   9      A      quyen  moi cho-1 xu-ly xong xu-ly xong                        mở lại
#   10     B      may    moi cho-1 xu-ly xong                                   đặt phòng HAI lần (nhan, giao)
#   11     C      giay   moi cho-1 xu-ly xong                                   đặt phòng MỘT lần
#   12     A      quyen  moi cho-1 xu-ly cho-1 xu-ly xong                       gửi 23:59:59 ngày 08/03: NGOÀI khoảng
#   13     B      may    moi cho-1 xu-ly xong                                   gửi 00:00:00 ngày 14/03: NGOÀI khoảng
#   14     A      may    moi cho-1 xu-ly xong                                   gửi đúng 00:00:00 ngày 09/03: TRONG
#   15     B      giay   moi cho-1 xu-ly xong                                   gửi 23:59:59 ngày 13/03: TRONG (ngày cuối tính cả ngày)
#   16     rỗng   may    moi cho-1 xu-ly xong                                   chưa chuyển phòng
#
# Loại yêu cầu (may, quyen, giay) dùng cho phép tách nhóm của #315.
#
# Hồ sơ 12-15 đặt ở sát biên để bắt lỗi tính ngày theo UTC thay vì theo múi giờ của lịch. Mọi hồ sơ
# kết thúc ở trạng thái kết thúc, nên không lượt nào còn dở tính tới `now()` và đáp án không đổi theo giờ chạy.
#
# Đáp án từng phép kiểm nằm cạnh phép kiểm, ở các tệp test_*.py.

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import NamedTuple

import psycopg
from psycopg.types.json import Jsonb

from app.cau_hinh import CauHinh
from app.du_lieu import doc_du_lieu
from app.phan_tich import phan_tich

BO_QUY_TAC = 901
BAT_DAU = "moi"
KHOANG = (dt.date(2026, 3, 9), dt.date(2026, 3, 13))

# (mã, nhãn, bắt đầu, kết thúc, thứ tự hiển thị)
TRANG_THAI = (
    ("moi", "Mới", True, False, 1),
    ("cho-1", "Chờ cấp 1", False, False, 2),
    ("cho-2", "Chờ cấp 2", False, False, 3),
    ("xu-ly", "Đang xử lý", False, False, 4),
    ("cho-kh", "Chờ bổ sung", False, False, 5),
    ("xong", "Xong", False, True, 6),
    ("huy", "Hủy", False, True, 7),
)


class Canh(NamedTuple):
    hoat_dong: str
    tu: str
    den: str
    lam_lai: bool = False
    he_thong: bool = False
    han_cho: int | None = None
    mo_lai: int | None = None


CANH = (
    Canh("nhan", "moi", "cho-1"),
    Canh("giao", "cho-1", "xu-ly"),
    Canh("hoan-tat", "xu-ly", "xong"),
    Canh("tu-xet", "xu-ly", "xu-ly"),
    Canh("tra-lai", "xu-ly", "cho-1", lam_lai=True),
    Canh("len-cap", "cho-1", "cho-2", he_thong=True),
    Canh("giao-cap-2", "cho-2", "xu-ly"),
    Canh("can-bo-sung", "xu-ly", "cho-kh"),
    Canh("bo-sung", "cho-kh", "xu-ly"),
    Canh("het-han-cho", "cho-kh", "huy", he_thong=True, han_cho=48),
    Canh("mo-lai", "xong", "xu-ly", mo_lai=72),
)


class SuKienThu(NamedTuple):
    hoat_dong: str
    den: str
    luc: str  # giờ địa phương của lịch, "YYYY-MM-DD HH:MM:SS"
    thay_doi: dict | None = None


@dataclass(frozen=True)
class HoSoThu:
    ma: int
    phong: str | None
    loai: str
    tao: str
    su_kien: tuple[SuKienThu, ...]


def _sk(hoat_dong: str, den: str, luc: str, thay_doi: dict | None = None) -> SuKienThu:
    return SuKienThu(hoat_dong, den, luc, thay_doi)


HO_SO = (
    HoSoThu(1, "A", "may", "2026-03-09 09:00:00", (
        _sk("nhan", "cho-1", "2026-03-09 09:10:00"),
        _sk("giao", "xu-ly", "2026-03-09 10:00:00"),
        _sk("hoan-tat", "xong", "2026-03-09 11:00:00"),
    )),
    HoSoThu(2, "A", "may", "2026-03-09 09:00:00", (
        _sk("nhan", "cho-1", "2026-03-09 09:30:00"),
        _sk("giao", "xu-ly", "2026-03-09 10:30:00", {"priority_code": "cao"}),
        _sk("hoan-tat", "xong", "2026-03-09 11:30:00", {"priority_code": "thap"}),
    )),
    HoSoThu(3, "A", "may", "2026-03-10 08:30:00", (
        _sk("nhan", "cho-1", "2026-03-10 08:40:00"),
        _sk("giao", "xu-ly", "2026-03-10 09:00:00"),
        _sk("tu-xet", "xu-ly", "2026-03-10 09:30:00"),
        _sk("hoan-tat", "xong", "2026-03-10 10:00:00"),
    )),
    HoSoThu(4, "A", "quyen", "2026-03-10 09:00:00", (
        _sk("nhan", "cho-1", "2026-03-10 09:05:00"),
        _sk("giao", "xu-ly", "2026-03-10 09:45:00"),
        _sk("tra-lai", "cho-1", "2026-03-10 10:30:00"),
        _sk("giao", "xu-ly", "2026-03-10 11:00:00"),
        _sk("hoan-tat", "xong", "2026-03-10 11:30:00"),
    )),
    HoSoThu(5, "A", "quyen", "2026-03-10 13:00:00", (
        _sk("nhan", "cho-1", "2026-03-10 13:10:00"),
        _sk("giao", "xu-ly", "2026-03-10 13:30:00"),
        _sk("tra-lai", "cho-1", "2026-03-10 14:00:00"),
        _sk("giao", "xu-ly", "2026-03-10 14:20:00"),
        _sk("tra-lai", "cho-1", "2026-03-10 15:00:00"),
        _sk("giao", "xu-ly", "2026-03-10 15:20:00"),
        _sk("hoan-tat", "xong", "2026-03-10 16:00:00"),
    )),
    HoSoThu(6, "B", "may", "2026-03-11 09:00:00", (
        _sk("nhan", "cho-1", "2026-03-11 09:05:00"),
        _sk("len-cap", "cho-2", "2026-03-11 11:00:00"),
        _sk("giao-cap-2", "xu-ly", "2026-03-11 11:30:00"),
        _sk("hoan-tat", "xong", "2026-03-11 13:30:00"),
    )),
    HoSoThu(7, "B", "giay", "2026-03-11 13:00:00", (
        _sk("nhan", "cho-1", "2026-03-11 13:10:00"),
        _sk("giao", "xu-ly", "2026-03-11 13:40:00"),
        _sk("can-bo-sung", "cho-kh", "2026-03-11 14:00:00"),
        _sk("bo-sung", "xu-ly", "2026-03-11 15:30:00"),
        _sk("hoan-tat", "xong", "2026-03-11 16:30:00"),
    )),
    HoSoThu(8, "B", "giay", "2026-03-12 08:30:00", (
        _sk("nhan", "cho-1", "2026-03-12 08:40:00"),
        _sk("giao", "xu-ly", "2026-03-12 09:00:00"),
        _sk("can-bo-sung", "cho-kh", "2026-03-12 09:30:00"),
        _sk("het-han-cho", "huy", "2026-03-13 09:30:00"),
    )),
    HoSoThu(9, "A", "quyen", "2026-03-12 09:00:00", (
        _sk("nhan", "cho-1", "2026-03-12 09:05:00"),
        _sk("giao", "xu-ly", "2026-03-12 09:30:00"),
        _sk("hoan-tat", "xong", "2026-03-12 10:00:00"),
        _sk("mo-lai", "xu-ly", "2026-03-12 14:00:00"),
        _sk("hoan-tat", "xong", "2026-03-12 15:00:00"),
    )),
    HoSoThu(10, "B", "may", "2026-03-12 13:00:00", (
        _sk("nhan", "cho-1", "2026-03-12 13:10:00", {"department_code": "B"}),
        _sk("giao", "xu-ly", "2026-03-12 13:30:00", {"department_code": "B"}),
        _sk("hoan-tat", "xong", "2026-03-12 15:00:00"),
    )),
    HoSoThu(11, "C", "giay", "2026-03-13 09:00:00", (
        _sk("nhan", "cho-1", "2026-03-13 09:10:00", {"department_code": "C"}),
        _sk("giao", "xu-ly", "2026-03-13 09:40:00"),
        _sk("hoan-tat", "xong", "2026-03-13 10:40:00"),
    )),
    HoSoThu(12, "A", "quyen", "2026-03-08 23:59:59", (
        _sk("nhan", "cho-1", "2026-03-09 09:00:00"),
        _sk("giao", "xu-ly", "2026-03-09 09:30:00"),
        _sk("tra-lai", "cho-1", "2026-03-09 10:00:00"),
        _sk("giao", "xu-ly", "2026-03-09 10:30:00"),
        _sk("hoan-tat", "xong", "2026-03-09 11:00:00"),
    )),
    HoSoThu(13, "B", "may", "2026-03-14 00:00:00", (
        _sk("nhan", "cho-1", "2026-03-16 08:30:00"),
        _sk("giao", "xu-ly", "2026-03-16 09:00:00"),
        _sk("hoan-tat", "xong", "2026-03-16 09:30:00"),
    )),
    HoSoThu(14, "A", "may", "2026-03-09 00:00:00", (
        _sk("nhan", "cho-1", "2026-03-09 09:00:00"),
        _sk("giao", "xu-ly", "2026-03-09 09:30:00"),
        _sk("hoan-tat", "xong", "2026-03-09 10:00:00"),
    )),
    HoSoThu(15, "B", "giay", "2026-03-13 23:59:59", (
        _sk("nhan", "cho-1", "2026-03-16 09:00:00"),
        _sk("giao", "xu-ly", "2026-03-16 09:30:00"),
        _sk("hoan-tat", "xong", "2026-03-16 10:00:00"),
    )),
    HoSoThu(16, None, "may", "2026-03-13 10:00:00", (
        _sk("nhan", "cho-1", "2026-03-13 10:10:00"),
        _sk("giao", "xu-ly", "2026-03-13 10:40:00"),
        _sk("hoan-tat", "xong", "2026-03-13 11:10:00"),
    )),
)

TAO_BANG = (
    """CREATE TEMP TABLE states (
        rule_set_id smallint, code text, label text, is_initial boolean, is_terminal boolean,
        display_order smallint)""",
    """CREATE TEMP TABLE transitions (
        id integer, rule_set_id smallint, from_state text, to_state text, activity_code text,
        is_system boolean, is_rework boolean, reopen_window_hours smallint, auto_after_hours smallint)""",
    """CREATE TEMP TABLE event_log (
        id bigint, case_id bigint, activity text, "timestamp" timestamptz, actor text,
        from_state text, to_state text, changes jsonb)""",
    """CREATE TEMP TABLE bao_cao_nhat_ky (
        case_id bigint, activity text, "timestamp" timestamptz, actor text, from_state text,
        to_state text, department_code text, rule_set_id smallint, thu_tu bigint,
        request_type_code text)""",
)

CAU_MOC = "%s::timestamp AT TIME ZONE %s"


def nap(ket_noi: psycopg.Connection, mui_gio: str) -> None:
    """Nạp bộ dữ liệu vào bốn bảng tạm của phiên. Phiên phải mở ở chế độ đọc-ghi và KHÔNG được commit."""
    with ket_noi.cursor() as c:
        for cau in TAO_BANG:
            c.execute(cau)
        for ma, nhan, bat_dau, ket_thuc, thu_tu in TRANG_THAI:
            c.execute("INSERT INTO states VALUES (%s, %s, %s, %s, %s, %s)",
                      (BO_QUY_TAC, ma, nhan, bat_dau, ket_thuc, thu_tu))
        for stt, canh in enumerate(CANH, 1):
            c.execute("INSERT INTO transitions VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                      (stt, BO_QUY_TAC, canh.tu, canh.den, canh.hoat_dong, canh.he_thong,
                       canh.lam_lai, canh.mo_lai, canh.han_cho))
        ma_su_kien = 0
        for ho_so in HO_SO:
            hien_tai = BAT_DAU
            c.execute(
                f"INSERT INTO bao_cao_nhat_ky VALUES (%s, 'create-case', {CAU_MOC}, 'nguoi-gui', NULL, %s, %s, %s, 0, %s)",
                (ho_so.ma, ho_so.tao, mui_gio, BAT_DAU, ho_so.phong, BO_QUY_TAC, ho_so.loai),
            )
            for sk in ho_so.su_kien:
                ma_su_kien += 1
                c.execute(
                    f"INSERT INTO event_log VALUES (%s, %s, %s, {CAU_MOC}, 'nguoi-xu-ly', %s, %s, %s)",
                    (ma_su_kien, ho_so.ma, sk.hoat_dong, sk.luc, mui_gio, hien_tai, sk.den,
                     Jsonb(sk.thay_doi) if sk.thay_doi is not None else None),
                )
                c.execute(
                    f"INSERT INTO bao_cao_nhat_ky VALUES (%s, %s, {CAU_MOC}, 'nguoi-xu-ly', %s, %s, %s, %s, %s, %s)",
                    (ho_so.ma, sk.hoat_dong, sk.luc, mui_gio, hien_tai, sk.den, ho_so.phong,
                     BO_QUY_TAC, ma_su_kien, ho_so.loai),
                )
                hien_tai = sk.den


def cau_hinh_thu(bo_may, **ghi_de) -> CauHinh:
    """Cấu hình dựng tay cho phép phân tích: đổi con số qua đây chứ không qua biến môi trường."""
    gia_tri = {
        "database_uri": "",
        "bo_may": bo_may.ten,
        "boi_so_nghen": 2.0,
        "so_bien_the": 10,
        "so_ho_so_moi_nhom": 200,
    }
    gia_tri.update(ghi_de)
    return CauHinh(**gia_tri)


def chay_phan_tich(
    ket_noi: psycopg.Connection,
    bo_may,
    tu: dt.date = KHOANG[0],
    den: dt.date = KHOANG[1],
    phong: list[str] | None = None,
    **cau_hinh_ghi_de,
) -> dict:
    """Đọc dữ liệu rồi phân tích đúng như điểm vào HTTP làm, chỉ khác là cấu hình truyền thẳng vào."""
    du_lieu = doc_du_lieu(ket_noi, tu, den, phong)
    return phan_tich(du_lieu, bo_may, cau_hinh_thu(bo_may, **cau_hinh_ghi_de))


def luot_vao_cua(ho_so: HoSoThu) -> list[tuple[str, str]]:
    """Các lần hồ sơ VÀO một trạng thái: (trạng thái, giờ địa phương). Cạnh tự trỏ không tính."""
    luot = [(BAT_DAU, ho_so.tao)]
    hien_tai = BAT_DAU
    for sk in ho_so.su_kien:
        if sk.den != hien_tai:
            luot.append((sk.den, sk.luc))
        hien_tai = sk.den
    return luot


def giay_cho_mong_doi(
    ket_noi: psycopg.Connection, mui_gio: str, ma_ho_so: set[int]
) -> dict[str, list[int]]:
    """Thời gian chờ từng lượt ở trạng thái chưa kết thúc, tính RIÊNG bằng chính hàm `so_giay_lam_viec`
    của cơ sở dữ liệu (cùng phép đo với đồng hồ hạn). Lượt cuối của mọi hồ sơ thử là trạng thái kết
    thúc nên không có lượt dở."""
    ket_thuc = {ma for ma, _, _, kt, _ in TRANG_THAI if kt}
    ket_qua: dict[str, list[int]] = {}
    for ho_so in HO_SO:
        if ho_so.ma not in ma_ho_so:
            continue
        luot = luot_vao_cua(ho_so)
        assert luot[-1][0] in ket_thuc, "bộ dữ liệu thử: lượt cuối phải ở trạng thái kết thúc"
        for (trang_thai, vao), (_, ra) in zip(luot, luot[1:]):
            if trang_thai in ket_thuc:
                continue
            giay = ket_noi.execute(
                f"SELECT so_giay_lam_viec({CAU_MOC}, {CAU_MOC})", (vao, mui_gio, ra, mui_gio)
            ).fetchone()[0]
            ket_qua.setdefault(trang_thai, []).append(int(giay))
    return ket_qua
