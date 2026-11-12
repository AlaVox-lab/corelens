# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Kiểm thử tệp đính kèm trên hồ sơ (#80).
#
# Navigator chốt 26/10: tệp đi qua dịch vụ ứng dụng (người ngoài nhận 404); ai mở được hồ sơ
# thì xem được tệp; chỉ người gửi đính kèm, vào những lúc họ có cạnh mang cờ
# `accepts_attachments`; hồ sơ hủy vẫn giữ tệp; giới hạn nằm trong cấu hình.
#
# Phần tải lên và tải xuống chạy với SeaweedFS thật của cụm thử — hạ tầng này là thứ cần kiểm.
# Không gọi được kho thì bỏ qua các bài đó, không đánh trượt.

from __future__ import annotations

import io
import socket
import struct
import threading
import time
import zipfile
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

from app.auth.dependencies import current_actor
from app.config import Settings
from app.db import get_session
from app.main import app
from app.models.case import CaseAttachment
from app.models.workflow_config import Priority, RequestType, Transition
from app.storage import objects, quet_ma_doc
from app.workflow import attachments
from app.workflow.context import Actor
from app.workflow.engine import create_case, perform_transition

NGUOI_GUI = "nguoi-gui-80"
NGUOI_KHAC = "nguoi-khac-80"
DIEU_PHOI = Actor(id="dp-80", roles=frozenset({"classifier"}))

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"x" * 64


def _nguoi_gui(ma: str = NGUOI_GUI) -> Actor:
    return Actor(id=ma, name="Người gửi thử", roles=frozenset({"requester"}))


def _cau_hinh(**doi) -> Settings:
    return Settings(**doi)


# ---------------------------------------------------------------------------
# Kiểm từng tệp — không cần kho
# ---------------------------------------------------------------------------


def test_chinh_sach_doc_tu_cau_hinh(monkeypatch):
    monkeypatch.setattr(
        attachments,
        "get_settings",
        lambda: _cau_hinh(
            attachment_allowed_extensions=" PNG, .pdf ,,png ",
            attachment_max_mb=3,
            attachment_max_files=2,
            attachment_max_files_per_case=7,
        ),
    )
    cs = attachments.chinh_sach()
    assert cs.duoi_cho_phep == ("png", "pdf")  # chuẩn hóa, bỏ trùng, giữ thứ tự
    assert (cs.toi_da_mb, cs.toi_da_tep, cs.toi_da_tep_moi_ho_so) == (3, 2, 7)
    assert cs.toi_da_byte == 3 * 1024 * 1024


@pytest.fixture
def cs(session) -> attachments.ChinhSach:
    """Chính sách kèm bảng chữ ký `attachment_file_types` nạp từ infra/seed/04 (#248)."""
    chinh = attachments.chinh_sach(session)
    assert chinh.loai_tep, "attachment_file_types rỗng — dữ liệu khởi tạo 04 chưa nạp"
    return chinh


def test_tep_hop_le_tra_ten_sach_va_loai_noi_dung(cs):
    ten, loai, co_macro = attachments.kiem_tep("Ảnh màn hình.PNG", PNG, cs)
    assert ten == "Ảnh màn hình.PNG"
    assert loai == "image/png"
    assert co_macro is False
    assert attachments.kiem_tep("bao-gia.pdf", PDF, cs).loai == "application/pdf"
    assert attachments.kiem_tep("a.jpeg", JPG, cs).loai == "image/jpeg"
    assert attachments.kiem_tep("ghi-chu.txt", "xin chào".encode(), cs).loai == "text/plain"


@pytest.mark.parametrize("ten", ["chay.exe", "lenh.bat", "ma.js", "nen.zip", "khong-duoi", "an.PHP"])
def test_duoi_ngoai_danh_sach_bi_chan(ten, cs):
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments.kiem_tep(ten, PNG, cs)
    assert loi.value.code == "attachment-type-not-allowed"
    # Thông điệp nói rõ cái gì được nhận
    assert "png" in loi.value.message and "pdf" in loi.value.message


