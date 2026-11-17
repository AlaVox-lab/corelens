# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấu hình quy trình sống được qua nâng cấp (#254).
#
# Ba nhóm bài:
#
#   1. Cụm dựng mới — chạy bản sửa gốc 0000 và hàm kiểm 0018 trong một lược đồ PostgreSQL tạm
#      ngay trong giao dịch của bài, rồi cho bộ nạp khởi tạo nạp `infra/seed/`. Cấu hình ra phải
#      y hệt cấu hình đang chạy ở lược đồ chính; lần khởi động sau không nạp lại.
#   2. Bộ quy tắc phiên bản mới — chép bộ đang bật, thêm một cạnh, kích hoạt: hồ sơ mới đi được cạnh
#      mới, hồ sơ cũ giữ bộ cũ. Không cần dựng lại cụm.
#   3. Bản cập nhật làm hỏng đồ thị quy trình bị từ chối và không để lại gì.
#
# Mọi thứ hoàn tác cùng giao dịch của bài, kể cả lược đồ tạm.
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.cau_hinh.bo_quy_tac import kich_hoat, sao_chep
from app.cau_hinh.khoi_tao import kiem_tra, nap_khoi_tao
from app.config import get_settings
from app.models.case import EventLog
from app.models.workflow_config import RequestType, RuleSet, Transition
from app.workflow.context import Actor
from app.workflow.engine import allowed_transitions, create_case, perform_transition

THU_MUC_SQL = Path(__file__).resolve().parent.parent / "alembic" / "sql"
LUOC_DO_TAM = "thu_254"
MA_CANH_MOI = "thu-canh-moi-254"


def _thu_muc_khoi_tao() -> Path:
    thu_muc = Path(get_settings().seed_dir)
    if not any(thu_muc.glob("*.sql")):
        pytest.skip(f"Không thấy dữ liệu khởi tạo ở {thu_muc} — bài chạy trong container dịch vụ.")
    return thu_muc


def _goc(session):
    """Kết nối psycopg bên dưới phiên, nằm trong giao dịch của bài."""
    return session.connection().connection.driver_connection


@pytest.fixture
def cum_moi(session):
    """Một lược đồ trống đi đúng đường của cụm dựng mới: bản sửa 0000 rồi hàm kiểm 0018, thay bằng
    bản 0025 (#255) như chuỗi Alembic."""
    goc = _goc(session)
    goc.execute(f"CREATE SCHEMA {LUOC_DO_TAM}")
    goc.execute(f"SET LOCAL search_path TO {LUOC_DO_TAM}")
    goc.execute((THU_MUC_SQL / "0000_luoc_do_cau_hinh.sql").read_text(encoding="utf-8"))
    goc.execute((THU_MUC_SQL / "0018_kiem_tra_cau_hinh.sql").read_text(encoding="utf-8"))
    goc.execute((THU_MUC_SQL / "0025_kiem_tra_cau_hinh.sql").read_text(encoding="utf-8"))
    # Bảng dữ liệu tạo ở bản sửa sau 0000 mà infra/seed/ cũng nạp — chữ ký tệp đính kèm (0023, #248),
    # loại thông báo (0024, #251), danh mục quy trình (0028, #376). Cụm thật chạy trọn Alembic trước bộ
    # nạp; ở đây chép cấu trúc từ lược đồ chính để bộ nạp chạy được mọi tệp như ở cụm thật
    for bang in ("attachment_file_types", "notification_types", "processes"):
        goc.execute(f"CREATE TABLE {bang} (LIKE public.{bang} INCLUDING ALL)")
    # Phần lược đồ cấu hình của 0028 (#376): bộ quy tắc và loại yêu cầu thuộc một quy trình, mỗi quy trình
    # một bộ đang bật, hàm kiểm thêm phép kiểm danh mục quy trình
    for bang in ("rule_sets", "request_types"):
        goc.execute(f"ALTER TABLE {bang} ADD COLUMN process_code TEXT NOT NULL REFERENCES processes (code)")
    goc.execute("DROP INDEX rule_sets_chi_mot_bo_kich_hoat")
    goc.execute("CREATE UNIQUE INDEX rule_sets_mot_bo_bat_moi_quy_trinh ON rule_sets (process_code) WHERE is_active")
    goc.execute((THU_MUC_SQL / "0028_kiem_tra_cau_hinh.sql").read_text(encoding="utf-8"))
    # Điều kiện trên cạnh (0032, #397): bảng mà tệp 07 của dữ liệu khởi tạo nạp
    goc.execute("CREATE TABLE transition_conditions (LIKE public.transition_conditions INCLUDING ALL)")
    return goc


