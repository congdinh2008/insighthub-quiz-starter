// InsightHub Web - list documents proxy cho client component
import { listDocuments } from "@/lib/api";
import { apiHeaders } from "@/lib/forward";

export async function GET(req: Request) {
  try {
    const docs = await listDocuments(apiHeaders(req.headers));
    return Response.json(docs);
  } catch {
    return Response.json([], { status: 502 });
  }
}