def test_doi_duoi_tep_chay_duoc_thanh_png_khong_qua(cs):
    """Đổi tên một tệp bất kỳ thành .png không đủ: nội dung phải đúng chữ ký ảnh."""
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments.kiem_tep("ngu-trang.png", b"MZ\x90\x00 chuong trinh chay duoc", cs)
    assert loi.value.code == "attachment-content-mismatch"
    with pytest.raises(attachments.TepBiTuChoi) as pdf:
        attachments.kiem_tep("gia.pdf", b"khong phai pdf", cs)
    # Thông báo rõ: nói thẳng đây không phải tệp .pdf thật (#248)
    assert "không phải tệp .pdf thật" in pdf.value.message
    with pytest.raises(attachments.TepBiTuChoi):
        attachments.kiem_tep("gia.docx", b"khong phai zip", cs)
    with pytest.raises(attachments.TepBiTuChoi):
        attachments.kiem_tep("nhi-phan.txt", b"abc\x00def", cs)


# ---------------------------------------------------------------------------
# Chữ ký từng đuôi, macro, quét mã độc — #248
# ---------------------------------------------------------------------------


def _goi_office(*ten_trong_goi: str) -> bytes:
    """Một gói ZIP kiểu Office Open XML, tạo trong bài — không lưu tệp mẫu nào vào kho."""
    bo_dem = io.BytesIO()
    with zipfile.ZipFile(bo_dem, "w") as goi:
        goi.writestr("[Content_Types].xml", "<Types/>")
        for ten in ten_trong_goi:
            goi.writestr(ten, b"\x00")
    return bo_dem.getvalue()


OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64
# Một mẫu hợp lệ cho mỗi dòng của infra/seed/04 — thêm dòng mới vào dữ liệu thì thêm mẫu ở đây
MAU_DUNG = {
    "png": PNG,
    "jpg": JPG,
    "jpeg": JPG,
    "gif": b"GIF89a" + b"\x00" * 16,
    "webp": b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 16,
    "pdf": PDF,
    "txt": b"van ban",
    "csv": b"a,b\n1,2\n",
    "doc": OLE,
    "xls": OLE,
    "ppt": OLE,
    "docx": _goi_office("word/document.xml"),
    "xlsx": _goi_office("xl/workbook.xml"),
    "pptx": _goi_office("ppt/presentation.xml"),
    "docm": _goi_office("word/document.xml", "word/vbaProject.bin"),
    "xlsm": _goi_office("xl/workbook.xml", "xl/vbaProject.bin"),
    "pptm": _goi_office("ppt/presentation.xml", "ppt/vbaProject.bin"),
}


def _cs_mo_het(cs: attachments.ChinhSach) -> attachments.ChinhSach:
    """Cùng bảng chữ ký, nhưng cho phép mọi đuôi bảng biết — để kiểm từng dòng dữ liệu."""
    return attachments.ChinhSach(
        tuple(cs.loai_tep), cs.toi_da_mb, cs.toi_da_tep, cs.toi_da_tep_moi_ho_so, cs.loai_tep
    )


def test_moi_dong_du_lieu_co_mau_kiem(cs):
    assert set(cs.loai_tep) == set(MAU_DUNG)


@pytest.mark.parametrize("duoi", sorted(MAU_DUNG))
def test_tung_duoi_nhan_dung_chu_ky_va_tu_choi_noi_dung_khac(cs, duoi):
    mo = _cs_mo_het(cs)
    kq = attachments.kiem_tep(f"tep.{duoi}", MAU_DUNG[duoi], mo)
    assert kq.loai == cs.loai_tep[duoi].loai_noi_dung
    # Nội dung chương trình chạy được mang đuôi này thì bị từ chối (văn bản thuần chỉ cấm byte 0)
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments.kiem_tep(f"tep.{duoi}", b"MZ\x90\x00\x03\x00", mo)
    assert loi.value.code == "attachment-content-mismatch"


