# SPDX-License-Identifier: MIT
# Copyright (c) 2026 AlaVox-lab
#
# Cấp cho vai khách quyền đọc kết nối dữ liệu nghiệp vụ, để bảng điều khiển nhúng trong cổng
# (#305) vẽ được biểu đồ bằng token khách.
#
# Token khách chỉ mở đúng dashboard ghi trong token; còn đọc dataset bên dưới thì vai khách
# (GUEST_ROLE_NAME trong superset_config.py) phải có quyền trên nguồn dữ liệu. Ảnh gốc không
# cấp, nên dashboard nhúng mở ra trống và API trả 404. Cấp theo tên kết nối, không theo số id:
# id do cơ sở dữ liệu của Superset sinh, đổi sau mỗi lần dựng lại.
#
# Điểm vào chạy tệp này sau `import-directory`, mỗi lần khởi động; cấp lại một quyền đã có thì
# không đổi gì. Phạm vi phòng ban không nằm ở đây — dịch vụ ứng dụng gắn điều kiện lọc theo
# dòng vào từng token.

import sys

from superset.app import create_app

TEN_KET_NOI = "Dữ liệu nghiệp vụ"

app = create_app()
with app.app_context():
    from superset import db, security_manager
    from superset.models.core import Database

    vai = security_manager.find_role(app.config["GUEST_ROLE_NAME"])
    ket_noi = db.session.query(Database).filter_by(database_name=TEN_KET_NOI).one_or_none()
    if vai is None or ket_noi is None:
        # Thiếu một trong hai là cấu hình hỏng: dừng khởi động cho lộ ra, đừng chạy với
        # bảng điều khiển nhúng trống mà không ai biết vì sao
        sys.exit(f"Thiếu vai khách hoặc kết nối '{TEN_KET_NOI}'")
    quyen = security_manager.add_permission_view_menu("database_access", ket_noi.perm)
    security_manager.add_permission_role(vai, quyen)
    db.session.commit()
    print(f"    vai {vai.name}: {quyen}")
