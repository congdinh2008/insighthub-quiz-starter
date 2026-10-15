# Prototype base (dùng chung token với web)

Thư mục nền cho học viên chọn **prototype HTML** ở LR-10 (M2). Học viên chọn Figma thì dùng cùng bảng token này khi tạo Variables trong Figma.

| File | Vai trò |
| --- | --- |
| `tokens.css` | Design token (màu, trạng thái, spacing, typography, radius). Trùng khớp khối `:root` của `web/app/globals.css`, kiểm bằng `web/tests/tokens.test.mjs` |
| `base.css` | Style tối thiểu theo tên component của `web/components/ui` (`.btn`, `.field`, `.card`, `.status`, `.alert`, `.empty`, `.skeleton`, `dialog`) |
| `components.html` | Trang minh họa component, mở trực tiếp bằng trình duyệt. Không phải màn hình InsightHub |

## Cách dùng

1. Tạo prototype trong `design/prototype/<ten-prototype>/` (ví dụ `design/prototype/m2/`), không sửa `_base/`.
2. Nhúng token trước rồi base:

   ```html
   <link rel="stylesheet" href="../_base/tokens.css">
   <link rel="stylesheet" href="../_base/base.css">
   ```

3. Style riêng của prototype đặt trong file của prototype và chỉ dùng biến `var(--...)` có trong `tokens.css`.
4. Cần token mới: thêm vào `web/app/globals.css` và `tokens.css` trong cùng commit, chạy `cd web && npm test`.

## Giới hạn

- Prototype là artifact thiết kế: không import vào `web/`, không gọi API thật, không chứa secret hoặc dữ liệu thật (LR-10).
- `_base/` chỉ cấp nền dùng chung. Màn hình, IA, nội dung nghiệp vụ và trạng thái của từng hành trình là bài của học viên.
- Ánh xạ class sang component React: [docs/UI_Foundation.md](../../../docs/UI_Foundation.md) mục 4.
