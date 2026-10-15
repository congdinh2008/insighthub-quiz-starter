// InsightHub Web - health endpoint cho môi trường phát triển
export async function GET() {
  return Response.json({ status: "ok", service: "insighthub-sdlc-web" });
}
