import { CheckCircle2, CircleAlert, Info, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

/** Trạng thái dùng chung cho tài liệu và tác vụ AI. Luôn có chữ và biểu tượng, không chỉ màu (IH-UX-003-AC02). */
export type Status = "Processing" | "Ready" | "Succeeded" | "Failed" | "NoEvidence" | "Pending";

const styles: Record<Status, { label: string; className: string; Icon: typeof Info }> = {
  Pending: { label: "Đang chờ", className: "text-warning border-warning/40", Icon: CircleAlert },
  Processing: { label: "Đang xử lý", className: "text-status-processing border-status-processing/40", Icon: Loader2 },
  Ready: { label: "Sẵn sàng", className: "text-status-ready border-status-ready/40", Icon: CheckCircle2 },
  Succeeded: { label: "Hoàn tất", className: "text-status-ready border-status-ready/40", Icon: CheckCircle2 },
  NoEvidence: { label: "Không đủ căn cứ", className: "text-status-noevidence border-status-noevidence/40", Icon: Info },
  Failed: { label: "Thất bại", className: "text-status-failed border-status-failed/40", Icon: XCircle },
};

export function StatusBadge({ status, label, className }: { status: Status; label?: string; className?: string }) {
  const { label: defaultLabel, className: tone, Icon } = styles[status];
  return (
    <span data-slot="status-badge" data-status={status} className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium", tone, className)}>
      <Icon aria-hidden="true" className={cn("size-3.5", status === "Processing" && "animate-spin")} />
      {label || defaultLabel}
    </span>
  );
}