def test_macro_duoc_nhan_nhung_gan_co(cs):
    mo = _cs_mo_het(cs)
    assert attachments.kiem_tep("a.docx", MAU_DUNG["docx"], mo).co_macro is False
    # .docx mà gói có vbaProject.bin — đổi đuôi .docm thành .docx không giấu được macro
    assert attachments.kiem_tep("a.docx", MAU_DUNG["docm"], mo).co_macro is True
    for duoi in ("docm", "xlsm", "pptm"):
        assert attachments.kiem_tep(f"a.{duoi}", MAU_DUNG[duoi], mo).co_macro is True
    assert attachments.kiem_tep("a.doc", OLE, mo).co_macro is False
    co_vba = OLE + "_VBA_PROJECT".encode("utf-16-le")
    assert attachments.kiem_tep("a.xls", co_vba, mo).co_macro is True


def test_goi_office_hong_bi_tu_choi(cs):
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments.kiem_tep("a.docx", b"PK\x03\x04 khong phai zip", _cs_mo_het(cs))
    assert loi.value.code == "attachment-content-mismatch"


def test_duoi_co_macro_chi_nhan_khi_nam_trong_danh_sach(cs):
    """Mặc định cụm không có .docm trong danh sách — bảng biết chữ ký không có nghĩa là được nhận."""
    assert "docm" not in cs.duoi_cho_phep
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments.kiem_tep("a.docm", MAU_DUNG["docm"], cs)
    assert loi.value.code == "attachment-type-not-allowed"


def test_duoi_chua_khai_chu_ky_chi_kiem_duoi(cs):
    rieng = attachments.ChinhSach(("dwg",), 10, 5, 20, cs.loai_tep)
    kq = attachments.kiem_tep("ban-ve.dwg", b"bat ky", rieng)
    assert kq.co_macro is False


# Chuỗi thử EICAR chuẩn (eicar.org) — ghép lúc chạy, không nằm nguyên vẹn trong kho để công cụ quét
# trên máy người đóng góp không báo nhầm tệp mã nguồn
EICAR = (
    "X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
).encode()


class _ClamdGia:
    """Máy chủ clamd giả: nghe một cổng cục bộ, trả lời INSTREAM và PING như clamd thật."""

    def __init__(self, tra_loi_im_lang: bool = False):
        self.im_lang = tra_loi_im_lang
        self.so_lan_quet = 0
        self.may_chu = socket.create_server(("127.0.0.1", 0))
        self.cong = self.may_chu.getsockname()[1]
        self.luong = threading.Thread(target=self._chay, daemon=True)
        self.luong.start()

    def _doc_du(self, ket_noi, n: int) -> bytes:
        du_lieu = b""
        while len(du_lieu) < n:
            phan = ket_noi.recv(n - len(du_lieu))
            if not phan:
                break
            du_lieu += phan
        return du_lieu

    def _chay(self):
        while True:
            try:
                ket_noi, _ = self.may_chu.accept()
            except OSError:
                return
            with ket_noi:
                lenh = b""
                while not lenh.endswith(b"\0"):
                    phan = ket_noi.recv(1)
                    if not phan:
                        break
                    lenh += phan
                if self.im_lang:
                    time.sleep(2)
                    continue
                if lenh == b"zPING\0":
                    ket_noi.sendall(b"PONG\0")
                    continue
                self.so_lan_quet += 1
                tep = b""
                while True:
                    (dai,) = struct.unpack(">I", self._doc_du(ket_noi, 4))
                    if dai == 0:
                        break
                    tep += self._doc_du(ket_noi, dai)
                if EICAR in tep:
                    ket_noi.sendall(b"stream: Eicar-Test-Signature FOUND\0")
                else:
                    ket_noi.sendall(b"stream: OK\0")

    def dong(self):
        self.may_chu.close()


