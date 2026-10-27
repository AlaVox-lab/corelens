// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Khung chờ khi trang đang tải (#235), vẽ đúng hình của màn thật — tiêu đề, dải số, các dòng
// danh sách, hay hai cột của trang hồ sơ — để lúc dữ liệu về, bố cục không nhảy. Trình đọc
// màn hình nghe "Đang tải" một lần thay vì một loạt khối trống.

function Vach({ rong, cao = 12 }: { rong: string; cao?: number }) {
  return <span className="khung-cho-vach" style={{ width: rong, height: `${cao}px` }} />;
}

function DongCho() {
  return (
    <div className="khung-cho-dong">
      <Vach rong="10px" cao={10} />
      <span style={{ display: "grid", gap: "8px" }}>
        <Vach rong="62%" />
        <Vach rong="38%" />
      </span>
      <Vach rong="110px" cao={32} />
    </div>
  );
}

export function KhungChoDanhSach({ dong = 5, coDaiSo = false }: { dong?: number; coDaiSo?: boolean }) {
  return (
    <div role="status" aria-label="Đang tải">
      <Vach rong="240px" cao={24} />
      <div style={{ marginTop: "10px" }}>
        <Vach rong="320px" />
      </div>
      {coDaiSo ? (
        <div className="dai-so">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="o-so">
              <Vach rong="60%" />
              <Vach rong="40px" cao={24} />
            </div>
          ))}
        </div>
      ) : (
        <div style={{ height: "20px" }} />
      )}
      <div className="the">
        {Array.from({ length: dong }, (_, i) => (
          <DongCho key={i} />
        ))}
      </div>
    </div>
  );
}

export function KhungChoHoSo() {
  return (
    <div role="status" aria-label="Đang tải">
      <Vach rong="140px" />
      <div style={{ marginTop: "10px" }}>
        <Vach rong="min(520px, 90%)" cao={26} />
      </div>
      <div className="khung-cho-hai-cot">
        <div className="the" style={{ padding: "18px", display: "grid", gap: "12px" }}>
          <Vach rong="40%" cao={16} />
          <Vach rong="90%" />
          <Vach rong="80%" />
          <Vach rong="85%" />
        </div>
        <div className="the" style={{ padding: "18px", display: "grid", gap: "12px" }}>
          <Vach rong="50%" cao={16} />
          <Vach rong="100%" cao={36} />
          <Vach rong="100%" cao={36} />
        </div>
      </div>
    </div>
  );
}
