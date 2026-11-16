# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Phiên bản bộ quy tắc (#254).
#
# Hồ sơ ghim `rule_set_id` lúc tạo và engine chỉ tra cạnh, trạng thái trong đúng bộ đó (#278). Vì
# vậy đổi quy trình KHÔNG sửa bộ đang chạy, mà:
#
#   1. sao_chep  — chép bộ đang bật thành một bộ mới chưa bật (trạng thái, cạnh, vai trò, ràng buộc)
#   2. sửa bộ mới bằng SQL thường — thêm cạnh, đổi nhãn, bật đồng hồ…
#   3. kich_hoat — gọi `kiem_tra_cau_hinh()`, đạt thì đổi bộ đang bật
#
# Chạy cả ba trong một bản sửa Alembic thì bản cập nhật làm hỏng đồ thị quy trình bị từ chối và
# hoàn tác cùng giao dịch; hồ sơ đang chạy đi tiếp theo bộ cũ, hồ sơ mới nhận bộ mới. Khuôn đầy đủ
# ở docs/ARCHITECTURE.md mục 5.
#
# Cột được chép tra từ information_schema lúc chạy, không liệt kê trong mã: thêm cột cấu hình mới
# vào trạng thái hay cạnh thì hàm vẫn chép đủ.

from __future__ import annotations

import json
from typing import Any, Protocol

from sqlalchemy import text


class ThucThi(Protocol):
    """Session hay Connection của SQLAlchemy — cả hai đều có `execute(text(...), tham_so)`, nên
    dùng được trong dịch vụ, trong bài kiểm thử và với `op.get_bind()` của Alembic."""

    def execute(self, statement: Any, params: Any = ...) -> Any: ...


def _cot_chep(ket_noi: ThucThi, bang: str) -> list[str]:
    """Cột tự ghi của bảng, trừ `rule_set_id` — bỏ cột định danh tự sinh và cột tính sẵn."""
    return list(
        ket_noi.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = :bang "
                "AND is_identity = 'NO' AND is_generated = 'NEVER' "
                "AND column_name <> 'rule_set_id' ORDER BY ordinal_position"
            ),
            {"bang": bang},
        ).scalars()
    )


def sao_chep(
    ket_noi: ThucThi,
    tu_bo: int,
    version: str,
    label: str,
    *,
    note: str | None = None,
    doi_ma_trang_thai: dict[str, str] | None = None,
) -> int:
    """Chép bộ quy tắc `tu_bo` thành một bộ mới CHƯA BẬT, trả mã bộ mới.

    `doi_ma_trang_thai` đổi mã trạng thái ngay trên đường chép (`{"mã cũ": "mã mới"}`) — khóa ngoại
    giữa cạnh và trạng thái không cho đổi mã sau khi đã chép."""
    doi = json.dumps(doi_ma_trang_thai or {})
    tham_so = {"tu": tu_bo, "doi": doi}

    def ma(cot: str) -> str:
        return f"COALESCE(CAST(:doi AS jsonb) ->> {cot}, {cot})"

    moi = ket_noi.execute(text("SELECT COALESCE(max(id), 0) + 1 FROM rule_sets")).scalar_one()
    tham_so["moi"] = moi
    # Bộ mới thuộc cùng quy trình với bộ được chép (#376)
    ket_noi.execute(
        text(
            "INSERT INTO rule_sets (id, process_code, version, label, effective_from, is_active, note) "
            "SELECT :moi, process_code, :version, :label, now(), FALSE, :note "
            "FROM rule_sets WHERE id = :tu"
        ),
        {"moi": moi, "tu": tu_bo, "version": version, "label": label, "note": note},
    )

    cot_trang_thai = _cot_chep(ket_noi, "states")
    chon = ", ".join(ma(c) if c == "code" else c for c in cot_trang_thai)
    ket_noi.execute(
        text(
            f"INSERT INTO states (rule_set_id, {', '.join(cot_trang_thai)}) "
            f"SELECT :moi, {chon} FROM states WHERE rule_set_id = :tu"
        ),
        tham_so,
    )

    cot_canh = _cot_chep(ket_noi, "transitions")
    chon = ", ".join(ma(c) if c in ("from_state", "to_state") else c for c in cot_canh)
    ket_noi.execute(
        text(
            f"INSERT INTO transitions (rule_set_id, {', '.join(cot_canh)}) "
            f"SELECT :moi, {chon} FROM transitions WHERE rule_set_id = :tu"
        ),
        tham_so,
    )

    # Cạnh mới có định danh mới: ghép với cạnh cũ theo khóa duy nhất của bảng
    # (bộ, từ, đến, cạnh hệ thống) — mỗi cặp trạng thái tối đa một cạnh người và một cạnh hệ thống
    ghep = (
        "FROM transitions c JOIN transitions m ON c.rule_set_id = :tu AND m.rule_set_id = :moi "
        f"AND m.from_state = {ma('c.from_state')} AND m.to_state = {ma('c.to_state')} "
        "AND m.is_system = c.is_system"
    )
    for bang, cot in (("transition_roles", "role_code"), ("transition_guards", "guard_code")):
        ket_noi.execute(
            text(
                f"INSERT INTO {bang} (transition_id, {cot}) "
                f"SELECT m.id, x.{cot} {ghep} JOIN {bang} x ON x.transition_id = c.id"
            ),
            tham_so,
        )
    return moi


def kich_hoat(ket_noi: ThucThi, ma_bo: int) -> None:
    """Kiểm nhất quán toàn bộ cấu hình rồi đổi bộ đang bật của quy trình chứa `ma_bo` sang `ma_bo`.

    Kiểm hỏng thì PostgreSQL ném lỗi trước khi có gì đổi, và giao dịch của người gọi hoàn tác cả
    phần đã chép, đã sửa. Hai câu UPDATE riêng: chỉ mục duy nhất từng phần không cho hai bộ của cùng
    một quy trình cùng bật, kể cả thoáng qua giữa một câu lệnh. Bộ đang bật của quy trình khác không
    bị đụng tới (#376)."""
    if ket_noi.execute(text("SELECT 1 FROM rule_sets WHERE id = :ma"), {"ma": ma_bo}).first() is None:
        raise ValueError(f"Không có bộ quy tắc mã {ma_bo}")
    ket_noi.execute(text("SELECT kiem_tra_cau_hinh()"))
    ket_noi.execute(
        text(
            "UPDATE rule_sets SET is_active = FALSE WHERE is_active AND id <> :ma "
            "AND process_code = (SELECT process_code FROM rule_sets WHERE id = :ma)"
        ),
        {"ma": ma_bo},
    )
    ket_noi.execute(
        text("UPDATE rule_sets SET is_active = TRUE, effective_from = now() WHERE id = :ma"),
        {"ma": ma_bo},
    )