@pytest.fixture
def clamd_gia(monkeypatch):
    gia = _ClamdGia()
    _bat_quet(monkeypatch, gia.cong)
    yield gia
    gia.dong()


def _bat_quet(monkeypatch, cong: int, **them):
    cau_hinh = _cau_hinh(clamav_host="127.0.0.1", clamav_port=cong, clamav_timeout_seconds=0.5, **them)
    monkeypatch.setattr(quet_ma_doc, "get_settings", lambda: cau_hinh)
    monkeypatch.setattr(attachments, "get_settings", lambda: cau_hinh)


def test_quet_tat_mac_dinh_khong_goi_gi():
    assert quet_ma_doc.quet(EICAR).trang_thai == quet_ma_doc.DA_TAT
    assert quet_ma_doc.tinh_trang() == {"status": "disabled"}


def test_clamd_gia_sach_nhiem_va_ping(clamd_gia):
    assert quet_ma_doc.quet(b"xin chao").trang_thai == quet_ma_doc.SACH
    kq = quet_ma_doc.quet(b"dau " + EICAR + b" cuoi")
    assert kq.trang_thai == quet_ma_doc.NHIEM and kq.chi_tiet == "Eicar-Test-Signature"
    # Tệp lớn hơn một khúc gửi vẫn tới nguyên vẹn
    assert quet_ma_doc.quet(b"x" * (quet_ma_doc.KHUC * 2 + 7) + EICAR).trang_thai == quet_ma_doc.NHIEM
    assert quet_ma_doc.tinh_trang()["status"] == "ready"


def test_clamd_khong_phan_hoi_thanh_khong_phan_hoi(monkeypatch):
    # Cổng không ai nghe
    tam = socket.create_server(("127.0.0.1", 0))
    cong = tam.getsockname()[1]
    tam.close()
    _bat_quet(monkeypatch, cong)
    assert quet_ma_doc.quet(b"x").trang_thai == quet_ma_doc.KHONG_PHAN_HOI
    assert quet_ma_doc.tinh_trang()["status"] == "unreachable"
    # Nghe mà không trả lời: hết hạn chót, không treo
    im = _ClamdGia(tra_loi_im_lang=True)
    try:
        _bat_quet(monkeypatch, im.cong)
        bat_dau = time.monotonic()
        assert quet_ma_doc.quet(b"x").trang_thai == quet_ma_doc.KHONG_PHAN_HOI
        assert time.monotonic() - bat_dau < 1.5
    finally:
        im.dong()


def test_eicar_bi_tu_choi_tep_sach_gan_clean(clamd_gia):
    assert attachments._quet("sach.txt", b"xin chao") == "clean"
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments._quet("eicar.txt", EICAR)
    assert loi.value.code == "attachment-infected"
    assert "Eicar-Test-Signature" in loi.value.message


def test_chinh_sach_khi_clamd_khong_phan_hoi(monkeypatch):
    tam = socket.create_server(("127.0.0.1", 0))
    cong = tam.getsockname()[1]
    tam.close()
    _bat_quet(monkeypatch, cong)
    assert attachments._quet("a.txt", b"x") == "unscanned"
    _bat_quet(monkeypatch, cong, clamav_on_unavailable="reject")
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments._quet("a.txt", b"x")
    assert loi.value.code == "attachment-scan-unavailable" and loi.value.http_status == 503


def test_tep_rong_va_qua_lon_bi_chan_kem_gioi_han(cs):
    with pytest.raises(attachments.TepBiTuChoi) as rong:
        attachments.kiem_tep("a.png", b"", cs)
    assert rong.value.code == "attachment-empty"

    cs = attachments.ChinhSach(("png",), toi_da_mb=1, toi_da_tep=5, toi_da_tep_moi_ho_so=20)
    qua_lon = PNG + b"\x00" * (1024 * 1024)
    with pytest.raises(attachments.TepBiTuChoi) as loi:
        attachments.kiem_tep("lon.png", qua_lon, cs)
    assert loi.value.code == "attachment-too-large" and loi.value.http_status == 413
    # Thông điệp nói rõ giới hạn là bao nhiêu (định nghĩa hoàn thành của issue)
    assert "1 MB" in loi.value.message
    # Đúng trần thì qua
    attachments.kiem_tep("vua.png", PNG + b"\x00" * (1024 * 1024 - len(PNG)), cs)


