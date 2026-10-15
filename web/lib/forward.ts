// Chuyển tiếp phiên đăng nhập từ trình duyệt sang API (Auth scaffold, learner-r1.3).
// Chỉ chuyển cookie phiên của InsightHub, không chuyển toàn bộ cookie của trình duyệt.
const SESSION_COOKIES = new Set(["__Secure-insighthub.session_token", "insighthub.session_token"]);

export function sessionCookie(source: Headers): string | undefined {
  const raw = source.get("cookie");
  if (!raw) return undefined;
  const kept = raw.split(";").map(part => part.trim()).filter(part => SESSION_COOKIES.has(part.split("=")[0]));
  return kept.length ? kept.join("; ") : undefined;
}

// Header gửi sang API cho mọi Route Handler: phiên, mã tra cứu và các header bổ sung.
export function apiHeaders(source: Headers, extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { "X-Request-ID": source.get("x-request-id") || crypto.randomUUID(), ...extra };
  const cookie = sessionCookie(source);
  if (cookie) headers.Cookie = cookie;
  return headers;
}
