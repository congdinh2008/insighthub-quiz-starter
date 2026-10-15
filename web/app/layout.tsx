import type { Metadata } from "next";
import "./globals.css";
import { AppHeader } from "@/components/app/app-header";
import { ToastProvider } from "@/components/ui/toast";
import { getSessionUser, type SessionUser } from "@/lib/auth/server";

export const metadata: Metadata = {
  title: "InsightHub SDLC",
  description: "Quản lý tài liệu và hỏi đáp có nguồn",
};

async function currentUser(): Promise<SessionUser | null> {
  if (!process.env.BETTER_AUTH_SECRET) return null;
  try {
    return await getSessionUser();
  } catch {
    // Auth chưa cấu hình hoặc database chưa sẵn sàng: hiển thị như khách, không chặn trang demo.
    return null;
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const user = await currentUser();
  return (
    <html lang="vi" className="dark">
      <body>
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground">
          Bỏ qua tới nội dung chính
        </a>
        <ToastProvider>
          <AppHeader user={user} />
          <main id="main" className="mx-auto w-full max-w-7xl px-4 py-6">{children}</main>
        </ToastProvider>
      </body>
    </html>
  );
}
