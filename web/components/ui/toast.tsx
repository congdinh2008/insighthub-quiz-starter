"use client";
import * as React from "react";
import { XIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Thông báo tạm thời cho kết quả thành công hoặc thông tin (SRS mục 3.5.1). Không dùng cho lỗi cần xử lý
 * và không đặt thao tác bắt buộc duy nhất trong toast. Vùng aria-live đọc nội dung cho công nghệ hỗ trợ.
 */
type ToastItem = { id: number; message: string; tone: "success" | "info" };
const ToastContext = React.createContext<(message: string, tone?: ToastItem["tone"]) => void>(() => undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<ToastItem[]>([]);
  const notify = React.useCallback((message: string, tone: ToastItem["tone"] = "success") => {
    const id = Date.now() + Math.random();
    setItems(current => [...current, { id, message, tone }]);
    window.setTimeout(() => setItems(current => current.filter(item => item.id !== id)), 6000);
  }, []);
  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-50 grid w-[min(24rem,calc(100%-2rem))] gap-2">
        {items.map(item => (
          <div key={item.id} className={cn("pointer-events-auto flex items-start justify-between gap-3 rounded-lg border bg-popover p-3 text-sm shadow-md", item.tone === "success" ? "border-status-ready/40" : "border-status-processing/40")}>
            <span>{item.message}</span>
            <button type="button" aria-label="Đóng thông báo" onClick={() => setItems(current => current.filter(other => other.id !== item.id))}>
              <XIcon className="size-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return React.useContext(ToastContext);
}
