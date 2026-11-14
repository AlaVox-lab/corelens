# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Khởi tạo kho tri thức Wiki.js (#321, ADR-0006) — chạy một lần mỗi lần dựng hồ sơ `tri-thuc`, lặp lại an toàn.
#
#     python /tri-thuc/khoi_tao.py chuan-bi   # TRƯỚC Wiki.js: database riêng, client OIDC trong Keycloak
#     python /tri-thuc/khoi_tao.py khoi-tao   # SAU Wiki.js: hoàn tất cài đặt, đăng nhập một lần, nhóm,
#                                             #   khóa API chỉ đọc, bài mẫu
#
# Ranh giới AGPL (ADR-0006): tệp này KHÔNG chứa hay nạp mã Wiki.js. Nó nói chuyện với Wiki.js qua HTTP
# (`/finalize` của trang cài đặt và GraphQL `/graphql`) như mọi chương trình khách khác, và với Keycloak
# qua API quản trị. Wiki.js chạy nguyên ảnh chính thức.
#
# Vì sao client OIDC tạo qua API quản trị chứ không khai trong realm-dx-os-lab.json: Keycloak chỉ nạp tệp
# realm lần đầu tạo realm, nên cụm đã chạy từ trước sẽ không bao giờ thấy client mới. Một đường duy nhất
# — kiểm, thiếu thì tạo, có rồi thì cập nhật — chạy được cho cả cụm dựng mới lẫn cụm cũ nâng lên.
#
# Chạy trong ảnh của dịch vụ ứng dụng (đã có Python và psycopg) nên không thêm ảnh nào. Mọi giá trị đọc từ
# biến môi trường Compose đặt; không có gì mã cứng ngoài từ vựng của chính Wiki.js và Keycloak.

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHO_TOI_DA_GIAY = 300


def bien(ten: str, mac_dinh: str | None = None) -> str:
    gia_tri = os.environ.get(ten, mac_dinh)
    if gia_tri is None or gia_tri == "":
        sys.exit(f"Thiếu biến môi trường {ten}")
    return gia_tri


def danh_sach(ten: str) -> list[str]:
    return [x.strip() for x in bien(ten).split(",") if x.strip()]


