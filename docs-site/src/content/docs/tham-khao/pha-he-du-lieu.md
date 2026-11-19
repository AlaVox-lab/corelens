---
title: Phả hệ dữ liệu
description: Mỗi biểu đồ của bảng điều khiển lấy số từ view nào và bảng nguồn nào; nguồn gốc nhật ký sự kiện.
sidebar:
  order: 3
---

<!-- Tệp SINH TỰ ĐỘNG bởi scripts/pha_he.py từ định nghĩa view (backend/alembic/versions/) và bảng điều
     khiển (infra/superset/bang-dieu-khien/). Đừng sửa tay: sửa định nghĩa rồi chạy python scripts/pha_he.py.
     Tích hợp liên tục chạy --kiem và báo đỏ khi trang này lệch với định nghĩa. -->

Nguyên lý (iii) của đề thi: kiểm soát phả hệ, nguồn gốc và chất lượng thông tin trên báo cáo tổng hợp.
Trang này trả lời câu hỏi *con số trên biểu đồ này lấy từ đâu*: biểu đồ → bộ dữ liệu → view báo cáo →
bảng nguồn, cùng các cột được dùng ở mỗi chặng. Mọi dòng dưới đây sinh từ chính định nghĩa trong kho —
định nghĩa view cuối cùng sau mọi bản sửa Alembic, và tệp YAML của bảng điều khiển Superset.

## Biểu đồ → bộ dữ liệu → view → bảng nguồn

Bảng điều khiển **Vận hành yêu cầu** (`van-hanh-yeu-cau`), 8 biểu đồ, theo thứ tự trên lưới.

| Biểu đồ | Bộ dữ liệu · cột dùng | View đọc qua | Bảng nguồn |
|---|---|---|---|
| Tồn đọng theo phòng ban (hồ sơ đang mở) | `bao_cao_ton_dong` · `phong_ban`, `so_ho_so`, `trang_thai` | `bao_cao_ton_dong` → `bao_cao_ho_so` | `departments`, `event_log`, `priorities`, `processes`, `request_types`, `requests`, `rule_sets`, `states` |
| Thời gian xử lý trung vị theo loại yêu cầu (giờ làm việc) | `bao_cao_ho_so` · `da_ket_thuc`, `da_qua_phong_ban`, `gio_dong_ho`, `gio_nguong`, `gio_xu_ly`, `loai_yeu_cau` | `bao_cao_ho_so` | `departments`, `event_log`, `priorities`, `processes`, `request_types`, `requests`, `rule_sets`, `states` |
| Tỷ lệ vi phạm hạn theo phòng ban (% hồ sơ đã xong) | `bao_cao_vi_pham` · `phong_ban`, `so_ho_so`, `so_vi_pham` | `bao_cao_vi_pham` → `bao_cao_ho_so` | `departments`, `event_log`, `priorities`, `processes`, `request_types`, `requests`, `rule_sets`, `states` |
| Phân bố loại yêu cầu theo tuần | `bao_cao_phan_bo_loai` · `loai_yeu_cau`, `so_ho_so`, `tuan` | `bao_cao_phan_bo_loai` → `bao_cao_ho_so` | `departments`, `event_log`, `priorities`, `processes`, `request_types`, `requests`, `rule_sets`, `states`, `work_calendars` |
| Tỷ lệ ghi đè gợi ý của hệ thống (% lượt người xác nhận chọn khác) | `bao_cao_goi_y` · `nguon`, `so_ghi_de`, `truong` | `bao_cao_goi_y` | `departments`, `event_log`, `requests`, `transitions` |
| Tỷ lệ yêu cầu được ngăn chặn nhờ gợi ý hồ sơ tương tự (%) | `bao_cao_ngan_chan` · `so_da_ket_thuc`, `so_ngan_chan` | `bao_cao_ngan_chan` | `departments`, `requests`, `similar_case_views` |
| Tỷ lệ vi phạm hạn theo loại yêu cầu (% hồ sơ đã xong) | `bao_cao_vi_pham` · `loai_yeu_cau`, `so_ho_so`, `so_vi_pham` | `bao_cao_vi_pham` → `bao_cao_ho_so` | `departments`, `event_log`, `priorities`, `processes`, `request_types`, `requests`, `rule_sets`, `states` |
| Tỷ lệ ghi đè gợi ý theo tuần (%) | `bao_cao_goi_y` · `luc`, `nguon`, `so_ghi_de`, `truong` | `bao_cao_goi_y` | `departments`, `event_log`, `requests`, `transitions` |

*Cột dùng* là cột của bộ dữ liệu xuất hiện trong trục, nhóm, chỉ số hay bộ lọc của biểu đồ; cột tính của
bộ dữ liệu được thay bằng các cột vật lý trong biểu thức của nó. *Bảng nguồn* gộp mọi bảng mà các view
trên đường đi đọc; cột của từng bảng ở mục *View báo cáo*.

## Sơ đồ

Sơ đồ mermaid của cùng phả hệ nằm trong bản ở kho mã: `docs/pha-he-du-lieu.md` (GitHub vẽ sơ đồ trực
tiếp khi xem tệp).

