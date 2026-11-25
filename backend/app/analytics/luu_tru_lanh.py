# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lưu trữ lạnh dữ liệu lịch sử ra kho đối tượng (#378) — nguyên lý (i) của đề thi: tách dữ liệu theo vòng
# đời, dữ liệu lịch sử xuống tầng lạnh để phân tích dài hạn mà không làm nghẽn hệ thống lõi.
#
# Bộ quét `cold-archive` theo khuôn `app/workflow/nhip_quet.py` (khóa tư vấn, nhịp sức khỏe trên màn Hệ
# thống). Mỗi lượt, với mỗi THÁNG ĐÃ KHÉP (tháng UTC cũ hơn `archive_min_age_months`) chưa có bản lưu:
#
#   <tiền tố><YYYY-MM>/nhat-ky-su-kien.csv.gz   nhật ký sự kiện của tháng, đúng cột của GET /core/v1/events
#   <tiền tố><YYYY-MM>/ho-so-ket-thuc.csv.gz    hồ sơ kết thúc trong tháng: cột quyết định và đồng hồ hạn
#   <tiền tố><YYYY-MM>/manifest.json            kỳ, quy trình, số dòng, SHA-256 từng tệp, lúc xuất, lược đồ
#
# Định dạng MỞ, không thêm thư viện: CSV theo RFC 4180 (UTF-8, có dòng tiêu đề, không BOM) nén gzip, bản kê
# JSON. Nén với mtime 0 nên cùng nội dung ra cùng mã băm.
#
# BẤT BIẾN. Bản lưu NIÊM PHONG khi manifest.json có mặt — ghi sau cùng, sau mọi tệp dữ liệu. Đã niêm phong
# thì không bao giờ ghi đè: chạy lại an toàn. Lượt hỏng giữa lúc ghi kho và lúc ghi sổ để lại bản đã niêm
# phong mà chưa có dòng `cold_archives`; lượt sau đọc manifest trong kho và ghi sổ theo nó, không xuất lại.
# Tệp dữ liệu không có manifest là dở dang, lượt sau ghi lại được.
#
# Dữ liệu cá nhân (ADR-0009): không cột tên người nào, không nội dung tự do (tiêu đề, mô tả, trường riêng,
# ghi chú, lời nhắn), không nội dung tệp đính kèm. Người chỉ xuất hiện bằng mã định danh (`sub` của
# Keycloak — bí danh, như dữ liệu xuất của #306). Lý do: bản lưu bất biến, nên một nhãn tên đi vào nó sẽ không
# bao giờ ẩn danh hóa được nữa; không đưa tên vào thì thao tác ẩn danh hóa của ADR-0009 vẫn đủ cho tầng lạnh.
#
# Tầng nóng giữ nguyên: nhật ký chỉ ghi thêm là nền của khai phá và kiểm toán, nên đợt này KHÔNG dọn gì
# khỏi cơ sở dữ liệu đang chạy. Tầng lạnh là bản sao niêm phong để phân tích dài hạn; xóa khỏi tầng nóng
# là việc tương lai, theo chính sách lưu giữ của ADR-0009.
#
# Hai thuộc tính trên dòng nhật ký (loại, phòng, ưu tiên) và hồ sơ đã kết thúc là ẢNH CHỤP lúc xuất — như
# GET /core/v1/events, chúng là thuộc tính hiện tại của hồ sơ. Hồ sơ mở lại rồi đóng lại sau khi tháng đã
# niêm phong thì có mặt ở cả bản cũ lẫn bản của tháng đóng lại.
#
# Chạy tay trong container dịch vụ (scripts/doc_luu_tru.py dùng hai lệnh sau):
#     python -m app.analytics.luu_tru_lanh chay              # một lượt ngay, có khóa và nhịp
#     python -m app.analytics.luu_tru_lanh tai 2026-10 manifest.json > manifest.json
#     python -m app.analytics.luu_tru_lanh so 2026-10        # dòng ghi sổ, JSON
#     python -m app.analytics.luu_tru_lanh dem-nong 2026-10  # số dòng của tháng ở tầng nóng, để đối chiếu

