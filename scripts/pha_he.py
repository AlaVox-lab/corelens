# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Phả hệ dữ liệu của bảng điều khiển và báo cáo (#379) — nguyên lý (iii) của đề: mỗi con số trên báo cáo
# tổng hợp chỉ ra được nó đến từ đâu.
#
# Kịch bản ĐỌC TĨNH chính kho mã, không cần cụm đang chạy, không cần gói nào ngoài thư viện chuẩn — để
# việc nhẹ nhất của tích hợp liên tục (việc header) chạy được:
#
#   1. Định nghĩa view: chạy `upgrade()` của mọi bản sửa Alembic có chữ `VIEW`, theo đúng chuỗi
#      `down_revision`, với mô-đun GIẢ thay cho alembic/sqlalchemy/psycopg/app — chỉ ghi lại các câu
#      `CREATE [OR REPLACE] VIEW` / `DROP VIEW` gửi qua `op.execute` (hay `get_bind().execute`). Định nghĩa
#      cuối của mỗi view là định nghĩa mà cụm đang chạy có sau `alembic upgrade head`. Câu SQL được đọc
#      bằng biểu thức chính quy (FROM/JOIN, bí danh, `bí_danh.cột`), không cần trình phân tích SQL.
#   2. Bảng điều khiển: YAML trong `infra/superset/bang-dieu-khien/` (dashboard → biểu đồ → bộ dữ liệu),
#      đọc bằng bộ đọc YAML tối giản ở dưới — đủ cho dạng Superset xuất ra.
#   3. Nơi khác đọc nhật ký sự kiện (khai phá, xuất dữ liệu, lưu trữ lạnh): câu SQL trong mã của chúng.
#
# Sinh `docs/pha-he-du-lieu.md` và trang tương ứng của trang tài liệu. `--kiem` không ghi gì: sinh trong bộ
# nhớ rồi so với hai tệp đang có, lệch thì thoát mã 1 — đổi một view hay một biểu đồ mà quên sinh lại
# trang là tích hợp liên tục đỏ.
#
#   python scripts/pha_he.py          # sinh lại hai tệp
#   python scripts/pha_he.py --kiem   # chỉ kiểm, cho tích hợp liên tục

from __future__ import annotations

import argparse
import ast
import difflib
import importlib.abc
import importlib.machinery
import json
import re
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC_BAN_SUA = GOC / "backend" / "alembic" / "versions"
THU_MUC_SUPERSET = GOC / "infra" / "superset" / "bang-dieu-khien"
TEP_TAI_LIEU = GOC / "docs" / "pha-he-du-lieu.md"
TEP_TRANG = GOC / "docs-site" / "src" / "content" / "docs" / "tham-khao" / "pha-he-du-lieu.md"

# Nơi đọc nhật ký sự kiện ngoài bảng điều khiển: nhãn, tệp mã chứa câu SQL
NOI_DOC_KHAC: tuple[tuple[str, str], ...] = (
    ("Xuất nhật ký — `GET /core/v1/events`", "backend/app/analytics/xuat_du_lieu.py"),
    ("Khai phá quy trình — dịch vụ `khai-pha`, màn Quy trình thực tế", "services/khai-pha/app/du_lieu.py"),
    ("Lưu trữ lạnh — `GET /core/v1/archive`", "backend/app/analytics/luu_tru_lanh.py"),
)

# Từ khóa SQL có thể đứng ngay sau FROM/JOIN hay ở chỗ bí danh — không phải tên bảng
TU_KHOA = {
    "select", "lateral", "on", "where", "join", "left", "right", "inner", "outer", "full", "cross", "group",
    "order", "union", "all", "using", "limit", "offset", "having", "window", "as", "and", "or", "not", "with",
    "natural", "unnest", "values", "only",
}

GIA_TRI_GIA = ("alembic", "sqlalchemy", "psycopg", "app")


# ---------------------------------------------------------------------------
# 1. Định nghĩa view từ các bản sửa Alembic
# ---------------------------------------------------------------------------


class _Gia:
    """Đối tượng giả: thuộc tính, lời gọi, chỉ số đều trả về một đối tượng giả; luôn sai khi xét đúng sai, lặp
    thì rỗng. Nhờ vậy các nhánh "cụm cũ" và các bước chạm cơ sở dữ liệu thật trong `upgrade()` tự bỏ qua."""

    def __getattr__(self, ten: str) -> _Gia:
        if ten.startswith("__"):
            raise AttributeError(ten)
        return _Gia()

    def __call__(self, *a, **k) -> _Gia:
        return _Gia()

    def __getitem__(self, k) -> _Gia:
        return _Gia()

    def __iter__(self):
        return iter(())

    def __bool__(self) -> bool:
        return False

    def __enter__(self) -> _Gia:
        return self

    def __exit__(self, *a) -> bool:
        return False

    def __str__(self) -> str:
        return ""