## View báo cáo

Mỗi view một dòng: bản sửa Alembic chứa định nghĩa đang có hiệu lực, quan hệ đọc trực tiếp, bảng nguồn
rốt cuộc kèm các cột được tham chiếu qua bí danh trong câu SQL (gộp qua mọi view trung gian), và các cột
view trả ra.

| View | Định nghĩa ở | Đọc trực tiếp | Bảng nguồn rốt cuộc (cột tham chiếu) | Cột ra |
|---|---|---|---|---|
| `bao_cao_goi_y` | `0021_goi_y_nguoi_xu_ly.py` | `departments`, `event_log`, `requests`, `transitions` | `departments` (code, label)<br>`event_log` (activity, case_id, from_state, id, suggestion, timestamp, to_state)<br>`requests` (department_code, id, rule_set_id)<br>`transitions` (activity_label, from_state, is_system, rule_set_id, to_state) | ma_su_kien, ma_ho_so, luc, ma_hoat_dong, hoat_dong, ma_truong, truong, ma_nguon, nguon, gia_tri_goi_y, gia_tri_chon, ghi_de, so_ghi_de, do_tin_cay, ma_phong, phong_ban |
| `bao_cao_ho_so` | `0028_nhieu_quy_trinh.py` | `departments`, `event_log`, `priorities`, `processes`, `request_types`, `requests`, `rule_sets`, `states` | `departments` (code, label)<br>`event_log` (case_id, to_state)<br>`priorities` (code, label, sla_factor_percent)<br>`processes` (code, is_app_default)<br>`request_types` (code, label, sla_hours)<br>`requests` (created_at, current_state, department_code, id, priority_code, request_type_code, rule_set_id, sla_extension_total_hours, sla_running_seconds)<br>`rule_sets` (id, process_code)<br>`states` (code, is_terminal, label, rule_set_id, sla_running) | ma_ho_so, bo_quy_tac, ma_loai, loai_yeu_cau, ma_phong, phong_ban, ma_uu_tien, muc_uu_tien, ma_trang_thai, trang_thai, da_ket_thuc, da_qua_phong_ban, luc_gui, luc_ket_thuc, gio_xu_ly, gio_nguong, gio_dong_ho, vi_pham, ma_quy_trinh |
| `bao_cao_ngan_chan` | `0022_ho_so_tuong_tu.py` | `departments`, `requests`, `similar_case_views` | `departments` (code, label)<br>`requests` (department_code, id)<br>`similar_case_views` (abandon_reason, abandoned_at, session_id, submitted_case_id, suggested_case_ids, top_case_id, viewed_at) | ma_phien, luc_xem, tuan, ket_qua, so_ngan_chan, so_da_ket_thuc, ly_do_bo, so_goi_y, ma_phong, phong_ban |
| `bao_cao_nhat_ky` | `0028_nhieu_quy_trinh.py` | `event_log`, `requests`, `rule_sets`, `states` | `event_log` (activity, actor, case_id, from_state, id, timestamp, to_state)<br>`requests` (created_at, department_code, id, priority_code, request_type_code, requester_id, rule_set_id)<br>`rule_sets` (id, process_code)<br>`states` (code, is_initial, rule_set_id) | case_id, activity, timestamp, actor, from_state, to_state, request_type_code, department_code, priority_code, rule_set_id, thu_tu, process_code |
| `bao_cao_phan_bo_loai` | `0014_lop_bao_cao.py` | `bao_cao_ho_so`, `work_calendars` | `departments` (code, label)<br>`event_log` (case_id, to_state)<br>`priorities` (code, label, sla_factor_percent)<br>`processes` (code, is_app_default)<br>`request_types` (code, label, sla_hours)<br>`requests` (created_at, current_state, department_code, id, priority_code, request_type_code, rule_set_id, sla_extension_total_hours, sla_running_seconds)<br>`rule_sets` (id, process_code)<br>`states` (code, is_terminal, label, rule_set_id, sla_running)<br>`work_calendars` (—) | tuan, ma_phong, phong_ban, ma_loai, loai_yeu_cau, so_ho_so |
| `bao_cao_thoi_gian_xu_ly` | `0014_lop_bao_cao.py` | `bao_cao_ho_so`, `request_types` | `departments` (code, label)<br>`event_log` (case_id, to_state)<br>`priorities` (code, label, sla_factor_percent)<br>`processes` (code, is_app_default)<br>`request_types` (code, label, sla_hours)<br>`requests` (created_at, current_state, department_code, id, priority_code, request_type_code, rule_set_id, sla_extension_total_hours, sla_running_seconds)<br>`rule_sets` (id, process_code)<br>`states` (code, is_terminal, label, rule_set_id, sla_running) | ma_loai, loai_yeu_cau, gio_han_chuan, so_ho_so, gio_xu_ly_trung_vi, so_vi_pham, ty_le_vi_pham |
| `bao_cao_ton_dong` | `0014_lop_bao_cao.py` | `bao_cao_ho_so` | `departments` (code, label)<br>`event_log` (case_id, to_state)<br>`priorities` (code, label, sla_factor_percent)<br>`processes` (code, is_app_default)<br>`request_types` (code, label, sla_hours)<br>`requests` (created_at, current_state, department_code, id, priority_code, request_type_code, rule_set_id, sla_extension_total_hours, sla_running_seconds)<br>`rule_sets` (id, process_code)<br>`states` (code, is_terminal, label, rule_set_id, sla_running) | ma_phong, phong_ban, ma_trang_thai, trang_thai, so_ho_so |
| `bao_cao_vi_pham` | `0014_lop_bao_cao.py` | `bao_cao_ho_so` | `departments` (code, label)<br>`event_log` (case_id, to_state)<br>`priorities` (code, label, sla_factor_percent)<br>`processes` (code, is_app_default)<br>`request_types` (code, label, sla_hours)<br>`requests` (created_at, current_state, department_code, id, priority_code, request_type_code, rule_set_id, sla_extension_total_hours, sla_running_seconds)<br>`rule_sets` (id, process_code)<br>`states` (code, is_terminal, label, rule_set_id, sla_running) | ma_phong, phong_ban, ma_loai, loai_yeu_cau, so_ho_so, so_vi_pham |

