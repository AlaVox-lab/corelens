# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# ${message}
#
# Mã bản sửa    : ${up_revision}
# Sửa đổi từ    : ${down_revision | comma,n}
# Ngày tạo      : ${create_date}

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