# ---------------------------------------------------------------------------
# 1. Cụm dựng mới
# ---------------------------------------------------------------------------


def test_cum_moi_nap_khoi_tao_ra_dung_cau_hinh_dang_chay(cum_moi):
    da_nap = nap_khoi_tao(cum_moi, _thu_muc_khoi_tao())
    assert da_nap, "lược đồ trống thì bộ nạp phải nạp dữ liệu khởi tạo"
    kiem_tra(cum_moi)

    # Đáp án biết trước: cấu hình của cụm đang chạy, nạp từ cùng dữ liệu khởi tạo
    for bang, cot in (
        ("states", "rule_set_id, code, label, is_initial, is_terminal, sla_running"),
        (
            "transitions",
            "rule_set_id, from_state, to_state, activity_code, is_system, is_rework, primary_scope",
        ),
        ("roles", "code, label, report_scope"),
        ("departments", "code, label"),
        ("processes", "code, label, is_app_default"),
        ("rule_sets", "version, process_code, is_active"),
        ("request_types", "code, process_code, label, sla_hours"),
        ("work_hours", "calendar_code, iso_weekday, start_time, end_time"),
    ):
        lech = cum_moi.execute(
            f"(SELECT {cot} FROM {LUOC_DO_TAM}.{bang} EXCEPT SELECT {cot} FROM public.{bang}) "
            f"UNION ALL (SELECT {cot} FROM public.{bang} EXCEPT SELECT {cot} FROM {LUOC_DO_TAM}.{bang})"
        ).fetchall()
        assert lech == [], f"bảng {bang} của cụm mới lệch cụm đang chạy: {lech[:3]}"

    # Mọi bộ mà dữ liệu khởi tạo nạp (một bộ cho mỗi quy trình), so theo version — cụm đang chạy có thể còn
    # bộ cũ đã thay
    so_vai_tro_canh = cum_moi.execute(
        f"SELECT (SELECT count(*) FROM {LUOC_DO_TAM}.transition_roles), "
        "(SELECT count(*) FROM public.transition_roles tr JOIN public.transitions t "
        " ON t.id = tr.transition_id JOIN public.rule_sets r ON r.id = t.rule_set_id "
        f" WHERE r.version IN (SELECT version FROM {LUOC_DO_TAM}.rule_sets))"
    ).fetchone()
    assert so_vai_tro_canh[0] == so_vai_tro_canh[1] > 0


def test_khoi_dong_lan_sau_khong_nap_lai(cum_moi, tmp_path):
    nap_khoi_tao(cum_moi, _thu_muc_khoi_tao())
    # Thư mục mà nạp vào là hỏng ngay: không được đụng tới khi đã có cấu hình
    (tmp_path / "01-hong.sql").write_text("SELECT 1 / 0;", encoding="utf-8")
    assert nap_khoi_tao(cum_moi, tmp_path) == []
    kiem_tra(cum_moi)


def test_cum_dang_chay_khong_nap_lai(session, tmp_path):
    (tmp_path / "01-hong.sql").write_text("SELECT 1 / 0;", encoding="utf-8")
    assert nap_khoi_tao(_goc(session), tmp_path) == []


def test_cum_moi_thieu_du_lieu_khoi_tao_thi_bao_loi(cum_moi, tmp_path):
    with pytest.raises(RuntimeError, match="chưa có bộ quy tắc"):
        nap_khoi_tao(cum_moi, tmp_path)


def test_ham_kiem_cua_cum_moi_bat_ngo_cut(cum_moi):
    """Hàm kiểm dựng từ chính tệp SQL của bản sửa 0018, không phải bản đang nằm trong lược đồ chính."""
    nap_khoi_tao(cum_moi, _thu_muc_khoi_tao())
    cum_moi.execute(
        "DELETE FROM transitions WHERE from_state = "
        "(SELECT code FROM states WHERE is_initial AND rule_set_id = 1)"
    )
    with pytest.raises(Exception, match="không có cạnh nào đi ra"):
        kiem_tra(cum_moi)


