# UI Foundation (learner-r2.0)

Nền giao diện dùng chung của Starter: design token, component, app shell và trang đăng nhập tối thiểu. Starter **chỉ cấp nền**, không thiết kế hộ màn hình nghiệp vụ. Ba màn Quiz (tạo đề, làm bài, kết quả) và điều hướng tới chúng là bài của học viên theo prototype đã chốt ở M2 (LR-10). Màn Notebook, Tóm tắt, Output và IA đầy đủ là Extended.

## 1. Stack và phiên bản

| Thành phần | Phiên bản | Vai trò |
| --- | --- | --- |
| `tailwindcss`, `@tailwindcss/postcss` | 4.3.3 | Utility CSS, cấu hình bằng CSS (`@import "tailwindcss"`, `@theme inline`), không có `tailwind.config.js` |
| `radix-ui` | 1.6.7 | Primitive có sẵn hành vi bàn phím, focus và ARIA cho Dialog, AlertDialog, Tabs, DropdownMenu, Label, Separator, Slot |
| `class-variance-authority`, `clsx`, `tailwind-merge` | 0.7.1, 2.1.1, 3.7.0 | Biến thể component và hàm `cn()` ở `web/lib/utils.ts` |
| `lucide-react` | 1.48.0 | Biểu tượng (luôn `aria-hidden` khi đi kèm chữ) |
| `tw-animate-css` | 1.4.0 | Animation mở, đóng của Dialog và menu |

Component viết theo quy ước shadcn/ui (mã nguồn nằm trong repo, học viên sửa trực tiếp, không phải thư viện đóng gói). Mọi package pin phiên bản chính xác. Thêm package mới theo quy tắc trong `AGENTS.md` (kiểm registry chính thức, đúng publisher, pin phiên bản).

## 2. Design token

Nguồn duy nhất: khối `:root` trong `web/app/globals.css`. Bản cho prototype HTML: `design/prototype/_base/tokens.css`. `web/tests/tokens.test.mjs` kiểm hai file trùng giá trị và các cặp màu đạt tương phản.

| Nhóm | Token | Dùng cho |
| --- | --- | --- |
| Nền và chữ | `--background`, `--foreground`, `--card`, `--popover`, `--muted`, `--muted-foreground` | Nền trang, thẻ, chữ phụ |
| Hành động | `--primary`, `--secondary`, `--accent`, `--destructive` (kèm `-foreground`) | Nút, mục đang chọn, thao tác xóa |
| Điều khiển | `--border`, `--input`, `--ring` | Viền thẻ, viền ô nhập, focus ring |
| Trạng thái | `--status-processing`, `--status-ready`, `--status-failed`, `--status-noevidence`, `--warning` | `StatusBadge`, Alert |
| Hình khối | `--radius` (suy ra `radius-sm/md/lg/xl`) | Bo góc |

Trong code dùng class Tailwind theo token: `bg-card`, `text-muted-foreground`, `border-input`, `text-status-failed`. Không dùng mã màu cứng trong component. Cần token mới thì thêm vào `globals.css` và `tokens.css` trong cùng commit.

Ngưỡng tương phản đã kiểm: chữ thường và chữ trạng thái từ 4,5:1 trở lên trên nền chính, viền ô nhập và focus ring từ 3:1 trở lên.

## 3. Component nền (`web/components/ui`)

Xem trực quan tại `/dev/ui-kit` (trang tham khảo cho người phát triển, không chứa dữ liệu).

| Component | File | Hành vi a11y có sẵn |
| --- | --- | --- |
| `Button` | `button.tsx` | Biến thể `default`, `outline`, `secondary`, `ghost`, `destructive`, `link`. Prop `loading` khóa nút và đặt `aria-busy` để không gửi trùng (IH-UX-004) |
| `Input`, `Textarea`, `Label` | `input.tsx`, `textarea.tsx`, `label.tsx` | Viền theo `--input`, trạng thái `aria-invalid` |
| `FormField` | `form-field.tsx` | Nối nhãn, gợi ý và lỗi bằng `htmlFor`, `aria-describedby`, `aria-invalid`. Lỗi hiển thị đúng trường |
| `Dialog`, `ConfirmDialog` | `dialog.tsx`, `confirm-dialog.tsx` | Bẫy focus, Escape để đóng, trả focus về nút mở. `ConfirmDialog` dùng AlertDialog cho thao tác không hoàn tác |
| `Tabs` | `tabs.tsx` | Phím mũi tên chuyển tab, `role="tablist"` |
| `DropdownMenu` | `dropdown-menu.tsx` | Phím mũi tên, Enter, Escape. Dùng cho menu người dùng |
| `StatusBadge` | `status-badge.tsx` | `Pending`, `Processing`, `Ready`, `Succeeded`, `NoEvidence`, `Failed`. Luôn có chữ và biểu tượng, không chỉ dùng màu (IH-UX-003-AC02) |
| `Card`, `Badge`, `Separator` | `card.tsx`, `badge.tsx`, `separator.tsx` | Bố cục |
| `Skeleton`, `Spinner`, `Alert`, `EmptyState` | `feedback.tsx` | `Spinner` có nhãn cho trình đọc màn hình. `Alert` biến thể lỗi dùng `role="alert"` |
| `CursorPagination` | `pagination.tsx` | Nút Trước, Sau theo cursor, có nhãn vùng điều hướng |
| `ToastProvider`, `useToast` | `toast.tsx` | Live region `aria-live` cho thông báo không chặn thao tác |

