# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Ảnh chứa cho cổng người dùng.
#
# Dựng nhiều tầng: tầng cài thư viện, tầng biên dịch, tầng chạy. Ảnh cuối chỉ mang
# kết quả biên dịch, không mang mã nguồn lẫn toàn bộ node_modules.
#
# Ảnh Node ghim thẻ cụ thể kèm mã băm, cùng một ảnh cho cả ba tầng. Thẻ trôi `node:24-alpine` từng làm
# `next build` hỏng chập chờn (không nạp được `@next/swc-linux-x64-*`) khi thẻ bị đẩy bản mới.

# ---------------------------------------------------------------------------
# Tầng 1 — cài thư viện
# ---------------------------------------------------------------------------
FROM node:24.22.1-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS deps

WORKDIR /app

# `npm ci` cài đúng theo package-lock.json và báo lỗi nếu tệp khóa lệch với
# package.json. Khác `npm install` ở chỗ nó không bao giờ tự sửa tệp khóa — đó
# chính là thứ bảo đảm ban giám khảo nhận đúng bộ thư viện nhóm đã kiểm thử.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ---------------------------------------------------------------------------
# Tầng 2 — biên dịch
# ---------------------------------------------------------------------------
FROM node:24.22.1-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS builder

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . ./

RUN npm run build

# ---------------------------------------------------------------------------
# Tầng 3 — chạy
# ---------------------------------------------------------------------------
FROM node:24.22.1-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Chạy bằng tài khoản thường, không phải root
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Nhờ output: "standalone" trong next.config.ts, thư mục này đã gói sẵn đúng những
# gói thư viện cần để chạy — không cần chép cả node_modules sang.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
