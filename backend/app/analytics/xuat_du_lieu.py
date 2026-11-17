# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Xuất nhật ký sự kiện dạng dữ liệu mở (#306): CSV và JSON, cột cố định.
#
# Đọc view `bao_cao_nhat_ky` (migration 0014) chứ không đọc thẳng `event_log`: view đó thêm
# sự kiện mở đầu dựng từ lúc tạo hồ sơ và thuộc tính của hồ sơ, và khai phá quy trình ở tầng
# I đọc đúng cùng một nguồn. Không có tên người, không có ghi chú: người thao tác chỉ ghi bằng
# mã định danh — dữ liệu xuất ra là để phân tích quy trình, không phải để đọc lại ai nói gì.
#
# Chỉ quản trị viên — cùng vai trò gác màn Hệ thống và lệnh quét hạn ở `app/main.py`.
#
# Đây là API của nền tảng lõi (#365, dữ liệu có cấu trúc): app/main.py gắn router hai lần — đường cũ
# `/analytics/event-log` và `/core/v1/events`. Tiền tố và nhãn OpenAPI gắn lúc include.

from __future__ import annotations

import csv
import datetime as dt
import io
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.db import get_session
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

router = APIRouter()


def _gia_tri(v):
    # Mốc thời gian luôn ra UTC dạng ISO 8601, như nhật ký lưu
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.UTC).isoformat()
    return v


@router.get("")
def xuat_nhat_ky(
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[Actor, Depends(require_roles(VAI_TRO_XUAT))],
    format: Annotated[Literal["csv", "json"], Query(description="csv hoặc json")] = "csv",
    tu: Annotated[dt.date | None, Query(alias="from", description="Từ ngày, tính theo UTC")] = None,
    den: Annotated[dt.date | None, Query(alias="to", description="Tới hết ngày này, UTC")] = None,
    process: Annotated[
        str | None, Query(description="Chỉ một quy trình (GET /core/v1/workflow/processes); bỏ trống là mọi quy trình")
    ] = None,
) -> Response:
    """Nhật ký sự kiện trong khoảng ngày, mỗi dòng một sự kiện, xếp theo hồ sơ rồi thời gian.

    Khoảng ngày tính theo UTC, như mốc trong nhật ký; `to` lấy trọn ngày đó. Bỏ trống hai đầu là
    lấy hết. Mỗi hồ sơ mở đầu bằng sự kiện `create-case` dựng từ lúc tạo, `from_state` rỗng.

    Mỗi dòng mang `process_code` (#376). `process` lọc một quy trình — khai phá hay phân tích một quy trình
    thì đừng trộn nhật ký của hai quy trình vào một mô hình. Bỏ trống là mọi quy trình: dữ liệu mở.
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
    if format == "json":
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
    return Response(
        content=than,
        media_type=kieu,
        headers={
            "Content-Disposition": f'attachment; filename="{ten}.{format}"',
            "Cache-Control": "no-store",
        },
    )
