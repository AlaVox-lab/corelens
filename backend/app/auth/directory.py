# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Danh bạ: tra người trong một phòng ban (#84), và liên hệ của một người (#131), từ
# Keycloak.
#
# Đây là chỗ DUY NHẤT dịch vụ ứng dụng gọi ngược sang Keycloak. ADR-0001 giữ Keycloak
# ngoài đường đi nóng — kiểm token ở mỗi yêu cầu chạy cục bộ bằng khóa công khai — và
# điều đó vẫn đúng: danh bạ chỉ được hỏi khi trưởng phòng mở ô chọn người xử lý, hay
# khi nhân viên mở trang chi tiết hồ sơ để xem liên hệ người gửi — vài lần cho mỗi hồ
# sơ, không phải ở mỗi yêu cầu. Máy trạng thái cũng không gọi tới đây: engine vẫn chạy
# được khi Keycloak tắt.
#
# KHÔNG GIỮ BỘ ĐỆM DANH BẠ, cố ý:
#
#   - Người vừa chuyển phòng hay nghỉ việc phải biến khỏi danh sách NGAY. Bộ đệm sẽ
#     còn gợi ý họ thêm một khoảng, và giao việc cho người đã rời phòng là lỗi thật,
#     không phải chuyện hiển thị chậm
#   - Chạy nhiều tiến trình dịch vụ thì mỗi tiến trình giữ một bộ đệm, lệch nhau
#   - Keycloak không phản hồi thì bộ đệm cũ sẽ che lỗi đi. Ô chọn người phải nói rõ là
#     không nạp được, cùng nguyên tắc với /health: hỏng thì nói là hỏng
#
# Chỉ giữ token của tài khoản dịch vụ, tới gần lúc hết hạn. Xin token mới ở mỗi lần
# tra là gấp đôi số lần gọi mà không được gì.
#
# Gọi bằng urllib của thư viện chuẩn, như PyJWKClient ở tokens.py — không thêm phụ
# thuộc nào cho vài lần gọi HTTP.

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as HetGio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.config import get_settings

# Số người lấy mỗi trang khi đọc thành viên nhóm. Một phòng ban hiếm khi vượt con số
# này, nhưng vẫn đọc theo trang để không cắt cụt danh sách một cách âm thầm.
_CO_TRANG = 100

# Luồng chạy các lần tra. Có luồng riêng là để giữ được trần thời gian: `timeout` của
# urllib chỉ phủ phần kết nối và đọc, KHÔNG phủ bước tra DNS. Đo thật khi tắt Keycloak
# trong cụm Compose: tên `keycloak` không còn ai trả lời, bước tra DNS treo 8 giây, và
# trang đứng theo dù trần đặt là 3 giây. Chờ kết quả bằng `result(timeout=...)` thì
# trả lời đúng hạn bất kể mạng hỏng ở tầng nào.
#
# Bốn luồng là đủ cho vài trưởng phòng mở ô chọn cùng lúc, và chặn trên số luồng bị
# kẹt khi Keycloak treo: luồng kẹt tự thoát khi phép gọi mạng bên trong hết hạn.
_LUONG_TRA = ThreadPoolExecutor(max_workers=4, thread_name_prefix="danh-ba")

# Trả token sớm hơn hạn thật chừng này giây, để một lần tra không bắt đầu bằng token
# còn hạn rồi kết thúc bằng token đã hết hạn.
_DU_TRU_HAN_TOKEN = 30


