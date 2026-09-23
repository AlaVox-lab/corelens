// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Dòng cảnh báo trước một thao tác không hoàn tác được (#98).
//
// Hiện khi trạng thái đích của cạnh là trạng thái kết thúc — cờ `to_state_is_terminal`
// mà dịch vụ tra từ cột `states.is_terminal`. Tệp này không biết thao tác nào là "hủy"
// hay "đóng": doanh nghiệp thêm một trạng thái kết thúc mới thì cảnh báo tự hiện ở mọi
// cạnh dẫn tới nó.
//
// Dùng chung cho cổng người gửi và buồng lái, để cùng một rủi ro được nói bằng cùng
// một câu ở mọi nơi.

export function CanhBaoKetThuc({ nhanTrangThai }: { nhanTrangThai: string }) {
  return (
    <p
      role="note"
      style={{
        margin: 0,
        padding: "10px 12px",
        borderRadius: "9px",
        background: "var(--f-a-bg)",
        border: "1px solid var(--f-a-line)",
        color: "var(--f-a-ink)",
        fontSize: "13px",
        lineHeight: 1.55,
      }}
    >
      Hồ sơ sẽ sang <strong>{nhanTrangThai}</strong> — trạng thái kết thúc, không hoàn
      tác được. Muốn làm tiếp sau đó phải gửi yêu cầu mới.
    </p>
  );
}
