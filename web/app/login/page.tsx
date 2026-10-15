import { LoginForm } from "./login-form";

// Khung đăng nhập tối thiểu của Auth scaffold, dùng để chạy thử phiên. Học viên thay theo prototype đã chốt (LR-10)
// và tự xây đăng ký, xác minh email (Core, LR-12, LR-14). Quên, đặt lại mật khẩu và hồ sơ là Extended.
export default function LoginPage() {
  return (
    <div className="mx-auto grid w-full max-w-sm gap-6 py-10">
      <div className="grid gap-1">
        <h1 className="text-2xl font-semibold">Đăng nhập</h1>
        <p className="text-sm text-muted-foreground">Dùng tài khoản thử tạo bằng <code>make seed-users</code>.</p>
      </div>
      <LoginForm />
    </div>
  );
}
