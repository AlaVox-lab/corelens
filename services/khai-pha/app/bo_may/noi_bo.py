# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Bộ máy khai phá dự phòng: Python thuần, chỉ dùng thư viện chuẩn (ADR-0007, #314).
#
# Vai trò: lối thoát khi giảng viên hay doanh nghiệp không nhận ranh giới AGPL của PM4Py. Đặt
# KHAI_PHA_BO_MAY=noi_bo và xóa dòng pm4py khỏi requirements.txt là dịch vụ chạy tiếp, dịch vụ ứng
# dụng và cổng không phải sửa gì. Tệp này không nhập pm4py, pandas hay thư viện khai phá nào.
#
# Hai việc duy nhất của giao diện BoMay, đều đơn giản tới mức tự viết gọn hơn kéo cả thư viện:
#
#   đồ thị trực tiếp — mỗi hồ sơ xếp các lượt vào trạng thái theo (lúc, thứ tự), đếm mỗi cặp liền kề
#   biến thể         — chuỗi trạng thái của từng hồ sơ, gom các hồ sơ đi đúng cùng một chuỗi
#
# Phải cho ĐÚNG y hệt BoMayPm4py trên cùng đầu vào (cùng khóa, cùng số, cùng danh sách hồ sơ đã xếp
# tăng dần): bài kiểm thử có đáp án biết trước chạy trên cả hai và so từng khóa.

from __future__ import annotations

from collections import Counter, defaultdict

from . import LuotVao


def _chuoi_theo_ho_so(luot: list[LuotVao]) -> dict[int, list[str]]:
    """Trạng thái hồ sơ đã vào, theo thứ tự thời gian; hai lượt cùng thời điểm xếp theo `thu_tu`."""
    theo_ho_so: dict[int, list[LuotVao]] = defaultdict(list)
    for l in luot:
        theo_ho_so[l.ho_so].append(l)
    return {
        ho_so: [l.trang_thai for l in sorted(cac_luot, key=lambda l: (l.luc, l.thu_tu))]
        for ho_so, cac_luot in theo_ho_so.items()
    }


class BoMayNoiBo:
    ten = "noi_bo"

    def do_thi(self, luot: list[LuotVao]) -> dict[tuple[str, str], int]:
        so_lan: Counter[tuple[str, str]] = Counter()
        for chuoi in _chuoi_theo_ho_so(luot).values():
            so_lan.update(zip(chuoi, chuoi[1:]))
        return dict(so_lan)

    def bien_the(self, luot: list[LuotVao]) -> dict[tuple[str, ...], list[int]]:
        ket_qua: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for ho_so, chuoi in _chuoi_theo_ho_so(luot).items():
            ket_qua[tuple(chuoi)].append(ho_so)
        return {chuoi: sorted(ho_so) for chuoi, ho_so in ket_qua.items()}
