"use client";
import * as React from "react";
import { AlertTriangle, Info, Inbox, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** Khung chờ khi đang tải danh sách. */
export function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="skeleton" aria-hidden="true" className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />;
}

/** Vòng xoay kèm chữ để công nghệ hỗ trợ đọc được trạng thái chờ. */
export function Spinner({ label = "Đang xử lý", className }: { label?: string; className?: string }) {
  return (
    <span role="status" className={cn("inline-flex items-center gap-2 text-sm text-muted-foreground", className)}>
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {label}
    </span>
  );
}

/** Thông báo tại chỗ. variant="error" dùng role="alert"; lỗi cần xử lý không tự biến mất (SRS mục 3.5.1). */
export function Alert({ variant = "info", title, children, action, className }: {
  variant?: "info" | "error" | "warning"; title?: string; children?: React.ReactNode; action?: React.ReactNode; className?: string;
}) {
  const Icon = variant === "info" ? Info : AlertTriangle;
  const tone = variant === "error" ? "border-status-failed/50 text-status-failed" : variant === "warning" ? "border-warning/50 text-warning" : "border-status-processing/40 text-status-processing";
  return (
    <div role={variant === "error" ? "alert" : "status"} className={cn("flex gap-3 rounded-lg border bg-card p-4", tone, className)}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="grid gap-1 text-sm text-foreground">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-muted-foreground">{children}</div>}
        {action && <div className="mt-2">{action}</div>}
      </div>
    </div>
  );
}

/** Danh sách rỗng luôn có hướng dẫn và hành động tiếp theo (IH-UX-004-AC01). */
export function EmptyState({ title, description, action, icon: IconComponent = Inbox, className }: {
  title: string; description?: string; action?: React.ReactNode; icon?: typeof Inbox; className?: string;
}) {
  return (
    <div className={cn("grid justify-items-center gap-2 rounded-xl border border-dashed p-8 text-center", className)}>
      <IconComponent className="size-8 text-muted-foreground" aria-hidden="true" />
      <p className="font-medium">{title}</p>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
