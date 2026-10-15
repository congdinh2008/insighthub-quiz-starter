// Auth scaffold: ví dụ chuỗi trình duyệt -> Next.js -> API với phiên đăng nhập được chuyển tiếp.
import { API_URL } from "@/lib/api";
import { apiHeaders } from "@/lib/forward";

export async function GET(req: Request) {
  const res = await fetch(`${API_URL}/auth/me`, { cache: "no-store", headers: apiHeaders(req.headers) });
  return Response.json(await res.json(), { status: res.status });
}
