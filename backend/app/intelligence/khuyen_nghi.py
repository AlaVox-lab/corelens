# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Khuyến nghị cải tiến quy trình bằng câu chữ (#320).
#
# Từ kết quả khai phá (#314, hợp đồng ở ARCHITECTURE.md mục 6.4), mô hình sinh văn bản viết vài câu
# khuyến nghị ngắn tiếng Việt cho người quản lý. Gọi ở DỊCH VỤ ỨNG DỤNG, không trong dịch vụ khai phá:
# dịch vụ khai phá chỉ trả JSON con số; mọi lời gọi mô hình đi qua `mo_hinh.py` (ADR-0008).
#
# BỐN LỜI HỨA
#
# 1. KHÔNG CON SỐ NÀO BỊA. Mô hình chỉ thấy một bảng dữ kiện dựng tất định từ kết quả khai phá, số đã
#    viết sẵn kiểu Việt Nam (dấu chấm ngăn nghìn, dấu phẩy thập phân, "%", "giờ … phút") như màn hình
#    hiện. Mỗi câu nó viết được tách số ra, chuẩn hóa, và so với tập số của bảng dữ kiện — số không tra
#    được thì BỎ cả câu; câu không dẫn số nào cũng bỏ, vì khuyến nghị phải có căn cứ. Số viết bằng chữ
#    ("hai lần") không bắt được — giới hạn đã biết, ghi ở mục 6.6.
# 2. KHÔNG CHỜ. Màn quy trình thực tế hiện ngay với câu kết luận tất định (`ket-luan-quy-trinh.ts`). Lời
#    hỏi đầu tiên chỉ xếp việc sinh vào MỘT luồng nền và trả `pending`; màn hỏi lại vài giây một lần.
# 3. KHÔNG HỎI LẠI. Bộ nhớ đệm theo khoảng ngày, phạm vi phòng và mã băm của chính kết quả khai phá:
#    mở lại màn với cùng dữ liệu thì có ngay; có hồ sơ mới làm số đổi thì sinh lại, nên đoạn khuyến nghị
#    không bao giờ nói số cũ cạnh sơ đồ số mới. Lần hỏng nhớ một lúc rồi mới thử lại.
# 4. CHỈ ĐỂ ĐỌC. Không ghi gì vào cơ sở dữ liệu, không đổi cấu hình nào; giao diện ghi rõ "gợi ý của
#    hệ thống". Mô hình tắt — `disabled`, màn chỉ có câu kết luận như trước.

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from app.config import get_settings
from app.intelligence import mo_hinh

log = logging.getLogger(__name__)

# Tình trạng trả cho màn hình
SAN_SANG = "ready"
DANG_SINH = "pending"
TAT = "disabled"
KHONG_PHAN_HOI = "unavailable"
KHONG_DU_LIEU = "no-data"

# Nhãn năm nhánh lệch — loại phân tích do dịch vụ khai phá định nghĩa (hợp đồng mục 6.4), không phải
# cấu hình nghiệp vụ; cùng bảng với `NHAN_NHANH_LECH` của `frontend/lib/ket-luan-quy-trinh.ts`
NHAN_NHANH_LECH = {
    "rework": "Trả về làm lại",
    "escalation": "Leo thang do quá hạn",
    "wait_expiry": "Tự chuyển khi hết hạn chờ",
    "reopen": "Mở lại sau khi kết thúc",
    "multiple_routing": "Chuyển phòng nhiều lần",
}

# Số trạng thái xếp hạng chờ lâu nhất đưa vào bảng dữ kiện
SO_TRANG_THAI = 5

# Tên gọi vai trò trên giao diện (ARCHITECTURE.md mục 8.3), để nhận ra câu mô hình viết nhắc tới vai nào
# (#557). Bảng trình bày như `NHAN_NHANH_LECH`, không phải danh mục vai: vai nào đi cạnh nào vẫn đọc từ bộ
# quy tắc (`turns`); vai không có ở đây thì chỉ nhận theo nhãn trong dữ liệu.
TEN_VAI = {
    "requester": ("người gửi", "người tạo yêu cầu"),
    "classifier": ("điều phối viên",),
    "approver": ("trưởng phòng",),
    "handler": ("người xử lý",),
}

