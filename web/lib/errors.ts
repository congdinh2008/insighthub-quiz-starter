export function errorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return fallback;
}

export function allowsMutation(
  request: Request,
  allowedOrigins = (process.env.MUTATION_ALLOWED_ORIGINS || "http://localhost:3107,http://127.0.0.1:3107").split(",").map(value => value.trim()),
): boolean {
  const origin = request.headers.get("origin");
  return origin === null || allowedOrigins.includes(origin);
}

export function documentError(code?: string | null): string {
  const messages: Record<string, string> = {
    invalid_document: "Tài liệu không có văn bản hợp lệ. Kiểm tra nội dung và định dạng.",
    provider_error: "Dịch vụ AI chưa xử lý được tài liệu. Thử lại với đúng tệp sau khi kiểm cấu hình.",
    provider_rate_limited: "Dịch vụ AI đang giới hạn lưu lượng. Thử lại sau.",
    provider_timeout: "Dịch vụ AI phản hồi chậm. Có thể thử lại với đúng tệp.",
    deadline_exceeded: "Xử lý quá thời hạn. Có thể thử lại với đúng tệp.",
    interrupted: "Xử lý bị gián đoạn. Có thể thử lại với đúng tệp.",
  };
  return code ? messages[code] || "Xử lý không thành công. Kiểm tra cấu hình hoặc liên hệ instructor." : "";
}