class _GhiLenh(_Gia):
    """Thay `alembic.op` và kết nối của nó: ghi lại mọi chuỗi SQL được gửi đi."""

    def __init__(self) -> None:
        self.cau: list[str] = []

    def execute(self, cau, *a, **k) -> _Gia:
        if isinstance(cau, str):
            self.cau.append(cau)
        return _Gia()

    def get_bind(self) -> _GhiLenh:
        return self


class _MoDunGia(types.ModuleType):
    def __getattr__(self, ten: str):
        if ten.startswith("__"):
            raise AttributeError(ten)
        if ten == "text":  # sqlalchemy.text(chuỗi) — giữ nguyên chuỗi để bộ ghi đọc được
            return lambda cau, *a, **k: cau
        return _Gia()


class _TimMoDunGia(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, ten, path, target=None):
        if ten.split(".")[0] in GIA_TRI_GIA:
            return importlib.machinery.ModuleSpec(ten, self, is_package=True)
        return None

    def create_module(self, spec):
        mo_dun = _MoDunGia(spec.name)
        mo_dun.__path__ = []
        return mo_dun

    def exec_module(self, mo_dun) -> None:
        return None


class LoiDoc(Exception):
    """Không đọc được một định nghĩa — báo rõ tệp nào, không sinh trang sai."""


def _gia_tri_cap_dau(nguon: str, ten: str) -> str | None:
    """Giá trị chuỗi của phép gán cấp đầu `ten = "..."` hoặc `ten: kiểu = "..."`."""
    for nut in ast.parse(nguon).body:
        dich = None
        if isinstance(nut, ast.AnnAssign) and isinstance(nut.target, ast.Name):
            dich, gia_tri = nut.target.id, nut.value
        elif isinstance(nut, ast.Assign) and len(nut.targets) == 1 and isinstance(nut.targets[0], ast.Name):
            dich, gia_tri = nut.targets[0].id, nut.value
        if dich == ten:
            return gia_tri.value if isinstance(gia_tri, ast.Constant) else None
    return None


def _chuoi_ban_sua() -> list[tuple[str, Path]]:
    """Các bản sửa theo chuỗi `down_revision`, từ gốc tới đầu."""
    theo_truoc: dict[str | None, tuple[str, Path]] = {}
    for tep in sorted(THU_MUC_BAN_SUA.glob("*.py")):
        nguon = tep.read_text(encoding="utf-8")
        ma = _gia_tri_cap_dau(nguon, "revision")
        if ma is None:
            continue
        truoc = _gia_tri_cap_dau(nguon, "down_revision")
        if truoc in theo_truoc:
            raise LoiDoc(f"Hai bản sửa cùng nối sau {truoc!r}: {theo_truoc[truoc][1].name}, {tep.name}")
        theo_truoc[truoc] = (ma, tep)
    chuoi, hien_tai = [], None
    while hien_tai in theo_truoc:
        ma, tep = theo_truoc.pop(hien_tai)
        chuoi.append((ma, tep))
        hien_tai = ma
    if theo_truoc:
        raise LoiDoc("Bản sửa không nối vào chuỗi: " + ", ".join(t.name for _, t in theo_truoc.values()))
    return chuoi


def _chay_upgrade(tep: Path) -> list[str]:
    """Chạy `upgrade()` của một bản sửa với mô-đun giả, trả về các câu SQL nó gửi đi."""
    ghi = _GhiLenh()
    sys.modules["alembic"].op = ghi
    ten_mo_dun = "ban_sua_" + re.sub(r"\W", "_", tep.stem)
    khong_gian = {"__file__": str(tep), "__name__": ten_mo_dun}
    try:
        exec(compile(tep.read_text(encoding="utf-8"), str(tep), "exec"), khong_gian)
    except Exception as loi:  # noqa: BLE001
        raise LoiDoc(f"{tep.name}: không nạp được mô-đun ({type(loi).__name__}: {loi})") from loi

    # Hàm phụ của bản sửa (sắp lại chỉ mục, chạy tệp dữ liệu, cấp quyền) chạm cơ sở dữ liệu thật: lỗi của
    # chúng trên mô-đun giả thì bỏ qua. Hàm dựng câu view (`_view`) vẫn trả kết quả như thường.
    def _boc(ham):
        def _ham_boc(*a, **k):
            try:
                return ham(*a, **k)
            except Exception:  # noqa: BLE001
                return None

        return _ham_boc

    for ten, gia_tri in list(khong_gian.items()):
        if (
            isinstance(gia_tri, types.FunctionType)
            and gia_tri.__module__ == ten_mo_dun
            and ten not in ("upgrade", "downgrade")
        ):
            khong_gian[ten] = _boc(gia_tri)
    try:
        khong_gian["upgrade"]()
    except Exception as loi:  # noqa: BLE001
        raise LoiDoc(f"{tep.name}: upgrade() hỏng trên mô-đun giả ({type(loi).__name__}: {loi})") from loi
    return ghi.cau


