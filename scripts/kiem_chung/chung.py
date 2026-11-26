# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Phần dùng chung của bộ công cụ kiểm chứng (#249): tìm lệnh docker, đặt tên cụm thử, sinh tệp biến
# môi trường cho cụm thử, và gọi Admin API của Keycloak.
#
# Chỉ dùng thư viện chuẩn của Python 3.10 trở lên và lệnh `docker`. Công cụ KHÔNG biết tên trạng
# thái, vai trò hay phòng ban nào: mọi thứ thuộc nghiệp vụ được đọc từ cơ sở dữ liệu của cụm.
from __future__ import annotations

import argparse
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parents[2]
TEP_COMPOSE = GOC_KHO / "infra" / "docker-compose.yml"
TEP_COMPOSE_GHI_DE = GOC_KHO / "infra" / "docker-compose.cum-thu.yml"
TEP_ENV_MAU = GOC_KHO / "infra" / ".env.example"
# Khớp mẫu `.env.*` trong .gitignore nên không bao giờ vào kho
TEP_ENV_CUM_THU = GOC_KHO / "infra" / ".env.cum-thu"

TIEN_TO_MAC_DINH = "thu-"
NHAN_MAC_DINH = "cum-thu"
DU_AN_MAC_DINH = "dxlab-thu"
DICH_CONG_MAC_DINH = 20000
MAT_KHAU_MAU = "matkhau123"

# Tên dự án và tiền tố container của cụm đang dùng thật (infra/docker-compose.yml). Cụm thử tuyệt
# đối không được trùng: `down -v` hay `rmi` theo tên trùng sẽ xóa dữ liệu của người dùng.
DU_AN_CUM_CHINH = "dx-os-lab"
TIEN_TO_CUM_CHINH = "dxlab-"

DICH_VU = ("postgres", "keycloak", "seaweedfs", "superset", "backend", "cong-api", "frontend", "khai-pha")
# Mọi biến cổng của .env.example, đều được dời khi sinh tệp cho cụm thử. BACKEND_PORT và POSTGRES_PORT chỉ
# có tác dụng khi thêm docker-compose.phat-trien.yml (#364) nhưng vẫn dời để cụm thử dùng được tệp đó
KHOA_CONG = ("POSTGRES_PORT", "KEYCLOAK_PORT", "SEAWEEDFS_S3_PORT", "SUPERSET_PORT", "BACKEND_PORT", "FRONTEND_PORT",
             "GATEWAY_PORT")
# Cổng thật sự mở ra máy ở cấu hình mặc định — phải trống trước khi dựng cụm thử
KHOA_CONG_MO = ("KEYCLOAK_PORT", "SEAWEEDFS_S3_PORT", "SUPERSET_PORT", "FRONTEND_PORT", "GATEWAY_PORT")


def dung_utf8() -> None:
    """Terminal Windows hay mặc định bảng mã cũ, in tiếng Việt có dấu sẽ vỡ."""
    for luong in (sys.stdout, sys.stderr):
        # Ghi từng dòng: đầu ra của lệnh con chảy thẳng ra màn hình, lời mình phải đứng đúng chỗ
        luong.reconfigure(encoding="utf-8", line_buffering=True)


def thoat(thong_bao: str, ma: int = 1) -> None:
    print(thong_bao, file=sys.stderr)
    sys.exit(ma)


# ---------------------------------------------------------------------------
# Lệnh docker
# ---------------------------------------------------------------------------

