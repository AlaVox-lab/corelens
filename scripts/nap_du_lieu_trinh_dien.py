# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Nạp dữ liệu trình diễn vào cụm đang chạy (#306): vài trăm hồ sơ trải vài tháng, để bảng điều
# khiển phân tích (#304) có số mà xem.
#
# CHỈ DÙNG CHO CỤM THỬ VÀ BUỔI TRÌNH DIỄN. Hồ sơ nạp vào là hồ sơ giả, và không gỡ ra được: nhật
# ký sự kiện chỉ ghi thêm, trigger chặn mọi lệnh xóa. Muốn sạch lại thì `down -v` cả cụm.
#
# Kịch bản lấy từ bộ sinh nhật ký ảo (scripts/sinh_nhat_ky_ao.py, #124): đi đúng cạnh, đúng vai
# trò, đúng luật quay về chỗ cũ của bộ quy tắc ĐANG BẬT, đọc thẳng từ cơ sở dữ liệu. Bộ sinh tự
# kiểm mọi sự kiện trước khi lệnh này ghi gì vào cơ sở dữ liệu.
#
# Lịch sử lùi về quá khứ mà nhật ký vẫn chỉ ghi thêm: lệnh chỉ chạy INSERT — hồ sơ mang sẵn
# trạng thái cuối, nhật ký mang sẵn mốc thời gian cũ — không UPDATE hay DELETE dòng nhật ký
# nào. Đây là lối ghi duy nhất ngoài engine (`perform_transition`), và nó là nhập lịch sử đã
# kiểm chứ không phải chuyển trạng thái: engine không ghi được mốc trong quá khứ.
#
# Thời gian: bộ sinh đếm giây trên một đồng hồ riêng; lệnh này coi đồng hồ đó là GIÂY LÀM VIỆC
# và đổi sang giờ thật bằng `moc_sau_giay_lam_viec` của cơ sở dữ liệu. Nhờ vậy sự kiện rơi vào
# giờ hành chính, đồng hồ hạn của hồ sơ đúng bằng cách hệ thống tự đo, và mỗi hồ sơ chỉ được
# mô phỏng tới lượng giờ làm việc còn lại tới hiện tại — không sự kiện nào nằm ở tương lai.
#
# Giới hạn đã biết: kịch bản chưa mô phỏng hệ số hạn theo mức ưu tiên (#101) — hồ sơ khẩn cấp
# trong dữ liệu trình diễn leo thang theo hạn chuẩn của loại.
#
# Cách dùng, ở gốc kho mã, khi cụm đang chạy:
#
#     python scripts/nap_du_lieu_trinh_dien.py --xac-nhan
#     python scripts/nap_du_lieu_trinh_dien.py --xac-nhan --so-ho-so 800 --so-ngay 90
#
# Chỉ cần Python 3.10 trở lên và lệnh `docker`.
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sinh_nhat_ky_ao import KICH_BAN_MAC_DINH, BoSinh, doc_quy_tac_tu_cum, tu_kiem  # noqa: E402

TIEN_TO = "[Mẫu]"
# Kịch bản của bộ sinh, chỉnh một hệ số cho dữ liệu trình diễn. Hạn tính theo mức ưu tiên (khẩn
# chỉ còn nửa hạn) và một hồ sơ có thể chạy đồng hồ nhiều đoạn — leo thang, làm lại — nên hệ số
# 0,55 của khảo sát cho gần 28 % hồ sơ trễ hạn; 0,45 cho khoảng 20 %, đo trên 600 hồ sơ.
KICH_BAN = {**KICH_BAN_MAC_DINH, "he_so_xu_ly_theo_sla": 0.45}
# Gốc của đồng hồ riêng của bộ sinh — một mốc bất kỳ, chỉ dùng để lấy độ lệch
GOC_AO = datetime(2000, 1, 3, tzinfo=timezone.utc)


def psql(ts: argparse.Namespace, cau: str, vao: str | None = None) -> str:
    lenh = ["docker", "exec", "-i", ts.container, "psql", "-U", ts.nguoi_dung, "-d", ts.csdl,
            "-At", "-q", "-v", "ON_ERROR_STOP=1", "-1", "-c", cau] if vao is None else [
            "docker", "exec", "-i", ts.container, "psql", "-U", ts.nguoi_dung, "-d", ts.csdl,
            "-At", "-q", "-v", "ON_ERROR_STOP=1", "-1", "-f", "-"]
    kq = subprocess.run(lenh, input=(vao or "").encode("utf-8"), capture_output=True, check=False)
    if kq.returncode != 0:
        sys.exit(f"Lệnh SQL thất bại, không có gì được ghi:\n{kq.stderr.decode('utf-8', 'replace')}")
    return kq.stdout.decode("utf-8").strip()


def mang(so: list[int]) -> str:
    return "ARRAY[" + ",".join(str(int(x)) for x in so) + "]::bigint[]"