@dataclass
class View:
    ten: str
    sql: str
    ban_sua: str  # tệp bản sửa chứa định nghĩa cuối


def doc_view() -> dict[str, View]:
    """Định nghĩa cuối của mọi view sau `alembic upgrade head`."""
    tim = _TimMoDunGia()
    cu = {k: v for k, v in sys.modules.items() if k.split(".")[0] in GIA_TRI_GIA}
    for k in cu:
        del sys.modules[k]
    sys.meta_path.insert(0, tim)
    try:
        import alembic  # noqa: F401 — mô-đun giả, để `_chay_upgrade` gắn `op`

        view: dict[str, View] = {}
        for _, tep in _chuoi_ban_sua():
            if "VIEW" not in tep.read_text(encoding="utf-8"):
                continue
            for cau in _chay_upgrade(tep):
                tao = re.match(r"\s*CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)\s+AS\s+(.*)\Z", cau, re.S | re.I)
                if tao:
                    view[tao.group(1).lower()] = View(tao.group(1).lower(), tao.group(2), tep.name)
                    continue
                xoa = re.match(r"\s*DROP\s+VIEW\s+(?:IF\s+EXISTS\s+)?(.+?)\s*(?:CASCADE|RESTRICT)?\s*;?\s*\Z", cau, re.S | re.I)
                if xoa:
                    for ten in xoa.group(1).split(","):
                        view.pop(ten.strip().lower(), None)
        return view
    finally:
        sys.meta_path.remove(tim)
        for k in [k for k in sys.modules if k.split(".")[0] in GIA_TRI_GIA]:
            del sys.modules[k]
        sys.modules.update(cu)


# ---------------------------------------------------------------------------
# Đọc câu SQL
# ---------------------------------------------------------------------------


def _lam_sach(sql: str) -> str:
    """Bỏ chú thích `--`, thay chuỗi trong nháy đơn bằng `''` — chữ trong chuỗi không bị đọc nhầm là tên."""
    return re.sub(r"'(?:[^']|'')*'|--[^\n]*", lambda m: "''" if m.group().startswith("'") else "", sql)


@dataclass
class DocSql:
    nguon: list[str]  # quan hệ đọc trực tiếp (bảng hay view), không gồm CTE
    cot: dict[str, set[str]]  # quan hệ → cột tham chiếu qua bí danh
    cot_ra: list[str] = field(default_factory=list)


def doc_sql(sql: str) -> DocSql:
    s = _lam_sach(sql)
    cte = {t.lower() for t in re.findall(r"(?:\bWITH|,)\s*([a-z_]\w*)\s+AS\s*\(", s, re.I)}
    bi_danh: dict[str, str] = {}
    nguon: list[str] = []
    for m in re.finditer(r"\b(?:FROM|JOIN)\s+(?:LATERAL\s+)?([a-z_]\w*)\b(?!\s*[.(])", s, re.I):
        ten = m.group(1).lower()
        if ten in TU_KHOA:
            continue
        bi_danh[ten] = ten
        sau = re.match(r"\s+(?:AS\s+)?([a-z_]\w*)", s[m.end():], re.I)
        if sau and sau.group(1).lower() not in TU_KHOA:
            bi_danh[sau.group(1).lower()] = ten
        if ten not in cte and ten not in nguon:
            nguon.append(ten)
    cot: dict[str, set[str]] = {t: set() for t in nguon}
    for m in re.finditer(r"\b([a-z_]\w*)\.([a-z_]\w*)\b", s, re.I):
        quan_he = bi_danh.get(m.group(1).lower())
        if quan_he in cot:
            cot[quan_he].add(m.group(2).lower())
    return DocSql(nguon=nguon, cot=cot, cot_ra=_cot_ra(s))