# ---------------------------------------------------------------------------
# Số kiểu Việt Nam — cùng quy tắc với `ket-luan-quy-trinh.ts` và `dinh-dang.ts`
# ---------------------------------------------------------------------------


def so_vn(so: float) -> str:
    """`1234` → `1.234`."""
    return f"{round(so):,}".replace(",", ".")


def so_thap_phan(so: float) -> str:
    """`3.4` → `3,4`, `2` → `2`."""
    lam = round(so * 10) / 10
    nguyen, le = f"{lam:.1f}".split(".")
    dau = so_vn(int(nguyen))
    return dau if le == "0" else f"{dau},{le}"


def phan_tram(ty_le: float) -> str:
    p = ty_le * 100
    if p <= 0:
        return "0 %"
    if p < 0.05:
        return "dưới 0,1 %"
    return f"{round(p) if p >= 10 else so_thap_phan(p)} %"


def thoi_luong(giay: float) -> str:
    if giay < 60:
        return "chưa tới một phút làm việc"
    phut = int(giay // 60)
    if phut < 60:
        return f"{phut} phút làm việc"
    gio, le = divmod(phut, 60)
    return f"{gio} giờ {le} phút làm việc" if le else f"{gio} giờ làm việc"


def so_lan(so: float) -> str:
    return so_vn(so) if so >= 10 else so_thap_phan(so)


def ngay_vn(iso: str) -> str:
    nam, thang, ngay = iso.split("-")
    return f"{ngay}/{thang}/{nam}"


# ---------------------------------------------------------------------------
# Bảng dữ kiện — dựng tất định, chỉ từ kết quả khai phá
# ---------------------------------------------------------------------------


def _nhan(kq: dict, nhom: str, ma: str | None) -> str:
    if ma is None:
        return "chưa chuyển phòng" if nhom == "departments" else "chưa rõ loại"
    return kq.get("labels", {}).get(nhom, {}).get(ma, ma)


def _nhieu_phong(kq: dict) -> bool:
    return bool(kq.get("scope", {}).get("all")) and len(kq.get("groups", {}).get("departments", [])) >= 2


def bang_du_kien(kq: dict) -> list[str]:
    """Các dòng dữ kiện tiếng Việt cho mô hình đọc. Mọi con số trong đây lấy từ kết quả khai phá."""
    pham_vi = kq.get("scope", {})
    if pham_vi.get("all"):
        chu_pham_vi = "toàn công ty"
    else:
        ten = [p["label"] for p in pham_vi.get("departments", [])]
        chu_pham_vi = "phòng " + ", ".join(ten) if ten else "phạm vi người xem"
    dong = [
        f"Khoảng ngày {ngay_vn(kq['range']['from'])} đến {ngay_vn(kq['range']['to'])}, {chu_pham_vi}: "
        f"{so_vn(kq['cases_count'])} hồ sơ được gửi."
    ]

    nghen = kq.get("bottlenecks", {})
    chung = nghen.get("overall_median_wait_seconds")
    if chung:
        dong.append(f"Thời gian chờ trung vị chung ở các trạng thái chưa kết thúc: {thoi_luong(chung)}.")
        trang_thai = {t["code"]: t for t in kq.get("states", [])}
        for r in nghen.get("ranking", [])[:SO_TRANG_THAI]:
            if r.get("median_wait_seconds") is None:
                continue
            cau = (
                f"Trạng thái “{r['label']}”: chờ trung vị {thoi_luong(r['median_wait_seconds'])}, "
                f"gấp {so_lan(r['median_wait_seconds'] / chung)} lần mức chung"
                + (", là điểm nghẽn" if r.get("is_bottleneck") else "")
            )
            tt = trang_thai.get(r["code"], {})
            if _nhieu_phong(kq) and tt.get("by_department"):
                n = tt["by_department"][0]
                cau += (f"; chậm nhất ở phòng {_nhan(kq, 'departments', n['code'])} "
                        f"(trung vị {thoi_luong(n['median_wait_seconds'])})")
            elif tt.get("by_request_type"):
                n = tt["by_request_type"][0]
                cau += (f"; chậm nhất ở loại {_nhan(kq, 'request_types', n['code'])} "
                        f"(trung vị {thoi_luong(n['median_wait_seconds'])})")
            dong.append(cau + ".")

    for n in kq.get("deviations", []):
        if not n.get("cases_count"):
            continue
        cau = (f"Nhánh lệch “{NHAN_NHANH_LECH.get(n['kind'], n['kind'])}”: {phan_tram(n['ratio'])} hồ sơ "
               f"({so_vn(n['cases_count'])} hồ sơ)")
        if n.get("by_request_type"):
            g = n["by_request_type"][0]
            cau += (f"; nhiều nhất ở loại {_nhan(kq, 'request_types', g['code'])} "
                    f"({so_vn(g['cases_count'])} hồ sơ, {phan_tram(g['ratio'])} hồ sơ của loại đó)")
        if _nhieu_phong(kq) and n.get("by_department"):
            g = n["by_department"][0]
            cau += (f"; ở phòng {_nhan(kq, 'departments', g['code'])} "
                    f"({so_vn(g['cases_count'])} hồ sơ, {phan_tram(g['ratio'])} hồ sơ của phòng đó)")
        dong.append(cau + ".")

    bien_the = kq.get("variants", [])
    if bien_the:
        v = bien_the[0]
        dong.append(f"Đường đi phổ biến nhất chiếm {phan_tram(v['ratio'])} hồ sơ "
                    f"({so_vn(v['cases_count'])} hồ sơ).")
    return dong


# ---------------------------------------------------------------------------
# Kiểm con số
# ---------------------------------------------------------------------------

# Một số viết kiểu Việt Nam: nhóm nghìn bằng dấu chấm, phần lẻ bằng dấu phẩy; chấp nhận cả dấu chấm
# thập phân kiểu Anh khi sau nó không đúng ba chữ số
_SO = re.compile(r"\d+(?:\.\d{3})+(?:,\d+)?(?!\d)|\d+(?:[.,]\d+)?")


# Đơn vị đứng ngay sau một con số trong bảng dữ kiện. Số đúng mà đổi đơn vị — "4 hồ sơ" lấy từ
# "4 giờ 14 phút" — là số bịa
_DON_VI = re.compile(r"\s*(%|giờ|phút|hồ sơ|lần)", re.IGNORECASE)


def _gia_tri(chu: str) -> float:
    if re.fullmatch(r"\d+(?:\.\d{3})+(?:,\d+)?", chu):
        chu = chu.replace(".", "").replace(",", ".")
    else:
        chu = chu.replace(",", ".")
    return round(float(chu), 2)


def cac_so(van_ban: str) -> list[float]:
    return [_gia_tri(m.group()) for m in _SO.finditer(van_ban)]


def so_kem_don_vi(van_ban: str) -> set[tuple[float, str]]:
    """(giá trị, đơn vị) của mọi con số; đơn vị rỗng khi sau số không có đơn vị nào trong danh sách."""
    ra = set()
    for m in _SO.finditer(van_ban):
        dv = _DON_VI.match(van_ban, m.end())
        ra.add((_gia_tri(m.group()), dv.group(1).lower() if dv else ""))
    return ra


def _khop_so(cau: set[tuple[float, str]], dong: set[tuple[float, str]]) -> bool:
    """Mọi số của câu có trong dòng, cùng đơn vị; số không đơn vị trong câu chỉ cần cùng giá trị."""
    return all(any(v == v2 and (u == u2 or not u) for v2, u2 in dong) for v, u in cau)


# Số thứ tự đầu mục ("1.", "2)") mô hình hay chèn — không phải con số căn cứ
_SO_THU_TU = re.compile(r"(^|\s)\d{1,2}[.)](?=\s|$)")


def tach_cau(van_ban: str) -> list[str]:
    """Tách đoạn thành câu ở dấu chấm hết câu theo sau là khoảng trắng và chữ hoa hay ngoặc mở. Bỏ số
    thứ tự đầu mục trước khi tách, để "1." không thành một câu, cũng không thành một con số."""
    gon = _SO_THU_TU.sub(r"\1", " ".join(van_ban.split()))
    cau = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ỹ“\"'(])", gon.strip())
    return [c.strip() for c in cau if c.strip() and re.search(r"\w", c)]


