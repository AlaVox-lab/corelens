# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Xuất nhật ký sự kiện dạng dữ liệu mở (#306): CSV và JSON, cột cố định; XES cho công cụ khai phá quy trình (#444).
#
# Đọc view `bao_cao_nhat_ky` (migration 0014) chứ không đọc thẳng `event_log`: view đó thêm
# sự kiện mở đầu dựng từ lúc tạo hồ sơ và thuộc tính của hồ sơ, và khai phá quy trình ở tầng
# I đọc đúng cùng một nguồn. Không có tên người, không có ghi chú: người thao tác chỉ ghi bằng
# mã định danh — dữ liệu xuất ra là để phân tích quy trình, không phải để đọc lại ai nói gì.
#
# Chỉ quản trị viên — cùng vai trò gác màn Hệ thống và lệnh quét hạn ở `app/main.py`.
#
# XES (IEEE 1849-2016) là chuẩn trao đổi của khai phá quy trình — ProM, Disco, PM4Py đọc thẳng. Mỗi hồ sơ
# một `trace` (`concept:name` = mã hồ sơ), mỗi dòng một `event`: `concept:name` = mã hoạt động,
# `time:timestamp` = mốc UTC, `org:resource` = mã người thao tác; các cột còn lại thành thuộc tính chuỗi cùng
# tên. Viết bằng `xml.etree` của thư viện chuẩn: dịch vụ này KHÔNG nhập thư viện khai phá AGPL (ADR-0007);
# bài kiểm cho PM4Py đọc lại tệp nằm trong dịch vụ khai phá (services/khai-pha/tests/).
#
# Đây là API của nền tảng lõi (#365, dữ liệu có cấu trúc): app/main.py gắn router hai lần — đường cũ
# `/analytics/event-log` và `/core/v1/events`. Tiền tố và nhãn OpenAPI gắn lúc include.

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import xml.etree.ElementTree as ET
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import Request as YeuCauHttp
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db import get_session
from app.kiem_toan import XUAT_NHAT_KY, ghi_truy_cap
from app.models.workflow_config import Process
from app.workflow.context import Actor

VAI_TRO_XUAT = "administrator"

# Thứ tự cột là một phần của định dạng: đổi thứ tự là đổi định dạng, công cụ đọc phía sau vỡ
COT = (
    "case_id",
    "activity",
    "timestamp",
    "actor",
    "from_state",
    "to_state",
    "request_type_code",
    "department_code",
    "priority_code",
    "rule_set_id",
    # Quy trình của hồ sơ (#376) — thêm ở CUỐI để công cụ đọc theo vị trí cột cũ không vỡ
    "process_code",
)

# Thuộc tính XES có sẵn nghĩa chuẩn (phần mở rộng Concept, Time, Organizational) — cột còn lại giữ tên cột
COT_XES_CHUAN = {"activity": "concept:name", "timestamp": "time:timestamp", "actor": "org:resource"}
PHAN_MO_RONG_XES = (
    ("Concept", "concept", "http://www.xes-standard.org/concept.xesext"),
    ("Time", "time", "http://www.xes-standard.org/time.xesext"),
    ("Organizational", "org", "http://www.xes-standard.org/org.xesext"),
)

router = APIRouter()


def _gio_xes(v: dt.datetime) -> str:
    """xs:dateTime theo UTC, có phần nghìn giây như XES mẫu: 2026-11-19T03:04:05.123+00:00."""
    return v.astimezone(dt.UTC).isoformat(timespec="milliseconds")


def xes(dong: list) -> bytes:
    """Nhật ký XES 1.0 từ các dòng đã xếp theo hồ sơ rồi thời gian (thứ tự cột `COT`)."""
    goc = ET.Element("log", {"xes.version": "1.0", "xes.features": "nested-attributes",
                             "xmlns": "http://www.xes-standard.org/"})
    for ten, tien_to, uri in PHAN_MO_RONG_XES:
        ET.SubElement(goc, "extension", {"name": ten, "prefix": tien_to, "uri": uri})
    chung_trace = ET.SubElement(goc, "global", {"scope": "trace"})
    ET.SubElement(chung_trace, "string", {"key": "concept:name", "value": ""})
    chung_event = ET.SubElement(goc, "global", {"scope": "event"})
    ET.SubElement(chung_event, "string", {"key": "concept:name", "value": ""})
    ET.SubElement(chung_event, "date", {"key": "time:timestamp", "value": "1970-01-01T00:00:00.000+00:00"})
    ET.SubElement(goc, "classifier", {"name": "Activity", "keys": "concept:name"})

    trace, ho_so = None, object()
    for d in dong:
        hang = dict(zip(COT, d))
        if hang["case_id"] != ho_so:
            ho_so = hang["case_id"]
            trace = ET.SubElement(goc, "trace")
            ET.SubElement(trace, "string", {"key": "concept:name", "value": str(ho_so)})
        su_kien = ET.SubElement(trace, "event")
        for cot, gia_tri in hang.items():
            if cot == "case_id" or gia_tri is None:
                continue
            khoa = COT_XES_CHUAN.get(cot, cot)
            if isinstance(gia_tri, dt.datetime):
                ET.SubElement(su_kien, "date", {"key": khoa, "value": _gio_xes(gia_tri)})
            elif isinstance(gia_tri, int) and not isinstance(gia_tri, bool):
                ET.SubElement(su_kien, "int", {"key": khoa, "value": str(gia_tri)})
            else:
                ET.SubElement(su_kien, "string", {"key": khoa, "value": str(gia_tri)})
    # Thụt lề: người mở tệp bằng tay đọc được, công cụ khai phá thì bỏ qua khoảng trắng giữa các thẻ
    ET.indent(goc)
    return ET.tostring(goc, encoding="utf-8", xml_declaration=True)


