import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { Pool } from "pg";
import { authOptions } from "./config";

// Khởi tạo khi có request đầu tiên (không chạy lúc build), để thiếu BETTER_AUTH_SECRET báo lỗi rõ ở runtime.
function createAuth() {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 5 });
  return betterAuth({ ...authOptions(pool), plugins: [nextCookies()] });
}

let instance: ReturnType<typeof createAuth> | null = null;

export function getAuth(): ReturnType<typeof createAuth> {
  if (!instance) instance = createAuth();
  return instance;
}

export type SessionUser = { id: string; email: string; name: string; emailVerified: boolean };

// Đọc phiên ở Server Component hoặc Route Handler. Trả null khi chưa đăng nhập.
export async function getSessionUser(): Promise<SessionUser | null> {
  const session = await getAuth().api.getSession({ headers: await headers() });
  if (!session) return null;
  const { id, email, name, emailVerified } = session.user;
  return { id, email, name, emailVerified };
}

// Dùng ở đầu Server Component của trang cần đăng nhập: chưa có phiên thì chuyển về /login.
// Chỉ là lớp giao diện. API vẫn phải tự kiểm phiên và quyền (current_user + policy phía FastAPI).
export async function requireSession(): Promise<SessionUser> {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  return user;
}
