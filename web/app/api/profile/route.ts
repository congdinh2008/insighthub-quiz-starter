import { API_URL } from "@/lib/api";

export async function GET() {
  const res = await fetch(`${API_URL}/system/profile`, { cache: "no-store" });
  return Response.json(await res.json(), { status: res.status });
}