def _cot_ra(s: str) -> list[str]:
    """Tên cột của SELECT chính (nhánh đầu nếu có UNION): bí danh `AS x`, hoặc `bí_danh.x`, hoặc `x`."""
    sau = 0
    while True:
        m = re.compile(r"\bSELECT\b", re.I).search(s, sau)
        if not m:
            return []
        if s[: m.start()].count("(") == s[: m.start()].count(")"):
            break
        sau = m.end()
    muc: list[str] = []
    sau_select = sau = m.end()
    tang = 0
    for i in range(sau_select, len(s)):
        c = s[i]
        if c == "(":
            tang += 1
        elif c == ")":
            tang -= 1
        elif tang == 0 and c == ",":
            muc.append(s[sau:i])
            sau = i + 1
        elif tang == 0 and re.match(r"\bFROM\b", s[i : i + 5], re.I) and not re.match(r"\w", s[i - 1]):
            muc.append(s[sau:i])
            break
    ket_qua = []
    for m in muc:
        m = m.strip()
        ten = re.search(r"\bAS\s+([a-z_]\w*)\s*\Z", m, re.I) or re.search(r"(?:\.|^)([a-z_]\w*)\s*\Z", m, re.I)
        if ten:
            ket_qua.append(ten.group(1).lower())
    return ket_qua


# ---------------------------------------------------------------------------
# 2. Bảng điều khiển Superset (YAML tối giản)
# ---------------------------------------------------------------------------


def _vo_huong(chu: str):
    if chu in ("null", "~"):
        return None
    if chu in ("true", "false"):
        return chu == "true"
    if chu == "[]":
        return []
    if chu == "{}":
        return {}
    if chu.startswith("'") and chu.endswith("'") and len(chu) >= 2:
        return chu[1:-1].replace("''", "'")
    if chu.startswith('"') and chu.endswith('"') and len(chu) >= 2:
        return json.loads(chu)
    if re.fullmatch(r"-?\d+", chu):
        return int(chu)
    if re.fullmatch(r"-?\d+\.\d+", chu):
        return float(chu)
    return chu


def _la_cap(chu: str) -> bool:
    return re.match(r"[A-Za-z_][\w-]*:(?: |$)", chu) is not None


def _khoi(dong: list[list], i: int, thut: int):
    if dong[i][1] == "-" or dong[i][1].startswith("- "):
        ds = []
        while i < len(dong) and dong[i][0] == thut and (dong[i][1] == "-" or dong[i][1].startswith("- ")):
            noi = dong[i][1][1:].strip()
            if not noi:
                i += 1
                gia_tri, i = _khoi(dong, i, dong[i][0])
            elif _la_cap(noi):
                dong[i] = [thut + 2, noi]
                gia_tri, i = _khoi(dong, i, thut + 2)
            else:
                gia_tri, i = _vo_huong(noi), i + 1
            ds.append(gia_tri)
        return ds, i
    tu: dict = {}
    while i < len(dong) and dong[i][0] == thut and not dong[i][1].startswith("- "):
        khoa, _, phan = dong[i][1].partition(":")
        phan = phan.strip()
        i += 1
        if phan:
            # Chuỗi dài bị xuống dòng: dòng tiếp thụt sâu hơn và không phải khối con
            while i < len(dong) and dong[i][0] > thut:
                phan += " " + dong[i][1]
                i += 1
            tu[khoa] = _vo_huong(phan)
        elif i < len(dong) and (dong[i][0] > thut or (dong[i][0] == thut and dong[i][1].startswith("- "))):
            tu[khoa], i = _khoi(dong, i, dong[i][0])
        else:
            tu[khoa] = None
    return tu, i


def doc_yaml(tep: Path):
    dong = []
    for d in tep.read_text(encoding="utf-8").splitlines():
        if not d.strip() or d.lstrip().startswith("#"):
            continue
        dong.append([len(d) - len(d.lstrip()), d.strip()])
    return _khoi(dong, 0, dong[0][0])[0] if dong else {}


@dataclass
class BoDuLieu:
    uuid: str
    bang: str
    sql: str | None
    cot: dict[str, str | None]  # tên cột → biểu thức (cột tính) hoặc None
    tep: str


@dataclass
class BieuDo:
    ten: str
    uuid: str
    bo_du_lieu: str
    chuoi: list[str]  # mọi chuỗi trong params — để tìm cột được dùng
    tep: str


def _moi_chuoi(gia_tri) -> list[str]:
    if isinstance(gia_tri, str):
        return [gia_tri]
    if isinstance(gia_tri, dict):
        return [c for v in gia_tri.values() for c in _moi_chuoi(v)]
    if isinstance(gia_tri, list):
        return [c for v in gia_tri for c in _moi_chuoi(v)]
    return []


