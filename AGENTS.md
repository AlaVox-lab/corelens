# AGENTS.md

Tệp này dành cho mọi trợ lý AI lập trình làm việc trên kho mã — Antigravity, Codex,
Cursor và các công cụ khác đọc chuẩn `AGENTS.md`. Claude Code đọc `CLAUDE.md`; nội dung
quy tắc là một.

---

## Việc đầu tiên

**Đọc toàn bộ `CLAUDE.md` ở gốc kho trước khi làm bất cứ việc gì.** Đó là bộ quy tắc đầy
đủ, dùng chung cho mọi trợ lý: chỗ nào trong tệp đó ghi "Claude Code" thì áp dụng nguyên
văn cho bạn. Sau đó đọc tiếp theo thứ tự ở mục 0 của `CLAUDE.md`.

Người dùng có thể đưa thêm bộ luật trợ lý của nhóm — `TRO-LY-THANH-VIEN.md` hoặc
`TRO-LY-NAVIGATOR.md`, nằm ngoài kho mã. Bộ luật đó quy định quy trình Git theo vai trò
của người dùng; `CLAUDE.md` quy định cách làm việc với mã nguồn. Hai bên không mâu thuẫn;
nếu thấy mâu thuẫn, dừng lại và hỏi.

---

## Năm quy tắc tuyệt đối

Tóm tắt để bạn không bỏ sót ngay cả trước khi đọc xong `CLAUDE.md`. Bản đầy đủ và lý do
ở chính tệp đó.

1. **Không tự chạy lệnh Git ghi** — `commit`, `push`, `merge`, `rebase`, `cherry-pick`,
   `tag`, `reset --hard`, `checkout` hay `switch` sang nhánh khác, tạo hay xóa nhánh — và
   không chạy `gh` để tạo hay sửa issue, pull request, bản phát hành. Lịch sử commit là
   căn cứ chấm điểm của cuộc thi và phải mang danh tính thật của người làm. **Kể cả khi
   công cụ của bạn cho phép tự chạy lệnh terminal**: soạn sẵn lệnh và commit message
   trong khối mã, rồi dừng để người dùng tự chạy
2. **Được chạy lệnh chỉ đọc**: `git status`, `git diff`, `git log`, `git show`,
   `git branch --list`, `git fetch`, và `gh issue view`, `gh issue list`, `gh pr view`,
   `gh pr list`. Người dùng đưa số issue thì tự đọc issue bằng `gh issue view <số>
   --comments` thay vì bắt họ chụp màn hình
3. **Mọi tệp mã nguồn mới có header giấy phép** ở hai dòng đầu — thiếu là mất điểm.
   Python viết `# SPDX-License-Identifier: MIT` rồi `# Copyright (c) 2026 AlaVox-lab`;
   TypeScript thay `#` bằng `//`, SQL thay bằng `--`
4. **Nghiệp vụ nằm trong dữ liệu, không mã cứng.** Trạng thái, vai trò, ngưỡng SLA tra từ
   bảng. Chuỗi như `"Đang xử lý"` hay `"in-progress"` nằm trong câu lệnh `if` là vi phạm
5. **Không sửa mã thư viện bên thứ ba, không tự thêm phụ thuộc.** Phụ thuộc mới phải có
   giấy phép thuộc danh sách OSI, ghi vào `docs/dependencies.md`, và tệp khóa phiên bản
   luôn được commit

Không tự chạy kiểm thử, máy chủ phát triển hay Docker khi chưa được yêu cầu. Được yêu cầu
dựng thử một thứ gì — ví dụ khi khảo sát một nền tảng — thì dựng thành **cụm riêng**, mang
tên dự án riêng (`docker compose -p <tên-riêng> …`), đặt ngoài kho mã; cụm riêng đó được
tự dọn. **Không bao giờ chạy `down -v` trên cụm chính `dx-os-lab`**, không
`docker volume rm`, không `docker system prune` — các lệnh đó xóa sạch dữ liệu thử của
người dùng. Dữ liệu cụm chính chỉ được đọc, không được sửa.

---

## Ngôn ngữ và commit message

Trả lời, viết tài liệu và commit message bằng **tiếng Việt có dấu**. Commit message theo
Conventional Commits — `CLAUDE.md` mục 6.2: tiêu đề dưới 72 ký tự, **không dòng nào mở
đầu bằng `#`** vì Git xóa dòng đó, footer `Closes #N` hoặc `Refs #N`.

---

## Bản đồ nhanh

| Thư mục | Nội dung |
|---|---|
| `backend/` | Dịch vụ ứng dụng FastAPI — máy trạng thái, ràng buộc, nhật ký sự kiện |
| `frontend/` | Cổng người dùng Next.js |
| `infra/` | Docker Compose, lược đồ khởi tạo, dữ liệu khởi tạo, realm Keycloak |
| `docs/` | Kiến trúc, trạng thái dự án, bản ghi quyết định (`docs/adr/`) |

Sơ đồ chi tiết: `docs/ARCHITECTURE.md` mục 4.1.

Dựng cả cụm bằng một lệnh, chạy ở gốc kho. Lần đầu chép `infra/.env.example` thành
`infra/.env`:

```
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build
```