class DirectoryUnavailable(Exception):
    """Danh bạ không trả lời được: Keycloak tắt, quá thời gian, hoặc từ chối tài khoản
    dịch vụ. Phía gọi phải báo rõ cho người dùng, không được coi như danh sách rỗng."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class Person:
    """Một người trong danh bạ.

    `id` là `sub` của Keycloak — đúng thứ ghi xuống `assignee_id`. Tên chỉ là lớp hiển
    thị, không bao giờ được lưu thay cho định danh: người đổi tên thì hồ sơ vẫn trỏ
    đúng người.
    """

    id: str
    username: str
    name: str
    roles: frozenset[str]
    # Chỉ `everyone()` (#251) điền hai trường dưới; `department_members` để trống
    departments: frozenset[str] = frozenset()
    email: str | None = None


@dataclass(frozen=True, slots=True)
class Contact:
    """Cách liên hệ một người, đọc từ hồ sơ người dùng của Keycloak (#131).

    Cả hai trường đều có thể trống: số điện thoại không bắt buộc, người dùng tự điền ở
    trang tài khoản. Trống nghĩa là *chưa điền*, khác với danh bạ không trả lời — trường
    hợp đó là `DirectoryUnavailable`.
    """

    email: str | None
    phone: str | None


def _ten_hien_thi(nguoi: dict) -> str:
    """Ghép tên y như claim `name` của token, để danh bạ và nhật ký gọi một người bằng
    cùng một tên. Keycloak dựng claim đó bằng tên riêng, dấu cách, rồi họ."""
    ghep = " ".join(p for p in (nguoi.get("firstName"), nguoi.get("lastName")) if p)
    return ghep or nguoi["username"]


class KeycloakDirectory:
    """Máy khách Admin API của Keycloak, chỉ đọc: thành viên phòng ban, và liên hệ của
    một người."""

    def __init__(
        self,
        *,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        department_prefix: str,
        timeout_seconds: float,
        phone_attribute: str = "phoneNumber",
    ) -> None:
        self._goc = base_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._bi_mat = client_secret
        self._tien_to = department_prefix
        self._tran_giay = timeout_seconds
        self._thuoc_tinh_so = phone_attribute

        self._khoa = threading.Lock()
        self._token: str | None = None
        self._token_het_han = 0.0

    def department_members(self, department_code: str) -> list[Person]:
        """Người thuộc trực tiếp nhóm phòng ban, kèm vai trò hiệu lực, xếp theo tên.

        Vai trò là vai trò HIỆU LỰC — kể cả vai trò nhận qua nhóm hay vai trò ghép —
        vì đó mới là thứ có trong token khi người đó đăng nhập. Tài khoản bị khóa bị
        loại: họ không đăng nhập được thì giao việc cho họ là giao vào khoảng không.

        Nhóm không tồn tại trong Keycloak thì trả danh sách rỗng: phòng ban có trong
        bảng dữ liệu nhưng chưa ai được xếp vào. Đó là dữ liệu, không phải sự cố.
        """
        return self._trong_tran(self._tra_phong, department_code)

    def contact(self, user_id: str) -> Contact | None:
        """Email và số điện thoại của một người, tra theo `sub` (#131).

        Không còn tài khoản — người đã bị xóa khỏi Keycloak — thì trả `None`, không coi
        là sự cố: hồ sơ cũ vẫn mang tên người gửi, chỉ không còn cách liên hệ. Tài khoản
        bị khóa thì vẫn trả: người đã nghỉ việc vẫn có thể cần được liên hệ về hồ sơ cũ.
        """
        return self._trong_tran(self._tra_lien_he, user_id)

    def everyone(self, timeout_seconds: float) -> list[Person]:
        """Mọi tài khoản đang bật, kèm vai trò hiệu lực, phòng ban và email — cho bộ gửi thư (#251).

        Bộ gửi thư cần biết ai đang có bước chính trên một hồ sơ, mà bước chính có thể thuộc một vai
        không gắn phòng ban nào (điều phối viên). Quyền `view-users` không đọc được `/roles/<vai>/users`
        (Keycloak đòi thêm quyền xem realm), nên đọc cả danh bạ theo trang rồi tra vai trò và nhóm từng
        người — hai lần gọi mỗi người. Chạy ở bộ quét nền với trần riêng, không bao giờ trên đường
        của một yêu cầu; phía gọi nhớ kết quả vài phút. Danh bạ vài nghìn người thì nên đổi sang nhóm
        theo vai — ghi ở ARCHITECTURE.md.
        """
        return self._trong_tran(self._tra_tat_ca, timeout_seconds, tran=timeout_seconds)

    def _trong_tran(self, ham: Callable[..., Any], *tham_so: Any, tran: float | None = None) -> Any:
        """Chạy một lần tra trong luồng riêng, giữ đúng trần thời gian — lý do ở chú thích
        của `_LUONG_TRA`."""
        tran = tran or self._tran_giay
        tuong_lai = _LUONG_TRA.submit(ham, *tham_so)
        try:
            return tuong_lai.result(timeout=tran)
        except HetGio:
            tuong_lai.cancel()
            raise DirectoryUnavailable(
                f"Keycloak không trả lời xong trong {tran:g} giây."
            ) from None

    def _tra_tat_ca(self, tran: float) -> list[Person]:
        thoi_han = time.monotonic() + tran
        tai_khoan: list[dict] = []
        while True:
            trang = self._goi(
                f"/users?first={len(tai_khoan)}&max={_CO_TRANG}&briefRepresentation=true",
                thoi_han,
            )
            tai_khoan.extend(trang)
            if len(trang) < _CO_TRANG:
                break
        tien_to = "/" + self._tien_to.strip("/") + "/"
        ket_qua = []
        for nguoi in tai_khoan:
            if not nguoi.get("enabled", True):
                continue
            vai_tro = self._goi(f"/users/{nguoi['id']}/role-mappings/realm/composite", thoi_han)
            nhom = self._goi(f"/users/{nguoi['id']}/groups?briefRepresentation=true", thoi_han)
            ket_qua.append(
                Person(
                    id=nguoi["id"],
                    username=nguoi["username"],
                    name=_ten_hien_thi(nguoi),
                    roles=frozenset(v["name"] for v in vai_tro),
                    departments=frozenset(
                        n["path"][len(tien_to) :]
                        for n in nhom
                        if n.get("path", "").startswith(tien_to) and len(n["path"]) > len(tien_to)
                    ),
                    email=nguoi.get("email") or None,
                )
            )
        return ket_qua

    def _tra_lien_he(self, user_id: str) -> Contact | None:
        thoi_han = time.monotonic() + self._tran_giay
        nguoi = self._goi(
            f"/users/{urllib.parse.quote(user_id, safe='')}", thoi_han, cho_phep_404=True
        )
        if nguoi is None:
            return None
        so = [s.strip() for s in (nguoi.get("attributes") or {}).get(self._thuoc_tinh_so, [])]
        return Contact(
            email=nguoi.get("email") or None,
            phone=next((s for s in so if s), None),
        )

    def _tra_phong(self, department_code: str) -> list[Person]:
        thoi_han = time.monotonic() + self._tran_giay

        duong_dan = urllib.parse.quote(
            (self._tien_to + department_code).strip("/"), safe="/"
        )
        nhom = self._goi(f"/group-by-path/{duong_dan}", thoi_han, cho_phep_404=True)
        if nhom is None:
            return []

        thanh_vien: list[dict] = []
        while True:
            trang = self._goi(
                f"/groups/{nhom['id']}/members"
                f"?first={len(thanh_vien)}&max={_CO_TRANG}&briefRepresentation=true",
                thoi_han,
            )
            thanh_vien.extend(trang)
            if len(trang) < _CO_TRANG:
                break

        ket_qua = []
        for nguoi in thanh_vien:
            if not nguoi.get("enabled", True):
                continue
            vai_tro = self._goi(
                f"/users/{nguoi['id']}/role-mappings/realm/composite", thoi_han
            )
            ket_qua.append(
                Person(
                    id=nguoi["id"],
                    username=nguoi["username"],
                    name=_ten_hien_thi(nguoi),
                    roles=frozenset(v["name"] for v in vai_tro),
                )
            )
        return sorted(ket_qua, key=lambda p: (p.name.casefold(), p.username))

    # --- Gọi mạng -----------------------------------------------------------

    def _con_lai(self, thoi_han: float) -> float:
        con_lai = thoi_han - time.monotonic()
        if con_lai <= 0:
            raise DirectoryUnavailable(
                f"Keycloak không trả lời xong trong {self._tran_giay:g} giây."
            )
        return con_lai

    def _goi(
        self,
        duong_dan: str,
        thoi_han: float,
        *,
        cho_phep_404: bool = False,
        da_thu_lai: bool = False,
    ) -> Any:
        """Một lần gọi Admin API. Hết hạn token giữa chừng thì xin token mới, thử lại
        đúng một lần."""
        yeu_cau = urllib.request.Request(
            f"{self._goc}/admin/realms/{self._realm}{duong_dan}",
            headers={
                "Authorization": f"Bearer {self._lay_token(thoi_han)}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(yeu_cau, timeout=self._con_lai(thoi_han)) as ph:
                return json.load(ph)
        except urllib.error.HTTPError as loi:
            if loi.code == 404 and cho_phep_404:
                return None
            if loi.code == 401 and not da_thu_lai:
                self._bo_token()
                return self._goi(
                    duong_dan, thoi_han, cho_phep_404=cho_phep_404, da_thu_lai=True
                )
            if loi.code == 403:
                raise DirectoryUnavailable(
                    f"Keycloak từ chối tài khoản dịch vụ '{self._client_id}'. Kiểm "
                    "client này có quyền view-users của realm-management."
                ) from loi
            raise DirectoryUnavailable(
                f"Keycloak trả lỗi {loi.code} khi tra danh bạ."
            ) from loi
        except (urllib.error.URLError, OSError, ValueError) as loi:
            # ValueError bắt cả JSONDecodeError: Keycloak đang khởi động có thể trả
            # một trang HTML thay vì JSON.
            raise DirectoryUnavailable(f"Không gọi được Keycloak: {loi}") from loi

    def _lay_token(self, thoi_han: float) -> str:
        """Token của tài khoản dịch vụ, xin bằng luồng client credentials.

        Giữ khóa trong lúc xin, để nhiều yêu cầu đến cùng lúc không cùng đi xin token.
        """
        with self._khoa:
            if self._token and time.monotonic() < self._token_het_han:
                return self._token

            if not self._bi_mat:
                raise DirectoryUnavailable(
                    "Chưa cấu hình bí mật cho client danh bạ "
                    "(biến môi trường DXLAB_DIRECTORY_CLIENT_SECRET)."
                )

            yeu_cau = urllib.request.Request(
                f"{self._goc}/realms/{self._realm}/protocol/openid-connect/token",
                data=urllib.parse.urlencode(
                    {
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._bi_mat,
                    }
                ).encode(),
            )
            try:
                with urllib.request.urlopen(
                    yeu_cau, timeout=self._con_lai(thoi_han)
                ) as ph:
                    goi = json.load(ph)
            except urllib.error.HTTPError as loi:
                raise DirectoryUnavailable(
                    f"Keycloak không cấp token cho tài khoản dịch vụ "
                    f"'{self._client_id}' (lỗi {loi.code}). Kiểm mã client và bí mật."
                ) from loi
            except (urllib.error.URLError, OSError, ValueError) as loi:
                raise DirectoryUnavailable(f"Không gọi được Keycloak: {loi}") from loi

            self._token = goi["access_token"]
            self._token_het_han = time.monotonic() + max(
                goi.get("expires_in", 60) - _DU_TRU_HAN_TOKEN, 0
            )
            return self._token

    def _bo_token(self) -> None:
        with self._khoa:
            self._token = None
            self._token_het_han = 0.0


@lru_cache
def get_directory() -> KeycloakDirectory:
    """Danh bạ dùng chung cho cả vòng đời tiến trình, để token dịch vụ được dùng lại.

    Là một phụ thuộc FastAPI, nên bộ kiểm thử thay được bằng danh bạ giả qua
    `app.dependency_overrides` mà không cần Keycloak.
    """
    cau_hinh = get_settings()
    return KeycloakDirectory(
        base_url=cau_hinh.keycloak_internal_url,
        realm=cau_hinh.keycloak_realm,
        client_id=cau_hinh.directory_client_id,
        client_secret=cau_hinh.directory_client_secret,
        department_prefix=cau_hinh.oidc_department_group_prefix,
        timeout_seconds=cau_hinh.directory_timeout_seconds,
        phone_attribute=cau_hinh.directory_phone_attribute,
    )