def test_lenh_khoi_dong_dung_dich_vu_khi_cau_hinh_hong(monkeypatch):
    """`python -m app.cau_hinh.khoi_tao` trả mã lỗi khi phép kiểm hỏng, để điểm vào dừng khởi động.

    Chạy trên kết nối riêng tới cụm đang chạy: cụm đã có cấu hình nên lệnh không ghi gì."""
    import app.cau_hinh.khoi_tao as khoi_tao

    assert khoi_tao.main() == 0

    def hong(_ket_noi):
        raise RuntimeError("cấu hình hỏng giả")

    monkeypatch.setattr(khoi_tao, "kiem_tra", hong)
    assert khoi_tao.main() == 1


def test_cum_moi_chay_tep_khoi_tao_that(cum_moi, tmp_path):
    """Đối chứng của hai bài trên: lược đồ trống thì tệp trong thư mục được chạy thật."""
    (tmp_path / "01-hong.sql").write_text("\\set ON_ERROR_STOP on\nSELECT 1 / 0;", encoding="utf-8")
    with pytest.raises(Exception, match="division by zero"):
        nap_khoi_tao(cum_moi, tmp_path)


# ---------------------------------------------------------------------------
# 2. Bộ quy tắc phiên bản mới
# ---------------------------------------------------------------------------


def _so_dong(session, bang: str, bo: int) -> int:
    if bang in ("transition_roles", "transition_guards"):
        cau = (
            f"SELECT count(*) FROM {bang} x JOIN transitions t ON t.id = x.transition_id "
            "WHERE t.rule_set_id = :bo"
        )
    else:
        cau = f"SELECT count(*) FROM {bang} WHERE rule_set_id = :bo"
    return session.execute(text(cau), {"bo": bo}).scalar_one()


def test_sao_chep_chep_du_trang_thai_canh_vai_tro_rang_buoc(session, rule_set):
    moi = sao_chep(session, rule_set.id, "thu-254-chep", "Bộ chép thử #254")
    for bang in ("states", "transitions", "transition_roles", "transition_guards"):
        assert _so_dong(session, bang, moi) == _so_dong(session, bang, rule_set.id) > 0, bang
    # Cột cấu hình của cạnh đi theo nguyên vẹn, không chỉ cặp trạng thái
    lech = session.execute(
        text(
            "SELECT from_state, to_state, is_system, activity_code, is_rework, primary_scope, "
            "auto_after_hours, reopen_window_hours, accepts_attachments FROM transitions "
            "WHERE rule_set_id = :cu EXCEPT SELECT from_state, to_state, is_system, activity_code, "
            "is_rework, primary_scope, auto_after_hours, reopen_window_hours, accepts_attachments "
            "FROM transitions WHERE rule_set_id = :moi"
        ),
        {"cu": rule_set.id, "moi": moi},
    ).fetchall()
    assert lech == []
    assert session.get(RuleSet, moi).is_active is False


def _canh_moi_tu_diem_vao(session, bo: int) -> tuple[str, str, str]:
    """(trạng thái bắt đầu, đích, vai trò) cho một cạnh mới hợp lệ: đích chưa có cạnh nào nối từ
    điểm vào, không phải trạng thái kết thúc hay trạng thái chờ có đường quay về; vai trò lấy từ
    một cạnh có sẵn ở điểm vào."""
    hang = session.execute(
        text(
            "WITH dau AS (SELECT code FROM states WHERE rule_set_id = :bo AND is_initial) "
            "SELECT dau.code, s.code, "
            " (SELECT tr.role_code FROM transitions t JOIN transition_roles tr "
            "   ON tr.transition_id = t.id WHERE t.rule_set_id = :bo AND t.from_state = dau.code "
            "   AND tr.role_code <> 'requester' ORDER BY t.display_order LIMIT 1) "
            "FROM dau JOIN states s ON s.rule_set_id = :bo AND s.code <> dau.code "
            "WHERE NOT s.is_terminal "
            "AND NOT EXISTS (SELECT 1 FROM transitions t WHERE t.rule_set_id = :bo "
            "  AND t.from_state = dau.code AND t.to_state = s.code) "
            "AND NOT EXISTS (SELECT 1 FROM transitions t JOIN transition_guards g "
            "  ON g.transition_id = t.id WHERE t.rule_set_id = :bo AND t.from_state = s.code "
            "  AND g.guard_code = 'return-to-previous-state') "
            "ORDER BY s.display_order LIMIT 1"
        ),
        {"bo": bo},
    ).first()
    if hang is None or hang[2] is None:
        pytest.skip("Bộ quy tắc không còn chỗ cho một cạnh mới từ điểm vào để dựng bài.")
    return hang[0], hang[1], hang[2]