@dataclass
class KetQuaKiem:
    giu: list[str] = field(default_factory=list)
    sai_so: list[str] = field(default_factory=list)
    khong_so: list[str] = field(default_factory=list)
    # Số thứ tự vấn đề của từng câu giữ, cùng thứ tự với `giu` (chỉ `dung_cau` ghi)
    dong_giu: list[int] = field(default_factory=list)


def ten_trong_ket_qua(kq: dict) -> list[str]:
    """Mọi tên mà một câu có thể gắn số vào: trạng thái, loại yêu cầu, phòng, nhánh lệch — đọc từ kết
    quả (và bảng nhãn nhánh lệch của hợp đồng). Dài trước, để "Chờ phòng ban xác duyệt" không bị hiểu
    thành một tên ngắn hơn nằm trong nó."""
    ten = {t["label"] for t in kq.get("states", []) if t.get("label")}
    ten |= {r["label"] for r in kq.get("bottlenecks", {}).get("ranking", []) if r.get("label")}
    for nhom in ("request_types", "departments"):
        ten |= set(kq.get("labels", {}).get(nhom, {}).values())
    ten |= set(NHAN_NHANH_LECH.values())
    return sorted((t for t in ten if t), key=len, reverse=True)


def _ten_nhac_toi(cau: str, cac_ten: list[str]) -> list[str]:
    con = cau.lower()
    ra = []
    for t in cac_ten:
        if t.lower() in con:
            ra.append(t)
            con = con.replace(t.lower(), " ")
    return ra