def test_ten_tep_duoc_lam_sach():
    assert attachments.lam_sach_ten("..\\..\\windows\\anh.png") == "anh.png"
    assert attachments.lam_sach_ten("../../etc/anh.png") == "anh.png"
    assert attachments.lam_sach_ten("a\x00b\nc.png") == "abc.png"
    dai = "x" * 500 + ".png"
    ten = attachments.lam_sach_ten(dai)
    assert len(ten) == attachments.TEN_TOI_DA and ten.endswith(".png")
    assert attachments.lam_sach_ten("   ") == ""
    with pytest.raises(attachments.TepBiTuChoi):
        attachments.kiem_tep("../", PNG, attachments.chinh_sach())


# ---------------------------------------------------------------------------
# Dữ liệu khai đúng
# ---------------------------------------------------------------------------


def test_chi_canh_cua_nguoi_gui_mang_co_dinh_kem(session, rule_set):
    canh = session.scalars(
        select(Transition).where(
            Transition.rule_set_id == rule_set.id, Transition.accepts_attachments
        )
    ).all()
    assert {(c.from_state, c.to_state, c.activity_code) for c in canh} == {
        ("submitted", "submitted", "edit-content"),
        ("classified", "submitted", "edit-content"),
        ("awaiting-info", "submitted", "provide-info"),
        ("awaiting-info", "awaiting-acceptance", "provide-info"),
        ("awaiting-info", "in-progress", "provide-info"),
    }
    for c in canh:
        assert c.role_codes == {"requester"} and not c.is_system
        assert "requester-owns-case" in c.guard_codes


# ---------------------------------------------------------------------------
# Tải lên và tải xuống qua điểm cuối — với kho thật
# ---------------------------------------------------------------------------


@pytest.fixture
def kho_that():
    """Kho SeaweedFS của cụm thử. Không gọi được thì bỏ qua bài, không đánh trượt."""
    try:
        objects.luu_tep("kiem-tra/ket-noi", b"x", "text/plain")
    except objects.KhoLoi as loi:
        pytest.skip(f"Không gọi được SeaweedFS: {loi}")


@contextmanager
def _may_khach(session, actor: Actor):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_actor] = lambda: actor
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _ho_so_moi(session, nguoi_gui: str = NGUOI_GUI):
    ho_so = create_case(session, title="Máy in kẹt giấy", requester_id=nguoi_gui)
    session.commit()
    return ho_so


def _phan_loai_den_phong(session, ho_so, phong_ban: str):
    loai = session.scalars(
        select(RequestType).where(RequestType.is_active).order_by(RequestType.display_order)
    ).first()
    uu_tien = session.scalars(select(Priority.code).where(Priority.is_default)).one()
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="classified",
        actor=DIEU_PHOI,
        changes={"priority_code": uu_tien, "request_type_code": loai.code},
    )
    perform_transition(
        session,
        case_id=ho_so.id,
        to_state="awaiting-acceptance",
        actor=DIEU_PHOI,
        changes={"department_code": phong_ban},
    )
    session.commit()


def _tai(c, case_id, *tep):
    return c.post(
        f"/requests/{case_id}/attachments",
        files=[("files", (ten, noi_dung, "application/octet-stream")) for ten, noi_dung in tep],
    )