from __future__ import annotations

import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import sys
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.analytics.xuat_du_lieu import COT as COT_NHAT_KY
from app.analytics.xuat_du_lieu import VAI_TRO_XUAT
from app.auth.dependencies import require_roles
from app.config import get_settings
from app.db import get_session
from app.models.luu_tru import ColdArchive
from app.storage import objects
from app.workflow.context import Actor

TEN_BO_QUET_LUU_TRU = "cold-archive"
NHAN_BO_QUET_LUU_TRU = "Bộ lưu trữ lạnh"

DINH_DANG = "dx-os-lab/cold-archive"
# Tăng khi đổi cột hay ý nghĩa của tệp. Bản cũ giữ số của nó trong manifest và trong sổ.
PHIEN_BAN_LUOC_DO = 1

TEP_NHAT_KY = "nhat-ky-su-kien.csv.gz"
TEP_HO_SO = "ho-so-ket-thuc.csv.gz"
TEP_BAN_KE = "manifest.json"

MAU_KY = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Hồ sơ đã kết thúc: trường quyết định (CLAUDE.md mục 4.3), người bằng mã, đồng hồ hạn. Không tên, không nội
# dung tự do, không trường riêng theo loại (có thể chứa dữ liệu cá nhân). Thêm cột ở CUỐI và tăng
# PHIEN_BAN_LUOC_DO.
COT_HO_SO = (
    "case_id",
    "process_code",
    "rule_set_id",
    "request_type_code",
    "department_code",
    "priority_code",
    "final_state",
    "requester_id",
    "assignee_id",
    "parent_request_id",
    "created_at",
    "closed_at",
    "sla_running_seconds",
    "sla_extension_total_hours",
    "sla_extension_count",
    "reopen_count",
)

# Cùng nghĩa "kết thúc" với view `bao_cao_ho_so`: trạng thái hiện tại `is_terminal` theo bộ quy tắc của hồ
# sơ, mốc kết thúc là sự kiện cuối cùng (hồ sơ chưa có sự kiện nào thì là lúc tạo). Mọi quy trình.
CAU_HO_SO = """
    WITH ket_thuc AS (
        SELECT r.id, coalesce(max(e.timestamp), r.created_at) AS luc
        FROM requests r
        JOIN states s ON s.rule_set_id = r.rule_set_id AND s.code = r.current_state AND s.is_terminal
        LEFT JOIN event_log e ON e.case_id = r.id
        GROUP BY r.id, r.created_at
    )
    SELECT
        r.id AS case_id,
        rs.process_code,
        r.rule_set_id,
        r.request_type_code,
        r.department_code,
        r.priority_code,
        r.current_state AS final_state,
        r.requester_id,
        r.assignee_id,
        r.parent_request_id,
        r.created_at,
        k.luc AS closed_at,
        r.sla_running_seconds,
        r.sla_extension_total_hours,
        r.sla_extension_count,
        r.reopen_count
    FROM ket_thuc k
    JOIN requests r ON r.id = k.id
    JOIN rule_sets rs ON rs.id = r.rule_set_id
    WHERE k.luc >= :tu AND k.luc < :den
    ORDER BY r.id
"""

# Nhật ký: view `bao_cao_nhat_ky` như GET /core/v1/events — cùng cột, cùng thứ tự, kèm sự kiện mở đầu
CAU_NHAT_KY = (
    f"SELECT {', '.join(COT_NHAT_KY)} FROM bao_cao_nhat_ky "
    "WHERE timestamp >= :tu AND timestamp < :den ORDER BY case_id, timestamp, thu_tu"
)

# Mốc sớm nhất có dữ liệu: từ đó trở đi mỗi tháng đã khép có một bản lưu, kể cả tháng trống — sổ không có
# lỗ hổng, và tháng trống không bị hỏi lại mỗi lượt
CAU_MOC_DAU = "SELECT least((SELECT min(created_at) FROM requests), (SELECT min(timestamp) FROM event_log))"


class LoiLuuTru(Exception):
    """Bản lưu trong kho không khớp điều phải có (manifest của kỳ khác, mã băm sai)."""