def doc_bang_dieu_khien() -> tuple[list[dict], dict[str, BoDuLieu], dict[str, BieuDo]]:
    bo: dict[str, BoDuLieu] = {}
    for tep in sorted((THU_MUC_SUPERSET / "datasets").rglob("*.yaml")):
        y = doc_yaml(tep)
        bo[y["uuid"]] = BoDuLieu(
            uuid=y["uuid"],
            bang=y["table_name"],
            sql=y.get("sql"),
            cot={c["column_name"]: c.get("expression") for c in (y.get("columns") or [])},
            tep=tep.relative_to(GOC).as_posix(),
        )
    bieu_do: dict[str, BieuDo] = {}
    for tep in sorted((THU_MUC_SUPERSET / "charts").glob("*.yaml")):
        y = doc_yaml(tep)
        bieu_do[y["uuid"]] = BieuDo(
            ten=y["slice_name"],
            uuid=y["uuid"],
            bo_du_lieu=y["dataset_uuid"],
            chuoi=_moi_chuoi(y.get("params")),
            tep=tep.relative_to(GOC).as_posix(),
        )
    bang: list[dict] = []
    for tep in sorted((THU_MUC_SUPERSET / "dashboards").glob("*.yaml")):
        y = doc_yaml(tep)
        vi_tri = y.get("position") or {}
        thu_tu: list[str] = []

        # Hàm gọi ngay trong cùng vòng lặp nên đọc đúng `vi_tri`, `thu_tu` của vòng đó
        def _duyet(ma: str) -> None:
            nut = vi_tri.get(ma) or {}  # noqa: B023
            if nut.get("type") == "CHART":
                thu_tu.append(nut["meta"]["uuid"])  # noqa: B023
            for con in nut.get("children") or []:
                _duyet(con)

        _duyet("ROOT_ID")
        bang.append({"ten": y["dashboard_title"], "slug": y.get("slug"), "bieu_do": thu_tu})
    return bang, bo, bieu_do


def cot_dung(bd: BieuDo, bo: BoDuLieu) -> list[str]:
    """Cột của bộ dữ liệu mà biểu đồ dùng; cột tính được thay bằng các cột vật lý trong biểu thức của nó."""
    tu = {t.lower() for c in bd.chuoi for t in re.findall(r"[A-Za-z_]\w*", c)}
    ket_qua: set[str] = set()
    for ten, bieu_thuc in bo.cot.items():
        if ten.lower() not in tu:
            continue
        if bieu_thuc:
            ket_qua |= {t for t in re.findall(r"[a-z_]\w*", _lam_sach(bieu_thuc).lower()) if t in bo.cot and not bo.cot[t]}
        else:
            ket_qua.add(ten)
    return sorted(ket_qua)


# ---------------------------------------------------------------------------
# 3. Nơi khác đọc nhật ký: câu SQL trong mã
# ---------------------------------------------------------------------------