def _tao_ho_so(session):
    loai = session.scalars(
        select(RequestType.code).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    return create_case(
        session, title="Thử thêm cạnh bằng bộ quy tắc mới", requester_id="nguoi-gui-254",
        request_type_code=loai,
    )


def test_them_canh_bang_bo_quy_tac_moi_khong_can_dung_lai_cum(session, rule_set):
    cu = rule_set.id
    dau, dich, vai = _canh_moi_tu_diem_vao(session, cu)
    tac_nhan = Actor(id="nguoi-thu-254", roles=frozenset({vai}))
    ho_so_cu = _tao_ho_so(session)

    moi = sao_chep(session, cu, "thu-254-them-canh", "Bộ thêm cạnh thử #254")
    session.execute(
        text(
            "INSERT INTO transitions (rule_set_id, from_state, to_state, activity_code, "
            "activity_label, display_order) VALUES (:moi, :dau, :dich, :ma, 'Cạnh thử #254', 99)"
        ),
        {"moi": moi, "dau": dau, "dich": dich, "ma": MA_CANH_MOI},
    )
    session.execute(
        text(
            "INSERT INTO transition_roles (transition_id, role_code) SELECT id, :vai "
            "FROM transitions WHERE rule_set_id = :moi AND activity_code = :ma"
        ),
        {"vai": vai, "moi": moi, "ma": MA_CANH_MOI},
    )
    kich_hoat(session, moi)
    session.expire_all()

    assert session.scalars(select(RuleSet.id).where(RuleSet.is_active, RuleSet.process_code == rule_set.process_code)).one() == moi
    ho_so_moi = _tao_ho_so(session)
    assert ho_so_moi.rule_set_id == moi
    assert ho_so_cu.rule_set_id == cu

    assert dich in {c.to_state for c in allowed_transitions(session, ho_so_moi, tac_nhan)}
    assert MA_CANH_MOI not in {
        c.activity_code for c in allowed_transitions(session, ho_so_cu, tac_nhan)
    }

    perform_transition(session, case_id=ho_so_moi.id, to_state=dich, actor=tac_nhan)
    dong = session.scalars(
        select(EventLog).where(EventLog.case_id == ho_so_moi.id).order_by(EventLog.id.desc())
    ).first()
    assert (dong.activity, dong.to_state) == (MA_CANH_MOI, dich)


# ---------------------------------------------------------------------------
# 3. Bản cập nhật làm hỏng đồ thị bị từ chối
# ---------------------------------------------------------------------------


def test_cap_nhat_tao_ngo_cut_bi_tu_choi_va_khong_de_lai_gi(session, rule_set):
    cu = rule_set.id
    ngo_cut = session.scalars(
        select(Transition.from_state)
        .where(Transition.rule_set_id == cu, Transition.from_is_terminal.is_(False))
        .order_by(Transition.display_order.desc())
    ).first()

    with pytest.raises(DBAPIError, match="không có cạnh nào đi ra"):
        with session.begin_nested():
            moi = sao_chep(session, cu, "thu-254-hong", "Bộ hỏng thử #254")
            session.execute(
                text("DELETE FROM transitions WHERE rule_set_id = :moi AND from_state = :tu"),
                {"moi": moi, "tu": ngo_cut},
            )
            kich_hoat(session, moi)

    session.expire_all()
    assert session.scalars(select(RuleSet.id).where(RuleSet.is_active, RuleSet.process_code == rule_set.process_code)).one() == cu
    assert session.scalars(select(RuleSet).where(RuleSet.version == "thu-254-hong")).first() is None


def test_kich_hoat_bo_khong_ton_tai_bao_loi(session, rule_set):
    with pytest.raises(ValueError, match="Không có bộ quy tắc"):
        kich_hoat(session, 32000)
    session.expire_all()
    assert session.scalars(select(RuleSet.id).where(RuleSet.is_active, RuleSet.process_code == rule_set.process_code)).one() == rule_set.id
