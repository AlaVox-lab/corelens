# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Khóa trùng lặp `Idempotency-Key` cho hai lệnh của nền tảng lõi (#426): tạo hồ sơ và đi một bước chuyển.
#
# Hệ thống tích hợp mất mạng giữa chừng không biết lệnh của nó đã chạy chưa, nên gửi lại. Không có khóa thì
# lần gửi lại chuyển trạng thái lần hai. Có khóa: lần đầu chạy lệnh và lưu kết quả; lần lặp cùng khóa, cùng
# lệnh nhận lại đúng kết quả đó kèm tiêu đề `Idempotent-Replayed: true` — không gọi engine, không thêm dòng
# nhật ký, không gửi webhook lần hai.
#
# Chỉ ở đường dưới `/core/v1`. Lệnh tạo hồ sơ dùng chung một hàm với cổng người dùng (router gắn hai lần,
# app/main.py), nên phụ thuộc ở đây tự xét đường thật của yêu cầu: đường của cổng có gửi tiêu đề này cũng bị
# bỏ qua, hành vi y như cũ. Không gửi tiêu đề thì cũng y như cũ.
#
# Luồng một lần gọi có khóa (bảng `idempotency_keys`, bản sửa 0037):
#
#   1. Giữ khóa trong giao dịch riêng, commit ngay: `INSERT … ON CONFLICT DO NOTHING` một dòng `in_progress`.
#      Đụng dòng sẵn có thì — hết hạn: xóa, làm như lần đầu; khác lệnh (`request_hash`): 422
#      `idempotency-key-reused`; đang chạy: 409 `idempotency-request-in-progress` kèm `Retry-After`; đang chạy
#      mà quá `locked_until` (lần trước chết giữa chừng): chiếm lại bằng UPDATE có điều kiện; đã xong: trả lại.
#   2. Chạy lệnh như cũ. Dòng khóa đổi sang `completed` + `case_id` TRONG CÙNG giao dịch với lần tạo hay lần
#      chuyển (móc `truoc_commit` của `di_buoc`). Nhờ vậy máy chết ngay sau commit thì khóa đã xong — lần lặp
#      trả lại chứ không chuyển hai lần; còn chết trước commit thì cả lệnh lẫn dấu xong cùng mất.
#   3. Sau commit ghi mã HTTP và thân phản hồi vào dòng, giao dịch riêng. Hỏng thì chỉ ghi nhật ký: lần lặp
#      dựng lại chi tiết hồ sơ `case_id` bằng đúng hàm dựng phản hồi của điểm cuối.
#   4. Lệnh thất bại ở bất kỳ đâu thì xóa dòng `in_progress` của chính lần này: chỉ kết quả thành công được
#      giữ, người tích hợp sửa lệnh rồi gửi lại cùng khóa được.
#
# Mỗi lần giữ khóa mang mốc `locked_until` của riêng nó, và mọi UPDATE/DELETE sau đó so mốc đó: lần chạy quá
# lâu bị lần khác chiếm khóa thì không đánh dấu xong được nữa — lệnh của nó hoàn tác, trả 409.

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import current_actor
from app.config import get_settings
from app.workflow.context import Actor

logger = logging.getLogger(__name__)

TIEU_DE_KHOA = "Idempotency-Key"
TIEU_DE_TRA_LAI = "Idempotent-Replayed"
DO_DAI_TOI_DA = 255

# Vòng đời kỹ thuật của một dòng khóa — không phải trạng thái nghiệp vụ, khớp ràng buộc CHECK của bản sửa 0037
DANG_CHAY = "in_progress"
DA_XONG = "completed"

# Đụng nhau liên tiếp (dòng vừa bị xóa, vừa bị chiếm) chừng này lần thì coi như đang có lần khác chạy
SO_LAN_THU = 5


@dataclass(frozen=True, slots=True)
class KhoaGoi:
    """Khóa của một lần gọi đã qua kiểm định dạng, kèm người gọi và điểm cuối mà nó thuộc về."""

    actor_id: str
    endpoint: str
    key: str
    # Mã HTTP của lần thành công ở điểm cuối này — dùng khi dựng lại phản hồi
    ma_thanh_cong: int


