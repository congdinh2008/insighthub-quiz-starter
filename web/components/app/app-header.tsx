"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { signOutAndClear } from "@/lib/auth/client";
import type { SessionUser } from "@/lib/auth/server";

/**
 * Header dùng chung (app shell). Chỉ có thương hiệu và menu người dùng.
 * Điều hướng giữa Notebook, nguồn, hỏi đáp, công cụ AI là thiết kế của học viên (LR-10), thêm qua prop `nav`.
 */
export function AppHeader({ user, nav }: { user: SessionUser | null; nav?: React.ReactNode }) {
  const router = useRouter();
  async function logout() {
    await signOutAndClear();
    router.push("/login");
    router.refresh();
  }
  return (
    <header className="border-b bg-card/60">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-4 px-4">
        <Link href="/" className="font-semibold tracking-tight">InsightHub</Link>
        <div className="flex min-w-0 flex-1 items-center gap-2">{nav}</div>
        {user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" aria-label={`Tài khoản ${user.email}`}>
                <UserRound aria-hidden="true" />
                <span className="hidden max-w-48 truncate sm:inline">{user.name || user.email}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>{user.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={logout}><LogOut aria-hidden="true" className="size-4" />Đăng xuất</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button asChild variant="outline" size="sm"><Link href="/login">Đăng nhập</Link></Button>
        )}
      </div>
    </header>
  );
}