def test_gui_kem_hai_tep_mo_lai_thay_du_va_tai_ve_duoc(session, kho_that):
    """Định nghĩa hoàn thành: gửi một yêu cầu kèm hai tệp, mở lại thấy đủ hai tệp, tải về được."""
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        r = _tai(c, ho_so.id, ("anh-man-hinh.png", PNG), ("bao-gia.pdf", PDF))
        assert r.status_code == 201, r.text
        assert [t["filename"] for t in r.json()] == ["anh-man-hinh.png", "bao-gia.pdf"]

        chi_tiet = c.get(f"/requests/{ho_so.id}").json()
        assert [(t["filename"], t["size_bytes"]) for t in chi_tiet["attachments"]] == [
            ("anh-man-hinh.png", len(PNG)),
            ("bao-gia.pdf", len(PDF)),
        ]
        assert chi_tiet["can_attach"] is True
        # Khóa trong kho không lộ ra ngoài
        assert "storage_key" not in str(chi_tiet["attachments"])

        for tep, goc, loai in zip(chi_tiet["attachments"], (PNG, PDF), ("image/png", "application/pdf")):
            tai = c.get(f"/attachments/{tep['id']}")
            assert tai.status_code == 200
            assert tai.content == goc
            assert tai.headers["content-type"].startswith(loai)
            # Luôn tải về, không để trình duyệt tự mở nội dung của người dùng
            assert tai.headers["content-disposition"].startswith("attachment;")
            assert tai.headers["x-content-type-options"] == "nosniff"


def test_nguoi_khong_phai_chu_ho_so_khong_tai_len_hay_tai_ve_duoc(session, kho_that):
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        ma_tep = _tai(c, ho_so.id, ("a.png", PNG)).json()[0]["id"]

    # Người gửi khác — kể cả mang đúng vai trò người gửi — nhận 404, không 403
    with _may_khach(session, _nguoi_gui(NGUOI_KHAC)) as c:
        r = _tai(c, ho_so.id, ("b.png", PNG))
        assert r.status_code == 404 and r.json()["detail"]["code"] == "case-not-found"
        r = c.get(f"/attachments/{ma_tep}")
        assert r.status_code == 404 and r.json()["detail"]["code"] == "attachment-not-found"
        # Tệp không tồn tại trả lời y hệt tệp của người khác — không lộ tệp có tồn tại
        assert c.get("/attachments/999999999").json() == r.json()
    assert session.scalars(select(CaseAttachment).where(CaseAttachment.case_id == ho_so.id)).all().__len__() == 1


def test_nhan_vien_xem_tep_theo_dung_luat_xem_ho_so(session, kho_that, phong_ban):
    from app.models.workflow_config import Department

    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        ma_tep = _tai(c, ho_so.id, ("a.png", PNG)).json()[0]["id"]
    _phan_loai_den_phong(session, ho_so, phong_ban)

    phong_khac = session.scalars(
        select(Department.code).where(Department.code != phong_ban, Department.is_active)
    ).first()
    cung_phong = Actor(id="xl-80", roles=frozenset({"handler"}), departments=frozenset({phong_ban}))
    khac_phong = Actor(id="xl-81", roles=frozenset({"handler"}), departments=frozenset({phong_khac}))
    nguoi_la = Actor(id="la-80", roles=frozenset(), departments=frozenset())

    for actor, mong_doi in (
        (DIEU_PHOI, 200),  # điều phối viên xem mọi hồ sơ
        (cung_phong, 200),  # phòng đang giữ hồ sơ
        (khac_phong, 404),  # phòng khác
        (nguoi_la, 404),  # người không có vai trò nào
    ):
        with _may_khach(session, actor) as c:
            assert c.get(f"/attachments/{ma_tep}").status_code == mong_doi, actor.id


def test_toi_phong_ban_thi_khoa_dinh_kem(session, kho_that, phong_ban):
    """Đính kèm khóa cùng lúc cạnh Sửa nội dung biến mất: hồ sơ tới phòng ban rồi thì thôi."""
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        assert c.get(f"/requests/{ho_so.id}").json()["can_attach"] is True
    _phan_loai_den_phong(session, ho_so, phong_ban)

    with _may_khach(session, _nguoi_gui()) as c:
        assert c.get(f"/requests/{ho_so.id}").json()["can_attach"] is False
        r = _tai(c, ho_so.id, ("a.png", PNG))
        assert r.status_code == 409 and r.json()["detail"]["code"] == "attachment-not-allowed"
    assert session.scalars(select(CaseAttachment).where(CaseAttachment.case_id == ho_so.id)).first() is None


