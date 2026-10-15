import { readJob } from "@/lib/jobs-server";

// Đọc trạng thái tác vụ AI theo id (AI Job scaffold). API kiểm phiên và policy; route chỉ chuyển tiếp.
export async function GET(req: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  return readJob(req, `/ai-jobs/${encodeURIComponent(id)}`);
}
