// Đọc envelope lỗi chung của API (SRS mục 3.3.1, AI Job scaffold learner-r1.3).
// UI quyết định thông báo theo `code`, không phân tích chuỗi tiếng Việt trong `message`.
export type FieldError = { field: string; code: string };

export type ApiError = {
  status: number;
  code: string;
  message: string;
  requestId: string | null;
  fields: FieldError[];
  retryAfterSeconds: number | null;
};

const FALLBACK_MESSAGE = "Không thể xử lý yêu cầu. Thử lại sau.";

function toSeconds(value: unknown): number | null {
  const seconds = typeof value === "string" ? Number(value) : value;
  return typeof seconds === "number" && Number.isFinite(seconds) && seconds >= 0 ? Math.ceil(seconds) : null;
}

export function parseApiError(status: number, payload: unknown, headers?: Headers): ApiError {
  const body = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const text = (value: unknown) => (typeof value === "string" && value.trim() ? value : null);
  const fields = Array.isArray(body.fields)
    ? body.fields.filter((item): item is FieldError => !!item && typeof item.field === "string" && typeof item.code === "string")
    : [];
  return {
    status,
    code: text(body.code) || (status === 0 ? "network_error" : `http_${status}`),
    message: text(body.message) || text(body.detail) || FALLBACK_MESSAGE,
    requestId: text(body.request_id) || headers?.get("X-Request-ID") || null,
    fields,
    retryAfterSeconds: toSeconds(body.retry_after_seconds) ?? toSeconds(headers?.get("Retry-After") ?? undefined),
  };
}

// Lỗi theo trường dạng { source_ids: "duplicate" } để FormField hiển thị đúng chỗ.
export function fieldErrors(error: ApiError): Record<string, string> {
  return Object.fromEntries(error.fields.map(item => [item.field, item.code]));
}