def _gia_tri(v):
    # Mốc thời gian luôn ra UTC dạng ISO 8601, như nhật ký lưu
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.UTC).isoformat()
    return v


@router.get("")
def xuat_nhat_ky(
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[Actor, Depends(require_roles(VAI_TRO_XUAT))],
    yeu_cau: YeuCauHttp,
    format: Annotated[
        Literal["csv", "json", "xes"], Query(description="csv, json, hoặc xes (IEEE 1849) cho công cụ khai phá quy trình")
    ] = "csv",
    tu: Annotated[dt.date | None, Query(alias="from", description="Từ ngày, tính theo UTC")] = None,
    den: Annotated[dt.date | None, Query(alias="to", description="Tới hết ngày này, UTC")] = None,
    process: Annotated[
        str | None, Query(description="Chỉ một quy trình (GET /core/v1/workflow/processes); bỏ trống là mọi quy trình")
    ] = None,
) -> Response:
    """Nhật ký sự kiện trong khoảng ngày, mỗi dòng một sự kiện, xếp theo hồ sơ rồi thời gian.

    Khoảng ngày tính theo UTC, như mốc trong nhật ký; `to` lấy trọn ngày đó. Bỏ trống hai đầu là
    lấy hết. Mỗi hồ sơ mở đầu bằng sự kiện `create-case` dựng từ lúc tạo, `from_state` rỗng.

    `format=xes` cho tệp XES (IEEE 1849) mở thẳng bằng ProM, Disco, PM4Py: mỗi hồ sơ một trace, hoạt động là
    `concept:name`, mốc UTC là `time:timestamp`, người thao tác là `org:resource`.

    Mỗi dòng mang `process_code` (#376). `process` lọc một quy trình — khai phá hay phân tích một quy trình
    thì đừng trộn nhật ký của hai quy trình vào một mô hình. Bỏ trống là mọi quy trình: dữ liệu mở.

    Mỗi lần xuất ghi một dòng nhật ký truy cập kèm định dạng, khoảng ngày, quy trình (#431, app/kiem_toan.py).
    """
    if tu and den and tu > den:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid-range", "message": "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc."},
        )
    dieu_kien, tham_so = [], {}
    if process is not None:
        if session.get(Process, process) is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "unknown-process", "message": f"Không có quy trình mang mã {process!r}."},
            )
        dieu_kien.append("process_code = :quy_trinh")
        tham_so["quy_trinh"] = process
    if tu:
        dieu_kien.append("timestamp >= :tu")
        tham_so["tu"] = dt.datetime.combine(tu, dt.time(), dt.UTC)
    if den:
        dieu_kien.append("timestamp < :den")
        tham_so["den"] = dt.datetime.combine(den + dt.timedelta(days=1), dt.time(), dt.UTC)
    loc = f"WHERE {' AND '.join(dieu_kien)}" if dieu_kien else ""
    dong = session.execute(
        text(f"SELECT {', '.join(COT)} FROM bao_cao_nhat_ky {loc} ORDER BY case_id, timestamp, thu_tu"),
        tham_so,
    ).all()

    ten = "nhat-ky-su-kien"
    if tu or den:
        ten += f"_{tu or 'dau'}_{den or 'nay'}"
    if format == "xes":
        than = xes(dong)
        kieu = "application/xml; charset=utf-8"
    elif format == "json":
        than = json.dumps(
            [{c: _gia_tri(v) for c, v in zip(COT, d)} for d in dong], ensure_ascii=False
        ).encode("utf-8")
        kieu = "application/json; charset=utf-8"
    else:
        bo_dem = io.StringIO()
        viet = csv.writer(bo_dem, lineterminator="\r\n")
        viet.writerow(COT)
        viet.writerows([_gia_tri(v) for v in d] for d in dong)
        # Dấu BOM để bảng tính trên Windows nhận ra UTF-8 và hiện đúng chữ có dấu
        than = "\ufeff".encode("utf-8") + bo_dem.getvalue().encode("utf-8")
        kieu = "text/csv; charset=utf-8"
    ghi_truy_cap(
        yeu_cau, actor, XUAT_NHAT_KY,
        details={"format": format, "from": tu.isoformat() if tu else None, "to": den.isoformat() if den else None,
                 "process": process, "rows": len(dong)},
    )
    return Response(
        content=than,
        media_type=kieu,
        headers={
            "Content-Disposition": f'attachment; filename="{ten}.{format}"',
            "Cache-Control": "no-store",
        },
    )