# ---------------------------------------------------------------------------
# Kỳ
# ---------------------------------------------------------------------------


def khoang_cua(ky: str) -> tuple[dt.datetime, dt.datetime]:
    """[đầu tháng, đầu tháng sau) theo UTC."""
    if not MAU_KY.match(ky):
        raise ValueError(f"Kỳ phải dạng YYYY-MM: {ky!r}")
    nam, thang = int(ky[:4]), int(ky[5:])
    tu = dt.datetime(nam, thang, 1, tzinfo=dt.UTC)
    den = dt.datetime(nam + thang // 12, thang % 12 + 1, 1, tzinfo=dt.UTC)
    return tu, den


def _ky(moc: dt.datetime) -> str:
    moc = moc.astimezone(dt.UTC)
    return f"{moc.year:04d}-{moc.month:02d}"


def _thang_sau(ky: str) -> str:
    return _ky(khoang_cua(ky)[1])


def ky_khep_cuoi(bay_gio: dt.datetime, so_thang: int) -> str:
    """Kỳ mới nhất đã khép: lùi `so_thang` tháng từ tháng chứa `bay_gio` (UTC)."""
    moc = bay_gio.astimezone(dt.UTC)
    chi_so = moc.year * 12 + (moc.month - 1) - so_thang
    return f"{chi_so // 12:04d}-{chi_so % 12 + 1:02d}"


def cac_ky_can_luu(phien: Session, bay_gio: dt.datetime | None = None) -> list[str]:
    """Các tháng đã khép chưa có bản lưu, cũ trước, tối đa `archive_max_months_per_run`."""
    cau_hinh = get_settings()
    moc_dau = phien.execute(text(CAU_MOC_DAU)).scalar()
    if moc_dau is None:
        return []
    bay_gio = bay_gio or dt.datetime.now(dt.UTC)
    cuoi = ky_khep_cuoi(bay_gio, cau_hinh.archive_min_age_months)
    da_co = set(phien.scalars(select(ColdArchive.period)))
    ket_qua: list[str] = []
    ky = _ky(moc_dau)
    while ky <= cuoi and len(ket_qua) < cau_hinh.archive_max_months_per_run:
        if ky not in da_co:
            ket_qua.append(ky)
        ky = _thang_sau(ky)
    return ket_qua


# ---------------------------------------------------------------------------
# Xuất một tháng
# ---------------------------------------------------------------------------


def _gia_tri(v: Any) -> Any:
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.UTC).isoformat()
    return v


def _csv_gzip(cot: tuple[str, ...], dong: list) -> bytes:
    bo_dem = io.StringIO()
    viet = csv.writer(bo_dem, lineterminator="\r\n")
    viet.writerow(cot)
    viet.writerows([_gia_tri(v) for v in d] for d in dong)
    # mtime=0: cùng nội dung thì cùng byte, cùng mã băm
    return gzip.compress(bo_dem.getvalue().encode("utf-8"), mtime=0)


def sha256(noi_dung: bytes) -> str:
    return hashlib.sha256(noi_dung).hexdigest()


def tien_to_cua(ky: str) -> str:
    tien_to = get_settings().archive_prefix
    if tien_to and not tien_to.endswith("/"):
        tien_to += "/"
    return f"{tien_to}{ky}/"