def copy_khoi(bang: str, cot: list[str], dong: list[list]) -> str:
    bo_dem = io.StringIO()
    csv.writer(bo_dem, lineterminator="\n").writerows(dong)
    return f"COPY {bang} ({', '.join(cot)}) FROM STDIN WITH (FORMAT csv);\n{bo_dem.getvalue()}\\.\n"


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="Nạp dữ liệu trình diễn vào cụm đang chạy.")
    p.add_argument("--xac-nhan", action="store_true",
                   help="Bắt buộc: xác nhận đây là cụm thử hay cụm trình diễn")
    p.add_argument("--so-ho-so", type=int, default=600)
    p.add_argument("--so-ngay", type=int, default=90, help="Hồ sơ gửi rải trong chừng này ngày tới nay")
    p.add_argument("--hat-giong", type=int, default=20261102)
    p.add_argument("--cho-tron", action="store_true",
                   help="Cho nạp cả khi cụm đã có hồ sơ thật (không phải hồ sơ mẫu)")
    p.add_argument("--container", default="dxlab-postgres")
    p.add_argument("--nguoi-dung", default="dxlab")
    p.add_argument("--csdl", default="dxlab")
    ts = p.parse_args()

    if not ts.xac_nhan:
        sys.exit("Lệnh này ghi hồ sơ GIẢ vào cụm và không gỡ ra được (chỉ `down -v`).\n"
                 "Chỉ chạy trên cụm thử hay cụm trình diễn, kèm --xac-nhan.")
    that = int(psql(ts, f"SELECT count(*) FROM requests WHERE title NOT LIKE '{TIEN_TO}%'"))
    if that and not ts.cho_tron:
        sys.exit(f"Cụm đã có {that} hồ sơ không phải hồ sơ mẫu — có thể đây là môi trường thật. "
                 "Dừng. Chắc chắn là cụm thử thì chạy lại kèm --cho-tron.")

    quy_tac = doc_quy_tac_tu_cum(ts.container, ts.nguoi_dung, ts.csdl)
    nhan_loai = dict(
        l.split("\t") for l in psql(ts, "SELECT code || E'\\t' || label FROM request_types").splitlines()
    )
    bo = BoSinh(quy_tac, json.loads(json.dumps(KICH_BAN)), ts.hat_giong)
    rng = random.Random(ts.hat_giong)

    # Lúc gửi: rải đều trên GIỜ LÀM VIỆC của khoảng ngày, nên không ai gửi lúc nửa đêm Chủ nhật
    bat_dau = f"now() - interval '{int(ts.so_ngay)} days'"
    tong = int(psql(ts, f"SELECT so_giay_lam_viec({bat_dau}, now())"))
    if tong <= 0:
        sys.exit("Lịch làm việc mặc định không có giờ làm nào trong khoảng ngày đã chọn.")
    lech = sorted(rng.randrange(tong) for _ in range(ts.so_ho_so))
    moc = psql(ts, f"""
        SELECT to_char(m AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') || E'\\t' ||
               so_giay_lam_viec(m, now())
        FROM unnest({mang(lech)}) WITH ORDINALITY AS u(o, i),
             LATERAL (SELECT moc_sau_giay_lam_viec({bat_dau}, u.o) AS m) x
        ORDER BY u.i
    """).splitlines()

    ho_so, su_kien = [], []
    for ma, dong in enumerate(moc, start=1):
        _, con_lai = dong.split("\t")
        hs, ds = bo.sinh_ho_so(ma, GOC_AO, GOC_AO + timedelta(seconds=int(con_lai)))
        ho_so.append(hs)
        su_kien.extend(ds)
    loi = tu_kiem(bo, ho_so, su_kien)
    if loi:
        print(f"Bộ sinh tự kiểm thấy {len(loi)} lỗi — không nạp gì:")
        for d in loi[:20]:
            print(f"  {d}")
        return 1

    def giay(luc: datetime | None) -> str:
        return "" if luc is None else str(int((luc - GOC_AO).total_seconds()))

    dong_ho_so = []
    for hs, dong in zip(ho_so, moc):
        tao, _ = dong.split("\t")
        loai = nhan_loai.get(hs.loai or "", "Yêu cầu")
        dong_ho_so.append([
            hs.ma, tao + "+00", hs.trang_thai, f"{TIEN_TO} {loai} — hồ sơ trình diễn số {hs.ma}",
            hs.mo_ta, hs.nguoi_gui, f"Người gửi mẫu {hs.nguoi_gui.rsplit('-', 1)[-1]}",
            hs.loai or "", hs.phong or "", hs.uu_tien or "", hs.nguoi_xu_ly or "",
            int(hs.chay_giay), int(hs.dung_giay), giay(hs.doan_mo_tu),
        ])
    dong_su_kien = [
        [e["case_id"], i, e["activity"], giay(e["timestamp"]), e["actor"], e["actor_label"],
         e["from_state"], e["to_state"], e["note"], e["changes"]]
        for i, e in enumerate(su_kien)
    ]

    sql = (
        "CREATE TEMP TABLE nap_ho_so (ma int, tao timestamptz, trang_thai text, tieu_de text, mo_ta text, "
        "nguoi_gui text, nhan_nguoi_gui text, loai text, phong text, uu_tien text, nguoi_xu_ly text, "
        "chay bigint, dung bigint, doan_lech bigint);\n"
        "CREATE TEMP TABLE nap_su_kien (ma int, thu_tu int, hoat_dong text, lech bigint, tac_nhan text, "
        "nhan_tac_nhan text, tu text, den text, ghi_chu text, thay_doi text);\n"
        + copy_khoi("nap_ho_so", ["ma", "tao", "trang_thai", "tieu_de", "mo_ta", "nguoi_gui",
                                  "nhan_nguoi_gui", "loai", "phong", "uu_tien", "nguoi_xu_ly",
                                  "chay", "dung", "doan_lech"], dong_ho_so)
        + copy_khoi("nap_su_kien", ["ma", "thu_tu", "hoat_dong", "lech", "tac_nhan", "nhan_tac_nhan",
                                    "tu", "den", "ghi_chu", "thay_doi"], dong_su_kien)
        + """
        CREATE TEMP TABLE nap_ma (ma int, id bigint);
        WITH moi AS (
            INSERT INTO requests (rule_set_id, current_state, title, description, requester_id,
                requester_label, request_type_code, department_code, priority_code, assignee_id,
                assignee_label, sla_running_seconds, sla_paused_seconds, sla_segment_since,
                created_at, updated_at)
            SELECT (SELECT id FROM rule_sets WHERE is_active), h.trang_thai, h.tieu_de, h.mo_ta,
                   h.nguoi_gui, h.nhan_nguoi_gui, nullif(h.loai, ''), nullif(h.phong, ''),
                   nullif(h.uu_tien, ''), nullif(h.nguoi_xu_ly, ''), nullif(h.nguoi_xu_ly, ''),
                   h.chay, h.dung,
                   CASE WHEN h.doan_lech IS NOT NULL THEN moc_sau_giay_lam_viec(h.tao, h.doan_lech) END,
                   h.tao, h.tao
            FROM nap_ho_so h ORDER BY h.ma
            RETURNING id, title
        )
        INSERT INTO nap_ma SELECT h.ma, moi.id FROM moi JOIN nap_ho_so h ON h.tieu_de = moi.title;

        INSERT INTO event_log (case_id, activity, timestamp, actor, actor_label, from_state,
            to_state, note, changes)
        SELECT m.id, s.hoat_dong, moc_sau_giay_lam_viec(h.tao, s.lech), s.tac_nhan,
               s.nhan_tac_nhan, s.tu, s.den, nullif(s.ghi_chu, ''), nullif(s.thay_doi, '')::jsonb
        FROM nap_su_kien s JOIN nap_ma m USING (ma) JOIN nap_ho_so h USING (ma)
        ORDER BY s.ma, s.thu_tu;

        -- Mốc sửa gần nhất và số lần mở lại theo nhật ký vừa ghi (ràng buộc reopen-limit đọc nó)
        UPDATE requests r SET updated_at = coalesce(e.luc, r.created_at),
               reopen_count = coalesce(e.mo_lai, 0)
        FROM nap_ma m
        LEFT JOIN (
            SELECT l.case_id, max(l.timestamp) AS luc,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM transitions t JOIN transition_guards g ON g.transition_id = t.id
                       WHERE t.rule_set_id = (SELECT id FROM rule_sets WHERE is_active)
                         AND t.from_state = l.from_state AND t.to_state = l.to_state
                         AND g.guard_code = 'reopen-limit')) AS mo_lai
            FROM event_log l GROUP BY l.case_id
        ) e ON e.case_id = m.id
        WHERE r.id = m.id;

        SELECT count(*) || ' hồ sơ, ' || (SELECT count(*) FROM event_log WHERE case_id IN
               (SELECT id FROM nap_ma)) || ' sự kiện' FROM nap_ma;
        """
    )
    print(f"Đã nạp {psql(ts, '', vao=sql)} — gửi rải trong {ts.so_ngay} ngày tới nay.")
    print(psql(ts, f"""
        SELECT 'Tỷ lệ vi phạm hạn ' || coalesce(round(100.0 * count(*) FILTER (WHERE vi_pham)
               / nullif(count(*), 0), 1)::text, '—') || ' % trên ' || count(*) || ' hồ sơ đã xong'
        FROM bao_cao_ho_so
        WHERE da_ket_thuc AND da_qua_phong_ban AND ma_ho_so IN
              (SELECT id FROM requests WHERE title LIKE '{TIEN_TO}%')
    """))
    return 0


if __name__ == "__main__":
    sys.exit(main())