def kiem_cau(cac_cau: list[str], du_kien: list[str], cac_ten: list[str] | None = None) -> KetQuaKiem:
    """Giữ câu dẫn ít nhất một con số, và có MỘT dòng dữ kiện chứa đủ mọi con số lẫn mọi tên (trạng thái,
    loại, phòng, nhánh lệch) mà câu nhắc tới. Số có thật mà gắn sai đối tượng — "15 giờ 9 phút ở phòng A"
    trong khi đó là số của phòng B — hay ghép số của hai dòng khác nhau, đều là sai số: bỏ cả câu."""
    dong = [(so_kem_don_vi(d), d.lower()) for d in du_kien]
    kq = KetQuaKiem()
    for cau in cac_cau:
        so = so_kem_don_vi(cau)
        if not so:
            kq.khong_so.append(cau)
            continue
        ten = [t.lower() for t in _ten_nhac_toi(cau, cac_ten or [])]
        if any(_khop_so(so, s) and all(t in chu for t in ten) for s, chu in dong):
            kq.giu.append(cau)
        else:
            kq.sai_so.append(cau)
    return kq


# ---------------------------------------------------------------------------
# Lời gọi mô hình
# ---------------------------------------------------------------------------

LOI_DAN = (
    "Bạn là trợ lý phân tích quy trình nội bộ của một doanh nghiệp. Bên dưới là bối cảnh và danh sách VẤN "
    "ĐỀ đánh số [1], [2]… rút từ khai phá quy trình. Chọn tối đa vài vấn đề đáng xử lý nhất (điểm nghẽn, "
    "nhánh lệch tỷ lệ cao) và với mỗi vấn đề viết MỘT câu tiếng Việt ngắn nêu việc cụ thể người quản lý nên "
    "làm để GIẢM thời gian chờ hay GIẢM số hồ sơ đi nhánh lệch — ví dụ bổ sung người xử lý cho một phòng "
    "chậm, rà lại biểu mẫu của một loại yêu cầu hay bị trả về, nhắc người xử lý hoàn thành sớm, đặt nhắc "
    "việc trước hạn. TRẠNG THÁI (tên trong ngoặc sau chữ 'Trạng thái') là một chặng của hồ sơ, KHÔNG phải "
    "phòng ban, cũng KHÔNG phải loại yêu cầu: phòng ban là tên ghi sau chữ 'phòng', loại yêu cầu là tên ghi "
    "sau chữ 'loại'; không viết 'phòng' hay 'loại' trước tên một trạng thái. Mục 'Ai đi bước tiếp' ghi vai "
    "nào đi bước tiếp ở mỗi trạng thái: muốn nhắc ai thì gọi đúng tên vai ghi ở đó, không nhắc vai khác. "
    "Ghi số thứ tự vấn đề vào 'dong'. Câu bắt đầu bằng 'Nên', KHÔNG chép lại con số (hệ thống tự gắn căn "
    "cứ), không nêu tên người, không xưng 'chúng tôi', không đề xuất tự động đổi hệ thống. Không vấn đề "
    "nào đáng xử lý thì trả danh sách rỗng."
)