## Nguồn gốc nhật ký sự kiện

Mọi chỉ số về quy trình bắt đầu ở một chỗ: **cửa chuyển trạng thái duy nhất** của engine
(`perform_transition`, `backend/app/workflow/engine.py`). Mỗi lần chuyển, cửa này ghi một dòng vào bảng
`event_log` trong cùng giao dịch với thay đổi trên hồ sơ — `case_id`, `activity`, `timestamp` (UTC),
`actor`, `from_state`, `to_state`. Trigger `event_log_chan_sua_xoa` chặn UPDATE và DELETE: nhật ký chỉ ghi
thêm, nên một con số tính từ nó hôm nay vẫn tính lại được ngày mai. Việc tạo hồ sơ không phải lần chuyển
trạng thái; view `bao_cao_nhat_ky` dựng sự kiện mở đầu `create-case` từ `requests.created_at`.

```text
perform_transition ──► event_log (chỉ ghi thêm)
                          │
                          ├──► bao_cao_nhat_ky ──► xuất dữ liệu mở, khai phá quy trình, lưu trữ lạnh
                          └──► bao_cao_ho_so ──► view tổng hợp ──► biểu đồ của bảng điều khiển
```

Nơi khác đọc nhật ký, ngoài bảng điều khiển — quan hệ đọc lấy từ câu SQL trong mã của từng nơi:

| Nơi đọc | Tệp mã | Quan hệ đọc |
|---|---|---|
| Xuất nhật ký — `GET /core/v1/events` | `backend/app/analytics/xuat_du_lieu.py` | `bao_cao_nhat_ky` |
| Khai phá quy trình — dịch vụ `khai-pha`, màn Quy trình thực tế | `services/khai-pha/app/du_lieu.py` | `bao_cao_nhat_ky`, `event_log`, `processes`, `states`, `transitions`, `work_calendars` |
| Lưu trữ lạnh — `GET /core/v1/archive` | `backend/app/analytics/luu_tru_lanh.py` | `bao_cao_nhat_ky`, `event_log`, `requests`, `rule_sets`, `states` |

Bản lưu trữ lạnh của mỗi tháng mang tệp `manifest.json` ghi mã băm SHA-256 và số dòng từng tệp, nên một
báo cáo dựng lại từ tầng lạnh đối chiếu được với tầng nóng (`scripts/doc_luu_tru.py`).

## Tra ngược con số trên màn Quy trình thực tế

Màn Quy trình thực tế (mục Báo cáo của cổng) không đi qua Superset: số trên đó là kết quả khai phá của
dịch vụ `khai-pha` trên `bao_cao_nhat_ky`, cùng nguồn với dữ liệu xuất ở bảng trên. Điểm nghẽn và nhánh
lệch chuẩn bấm ra đúng danh sách hồ sơ làm nên con số; mọi con số trong câu khuyến nghị tra được về kết
quả khai phá; mỗi hồ sơ mở ra lịch sử dựng từ chính `event_log` — chuỗi con số → hồ sơ → sự kiện khép
kín ngay trên giao diện.

## Giữ trang này đúng

- Đổi một view: thêm bản sửa Alembic mới (`CREATE OR REPLACE VIEW`, không sửa bản cũ), rồi chạy
  `python scripts/pha_he.py` để sinh lại trang này và trang tương ứng của trang tài liệu.
- Đổi bảng điều khiển: sửa trên Superset, xuất lại vào `infra/superset/bang-dieu-khien/`, rồi sinh lại.
- Tích hợp liên tục chạy `python3 scripts/pha_he.py --kiem` trong việc kiểm header: trang lệch với định
  nghĩa là đỏ. Kịch bản chỉ dùng thư viện chuẩn và đọc tĩnh kho mã, không cần cụm.
- View phải tạo bằng `op.execute("CREATE [OR REPLACE] VIEW …")` trong `upgrade()` của bản sửa — kịch
  bản đọc đúng các câu đó.
