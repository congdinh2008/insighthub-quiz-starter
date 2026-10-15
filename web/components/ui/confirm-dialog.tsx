"use client";
import * as React from "react";
import { AlertDialog as AlertDialogPrimitive } from "radix-ui";
import { Button } from "./button";

/**
 * Xác nhận thao tác thay đổi dữ liệu (SRS mục 3.5.1): nêu đối tượng, dữ liệu bị ảnh hưởng, có lựa chọn hủy.
 * Đóng hộp thoại không đồng nghĩa đã xác nhận. Focus mặc định vào nút Hủy.
 */
export function ConfirmDialog({
  trigger, title, description, confirmLabel = "Xác nhận", cancelLabel = "Hủy", destructive = false, onConfirm,
}: {
  trigger: React.ReactNode; title: string; description: React.ReactNode; confirmLabel?: string; cancelLabel?: string;
  destructive?: boolean; onConfirm: () => void | Promise<void>;
}) {
  const [busy, setBusy] = React.useState(false);
  const [open, setOpen] = React.useState(false);
  async function confirm(event: React.MouseEvent) {
    event.preventDefault();
    setBusy(true);
    try { await onConfirm(); setOpen(false); } finally { setBusy(false); }
  }
  return (
    <AlertDialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <AlertDialogPrimitive.Trigger asChild>{trigger}</AlertDialogPrimitive.Trigger>
      <AlertDialogPrimitive.Portal>
        <AlertDialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60" />
        <AlertDialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 grid w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 gap-4 rounded-xl border bg-popover p-6 text-popover-foreground shadow-lg">
          <AlertDialogPrimitive.Title className="text-lg font-semibold">{title}</AlertDialogPrimitive.Title>
          <AlertDialogPrimitive.Description asChild>
            <div className="text-sm text-muted-foreground">{description}</div>
          </AlertDialogPrimitive.Description>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <AlertDialogPrimitive.Cancel asChild><Button variant="outline" disabled={busy}>{cancelLabel}</Button></AlertDialogPrimitive.Cancel>
            <AlertDialogPrimitive.Action asChild>
              <Button variant={destructive ? "destructive" : "default"} loading={busy} onClick={confirm}>{confirmLabel}</Button>
            </AlertDialogPrimitive.Action>
          </div>
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive.Root>
  );
}
