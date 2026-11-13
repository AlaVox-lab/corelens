---
title: Ủy quyền khi vắng mặt
description: Nhờ người cùng phòng làm thay trong những ngày vắng; trưởng phòng khai thay cho người xử lý.
sidebar:
  order: 4.5
---

Trưởng phòng hay người xử lý vắng vài ngày thì hồ sơ không phải chờ tới lúc tự leo thang. Mở **Ủy
quyền** (`/uy-quyen`) trên thanh bên, nhóm *Làm việc*.

## Khai

1. Chọn **người làm thay** — chỉ người cùng phòng
2. Chọn **từ ngày** và **đến hết ngày**. Ủy quyền có hiệu lực từ 00:00 ngày đầu tới hết ngày cuối, theo
   giờ của lịch làm việc; mỗi lần dài tối đa 60 ngày (đổi bằng `DELEGATION_MAX_DAYS` trong `infra/.env`)
3. Bấm **Khai ủy quyền**

Trưởng phòng có thêm ô **người vắng**: khai thay cho một người xử lý trong phòng (người xử lý ốm, không
tự vào được). Trưởng phòng không khai thay cho một trưởng phòng khác.

Người làm thay **không phải xác nhận**. Từ ngày bắt đầu, trang chủ của họ hiện:

> Bạn đang làm thay **Dung Phạm** (Người xét duyệt yêu cầu · Công nghệ thông tin) đến hết ngày 16/11.

## Trong những ngày làm thay

- Người làm thay mang **vai của người vắng, chỉ trong phòng đó**: làm thay trưởng phòng thì nhận được hồ
  sơ về phòng, giao người xử lý, phân công lại hồ sơ leo thang
- Hồ sơ đang giao cho người xử lý vắng hiện trong **việc chờ** của người làm thay; người được giao vẫn
  giữ nguyên
- Mỗi thao tác chỉ làm được nhờ ủy quyền ghi trên dòng thời gian: *Cường Lê · thay mặt Dung Phạm*
- **Không** dùng ủy quyền để xử lý hồ sơ do chính người làm thay gửi
- **Không** ủy quyền tiếp: người đang làm thay trưởng phòng không khai ủy quyền vai trưởng phòng cho ai

## Thu hồi

Người vắng, người đã khai hay trưởng phòng bấm **Thu hồi** trên dòng ủy quyền. Quyền mất ngay ở lần thao
tác kế tiếp của người làm thay. Hết ngày cuối cũng vậy. Dòng ủy quyền đã hết hay thu hồi còn hiện trên
màn thêm 30 ngày.
