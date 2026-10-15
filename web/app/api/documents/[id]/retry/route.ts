import { API_URL } from "@/lib/api";
import { allowsMutation } from "@/lib/errors";
import { apiHeaders } from "@/lib/forward";

export async function POST(req: Request, context: { params: Promise<{ id: string }> }) {
  if (!allowsMutation(req)) return Response.json({ detail: "Origin không được phép." }, { status: 403 });
  const { id } = await context.params;
  const res = await fetch(`${API_URL}/documents/${encodeURIComponent(id)}/retry`, {
    method: "POST", body: await req.arrayBuffer(),
    headers: apiHeaders(req.headers, { "Content-Type": req.headers.get("content-type") || "application/octet-stream", "Idempotency-Key": req.headers.get("idempotency-key") || crypto.randomUUID() }),
    signal: AbortSignal.timeout(125000),
  });
  return Response.json(await res.json(), { status: res.status, headers: { "X-Request-ID": res.headers.get("X-Request-ID") || "" } });
}