# Dòng dữ kiện là một VẤN ĐỀ để khuyến nghị: trạng thái chờ và nhánh lệch — tiền tố của chính
# `bang_du_kien` ở trên, không phải dữ liệu nghiệp vụ
TIEN_TO_VAN_DE = ("Trạng thái “", "Nhánh lệch “")


def luoc_do(so_cau: int, so_van_de: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "khuyen_nghi": {
                "type": "array",
                "maxItems": so_cau,
                "items": {
                    "type": "object",
                    "properties": {
                        "dong": {"type": "integer", "enum": list(range(1, so_van_de + 1))},
                        "viec": {"type": "string"},
                    },
                    "required": ["dong", "viec"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["khuyen_nghi"],
        "additionalProperties": False,
    }


@dataclass(frozen=True)
class KhuyenNghi:
    status: str
    sentences: tuple[str, ...] = ()
    # Câu bỏ vì có số hay tên không khớp đúng dòng dữ kiện của nó
    dropped_wrong_number: int = 0
    # Câu bỏ vì không dùng được: rỗng, trùng vấn đề đã có, không trỏ tới vấn đề nào
    dropped_no_number: int = 0
    # Câu khuôn dựng tất định cho điểm nghẽn không còn câu nào của mô hình (#559), đã nằm trong `sentences`
    template_sentences: int = 0
    model: str | None = None
    elapsed_ms: int | None = None
    generated_at: dt.datetime | None = None
    # Lúc kết quả hỏng hết hiệu lực trong bộ nhớ đệm (giây đơn điệu); `None` là giữ tới khi bị đẩy ra
    het_han: float | None = None


def ghep_cau(viec: str, dong: str) -> str:
    """Câu hiện cho người đọc: việc mô hình đề xuất, rồi căn cứ chép nguyên dòng dữ kiện — con số trong
    câu luôn là con số của hệ thống. Ngoặc đơn thẳng quanh một tên đổi thành ngoặc kép như dòng dữ kiện
    (#557: một câu từng lẫn '…' với “…”)."""
    viec = re.sub(r"'([^']+)'", r"“\1”", viec.strip()).rstrip(".;:")
    return f"{viec[0].upper()}{viec[1:]} — căn cứ: {dong[0].lower()}{dong[1:].rstrip('.')}."


def ten_vai(ma: str, nhan: dict[str, str]) -> tuple[str, ...]:
    """Các cách gọi một vai: tên giao diện ở `TEN_VAI`, cộng nhãn trong dữ liệu."""
    ten = TEN_VAI.get(ma, ())
    return tuple(t.lower() for t in (*ten, nhan.get(ma, "")) if t)


def trang_thai_cua_dong(dong: str, kq: dict) -> str | None:
    """Mã trạng thái mà một dòng vấn đề "Trạng thái “X”: …" nói tới; dòng nhánh lệch thì `None`."""
    m = re.match(r"Trạng thái “([^”]+)”", dong)
    if not m:
        return None
    for r in kq.get("bottlenecks", {}).get("ranking", []):
        if r.get("label") == m.group(1):
            return r.get("code")
    return None


def sai_doi_tuong(viec: str, dong: str, kq: dict) -> bool:
    """Câu gán trạng thái thành phòng ban hay loại yêu cầu, hoặc nhắc tới một vai không đi bước tiếp ở trạng
    thái của dòng nó trỏ tới (#557). Ba lỗi mô hình từng viết trên cụm trình diễn: "bổ sung người xử lý cho phòng
    ‘Chờ bổ sung thông tin’", "rà lại biểu mẫu của loại ‘Hoàn tất’" và "nhắc người gửi bổ sung thông tin cho hồ sơ
    ‘Đang xử lý’" — số đúng nên lọt phép kiểm số.
    Vai nào đi bước tiếp đọc từ bộ quy tắc (`turns`); không có thông tin đó thì không kiểm vai."""
    chu = " ".join(viec.lower().split())
    nhan_tt = {t.get("label") for t in kq.get("states", [])}
    nhan_tt |= {r.get("label") for r in kq.get("bottlenecks", {}).get("ranking", [])}
    for nhan in (n for n in nhan_tt if n):
        if re.search(r"(?:phòng|loại)(?:\s+ban|\s+yêu\s+cầu)?\s*[“\"'‘]?\s*" + re.escape(nhan.lower()), chu):
            return True
    ma = trang_thai_cua_dong(dong, kq)
    luot = kq.get("turns", {}).get(ma) if ma else None
    if not luot:
        return False
    nhan_vai = kq.get("role_labels", {})
    for vai in {*TEN_VAI, *nhan_vai}:
        if vai not in luot and any(t in chu for t in ten_vai(vai, nhan_vai)):
            return True
    return False


def ai_di_tiep(van_de: list[str], kq: dict) -> list[str]:
    """Dòng "Ai đi bước tiếp" cho mỗi trạng thái trong danh sách vấn đề — cho mô hình đọc, không phải căn cứ."""
    nhan_vai = kq.get("role_labels", {})
    ra = []
    for d in van_de:
        ma = trang_thai_cua_dong(d, kq)
        luot = kq.get("turns", {}).get(ma) if ma else None
        if not luot:
            continue
        ten = ", ".join(ten_vai(v, nhan_vai)[0] for v in luot if ten_vai(v, nhan_vai))
        nhan = re.match(r"Trạng thái “([^”]+)”", d).group(1)
        ra.append(f"Trạng thái “{nhan}”: {ten}.")
    return ra


def dung_cau(tho: Any, du_kien: list[str], cac_ten: list[str], kq: dict | None = None) -> KetQuaKiem:
    """Đổi đầu ra của mô hình thành câu đã kiểm. Phần mô hình viết (`viec`) qua đúng phép kiểm số và tên
    với DÒNG nó trỏ tới: dẫn số không có trong dòng đó, hay nhắc trạng thái, loại, phòng của dòng khác, là
    bỏ; gán trạng thái thành phòng hay nhắc sai vai (`sai_doi_tuong`, khi có kết quả khai phá) cũng bỏ. Phần
    căn cứ là dòng dữ kiện dựng tất định."""
    ket_qua = kq
    van_de = [d for d in du_kien if d.startswith(TIEN_TO_VAN_DE)]
    kq = KetQuaKiem()
    da_co: set[int] = set()
    for muc in tho if isinstance(tho, list) else []:
        so = muc.get("dong") if isinstance(muc, dict) else None
        viec = " ".join(tach_cau(muc.get("viec", ""))) if isinstance(muc, dict) and isinstance(
            muc.get("viec"), str) else ""
        if not isinstance(so, int) or not 1 <= so <= len(van_de) or so in da_co or not viec:
            kq.khong_so.append(str(muc))
            continue
        dong = van_de[so - 1]
        ten = [t.lower() for t in _ten_nhac_toi(viec, cac_ten)]
        if (
            not _khop_so(so_kem_don_vi(viec), so_kem_don_vi(dong))
            or not all(t in dong.lower() for t in ten)
            or (ket_qua is not None and sai_doi_tuong(viec, dong, ket_qua))
        ):
            kq.sai_so.append(viec)
            continue
        da_co.add(so)
        kq.giu.append(ghep_cau(viec, dong))
        kq.dong_giu.append(so)
    return kq


def cau_khuon(van_de: list[str], da_co: set[int], kq: dict) -> list[tuple[int, str]]:
    """Câu dự phòng cho điểm nghẽn không còn câu nào của mô hình qua phép kiểm (#559), để điểm nghẽn lớn
    nhất không bị bỏ trống. Dựng tất định: vai đi bước tiếp đọc từ bộ quy tắc (`turns`), nhãn trạng thái từ
    dòng vấn đề, động từ chung cho mọi vai; căn cứ là chính dòng đó (`ghep_cau`). Trạng thái không có bước
    chính thì không có vai để nhắc — bỏ trống như cũ. Trả cặp (số thứ tự vấn đề, câu)."""
    nghen = {r.get("code") for r in kq.get("bottlenecks", {}).get("ranking", []) if r.get("is_bottleneck")}
    nhan_vai = kq.get("role_labels", {})
    ra = []
    for so, dong in enumerate(van_de, start=1):
        ma = trang_thai_cua_dong(dong, kq)
        if so in da_co or ma is None or ma not in nghen:
            continue
        vai = [ten_vai(v, nhan_vai)[0] for v in kq.get("turns", {}).get(ma, []) if ten_vai(v, nhan_vai)]
        if not vai:
            continue
        nhan = re.match(r"Trạng thái “([^”]+)”", dong).group(1)
        ra.append((so, ghep_cau(f"Nên nhắc {' hoặc '.join(vai)} làm sớm bước tiếp theo cho hồ sơ ở “{nhan}”",
                                dong)))
    return ra


def sinh(kq: dict) -> KhuyenNghi:
    """Sinh và kiểm một lần. Không ném lỗi: mô hình hỏng thì `unavailable`."""
    cau_hinh = get_settings()
    du_kien = bang_du_kien(kq)
    boi_canh = [d for d in du_kien if not d.startswith(TIEN_TO_VAN_DE)]
    van_de = [d for d in du_kien if d.startswith(TIEN_TO_VAN_DE)]
    if not van_de:
        return KhuyenNghi(status=SAN_SANG, model=cau_hinh.llm_model,
                          generated_at=dt.datetime.now(dt.UTC))
    noi_dung = ("Bối cảnh:\n" + "\n".join(f"- {d}" for d in boi_canh)
                + "\n\nVấn đề:\n" + "\n".join(f"[{i}] {d}" for i, d in enumerate(van_de, start=1)))
    # Vai nào đi bước tiếp ở mỗi trạng thái — đọc từ bộ quy tắc (#557), để mô hình không nhắc sai vai
    luot = ai_di_tiep(van_de, kq)
    if luot:
        noi_dung += "\n\nAi đi bước tiếp:\n" + "\n".join(f"- {d}" for d in luot)
    tin_nhan = [
        {"role": "system", "content": LOI_DAN},
        {"role": "user", "content": noi_dung},
    ]
    try:
        dap_an, ms = mo_hinh.hoi_json(
            tin_nhan,
            luoc_do(cau_hinh.recommendation_max_sentences, len(van_de)),
            ten="khuyen_nghi",
            han_giay=cau_hinh.recommendation_timeout_seconds,
            so_token=cau_hinh.recommendation_max_tokens,
        )
    except mo_hinh.LoiMoHinh as loi:
        if loi.ma != mo_hinh.LOI_TAT:
            log.warning("Không sinh được khuyến nghị cải tiến: %s", loi)
        return KhuyenNghi(
            status=TAT if loi.ma == mo_hinh.LOI_TAT else KHONG_PHAN_HOI,
            het_han=time.monotonic() + cau_hinh.recommendation_retry_after_seconds,
        )
    kiem = dung_cau(dap_an.get("khuyen_nghi"), du_kien, ten_trong_ket_qua(kq), kq)
    if kiem.sai_so or kiem.khong_so:
        log.info("Khuyến nghị: bỏ %d câu sai số hay sai đối tượng, %d mục không dùng được: %s",
                 len(kiem.sai_so), len(kiem.khong_so), kiem.sai_so + kiem.khong_so)
    # Điểm nghẽn bị bỏ trống thì lấp bằng câu khuôn (#559); câu xếp theo thứ tự vấn đề — điểm nghẽn lớn trước
    khuon = cau_khuon(van_de, set(kiem.dong_giu), kq)
    cac_cau = sorted([*zip(kiem.dong_giu, kiem.giu, strict=True), *khuon], key=lambda c: c[0])
    return KhuyenNghi(
        status=SAN_SANG,
        sentences=tuple(c for _, c in cac_cau),
        dropped_wrong_number=len(kiem.sai_so),
        dropped_no_number=len(kiem.khong_so),
        template_sentences=len(khuon),
        model=cau_hinh.llm_model,
        elapsed_ms=ms,
        generated_at=dt.datetime.now(dt.UTC),
    )


# ---------------------------------------------------------------------------
# Bộ nhớ đệm và luồng nền
# ---------------------------------------------------------------------------

# Một luồng: llama.cpp xử lý lần lượt, xếp hàng ở đây gọn hơn ở máy chủ mô hình
_LUONG = ThreadPoolExecutor(max_workers=1, thread_name_prefix="khuyen-nghi")
_KHOA = threading.Lock()
_DEM: OrderedDict[str, KhuyenNghi] = OrderedDict()
_DANG_SINH: set[str] = set()


def khoa_dem(tu: dt.date, den: dt.date, phong: list[str] | None, kq: dict) -> str:
    """Khóa bộ nhớ đệm: khoảng ngày, phạm vi, và mã băm của chính kết quả (kể cả nhãn) — dữ liệu đổi thì
    khóa đổi."""
    bam = hashlib.sha256(json.dumps(kq, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    return f"{tu.isoformat()}|{den.isoformat()}|{','.join(sorted(phong)) if phong else '*'}|{bam}"


def _ghi_dem(khoa: str, kn: KhuyenNghi) -> None:
    with _KHOA:
        _DANG_SINH.discard(khoa)
        _DEM[khoa] = kn
        _DEM.move_to_end(khoa)
        while len(_DEM) > max(1, get_settings().recommendation_cache_size):
            _DEM.popitem(last=False)


def _chay(khoa: str, kq: dict) -> None:
    try:
        kn = sinh(kq)
    except Exception:  # noqa: BLE001 — lỗi bất ngờ không được giữ khóa "đang sinh" mãi
        log.exception("Lỗi bất ngờ khi sinh khuyến nghị")
        kn = KhuyenNghi(status=KHONG_PHAN_HOI,
                        het_han=time.monotonic() + get_settings().recommendation_retry_after_seconds)
    _ghi_dem(khoa, kn)


def lay(tu: dt.date, den: dt.date, phong: list[str] | None, kq: dict) -> tuple[KhuyenNghi, bool]:
    """(khuyến nghị, có từ bộ nhớ đệm). Chưa có thì xếp việc sinh vào luồng nền, trả `pending`."""
    cau_hinh = get_settings()
    if not cau_hinh.recommendation_enabled or not cau_hinh.llm_enabled:
        return KhuyenNghi(status=TAT), False
    if not kq.get("cases_count"):
        return KhuyenNghi(status=KHONG_DU_LIEU), False
    khoa = khoa_dem(tu, den, phong, kq)
    with _KHOA:
        co = _DEM.get(khoa)
        if co is not None and (co.het_han is None or co.het_han > time.monotonic()):
            _DEM.move_to_end(khoa)
            return co, True
        if khoa in _DANG_SINH:
            return KhuyenNghi(status=DANG_SINH), False
        _DANG_SINH.add(khoa)
    _LUONG.submit(_chay, khoa, kq)
    return KhuyenNghi(status=DANG_SINH), False


def xoa_dem() -> None:
    """Cho bài kiểm thử."""
    with _KHOA:
        _DEM.clear()
        _DANG_SINH.clear()
