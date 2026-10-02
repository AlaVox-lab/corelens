# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hạ tầng chung cho bộ kiểm thử.
#
# Bộ kiểm thử cần một PostgreSQL THẬT đang chạy, không thay bằng SQLite được: lược đồ
# dùng chỉ mục duy nhất từng phần, khóa ngoại tổng hợp, kiểu TIMESTAMPTZ và trigger
# PL/pgSQL — SQLite không có thứ nào trong số đó. Mà chính những thứ đó mới là cái
# cần kiểm chứng.
#
# Cách chạy:
#
#     cd infra && docker compose --env-file .env up -d postgres
#     cd ../backend && pytest
#
# Mỗi bài kiểm thử chạy trong một giao dịch được hoàn tác ở cuối, nên cơ sở dữ liệu
# sạch nguyên sau khi chạy xong — kể cả khi bài kiểm thử thất bại giữa chừng.

from __future__ import annotations

import os
import urllib.error
import urllib.request

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.directory import KeycloakDirectory
from app.config import get_settings
from app.models.workflow_config import Department, RuleSet

DIA_CHI_MAC_DINH = "postgresql+psycopg://dxlab:doi_mat_khau_nay_truoc_khi_trien_khai@localhost:5432/dxlab"


@pytest.fixture(scope="session")
def db_engine():
    """Kết nối tới PostgreSQL đang chạy trong cụm phát triển."""
    dia_chi = os.environ.get("DXLAB_DATABASE_URI", DIA_CHI_MAC_DINH)
    engine = create_engine(dia_chi, pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            conn.execute(select(1))
    except Exception as loi:  # noqa: BLE001
        pytest.skip(
            f"Không kết nối được PostgreSQL ({loi}). "
            f"Dựng cụm bằng: cd infra && docker compose --env-file .env up -d postgres"
        )

    yield engine
    engine.dispose()


@pytest.fixture
def session(db_engine):
    """Một phiên làm việc được hoàn tác sạch sau mỗi bài kiểm thử.

    Phiên gắn vào một giao dịch bên ngoài rồi dùng điểm lưu bên trong, nên mã nghiệp
    vụ vẫn `flush` và `commit` bình thường mà không có gì thoát ra cơ sở dữ liệu thật.
    """
    ket_noi = db_engine.connect()
    giao_dich = ket_noi.begin()
    phien = Session(bind=ket_noi, join_transaction_mode="create_savepoint")

    try:
        yield phien
    finally:
        phien.close()
        giao_dich.rollback()
        ket_noi.close()


@pytest.fixture
def rule_set(session) -> RuleSet:
    """Bộ quy tắc đang kích hoạt, nạp từ infra/seed/."""
    bo = session.scalars(select(RuleSet).where(RuleSet.is_active)).one_or_none()
    if bo is None:
        pytest.skip(
            "Chưa có bộ quy tắc nào được kích hoạt. Dữ liệu khởi tạo chỉ nạp một "
            "lần lúc PostgreSQL tạo thực thể — dựng lại bằng: "
            "docker compose --env-file .env down -v && ... up -d"
        )
    return bo


@pytest.fixture
def phong_ban(session) -> str:
    """Mã một phòng ban bất kỳ đang hoạt động.

    Lấy từ dữ liệu thay vì viết cứng `"it"`, để bộ kiểm thử không vỡ khi doanh nghiệp
    triển khai khai lại cơ cấu tổ chức của họ.
    """
    ma = session.scalars(
        select(Department.code).where(Department.is_active).order_by(Department.display_order)
    ).first()
    if ma is None:
        pytest.skip("Chưa khai phòng ban nào trong dữ liệu khởi tạo.")
    return ma


@pytest.fixture
def danh_ba_that() -> KeycloakDirectory:
    """Danh bạ trỏ vào Keycloak thật của cụm, cho bài kiểm thử tích hợp (#84, #131).
    Không gọi được Keycloak thì bỏ qua bài, không đánh trượt."""
    cau_hinh = get_settings()
    goc = cau_hinh.keycloak_internal_url.rstrip("/")
    try:
        urllib.request.urlopen(f"{goc}/realms/{cau_hinh.keycloak_realm}", timeout=3).close()
    except (urllib.error.URLError, OSError):
        pytest.skip(
            "Không gọi được Keycloak. Dựng cụm bằng: "
            "cd infra && docker compose --env-file .env up -d keycloak"
        )
    return KeycloakDirectory(
        base_url=goc,
        realm=cau_hinh.keycloak_realm,
        client_id=cau_hinh.directory_client_id,
        client_secret=cau_hinh.directory_client_secret
        or os.environ.get("KEYCLOAK_DIRECTORY_SECRET", "doi_bi_mat_nay_truoc_khi_trien_khai"),
        department_prefix=cau_hinh.oidc_department_group_prefix,
        timeout_seconds=cau_hinh.directory_timeout_seconds,
        phone_attribute=cau_hinh.directory_phone_attribute,
    )
