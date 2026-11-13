---
title: Sao lưu và khôi phục
description: Sao lưu tay cơ sở dữ liệu và kho tệp trong cùng một lần, khôi phục dưới 15 phút, đối soát sau khôi phục.
sidebar:
  order: 4.5
---

Dữ liệu của cụm nằm ở hai nơi phải khớp nhau: PostgreSQL (ba cơ sở dữ liệu — ứng dụng, Keycloak,
Superset) và SeaweedFS (tệp đính kèm, mà bảng `case_attachments` trỏ tới). Kịch bản
`scripts/sao_luu.py` sao cả hai trong **cùng một lần**, khôi phục cả hai, rồi đối soát.

## Mục tiêu

| | |
|---|---|
| Cách sao lưu | Tay, trước buổi trình diễn hay trước khi đổi lớn. Không có lịch tự động |
| Dữ liệu mất tối đa | Phần phát sinh sau lần sao lưu gần nhất |
| Thời gian khôi phục | Dưới 15 phút. Đo trên cụm thử: 200 hồ sơ, 1 249 sự kiện — khôi phục và đối soát xong trong khoảng 40 giây |
| Cụm ngừng nhận thao tác khi sao lưu | Khoảng 20 giây — cổng và dịch vụ ứng dụng tạm dừng để hồ sơ và tệp đứng yên |

## Sao lưu

Ở gốc kho mã, khi cụm đang chạy:

```bash
python scripts/sao_luu.py tao sao-luu/2026-12-09
```

Thư mục kết quả có ba tệp `.dump` (mỗi cơ sở dữ liệu một tệp), `kho-tep.tar.gz`, `vai-tro.sql` (tài
khoản chỉ đọc của Superset và dịch vụ khai phá), `doi-soat.json` (số dòng và mã băm của hồ sơ, nhật ký,
lời nhắn, tệp đính kèm) và `sao-luu.json` (thời điểm UTC, mã SHA-256 từng tệp). Chép thư mục đó ra
ngoài máy; thư mục đã có tệp thì lệnh từ chối ghi đè.

## Khôi phục

Cụm đích dựng từ **cùng phiên bản mã** và **cùng tệp `infra/.env`** với cụm đã sao lưu. Có thể là cụm
vừa `down -v` rồi `up -d`:

```bash
python scripts/sao_luu.py khoi-phuc sao-luu/2026-12-09
```

Lệnh kiểm mã SHA-256 trước khi đụng cụm, dừng mọi dịch vụ đọc/ghi dữ liệu, thay **toàn bộ** ba cơ sở
dữ liệu và kho tệp — kể cả tài khoản Keycloak và bảng điều khiển Superset — bật lại cụm, rồi đối soát:

```text
Đã khôi phục trong 0.6 phút (mục tiêu: dưới 15 phút). Đối soát:
  ĐẠT  requests: 204 dòng trước, 204 dòng đó sau khôi phục
  ĐẠT  event_log: 1249 dòng trước, 1249 dòng đó sau khôi phục
  ĐẠT  case_messages: 0 dòng trước, 0 dòng đó sau khôi phục
  ĐẠT  case_attachments: 2 dòng trước, 2 dòng đó sau khôi phục
  ĐẠT  kho tệp: 2 tệp (78 byte) trước, 2 tệp (78 byte) sau
Khôi phục giữ nguyên dữ liệu.
```

Chạy lại riêng bước đối soát bằng `python scripts/sao_luu.py doi-soat sao-luu/2026-12-09`.

## Ghi chú

- Cụm dùng tên container khác `dxlab-*` thì thêm `--tien-to <tiền tố>`
- Kịch bản chỉ dùng thư viện chuẩn Python 3.10 trở lên và lệnh `docker`; kho tệp được nén bằng chính
  ảnh SeaweedFS của cụm, không tải thêm ảnh nào
- Bản sao lưu chứa dữ liệu cá nhân (tên người trong hồ sơ và nhật ký, tệp đính kèm) — giữ ở nơi có
  kiểm soát truy cập. Chính sách lưu giữ: ADR-0009
- Sao lưu tự động theo lịch và sao lưu cho môi trường thật nằm ngoài phạm vi hiện tại
  (`docs/ARCHITECTURE.md` mục 9)
