# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Quan sát vận hành (#247): nhật ký có cấu trúc, mã yêu cầu xuyên cổng → dịch vụ, và số đo cơ bản.
#
# Ba việc, không thêm thư viện nào:
#
# 1. NHẬT KÝ JSON. Mỗi dòng nhật ký là một đối tượng JSON (`ts` UTC, `level`, `logger`, `msg`,
#    `request_id`, và `exc` khi có ngoại lệ) — `docker compose logs backend | jq` lọc được theo mã yêu
#    cầu. Đặt `DXLAB_LOG_FORMAT=text` để quay về dạng chữ khi đọc tay. Bộ ghi của uvicorn cũng được
#    gom về cùng định dạng; dòng truy cập do lớp giữa ở đây ghi (uvicorn chạy `--no-access-log`) để
#    mang được mã yêu cầu và thời gian xử lý.
#
# 2. MÃ YÊU CẦU. Cổng gửi tiêu đề `X-Request-ID` theo mỗi lần gọi dịch vụ (frontend/lib/api.ts); dịch
#    vụ nhận nếu hợp lệ, không thì tự sinh, đặt vào biến ngữ cảnh — mọi dòng nhật ký của lượt đó mang
#    nó, kể cả dòng ghi từ luồng `to_thread` (biến ngữ cảnh được sao sang luồng) — và trả lại trong
#    tiêu đề phản hồi. Mã từ ngoài chỉ nhận chữ, số, `-`, `_`, `.`, tối đa 64 ký tự: chặn chèn dòng giả
#    vào nhật ký.
#
# 3. SỐ ĐO. Bộ đếm trong bộ nhớ tiến trình: số yêu cầu theo phương thức, mẫu đường dẫn (không phải
#    đường dẫn thật — `/requests/{case_id}` chứ không phải `/requests/123`, để số chuỗi không phình),
#    mã trạng thái; tổng và phân bố độ trễ; số lỗi 5xx. Xuất ở `/metrics` dạng văn bản Prometheus
#    (main.py), kèm độ dài hàng đợi thư và lượt quét cuối đọc từ cơ sở dữ liệu lúc gọi. Mỗi bản dịch vụ
#    đếm riêng phần của nó.

from __future__ import annotations

import contextvars
import datetime as dt
import json
import logging
import re
import threading
import time
import uuid
from collections import defaultdict

from starlette.types import ASGIApp, Message, Receive, Scope, Send

TIEU_DE_MA_YEU_CAU = "x-request-id"
_MA_HOP_LE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

ma_yeu_cau: contextvars.ContextVar[str | None] = contextvars.ContextVar("ma_yeu_cau", default=None)

logger_truy_cap = logging.getLogger("app.access")


# --- 1. Nhật ký ----------------------------------------------------------------


