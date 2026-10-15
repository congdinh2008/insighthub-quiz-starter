// InsightHub Web - API client
// Server Components / Route Handlers gọi API qua docker network (API_INTERNAL_URL).

const API_URL = process.env.API_INTERNAL_URL || "http://api:8000";

export interface Document {
  id: number;
  filename: string;
  status: "pending" | "ready" | "failed";
  chunk_count: number;
  created_at: string | null;
  error_code?: string | null;
  embedding_identity_id?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  updated_at?: string | null;
}

export interface ChatResult {
  historical_sources_unavailable?: boolean;
  status: "Answered" | "NoEvidence";
  answer: string | null;
  claims: { text: string; citation_ids: string[] }[];
  sources: string[];
  citations: { citation_id: string; document_id: number; source_segment_id?: number; source: string; locator: { type: string; value: string }; excerpt: string | null; available?: boolean }[];
  contexts: { source: string; similarity: number; rerank_score?: number | null }[];
  latency_ms: number;
  mode?: "fixture" | "real";
  provider?: string;
  model?: string;
  prompt_version?: string;
  profile?: string;
  retrieval?: { reranker_provider: string; reranker_model?: string | null; context_count: number };
}

export interface RuntimeProfile {
  profile: string;
  mode: "fixture" | "real";
  llm: { provider: string; model: string };
  embedding: { provider: string; model: string; dimension: number };
  reranker: { provider: "none" | "local" | "cohere"; model: string | null };
  disclosure: { external_data_transfer: boolean; notice: string; policy_url: string | null };
}

export async function listDocuments(headers: Record<string, string> = {}): Promise<Document[]> {
  const res = await fetch(`${API_URL}/documents`, { cache: "no-store", headers, signal: AbortSignal.timeout(10000) });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getRuntimeProfile(): Promise<RuntimeProfile> {
  const res = await fetch(`${API_URL}/system/profile`, {
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export { API_URL };