@functools.cache
def docker() -> str:
    """Tìm lệnh `docker`: biến DOCKER_BIN, rồi PATH, rồi hai chỗ cài mặc định của Docker Desktop."""
    tu_bien = os.environ.get("DOCKER_BIN")
    if tu_bien:
        return tu_bien
    thay = shutil.which("docker")
    if thay:
        return thay
    for goc in (os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if not goc:
            continue
        for phan_con in ("Docker/Docker/resources/bin", "Programs/DockerDesktop/resources/bin"):
            ung_vien = Path(goc) / phan_con / "docker.exe"
            if ung_vien.is_file():
                return str(ung_vien)
    thoat("Không tìm thấy lệnh docker. Bật Docker Desktop (hay cài Docker Engine), hoặc đặt biến "
          "DOCKER_BIN trỏ tới tệp docker.")
    raise AssertionError  # không tới được


# Git Bash trên Windows tự đổi đường dẫn kiểu /app/... thành đường dẫn Windows; tắt cho lệnh con
MOI_TRUONG = {**os.environ, "MSYS_NO_PATHCONV": "1", "MSYS2_ARG_CONV_EXCL": "*"}


@dataclass
class KetQuaLenh:
    ma: int
    dau_ra: str
    loi: str


def chay(lenh: list[str], *, vao: str | None = None, cho_toi_da: float | None = None,
         cwd: Path | None = None) -> KetQuaLenh:
    """Chạy một lệnh và gom đầu ra. Hết giờ thì trả mã 124 (cùng quy ước với lệnh `timeout`)."""
    try:
        kq = subprocess.run(
            lenh, input=None if vao is None else vao.encode("utf-8"), capture_output=True,
            env=MOI_TRUONG, timeout=cho_toi_da, cwd=cwd, check=False,
        )
    except subprocess.TimeoutExpired:
        return KetQuaLenh(124, "", "quá giờ")
    return KetQuaLenh(kq.returncode, kq.stdout.decode("utf-8", "replace"), kq.stderr.decode("utf-8", "replace"))


def chay_truc_tiep(lenh: list[str], cwd: Path | None = None) -> int:
    """Chạy một lệnh, để đầu ra chảy thẳng ra màn hình (dựng ảnh có thể mất vài phút)."""
    return subprocess.run(lenh, env=MOI_TRUONG, cwd=cwd, check=False).returncode


def trang_thai_suc_khoe(container: str) -> str:
    """`healthy`, `unhealthy`, `starting`, hay `running`/`exited`… khi container không khai kiểm sức khỏe."""
    kq = chay([docker(), "inspect", "--format",
               "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", container])
    return kq.dau_ra.strip() if kq.ma == 0 else "khong-co"


def cho_container(container: str, mong_doi: str = "healthy", toi_da_giay: int = 600) -> bool:
    import time

    han = time.monotonic() + toi_da_giay
    while time.monotonic() < han:
        tt = trang_thai_suc_khoe(container)
        if tt == mong_doi:
            return True
        if tt in ("exited", "dead"):
            return False
        time.sleep(3)
    return False


# ---------------------------------------------------------------------------
# Tham số cụm thử, dùng chung cho mọi công cụ
# ---------------------------------------------------------------------------

def them_tham_so_cum(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("cụm thử")
    g.add_argument("--tien-to", default=TIEN_TO_MAC_DINH,
                   help=f"Tiền tố tên container (mặc định {TIEN_TO_MAC_DINH!r})")
    g.add_argument("--nhan", default=NHAN_MAC_DINH,
                   help=f"Nhãn ảnh dxlab-backend, dxlab-frontend, dxlab-superset (mặc định {NHAN_MAC_DINH!r})")
    g.add_argument("--du-an", default=DU_AN_MAC_DINH,
                   help=f"Tên dự án Compose (mặc định {DU_AN_MAC_DINH!r})")
    g.add_argument("--dich-cong", type=int, default=DICH_CONG_MAC_DINH,
                   help=f"Cộng thêm số này vào mọi cổng của .env.example (mặc định {DICH_CONG_MAC_DINH})")
    g.add_argument("--tep-env", type=Path, default=TEP_ENV_CUM_THU,
                   help="Tệp biến môi trường sinh cho cụm thử (mặc định infra/.env.cum-thu, đã nằm trong .gitignore)")


def doc_env(tep: Path) -> dict[str, str]:
    ket_qua: dict[str, str] = {}
    for dong in tep.read_text(encoding="utf-8").splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        khoa, _, gia_tri = dong.partition("=")
        ket_qua[khoa.strip()] = gia_tri.strip()
    return ket_qua


@dataclass
class CumThu:
    tien_to: str
    nhan: str
    du_an: str
    dich_cong: int
    tep_env: Path

    @classmethod
    def tu_tham_so(cls, ts: argparse.Namespace) -> CumThu:
        cum = cls(ts.tien_to, ts.nhan, ts.du_an, ts.dich_cong, Path(ts.tep_env).resolve())
        cum.kiem_an_toan()
        return cum

    def kiem_an_toan(self) -> None:
        """Từ chối mọi tham số làm cụm thử trùng tên hay cổng với cụm đang dùng thật."""
        mau = doc_env(TEP_ENV_MAU)
        if self.du_an == DU_AN_CUM_CHINH:
            thoat(f"--du-an {self.du_an!r} là tên dự án của cụm đang dùng thật. Chọn tên khác.")
        if self.tien_to.startswith(TIEN_TO_CUM_CHINH) or not self.tien_to:
            thoat(f"--tien-to {self.tien_to!r} trùng tên container của cụm đang dùng thật "
                  f"({TIEN_TO_CUM_CHINH}*). Chọn tiền tố khác.")
        cam_nhan = {mau.get("DXLAB_VERSION"), mau.get("SUPERSET_VERSION"), "latest"}
        # Cụm đang dùng thật đọc thẻ ảnh ở infra/.env — có thể khác tệp mẫu (cụm dựng trước #552 ghi 0.3.0)
        that = GOC_KHO / "infra" / ".env"
        if that.is_file():
            env_that = doc_env(that)
            cam_nhan |= {env_that.get("DXLAB_VERSION"), env_that.get("SUPERSET_VERSION")}
        if self.nhan in cam_nhan:
            thoat(f"--nhan {self.nhan!r} trùng nhãn ảnh của cụm đang dùng thật: dựng lại sẽ ghi đè ảnh "
                  "của người dùng. Chọn nhãn khác.")
        if self.dich_cong == 0:
            thoat("--dich-cong 0 là giữ nguyên cổng của cụm đang dùng thật. Dùng số khác 0.")
        if self.tep_env.resolve() == TEP_ENV_MAU.resolve():
            thoat("--tep-env không được trùng infra/.env.example.")

    # --- tên gọi ---

    def container(self, dich_vu: str) -> str:
        return f"{self.tien_to}{dich_vu}"

    def anh(self, ten: str) -> str:
        return f"dxlab-{ten}:{self.nhan}"

    @property
    def ten_cac_anh(self) -> list[str]:
        return [self.anh(t) for t in ("backend", "frontend", "superset", "khai-pha")]

    # --- tệp biến môi trường ---

    def sinh_env(self) -> dict[str, str]:
        """Sinh tệp biến môi trường từ infra/.env.example (không sửa tệp mẫu) và trả về nội dung."""
        mau = TEP_ENV_MAU.read_text(encoding="utf-8").splitlines()
        ra: list[str] = [
            "# Tệp SINH TỰ ĐỘNG bởi scripts/kiem_chung/cum_thu.py (#249) cho cụm thử cách ly.",
            "# Đã nằm trong .gitignore. Xóa và sinh lại bất cứ lúc nào, đừng sửa tay.",
            "",
        ]
        gia_tri: dict[str, str] = {}
        for dong in mau:
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", dong)
            if m:
                khoa, v = m.group(1), m.group(2).strip()
                if khoa in KHOA_CONG:
                    v = str(int(v) + self.dich_cong)
                elif khoa == "DXLAB_VERSION":
                    v = self.nhan
                gia_tri[khoa] = v
                dong = f"{khoa}={v}"
            ra.append(dong)
        ra += [
            "",
            "# =============================================================================",
            "# Riêng cụm thử — docker-compose.cum-thu.yml đọc hai biến này",
            "# =============================================================================",
            f"CUM_THU_TIEN_TO={self.tien_to}",
            f"CUM_THU_NHAN={self.nhan}",
            "",
        ]
        gia_tri["CUM_THU_TIEN_TO"] = self.tien_to
        gia_tri["CUM_THU_NHAN"] = self.nhan
        self.tep_env.parent.mkdir(parents=True, exist_ok=True)
        self.tep_env.write_text("\n".join(ra), encoding="utf-8", newline="\n")
        return gia_tri

    def env(self) -> dict[str, str]:
        """Biến của cụm thử; sinh tệp nếu chưa có."""
        if not self.tep_env.is_file():
            return self.sinh_env()
        return doc_env(self.tep_env)

    def lenh_compose(self, *doi_so: str) -> list[str]:
        return [docker(), "compose", "-p", self.du_an, "--env-file", str(self.tep_env),
                "-f", str(TEP_COMPOSE), "-f", str(TEP_COMPOSE_GHI_DE), *doi_so]

    # --- địa chỉ ---

    def dia_chi(self, co_superset: bool = True) -> list[tuple[str, str]]:
        e = self.env()
        bang = [
            ("Cổng người dùng", f"http://localhost:{e['FRONTEND_PORT']}"),
            ("Keycloak (quản trị: admin)", f"http://localhost:{e['KEYCLOAK_PORT']}"),
            # Cửa vào duy nhất của API (#364); dịch vụ ứng dụng và PostgreSQL không mở cổng ra máy
            ("Cổng API (tài liệu API)", f"http://localhost:{e['GATEWAY_PORT']}/docs"),
            ("Superset", f"http://localhost:{e['SUPERSET_PORT']}"),
            ("S3 của SeaweedFS", f"http://localhost:{e['SEAWEEDFS_S3_PORT']}"),
        ]
        return bang if co_superset else [b for b in bang if b[0] != "Superset"]

    def in_dia_chi(self, co_superset: bool = True) -> None:
        print("\nĐịa chỉ cụm thử:")
        rong = max(len(ten) for ten, _ in self.dia_chi(co_superset))
        for ten, url in self.dia_chi(co_superset):
            print(f"  {ten.ljust(rong)}  {url}")


# ---------------------------------------------------------------------------
# HTTP và Keycloak
# ---------------------------------------------------------------------------

def http_lay(url: str, cho: float = 5.0) -> int | None:
    """Mã trạng thái HTTP của một yêu cầu GET, `None` khi không kết nối được."""
    try:
        with urllib.request.urlopen(url, timeout=cho) as r:
            return r.status
    except urllib.error.HTTPError as loi:
        return loi.code
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def keycloak_goi(url: str, *, than: bytes | None = None, token: str | None = None,
                 phuong_thuc: str | None = None, json_body: object = None):
    tieu_de: dict[str, str] = {}
    if token:
        tieu_de["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        than = json.dumps(json_body).encode("utf-8")
        tieu_de["Content-Type"] = "application/json"
    yc = urllib.request.Request(url, data=than, headers=tieu_de, method=phuong_thuc)
    with urllib.request.urlopen(yc, timeout=15) as r:
        noi_dung = r.read()
        return json.loads(noi_dung) if noi_dung else None


def keycloak_token_quan_tri(goc: str, ten: str, mat_khau: str) -> str:
    return keycloak_goi(
        f"{goc}/realms/master/protocol/openid-connect/token",
        than=urllib.parse.urlencode(
            {"grant_type": "password", "client_id": "admin-cli", "username": ten, "password": mat_khau}
        ).encode(),
    )["access_token"]