@dataclass(frozen=True, slots=True)
class _LanGiu:
    """Lần gọi này đang giữ dòng khóa `id`; `locked_until` là mốc riêng của lần giữ."""

    id: int
    locked_until: dt.datetime


@dataclass(frozen=True, slots=True)
class _DaXong:
    case_id: int | None
    response_status: int | None
    response_body: Any


def _loi(ma_http: int, code: str, message: str, headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(status_code=ma_http, detail={"code": code, "message": message}, headers=headers)


def _hop_le(khoa: str) -> bool:
    """1–255 ký tự ASCII in được (khoảng trắng tới dấu ngã)."""
    return 1 <= len(khoa) <= DO_DAI_TOI_DA and all(" " <= ky <= "~" for ky in khoa)


def _thuoc_loi(duong: str) -> bool:
    # Nhập muộn: app/main.py nhập mô-đun này qua router, còn tiền tố lõi là hằng của app/main.py
    from app.main import TIEN_TO_LOI

    return duong.startswith(TIEN_TO_LOI + "/")


def _mau_duong(request: Request) -> str:
    """Mẫu đường của điểm cuối, ví dụ `/core/v1/workflow/requests/{case_id}/transitions`.

    Tuyến đã khớp (`scope["route"]`) mang mẫu đường TƯƠNG ĐỐI với router của nó khi router được gắn nhiều lần
    (FastAPI đang ghim, 0.141, không chép tuyến lúc `include_router`), nên tiền tố gắn là phần đầu của đường thật
    mà phần còn lại khớp biểu thức của tuyến. Bản FastAPI chép tuyến thì mẫu đã đầy đủ, khớp ngay từ đầu."""
    duong = request.url.path
    tuyen = request.scope.get("route")
    mau, bieu_thuc = getattr(tuyen, "path", None), getattr(tuyen, "path_regex", None)
    if mau is None or bieu_thuc is None:
        return duong
    for vi_tri, ky in enumerate(duong):
        if ky == "/" and bieu_thuc.match(duong[vi_tri:]):
            return duong[:vi_tri] + mau
    return duong


def khoa_trung_lap(
    request: Request,
    actor: Annotated[Actor, Depends(current_actor)],
    idempotency_key: Annotated[str | None, Header(alias=TIEU_DE_KHOA, include_in_schema=False)] = None,
) -> KhoaGoi | None:
    """Phụ thuộc FastAPI: khóa của lần gọi, hoặc `None` nếu không gửi tiêu đề hay đường không thuộc lõi.

    Chỉ kiểm định dạng, không ghi gì: phụ thuộc chạy cả khi thân yêu cầu sai (FastAPI gom lỗi thân sau), nên
    giữ khóa ở đây sẽ để lại dòng của một lần gọi chưa bao giờ chạy. Việc giữ khóa nằm trong `chay_mot_lan`.
    Đường của lõi xét trên đường thật của yêu cầu, vì cùng một tuyến phục vụ cả hai nơi. Tiêu đề trong đặc tả
    OpenAPI chỉ khai ở đường của lõi (`them_vao_dac_ta`, gọi từ app/main.py).
    """
    if idempotency_key is None or not _thuoc_loi(request.url.path):
        return None
    tuyen = request.scope.get("route")
    duong = _mau_duong(request)
    if not _hop_le(idempotency_key):
        raise _loi(
            422,
            "idempotency-key-invalid",
            f"Tiêu đề {TIEU_DE_KHOA} phải dài 1–{DO_DAI_TOI_DA} ký tự ASCII in được.",
        )
    return KhoaGoi(
        actor_id=actor.id,
        endpoint=f"{request.method} {duong}",
        key=idempotency_key,
        ma_thanh_cong=getattr(tuyen, "status_code", None) or 200,
    )


def bam_lenh(than: BaseModel, tham_so_duong: dict[str, Any]) -> str:
    """sha256 của lệnh: thân yêu cầu sau khi kiểm, dạng JSON chuẩn hóa (khóa xếp thứ tự, không khoảng trắng),
    cộng tham số đường. Thứ tự khóa hay khoảng trắng khác nhau vẫn là cùng một lệnh; khác hồ sơ là khác lệnh."""
    chuan = json.dumps(
        {"body": than.model_dump(mode="json"), "path": tham_so_duong},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(chuan.encode("utf-8")).hexdigest()


def _giu_khoa(session: Session, khoa: KhoaGoi, bam: str) -> _LanGiu | _DaXong:
    """Bước 1 của luồng (đầu tệp). Mỗi nhánh ghi xong là commit: dòng khóa phải thấy được từ lần gọi song song
    ngay, không đợi lệnh chạy xong."""
    cau_hinh = get_settings()
    tham_so = {
        "a": khoa.actor_id, "e": khoa.endpoint, "k": khoa.key, "h": bam,
        "giu": cau_hinh.idempotency_lock_seconds, "song": cau_hinh.idempotency_ttl_hours * 3600,
    }
    for _ in range(SO_LAN_THU):
        moi = session.execute(
            text(
                """
                INSERT INTO idempotency_keys (actor, endpoint, key, request_hash, status, locked_until, expires_at)
                VALUES (:a, :e, :k, :h, 'in_progress',
                        clock_timestamp() + make_interval(secs => :giu),
                        clock_timestamp() + make_interval(secs => :song))
                ON CONFLICT (actor, endpoint, key) DO NOTHING
                RETURNING id, locked_until
                """
            ),
            tham_so,
        ).one_or_none()
        if moi is not None:
            session.commit()
            return _LanGiu(id=moi.id, locked_until=moi.locked_until)

        co = session.execute(
            text(
                """
                SELECT id, request_hash, status, case_id, response_status, response_body, locked_until,
                       expires_at <= clock_timestamp() AS het_han,
                       locked_until > clock_timestamp() AS con_giu,
                       ceil(extract(epoch FROM locked_until - clock_timestamp()))::int AS con_lai
                FROM idempotency_keys
                WHERE actor = :a AND endpoint = :e AND key = :k
                """
            ),
            tham_so,
        ).one_or_none()
        if co is None:
            continue  # lần khác vừa xóa dòng: thử chèn lại
        if co.het_han:
            session.execute(
                text("DELETE FROM idempotency_keys WHERE id = :id AND expires_at <= clock_timestamp()"),
                {"id": co.id},
            )
            session.commit()
            continue
        if co.request_hash != bam:
            session.commit()
            raise _loi(
                422,
                "idempotency-key-reused",
                f"{TIEU_DE_KHOA} này đã dùng cho một lệnh khác. Mỗi lệnh cần một khóa riêng.",
            )
        if co.status == DA_XONG:
            session.commit()
            return _DaXong(case_id=co.case_id, response_status=co.response_status, response_body=co.response_body)
        if co.con_giu:
            session.commit()
            con_lai = max(1, co.con_lai)
            raise _loi(
                409,
                "idempotency-request-in-progress",
                f"Một lần gọi cùng {TIEU_DE_KHOA} đang chạy. Thử lại sau {con_lai} giây.",
                headers={"Retry-After": str(con_lai)},
            )
        # Lần trước chết giữa chừng, khóa đã quá hạn giữ: chiếm lại. So mốc cũ để hai lần cùng tới không cùng chiếm
        chiem = session.execute(
            text(
                """
                UPDATE idempotency_keys
                SET locked_until = clock_timestamp() + make_interval(secs => :giu),
                    expires_at = clock_timestamp() + make_interval(secs => :song)
                WHERE id = :id AND status = 'in_progress' AND locked_until = :cu
                RETURNING id, locked_until
                """
            ),
            {**tham_so, "id": co.id, "cu": co.locked_until},
        ).one_or_none()
        session.commit()
        if chiem is not None:
            return _LanGiu(id=chiem.id, locked_until=chiem.locked_until)
    raise _loi(
        409,
        "idempotency-request-in-progress",
        f"Một lần gọi cùng {TIEU_DE_KHOA} đang chạy. Thử lại sau giây lát.",
        headers={"Retry-After": "1"},
    )


def _danh_dau_xong(session: Session, lan: _LanGiu, case_id: int) -> None:
    """Bước 2: chạy trong giao dịch của lệnh, trước commit. Không còn giữ khóa (lần khác đã chiếm) thì từ chối —
    lệnh hoàn tác, lần đang giữ khóa mới là lần chạy."""
    da_doi = session.execute(
        text(
            "UPDATE idempotency_keys SET status = 'completed', case_id = :c"
            " WHERE id = :id AND status = 'in_progress' AND locked_until = :l"
        ),
        {"c": case_id, "id": lan.id, "l": lan.locked_until},
    ).rowcount
    if da_doi != 1:
        raise _loi(
            409,
            "idempotency-request-in-progress",
            f"Lần gọi này chạy quá lâu, một lần gọi khác cùng {TIEU_DE_KHOA} đã nhận việc. Gửi lại để nhận kết quả.",
            headers={"Retry-After": "1"},
        )


def _ghi_ket_qua(session: Session, lan: _LanGiu, ma_http: int, than: Any) -> None:
    """Bước 3: giao dịch riêng sau commit. Hỏng thì lần lặp dựng lại phản hồi từ `case_id`."""
    try:
        session.execute(
            text(
                "UPDATE idempotency_keys SET response_status = :s, response_body = CAST(:b AS jsonb)"
                " WHERE id = :id AND status = 'completed'"
            ),
            {"s": ma_http, "b": json.dumps(than, ensure_ascii=False), "id": lan.id},
        )
        session.commit()
    except Exception:  # noqa: BLE001 — lệnh đã commit; lần lặp vẫn có đường dựng lại
        session.rollback()
        logger.exception("Không ghi được phản hồi vào khóa trùng lặp %s", lan.id)


def _bo_khoa(session: Session, lan: _LanGiu) -> None:
    """Bước 4: xóa dòng `in_progress` của chính lần này. Dòng đã xong hay đã bị chiếm thì không đụng."""
    try:
        session.execute(
            text(
                "DELETE FROM idempotency_keys"
                " WHERE id = :id AND status = 'in_progress' AND locked_until = :l"
            ),
            {"id": lan.id, "l": lan.locked_until},
        )
        session.commit()
    except Exception:  # noqa: BLE001 — lỗi gốc của lệnh mới là lỗi trả cho người gọi
        session.rollback()
        logger.exception("Không bỏ được khóa trùng lặp %s sau lần gọi hỏng", lan.id)


def _tra_lai(ma_http: int, than: Any) -> JSONResponse:
    return JSONResponse(status_code=ma_http, content=than, headers={TIEU_DE_TRA_LAI: "true"})


def chay_mot_lan(
    session: Session,
    khoa: KhoaGoi | None,
    *,
    than: BaseModel,
    tham_so_duong: dict[str, Any],
    lam: Callable[[Callable[[int], None]], BaseModel],
    dung_lai: Callable[[int], BaseModel],
) -> BaseModel | JSONResponse:
    """Chạy lệnh `lam` đúng một lần cho mỗi khóa.

    `lam(danh_dau)` là thân điểm cuối: nó phải gọi `danh_dau(case_id)` ngay trước commit của lệnh, trong cùng
    giao dịch, và trả mô hình phản hồi. `dung_lai(case_id)` dựng phản hồi của điểm cuối cho hồ sơ đó, trong
    phạm vi người gọi — chỉ dùng khi lần đầu commit được mà không ghi được thân phản hồi. Không có khóa thì
    chỉ gọi `lam`, y như trước #426.
    """
    if khoa is None:
        return lam(lambda case_id: None)

    giu = _giu_khoa(session, khoa, bam_lenh(than, tham_so_duong))
    if isinstance(giu, _DaXong):
        if giu.response_body is not None:
            return _tra_lai(giu.response_status or khoa.ma_thanh_cong, giu.response_body)
        return _tra_lai(khoa.ma_thanh_cong, dung_lai(giu.case_id).model_dump(mode="json"))

    try:
        ket_qua = lam(lambda case_id: _danh_dau_xong(session, giu, case_id))
    except BaseException:
        session.rollback()
        _bo_khoa(session, giu)
        raise
    _ghi_ket_qua(session, giu, khoa.ma_thanh_cong, ket_qua.model_dump(mode="json"))
    return ket_qua


def don_khoa_het_han(session: Session) -> int:
    """Xóa các dòng khóa đã quá `expires_at`. Trả số dòng đã xóa; người gọi commit.

    Gọi từ vòng của bộ quét nền, cạnh việc dọn bộ đếm giới hạn tốc độ. Nhiều bản dịch vụ cùng dọn vô hại."""
    return session.execute(text("DELETE FROM idempotency_keys WHERE expires_at <= clock_timestamp()")).rowcount


def them_vao_dac_ta(thao_tac: dict[str, Any]) -> None:
    """Thêm vào một thao tác OpenAPI của lệnh lõi có khóa trùng lặp: tiêu đề vào, tiêu đề ra, phản hồi 409.

    Gọi từ app/main.py trên đúng thao tác dưới `/core/v1`, không phải thao tác của cổng người dùng dùng chung hàm
    — nên không khai bằng `openapi_extra` của tuyến (tuyến dùng chung cho cả hai đường). Chỉ thêm khóa, không
    đổi tham số hay phản hồi sẵn có."""
    # Dựng danh sách và từ điển mới thay vì sửa tại chỗ: hai thao tác sinh từ cùng một tuyến có thể dùng chung
    # đối tượng con, sửa tại chỗ là thao tác của cổng người dùng đổi theo.
    phan_hoi = dict(thao_tac["responses"])
    ma_thanh_cong = next(ma for ma in phan_hoi if ma.startswith("2"))
    phan_them = _phan_dac_ta(ma_thanh_cong)
    thao_tac["parameters"] = [*thao_tac.get("parameters", []), *phan_them["parameters"]]
    thanh_cong = dict(phan_hoi[ma_thanh_cong])
    thanh_cong["headers"] = {**thanh_cong.get("headers", {}), **phan_them["responses"][ma_thanh_cong]["headers"]}
    phan_hoi[ma_thanh_cong] = thanh_cong
    phan_hoi.setdefault("409", phan_them["responses"]["409"])
    thao_tac["responses"] = phan_hoi


def _phan_dac_ta(ma_thanh_cong: str) -> dict[str, Any]:
    return {
        "parameters": [
            {
                "name": TIEU_DE_KHOA,
                "in": "header",
                "required": False,
                "description": (
                    "Khóa trùng lặp, tùy chọn (#426): 1–255 ký tự ASCII in được, mỗi lệnh một khóa (ví dụ một "
                    "UUID). Gọi lặp cùng khóa, cùng lệnh trong `IDEMPOTENCY_TTL_HOURS` giờ thì nhận lại đúng "
                    f"phản hồi lần đầu kèm `{TIEU_DE_TRA_LAI}: true`, lệnh không chạy lần hai. Khóa tính theo "
                    "người gọi. Chỉ lần thành công được giữ: lần bị từ chối thì sửa rồi gửi lại cùng khóa được. "
                    "Khóa sai định dạng: 422 `idempotency-key-invalid`; cùng khóa mà khác thân hay khác hồ sơ: "
                    "422 `idempotency-key-reused`."
                ),
                "schema": {"type": "string", "minLength": 1, "maxLength": DO_DAI_TOI_DA},
            }
        ],
        "responses": {
            ma_thanh_cong: {
                "headers": {
                    TIEU_DE_TRA_LAI: {
                        "description": "Có mặt (giá trị `true`) khi phản hồi là kết quả đã lưu của lần gọi "
                        f"trước cùng {TIEU_DE_KHOA}, không phải lần chạy mới.",
                        "schema": {"type": "string", "enum": ["true"]},
                    }
                }
            },
            "409": {
                "description": (
                    f"Với {TIEU_DE_KHOA}: một lần gọi cùng khóa đang chạy (`idempotency-request-in-progress`, "
                    "kèm `Retry-After`) — thử lại sau. Điểm cuối còn có thể trả 409 vì lý do riêng của nó (ở "
                    "bước chuyển: cạnh không đi được từ trạng thái hiện tại); phân biệt bằng `detail.code`."
                ),
            },
        },
    }
