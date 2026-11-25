# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nạp dữ liệu trình diễn vào cụm đang chạy (#306): vài trăm hồ sơ trải vài tháng, để bảng điều
# khiển phân tích (#304) có số mà xem.
#
# CHỈ DÙNG CHO CỤM THỬ VÀ BUỔI TRÌNH DIỄN. Hồ sơ nạp vào là hồ sơ giả, và không gỡ ra được: nhật
# ký sự kiện chỉ ghi thêm, trigger chặn mọi lệnh xóa. Muốn sạch lại thì `down -v` cả cụm.
#
# NHẬN RA HỒ SƠ MẪU (#541): bằng mã người gửi, không bằng tiêu đề. Người gửi của hồ sơ mẫu là mã ảo của
# bộ sinh — vai người gửi của bộ quy tắc và ba chữ số, ví dụ `requester-008` (`mau_ma_nguoi_gui` trong
# scripts/sinh_nhat_ky_ao.py) — còn tài khoản thật mang mã UUID của Keycloak. Tra hồ sơ mẫu bằng
# `requests.requester_id ~ '^requester-[0-9]{3}$'`. Mã người xử lý, trưởng phòng, điều phối viên cũng là
# mã ảo (`handler-it-3`, `approver-hr-1`, `classifier-2`); chỉ NHÃN hiển thị mang tên người.
#
# Kịch bản lấy từ bộ sinh nhật ký ảo (scripts/sinh_nhat_ky_ao.py, #124): đi đúng cạnh, đúng vai
# trò, đúng luật quay về chỗ cũ của bộ quy tắc ĐANG BẬT, đọc thẳng từ cơ sở dữ liệu. Bộ sinh tự
# kiểm mọi sự kiện trước khi lệnh này ghi gì vào cơ sở dữ liệu.
#
# Lịch sử lùi về quá khứ mà nhật ký vẫn chỉ ghi thêm: lệnh chỉ chạy INSERT — hồ sơ mang sẵn
# trạng thái cuối, nhật ký mang sẵn mốc thời gian cũ — không UPDATE hay DELETE dòng nhật ký
# nào. Đây là lối ghi duy nhất ngoài engine (`perform_transition`), và nó là nhập lịch sử đã
# kiểm chứ không phải chuyển trạng thái: engine không ghi được mốc trong quá khứ.
#
# Thời gian: bộ sinh đếm giây trên một đồng hồ riêng; lệnh này coi đồng hồ đó là GIÂY LÀM VIỆC
# và đổi sang giờ thật bằng `moc_sau_giay_lam_viec` của cơ sở dữ liệu. Nhờ vậy sự kiện rơi vào
# giờ hành chính, đồng hồ hạn của hồ sơ đúng bằng cách hệ thống tự đo, và mỗi hồ sơ chỉ được
# mô phỏng tới lượng giờ làm việc còn lại tới hiện tại — không sự kiện nào nằm ở tương lai.
#
# Nội dung đọc như doanh nghiệp thật (#541), từ scripts/du_lieu/noi_dung_trinh_dien.json: tiêu đề, mô tả
# và trường riêng (`requests.details`) theo loại yêu cầu, tên người cho mọi mã ảo, ghi chú của các bước bắt
# buộc ghi chú, câu bổ sung khi người gửi sửa nội dung. Trường riêng đọc khai báo từ `request_type_fields`
# của cụm: chỉ ghi trường có thật, đúng kiểu (danh mục thì trong danh mục) như app/rules/truong_rieng.py;
# loại hay trường không có trong tệp thì để trống. Trường riêng theo loại người gửi chọn lúc gửi — đúng như
# hệ thống kiểm lúc tạo hồ sơ — và đổi theo khi người gửi tự sửa loại.
#
# Hồ sơ đã giải quyết có nội dung thật (#319): một phần hồ sơ mẫu mà bộ sinh cho đi tới "người gửi
# xác nhận đạt" được thay tiêu đề, mô tả bằng các mục trong scripts/du_lieu/ho_so_da_giai_quyet.json,
# và ghi chú của bước hoàn thành xử lý mang cách giải quyết của mục đó — để bộ lập chỉ mục hồ sơ tương
# tự có thứ đáng tìm, và bộ đo backend/tests/du_lieu/bo_do_tuong_tu.json có đáp án. Cạnh "hoàn thành
# xử lý" và "xác nhận đạt" tra từ bộ quy tắc (bước chính của người được giao, #227), không mã trạng
# thái nào. Mọi thứ vẫn ghi trước khi INSERT — không sửa dòng nhật ký nào sau đó.
#
# Hồ sơ đóng đạt khác cũng có cách giải quyết (#556): lần hoàn thành cuối mang `cach_giai_quyet` của mục nội dung
# hồ sơ đã rút, theo tỷ lệ trong tệp dữ liệu (ô không bắt buộc), rút từ hạt giống riêng. Nhiều hồ sơ rút trúng một
# mục thì lần lượt nhận tiêu đề gốc và các `bien_the` của mục — bớt trùng tiêu đề mà không đổi mục, mô tả, trường
# riêng của hồ sơ nào.
#
# Gợi ý của hệ thống (#541): lần chuyển mà ở hệ thống thật người quyết định gửi trường có gợi ý — trường do
# ràng buộc của cạnh quản (phân loại, chuyển phòng, giao người xử lý, tự nhận việc), tra từ bộ quy tắc — mang
# `event_log.suggestion` đúng khuôn `app/intelligence/goi_y.py`. Lượt xem hồ sơ tương tự (#319) ghi vào
# `similar_case_views` đúng cột `app/intelligence/tuong_tu.py` ghi: một phần hồ sơ mẫu có phiên soạn đã thấy
# gợi ý rồi vẫn gửi, cộng các phiên bỏ không gửi. Tỷ lệ ghi đè và tỷ lệ ngăn chặn đặt trong tệp dữ liệu.
#
# Mỗi phần thêm sau (mức hài lòng #433, nội dung, tên, gợi ý, lượt xem #541) rút từ hạt giống riêng, nên
# không đổi hồ sơ và nhật ký mà hạt giống cũ sinh ra.
#
# Giới hạn đã biết: kịch bản chưa mô phỏng hệ số hạn theo mức ưu tiên (#101) — hồ sơ khẩn cấp
# trong dữ liệu trình diễn leo thang theo hạn chuẩn của loại.
#
# Cách dùng, ở gốc kho mã, khi cụm đang chạy:
#
#     python scripts/nap_du_lieu_trinh_dien.py --xac-nhan
#     python scripts/nap_du_lieu_trinh_dien.py --xac-nhan --so-ho-so 800 --so-ngay 90
#
# Chỉ cần Python 3.10 trở lên và lệnh `docker`.
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import subprocess
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sinh_nhat_ky_ao import (  # noqa: E402
    KICH_BAN_MAC_DINH,
    RB_GIAO_NGUOI,
    RB_LOAI,
    RB_PHONG,
    RB_TU_NHAN,
    RB_UU_TIEN,
    TAC_NHAN_HAN_CHO,
    TAC_NHAN_HE_THONG,
    BoSinh,
    doc_quy_tac_tu_cum,
    mau_ma_nguoi_gui,
    tu_kiem,
)

