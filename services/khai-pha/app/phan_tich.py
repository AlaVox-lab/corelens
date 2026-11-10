# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Dựng kết quả khai phá từ dữ liệu đã đọc (app/du_lieu.py) và một bộ máy (app/bo_may/).
#
# Bộ máy lo phần thuật toán khai phá: đồ thị trực tiếp và biến thể. Mọi phần khác ở đây, chung cho
# cả hai bộ máy, và chỉ đi theo cờ trong dữ liệu:
#
#   nhánh lệch  — hồ sơ đi qua ít nhất một cạnh làm lại / leo thang / tự đi khi hết hạn chờ / mở lại,
#                 hay được đặt phòng ban phụ trách từ hai lần trở lên
#   luồng chính — sự kiện không thuộc nhánh nào ở trên; luồng chính THEO THIẾT KẾ đọc từ bộ quy tắc
#   điểm nghẽn  — trạng thái xếp theo thời gian chờ trung vị (giây làm việc); nghẽn khi trung vị ở đó
#                 gấp từ KHAI_PHA_BOI_SO_NGHEN lần trung vị chung của mọi lượt ở trạng thái chưa kết thúc
#   tách nhóm   — (#315) nhánh lệch và thời gian chờ tách theo loại yêu cầu và phòng hiện tại của hồ
#                 sơ, cùng danh sách hồ sơ chờ lâu nhất ở từng trạng thái, để màn quy trình thực tế nói
#                 được "nhiều nhất ở đâu" và mở được hồ sơ cụ thể
#
# Hợp đồng trả về (JSON, khóa tiếng Anh như mọi API của dự án) ghi ở docs/ARCHITECTURE.md mục 6.4.

from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from .bo_may import BoMay, LuotVao
from .cau_hinh import CauHinh
from .du_lieu import DuLieu

# Thứ tự các nhánh lệch trong kết quả; giao diện tra nhãn theo mã
NHANH_LECH = ("rework", "escalation", "wait_expiry", "reopen", "multiple_routing")
LOAI_CANH = ("main", "rework", "escalation", "wait_expiry", "reopen")


def _trung_vi(gia_tri: list[int]) -> int | None:
    return int(round(statistics.median(gia_tri))) if gia_tri else None


def _ty_le(so: int, tong: int) -> float:
    return round(so / tong, 4) if tong else 0.0


def _khoa_ma(ma: str | None) -> tuple[bool, str]:
    """Xếp mã nhóm tăng dần, nhóm rỗng (hồ sơ chưa có phòng) xuống cuối."""
    return (ma is None, ma or "")


def _dem_nhom(ho_so: set[int], nhom_cua: dict[int, str | None], tong_nhom: Counter) -> list[dict]:
    """Số hồ sơ của một tập theo từng nhóm, kèm tỷ lệ trên tổng hồ sơ của nhóm đó trong phạm vi.
    Nhiều hồ sơ nhất trước; bằng nhau thì theo mã. Nhóm không có hồ sơ nào thì bỏ."""
    dem = Counter(nhom_cua[h] for h in ho_so)
    return [
        {"code": ma, "cases_count": so, "ratio": _ty_le(so, tong_nhom[ma])}
        for ma, so in sorted(dem.items(), key=lambda m: (-m[1], _khoa_ma(m[0])))
    ]


def _cho_theo_nhom(giay_theo_nhom: dict[str | None, list[int]]) -> list[dict]:
    """Trung vị chờ của một trạng thái theo từng nhóm. Chậm nhất trước; bằng nhau thì theo mã."""
    return sorted(
        ({"code": ma, "visits": len(ds), "median_wait_seconds": _trung_vi(ds)}
         for ma, ds in giay_theo_nhom.items()),
        key=lambda m: (-m["median_wait_seconds"], _khoa_ma(m["code"])),
    )


