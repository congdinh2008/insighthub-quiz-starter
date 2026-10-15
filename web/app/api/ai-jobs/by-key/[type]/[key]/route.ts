import { readJob } from "@/lib/jobs-server";

// Đối soát theo idempotency key khi client chưa nhận được id (mất kết nối ngay sau khi gửi).
export async function GET(req: Request, context: { params: Promise<{ type: string; key: string }> }) {
  const { type, key } = await context.params;
  return readJob(req, `/ai-jobs/by-key/${encodeURIComponent(type)}/${encodeURIComponent(key)}`);
}