## 4. App shell và trang có sẵn

| Phần | File | Ghi chú |
| --- | --- | --- |
| Layout gốc | `web/app/layout.tsx` | `lang="vi"`, skip link tới `#main`, `ToastProvider`, header, vùng nội dung `max-w-7xl` co giãn cho 1440 × 900 và 390 × 844 |
| Header | `web/components/app/app-header.tsx` | Thương hiệu, slot `nav` cho điều hướng của học viên, menu người dùng có Đăng xuất (gọi `signOutAndClear()` xóa trạng thái client rồi về `/login`) |
| Đăng nhập | `web/app/login/` | **Khung tối thiểu** để chạy thử Auth scaffold bằng email và mật khẩu. Thông báo lỗi chung, không tiết lộ email có tồn tại hay không. Thay theo prototype của học viên |
| Lỗi, không tìm thấy | `web/app/error.tsx`, `web/app/not-found.tsx` | Không hiển thị stack hoặc chi tiết nội bộ |
| Trang demo | `web/app/page.tsx` | Luồng M0.1 kế thừa, bọc trong `.starter-demo` với style cũ ở `web/app/demo.css`. Học viên thay dần bằng component nền |

Bảo vệ trang cần đăng nhập: gọi `requireSession()` (`web/lib/auth/server.ts`) ở đầu Server Component. Đây chỉ là lớp giao diện, API vẫn phải kiểm phiên và quyền phía FastAPI.

Không gồm (bài của học viên): đăng ký, xác minh email (Core), quên và đặt lại mật khẩu, đổi mật khẩu, hồ sơ (Extended), IA và điều hướng, toàn bộ màn hình nghiệp vụ, danh mục thông báo MSG của SRS.

## 5. Từ prototype sang code

| Prototype HTML (`design/prototype/_base`) | Figma | Component React |
| --- | --- | --- |
| `.btn`, `.btn-outline`, `.btn-destructive` | Component Button có variant cùng tên | `<Button variant="...">` |
| `.field` + `label` + `.error` | Form field có nhãn và lỗi | `<FormField label error>` bọc `<Input>` |
| `dialog` | Modal | `<Dialog>` hoặc `<ConfirmDialog>` |
| `.status[data-status]` | Status chip có biểu tượng | `<StatusBadge status>` |
| `.alert`, `.empty`, `.skeleton` | Alert, Empty, Loading | `<Alert>`, `<EmptyState>`, `<Skeleton>` |
| Biến `var(--...)` | Variables cùng tên | Class Tailwind theo token |

Quy trình gợi ý khi dùng coding agent ở M3: đưa agent link prototype đã chốt, đường dẫn `web/components/ui` và mục này, yêu cầu **dùng lại component có sẵn**, không tạo component trùng chức năng. Khác biệt hợp lý so với prototype ghi trong PR.

## 6. Quy tắc a11y và kiểm thử

- Mọi điều khiển có nhãn nhìn thấy hoặc `aria-label`. Biểu tượng đi kèm chữ đặt `aria-hidden`.
- Không dùng màu làm tín hiệu duy nhất (trạng thái, lỗi, trường bắt buộc).
- Thứ tự Tab theo thứ tự đọc. Dialog giữ focus và trả focus khi đóng.
- E2E tìm phần tử theo role và nhãn (`getByRole`, `getByLabel`). Khi đổi style, giữ nguyên nhãn để test không vỡ.
- Kiểm hai viewport 1440 × 900 và 390 × 844 trước khi nộp milestone.

## 7. Lệnh kiểm

```bash
cd web
npm run typecheck
npm test            # gồm tokens.test.mjs
npm run build
npm run test:pw     # Playwright Test trong web/e2e, cần API và web fixture đang chạy
npm run test:e2e    # script E2E cũ của rc.3
```
