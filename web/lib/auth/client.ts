"use client";
import { createAuthClient } from "better-auth/react";
import { clearClientState } from "@/lib/client-state";

export const authClient = createAuthClient();

// Đăng xuất: thu hồi phiên ở server rồi xóa trạng thái riêng của người dùng trên trình duyệt (IH-AUTH-008-R03).
export async function signOutAndClear(): Promise<void> {
  try {
    await authClient.signOut();
  } finally {
    clearClientState();
  }
}