def _chuoi_sql_trong(tep: Path) -> list[str]:
    cac = []
    for nut in ast.walk(ast.parse(tep.read_text(encoding="utf-8"))):
        if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            chu = nut.value
        elif isinstance(nut, ast.JoinedStr):
            chu = " x ".join(v.value for v in nut.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
        else:
            continue
        if re.search(r"\bSELECT\b", chu) and re.search(r"\bFROM\b", chu):
            cac.append(chu)
    return cac


def nguon_cua_tep(duong: str) -> list[str] | None:
    tep = GOC / duong
    if not tep.exists():
        return None
    ten: list[str] = []
    for cau in _chuoi_sql_trong(tep):
        for t in doc_sql(cau).nguon:
            if t not in ten:
                ten.append(t)
    return sorted(ten)


# ---------------------------------------------------------------------------
# Dựng trang
# ---------------------------------------------------------------------------


def _bang_goc(ten: str, view: dict[str, View], doc: dict[str, DocSql], da_tham: set[str] | None = None) -> set[str]:
    """Bảng nguồn (không phải view) mà một view rốt cuộc đọc."""
    da_tham = da_tham if da_tham is not None else set()
    if ten not in view or ten in da_tham:
        return {ten} if ten not in view else set()
    da_tham.add(ten)
    ket_qua: set[str] = set()
    for n in doc[ten].nguon:
        ket_qua |= _bang_goc(n, view, doc, da_tham)
    return ket_qua


def _view_trung_gian(ten: str, view: dict[str, View], doc: dict[str, DocSql]) -> list[str]:
    ket_qua: list[str] = []
    hang = [n for n in doc[ten].nguon if n in view] if ten in view else []
    while hang:
        n = hang.pop(0)
        if n not in ket_qua:
            ket_qua.append(n)
            hang += [m for m in doc[n].nguon if m in view]
    return ket_qua


def _cot_bang_qua(ten: str, view: dict[str, View], doc: dict[str, DocSql]) -> dict[str, set[str]]:
    """Bảng nguồn → cột được tham chiếu, gộp trên mọi view trên đường đi."""
    ket_qua: dict[str, set[str]] = {}
    for v in [ten, *_view_trung_gian(ten, view, doc)]:
        if v not in doc:
            continue
        for bang, cot in doc[v].cot.items():
            if bang not in view:
                ket_qua.setdefault(bang, set()).update(cot)
    return ket_qua


def _o(cac: list[str] | set[str]) -> str:
    return ", ".join(f"`{c}`" for c in sorted(cac)) if cac else "—"


def _bang_cot(cot: dict[str, set[str]]) -> str:
    return "<br>".join(f"`{b}` ({', '.join(sorted(c)) or '—'})" for b, c in sorted(cot.items())) or "—"


def _ma(ten: str) -> str:
    return re.sub(r"\W", "_", ten)


def dung_trang(cho_trang_tai_lieu: bool) -> str:
    view = doc_view()
    doc = {t: doc_sql(v.sql) for t, v in view.items()}
    bang, bo, bieu_do = doc_bang_dieu_khien()

    thu_tu = [u for b in bang for u in b["bieu_do"]]
    thu_tu += sorted((u for u in bieu_do if u not in thu_tu), key=lambda u: bieu_do[u].ten)

    d: list[str] = []
    w = d.append
    w("<!-- Tệp SINH TỰ ĐỘNG bởi scripts/pha_he.py từ định nghĩa view (backend/alembic/versions/) và bảng điều")
    w("     khiển (infra/superset/bang-dieu-khien/). Đừng sửa tay: sửa định nghĩa rồi chạy python scripts/pha_he.py.")
    w("     Tích hợp liên tục chạy --kiem và báo đỏ khi trang này lệch với định nghĩa. -->")
    w("")
    if not cho_trang_tai_lieu:
        w("# Phả hệ dữ liệu")
        w("")
    w("Nguyên lý (iii) của đề thi: kiểm soát phả hệ, nguồn gốc và chất lượng thông tin trên báo cáo tổng hợp.")
    w("Trang này trả lời câu hỏi *con số trên biểu đồ này lấy từ đâu*: biểu đồ → bộ dữ liệu → view báo cáo →")
    w("bảng nguồn, cùng các cột được dùng ở mỗi chặng. Mọi dòng dưới đây sinh từ chính định nghĩa trong kho —")
    w("định nghĩa view cuối cùng sau mọi bản sửa Alembic, và tệp YAML của bảng điều khiển Superset.")
    w("")

    # 1. Biểu đồ
    w("## Biểu đồ → bộ dữ liệu → view → bảng nguồn")
    w("")
    for b in bang:
        w(f"Bảng điều khiển **{b['ten']}** (`{b['slug']}`), {len(b['bieu_do'])} biểu đồ, theo thứ tự trên lưới.")
    w("")
    w("| Biểu đồ | Bộ dữ liệu · cột dùng | View đọc qua | Bảng nguồn |")
    w("|---|---|---|---|")
    for u in thu_tu:
        bd = bieu_do[u]
        bdl = bo.get(bd.bo_du_lieu)
        if bdl is None:
            raise LoiDoc(f"{bd.tep}: bộ dữ liệu {bd.bo_du_lieu} không có trong infra/superset/bang-dieu-khien/datasets")
        if bdl.sql:
            nguon_bo = doc_sql(bdl.sql).nguon
        else:
            nguon_bo = [bdl.bang.lower()]
        trung_gian: list[str] = []
        cot_goc: dict[str, set[str]] = {}
        for n in nguon_bo:
            if n in view:
                for v in [n, *_view_trung_gian(n, view, doc)]:
                    if v not in trung_gian:
                        trung_gian.append(v)
                for k, c in _cot_bang_qua(n, view, doc).items():
                    cot_goc.setdefault(k, set()).update(c)
            else:
                cot_goc.setdefault(n, set())
        w(
            f"| {bd.ten} | `{bdl.bang}` · {_o(cot_dung(bd, bdl))} | {' → '.join(f'`{v}`' for v in trung_gian) or '—'} "
            f"| {_o(cot_goc)} |"
        )
    w("")
    w("*Cột dùng* là cột của bộ dữ liệu xuất hiện trong trục, nhóm, chỉ số hay bộ lọc của biểu đồ; cột tính của")
    w("bộ dữ liệu được thay bằng các cột vật lý trong biểu thức của nó. *Bảng nguồn* gộp mọi bảng mà các view")
    w("trên đường đi đọc; cột của từng bảng ở mục *View báo cáo*.")
    w("")

    # 2. Sơ đồ
    w("## Sơ đồ")
    w("")
    if cho_trang_tai_lieu:
        w("Sơ đồ mermaid của cùng phả hệ nằm trong bản ở kho mã: `docs/pha-he-du-lieu.md` (GitHub vẽ sơ đồ trực")
        w("tiếp khi xem tệp).")
    else:
        w("```mermaid")
        w("flowchart LR")
        canh: list[str] = []
        nut_bang: set[str] = set()

        def _noi(tu: str, n: str) -> None:
            if n in view:
                c = f"  {tu} --> v_{_ma(n)}"
            else:
                nut_bang.add(n)
                c = f"  {tu} --> t_{_ma(n)}"
            if c not in canh:
                canh.append(c)

        for i, u in enumerate(thu_tu, 1):
            bd = bieu_do[u]
            ten = bd.ten.replace('"', "'")
            w(f'  bd{i}["{ten}"]')
            bdl = bo[bd.bo_du_lieu]
            for n in doc_sql(bdl.sql).nguon if bdl.sql else [bdl.bang.lower()]:
                _noi(f"bd{i}", n)
        for t in sorted(view):
            w(f'  v_{_ma(t)}[("{t}")]')
            for n in doc[t].nguon:
                _noi(f"v_{_ma(t)}", n)
        for t in sorted(nut_bang):
            w(f'  t_{_ma(t)}[["{t}"]]')
        for c in canh:
            w(c)
        w("```")
        w("")
        w("Hình chữ nhật là biểu đồ, hình trụ là view báo cáo, hình có viền đôi là bảng nguồn.")
    w("")

    # 3. View
    w("## View báo cáo")
    w("")
    w("Mỗi view một dòng: bản sửa Alembic chứa định nghĩa đang có hiệu lực, quan hệ đọc trực tiếp, bảng nguồn")
    w("rốt cuộc kèm các cột được tham chiếu qua bí danh trong câu SQL (gộp qua mọi view trung gian), và các cột")
    w("view trả ra.")
    w("")
    w("| View | Định nghĩa ở | Đọc trực tiếp | Bảng nguồn rốt cuộc (cột tham chiếu) | Cột ra |")
    w("|---|---|---|---|---|")
    for t in sorted(view):
        cot_goc = _cot_bang_qua(t, view, doc)
        for b in _bang_goc(t, view, doc):
            cot_goc.setdefault(b, set())
        w(
            f"| `{t}` | `{view[t].ban_sua}` | {_o(doc[t].nguon)} | {_bang_cot(cot_goc)} "
            f"| {', '.join(doc[t].cot_ra) or '—'} |"
        )
    w("")

    # 4. Nguồn gốc nhật ký
    w("## Nguồn gốc nhật ký sự kiện")
    w("")
    w("Mọi chỉ số về quy trình bắt đầu ở một chỗ: **cửa chuyển trạng thái duy nhất** của engine")
    w("(`perform_transition`, `backend/app/workflow/engine.py`). Mỗi lần chuyển, cửa này ghi một dòng vào bảng")
    w("`event_log` trong cùng giao dịch với thay đổi trên hồ sơ — `case_id`, `activity`, `timestamp` (UTC),")
    w("`actor`, `from_state`, `to_state`. Trigger `event_log_chan_sua_xoa` chặn UPDATE và DELETE: nhật ký chỉ ghi")
    w("thêm, nên một con số tính từ nó hôm nay vẫn tính lại được ngày mai. Việc tạo hồ sơ không phải lần chuyển")
    w("trạng thái; view `bao_cao_nhat_ky` dựng sự kiện mở đầu `create-case` từ `requests.created_at`.")
    w("")
    w("```text")
    w("perform_transition ──► event_log (chỉ ghi thêm)")
    w("                          │")
    w("                          ├──► bao_cao_nhat_ky ──► xuất dữ liệu mở, khai phá quy trình, lưu trữ lạnh")
    w("                          └──► bao_cao_ho_so ──► view tổng hợp ──► biểu đồ của bảng điều khiển")
    w("```")
    w("")
    w("Nơi khác đọc nhật ký, ngoài bảng điều khiển — quan hệ đọc lấy từ câu SQL trong mã của từng nơi:")
    w("")
    w("| Nơi đọc | Tệp mã | Quan hệ đọc |")
    w("|---|---|---|")
    for nhan, duong in NOI_DOC_KHAC:
        nguon = nguon_cua_tep(duong)
        if nguon is None:
            continue
        w(f"| {nhan} | `{duong}` | {_o(nguon)} |")
    w("")
    w("Bản lưu trữ lạnh của mỗi tháng mang tệp `manifest.json` ghi mã băm SHA-256 và số dòng từng tệp, nên một")
    w("báo cáo dựng lại từ tầng lạnh đối chiếu được với tầng nóng (`scripts/doc_luu_tru.py`).")
    w("")

    # 5. Tra ngược trên màn Quy trình thực tế
    w("## Tra ngược con số trên màn Quy trình thực tế")
    w("")
    w("Màn Quy trình thực tế (mục Báo cáo của cổng) không đi qua Superset: số trên đó là kết quả khai phá của")
    w("dịch vụ `khai-pha` trên `bao_cao_nhat_ky`, cùng nguồn với dữ liệu xuất ở bảng trên. Điểm nghẽn và nhánh")
    w("lệch chuẩn bấm ra đúng danh sách hồ sơ làm nên con số; mọi con số trong câu khuyến nghị tra được về kết")
    w("quả khai phá; mỗi hồ sơ mở ra lịch sử dựng từ chính `event_log` — chuỗi con số → hồ sơ → sự kiện khép")
    w("kín ngay trên giao diện.")
    w("")

    # 6. Giữ đúng
    w("## Giữ trang này đúng")
    w("")
    w("- Đổi một view: thêm bản sửa Alembic mới (`CREATE OR REPLACE VIEW`, không sửa bản cũ), rồi chạy")
    w("  `python scripts/pha_he.py` để sinh lại trang này và trang tương ứng của trang tài liệu.")
    w("- Đổi bảng điều khiển: sửa trên Superset, xuất lại vào `infra/superset/bang-dieu-khien/`, rồi sinh lại.")
    w("- Tích hợp liên tục chạy `python3 scripts/pha_he.py --kiem` trong việc kiểm header: trang lệch với định")
    w("  nghĩa là đỏ. Kịch bản chỉ dùng thư viện chuẩn và đọc tĩnh kho mã, không cần cụm.")
    w("- View phải tạo bằng `op.execute(\"CREATE [OR REPLACE] VIEW …\")` trong `upgrade()` của bản sửa — kịch")
    w("  bản đọc đúng các câu đó.")
    return "\n".join(d) + "\n"


def _dau_trang() -> str:
    return (
        "---\n"
        "title: Phả hệ dữ liệu\n"
        "description: Mỗi biểu đồ của bảng điều khiển lấy số từ view nào và bảng nguồn nào; nguồn gốc nhật ký sự kiện.\n"
        "sidebar:\n"
        "  order: 3\n"
        "---\n\n"
    )


def main() -> int:
    # Bảng điều khiển Windows mặc định không phải UTF-8: không có dòng này, lệnh in câu tiếng Việt đầu tiên
    # ném UnicodeEncodeError trừ khi người chạy tự đặt PYTHONIOENCODING (#368, #472)
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8")
    tham_so = argparse.ArgumentParser(description="Sinh hoặc kiểm trang phả hệ dữ liệu (#379).")
    tham_so.add_argument("--kiem", action="store_true", help="chỉ kiểm hai tệp đã sinh có khớp định nghĩa không")
    ts = tham_so.parse_args()
    try:
        noi_dung = {
            TEP_TAI_LIEU: dung_trang(cho_trang_tai_lieu=False),
            TEP_TRANG: _dau_trang() + dung_trang(cho_trang_tai_lieu=True),
        }
    except LoiDoc as loi:
        print(f"LỖI: {loi}", file=sys.stderr)
        return 2

    if not ts.kiem:
        for tep, chu in noi_dung.items():
            tep.write_bytes(chu.encode("utf-8"))
            print(f"Đã sinh {tep.relative_to(GOC).as_posix()}")
        return 0

    lech = 0
    for tep, chu in noi_dung.items():
        ten = tep.relative_to(GOC).as_posix()
        hien = tep.read_bytes().decode("utf-8").replace("\r\n", "\n") if tep.exists() else ""
        if hien == chu:
            print(f"Khớp: {ten}")
            continue
        lech += 1
        print(f"LỆCH: {ten} — chạy `python scripts/pha_he.py` rồi commit tệp sinh lại.", file=sys.stderr)
        for dong in list(difflib.unified_diff(hien.splitlines(), chu.splitlines(), "đang có", "sinh lại", lineterm=""))[:40]:
            print(dong, file=sys.stderr)
    return 1 if lech else 0


if __name__ == "__main__":
    sys.exit(main())
