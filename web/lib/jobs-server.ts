// Phía server (Route Handler): chuyển request tạo tác vụ AI sang API (AI Job scaffold learner-r1.3).
// Timeout 125 giây: công cụ AI có deadline 120 giây (LIM-11) cộng thời gian ghi kết quả.
import { API_URL } from "@/lib/api";
import { allowsMutation } from "@/lib/errors";
import { apiHeaders } from "@/lib/forward";

export const AI_JOB_PROXY_TIMEOUT_MS = 125_000;
const MAX_BODY_BYTES = 64_000;

function envelope(status: number, code: string, message: string): Response {
  return Response.json({ code, message, detail: message, request_id: null, fields: [] }, { status });
}

// Dùng trong route của học viên, ví dụ app/api/notebooks/[id]/summaries/route.ts:
//   export async function POST(req: Request, ctx) { return forwardJobRequest(req, `/notebooks/${id}/summaries`); }
// Idempotency-Key bắt buộc do client sinh và giữ (lib/jobs.ts). Server không tự sinh key thay client,
// vì như vậy gửi lại sau khi mất kết nối sẽ tạo tác vụ mới.
export async function forwardJobRequest(req: Request, apiPath: string): Promise<Response> {
  if (!allowsMutation(req)) return envelope(403, "origin_not_allowed", "Origin không được phép.");
  const key = req.headers.get("idempotency-key");
  if (!key) return envelope(400, "idempotency_key_required", "Thiếu Idempotency-Key hợp lệ.");
  const body = await req.text();
  if (new TextEncoder().encode(body).byteLength > MAX_BODY_BYTES) return envelope(413, "request_too_large", "Yêu cầu vượt giới hạn kích thước.");
  try {
    const res = await fetch(`${API_URL}${apiPath}`, {
      method: "POST",
      body,
      headers: apiHeaders(req.headers, { "Content-Type": "application/json", "Idempotency-Key": key }),
      signal: AbortSignal.timeout(AI_JOB_PROXY_TIMEOUT_MS),
      cache: "no-store",
    });
    return passthrough(res);
  } catch {
    // Không biết API đã tiếp nhận hay chưa: client đối soát bằng key (GET /api/ai-jobs/by-key/...), không gửi key mới.
    return envelope(504, "proxy_timeout", "Chưa nhận được phản hồi. Đang kiểm tra lại trạng thái tác vụ.");
  }
}

// Giữ nguyên status, body và các header client cần (mã tra cứu, Retry-After).
export async function passthrough(res: Response): Promise<Response> {
  const headers = new Headers({ "X-Request-ID": res.headers.get("X-Request-ID") || "" });
  const retryAfter = res.headers.get("Retry-After");
  if (retryAfter) headers.set("Retry-After", retryAfter);
  const text = await res.text();
  headers.set("Content-Type", "application/json");
  return new Response(text || "{}", { status: res.status, headers });
}

export async function readJob(req: Request, apiPath: string): Promise<Response> {
  try {
    const res = await fetch(`${API_URL}${apiPath}`, { headers: apiHeaders(req.headers), cache: "no-store", signal: AbortSignal.timeout(10_000) });
    return passthrough(res);
  } catch {
    return envelope(502, "api_unavailable", "API không sẵn sàng.");
  }
}
