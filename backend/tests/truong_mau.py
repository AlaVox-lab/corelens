# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Hàm dùng chung cho bài kiểm thử gửi yêu cầu qua điểm cuối (#250).


def chi_tiet_mau(loai: dict) -> dict:
    """Bộ trường riêng hợp lệ tối thiểu cho một loại yêu cầu (#250), dựng từ phần `fields` mà
    `GET /request-types` trả về: điền đúng các trường bắt buộc, để bài kiểm thử gửi yêu cầu qua
    điểm cuối không phải biết loại nào có trường gì."""
    mau = {"text": "Mẫu", "number": 1, "date": "2026-11-02"}
    return {
        t["code"]: t["options"][0] if t["kind"] == "choice" else mau[t["kind"]]
        for t in loai.get("fields", [])
        if t["required"]
    }