def test_bo_sung_thong_tin_mo_lai_cho_dinh_kem(session, kho_that, phong_ban):
    """Đang Chờ bổ sung thông tin thì người gửi có cạnh Bổ sung — đính kèm được trở lại."""
    ho_so = _ho_so_moi(session)
    perform_transition(
        session, case_id=ho_so.id, to_state="awaiting-info", actor=DIEU_PHOI, note="Cho xem ảnh lỗi"
    )
    session.commit()
    with _may_khach(session, _nguoi_gui()) as c:
        assert c.get(f"/requests/{ho_so.id}").json()["can_attach"] is True
        assert _tai(c, ho_so.id, ("loi.png", PNG)).status_code == 201


def test_ho_so_huy_van_giu_tep(session, kho_that):
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        ma_tep = _tai(c, ho_so.id, ("a.png", PNG)).json()[0]["id"]
        r = c.post(f"/requests/{ho_so.id}/transitions", json={"to_state": "cancelled"})
        assert r.status_code == 200, r.text
        chi_tiet = c.get(f"/requests/{ho_so.id}").json()
        assert chi_tiet["state"]["is_terminal"] is True
        assert [t["id"] for t in chi_tiet["attachments"]] == [ma_tep]
        assert chi_tiet["can_attach"] is False
        assert c.get(f"/attachments/{ma_tep}").content == PNG


def test_mot_tep_hong_thi_ca_lo_bi_tu_choi(session, kho_that):
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        r = _tai(c, ho_so.id, ("tot.png", PNG), ("chay.exe", b"MZ"), ("tot2.pdf", PDF))
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "attachment-type-not-allowed"
        assert c.get(f"/requests/{ho_so.id}").json()["attachments"] == []


def test_tai_len_docx_co_macro_duoc_nhan_kem_co(session, kho_that):
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        r = _tai(c, ho_so.id, ("bang-tinh.docx", MAU_DUNG["docm"]), ("anh.png", PNG))
        assert r.status_code == 201, r.text
        tep = {t["filename"]: t for t in c.get(f"/requests/{ho_so.id}").json()["attachments"]}
        assert tep["bang-tinh.docx"]["has_macro"] is True
        assert tep["anh.png"]["has_macro"] is False
        # Quét tắt (mặc định): cột ghi đúng là chưa từng bật, không phải "sạch"
        assert {t["scan_status"] for t in tep.values()} == {"disabled"}


def test_tai_len_eicar_khi_quet_bat_bi_tu_choi_ca_lo(session, kho_that, clamd_gia):
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        r = _tai(c, ho_so.id, ("tot.txt", b"xin chao"), ("eicar.txt", EICAR))
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "attachment-infected"
        assert c.get(f"/requests/{ho_so.id}").json()["attachments"] == []
        r = _tai(c, ho_so.id, ("tot.txt", b"xin chao"))
        assert r.status_code == 201
        assert c.get(f"/requests/{ho_so.id}").json()["attachments"][0]["scan_status"] == "clean"