def _dung_ban_luu(phien: Session, ky: str, bay_gio: dt.datetime) -> tuple[dict, dict[str, bytes]]:
    """Đọc tầng nóng, dựng hai tệp dữ liệu và bản kê (chưa ghi gì)."""
    tu, den = khoang_cua(ky)
    nhat_ky = phien.execute(text(CAU_NHAT_KY), {"tu": tu, "den": den}).all()
    ho_so = phien.execute(text(CAU_HO_SO), {"tu": tu, "den": den}).all()

    quy_trinh: dict[str, dict[str, int]] = {}
    vi_tri_nk, vi_tri_hs = COT_NHAT_KY.index("process_code"), COT_HO_SO.index("process_code")
    for d in nhat_ky:
        quy_trinh.setdefault(d[vi_tri_nk], {"events": 0, "closed_cases": 0})["events"] += 1
    for d in ho_so:
        quy_trinh.setdefault(d[vi_tri_hs], {"events": 0, "closed_cases": 0})["closed_cases"] += 1

    tep = {TEP_NHAT_KY: _csv_gzip(COT_NHAT_KY, nhat_ky), TEP_HO_SO: _csv_gzip(COT_HO_SO, ho_so)}
    mo_ta = {
        TEP_NHAT_KY: ("event_log", COT_NHAT_KY, len(nhat_ky)),
        TEP_HO_SO: ("closed_cases", COT_HO_SO, len(ho_so)),
    }
    ban_ke = {
        "format": DINH_DANG,
        "schema_version": PHIEN_BAN_LUOC_DO,
        "period": ky,
        "period_start": tu.isoformat(),
        "period_end": den.isoformat(),
        "timezone": "UTC",
        "exported_at": bay_gio.astimezone(dt.UTC).isoformat(),
        "processes": {k: quy_trinh[k] for k in sorted(quy_trinh, key=str)},
        "files": [
            {
                "name": ten,
                "content": mo_ta[ten][0],
                "media_type": "text/csv",
                "compression": "gzip",
                "encoding": "utf-8",
                "header": True,
                "columns": list(mo_ta[ten][1]),
                "rows": mo_ta[ten][2],
                "bytes": len(tep[ten]),
                "sha256": sha256(tep[ten]),
            }
            for ten in (TEP_NHAT_KY, TEP_HO_SO)
        ],
    }
    return ban_ke, tep


def xuat_thang(phien: Session, ky: str, bay_gio: dt.datetime | None = None) -> ColdArchive:
    """Niêm phong bản lưu của một tháng và ghi sổ. Không tự commit — `chay_luot_quet` lo giao dịch.

    Đã có dòng sổ: trả về dòng đó, không làm gì. Kho đã có manifest (lượt trước hỏng sau khi niêm phong):
    ghi sổ theo manifest đó, không xuất lại.
    """
    co_san = phien.get(ColdArchive, ky)
    if co_san is not None:
        return co_san
    cau_hinh = get_settings()
    thung, goc = cau_hinh.archive_bucket_name, tien_to_cua(ky)
    bay_gio = bay_gio or dt.datetime.now(dt.UTC)

    if objects.co_tep(goc + TEP_BAN_KE, thung):
        than_ban_ke = objects.doc_tep(goc + TEP_BAN_KE, thung)
        ban_ke = json.loads(than_ban_ke)
        if ban_ke.get("period") != ky:
            raise LoiLuuTru(f"{goc}{TEP_BAN_KE} trong kho là của kỳ {ban_ke.get('period')!r}, không phải {ky}")
    else:
        ban_ke, tep = _dung_ban_luu(phien, ky, bay_gio)
        for ten, noi_dung in tep.items():
            objects.luu_tep(goc + ten, noi_dung, "application/gzip", thung)
        than_ban_ke = (json.dumps(ban_ke, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        # Sau cùng: có manifest là bản lưu đã đủ
        objects.luu_tep(goc + TEP_BAN_KE, than_ban_ke, "application/json", thung)

    so_dong = {f["content"]: f["rows"] for f in ban_ke["files"]}
    ban_ghi = ColdArchive(
        period=ky,
        bucket=thung,
        object_prefix=goc,
        schema_version=ban_ke["schema_version"],
        event_rows=so_dong.get("event_log", 0),
        case_rows=so_dong.get("closed_cases", 0),
        manifest=ban_ke,
        manifest_sha256=sha256(than_ban_ke),
        exported_at=dt.datetime.fromisoformat(ban_ke["exported_at"]),
    )
    phien.add(ban_ghi)
    phien.flush()
    return ban_ghi


def quet_luu_tru(phien: Session) -> list[str]:
    """Một lượt bộ quét: niêm phong mọi tháng đã khép còn thiếu (tối đa số tháng cấu hình). Không tự commit."""
    da_xuat = []
    for ky in cac_ky_can_luu(phien):
        xuat_thang(phien, ky)
        da_xuat.append(ky)
    return da_xuat


def doc_tep_luu_tru(ban_ghi: ColdArchive, ten_tep: str) -> bytes:
    """Một tệp của bản lưu, đã kiểm mã băm với manifest trong sổ (manifest kiểm với mã băm trong sổ)."""
    noi_dung = objects.doc_tep(ban_ghi.object_prefix + ten_tep, ban_ghi.bucket)
    if ten_tep == TEP_BAN_KE:
        mong = ban_ghi.manifest_sha256
    else:
        mong = next(f["sha256"] for f in ban_ghi.manifest["files"] if f["name"] == ten_tep)
    if sha256(noi_dung) != mong:
        raise LoiLuuTru(f"Mã băm của {ban_ghi.object_prefix}{ten_tep} không khớp bản kê")
    return noi_dung


def dem_tang_nong(phien: Session, ky: str) -> dict[str, int]:
    """Số dòng của tháng ở tầng nóng, đọc bằng chính hai câu xuất — để đối chiếu với bản lưu."""
    tu, den = khoang_cua(ky)
    return {
        "event_rows": len(phien.execute(text(CAU_NHAT_KY), {"tu": tu, "den": den}).all()),
        "case_rows": len(phien.execute(text(CAU_HO_SO), {"tu": tu, "den": den}).all()),
    }


# ---------------------------------------------------------------------------
# API của lõi — gắn dưới /core/v1/archive (app/main.py), quyền như GET /core/v1/events
# ---------------------------------------------------------------------------

router = APIRouter()

KyDuong = Annotated[str, Path(pattern=MAU_KY.pattern, description="Kỳ dạng YYYY-MM (tháng UTC)")]


def _ban_ghi_hoac_404(phien: Session, ky: str) -> ColdArchive:
    ban_ghi = phien.get(ColdArchive, ky)
    if ban_ghi is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "archive-not-found", "message": f"Chưa có bản lưu trữ lạnh của kỳ {ky}."},
        )
    return ban_ghi