def phan_tich(du_lieu: DuLieu, bo_may: BoMay, cau_hinh: CauHinh) -> dict:
    su_kien = du_lieu.su_kien
    cac_ho_so = sorted({s.ho_so for s in su_kien})
    tong = len(cac_ho_so)
    gioi_han = cau_hinh.so_ho_so_moi_nhom

    # --- Lượt vào trạng thái, đầu vào của bộ máy -----------------------------------------------
    luot_vao = [
        LuotVao(ho_so=s.ho_so, trang_thai=s.den, luc=s.luc, thu_tu=i)
        for i, s in enumerate(su_kien)
        if s.doi_trang_thai
    ]
    do_thi = bo_may.do_thi(luot_vao)

    # --- Cạnh: số lần (của bộ máy), số hồ sơ và loại (từ cờ của từng sự kiện) -----------------------
    ho_so_canh: dict[tuple[str, str], set[int]] = defaultdict(set)
    loai_canh: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for s in su_kien:
        if s.tu is None or not s.doi_trang_thai:
            continue
        cap = (s.tu, s.den)
        ho_so_canh[cap].add(s.ho_so)
        loai = (
            "rework" if s.lam_lai else "escalation" if s.leo_thang
            else "wait_expiry" if s.het_han_cho else "reopen" if s.mo_lai else "main"
        )
        loai_canh[cap][loai] += 1

    canh = [
        {
            "from": a,
            "to": b,
            "count": so,
            "cases": len(ho_so_canh.get((a, b), ())),
            "is_main": loai_canh[(a, b)]["main"] == sum(loai_canh[(a, b)].values()) > 0,
            "kinds": {k: loai_canh[(a, b)][k] for k in LOAI_CANH if loai_canh[(a, b)][k]},
        }
        for (a, b), so in sorted(do_thi.items(), key=lambda m: (-m[1], m[0]))
    ]

    # --- Trạng thái và thời gian chờ ---------------------------------------------------------------
    loai_cua = {h: hs.loai for h, hs in du_lieu.ho_so.items()}
    phong_cua = {h: hs.phong for h, hs in du_lieu.ho_so.items()}
    giay_theo_trang_thai: dict[str, list[int]] = defaultdict(list)
    # Theo trạng thái: tổng giây và số lượt của từng hồ sơ; giây từng lượt theo loại và theo phòng
    cho_ho_so: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    cho_theo_loai: dict[str, dict[str | None, list[int]]] = defaultdict(lambda: defaultdict(list))
    cho_theo_phong: dict[str, dict[str | None, list[int]]] = defaultdict(lambda: defaultdict(list))
    # Lượt cuối của mỗi hồ sơ là chỗ hồ sơ đang nằm (lượt xếp theo hồ sơ rồi theo thời điểm vào)
    dang_o: dict[int, str] = {}
    for l in du_lieu.luot:
        dang_o[l.ho_so] = l.trang_thai
        if not l.ket_thuc and l.so_giay is not None:
            giay = int(l.so_giay)
            giay_theo_trang_thai[l.trang_thai].append(giay)
            tong_luot = cho_ho_so[l.trang_thai][l.ho_so]
            tong_luot[0] += giay
            tong_luot[1] += 1
            cho_theo_loai[l.trang_thai][loai_cua.get(l.ho_so)].append(giay)
            cho_theo_phong[l.trang_thai][phong_cua.get(l.ho_so)].append(giay)
    tat_ca_giay = [g for ds in giay_theo_trang_thai.values() for g in ds]
    trung_vi_chung = _trung_vi(tat_ca_giay)
    nguong = cau_hinh.boi_so_nghen * trung_vi_chung if trung_vi_chung else None

    so_lan_vao = Counter(l.trang_thai for l in luot_vao)
    ho_so_vao: dict[str, set[int]] = defaultdict(set)
    for l in luot_vao:
        ho_so_vao[l.trang_thai].add(l.ho_so)

    def nghen(trung_vi: int | None) -> bool:
        return bool(nguong and trung_vi is not None and trung_vi > 0 and trung_vi >= nguong)

    def cho_lau_nhat(ma: str) -> list[dict]:
        """Hồ sơ chờ lâu nhất ở trạng thái: tổng giây làm việc mọi lượt của hồ sơ ở đó, nhiều nhất
        trước; bằng nhau thì theo mã hồ sơ. `current` là hồ sơ hiện còn nằm ở đây (lượt cuối, còn dở)."""
        theo_ho_so = cho_ho_so.get(ma, {})
        xep = sorted(theo_ho_so.items(), key=lambda m: (-m[1][0], m[0]))[:gioi_han]
        return [
            {"case": h, "seconds": giay, "visits": so, "current": dang_o.get(h) == ma}
            for h, (giay, so) in xep
        ]

    trang_thai = []
    for ma in sorted(so_lan_vao, key=lambda m: (du_lieu.trang_thai[m].thu_tu, m) if m in du_lieu.trang_thai else (9999, m)):
        tt = du_lieu.trang_thai.get(ma)
        trung_vi = _trung_vi(giay_theo_trang_thai.get(ma, []))
        trang_thai.append({
            "code": ma,
            "label": tt.nhan if tt else ma,
            "is_initial": bool(tt and tt.bat_dau),
            "is_terminal": bool(tt and tt.ket_thuc),
            "visits": so_lan_vao[ma],
            "cases": len(ho_so_vao[ma]),
            "median_wait_seconds": trung_vi,
            "is_bottleneck": nghen(trung_vi),
            "longest_waits": cho_lau_nhat(ma),
            "by_request_type": _cho_theo_nhom(cho_theo_loai.get(ma, {})),
            "by_department": _cho_theo_nhom(cho_theo_phong.get(ma, {})),
        })

    xep_hang = sorted(
        (t for t in trang_thai if t["median_wait_seconds"] is not None),
        key=lambda t: (-t["median_wait_seconds"], t["code"]),
    )

    # --- Nhánh lệch ----------------------------------------------------------------------------------
    co: dict[str, set[int]] = {k: set() for k in NHANH_LECH}
    so_lan_dat_phong: Counter = Counter()
    for s in su_kien:
        if s.lam_lai:
            co["rework"].add(s.ho_so)
        if s.leo_thang:
            co["escalation"].add(s.ho_so)
        if s.het_han_cho:
            co["wait_expiry"].add(s.ho_so)
        if s.mo_lai:
            co["reopen"].add(s.ho_so)
        if s.doi_phong:
            so_lan_dat_phong[s.ho_so] += 1
    co["multiple_routing"] = {h for h, so in so_lan_dat_phong.items() if so >= 2}

    tong_loai = Counter(loai_cua[h] for h in cac_ho_so)
    tong_phong = Counter(phong_cua[h] for h in cac_ho_so)
    nhanh_lech = [
        {"kind": k, "cases_count": len(co[k]), "ratio": _ty_le(len(co[k]), tong),
         "cases": sorted(co[k])[:gioi_han],
         "by_request_type": _dem_nhom(co[k], loai_cua, tong_loai),
         "by_department": _dem_nhom(co[k], phong_cua, tong_phong)}
        for k in NHANH_LECH
    ]

    def nhan_cua(ma: str) -> str:
        tt = du_lieu.trang_thai.get(ma)
        return tt.nhan if tt else ma

    # --- Biến thể ------------------------------------------------------------------------------------
    bien_the = sorted(bo_may.bien_the(luot_vao).items(), key=lambda m: (-len(m[1]), m[0]))
    hien = bien_the[: cau_hinh.so_bien_the]

    return {
        "engine": bo_may.ten,
        "cases_count": tong,
        "events_count": len(su_kien),
        "groups": {
            "request_types": [{"code": m, "cases_count": s}
                              for m, s in sorted(tong_loai.items(), key=lambda m: (-m[1], _khoa_ma(m[0])))],
            "departments": [{"code": m, "cases_count": s}
                            for m, s in sorted(tong_phong.items(), key=lambda m: (-m[1], _khoa_ma(m[0])))],
        },
        "states": trang_thai,
        "edges": canh,
        # Kèm nhãn: bước thiết kế chưa hồ sơ nào đi qua có thể chạm trạng thái không nằm trong `states`
        "designed_main_flow": [
            {"from": a, "to": b, "from_label": nhan_cua(a), "to_label": nhan_cua(b)}
            for a, b in du_lieu.luong_chinh
        ],
        "deviations": nhanh_lech,
        "bottlenecks": {
            "overall_median_wait_seconds": trung_vi_chung,
            "factor": cau_hinh.boi_so_nghen,
            "threshold_seconds": int(round(nguong)) if nguong else None,
            "ranking": [
                {"code": t["code"], "label": t["label"], "median_wait_seconds": t["median_wait_seconds"],
                 "visits": t["visits"], "is_bottleneck": t["is_bottleneck"]}
                for t in xep_hang
            ],
        },
        "variants": [
            {"sequence": list(chuoi), "cases_count": len(ho_so), "ratio": _ty_le(len(ho_so), tong),
             "cases": ho_so[:gioi_han]}
            for chuoi, ho_so in hien
        ],
        "other_variants_cases": sum(len(h) for _, h in bien_the[cau_hinh.so_bien_the:]),
    }