def test_vuot_gioi_han_kem_thong_diep_noi_ro(session, kho_that, monkeypatch):
    monkeypatch.setattr(
        attachments,
        "get_settings",
        lambda: _cau_hinh(attachment_max_mb=1, attachment_max_files=2, attachment_max_files_per_case=3),
    )
    ho_so = _ho_so_moi(session)
    to = PNG + b"\x00" * (1024 * 1024)
    with _may_khach(session, _nguoi_gui()) as c:
        r = _tai(c, ho_so.id, ("to.png", to))
        assert r.status_code == 413
        assert "tối đa 1 MB" in r.json()["detail"]["message"]

        r = _tai(c, ho_so.id, ("1.png", PNG), ("2.png", PNG), ("3.png", PNG))
        assert r.status_code == 422 and "tối đa 2 tệp" in r.json()["detail"]["message"]

        assert _tai(c, ho_so.id, ("1.png", PNG), ("2.png", PNG)).status_code == 201
        r = _tai(c, ho_so.id, ("3.png", PNG), ("4.png", PNG))
        assert r.status_code == 409 and r.json()["detail"]["code"] == "attachment-case-full"
        assert "tối đa 3 tệp" in r.json()["detail"]["message"]
        assert _tai(c, ho_so.id, ("3.png", PNG)).status_code == 201


def test_khong_chon_tep_nao_bi_tu_choi(session, kho_that):
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        r = c.post(f"/requests/{ho_so.id}/attachments")
        assert r.status_code == 422


def test_kho_tep_loi_thi_tra_502_va_khong_ghi_dong_nao(session, monkeypatch):
    def hong(*_a, **_k):
        raise objects.KhoLoi("Kho tệp không phản hồi.")

    monkeypatch.setattr(objects, "luu_tep", hong)
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        r = _tai(c, ho_so.id, ("a.png", PNG))
        assert r.status_code == 502 and r.json()["detail"]["code"] == "storage-unavailable"
        # Hồ sơ vẫn xem được: kho tắt chỉ làm phần đính kèm báo lỗi
        assert c.get(f"/requests/{ho_so.id}").status_code == 200
    assert (
        session.scalars(select(CaseAttachment).where(CaseAttachment.case_id == ho_so.id)).first()
        is None
    )


def test_endpoint_chinh_sach_cho_giao_dien(session):
    with _may_khach(session, _nguoi_gui()) as c:
        r = c.get("/attachments/policy")
    assert r.status_code == 200
    cs = r.json()
    assert "png" in cs["allowed_extensions"] and "exe" not in cs["allowed_extensions"]
    assert cs["max_mb"] >= 1 and cs["max_files"] >= 1 and cs["max_files_per_case"] >= cs["max_files"]


def test_tep_dinh_kem_chi_ghi_them(session):
    ho_so = _ho_so_moi(session)
    tep = CaseAttachment(
        case_id=ho_so.id,
        filename="a.png",
        content_type="image/png",
        size_bytes=1,
        storage_key="kiem-tra/khoa-chi-ghi-them",
        uploaded_by=NGUOI_GUI,
        uploaded_by_label="Người gửi",
    )
    session.add(tep)
    session.flush()

    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(update(CaseAttachment).where(CaseAttachment.id == tep.id).values(filename="b.png"))
    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(delete(CaseAttachment).where(CaseAttachment.id == tep.id))


def test_canh_he_thong_khong_bao_gio_mang_co_dinh_kem(session):
    """Cờ đính kèm chỉ có nghĩa với cạnh của người gửi; cạnh hệ thống không có người nào để đính kèm."""
    n = session.scalar(text("SELECT count(*) FROM transitions WHERE accepts_attachments AND is_system"))
    assert n == 0


def test_tep_mat_trong_kho_tra_404_chu_khong_500(session, kho_that):
    """Dòng siêu dữ liệu còn mà nội dung đã mất khỏi kho: người dùng nhận 404 như mọi tệp không có."""
    ho_so = _ho_so_moi(session)
    with _may_khach(session, _nguoi_gui()) as c:
        ma_tep = _tai(c, ho_so.id, ("a.png", PNG)).json()[0]["id"]
        khoa = session.scalar(select(CaseAttachment.storage_key).where(CaseAttachment.id == ma_tep))
        objects._khach().delete_object(Bucket=objects.get_settings().s3_bucket, Key=khoa)
        r = c.get(f"/attachments/{ma_tep}")
        assert r.status_code == 404 and r.json()["detail"]["code"] == "attachment-not-found"