class _GanMaYeuCau(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = ma_yeu_cau.get()
        return True


class DinhDangJson(logging.Formatter):
    """Một dòng JSON mỗi bản ghi. Trường thêm qua `extra={"fields": {...}}` được gộp vào."""

    def format(self, record: logging.LogRecord) -> str:
        dong = {
            "ts": dt.datetime.fromtimestamp(record.created, dt.UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        them = getattr(record, "fields", None)
        if isinstance(them, dict):
            dong.update(them)
        if record.exc_info:
            dong["exc"] = self.formatException(record.exc_info)
        return json.dumps(dong, ensure_ascii=False, default=str)


def cau_hinh_nhat_ky(dang: str = "json", muc: str = "INFO") -> None:
    """Gắn một bộ xử lý duy nhất cho gốc và cho các bộ ghi của uvicorn."""
    xu_ly = logging.StreamHandler()
    xu_ly.addFilter(_GanMaYeuCau())
    if dang == "json":
        xu_ly.setFormatter(DinhDangJson())
    else:
        xu_ly.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] [%(request_id)s] %(message)s")
        )
    goc = logging.getLogger()
    goc.handlers = [xu_ly]
    goc.setLevel(muc)
    # Uvicorn tự gắn bộ xử lý của nó trước khi nạp ứng dụng; gom về gốc để cùng định dạng
    for ten in ("uvicorn", "uvicorn.error"):
        bo_ghi = logging.getLogger(ten)
        bo_ghi.handlers = []
        bo_ghi.propagate = True
    # Dòng truy cập do LopQuanSat ghi. Uvicorn quyết có ghi dòng truy cập hay không bằng
    # `hasHandlers()` của bộ ghi này — để nó lan lên gốc là bật lại thứ `--no-access-log` đã tắt
    truy_cap = logging.getLogger("uvicorn.access")
    truy_cap.handlers = []
    truy_cap.propagate = False


# --- 3. Số đo -------------------------------------------------------------------

# Biên trên của các ô phân bố độ trễ, tính bằng giây
CAC_O_DO_TRE = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class BoDem:
    """Bộ đếm yêu cầu của một tiến trình. Khóa vì yêu cầu chạy song song trên nhiều luồng."""

    def __init__(self) -> None:
        self._khoa = threading.Lock()
        self.so_yeu_cau: dict[tuple[str, str, int], int] = defaultdict(int)
        self.tong_do_tre: dict[tuple[str, str], float] = defaultdict(float)
        self.dem_do_tre: dict[tuple[str, str], int] = defaultdict(int)
        self.o_do_tre: dict[tuple[str, str], list[int]] = {}
        self.so_loi = 0
        self.bat_dau = time.time()

    def ghi(self, phuong_thuc: str, mau: str, ma: int, giay: float) -> None:
        with self._khoa:
            self.so_yeu_cau[(phuong_thuc, mau, ma)] += 1
            k = (phuong_thuc, mau)
            self.tong_do_tre[k] += giay
            self.dem_do_tre[k] += 1
            o = self.o_do_tre.setdefault(k, [0] * len(CAC_O_DO_TRE))
            for i, bien in enumerate(CAC_O_DO_TRE):
                if giay <= bien:
                    o[i] += 1
            if ma >= 500:
                self.so_loi += 1

    def xuat(self) -> list[str]:
        """Các dòng văn bản Prometheus cho phần bộ đếm trong bộ nhớ."""
        with self._khoa:
            dong = [
                "# HELP dxlab_http_requests_total Số yêu cầu HTTP theo phương thức, mẫu đường dẫn, mã trạng thái.",
                "# TYPE dxlab_http_requests_total counter",
            ]
            for (pt, mau, ma), so in sorted(self.so_yeu_cau.items()):
                dong.append(
                    f'dxlab_http_requests_total{{method="{pt}",route="{_thoat(mau)}",status="{ma}"}} {so}'
                )
            dong += [
                "# HELP dxlab_http_request_duration_seconds Độ trễ xử lý yêu cầu HTTP.",
                "# TYPE dxlab_http_request_duration_seconds histogram",
            ]
            for (pt, mau), o in sorted(self.o_do_tre.items()):
                nhan = f'method="{pt}",route="{_thoat(mau)}"'
                for bien, so in zip(CAC_O_DO_TRE, o, strict=True):
                    dong.append(f'dxlab_http_request_duration_seconds_bucket{{{nhan},le="{bien}"}} {so}')
                dem = self.dem_do_tre[(pt, mau)]
                dong.append(f'dxlab_http_request_duration_seconds_bucket{{{nhan},le="+Inf"}} {dem}')
                dong.append(
                    f"dxlab_http_request_duration_seconds_sum{{{nhan}}} {self.tong_do_tre[(pt, mau)]:.6f}"
                )
                dong.append(f"dxlab_http_request_duration_seconds_count{{{nhan}}} {dem}")
            dong += [
                "# HELP dxlab_http_errors_total Số yêu cầu HTTP kết thúc bằng lỗi 5xx.",
                "# TYPE dxlab_http_errors_total counter",
                f"dxlab_http_errors_total {self.so_loi}",
                "# HELP dxlab_process_start_time_seconds Lúc tiến trình dịch vụ khởi động (Unix).",
                "# TYPE dxlab_process_start_time_seconds gauge",
                f"dxlab_process_start_time_seconds {self.bat_dau:.0f}",
            ]
            return dong


def _thoat(chu: str) -> str:
    return chu.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


bo_dem = BoDem()


# --- 2. Lớp giữa: mã yêu cầu, dòng truy cập, số đo ------------------------------


class LopQuanSat:
    """Lớp giữa ASGI thuần (không qua `BaseHTTPMiddleware`, để biến ngữ cảnh đi tới điểm cuối)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        tu_ngoai = next(
            (v.decode("latin-1") for k, v in scope.get("headers", []) if k == TIEU_DE_MA_YEU_CAU.encode()),
            None,
        )
        ma = tu_ngoai if tu_ngoai and _MA_HOP_LE.match(tu_ngoai) else uuid.uuid4().hex
        dau_moc = ma_yeu_cau.set(ma)
        bat_dau = time.perf_counter()
        ma_trang_thai = 500

        async def gui_kem_ma(thong_diep: Message) -> None:
            nonlocal ma_trang_thai
            if thong_diep["type"] == "http.response.start":
                ma_trang_thai = thong_diep["status"]
                thong_diep.setdefault("headers", [])
                thong_diep["headers"] = [*thong_diep["headers"], (b"x-request-id", ma.encode())]
            await send(thong_diep)

        try:
            await self.app(scope, receive, gui_kem_ma)
        finally:
            giay = time.perf_counter() - bat_dau
            tuyen = scope.get("route")
            mau = getattr(tuyen, "path", None) or "khong-khop"
            bo_dem.ghi(scope["method"], mau, ma_trang_thai, giay)
            # Điểm kiểm tra sức khỏe bị gọi mỗi vài giây: đếm, nhưng không ghi dòng truy cập
            if not scope["path"].startswith("/health"):
                logger_truy_cap.info(
                    "%s %s %d %.1fms",
                    scope["method"],
                    scope["path"],
                    ma_trang_thai,
                    giay * 1000,
                    extra={
                        "fields": {
                            "method": scope["method"],
                            "path": scope["path"],
                            "route": mau,
                            "status": ma_trang_thai,
                            "duration_ms": round(giay * 1000, 1),
                        }
                    },
                )
            ma_yeu_cau.reset(dau_moc)
