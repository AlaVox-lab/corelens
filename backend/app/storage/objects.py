# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Lớp bọc kho lưu trữ đối tượng (#80, ADR-0002).
#
# Mọi cuộc gọi sang SeaweedFS đi qua tệp này, bằng S3 API chuẩn qua boto3. Không nhúng
# thư viện của SeaweedFS, không dùng API riêng của nó — đổi sang Garage hay MinIO chỉ là đổi
# bốn giá trị cấu hình. Phần còn lại của dịch vụ chỉ biết bốn hàm dưới đây và `KhoLoi`, nên
# kho có tắt hay lỗi cũng chỉ làm đúng phần đính kèm báo lỗi.

from __future__ import annotations

import logging
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


class KhoLoi(Exception):
    """Kho tệp không trả lời hoặc từ chối. Điểm cuối dịch thành 502, không lộ chi tiết."""


class KhongCoTep(KhoLoi):
    """Khóa không có trong kho — dòng siêu dữ liệu còn mà nội dung đã mất."""


@lru_cache
def _khach():
    """Một ứng dụng khách dùng chung. Hết thời gian chờ ngắn: kho treo thì trả lỗi sớm,
    không giữ luồng của dịch vụ."""
    cau_hinh = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=cau_hinh.s3_endpoint,
        aws_access_key_id=cau_hinh.s3_access_key,
        aws_secret_access_key=cau_hinh.s3_secret_key,
        region_name=cau_hinh.s3_region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # SeaweedFS không có tên miền con theo thùng
            connect_timeout=3,
            read_timeout=15,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )


def _dam_bao_thung() -> None:
    """Tạo thùng nếu chưa có. Gọi trước mỗi lần ghi — rẻ, và nhờ đó không có bước khởi tạo kho
    nào phải nhớ làm, kể cả khi volume của kho vừa bị xóa."""
    thung = get_settings().s3_bucket
    try:
        _khach().head_bucket(Bucket=thung)
    except ClientError as loi:
        ma = str(loi.response.get("Error", {}).get("Code", ""))
        if ma not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        _khach().create_bucket(Bucket=thung)


def luu_tep(khoa: str, noi_dung: bytes, loai: str) -> None:
    """Ghi một tệp vào kho dưới khóa cho trước."""
    try:
        _dam_bao_thung()
        _khach().put_object(
            Bucket=get_settings().s3_bucket, Key=khoa, Body=noi_dung, ContentType=loai
        )
    except (BotoCoreError, ClientError) as loi:
        logger.exception("Không ghi được tệp vào kho: %s", khoa)
        raise KhoLoi("Kho tệp không phản hồi.") from loi


def doc_tep(khoa: str) -> bytes:
    """Đọc nguyên một tệp. Tệp tối đa vài chục MB nên đọc cả vào bộ nhớ là đủ."""
    try:
        phan_hoi = _khach().get_object(Bucket=get_settings().s3_bucket, Key=khoa)
        return phan_hoi["Body"].read()
    except ClientError as loi:
        ma = str(loi.response.get("Error", {}).get("Code", ""))
        if ma in {"NoSuchKey", "404", "NoSuchBucket"}:
            raise KhongCoTep(khoa) from loi
        logger.exception("Không đọc được tệp từ kho: %s", khoa)
        raise KhoLoi("Kho tệp không phản hồi.") from loi
    except BotoCoreError as loi:
        logger.exception("Không đọc được tệp từ kho: %s", khoa)
        raise KhoLoi("Kho tệp không phản hồi.") from loi