def ghi(thong_diep: str) -> None:
    print(f"[tri-thuc] {thong_diep}", flush=True)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def goi(
    url: str,
    *,
    phuong_thuc: str = "GET",
    json_than: object | None = None,
    form: dict | None = None,
    token: str | None = None,
    thoi_han: float = 15,
) -> tuple[int, bytes]:
    tieu_de = {"Accept": "application/json"}
    du_lieu = None
    if json_than is not None:
        du_lieu = json.dumps(json_than).encode("utf-8")
        tieu_de["Content-Type"] = "application/json; charset=utf-8"
    elif form is not None:
        du_lieu = urllib.parse.urlencode(form).encode("utf-8")
        tieu_de["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        tieu_de["Authorization"] = f"Bearer {token}"
    yeu_cau = urllib.request.Request(url, data=du_lieu, headers=tieu_de, method=phuong_thuc)
    try:
        with urllib.request.urlopen(yeu_cau, timeout=thoi_han) as tl:
            return tl.status, tl.read()
    except urllib.error.HTTPError as loi:
        return loi.code, loi.read()


def cho(mo_ta: str, ham) -> object:
    """Gọi `ham` tới khi nó trả giá trị khác None, hay hết giờ."""
    het = time.monotonic() + CHO_TOI_DA_GIAY
    while True:
        try:
            ket_qua = ham()
            if ket_qua is not None:
                return ket_qua
        except (urllib.error.URLError, OSError, ConnectionError):
            pass
        if time.monotonic() > het:
            sys.exit(f"Hết {CHO_TOI_DA_GIAY} giây chờ {mo_ta}")
        time.sleep(3)


# ---------------------------------------------------------------------------
# Bước 1 — trước Wiki.js
# ---------------------------------------------------------------------------


def tao_csdl() -> None:
    """Database riêng của Wiki.js trên thực thể PostgreSQL của cụm (ảnh đã ghim, không thêm ảnh CSDL)."""
    import psycopg

    ten = bien("WIKI_DB_NAME")
    with psycopg.connect(
        host=bien("PGHOST"), user=bien("PGUSER"), password=bien("PGPASSWORD"), dbname=bien("PGDATABASE"),
        autocommit=True,
    ) as ket_noi:
        co = ket_noi.execute("SELECT 1 FROM pg_database WHERE datname = %s", (ten,)).fetchone()
        if co:
            ghi(f"database {ten} đã có")
            return
        ket_noi.execute(f'CREATE DATABASE "{ten}"')
        ghi(f"đã tạo database {ten}")


def token_quan_tri_keycloak(goc: str) -> str:
    def thu():
        ma, than = goi(
            f"{goc}/realms/master/protocol/openid-connect/token",
            phuong_thuc="POST",
            form={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": bien("KEYCLOAK_ADMIN_USER"),
                "password": bien("KEYCLOAK_ADMIN_PASSWORD"),
            },
        )
        return json.loads(than)["access_token"] if ma == 200 else None

    return cho("Keycloak nhận đăng nhập quản trị", thu)


def dam_bao_client() -> None:
    """Client OIDC của kho tri thức trong realm, kèm bộ ánh xạ đưa vai trò realm vào claim nhóm."""
    goc = bien("KEYCLOAK_INTERNAL_URL")
    realm = bien("KEYCLOAK_REALM")
    ma_client = bien("WIKI_OIDC_CLIENT_ID")
    dia_chi_wiki = bien("WIKI_PUBLIC_URL").rstrip("/")
    khoa = bien("WIKI_STRATEGY_KEY")
    token = token_quan_tri_keycloak(goc)
    api = f"{goc}/admin/realms/{realm}/clients"

    mong_muon = {
        "clientId": ma_client,
        "name": "Kho tri thức",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "secret": bien("WIKI_OIDC_SECRET"),
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "rootUrl": dia_chi_wiki,
        "baseUrl": f"/login/{khoa}",
        "redirectUris": [f"{dia_chi_wiki}/login/{khoa}/callback"],
        "webOrigins": [dia_chi_wiki],
        "attributes": {"post.logout.redirect.uris": f"{dia_chi_wiki}/*"},
    }
    ma, than = goi(f"{api}?clientId={urllib.parse.quote(ma_client)}", token=token)
    if ma != 200:
        sys.exit(f"Không đọc được danh sách client của realm {realm}: {ma} {than[:200]!r}")
    co_san = json.loads(than)
    if co_san:
        ban = {**co_san[0], **mong_muon, "attributes": {**co_san[0].get("attributes", {}), **mong_muon["attributes"]}}
        ma, than = goi(f"{api}/{ban['id']}", phuong_thuc="PUT", json_than=ban, token=token)
        if ma not in (200, 204):
            sys.exit(f"Không cập nhật được client {ma_client}: {ma} {than[:200]!r}")
        id_client = ban["id"]
        ghi(f"client {ma_client} đã có, đã cập nhật địa chỉ và bí mật")
    else:
        ma, than = goi(api, phuong_thuc="POST", json_than=mong_muon, token=token)
        if ma != 201:
            sys.exit(f"Không tạo được client {ma_client}: {ma} {than[:200]!r}")
        ma, than = goi(f"{api}?clientId={urllib.parse.quote(ma_client)}", token=token)
        id_client = json.loads(than)[0]["id"]
        ghi(f"đã tạo client {ma_client}")

    ten_anh_xa = "vai-tro-thanh-nhom-wiki"
    ma, than = goi(f"{api}/{id_client}/protocol-mappers/models", token=token)
    if not any(m.get("name") == ten_anh_xa for m in json.loads(than)):
        ma, than = goi(
            f"{api}/{id_client}/protocol-mappers/models",
            phuong_thuc="POST",
            token=token,
            json_than={
                "name": ten_anh_xa,
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-realm-role-mapper",
                "config": {
                    "claim.name": bien("WIKI_GROUPS_CLAIM"),
                    "multivalued": "true",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                },
            },
        )
        if ma != 201:
            sys.exit(f"Không tạo được bộ ánh xạ vai trò: {ma} {than[:200]!r}")
        ghi("đã thêm bộ ánh xạ vai trò realm → claim nhóm")


# ---------------------------------------------------------------------------
# Bước 2 — sau Wiki.js
# ---------------------------------------------------------------------------


class Wiki:
    def __init__(self) -> None:
        self.goc = bien("WIKI_INTERNAL_URL").rstrip("/")
        self.jwt: str | None = None

    def graphql(self, truy_van: str, bien_so: dict | None = None, token: str | None = None) -> dict:
        ma, than = goi(
            f"{self.goc}/graphql",
            phuong_thuc="POST",
            json_than={"query": truy_van, "variables": bien_so or {}},
            token=token or self.jwt,
            thoi_han=30,
        )
        if ma != 200:
            raise RuntimeError(f"GraphQL trả {ma}")
        ket_qua = json.loads(than)
        if ket_qua.get("errors"):
            raise RuntimeError(f"GraphQL báo lỗi: {ket_qua['errors']}")
        return ket_qua["data"]

    def dang_cai_dat(self) -> bool:
        """Trang cài đặt lần đầu chỉ có GET và POST /finalize — /graphql chưa tồn tại."""
        ma, _ = goi(f"{self.goc}/graphql", phuong_thuc="POST", json_than={"query": "{ __typename }"})
        return ma != 200


def kiem_ket_qua(phan_hoi: dict, viec: str) -> None:
    kq = phan_hoi.get("responseResult") or {}
    if not kq.get("succeeded"):
        sys.exit(f"{viec} thất bại: {kq.get('message')}")


def hoan_tat_cai_dat(w: Wiki) -> None:
    cho("Wiki.js trả lời", lambda: goi(f"{w.goc}/", thoi_han=5)[0] or None)
    if not w.dang_cai_dat():
        ghi("Wiki.js đã cài đặt từ trước")
        return
    mat_khau = bien("WIKI_ADMIN_PASSWORD")
    ma, than = goi(
        f"{w.goc}/finalize",
        phuong_thuc="POST",
        json_than={
            "adminEmail": bien("WIKI_ADMIN_EMAIL"),
            "adminPassword": mat_khau,
            "adminPasswordConfirm": mat_khau,
            "siteUrl": bien("WIKI_PUBLIC_URL").rstrip("/"),
            # Không gửi thống kê sử dụng ra ngoài, như SeaweedFS (-master.telemetry=false)
            "telemetry": False,
        },
        thoi_han=120,
    )
    if ma != 200 or not json.loads(than).get("ok"):
        sys.exit(f"Hoàn tất cài đặt Wiki.js thất bại: {ma} {than[:300]!r}")
    ghi("đã hoàn tất cài đặt lần đầu, chờ Wiki.js khởi động lại")
    cho("Wiki.js chạy ở chế độ thường", lambda: (not w.dang_cai_dat()) or None)


def dang_nhap(w: Wiki) -> None:
    def thu():
        d = w.graphql(
            """mutation($u: String!, $p: String!) { authentication { login(username: $u, password: $p,
               strategy: "local") { responseResult { succeeded message } jwt } } }""",
            {"u": bien("WIKI_ADMIN_EMAIL"), "p": bien("WIKI_ADMIN_PASSWORD")},
        )["authentication"]["login"]
        return d["jwt"] if d["responseResult"]["succeeded"] else None

    w.jwt = cho("đăng nhập quản trị Wiki.js", thu)


QUYEN_DOC = ["read:pages", "read:assets", "read:comments", "write:comments"]
QUYEN_VIET = QUYEN_DOC + [
    "write:pages", "manage:pages", "delete:pages", "read:source", "read:history", "write:assets", "manage:assets",
]


def dam_bao_nhom(w: Wiki) -> dict[str, int]:
    """Mỗi vai trò realm một nhóm Wiki.js cùng tên. Wiki.js gán người dùng vào nhóm có TÊN trùng giá trị
    trong claim nhóm (`mapGroups`), nên tên nhóm chính là mã vai trò — bảng vai đọc/viết nằm ở cấu hình."""
    doc = danh_sach("WIKI_READ_ROLES")
    viet = set(danh_sach("WIKI_WRITE_ROLES"))
    nhom_api = bien("WIKI_API_GROUP")
    co_san = {g["name"]: g["id"] for g in w.graphql("{ groups { list { id name } } }")["groups"]["list"]}

    can = {ten: (QUYEN_VIET if ten in viet else QUYEN_DOC) for ten in [*doc, *viet]}
    can[nhom_api] = ["read:pages", "read:source"]
    for ten, quyen in can.items():
        if ten not in co_san:
            d = w.graphql(
                "mutation($n: String!) { groups { create(name: $n) { responseResult { succeeded message } group { id } } } }",
                {"n": ten},
            )["groups"]["create"]
            kiem_ket_qua(d, f"tạo nhóm {ten}")
            co_san[ten] = d["group"]["id"]
        d = w.graphql(
            """mutation($id: Int!, $n: String!, $q: [String]!, $r: [PageRuleInput]!) { groups { update(id: $id,
               name: $n, redirectOnLogin: "/", permissions: $q, pageRules: $r) { responseResult { succeeded message } } } }""",
            {
                "id": co_san[ten],
                "n": ten,
                "q": quyen,
                "r": [{"id": "toan-bo", "deny": False, "match": "START", "roles": quyen, "path": "", "locales": []}],
            },
        )["groups"]["update"]
        kiem_ket_qua(d, f"đặt quyền nhóm {ten}")
    ghi(f"nhóm: {len(doc)} vai đọc, {len(viet)} vai viết, 1 nhóm cho khóa API")
    return co_san


def cau_hinh_dang_nhap(w: Wiki) -> None:
    """Đăng nhập một lần qua Keycloak. Gửi kèm chiến lược `local`: Wiki.js xóa mọi chiến lược không có
    trong danh sách, mà tài khoản quản trị wiki đăng nhập bằng nó. `local` tắt tự đăng ký."""
    kc_cong_khai = bien("KEYCLOAK_PUBLIC_URL").rstrip("/")
    kc_noi_bo = bien("KEYCLOAK_INTERNAL_URL").rstrip("/")
    realm = bien("KEYCLOAK_REALM")
    duong = f"realms/{realm}/protocol/openid-connect"
    cau_hinh = {
        "clientId": bien("WIKI_OIDC_CLIENT_ID"),
        "clientSecret": bien("WIKI_OIDC_SECRET"),
        # Trình duyệt mở địa chỉ công khai; Wiki.js gọi token và userinfo trong mạng Compose. Keycloak
        # cố định địa chỉ công khai (KC_HOSTNAME) nên token mang iss công khai ở cả hai đường.
        "authorizationURL": f"{kc_cong_khai}/{duong}/auth",
        "tokenURL": f"{kc_noi_bo}/{duong}/token",
        "userInfoURL": f"{kc_noi_bo}/{duong}/userinfo",
        "skipUserProfile": False,
        "issuer": f"{kc_cong_khai}/realms/{realm}",
        "emailClaim": "email",
        "displayNameClaim": "name",
        "pictureClaim": "picture",
        "mapGroups": True,
        "groupsClaim": bien("WIKI_GROUPS_CLAIM"),
        "logoutURL": f"{kc_cong_khai}/{duong}/logout",
        "acrValues": "",
    }
    chien_luoc = [
        {
            "key": bien("WIKI_STRATEGY_KEY"),
            "strategyKey": "oidc",
            "displayName": "Tài khoản công ty",
            "order": 0,
            "isEnabled": True,
            "selfRegistration": True,
            "domainWhitelist": [],
            "autoEnrollGroups": [],
            "config": [{"key": k, "value": json.dumps({"v": v})} for k, v in cau_hinh.items()],
        },
        {
            "key": "local",
            "strategyKey": "local",
            "displayName": "Tài khoản quản trị kho tri thức",
            "order": 1,
            "isEnabled": True,
            "selfRegistration": False,
            "domainWhitelist": [],
            "autoEnrollGroups": [],
            "config": [],
        },
    ]
    d = w.graphql(
        """mutation($s: [AuthenticationStrategyInput]!) { authentication { updateStrategies(strategies: $s) {
           responseResult { succeeded message } } } }""",
        {"s": chien_luoc},
    )["authentication"]["updateStrategies"]
    kiem_ket_qua(d, "cấu hình đăng nhập một lần")
    ghi("đã cấu hình đăng nhập một lần qua Keycloak")


def dam_bao_khoa_api(w: Wiki, nhom: dict[str, int]) -> None:
    """Khóa API chỉ đọc cho dịch vụ ứng dụng, ghi vào volume chung. Khóa cũ còn dùng được thì giữ."""
    tep = Path(bien("WIKI_API_KEY_FILE"))
    ten_khoa = "dx-os-lab"
    if tep.exists():
        try:
            w.graphql("{ pages { list(limit: 1) { id } } }", token=tep.read_text(encoding="utf-8").strip())
            ghi("khóa API cũ còn dùng được")
            return
        except RuntimeError:
            ghi("khóa API cũ không còn dùng được, cấp khóa mới")
    d = w.graphql("mutation { authentication { setApiState(enabled: true) { responseResult { succeeded message } } } }")
    kiem_ket_qua(d["authentication"]["setApiState"], "bật truy cập API")
    for k in w.graphql("{ authentication { apiKeys { id name isRevoked } } }")["authentication"]["apiKeys"]:
        if k["name"] == ten_khoa and not k["isRevoked"]:
            w.graphql("mutation($id: Int!) { authentication { revokeApiKey(id: $id) { responseResult { succeeded } } } }",
                      {"id": k["id"]})
    d = w.graphql(
        """mutation($n: String!, $g: Int!) { authentication { createApiKey(name: $n, expiration: "2y",
           fullAccess: false, group: $g) { responseResult { succeeded message } key } } }""",
        {"n": ten_khoa, "g": nhom[bien("WIKI_API_GROUP")]},
    )["authentication"]["createApiKey"]
    kiem_ket_qua(d, "cấp khóa API")
    tep.parent.mkdir(parents=True, exist_ok=True)
    tep.write_text(d["key"], encoding="utf-8")
    # Dịch vụ ứng dụng chạy bằng người dùng thường, chỉ cần đọc
    tep.chmod(0o644)
    ghi("đã cấp khóa API chỉ đọc")


def ngon_ngu(w: Wiki) -> str:
    """Giao diện tiếng Việt nếu tải được gói ngôn ngữ (cần mạng ra ngoài); không được thì giữ tiếng Anh —
    nội dung bài vẫn tiếng Việt có dấu. Trả về mã ngôn ngữ đang dùng cho trang."""
    muon = bien("WIKI_LOCALE")
    hien = w.graphql("{ localization { config { locale } } }")["localization"]["config"]["locale"]
    if hien == muon:
        return hien
    try:
        d = w.graphql("mutation($l: String!) { localization { downloadLocale(locale: $l) { responseResult { succeeded message } } } }",
                      {"l": muon})["localization"]["downloadLocale"]
        if not d["responseResult"]["succeeded"]:
            raise RuntimeError(d["responseResult"]["message"])
        d = w.graphql(
            """mutation($l: String!) { localization { updateLocale(locale: $l, autoUpdate: false, namespacing: false,
               namespaces: []) { responseResult { succeeded message } } } }""",
            {"l": muon},
        )["localization"]["updateLocale"]
        kiem_ket_qua(d, "đổi ngôn ngữ giao diện")
        ghi(f"giao diện: {muon}")
        return muon
    except RuntimeError as loi:
        ghi(f"không tải được gói ngôn ngữ {muon} ({loi}); giữ {hien}")
        return hien


def doc_bai(tep: Path) -> tuple[dict, str]:
    """Bài mẫu: khối đầu `---` gồm các dòng `khóa: giá trị`, rồi nội dung Markdown."""
    chu = tep.read_text(encoding="utf-8")
    _, dau, than = chu.split("---", 2)
    meta = {}
    for dong in dau.strip().splitlines():
        khoa, _, gia_tri = dong.partition(":")
        meta[khoa.strip()] = gia_tri.strip()
    return meta, than.strip() + "\n"


def nap_bai_mau(w: Wiki, locale: str) -> None:
    """Bài hướng dẫn mẫu — DỮ LIỆU trong infra/tri-thuc/bai-mau/. Bài đã có (cùng đường dẫn) thì để yên:
    người dùng có thể đã sửa nó trên wiki."""
    so_tao = 0
    for tep in sorted(Path(bien("WIKI_SEED_DIR")).glob("*.md")):
        meta, noi_dung = doc_bai(tep)
        try:
            w.graphql("query($p: String!, $l: String!) { pages { singleByPath(path: $p, locale: $l) { id } } }",
                      {"p": meta["duong-dan"], "l": locale})
            continue
        except RuntimeError:
            pass  # chưa có bài ở đường dẫn này
        d = w.graphql(
            """mutation($c: String!, $d: String!, $l: String!, $p: String!, $t: [String]!, $ti: String!) { pages {
               create(content: $c, description: $d, editor: "markdown", isPublished: true, isPrivate: false,
               locale: $l, path: $p, tags: $t, title: $ti) { responseResult { succeeded message } } } }""",
            {
                "c": noi_dung,
                "d": meta.get("mo-ta", ""),
                "l": locale,
                "p": meta["duong-dan"],
                "t": [x.strip() for x in meta.get("the", "").split(",") if x.strip()],
                "ti": meta["tieu-de"],
            },
        )["pages"]["create"]
        kiem_ket_qua(d, f"tạo bài {meta['duong-dan']}")
        so_tao += 1
    ghi(f"bài mẫu: tạo mới {so_tao}")


def khoi_tao() -> None:
    w = Wiki()
    hoan_tat_cai_dat(w)
    dang_nhap(w)
    # Tự đăng nhập: /login chuyển thẳng sang chiến lược đầu tiên (Keycloak), nên liên kết tới một bài mở được
    # ngay — người chưa đăng nhập wiki đi qua Keycloak rồi quay về đúng bài. Quản trị wiki vào /login?all=1
    d = w.graphql(
        """mutation($t: String!) { site { updateConfig(title: $t, authAutoLogin: true) {
           responseResult { succeeded message } } } }""",
        {"t": bien("WIKI_SITE_TITLE")},
    )["site"]["updateConfig"]
    kiem_ket_qua(d, "đặt tiêu đề và tự đăng nhập")
    locale = ngon_ngu(w)
    nhom = dam_bao_nhom(w)
    cau_hinh_dang_nhap(w)
    dam_bao_khoa_api(w, nhom)
    nap_bai_mau(w, locale)
    ghi("xong")


def main() -> None:
    viec = sys.argv[1] if len(sys.argv) > 1 else ""
    if viec == "chuan-bi":
        tao_csdl()
        dam_bao_client()
        ghi("xong")
    elif viec == "khoi-tao":
        khoi_tao()
    else:
        sys.exit("Dùng: khoi_tao.py chuan-bi | khoi-tao")


if __name__ == "__main__":
    main()