def _tom_tat(ban_ghi: ColdArchive, yeu_cau: Request) -> dict:
    return {
        "period": ban_ghi.period,
        "exported_at": ban_ghi.exported_at,
        "schema_version": ban_ghi.schema_version,
        "event_rows": ban_ghi.event_rows,
        "case_rows": ban_ghi.case_rows,
        "processes": ban_ghi.manifest.get("processes", {}),
        "manifest_sha256": ban_ghi.manifest_sha256,
        "url": yeu_cau.url_for("doc_ban_luu_tru", ky=ban_ghi.period).path,
    }


@router.get("", summary="Danh sách bản lưu trữ lạnh")
def liet_ke_ban_luu_tru(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(require_roles(VAI_TRO_XUAT))],
    request: Request,
) -> list[dict]:
    """Các bản lưu trữ lạnh đã niêm phong, mới trước: kỳ, số dòng, quy trình có mặt, mã băm của bản kê.

    Mỗi tháng UTC đã khép một bản, gồm nhật ký sự kiện và hồ sơ đã kết thúc trong tháng (CSV gzip) cùng
    `manifest.json`. Bản lưu bất biến: đã niêm phong thì không bao giờ ghi đè."""
    cac = session.scalars(select(ColdArchive).order_by(ColdArchive.period.desc())).all()
    return [_tom_tat(b, request) for b in cac]


@router.get("/{ky}", summary="Bản kê một kỳ lưu trữ")
def doc_ban_luu_tru(
    ky: KyDuong,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(require_roles(VAI_TRO_XUAT))],
    request: Request,
) -> dict:
    """Bản kê của một kỳ và liên kết tải từng tệp. Người đọc tải tệp, tính SHA-256 rồi so với `sha256` của
    tệp trong `manifest`, và so mã băm của chính manifest.json với `manifest_sha256`."""
    ban_ghi = _ban_ghi_hoac_404(session, ky)

    def _lien_ket(ten: str) -> str:
        return request.url_for("tai_tep_luu_tru", ky=ky, ten_tep=ten).path

    return {
        **_tom_tat(ban_ghi, request),
        "manifest": ban_ghi.manifest,
        "manifest_url": _lien_ket(TEP_BAN_KE),
        "files": [
            {k: f[k] for k in ("name", "content", "rows", "bytes", "sha256")} | {"url": _lien_ket(f["name"])}
            for f in ban_ghi.manifest["files"]
        ],
    }


