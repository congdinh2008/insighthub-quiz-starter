import UploadPanel from "@/components/UploadPanel";
import ChatPanel from "@/components/ChatPanel";
import ProfileDisclosure from "@/components/ProfileDisclosure";
import { headers } from "next/headers";
import { getRuntimeProfile, listDocuments } from "@/lib/api";
import { apiHeaders } from "@/lib/forward";
import type { Document, RuntimeProfile } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  let docs: Document[] = [];
  let initialError = "";
  let profile: RuntimeProfile | null = null;
  try {
    [docs, profile] = await Promise.all([listDocuments(apiHeaders(await headers())), getRuntimeProfile()]);
  } catch {
    initialError = "Không tải được danh sách tài liệu. Kiểm tra API rồi làm mới trạng thái.";
  }

  return (
    <div className="starter-demo">
    <div className="container">
      <header>
        <h1>InsightHub SDLC</h1>
        <p>Tra cứu và hỏi đáp từ tài liệu của bạn</p>
      </header>

      <ProfileDisclosure profile={profile} />

      <div className="grid">
        <UploadPanel initial={docs} initialError={initialError} />
        <ChatPanel />
      </div>

      <footer>
        InsightHub SDLC - Không gian thực hành phát triển phần mềm.
      </footer>
    </div>
    </div>
  );
}