# Kịch bản của bộ sinh, chỉnh một hệ số cho dữ liệu trình diễn. Hạn tính theo mức ưu tiên (khẩn
# chỉ còn nửa hạn) và một hồ sơ có thể chạy đồng hồ nhiều đoạn — leo thang, làm lại — nên hệ số
# 0,55 của khảo sát cho gần 28 % hồ sơ trễ hạn; 0,45 cho khoảng 20 %, đo trên 600 hồ sơ.
KICH_BAN = {**KICH_BAN_MAC_DINH, "he_so_xu_ly_theo_sla": 0.45}
# Gốc của đồng hồ riêng của bộ sinh — một mốc bất kỳ, chỉ dùng để lấy độ lệch
GOC_AO = datetime(2000, 1, 3, tzinfo=timezone.utc)
DU_LIEU = Path(__file__).resolve().parent / "du_lieu"
HO_SO_DA_GIAI_QUYET = DU_LIEU / "ho_so_da_giai_quyet.json"
NOI_DUNG = DU_LIEU / "noi_dung_trinh_dien.json"
# Giá trị `transitions.primary_scope` của bước chính do người được giao đi (#227)
PHAM_VI_NGUOI_DUOC_GIAO = "assignee"
TAC_NHAN_HE_THONG_CA = {TAC_NHAN_HE_THONG, TAC_NHAN_HAN_CHO}

# Mức hài lòng (#433): lần đi qua cạnh cho chấm (`transitions.collects_feedback`, tra từ bộ quy tắc) có điểm
# với xác suất này; điểm rải theo trọng số, một phần kèm nhận xét. Rút từ hạt giống riêng, nên thêm phần này
# không đổi hồ sơ và nhật ký mà hạt giống cũ sinh ra.
TY_LE_CO_CHAM = 0.75
TRONG_SO_DIEM = {5: 40, 4: 30, 3: 15, 2: 10, 1: 5}
TY_LE_CO_NHAN_XET = 0.35
NHAN_XET_MAU = {
    5: ["Xử lý nhanh, hướng dẫn rõ ràng.", "Rất hài lòng, cảm ơn phòng đã hỗ trợ."],
    4: ["Ổn, chỉ hơi chờ lâu lúc đầu.", "Đã xong việc, liên lạc tốt."],
    3: ["Được việc nhưng phải hỏi lại nhiều lần.", "Tạm ổn."],
    2: ["Chờ quá lâu mới có người nhận.", "Giải quyết chưa triệt để."],
    1: ["Phải mở lại vì vẫn chưa xong.", "Không ai báo tiến độ."],
}

# Hạt giống riêng của từng phần thêm sau (#541), cộng vào --hat-giong như phần mức hài lòng
HAT_NOI_DUNG, HAT_TEN, HAT_GHI_CHU, HAT_GOI_Y, HAT_XEM = 541, 5411, 5412, 5413, 5414
# Cách giải quyết ở bước Hoàn thành xử lý của hồ sơ đóng đạt (#556)
HAT_CACH_GIAI_QUYET = 556

# Trường quyết định mà ràng buộc của cạnh cho đặt — cùng `governs`/`sets` của app/rules/guards.py, với mã
# ràng buộc là hợp đồng giữa dữ liệu và mã nguồn (như ở bộ sinh). Cửa chuyển trạng thái ghi giữ hay ghi đè
# cho đúng những trường này khi người dùng gửi kèm, kể cả khi giá trị không đổi.
TRUONG_THEO_RANG_BUOC = {
    RB_LOAI: "request_type_code",
    RB_UU_TIEN: "priority_code",
    RB_PHONG: "department_code",
    RB_GIAO_NGUOI: "assignee_id",
    RB_TU_NHAN: "assignee_id",
}
# Mã nguồn gợi ý theo bảng ánh xạ — từ vựng của hệ thống (`NGUON_BANG_ANH_XA` trong app/intelligence/goi_y.py).
# Nguồn này không ngẫu nhiên: gợi ý là phòng mặc định của loại, đúng như hệ thống tính.
NGUON_BANG_ANH_XA = "routing"
# Lý do bỏ không gửi — từ vựng của hệ thống (`BO_NGUOI_GUI`, `BO_HET_GIO` trong app/intelligence/tuong_tu.py)
BO_NGUOI_GUI, BO_HET_GIO = "requester", "timeout"
CHU_TOI_DA = 500  # cùng giới hạn chữ của app/rules/truong_rieng.py


def sinh_danh_gia(ts: argparse.Namespace, su_kien: list[dict]) -> list[list]:
    """Điểm cho những lần đi qua cạnh cho chấm, xác định theo hạt giống: `[mã hồ sơ, thứ tự sự kiện, điểm, nhận xét]`."""
    canh_cham = set(psql(ts, """
        SELECT from_state || E'\\t' || to_state || E'\\t' || activity_code FROM transitions
        WHERE collects_feedback AND NOT is_system
          AND rule_set_id = (SELECT id FROM rule_sets WHERE is_active
                             AND process_code = (SELECT code FROM processes WHERE is_app_default))
    """).splitlines())
    rng = random.Random(ts.hat_giong + 433)
    dong = []
    for i, e in enumerate(su_kien):
        if f"{e['from_state']}\t{e['to_state']}\t{e['activity']}" not in canh_cham:
            continue
        if rng.random() >= TY_LE_CO_CHAM:
            continue
        diem = rng.choices(list(TRONG_SO_DIEM), weights=list(TRONG_SO_DIEM.values()))[0]
        nhan_xet = rng.choice(NHAN_XET_MAU[diem]) if rng.random() < TY_LE_CO_NHAN_XET else ""
        dong.append([e["case_id"], i, diem, nhan_xet])
    return dong


def psql(ts: argparse.Namespace, cau: str, vao: str | None = None) -> str:
    lenh = ["docker", "exec", "-i", ts.container, "psql", "-U", ts.nguoi_dung, "-d", ts.csdl,
            "-At", "-q", "-v", "ON_ERROR_STOP=1", "-1", "-c", cau] if vao is None else [
            "docker", "exec", "-i", ts.container, "psql", "-U", ts.nguoi_dung, "-d", ts.csdl,
            "-At", "-q", "-v", "ON_ERROR_STOP=1", "-1", "-f", "-"]
    kq = subprocess.run(lenh, input=(vao or "").encode("utf-8"), capture_output=True, check=False)
    if kq.returncode != 0:
        sys.exit(f"Lệnh SQL thất bại, không có gì được ghi:\n{kq.stderr.decode('utf-8', 'replace')}")
    return kq.stdout.decode("utf-8").strip()