@router.get("/{ky}/files/{ten_tep}", summary="Tải một tệp của bản lưu trữ")
def tai_tep_luu_tru(
    ky: KyDuong,
    ten_tep: str,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(require_roles(VAI_TRO_XUAT))],
) -> Response:
    """Tải một tệp của bản lưu (`manifest.json` hoặc một tệp mà bản kê liệt kê). Dịch vụ kiểm mã băm với
    bản kê trước khi trả: bản lưu bị sửa trong kho thì trả 502 thay vì trả dữ liệu sai."""
    ban_ghi = _ban_ghi_hoac_404(session, ky)
    ten_hop_le = {TEP_BAN_KE} | {f["name"] for f in ban_ghi.manifest["files"]}
    if ten_tep not in ten_hop_le:
        raise HTTPException(
            status_code=404,
            detail={"code": "archive-file-not-found", "message": f"Bản lưu {ky} không có tệp {ten_tep!r}."},
        )
    try:
        noi_dung = doc_tep_luu_tru(ban_ghi, ten_tep)
    except LoiLuuTru as loi:
        raise HTTPException(
            status_code=502, detail={"code": "archive-corrupted", "message": str(loi)}
        ) from loi
    except objects.KhoLoi as loi:
        raise HTTPException(
            status_code=502, detail={"code": "storage-unavailable", "message": "Kho đối tượng không phản hồi."}
        ) from loi
    return Response(
        content=noi_dung,
        media_type="application/json" if ten_tep == TEP_BAN_KE else "application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{ky}_{ten_tep}"',
            "Cache-Control": "no-store",
        },
    )


# ---------------------------------------------------------------------------
# Dòng lệnh trong container dịch vụ
# ---------------------------------------------------------------------------


def _dong_lenh(tham_so: list[str]) -> int:
    from app.db import SessionLocal
    from app.workflow.nhip_quet import chay_luot_quet

    if not tham_so:
        print(__doc__ or "chay | tai <kỳ> <tệp> | so <kỳ> | dem-nong <kỳ>", file=sys.stderr)
        return 2
    lenh = tham_so[0]
    with SessionLocal() as phien:
        if lenh == "chay":
            luot = chay_luot_quet(phien, TEN_BO_QUET_LUU_TRU, quet_luu_tru)
            print(json.dumps({"ran": luot.da_chay, "exported": luot.ket_qua or []}))
            return 0
        ky = tham_so[1] if len(tham_so) > 1 else ""
        if not MAU_KY.match(ky):
            print("Kỳ phải dạng YYYY-MM", file=sys.stderr)
            return 2
        if lenh == "dem-nong":
            print(json.dumps(dem_tang_nong(phien, ky)))
            return 0
        ban_ghi = phien.get(ColdArchive, ky)
        if ban_ghi is None:
            print(f"Chưa có bản lưu của kỳ {ky}", file=sys.stderr)
            return 1
        if lenh == "so":
            print(
                json.dumps(
                    {
                        "period": ban_ghi.period,
                        "bucket": ban_ghi.bucket,
                        "object_prefix": ban_ghi.object_prefix,
                        "manifest_sha256": ban_ghi.manifest_sha256,
                        "event_rows": ban_ghi.event_rows,
                        "case_rows": ban_ghi.case_rows,
                    }
                )
            )
            return 0
        ten_hop_le = {TEP_BAN_KE} | {f["name"] for f in ban_ghi.manifest["files"]}
        if lenh == "tai" and len(tham_so) == 3 and tham_so[2] in ten_hop_le:
            # Thô, không kiểm mã băm — người đọc tự kiểm (scripts/doc_luu_tru.py)
            sys.stdout.buffer.write(objects.doc_tep(ban_ghi.object_prefix + tham_so[2], ban_ghi.bucket))
            return 0
    print(f"Lệnh không rõ: {' '.join(tham_so)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_dong_lenh(sys.argv[1:]))
