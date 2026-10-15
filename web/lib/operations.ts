export type OperationType = "upload" | "retry" | "chat" | "delete";
export type PendingOperation = { type: OperationType; key: string; startedAt: number; deadlineAt: number; documentId?: number };
export type OperationResult = { status: "succeeded" | "failed"; response: any; http_status: number };
import { scopedKey } from "./client-state.ts";

// Khóa gắn người dùng ("anon" cho trang demo chưa đăng nhập). Logout xóa mọi khóa insighthub.* (lib/client-state.ts).
const STORAGE = scopedKey("pending.v1");

export function pendingOperations(): PendingOperation[] {
  try {
    const values = JSON.parse(sessionStorage.getItem(STORAGE) || "[]");
    return Array.isArray(values) ? values.filter(v => v && ["upload", "retry", "chat", "delete"].includes(v.type) && typeof v.key === "string" && Number.isFinite(v.deadlineAt)) : [];
  } catch { return []; }
}

export function beginOperation(type: OperationType, documentId?: number): PendingOperation {
  const operation = { type, key: crypto.randomUUID(), startedAt: Date.now(), deadlineAt: Date.now() + (["upload", "retry"].includes(type) ? 125000 : 65000), documentId };
  // Persist before sending. A reload never generates a replacement request/key.
  sessionStorage.setItem(STORAGE, JSON.stringify([...pendingOperations(), operation]));
  return operation;
}

export function finishOperation(key: string) {
  sessionStorage.setItem(STORAGE, JSON.stringify(pendingOperations().filter(item => item.key !== key)));
}

export async function reconcileOperation(operation: PendingOperation, signal?: AbortSignal): Promise<OperationResult | null> {
  while (!signal?.aborted) {
    try {
      const timeout = AbortSignal.timeout(5000);
      const res = await fetch(`/api/operations/${operation.type}/${encodeURIComponent(operation.key)}`, { cache: "no-store", signal: signal ? AbortSignal.any([signal, timeout]) : timeout });
      if (res.ok) {
        const state = await res.json();
        if (["succeeded", "failed"].includes(state.status)) { finishOperation(operation.key); return state; }
      }
      if (res.status === 404 && Date.now() >= operation.deadlineAt) {
        finishOperation(operation.key);
        return { status: "failed", http_status: 404, response: { detail: "Máy chủ không ghi nhận thao tác trong thời hạn. Có thể gửi lại.", code: "operation_not_found" } };
      }
    } catch { /* Keep the key while connectivity is uncertain. */ }
    if (Date.now() >= operation.deadlineAt || signal?.aborted) return null;
    await new Promise(resolve => setTimeout(resolve, Math.min(1000, Math.max(0, operation.deadlineAt - Date.now()))));
  }
  return null;
}

export async function sendOperation(operation: PendingOperation, url: string, options: RequestInit): Promise<OperationResult | null> {
  try {
    const res = await fetch(url, { ...options, headers: { ...options.headers, "Idempotency-Key": operation.key }, signal: AbortSignal.timeout(Math.max(1, operation.deadlineAt - Date.now())) });
    const response = res.status === 204 ? {} : await res.json();
    // An application error has a code; a proxy/network timeout has no terminal evidence.
    if (res.ok || res.status < 500 || response?.code) {
      finishOperation(operation.key);
      const requestId = res.headers.get("X-Request-ID");
      if (requestId && !res.ok) response.request_id = requestId;
      return { status: res.ok ? "succeeded" : "failed", http_status: res.status, response };
    }
  } catch { /* Reconcile using the persisted key, never resubmit the mutation. */ }
  return reconcileOperation(operation);
}

export function operationError(result: OperationResult | null): string {
  if (!result) return "Chưa xác định được kết quả do mất kết nối. Thao tác đã được lưu để kiểm tra lại; không gửi thao tác mới.";
  const message = typeof result.response?.detail === "string" ? result.response.detail : "Thao tác không thành công. Kiểm tra đầu vào và thử lại.";
  return message + (result.response?.request_id ? ` Mã tra cứu: ${result.response.request_id}` : "");
}