def chuoi_sql(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def mang(so: list[int]) -> str:
    return "ARRAY[" + ",".join(str(int(x)) for x in so) + "]::bigint[]"


def copy_khoi(bang: str, cot: list[str], dong: list[list]) -> str:
    bo_dem = io.StringIO()
    csv.writer(bo_dem, lineterminator="\n").writerows(dong)
    return f"COPY {bang} ({', '.join(cot)}) FROM STDIN WITH (FORMAT csv);\n{bo_dem.getvalue()}\\.\n"


def doc_canh_ket_thuc(ts: argparse.Namespace) -> dict[str, set[tuple[str, str, str]]]:
    """Cạnh "hoàn thành xử lý" (bước chính của người được giao, #227) và cạnh "xác nhận đạt" đi tiếp từ đó vào
    trạng thái kết thúc — cùng cách `app/intelligence/tuong_tu.py` nhận hồ sơ đã giải quyết."""
    canh: dict[str, set[tuple[str, str, str]]] = {"xong": set(), "dat": set()}
    for dong in psql(ts, f"""
        WITH dang AS (SELECT id FROM rule_sets WHERE is_active AND process_code = (SELECT code FROM processes WHERE is_app_default)),
        xong AS (
            SELECT t.from_state, t.to_state, t.activity_code
            FROM transitions t JOIN dang ON dang.id = t.rule_set_id
            WHERE t.primary_scope = '{PHAM_VI_NGUOI_DUOC_GIAO}' AND NOT t.is_system
        )
        SELECT 'xong', from_state, to_state, activity_code FROM xong
        UNION
        SELECT 'dat', t.from_state, t.to_state, t.activity_code FROM transitions t
        JOIN dang ON dang.id = t.rule_set_id
        JOIN states s ON s.rule_set_id = t.rule_set_id AND s.code = t.to_state AND s.is_terminal
        WHERE NOT t.is_system AND t.from_state IN (SELECT to_state FROM xong)
    """).splitlines():
        loai, tu, den, hoat_dong = dong.split("|")
        canh[loai].add((tu, den, hoat_dong))
    return canh


def theo_ho_so(su_kien: list[dict]) -> dict[int, list[dict]]:
    ds: dict[int, list[dict]] = {}
    for e in su_kien:
        ds.setdefault(e["case_id"], []).append(e)
    return ds


def gan_ho_so_da_giai_quyet(ho_so: list, su_kien: list[dict], canh: dict) -> dict[int, dict]:
    """Gắn nội dung thật vào hồ sơ mẫu đóng đạt (đầu tệp). Sửa `hs.mo_ta` và ghi chú sự kiện tại chỗ,
    trả mục đã gắn theo mã hồ sơ mẫu."""
    muc = json.loads(HO_SO_DA_GIAI_QUYET.read_text(encoding="utf-8"))["ho_so"]
    ds_theo_ho_so = theo_ho_so(su_kien)
    con: dict[str, list[dict]] = {}
    for m in muc:
        con.setdefault(m["loai"], []).append(m)

    da_gan: dict[int, dict] = {}
    for hs in ho_so:
        ds = ds_theo_ho_so.get(hs.ma, [])
        if not ds or not con.get(hs.loai or ""):
            continue
        cuoi = ds[-1]
        if (cuoi["from_state"], cuoi["to_state"], cuoi["activity"]) not in canh["dat"]:
            continue
        # Hồ sơ có lần sửa mô tả thì nhật ký mang mô tả lúc gửi khác — bỏ qua cho khớp
        if any('"description"' in e["changes"] for e in ds):
            continue
        xong = [e for e in ds if (e["from_state"], e["to_state"], e["activity"]) in canh["xong"]]
        if not xong:
            continue
        m = con[hs.loai].pop(0)
        hs.mo_ta = m["mo_ta"]
        xong[-1]["note"] = m["cach_giai_quyet"]
        da_gan[hs.ma] = m
    thieu = sum(len(v) for v in con.values())
    if thieu:
        print(f"Lưu ý: còn {thieu} hồ sơ đã giải quyết chưa gắn được — tăng --so-ho-so.")
    return da_gan


# --- Nội dung, trường riêng, tên người, ghi chú (#541) -----------------------------------


def doc_truong_rieng(ts: argparse.Namespace) -> dict[str, list[dict]]:
    """Khai báo trường riêng của cụm, theo loại và thứ tự hiển thị — như `truong_cua_loai`."""
    tho = psql(ts, """
        SELECT coalesce(json_agg(json_build_object('loai', request_type_code, 'ma', code, 'kieu', kind,
               'bat_buoc', required, 'lua_chon', options) ORDER BY request_type_code, display_order, code), '[]')
        FROM request_type_fields
    """)
    khai: dict[str, list[dict]] = {}
    for t in json.loads(tho):
        khai.setdefault(t["loai"], []).append(t)
    return khai


def gia_tri_hop_le(truong: dict, gia_tri: object, ngay_gui: date) -> object | None:
    """Giá trị đúng kiểu khai báo (cùng luật `_chuan_hoa` của app/rules/truong_rieng.py), hay None khi không
    dùng được. Trường kiểu ngày trong tệp dữ liệu ghi số ngày sau lúc gửi."""
    kieu = truong["kieu"]
    if kieu == "text":
        return gia_tri.strip() if isinstance(gia_tri, str) and gia_tri.strip() and len(gia_tri) <= CHU_TOI_DA else None
    if kieu == "number":
        ok = isinstance(gia_tri, (int, float)) and not isinstance(gia_tri, bool) and gia_tri >= 0
        return gia_tri if ok else None
    if kieu == "date":
        if isinstance(gia_tri, int) and not isinstance(gia_tri, bool):
            return (ngay_gui + timedelta(days=gia_tri)).isoformat()
        try:
            return date.fromisoformat(str(gia_tri)).isoformat()
        except ValueError:
            return None
    return gia_tri if gia_tri in (truong["lua_chon"] or []) else None


class NoiDung:
    """Bộ nội dung của tệp dữ liệu, rút theo một hạt giống."""

    def __init__(self, du_lieu: dict, khai: dict[str, list[dict]], rng: random.Random) -> None:
        self.dl = du_lieu
        self.khai = khai
        self.rng = rng
        self.canh_bao: dict[str, int] = {}
        # Số hồ sơ đã nhận tiêu đề của từng mục, theo tiêu đề gốc của mục (#556)
        self.lan_dung: dict[str, int] = {}

    def _bao(self, cau: str) -> None:
        self.canh_bao[cau] = self.canh_bao.get(cau, 0) + 1

    def muc_ngau_nhien(self, loai: str | None) -> dict | None:
        ds = (self.dl["loai"].get(loai or "") or {}).get("ho_so") or []
        return self.rng.choice(ds) if ds else None

    def tieu_de_cua(self, muc: dict) -> str:
        """Tiêu đề cho một hồ sơ rút trúng `muc` (#556): lần lượt tiêu đề gốc rồi từng `bien_the`, để nhiều hồ sơ cùng
        một vấn đề không trùng hệt tiêu đề. Lần lượt chứ không rút ngẫu nhiên: không ăn vào dãy số của hạt giống nội
        dung, nên mục, mô tả và trường riêng của mọi hồ sơ giữ như trước; hồ sơ đầu tiên của mỗi mục giữ tiêu đề cũ."""
        cac = [muc["tieu_de"], *(muc.get("bien_the") or [])]
        lan = self.lan_dung.get(muc["tieu_de"], 0)
        self.lan_dung[muc["tieu_de"]] = lan + 1
        return cac[lan % len(cac)]

    def chi_tiet(self, loai: str | None, muc: dict | None, them: dict | None, ngay_gui: date) -> dict:
        """Bộ trường riêng của loại `loai`: giá trị khai ở `them`, rồi ở mục `muc`, rồi rút từ kho của loại.
        Chỉ trường cụm khai cho loại, đúng kiểu; null là cố ý để trống."""
        kho = (self.dl["loai"].get(loai or "") or {}).get("truong") or {}
        rieng = {**((muc or {}).get("truong") or {}), **(them or {})}
        kq: dict = {}
        for t in self.khai.get(loai or "", []):
            if t["ma"] in rieng:
                tho = rieng[t["ma"]]
            elif kho.get(t["ma"]):
                tho = self.rng.choice(kho[t["ma"]])
            else:
                tho = None
            gia_tri = None if tho is None else gia_tri_hop_le(t, tho, ngay_gui)
            if tho is not None and gia_tri is None:
                self._bao(f"giá trị không hợp lệ cho trường {loai}/{t['ma']} — bỏ trống")
            if gia_tri is None:
                if t["bat_buoc"]:
                    self._bao(f"trường bắt buộc {loai}/{t['ma']} không có giá trị trong tệp dữ liệu")
                continue
            kq[t["ma"]] = gia_tri
        return kq

    def ghi_chu(self, hoat_dong: str, loai: str | None) -> str:
        bo = self.dl["ghi_chu"]
        theo = bo.get(hoat_dong) or {}
        ds = list(theo.get(loai or "", [])) + list(theo.get("_chung", []))
        return self.rng.choice(ds or bo["_mac_dinh"])

    def bo_sung(self) -> str:
        return self.rng.choice(self.dl["bo_sung_mo_ta"])


def doi_ghi_chu(nd: NoiDung, ho_so: list, su_kien: list[dict]) -> None:
    """Ghi chú bộ sinh viết cho cạnh bắt buộc ghi chú thành câu của tệp dữ liệu, theo hoạt động và loại."""
    loai = {hs.ma: hs.loai_that for hs in ho_so}
    for e in su_kien:
        if e["note"]:
            e["note"] = nd.ghi_chu(e["activity"], loai.get(e["case_id"]))


def gan_noi_dung(
    nd: NoiDung, ho_so: list, su_kien: list[dict], da_gan: dict[int, dict], ngay_gui: dict[int, date],
    nhan_loai: dict[str, str],
) -> tuple[dict[int, str], dict[int, dict], dict[int, dict]]:
    """Tiêu đề, mô tả, trường riêng cho mọi hồ sơ mẫu. Lần người gửi sửa nội dung trong nhật ký được viết lại
    theo nội dung mới — `changes` của mô tả, và của trường riêng khi lần sửa đổi luôn loại (ràng buộc
    `edit-content` kiểm trường riêng theo loại mới). Trả tiêu đề, trường riêng và mục nội dung đã rút (#556 — cách
    giải quyết đi theo mục) theo mã hồ sơ mẫu."""
    truong_da_giai = nd.dl.get("truong_ho_so_da_giai_quyet") or {}
    ds_theo_ho_so = theo_ho_so(su_kien)
    tieu_de: dict[int, str] = {}
    chi_tiet: dict[int, dict] = {}
    muc_theo_ho_so: dict[int, dict] = {}
    for hs in ho_so:
        ds = ds_theo_ho_so.get(hs.ma, [])
        if hs.ma in da_gan:
            m = da_gan[hs.ma]
            muc, them, mo_ta = None, truong_da_giai.get(m["ma"]), hs.mo_ta
            tieu_de[hs.ma] = m["tieu_de"]
        else:
            muc = nd.muc_ngau_nhien(hs.loai_that)
            them = None
            # Loại không có nội dung trong tệp: nhãn loại làm tiêu đề, mô tả trống — không vỡ
            tieu_de[hs.ma] = nd.tieu_de_cua(muc) if muc else nhan_loai.get(hs.loai_that, hs.loai_that)
            mo_ta = muc["mo_ta"] if muc else ""
            if muc:
                muc_theo_ho_so[hs.ma] = muc
        muc_cua_loai = {hs.loai_that: (muc, them)}

        def bo_truong(loai: str | None, _ma: int = hs.ma, _muc: dict = muc_cua_loai) -> dict:
            # Mục của chính hồ sơ khi đúng loại; loại khác (người gửi chọn nhầm) rút một mục của loại đó
            m_loai, t_loai = _muc.get(loai or "", (nd.muc_ngau_nhien(loai), None))
            return nd.chi_tiet(loai, m_loai, t_loai, ngay_gui[_ma])

        # Loại lúc gửi: giá trị "từ" của lần đổi loại đầu tiên, không đổi lần nào thì là loại cuối
        doi_loai = [json.loads(e["changes"])["request_type_code"] for e in ds if '"request_type_code"' in e["changes"]]
        loai_gui = doi_loai[0]["from"] if doi_loai else hs.loai
        truong = bo_truong(loai_gui)
        loai_hien = loai_gui
        for e in ds:
            if not e["changes"] or '"description"' not in e["changes"]:
                if e["changes"] and '"request_type_code"' in e["changes"]:
                    loai_hien = json.loads(e["changes"])["request_type_code"]["to"]
                continue
            thay = json.loads(e["changes"])
            moi = f"{mo_ta} {nd.bo_sung()}".strip()
            thay["description"] = {"from": mo_ta, "to": moi}
            mo_ta = moi
            if "request_type_code" in thay:
                loai_hien = thay["request_type_code"]["to"]
                truong_moi = bo_truong(loai_hien)
                if truong_moi != truong:
                    thay["details"] = {"from": truong, "to": truong_moi}
                truong = truong_moi
            e["changes"] = json.dumps(thay, ensure_ascii=False)
        hs.mo_ta = mo_ta
        chi_tiet[hs.ma] = truong
    return tieu_de, chi_tiet, muc_theo_ho_so


def gan_cach_giai_quyet(
    cau_hinh: dict, su_kien: list[dict], canh: dict, da_gan: dict[int, dict], muc_theo_ho_so: dict[int, dict],
    rng: random.Random,
) -> int:
    """Cách giải quyết ở lần hoàn thành cuối của hồ sơ mẫu đóng đạt (#556): `cach_giai_quyet` của mục nội dung hồ
    sơ đã rút, với xác suất `ty_le_co_ghi` — ô không bắt buộc. Hồ sơ đã gắn nội dung thật (`da_gan`) giữ cách giải
    quyết của nó; lần hoàn thành đã có ghi chú thì không đè. Sửa ghi chú tại chỗ TRƯỚC khi INSERT. Trả số hồ sơ đã
    ghi."""
    ty_le = float(cau_hinh["ty_le_co_ghi"])
    so = 0
    for ma, ds in theo_ho_so(su_kien).items():
        cach = (muc_theo_ho_so.get(ma) or {}).get("cach_giai_quyet")
        if ma in da_gan or not cach:
            continue
        cuoi = ds[-1]
        if (cuoi["from_state"], cuoi["to_state"], cuoi["activity"]) not in canh["dat"]:
            continue
        xong = [e for e in ds if (e["from_state"], e["to_state"], e["activity"]) in canh["xong"]]
        if not xong or xong[-1]["note"] or rng.random() >= ty_le:
            continue
        xong[-1]["note"] = cach
        so += 1
    return so


def dat_ten(du_lieu: dict, ho_so: list, su_kien: list[dict], rng: random.Random) -> dict[str, str]:
    """Mỗi mã ảo một tên cố định, không hai mã trùng tên. Nhãn hệ thống giữ nguyên. Đổi nhãn tại chỗ."""
    ma: set[str] = set()
    for hs in ho_so:
        ma.add(hs.nguoi_gui)
        if hs.nguoi_xu_ly:
            ma.add(hs.nguoi_xu_ly)
    for e in su_kien:
        if e["actor"] not in TAC_NHAN_HE_THONG_CA:
            ma.add(e["actor"])
        if '"assignee_id"' in e["changes"]:
            gn = json.loads(e["changes"])["assignee_id"]
            ma.update(x for x in (gn.get("from"), gn.get("to")) if x)
    ten = list(dict.fromkeys(du_lieu["ten_nguoi"]))
    if len(ten) < len(ma):
        sys.exit(f"Tệp {NOI_DUNG.name} có {len(ten)} tên khác nhau, cần {len(ma)} — không nạp gì.")
    rng.shuffle(ten)
    bang = dict(zip(sorted(ma), ten))
    for e in su_kien:
        if e["actor"] in bang:
            e["actor_label"] = bang[e["actor"]]
        if '"assignee_id"' in e["changes"]:
            thay = json.loads(e["changes"])
            gn = thay["assignee_id"]
            for khoa, nhan in (("from", "from_label"), ("to", "to_label")):
                if nhan in gn:
                    gn[nhan] = bang.get(gn.get(khoa)) if gn.get(khoa) else gn[nhan]
            e["changes"] = json.dumps(thay, ensure_ascii=False)
    return bang


def sinh_goi_y(bo: BoSinh, cau_hinh: dict, ho_so: list, su_kien: list[dict], rng: random.Random) -> None:
    """`suggestion` cho từng sự kiện, đúng khuôn `ghi_nhan_goi_y` của app/intelligence/goi_y.py:
    `{trường: {suggested, chosen, overridden, source, confidence}}`. Chỉ cạnh người (không phải người gửi) có
    ràng buộc quản trường có gợi ý; `chosen` là giá trị hồ sơ nhận ở lần chuyển đó, ô trống thì không ghi.
    Không nguồn nào có số độ tin cậy thật nên `confidence` để trống, như hệ thống."""
    ty_le = float(cau_hinh["ty_le_ghi_de"])
    nguon = cau_hinh["nguon"]
    canh = {(c.tu, c.den, c.hoat_dong): c for c in bo.canh if not c.he_thong}
    nguoi_gui = {hs.ma: hs.nguoi_gui for hs in ho_so}
    ds_theo_ho_so = theo_ho_so(su_kien)

    def doc_trang_thai(ds: list[dict], loai_dau: str | None):
        """Giá trị bốn trường quyết định ngay sau mỗi sự kiện."""
        gt = {"request_type_code": loai_dau, "priority_code": None, "department_code": None, "assignee_id": None}
        for e in ds:
            for k, v in (json.loads(e["changes"]) if e["changes"] else {}).items():
                if k in gt:
                    gt[k] = v["to"]
            yield e, dict(gt)

    def loai_dau(hs, ds) -> str | None:
        doi = [json.loads(e["changes"])["request_type_code"] for e in ds if '"request_type_code"' in e["changes"]]
        return doi[0]["from"] if doi else hs.loai

    # Người xử lý từng có ở mỗi phòng — ứng viên cho gợi ý theo tải việc
    nguoi_theo_phong: dict[str, set[str]] = {}
    for hs in ho_so:
        ds = ds_theo_ho_so.get(hs.ma, [])
        for _, gt in doc_trang_thai(ds, loai_dau(hs, ds)):
            if gt["department_code"] and gt["assignee_id"]:
                nguoi_theo_phong.setdefault(gt["department_code"], set()).add(gt["assignee_id"])

    def gia_tri_khac(truong: str, chon: str, gt: dict) -> list[str]:
        if truong == "request_type_code":
            ds = list(bo.loai)
        elif truong == "priority_code":
            ds = list(bo.muc_uu_tien)
        elif truong == "department_code":
            ds = list(bo.phong_ban)
        else:
            ds = sorted(nguoi_theo_phong.get(gt["department_code"] or "", set()))
        return [x for x in ds if x != chon]

    for hs in ho_so:
        ds = ds_theo_ho_so.get(hs.ma, [])
        # Gợi ý của mô hình tính một lần lúc gửi, nên mọi lần xác nhận trên hồ sơ so với cùng một giá trị
        cua_ho_so: dict[str, str] = {}
        for e, gt in doc_trang_thai(ds, loai_dau(hs, ds)):
            if e["actor"] in TAC_NHAN_HE_THONG_CA or e["actor"] == nguoi_gui[hs.ma]:
                continue
            c = canh.get((e["from_state"], e["to_state"], e["activity"]))
            if c is None:
                continue
            truong_gui = {TRUONG_THEO_RANG_BUOC[g] for g in c.rang_buoc if g in TRUONG_THEO_RANG_BUOC}
            dau: dict = {}
            for truong in sorted(truong_gui):
                ma_nguon = nguon.get(truong)
                chon = gt.get(truong)
                if not ma_nguon or chon in (None, ""):
                    continue
                if ma_nguon == NGUON_BANG_ANH_XA:
                    goi_y = bo.phong_mac_dinh.get(gt["request_type_code"] or "")
                    if goi_y is None:
                        continue
                else:
                    goi_y = cua_ho_so.get(truong) if truong != "assignee_id" else None
                    if goi_y is None:
                        khac = gia_tri_khac(truong, chon, gt)
                        goi_y = rng.choice(khac) if khac and rng.random() < ty_le else chon
                        if truong != "assignee_id":
                            cua_ho_so[truong] = goi_y
                dau[truong] = {"suggested": goi_y, "chosen": chon, "overridden": chon != goi_y,
                               "source": ma_nguon, "confidence": None}
            e["suggestion"] = json.dumps(dau, ensure_ascii=False) if dau else ""


def sinh_luot_xem(cau_hinh: dict, ho_so: list, rng: random.Random) -> list[list]:
    """Phiên soạn đã thấy hồ sơ tương tự: một phần hồ sơ mẫu xem rồi vẫn gửi, thêm các phiên bỏ không gửi sao
    cho bỏ / (bỏ + gửi) quanh tỷ lệ ngăn chặn. Mốc thời gian tính từ lúc gửi của hồ sơ làm mốc, bằng SQL.
    Dòng: `[phiên, mã hồ sơ đã gửi, mã hồ sơ làm mốc, người gửi, phút trước mốc, số lần xem, lý do bỏ, phút tới
    lúc bỏ, loại]`."""
    def doan(khoa: str) -> int:
        a, b = cau_hinh[khoa]
        return rng.randint(int(a), int(b))

    def phien() -> str:
        return str(uuid.UUID(int=rng.getrandbits(128), version=4))

    dong = []
    for hs in ho_so:
        if rng.random() < float(cau_hinh["ty_le_ho_so_co_xem"]):
            dong.append([phien(), hs.ma, hs.ma, hs.nguoi_gui, doan("phut_xem_truoc_khi_gui"),
                         doan("so_lan_xem"), "", "", hs.loai_that])
    ty_le = float(cau_hinh["ty_le_ngan_chan"])
    so_bo = round(len(dong) * ty_le / (1 - ty_le)) if 0 <= ty_le < 1 else 0
    nguoi = sorted({hs.nguoi_gui for hs in ho_so})
    for _ in range(so_bo):
        moc = rng.choice(ho_so)
        het_gio = rng.random() < float(cau_hinh["ty_le_bo_vi_het_gio"])
        dong.append([phien(), "", moc.ma, rng.choice(nguoi), doan("phut_xem_truoc_khi_gui"), doan("so_lan_xem"),
                     BO_HET_GIO if het_gio else BO_NGUOI_GUI,
                     int(cau_hinh["phut_het_gio"]) if het_gio else doan("phut_nguoi_gui_bo"), moc.loai_that])
    return dong


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="Nạp dữ liệu trình diễn vào cụm đang chạy.")
    p.add_argument("--xac-nhan", action="store_true",
                   help="Bắt buộc: xác nhận đây là cụm thử hay cụm trình diễn")
    p.add_argument("--so-ho-so", type=int, default=600)
    p.add_argument("--so-ngay", type=int, default=90, help="Hồ sơ gửi rải trong chừng này ngày tới nay")
    p.add_argument("--hat-giong", type=int, default=20261102)
    p.add_argument("--cho-tron", action="store_true",
                   help="Cho nạp cả khi cụm đã có hồ sơ thật (không phải hồ sơ mẫu)")
    p.add_argument("--container", default="dxlab-postgres")
    p.add_argument("--nguoi-dung", default="dxlab")
    p.add_argument("--csdl", default="dxlab")
    ts = p.parse_args()

    if not ts.xac_nhan:
        sys.exit("Lệnh này ghi hồ sơ GIẢ vào cụm và không gỡ ra được (chỉ `down -v`).\n"
                 "Chỉ chạy trên cụm thử hay cụm trình diễn, kèm --xac-nhan.")

    quy_tac = doc_quy_tac_tu_cum(ts.container, ts.nguoi_dung, ts.csdl)
    bo = BoSinh(quy_tac, json.loads(json.dumps(KICH_BAN)), ts.hat_giong)
    # Hồ sơ mẫu nhận ra bằng mã người gửi ảo (đầu tệp), không bằng tiêu đề
    mau_sql = chuoi_sql(mau_ma_nguoi_gui(bo.vai_tro_nguoi_gui))
    that = int(psql(ts, f"SELECT count(*) FROM requests WHERE requester_id !~ {mau_sql}"))
    if that and not ts.cho_tron:
        sys.exit(f"Cụm đã có {that} hồ sơ không phải hồ sơ mẫu — có thể đây là môi trường thật. "
                 "Dừng. Chắc chắn là cụm thử thì chạy lại kèm --cho-tron.")

    du_lieu = json.loads(NOI_DUNG.read_text(encoding="utf-8"))
    # Bộ đo hồ sơ tương tự (scripts/do_ho_so_tuong_tu.py) nhận hồ sơ đã giải quyết bằng tiêu đề: không hồ sơ
    # mẫu nào khác được mang trùng tiêu đề của chúng
    da_giai_tieu_de = {m["tieu_de"] for m in json.loads(HO_SO_DA_GIAI_QUYET.read_text(encoding="utf-8"))["ho_so"]}
    for v in du_lieu["loai"].values():
        v["ho_so"] = [m for m in v.get("ho_so") or [] if m["tieu_de"] not in da_giai_tieu_de]
        # Tiêu đề biến thể (#556) cũng không được trùng tiêu đề của hồ sơ đã giải quyết
        for m in v["ho_so"]:
            m["bien_the"] = [t for t in m.get("bien_the") or [] if t not in da_giai_tieu_de]
    nhan_loai = dict(
        l.split("\t") for l in psql(ts, "SELECT code || E'\\t' || label FROM request_types").splitlines()
    )
    rng = random.Random(ts.hat_giong)

    # Lúc gửi: rải đều trên GIỜ LÀM VIỆC của khoảng ngày, nên không ai gửi lúc nửa đêm Chủ nhật
    bat_dau = f"now() - interval '{int(ts.so_ngay)} days'"
    tong = int(psql(ts, f"SELECT so_giay_lam_viec({bat_dau}, now())"))
    if tong <= 0:
        sys.exit("Lịch làm việc mặc định không có giờ làm nào trong khoảng ngày đã chọn.")
    lech = sorted(rng.randrange(tong) for _ in range(ts.so_ho_so))
    moc = psql(ts, f"""
        SELECT to_char(m AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') || E'\\t' ||
               so_giay_lam_viec(m, now())
        FROM unnest({mang(lech)}) WITH ORDINALITY AS u(o, i),
             LATERAL (SELECT moc_sau_giay_lam_viec({bat_dau}, u.o) AS m) x
        ORDER BY u.i
    """).splitlines()

    ho_so, su_kien = [], []
    for ma, dong in enumerate(moc, start=1):
        _, con_lai = dong.split("\t")
        hs, ds = bo.sinh_ho_so(ma, GOC_AO, GOC_AO + timedelta(seconds=int(con_lai)))
        ho_so.append(hs)
        su_kien.extend(ds)
    loi = tu_kiem(bo, ho_so, su_kien)
    if loi:
        print(f"Bộ sinh tự kiểm thấy {len(loi)} lỗi — không nạp gì:")
        for d in loi[:20]:
            print(f"  {d}")
        return 1

    # Mọi thay đổi dưới đây sửa hồ sơ và sự kiện TRƯỚC khi INSERT: không dòng nhật ký nào bị sửa sau đó.
    # Ghi chú đổi trước, để cách giải quyết của hồ sơ đã giải quyết không bị đè.
    nd = NoiDung(du_lieu, doc_truong_rieng(ts), random.Random(ts.hat_giong + HAT_NOI_DUNG))
    doi_ghi_chu(NoiDung(du_lieu, {}, random.Random(ts.hat_giong + HAT_GHI_CHU)), ho_so, su_kien)
    canh_ket_thuc = doc_canh_ket_thuc(ts)
    da_gan = gan_ho_so_da_giai_quyet(ho_so, su_kien, canh_ket_thuc)
    ngay_gui = {hs.ma: date.fromisoformat(dong.split("\t")[0][:10]) for hs, dong in zip(ho_so, moc)}
    tieu_de, chi_tiet, muc_theo_ho_so = gan_noi_dung(nd, ho_so, su_kien, da_gan, ngay_gui, nhan_loai)
    so_co_cach = gan_cach_giai_quyet(du_lieu["cach_giai_quyet"], su_kien, canh_ket_thuc, da_gan, muc_theo_ho_so,
                                     random.Random(ts.hat_giong + HAT_CACH_GIAI_QUYET))
    sinh_goi_y(bo, du_lieu["goi_y"], ho_so, su_kien, random.Random(ts.hat_giong + HAT_GOI_Y))
    ten = dat_ten(du_lieu, ho_so, su_kien, random.Random(ts.hat_giong + HAT_TEN))
    dong_xem = sinh_luot_xem(du_lieu["ngan_chan"], ho_so, random.Random(ts.hat_giong + HAT_XEM))
    ds_theo_ho_so = theo_ho_so(su_kien)
    da_giai = [
        [hs.ma] for hs in ho_so
        if ds_theo_ho_so.get(hs.ma)
        and (ds_theo_ho_so[hs.ma][-1]["from_state"], ds_theo_ho_so[hs.ma][-1]["to_state"],
             ds_theo_ho_so[hs.ma][-1]["activity"]) in canh_ket_thuc["dat"]
    ]
    for cau, so in sorted(nd.canh_bao.items()):
        print(f"Lưu ý: {so} lần {cau}.")

    def giay(luc: datetime | None) -> str:
        return "" if luc is None else str(int((luc - GOC_AO).total_seconds()))

    dong_ho_so = []
    for hs, dong in zip(ho_so, moc):
        tao, _ = dong.split("\t")
        dong_ho_so.append([
            hs.ma, tao + "+00", hs.trang_thai, tieu_de[hs.ma], hs.mo_ta, hs.nguoi_gui, ten[hs.nguoi_gui],
            hs.loai or "", hs.phong or "", hs.uu_tien or "", hs.nguoi_xu_ly or "",
            ten.get(hs.nguoi_xu_ly or "", ""), json.dumps(chi_tiet[hs.ma], ensure_ascii=False),
            int(hs.chay_giay), int(hs.dung_giay), giay(hs.doan_mo_tu),
        ])
    dong_su_kien = [
        [e["case_id"], i, e["activity"], giay(e["timestamp"]), e["actor"], e["actor_label"],
         e["from_state"], e["to_state"], e["note"], e["changes"], e.get("suggestion", "")]
        for i, e in enumerate(su_kien)
    ]
    dong_danh_gia = sinh_danh_gia(ts, su_kien)

    sql = (
        "CREATE TEMP TABLE nap_ho_so (ma int, tao timestamptz, trang_thai text, tieu_de text, mo_ta text, "
        "nguoi_gui text, nhan_nguoi_gui text, loai text, phong text, uu_tien text, nguoi_xu_ly text, "
        "nhan_nguoi_xu_ly text, chi_tiet jsonb, chay bigint, dung bigint, doan_lech bigint);\n"
        "CREATE TEMP TABLE nap_su_kien (ma int, thu_tu int, hoat_dong text, lech bigint, tac_nhan text, "
        "nhan_tac_nhan text, tu text, den text, ghi_chu text, thay_doi text, goi_y text);\n"
        + copy_khoi("nap_ho_so", ["ma", "tao", "trang_thai", "tieu_de", "mo_ta", "nguoi_gui",
                                  "nhan_nguoi_gui", "loai", "phong", "uu_tien", "nguoi_xu_ly",
                                  "nhan_nguoi_xu_ly", "chi_tiet", "chay", "dung", "doan_lech"], dong_ho_so)
        + copy_khoi("nap_su_kien", ["ma", "thu_tu", "hoat_dong", "lech", "tac_nhan", "nhan_tac_nhan",
                                    "tu", "den", "ghi_chu", "thay_doi", "goi_y"], dong_su_kien)
        + "CREATE TEMP TABLE nap_danh_gia (ma int, thu_tu int, diem smallint, nhan_xet text);\n"
        + copy_khoi("nap_danh_gia", ["ma", "thu_tu", "diem", "nhan_xet"], dong_danh_gia)
        + "CREATE TEMP TABLE nap_xem (phien uuid, ma_gui int, ma_moc int, nguoi text, phut_truoc int, "
          "so_lan int, ly_do text, phut_bo int, loai text);\n"
        + copy_khoi("nap_xem", ["phien", "ma_gui", "ma_moc", "nguoi", "phut_truoc", "so_lan", "ly_do",
                                "phut_bo", "loai"], dong_xem)
        + "CREATE TEMP TABLE nap_da_giai (ma int);\n"
        + copy_khoi("nap_da_giai", ["ma"], da_giai)
        + f"""
        -- Mã hồ sơ cấp trước từ chính dãy số của cột id, mỗi hồ sơ mẫu một mã — không ghép theo tiêu đề,
        -- vì tiêu đề của hồ sơ mẫu được phép trùng nhau như ngoài đời
        CREATE TEMP TABLE nap_ma AS
            SELECT h.ma, nextval(pg_get_serial_sequence('requests', 'id')) AS id FROM nap_ho_so h ORDER BY h.ma;
        INSERT INTO requests (id, rule_set_id, current_state, title, description, requester_id,
            requester_label, request_type_code, department_code, priority_code, assignee_id,
            assignee_label, details, sla_running_seconds, sla_paused_seconds, sla_segment_since,
            created_at, updated_at)
        OVERRIDING SYSTEM VALUE
        SELECT m.id, (SELECT id FROM rule_sets WHERE is_active AND process_code = (SELECT code FROM processes WHERE is_app_default)), h.trang_thai, h.tieu_de, h.mo_ta,
               h.nguoi_gui, h.nhan_nguoi_gui, nullif(h.loai, ''), nullif(h.phong, ''),
               nullif(h.uu_tien, ''), nullif(h.nguoi_xu_ly, ''), nullif(h.nhan_nguoi_xu_ly, ''),
               h.chi_tiet, h.chay, h.dung,
               CASE WHEN h.doan_lech IS NOT NULL THEN moc_sau_giay_lam_viec(h.tao, h.doan_lech) END,
               h.tao, h.tao
        FROM nap_ho_so h JOIN nap_ma m USING (ma) ORDER BY h.ma;

        -- Mỗi hồ sơ mẫu đúng một mã, mỗi mã một hồ sơ: lệch là dừng, cả giao dịch không ghi gì
        DO $$
        BEGIN
            IF (SELECT count(*) FROM nap_ma) <> (SELECT count(*) FROM nap_ho_so)
               OR (SELECT count(DISTINCT ma) FROM nap_ma) <> (SELECT count(*) FROM nap_ma)
               OR (SELECT count(DISTINCT id) FROM nap_ma) <> (SELECT count(*) FROM nap_ma)
               OR (SELECT count(*) FROM requests WHERE id IN (SELECT id FROM nap_ma)) <> (SELECT count(*) FROM nap_ho_so)
            THEN
                RAISE EXCEPTION 'Ghép mã hồ sơ mẫu lệch: % dòng nap_ma cho % hồ sơ',
                    (SELECT count(*) FROM nap_ma), (SELECT count(*) FROM nap_ho_so);
            END IF;
        END $$;

        INSERT INTO event_log (case_id, activity, timestamp, actor, actor_label, from_state,
            to_state, note, changes, suggestion)
        SELECT m.id, s.hoat_dong, moc_sau_giay_lam_viec(h.tao, s.lech), s.tac_nhan,
               s.nhan_tac_nhan, s.tu, s.den, nullif(s.ghi_chu, ''), nullif(s.thay_doi, '')::jsonb,
               nullif(s.goi_y, '')::jsonb
        FROM nap_su_kien s JOIN nap_ma m USING (ma) JOIN nap_ho_so h USING (ma)
        ORDER BY s.ma, s.thu_tu;

        -- Mức hài lòng (#433): gắn đúng dòng nhật ký của lần xác nhận — cùng hồ sơ, cùng mốc, cùng cạnh
        INSERT INTO case_feedback (case_id, event_id, score, comment, created_at)
        SELECT m.id, e.id, d.diem, nullif(d.nhan_xet, ''), e.timestamp
        FROM nap_danh_gia d
        JOIN nap_ma m USING (ma)
        JOIN nap_ho_so h USING (ma)
        JOIN nap_su_kien s ON s.ma = d.ma AND s.thu_tu = d.thu_tu
        JOIN event_log e ON e.case_id = m.id AND e.activity = s.hoat_dong AND e.to_state = s.den
                        AND e.timestamp = moc_sau_giay_lam_viec(h.tao, s.lech);

        -- Mốc sửa gần nhất và số lần mở lại theo nhật ký vừa ghi (ràng buộc reopen-limit đọc nó)
        UPDATE requests r SET updated_at = coalesce(e.luc, r.created_at),
               reopen_count = coalesce(e.mo_lai, 0)
        FROM nap_ma m
        LEFT JOIN (
            SELECT l.case_id, max(l.timestamp) AS luc,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM transitions t JOIN transition_guards g ON g.transition_id = t.id
                       WHERE t.rule_set_id = (SELECT id FROM rule_sets WHERE is_active AND process_code = (SELECT code FROM processes WHERE is_app_default))
                         AND t.from_state = l.from_state AND t.to_state = l.to_state
                         AND g.guard_code = 'reopen-limit')) AS mo_lai
            FROM event_log l GROUP BY l.case_id
        ) e ON e.case_id = m.id
        WHERE r.id = m.id;

        -- Lượt xem hồ sơ tương tự (#319): gợi ý là hồ sơ mẫu đã giải quyết, đóng trước lúc xem, cùng loại
        -- trước. Lúc xem tính lùi từ lúc gửi của hồ sơ làm mốc (UTC); không có hồ sơ nào để gợi ý thì hệ
        -- thống không hiện gì — không ghi lượt xem.
        INSERT INTO similar_case_views (session_id, requester_id, viewed_at, view_count, suggested_case_ids,
            top_case_id, submitted_case_id, abandoned_at, abandon_reason)
        SELECT x.phien, x.nguoi, v.luc, x.so_lan, g.ma_goi_y, g.ma_goi_y[1], mg.id,
               -- COPY dạng CSV đọc ô rỗng thành NULL: phiên vẫn gửi không có lý do bỏ
               CASE WHEN coalesce(x.ly_do, '') <> '' THEN least(v.luc + make_interval(mins => x.phut_bo), now()) END,
               nullif(x.ly_do, '')
        FROM nap_xem x
        JOIN nap_ma mm ON mm.ma = x.ma_moc
        JOIN requests rm ON rm.id = mm.id
        LEFT JOIN nap_ma mg ON mg.ma = x.ma_gui
        CROSS JOIN LATERAL (SELECT rm.created_at - make_interval(mins => x.phut_truoc) AS luc) v
        CROSS JOIN LATERAL (
            SELECT array_agg(c.id ORDER BY c.thu_tu) AS ma_goi_y FROM (
                SELECT r.id, row_number() OVER (ORDER BY (r.request_type_code = x.loai) DESC,
                       md5(x.phien::text || r.id::text)) AS thu_tu
                FROM nap_da_giai d JOIN nap_ma m USING (ma) JOIN requests r ON r.id = m.id
                WHERE r.updated_at < v.luc
                ORDER BY 2 LIMIT {int(du_lieu["ngan_chan"]["so_goi_y"])}
            ) c
        ) g
        WHERE g.ma_goi_y IS NOT NULL;

        SELECT count(*) || ' hồ sơ, ' || (SELECT count(*) FROM event_log WHERE case_id IN
               (SELECT id FROM nap_ma)) || ' sự kiện, ' || (SELECT count(*) FROM similar_case_views
               WHERE requester_id ~ {mau_sql}) || ' lượt xem hồ sơ tương tự' FROM nap_ma;
        """
    )
    print(f"Đã nạp {psql(ts, '', vao=sql)} — gửi rải trong {ts.so_ngay} ngày tới nay, "
          f"{len(da_gan)} hồ sơ đã giải quyết có nội dung thật, {so_co_cach} hồ sơ đóng đạt khác ghi cách giải "
          f"quyết, {len(ten)} tên người.")
    print(psql(ts, f"""
        SELECT 'Tỷ lệ vi phạm hạn ' || coalesce(round(100.0 * count(*) FILTER (WHERE vi_pham)
               / nullif(count(*), 0), 1)::text, '—') || ' % trên ' || count(*) || ' hồ sơ đã xong'
        FROM bao_cao_ho_so
        WHERE da_ket_thuc AND da_qua_phong_ban AND ma_ho_so IN
              (SELECT id FROM requests WHERE requester_id ~ {mau_sql})
    """))
    print(psql(ts, f"""
        SELECT 'Tỷ lệ ghi đè gợi ý ' || coalesce(round(100.0 * sum(so_ghi_de) / nullif(count(*), 0), 1)::text, '—')
               || ' % trên ' || count(*) || ' lượt'
        FROM bao_cao_goi_y WHERE ma_ho_so IN (SELECT id FROM requests WHERE requester_id ~ {mau_sql})
    """))
    print(psql(ts, f"""
        SELECT 'Tỷ lệ ngăn chặn ' || coalesce(round(100.0 * sum(so_ngan_chan) / nullif(sum(so_da_ket_thuc), 0), 1)::text, '—')
               || ' % trên ' || coalesce(sum(so_da_ket_thuc), 0) || ' phiên đã kết thúc'
        FROM bao_cao_ngan_chan WHERE ma_phien IN (SELECT session_id FROM similar_case_views WHERE requester_id ~ {mau_sql})
    """))
    return 0


if __name__ == "__main__":
    sys.exit(main())
