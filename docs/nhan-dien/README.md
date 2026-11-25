# Nhận diện Corelens

Dấu của Corelens là chữ **C** ghép từ ba dải kính trong suốt — san hô, hồng tím, tím — ôm quanh một lõi đá cắt mặt.
Chữ C là Corelens. Ba dải là ba phía cùng đi trên một quy trình: người gửi, điều phối, phòng ban. Lõi là nơi mọi yêu
cầu được gom về.

## Các tệp

| Tệp | Dùng khi |
|---|---|
| `corelens-dau.svg` | Bản màu, dùng mặc định: cổng, trang tài liệu, màn đăng nhập, trình chiếu |
| `corelens-dau-mot-mau.svg` | Một màu theo `currentColor`: in ấn, đặt trên nền ảnh, chỗ không hiện được chuyển màu |
| `corelens-16.png` … `corelens-512.png` | Biểu tượng tab (16, 32, 48), biểu tượng trên màn hình chính (180, 192, 512) |
| `corelens-kem-chu-sang.png` | Dấu kèm chữ "Corelens" trên nền sáng |
| `corelens-kem-chu-toi.png` | Dấu kèm chữ "Corelens" trên nền tối |

Cổng dùng dấu qua `frontend/components/dau-corelens.tsx` và `frontend/app/icon.svg`; trang tài liệu qua
`docs-site/public/favicon.svg` và `docs-site/src/assets/corelens-dau.svg`; màn đăng nhập qua chủ đề
`infra/keycloak/themes/dx-os-lab/login/`. Sửa dấu thì sửa ở đây trước, rồi chép sang các chỗ đó.

## Cách dùng

- Cỡ nhỏ nhất 16 px. Dưới cỡ đó các dải kính dính vào nhau.
- Chừa khoảng trống quanh dấu bằng một phần tư bề rộng dấu; không đặt chữ hay hình khác vào khoảng đó.
- Không kéo méo, không xoay, không thêm bóng hay viền. Không đổi màu bản màu — cần một màu khác thì dùng bản một màu.
- Đặt cạnh tên sản phẩm thì dấu là hình trang trí: trên trang web gắn `aria-hidden`, để trình đọc màn hình không đọc
  tên hai lần.

## Giấy phép

Mọi tệp trong thư mục này do nhóm vẽ, theo giấy phép MIT như phần còn lại của kho (`LICENSE`). Chữ "Corelens" trong
bản kèm chữ dùng phông Be Vietnam Pro (SIL Open Font License 1.1); phông chỉ nằm trong ảnh PNG, thư mục không chứa tệp
phông — ghi ở `docs/dependencies.md`, mục *Tài sản thiết kế*.
